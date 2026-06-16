"""Wallex adapter: fetches market prices for the supported coins.

PROVISIONAL SPEC ASSUMPTIONS (verify against docs/taskbook.md):
- Provider is Wallex (``/v1/markets``), an Iranian exchange API.
- Works without an API key for public endpoints.
- Provides native Toman (TMN) and Tether (USDT) pairings, meaning we extract
  both ``price_usd`` and ``price_toman`` directly from the local market,
  bypassing the need for a separate fiat conversion step.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.clients.base_client import DEFAULT_TIMEOUT, BaseAPIClient
from app.models.crypto import Coin, CryptoPrice
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
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        headers = {"X-API-Key": api_key} if api_key else None
        super().__init__(
            WALLEX_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers,
        )

    def fetch_prices(self, coins: Sequence[Coin]) -> list[CryptoPrice]:
        """Fetch current prices for *coins* in a single HTTP request.

        Raises:
            APIError: on any transport failure or unexpected payload shape.
        """
        if not coins:
            return []

        payload = self.get_json("/markets")
        if not isinstance(payload, dict) or "result" not in payload:
            raise APIError("Wallex returned an unexpected payload shape")

        result = payload.get("result", {})
        if not isinstance(result, dict) or "symbols" not in result:
            raise APIError("Wallex payload missing 'symbols' dictionary")

        symbols = result["symbols"]
        if not isinstance(symbols, dict):
            raise APIError("Wallex 'symbols' is not a dictionary")

        fetched_at = datetime.now(UTC)
        return [self._map_entry(coin, symbols, fetched_at) for coin in coins]

    def _map_entry(
        self,
        coin: Coin,
        symbols: dict[str, Any],
        fetched_at: datetime,
    ) -> CryptoPrice:
        """Translate one Wallex entry into a domain ``CryptoPrice``."""
        usd_pair = f"{coin.symbol}USDT"
        tmn_pair = f"{coin.symbol}TMN"

        usd_data = symbols.get(usd_pair)
        tmn_data = symbols.get(tmn_pair)

        if not isinstance(usd_data, dict) or not isinstance(tmn_data, dict):
            raise APIError(f"Wallex response missing data for {coin.symbol}")

        usd_stats = usd_data.get("stats", {})
        tmn_stats = tmn_data.get("stats", {})

        if not isinstance(usd_stats, dict) or not isinstance(tmn_stats, dict):
            raise APIError(f"Wallex stats missing for {coin.symbol}")

        try:
            price_usd = Decimal(str(usd_stats.get("lastPrice", "0")))
            price_toman = Decimal(str(tmn_stats.get("lastPrice", "0")))
            # We use the 24h change from the USDT pair as the primary change metric
            change_24h = Decimal(str(usd_stats.get("24h_ch", "0.0")))
        except (TypeError, ValueError) as exc:
            raise APIError(
                f"Wallex returned non-numeric data for {coin.symbol}"
            ) from exc

        if price_usd <= 0 or price_toman <= 0:
            raise APIError(f"Wallex returned invalid prices for {coin.symbol}")

        return CryptoPrice(
            symbol=coin.symbol,
            name=coin.full_name,
            price_usd=price_usd,
            price_toman=price_toman,
            change_24h=change_24h,
            last_updated=fetched_at,
        )
