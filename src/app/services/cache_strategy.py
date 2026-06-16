"""Cache invalidation strategies.

Provides the CacheStrategyProtocol and implementations like TTLCacheStrategy
to decouple freshness rules from the orchestrating services.
"""

from datetime import UTC, datetime, timedelta
from typing import Protocol


class CacheStrategyProtocol(Protocol):
    """Determines whether a cached item is still valid."""

    def is_fresh(self, fetched_at: datetime) -> bool:
        """Return True if the item fetched at *fetched_at* is still fresh."""
        ...


class TTLCacheStrategy:
    """A time-to-live strategy: fresh if age is less than *ttl_seconds*."""

    def __init__(self, ttl_seconds: int) -> None:
        self.ttl_seconds = ttl_seconds

    def is_fresh(self, fetched_at: datetime) -> bool:
        return datetime.now(UTC) - fetched_at <= timedelta(seconds=self.ttl_seconds)
