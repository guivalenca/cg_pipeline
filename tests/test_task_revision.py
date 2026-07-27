"""The task-revision parser and its files; no model, no transport."""

from pathlib import Path

import pytest

from universe.harness import load_prompt, load_tool
from universe.task_revision import revision_of

TOOL_PATH = Path(__file__).resolve().parents[1] / "prompts" / "task-revision" / "tool-v001.json"


# --- reading revisions back -------------------------------------------------


def test_a_task_that_stands_carries_no_rewrite():
    item = {"error": None, "response": '{"verdict": "stands"}'}
    assert revision_of(item) == {"verdict": "stands", "task": None}


def test_a_rewrite_carries_the_new_task():
    item = {"error": None, "response": '{"verdict": "rewritten", "task": "Explain X."}'}
    assert revision_of(item) == {"verdict": "rewritten", "task": "Explain X."}


def test_a_stray_task_beside_a_non_rewrite_verdict_is_dropped():
    item = {"error": None, "response": '{"verdict": "unfixable", "task": "Explain X."}'}
    assert revision_of(item) == {"verdict": "unfixable", "task": None}


@pytest.mark.parametrize(
    "item",
    [
        {"error": "HTTP 502", "response": None},
        {"error": None, "response": "prose, not a tool call"},
        {"error": None, "response": '{"verdict": "supported"}'},
        {"error": None, "response": '{"verdict": "rewritten"}'},
        {"error": None, "response": '{"verdict": "rewritten", "task": "  "}'},
        {"error": None, "response": '{"tasks": []}'},
    ],
)
def test_revision_of_names_what_it_cannot_use(item):
    assert revision_of(item) in ("error", "unparseable")


# --- the stage's files ------------------------------------------------------


def test_the_prompt_reads_task_and_answer_and_no_source():
    prompt = load_prompt("task-revision", "v001", require_body=False)
    assert "Use the report_revision tool" in prompt.template
    assert "{{task}}" in prompt.template and "{{answer}}" in prompt.template
    assert "{{body}}" not in prompt.template


def test_a_bodyless_prompt_still_fails_where_a_body_is_required():
    with pytest.raises(SystemExit):
        load_prompt("task-revision", "v001")


def test_the_tool_definition_loads_and_forces_report_revision():
    payload = load_tool(str(TOOL_PATH))
    assert payload["tool_choice"]["function"]["name"] == "report_revision"
    parameters = payload["tools"][0]["function"]["parameters"]
    assert parameters["properties"]["verdict"]["enum"] == ["stands", "rewritten", "unfixable"]
    assert parameters["required"] == ["verdict"]
