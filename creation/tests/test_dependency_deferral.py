import json

from concept_graph_creation.cli import run_pipeline
from concept_graph_creation.stages.dependency_deferral import run_dependency_deferral_phase


def test_dependency_deferral_writes_explicit_empty_dependency_artifact(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "schema_version": "source_ledger.v0",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "computacao",
                "lessons": [{"lesson_id": "lesson-bow", "title": "Bag of Words"}],
                "summary": {"lesson_count": 1},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "subject_merge.json").write_text(
        json.dumps(
            {
                "artifact_type": "subject_merge",
                "schema_version": "subject_merge.v0",
                "concepts": [{"concept_id": "concept_bow", "label": "Bag of Words"}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_dependency_deferral_phase(run_dir=run_dir)

    artifact = json.loads((run_dir / "dependency_inference.json").read_text(encoding="utf-8"))
    assert result["summary"] == {
        "concept_count": 1,
        "dependency_edge_count": 0,
        "deferred": True,
    }
    assert artifact["artifact_type"] == "dependency_inference"
    assert artifact["schema_version"] == "dependency_inference.v0"
    assert artifact["dependency_edges"] == []
    assert artifact["deferred"] is True
    assert "university Lesson order is the trusted prerequisite structure" in artifact["deferral_reason"]


def test_pipeline_runs_phase_6_and_reports_dependency_deferral_summary(tmp_path):
    run_dir = tmp_path / "run"
    _write_phase_6_inputs(run_dir)

    result = run_pipeline(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        clean_run_dir=False,
        phases=["phase-6"],
    )

    assert result["dependency_deferral"]["summary"] == {
        "concept_count": 1,
        "dependency_edge_count": 0,
        "deferred": True,
    }
    assert result["manual_output"]["dependency_deferral_summary"] == {
        "concept_count": 1,
        "dependency_edge_count": 0,
        "deferred": True,
    }


def _write_phase_6_inputs(run_dir):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "schema_version": "source_ledger.v0",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "computacao",
                "lessons": [{"lesson_id": "lesson-bow", "title": "Bag of Words"}],
                "summary": {"lesson_count": 1},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "subject_merge.json").write_text(
        json.dumps(
            {
                "artifact_type": "subject_merge",
                "schema_version": "subject_merge.v0",
                "concepts": [{"concept_id": "concept_bow", "label": "Bag of Words"}],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
