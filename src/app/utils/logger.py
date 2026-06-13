"""Centralized logging configuration for the application.

Logging is configured exactly once, at application startup, by calling
``setup_logging``. Every module obtains its own logger via ``get_logger`` (or
``logging.getLogger(__name__)`` directly) and emits records that propagate up to
the root logger, where the handlers configured here decide where they go.

Two destinations are configured:

* A rotating file handler that records everything from ``DEBUG`` upward, giving a
  complete diagnostic trail without growing without bound.
* A console handler that shows only ``WARNING`` and above, keeping normal CLI
  output clean for the user.

Never log secrets (API keys, raw ``.env`` values). Logging is for diagnostics,
not for echoing configuration.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_FILE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_CONSOLE_FORMAT = "%(levelname)-8s | %(message)s"

_DEFAULT_LOG_DIR = Path("data/logs")
_LOG_FILENAME = "app.log"
_MAX_BYTES = 1_000_000  # ~1 MB per file before rollover
_BACKUP_COUNT = 3  # keep app.log plus three rolled-over copies


def setup_logging(
    log_dir: Path = _DEFAULT_LOG_DIR,
    *,
    console_level: int = logging.WARNING,
    file_level: int = logging.DEBUG,
) -> None:
    """Configure application-wide logging. Call once at startup.

    Attaches a rotating file handler and a console handler to the root logger.
    Safe to call more than once: existing handlers are cleared first so handlers
    are never duplicated.

    Args:
        log_dir: Directory for the log file. Created if it does not exist.
        console_level: Minimum level shown on the console. Defaults to WARNING
            so routine INFO/DEBUG messages do not clutter the CLI.
        file_level: Minimum level written to the file. Defaults to DEBUG so the
            log file holds a complete diagnostic record.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / _LOG_FILENAME

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Clear any existing handlers so repeated calls don't duplicate output.
    root_logger.handlers.clear()

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT))
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(console_level)
    console_handler.setFormatter(logging.Formatter(_CONSOLE_FORMAT))
    root_logger.addHandler(console_handler)


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given name.

    Thin wrapper over ``logging.getLogger`` so the rest of the codebase depends
    on this module rather than importing ``logging`` directly. Pass ``__name__``
    from the calling module so the logger's name reflects its location.

    Args:
        name: Logger name, conventionally the module's ``__name__``.

    Returns:
        A configured ``logging.Logger`` instance.
    """
    return logging.getLogger(name)
