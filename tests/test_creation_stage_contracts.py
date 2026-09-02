import hashlib
import json

import pytest

from concept_graph_creation.runtime.generation import ledger_fingerprint
from concept_graph_creation.runtime.stage_runner import StageBlockedError
from concept_graph_creation.stages.dependency_deferral import (
    run_dependency_deferral_phase,
)
from concept_graph_creation.stages.knowledge_type_classification import (
    run_knowledge_type_classification_phase,
)
from concept_graph_creation.stages.lesson_reconciliation import (
    run_lesson_reconciliation_phase,
    validate_lesson_reconciliation_artifact,
)
from concept_graph_creation.stages.lesson_segmentation import (
    run_lesson_segmentation_phase,
)
from concept_graph_creation.stages.self_study_extraction import (
    run_self_study_extraction_phase,
    validate_self_study_extraction,
)
from concept_graph_creation.stages.source_ledger import (
    read_workbook_source_extracted_at,
    resolve_source_body_path,
)


@pytest.mark.parametrize(
    "validator",
    [
        validate_self_study_extraction,
        validate_lesson_reconciliation_artifact,
    ],
)
def test_extraction_and_reconciliation_contracts_reject_empty_artifacts(validator):
    assert validator({})


def test_self_study_extraction_rejects_malformed_model_response(tmp_path):
    source_path = tmp_path / "source.md"
    source_path.write_text("# Busca\n\nExploração de estados.\n", encoding="utf-8")
    source_ledger = _source_ledger()
    source_ledger["self_studies"] = [
        {
            "self_study_id": "source-1",
            "lesson_id": "lesson-stable",
            "source_body_status": "usable_source_body",
            "workbook_metadata": {"title": "Busca em profundidade"},
            "source_body": {
                "path": str(source_path),
                "sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                "word_count": 3,
            },
        }
    ]
    run_dir = tmp_path / "run"
    _write_json(run_dir / "source_ledger.json", source_ledger)

    with pytest.raises(StageBlockedError, match="JSON parse error"):
        run_self_study_extraction_phase(
            cg_pipeline_root=tmp_path,
            run_dir=run_dir,
            model_call=lambda **_kwargs: "not-json",
            initial_concurrency=1,
            pressure_backoff_seconds=0,
        )


def test_source_body_resolution_rejects_bytes_outside_the_pinned_hash(tmp_path):
    source_path = tmp_path / "source.md"
    source_path.write_text("conteúdo diferente", encoding="utf-8")

    assert resolve_source_body_path(
        source_body={"path": str(source_path), "sha256": "pinned-hash"},
        self_study_id="source-1",
        run_dir=tmp_path / "run",
        cg_pipeline_root=tmp_path,
    ) is None


def test_creation_boundary_rejects_legacy_workbook_provenance(tmp_path):
    with pytest.raises(StageBlockedError, match="fallback is disabled"):
        read_workbook_source_extracted_at(tmp_path / "source.xlsx")


def test_lesson_reconciliation_rejects_malformed_model_response(tmp_path):
    run_dir = tmp_path / "run"
    source_ledger = _source_ledger()
    source_ledger["self_studies"] = [
        {
            "self_study_id": "source-1",
            "lesson_id": "lesson-stable",
            "source_body_status": "usable_source_body",
            "workbook_metadata": {"title": "Busca em profundidade"},
        }
    ]
    _write_json(run_dir / "source_ledger.json", source_ledger)
    artifact_ref = (
        "lessons/lesson-stable/self_studies/source-1/extraction_passes/"
        "pro-thinking/self_study_extraction.json"
    )
    _write_json(
        run_dir / artifact_ref,
        {
            "artifact_type": "self_study_extraction",
            "schema_version": "self_study_extraction.v0",
            "model_route": "Pro Thinking",
            "lesson_id": "lesson-stable",
            "self_study_id": "source-1",
            "source_name": "Busca em profundidade",
            "candidate_concepts": [
                {
                    "candidate_id": "candidate-source-1-001",
                    "label": "Busca em profundidade",
                    "description": "Exploração sistemática de estados.",
                    "coverage_criteria": ["Explicar a ordem da busca."],
                    "source_roles": ["explaining"],
                    "source_anchors": [
                        {"kind": "markdown_heading", "locator": "Busca"}
                    ],
                    "extraction_reason": {
                        "source_grounded_rationale": "A fonte explica a busca.",
                        "granularity_rationale": "É uma ideia verificável.",
                    },
                    "evidence_type": "source_body",
                }
            ],
            "source_local_connector_candidates": [],
            "summary": {
                "candidate_count": 1,
                "source_local_connector_candidate_count": 0,
            },
        },
    )
    _write_json(
        run_dir
        / "lessons/lesson-stable/self_studies/source-1/"
        "self_study_extraction_set.json",
        {
            "artifact_type": "self_study_extraction_set",
            "schema_version": "self_study_extraction_set.v0",
            "lesson_id": "lesson-stable",
            "self_study_id": "source-1",
            "extraction_passes": [
                {
                    "pass_id": "pro-thinking",
                    "route_alias": "Pro Thinking",
                    "artifact_path": artifact_ref,
                    "candidate_count": 1,
                }
            ],
        },
    )

    with pytest.raises(StageBlockedError, match="JSON parse error"):
        run_lesson_reconciliation_phase(
            run_dir=run_dir,
            model_call=lambda **_kwargs: "not-json",
            concurrency=1,
            provider_retry_backoff_seconds=0,
        )


def test_dependency_deferral_contract_requires_both_upstream_artifacts(tmp_path):
    with pytest.raises(StageBlockedError, match="requires source_ledger.json"):
        run_dependency_deferral_phase(run_dir=tmp_path)

    _write_json(tmp_path / "source_ledger.json", _source_ledger())

    with pytest.raises(StageBlockedError, match="requires subject_merge.json"):
        run_dependency_deferral_phase(run_dir=tmp_path)


def test_lesson_segmentation_rejects_malformed_model_response(tmp_path):
    _write_json(tmp_path / "source_ledger.json", _source_ledger())
    _write_json(tmp_path / "subject_merge.json", _subject_merge())

    with pytest.raises(StageBlockedError, match="JSON parse error"):
        run_lesson_segmentation_phase(
            run_dir=tmp_path,
            model_call=lambda **_kwargs: "not-json",
            concurrency=1,
            provider_retry_backoff_seconds=0,
        )


def test_knowledge_type_classification_rejects_malformed_model_response(tmp_path):
    source_ledger = _source_ledger()
    _write_json(tmp_path / "source_ledger.json", source_ledger)
    _write_json(tmp_path / "subject_merge.json", _subject_merge())
    segment_path = "lessons/lesson-stable/lesson_segments.json"
    _write_json(
        tmp_path / segment_path,
        {
            "artifact_type": "lesson_segments",
            "schema_version": "lesson_segments.v0",
            "ledger_fingerprint": ledger_fingerprint(source_ledger),
            "lesson_id": "lesson-stable",
            "status": "reliable",
            "repaired": False,
            "segments": [
                {
                    "segment_id": "segment_001",
                    "label": "Busca em profundidade",
                    "instructional_role": "teach",
                    "concept_ids": ["concept-stable"],
                }
            ],
            "structural_warnings": [],
        },
    )
    _write_json(
        tmp_path / "lesson_segmentation_summary.json",
        {
            "artifact_type": "lesson_segmentation_summary",
            "schema_version": "lesson_segmentation_summary.v0",
            "artifacts": [segment_path],
        },
    )

    with pytest.raises(StageBlockedError, match="JSON parse error"):
        run_knowledge_type_classification_phase(
            run_dir=tmp_path,
            model_call=lambda **_kwargs: "not-json",
            concurrency=1,
            provider_retry_backoff_seconds=0,
        )


def _source_ledger():
    return {
        "artifact_type": "source_ledger",
        "schema_version": "source_ledger.v0",
        "course_id": "cc",
        "module_id": "mod6",
        "subject_id": "COM",
        "lessons": [
            {
                "lesson_id": "lesson-stable",
                "title": "Busca em profundidade",
            }
        ],
        "self_studies": [],
    }


def _subject_merge():
    return {
        "artifact_type": "subject_merge",
        "schema_version": "subject_merge.v0",
        "concepts": [
            {
                "concept_id": "concept-stable",
                "label": "Busca em profundidade",
                "teaching_description": "Exploração sistemática de estados.",
                "coverage_criteria": ["Explicar a ordem da busca."],
                "occurrences": [
                    {
                        "lesson": {
                            "lesson_id": "lesson-stable",
                            "title": "Busca em profundidade",
                        }
                    }
                ],
            }
        ],
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
