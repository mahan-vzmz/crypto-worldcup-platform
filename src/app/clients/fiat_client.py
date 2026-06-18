"""Fiat client adapter: fetches standard fiat exchange rates.

Uses a public free API to get the base exchange rates against USD.
This data is then multiplied by the USDT/TMN rate in the service layer
to provide the true Iranian Toman price for foreign fiat currencies.
"""

from decimal import Decimal

from app.clients.base_client import DEFAULT_TIMEOUT, BaseAPIClient
from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)

FIAT_BASE_URL = "https://api.exchangerate-api.com/v4/latest"


class FiatClient(BaseAPIClient):
    """Fetches exchange rates from a public API."""

    def __init__(
        self,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        super().__init__(
            FIAT_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
        )

    async def fetch_rates(self, base_currency: str = "USD") -> dict[str, Decimal]:
        """Fetch the exchange rates relative to *base_currency*.

        Returns a dictionary mapping currency codes to their rate relative
        to the base currency (e.g. "EUR" -> 0.85).

        Raises:
            APIError: on any transport failure or unexpected payload.
        """
        payload = await self.get_json(f"/{base_currency}")
        if not isinstance(payload, dict) or "rates" not in payload:
            raise APIError("Fiat API returned an unexpected payload shape")

        rates = payload["rates"]
        if not isinstance(rates, dict):
            raise APIError("Fiat API 'rates' is not a dictionary")

        result: dict[str, Decimal] = {}
        for code, rate in rates.items():
            try:
                result[str(code)] = Decimal(str(rate))
            except (TypeError, ValueError):
                continue

        if not result:
            raise APIError("Fiat API returned no valid rates")

        return result
