"""Tests for the CoinGecko market-data client (no live network)."""

from decimal import Decimal
from typing import Any

import pytest

from app.clients.coingecko_client import CoinGeckoClient
from app.models.crypto import AssetType
from app.utils.exceptions import APIError

SAMPLE_ENTRY: dict[str, Any] = {
    "id": "bitcoin",
    "symbol": "btc",
    "name": "Bitcoin",
    "image": "https://example.com/btc.png",
    "current_price": 65000.0,
    "market_cap": 1280000000000,
    "market_cap_rank": 1,
    "total_volume": 35000000000,
    "price_change_percentage_24h": 2.53,
    "sparkline_in_7d": {"price": [64000.0, 64500.5, 65000.0]},
}


def _patch_payload(client: CoinGeckoClient, payload: Any) -> None:
    async def fake_get_json(_path: str, params: dict[str, str] | None = None) -> Any:
        return payload

    client.get_json = fake_get_json  # type: ignore[method-assign]


class TestMapping:
    @pytest.mark.asyncio
    async def test_maps_entry_into_domain_model(self) -> None:
        client = CoinGeckoClient()
        _patch_payload(client, [SAMPLE_ENTRY])

        prices = await client.fetch_markets()

        assert len(prices) == 1
        p = prices[0]
        assert p.symbol == "BTC"  # uppercased
        assert p.name == "Bitcoin"
        assert p.type is AssetType.CRYPTO
        assert p.price_usd == Decimal("65000.0")
        assert p.price_toman == Decimal("0")  # enriched later by the service
        assert p.change_24h == Decimal("2.53")
        assert p.market_cap == Decimal("1280000000000")
        assert p.volume_24h == Decimal("35000000000")
        assert p.rank == 1
        assert p.image_url == "https://example.com/btc.png"
        assert p.sparkline == (64000.0, 64500.5, 65000.0)

    @pytest.mark.asyncio
    async def test_skips_entries_with_non_positive_price(self) -> None:
        client = CoinGeckoClient()
        bad = {**SAMPLE_ENTRY, "current_price": 0}
        _patch_payload(client, [bad, SAMPLE_ENTRY])

        prices = await client.fetch_markets()

        assert len(prices) == 1


class TestPayloadValidation:
    @pytest.mark.asyncio
    async def test_non_list_payload_raises(self) -> None:
        client = CoinGeckoClient()
        _patch_payload(client, {"unexpected": "shape"})

        with pytest.raises(APIError):
            await client.fetch_markets()

    @pytest.mark.asyncio
    async def test_empty_result_raises(self) -> None:
        client = CoinGeckoClient()
        _patch_payload(client, [])

        with pytest.raises(APIError):
            await client.fetch_markets()
