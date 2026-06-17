"""Entry point for running the Telegram Bot."""

import sys

from app.bot.main import run_bot
from app.config.container import Container
from app.config.settings import Settings
from app.utils.exceptions import ConfigError
from app.utils.logger import get_logger, setup_logging


def main() -> None:
    """Entry point for the Telegram bot."""
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    settings.ensure_directories()
    setup_logging(settings.logs_dir)
    logger = get_logger(__name__)
    logger.info("Starting Telegram Bot entry point; data_dir=%s", settings.data_dir)

    container = Container(settings)

    try:
        run_bot(container)
    except Exception as e:
        logger.exception("Fatal error in Telegram Bot: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
