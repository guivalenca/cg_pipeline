"""Usage accounting in static run reports."""

from universe.report import aggregate_usage


def test_usage_ledger_counts_each_attempt_once_instead_of_the_final_twice():
    items = [
        {
            "usage": {
                # These are the final attempt repeated for compatibility and
                # must not be added on top of the authoritative ledger.
                "prompt_tokens": 20,
                "completion_tokens": 5,
                "total_tokens": 25,
                "cost": 0.003,
                "retry_count": 1,
                "attempts": [
                    {
                        "status": "failed",
                        "usage": {
                            "prompt_tokens": 10,
                            "completion_tokens": 0,
                            "total_tokens": 10,
                            "cost": 0.002,
                            "prompt_tokens_details": {"cached_tokens": 2},
                        },
                    },
                    {
                        "status": "succeeded",
                        "usage": {
                            "prompt_tokens": 20,
                            "completion_tokens": 5,
                            "total_tokens": 25,
                            "cost": 0.003,
                            "prompt_tokens_details": {"cached_tokens": 3},
                            "completion_tokens_details": {"reasoning_tokens": 2},
                        },
                    },
                ],
            }
        }
    ]

    assert aggregate_usage(items) == {
        "prompt_tokens": 30,
        "completion_tokens": 5,
        "total_tokens": 35,
        "cost": 0.005,
        "cached_tokens": 5,
        "reasoning_tokens": 2,
    }


def test_usage_without_attempt_ledger_keeps_legacy_aggregation():
    items = [
        {
            "usage": {
                "prompt_tokens": 7,
                "completion_tokens": 3,
                "total_tokens": 10,
                "cost": 0.001,
                "retry_count": 2,
                "prompt_tokens_details": {"cached_tokens": 4},
            }
        },
        {
            "usage": {
                "prompt_tokens": 11,
                "completion_tokens": 2,
                "total_tokens": 13,
                "cost": 0.002,
                "retry_count": 1,
                "completion_tokens_details": {"reasoning_tokens": 1},
            }
        },
    ]

    assert aggregate_usage(items) == {
        "prompt_tokens": 18,
        "completion_tokens": 5,
        "total_tokens": 23,
        "cost": 0.003,
        "cached_tokens": 4,
        "reasoning_tokens": 1,
        "retry_count": 3,
    }
