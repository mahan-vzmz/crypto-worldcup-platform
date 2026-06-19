"""Tests for the FastAPI routes."""

from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_crypto_service
from app.api.main import app
from app.models.crypto import AssetType, CryptoPrice
from app.utils.exceptions import APIError
from app.utils.result import Err, Ok


class FakeCryptoService:
    async def get_prices(self) -> Ok[list[CryptoPrice]] | Err[APIError]:
        now = datetime.now(UTC)
        return Ok(
            [
                CryptoPrice(
                    symbol="BTC",
                    name="Bitcoin",
                    price_usd=Decimal("50000.0"),
                    price_toman=Decimal("3000000000.0"),
                    change_24h=Decimal("5.0"),
                    type=AssetType.CRYPTO,
                    last_updated=now,
                ),
                CryptoPrice(
                    symbol="ETH",
                    name="Ethereum",
                    price_usd=Decimal("3000.0"),
                    price_toman=Decimal("180000000.0"),
                    change_24h=Decimal("2.0"),
                    type=AssetType.CRYPTO,
                    last_updated=now,
                ),
                CryptoPrice(
                    symbol="SOL",
                    name="Solana",
                    price_usd=Decimal("150.0"),
                    price_toman=Decimal("9000000.0"),
                    change_24h=Decimal("10.0"),
                    type=AssetType.CRYPTO,
                    last_updated=now,
                ),
            ]
        )

    async def get_price_history(
        self, symbol: str, *, limit: int = 10
    ) -> Ok[list[CryptoPrice]] | Err[APIError]:
        now = datetime.now(UTC)
        return Ok(
            [
                CryptoPrice(
                    symbol=symbol.upper(),
                    name="Test Coin",
                    price_usd=Decimal("50000.0"),
                    price_toman=Decimal("3000000000.0"),
                    change_24h=Decimal("5.0"),
                    type=AssetType.CRYPTO,
                    last_updated=now,
                )
            ]
        )


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_crypto_service] = lambda: FakeCryptoService()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_all_prices(client: TestClient) -> None:
    response = client.get("/crypto/prices")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    assert data[0]["symbol"] == "BTC"


def test_get_coin_price(client: TestClient) -> None:
    response = client.get("/crypto/prices/ETH")
    assert response.status_code == 200
    data = response.json()
    assert data["symbol"] == "ETH"


def test_get_price_history(client: TestClient) -> None:
    response = client.get("/crypto/history/SOL")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["symbol"] == "SOL"


def test_invalid_coin(client: TestClient) -> None:
    response = client.get("/crypto/prices/INVALID")
    assert response.status_code == 404
    assert "not supported" in response.json()["detail"]
