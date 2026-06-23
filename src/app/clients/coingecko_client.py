"""CoinGecko adapter: the global crypto market-data source.

CoinGecko's public ``/coins/markets`` endpoint returns everything a
CoinMarketCap-style coin list needs in a single request — logo, price,
24h change, market cap, 24h volume, rank, and an optional 7-day sparkline.

The free, keyless endpoint is rate-limited; the service layer's TTL cache
keeps us comfortably within those limits. An optional API key (CoinGecko
Demo/Pro) raises the ceiling and is sent via the documented header.
"""

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.clients.base_client import DEFAULT_TIMEOUT, BaseAPIClient
from app.models.crypto import AssetType, CryptoPrice
from app.utils.exceptions import APIError
from app.utils.logger import get_logger

logger = get_logger(__name__)

COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

#: How many top coins (by market cap) to pull for the coin list.
DEFAULT_PER_PAGE = 100


class CoinGeckoClient(BaseAPIClient):
    """Fetches and maps the global crypto market into domain models."""

    def __init__(
        self,
        *,
        api_key: str = "",
        per_page: int = DEFAULT_PER_PAGE,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = 3,
    ) -> None:
        # CoinGecko's Demo API uses a dedicated header; harmless if unset.
        headers = {"x-cg-demo-api-key": api_key} if api_key else None
        super().__init__(
            COINGECKO_BASE_URL,
            timeout=timeout,
            max_retries=max_retries,
            headers=headers,
        )
        self._per_page = per_page

    async def fetch_markets(self) -> list[CryptoPrice]:
        """Fetch the top markets by market cap in a single request.

        Raises:
            APIError: on any transport failure or unexpected payload shape.
        """
        payload = await self.get_json(
            "/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": str(self._per_page),
                "page": "1",
                "sparkline": "true",
                "price_change_percentage": "24h",
            },
        )
        if not isinstance(payload, list):
            raise APIError("CoinGecko returned an unexpected payload shape")

        fetched_at = datetime.now(UTC)
        prices: list[CryptoPrice] = []
        for entry in payload:
            if not isinstance(entry, dict):
                continue
            price = self._map_entry(entry, fetched_at)
            if price:
                prices.append(price)

        if not prices:
            raise APIError("CoinGecko returned no usable market entries")

        return prices

    @staticmethod
    def _map_entry(entry: dict[str, Any], fetched_at: datetime) -> CryptoPrice | None:
        """Translate one CoinGecko market entry into a domain ``CryptoPrice``."""
        symbol = str(entry.get("symbol", "")).upper()
        name = str(entry.get("name", "")) or symbol
        if not symbol:
            return None

        try:
            price_usd = Decimal(str(entry.get("current_price") or "0"))
            change_24h = Decimal(str(entry.get("price_change_percentage_24h") or "0"))
            market_cap = Decimal(str(entry.get("market_cap") or "0"))
            volume_24h = Decimal(str(entry.get("total_volume") or "0"))
        except (TypeError, ValueError, InvalidOperation):
            return None

        if price_usd <= 0:
            return None

        rank_raw = entry.get("market_cap_rank")
        rank = int(rank_raw) if isinstance(rank_raw, int) else 0

        spark_raw = entry.get("sparkline_in_7d") or {}
        points = spark_raw.get("price", []) if isinstance(spark_raw, dict) else []
        sparkline: tuple[float, ...] = tuple(
            float(p) for p in points if isinstance(p, (int, float))
        )

        return CryptoPrice(
            symbol=symbol,
            name=name,
            price_usd=price_usd,
            price_toman=Decimal("0"),  # enriched from the local exchange later
            change_24h=change_24h,
            type=AssetType.CRYPTO,
            last_updated=fetched_at,
            image_url=str(entry.get("image", "")),
            market_cap=market_cap if market_cap >= 0 else Decimal("0"),
            volume_24h=volume_24h if volume_24h >= 0 else Decimal("0"),
            rank=rank,
            sparkline=sparkline,
        )
