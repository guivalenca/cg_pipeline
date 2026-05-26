import json

import pytest

from concept_graph_creation.runtime.semantic_reduce import (
    build_candidate_registry,
    build_reduce_input,
    normalize_decision_output,
    validate_reduce_decision,
)


def test_semantic_reduce_registry_assigns_compact_ids_and_preserves_candidate_refs():
    registry = build_candidate_registry(
        scope_id="lesson-2026-05-05-bow",
        source_artifact="source_ledger.json",
        candidate_sources=[
            {
                "namespace": "c22_pro_thinking",
                "artifact_type": "self_study_extraction",
                "artifact_path": "lessons/lesson-2026-05-05-bow/self_studies/22/self_study_extraction.json",
                "lesson_id": "lesson-2026-05-05-bow",
                "self_study_id": "22",
                "model_route": "Pro Thinking",
                "evidence_type": "source_body",
                "source_metadata": {"source_name": "Bag of Words article"},
                "candidates": [
                    {
                        "candidate_id": "candidate-22-001",
                        "label": "Bag-of-Words count vectors",
                        "description": "Bag-of-Words represents text as word-count vectors.",
                        "coverage_criteria": ["Student can describe BoW count-vector representation."],
                        "source_roles": ["explaining"],
                        "source_anchors": [{"kind": "markdown_heading", "locator": "BoW model"}],
                        "extraction_reason": {
                            "source_grounded_rationale": "The source defines BoW as count vectors.",
                            "granularity_rationale": "This is one checkable idea.",
                        },
                    }
                ],
            },
            {
                "namespace": "m64",
                "artifact_type": "metadata_only_extraction",
                "artifact_path": "lessons/lesson-2026-05-05-bow/self_studies/64/metadata_only_extraction.json",
                "lesson_id": "lesson-2026-05-05-bow",
                "self_study_id": "64",
                "model_route": "Pro",
                "evidence_type": "workbook_metadata",
                "candidates": [
                    {
                        "candidate_id": "metadata-candidate-64-001",
                        "label": "Language processing for sentiment analysis",
                        "description": "Workbook metadata points to language processing in sentiment analysis.",
                        "coverage_criteria": ["Student can connect language processing to sentiment analysis."],
                        "metadata_anchors": [{"kind": "workbook_description", "locator": "Description"}],
                        "extraction_reason": {
                            "metadata_grounded_rationale": "The description names sentiment analysis.",
                            "granularity_rationale": "This is one metadata-backed teaching signal.",
                        },
                    }
                ],
            },
        ],
    )

    assert registry["artifact_type"] == "semantic_reduce_candidate_registry"
    assert registry["schema_version"] == "semantic_reduce_candidate_registry.v0"
    assert registry["scope_id"] == "lesson-2026-05-05-bow"
    assert list(registry["candidates"]) == ["c22_pro_thinking_001", "m64_001"]
    assert registry["summary"] == {"candidate_count": 2}

    source_body = registry["candidates"]["c22_pro_thinking_001"]
    assert source_body["candidate_ref"] == {
        "artifact_path": "lessons/lesson-2026-05-05-bow/self_studies/22/self_study_extraction.json",
        "candidate_id": "candidate-22-001",
        "evidence_type": "source_body",
        "model_route": "Pro Thinking",
        "lesson_id": "lesson-2026-05-05-bow",
        "self_study_id": "22",
    }
    assert source_body["anchors"] == [{"kind": "markdown_heading", "locator": "BoW model"}]

    metadata_only = registry["candidates"]["m64_001"]
    assert metadata_only["candidate_ref"]["evidence_type"] == "workbook_metadata"
    assert metadata_only["anchors"] == [{"kind": "workbook_description", "locator": "Description"}]


def test_semantic_reduce_decision_preserves_one_candidate_used_in_multiple_concepts():
    registry = build_candidate_registry(
        scope_id="lesson-2026-05-05-bow",
        source_artifact="source_ledger.json",
        candidate_sources=[
            {
                "namespace": "c22_pro_thinking",
                "artifact_type": "self_study_extraction",
                "artifact_path": "lessons/lesson-2026-05-05-bow/self_studies/22/self_study_extraction.json",
                "lesson_id": "lesson-2026-05-05-bow",
                "self_study_id": "22",
                "model_route": "Pro Thinking",
                "evidence_type": "source_body",
                "candidates": [
                    {
                        "candidate_id": "candidate-22-001",
                        "label": "Bag-of-Words count vectors",
                        "description": "Bag-of-Words represents text as word-count vectors.",
                        "coverage_criteria": ["Student can explain count-vector representation."],
                    },
                    {
                        "candidate_id": "candidate-22-002",
                        "label": "Word frequency vectors",
                        "description": "Word frequencies can be encoded as vectors.",
                        "coverage_criteria": ["Student can connect word frequency to vectors."],
                    },
                    {
                        "candidate_id": "candidate-22-003",
                        "label": "Bag-of-Words loses sequence information",
                        "description": "Bag-of-Words keeps counts but discards word order.",
                        "coverage_criteria": ["Student can state what information BoW loses."],
                    },
                ],
            }
        ],
    )

    decision = normalize_decision_output(
        raw=json.dumps(
            {
                "accepted_concepts": [
                    {
                        "id": "lr001",
                        "label": "Bag-of-Words count-vector representation",
                        "description": "Bag-of-Words represents text through word-count vectors.",
                        "coverage_criteria": ["Student can describe how BoW creates a count vector."],
                        "source_candidate_ids": [
                            "c22_pro_thinking_001",
                            "c22_pro_thinking_002",
                            "c22_pro_thinking_003",
                        ],
                        "merge_rationale": "Both candidates describe the same count-vector representation.",
                    },
                    {
                        "id": "lr002",
                        "label": "Information lost by Bag-of-Words",
                        "description": "Bag-of-Words loses sequence information while keeping word counts.",
                        "coverage_criteria": ["Student can explain that BoW ignores word order."],
                        "source_candidate_ids": ["c22_pro_thinking_003"],
                        "merge_rationale": "This candidate is a distinct consequence of BoW representation.",
                    },
                ],
                "candidate_assignments": [
                    {
                        "candidate_id": "c22_pro_thinking_001",
                        "status": "used_in",
                        "accepted_ids": ["lr001"],
                    },
                    {
                        "candidate_id": "c22_pro_thinking_002",
                        "status": "merged_into",
                        "merged_into": "lr001",
                        "explanation": "Same teachable idea as lr001, with weaker wording.",
                    },
                    {
                        "candidate_id": "c22_pro_thinking_003",
                        "status": "used_in",
                        "accepted_ids": ["lr001", "lr002"],
                    },
                ],
            },
            ensure_ascii=False,
        ),
        scope_id="lesson-2026-05-05-bow",
        stage_name="lesson_reduce",
        model_route="Pro Thinking",
        input_candidate_ids=list(registry["candidates"]),
    )

    assert validate_reduce_decision(decision, registry) == []
    assert decision["artifact_type"] == "semantic_reduce_decision"
    assert decision["stage_name"] == "lesson_reduce"
    assert decision["summary"] == {
        "input_candidate_count": 3,
        "accepted_count": 2,
        "pruned_count": 0,
        "candidate_assignment_count": 3,
        "review_count": 0,
    }
    assert decision["candidate_assignments"][2] == {
        "candidate_id": "c22_pro_thinking_003",
        "status": "used_in",
        "accepted_ids": ["lr001", "lr002"],
    }


def test_semantic_reduce_input_contains_compact_cards_and_assignment_contract():
    registry = build_candidate_registry(
        scope_id="lesson-2026-05-05-bow",
        source_artifact="source_ledger.json",
        candidate_sources=[
            {
                "namespace": "c22_pro_thinking",
                "artifact_type": "self_study_extraction",
                "artifact_path": "lessons/lesson-2026-05-05-bow/self_studies/22/self_study_extraction.json",
                "lesson_id": "lesson-2026-05-05-bow",
                "self_study_id": "22",
                "model_route": "Pro Thinking",
                "evidence_type": "source_body",
                "candidates": [
                    {
                        "candidate_id": "candidate-22-001",
                        "label": "Bag-of-Words count vectors",
                        "description": "Bag-of-Words represents text as word-count vectors.",
                        "coverage_criteria": ["Student can explain count-vector representation."],
                        "source_roles": ["explaining"],
                        "source_anchors": [{"kind": "paragraph", "locator": "BoW turns text into vectors."}],
                        "extraction_reason": {
                            "source_grounded_rationale": "The source says BoW turns text into vectors.",
                            "granularity_rationale": "This is one checkable idea.",
                        },
                    }
                ],
            }
        ],
    )

    reduce_input = build_reduce_input(
        stage_name="lesson_reduce",
        scope={"id": "lesson-2026-05-05-bow", "title": "Bag of Words"},
        registry=registry,
        input_candidate_ids=["c22_pro_thinking_001"],
        prompt="Reduce these candidates.",
        prompt_path="prompts/lesson_reduce.md",
        model_route="Pro Thinking",
    )

    assert reduce_input["artifact_type"] == "semantic_reduce_input"
    assert reduce_input["task"] == "lesson_reduce"
    assert reduce_input["scope"] == {"id": "lesson-2026-05-05-bow", "title": "Bag of Words"}
    assert reduce_input["candidates"] == [
        {
            "id": "c22_pro_thinking_001",
            "label": "Bag-of-Words count vectors",
            "description": "Bag-of-Words represents text as word-count vectors.",
            "coverage_criteria": ["Student can explain count-vector representation."],
            "source_roles": ["explaining"],
            "evidence_type": "source_body",
            "rationale": {
                "source_grounded_rationale": "The source says BoW turns text into vectors.",
                "granularity_rationale": "This is one checkable idea.",
            },
            "anchors": ["BoW turns text into vectors."],
        }
    ]
    assert "original_candidate" not in reduce_input["candidates"][0]
    assert "candidate_ref" not in reduce_input["candidates"][0]
    assert reduce_input["output_contract"]["candidate_assignments"][0]["status"] == "used_in"
    assert reduce_input["web_access_policy"]["web_search_allowed"] is False


def test_semantic_reduce_validation_blocks_pruning_candidate_used_as_evidence():
    registry = build_candidate_registry(
        scope_id="lesson-2026-05-05-bow",
        source_artifact="source_ledger.json",
        candidate_sources=[
            {
                "namespace": "c22_pro_thinking",
                "artifact_type": "self_study_extraction",
                "artifact_path": "lessons/lesson-2026-05-05-bow/self_studies/22/self_study_extraction.json",
                "lesson_id": "lesson-2026-05-05-bow",
                "self_study_id": "22",
                "model_route": "Pro Thinking",
                "evidence_type": "source_body",
                "candidates": [
                    {
                        "candidate_id": "candidate-22-001",
                        "label": "Bag-of-Words count vectors",
                        "description": "Bag-of-Words represents text as word-count vectors.",
                        "coverage_criteria": ["Student can explain count-vector representation."],
                    },
                    {
                        "candidate_id": "candidate-22-002",
                        "label": "Historical aside",
                        "description": "The source mentions a historical aside.",
                        "coverage_criteria": ["Student can recall the aside."],
                    },
                ],
            }
        ],
    )
    decision = normalize_decision_output(
        raw=json.dumps(
            {
                "accepted_concepts": [
                    {
                        "id": "lr001",
                        "label": "Bag-of-Words count-vector representation",
                        "description": "Bag-of-Words represents text through word-count vectors.",
                        "coverage_criteria": ["Student can describe how BoW creates a count vector."],
                        "source_candidate_ids": ["c22_pro_thinking_001"],
                        "merge_rationale": "The candidate directly defines the representation.",
                    }
                ],
                "candidate_assignments": [
                    {
                        "candidate_id": "c22_pro_thinking_001",
                        "status": "pruned",
                        "reason": "incidental",
                        "explanation": "Invalid: this candidate is still cited as accepted evidence.",
                    },
                    {
                        "candidate_id": "c22_pro_thinking_002",
                        "status": "pruned",
                        "reason": "incidental",
                        "explanation": "The historical aside should not influence this lesson concept set.",
                    },
                ],
            },
            ensure_ascii=False,
        ),
        scope_id="lesson-2026-05-05-bow",
        stage_name="lesson_reduce",
        model_route="Pro Thinking",
        input_candidate_ids=list(registry["candidates"]),
    )

    errors = validate_reduce_decision(decision, registry)

    assert any("cannot be pruned because it is used as accepted evidence" in error for error in errors)
    assert decision["pruned"] == [
        {
            "candidate_id": "c22_pro_thinking_001",
            "reason": "incidental",
            "explanation": "Invalid: this candidate is still cited as accepted evidence.",
        },
        {
            "candidate_id": "c22_pro_thinking_002",
            "reason": "incidental",
            "explanation": "The historical aside should not influence this lesson concept set.",
        },
    ]


def test_semantic_reduce_input_rejects_unknown_candidate_ids_before_model_call():
    registry = build_candidate_registry(
        scope_id="lesson-2026-05-05-bow",
        source_artifact="source_ledger.json",
        candidate_sources=[
            {
                "namespace": "c22_pro_thinking",
                "artifact_type": "self_study_extraction",
                "artifact_path": "lessons/lesson-2026-05-05-bow/self_studies/22/self_study_extraction.json",
                "lesson_id": "lesson-2026-05-05-bow",
                "self_study_id": "22",
                "model_route": "Pro Thinking",
                "evidence_type": "source_body",
                "candidates": [
                    {
                        "candidate_id": "candidate-22-001",
                        "label": "Bag-of-Words count vectors",
                        "description": "Bag-of-Words represents text as word-count vectors.",
                        "coverage_criteria": ["Student can explain count-vector representation."],
                    }
                ],
            }
        ],
    )

    with pytest.raises(ValueError, match="unknown semantic reduce candidate IDs: missing"):
        build_reduce_input(
            stage_name="lesson_reduce",
            scope={"id": "lesson-2026-05-05-bow"},
            registry=registry,
            input_candidate_ids=["c22_pro_thinking_001", "missing"],
            prompt="Reduce these candidates.",
            prompt_path="prompts/lesson_reduce.md",
            model_route="Pro Thinking",
        )
