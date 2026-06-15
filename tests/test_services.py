"""Tests for service orchestration.

Lightweight in-memory fakes replace the real client and repository so
the cache-then-fetch policy is tested in isolation: no network, no disk.
The BaseRepository ABC is what makes the fake repository a drop-in;
FakeCryptoClient structurally satisfies CryptoClientProtocol (no inheritance).
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.config.settings import Settings
from app.models.crypto import Coin, CryptoPrice
from app.models.football import Tournament
from app.services.crypto_service import CryptoService
from app.storage.base_repository import BaseRepository, Cached
from app.utils.exceptions import APIError

SETTINGS = Settings(
    data_dir=Path("dummy_dir"),
    crypto_api_key="dummy_crypto",
    football_api_key="dummy_football",
    cache_ttl_seconds=300,
    usd_to_toman_rate=90_000.0,
)
COINS = [Coin.BTC]


def a_price() -> CryptoPrice:
    return CryptoPrice(
        symbol="BTC",
        name="Bitcoin",
        price_usd=65_000.0,
        price_toman=4_500_000_000.0,
        change_24h=2.5,
        last_updated=datetime.now(UTC),
    )


class FakeRepository(BaseRepository):
    """In-memory repository honouring the BaseRepository contract."""

    def __init__(self) -> None:
        self._prices: Cached[list[CryptoPrice]] | None = None
        self._history: list[CryptoPrice] = []
        self._tournament: Cached[Tournament] | None = None
        self.save_calls = 0

    def save_prices(self, prices: list[CryptoPrice]) -> None:
        self.save_calls += 1
        self._prices = Cached(data=list(prices), fetched_at=datetime.now(UTC))
        self._history = list(prices) + self._history

    def load_latest_prices(self) -> Cached[list[CryptoPrice]] | None:
        return self._prices

    def get_price_history(self, symbol: str, *, limit: int) -> list[CryptoPrice]:
        return [p for p in self._history if p.symbol == symbol][:limit]

    def save_tournament(self, tournament: Tournament) -> None:
        self.save_calls += 1
        self._tournament = Cached(data=tournament, fetched_at=datetime.now(UTC))

    def load_latest_tournament(self) -> Cached[Tournament] | None:
        return self._tournament

    def seed_prices(self, prices: list[CryptoPrice], *, age_seconds: int) -> None:
        """Place a pre-built cache entry with a chosen age."""
        fetched_at = datetime.now(UTC) - timedelta(seconds=age_seconds)
        self._prices = Cached(data=list(prices), fetched_at=fetched_at)


class FakeCryptoClient:
    """Stand-in for CryptoClient: returns canned prices or raises."""

    def __init__(
        self, prices: list[CryptoPrice] | None = None, *, fail: bool = False
    ) -> None:
        self._prices = prices or []
        self._fail = fail
        self.fetch_calls = 0

    def fetch_prices(self, coins: list[Coin]) -> list[CryptoPrice]:
        self.fetch_calls += 1
        if self._fail:
            raise APIError("simulated outage")
        return self._prices


def build_service(client: FakeCryptoClient, repo: FakeRepository) -> CryptoService:
    # FakeCryptoClient structurally satisfies CryptoClientProtocol -- no cast needed.
    return CryptoService(client, repo, SETTINGS)


class TestFreshCacheHit:
    def test_serves_cache_without_calling_client(self) -> None:
        repo = FakeRepository()
        repo.seed_prices([a_price()], age_seconds=10)
        client = FakeCryptoClient(fail=True)  # would raise if called
        service = build_service(client, repo)

        result = service.get_prices(COINS)

        assert client.fetch_calls == 0
        assert result[0].symbol == "BTC"


class TestStaleAndMiss:
    def test_stale_cache_triggers_fetch_and_save(self) -> None:
        repo = FakeRepository()
        repo.seed_prices([a_price()], age_seconds=10_000)
        fresh = [a_price()]
        client = FakeCryptoClient(fresh)
        service = build_service(client, repo)

        result = service.get_prices(COINS)

        assert client.fetch_calls == 1
        assert repo.save_calls == 1
        assert result == fresh

    def test_cache_miss_triggers_fetch_and_save(self) -> None:
        repo = FakeRepository()
        client = FakeCryptoClient([a_price()])
        service = build_service(client, repo)

        service.get_prices(COINS)

        assert client.fetch_calls == 1
        assert repo.save_calls == 1


class TestOfflineFallback:
    def test_api_failure_with_stale_cache_serves_stale(self) -> None:
        repo = FakeRepository()
        repo.seed_prices([a_price()], age_seconds=10_000)
        client = FakeCryptoClient(fail=True)
        service = build_service(client, repo)

        result = service.get_prices(COINS)

        assert client.fetch_calls == 1
        assert repo.save_calls == 0  # nothing fresh to save
        assert result[0].symbol == "BTC"


class TestCompleteFailure:
    def test_api_failure_with_no_cache_reraises(self) -> None:
        repo = FakeRepository()
        client = FakeCryptoClient(fail=True)
        service = build_service(client, repo)

        with pytest.raises(APIError):
            service.get_prices(COINS)


class TestPriceHistory:
    def test_history_reads_from_repository(self) -> None:
        repo = FakeRepository()
        client = FakeCryptoClient([a_price()])
        service = build_service(client, repo)

        service.get_prices(COINS)  # records one batch
        history = service.get_price_history(Coin.BTC, limit=10)

        assert [p.symbol for p in history] == ["BTC"]
