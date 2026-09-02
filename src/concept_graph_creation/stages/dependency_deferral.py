from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from concept_graph_creation.runtime.stage_runner import StageBlockedError


def run_dependency_deferral_phase(*, run_dir: Path) -> dict[str, Any]:
    source_ledger_path = run_dir / "source_ledger.json"
    subject_merge_path = run_dir / "subject_merge.json"
    if not source_ledger_path.is_file():
        raise StageBlockedError("Dependency Deferral requires source_ledger.json")
    if not subject_merge_path.is_file():
        raise StageBlockedError("Dependency Deferral requires subject_merge.json from 06-subject-merge")

    source_ledger = _read_json(source_ledger_path)
    subject_merge = _read_json(subject_merge_path)
    concepts = [concept for concept in subject_merge.get("concepts") or [] if isinstance(concept, dict)]
    artifact = {
        "artifact_type": "dependency_inference",
        "schema_version": "dependency_inference.v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_artifact": "source_ledger.json",
        "subject_merge_artifact": "subject_merge.json",
        "course_id": source_ledger.get("course_id"),
        "module_id": source_ledger.get("module_id"),
        "subject_id": source_ledger.get("subject_id"),
        "deferred": True,
        "deferral_reason": (
            "Dependency inference is deferred for v0 because the university Lesson order is "
            "the trusted prerequisite structure. Workbook prerequisite labels are retained "
            "for audit and future exam-study or adaptive-remediation work, not converted "
            "into v0 dependency edges."
        ),
        "dependency_edges": [],
        "summary": {
            "concept_count": len(concepts),
            "dependency_edge_count": 0,
            "deferred": True,
        },
    }
    output_path = run_dir / "dependency_inference.json"
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"summary": artifact["summary"], "artifact_path": output_path}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))
