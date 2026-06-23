"""Dependency Injection Container.

Provides a centralized service locator to instantiate and wire all application
dependencies cleanly. Replaces manual wiring in main.py (TD-03).
"""

from app.clients.bourse_client import YahooBourseClient
from app.clients.coingecko_client import CoinGeckoClient
from app.clients.crypto_client import CryptoClient
from app.clients.fiat_client import FiatClient
from app.config.settings import Settings
from app.services.cache_strategy import TTLCacheStrategy
from app.services.crypto_service import CryptoService
from app.storage.sqlalchemy_repository import SQLAlchemyRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


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
        self.market_client = CoinGeckoClient(api_key=self.settings.coingecko_api_key)
        self.fiat_client = FiatClient()
        self.bourse_client = YahooBourseClient()

        # Services
        self.crypto_service = CryptoService(
            client=self.crypto_client,
            fiat_client=self.fiat_client,
            bourse_client=self.bourse_client,
            repository=self.repository,
            cache_strategy=self.cache_strategy,
            market_client=self.market_client,
        )
