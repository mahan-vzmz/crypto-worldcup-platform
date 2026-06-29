"""Tests for the SQLAlchemy repository — round-trip serialization and history."""

import time
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.models.crypto import AssetType, CryptoPrice
from app.storage.sqlalchemy_repository import SQLAlchemyRepository


async def make_repo(tmp_path: Path) -> SQLAlchemyRepository:
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

        await repo.save_prices([a_price("BTC", Decimal("60000.0"))])
        time.sleep(0.01)
        await repo.save_prices([a_price("BTC", Decimal("65000.0"))])

        cached = await repo.load_latest_prices()
        assert cached is not None
        assert len(cached.data) == 1
        assert cached.data[0].price_usd == Decimal("65000.0")


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


class TestSchemaMigration:
    @pytest.mark.asyncio
    async def test_initialize_adds_missing_columns_to_legacy_table(
        self, tmp_path: Path
    ) -> None:
        db_url = f"sqlite+aiosqlite:///{(tmp_path / 'legacy.db').as_posix()}"

        # Build a pre-v9 price_history table that lacks the new columns,
        # with one existing row.
        engine = create_async_engine(db_url)
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "CREATE TABLE price_history ("
                    "id INTEGER PRIMARY KEY AUTOINCREMENT, symbol VARCHAR, "
                    "name VARCHAR, price_usd FLOAT, price_toman FLOAT, "
                    "change_24h FLOAT, asset_type VARCHAR, "
                    "last_updated DATETIME, fetched_at DATETIME)"
                )
            )
            await conn.execute(
                text(
                    "INSERT INTO price_history (symbol, name, price_usd, "
                    "price_toman, change_24h, asset_type, last_updated, "
                    "fetched_at) VALUES ('BTC', 'Bitcoin', 65000, 4000000000, "
                    "1.5, 'crypto', '2026-06-21 16:00:00.000000', "
                    "'2026-06-21 16:00:00.000000')"
                )
            )
        await engine.dispose()

        # Initializing the repository should migrate the table in place.
        repo = SQLAlchemyRepository(database_url=db_url)
        await repo.initialize()

        # The legacy row is now readable, with defaults for the new columns.
        cached = await repo.load_latest_prices()
        assert cached is not None
        assert cached.data[0].symbol == "BTC"
        assert cached.data[0].image_url == ""
        assert cached.data[0].sparkline == ()

        # And new writes carrying the new columns round-trip correctly.
        await repo.save_prices([a_price("ETH", Decimal("3000.0"))])
        latest = await repo.load_latest_prices()
        assert latest is not None
        assert latest.data[0].symbol == "ETH"

    @pytest.mark.asyncio
    async def test_initialize_is_idempotent(self, tmp_path: Path) -> None:
        repo = await make_repo(tmp_path)
        # Running initialize again must not fail or duplicate columns.
        await repo.initialize()
        await repo.save_prices([a_price("BTC")])
        cached = await repo.load_latest_prices()
        assert cached is not None
        assert cached.data[0].symbol == "BTC"


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
