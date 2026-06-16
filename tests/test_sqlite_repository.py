"""Tests for the SQLite repository contract (V2).

Uses pytest's tmp_path fixture: a fresh temporary directory per test, so
real SQLite file behaviour is exercised without touching the project's
data/ folder. ``sqlite3`` is stdlib, so these run anywhere.
"""

import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from app.models.crypto import CryptoPrice
from app.models.football import Match, MatchStatus, Team, Tournament
from app.storage.sqlite_repository import SQLiteRepository


def make_repo(tmp_path: Path) -> SQLiteRepository:
    return SQLiteRepository(db_path=tmp_path / "test.db")


def a_price(
    symbol: str = "BTC", price_usd: Decimal = Decimal("65000.0")
) -> CryptoPrice:
    return CryptoPrice(
        symbol=symbol,
        name="Bitcoin" if symbol == "BTC" else symbol,
        price_usd=price_usd,
        price_toman=price_usd * Decimal("90000.0"),
        change_24h=Decimal("1.5"),
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
        matches=(match, scheduled),
        current_stage="Final",
    )


class TestPricesRoundTrip:
    def test_save_then_load_latest(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        prices = [a_price("BTC"), a_price("ETH", Decimal("3000.0"))]
        repo.save_prices(prices)

        cached = repo.load_latest_prices()

        assert cached is not None
        assert [p.symbol for p in cached.data] == ["BTC", "ETH"]
        assert cached.data[1].price_usd == Decimal("3000.0")

    def test_load_latest_on_empty_returns_none(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        assert repo.load_latest_prices() is None

    def test_latest_reflects_most_recent_batch(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save_prices([a_price("BTC", Decimal("60000.0"))])
        time.sleep(0.01)  # ensure a distinct fetched_at timestamp
        repo.save_prices([a_price("BTC", Decimal("70000.0"))])

        cached = repo.load_latest_prices()

        assert cached is not None
        assert len(cached.data) == 1
        assert cached.data[0].price_usd == Decimal("70000.0")


class TestPriceHistory:
    def test_history_is_newest_first_and_limited(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        for usd in (Decimal("10.0"), Decimal("20.0"), Decimal("30.0")):
            repo.save_prices([a_price("SOL", usd)])
            time.sleep(0.01)

        history = repo.get_price_history("SOL", limit=2)

        assert [p.price_usd for p in history] == [Decimal("30.0"), Decimal("20.0")]

    def test_history_filters_by_symbol(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save_prices([a_price("BTC"), a_price("ETH", Decimal("3000.0"))])

        history = repo.get_price_history("ETH", limit=10)

        assert len(history) == 1
        assert history[0].symbol == "ETH"

    def test_history_empty_for_unknown_symbol(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        assert repo.get_price_history("BTC", limit=10) == []

    def test_zero_limit_returns_empty(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save_prices([a_price("BTC")])
        assert repo.get_price_history("BTC", limit=0) == []


class TestTournamentRoundTrip:
    def test_save_then_load(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save_tournament(a_tournament())

        cached = repo.load_latest_tournament()

        assert cached is not None
        t = cached.data
        assert t.name == "World Cup"
        assert t.current_stage == "Final"
        assert len(t.matches) == 2
        assert t.matches[0].home_team.code == "ARG"
        assert t.matches[0].home_score == 3
        assert t.matches[1].status is MatchStatus.SCHEDULED
        assert t.matches[1].home_score is None

    def test_load_on_empty_returns_none(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        assert repo.load_latest_tournament() is None

    def test_save_replaces_previous_snapshot(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save_tournament(a_tournament())
        time.sleep(0.01)
        repo.save_tournament(
            Tournament(name="World Cup 2", matches=(), current_stage="Group")
        )

        cached = repo.load_latest_tournament()

        assert cached is not None
        assert cached.data.name == "World Cup 2"
        assert cached.data.matches == ()


class TestPersistence:
    def test_data_survives_a_new_repository_instance(self, tmp_path: Path) -> None:
        db = tmp_path / "test.db"
        SQLiteRepository(db_path=db).save_prices([a_price("BTC")])

        # A brand-new instance against the same file must see the data.
        reopened = SQLiteRepository(db_path=db)
        cached = reopened.load_latest_prices()

        assert cached is not None
        assert cached.data[0].symbol == "BTC"
