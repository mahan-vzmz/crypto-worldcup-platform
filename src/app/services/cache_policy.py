"""Shared cache-freshness policy for the service layer.

Both services apply the identical TTL rule (ADR-006): cached data is fresh
while the moment it was fetched is within the configured window. Keeping the
rule in one place means the crypto and football services cannot drift apart
in how they judge freshness.

V2 note: the repository now hands the service a typed ``Cached`` value
carrying a real ``datetime`` (instead of a raw JSON envelope), so this helper
takes a ``datetime`` directly.
"""

from datetime import UTC, datetime, timedelta


def is_fresh(fetched_at: datetime, ttl_seconds: int) -> bool:
    """Return whether *fetched_at* is within *ttl_seconds* of now (UTC)."""
    return datetime.now(UTC) - fetched_at <= timedelta(seconds=ttl_seconds)
