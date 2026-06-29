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
    BOURSE = "bourse"


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
    image_url: str = ""
    # Global market data (sourced from CoinGecko for crypto; 0 when unknown).
    market_cap: Decimal = Decimal("0")
    volume_24h: Decimal = Decimal("0")
    rank: int = 0
    # Last-7-days price points for a mini chart. A tuple keeps the model hashable
    # and consistent with its frozen, immutable design.
    sparkline: tuple[float, ...] = ()

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must be a non-empty string")
        if self.price_usd < 0:
            raise ValueError(f"price_usd must be non-negative, got {self.price_usd}")
        if self.price_toman < 0:
            raise ValueError(
                f"price_toman must be non-negative, got {self.price_toman}"
            )
        if self.market_cap < 0:
            raise ValueError(f"market_cap must be non-negative, got {self.market_cap}")
        if self.volume_24h < 0:
            raise ValueError(f"volume_24h must be non-negative, got {self.volume_24h}")
        if self.last_updated.tzinfo is None:
            raise ValueError("last_updated must be timezone-aware (use UTC)")
