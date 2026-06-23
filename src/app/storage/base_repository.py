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
    async def save_prices(self, prices: list[CryptoPrice]) -> None:
        """Persist a fresh batch of prices, stamping it with the current time.

        Each batch is appended to the price history (it does not overwrite
        earlier batches), which is what makes ``get_price_history`` possible.

        Raises:
            StorageError: if the data cannot be written.
        """

    @abstractmethod
    async def load_latest_prices(self) -> "Cached[list[CryptoPrice]] | None":
        """Return the most recently saved batch of prices, or ``None``.

        Absence (a cold cache) is signalled by ``None``, not an exception.

        Raises:
            StorageError: if stored data exists but cannot be read.
        """

    @abstractmethod
    async def get_price_history(self, symbol: str, *, limit: int) -> list[CryptoPrice]:
        """Return up to *limit* most-recent recorded prices for *symbol*.

        Ordered newest first. An empty list means no history yet.

        Raises:
            StorageError: if the history cannot be read.
        """

    # ---- user & watchlist ----

    @abstractmethod
    async def get_or_create_user(
        self, telegram_id: int, username: str | None, first_name: str | None
    ) -> None:
        """Ensure a user exists in the database.

        Raises:
            StorageError: if the data cannot be written.
        """

    @abstractmethod
    async def get_watchlist(self, telegram_id: int) -> list[str]:
        """Return a list of symbols in the user's watchlist.

        Raises:
            StorageError: if the data cannot be read.
        """

    @abstractmethod
    async def add_to_watchlist(self, telegram_id: int, symbol: str) -> bool:
        """Add a symbol to the user's watchlist.

        Returns True if added, False if it already exists.

        Raises:
            StorageError: if the data cannot be written.
        """

    @abstractmethod
    async def remove_from_watchlist(self, telegram_id: int, symbol: str) -> bool:
        """Remove a symbol from the user's watchlist.

        Returns True if removed, False if it wasn't there.

        Raises:
            StorageError: if the data cannot be written.
        """
