import json

from concept_graph_creation.cli import run_pipeline
from concept_graph_creation.stages.knowledge_type_classification import run_knowledge_type_classification_phase


def test_knowledge_type_classification_runs_per_segment_and_writes_overlay(tmp_path):
    run_dir = tmp_path / "run"
    _write_inputs(
        run_dir,
        lessons=[{"lesson_id": "lesson-bow", "title": "Bag of Words"}],
        concepts=[
            _concept(
                "concept_tokenization",
                "Tokenization",
                "Split text into tokens before vectorization.",
                ["Student can explain why tokenization matters."],
                ["lesson-bow"],
            ),
            _concept(
                "concept_counts",
                "Token counts",
                "Count token occurrences in a document.",
                ["Student can build a tiny count vector."],
                ["lesson-bow"],
            ),
        ],
        segments_by_lesson={
            "lesson-bow": [
                {
                    "segment_id": "segment_001",
                    "label": "Tokenization and counts",
                    "concept_ids": ["concept_tokenization", "concept_counts"],
                }
            ]
        },
    )
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        calls.append({"stage_name": stage_name, "route": route.alias})
        if stage_name == "knowledge_type_classification":
            model_input = inputs["knowledge_type_classification_input.json"]
            assert model_input["prompt_path"] == "knowledge_type_classification/classify.md"
            assert model_input["taxonomy"]["source_artifact"] == "prompts/system_prompt.txt"
            assert model_input["lesson"] == {"lesson_id": "lesson-bow", "title": "Bag of Words"}
            assert model_input["segment"]["segment_id"] == "segment_001"
            assert "knowledge_type" not in model_input["concepts"][0]
            return json.dumps(
                {
                    "classifications": [
                        {
                            "concept_id": "concept_tokenization",
                            "knowledge_type": "conceptual",
                            "rationale": "Coverage asks why tokenization matters.",
                            "confidence": 0.91,
                        },
                        {
                            "concept_id": "concept_counts",
                            "knowledge_type": "procedural",
                            "rationale": "Coverage asks the student to build a vector.",
                            "confidence": 0.88,
                        },
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "knowledge_type_quality_audit":
            return _reliable_audit_json()
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_knowledge_type_classification_phase(run_dir=run_dir, model_call=model_call)

    artifact = json.loads((run_dir / "knowledge_type_classification_summary.json").read_text(encoding="utf-8"))
    assert calls == [
        {"stage_name": "knowledge_type_classification", "route": "Pro Thinking"},
        {"stage_name": "knowledge_type_quality_audit", "route": "Pro Thinking"},
    ]
    assert result["summary"]["classified_concept_count"] == 2
    assert result["status"] == "reliable"
    assert artifact["status"] == "reliable"
    assert artifact["summary"]["distribution"] == {
        "applied": 0,
        "conceptual": 1,
        "factual": 0,
        "procedural": 1,
    }
    assert artifact["artifacts"] == [
        "lessons/lesson-bow/knowledge_type_segments/segment_001/knowledge_type_classification.json"
    ]
    assert artifact["classifications"][0]["concept_id"] == "concept_tokenization"
    assert artifact["classifications"][0]["knowledge_type"] == "conceptual"


def test_knowledge_type_classification_repairs_repeated_concept_conflict(tmp_path):
    run_dir = tmp_path / "run"
    _write_inputs(
        run_dir,
        lessons=[
            {"lesson_id": "lesson-a", "title": "Regex concepts"},
            {"lesson_id": "lesson-b", "title": "Regex practice"},
        ],
        concepts=[
            _concept(
                "concept_regex",
                "Python regex groups",
                "Use groups to capture parts of matched text.",
                ["Student can use group() after a regex match."],
                ["lesson-a", "lesson-b"],
            )
        ],
        segments_by_lesson={
            "lesson-a": [
                {"segment_id": "segment_001", "label": "Regex idea", "concept_ids": ["concept_regex"]}
            ],
            "lesson-b": [
                {"segment_id": "segment_001", "label": "Regex practice", "concept_ids": ["concept_regex"]}
            ],
        },
    )
    audit_calls = 0

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal audit_calls
        if stage_name == "knowledge_type_classification":
            model_input = inputs["knowledge_type_classification_input.json"]
            knowledge_type = "conceptual" if model_input["lesson"]["lesson_id"] == "lesson-a" else "procedural"
            return json.dumps(
                {
                    "classifications": [
                        {
                            "concept_id": "concept_regex",
                            "knowledge_type": knowledge_type,
                            "rationale": f"Fixture chose {knowledge_type}.",
                            "confidence": 0.8,
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "knowledge_type_quality_audit":
            audit_calls += 1
            return _reliable_audit_json()
        if stage_name == "knowledge_type_quality_repair":
            model_input = inputs["knowledge_type_quality_repair_input.json"]
            assert model_input["target_concept_ids"] == ["concept_regex"]
            assert model_input["current_classifications"][0]["source"] == "segment_conflict_unresolved"
            return json.dumps(
                {
                    "classifications": [
                        {
                            "concept_id": "concept_regex",
                            "knowledge_type": "procedural",
                            "rationale": "Coverage requires using group() after a regex match.",
                            "confidence": 0.93,
                        }
                    ]
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_knowledge_type_classification_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "knowledge_type_classification_summary.json").read_text(encoding="utf-8"))
    assert audit_calls == 2
    assert result["status"] == "repaired"
    assert artifact["summary"]["repair_count"] == 1
    assert artifact["summary"]["unrepaired_count"] == 0
    assert artifact["conflicts"] == []
    assert artifact["classifications"] == [
        {
            "concept_id": "concept_regex",
            "knowledge_type": "procedural",
            "rationale": "Coverage requires using group() after a regex match.",
            "source": "quality_repair",
            "segment_refs": artifact["classifications"][0]["segment_refs"],
            "confidence": 0.93,
            "repair_decision_artifact": "knowledge_type_quality_repair_decision.json",
        }
    ]


def test_pipeline_runs_phase_7b_and_reports_knowledge_type_summary(tmp_path):
    cg_pipeline_root = tmp_path / "cg_pipeline"
    run_dir = tmp_path / "run"
    _write_inputs(
        run_dir,
        lessons=[{"lesson_id": "lesson-bow", "title": "Bag of Words"}],
        concepts=[
            _concept(
                "concept_bow",
                "Bag of Words",
                "Represent documents by token counts.",
                ["Student can build a tiny count vector."],
                ["lesson-bow"],
            )
        ],
        segments_by_lesson={
            "lesson-bow": [{"segment_id": "segment_001", "label": "BoW", "concept_ids": ["concept_bow"]}]
        },
    )

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "knowledge_type_classification":
            return json.dumps(
                {
                    "classifications": [
                        {
                            "concept_id": "concept_bow",
                            "knowledge_type": "procedural",
                            "rationale": "Coverage asks the student to build a count vector.",
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "knowledge_type_quality_audit":
            return _reliable_audit_json()
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_pipeline(
        cg_pipeline_root=cg_pipeline_root,
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        clean_run_dir=False,
        phases=["phase-7b"],
        knowledge_type_model_call=model_call,
    )

    assert result["knowledge_type_classification"]["summary"]["classified_concept_count"] == 1
    assert result["manual_output"]["knowledge_type_classification_summary"]["distribution"]["procedural"] == 1


def _write_inputs(run_dir, *, lessons, concepts, segments_by_lesson):
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(
        run_dir / "source_ledger.json",
        {
            "artifact_type": "source_ledger",
            "schema_version": "source_ledger.v0",
            "course_id": "si",
            "module_id": "mod6",
            "subject_id": "COM",
            "lessons": lessons,
            "self_studies": [],
            "summary": {"lesson_count": len(lessons)},
        },
    )
    _write_json(
        run_dir / "subject_merge.json",
        {
            "artifact_type": "subject_merge",
            "schema_version": "subject_merge.v0",
            "source_artifact": "source_ledger.json",
            "concepts": concepts,
            "summary": {"concept_count": len(concepts)},
        },
    )

    summary_lessons = []
    artifact_refs = []
    for lesson in lessons:
        lesson_id = lesson["lesson_id"]
        segments = segments_by_lesson.get(lesson_id) or []
        if segments:
            artifact_ref = f"lessons/{lesson_id}/lesson_segments.json"
            artifact_refs.append(artifact_ref)
            summary_lessons.append(
                {
                    "lesson_id": lesson_id,
                    "artifact_path": artifact_ref,
                    "status": "reliable",
                    "repaired": False,
                    "segment_count": len(segments),
                    "quality_audit_artifact": f"lessons/{lesson_id}/lesson_segmentation_quality_audit.json",
                }
            )
            _write_json(
                run_dir / artifact_ref,
                {
                    "artifact_type": "lesson_segments",
                    "schema_version": "lesson_segments.v0",
                    "lesson_id": lesson_id,
                    "status": "reliable",
                    "repaired": False,
                    "segments": [
                        {"instructional_role": "teach", **segment}
                        for segment in segments
                    ],
                    "structural_warnings": [],
                },
            )
        else:
            summary_lessons.append(
                {
                    "lesson_id": lesson_id,
                    "artifact_path": None,
                    "status": "skipped_no_concepts",
                    "repaired": False,
                    "segment_count": 0,
                    "quality_audit_artifact": None,
                }
            )

    _write_json(
        run_dir / "lesson_segmentation_summary.json",
        {
            "artifact_type": "lesson_segmentation_summary",
            "schema_version": "lesson_segmentation_summary.v0",
            "summary": {
                "lesson_count": len(lessons),
                "segmented_lesson_count": len(artifact_refs),
                "segment_count": sum(len(segments) for segments in segments_by_lesson.values()),
                "repair_count": 0,
                "unrepaired_count": 0,
                "skipped_no_concept_lesson_count": len(lessons) - len(artifact_refs),
            },
            "artifacts": artifact_refs,
            "lessons": summary_lessons,
        },
    )


def _concept(concept_id, label, description, coverage_criteria, lesson_ids):
    return {
        "concept_id": concept_id,
        "label": label,
        "description": description,
        "coverage_criteria": coverage_criteria,
        "source_candidate_ids": [f"{concept_id}-candidate"],
        "occurrences": [
            {
                "lesson": {"lesson_id": lesson_id, "title": "Lesson"},
                "source_candidate_ids": [f"{concept_id}-candidate"],
            }
            for lesson_id in lesson_ids
        ],
    }


def _reliable_audit_json():
    return json.dumps(
        {
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
        ensure_ascii=False,
    )


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
