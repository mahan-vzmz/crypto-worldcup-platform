"""Client for fetching stock and index data from Yahoo Finance."""

import asyncio
from decimal import Decimal

import httpx

from app.clients.base_client import BaseAPIClient
from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class YahooBourseClient(BaseAPIClient):
    """Fetches global stock/index data from Yahoo Finance unofficial API."""

    def __init__(self, timeout: float = 10.0) -> None:
        super().__init__("https://query1.finance.yahoo.com", timeout=timeout)
        # Yahoo Finance requires a standard User-Agent
        self._client.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/91.0.4472.124 Safari/537.36"
                )
            }
        )

    async def fetch_stocks(
        self, symbols: list[str]
    ) -> dict[str, dict[str, str | Decimal]]:
        """Fetch stock market data for multiple symbols.

        Yahoo Finance API /v8/finance/chart/{ticker}
        """
        results: dict[str, dict[str, str | Decimal]] = {}

        # Fetch concurrently
        async def _fetch_one(symbol: str) -> None:
            try:
                # We fetch 2 days to calculate 24h change easily if needed,
                # but Yahoo provides regularMarketPrice and regularMarketChangePercent
                data = await self.get_json(
                    f"/v8/finance/chart/{symbol}",
                    params={"interval": "1d", "range": "1d"},
                )

                meta = data["chart"]["result"][0]["meta"]
                price = Decimal(str(meta.get("regularMarketPrice", 0)))
                # Yahoo sometimes gives regularMarketChangePercent as a
                # decimal e.g. 1.25 for 1.25%
                prev_close = Decimal(str(meta.get("chartPreviousClose", 0)))

                change_pct = Decimal("0")
                if prev_close > 0:
                    change_pct = ((price - prev_close) / prev_close) * Decimal("100")

                results[symbol] = {"price": price, "change": change_pct}
            except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
                logger.warning("Failed to fetch bourse data for %s: %s", symbol, exc)

        await asyncio.gather(*[_fetch_one(sym) for sym in symbols])

        if not results:
            raise APIError("Failed to fetch any stock data from Yahoo Finance.")

        return results
