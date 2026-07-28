"""The task-fact parser; no model, no transport."""

import pytest

from universe.task_fact import fact_of


def test_an_errored_item_is_an_error():
    assert fact_of({"error": "HTTP 502", "response": None}) == "error"


@pytest.mark.parametrize(
    "response",
    [
        "prose, not a tool call",
        "[]",
        '{"verdict": "other", "reason": "Not a fact verdict."}',
        '{"verdict": "fact"}',
        '{"verdict": "not_fact", "reason": ""}',
        '{"verdict": "fact", "reason": "  "}',
    ],
)
def test_an_invalid_response_is_unparseable(response):
    assert fact_of({"error": None, "response": response}) == "unparseable"


@pytest.mark.parametrize("verdict", ["fact", "not_fact"])
def test_every_verdict_carries_a_stripped_reason(verdict):
    item = {
        "error": None,
        "response": (
            f'{{"verdict": "{verdict}",'
            ' "reason": "  The requested response determines if it is a fact.  "}'
        ),
    }
    assert fact_of(item) == {
        "verdict": verdict,
        "reason": "The requested response determines if it is a fact.",
    }
