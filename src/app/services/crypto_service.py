"""Crypto orchestration: cache-then-fetch with TTL and offline fallback.

Owns the policy ADR-006 describes: serve fresh cache, refetch when
stale, fall back to stale cache when the API is unreachable. Depends on
abstractions (BaseRepository) injected via the constructor, so it is
testable with fakes and no network or filesystem.
"""

from datetime import datetime
from typing import Any

from app.clients.protocols import CryptoClientProtocol
from app.config.settings import Settings
from app.models.crypto import Coin, CryptoPrice
from app.services.cache_policy import is_fresh
from app.storage.base_repository import BaseRepository
from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)

CACHE_KEY = "crypto_prices"


class CryptoService:
    """Coordinates the crypto client and the cache repository."""

    def __init__(
        self,
        client: CryptoClientProtocol,
        repository: BaseRepository,
        settings: Settings,
    ) -> None:
        self._client = client
        self._repository = repository
        self._settings = settings

    def get_prices(self, coins: list[Coin]) -> list[CryptoPrice]:
        """Return prices, preferring fresh cache, then API, then stale cache.

        Raises:
            APIError: only when the API fails and no cache exists at all.
        """
        envelope = self._repository.load(CACHE_KEY)

        if envelope is not None and is_fresh(
            envelope, self._settings.cache_ttl_seconds
        ):
            logger.debug("crypto cache hit (fresh)")
            return self._deserialize(envelope["data"])

        try:
            prices = self._client.fetch_prices(coins)
        except APIError:
            if envelope is not None:
                logger.warning("crypto API unavailable; serving stale cache")
                return self._deserialize(envelope["data"])
            logger.error("crypto API unavailable and no cache to fall back on")
            raise

        self._repository.save(CACHE_KEY, self._serialize(prices))
        logger.debug("crypto cache refreshed from API")
        return prices

    @staticmethod
    def _serialize(prices: list[CryptoPrice]) -> dict[str, Any]:
        """Map domain models to a JSON-safe payload (datetime -> ISO)."""
        return {
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
        }

    @staticmethod
    def _deserialize(data: dict[str, Any]) -> list[CryptoPrice]:
        """Map a cached payload back to validated domain models.

        Reconstruction re-runs __post_init__, so corrupt cached values
        cannot silently re-enter the domain.
        """
        return [
            CryptoPrice(
                symbol=item["symbol"],
                name=item["name"],
                price_usd=item["price_usd"],
                price_toman=item["price_toman"],
                change_24h=item["change_24h"],
                last_updated=datetime.fromisoformat(item["last_updated"]),
            )
            for item in data["prices"]
        ]
