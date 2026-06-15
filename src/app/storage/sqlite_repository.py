"""SQLite implementation of the repository contract (V2).

Replaces the V1 JSON files with a real relational store. The schema is
normalized: prices live in an append-only ``price_history`` table (so we can
query a coin's history), and a tournament is one ``tournament`` row plus its
``match`` rows (snapshot-only, replaced on each save).

Every ``sqlite3`` failure is translated into ``StorageError`` at this
boundary, per the layering rules. ``sqlite3`` is in the standard library, so
V2 adds no new runtime dependency.
"""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from app.models.crypto import CryptoPrice
from app.models.football import Match, MatchStatus, Team, Tournament
from app.storage.base_repository import BaseRepository, Cached
from app.utils.exceptions import StorageError
from app.utils.logger import get_logger

logger = get_logger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS price_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol       TEXT NOT NULL,
    name         TEXT NOT NULL,
    price_usd    REAL NOT NULL,
    price_toman  REAL NOT NULL,
    change_24h   REAL NOT NULL,
    last_updated TEXT NOT NULL,
    fetched_at   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_price_history_symbol
    ON price_history (symbol, fetched_at);

CREATE TABLE IF NOT EXISTS tournament (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    current_stage TEXT NOT NULL,
    fetched_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS match (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id INTEGER NOT NULL REFERENCES tournament (id) ON DELETE CASCADE,
    home_name     TEXT NOT NULL,
    home_code     TEXT,
    away_name     TEXT NOT NULL,
    away_code     TEXT,
    home_score    INTEGER,
    away_score    INTEGER,
    kickoff       TEXT NOT NULL,
    status        TEXT NOT NULL
);
"""


class SQLiteRepository(BaseRepository):
    """File-backed SQLite storage honouring the BaseRepository contract."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        try:
            with self._connect() as conn:
                conn.executescript(_SCHEMA)
        except sqlite3.Error as exc:
            raise StorageError("failed to initialise the database") from exc

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Yield a connection, committing on success and rolling back on error.

        A fresh connection per operation keeps the CLI simple and avoids
        cross-thread issues; SQLite opens are cheap.
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    # ---- cryptocurrency ----

    def save_prices(self, prices: list[CryptoPrice]) -> None:
        fetched_at = datetime.now(UTC).isoformat()
        try:
            with self._connect() as conn:
                conn.executemany(
                    "INSERT INTO price_history "
                    "(symbol, name, price_usd, price_toman, change_24h, "
                    "last_updated, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            p.symbol,
                            p.name,
                            p.price_usd,
                            p.price_toman,
                            p.change_24h,
                            p.last_updated.isoformat(),
                            fetched_at,
                        )
                        for p in prices
                    ],
                )
        except sqlite3.Error as exc:
            raise StorageError("failed to save prices") from exc
        logger.debug("saved %d price rows", len(prices))

    def load_latest_prices(self) -> Cached[list[CryptoPrice]] | None:
        try:
            with self._connect() as conn:
                head = conn.execute(
                    "SELECT MAX(fetched_at) AS latest FROM price_history"
                ).fetchone()
                if head is None or head["latest"] is None:
                    return None
                latest: str = head["latest"]
                rows = conn.execute(
                    "SELECT * FROM price_history WHERE fetched_at = ? ORDER BY id",
                    (latest,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise StorageError("failed to load latest prices") from exc
        prices = [self._row_to_price(row) for row in rows]
        return Cached(data=prices, fetched_at=datetime.fromisoformat(latest))

    def get_price_history(self, symbol: str, *, limit: int) -> list[CryptoPrice]:
        if limit <= 0:
            return []
        try:
            with self._connect() as conn:
                rows = conn.execute(
                    "SELECT * FROM price_history WHERE symbol = ? "
                    "ORDER BY fetched_at DESC, id DESC LIMIT ?",
                    (symbol, limit),
                ).fetchall()
        except sqlite3.Error as exc:
            raise StorageError(f"failed to load history for {symbol!r}") from exc
        return [self._row_to_price(row) for row in rows]

    # ---- football ----

    def save_tournament(self, tournament: Tournament) -> None:
        fetched_at = datetime.now(UTC).isoformat()
        try:
            with self._connect() as conn:
                # Snapshot-only: drop the previous tournament (matches cascade).
                conn.execute("DELETE FROM tournament")
                cursor = conn.execute(
                    "INSERT INTO tournament (name, current_stage, fetched_at) "
                    "VALUES (?, ?, ?)",
                    (tournament.name, tournament.current_stage, fetched_at),
                )
                tournament_id = cursor.lastrowid
                conn.executemany(
                    "INSERT INTO match (tournament_id, home_name, home_code, "
                    "away_name, away_code, home_score, away_score, kickoff, "
                    "status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    [
                        (
                            tournament_id,
                            m.home_team.name,
                            m.home_team.code,
                            m.away_team.name,
                            m.away_team.code,
                            m.home_score,
                            m.away_score,
                            m.kickoff.isoformat(),
                            m.status.value,
                        )
                        for m in tournament.matches
                    ],
                )
        except sqlite3.Error as exc:
            raise StorageError("failed to save tournament") from exc
        logger.debug("saved tournament with %d matches", len(tournament.matches))

    def load_latest_tournament(self) -> Cached[Tournament] | None:
        try:
            with self._connect() as conn:
                trow = conn.execute(
                    "SELECT * FROM tournament ORDER BY fetched_at DESC, id DESC LIMIT 1"
                ).fetchone()
                if trow is None:
                    return None
                mrows = conn.execute(
                    "SELECT * FROM match WHERE tournament_id = ? ORDER BY id",
                    (trow["id"],),
                ).fetchall()
        except sqlite3.Error as exc:
            raise StorageError("failed to load tournament") from exc
        tournament = Tournament(
            name=trow["name"],
            matches=tuple(self._row_to_match(row) for row in mrows),
            current_stage=trow["current_stage"],
        )
        return Cached(
            data=tournament,
            fetched_at=datetime.fromisoformat(trow["fetched_at"]),
        )

    # ---- row mappers (anti-corruption from DB rows to domain models) ----

    @staticmethod
    def _row_to_price(row: sqlite3.Row) -> CryptoPrice:
        return CryptoPrice(
            symbol=row["symbol"],
            name=row["name"],
            price_usd=row["price_usd"],
            price_toman=row["price_toman"],
            change_24h=row["change_24h"],
            last_updated=datetime.fromisoformat(row["last_updated"]),
        )

    @staticmethod
    def _row_to_match(row: sqlite3.Row) -> Match:
        return Match(
            home_team=Team(name=row["home_name"], code=row["home_code"]),
            away_team=Team(name=row["away_name"], code=row["away_code"]),
            home_score=row["home_score"],
            away_score=row["away_score"],
            kickoff=datetime.fromisoformat(row["kickoff"]),
            status=MatchStatus(row["status"]),
        )
