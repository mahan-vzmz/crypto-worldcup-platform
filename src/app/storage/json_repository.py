"""Concrete JSON file storage implementing the BaseRepository contract.

Each key maps to one ``<key>.json`` file inside a base directory.
Writes are atomic (temp file + ``os.replace``) so a crash mid-write can
never corrupt existing data. Every file carries the schema envelope::

    {"fetched_at": "<ISO-8601 UTC>", "schema_version": 1, "data": {...}}

All foreign failures (OSError, json errors, TypeError) are translated
into ``StorageError`` at this boundary, per the layering rules.
"""

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.storage.base_repository import BaseRepository
from app.utils.exceptions import StorageError
from app.utils.logger import get_logger

logger = get_logger(__name__)

SCHEMA_VERSION = 1
_VALID_KEY = re.compile(r"^[a-z0-9_-]+$")


class JSONRepository(BaseRepository):
    """File-per-key JSON storage with atomic writes."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def save(self, key: str, data: dict[str, Any]) -> None:
        path = self._path_for(key)
        tmp_path = path.with_name(path.name + ".tmp")
        envelope: dict[str, Any] = {
            "fetched_at": datetime.now(UTC).isoformat(),
            "schema_version": SCHEMA_VERSION,
            "data": data,
        }
        try:
            with tmp_path.open("w", encoding="utf-8") as file:
                json.dump(envelope, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            os.replace(tmp_path, path)
        except (OSError, TypeError, ValueError) as exc:
            tmp_path.unlink(missing_ok=True)
            raise StorageError(f"failed to save record {key!r}") from exc
        logger.debug("saved record %r to %s", key, path)

    def load(self, key: str) -> dict[str, Any] | None:
        path = self._path_for(key)
        try:
            raw_text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return None  # absence is normal, not an error
        except OSError as exc:
            raise StorageError(f"failed to read record {key!r}") from exc

        try:
            envelope = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise StorageError(f"record {key!r} is corrupt") from exc

        if not isinstance(envelope, dict) or "data" not in envelope:
            raise StorageError(f"record {key!r} has a malformed envelope")

        version = envelope.get("schema_version")
        if version != SCHEMA_VERSION:
            logger.warning(
                "record %r has schema version %r (expected %s); treating as missing",
                key,
                version,
                SCHEMA_VERSION,
            )
            return None

        return envelope

    def exists(self, key: str) -> bool:
        try:
            return self._path_for(key).is_file()
        except OSError as exc:
            raise StorageError(f"failed to check existence of record {key!r}") from exc

    def delete(self, key: str) -> None:
        try:
            self._path_for(key).unlink(missing_ok=True)
        except OSError as exc:
            raise StorageError(f"failed to delete record {key!r}") from exc
        logger.debug("deleted record %r (if it existed)", key)

    def _path_for(self, key: str) -> Path:
        """Map a key to its file path, rejecting unsafe key names."""
        if not _VALID_KEY.fullmatch(key):
            raise StorageError(
                f"invalid key {key!r}: use lowercase letters, digits, "
                "underscores, or hyphens only"
            )
        return self._base_dir / f"{key}.json"
