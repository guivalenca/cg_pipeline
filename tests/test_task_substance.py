"""The task-substance parser and its files; no model, no transport."""

from pathlib import Path

import pytest

from universe.harness import load_prompt, load_tool
from universe.task_substance import DROPPED, build_parser, substance_of
from universe.task_substance_report import render_verdict

TOOL_PATH = Path(__file__).resolve().parents[1] / "prompts" / "task-substance" / "tool-v004.json"


# --- reading verdicts back -------------------------------------------------


def test_a_legacy_substantive_task_carries_the_verdict():
    item = {"error": None, "response": '{"verdict": "substantive"}'}
    assert substance_of(item) == {"verdict": "substantive"}


def test_a_legacy_trivial_task_carries_the_verdict():
    item = {"error": None, "response": '{"verdict": "trivial"}'}
    assert substance_of(item) == {"verdict": "trivial"}


def test_an_unsure_task_carries_the_verdict():
    item = {"error": None, "response": '{"verdict": "unsure"}'}
    assert substance_of(item) == {"verdict": "unsure"}


def test_a_does_not_work_task_carries_the_verdict():
    item = {"error": None, "response": '{"verdict": "does_not_work"}'}
    assert substance_of(item) == {"verdict": "does_not_work"}


def test_a_verdict_carries_a_nonblank_reason_when_present():
    item = {"error": None, "response": '{"verdict": "does_not_work", "reason": "It asks about the document."}'}
    assert substance_of(item) == {
        "verdict": "does_not_work",
        "reason": "It asks about the document.",
    }


def test_a_missing_or_blank_reason_does_not_make_a_verdict_unparseable():
    assert substance_of({"error": None, "response": '{"verdict": "works"}'}) == {"verdict": "works"}
    assert substance_of({"error": None, "response": '{"verdict": "unsure", "reason": "  "}'}) == {"verdict": "unsure"}


def test_does_not_work_is_a_dropped_verdict():
    assert "does_not_work" in DROPPED


def test_a_does_not_work_verdict_renders_as_its_raw_name():
    assert render_verdict("r0001", {"verdict": "does_not_work"}) == [
        "- r0001: does_not_work"
    ]


def test_a_verdict_reason_renders_on_its_run_line():
    assert render_verdict("r0001", {"verdict": "does_not_work", "reason": "It is document trivia."}) == [
        "- r0001: does_not_work — It is document trivia."
    ]


def test_a_fixable_task_carries_delivered_corrections():
    item = {
        "error": None,
        "response": '{"verdict": "fixable", "task": "Ask about stopwords.", "answer": "They add little meaning."}',
    }
    assert substance_of(item) == {
        "verdict": "fixable",
        "task": "Ask about stopwords.",
        "answer": "They add little meaning.",
    }


def test_a_fixable_verdict_without_a_nonblank_correction_is_unparseable():
    item = {"error": None, "response": '{"verdict": "fixable", "task": "  "}'}
    assert substance_of(item) == "unparseable"


@pytest.mark.parametrize("verdict", ["works", "does_not_work", "beyond_repair"])
def test_nonfixable_verdicts_drop_stray_corrections(verdict):
    item = {
        "error": None,
        "response": f'{{"verdict": "{verdict}", "task": "Ignore this", "answer": "Ignore this too"}}',
    }
    assert substance_of(item) == {"verdict": verdict}


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
    prompt = load_prompt("task-substance", "v004", require_body=False)
    assert "Use the report_check tool" in prompt.template
    assert "{{task}}" in prompt.template and "{{answer}}" in prompt.template
    assert "{{body}}" not in prompt.template


def test_a_bodyless_prompt_still_fails_where_a_body_is_required():
    with pytest.raises(SystemExit):
        load_prompt("task-substance", "v003")


def test_the_verdict_only_tool_definition_loads_and_forces_report_check():
    payload = load_tool(str(TOOL_PATH))
    assert payload["tool_choice"]["function"]["name"] == "report_check"
    parameters = payload["tools"][0]["function"]["parameters"]
    assert parameters["properties"] == {
        "verdict": {
            "type": "string",
            "enum": ["works", "does_not_work", "unsure"],
            "description": "works when the task does its job as it is; does_not_work when it does not; unsure when you cannot tell",
        },
        "reason": {
            "type": "string",
            "description": "The reason for the verdict, in one sentence.",
        },
    }
    assert parameters["required"] == ["verdict", "reason"]


def test_substance_cli_requires_the_support_triage_witness():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            [
                "run",
                "--prompt",
                "v004",
                "--model",
                "model",
                "--gen-runs",
                "generation",
                "--tool",
                str(TOOL_PATH),
            ]
        )
