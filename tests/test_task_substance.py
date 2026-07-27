"""The task-substance parser and its files; no model, no transport."""

from pathlib import Path

import pytest

from universe.harness import load_prompt, load_tool
from universe.task_substance import substance_of

TOOL_PATH = Path(__file__).resolve().parents[1] / "prompts" / "task-substance" / "tool-v001.json"


# --- reading verdicts back -------------------------------------------------


def test_a_substantive_task_carries_the_verdict():
    item = {"error": None, "response": '{"verdict": "substantive"}'}
    assert substance_of(item) == {"verdict": "substantive"}


def test_a_trivial_task_carries_the_verdict():
    item = {"error": None, "response": '{"verdict": "trivial"}'}
    assert substance_of(item) == {"verdict": "trivial"}


def test_an_unsure_task_carries_the_verdict():
    item = {"error": None, "response": '{"verdict": "unsure"}'}
    assert substance_of(item) == {"verdict": "unsure"}


@pytest.mark.parametrize(
    "item",
    [
        {"error": "HTTP 502", "response": None},
        {"error": None, "response": "prose, not a tool call"},
        {"error": None, "response": '{"verdict": "important"}'},
    ],
)
def test_substance_of_names_what_it_cannot_use(item):
    assert substance_of(item) in ("error", "unparseable")


# --- the stage's files ------------------------------------------------------


def test_the_prompt_reads_task_and_answer_and_no_source():
    prompt = load_prompt("task-substance", "v001", require_body=False)
    assert "Use the report_substance tool" in prompt.template
    assert "{{task}}" in prompt.template and "{{answer}}" in prompt.template
    assert "{{body}}" not in prompt.template


def test_a_bodyless_prompt_still_fails_where_a_body_is_required():
    with pytest.raises(SystemExit):
        load_prompt("task-substance", "v001")


def test_the_tool_definition_loads_and_forces_report_substance():
    payload = load_tool(str(TOOL_PATH))
    assert payload["tool_choice"]["function"]["name"] == "report_substance"
    parameters = payload["tools"][0]["function"]["parameters"]
    assert parameters["properties"]["verdict"]["enum"] == ["substantive", "trivial", "unsure"]
    assert parameters["required"] == ["verdict"]
