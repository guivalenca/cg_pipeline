"""Regression coverage for the structure-review audit repairs."""

import argparse
from contextlib import nullcontext
from types import SimpleNamespace

import pytest

from universe import task_substance, task_triage
from universe import task_revision_report as revision_report
from universe.effective_evidence import effective_task_manifest_sha


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


def test_task_substance_uses_supported_effective_scope_and_stamps_it(monkeypatch):
    args = argparse.Namespace(
        prompt="v004", tool=None, extra=None, gen_runs=["gen"], passages_from=None,
        revision_run="revision", granularity_run="split", parts_revision_run=None,
        triage_run="triage", model="model", temperature=None, max_tokens=1, workers=1,
    )
    conn = object()
    selected = [
        {
            "id": "split-1:t01",
            "artifact_id": "artifact",
            "passage_id": "passage",
            "body": "Supported rewritten part",
            "answer": "Answer",
        }
    ]
    captured = {}
    monkeypatch.setattr(task_substance, "connect", lambda: nullcontext(conn))
    monkeypatch.setattr(
        task_substance, "load_prompt",
        lambda *_args, **_kwargs: argparse.Namespace(ref="v004", sha="a" * 12),
    )
    monkeypatch.setattr(
        task_substance,
        "effective_tasks",
        lambda _conn, **kwargs: captured.update(scope=kwargs) or selected,
    )
    monkeypatch.setattr(task_substance, "build_targets", lambda _conn, tasks: [object()])
    monkeypatch.setattr(task_substance, "ModelClient", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        task_substance,
        "execute",
        lambda *_args, **kwargs: captured.update(params=kwargs["run_params"])
        or {"run_id": "substance", "status": "done"},
    )
    monkeypatch.setattr(task_substance, "fetch_items", lambda *_args: [])
    monkeypatch.setattr(task_substance.report, "aggregate_usage", lambda _items: {})

    task_substance.cmd_run(args)

    assert captured["scope"] == {
        "generation_runs": ["gen"],
        "passages_from": None,
        "granularity_run": "split",
        "revision_run": "revision",
        "parts_revision_run": None,
        "triage_run": "triage",
    }
    assert captured["params"]["effective_task_manifest_sha"] == (
        effective_task_manifest_sha(selected)
    )


def test_task_triage_uses_post_split_scope_and_stamps_it(monkeypatch):
    args = argparse.Namespace(
        prompt="v001", tool=None, extra=None, gen_runs=["gen"], passages_from=None,
        revision_run=None, granularity_runs=["split"], model="model",
        temperature=None, max_tokens=1, workers=1,
    )
    selected = [
        {
            "id": "base:single",
            "artifact_id": "artifact",
            "passage_id": "p1",
            "body": "Single",
            "answer": "A",
        },
        {
            "id": "split-1:t01",
            "artifact_id": "artifact",
            "passage_id": "p1",
            "body": "Part",
            "answer": "B",
        },
    ]
    captured = {}
    monkeypatch.setattr(task_triage, "connect", lambda: nullcontext(object()))
    monkeypatch.setattr(task_triage, "load_prompt", lambda *_: argparse.Namespace(ref="v001", sha="a" * 12))
    monkeypatch.setattr(
        task_triage,
        "post_split_tasks",
        lambda _conn, **kwargs: captured.update(scope=kwargs) or selected,
    )
    monkeypatch.setattr(task_triage, "build_targets", lambda _conn, tasks: [object()])
    monkeypatch.setattr(task_triage, "ModelClient", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        task_triage,
        "execute",
        lambda *_args, **kwargs: captured.update(params=kwargs["run_params"])
        or {"run_id": "triage", "status": "done", "ok": 0, "failed": 0},
    )
    monkeypatch.setattr(task_triage, "fetch_items", lambda *_args: [])
    monkeypatch.setattr(task_triage.report, "aggregate_usage", lambda _items: {})

    task_triage.cmd_run(args)

    assert captured["scope"] == {
        "generation_runs": ["gen"],
        "granularity_runs": ["split"],
    }
    assert captured["params"]["effective_task_manifest_sha"] == (
        effective_task_manifest_sha(selected)
    )
