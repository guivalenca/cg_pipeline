"""The task-granularity parser and its files; no model, no transport."""

from pathlib import Path

import pytest

from universe.harness import load_prompt, load_tool
from universe.task_granularity import granularity_of

TOOL_PATH = (
    Path(__file__).resolve().parents[1]
    / "prompts"
    / "task-granularity"
    / "tool-v001.json"
)


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


# --- the stage's files ------------------------------------------------------


def test_the_prompt_reads_task_and_answer_and_no_source():
    prompt = load_prompt("task-granularity", "v004", require_body=False)
    assert "{{task}}" in prompt.template and "{{answer}}" in prompt.template
    assert "{{body}}" not in prompt.template


def test_the_tool_definition_loads_and_forces_report_granularity():
    payload = load_tool(str(TOOL_PATH))
    assert payload["tool_choice"]["function"]["name"] == "report_granularity"
    parameters = payload["tools"][0]["function"]["parameters"]
    assert parameters["properties"]["verdict"]["enum"] == [
        "single",
        "composite",
        "unsure",
    ]
    assert "only when the verdict is composite" in parameters["properties"]["parts"][
        "description"
    ]
    assert parameters["required"] == ["verdict"]
