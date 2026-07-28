"""The task-knowledge parser; no model, no transport."""

import pytest

from universe.task_knowledge import knowledge_of


def test_an_errored_item_is_an_error():
    assert knowledge_of({"error": "HTTP 502", "response": None}) == "error"


@pytest.mark.parametrize(
    "response",
    [
        "prose, not a tool call",
        "[]",
        '{"verdict": "skill", "reason": "Not a knowledge verdict."}',
        '{"verdict": "fact"}',
        '{"verdict": "concept", "reason": ""}',
        '{"verdict": "procedure", "reason": "  "}',
    ],
)
def test_an_invalid_response_is_unparseable(response):
    assert knowledge_of({"error": None, "response": response}) == "unparseable"


@pytest.mark.parametrize("verdict", ["fact", "concept", "procedure", "unsure"])
def test_every_verdict_carries_a_stripped_reason(verdict):
    item = {
        "error": None,
        "response": (
            f'{{"verdict": "{verdict}",'
            ' "reason": "  The requested response determines the knowledge kind.  "}'
        ),
    }
    assert knowledge_of(item) == {
        "verdict": verdict,
        "reason": "The requested response determines the knowledge kind.",
    }
