"""Application configuration: the single, validated source of truth."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from app.utils.exceptions import ConfigError

_DEFAULT_DATA_DIR = "data"
_DEFAULT_CACHE_TTL_SECONDS = 300


@dataclass(frozen=True)
class Settings:
    """Immutable application configuration."""

    data_dir: Path
    cache_ttl_seconds: int
    crypto_api_key: str
    telegram_bot_token: str
    telegram_broadcast_chat_id: str

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

    @property
    def db_path(self) -> Path:
        """Path to the SQLite database file (V2 durable storage)."""
        return self.data_dir / "app.db"

    @property
    def database_url(self) -> str:
        """Database connection string (V7 SQLAlchemy)."""
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            return db_url
        return f"sqlite+aiosqlite:///{self.db_path.as_posix()}"

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
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_broadcast_chat_id=os.getenv("TELEGRAM_BROADCAST_CHAT_ID", ""),
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
