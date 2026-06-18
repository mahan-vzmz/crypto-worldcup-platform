"""Wallex adapter: fetches market prices for all supported assets.

PROVISIONAL SPEC ASSUMPTIONS (verify against docs/taskbook.md):
- Provider is Wallex (``/v1/markets``), an Iranian exchange API.
- Works without an API key for public endpoints.
- Provides native Toman (TMN) and Tether (USDT) pairings, meaning we extract
  both ``price_usd`` and ``price_toman`` directly from the local market.
"""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.clients.base_client import DEFAULT_TIMEOUT, BaseAPIClient
from app.models.crypto import AssetType, CryptoPrice
from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)

WALLEX_BASE_URL = "https://api.wallex.ir/v1"


class CryptoClient(BaseAPIClient):
    """Fetches and maps cryptocurrency prices from Wallex into domain models."""

    def __init__(
        self,
        *,
        api_key: str = "",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        headers = {"X-API-Key": api_key} if api_key else None
        super().__init__(
            WALLEX_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers,
        )

    async def fetch_prices(self) -> list[CryptoPrice]:
        """Fetch current prices for all available assets in a single HTTP request.

        Raises:
            APIError: on any transport failure or unexpected payload shape.
        """
        payload = await self.get_json("/markets")
        if not isinstance(payload, dict) or "result" not in payload:
            raise APIError("Wallex returned an unexpected payload shape")

        result = payload.get("result", {})
        if not isinstance(result, dict) or "symbols" not in result:
            raise APIError("Wallex payload missing 'symbols' dictionary")

        symbols = result["symbols"]
        if not isinstance(symbols, dict):
            raise APIError("Wallex 'symbols' is not a dictionary")

        fetched_at = datetime.now(UTC)

        # Extract base assets that have both a TMN and USDT pair
        # (or are USDT themselves)
        base_assets: set[str] = set()
        for pair_name in symbols.keys():
            if pair_name.endswith("TMN"):
                base_assets.add(pair_name[:-3])

        prices: list[CryptoPrice] = []
        for symbol in sorted(list(base_assets)):
            # Special case: USDT itself
            if symbol == "USDT":
                price = self._map_usdt(symbols, fetched_at)
                if price:
                    prices.append(price)
            else:
                price = self._map_entry(symbol, symbols, fetched_at)
                if price:
                    prices.append(price)

        return prices

    def _determine_type(self, symbol: str) -> AssetType:
        if symbol in ("XAUT", "PAXG", "XAG"):
            return AssetType.METAL
        if symbol in ("USDT", "USDC", "DAI"):
            return AssetType.FIAT
        return AssetType.CRYPTO

    def _map_usdt(
        self,
        symbols: dict[str, Any],
        fetched_at: datetime,
    ) -> CryptoPrice | None:
        """Map USDT which only has a TMN pair, mapping to USD directly."""
        tmn_data = symbols.get("USDTTMN")
        if not isinstance(tmn_data, dict):
            return None

        tmn_stats = tmn_data.get("stats", {})
        try:
            price_toman = Decimal(str(tmn_stats.get("lastPrice", "0")))
            change_24h = Decimal(str(tmn_stats.get("24h_ch", "0.0")))
        except (TypeError, ValueError, InvalidOperation):
            return None

        if price_toman <= 0:
            return None

        return CryptoPrice(
            symbol="USDT",
            name="US Dollar (Tether)",
            price_usd=Decimal("1.0"),
            price_toman=price_toman,
            change_24h=change_24h,
            type=AssetType.FIAT,
            last_updated=fetched_at,
        )

    def _map_entry(
        self,
        symbol: str,
        symbols: dict[str, Any],
        fetched_at: datetime,
    ) -> CryptoPrice | None:
        """Translate one Wallex entry into a domain ``CryptoPrice``."""
        usd_pair = f"{symbol}USDT"
        tmn_pair = f"{symbol}TMN"

        usd_data = symbols.get(usd_pair)
        tmn_data = symbols.get(tmn_pair)

        if not isinstance(usd_data, dict) or not isinstance(tmn_data, dict):
            return None

        usd_stats = usd_data.get("stats", {})
        tmn_stats = tmn_data.get("stats", {})

        if not isinstance(usd_stats, dict) or not isinstance(tmn_stats, dict):
            return None

        name = usd_data.get("enBaseAsset", symbol)

        try:
            price_usd = Decimal(str(usd_stats.get("lastPrice", "0")))
            price_toman = Decimal(str(tmn_stats.get("lastPrice", "0")))
            # We use the 24h change from the USDT pair as the primary change metric
            change_24h = Decimal(str(usd_stats.get("24h_ch", "0.0")))
        except (TypeError, ValueError, InvalidOperation):
            return None

        if price_usd <= 0 or price_toman <= 0:
            return None

        return CryptoPrice(
            symbol=symbol,
            name=name,
            price_usd=price_usd,
            price_toman=price_toman,
            change_24h=change_24h,
            type=self._determine_type(symbol),
            last_updated=fetched_at,
        )
