"""Local content-addressed binary storage outside PostgreSQL."""

from __future__ import annotations

import hashlib
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


ASSET_KEY_RE = re.compile(r"^sha256/([0-9a-f]{2})/([0-9a-f]{64})$")
DEFAULT_LOCAL_ROOT = Path(__file__).resolve().parents[2] / ".data" / "source-assets"


@dataclass(frozen=True)
class StoredAsset:
    key: str
    sha256: str
    created: bool


class AssetStore(Protocol):
    def put(self, body: bytes, *, sha256: str | None = None) -> StoredAsset: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


def content_key(digest: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("asset SHA-256 must be 64 lowercase hexadecimal characters")
    return f"sha256/{digest[:2]}/{digest}"


def key_digest(key: str) -> str:
    match = ASSET_KEY_RE.fullmatch(str(key or ""))
    if match is None or match.group(1) != match.group(2)[:2]:
        raise ValueError("invalid content-addressed asset key")
    return match.group(2)


class LocalAssetStore:
    """Application-managed filesystem store for local development."""

    def __init__(self, root: str | Path | None = None) -> None:
        configured = root or os.environ.get("CONCEPT_UNIVERSE_ASSET_ROOT") or DEFAULT_LOCAL_ROOT
        self.root = Path(configured).expanduser().resolve()

    def put(self, body: bytes, *, sha256: str | None = None) -> StoredAsset:
        payload = _bytes(body)
        digest = hashlib.sha256(payload).hexdigest()
        if sha256 is not None and sha256 != digest:
            raise ValueError("asset bytes do not match the declared SHA-256")
        key = content_key(digest)
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            self._verify(target.read_bytes(), digest)
            return StoredAsset(key, digest, False)

        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{digest}.", dir=target.parent
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.link(temporary, target)
                created = True
            except FileExistsError:
                self._verify(target.read_bytes(), digest)
                created = False
        finally:
            temporary.unlink(missing_ok=True)
        return StoredAsset(key, digest, created)

    def get(self, key: str) -> bytes:
        digest = key_digest(key)
        body = self._path(key).read_bytes()
        self._verify(body, digest)
        return body

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def _path(self, key: str) -> Path:
        key_digest(key)
        return self.root.joinpath(*key.split("/"))

    @staticmethod
    def _verify(body: bytes, digest: str) -> None:
        if hashlib.sha256(body).hexdigest() != digest:
            raise IOError("stored asset failed SHA-256 integrity verification")


def asset_store_from_env() -> AssetStore:
    """Return the pilot's single application-managed Asset Store."""
    return LocalAssetStore()


def _bytes(value: bytes) -> bytes:
    if not isinstance(value, bytes) or not value:
        raise ValueError("asset body must be non-empty bytes")
    return value
