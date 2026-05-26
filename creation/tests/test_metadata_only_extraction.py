import json
import threading
import time

import pytest

from concept_graph_creation.runtime.stage_runner import StageBlockedError
from concept_graph_creation.stages.metadata_only_extraction import run_metadata_only_extraction_phase


def test_metadata_only_extraction_writes_workbook_metadata_artifact_for_unavailable_self_study(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [
                    {
                        "lesson_id": "lesson-2026-05-22-word2vec",
                        "display_code": "L10",
                        "title": "Word2Vec: aplicação utilizando redes neurais",
                        "description": "Representação vetorial de palavras com redes neurais.",
                    }
                ],
                "self_studies": [
                    {
                        "self_study_id": "64",
                        "lesson_id": "lesson-2026-05-22-word2vec",
                        "source_body_status": "unavailable_source_body",
                        "workbook_metadata": {
                            "title": "Processando a Linguagem",
                            "description": "Processando a Linguagem no contexto de análise de sentimentos.",
                            "related_labels": ["Análise de sentimentos"],
                            "url": "https://example.test/blocked",
                            "required": True,
                        },
                        "source_body": {"availability_failures": ["manual_access_required"]},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        model_input = inputs["metadata_only_extraction_input.json"]
        calls.append(
            {
                "route": route.alias,
                "stage_name": stage_name,
                "self_study_id": model_input["self_study"]["self_study_id"],
                "has_source_body": "source_body" in model_input,
                "repair_context": repair_context,
            }
        )
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": "metadata-candidate-64-001",
                        "label": "Language processing for sentiment analysis",
                        "description": "The workbook metadata points to language processing in a sentiment-analysis context.",
                        "coverage_criteria": [
                            "Student can explain why language processing matters for sentiment analysis."
                        ],
                        "evidence_type": "workbook_metadata",
                        "metadata_anchors": [{"kind": "workbook_description", "locator": "Description"}],
                        "extraction_reason": {
                            "metadata_grounded_rationale": "The title and description explicitly mention language processing and sentiment analysis.",
                            "granularity_rationale": "This is one checkable lesson-intent idea.",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        )

    result = run_metadata_only_extraction_phase(run_dir=run_dir, model_call=model_call)

    artifact_path = (
        run_dir
        / "lessons"
        / "lesson-2026-05-22-word2vec"
        / "self_studies"
        / "64"
        / "metadata_only_extraction.json"
    )
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert calls == [
        {
            "route": "Pro",
            "stage_name": "metadata_only_extraction",
            "self_study_id": "64",
            "has_source_body": False,
            "repair_context": None,
        }
    ]
    assert result["summary"] == {
        "metadata_only_candidate_count": 1,
        "extracted_self_study_count": 1,
        "reused_extraction_count": 0,
        "skipped_count": 0,
    }
    assert artifact["artifact_type"] == "metadata_only_extraction"
    assert artifact["model_route"] == "Pro"
    assert artifact["candidate_concepts"][0]["evidence_type"] == "workbook_metadata"


def test_metadata_only_extraction_rejects_final_concepts_and_dependency_edges(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": [
                    {
                        "self_study_id": "64",
                        "lesson_id": "lesson-1",
                        "source_body_status": "unavailable_source_body",
                        "workbook_metadata": {"title": "Blocked source", "description": "Metadata only."},
                        "source_body": {"availability_failures": ["manual_access_required"]},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def model_call(**_kwargs):
        return json.dumps(
            {
                "dependency_edges": [{"from": "final-a", "to": "final-b"}],
                "candidate_concepts": [
                    {
                        "candidate_id": "metadata-candidate-64-001",
                        "concept_id": "final-a",
                        "label": "Blocked source",
                        "description": "A forbidden final concept.",
                        "coverage_criteria": ["Student can explain it."],
                        "evidence_type": "workbook_metadata",
                        "metadata_anchors": [{"kind": "workbook_title", "locator": "Title"}],
                        "extraction_reason": {
                            "metadata_grounded_rationale": "The title names it.",
                            "granularity_rationale": "One checkable idea.",
                        },
                    }
                ],
            },
            ensure_ascii=False,
        )

    with pytest.raises(StageBlockedError, match="concept_id is forbidden|dependency_edges is forbidden"):
        run_metadata_only_extraction_phase(run_dir=run_dir, model_call=model_call)


def test_metadata_only_extraction_runs_with_ten_worker_queue(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    self_studies = []
    for index in range(1, 12):
        self_study_id = str(index)
        self_studies.append(
            {
                "self_study_id": self_study_id,
                "lesson_id": "lesson-1",
                "source_body_status": "unavailable_source_body",
                "workbook_metadata": {"title": f"Blocked source {self_study_id}", "description": "Metadata only."},
                "source_body": {"availability_failures": ["manual_access_required"]},
            }
        )
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": self_studies,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    lock = threading.Lock()
    active = 0
    max_active = 0

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal active, max_active
        model_input = inputs["metadata_only_extraction_input.json"]
        self_study_id = str(model_input["self_study"]["self_study_id"])
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": f"metadata-candidate-{self_study_id}-001",
                        "label": f"Blocked source {self_study_id}",
                        "description": "A metadata-only candidate.",
                        "coverage_criteria": ["Student can explain the metadata-backed idea."],
                        "evidence_type": "workbook_metadata",
                        "metadata_anchors": [{"kind": "workbook_title", "locator": "Title"}],
                        "extraction_reason": {
                            "metadata_grounded_rationale": "The workbook title names this idea.",
                            "granularity_rationale": "The idea is checkable.",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        )

    result = run_metadata_only_extraction_phase(run_dir=run_dir, model_call=model_call)

    assert max_active == 10
    assert result["summary"]["extracted_self_study_count"] == 11
    assert result["concurrency"] == {"initial": 10, "final": 10}


def test_metadata_only_extraction_reuses_valid_completed_artifacts_on_rerun(tmp_path):
    run_dir = tmp_path / "run"
    artifact_dir = run_dir / "lessons" / "lesson-1" / "self_studies" / "64"
    artifact_dir.mkdir(parents=True)
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "lessons": [{"lesson_id": "lesson-1", "title": "Intro"}],
                "self_studies": [
                    {
                        "self_study_id": "64",
                        "lesson_id": "lesson-1",
                        "source_body_status": "unavailable_source_body",
                        "workbook_metadata": {"title": "Blocked source", "description": "Metadata only."},
                        "source_body": {"availability_failures": ["manual_access_required"]},
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (artifact_dir / "metadata_only_extraction.json").write_text(
        json.dumps(
            {
                "artifact_type": "metadata_only_extraction",
                "schema_version": "metadata_only_extraction.v0",
                "model_route": "Pro",
                "lesson_id": "lesson-1",
                "self_study_id": "64",
                "candidate_concepts": [
                    {
                        "candidate_id": "metadata-candidate-64-001",
                        "label": "Blocked source",
                        "description": "A cached metadata-only candidate.",
                        "coverage_criteria": ["Student can explain the metadata-backed idea."],
                        "evidence_type": "workbook_metadata",
                        "metadata_anchors": [{"kind": "workbook_title", "locator": "Title"}],
                        "extraction_reason": {
                            "metadata_grounded_rationale": "The workbook title names this idea.",
                            "granularity_rationale": "The idea is checkable.",
                        },
                    }
                ],
                "summary": {"candidate_count": 1},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def model_call(**_kwargs):
        raise AssertionError("valid metadata-only artifact should have been reused")

    result = run_metadata_only_extraction_phase(run_dir=run_dir, model_call=model_call)

    assert result["summary"]["reused_extraction_count"] == 1
    assert result["summary"]["extracted_self_study_count"] == 1
