"""Tests for the JSON repository contract (#25).

Uses pytest's tmp_path fixture: a fresh temporary directory per test,
so filesystem behaviour is exercised for real without touching the
project's data/ folders.
"""

import json
from pathlib import Path

import pytest

from app.storage.json_repository import SCHEMA_VERSION, JSONRepository
from app.utils.exceptions import StorageError


def make_repo(tmp_path: Path) -> JSONRepository:
    return JSONRepository(base_dir=tmp_path)


class TestRoundTrip:
    def test_save_then_load_preserves_data(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        payload = {"answer": 42, "nested": {"x": [1, 2, 3]}}
        repo.save("sample", payload)
        envelope = repo.load("sample")
        assert envelope is not None
        assert envelope["data"] == payload
        assert envelope["schema_version"] == SCHEMA_VERSION
        assert "fetched_at" in envelope

    def test_save_overwrites_existing(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save("sample", {"v": 1})
        repo.save("sample", {"v": 2})
        envelope = repo.load("sample")
        assert envelope is not None
        assert envelope["data"] == {"v": 2}


class TestMissing:
    def test_load_missing_returns_none(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        assert repo.load("nope") is None

    def test_exists_reflects_state(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        assert repo.exists("k") is False
        repo.save("k", {"a": 1})
        assert repo.exists("k") is True


class TestCorruption:
    def test_corrupt_json_raises_storage_error(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        (tmp_path / "broken.json").write_text("{ not json", encoding="utf-8")
        with pytest.raises(StorageError):
            repo.load("broken")

    def test_malformed_envelope_raises(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        # Valid JSON, but no "data" key -> malformed envelope.
        (tmp_path / "weird.json").write_text('{"foo": 1}', encoding="utf-8")
        with pytest.raises(StorageError):
            repo.load("weird")


class TestSchemaVersion:
    def test_future_version_treated_as_miss(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        envelope = {
            "fetched_at": "2026-06-12T12:00:00+00:00",
            "schema_version": SCHEMA_VERSION + 1,
            "data": {"x": 1},
        }
        (tmp_path / "future.json").write_text(json.dumps(envelope), encoding="utf-8")
        assert repo.load("future") is None


class TestDelete:
    def test_double_delete_is_idempotent(self, tmp_path: Path) -> None:
        repo = make_repo(tmp_path)
        repo.save("k", {"a": 1})
        repo.delete("k")
        repo.delete("k")  # must not raise
        assert repo.exists("k") is False


class TestKeySafety:
    @pytest.mark.parametrize("bad_key", ["../escape", "a/b", "UPPER", "sp ace"])
    def test_unsafe_keys_raise(self, tmp_path: Path, bad_key: str) -> None:
        repo = make_repo(tmp_path)
        with pytest.raises(StorageError):
            repo.save(bad_key, {"a": 1})
