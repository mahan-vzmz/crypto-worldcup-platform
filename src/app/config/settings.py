"""Application configuration: the single, validated source of truth.

Configuration is loaded once at startup via ``Settings.from_env`` and injected
wherever it is needed. No other module reads the environment directly.

Secrets and environment-specific values (the data directory, API keys) come from
environment variables, optionally populated from a gitignored ``.env`` file.
Non-secret tunable values (such as the cache TTL) have sensible in-code defaults
that the environment may override.

The data directory and its subdirectories are created on startup
(``ensure_directories``) so the application runs correctly on a fresh clone,
where the gitignored runtime folders do not yet exist.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app.utils.exceptions import ConfigError

_DEFAULT_DATA_DIR = "data"
_DEFAULT_CACHE_TTL_SECONDS = 300


@dataclass(frozen=True)
class Settings:
    """Immutable application configuration.

    Attributes:
        data_dir: Root directory for all runtime data (cache, logs, etc.).
        cache_ttl_seconds: How long cached API data is considered fresh.
        crypto_api_key: API key for the cryptocurrency provider. May be empty in
            Version 1 until the client is implemented (Milestone M4).
        football_api_key: API key for the football provider. May be empty until
            Milestone M4.
    """

    data_dir: Path
    cache_ttl_seconds: int
    crypto_api_key: str
    football_api_key: str

    @property
    def cache_dir(self) -> Path:
        """Directory for cached API responses."""
        return self.data_dir / "cache"

    @property
    def settings_dir(self) -> Path:
        """Directory for persisted settings and user preferences."""
        return self.data_dir / "settings"

    @property
    def history_dir(self) -> Path:
        """Directory for request history."""
        return self.data_dir / "history"

    @property
    def logs_dir(self) -> Path:
        """Directory for log files."""
        return self.data_dir / "logs"

    @classmethod
    def from_env(cls) -> "Settings":
        """Build a ``Settings`` instance from the environment.

        Loads variables from a ``.env`` file if present, then reads them with
        sensible defaults for non-secret values. Raises ``ConfigError`` if a
        provided value is malformed.

        Returns:
            A validated, immutable ``Settings`` instance.

        Raises:
            ConfigError: If ``CACHE_TTL_SECONDS`` is set but not a positive
                integer.
        """
        load_dotenv()

        data_dir = Path(os.getenv("DATA_DIR", _DEFAULT_DATA_DIR))

        raw_ttl = os.getenv("CACHE_TTL_SECONDS", str(_DEFAULT_CACHE_TTL_SECONDS))
        try:
            cache_ttl_seconds = int(raw_ttl)
        except ValueError as exc:
            raise ConfigError(
                f"CACHE_TTL_SECONDS must be an integer, got {raw_ttl!r}."
            ) from exc

        if cache_ttl_seconds <= 0:
            raise ConfigError(
                f"CACHE_TTL_SECONDS must be positive, got {cache_ttl_seconds}."
            )

        return cls(
            data_dir=data_dir,
            cache_ttl_seconds=cache_ttl_seconds,
            crypto_api_key=os.getenv("CRYPTO_API_KEY", ""),
            football_api_key=os.getenv("FOOTBALL_API_KEY", ""),
        )

    def ensure_directories(self) -> None:
        """Create all runtime directories if they do not already exist.

        Idempotent: safe to call on every startup. This is what allows the
        application to run on a fresh clone, where the gitignored ``data``
        subdirectories are not present.
        """
        for directory in (
            self.cache_dir,
            self.settings_dir,
            self.history_dir,
            self.logs_dir,
        ):
            directory.mkdir(parents=True, exist_ok=True)