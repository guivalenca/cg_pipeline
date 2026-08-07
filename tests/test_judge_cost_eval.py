from universe.judge_cost_eval import (
    candidate_pairs,
    normalized_pair,
    score_candidate_policy,
    score_model_results,
)


def _item(task_id, statement, *, modality="explain", knowledge="concept"):
    return {
        "id": task_id,
        "statement": statement,
        "modality": modality,
        "knowledge": knowledge,
        "body": f"task {task_id}",
        "answer": f"answer {task_id}",
    }


def test_candidate_policy_can_require_reciprocal_semantic_neighbors():
    data = {
        "items": [
            _item("a", "alpha"),
            _item("b", "beta"),
            _item("c", "gamma"),
        ],
        "similarities": [
            {"a": "a", "b": "b", "similarity": 0.90},
            {"a": "a", "b": "c", "similarity": 0.80},
            {"a": "b", "b": "c", "similarity": 0.70},
        ],
        "cases": [],
    }

    union, _ = candidate_pairs(
        data, floor=0.70, semantic_cap=1, lexical_k=0
    )
    reciprocal, _ = candidate_pairs(
        data,
        floor=0.70,
        semantic_cap=1,
        lexical_k=0,
        reciprocal_semantic=True,
    )

    assert union == {normalized_pair("a", "b"), normalized_pair("a", "c")}
    assert reciprocal == {normalized_pair("a", "b")}


def test_candidate_policy_filters_incompatible_axes_and_scores_gold_recall():
    data = {
        "items": [
            _item("a", "shared alpha"),
            _item("b", "shared beta"),
            _item("d", "shared delta", modality="do"),
        ],
        "similarities": [
            {"a": "a", "b": "b", "similarity": 0.91},
            {"a": "a", "b": "d", "similarity": 0.99},
            {"a": "b", "b": "d", "similarity": 0.98},
        ],
        "cases": [
            {
                "id": "positive",
                "a": "a",
                "b": "b",
                "bucket": "gold",
                "gold_merge": True,
            },
            {
                "id": "negative",
                "a": "a",
                "b": "d",
                "bucket": "gold",
                "gold_merge": False,
            },
        ],
    }

    pairs, _ = candidate_pairs(
        data, floor=0.70, semantic_cap=3, lexical_k=0
    )
    score = score_candidate_policy(data, pairs)

    assert pairs == {normalized_pair("a", "b")}
    assert score["gold_positive_recall"] == 1.0
    assert score["known_negative_candidates"] == 0


def test_model_score_tracks_quality_cost_and_directionality():
    data = {
        "cases": [
            {
                "id": "positive",
                "a": "a",
                "b": "b",
                "bucket": "gold",
                "gold_merge": True,
                "gold_a_clear_yes": True,
                "gold_b_clear_yes": True,
            },
            {
                "id": "negative",
                "a": "c",
                "b": "d",
                "bucket": "gold",
                "gold_merge": False,
                "gold_a_clear_yes": False,
                "gold_b_clear_yes": False,
            },
            {
                "id": "ambiguous",
                "a": "e",
                "b": "f",
                "bucket": "ambiguous",
                "gold_merge": None,
            },
        ]
    }
    results = [
        {
            "case_id": "positive",
            "parsed": {
                "verdict_a_to_b": "clear_yes",
                "verdict_b_to_a": "clear_yes",
            },
            "usage": {"cost": 0.01, "prompt_tokens": 100, "completion_tokens": 20},
        },
        {
            "case_id": "negative",
            "parsed": {
                "verdict_a_to_b": "clear_no",
                "verdict_b_to_a": "unlikely",
            },
            "usage": {"cost": 0.02, "prompt_tokens": 110, "completion_tokens": 30},
        },
    ]

    score = score_model_results(data, results)

    assert score["cases"] == 2
    assert score["merge_accuracy"] == 1.0
    assert score["false_merges"] == 0
    assert score["missed_merges"] == 0
    assert score["direction_accuracy"] == 1.0
    assert score["total_cost"] == 0.03
    assert score["prompt_tokens"] == 210
    assert score["completion_tokens"] == 50


def test_model_score_reports_failures_without_treating_them_as_non_merges():
    data = {
        "cases": [
            {
                "id": "failed-negative",
                "a": "a",
                "b": "b",
                "bucket": "gold",
                "gold_merge": False,
                "gold_a_clear_yes": False,
                "gold_b_clear_yes": False,
            }
        ]
    }

    score = score_model_results(
        data,
        [{"case_id": "failed-negative", "parsed": None, "usage": None}],
    )

    assert score["scored_cases"] == 0
    assert score["failed_calls"] == 1
    assert score["merge_accuracy"] is None
    assert score["false_merges"] == 0
