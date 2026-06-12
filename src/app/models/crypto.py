"""Domain models for cryptocurrency data.

Pure value objects: immutable snapshots of market data at a point in
time. No knowledge of APIs, storage, or presentation.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Coin(Enum):
    """The supported coins (V1 frozen scope: exactly these three).

    Each member carries its market symbol and full display name.
    Usage: ``Coin.BTC.symbol`` -> "BTC", ``Coin.BTC.full_name`` -> "Bitcoin".
    """

    BTC = ("BTC", "Bitcoin")
    ETH = ("ETH", "Ethereum")
    SOL = ("SOL", "Solana")

    def __init__(self, symbol: str, full_name: str) -> None:
        self.symbol = symbol
        self.full_name = full_name


@dataclass(frozen=True, slots=True)
class CryptoPrice:
    """A snapshot of a single coin's price at a moment in time.

    Immutable by design: a new observation is a new object
    (use ``dataclasses.replace`` for modified copies).
    Money is ``float`` per ADR-009 (tracked debt TD-02).
    """

    symbol: str
    name: str
    price_usd: float
    price_toman: float
    change_24h: float
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
