from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_crypto_service, get_football_service
from app.api.main import app
from app.models.crypto import Coin, CryptoPrice
from app.models.football import Tournament
from app.utils.exceptions import APIError
from app.utils.result import Err, Ok


class FakeCryptoService:
    def get_prices(self, coins: list[Coin]) -> Ok[list[CryptoPrice]] | Err[APIError]:
        now = datetime.now(UTC)
        return Ok(
            [
                CryptoPrice(
                    symbol=c.name,
                    name=str(c.value),
                    price_usd=Decimal("50000.0"),
                    price_toman=Decimal("3000000000.0"),
                    change_24h=Decimal("5.0"),
                    last_updated=now,
                )
                for c in coins
            ]
        )

    def get_price_history(
        self, coin: Coin, *, limit: int = 10
    ) -> Ok[list[CryptoPrice]] | Err[APIError]:
        now = datetime.now(UTC)
        return Ok(
            [
                CryptoPrice(
                    symbol=coin.name,
                    name=str(coin.value),
                    price_usd=Decimal("50000.0"),
                    price_toman=Decimal("3000000000.0"),
                    change_24h=Decimal("5.0"),
                    last_updated=now,
                )
            ]
        )


class FakeFootballService:
    def get_tournament(self) -> Ok[Tournament] | Err[APIError]:
        return Ok(Tournament("World Cup", (), "Group Stage"))


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_crypto_service] = lambda: FakeCryptoService()
    app.dependency_overrides[get_football_service] = lambda: FakeFootballService()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_all_prices(client: TestClient) -> None:
    response = client.get("/crypto/prices")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3  # All coins
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


def test_get_tournament(client: TestClient) -> None:
    response = client.get("/football/tournament")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "World Cup"
