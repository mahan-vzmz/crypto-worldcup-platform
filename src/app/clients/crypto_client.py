"""CoinGecko adapter: fetches market prices for the supported coins.

PROVISIONAL SPEC ASSUMPTIONS (verify against docs/taskbook.md):
- Provider is CoinGecko (``/simple/price``), which works without a key
  (a key, when configured, lifts rate limits).
- CoinGecko does not quote toman, so ``price_toman`` is derived from a
  USD->toman exchange rate injected by the caller. Where that rate
  originates (config, another API) is a service-layer decision.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.clients.base_client import DEFAULT_TIMEOUT, BaseAPIClient
from app.models.crypto import Coin, CryptoPrice
from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

#: Our domain identifiers -> CoinGecko's identifiers. This map is the
#: anti-corruption seam: CoinGecko's naming never leaves this module.
_COINGECKO_IDS: dict[Coin, str] = {
    Coin.BTC: "bitcoin",
    Coin.ETH: "ethereum",
    Coin.SOL: "solana",
}


class CryptoClient(BaseAPIClient):
    """Fetches and maps cryptocurrency prices into domain models."""

    def __init__(
        self,
        *,
        usd_to_toman_rate: float,
        api_key: str = "",
        timeout: tuple[float, float] = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        if usd_to_toman_rate <= 0:
            raise ValueError(
                f"usd_to_toman_rate must be positive, got {usd_to_toman_rate}"
            )
        headers = {"x-cg-demo-api-key": api_key} if api_key else None
        super().__init__(
            COINGECKO_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers,
        )
        self._usd_to_toman_rate = usd_to_toman_rate

    def fetch_prices(self, coins: Sequence[Coin]) -> list[CryptoPrice]:
        """Fetch current prices for *coins* in a single HTTP request.

        Raises:
            APIError: on any transport failure or unexpected payload shape.
        """
        if not coins:
            return []

        payload = self.get_json(
            "/simple/price",
            params={
                "ids": ",".join(_COINGECKO_IDS[coin] for coin in coins),
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
        )
        if not isinstance(payload, dict):
            raise APIError("CoinGecko returned an unexpected payload shape")

        fetched_at = datetime.now(UTC)
        return [self._map_entry(coin, payload, fetched_at) for coin in coins]

    def _map_entry(
        self, coin: Coin, payload: dict[str, Any], fetched_at: datetime
    ) -> CryptoPrice:
        """Translate one CoinGecko entry into a domain ``CryptoPrice``."""
        entry = payload.get(_COINGECKO_IDS[coin])
        if not isinstance(entry, dict) or "usd" not in entry:
            raise APIError(f"CoinGecko response missing data for {coin.symbol}")
        try:
            price_usd = float(entry["usd"])
            change_24h = float(entry.get("usd_24h_change", 0.0))
        except (TypeError, ValueError) as exc:
            raise APIError(
                f"CoinGecko returned non-numeric data for {coin.symbol}"
            ) from exc

        return CryptoPrice(
            symbol=coin.symbol,
            name=coin.full_name,
            price_usd=price_usd,
            price_toman=price_usd * self._usd_to_toman_rate,
            change_24h=change_24h,
            last_updated=fetched_at,
        )