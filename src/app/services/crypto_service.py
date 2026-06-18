"""Crypto orchestration: cache-then-fetch with TTL and offline fallback.

Owns the policy ADR-006 describes: serve fresh cache, refetch when stale,
fall back to stale cache when the API is unreachable. Depends on
abstractions (CryptoClientProtocol, BaseRepository) injected via the
constructor, so it is testable with fakes and no network or filesystem.

V2: the repository now maps domain models <-> rows itself, so the service no
longer (de)serializes -- it just orchestrates. It also exposes price history.
"""

from datetime import UTC, datetime
from decimal import Decimal

from app.clients.protocols import CryptoClientProtocol, FiatClientProtocol
from app.models.crypto import AssetType, CryptoPrice
from app.services.cache_strategy import CacheStrategyProtocol
from app.storage.base_repository import BaseRepository
from app.utils.exceptions import APIError
from app.utils.logger import get_logger
from app.utils.result import Err, Ok, Result

logger = get_logger(__name__)


class CryptoService:
    """Coordinates the crypto client, fiat client, and the storage repository."""

    def __init__(
        self,
        client: CryptoClientProtocol,
        fiat_client: FiatClientProtocol,
        repository: BaseRepository,
        cache_strategy: CacheStrategyProtocol,
    ) -> None:
        self._client = client
        self._fiat_client = fiat_client
        self._repository = repository
        self._cache_strategy = cache_strategy

    async def get_prices(self) -> Result[list[CryptoPrice], APIError]:
        """Return prices, preferring fresh cache, then API, then stale cache.

        Returns an Ok with prices on success, or an Err with an APIError
        if the API fails and no cache exists at all.
        """
        cached = await self._repository.load_latest_prices()
        if cached is not None and self._cache_strategy.is_fresh(cached.fetched_at):
            logger.debug("crypto cache hit (fresh)")
            return Ok(cached.data)

        try:
            prices = await self._client.fetch_prices()
        except APIError as exc:
            if cached is not None:
                logger.warning("crypto API unavailable; serving stale cache")
                return Ok(cached.data)
            logger.error("crypto API unavailable and no cache to fall back on")
            return Err(exc)

        # Attempt to enrich with fiat prices (EUR, GBP)
        usd_price_toman = None
        for p in prices:
            if p.symbol == "USDT":
                usd_price_toman = p.price_toman
                break

        if usd_price_toman is not None:
            try:
                rates = await self._fiat_client.fetch_rates("USD")
                fetched_at = datetime.now(UTC)

                # Euro
                if "EUR" in rates:
                    eur_usd = Decimal("1") / rates["EUR"]
                    prices.append(
                        CryptoPrice(
                            symbol="EUR",
                            name="Euro",
                            price_usd=eur_usd,
                            price_toman=eur_usd * usd_price_toman,
                            change_24h=Decimal("0"),  # API doesn't provide 24h change
                            type=AssetType.FIAT,
                            last_updated=fetched_at,
                        )
                    )

                # Pound
                if "GBP" in rates:
                    gbp_usd = Decimal("1") / rates["GBP"]
                    prices.append(
                        CryptoPrice(
                            symbol="GBP",
                            name="British Pound",
                            price_usd=gbp_usd,
                            price_toman=gbp_usd * usd_price_toman,
                            change_24h=Decimal("0"),
                            type=AssetType.FIAT,
                            last_updated=fetched_at,
                        )
                    )
            except APIError as exc:
                logger.warning(f"Failed to fetch fiat rates: {exc}")

        await self._repository.save_prices(prices)
        logger.debug("crypto cache refreshed from API")
        return Ok(prices)

    async def get_price_history(
        self, symbol: str, *, limit: int = 10
    ) -> Result[list[CryptoPrice], APIError]:
        """Return up to *limit* most-recent recorded prices for *symbol*.

        Reads straight from storage (no network), so it never fails with APIError.
        """
        prices = await self._repository.get_price_history(symbol.upper(), limit=limit)
        return Ok(prices)
