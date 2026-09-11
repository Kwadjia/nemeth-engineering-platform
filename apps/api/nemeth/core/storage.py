"""File storage interface (ADR-003).

Bytes never live in PostgreSQL. Callers hand a stream to ``FileStorage.put`` under a
server-generated key and get back the size and SHA-256. The only implementation today
writes under ``settings.storage_root``; S3 or Azure Blob backends implement the same
protocol later.
"""

from __future__ import annotations

import hashlib
import os
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Protocol

from nemeth.core.config import Settings

_KEY_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_CHUNK = 1024 * 1024


class StorageKeyError(ValueError):
    """The key is malformed or would escape the storage root."""


@dataclass(frozen=True, slots=True)
class StoredFile:
    key: str
    size: int
    sha256: str


def validate_key(key: str) -> str:
    """Accept only ``segment/segment/...`` keys with safe characters and no traversal."""
    if not key or len(key) > 512:
        raise StorageKeyError("storage key must be 1-512 characters")
    if key.startswith(("/", "\\")) or "\\" in key or ":" in key:
        raise StorageKeyError("storage key must be a relative POSIX path")
    segments = key.split("/")
    for segment in segments:
        if segment in ("", ".", ".."):
            raise StorageKeyError("storage key contains an empty or traversal segment")
        if not _KEY_SEGMENT.match(segment):
            raise StorageKeyError(f"storage key segment {segment!r} contains unsafe characters")
    return key


def make_key(category: str, original_filename: str, *, now: datetime | None = None) -> str:
    """``{category}/{yyyy}/{mm}/{uuid}{ext}`` — the client's name is metadata only."""
    ts = now or datetime.now(tz=UTC)
    suffix = Path(original_filename).suffix.lower()
    if not re.fullmatch(r"(\.[a-z0-9]{1,10})?", suffix):
        suffix = ""
    return validate_key(f"{category}/{ts:%Y}/{ts:%m}/{uuid.uuid4().hex}{suffix}")


class FileStorage(Protocol):
    def put(self, key: str, stream: BinaryIO) -> StoredFile: ...

    def open(self, key: str) -> BinaryIO: ...

    def exists(self, key: str) -> bool: ...

    def delete(self, key: str) -> None: ...

    def stat(self, key: str) -> StoredFile: ...


def _sha256_of(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(_CHUNK), b""):
            digest.update(chunk)
            size += len(chunk)
    return size, digest.hexdigest()


class LocalFileStorage:
    """Files under a root directory. Writes are atomic (temp file + rename)."""

    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        validate_key(key)
        candidate = (self.root / key).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise StorageKeyError("storage key resolves outside the storage root")
        return candidate

    def put(self, key: str, stream: BinaryIO) -> StoredFile:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_name(target.name + ".part")
        digest = hashlib.sha256()
        size = 0
        with tmp.open("wb") as out:
            for chunk in iter(lambda: stream.read(_CHUNK), b""):
                digest.update(chunk)
                size += len(chunk)
                out.write(chunk)
        os.replace(tmp, target)
        return StoredFile(key=key, size=size, sha256=digest.hexdigest())

    def open(self, key: str) -> BinaryIO:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.open("rb")

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def stat(self, key: str) -> StoredFile:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        size, sha = _sha256_of(path)
        return StoredFile(key=key, size=size, sha256=sha)

    def iter_keys(self) -> Iterator[str]:
        for path in self.root.rglob("*"):
            if path.is_file() and not path.name.endswith(".part"):
                yield path.relative_to(self.root).as_posix()


def build_storage(settings: Settings) -> FileStorage:
    if settings.storage_backend == "local":
        return LocalFileStorage(settings.storage_root)
    raise ValueError(f"unknown storage backend {settings.storage_backend!r}")
