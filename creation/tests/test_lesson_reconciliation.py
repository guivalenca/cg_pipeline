import json

from concept_graph_creation.runtime.semantic_reduce import build_candidate_registry
from concept_graph_creation.stages.lesson_reconciliation import run_lesson_reconciliation_phase
from concept_graph_creation.stages.lesson_reconciliation import run_lesson_reconciliation_phase4b
from concept_graph_creation.stages.lesson_reconciliation import validate_lesson_candidate_clustering_decision


def test_lesson_reconciliation_uses_semantic_reduce_and_assembles_lesson_artifact(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    self_study_dir = run_dir / "lessons" / lesson_id / "self_studies" / "22"
    metadata_dir = run_dir / "lessons" / lesson_id / "self_studies" / "64"
    extraction_dir = self_study_dir / "extraction_passes" / "pro-thinking"
    extraction_dir.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    _write_source_ledger(run_dir, lesson_id=lesson_id)
    _write_self_study_extraction(
        extraction_dir / "self_study_extraction.json",
        lesson_id=lesson_id,
        self_study_id="22",
        candidate_id="candidate-22-001",
        label="Bag-of-Words count vectors",
        evidence_type="source_body",
    )
    _write_extraction_set(
        self_study_dir / "self_study_extraction_set.json",
        artifact_path=(
            f"lessons/{lesson_id}/self_studies/22/"
            "extraction_passes/pro-thinking/self_study_extraction.json"
        ),
        lesson_id=lesson_id,
        self_study_id="22",
    )
    _write_metadata_only_extraction(metadata_dir / "metadata_only_extraction.json", lesson_id=lesson_id)
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            calls.append(
                {
                    "route": route.alias,
                    "stage_name": stage_name,
                    "task": model_input["task"],
                    "candidate_ids": model_input["input_candidate_ids"],
                    "repair_context": repair_context,
                }
            )
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Bag-of-Words representation",
                            "rationale": "Both candidates describe Bag-of-Words as a lesson idea.",
                            "candidate_ids": ["c22_pro_thinking_001", "m64_001"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            calls.append(
                {
                    "route": route.alias,
                    "stage_name": stage_name,
                    "task": model_input["task"],
                    "cluster_id": model_input["cluster"]["id"],
                    "candidate_ids": model_input["input_candidate_ids"],
                    "repair_context": repair_context,
                }
            )
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Bag-of-Words count-vector representation",
                            "description": "Bag-of-Words represents text through word-count vectors.",
                            "coverage_criteria": ["Student can explain how BoW creates a count vector."],
                            "source_candidate_ids": ["c22_pro_thinking_001", "m64_001"],
                            "merge_rationale": "The source-body candidate and metadata candidate describe the same lesson idea.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": "c22_pro_thinking_001",
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        },
                        {
                            "candidate_id": "m64_001",
                            "status": "merged_into",
                            "merged_into": "lr001",
                            "explanation": "The metadata-only candidate is represented by the source-backed concept.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    assert calls == [
        {
            "route": "Pro",
            "stage_name": "lesson_candidate_clustering",
            "task": "lesson_candidate_clustering",
            "candidate_ids": ["c22_pro_thinking_001", "m64_001"],
            "repair_context": None,
        },
        {
            "route": "Pro Thinking",
            "stage_name": "lesson_cluster_evaluation",
            "task": "lesson_cluster_evaluation",
            "cluster_id": "cluster_001",
            "candidate_ids": ["c22_pro_thinking_001", "m64_001"],
            "repair_context": None,
        },
    ]
    assert (run_dir / "lessons" / lesson_id / "lesson_candidate_clustering_input.json").is_file()
    assert (run_dir / "lessons" / lesson_id / "lesson_candidate_clustering_decision.json").is_file()
    assert (run_dir / "lessons" / lesson_id / "lesson_candidate_clusters.json").is_file()
    assert (
        run_dir
        / "lessons"
        / lesson_id
        / "cluster_evaluations"
        / "cluster_001"
        / "cluster_evaluation_decision.json"
    ).is_file()
    assert result["summary"] == {
        "lesson_count": 1,
        "reconciled_lesson_count": 1,
        "reused_lesson_count": 0,
        "skipped_count": 0,
    }
    assert result["concurrency"] == {"initial": 2, "final": 2}
    assert artifact["artifact_type"] == "lesson_reconciliation"
    assert artifact["lesson_id"] == lesson_id
    assert artifact["reconciled_candidates"] == [
        {
            "reconciled_candidate_id": f"reconciled-candidate-{lesson_id}-001",
            "label": "Bag-of-Words count-vector representation",
            "description": "Bag-of-Words represents text through word-count vectors.",
            "coverage_criteria": ["Student can explain how BoW creates a count vector."],
            "source_candidate_ids": ["c22_pro_thinking_001", "m64_001"],
            "merge_rationale": "The source-body candidate and metadata candidate describe the same lesson idea.",
            "source_roles": ["explaining"],
            "evidence_types": ["source_body", "workbook_metadata"],
            "evidence": [
                {
                    "candidate_ref": {
                        "artifact_path": (
                            "lessons/lesson-2026-05-05-bow/self_studies/22/"
                            "extraction_passes/pro-thinking/self_study_extraction.json"
                        ),
                        "candidate_id": "candidate-22-001",
                        "evidence_type": "source_body",
                        "model_route": "Pro Thinking",
                        "lesson_id": lesson_id,
                        "self_study_id": "22",
                        "pass_id": "pro-thinking",
                    },
                    "evidence_type": "source_body",
                    "anchors": [{"kind": "markdown_heading", "locator": "BoW"}],
                    "extraction_reason": {
                        "source_grounded_rationale": "The source defines BoW as count vectors.",
                        "granularity_rationale": "This is one checkable idea.",
                    },
                    "source_metadata": {"source_name": "Bag-of-Words count vectors"},
                },
                {
                    "candidate_ref": {
                        "artifact_path": (
                            "lessons/lesson-2026-05-05-bow/self_studies/64/"
                            "metadata_only_extraction.json"
                        ),
                        "candidate_id": "metadata-candidate-64-001",
                        "evidence_type": "workbook_metadata",
                        "model_route": "Pro",
                        "lesson_id": lesson_id,
                        "self_study_id": "64",
                    },
                    "evidence_type": "workbook_metadata",
                    "anchors": [{"kind": "workbook_title", "locator": "Title"}],
                    "extraction_reason": {
                        "metadata_grounded_rationale": "The workbook title names Bag-of-Words.",
                        "granularity_rationale": "This is one metadata-backed idea.",
                    },
                    "source_metadata": {"source_name": "Blocked BoW source"},
                },
            ],
        }
    ]
    assert artifact["candidate_assignments"][1]["status"] == "merged_into"
    assert artifact["summary"] == {
        "input_candidate_count": 2,
        "reconciled_candidate_count": 1,
        "pruned_candidate_count": 0,
        "review_candidate_count": 0,
    }


def test_lesson_candidate_clustering_validation_rejects_missing_duplicate_and_unknown_candidate_ids():
    registry = build_candidate_registry(
        scope_id="lesson-1",
        source_artifact="source_ledger.json",
        candidate_sources=[
            {
                "namespace": "c1",
                "artifact_type": "self_study_extraction",
                "artifact_path": "lessons/lesson-1/self_studies/1/self_study_extraction.json",
                "lesson_id": "lesson-1",
                "self_study_id": "1",
                "model_route": "Pro Thinking",
                "evidence_type": "source_body",
                "candidates": [
                    {"candidate_id": "candidate-1", "label": "One"},
                    {"candidate_id": "candidate-2", "label": "Two"},
                ],
            }
        ],
    )
    decision = {
        "artifact_type": "lesson_candidate_clustering_decision",
        "schema_version": "lesson_candidate_clustering_decision.v0",
        "lesson_id": "lesson-1",
        "model_route": "Pro",
        "input_candidate_ids": ["c1_001", "c1_002"],
        "clusters": [
            {
                "id": "cluster_001",
                "label": "Duplicate candidate",
                "rationale": "Invalid duplicate assignment.",
                "candidate_ids": ["c1_001", "c1_001"],
            },
            {
                "id": "cluster_002",
                "label": "Unknown candidate",
                "rationale": "Invalid unknown assignment.",
                "candidate_ids": ["c1_999"],
            },
        ],
        "summary": {"input_candidate_count": 2, "cluster_count": 2},
    }

    errors = validate_lesson_candidate_clustering_decision(decision, registry)

    assert any("contains duplicates: c1_001" in error for error in errors)
    assert any("references unknown candidate c1_999" in error for error in errors)
    assert any("must appear in exactly one cluster: c1_002" in error for error in errors)


def test_lesson_reconciliation_reuses_valid_clustering_and_evaluation_artifacts(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    _write_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id)
    calls = []

    run_lesson_reconciliation_phase(
        run_dir=run_dir,
        model_call=_two_step_lesson_reconciliation_model_call(calls),
        concurrency=2,
    )
    (run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").unlink()
    (run_dir / "lessons" / lesson_id / "lesson_reconciliation_decision.json").unlink()

    def fail_on_model_call(**_kwargs):
        raise AssertionError("valid Phase 4 intermediate artifacts should be reused")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=fail_on_model_call, concurrency=2)

    assert (run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").is_file()
    assert result["stage_counts"]["reused_clustering_count"] == 1
    assert result["stage_counts"]["reused_evaluation_count"] == 1


def test_lesson_reconciliation_clean_removes_phase_four_artifacts_without_touching_phase_three(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    _write_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id)
    calls = []
    run_lesson_reconciliation_phase(
        run_dir=run_dir,
        model_call=_two_step_lesson_reconciliation_model_call(calls),
        concurrency=2,
    )
    lesson_dir = run_dir / "lessons" / lesson_id
    stale_cluster_dir = lesson_dir / "cluster_evaluations" / "stale_cluster"
    stale_cluster_dir.mkdir(parents=True)
    stale_cluster_artifact = stale_cluster_dir / "cluster_evaluation_decision.json"
    stale_cluster_artifact.write_text("{}\n", encoding="utf-8")
    phase_three_artifact = (
        lesson_dir / "self_studies" / "22" / "extraction_passes" / "pro-thinking" / "self_study_extraction.json"
    )

    rerun_calls = []
    run_lesson_reconciliation_phase(
        run_dir=run_dir,
        model_call=_two_step_lesson_reconciliation_model_call(rerun_calls),
        concurrency=2,
        clean_phase_artifacts=True,
    )

    assert not stale_cluster_artifact.exists()
    assert phase_three_artifact.is_file()
    assert [call["stage_name"] for call in rerun_calls] == [
        "lesson_candidate_clustering",
        "lesson_cluster_evaluation",
    ]


def test_lesson_reconciliation_canonicalizes_clustering_assignment_coverage(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    _write_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id)
    evaluation_candidate_groups = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Duplicated assignment",
                            "rationale": "The model repeated one candidate and omitted another.",
                            "candidate_ids": ["c22_pro_thinking_001", "c22_pro_thinking_001"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            candidate_ids = model_input["input_candidate_ids"]
            evaluation_candidate_groups.append(candidate_ids)
            accepted_id = f"lr_{len(evaluation_candidate_groups):03d}"
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": accepted_id,
                            "label": model_input["candidates"][0]["label"],
                            "description": model_input["candidates"][0]["description"],
                            "coverage_criteria": model_input["candidates"][0]["coverage_criteria"],
                            "source_candidate_ids": candidate_ids,
                            "merge_rationale": "Single-candidate deterministic evaluation.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": candidate_id, "status": "used_in", "accepted_ids": [accepted_id]}
                        for candidate_id in candidate_ids
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    clusters = json.loads(
        (run_dir / "lessons" / lesson_id / "lesson_candidate_clusters.json").read_text(encoding="utf-8")
    )["clusters"]
    assert [cluster["candidate_ids"] for cluster in clusters] == [["c22_pro_thinking_001"], ["m64_001"]]
    assert evaluation_candidate_groups == [["c22_pro_thinking_001", "m64_001"]]


def test_lesson_reconciliation_adds_missing_evaluation_assignments_from_accepted_sources(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    _write_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id)

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Bag-of-Words representation",
                            "rationale": "Both candidates describe the same lesson idea.",
                            "candidate_ids": ["c22_pro_thinking_001", "m64_001"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Bag-of-Words count-vector representation",
                            "description": "Bag-of-Words represents text through word-count vectors.",
                            "coverage_criteria": ["Student can explain how BoW creates a count vector."],
                            "source_candidate_ids": ["c22_pro_thinking_001", "m64_001"],
                            "merge_rationale": "Both candidates support one lesson-local concept.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": "c22_pro_thinking_001",
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        }
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    assert artifact["candidate_assignments"][1] == {
        "candidate_id": "m64_001",
        "status": "used_in",
        "accepted_ids": ["cluster_001__lr001"],
    }


def test_lesson_reconciliation_phase4b_repairs_review_fallback_without_human_review(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    _write_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id)
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            calls.append({"route": route.alias, "stage_name": stage_name})
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Bag-of-Words representation",
                            "rationale": "Both candidates describe the same lesson topic.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            calls.append({"route": route.alias, "stage_name": stage_name})
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Bag-of-Words count-vector representation",
                            "description": "Bag-of-Words represents text through word-count vectors.",
                            "coverage_criteria": ["Student can explain how BoW creates a count vector."],
                            "source_candidate_ids": ["c22_pro_thinking_001"],
                            "merge_rationale": "The source-body candidate is a clear lesson-local concept.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": "c22_pro_thinking_001",
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        }
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
            calls.append(
                {
                    "route": route.alias,
                    "stage_name": stage_name,
                    "candidate_ids": model_input["target_candidate_ids"],
                    "review_count": model_input["quality_audit"]["metrics"]["review_count"],
                    "repair_reason": model_input["repair_reason"],
                }
            )
            return json.dumps(
                {
                    "new_accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "Workbook-backed Bag-of-Words signal",
                            "description": "The workbook metadata reinforces Bag-of-Words as a lesson-local topic.",
                            "coverage_criteria": ["Student can connect the workbook title to the BoW lesson topic."],
                            "source_candidate_ids": ["m64_001"],
                            "merge_rationale": "The omitted metadata candidate is lesson-relevant and should not remain in review.",
                        }
                    ],
                    "existing_concept_candidate_additions": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": "m64_001",
                            "status": "used_in",
                            "accepted_ids": ["repair001"],
                            "explanation": "Accepted as a repaired lesson-local concept.",
                        }
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    repair_artifact = (
        run_dir
        / "lessons"
        / lesson_id
        / "phase4b_repairs"
        / "review_fallback"
        / "lesson_reconciliation_quality_repair_decision.json"
    )
    assert repair_artifact.is_file()
    assert [call["stage_name"] for call in calls] == [
        "lesson_candidate_clustering",
        "lesson_cluster_evaluation",
        "lesson_reconciliation_quality_repair",
    ]
    assert calls[-1] == {
        "route": "Pro Thinking",
        "stage_name": "lesson_reconciliation_quality_repair",
        "candidate_ids": ["m64_001"],
        "review_count": 1,
        "repair_reason": "review_fallback",
    }
    assert artifact["summary"] == {
        "input_candidate_count": 2,
        "reconciled_candidate_count": 2,
        "pruned_candidate_count": 0,
        "review_candidate_count": 0,
    }
    assert artifact["phase4b_quality_audit"]["reliability"] == "repaired"
    assert result["phase4b"]["repair_count"] == 1


def test_lesson_reconciliation_phase4b_repairs_questionable_near_duplicate_pruning(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    _write_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id)
    repair_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Bag-of-Words representation",
                            "rationale": "Both candidates are in the same broad topic.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Bag-of-Words count-vector representation",
                            "description": "Bag-of-Words represents text through word-count vectors.",
                            "coverage_criteria": ["Student can explain how BoW creates a count vector."],
                            "source_candidate_ids": ["c22_pro_thinking_001"],
                            "merge_rationale": "The source-body candidate is a clear lesson-local concept.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": "c22_pro_thinking_001",
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        },
                        {
                            "candidate_id": "m64_001",
                            "status": "pruned",
                            "reason": "near_duplicate",
                            "explanation": "This will be handled elsewhere.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
            repair_calls.append(
                {
                    "repair_reason": model_input["repair_reason"],
                    "candidate_ids": model_input["target_candidate_ids"],
                }
            )
            return json.dumps(
                {
                    "new_accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "Workbook-backed Bag-of-Words signal",
                            "description": "The metadata candidate is a distinct lesson-local signal, not a duplicate.",
                            "coverage_criteria": ["Student can identify the workbook-backed BoW signal."],
                            "source_candidate_ids": ["m64_001"],
                            "merge_rationale": "The earlier near-duplicate prune did not represent this candidate.",
                        }
                    ],
                    "existing_concept_candidate_additions": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": "m64_001",
                            "status": "used_in",
                            "accepted_ids": ["repair001"],
                            "explanation": "Accepted after questionable-prune repair.",
                        }
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    assert repair_calls == [{"repair_reason": "questionable_prune", "candidate_ids": ["m64_001"]}]
    assert artifact["summary"]["reconciled_candidate_count"] == 2
    assert artifact["summary"]["pruned_candidate_count"] == 0
    assert artifact["phase4b_quality_audit"]["reliability"] == "repaired"
    assert result["phase4b"]["repair_count"] == 1


def test_lesson_reconciliation_phase4b_repairs_low_net_over_pruned_lesson(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-04-27-intro-nlp"
    _write_over_pruned_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id, candidate_count=8)
    repair_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Introductory NLP concepts",
                            "rationale": "All candidates belong to the introductory NLP lesson.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            candidate_ids = model_input["input_candidate_ids"]
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Natural language processing overview",
                            "description": "NLP studies computational processing of natural language.",
                            "coverage_criteria": ["Student can define NLP as computational language processing."],
                            "source_candidate_ids": [candidate_ids[0]],
                            "merge_rationale": "Only the first candidate was preserved by the flawed evaluation.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_ids[0],
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        },
                        *[
                            {
                                "candidate_id": candidate_id,
                                "status": "pruned",
                                "reason": "low_teaching_value",
                                "explanation": "The flawed evaluation over-pruned this lesson-local concept.",
                            }
                            for candidate_id in candidate_ids[1:]
                        ],
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
            target_ids = model_input["target_candidate_ids"]
            repair_calls.append(
                {
                    "repair_reason": model_input["repair_reason"],
                    "candidate_ids": target_ids,
                    "net": model_input["quality_audit"]["scores"]["net_phase4_benefit"],
                    "flags": model_input["quality_audit"]["flags"],
                }
            )
            return json.dumps(
                {
                    "new_accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "NLP application areas",
                            "description": "NLP includes lesson-local application areas worth preserving.",
                            "coverage_criteria": ["Student can name NLP application areas from the lesson."],
                            "source_candidate_ids": [target_ids[0]],
                            "merge_rationale": "The over-pruned candidate carries a distinct lesson-local concept.",
                        }
                    ],
                    "existing_concept_candidate_additions": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": target_ids[0],
                            "status": "used_in",
                            "accepted_ids": ["repair001"],
                            "explanation": "Recovered as a distinct lesson-local concept.",
                        },
                        *[
                            {
                                "candidate_id": candidate_id,
                                "status": "pruned",
                                "reason": "low_teaching_value",
                                "explanation": "Still below the lesson concept threshold after targeted repair.",
                            }
                            for candidate_id in target_ids[1:]
                        ],
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    expected_target_ids = [f"c{index}_pro_thinking_001" for index in range(2, 9)]
    assert repair_calls == [
        {
            "repair_reason": "over_pruned",
            "candidate_ids": expected_target_ids,
            "net": 1,
            "flags": ["over_pruned"],
        }
    ]
    assert artifact["summary"]["reconciled_candidate_count"] == 2
    assert artifact["summary"]["pruned_candidate_count"] == 6
    assert artifact["phase4b_quality_audit"]["reliability"] == "repaired"
    assert result["phase4b"]["repair_count"] == 1


def test_lesson_reconciliation_phase4b_confirms_over_pruned_when_repair_prunes_every_target(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-04-27-intro-nlp"
    _write_over_pruned_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id, candidate_count=8)

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Introductory NLP concepts",
                            "rationale": "All candidates belong to the introductory NLP lesson.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            candidate_ids = model_input["input_candidate_ids"]
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Natural language processing overview",
                            "description": "NLP studies computational processing of natural language.",
                            "coverage_criteria": ["Student can define NLP as computational language processing."],
                            "source_candidate_ids": [candidate_ids[0]],
                            "merge_rationale": "Only the first candidate was preserved by the flawed evaluation.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_ids[0],
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        },
                        *[
                            {
                                "candidate_id": candidate_id,
                                "status": "pruned",
                                "reason": "low_teaching_value",
                                "explanation": "The flawed evaluation over-pruned this lesson-local concept.",
                            }
                            for candidate_id in candidate_ids[1:]
                        ],
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            target_ids = inputs["lesson_reconciliation_quality_repair_input.json"]["target_candidate_ids"]
            return json.dumps(
                {
                    "new_accepted_concepts": [],
                    "existing_concept_candidate_additions": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_id,
                            "status": "pruned",
                            "reason": "low_teaching_value",
                            "explanation": "The repair failed to recover any lesson-local concept.",
                        }
                        for candidate_id in target_ids
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    audit = artifact["phase4b_quality_audit"]
    assert audit["reliability"] == "confirmed"
    assert audit["flags"] == ["over_pruned_confirmed"]
    assert result["phase4b"]["repair_count"] == 0
    assert result["phase4b"]["confirmed_count"] == 1
    assert result["phase4b"]["unrepaired_count"] == 0


def test_lesson_reconciliation_phase4b_repairs_over_merged_lesson(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-04-27-intro-nlp"
    _write_over_pruned_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id, candidate_count=8)
    repair_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Introductory NLP concepts",
                            "rationale": "All candidates belong to the introductory NLP lesson.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            candidate_ids = model_input["input_candidate_ids"]
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Broad NLP overview",
                            "description": "A broad concept that incorrectly absorbs distinct NLP ideas.",
                            "coverage_criteria": ["Student can discuss NLP broadly."],
                            "source_candidate_ids": candidate_ids,
                            "merge_rationale": "The flawed evaluation merged every candidate into one broad concept.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_ids[0],
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        },
                        *[
                            {
                                "candidate_id": candidate_id,
                                "status": "merged_into",
                                "merged_into": "lr001",
                                "explanation": "Incorrectly collapsed into a broad concept.",
                            }
                            for candidate_id in candidate_ids[1:]
                        ],
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
            target_ids = model_input["target_candidate_ids"]
            repair_calls.append(
                {
                    "repair_reason": model_input["repair_reason"],
                    "candidate_ids": target_ids,
                    "flags": model_input["quality_audit"]["flags"],
                }
            )
            return json.dumps(
                {
                    "new_accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "NLP application areas",
                            "description": "A distinct introductory NLP idea split out from the broad merge.",
                            "coverage_criteria": ["Student can name NLP application areas."],
                            "source_candidate_ids": [target_ids[0]],
                            "merge_rationale": "The target candidate is not represented precisely by the broad overview.",
                        }
                    ],
                    "existing_concept_candidate_additions": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": target_ids[0],
                            "status": "used_in",
                            "accepted_ids": ["repair001"],
                            "explanation": "Recovered as a distinct concept.",
                        },
                        *[
                            {
                                "candidate_id": candidate_id,
                                "status": "merged_into",
                                "merged_into": "reconciled-candidate-lesson-2026-04-27-intro-nlp-001",
                                "explanation": "Still represented by the broad overview.",
                            }
                            for candidate_id in target_ids[1:]
                        ],
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    expected_target_ids = [f"c{index}_pro_thinking_001" for index in range(2, 9)]
    assert repair_calls == [
        {
            "repair_reason": "over_merged",
            "candidate_ids": expected_target_ids,
            "flags": ["over_merged"],
        }
    ]
    assert artifact["summary"]["reconciled_candidate_count"] == 2
    assert artifact["phase4b_quality_audit"]["reliability"] == "repaired"
    assert result["phase4b"]["repair_count"] == 1


def test_lesson_reconciliation_phase4b_repairs_fragmented_duplicate_concepts(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-04-27-intro-nlp"
    _write_over_pruned_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id, candidate_count=4)
    repair_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": f"cluster_{index:03d}",
                            "label": candidate_id,
                            "rationale": "Singleton cluster for duplicate-fragmentation test.",
                            "candidate_ids": [candidate_id],
                        }
                        for index, candidate_id in enumerate(model_input["input_candidate_ids"], start=1)
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            candidate_ids = model_input["input_candidate_ids"]
            candidates_by_id = {candidate["id"]: candidate for candidate in model_input["candidates"]}
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": f"lr{index:03d}",
                            "label": (
                                "Natural language processing definition"
                                if candidate_id in {"c1_pro_thinking_001", "c2_pro_thinking_001"}
                                else candidates_by_id[candidate_id]["label"]
                            ),
                            "description": f"{label} as a lesson-local concept.",
                            "coverage_criteria": [f"Student can explain {label}."],
                            "source_candidate_ids": [candidate_id],
                            "merge_rationale": "Accepted as a standalone concept.",
                        }
                        for index, candidate_id in enumerate(candidate_ids, start=1)
                        for label in [
                            (
                                "Natural language processing definition"
                                if candidate_id in {"c1_pro_thinking_001", "c2_pro_thinking_001"}
                                else candidates_by_id[candidate_id]["label"]
                            )
                        ]
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_id,
                            "status": "used_in",
                            "accepted_ids": [f"lr{index:03d}"],
                        }
                        for index, candidate_id in enumerate(candidate_ids, start=1)
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
            target_ids = model_input["target_candidate_ids"]
            repair_calls.append(
                {
                    "repair_reason": model_input["repair_reason"],
                    "candidate_ids": target_ids,
                    "flags": model_input["quality_audit"]["flags"],
                }
            )
            return json.dumps(
                {
                    "new_accepted_concepts": [],
                    "existing_concept_candidate_additions": [
                        {
                            "reconciled_candidate_id": "reconciled-candidate-lesson-2026-04-27-intro-nlp-001",
                            "candidate_ids": target_ids,
                            "explanation": "The duplicate candidate is represented by the first accepted NLP definition.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_id,
                            "status": "merged_into",
                            "merged_into": "reconciled-candidate-lesson-2026-04-27-intro-nlp-001",
                            "explanation": "Merged into the canonical duplicate concept.",
                        }
                        for candidate_id in target_ids
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    assert repair_calls == [
        {
            "repair_reason": "fragmented_duplicates",
            "candidate_ids": ["c2_pro_thinking_001"],
            "flags": ["fragmented_duplicates"],
        }
    ]
    assert artifact["summary"]["reconciled_candidate_count"] == 3
    assert artifact["phase4b_quality_audit"]["reliability"] == "repaired"
    assert result["phase4b"]["repair_count"] == 1


def test_lesson_reconciliation_phase4b_repairs_metadata_overreach(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    _write_metadata_overreach_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id)
    repair_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Metadata overreach batch",
                            "rationale": "One batch for metadata overreach test.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": f"lr{index:03d}",
                            "label": candidate["label"],
                            "description": candidate["description"],
                            "coverage_criteria": candidate["coverage_criteria"],
                            "source_candidate_ids": [candidate["id"]],
                            "merge_rationale": "Accepted too aggressively for metadata overreach test.",
                        }
                        for index, candidate in enumerate(model_input["candidates"], start=1)
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_id,
                            "status": "used_in",
                            "accepted_ids": [f"lr{index:03d}"],
                        }
                        for index, candidate_id in enumerate(model_input["input_candidate_ids"], start=1)
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
            target_ids = model_input["target_candidate_ids"]
            repair_calls.append(
                {
                    "repair_reason": model_input["repair_reason"],
                    "candidate_ids": target_ids,
                    "flags": model_input["quality_audit"]["flags"],
                }
            )
            return json.dumps(
                {
                    "new_accepted_concepts": [],
                    "existing_concept_candidate_additions": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_id,
                            "status": "pruned",
                            "reason": "unsupported_metadata_only",
                            "explanation": "Metadata-only candidate does not add a lesson gap beyond source body evidence.",
                        }
                        for candidate_id in target_ids
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    assert repair_calls == [
        {
            "repair_reason": "metadata_overreach",
            "candidate_ids": ["m2_001", "m3_001", "m4_001"],
            "flags": ["metadata_overreach"],
        }
    ]
    assert artifact["summary"]["reconciled_candidate_count"] == 1
    assert artifact["summary"]["pruned_candidate_count"] == 3
    assert artifact["phase4b_quality_audit"]["reliability"] == "repaired"
    assert result["phase4b"]["repair_count"] == 1


def test_lesson_reconciliation_phase4b_repairs_off_lesson_accepted_concepts(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-04-27-intro-nlp"
    _write_over_pruned_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id, candidate_count=4)
    repair_calls = []

    accepted_labels = {
        "c1_pro_thinking_001": "Natural language processing definition",
        "c2_pro_thinking_001": "Pip install environment setup",
        "c3_pro_thinking_001": "GitHub repository setup",
        "c4_pro_thinking_001": "NLP application areas",
    }

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Accepted off-lesson batch",
                            "rationale": "One batch for off-lesson accepted test.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            candidate_ids = model_input["input_candidate_ids"]
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": f"lr{index:03d}",
                            "label": accepted_labels[candidate_id],
                            "description": f"{accepted_labels[candidate_id]} in the lesson.",
                            "coverage_criteria": [f"Student can explain {accepted_labels[candidate_id]}."],
                            "source_candidate_ids": [candidate_id],
                            "merge_rationale": "Accepted as a standalone concept.",
                        }
                        for index, candidate_id in enumerate(candidate_ids, start=1)
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_id,
                            "status": "used_in",
                            "accepted_ids": [f"lr{index:03d}"],
                        }
                        for index, candidate_id in enumerate(candidate_ids, start=1)
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
            target_ids = model_input["target_candidate_ids"]
            repair_calls.append(
                {
                    "repair_reason": model_input["repair_reason"],
                    "candidate_ids": target_ids,
                    "flags": model_input["quality_audit"]["flags"],
                }
            )
            return json.dumps(
                {
                    "new_accepted_concepts": [],
                    "existing_concept_candidate_additions": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_id,
                            "status": "pruned",
                            "reason": "incidental",
                            "explanation": "Setup or repository mechanics are not lesson-local concepts here.",
                        }
                        for candidate_id in target_ids
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    assert repair_calls == [
        {
            "repair_reason": "off_lesson_accepted",
            "candidate_ids": ["c2_pro_thinking_001", "c3_pro_thinking_001"],
            "flags": ["off_lesson_accepted"],
        }
    ]
    assert artifact["summary"]["reconciled_candidate_count"] == 2
    assert artifact["summary"]["pruned_candidate_count"] == 2
    assert artifact["phase4b_quality_audit"]["reliability"] == "repaired"
    assert result["phase4b"]["repair_count"] == 1


def test_lesson_reconciliation_phase4b_repairs_over_accepted_lesson(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-04-27-intro-nlp"
    _write_over_pruned_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id, candidate_count=6)
    repair_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Over accepted batch",
                            "rationale": "One batch for over-accepted test.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": f"lr{index:03d}",
                            "label": candidate["label"],
                            "description": candidate["description"],
                            "coverage_criteria": candidate["coverage_criteria"],
                            "source_candidate_ids": [candidate["id"]],
                            "merge_rationale": "Accepted every candidate too aggressively.",
                        }
                        for index, candidate in enumerate(model_input["candidates"], start=1)
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": candidate_id,
                            "status": "used_in",
                            "accepted_ids": [f"lr{index:03d}"],
                        }
                        for index, candidate_id in enumerate(model_input["input_candidate_ids"], start=1)
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
            target_ids = model_input["target_candidate_ids"]
            repair_calls.append(
                {
                    "repair_reason": model_input["repair_reason"],
                    "candidate_ids": target_ids,
                    "flags": model_input["quality_audit"]["flags"],
                }
            )
            return json.dumps(
                {
                    "new_accepted_concepts": [],
                    "existing_concept_candidate_additions": [
                        {
                            "reconciled_candidate_id": "reconciled-candidate-lesson-2026-04-27-intro-nlp-001",
                            "candidate_ids": [target_ids[0]],
                            "explanation": "One target is represented by the first accepted concept.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": target_ids[0],
                            "status": "merged_into",
                            "merged_into": "reconciled-candidate-lesson-2026-04-27-intro-nlp-001",
                            "explanation": "Merged into an existing concept after over-accepted recheck.",
                        },
                        *[
                            {
                                "candidate_id": candidate_id,
                                "status": "pruned",
                                "reason": "low_teaching_value",
                                "explanation": "Not strong enough to survive targeted over-accepted recheck.",
                            }
                            for candidate_id in target_ids[1:]
                        ],
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_reconciliation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    artifact = json.loads((run_dir / "lessons" / lesson_id / "lesson_reconciliation.json").read_text())
    assert repair_calls == [
        {
            "repair_reason": "over_accepted",
            "candidate_ids": [f"c{index}_pro_thinking_001" for index in range(2, 7)],
            "flags": ["over_accepted"],
        }
    ]
    assert artifact["summary"]["reconciled_candidate_count"] == 1
    assert artifact["summary"]["pruned_candidate_count"] == 4
    assert artifact["phase4b_quality_audit"]["reliability"] == "repaired"
    assert result["phase4b"]["repair_count"] == 1


def test_lesson_reconciliation_phase4b_restart_rebuilds_from_phase4a_outputs(tmp_path):
    run_dir = tmp_path / "run"
    lesson_id = "lesson-2026-05-05-bow"
    _write_lesson_reconciliation_phase_inputs(run_dir, lesson_id=lesson_id)

    def initial_model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Bag-of-Words representation",
                            "rationale": "Both candidates describe the same lesson topic.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Bag-of-Words count-vector representation",
                            "description": "Bag-of-Words represents text through word-count vectors.",
                            "coverage_criteria": ["Student can explain how BoW creates a count vector."],
                            "source_candidate_ids": ["c22_pro_thinking_001"],
                            "merge_rationale": "The source-body candidate is a clear lesson-local concept.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": "c22_pro_thinking_001",
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        }
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_reconciliation_quality_repair":
            return json.dumps(
                {
                    "new_accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "Workbook-backed Bag-of-Words signal",
                            "description": "The workbook metadata reinforces Bag-of-Words as a lesson-local topic.",
                            "coverage_criteria": ["Student can connect the workbook title to the BoW lesson topic."],
                            "source_candidate_ids": ["m64_001"],
                            "merge_rationale": "The omitted metadata candidate is lesson-relevant.",
                        }
                    ],
                    "existing_concept_candidate_additions": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": "m64_001",
                            "status": "used_in",
                            "accepted_ids": ["repair001"],
                            "explanation": "Accepted by the first Phase 4b run.",
                        }
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_lesson_reconciliation_phase(run_dir=run_dir, model_call=initial_model_call, concurrency=2)
    lesson_dir = run_dir / "lessons" / lesson_id
    stale_marker = lesson_dir / "phase4b_repairs" / "review_fallback" / "stale.txt"
    stale_marker.write_text("old phase4b artifact\n", encoding="utf-8")
    repaired_artifact = json.loads((lesson_dir / "lesson_reconciliation.json").read_text())
    assert repaired_artifact["summary"]["reconciled_candidate_count"] == 2

    restart_calls = []

    def phase4b_restart_model_call(*, route, stage_name, inputs, repair_context=None):
        restart_calls.append(stage_name)
        if stage_name != "lesson_reconciliation_quality_repair":
            raise AssertionError("Phase 4b restart must not rerun Phase 4a model calls")
        return json.dumps(
            {
                "new_accepted_concepts": [],
                "existing_concept_candidate_additions": [],
                "candidate_assignments": [
                    {
                        "candidate_id": "m64_001",
                        "status": "pruned",
                        "reason": "unsupported_metadata_only",
                        "explanation": "The restarted Phase 4b run pruned the reviewed metadata candidate.",
                    }
                ],
            },
            ensure_ascii=False,
        )

    result = run_lesson_reconciliation_phase4b(run_dir=run_dir, model_call=phase4b_restart_model_call)

    restarted_artifact = json.loads((lesson_dir / "lesson_reconciliation.json").read_text())
    assert restart_calls == ["lesson_reconciliation_quality_repair"]
    assert not stale_marker.exists()
    assert restarted_artifact["summary"] == {
        "input_candidate_count": 2,
        "reconciled_candidate_count": 1,
        "pruned_candidate_count": 1,
        "review_candidate_count": 0,
    }
    assert result["rebuilt_from_phase4a_count"] == 1
    assert result["phase4b"]["repair_count"] == 1


def _write_lesson_reconciliation_phase_inputs(run_dir, *, lesson_id):
    self_study_dir = run_dir / "lessons" / lesson_id / "self_studies" / "22"
    metadata_dir = run_dir / "lessons" / lesson_id / "self_studies" / "64"
    extraction_dir = self_study_dir / "extraction_passes" / "pro-thinking"
    extraction_dir.mkdir(parents=True)
    metadata_dir.mkdir(parents=True)
    _write_source_ledger(run_dir, lesson_id=lesson_id)
    _write_self_study_extraction(
        extraction_dir / "self_study_extraction.json",
        lesson_id=lesson_id,
        self_study_id="22",
        candidate_id="candidate-22-001",
        label="Bag-of-Words count vectors",
        evidence_type="source_body",
    )
    _write_extraction_set(
        self_study_dir / "self_study_extraction_set.json",
        artifact_path=(
            "lessons/lesson-2026-05-05-bow/self_studies/22/"
            "extraction_passes/pro-thinking/self_study_extraction.json"
        ),
        lesson_id=lesson_id,
        self_study_id="22",
    )
    _write_metadata_only_extraction(metadata_dir / "metadata_only_extraction.json", lesson_id=lesson_id)


def _write_over_pruned_lesson_reconciliation_phase_inputs(run_dir, *, lesson_id, candidate_count):
    run_dir.mkdir(parents=True, exist_ok=True)
    self_studies = [
        {
            "self_study_id": str(index),
            "lesson_id": lesson_id,
            "source_body_status": "usable_source_body",
            "workbook_metadata": {"title": f"Introductory NLP concept {index}"},
        }
        for index in range(1, candidate_count + 1)
    ]
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": lesson_id, "title": "Introductory NLP"}],
                "self_studies": self_studies,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    for index in range(1, candidate_count + 1):
        self_study_id = str(index)
        self_study_dir = run_dir / "lessons" / lesson_id / "self_studies" / self_study_id
        extraction_dir = self_study_dir / "extraction_passes" / "pro-thinking"
        extraction_dir.mkdir(parents=True)
        _write_self_study_extraction(
            extraction_dir / "self_study_extraction.json",
            lesson_id=lesson_id,
            self_study_id=self_study_id,
            candidate_id=f"candidate-{index}-001",
            label=f"Introductory NLP concept {index}",
            evidence_type="source_body",
        )
        _write_extraction_set(
            self_study_dir / "self_study_extraction_set.json",
            artifact_path=(
                f"lessons/{lesson_id}/self_studies/{self_study_id}/"
                "extraction_passes/pro-thinking/self_study_extraction.json"
            ),
            lesson_id=lesson_id,
            self_study_id=self_study_id,
        )


def _write_metadata_overreach_lesson_reconciliation_phase_inputs(run_dir, *, lesson_id):
    run_dir.mkdir(parents=True, exist_ok=True)
    self_studies = [
        {
            "self_study_id": "1",
            "lesson_id": lesson_id,
            "source_body_status": "usable_source_body",
            "workbook_metadata": {"title": "Bag-of-Words count vectors"},
        },
        *[
            {
                "self_study_id": str(index),
                "lesson_id": lesson_id,
                "source_body_status": "unavailable_source_body",
                "workbook_metadata": {"title": f"Metadata-only BoW hint {index}"},
            }
            for index in range(2, 5)
        ],
    ]
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": lesson_id, "title": "Bag of Words"}],
                "self_studies": self_studies,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    source_dir = run_dir / "lessons" / lesson_id / "self_studies" / "1"
    extraction_dir = source_dir / "extraction_passes" / "pro-thinking"
    extraction_dir.mkdir(parents=True)
    _write_self_study_extraction(
        extraction_dir / "self_study_extraction.json",
        lesson_id=lesson_id,
        self_study_id="1",
        candidate_id="candidate-1-001",
        label="Bag-of-Words count vectors",
        evidence_type="source_body",
    )
    _write_extraction_set(
        source_dir / "self_study_extraction_set.json",
        artifact_path=(
            f"lessons/{lesson_id}/self_studies/1/"
            "extraction_passes/pro-thinking/self_study_extraction.json"
        ),
        lesson_id=lesson_id,
        self_study_id="1",
    )
    for index in range(2, 5):
        metadata_dir = run_dir / "lessons" / lesson_id / "self_studies" / str(index)
        metadata_dir.mkdir(parents=True)
        _write_metadata_only_extraction(
            metadata_dir / "metadata_only_extraction.json",
            lesson_id=lesson_id,
            self_study_id=str(index),
            label=f"Metadata-only BoW hint {index}",
        )


def _two_step_lesson_reconciliation_model_call(calls):
    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_candidate_clustering":
            model_input = inputs["lesson_candidate_clustering_input.json"]
            calls.append({"route": route.alias, "stage_name": stage_name})
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Bag-of-Words representation",
                            "rationale": "Both candidates describe Bag-of-Words as a lesson idea.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_cluster_evaluation":
            model_input = inputs["cluster_evaluation_input.json"]
            calls.append({"route": route.alias, "stage_name": stage_name})
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "lr001",
                            "label": "Bag-of-Words count-vector representation",
                            "description": "Bag-of-Words represents text through word-count vectors.",
                            "coverage_criteria": ["Student can explain how BoW creates a count vector."],
                            "source_candidate_ids": model_input["input_candidate_ids"],
                            "merge_rationale": "The cluster describes one lesson idea.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": model_input["input_candidate_ids"][0],
                            "status": "used_in",
                            "accepted_ids": ["lr001"],
                        },
                        {
                            "candidate_id": model_input["input_candidate_ids"][1],
                            "status": "merged_into",
                            "merged_into": "lr001",
                            "explanation": "The metadata-only candidate is represented by the source-backed concept.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    return model_call


def _write_source_ledger(run_dir, *, lesson_id):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": lesson_id, "title": "Bag of Words"}],
                "self_studies": [
                    {
                        "self_study_id": "22",
                        "lesson_id": lesson_id,
                        "source_body_status": "usable_source_body",
                        "workbook_metadata": {"title": "Bag-of-Words count vectors"},
                    },
                    {
                        "self_study_id": "64",
                        "lesson_id": lesson_id,
                        "source_body_status": "unavailable_source_body",
                        "workbook_metadata": {"title": "Blocked BoW source"},
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_self_study_extraction(path, *, lesson_id, self_study_id, candidate_id, label, evidence_type):
    path.write_text(
        json.dumps(
            {
                "artifact_type": "self_study_extraction",
                "schema_version": "self_study_extraction.v0",
                "model_route": "Pro Thinking",
                "lesson_id": lesson_id,
                "self_study_id": self_study_id,
                "source_name": label,
                "candidate_concepts": [
                    {
                        "candidate_id": candidate_id,
                        "label": label,
                        "description": "Bag-of-Words represents text as word-count vectors.",
                        "coverage_criteria": ["Student can explain count-vector representation."],
                        "source_roles": ["explaining"],
                        "source_anchors": [{"kind": "markdown_heading", "locator": "BoW"}],
                        "extraction_reason": {
                            "source_grounded_rationale": "The source defines BoW as count vectors.",
                            "granularity_rationale": "This is one checkable idea.",
                        },
                        "evidence_type": evidence_type,
                    }
                ],
                "source_local_connector_candidates": [],
                "summary": {"candidate_count": 1, "source_local_connector_candidate_count": 0},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_extraction_set(path, *, artifact_path, lesson_id, self_study_id):
    path.write_text(
        json.dumps(
            {
                "artifact_type": "self_study_extraction_set",
                "schema_version": "self_study_extraction_set.v0",
                "lesson_id": lesson_id,
                "self_study_id": self_study_id,
                "extraction_passes": [
                    {
                        "pass_id": "pro-thinking",
                        "route_alias": "Pro Thinking",
                        "artifact_path": artifact_path,
                        "candidate_count": 1,
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_metadata_only_extraction(path, *, lesson_id, self_study_id="64", label="Blocked BoW source"):
    path.write_text(
        json.dumps(
            {
                "artifact_type": "metadata_only_extraction",
                "schema_version": "metadata_only_extraction.v0",
                "model_route": "Pro",
                "lesson_id": lesson_id,
                "self_study_id": self_study_id,
                "source_name": label,
                "candidate_concepts": [
                    {
                        "candidate_id": f"metadata-candidate-{self_study_id}-001",
                        "label": label,
                        "description": f"Workbook metadata points to {label}.",
                        "coverage_criteria": ["Student can explain the metadata-backed idea."],
                        "evidence_type": "workbook_metadata",
                        "metadata_anchors": [{"kind": "workbook_title", "locator": "Title"}],
                        "extraction_reason": {
                            "metadata_grounded_rationale": "The workbook title names Bag-of-Words.",
                            "granularity_rationale": "This is one metadata-backed idea.",
                        },
                    }
                ],
                "summary": {"candidate_count": 1},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
