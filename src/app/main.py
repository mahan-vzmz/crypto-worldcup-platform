"""Composition root: the one place that wires every layer together.

Ordering is deliberate and anti-fragile (extends the M1 startup
sequence): settings -> directories -> logging -> build container ->
launch menu. main.py is the only module permitted to
import across all layers.

V3: Introduced a DI Container to remove manual wiring logic (TD-03).
"""

import asyncio
import sys

from rich.console import Console

from app.config.container import Container
from app.config.settings import Settings
from app.presentation.menu import Menu
from app.utils.exceptions import ConfigError
from app.utils.logger import get_logger, setup_logging


async def async_main() -> None:
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

    # 4. Build the DI Container.
    container = Container(settings)

    # 5. Initialize Database schema
    await container.repository().initialize()

    # 6. Launch the presentation layer.
    await Menu(
        crypto_service=container.crypto_service,
        football_service=container.football_service,
        console=console,
    ).run()

def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
