from pathlib import Path

from concept_graph_creation.stages.source_ledger import build_source_ledger, validate_source_ledger, write_source_ledger


REPO_ROOT = Path(__file__).resolve().parents[3]
CG_PIPELINE_ROOT = REPO_ROOT / "cg_pipeline"


def test_source_ledger_reads_real_cg_pipeline_inputs_and_writes_validated_artifact():
    ledger = build_source_ledger(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        workbook_path=CG_PIPELINE_ROOT / "source" / "si_mod6.xlsx",
        index_path=CG_PIPELINE_ROOT / "index.json",
        subject_sheet="COM",
        course_id="si",
        module_id="mod6",
        subject_id="COM",
    )

    errors = validate_source_ledger(ledger, cg_pipeline_root=CG_PIPELINE_ROOT)
    assert errors == []

    output_path = write_source_ledger(
        ledger,
        Path(__file__).resolve().parents[1] / "tmp" / "pytest" / "source_ledger.json",
    )
    assert output_path.is_file()

    assert ledger["artifact_type"] == "source_ledger"
    assert ledger["course_id"] == "si"
    assert ledger["module_id"] == "mod6"
    assert ledger["subject_id"] == "COM"
    assert len(ledger["lessons"]) > 0
    assert len(ledger["self_studies"]) == 69

    statuses = {item["source_body_status"] for item in ledger["self_studies"]}
    assert "usable_source_body" in statuses
    assert "unavailable_source_body" in statuses

    first = ledger["self_studies"][0]
    assert first["workbook_metadata"]["title"] == "Bash in 100 Seconds"
    assert first["lesson_id"].startswith("lesson-")
    assert first["source_body"]["sha256"]
    assert first["source_body"]["path"].startswith("extraction/")
    assert first["source_body"]["availability_warnings"] == []

    unavailable = [item for item in ledger["self_studies"] if item["source_body_status"] == "unavailable_source_body"]
    assert {item["source_body"]["availability_failures"][0] for item in unavailable} >= {
        "manual_access_required",
        "auth_wall_detected",
    }
    assert all(item["metadata_only_candidate"] is True for item in unavailable)
