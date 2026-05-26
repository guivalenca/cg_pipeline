import json
import threading

from concept_graph_creation.cli import run_pipeline
from concept_graph_creation.stages.lesson_segmentation import run_lesson_segmentation_phase


def test_lesson_segmentation_plans_orders_and_audits_one_lesson(tmp_path):
    run_dir = tmp_path / "run"
    _write_source_ledger(
        run_dir,
        lessons=[
            {
                "lesson_id": "lesson-bow",
                "title": "Representacao de palavras e Bag of Words",
                "date": "2026-05-05",
            }
        ],
    )
    _write_subject_merge(
        run_dir,
        concepts=[
            _concept(
                "concept_tokenization",
                "Tokenizacao em PLN",
                "conceptual",
                "Dividir texto em unidades processaveis.",
                ["Student can explain why tokenization is not just splitting by spaces."],
                "lesson-bow",
            ),
            _concept(
                "concept_counts",
                "Contagem de tokens",
                "procedural",
                "Contar ocorrencias de tokens em um corpus.",
                ["Student can count token occurrences in a tiny corpus."],
                "lesson-bow",
            ),
            _concept(
                "concept_bow",
                "Bag of Words",
                "conceptual",
                "Representar documentos por frequencias de termos.",
                ["Student can explain what information Bag of Words preserves and discards."],
                "lesson-bow",
            ),
        ],
    )
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        calls.append({"stage_name": stage_name, "route": route.alias})
        if stage_name == "lesson_segment_planner":
            model_input = inputs["lesson_segment_planner_input.json"]
            assert model_input["prompt_path"] == "lesson_segmentation/segment_planner.md"
            assert model_input["lesson"] == {
                "lesson_id": "lesson-bow",
                "title": "Representacao de palavras e Bag of Words",
            }
            assert "date" not in model_input["lesson"]
            assert "lesson_order" not in model_input["lesson"]
            assert [concept["concept_id"] for concept in model_input["concepts"]] == [
                "concept_tokenization",
                "concept_counts",
                "concept_bow",
            ]
            assert "knowledge_type" not in model_input["concepts"][0]
            assert model_input["concepts"][0]["coverage_criteria"] == [
                "Student can explain why tokenization is not just splitting by spaces."
            ]
            assert "source_flow_hints" not in model_input
            return json.dumps(
                {
                    "segments": [
                        {
                            "label": "Tokenization and token counts",
                            "concept_ids": ["concept_counts", "concept_tokenization"],
                        },
                        {
                            "label": "Bag of Words representation",
                            "concept_ids": ["concept_bow"],
                        },
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_segment_concept_orderer":
            model_input = inputs["lesson_segment_concept_orderer_input.json"]
            assert model_input["prompt_path"] == "lesson_segmentation/concept_orderer.md"
            assert [segment["label"] for segment in model_input["segments"]] == [
                "Tokenization and token counts",
                "Bag of Words representation",
            ]
            return json.dumps(
                {
                    "segments": [
                        {
                            "label": "Tokenization and token counts",
                            "concept_ids": ["concept_tokenization", "concept_counts"],
                        },
                        {
                            "label": "Bag of Words representation",
                            "concept_ids": ["concept_bow"],
                        },
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_segmentation_quality_audit":
            model_input = inputs["lesson_segmentation_quality_audit_input.json"]
            assert model_input["prompt_path"] == "lesson_segmentation/quality_audit.md"
            assert model_input["lesson"] == {
                "lesson_id": "lesson-bow",
                "title": "Representacao de palavras e Bag of Words",
            }
            assert "neighbor_lessons" not in model_input
            return json.dumps(
                {
                    "scores": {
                        "segment_coherence": 3,
                        "segment_order": 3,
                        "concept_order": 3,
                        "label_quality": 3,
                        "focus_window_size": 3,
                    },
                    "reliability": "reliable",
                    "findings": [],
                    "repair_instructions": [],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_segmentation_phase(run_dir=run_dir, model_call=model_call)

    artifact = json.loads((run_dir / "lessons" / "lesson-bow" / "lesson_segments.json").read_text(encoding="utf-8"))
    assert calls == [
        {"stage_name": "lesson_segment_planner", "route": "Pro Thinking"},
        {"stage_name": "lesson_segment_concept_orderer", "route": "Pro"},
        {"stage_name": "lesson_segmentation_quality_audit", "route": "Pro Thinking"},
    ]
    assert result["summary"] == {
        "lesson_count": 1,
        "segmented_lesson_count": 1,
        "segment_count": 2,
        "repair_count": 0,
        "unrepaired_count": 0,
        "skipped_no_concept_lesson_count": 0,
    }
    assert artifact["artifact_type"] == "lesson_segments"
    assert artifact["schema_version"] == "lesson_segments.v0"
    assert artifact["lesson_id"] == "lesson-bow"
    assert artifact["segments"] == [
        {
            "segment_id": "segment_001",
            "label": "Tokenization and token counts",
            "instructional_role": "teach",
            "concept_ids": ["concept_tokenization", "concept_counts"],
        },
        {
            "segment_id": "segment_002",
            "label": "Bag of Words representation",
            "instructional_role": "teach",
            "concept_ids": ["concept_bow"],
        },
    ]
    assert "quality_audit" not in artifact


def test_lesson_segmentation_repairs_rejected_audit_with_pro_and_reaudits(tmp_path):
    run_dir = tmp_path / "run"
    _write_source_ledger(
        run_dir,
        lessons=[{"lesson_id": "lesson-nlp", "title": "Introducao ao PLN"}],
    )
    _write_subject_merge(
        run_dir,
        concepts=[
            _concept("concept_nlp", "Definicao de PLN", "conceptual", "Definir PLN.", ["Student can define NLP."], "lesson-nlp"),
            _concept(
                "concept_tokens",
                "Tokenizacao",
                "conceptual",
                "Dividir texto em tokens.",
                ["Student can explain tokenization."],
                "lesson-nlp",
            ),
            _concept(
                "concept_stopwords",
                "Stopwords",
                "factual",
                "Reconhecer palavras comuns removidas em preprocessamento.",
                ["Student can identify why stopwords may be removed."],
                "lesson-nlp",
            ),
            _concept(
                "concept_stemming",
                "Stemming",
                "procedural",
                "Reduzir palavras a radicais.",
                ["Student can apply a simple stemming example."],
                "lesson-nlp",
            ),
            _concept(
                "concept_lemmatization",
                "Lematizacao",
                "procedural",
                "Reduzir palavras a lemas.",
                ["Student can distinguish lemmatization from stemming."],
                "lesson-nlp",
            ),
        ],
    )
    audit_calls = 0
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal audit_calls
        calls.append({"stage_name": stage_name, "route": route.alias})
        if stage_name == "lesson_segment_planner":
            return json.dumps(
                {
                    "segments": [
                        {
                            "label": "NLP preprocessing",
                            "concept_ids": [
                                "concept_nlp",
                                "concept_tokens",
                                "concept_stopwords",
                                "concept_stemming",
                                "concept_lemmatization",
                            ],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_segment_concept_orderer":
            return json.dumps(inputs["lesson_segment_concept_orderer_input.json"], ensure_ascii=False)
        if stage_name == "lesson_segmentation_quality_audit":
            audit_calls += 1
            if audit_calls == 1:
                return json.dumps(
                    {
                        "scores": {
                            "segment_coherence": 1,
                            "segment_order": 2,
                            "concept_order": 2,
                            "label_quality": 2,
                            "focus_window_size": 0,
                        },
                        "reliability": "repair_required",
                        "findings": [
                            {
                                "issue": "segment_too_large",
                                "segment_labels": ["NLP preprocessing"],
                                "concept_ids": [
                                    "concept_nlp",
                                    "concept_tokens",
                                    "concept_stopwords",
                                    "concept_stemming",
                                    "concept_lemmatization",
                                ],
                                "explanation": "One five-Concept Segment is too broad.",
                            }
                        ],
                        "repair_instructions": [
                            "Split the broad preprocessing Segment into an overview and a transformations Segment."
                        ],
                    },
                    ensure_ascii=False,
                )
            return json.dumps(
                {
                    "scores": {
                        "segment_coherence": 3,
                        "segment_order": 3,
                        "concept_order": 3,
                        "label_quality": 3,
                        "focus_window_size": 3,
                    },
                    "reliability": "reliable",
                    "findings": [],
                    "repair_instructions": [],
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_segmentation_quality_repair":
            model_input = inputs["lesson_segmentation_quality_repair_input.json"]
            assert model_input["prompt_path"] == "lesson_segmentation/quality_repair.md"
            assert model_input["quality_audit"]["reliability"] == "repair_required"
            return json.dumps(
                {
                    "segments": [
                        {
                            "label": "NLP and token preparation",
                            "concept_ids": ["concept_nlp", "concept_tokens", "concept_stopwords"],
                        },
                        {
                            "label": "Word normalization transforms",
                            "concept_ids": ["concept_stemming", "concept_lemmatization"],
                        },
                    ]
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_segmentation_phase(run_dir=run_dir, model_call=model_call)

    artifact = json.loads((run_dir / "lessons" / "lesson-nlp" / "lesson_segments.json").read_text(encoding="utf-8"))
    assert calls == [
        {"stage_name": "lesson_segment_planner", "route": "Pro Thinking"},
        {"stage_name": "lesson_segment_concept_orderer", "route": "Pro"},
        {"stage_name": "lesson_segmentation_quality_audit", "route": "Pro Thinking"},
        {"stage_name": "lesson_segmentation_quality_repair", "route": "Pro"},
        {"stage_name": "lesson_segmentation_quality_audit", "route": "Pro Thinking"},
    ]
    assert result["summary"]["repair_count"] == 1
    assert result["summary"]["unrepaired_count"] == 0
    assert artifact["status"] == "reliable"
    assert artifact["repaired"] is True
    assert artifact["segments"] == [
        {
            "segment_id": "segment_001",
            "label": "NLP and token preparation",
            "instructional_role": "teach",
            "concept_ids": ["concept_nlp", "concept_tokens", "concept_stopwords"],
        },
        {
            "segment_id": "segment_002",
            "label": "Word normalization transforms",
            "instructional_role": "teach",
            "concept_ids": ["concept_stemming", "concept_lemmatization"],
        },
    ]


def test_pipeline_runs_phase_7_and_reports_lesson_segmentation_summary(tmp_path):
    cg_pipeline_root = tmp_path / "cg_pipeline"
    run_dir = tmp_path / "run"
    _write_source_ledger(
        run_dir,
        lessons=[{"lesson_id": "lesson-bow", "title": "Bag of Words"}],
    )
    _write_subject_merge(
        run_dir,
        concepts=[
            _concept(
                "concept_tokenization",
                "Tokenizacao",
                "conceptual",
                "Dividir texto em tokens.",
                ["Student can explain tokenization."],
                "lesson-bow",
            ),
            _concept(
                "concept_bow",
                "Bag of Words",
                "conceptual",
                "Representar documentos por contagens.",
                ["Student can explain count-vector representation."],
                "lesson-bow",
            ),
        ],
    )

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name in {"lesson_segment_planner", "lesson_segment_concept_orderer"}:
            return json.dumps(
                {
                    "segments": [
                        {
                            "label": "Tokenization into Bag of Words",
                            "concept_ids": ["concept_tokenization", "concept_bow"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "lesson_segmentation_quality_audit":
            return json.dumps(
                {
                    "scores": {
                        "segment_coherence": 3,
                        "segment_order": 3,
                        "concept_order": 3,
                        "label_quality": 3,
                        "focus_window_size": 3,
                    },
                    "reliability": "reliable",
                    "findings": [],
                    "repair_instructions": [],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_pipeline(
        cg_pipeline_root=cg_pipeline_root,
        run_dir=run_dir,
        subject_sheet="COM",
        include_validation_failure_demo=False,
        clean_run_dir=False,
        phases=["phase-7"],
        lesson_segmentation_model_call=model_call,
    )

    assert result["lesson_segmentation"]["summary"]["segment_count"] == 1
    assert result["manual_output"]["lesson_segmentation_summary"] == {
        "lesson_count": 1,
        "segmented_lesson_count": 1,
        "segment_count": 1,
        "repair_count": 0,
        "unrepaired_count": 0,
        "skipped_no_concept_lesson_count": 0,
    }


def test_lesson_segmentation_runs_lessons_concurrently(tmp_path):
    run_dir = tmp_path / "run"
    _write_source_ledger(
        run_dir,
        lessons=[
            {"lesson_id": "lesson-a", "title": "Lesson A"},
            {"lesson_id": "lesson-b", "title": "Lesson B"},
        ],
    )
    _write_subject_merge(
        run_dir,
        concepts=[
            _concept("concept_a", "Concept A", "conceptual", "Teach A.", ["Student can explain A."], "lesson-a"),
            _concept("concept_b", "Concept B", "conceptual", "Teach B.", ["Student can explain B."], "lesson-b"),
        ],
    )
    planner_barrier = threading.Barrier(2, timeout=2)

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "lesson_segment_planner":
            planner_barrier.wait()
            model_input = inputs["lesson_segment_planner_input.json"]
            concept_id = model_input["concepts"][0]["concept_id"]
            return json.dumps({"segments": [{"label": model_input["concepts"][0]["label"], "concept_ids": [concept_id]}]})
        if stage_name == "lesson_segment_concept_orderer":
            model_input = inputs["lesson_segment_concept_orderer_input.json"]
            return json.dumps({"segments": model_input["segments"]})
        if stage_name == "lesson_segmentation_quality_audit":
            return json.dumps(
                {
                    "scores": {
                        "segment_coherence": 3,
                        "segment_order": 3,
                        "concept_order": 3,
                        "label_quality": 3,
                        "focus_window_size": 3,
                    },
                    "reliability": "reliable",
                    "findings": [],
                    "repair_instructions": [],
                }
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_segmentation_phase(run_dir=run_dir, model_call=model_call, concurrency=2)

    assert result["summary"]["lesson_count"] == 2
    assert result["summary"]["segment_count"] == 2
    assert (run_dir / "lessons" / "lesson-a" / "lesson_segments.json").is_file()
    assert (run_dir / "lessons" / "lesson-b" / "lesson_segments.json").is_file()


def test_lesson_segmentation_allows_concept_without_knowledge_type(tmp_path):
    run_dir = tmp_path / "run"
    _write_source_ledger(run_dir, lessons=[{"lesson_id": "lesson-bow", "title": "Bag of Words"}])
    concept = _concept(
        "concept_bow",
        "Bag of Words",
        "conceptual",
        "Representar documentos por contagens.",
        ["Student can explain count-vector representation."],
        "lesson-bow",
    )
    concept.pop("knowledge_type")
    _write_subject_merge(run_dir, concepts=[concept])

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name in {"lesson_segment_planner", "lesson_segment_concept_orderer"}:
            return json.dumps(
                {"segments": [{"label": "Bag of Words", "concept_ids": ["concept_bow"]}]},
                ensure_ascii=False,
            )
        if stage_name == "lesson_segmentation_quality_audit":
            return json.dumps(
                {
                    "scores": {
                        "segment_coherence": 3,
                        "segment_order": 3,
                        "concept_order": 3,
                        "label_quality": 3,
                        "focus_window_size": 3,
                    },
                    "reliability": "reliable",
                    "findings": [],
                    "repair_instructions": [],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_lesson_segmentation_phase(run_dir=run_dir, model_call=model_call)

    assert result["summary"]["segment_count"] == 1


def _write_source_ledger(run_dir, *, lessons):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "schema_version": "source_ledger.v0",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "computacao",
                "lessons": lessons,
                "self_studies": [],
                "summary": {"lesson_count": len(lessons)},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_subject_merge(run_dir, *, concepts):
    (run_dir / "subject_merge.json").write_text(
        json.dumps(
            {
                "artifact_type": "subject_merge",
                "schema_version": "subject_merge.v0",
                "source_artifact": "source_ledger.json",
                "concepts": concepts,
                "summary": {"concept_count": len(concepts)},
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _concept(concept_id, label, knowledge_type, description, coverage_criteria, lesson_id):
    return {
        "concept_id": concept_id,
        "label": label,
        "knowledge_type": knowledge_type,
        "description": description,
        "coverage_criteria": coverage_criteria,
        "occurrences": [{"lesson": {"lesson_id": lesson_id, "title": "Lesson"}}],
    }
