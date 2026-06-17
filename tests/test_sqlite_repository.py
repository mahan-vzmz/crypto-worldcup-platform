"""Tests for the SQLite implementation of BaseRepository.

Focuses on the round-trip through the database: do domain models serialize
into tables and deserialize back exactly as they were? We use in-memory
or temporary databases so tests remain fast and isolated.
"""

import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from app.models.crypto import AssetType, CryptoPrice
from app.models.football import Match, MatchStatus, Team, Tournament
from app.storage.sqlite_repository import SQLiteRepository


def make_repo(tmp_path: Path) -> SQLiteRepository:
    """Provide a fresh repository pointing to a temporary file."""
    db = tmp_path / "test.db"
    return SQLiteRepository(db_path=db)


def a_price(
    symbol: str = "BTC", price_usd: Decimal = Decimal("65000.0")
) -> CryptoPrice:
    return CryptoPrice(
        symbol=symbol,
        name="Bitcoin" if symbol == "BTC" else symbol,
        price_usd=price_usd,
        price_toman=price_usd * Decimal("90000.0"),
        change_24h=Decimal("1.5"),
        type=AssetType.CRYPTO,
        last_updated=datetime.now(UTC),
    )


def a_tournament() -> Tournament:
    match = Match(
        home_team=Team(name="Argentina", code="ARG"),
        away_team=Team(name="France", code="FRA"),
        home_score=3,
        away_score=3,
        kickoff=datetime.now(UTC),
        status=MatchStatus.FINISHED,
    )
    scheduled = Match(
        home_team=Team(name="Brazil", code="BRA"),
        away_team=Team(name="TBD"),
        home_score=None,
        away_score=None,
        kickoff=datetime.now(UTC),
        status=MatchStatus.SCHEDULED,
    )
    return Tournament(
        name="World Cup",
        code="WC",
        matches=(match, scheduled),
        current_stage="Final",
    )


class TestPricesRoundTrip:
    def test_save_then_load_latest(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        prices = [a_price("BTC"), a_price("ETH")]

        repo.save_prices(prices)
        cached = repo.load_latest_prices()

        assert cached is not None
        assert cached.data == prices
        assert (datetime.now(UTC) - cached.fetched_at).total_seconds() < 1.0

    def test_load_on_empty_returns_none(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        assert repo.load_latest_prices() is None

    def test_latest_reflects_most_recent_batch(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)

        batch1 = [a_price("BTC", Decimal("60000.0"))]
        repo.save_prices(batch1)
        time.sleep(0.01)

        batch2 = [a_price("BTC", Decimal("65000.0"))]
        repo.save_prices(batch2)

        cached = repo.load_latest_prices()
        assert cached is not None
        assert cached.data == batch2


class TestPriceHistory:
    def test_history_is_newest_first_and_limited(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)

        repo.save_prices([a_price("BTC", Decimal("100.0"))])
        time.sleep(0.01)
        repo.save_prices([a_price("BTC", Decimal("110.0"))])
        time.sleep(0.01)
        repo.save_prices([a_price("BTC", Decimal("120.0"))])

        history = repo.get_price_history("BTC", limit=2)

        assert len(history) == 2
        assert history[0].price_usd == Decimal("120.0")
        assert history[1].price_usd == Decimal("110.0")

    def test_history_filters_by_symbol(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save_prices([a_price("BTC"), a_price("ETH", Decimal("3000.0"))])
        repo.save_prices([a_price("BTC"), a_price("SOL", Decimal("150.0"))])

        history = repo.get_price_history("ETH", limit=10)

        assert len(history) == 1
        assert history[0].symbol == "ETH"

    def test_zero_limit_returns_empty(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save_prices([a_price("BTC")])

        history = repo.get_price_history("BTC", limit=0)

        assert history == []


class TestTournamentRoundTrip:
    def test_save_then_load(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        tournament = a_tournament()

        repo.save_tournament(tournament)
        cached = repo.load_tournament("WC")

        assert cached is not None
        assert cached.data == tournament
        assert (datetime.now(UTC) - cached.fetched_at).total_seconds() < 1.0

    def test_load_on_empty_returns_none(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        assert repo.load_tournament("WC") is None

    def test_save_replaces_previous_snapshot(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)

        first = a_tournament()
        repo.save_tournament(first)
        time.sleep(0.01)

        second = Tournament(
            name="World Cup",
            code="WC",
            matches=first.matches[:1],
            current_stage="Finished",
        )
        repo.save_tournament(second)

        cached = repo.load_tournament("WC")
        assert cached is not None
        assert cached.data == second
        assert len(cached.data.matches) == 1


class TestPersistence:
    def test_data_survives_a_new_repository_instance(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"

        SQLiteRepository(db_path=db).save_prices([a_price("BTC")])
        cached = SQLiteRepository(db_path=db).load_latest_prices()

        assert cached is not None
        assert cached.data[0].symbol == "BTC"
