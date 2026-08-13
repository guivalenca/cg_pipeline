"""The task-revision parser and its files; no model, no transport."""

import pytest

from universe.task_revision import revision_of


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
