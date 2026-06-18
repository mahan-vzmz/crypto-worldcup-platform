"""Tests for the SQLAlchemy implementation of BaseRepository.

Focuses on the round-trip through the database: do domain models serialize
into tables and deserialize back exactly as they were? We use in-memory
or temporary databases so tests remain fast and isolated.
"""

import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from app.models.crypto import AssetType, CryptoPrice
from app.models.football import Match, MatchStatus, Team, Tournament
from app.storage.sqlalchemy_repository import SQLAlchemyRepository


async def make_repo(tmp_path: Path) -> SQLAlchemyRepository:
    """Provide a fresh repository pointing to a temporary file."""
    db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"
    repo = SQLAlchemyRepository(database_url=db_url)
    await repo.initialize()
    return repo


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
    @pytest.mark.asyncio
    async def test_save_then_load_latest(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)
        prices = [a_price("BTC"), a_price("ETH")]

        await repo.save_prices(prices)
        cached = await repo.load_latest_prices()

        assert cached is not None
        assert cached.data == prices
        assert (datetime.now(UTC) - cached.fetched_at).total_seconds() < 1.0

    @pytest.mark.asyncio
    async def test_load_on_empty_returns_none(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)
        assert await repo.load_latest_prices() is None

    @pytest.mark.asyncio
    async def test_latest_reflects_most_recent_batch(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)

        batch1 = [a_price("BTC", Decimal("60000.0"))]
        await repo.save_prices(batch1)
        time.sleep(0.01)

        batch2 = [a_price("BTC", Decimal("65000.0"))]
        await repo.save_prices(batch2)

        cached = await repo.load_latest_prices()
        assert cached is not None
        assert cached.data == batch2


class TestPriceHistory:
    @pytest.mark.asyncio
    async def test_history_is_newest_first_and_limited(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)

        await repo.save_prices([a_price("BTC", Decimal("100.0"))])
        time.sleep(0.01)
        await repo.save_prices([a_price("BTC", Decimal("110.0"))])
        time.sleep(0.01)
        await repo.save_prices([a_price("BTC", Decimal("120.0"))])

        history = await repo.get_price_history("BTC", limit=2)

        assert len(history) == 2
        assert history[0].price_usd == Decimal("120.0")
        assert history[1].price_usd == Decimal("110.0")

    @pytest.mark.asyncio
    async def test_history_filters_by_symbol(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)
        await repo.save_prices([a_price("BTC"), a_price("ETH", Decimal("3000.0"))])
        await repo.save_prices([a_price("BTC"), a_price("SOL", Decimal("150.0"))])

        history = await repo.get_price_history("ETH", limit=10)

        assert len(history) == 1
        assert history[0].symbol == "ETH"

    @pytest.mark.asyncio
    async def test_zero_limit_returns_empty(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)
        await repo.save_prices([a_price("BTC")])

        history = await repo.get_price_history("BTC", limit=0)

        assert history == []


class TestTournamentRoundTrip:
    @pytest.mark.asyncio
    async def test_save_then_load(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)
        tournament = a_tournament()

        await repo.save_tournament(tournament)
        cached = await repo.load_tournament("WC")

        assert cached is not None
        assert cached.data == tournament
        assert (datetime.now(UTC) - cached.fetched_at).total_seconds() < 1.0

    @pytest.mark.asyncio
    async def test_load_on_empty_returns_none(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)
        assert await repo.load_tournament("WC") is None

    @pytest.mark.asyncio
    async def test_save_replaces_previous_snapshot(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)

        first = a_tournament()
        await repo.save_tournament(first)
        time.sleep(0.01)

        second = Tournament(
            name="World Cup",
            code="WC",
            matches=first.matches[:1],
            current_stage="Finished",
        )
        await repo.save_tournament(second)

        cached = await repo.load_tournament("WC")
        assert cached is not None
        assert cached.data == second
        assert len(cached.data.matches) == 1


class TestPersistence:
    @pytest.mark.asyncio
    async def test_data_survives_a_new_repository_instance(
        self, tmp_path: Path
    ) -> None:
        db_url = f"sqlite+aiosqlite:///{(tmp_path / 'test.db').as_posix()}"

        repo1 = SQLAlchemyRepository(database_url=db_url)
        await repo1.initialize()
        await repo1.save_prices([a_price("BTC")])

        repo2 = SQLAlchemyRepository(database_url=db_url)
        await repo2.initialize()
        cached = await repo2.load_latest_prices()

        assert cached is not None
        assert cached.data[0].symbol == "BTC"
