"""Content-addressed binary storage outside PostgreSQL.

Postgres owns immutable metadata and lineage; this module owns source bytes.
The same key contract is used by the local filesystem and S3-compatible
Railway buckets, so Markdown and ledger rows do not depend on deployment.
"""

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


class S3AssetStore:
    """S3-compatible content store, including Railway Storage Buckets."""

    def __init__(
        self,
        *,
        bucket: str | None = None,
        endpoint_url: str | None = None,
        region: str | None = None,
        url_style: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        client=None,
    ) -> None:
        self.bucket = bucket or os.environ.get("AWS_S3_BUCKET_NAME", "").strip()
        if not self.bucket:
            raise ValueError("AWS_S3_BUCKET_NAME is required for S3 asset storage")
        self.endpoint_url = endpoint_url or os.environ.get("AWS_ENDPOINT_URL") or None
        self.region = region or os.environ.get("AWS_DEFAULT_REGION") or "auto"
        self.url_style = (url_style or os.environ.get("AWS_S3_URL_STYLE") or "path").lower()
        if self.url_style not in {"path", "virtual", "auto"}:
            raise ValueError("AWS_S3_URL_STYLE must be path, virtual, or auto")
        if client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:  # pragma: no cover - packaging failure
                raise RuntimeError("boto3 is required for S3 asset storage") from exc
            self.client = boto3.client(
                "s3",
                endpoint_url=self.endpoint_url,
                region_name=self.region,
                aws_access_key_id=(
                    access_key_id or os.environ.get("AWS_ACCESS_KEY_ID") or None
                ),
                aws_secret_access_key=(
                    secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY") or None
                ),
                config=Config(s3={"addressing_style": self.url_style}),
            )
        else:
            self.client = client

    def put(self, body: bytes, *, sha256: str | None = None) -> StoredAsset:
        payload = _bytes(body)
        digest = hashlib.sha256(payload).hexdigest()
        if sha256 is not None and sha256 != digest:
            raise ValueError("asset bytes do not match the declared SHA-256")
        key = content_key(digest)
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=payload,
                Metadata={"sha256": digest},
                IfNoneMatch="*",
            )
            created = True
        except Exception as exc:
            if _error_code(exc) not in {"PreconditionFailed", "412", "ConditionalRequestConflict"}:
                raise
            created = False
        return StoredAsset(key, digest, created)

    def get(self, key: str) -> bytes:
        digest = key_digest(key)
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body = response["Body"].read()
        if not isinstance(body, bytes):
            body = bytes(body)
        if hashlib.sha256(body).hexdigest() != digest:
            raise IOError("stored asset failed SHA-256 integrity verification")
        return body

    def delete(self, key: str) -> None:
        key_digest(key)
        self.client.delete_object(Bucket=self.bucket, Key=key)


def asset_store_from_env(*, s3_client=None) -> AssetStore:
    """Select S3 when a bucket is configured; otherwise use local storage."""
    if os.environ.get("AWS_S3_BUCKET_NAME", "").strip():
        return S3AssetStore(client=s3_client)
    return LocalAssetStore()


def _bytes(value: bytes) -> bytes:
    if not isinstance(value, bytes) or not value:
        raise ValueError("asset body must be non-empty bytes")
    return value


def _error_code(exc: Exception) -> str | None:
    response = getattr(exc, "response", None)
    if not isinstance(response, dict):
        return None
    error = response.get("Error")
    code = error.get("Code") if isinstance(error, dict) else None
    return str(code) if code is not None else None
