"""Structural interfaces for the API clients (the client-side DIP seam).

Services depend on these Protocols, never on the concrete client classes,
so a fake (in tests) or a stand-in can satisfy
the contract by *shape* alone -- no inheritance required.

This mirrors what ``storage.base_repository.BaseRepository`` does for
persistence, but uses ``typing.Protocol`` (structural typing) instead of an
ABC (nominal typing).
"""

from decimal import Decimal
from typing import Protocol

from app.models.crypto import CryptoPrice


class CryptoClientProtocol(Protocol):
    """What a crypto service needs from a crypto client."""

    async def fetch_prices(self) -> list[CryptoPrice]:
        """Fetch current prices for all available assets.

        Raises:
            APIError: on any transport failure or unexpected payload.
        """
        ...


class FiatClientProtocol(Protocol):
    """Interface for fetching fiat exchange rates."""

    async def fetch_rates(self, base_currency: str = "USD") -> dict[str, Decimal]:
        """Fetch current exchange rates against the base currency."""
        ...


class BourseClientProtocol(Protocol):
    """Interface for fetching stock/index data."""

    async def fetch_stocks(self, symbols: list[str]) -> dict[str, dict[str, str | Decimal]]:
        """Fetch stock market data for the given symbols.
        
        Returns a dictionary mapping symbols to their price and 24h change data.
        Example: {'NVDA': {'price': Decimal('130.50'), 'change': Decimal('2.5')}}
        
        Raises:
            APIError: on any transport failure or unexpected payload.
        """
        ...


