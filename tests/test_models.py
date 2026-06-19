"""Tests for the CryptoPrice domain model — invariants and immutability."""

from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.crypto import AssetType, CryptoPrice

NOW = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)
NAIVE_NOW = datetime(2026, 6, 12, 12, 0)


def make_price(**overrides: object) -> CryptoPrice:
    defaults: dict[str, object] = {
        "symbol": "BTC",
        "name": "Bitcoin",
        "price_usd": Decimal("65000.0"),
        "price_toman": Decimal("4500000000.0"),
        "change_24h": Decimal("2.5"),
        "type": AssetType.CRYPTO,
        "last_updated": NOW,
    }
    defaults.update(overrides)
    return CryptoPrice(**defaults)  # type: ignore[arg-type]


class TestCryptoPrice:
    def test_happy_path_construction(self) -> None:
        price = make_price()
        assert price.symbol == "BTC"
        assert price.price_usd == Decimal("65000.0")

    def test_negative_change_is_valid(self) -> None:
        assert make_price(change_24h=Decimal("-3.2")).change_24h == Decimal("-3.2")

    def test_negative_price_usd_raises(self) -> None:
        with pytest.raises(ValueError):
            make_price(price_usd=Decimal("-10.0"))

    def test_negative_price_toman_raises(self) -> None:
        with pytest.raises(ValueError):
            make_price(price_toman=Decimal("-1.0"))

    def test_empty_symbol_raises(self) -> None:
        with pytest.raises(ValueError):
            make_price(symbol="")

    def test_naive_datetime_raises(self) -> None:
        with pytest.raises(ValueError):
            make_price(last_updated=NAIVE_NOW)

    def test_mutation_raises(self) -> None:
        price = make_price()
        with pytest.raises(FrozenInstanceError):
            price.price_usd = Decimal("200.0")  # type: ignore[misc]

    def test_replace_creates_new_valid_object(self) -> None:
        original = make_price()
        updated = replace(original, price_usd=Decimal("70000.0"))
        assert updated.price_usd == Decimal("70000.0")
        assert original.price_usd == Decimal("65000.0")

    def test_image_url_defaults_to_empty_string(self) -> None:
        price = make_price()
        assert price.image_url == ""

    def test_image_url_can_be_set(self) -> None:
        price = make_price(image_url="https://example.com/btc.png")
        assert price.image_url == "https://example.com/btc.png"
