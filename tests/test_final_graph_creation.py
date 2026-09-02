import json

import pytest

from concept_graph_creation.runtime.generation import ledger_fingerprint
from concept_graph_creation.runtime.stage_runner import StageBlockedError
from concept_graph_creation.stages.dependency_deferral import (
    run_dependency_deferral_phase,
)
from concept_graph_creation.stages.final_graph_assembly import (
    assemble_runtime_graph_from_build_graph,
    run_final_graph_assembly_phase,
)
from concept_graph_creation.stages.lesson_reconciliation_passthrough import (
    build_lesson_reconciliation_passthrough,
)


@pytest.mark.parametrize(
    ("knowledge_type", "message"),
    [
        (None, "missing knowledge_type"),
        ("synthetic", "unsupported knowledge_type 'synthetic'"),
    ],
)
def test_final_assembly_stops_on_missing_or_unsupported_knowledge_type(
    tmp_path,
    knowledge_type,
    message,
):
    run_dir = tmp_path / "run"
    lesson_id = "stable-lesson-id"
    source_ledger = {
        "artifact_type": "source_ledger",
        "schema_version": "source_ledger.v0",
        "source_extracted_at": "2026-09-02T12:00:00+00:00",
        "course_id": "cc",
        "module_id": "mod6",
        "subject_id": "COM",
        "summary": {
            "lesson_count": 1,
            "self_study_count": 0,
            "available_count": 0,
            "unavailable_count": 0,
        },
        "lessons": [
            {
                "lesson_id": lesson_id,
                "display_code": "L01",
                "title": "Busca em profundidade",
                "description": "Exploração de estados.",
                "date": "02/09/2026",
                "axis": "COM",
            }
        ],
        "self_studies": [],
    }
    reconciliation = {
        "artifact_type": "lesson_reconciliation",
        "schema_version": "lesson_reconciliation.v0",
        "lesson_id": lesson_id,
        "reconciled_candidates": [
            {
                "reconciled_candidate_id": f"reconciled-candidate-{lesson_id}-001",
                "label": "Busca em profundidade",
                "description": "Exploração sistemática de estados.",
                "coverage_criteria": ["Explicar a ordem da busca."],
                "source_candidate_ids": [],
                "source_roles": [],
                "evidence_types": [],
                "evidence": [],
            }
        ],
    }
    subject_merge = build_lesson_reconciliation_passthrough(
        source_ledger=source_ledger,
        lesson_reconciliation=reconciliation,
    )
    concept_id = subject_merge["concepts"][0]["concept_id"]
    fingerprint = ledger_fingerprint(source_ledger)
    _write_json(run_dir / "source_ledger.json", source_ledger)
    _write_json(run_dir / "subject_merge.json", subject_merge)
    run_dependency_deferral_phase(run_dir=run_dir)
    lesson_segments = {
        "artifact_type": "lesson_segments",
        "schema_version": "lesson_segments.v0",
        "ledger_fingerprint": fingerprint,
        "lesson_id": lesson_id,
        "status": "reliable",
        "repaired": False,
        "segments": [
            {
                "segment_id": "segment_001",
                "label": "Busca em profundidade",
                "instructional_role": "teach",
                "concept_ids": [concept_id],
            }
        ],
        "structural_warnings": [],
    }
    segment_path = f"lessons/{lesson_id}/lesson_segments.json"
    _write_json(run_dir / segment_path, lesson_segments)
    _write_json(
        run_dir / "lesson_segmentation_summary.json",
        {
            "artifact_type": "lesson_segmentation_summary",
            "schema_version": "lesson_segmentation_summary.v0",
            "summary": {
                "lesson_count": 1,
                "segmented_lesson_count": 1,
                "segment_count": 1,
                "repair_count": 0,
                "unrepaired_count": 0,
                "skipped_no_concept_lesson_count": 0,
            },
            "artifacts": [segment_path],
            "lessons": [
                {
                    "lesson_id": lesson_id,
                    "artifact_path": segment_path,
                    "status": "reliable",
                    "repaired": False,
                    "segment_count": 1,
                }
            ],
        },
    )
    _write_json(
        run_dir / "knowledge_type_classification_summary.json",
        {
            "artifact_type": "knowledge_type_classification_summary",
            "schema_version": "knowledge_type_classification_summary.v0",
            "ledger_fingerprint": fingerprint,
            "status": "reliable",
            "summary": {"unrepaired_count": 0},
            "classifications": [
                {
                    "concept_id": concept_id,
                    "knowledge_type": knowledge_type,
                    "rationale": "Classificação de teste.",
                }
            ],
        },
    )

    with pytest.raises(StageBlockedError, match=message):
        run_final_graph_assembly_phase(run_dir=run_dir)


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def test_replacement_build_mints_new_runtime_lesson_segment_ids():
    def build_graph(build_id):
        return {
            "subject": {"pipeline_subject_id": "COM", "title": "Computação"},
            "source_inventory": {"inputs": {"lesson_build_id": build_id}},
            "concepts": [
                {
                    "concept_id": "concept-stable-for-this-projection",
                    "label": "Busca em profundidade",
                    "knowledge_type": "conceptual",
                    "description": "Exploração sistemática de estados.",
                    "coverage_criteria": ["Explicar a ordem da busca."],
                    "common_misconceptions": [],
                    "dependencies": {"blocking": [], "hard": [], "soft": []},
                    "provenance": {},
                }
            ],
            "lessons": [
                {
                    "lesson_id": "stable-lesson-id",
                    "display_code": "L01",
                    "title": "Busca em profundidade",
                    "description": "",
                    "segments": [
                        {
                            "segment_id": "segment_001",
                            "display_code": "L01-S01",
                            "label": "Fundamentos",
                            "instructional_role": "teach",
                            "concept_ids": ["concept-stable-for-this-projection"],
                        }
                    ],
                }
            ],
        }

    first = assemble_runtime_graph_from_build_graph(
        build_graph("lesson-build-first"), generated_at="2026-09-02T12:00:00+00:00"
    )
    repeated = assemble_runtime_graph_from_build_graph(
        build_graph("lesson-build-first"), generated_at="2026-09-02T12:00:00+00:00"
    )
    replacement = assemble_runtime_graph_from_build_graph(
        build_graph("lesson-build-replacement"),
        generated_at="2026-09-02T12:00:00+00:00",
    )

    first_segment_id = first["lessons"][0]["segments"][0]["segment_id"]
    first_concept_id = first["concepts"][0]["concept_id"]
    assert repeated["lessons"][0]["segments"][0]["segment_id"] == first_segment_id
    assert repeated["concepts"][0]["concept_id"] == first_concept_id
    assert replacement["lessons"][0]["lesson_id"] == first["lessons"][0]["lesson_id"]
    assert replacement["lessons"][0]["segments"][0]["segment_id"] != first_segment_id
    assert replacement["concepts"][0]["concept_id"] != first_concept_id
    assert replacement["lessons"][0]["segments"][0]["concept_ids"] == [
        replacement["concepts"][0]["concept_id"]
    ]

    without_provenance = build_graph("ignored")
    del without_provenance["source_inventory"]["inputs"]["lesson_build_id"]
    with pytest.raises(ValueError, match="lesson_build_id"):
        assemble_runtime_graph_from_build_graph(without_provenance)
