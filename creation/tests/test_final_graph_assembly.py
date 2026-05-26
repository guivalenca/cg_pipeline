import json

import pytest

from concept_graph_creation.cli import run_pipeline
from concept_graph_creation.runtime.stage_runner import StageBlockedError
from concept_graph_creation.stages.final_graph_assembly import run_final_graph_assembly_phase


def test_final_graph_assembly_writes_run_local_build_and_runtime_graphs(tmp_path):
    run_dir = tmp_path / "run"
    _write_complete_final_assembly_inputs(run_dir)

    result = run_final_graph_assembly_phase(run_dir=run_dir)

    final_dir = run_dir / "final_graph"
    build_graph = json.loads((final_dir / "build_graph.json").read_text(encoding="utf-8"))
    runtime_graph = json.loads((final_dir / "runtime_graph.json").read_text(encoding="utf-8"))
    validation_report = json.loads((final_dir / "validation_report.json").read_text(encoding="utf-8"))

    assert result["summary"] == {
        "concept_count": 2,
        "lesson_count": 2,
        "segmented_lesson_count": 1,
        "runtime_lesson_count": 2,
        "dependency_edge_count": 0,
        "blocking_error_count": 0,
        "warning_count": 1,
    }
    assert result["artifact_paths"] == {
        "build_graph": "final_graph/build_graph.json",
        "runtime_graph": "final_graph/runtime_graph.json",
        "validation_report": "final_graph/validation_report.json",
    }

    assert build_graph["artifact_type"] == "build_graph"
    assert build_graph["schema_version"] == "build_graph.v0"
    assert build_graph["source_artifacts"]["source_ledger"] == "source_ledger.json"
    assert build_graph["source_artifacts"]["subject_merge"] == "subject_merge.json"
    assert build_graph["source_artifacts"]["dependency_inference"] == "dependency_inference.json"
    assert build_graph["source_artifacts"]["lesson_segmentation_summary"] == "lesson_segmentation_summary.json"
    assert build_graph["source_artifacts"]["knowledge_type_classification"] == "knowledge_type_classification_summary.json"
    assert build_graph["subject"]["pipeline_subject_id"] == "COM"
    assert build_graph["concepts"][0]["display_code"] == "COM-001"
    assert build_graph["concepts"][0]["provenance"]["knowledge_type_classification"]["rationale"] == (
        "Teaching focuses on why tokenization matters."
    )
    assert build_graph["concepts"][0]["provenance"]["source_candidate_ids"] == ["lr001_001"]
    assert build_graph["concepts"][0]["provenance"]["lesson_reconciliation_refs"][0]["artifact_path"] == (
        "lessons/lesson-bow/lesson_reconciliation.json"
    )
    assert build_graph["lessons"][0]["segments"][0]["display_code"] == "L01-S01"
    assert build_graph["lessons"][1]["segments"] == []
    assert build_graph["validation"]["status"] == "passed_with_warnings"

    assert runtime_graph["artifact_type"] == "runtime_graph"
    assert runtime_graph["schema_version"] == "runtime_graph.v0"
    assert "day_presets" not in runtime_graph
    assert runtime_graph["subject"]["pipeline_subject_id"] == "COM"
    assert runtime_graph["concepts"] == [
        {
            "concept_id": "concept_tokenization",
            "display_code": "COM-001",
            "label": "Tokenization",
            "knowledge_type": "conceptual",
            "description": "Split text into tokens.",
            "coverage_criteria": ["Student can explain tokenization."],
            "common_misconceptions": [],
            "dependencies": {"blocking": [], "hard": [], "soft": []},
        },
        {
            "concept_id": "concept_bow",
            "display_code": "COM-002",
            "label": "Bag of Words",
            "knowledge_type": "procedural",
            "description": "Represent text by token counts.",
            "coverage_criteria": ["Student can build a tiny count vector."],
            "common_misconceptions": [],
            "dependencies": {"blocking": [], "hard": [], "soft": []},
        },
    ]
    assert runtime_graph["lessons"] == [
        {
            "lesson_id": "lesson-bow",
            "display_code": "L01",
            "date": "2026-05-05",
            "title": "Bag of Words",
            "description": "Representacao vetorial de textos.",
            "segments": [
                {
                    "segment_id": "segment_001",
                    "display_code": "L01-S01",
                    "label": "Tokenization before counts",
                    "instructional_role": "teach",
                    "concept_ids": ["concept_tokenization", "concept_bow"],
                    "teaching_notes": "",
                }
            ],
        },
        {
            "lesson_id": "lesson-review",
            "display_code": "L02",
            "date": "2026-05-12",
            "title": "Review",
            "description": ".",
            "segments": [],
        },
    ]
    assert validation_report["status"] == "passed_with_warnings"
    assert validation_report["blocking_errors"] == []
    assert validation_report["warnings"] == [
        {
            "code": "lesson_without_concepts",
            "message": "Lesson has no Concepts and was exported without Segments.",
            "lesson_id": "lesson-review",
        }
    ]


def test_final_graph_assembly_blocks_runtime_export_when_segments_miss_a_lesson_concept(tmp_path):
    run_dir = tmp_path / "run"
    _write_complete_final_assembly_inputs(run_dir)
    segment_path = run_dir / "lessons" / "lesson-bow" / "lesson_segments.json"
    segment_artifact = json.loads(segment_path.read_text(encoding="utf-8"))
    segment_artifact["segments"][0]["concept_ids"] = ["concept_tokenization"]
    _write_json(segment_path, segment_artifact)

    with pytest.raises(StageBlockedError, match="Final Graph Assembly blocked by validation"):
        run_final_graph_assembly_phase(run_dir=run_dir)

    final_dir = run_dir / "final_graph"
    validation_report = json.loads((final_dir / "validation_report.json").read_text(encoding="utf-8"))
    assert validation_report["status"] == "failed"
    assert validation_report["blocking_errors"] == [
        {
            "code": "segment_concept_mismatch",
            "message": "Lesson Segments must cover every Lesson Concept exactly once.",
            "lesson_id": "lesson-bow",
        }
    ]
    assert not (final_dir / "build_graph.json").exists()
    assert not (final_dir / "runtime_graph.json").exists()


def test_final_graph_assembly_blocks_without_knowledge_type_classification(tmp_path):
    run_dir = tmp_path / "run"
    _write_complete_final_assembly_inputs(run_dir)
    (run_dir / "knowledge_type_classification_summary.json").unlink()

    with pytest.raises(StageBlockedError, match="Phase 7b"):
        run_final_graph_assembly_phase(run_dir=run_dir)


def test_pipeline_runs_phase_8_final_graph_assembly_from_existing_run_artifacts(tmp_path):
    run_dir = tmp_path / "run"
    _write_complete_final_assembly_inputs(run_dir)
    reference_graph = tmp_path / "cg_pipeline" / "reference" / "courses" / "si" / "mod6" / "computacao" / "graph.json"

    result = run_pipeline(
        cg_pipeline_root=tmp_path / "cg_pipeline",
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        clean_run_dir=False,
        phases=["phase-8"],
    )

    assert result["final_graph_assembly"]["summary"]["concept_count"] == 2
    assert result["manual_output"]["final_graph_assembly_summary"]["runtime_lesson_count"] == 2
    assert result["manual_output"]["final_graph_artifact_paths"] == {
        "build_graph": "final_graph/build_graph.json",
        "runtime_graph": "final_graph/runtime_graph.json",
        "validation_report": "final_graph/validation_report.json",
    }
    assert (run_dir / "final_graph" / "build_graph.json").is_file()
    assert (run_dir / "final_graph" / "runtime_graph.json").is_file()
    assert not reference_graph.exists()


def _write_complete_final_assembly_inputs(run_dir):
    (run_dir / "lessons" / "lesson-bow").mkdir(parents=True)
    source_ledger = {
        "artifact_type": "source_ledger",
        "schema_version": "source_ledger.v0",
        "course_id": "si",
        "module_id": "mod6",
        "subject_id": "COM",
        "inputs": {"workbook_path": "source/si_mod6.xlsx"},
        "summary": {"lesson_count": 2, "self_study_count": 1, "available_count": 1, "unavailable_count": 0},
        "lessons": [
            {
                "lesson_id": "lesson-bow",
                "display_code": "L01",
                "title": "Bag of Words",
                "date": "05/05/2026",
                "professor": "Ada",
                "axis": "COM",
                "description": "Representacao vetorial de textos.",
            },
            {
                "lesson_id": "lesson-review",
                "display_code": "L02",
                "title": "Review",
                "date": "12/05/2026",
                "professor": "Ada",
                "axis": "COM",
                "description": ".",
            },
        ],
        "self_studies": [
            {
                "self_study_id": "1",
                "lesson_id": "lesson-bow",
                "source_body_status": "usable_source_body",
                "workbook_metadata": {"title": "BoW article", "url": "https://example.test/bow"},
                "source_body": {"path": "extraction/post-image/0001-bow.md", "sha256": "abc123"},
            }
        ],
    }
    subject_merge = {
        "artifact_type": "subject_merge",
        "schema_version": "subject_merge.v0",
        "course_id": "si",
        "module_id": "mod6",
        "subject_id": "COM",
        "summary": {"concept_count": 2},
        "concepts": [
            _concept("concept_tokenization", "Tokenization", "conceptual", "Split text into tokens.", ["Student can explain tokenization."], "lr001_001"),
            _concept("concept_bow", "Bag of Words", "procedural", "Represent text by token counts.", ["Student can build a tiny count vector."], "lr001_002"),
        ],
    }
    dependency_inference = {
        "artifact_type": "dependency_inference",
        "schema_version": "dependency_inference.v0",
        "deferred": True,
        "dependency_edges": [],
        "summary": {"concept_count": 2, "dependency_edge_count": 0, "deferred": True},
    }
    lesson_segments = {
        "artifact_type": "lesson_segments",
        "schema_version": "lesson_segments.v0",
        "lesson_id": "lesson-bow",
        "status": "reliable",
        "repaired": False,
        "segments": [
            {
                "segment_id": "segment_001",
                "label": "Tokenization before counts",
                "instructional_role": "teach",
                "concept_ids": ["concept_tokenization", "concept_bow"],
            }
        ],
        "structural_warnings": [],
    }
    segmentation_summary = {
        "artifact_type": "lesson_segmentation_summary",
        "schema_version": "lesson_segmentation_summary.v0",
        "summary": {
            "lesson_count": 2,
            "segmented_lesson_count": 1,
            "segment_count": 1,
            "repair_count": 0,
            "unrepaired_count": 0,
            "skipped_no_concept_lesson_count": 1,
        },
        "artifacts": ["lessons/lesson-bow/lesson_segments.json"],
        "lessons": [
            {
                "lesson_id": "lesson-bow",
                "artifact_path": "lessons/lesson-bow/lesson_segments.json",
                "status": "reliable",
                "repaired": False,
                "segment_count": 1,
                "quality_audit_artifact": "lessons/lesson-bow/lesson_segmentation_quality_audit.json",
            },
            {
                "lesson_id": "lesson-review",
                "artifact_path": None,
                "status": "skipped_no_concepts",
                "repaired": False,
                "segment_count": 0,
                "quality_audit_artifact": None,
            },
        ],
    }
    _write_json(run_dir / "source_ledger.json", source_ledger)
    _write_json(run_dir / "subject_merge.json", subject_merge)
    _write_json(run_dir / "dependency_inference.json", dependency_inference)
    _write_json(run_dir / "lesson_segmentation_summary.json", segmentation_summary)
    _write_json(run_dir / "lessons" / "lesson-bow" / "lesson_segments.json", lesson_segments)
    _write_json(
        run_dir / "knowledge_type_classification_summary.json",
        {
            "artifact_type": "knowledge_type_classification_summary",
            "schema_version": "knowledge_type_classification_summary.v0",
            "status": "reliable",
            "summary": {
                "concept_count": 2,
                "classified_concept_count": 2,
                "segment_classification_count": 1,
                "conflict_count": 0,
                "audit_count": 1,
                "repair_count": 0,
                "unrepaired_count": 0,
                "distribution": {"applied": 0, "conceptual": 1, "factual": 0, "procedural": 1},
            },
            "quality_audit": {"reliability": "reliable"},
            "classifications": [
                {
                    "concept_id": "concept_tokenization",
                    "knowledge_type": "conceptual",
                    "rationale": "Teaching focuses on why tokenization matters.",
                    "confidence": 0.9,
                    "source": "segment_consensus",
                    "segment_refs": [],
                },
                {
                    "concept_id": "concept_bow",
                    "knowledge_type": "procedural",
                    "rationale": "Coverage asks the student to build a count vector.",
                    "confidence": 0.9,
                    "source": "segment_consensus",
                    "segment_refs": [],
                },
            ],
            "conflicts": [],
        },
    )


def _concept(concept_id, label, knowledge_type, description, coverage_criteria, source_candidate_id):
    return {
        "concept_id": concept_id,
        "label": label,
        "knowledge_type": knowledge_type,
        "description": description,
        "coverage_criteria": coverage_criteria,
        "source_candidate_ids": [source_candidate_id],
        "lesson_reconciliation_refs": [
            {
                "artifact_path": "lessons/lesson-bow/lesson_reconciliation.json",
                "lesson_id": "lesson-bow",
                "reconciled_candidate_id": source_candidate_id,
                "evidence": [
                    {
                        "candidate_ref": {"artifact_path": "lessons/lesson-bow/self_studies/1/extraction_passes/pro-thinking/self_study_extraction.json"},
                        "evidence_type": "source_body",
                        "anchors": [{"kind": "markdown_heading", "locator": "Intro"}],
                    }
                ],
            }
        ],
        "occurrences": [
            {
                "lesson": {"lesson_id": "lesson-bow", "title": "Bag of Words"},
                "source_candidate_ids": [source_candidate_id],
                "source_roles": ["introducing"],
                "evidence_types": ["source_body"],
                "depth": "definition",
            }
        ],
        "depth": "definition",
    }


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
