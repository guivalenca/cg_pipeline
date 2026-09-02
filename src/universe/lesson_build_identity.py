"""Canonical content identities shared by Lesson Build creation and execution."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


def bytes_sha256(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def path_sha256(path: Path) -> str:
    """Hash one file or an ordered tree of relative paths and file hashes."""
    if path.is_file():
        return bytes_sha256(path.read_bytes())
    members = [
        (member.relative_to(path).as_posix(), bytes_sha256(member.read_bytes()))
        for member in sorted(path.rglob("*"))
        if member.is_file()
    ]
    encoded = json.dumps(
        members, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return bytes_sha256(encoded)


def creation_implementation_sha256(project_root: Path) -> str:
    """Hash the vendored creation implementation as one executable identity."""
    root = project_root / "src/concept_graph_creation"
    members = [
        (path.relative_to(root).as_posix(), bytes_sha256(path.read_bytes()))
        for path in sorted(root.rglob("*.py"))
    ]
    encoded = json.dumps(
        members, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return bytes_sha256(encoded)
