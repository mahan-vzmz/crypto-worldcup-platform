"""Structural interfaces for the API clients (the client-side DIP seam).

Services depend on these Protocols, never on the concrete client classes,
so a fake (in tests) or a stand-in (the no-key football case) can satisfy
the contract by *shape* alone -- no inheritance required.

This mirrors what ``storage.base_repository.BaseRepository`` does for
persistence, but uses ``typing.Protocol`` (structural typing) instead of an
ABC (nominal typing). The difference is deliberate: the test fakes and the
unavailable-client stand-in are not subclasses of the real clients, yet they
are valid collaborators because they have the right methods.
"""

from decimal import Decimal
from typing import Protocol

from app.models.crypto import CryptoPrice
from app.models.football import Tournament


class CryptoClientProtocol(Protocol):
    """What a crypto service needs from a crypto client."""

    async def fetch_prices(self) -> list[CryptoPrice]:
        """Fetch current prices for all available assets.

        Raises:
            APIError: on any transport failure or unexpected payload.
        """
        ...


class FootballClientProtocol(Protocol):
    """What a football service needs from a football client."""

    async def fetch_tournament(self, competition_code: str) -> Tournament:
        """Fetch the current snapshot for a specific competition.

        Raises:
            APIError: on transport failure or a malformed payload.
            ConfigError: if the client is unconfigured (no API key).
        """
        ...


class FiatClientProtocol(Protocol):
    """What a crypto service needs to fetch fiat forex rates."""

    def fetch_rates(self, base_currency: str = "USD") -> dict[str, Decimal]:
        """Fetch the exchange rates relative to *base_currency*.

        Raises:
            APIError: on any transport failure or unexpected payload.
        """
        ...
