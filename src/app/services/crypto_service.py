"""Crypto orchestration: cache-then-fetch with TTL and offline fallback.

Owns the policy ADR-006 describes: serve fresh cache, refetch when stale,
fall back to stale cache when the API is unreachable. Depends on
abstractions (CryptoClientProtocol, BaseRepository) injected via the
constructor, so it is testable with fakes and no network or filesystem.

V2: the repository now maps domain models <-> rows itself, so the service no
longer (de)serializes -- it just orchestrates. It also exposes price history.
"""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

from app.clients.protocols import (
    BourseClientProtocol,
    CryptoClientProtocol,
    FiatClientProtocol,
    MarketDataClientProtocol,
)
from app.models.crypto import AssetType, CryptoPrice
from app.services.cache_strategy import CacheStrategyProtocol
from app.storage.base_repository import BaseRepository
from app.utils.exceptions import APIError
from app.utils.logger import get_logger
from app.utils.result import Err, Ok, Result

logger = get_logger(__name__)


class CryptoService:
    """Coordinates the market-data sources, fiat client, and storage repository.

    The crypto coin list is sourced from a global provider (CoinGecko) for its
    rich data — logos, market cap, volume, rank, sparklines — then enriched with
    Toman prices from the local exchange (Wallex). The local exchange also
    supplies metals and the USDT/Toman reference rate used to convert fiat.
    """

    def __init__(
        self,
        client: CryptoClientProtocol,
        fiat_client: FiatClientProtocol,
        bourse_client: BourseClientProtocol,
        repository: BaseRepository,
        cache_strategy: CacheStrategyProtocol,
        market_client: MarketDataClientProtocol,
    ) -> None:
        self._client = client
        self._fiat_client = fiat_client
        self._bourse_client = bourse_client
        self._repository = repository
        self._cache_strategy = cache_strategy
        self._market_client = market_client

    async def get_prices(self) -> Result[list[CryptoPrice], APIError]:
        """Return prices, preferring fresh cache, then APIs, then stale cache.

        Returns an Ok with prices on success, or an Err with an APIError if
        every market source fails and no cache exists at all.
        """
        cached = await self._repository.load_latest_prices()
        if cached is not None and self._cache_strategy.is_fresh(cached.fetched_at):
            logger.debug("crypto cache hit (fresh)")
            return Ok(cached.data)

        prices: list[CryptoPrice] = []

        # 1. Local exchange (Wallex): Toman prices, USDT rate, metals, fiat.
        toman_by_symbol: dict[str, Decimal] = {}
        usd_price_toman: Decimal | None = None
        wallex_prices: list[CryptoPrice] | None = None
        try:
            wallex_prices = await self._client.fetch_prices()
        except APIError as exc:
            logger.warning("local exchange (Wallex) unavailable: %s", exc)

        if wallex_prices is not None:
            for p in wallex_prices:
                toman_by_symbol[p.symbol] = p.price_toman
                if p.symbol == "USDT":
                    usd_price_toman = p.price_toman
                # Keep non-crypto entries; CoinGecko owns the crypto list.
                if p.type is not AssetType.CRYPTO:
                    prices.append(p)

        # 2. Global market data (CoinGecko): the crypto coin list itself.
        coins: list[CryptoPrice] | None = None
        try:
            coins = await self._market_client.fetch_markets()
        except APIError as exc:
            logger.warning("global market data (CoinGecko) unavailable: %s", exc)

        if coins is not None:
            for c in coins:
                toman = toman_by_symbol.get(c.symbol)
                if toman is None and usd_price_toman is not None:
                    # No local market for this coin: convert via the USDT rate.
                    toman = usd_price_toman * c.price_usd
                prices.append(
                    replace(c, price_toman=toman if toman is not None else Decimal("0"))
                )
        elif wallex_prices is not None:
            # CoinGecko down: keep Wallex's own crypto entries so the list still
            # renders (without logos / market cap / sparklines).
            prices.extend(p for p in wallex_prices if p.type is AssetType.CRYPTO)

        # If every crypto source failed, fall back to the last good cache.
        if not prices:
            if cached is not None:
                logger.warning("all market sources unavailable; serving stale cache")
                return Ok(cached.data)
            logger.error("all market sources unavailable and no cache to fall back on")
            return Err(APIError("no market data available from any source"))

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

        # Fetch Bourse (Stocks/Indices)
        try:
            bourse_symbols = ["NVDA", "AAPL", "MSFT", "^GSPC", "^IXIC", "^DJI"]
            bourse_names = {
                "NVDA": "Nvidia",
                "AAPL": "Apple",
                "MSFT": "Microsoft",
                "^GSPC": "S&P 500",
                "^IXIC": "NASDAQ",
                "^DJI": "Dow Jones",
            }
            stocks = await self._bourse_client.fetch_stocks(bourse_symbols)
            bourse_fetched_at = datetime.now(UTC)
            for sym, data in stocks.items():
                prices.append(
                    CryptoPrice(
                        symbol=sym,
                        name=bourse_names.get(sym, sym),
                        price_usd=Decimal(str(data["price"])),
                        price_toman=Decimal(
                            "0"
                        ),  # Usually not priced in toman directly
                        change_24h=Decimal(str(data["change"])),
                        type=AssetType.BOURSE,
                        last_updated=bourse_fetched_at,
                    )
                )
        except Exception as exc:
            logger.warning(f"Failed to fetch bourse data: {exc}")

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
