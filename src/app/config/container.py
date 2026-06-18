"""Dependency Injection Container.

Provides a centralized service locator to instantiate and wire all application
dependencies cleanly. Replaces manual wiring in main.py (TD-03).
"""

from app.clients.crypto_client import CryptoClient
from app.clients.fiat_client import FiatClient
from app.clients.football_client import FootballClient
from app.clients.protocols import FootballClientProtocol
from app.config.settings import Settings
from app.models.football import Tournament
from app.services.cache_strategy import TTLCacheStrategy
from app.services.crypto_service import CryptoService
from app.services.football_service import FootballService
from app.storage.sqlalchemy_repository import SQLAlchemyRepository
from app.utils.exceptions import ConfigError
from app.utils.logger import get_logger

logger = get_logger(__name__)


class _UnavailableFootballClient:
    """Stand-in used when no football key is configured."""

    async def fetch_tournament(self, competition_code: str) -> Tournament:
        raise ConfigError("FOOTBALL_API_KEY is not set; football data is unavailable")


class Container:
    """IoC container that wires application components together."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # Core Infrastructure
        self.repository = SQLAlchemyRepository(database_url=self.settings.database_url)
        self.cache_strategy = TTLCacheStrategy(
            ttl_seconds=self.settings.cache_ttl_seconds
        )

        # Clients
        self.crypto_client = CryptoClient(api_key=self.settings.crypto_api_key)
        self.fiat_client = FiatClient()
        self.football_client = self._build_football_client()

        # Services
        self.crypto_service = CryptoService(
            client=self.crypto_client,
            fiat_client=self.fiat_client,
            repository=self.repository,
            cache_strategy=self.cache_strategy,
        )

        self.football_service = FootballService(
            client=self.football_client,
            repository=self.repository,
            cache_strategy=self.cache_strategy,
        )

    def _build_football_client(self) -> FootballClientProtocol:
        try:
            return FootballClient(api_key=self.settings.football_api_key)
        except ConfigError:
            logger.warning(
                "football API key not set; football features will be unavailable"
            )
            return _UnavailableFootballClient()
