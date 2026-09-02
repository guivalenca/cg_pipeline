import hashlib
import json
from pathlib import Path

from concept_graph_creation.lesson_ledger import build_lesson_ledger
from concept_graph_creation.runtime.fixture_model import FixtureModelClient
from concept_graph_creation.stages.dependency_deferral import (
    run_dependency_deferral_phase,
)
from concept_graph_creation.stages.lesson_reconciliation import (
    run_lesson_reconciliation_phase,
)
from concept_graph_creation.stages.lesson_reconciliation_passthrough import (
    run_lesson_reconciliation_passthrough_phase,
)
from concept_graph_creation.stages.lesson_segmentation import (
    run_lesson_segmentation_phase,
)
from concept_graph_creation.stages.knowledge_type_classification import (
    run_knowledge_type_classification_phase,
)
from concept_graph_creation.stages.final_graph_assembly import (
    run_final_graph_assembly_phase,
)
from concept_graph_creation.stages.self_study_extraction import (
    run_self_study_extraction_phase,
)


FIXTURE_ROOT = (
    Path(__file__).parent
    / "fixtures"
    / "archived_cc_mod6_com"
    / "backtracking"
)
LESSON_ID = "lesson-2026-06-02-backtracking"
LOCALIZABLE_PROSE_KEYS = {
    "coverage_criteria",
    "description",
    "explanation",
    "granularity_rationale",
    "label",
    "merge_rationale",
    "rationale",
    "source_grounded_rationale",
}


def test_archived_source_bodies_lift_reconciliation_and_segmentation(tmp_path):
    subject_ledger = _read_json(FIXTURE_ROOT / "subject_ledger.json")
    for self_study in subject_ledger["self_studies"]:
        if (
            self_study.get("lesson_id") != LESSON_ID
            or self_study.get("source_body_status") != "usable_source_body"
        ):
            continue
        self_study_id = str(self_study["self_study_id"])
        source_body_path = FIXTURE_ROOT / "source_bodies" / f"{self_study_id}.md"
        assert hashlib.sha256(source_body_path.read_bytes()).hexdigest() == (
            self_study["source_body"]["sha256"]
        )
        self_study["source_body"]["path"] = str(source_body_path)
    source_ledger = build_lesson_ledger(subject_ledger, LESSON_ID)
    source_ledger.setdefault("inputs", {})["lesson_build_id"] = (
        "archived-backtracking-fixture-build"
    )
    run_dir = tmp_path / "creation-run"
    _write_json(run_dir / "source_ledger.json", source_ledger)
    fixture_model = FixtureModelClient.from_file(FIXTURE_ROOT / "fixture-model.json")

    extraction = run_self_study_extraction_phase(
        cg_pipeline_root=FIXTURE_ROOT,
        run_dir=run_dir,
        model_call=fixture_model,
        initial_concurrency=4,
        pressure_backoff_seconds=0,
    )
    assert extraction["summary"]["extracted_self_study_count"] == 4

    reconciliation = run_lesson_reconciliation_phase(
        run_dir=run_dir,
        model_call=fixture_model,
        concurrency=2,
        provider_retry_backoff_seconds=0,
    )
    assert reconciliation["summary"]["reconciled_lesson_count"] == 1
    actual_reconciliation = _read_json(
        run_dir / "lessons" / LESSON_ID / "lesson_reconciliation.json"
    )
    archived_reconciliation = _read_json(
        FIXTURE_ROOT / "expected" / "lesson_reconciliation.json"
    )
    assert _reconciliation_contract(actual_reconciliation) == _reconciliation_contract(
        archived_reconciliation
    )

    run_lesson_reconciliation_passthrough_phase(run_dir=run_dir)
    run_dependency_deferral_phase(run_dir=run_dir)
    segmentation = run_lesson_segmentation_phase(
        run_dir=run_dir,
        model_call=fixture_model,
        concurrency=1,
        provider_retry_backoff_seconds=0,
    )
    assert segmentation["summary"]["segmented_lesson_count"] == 1
    actual_segments = _read_json(
        run_dir / "lessons" / LESSON_ID / "lesson_segments.json"
    )
    archived_segments = _read_json(FIXTURE_ROOT / "expected" / "lesson_segments.json")
    replacements = _read_json(FIXTURE_ROOT / "fixture-model.json")[
        "response_replacements"
    ]
    expected_segments = _replace_ids(archived_segments, replacements)
    assert _segmentation_contract(actual_segments) == _segmentation_contract(
        expected_segments
    )
    fixture_model.assert_exhausted()

    knowledge_fixture_path = tmp_path / "knowledge-fixture-model.json"
    knowledge_fixture_path.write_text(
        json.dumps(
            {
                "schema_version": "creation_fixture_model.v1",
                "responses": [
                    *[
                        {
                            "stage_name": "knowledge_type_classification",
                            "input_subset": {
                                "knowledge_type_classification_input.json": {
                                    "segment": {"segment_id": segment["segment_id"]}
                                }
                            },
                            "response": {
                                "classifications": [
                                    {
                                        "concept_id": concept_id,
                                        "knowledge_type": "conceptual",
                                        "rationale": "A compreensão conceitual organiza este trecho.",
                                        "confidence": 0.9,
                                    }
                                    for concept_id in segment["concept_ids"]
                                ]
                            },
                        }
                        for segment in actual_segments["segments"]
                    ],
                    {
                        "stage_name": "knowledge_type_quality_audit",
                        "input_subset": {},
                        "response": {
                            "scores": {
                                "taxonomy_fit": 3,
                                "teaching_mode_alignment": 3,
                                "segment_consistency": 3,
                                "factual_boundary": 3,
                                "applied_boundary": 3,
                            },
                            "reliability": "reliable",
                            "flags": [],
                            "findings": [],
                            "repair_plan": [],
                        },
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    knowledge_fixture = FixtureModelClient.from_file(knowledge_fixture_path)
    knowledge = run_knowledge_type_classification_phase(
        run_dir=run_dir,
        model_call=knowledge_fixture,
        concurrency=5,
        provider_retry_backoff_seconds=0,
    )
    assert knowledge["status"] == "reliable"
    knowledge_fixture.assert_exhausted()

    final = run_final_graph_assembly_phase(run_dir=run_dir)
    runtime_graph = _read_json(final["artifact_path"])
    assert final["summary"] == {
        "concept_count": 10,
        "lesson_count": 1,
        "segmented_lesson_count": 1,
        "runtime_lesson_count": 1,
        "dependency_edge_count": 0,
        "blocking_error_count": 0,
        "warning_count": 0,
    }
    assert len(runtime_graph["concepts"]) == 10


def _reconciliation_contract(artifact):
    contract = {
        key: artifact.get(key)
        for key in (
            "artifact_type",
            "schema_version",
            "lesson_id",
            "reconciled_candidates",
            "pruned_candidates",
            "review_candidates",
            "candidate_assignments",
            "summary",
        )
    }
    # Coverage diagnostics post-date the archived run, while prose is expected
    # to move from English to pt-BR. IDs, assignments, evidence, and counts stay
    # comparison-bearing.
    return _without_keys(
        contract,
        LOCALIZABLE_PROSE_KEYS | {"coverage_diagnostics"},
    )


def _segmentation_contract(artifact):
    contract = {
        key: artifact.get(key)
        for key in (
            "artifact_type",
            "schema_version",
            "lesson_id",
            "status",
            "repaired",
            "segments",
            "structural_warnings",
            "summary",
        )
    }
    return _without_keys(contract, LOCALIZABLE_PROSE_KEYS)


def _replace_ids(value, replacements):
    serialized = json.dumps(value, ensure_ascii=False)
    for old, new in sorted(replacements.items(), key=lambda item: len(item[0]), reverse=True):
        serialized = serialized.replace(old, new)
    return json.loads(serialized)


def _without_keys(value, keys_to_remove):
    if isinstance(value, dict):
        return {
            key: _without_keys(item, keys_to_remove)
            for key, item in value.items()
            if key not in keys_to_remove
        }
    if isinstance(value, list):
        return [_without_keys(item, keys_to_remove) for item in value]
    return value


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
