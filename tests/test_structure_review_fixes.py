"""Regression coverage for the structure-review audit repairs."""

import pytest

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
