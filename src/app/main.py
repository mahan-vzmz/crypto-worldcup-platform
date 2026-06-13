"""Composition root: the one place that wires every layer together.

Ordering is deliberate and anti-fragile (extends the M1 startup
sequence): settings -> directories -> logging -> build data/clients ->
build services -> launch menu. main.py is the only module permitted to
import across all layers (TD-03: manual wiring, acceptable for V1).
"""

import sys
from pathlib import Path

from rich.console import Console

from app.clients.crypto_client import CryptoClient
from app.clients.football_client import FootballClient
from app.config.settings import Settings
from app.presentation.menu import Menu
from app.services.crypto_service import CryptoService
from app.services.football_service import FootballService
from app.storage.json_repository import JSONRepository
from app.utils.exceptions import ConfigError
from app.utils.logger import get_logger, setup_logging


def main() -> None:
    """Entry point for the Crypto & World Cup Information Platform."""
    console = Console()

    # 1. Load settings. Logging is not configured yet, so a ConfigError
    #    must go to stderr, not the logger. Only ConfigError is caught;
    #    real bugs surface loudly.
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    # 2. Ensure runtime directories exist before logging writes (ADR-006).
    settings.ensure_directories()

    # 3. Configure logging once, at the root.
    setup_logging(settings.logs_dir)
    logger = get_logger(__name__)
    logger.info("starting platform; data_dir=%s", settings.data_dir)

    # 4. Build the data layer: one repository, two API clients.
    repository = JSONRepository(base_dir=Path(settings.cache_dir))
    crypto_client = CryptoClient(
        usd_to_toman_rate=settings.usd_to_toman_rate,
        api_key=settings.crypto_api_key,
    )

    # 5. Build services (clients + repository injected).
    crypto_service = CryptoService(crypto_client, repository, settings)

    # The football path needs a key; if absent, build a service whose
    # client raises ConfigError on use -- the menu degrades gracefully
    # rather than crashing the whole app at startup.
    football_client = _build_football_client(settings, logger)
    football_service = FootballService(football_client, repository, settings)

    # 6. Launch the presentation layer.
    Menu(crypto_service, football_service, console=console).run()


def _build_football_client(settings: Settings, logger):  # type: ignore[no-untyped-def]
    """Construct the football client, deferring a missing-key failure
    to point of use so crypto still works without a football key."""
    try:
        return FootballClient(api_key=settings.football_api_key)
    except ConfigError:
        logger.warning(
            "football API key not set; football features will be unavailable"
        )
        # Return an unconfigured client: any call raises ConfigError,
        # which the menu catches and shows as "Unavailable".
        return _UnavailableFootballClient()


class _UnavailableFootballClient:
    """Stand-in used when no football key is configured."""

    def fetch_world_cup(self):  # type: ignore[no-untyped-def]
        raise ConfigError(
            "FOOTBALL_API_KEY is not set; football data is unavailable"
        )


if __name__ == "__main__":
    main()