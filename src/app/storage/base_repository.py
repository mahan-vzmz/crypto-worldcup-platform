"""Abstract persistence contract: the seam between services and storage.

Services depend on this interface, never on a concrete backend
(Dependency Inversion). Implementations (JSON in V1, possibly a
database later) must honour every contract documented below, and must
translate all foreign failures (OSError, json errors, ...) into
``StorageError`` at this boundary.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseRepository(ABC):
    """Key-value persistence for JSON-shaped payloads.

    Keys are short, stable identifiers (e.g. ``"crypto_prices"``).
    Payloads are plain ``dict`` structures; mapping domain models to
    and from dicts is the caller's concern, not the repository's.
    """

    @abstractmethod
    def save(self, key: str, data: dict[str, Any]) -> None:
        """Persist *data* under *key*, overwriting any existing record.

        Raises:
            StorageError: if the data cannot be written.
        """

    @abstractmethod
    def load(self, key: str) -> dict[str, Any] | None:
        """Return the record stored under *key*, or ``None`` if absent.

        Absence is a normal outcome (e.g. a cold cache) and is signalled
        by ``None``, not an exception.

        Raises:
            StorageError: if the record exists but cannot be read or parsed.
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether a record is stored under *key*.

        Raises:
            StorageError: if existence cannot be determined.
        """

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove the record under *key*. A missing key is a no-op.

        Idempotent by contract: deleting twice is not an error.

        Raises:
            StorageError: if an existing record cannot be removed.
        """
