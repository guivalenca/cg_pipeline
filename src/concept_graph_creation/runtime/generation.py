from __future__ import annotations

import hashlib
import json
from typing import Any


LEDGER_FINGERPRINT_VERSION_PREFIX = "lfp1-"


def ledger_fingerprint(source_ledger: dict[str, Any]) -> str:
    """Fingerprint of the semantic content of a Source Ledger.

    Only the generation-defining content (Lessons and Self-studies) is hashed.
    Volatile fields such as ``generated_at`` are excluded so rebuilding an
    identical ledger keeps the same fingerprint and legitimate resumes stay cheap.
    """
    semantic_content = {
        "lessons": source_ledger.get("lessons"),
        "self_studies": source_ledger.get("self_studies"),
    }
    canonical = json.dumps(semantic_content, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"{LEDGER_FINGERPRINT_VERSION_PREFIX}{digest}"


def stamp_ledger_fingerprint(artifact: dict[str, Any], fingerprint: str) -> dict[str, Any]:
    artifact["ledger_fingerprint"] = fingerprint
    return artifact


def matches_ledger_fingerprint(artifact: dict[str, Any], fingerprint: str) -> bool:
    """True iff the artifact was produced for the given ledger generation.

    Artifacts without a ``ledger_fingerprint`` (legacy or foreign) never match,
    so they are treated as stale and regenerated.
    """
    if not isinstance(artifact, dict):
        return False
    return artifact.get("ledger_fingerprint") == fingerprint
