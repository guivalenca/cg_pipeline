"""The task-revision parser and its files; no model, no transport."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from universe.harness import load_prompt, load_tool
from universe import task_granularity, task_revision
from universe.task_revision import revision_of

TOOL_PATH = Path(__file__).resolve().parents[1] / "prompts" / "task-revision" / "tool-v003.json"


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


# --- overlaying revisions onto the tasks triage judges ----------------------


def task_row(name: str) -> dict:
    return {"id": name, "body": f"original {name}", "answer": "A."}


def test_apply_revisions_swaps_rewrites_drops_unfixables_keeps_stands():
    from universe.task_triage import apply_revisions

    tasks = [task_row("t1"), task_row("t2"), task_row("t3")]
    revisions = {
        "t1": {"verdict": "stands", "task": None},
        "t2": {"verdict": "rewritten", "task": "better t2"},
        "t3": {"verdict": "unfixable", "task": None},
    }
    kept, dropped, unjudged = apply_revisions(tasks, revisions)
    assert [t["body"] for t in kept] == ["original t1", "better t2"]
    assert [t["id"] for t in dropped] == ["t3"]
    assert unjudged == []


def test_a_task_the_revision_run_never_saw_is_unjudged():
    from universe.task_triage import apply_revisions

    silent, broken = task_row("t1"), task_row("t2")
    kept, dropped, unjudged = apply_revisions([silent, broken], {"t2": "unparseable"})
    assert kept == [] and dropped == []
    assert unjudged == [silent, broken]


# --- the stage's files ------------------------------------------------------


def test_the_prompt_reads_task_and_answer_and_no_source():
    prompt = load_prompt("task-revision", "v004", require_body=False)
    assert "Use the report_revision tool" in prompt.template
    assert "{{task}}" in prompt.template and "{{answer}}" in prompt.template
    assert "{{body}}" not in prompt.template


def test_a_bodyless_prompt_still_fails_where_a_body_is_required():
    with pytest.raises(SystemExit):
        load_prompt("task-revision", "v004")


def test_the_tool_definition_loads_and_forces_report_revision():
    payload = load_tool(str(TOOL_PATH))
    assert payload["tool_choice"]["function"]["name"] == "report_revision"
    parameters = payload["tools"][0]["function"]["parameters"]
    assert parameters["properties"]["verdict"]["enum"] == ["stands", "rewritten", "unfixable"]
    assert parameters["required"] == ["verdict"]


def test_revision_cli_consumes_only_the_shared_post_split_scope(monkeypatch):
    conn = object()
    selected = [{"id": "part-1", "artifact_id": "artifact", "body": "Part", "answer": "A"}]
    seen = {}

    class Connected:
        def __enter__(self):
            return conn

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(task_revision, "connect", lambda: Connected())
    monkeypatch.setattr(
        task_revision,
        "materialize",
        lambda *_args: {"tasks_new": 0, "tasks_existing": 1},
    )
    monkeypatch.setattr(
        task_granularity,
        "materialize_parts",
        lambda *_args: {"tasks_new": 0, "tasks_existing": 1},
    )

    def post_split(_conn, *, generation_runs, granularity_runs):
        seen["scope"] = (generation_runs, granularity_runs)
        return selected

    monkeypatch.setattr(task_revision, "post_split_tasks", post_split)
    monkeypatch.setattr(
        task_revision,
        "build_targets",
        lambda _conn, tasks: seen.setdefault("tasks", tasks) or [object()],
    )
    monkeypatch.setattr(
        task_revision,
        "load_prompt",
        lambda *_args, **_kwargs: SimpleNamespace(ref="task-revision/v004", sha="sha"),
    )
    monkeypatch.setattr(task_revision, "load_tool", lambda *_args: {})
    monkeypatch.setattr(task_revision, "ModelClient", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        task_revision,
        "execute",
        lambda *_args, **_kwargs: {
            "run_id": "revision-run",
            "status": "done",
            "ok": 1,
            "failed": 0,
        },
    )
    monkeypatch.setattr(
        task_revision,
        "fetch_items",
        lambda *_args: [
            {"error": None, "response": '{"verdict":"stands"}', "duration_ms": 0}
        ],
    )
    monkeypatch.setattr(task_revision.report, "aggregate_usage", lambda _items: {})

    task_revision.cmd_run(
        SimpleNamespace(
            gen_runs=["generation-run"],
            granularity_runs=["granularity-run"],
            passages_from=None,
            prompt="v004",
            model="model",
            tool="tool.json",
            extra=None,
            temperature=None,
            max_tokens=100,
            workers=1,
        )
    )

    assert seen["scope"] == (["generation-run"], ["granularity-run"])
    assert seen["tasks"] == selected
