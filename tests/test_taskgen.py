"""The task-generation gate and its parsers; no model, no transport."""

from pathlib import Path

import pytest

from universe.harness import load_prompt, load_tool
from universe.taskgen import build_parser, split_by_verdict, tasks_of

TOOL_PATH = Path(__file__).resolve().parents[1] / "prompts" / "task-generation" / "tool-v002.json"


def passage(first: int, last: int) -> dict:
    return {
        "id": f"art:b2:p{first:04d}-{last:04d}",
        "artifact_id": "art",
        "blocker_version": "2",
        "first_seq": first,
        "last_seq": last,
    }


# --- the gate ---------------------------------------------------------------


def test_keep_and_unknown_are_preserved_while_drop_is_not():
    kept, unknown, agreement = passage(4, 9), passage(10, 12), passage(13, 16)
    dropped = passage(1, 3)
    verdicts = {
        kept["id"]: {"keep"},
        unknown["id"]: {"unknown"},
        agreement["id"]: {"keep", "unknown"},
        dropped["id"]: {"drop"},
    }
    preserved, removed, unjudged = split_by_verdict(
        [kept, dropped, unknown, agreement], verdicts
    )
    assert preserved == [kept, unknown, agreement]
    assert removed == [dropped]
    assert unjudged == []


def test_legacy_not_filler_still_passes_and_unsure_does_not():
    kept, unsure = passage(5, 8), passage(9, 11)
    preserved, dropped, unjudged = split_by_verdict(
        [kept, unsure],
        {kept["id"]: {"not_filler"}, unsure["id"]: {"unsure"}},
    )
    assert preserved == [kept]
    assert dropped == [unsure]
    assert unjudged == []


def test_refine_and_unusable_results_are_not_terminal():
    refine, malformed = passage(5, 8), passage(9, 11)
    kept, dropped, unjudged = split_by_verdict(
        [refine, malformed],
        {refine["id"]: {"refine"}, malformed["id"]: {"unparseable"}},
    )
    assert kept == [] and dropped == []
    assert unjudged == [refine, malformed]


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
    prompt = load_prompt("task-generation", "v005")
    assert "Use the report_tasks tool" in prompt.template
    assert "If the passage supports no such task, report an empty tasks array." in (
        prompt.template
    )
    assert "do not invent a task" not in prompt.template
    assert "{{body}}" in prompt.template and "{{passage}}" in prompt.template


def test_the_tool_definition_loads_and_forces_report_tasks():
    payload = load_tool(str(TOOL_PATH))
    assert payload["tool_choice"]["function"]["name"] == "report_tasks"
    parameters = payload["tools"][0]["function"]["parameters"]
    tasks = parameters["properties"]["tasks"]
    assert "minItems" not in tasks
    entry = tasks["items"]
    assert entry["required"] == ["task", "answer"]


def test_cleanup_gate_does_not_require_legacy_cut_or_triage_runs():
    args = build_parser().parse_args(
        [
            "run",
            "--prompt",
            "v005",
            "--model",
            "fake/model",
            "--cleanup",
            "pc-test",
            "--tool",
            str(TOOL_PATH),
        ]
    )
    assert args.cleanup == "pc-test"
    assert args.cuts_runs is None and args.triage_runs is None
