"""Shared cache-freshness policy for the service layer.

Both services apply the identical TTL rule (ADR-006): a cache envelope is
fresh while its ``fetched_at`` timestamp is within the configured window.
Keeping the rule in one place means the crypto and football services cannot
drift apart in how they judge freshness.
"""

from datetime import UTC, datetime, timedelta
from typing import Any


def is_fresh(envelope: dict[str, Any], ttl_seconds: int) -> bool:
    """Return whether *envelope* is within *ttl_seconds* of now.

    A missing or unparseable ``fetched_at`` is treated as stale: that is the
    safe default, since it forces a refetch rather than trusting unknown data.
    """
    raw = envelope.get("fetched_at")
    if not isinstance(raw, str):
        return False
    try:
        fetched_at = datetime.fromisoformat(raw)
    except ValueError:
        return False
    return datetime.now(UTC) - fetched_at <= timedelta(seconds=ttl_seconds)
