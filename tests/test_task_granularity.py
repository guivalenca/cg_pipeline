"""The task-granularity parser and its files; no model, no transport."""

import pytest

from universe.task_granularity import granularity_of


# --- reading granularity verdicts back --------------------------------------


def test_a_single_task_carries_no_parts():
    item = {"error": None, "response": '{"verdict": "single"}'}
    assert granularity_of(item) == {"verdict": "single", "parts": None}


def test_an_unsure_task_carries_no_parts():
    item = {"error": None, "response": '{"verdict": "unsure"}'}
    assert granularity_of(item) == {"verdict": "unsure", "parts": None}


def test_a_composite_task_carries_its_parts():
    item = {
        "error": None,
        "response": (
            '{"verdict": "composite", "parts": ['
            '{"task": "Explain X.", "answer": "X."},'
            '{"task": "Explain Y.", "answer": "Y."}'
            "]}"
        ),
    }
    assert granularity_of(item) == {
        "verdict": "composite",
        "parts": [
            {"task": "Explain X.", "answer": "X."},
            {"task": "Explain Y.", "answer": "Y."},
        ],
    }


@pytest.mark.parametrize(
    "response",
    [
        '{"verdict": "composite"}',
        '{"verdict": "composite", "parts": []}',
        (
            '{"verdict": "composite", "parts": ['
            '{"task": "  ", "answer": "An answer."}'
            "]}"
        ),
    ],
)
def test_a_composite_without_usable_parts_is_unparseable(response):
    assert granularity_of({"error": None, "response": response}) == "unparseable"


def test_stray_parts_beside_a_single_verdict_are_dropped():
    item = {
        "error": None,
        "response": (
            '{"verdict": "single", "parts": ['
            '{"task": "Explain X.", "answer": "X."}'
            "]}"
        ),
    }
    assert granularity_of(item) == {"verdict": "single", "parts": None}


def test_an_error_item_is_an_error():
    assert granularity_of({"error": "HTTP 502", "response": None}) == "error"


def test_a_non_json_response_is_unparseable():
    item = {"error": None, "response": "prose, not a tool call"}
    assert granularity_of(item) == "unparseable"
