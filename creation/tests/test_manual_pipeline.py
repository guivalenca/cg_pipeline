import json
from pathlib import Path

from concept_graph_creation.cli import run_pipeline


REPO_ROOT = Path(__file__).resolve().parents[3]
CG_PIPELINE_ROOT = REPO_ROOT / "cg_pipeline"


def test_run_pipeline_writes_named_run_and_validation_failure_report(tmp_path):
    run_dir = tmp_path / "manual_pipeline"
    stale_path = run_dir / "stale_previous_run.json"
    stale_path.parent.mkdir(parents=True)
    stale_path.write_text("stale\n", encoding="utf-8")
    calls = []

    def workbook_label_model_call(*, route, stage_name, inputs, repair_context=None):
        model_input = inputs["workbook_label_interpretation_input.json"]
        calls.append(
            {
                "route": route.alias,
                "stage_name": stage_name,
                "label_count": len(model_input["labels_to_classify"]),
                "has_prompt": bool(model_input["prompt"]),
                "repair_context": repair_context,
            }
        )

        return json.dumps(
            {
                "classifications": [
                    {
                        "label": item["label"],
                        "pattern": "prerequisite_hint" if item["label"] == "Programação lógica" else "ignored_ambiguous",
                        "confidence": "fake_model",
                        "rationale": "Fake model classified this workbook label.",
                    }
                    for item in model_input["labels_to_classify"]
                ],
                "model_route": route.alias,
            },
            ensure_ascii=False,
        )

    result = run_pipeline(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=True,
        workbook_label_model_call=workbook_label_model_call,
    )

    assert result["ok"] is True
    assert not stale_path.exists()
    assert (run_dir / "source_ledger.json").is_file()
    assert (run_dir / "workbook_label_interpretation.json").is_file()
    assert (run_dir / "run_summary.json").is_file()
    assert (run_dir / "lessons").is_dir()
    assert (run_dir / "critics").is_dir()
    assert (run_dir / "repairs").is_dir()
    assert (run_dir / "validation_failure_demo.txt").read_text(encoding="utf-8").startswith(
        "Stage 'validation_failure_demo' failed Stage Contract:"
    )
    assert result["source_ledger"]["summary"]["self_study_count"] == 69
    assert result["workbook_label_interpretation"]["summary"]["unique_label_count"] > 40
    assert result["workbook_label_interpretation"]["active_outputs"]["prerequisite_hints"] == ["Programação lógica"]
    assert (run_dir / "raw_model_outputs" / "workbook_label_interpretation" / "attempt_1.txt").is_file()
    assert calls == [
        {
            "route": "Pro",
            "stage_name": "workbook_label_interpretation",
            "label_count": result["workbook_label_interpretation"]["summary"]["unique_label_count"],
            "has_prompt": True,
            "repair_context": None,
        }
    ]


def test_run_pipeline_can_run_phase_three_from_existing_phase_two_artifacts(tmp_path):
    run_dir = tmp_path / "manual_pipeline"

    def workbook_label_model_call(*, route, stage_name, inputs, repair_context=None):
        model_input = inputs["workbook_label_interpretation_input.json"]
        return json.dumps(
            {
                "classifications": [
                    {
                        "label": item["label"],
                        "pattern": "ignored_ambiguous",
                        "confidence": "fake_model",
                        "rationale": "Fake model ignored this label.",
                    }
                    for item in model_input["labels_to_classify"]
                ],
                "model_route": route.alias,
            },
            ensure_ascii=False,
        )

    phase_two = run_pipeline(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        workbook_label_model_call=workbook_label_model_call,
        phases=["phase-2"],
    )
    calls = []

    def self_study_model_call(*, route, stage_name, inputs, repair_context=None):
        model_input = inputs["self_study_extraction_input.json"]
        self_study_id = str(model_input["self_study"]["self_study_id"])
        calls.append(
            {
                "route": route.alias,
                "stage_name": stage_name,
                "self_study_id": self_study_id,
                "repair_context": repair_context,
            }
        )
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": f"candidate-{self_study_id}-001",
                        "label": model_input["self_study"]["workbook_metadata"]["title"],
                        "description": "Fake source-local candidate for phase activation testing.",
                        "coverage_criteria": ["Student can explain the source-local teaching signal."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "Fake model used the assigned source body only.",
                            "granularity_rationale": "The candidate is scoped to one checkable idea.",
                        },
                        "source_anchors": [{"kind": "source_body", "locator": "assigned markdown"}],
                        "evidence_type": "source_body",
                        "source_name": model_input["self_study"]["workbook_metadata"]["title"],
                        "source_year": None,
                        "name_drops": [],
                    }
                ],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    phase_three = run_pipeline(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        phases=["phase-3"],
        clean_run_dir=False,
        phase_three_concurrency=6,
        self_study_model_call=self_study_model_call,
    )

    assert len(calls) == phase_two["source_ledger"]["summary"]["available_count"]
    assert {call["route"] for call in calls} == {"Pro Thinking"}
    assert phase_three["manual_output"]["phase_three_summary"] == {
        "usable_self_study_count": phase_two["source_ledger"]["summary"]["available_count"],
        "extracted_self_study_count": phase_two["source_ledger"]["summary"]["available_count"],
        "extraction_pass_count": phase_two["source_ledger"]["summary"]["available_count"],
        "reused_extraction_pass_count": 0,
        "skipped_count": phase_two["source_ledger"]["summary"]["unavailable_count"]
        + phase_two["source_ledger"]["summary"]["excluded_count"],
    }
    assert phase_three["manual_output"]["phase_three_concurrency"]["initial"] == 6
    assert phase_three["manual_output"]["phase_three_concurrency"]["final"] == 6
    assert phase_three["self_study_extraction"]["artifact_paths"]


def test_run_pipeline_can_run_metadata_only_phase_three_b_from_existing_phase_two_artifacts(tmp_path):
    run_dir = tmp_path / "manual_pipeline"
    phase_two = run_pipeline(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        deterministic_fixture=True,
        phases=["phase-2"],
    )
    calls = []

    def metadata_only_model_call(*, route, stage_name, inputs, repair_context=None):
        model_input = inputs["metadata_only_extraction_input.json"]
        self_study_id = str(model_input["self_study"]["self_study_id"])
        calls.append(
            {
                "route": route.alias,
                "stage_name": stage_name,
                "self_study_id": self_study_id,
                "has_source_body": "source_body" in model_input,
                "repair_context": repair_context,
            }
        )
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": f"metadata-candidate-{self_study_id}-001",
                        "label": model_input["self_study"]["workbook_metadata"]["title"],
                        "description": "Fake metadata-only candidate for phase activation testing.",
                        "coverage_criteria": ["Student can explain the metadata-backed teaching signal."],
                        "evidence_type": "workbook_metadata",
                        "metadata_anchors": [{"kind": "workbook_title", "locator": "Title"}],
                        "extraction_reason": {
                            "metadata_grounded_rationale": "Fake model used workbook metadata only.",
                            "granularity_rationale": "The candidate is scoped to one checkable idea.",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        )

    phase_three_b = run_pipeline(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        phases=["phase-3b"],
        clean_run_dir=False,
        metadata_only_model_call=metadata_only_model_call,
    )

    assert phase_three_b["manual_output"]["metadata_only_extraction_summary"] == {
        "metadata_only_candidate_count": phase_two["source_ledger"]["summary"]["unavailable_count"],
        "extracted_self_study_count": phase_two["source_ledger"]["summary"]["unavailable_count"],
        "reused_extraction_count": 0,
        "skipped_count": 0,
    }
    assert phase_three_b["manual_output"]["metadata_only_extraction_concurrency"] == {"initial": 10, "final": 10}
    assert len(calls) == phase_two["source_ledger"]["summary"]["unavailable_count"]
    assert {call["route"] for call in calls} == {"Pro"}
    assert {call["stage_name"] for call in calls} == {"metadata_only_extraction"}
    assert all(call["has_source_body"] is False for call in calls)


def test_run_pipeline_all_reaches_lesson_reconciliation_and_subject_merge_with_fixture(tmp_path):
    run_dir = tmp_path / "manual_pipeline_all"

    result = run_pipeline(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        deterministic_fixture=True,
        phases=["all"],
        phase_three_concurrency=12,
        phase_four_concurrency=3,
    )

    assert result["manual_output"]["lesson_reconciliation_summary"]["reconciled_lesson_count"] > 0
    assert result["manual_output"]["lesson_reconciliation_concurrency"] == {"initial": 3, "final": 3}
    assert result["manual_output"]["subject_merge_summary"]["concept_count"] > 0
    assert (run_dir / "lesson_reconciliation_summary.json").is_file()
    assert (run_dir / "subject_merge.json").is_file()
