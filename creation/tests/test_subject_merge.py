import json

import pytest

from concept_graph_creation.runtime.stage_runner import StageBlockedError
from concept_graph_creation.stages.subject_merge import run_subject_merge_phase
from concept_graph_creation.stages.subject_merge import run_subject_merge_phase5b
from concept_graph_creation.stages.subject_merge import validate_subject_merge_decision


def test_subject_merge_two_round_clustering_merges_nlp_and_passthroughs_singletons(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-2026-04-27-introdu-o-ao-processamento-de-linguagem-natural",
                "title": "Introducao ao Processamento de Linguagem Natural",
                "candidates": [
                    _candidate(
                        "Natural Language Processing (NLP) Definition",
                        "NLP is a branch of AI that enables machines to read, understand, and derive meaning from human languages, combining linguistics and computer science.",
                        ["Define NLP and its two foundational fields: linguistics and computer science."],
                    ),
                    _candidate(
                        "Text Preprocessing: Segmentation, Tokenization, and Stop Words",
                        "The initial NLP steps: breaking documents into sentences, sentences into words, and removing common stop words.",
                        ["Explain segmentation, tokenization, and the role of stop words in NLP preprocessing."],
                    ),
                ],
            },
            {
                "lesson_id": "lesson-2026-04-29-processamento-de-texto-m-tricas-e-t-cnicas",
                "title": "Processamento de Texto",
                "candidates": [
                    _candidate(
                        "NLP Definition and Suitability Criteria",
                        "Natural Language Processing (NLP) is a branch of artificial intelligence that uses machine learning to process and interpret texts and data.",
                        ["Define NLP as presented in the lesson."],
                    ),
                ],
            },
        ],
    )
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        calls.append({"route": route.alias, "stage_name": stage_name})
        if stage_name == "subject_merge_area_partition":
            model_input = inputs["subject_merge_area_partition_input.json"]
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "area_001",
                            "label": "NLP foundations",
                            "rationale": "Introductory NLP concepts.",
                            "candidate_ids": model_input["input_candidate_ids"],
                        }
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_merge_fine_clustering":
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "What is NLP",
                            "rationale": "These candidates define NLP at the same level.",
                            "candidate_ids": ["lr001_001", "lr002_001"],
                        },
                        {
                            "id": "cluster_002",
                            "label": "Text preprocessing sequence",
                            "rationale": "Compound preprocessing concept; leave standalone.",
                            "candidate_ids": ["lr001_002"],
                        },
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_cluster_evaluation":
            model_input = inputs["subject_cluster_evaluation_input.json"]
            assert model_input["input_candidate_ids"] == ["lr001_001", "lr002_001"]
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "sm001",
                            "label": "Natural Language Processing (NLP) Definition",
                            "description": "NLP is the field of enabling computers to process and understand human language.",
                            "coverage_criteria": ["Student can define NLP as computational processing of human language."],
                            "source_candidate_ids": ["lr001_001", "lr002_001"],
                            "merge_rationale": "Both lessons ask for the same teachable definition of NLP.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["sm001"]},
                        {
                            "candidate_id": "lr002_001",
                            "status": "merged_into",
                            "merged_into": "sm001",
                            "explanation": "Same definition at the same level.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_subject_merge_phase(run_dir=run_dir, model_call=model_call, phase5b_enabled=False)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    clusters = json.loads((run_dir / "subject_merge_candidate_clusters.json").read_text(encoding="utf-8"))
    assigned_ids = [candidate_id for cluster in clusters["clusters"] for candidate_id in cluster["candidate_ids"]]
    nlp_concept = _concept_by_label(artifact, "Natural Language Processing (NLP) Definition")
    preprocessing = _concept_by_label(artifact, "Text Preprocessing: Segmentation, Tokenization, and Stop Words")

    assert calls == [
        {"route": "Pro Thinking", "stage_name": "subject_merge_area_partition"},
        {"route": "Pro Thinking", "stage_name": "subject_merge_fine_clustering"},
        {"route": "Pro Thinking", "stage_name": "subject_cluster_evaluation"},
    ]
    assert assigned_ids == ["lr001_001", "lr002_001", "lr001_002"]
    assert result["summary"]["concept_count"] == 2
    assert result["summary"]["review_candidate_count"] == 0
    assert result["summary"]["pruned_candidate_count"] == 0
    assert nlp_concept["source_candidate_ids"] == ["lr001_001", "lr002_001"]
    assert [item["lesson"]["lesson_id"] for item in nlp_concept["occurrences"]] == [
        "lesson-2026-04-27-introdu-o-ao-processamento-de-linguagem-natural",
        "lesson-2026-04-29-processamento-de-texto-m-tricas-e-t-cnicas",
    ]
    assert all(item["source_candidate_ids"] for item in nlp_concept["occurrences"])
    assert preprocessing["source_candidate_ids"] == ["lr001_002"]
    assert preprocessing["candidate_assignment_status"] == "used_in"


def test_subject_merge_uses_task_specific_prompts_and_pro_thinking_routes(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [
                    _candidate("Shared concept", "Defines one idea.", ["Define the idea."]),
                    _candidate("Standalone concept", "Defines another idea.", ["Define the other idea."]),
                ],
            },
            {
                "lesson_id": "lesson-b",
                "title": "B",
                "candidates": [_candidate("Shared concept variant", "Defines the same idea.", ["Define the idea."])],
            },
        ],
    )
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "subject_merge_area_partition":
            model_input = inputs["subject_merge_area_partition_input.json"]
            calls.append((stage_name, route.alias, model_input["prompt_path"]))
            return _all_in_one_cluster_json(model_input, cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            model_input = inputs["subject_merge_fine_clustering_input.json"]
            calls.append((stage_name, route.alias, model_input["prompt_path"]))
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "Shared concept",
                            "rationale": "Same idea.",
                            "candidate_ids": ["lr001_001", "lr002_001"],
                        },
                        {
                            "id": "cluster_002",
                            "label": "Standalone concept",
                            "rationale": "Different idea.",
                            "candidate_ids": ["lr001_002"],
                        },
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_cluster_evaluation":
            model_input = inputs["subject_cluster_evaluation_input.json"]
            calls.append((stage_name, route.alias, model_input["prompt_path"]))
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "sm001",
                            "label": "Shared concept",
                            "description": "The same idea.",
                            "coverage_criteria": ["Define the idea."],
                            "source_candidate_ids": model_input["input_candidate_ids"],
                            "merge_rationale": "Same teachable idea.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": model_input["input_candidate_ids"][0], "status": "used_in", "accepted_ids": ["sm001"]},
                        {
                            "candidate_id": model_input["input_candidate_ids"][1],
                            "status": "merged_into",
                            "merged_into": "sm001",
                            "explanation": "Same teachable idea.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_subject_merge_phase(run_dir=run_dir, model_call=model_call, phase5b_enabled=False)

    assert calls == [
        ("subject_merge_area_partition", "Pro Thinking", "subject_merge/area_partition.md"),
        ("subject_merge_fine_clustering", "Pro Thinking", "subject_merge/fine_clustering.md"),
        ("subject_cluster_evaluation", "Pro Thinking", "subject_merge/cluster_evaluation.md"),
    ]


def test_subject_merge_evaluates_each_candidate_cluster_in_its_own_call(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [
                    _candidate("First duplicate", "Defines the first idea.", ["Define first idea."]),
                    _candidate("Second duplicate", "Defines the second idea.", ["Define second idea."]),
                ],
            },
            {
                "lesson_id": "lesson-b",
                "title": "B",
                "candidates": [
                    _candidate("First duplicate variant", "Defines the first idea.", ["Define first idea."]),
                    _candidate("Second duplicate variant", "Defines the second idea.", ["Define second idea."]),
                ],
            },
        ],
    )
    evaluation_inputs = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "subject_merge_area_partition":
            return _all_in_one_cluster_json(inputs["subject_merge_area_partition_input.json"], cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": "cluster_001",
                            "label": "First duplicate",
                            "rationale": "Same first idea.",
                            "candidate_ids": ["lr001_001", "lr002_001"],
                        },
                        {
                            "id": "cluster_002",
                            "label": "Second duplicate",
                            "rationale": "Same second idea.",
                            "candidate_ids": ["lr001_002", "lr002_002"],
                        },
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_cluster_evaluation":
            model_input = inputs["subject_cluster_evaluation_input.json"]
            evaluation_inputs.append(model_input["input_candidate_ids"])
            accepted_id = "sm001"
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": accepted_id,
                            "label": model_input["candidates"][0]["label"],
                            "description": "Merged same-level duplicate.",
                            "coverage_criteria": ["Explain the same idea."],
                            "source_candidate_ids": model_input["input_candidate_ids"],
                            "merge_rationale": "Same teachable idea.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": model_input["input_candidate_ids"][0], "status": "used_in", "accepted_ids": [accepted_id]},
                        {
                            "candidate_id": model_input["input_candidate_ids"][1],
                            "status": "merged_into",
                            "merged_into": accepted_id,
                            "explanation": "Same teachable idea.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_subject_merge_phase(run_dir=run_dir, model_call=model_call, phase5b_enabled=False)

    assert sorted(evaluation_inputs) == [["lr001_001", "lr002_001"], ["lr001_002", "lr002_002"]]
    assert result["stage_counts"]["cluster_evaluation_count"] == 2
    assert result["evaluation_batch_size"] == 1


def test_subject_merge_routes_contextual_repairs_to_pro_thinking_by_default(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [
                    _candidate("Shared concept", "Defines one idea.", ["Define the idea."]),
                    _candidate("Shared concept variant", "Defines the same idea.", ["Define the idea."]),
                ],
            }
        ],
    )
    repair_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "subject_merge_area_partition":
            return _all_in_one_cluster_json(inputs["subject_merge_area_partition_input.json"], cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_cluster_evaluation" and repair_context is None:
            model_input = inputs["subject_cluster_evaluation_input.json"]
            return json.dumps(
                {
                    "accepted_concepts": [],
                    "candidate_assignments": [
                        {
                            "candidate_id": model_input["input_candidate_ids"][0],
                            "status": "review",
                            "explanation": "Fixture forces contextual repair.",
                        }
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_cluster_evaluation":
            repair_calls.append((route.alias, repair_context["repair_type"]))
            model_input = inputs["subject_cluster_evaluation_input.json"]
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "sm001",
                            "label": "Shared concept",
                            "description": "Defines one idea.",
                            "coverage_criteria": ["Define the idea."],
                            "source_candidate_ids": model_input["input_candidate_ids"],
                            "merge_rationale": "Same teachable idea.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": model_input["input_candidate_ids"][0], "status": "used_in", "accepted_ids": ["sm001"]},
                        {
                            "candidate_id": model_input["input_candidate_ids"][1],
                            "status": "merged_into",
                            "merged_into": "sm001",
                            "explanation": "Same teachable idea.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_subject_merge_phase(run_dir=run_dir, model_call=model_call, phase5b_enabled=False)

    assert repair_calls == [("Pro Thinking", "contextual_repair")]


def test_subject_merge_keeps_deepening_and_doubt_as_standalone_without_review_or_pruned(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-2026-05-05-representa-o-de-palavras-e-bag-of-words-bow",
                "title": "Bag of Words",
                "candidates": [
                    _candidate(
                        "Bag-of-Words Model Definition",
                        "The bag-of-words model converts documents into fixed-length vectors by counting word occurrences.",
                        ["Define the BOW model and explain how it represents text as word count vectors."],
                    )
                ],
            },
            {
                "lesson_id": "lesson-2026-05-11-nltk-bow-e-naive-bayes-para-an-lise-de-conte-do",
                "title": "NLTK BoW e Naive Bayes",
                "candidates": [
                    _candidate(
                        "Bag of Words with CountVectorizer",
                        "Converting preprocessed text into a numerical matrix of token counts using scikit-learn's CountVectorizer.",
                        ["Transform a list of texts into a BoW matrix using CountVectorizer."],
                        roles=["introducing", "demonstrating"],
                    )
                ],
            },
        ],
    )

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "subject_merge_area_partition":
            return _all_in_one_cluster_json(inputs["subject_merge_area_partition_input.json"], cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_cluster_evaluation":
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "sm001",
                            "label": "Bag-of-Words Model Definition",
                            "description": "BOW represents text as word-count vectors.",
                            "coverage_criteria": ["Student can define BOW as count-vector text representation."],
                            "source_candidate_ids": ["lr001_001"],
                            "merge_rationale": "Definition-level concept.",
                        },
                        {
                            "id": "sm002",
                            "label": "Bag of Words with CountVectorizer",
                            "description": "Using scikit-learn CountVectorizer to implement BOW matrices.",
                            "coverage_criteria": ["Student can transform text with CountVectorizer."],
                            "source_candidate_ids": ["lr002_001"],
                            "merge_rationale": "Implementation behavior must remain separate from the definition.",
                        },
                    ],
                    "candidate_assignments": [
                        {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["sm001"]},
                        {"candidate_id": "lr002_001", "status": "used_in", "accepted_ids": ["sm002"]},
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_subject_merge_phase(run_dir=run_dir, model_call=model_call, phase5b_enabled=False)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    statuses = [assignment["status"] for assignment in artifact["candidate_assignments"]]
    assert artifact["summary"]["concept_count"] == 2
    assert statuses == ["used_in", "used_in"]
    assert "review" not in statuses
    assert "pruned" not in statuses


def test_subject_merge_merges_cross_language_same_concepts(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-2026-05-12-vetores-multidimensionais-word2vec-e-gensim",
                "title": "Word2Vec e Gensim",
                "candidates": [
                    _candidate(
                        "Arquiteturas do Word2Vec: CBOW e Skip-Gram",
                        "Word2Vec possui duas arquiteturas principais: CBOW preve a palavra central a partir do contexto, enquanto Skip-Gram preve o contexto a partir da palavra central.",
                        ["Diferencie CBOW de Skip-Gram."],
                    )
                ],
            },
            {
                "lesson_id": "lesson-2026-05-26-outras-t-cnicas-word-embedding-tf-tf-idf-e-lsa",
                "title": "Word embeddings",
                "candidates": [
                    _candidate(
                        "Word2vec: CBOW and Skip-gram Architectures",
                        "CBOW predicts a target word from context, while Skip-gram predicts context words from a target word.",
                        ["Differentiate CBOW and Skip-gram and state what each predicts."],
                    )
                ],
            },
        ],
    )

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "subject_merge_area_partition":
            return _all_in_one_cluster_json(inputs["subject_merge_area_partition_input.json"], cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_cluster_evaluation":
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "sm001",
                            "label": "Word2Vec CBOW and Skip-gram Architectures",
                            "description": "CBOW predicts a target from context; Skip-gram predicts context from a target.",
                            "coverage_criteria": ["Student can distinguish CBOW and Skip-gram prediction directions."],
                            "source_candidate_ids": ["lr001_001", "lr002_001"],
                            "merge_rationale": "Language differs, but the teachable idea and level are the same.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["sm001"]},
                        {
                            "candidate_id": "lr002_001",
                            "status": "merged_into",
                            "merged_into": "sm001",
                            "explanation": "English restatement of the Portuguese Word2Vec architecture concept.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_subject_merge_phase(run_dir=run_dir, model_call=model_call, phase5b_enabled=False)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    concept = artifact["concepts"][0]
    assert result["summary"]["concept_count"] == 1
    assert concept["source_candidate_ids"] == ["lr001_001", "lr002_001"]
    assert len(concept["occurrences"]) == 2


def test_subject_merge_validator_rejects_review_and_pruned_statuses():
    registry = {
        "scope_id": "si-mod6-COM",
        "candidates": {"lr001_001": {}, "lr002_001": {}},
    }
    decision = {
        "artifact_type": "semantic_reduce_decision",
        "schema_version": "semantic_reduce_decision.v0",
        "scope_id": "si-mod6-COM",
        "input_candidate_ids": ["lr001_001", "lr002_001"],
        "accepted": [
            {
                "id": "sm001",
                "label": "One",
                "description": "One concept.",
                "coverage_criteria": ["Explain one."],
                "source_candidate_ids": ["lr001_001"],
                "merge_rationale": "Accepted.",
            }
        ],
        "accepted_concepts": [
            {
                "id": "sm001",
                "label": "One",
                "description": "One concept.",
                "coverage_criteria": ["Explain one."],
                "source_candidate_ids": ["lr001_001"],
                "merge_rationale": "Accepted.",
            }
        ],
        "candidate_assignments": [
            {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["sm001"]},
            {"candidate_id": "lr002_001", "status": "review", "explanation": "Not allowed."},
        ],
        "pruned": [],
        "summary": {
            "input_candidate_count": 2,
            "accepted_count": 1,
            "pruned_count": 0,
            "candidate_assignment_count": 2,
            "review_count": 1,
        },
    }

    review_errors = validate_subject_merge_decision(decision, registry)
    decision["candidate_assignments"][1] = {
        "candidate_id": "lr002_001",
        "status": "pruned",
        "reason": "near_duplicate",
        "explanation": "Not allowed.",
    }
    decision["pruned"] = [{"candidate_id": "lr002_001", "reason": "near_duplicate", "explanation": "Not allowed."}]
    decision["summary"]["pruned_count"] = 1
    decision["summary"]["review_count"] = 0

    pruned_errors = validate_subject_merge_decision(decision, registry)

    assert any("must not use review" in error for error in review_errors)
    assert any("must not use pruned" in error for error in pruned_errors)


def test_subject_merge_phase5b_repairs_over_merged_definition_and_implementation(tmp_path):
    run_dir = tmp_path / "run"
    _write_bow_definition_and_countvectorizer_inputs(run_dir)
    repair_calls = []
    audit_call_count = 0

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal audit_call_count
        if stage_name == "subject_merge_area_partition":
            return _all_in_one_cluster_json(inputs["subject_merge_area_partition_input.json"], cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_cluster_evaluation":
            return _merged_bow_definition_and_countvectorizer()
        if stage_name == "subject_merge_quality_audit":
            audit_call_count += 1
            if audit_call_count == 1:
                return _quality_audit_json(
                    flags=["over_merged_group", "granularity_violation"],
                    repair_plan=[
                        {
                            "repair_reason": "over_merged_group",
                            "candidate_ids": ["lr001_001", "lr002_001"],
                            "explanation": "Definition and implementation were collapsed.",
                        }
                    ],
                )
            return _quality_audit_json()
        if stage_name == "subject_merge_quality_repair":
            model_input = inputs["subject_merge_quality_repair_input.json"]
            repair_calls.append(
                {
                    "route": route.alias,
                    "prompt_path": model_input["prompt_path"],
                    "repair_reason": model_input["repair_reason"],
                    "target_candidate_ids": model_input["target_candidate_ids"],
                    "flags": model_input["quality_audit"]["flags"],
                }
            )
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "Bag-of-Words Model Definition",
                            "description": "BOW represents text as word-count vectors.",
                            "coverage_criteria": ["Student can define BOW as count-vector text representation."],
                            "source_candidate_ids": ["lr001_001"],
                            "merge_rationale": "Definition-level concept split from implementation.",
                        },
                        {
                            "id": "repair002",
                            "label": "Bag of Words with CountVectorizer",
                            "description": "Using scikit-learn CountVectorizer to implement BOW matrices.",
                            "coverage_criteria": ["Student can transform text with CountVectorizer."],
                            "source_candidate_ids": ["lr002_001"],
                            "merge_rationale": "Implementation behavior stays separate.",
                        },
                    ],
                    "candidate_assignments": [
                        {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["repair001"]},
                        {"candidate_id": "lr002_001", "status": "used_in", "accepted_ids": ["repair002"]},
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_subject_merge_phase(run_dir=run_dir, model_call=model_call)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    assert repair_calls == [
        {
            "route": "Pro Thinking",
            "prompt_path": "subject_merge/quality_repair.md",
            "repair_reason": "over_merged_group",
            "target_candidate_ids": ["lr001_001", "lr002_001"],
            "flags": ["over_merged_group", "granularity_violation"],
        }
    ]
    assert artifact["summary"]["concept_count"] == 2
    assert artifact["phase5b_quality_audit"]["reliability"] == "repaired"
    assert result["phase5b"]["repair_count"] == 1


def test_subject_merge_phase5b_repairs_residual_duplicate_survivors(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [_candidate("TF-IDF", "A weighting scheme for term importance in a document corpus.", ["Define TF-IDF."])],
            },
            {
                "lesson_id": "lesson-b",
                "title": "B",
                "candidates": [
                    _candidate(
                        "TF-IDF Definition and Computation",
                        "TF-IDF is a statistical measure of word relevance in a document corpus.",
                        ["Define TF-IDF and compute it."],
                    )
                ],
            },
        ],
    )
    repair_calls = []
    audit_call_count = 0

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal audit_call_count
        if stage_name == "subject_merge_area_partition":
            return json.dumps(
                {
                    "clusters": [
                        {"id": "area_001", "label": "A", "rationale": "A", "candidate_ids": ["lr001_001"]},
                        {"id": "area_002", "label": "B", "rationale": "B", "candidate_ids": ["lr002_001"]},
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_merge_quality_audit":
            audit_call_count += 1
            if audit_call_count == 1:
                return _quality_audit_json(
                    flags=["residual_duplicate"],
                    repair_plan=[
                        {
                            "repair_reason": "residual_duplicate",
                            "candidate_ids": ["lr001_001", "lr002_001"],
                            "explanation": "Same TF-IDF definition survived as separate concepts.",
                        }
                    ],
                )
            return _quality_audit_json()
        if stage_name == "subject_merge_quality_repair":
            model_input = inputs["subject_merge_quality_repair_input.json"]
            repair_calls.append(model_input["repair_reason"])
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "TF-IDF Definition",
                            "description": "TF-IDF weights terms by term frequency and inverse document frequency.",
                            "coverage_criteria": ["Student can define TF-IDF."],
                            "source_candidate_ids": model_input["target_candidate_ids"],
                            "merge_rationale": "Residual duplicates were consolidated.",
                        }
                    ],
                    "candidate_assignments": [
                        {
                            "candidate_id": model_input["target_candidate_ids"][0],
                            "status": "used_in",
                            "accepted_ids": ["repair001"],
                        },
                        {
                            "candidate_id": model_input["target_candidate_ids"][1],
                            "status": "merged_into",
                            "merged_into": "repair001",
                            "explanation": "Duplicate definition.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_subject_merge_phase(run_dir=run_dir, model_call=model_call)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    assert repair_calls == ["residual_duplicate"]
    assert artifact["summary"]["concept_count"] == 1
    assert artifact["phase5b_quality_audit"]["reliability"] == "repaired"


def test_subject_merge_phase5b_repairs_multiple_residual_duplicate_pairs_in_one_pass(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [
                    _candidate("TF-IDF", "A weighting scheme for term importance in a document corpus.", ["Define TF-IDF."])
                ],
            },
            {
                "lesson_id": "lesson-b",
                "title": "B",
                "candidates": [
                    _candidate(
                        "TF-IDF Definition and Computation",
                        "TF-IDF is a statistical measure of word relevance in a document corpus.",
                        ["Define TF-IDF and compute it."],
                    )
                ],
            },
            {
                "lesson_id": "lesson-c",
                "title": "C",
                "candidates": [
                    _candidate(
                        "Sentiment Analysis: Definition and Supervised Learning",
                        "Sentiment analysis classifies text as positive or negative.",
                        ["Define sentiment analysis."],
                    )
                ],
            },
            {
                "lesson_id": "lesson-d",
                "title": "D",
                "candidates": [
                    _candidate(
                        "Análise de Sentimentos",
                        "Técnicas para classificar a polaridade de textos como positivo, negativo ou neutro.",
                        ["Definir análise de sentimentos."],
                    )
                ],
            },
            {
                "lesson_id": "lesson-e",
                "title": "E",
                "candidates": [
                    _candidate(
                        "Bag of Words with CountVectorizer",
                        "Converting text into token-count matrices with scikit-learn CountVectorizer.",
                        ["Transform texts with CountVectorizer."],
                    )
                ],
            },
        ],
    )
    repair_calls = []
    audit_call_count = 0

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal audit_call_count
        if stage_name == "subject_merge_area_partition":
            return json.dumps(
                {
                    "clusters": [
                        {"id": f"area_{index:03d}", "label": candidate["label"], "rationale": "Singleton area.", "candidate_ids": [candidate["id"]]}
                        for index, candidate in enumerate(inputs["subject_merge_area_partition_input.json"]["candidates"], start=1)
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_merge_quality_audit":
            audit_call_count += 1
            if audit_call_count == 1:
                return _quality_audit_json(
                    flags=["residual_duplicate"],
                    repair_plan=[
                        {
                            "repair_reason": "residual_duplicate",
                            "candidate_ids": ["lr001_001", "lr002_001"],
                            "explanation": "Same TF-IDF definition survived as separate concepts.",
                        },
                        {
                            "repair_reason": "residual_duplicate",
                            "candidate_ids": ["lr003_001", "lr004_001"],
                            "explanation": "Same sentiment-analysis definition survived as separate concepts.",
                        },
                    ],
                )
            return _quality_audit_json()
        if stage_name == "subject_merge_quality_repair":
            target_ids = inputs["subject_merge_quality_repair_input.json"]["target_candidate_ids"]
            repair_calls.append(target_ids)
            if set(target_ids) == {"lr001_001", "lr002_001"}:
                label = "TF-IDF Definition"
            elif set(target_ids) == {"lr003_001", "lr004_001"}:
                label = "Sentiment Analysis Definition"
            else:
                raise AssertionError(f"unexpected repair target ids: {target_ids}")
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": label,
                            "description": f"Merged duplicate concept for {label}.",
                            "coverage_criteria": [f"Student can explain {label}."],
                            "source_candidate_ids": target_ids,
                            "merge_rationale": "High-confidence residual duplicate pair.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": target_ids[0], "status": "used_in", "accepted_ids": ["repair001"]},
                        {
                            "candidate_id": target_ids[1],
                            "status": "merged_into",
                            "merged_into": "repair001",
                            "explanation": "Same definition.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_subject_merge_phase(run_dir=run_dir, model_call=model_call)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    assert repair_calls == [["lr001_001", "lr002_001"], ["lr003_001", "lr004_001"]]
    assert artifact["summary"]["concept_count"] == 3
    assert _concept_by_label(artifact, "Bag of Words with CountVectorizer")
    assert artifact["phase5b_quality_audit"]["reliability"] == "repaired"


def test_subject_merge_phase5b_audit_can_repair_obvious_missed_merge_from_rejected_cluster(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [_candidate("One-Hot Encoding", "A sparse vector with one active vocabulary index.", ["Define one-hot encoding."])],
            },
            {
                "lesson_id": "lesson-b",
                "title": "B",
                "candidates": [
                    _candidate(
                        "One-Hot Encoding Definition",
                        "One-hot encoding represents each word as zeros with a single one at the word's vocabulary index.",
                        ["Create and explain a one-hot vector."],
                    )
                ],
            },
        ],
    )
    audit_call_count = 0
    repair_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal audit_call_count
        if stage_name == "subject_merge_area_partition":
            return _all_in_one_cluster_json(inputs["subject_merge_area_partition_input.json"], cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_cluster_evaluation":
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "sm001",
                            "label": "One-Hot Encoding",
                            "description": "A sparse vector representation.",
                            "coverage_criteria": ["Define one-hot encoding."],
                            "source_candidate_ids": ["lr001_001"],
                            "merge_rationale": "Fixture keeps separate to create a missed merge.",
                        },
                        {
                            "id": "sm002",
                            "label": "One-Hot Encoding Definition",
                            "description": "A vector with a single one at the vocabulary index.",
                            "coverage_criteria": ["Create a one-hot vector."],
                            "source_candidate_ids": ["lr002_001"],
                            "merge_rationale": "Fixture keeps separate to create a missed merge.",
                        },
                    ],
                    "candidate_assignments": [
                        {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["sm001"]},
                        {"candidate_id": "lr002_001", "status": "used_in", "accepted_ids": ["sm002"]},
                    ],
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_merge_quality_audit":
            audit_call_count += 1
            model_input = inputs["subject_merge_quality_audit_input.json"]
            if audit_call_count == 1:
                assert route.alias == "Pro Thinking"
                assert model_input["prompt_path"] == "subject_merge/quality_audit.md"
                rejected = model_input["review_signals"]["same_fine_cluster_kept_separate"]
                assert rejected[0]["candidate_ids"] == ["lr001_001", "lr002_001"]
                return _quality_audit_json(
                    flags=["missed_obvious_merge"],
                    repair_plan=[
                        {
                            "repair_reason": "missed_obvious_merge",
                            "candidate_ids": ["lr001_001", "lr002_001"],
                            "explanation": "Both candidates assess the same one-hot encoding idea.",
                        }
                    ],
                    missed_merge_candidates=[
                        {
                            "candidate_ids": ["lr001_001", "lr002_001"],
                            "confidence": "high",
                            "explanation": "Same idea and same level.",
                        }
                    ],
                )
            return _quality_audit_json()
        if stage_name == "subject_merge_quality_repair":
            model_input = inputs["subject_merge_quality_repair_input.json"]
            repair_calls.append(model_input["repair_reason"])
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "One-Hot Encoding",
                            "description": "One-hot encoding represents a token as a sparse vector with one active vocabulary index.",
                            "coverage_criteria": ["Define and create a one-hot vector."],
                            "source_candidate_ids": model_input["target_candidate_ids"],
                            "merge_rationale": "Obvious missed merge at the same level.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["repair001"]},
                        {
                            "candidate_id": "lr002_001",
                            "status": "merged_into",
                            "merged_into": "repair001",
                            "explanation": "Same one-hot encoding idea.",
                        },
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_subject_merge_phase(run_dir=run_dir, model_call=model_call)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    assert repair_calls == ["missed_obvious_merge"]
    assert artifact["summary"]["concept_count"] == 1
    assert artifact["phase5b_quality_audit"]["reliability"] == "repaired"


def test_subject_merge_phase5b_residual_duplicate_gate_ignores_applications_challenges_and_implementations(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [
                    _candidate("Natural Language Processing (NLP) Definition", "NLP is a branch of AI for processing human language.", ["Define NLP."])
                ],
            },
            {
                "lesson_id": "lesson-b",
                "title": "B",
                "candidates": [
                    _candidate("Natural Language Challenges", "Ambiguity, context, and semantics make human language difficult to process.", ["Name NLP challenges."])
                ],
            },
            {
                "lesson_id": "lesson-c",
                "title": "C",
                "candidates": [
                    _candidate("Everyday Applications of NLP", "Autocorrect and plagiarism checkers are everyday NLP applications.", ["List applications."])
                ],
            },
            {
                "lesson_id": "lesson-d",
                "title": "D",
                "candidates": [
                    _candidate("Bag of Words with CountVectorizer", "Implement Bag-of-Words with scikit-learn CountVectorizer.", ["Use CountVectorizer."])
                ],
            },
            {
                "lesson_id": "lesson-e",
                "title": "E",
                "candidates": [
                    _candidate("Bag-of-Words Model Definition", "Bag-of-Words represents text as word-count vectors.", ["Define BoW."])
                ],
            },
        ],
    )

    run_subject_merge_phase(
        run_dir=run_dir,
        model_call=_standalone_subject_merge_model_call,
        phase5b_enabled=True,
    )

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    assert artifact["summary"]["concept_count"] == 5
    assert artifact["phase5b_quality_audit"]["reliability"] == "reliable"


def test_subject_merge_phase5b_residual_duplicate_gate_flags_same_definition_variants(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [_candidate("Bag-of-Words Model Definition", "BoW represents text as word-count vectors.", ["Define BoW."])],
            },
            {
                "lesson_id": "lesson-b",
                "title": "B",
                "candidates": [_candidate("Bag-of-Words Representation", "The bag-of-words model represents text as a vector of word frequencies.", ["Explain BoW representation."])],
            },
            {
                "lesson_id": "lesson-c",
                "title": "C",
                "candidates": [_candidate("TF-IDF", "A weighting scheme that scales term frequency by inverse document frequency.", ["Define TF-IDF."])],
            },
            {
                "lesson_id": "lesson-d",
                "title": "D",
                "candidates": [_candidate("TF-IDF Definition and Computation", "TF-IDF is a statistical measure computed as TF times IDF.", ["Define TF-IDF."])],
            },
            {
                "lesson_id": "lesson-e",
                "title": "E",
                "candidates": [_candidate("Word2Vec: CBOW and Skip-gram Architectures", "CBOW predicts a target word from context; Skip-gram predicts context from target.", ["Differentiate CBOW and Skip-gram."])],
            },
            {
                "lesson_id": "lesson-f",
                "title": "F",
                "candidates": [_candidate("Arquiteturas do Word2Vec: CBOW e Skip-Gram", "CBOW prevê a palavra central pelo contexto; Skip-Gram prevê contexto pela palavra central.", ["Diferencie CBOW e Skip-Gram."])],
            },
        ],
    )
    repair_calls = []
    audit_call_count = 0

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal audit_call_count
        if stage_name in {"subject_merge_area_partition", "subject_merge_fine_clustering"}:
            key = f"{stage_name}_input.json"
            return json.dumps(
                {
                    "clusters": [
                        {
                            "id": f"cluster_{index:03d}",
                            "label": candidate["label"],
                            "rationale": "Fixture singleton.",
                            "candidate_ids": [candidate["id"]],
                        }
                        for index, candidate in enumerate(inputs[key]["candidates"], start=1)
                    ]
                },
                ensure_ascii=False,
            )
        if stage_name == "subject_merge_quality_audit":
            audit_call_count += 1
            if audit_call_count == 1:
                return _quality_audit_json(
                    flags=["residual_duplicate"],
                    repair_plan=[
                        {
                            "repair_reason": "residual_duplicate",
                            "candidate_ids": ["lr001_001", "lr002_001"],
                            "explanation": "Same BOW definition survived as separate concepts.",
                        },
                        {
                            "repair_reason": "residual_duplicate",
                            "candidate_ids": ["lr003_001", "lr004_001"],
                            "explanation": "Same TF-IDF definition survived as separate concepts.",
                        },
                        {
                            "repair_reason": "residual_duplicate",
                            "candidate_ids": ["lr005_001", "lr006_001"],
                            "explanation": "Same Word2Vec architecture definition survived as separate concepts.",
                        },
                    ],
                )
            return _quality_audit_json()
        if stage_name == "subject_merge_quality_repair":
            target_ids = inputs["subject_merge_quality_repair_input.json"]["target_candidate_ids"]
            repair_calls.append(target_ids)
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "repair001",
                            "label": "Merged definition concept",
                            "description": "Merged same-level definition variants.",
                            "coverage_criteria": ["Student can explain the same-level definition."],
                            "source_candidate_ids": target_ids,
                            "merge_rationale": "Same canonical definition at the same level.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": target_ids[0], "status": "used_in", "accepted_ids": ["repair001"]},
                        *[
                            {
                                "candidate_id": candidate_id,
                                "status": "merged_into",
                                "merged_into": "repair001",
                                "explanation": "Same definition variant.",
                            }
                            for candidate_id in target_ids[1:]
                        ],
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_subject_merge_phase(run_dir=run_dir, model_call=model_call)

    assert repair_calls == [
        ["lr001_001", "lr002_001"],
        ["lr003_001", "lr004_001"],
        ["lr005_001", "lr006_001"],
    ]


def test_subject_merge_evaluation_synthesizes_missing_standalone_concepts_from_assignments(tmp_path):
    run_dir = tmp_path / "run"
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-a",
                "title": "A",
                "candidates": [
                    _candidate("Perceptron", "A single-layer classifier.", ["Define perceptron."]),
                    _candidate("RNN basics", "Recurrent neural networks process sequences.", ["Define RNN."]),
                ],
            }
        ],
    )

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "subject_merge_area_partition":
            return _all_in_one_cluster_json(inputs["subject_merge_area_partition_input.json"], cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_cluster_evaluation":
            return json.dumps(
                {
                    "accepted_concepts": [
                        {
                            "id": "ac_001",
                            "label": "Perceptron",
                            "description": "A single-layer classifier.",
                            "coverage_criteria": ["Define perceptron."],
                            "source_candidate_ids": ["lr001_001"],
                            "merge_rationale": "Accepted concept.",
                        }
                    ],
                    "candidate_assignments": [
                        {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["ac_001"]},
                        {"candidate_id": "lr001_002", "status": "used_in", "accepted_ids": ["ac_002"]},
                    ],
                },
                ensure_ascii=False,
            )
        raise AssertionError(f"unexpected stage call: {stage_name}")

    run_subject_merge_phase(run_dir=run_dir, model_call=model_call, phase5b_enabled=False)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    assert artifact["summary"]["concept_count"] == 2
    assert _concept_by_label(artifact, "RNN basics")["source_candidate_ids"] == ["lr001_002"]


def test_subject_merge_phase5b_rebuilds_lost_occurrences_before_model_audit(tmp_path):
    run_dir = tmp_path / "run"
    _write_bow_definition_and_countvectorizer_inputs(run_dir)

    run_subject_merge_phase(
        run_dir=run_dir,
        model_call=_standalone_subject_merge_model_call,
        phase5b_enabled=False,
    )
    artifact_path = run_dir / "subject_merge.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    artifact["concepts"][0]["occurrences"] = []
    artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    audit_calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        if stage_name == "subject_merge_quality_audit":
            audit_calls.append(route.alias)
            assert inputs["subject_merge_quality_audit_input.json"]["guardrails"]["findings"] == []
            return _quality_audit_json()
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_subject_merge_phase5b(run_dir=run_dir, model_call=model_call)

    repaired = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert audit_calls == ["Pro Thinking"]
    assert result["phase5b"]["repair_count"] == 1
    assert repaired["phase5b_quality_audit"]["flags"] == []
    assert repaired["concepts"][0]["occurrences"]


def test_subject_merge_phase5b_records_repair_unstable_without_looping(tmp_path):
    run_dir = tmp_path / "run"
    _write_bow_definition_and_countvectorizer_inputs(run_dir)
    repair_call_count = 0
    audit_call_count = 0

    def model_call(*, route, stage_name, inputs, repair_context=None):
        nonlocal audit_call_count, repair_call_count
        if stage_name == "subject_merge_area_partition":
            return _all_in_one_cluster_json(inputs["subject_merge_area_partition_input.json"], cluster_id="area_001")
        if stage_name == "subject_merge_fine_clustering":
            return _all_in_one_cluster_json(inputs["subject_merge_fine_clustering_input.json"], cluster_id="cluster_001")
        if stage_name == "subject_cluster_evaluation":
            return _merged_bow_definition_and_countvectorizer()
        if stage_name == "subject_merge_quality_audit":
            audit_call_count += 1
            return _quality_audit_json(
                flags=["over_merged_group", "granularity_violation"],
                repair_plan=[
                    {
                        "repair_reason": "over_merged_group",
                        "candidate_ids": ["lr001_001", "lr002_001"],
                        "explanation": "Definition and implementation are still collapsed.",
                    }
                ],
            )
        if stage_name == "subject_merge_quality_repair":
            repair_call_count += 1
            return _merged_bow_definition_and_countvectorizer()
        raise AssertionError(f"unexpected stage call: {stage_name}")

    result = run_subject_merge_phase(run_dir=run_dir, model_call=model_call)

    artifact = json.loads((run_dir / "subject_merge.json").read_text(encoding="utf-8"))
    assert audit_call_count == 2
    assert repair_call_count == 1
    assert artifact["phase5b_quality_audit"]["reliability"] == "repair_required"
    assert "repair_unstable" in artifact["phase5b_quality_audit"]["flags"]
    assert result["phase5b"]["unrepaired_count"] == 1


def test_subject_merge_blocks_without_complete_lesson_reconciliation_summary(tmp_path):
    run_dir = tmp_path / "run"
    lesson_a = "lesson-2026-05-05-bow"
    _write_source_ledger(run_dir, lessons=[{"lesson_id": lesson_a, "title": lesson_a}])
    _write_lesson_reconciliation(
        run_dir / "lessons" / lesson_a / "lesson_reconciliation.json",
        lesson_id=lesson_a,
        candidates=[_candidate("Bag-of-Words count-vector representation", "BoW description.", ["Explain BoW."])],
    )

    with pytest.raises(StageBlockedError, match="complete lesson_reconciliation_summary"):
        run_subject_merge_phase(run_dir=run_dir, model_call=lambda **_kwargs: "{}")


def _write_bow_definition_and_countvectorizer_inputs(run_dir):
    _write_subject_merge_inputs(
        run_dir,
        [
            {
                "lesson_id": "lesson-2026-05-05-representa-o-de-palavras-e-bag-of-words-bow",
                "title": "Bag of Words",
                "candidates": [
                    _candidate(
                        "Bag-of-Words Model Definition",
                        "The bag-of-words model converts documents into fixed-length vectors by counting word occurrences.",
                        ["Define the BOW model and explain how it represents text as word count vectors."],
                    )
                ],
            },
            {
                "lesson_id": "lesson-2026-05-11-nltk-bow-e-naive-bayes-para-an-lise-de-conte-do",
                "title": "NLTK BoW e Naive Bayes",
                "candidates": [
                    _candidate(
                        "Bag of Words with CountVectorizer",
                        "Converting preprocessed text into a numerical matrix of token counts using scikit-learn's CountVectorizer.",
                        ["Transform a list of texts into a BoW matrix using CountVectorizer."],
                        roles=["introducing", "demonstrating"],
                    )
                ],
            },
        ],
    )


def _merged_bow_definition_and_countvectorizer():
    return json.dumps(
        {
            "accepted_concepts": [
                {
                    "id": "sm001",
                    "label": "Bag-of-Words",
                    "description": "BOW represents text as word-count vectors and can be implemented with CountVectorizer.",
                    "coverage_criteria": ["Student can discuss BOW and implement it with CountVectorizer."],
                    "source_candidate_ids": ["lr001_001", "lr002_001"],
                    "merge_rationale": "Incorrectly merged definition and implementation.",
                }
            ],
            "candidate_assignments": [
                {"candidate_id": "lr001_001", "status": "used_in", "accepted_ids": ["sm001"]},
                {
                    "candidate_id": "lr002_001",
                    "status": "merged_into",
                    "merged_into": "sm001",
                    "explanation": "Incorrectly collapsed implementation into definition.",
                },
            ],
        },
        ensure_ascii=False,
    )


def _quality_audit_json(*, flags=None, repair_plan=None, missed_merge_candidates=None):
    flags = flags or []
    repair_plan = repair_plan or []
    missed_merge_candidates = missed_merge_candidates or []
    reliable = not flags and not repair_plan and not missed_merge_candidates
    score = 3 if reliable else 1
    return json.dumps(
        {
            "scores": {
                "identity_correctness": score,
                "granularity_preservation": score,
                "provenance_preservation": 3,
                "assignment_completeness": 3,
                "overlap_reduction": score,
                "subject_coherence": score,
                "net_phase5_benefit": score,
            },
            "reliability": "reliable" if reliable else "repair_required",
            "flags": flags,
            "repair_plan": repair_plan,
            "missed_merge_candidates": missed_merge_candidates,
        },
        ensure_ascii=False,
    )


def _standalone_subject_merge_model_call(*, route, stage_name, inputs, repair_context=None):
    if stage_name in {"subject_merge_area_partition", "subject_merge_fine_clustering"}:
        key = f"{stage_name}_input.json"
        return json.dumps(
            {
                "clusters": [
                    {
                        "id": f"cluster_{index:03d}",
                        "label": candidate["label"],
                        "rationale": "Deterministic singleton fixture.",
                        "candidate_ids": [candidate["id"]],
                    }
                    for index, candidate in enumerate(inputs[key]["candidates"], start=1)
                ]
            },
            ensure_ascii=False,
        )
    if stage_name == "subject_merge_quality_audit":
        return _quality_audit_json()
    raise AssertionError(f"unexpected stage call: {stage_name}")


def _all_in_one_cluster_json(model_input, *, cluster_id):
    return json.dumps(
        {
            "clusters": [
                {
                    "id": cluster_id,
                    "label": "All candidates",
                    "rationale": "Fixture groups all candidates.",
                    "candidate_ids": model_input["input_candidate_ids"],
                }
            ]
        },
        ensure_ascii=False,
    )


def _concept_by_label(artifact, label):
    return next(concept for concept in artifact["concepts"] if concept["label"] == label)


def _candidate(label, description, coverage_criteria, *, roles=None):
    return {
        "label": label,
        "description": description,
        "coverage_criteria": coverage_criteria,
        "source_roles": roles or ["introducing", "explaining"],
        "evidence_types": ["source_body"],
    }


def _write_subject_merge_inputs(run_dir, lesson_specs):
    lessons = [{"lesson_id": spec["lesson_id"], "title": spec["title"]} for spec in lesson_specs]
    _write_source_ledger(run_dir, lessons=lessons)
    for spec in lesson_specs:
        _write_lesson_reconciliation(
            run_dir / "lessons" / spec["lesson_id"] / "lesson_reconciliation.json",
            lesson_id=spec["lesson_id"],
            candidates=spec["candidates"],
        )
    _write_lesson_reconciliation_summary(run_dir, lesson_ids=[lesson["lesson_id"] for lesson in lessons])


def _write_source_ledger(run_dir, *, lessons):
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "course_id": "si",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": lessons,
                "self_studies": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_lesson_reconciliation_summary(run_dir, *, lesson_ids):
    (run_dir / "lesson_reconciliation_summary.json").write_text(
        json.dumps(
            {
                "artifact_type": "lesson_reconciliation_summary",
                "schema_version": "lesson_reconciliation_summary.v0",
                "summary": {
                    "lesson_count": len(lesson_ids),
                    "reconciled_lesson_count": len(lesson_ids),
                    "reused_lesson_count": 0,
                    "skipped_count": 0,
                },
                "artifacts": [f"lessons/{lesson_id}/lesson_reconciliation.json" for lesson_id in lesson_ids],
                "skipped": [],
                "model_route": "Pro",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def _write_lesson_reconciliation(path, *, lesson_id, candidates):
    path.parent.mkdir(parents=True, exist_ok=True)
    reconciled_candidates = []
    for index, candidate in enumerate(candidates, start=1):
        reconciled_candidate_id = f"reconciled-candidate-{lesson_id}-{index:03d}"
        reconciled_candidates.append(
            {
                "reconciled_candidate_id": reconciled_candidate_id,
                "label": candidate["label"],
                "description": candidate["description"],
                "coverage_criteria": candidate["coverage_criteria"],
                "source_candidate_ids": [f"source-{lesson_id}-{index:03d}"],
                "merge_rationale": "Fixture lesson-local reconciliation accepted this candidate.",
                "source_roles": candidate["source_roles"],
                "evidence_types": candidate["evidence_types"],
                "evidence": [
                    {
                        "candidate_ref": {
                            "artifact_path": f"lessons/{lesson_id}/self_studies/{index}/self_study_extraction.json",
                            "candidate_id": f"candidate-{index:03d}",
                            "evidence_type": "source_body",
                            "lesson_id": lesson_id,
                            "self_study_id": str(index),
                        },
                        "evidence_type": "source_body",
                        "anchors": [{"kind": "markdown_heading", "locator": candidate["label"]}],
                        "extraction_reason": {
                            "source_grounded_rationale": "The source supports this fixture candidate.",
                            "granularity_rationale": "One checkable idea.",
                        },
                        "source_metadata": {"source_name": candidate["label"]},
                    }
                ],
            }
        )
    path.write_text(
        json.dumps(
            {
                "artifact_type": "lesson_reconciliation",
                "schema_version": "lesson_reconciliation.v0",
                "lesson_id": lesson_id,
                "reconciled_candidates": reconciled_candidates,
                "candidate_assignments": [],
                "pruned_candidates": [],
                "review_candidates": [],
                "summary": {
                    "input_candidate_count": len(reconciled_candidates),
                    "reconciled_candidate_count": len(reconciled_candidates),
                    "pruned_candidate_count": 0,
                    "review_candidate_count": 0,
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
