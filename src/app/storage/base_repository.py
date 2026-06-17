"""Abstract persistence contract: the seam between services and storage.

Services depend on this interface, never on a concrete backend (Dependency
Inversion). Implementations (SQLite in V2; the in-memory fake in tests) must
honour every contract documented below and translate all foreign failures
(``sqlite3`` errors, ...) into ``StorageError`` at this boundary.

V2 change: the contract evolved from a generic key->dict store into a
*domain-specific* interface. This was driven by a new capability -- price
history / queries -- which a flat key-value cache cannot express. See ADR-011.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.crypto import CryptoPrice
from app.models.football import Tournament


@dataclass(frozen=True)
class Cached[T]:
    """A stored value together with the moment it was fetched.

    The ``fetched_at`` timestamp lets the service apply its TTL freshness
    policy without the repository knowing anything about caching.
    """

    data: T
    fetched_at: datetime


class BaseRepository(ABC):
    """Durable storage for the domain's cached data and history."""

    # ---- cryptocurrency ----

    @abstractmethod
    def save_prices(self, prices: list[CryptoPrice]) -> None:
        """Persist a fresh batch of prices, stamping it with the current time.

        Each batch is appended to the price history (it does not overwrite
        earlier batches), which is what makes ``get_price_history`` possible.

        Raises:
            StorageError: if the data cannot be written.
        """

    @abstractmethod
    def load_latest_prices(self) -> "Cached[list[CryptoPrice]] | None":
        """Return the most recently saved batch of prices, or ``None``.

        Absence (a cold cache) is signalled by ``None``, not an exception.

        Raises:
            StorageError: if stored data exists but cannot be read.
        """

    @abstractmethod
    def get_price_history(self, symbol: str, *, limit: int) -> list[CryptoPrice]:
        """Return up to *limit* most-recent recorded prices for *symbol*.

        Ordered newest first. An empty list means no history yet.

        Raises:
            StorageError: if the history cannot be read.
        """

    # ---- football ----

    @abstractmethod
    def save_tournament(self, tournament: Tournament) -> None:
        """Persist the tournament snapshot, replacing any previous one.

        The tournament is snapshot-only (no history in V2): each save
        supersedes the last.

        Raises:
            StorageError: if the data cannot be written.
        """

    @abstractmethod
    def load_tournament(self, name: str) -> "Cached[Tournament] | None":
        """Return the most recently saved tournament by name, or ``None`` if absent.

        Raises:
            StorageError: if stored data exists but cannot be read.
        """
