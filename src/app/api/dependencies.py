import logging
from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.config.container import Container
from app.config.settings import Settings
from app.services.crypto_service import CryptoService

logger = logging.getLogger(__name__)


@lru_cache
def get_container() -> Container:
    """Return a cached, single instance of the application container."""
    logger.info("Initializing DI Container for API")
    settings = Settings.from_env()
    return Container(settings)


def get_crypto_service(
    container: Annotated[Container, Depends(get_container)],
) -> CryptoService:
    """Inject the CryptoService from the DI container."""
    return container.crypto_service
