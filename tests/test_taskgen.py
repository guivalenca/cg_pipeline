"""The task-generation gate and its parsers; no model, no transport."""

from pathlib import Path

import pytest

from universe.harness import load_prompt, load_tool
from universe.taskgen import split_by_verdict, tasks_of

TOOL_PATH = Path(__file__).resolve().parents[1] / "prompts" / "task-generation" / "tool-v001.json"


def passage(first: int, last: int) -> dict:
    return {
        "id": f"art:b2:p{first:04d}-{last:04d}",
        "artifact_id": "art",
        "blocker_version": "2",
        "first_seq": first,
        "last_seq": last,
    }


# --- the gate ---------------------------------------------------------------


def test_only_unanimous_not_filler_gets_a_call():
    kept_one, kept_two = passage(4, 9), passage(10, 12)
    filler = passage(1, 3)
    mixed = passage(13, 33)
    verdicts = {
        kept_one["id"]: {"not_filler"},
        kept_two["id"]: {"not_filler"},
        filler["id"]: {"filler"},
        mixed["id"]: {"not_filler", "filler"},
    }
    kept, dropped, unjudged = split_by_verdict([kept_one, filler, kept_two, mixed], verdicts)
    assert kept == [kept_one, kept_two]
    assert dropped == [filler, mixed]
    assert unjudged == []


def test_unsure_is_a_blocker_not_a_pass():
    unsure = passage(5, 8)
    kept, dropped, _ = split_by_verdict([unsure], {unsure["id"]: {"unsure"}})
    assert kept == [] and dropped == [unsure]


def test_a_passage_with_no_verdict_is_reported_as_unjudged():
    silent = passage(7, 7)
    kept, dropped, unjudged = split_by_verdict([silent], {})
    assert unjudged == [silent]
    assert kept == [] and dropped == []


# --- reading tasks back -----------------------------------------------------


def test_tasks_of_returns_the_reported_pairs():
    item = {
        "error": None,
        "response": '{"tasks": [{"task": "Explain X.", "answer": "Because Y."}]}',
    }
    assert tasks_of(item) == [{"task": "Explain X.", "answer": "Because Y."}]


def test_tasks_of_accepts_an_empty_list():
    assert tasks_of({"error": None, "response": '{"tasks": []}'}) == []


@pytest.mark.parametrize(
    "item",
    [
        {"error": "HTTP 502", "response": None},
        {"error": None, "response": "prose, not a tool call"},
        {"error": None, "response": '{"verdict": "not_filler"}'},
        {"error": None, "response": '{"tasks": [{"task": "Explain X."}]}'},
        {"error": None, "response": '{"tasks": [{"task": "", "answer": "Y"}]}'},
        {"error": None, "response": '{"tasks": "one big string"}'},
    ],
)
def test_tasks_of_names_what_it_cannot_use(item):
    assert tasks_of(item) in ("error", "unparseable")


# --- the stage's files ------------------------------------------------------


def test_the_prompt_declares_the_tool_and_both_fields():
    prompt = load_prompt("task-generation", "v001")
    assert "Use the report_tasks tool" in prompt.template
    assert "{{body}}" in prompt.template and "{{passage}}" in prompt.template


def test_the_tool_definition_loads_and_forces_report_tasks():
    payload = load_tool(str(TOOL_PATH))
    assert payload["tool_choice"]["function"]["name"] == "report_tasks"
    parameters = payload["tools"][0]["function"]["parameters"]
    entry = parameters["properties"]["tasks"]["items"]
    assert entry["required"] == ["task", "answer"]
