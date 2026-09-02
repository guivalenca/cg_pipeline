"""Source Ledger compatibility helpers used by the retained creation stages.

The pilot's Source Publication boundary supplies the per-Lesson ledger. The
donor's workbook-to-ledger creation stage is intentionally not vendored.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from concept_graph_creation.runtime.stage_runner import StageBlockedError


def resolve_source_body_path(
    *,
    source_body: dict[str, Any],
    self_study_id: str,
    run_dir: Path | None,
    cg_pipeline_root: Path,
) -> Path | None:
    """Resolve current and legacy Source Body locators by verified content hash."""

    raw_path = str(source_body.get("path") or "").strip()
    expected_sha = str(source_body.get("sha256") or "").strip()
    if not expected_sha:
        return None
    candidates: list[Path] = []
    if raw_path:
        locator = Path(raw_path)
        if locator.is_absolute():
            candidates.append(locator)
        else:
            if run_dir is not None:
                candidates.append(run_dir / locator)
            candidates.append(cg_pipeline_root / locator)
    if run_dir is not None:
        # A relocated legacy ledger points at a deleted absolute workspace. The
        # deterministic run-local fallback is accepted only when bytes match the
        # immutable hash recorded by that checkpoint.
        candidates.append(run_dir / "source_bodies" / f"{self_study_id}.md")

    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if not resolved.is_file():
            continue
        if _sha256_file(resolved) != expected_sha:
            continue
        return resolved
    return None


def read_workbook_source_extracted_at(_workbook_path: Path) -> str:
    """Reject the donor's legacy pre-publication provenance fallback."""

    raise StageBlockedError(
        "Workbook provenance fallback is disabled at the Source Publication boundary"
    )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
