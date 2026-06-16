"""Tests for the configuration layer (Settings.from_env).

Each test isolates the environment with monkeypatch so no real ``.env`` or
ambient variable can leak in. These guard the composition root's contract:
every field main.py reads must exist and validate.
"""

from pathlib import Path

import pytest

from app.config.settings import Settings
from app.utils.exceptions import ConfigError

# Variables from_env reads; cleared before each test for a known baseline.
_ENV_VARS = (
    "DATA_DIR",
    "CACHE_TTL_SECONDS",
    "CRYPTO_API_KEY",
    "FOOTBALL_API_KEY",
)


@pytest.fixture
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # Neutralize any real .env file so these tests depend only on the
    # variables they set explicitly -- never the developer's local secrets.
    monkeypatch.setattr("app.config.settings.load_dotenv", lambda *a, **k: False)
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


class TestDefaults:
    def test_defaults_applied_when_env_empty(self, clean_env: None) -> None:
        settings = Settings.from_env()
        assert settings.data_dir == Path("data")
        assert settings.cache_ttl_seconds == 300
        assert settings.crypto_api_key == ""
        assert settings.football_api_key == ""

    def test_every_field_main_reads_is_present(self, clean_env: None) -> None:
        # Regression guard: main.py wires these exact attributes.
        settings = Settings.from_env()
        for attr in ("cache_ttl_seconds", "data_dir"):
            assert hasattr(settings, attr)


class TestOverrides:
    def test_env_overrides_are_parsed(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DATA_DIR", "/tmp/custom")
        monkeypatch.setenv("CACHE_TTL_SECONDS", "60")
        monkeypatch.setenv("CRYPTO_API_KEY", "ck")
        monkeypatch.setenv("FOOTBALL_API_KEY", "fk")

        settings = Settings.from_env()

        assert settings.data_dir == Path("/tmp/custom")
        assert settings.cache_ttl_seconds == 60
        assert settings.crypto_api_key == "ck"
        assert settings.football_api_key == "fk"


class TestValidation:
    @pytest.mark.parametrize("bad", ["abc", "1.5"])
    def test_non_integer_ttl_raises(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        monkeypatch.setenv("CACHE_TTL_SECONDS", bad)
        with pytest.raises(ConfigError):
            Settings.from_env()

    @pytest.mark.parametrize("bad", ["0", "-1"])
    def test_non_positive_ttl_raises(
        self, clean_env: None, monkeypatch: pytest.MonkeyPatch, bad: str
    ) -> None:
        monkeypatch.setenv("CACHE_TTL_SECONDS", bad)
        with pytest.raises(ConfigError):
            Settings.from_env()


class TestDirectories:
    def test_ensure_directories_creates_all(self, tmp_path: Path) -> None:
        settings = Settings(
            data_dir=tmp_path / "data",
            cache_ttl_seconds=300,
            crypto_api_key="",
            football_api_key="",
        )
        settings.ensure_directories()
        assert settings.cache_dir.is_dir()
        assert settings.settings_dir.is_dir()
        assert settings.history_dir.is_dir()
        assert settings.logs_dir.is_dir()
