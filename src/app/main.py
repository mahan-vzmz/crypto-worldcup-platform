"""Application entry point.

Wires the foundation layer together in the correct startup order: load
configuration, create runtime directories, configure logging, then announce a
successful start. Configuration failures are handled gracefully — the program
prints a clear message and exits with a non-zero status. Unexpected errors are
deliberately left to surface, so genuine bugs are not silently swallowed.
"""

import sys

from rich.console import Console
from rich.panel import Panel

from app.config.settings import Settings
from app.utils.exceptions import ConfigError
from app.utils.logger import get_logger, setup_logging

console = Console()


def main() -> None:
    """Start the application foundation and report readiness.

    Startup order is significant: settings must load before anything depends on
    them; directories must exist before logging writes to them; logging must be
    configured before the first log message is emitted.
    """
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(1)

    settings.ensure_directories()
    setup_logging(settings.logs_dir)

    logger = get_logger(__name__)
    logger.info(
        "Application started. data_dir=%s, cache_ttl=%ss",
        settings.data_dir,
        settings.cache_ttl_seconds,
    )

    banner_text = (
        "[bold cyan]Crypto & World Cup Platform[/bold cyan]\n"
        "[green]Foundation initialized successfully![/green]\n\n"
        f"Python Version: {sys.version.split()[0]}"
    )
    console.print(Panel(banner_text, border_style="bold magenta", expand=False))


if __name__ == "__main__":
    main()