"""Crypto orchestration: cache-then-fetch with TTL and offline fallback.

Owns the policy ADR-006 describes: serve fresh cache, refetch when stale,
fall back to stale cache when the API is unreachable. Depends on
abstractions (CryptoClientProtocol, BaseRepository) injected via the
constructor, so it is testable with fakes and no network or filesystem.

V2: the repository now maps domain models <-> rows itself, so the service no
longer (de)serializes -- it just orchestrates. It also exposes price history.
"""

from app.clients.protocols import CryptoClientProtocol
from app.models.crypto import Coin, CryptoPrice
from app.services.cache_strategy import CacheStrategyProtocol
from app.storage.base_repository import BaseRepository
from app.utils.exceptions import APIError
from app.utils.logger import get_logger
from app.utils.result import Err, Ok, Result

logger = get_logger(__name__)


class CryptoService:
    """Coordinates the crypto client and the storage repository."""

    def __init__(
        self,
        client: CryptoClientProtocol,
        repository: BaseRepository,
        cache_strategy: CacheStrategyProtocol,
    ) -> None:
        self._client = client
        self._repository = repository
        self._cache_strategy = cache_strategy

    def get_prices(self, coins: list[Coin]) -> Result[list[CryptoPrice], APIError]:
        """Return prices, preferring fresh cache, then API, then stale cache.

        Returns an Ok with prices on success, or an Err with an APIError
        if the API fails and no cache exists at all.
        """
        cached = self._repository.load_latest_prices()
        if cached is not None and self._cache_strategy.is_fresh(cached.fetched_at):
            logger.debug("crypto cache hit (fresh)")
            return Ok(cached.data)

        try:
            prices = self._client.fetch_prices(coins)
        except APIError as exc:
            if cached is not None:
                logger.warning("crypto API unavailable; serving stale cache")
                return Ok(cached.data)
            logger.error("crypto API unavailable and no cache to fall back on")
            return Err(exc)

        self._repository.save_prices(prices)
        logger.debug("crypto cache refreshed from API")
        return Ok(prices)

    def get_price_history(
        self, coin: Coin, *, limit: int = 10
    ) -> Result[list[CryptoPrice], APIError]:
        """Return up to *limit* most-recent recorded prices for *coin*.

        Reads straight from storage (no network), so it never fails with APIError.
        """
        prices = self._repository.get_price_history(coin.symbol, limit=limit)
        return Ok(prices)
