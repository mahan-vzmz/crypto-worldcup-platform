"""Tests for CryptoService orchestration.

Lightweight in-memory fakes replace the real client and repository so
the cache-then-fetch policy is tested in isolation: no network, no disk.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.models.crypto import AssetType, CryptoPrice
from app.services.cache_strategy import TTLCacheStrategy
from app.services.crypto_service import CryptoService
from app.storage.base_repository import BaseRepository, Cached
from app.utils.exceptions import APIError
from app.utils.result import Err, Ok

SETTINGS = Settings(
    data_dir=Path("dummy_dir"),
    crypto_api_key="dummy_crypto",
    coingecko_api_key="dummy_coingecko",
    cache_ttl_seconds=300,
    telegram_bot_token="dummy_token",
    telegram_broadcast_chat_id="dummy_chat",
)


def a_price() -> CryptoPrice:
    return CryptoPrice(
        symbol="BTC",
        name="Bitcoin",
        price_usd=Decimal("65000.0"),
        price_toman=Decimal("4500000000.0"),
        change_24h=Decimal("2.5"),
        type=AssetType.CRYPTO,
        last_updated=datetime.now(UTC),
    )


class FakeRepository(BaseRepository):
    """In-memory repository honouring the BaseRepository contract."""

    def __init__(self) -> None:
        self._prices: Cached[list[CryptoPrice]] | None = None
        self._history: list[CryptoPrice] = []
        self.save_calls = 0

    async def save_prices(self, prices: list[CryptoPrice]) -> None:
        self.save_calls += 1
        self._prices = Cached(data=list(prices), fetched_at=datetime.now(UTC))
        self._history = list(prices) + self._history

    async def load_latest_prices(self) -> Cached[list[CryptoPrice]] | None:
        return self._prices

    async def get_price_history(self, symbol: str, *, limit: int) -> list[CryptoPrice]:
        return [p for p in self._history if p.symbol == symbol][:limit]

    async def get_or_create_user(
        self, _telegram_id: int, _username: str | None, _first_name: str | None
    ) -> None:
        pass

    async def get_watchlist(self, _telegram_id: int) -> list[str]:
        return []

    async def add_to_watchlist(self, _telegram_id: int, _symbol: str) -> bool:
        return True

    async def remove_from_watchlist(self, _telegram_id: int, _symbol: str) -> bool:
        return True

    def seed_prices(self, prices: list[CryptoPrice], *, age_seconds: int) -> None:
        fetched_at = datetime.now(UTC) - timedelta(seconds=age_seconds)
        self._prices = Cached(data=list(prices), fetched_at=fetched_at)


class FakeCryptoClient:
    def __init__(
        self, prices: list[CryptoPrice] | None = None, *, fail: bool = False
    ) -> None:
        self._prices = prices or []
        self._fail = fail
        self.fetch_calls = 0

    async def fetch_prices(self) -> list[CryptoPrice]:
        self.fetch_calls += 1
        if self._fail:
            raise APIError("simulated outage")
        return self._prices


class FakeMarketDataClient:
    """Stands in for CoinGecko, the global crypto market-data source."""

    def __init__(
        self, prices: list[CryptoPrice] | None = None, *, fail: bool = False
    ) -> None:
        self._prices = prices or []
        self._fail = fail
        self.fetch_calls = 0

    async def fetch_markets(self) -> list[CryptoPrice]:
        self.fetch_calls += 1
        if self._fail:
            raise APIError("simulated market-data outage")
        return self._prices


class FakeFiatClient:
    async def fetch_rates(self, base_currency: str = "USD") -> dict[str, Decimal]:  # noqa: ARG002
        return {}


class FakeBourseClient:
    async def fetch_stocks(
        self, symbols: list[str]
    ) -> dict[str, dict[str, str | Decimal]]:  # noqa: ARG002
        return {}


def build_service(
    client: FakeCryptoClient,
    repo: FakeRepository,
    market_client: FakeMarketDataClient | None = None,
) -> CryptoService:
    cache_strategy = TTLCacheStrategy(ttl_seconds=SETTINGS.cache_ttl_seconds)
    return CryptoService(
        client=client,
        fiat_client=FakeFiatClient(),
        bourse_client=FakeBourseClient(),
        repository=repo,
        cache_strategy=cache_strategy,
        market_client=market_client or FakeMarketDataClient([a_price()]),
    )


class TestFreshCacheHit:
    @pytest.mark.asyncio
    async def test_serves_cache_without_calling_client(self) -> None:
        repo = FakeRepository()
        repo.seed_prices([a_price()], age_seconds=10)
        client = FakeCryptoClient(fail=True)
        service = build_service(client, repo)

        result = await service.get_prices()

        assert client.fetch_calls == 0
        assert isinstance(result, Ok)
        assert result.value[0].symbol == "BTC"


class TestStaleAndMiss:
    @pytest.mark.asyncio
    async def test_stale_cache_triggers_fetch_and_save(self) -> None:
        repo = FakeRepository()
        repo.seed_prices([a_price()], age_seconds=10_000)
        fresh = [a_price()]
        client = FakeCryptoClient(fresh)
        service = build_service(client, repo)

        result = await service.get_prices()

        assert client.fetch_calls == 1
        assert repo.save_calls == 1
        assert isinstance(result, Ok)

    @pytest.mark.asyncio
    async def test_cache_miss_triggers_fetch_and_save(self) -> None:
        repo = FakeRepository()
        client = FakeCryptoClient([a_price()])
        service = build_service(client, repo)

        await service.get_prices()

        assert client.fetch_calls == 1
        assert repo.save_calls == 1


class TestOfflineFallback:
    @pytest.mark.asyncio
    async def test_api_failure_with_stale_cache_serves_stale(self) -> None:
        repo = FakeRepository()
        repo.seed_prices([a_price()], age_seconds=10_000)
        client = FakeCryptoClient(fail=True)
        service = build_service(client, repo, FakeMarketDataClient(fail=True))

        result = await service.get_prices()

        assert client.fetch_calls == 1
        assert repo.save_calls == 0
        assert isinstance(result, Ok)
        assert result.value[0].symbol == "BTC"


class TestCompleteFailure:
    @pytest.mark.asyncio
    async def test_api_failure_with_no_cache_reraises(self) -> None:
        repo = FakeRepository()
        client = FakeCryptoClient(fail=True)
        service = build_service(client, repo, FakeMarketDataClient(fail=True))

        result = await service.get_prices()
        assert isinstance(result, Err)
        assert isinstance(result.error, APIError)


def usdt_price(toman: str = "60000") -> CryptoPrice:
    return CryptoPrice(
        symbol="USDT",
        name="Tether",
        price_usd=Decimal("1.0"),
        price_toman=Decimal(toman),
        change_24h=Decimal("0"),
        type=AssetType.FIAT,
        last_updated=datetime.now(UTC),
    )


def gold_price() -> CryptoPrice:
    return CryptoPrice(
        symbol="XAUT",
        name="Tether Gold",
        price_usd=Decimal("2300"),
        price_toman=Decimal("138000000"),
        change_24h=Decimal("0.5"),
        type=AssetType.METAL,
        last_updated=datetime.now(UTC),
    )


class TestMarketMerge:
    @pytest.mark.asyncio
    async def test_coingecko_crypto_enriched_with_wallex_toman(self) -> None:
        repo = FakeRepository()
        # Wallex provides USDT rate + a metal, but no BTC TMN pair.
        wallex = FakeCryptoClient([usdt_price("60000"), gold_price()])
        # CoinGecko provides the BTC crypto entry (Toman 0, to be enriched).
        market = FakeMarketDataClient([a_price()])
        service = build_service(wallex, repo, market)

        result = await service.get_prices()

        assert isinstance(result, Ok)
        by_symbol = {p.symbol: p for p in result.value}
        # Crypto list comes from CoinGecko, kept once.
        assert "BTC" in by_symbol
        # BTC had no local pair, so Toman is converted via the USDT rate.
        assert by_symbol["BTC"].price_toman == Decimal("60000") * Decimal("65000.0")
        # Non-crypto Wallex entries (USDT, metals) are preserved.
        assert by_symbol["USDT"].type is AssetType.FIAT
        assert by_symbol["XAUT"].type is AssetType.METAL

    @pytest.mark.asyncio
    async def test_coingecko_down_falls_back_to_wallex_crypto(self) -> None:
        repo = FakeRepository()
        wallex = FakeCryptoClient([a_price()])  # BTC crypto from Wallex
        market = FakeMarketDataClient(fail=True)
        service = build_service(wallex, repo, market)

        result = await service.get_prices()

        assert isinstance(result, Ok)
        assert [p.symbol for p in result.value] == ["BTC"]


class TestPriceHistory:
    @pytest.mark.asyncio
    async def test_history_reads_from_repository(self) -> None:
        repo = FakeRepository()
        client = FakeCryptoClient([a_price()])
        service = build_service(client, repo)

        await service.get_prices()
        result = await service.get_price_history("BTC", limit=10)

        assert isinstance(result, Ok)
        assert [p.symbol for p in result.value] == ["BTC"]
