"""Regression coverage for the structure-review audit repairs."""

import argparse
from contextlib import nullcontext

import pytest

from universe import task_granularity, task_substance, task_triage
from universe import task_revision_report as revision_report


def test_revision_report_task_set_must_match(monkeypatch):
    monkeypatch.setattr(
        revision_report,
        "collect",
        lambda *_: (
            [{"id": "r1", "label": "one"}, {"id": "r2", "label": "two"}],
            {("r1", "t1"): {"verdict": "stands", "task": None},
             ("r2", "t2"): {"verdict": "stands", "task": None}},
        ),
    )

    with pytest.raises(SystemExit, match="r2: task_id mismatch. Missing: t1. Extra: t2."):
        revision_report.render_runs(object(), ["r1", "r2"])


def test_task_substance_refuses_rewritten_composites(monkeypatch):
    args = argparse.Namespace(
        prompt="v004", tool=None, extra=None, gen_runs=["gen"], passages_from=None,
        revision_run="revision", granularity_run="split", parts_revision_run=None,
        model="model", temperature=None, max_tokens=1, workers=1,
    )
    monkeypatch.setattr(task_substance, "connect", lambda: nullcontext(object()))
    monkeypatch.setattr(task_substance, "load_prompt", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(task_substance, "materialize", lambda *_: {"tasks_new": 0, "tasks_existing": 0})
    monkeypatch.setattr(
        task_substance, "fetch_tasks_for_runs", lambda *_: [{"id": "base:t01", "passage_id": "p1"}]
    )
    monkeypatch.setattr(
        task_substance, "fetch_revisions",
        lambda *_: {"base:t01": {"verdict": "rewritten", "task": "replacement"}},
    )
    monkeypatch.setattr(
        task_substance, "fetch_items",
        lambda *_: [{"id": "split-1", "task_id": "base:t01", "error": None,
                      "response": '{"verdict": "composite", "parts": [{"task": "one", "answer": "one"}]}' }],
    )

    with pytest.raises(SystemExit, match="rewrote composite task"):
        task_substance.cmd_run(args)


def test_task_triage_replaces_composites_with_parts(monkeypatch):
    args = argparse.Namespace(
        prompt="v001", tool=None, extra=None, gen_runs=["gen"], passages_from=None,
        revision_run=None, granularity_runs=["split"], model="model",
        temperature=None, max_tokens=1, workers=1,
    )
    base_tasks = [
        {"id": "base:composite", "passage_id": "p1"},
        {"id": "base:single", "passage_id": "p1"},
    ]
    parts = [{"id": "split-1:t01", "run_item_id": "split-1", "passage_id": "p1"}]
    seen = []
    monkeypatch.setattr(task_triage, "connect", lambda: nullcontext(object()))
    monkeypatch.setattr(task_triage, "load_prompt", lambda *_: argparse.Namespace(ref="v001", sha="a" * 12))
    monkeypatch.setattr(task_triage, "materialize", lambda *_: {"tasks_new": 0, "tasks_existing": 0})
    monkeypatch.setattr(task_granularity, "materialize_parts", lambda *_: {"tasks_new": 0, "tasks_existing": 0})
    monkeypatch.setattr(task_triage, "fetch_tasks_for_runs", lambda _conn, runs: base_tasks if runs == ["gen"] else parts)
    monkeypatch.setattr(
        task_triage, "fetch_items",
        lambda _conn, run_id: ([{"id": "split-1", "task_id": "base:composite", "error": None,
                                  "response": '{"verdict": "composite", "parts": [{"task": "part", "answer": "answer"}]}' }] if run_id == "split" else []),
    )
    monkeypatch.setattr(task_triage, "build_targets", lambda _conn, tasks: seen.extend(tasks) or [])
    monkeypatch.setattr(task_triage, "ModelClient", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(task_triage, "execute", lambda *_args, **_kwargs: {"run_id": "triage", "status": "ok", "ok": 0, "failed": 0})

    task_triage.cmd_run(args)

    assert [task["id"] for task in seen] == ["base:single", "split-1:t01"]
