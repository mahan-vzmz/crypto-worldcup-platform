"""Tests for service orchestration (#26).

Lightweight in-memory fakes replace the real client and repository so
the cache-then-fetch policy is tested in isolation: no network, no disk.
The BaseRepository ABC is what makes the fake repository a drop-in.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest

from app.config.settings import Settings
from app.models.crypto import Coin, CryptoPrice
from app.services.crypto_service import CACHE_KEY, CryptoService
from app.storage.base_repository import BaseRepository
from app.utils.exceptions import APIError

from pathlib import Path

SETTINGS = Settings(
    data_dir=Path("dummy_dir"),
    crypto_api_key="dummy_crypto",
    football_api_key="dummy_football",
    cache_ttl_seconds=300,
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
        self._store: dict[str, dict[str, Any]] = {}
        self.save_calls = 0

    def save(self, key: str, data: dict[str, Any]) -> None:
        self.save_calls += 1
        self._store[key] = data

    def load(self, key: str) -> dict[str, Any] | None:
        return self._store.get(key)

    def exists(self, key: str) -> bool:
        return key in self._store

    def delete(self, key: str) -> None:
        self._store.pop(key, None)

    def seed_envelope(
        self, key: str, prices: list[CryptoPrice], *, age_seconds: int
    ) -> None:
        """Place a pre-built cache envelope with a chosen age."""
        fetched_at = datetime.now(UTC) - timedelta(seconds=age_seconds)
        self._store[key] = {
            "fetched_at": fetched_at.isoformat(),
            "schema_version": 1,
            "data": {
                "prices": [
                    {
                        "symbol": p.symbol,
                        "name": p.name,
                        "price_usd": p.price_usd,
                        "price_toman": p.price_toman,
                        "change_24h": p.change_24h,
                        "last_updated": p.last_updated.isoformat(),
                    }
                    for p in prices
                ]
            },
        }


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
    # The fake client is structurally compatible; ignore the nominal type.
    return CryptoService(client, repo, SETTINGS)  # type: ignore[arg-type]


class TestFreshCacheHit:
    def test_serves_cache_without_calling_client(self) -> None:
        repo = FakeRepository()
        repo.seed_envelope(CACHE_KEY, [a_price()], age_seconds=10)
        client = FakeCryptoClient(fail=True)  # would raise if called
        service = build_service(client, repo)

        result = service.get_prices(COINS)

        assert client.fetch_calls == 0
        assert result[0].symbol == "BTC"


class TestStaleAndMiss:
    def test_stale_cache_triggers_fetch_and_save(self) -> None:
        repo = FakeRepository()
        repo.seed_envelope(CACHE_KEY, [a_price()], age_seconds=10_000)
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
        repo.seed_envelope(CACHE_KEY, [a_price()], age_seconds=10_000)
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
