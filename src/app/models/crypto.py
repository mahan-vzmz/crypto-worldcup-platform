"""Domain models for cryptocurrency data.

Pure value objects: immutable snapshots of market data at a point in
time. No knowledge of APIs, storage, or presentation.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum


class AssetType(Enum):
    """The type of asset being tracked."""

    CRYPTO = "crypto"
    FIAT = "fiat"
    METAL = "metal"


@dataclass(frozen=True, slots=True)
class CryptoPrice:
    """A snapshot of a single asset's price at a moment in time.

    Immutable by design: a new observation is a new object
    (use ``dataclasses.replace`` for modified copies).
    Money is ``Decimal`` (TD-02 resolved).
    """

    symbol: str
    name: str
    price_usd: Decimal
    price_toman: Decimal
    change_24h: Decimal
    type: AssetType
    last_updated: datetime

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must be a non-empty string")
        if self.price_usd < 0:
            raise ValueError(f"price_usd must be non-negative, got {self.price_usd}")
        if self.price_toman < 0:
            raise ValueError(
                f"price_toman must be non-negative, got {self.price_toman}"
            )
        if self.last_updated.tzinfo is None:
            raise ValueError("last_updated must be timezone-aware (use UTC)")
