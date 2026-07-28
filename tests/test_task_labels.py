"""Chain-relative labels for base tasks and materialized granularity parts."""

import pytest

from universe import task_labels


def test_label_map_filters_revises_numbers_and_labels_parts(monkeypatch):
    base_tasks = [
        {"id": "g-1:t01", "passage_id": "p1"},
        {"id": "g-1:t02", "passage_id": "outside"},
        {"id": "g-2:t01", "passage_id": "p2"},
        {"id": "g-2:t02", "passage_id": "p2"},
    ]
    part_tasks = [
        {"id": "split-1:t01", "run_item_id": "split-1", "seq": 1},
        {"id": "split-1:t02", "run_item_id": "split-1", "seq": 2},
        {"id": "split-2:t01", "run_item_id": "split-2", "seq": 1},
    ]
    materialized = []

    def fetch_tasks_for_runs(_conn, run_ids):
        return base_tasks if run_ids == ["gen"] else part_tasks

    monkeypatch.setattr(task_labels, "fetch_tasks_for_runs", fetch_tasks_for_runs)
    monkeypatch.setattr(
        task_labels,
        "fetch_passages_for_runs",
        lambda _conn, _run_ids: [{"id": "p1"}, {"id": "p2"}],
    )
    monkeypatch.setattr(
        task_labels,
        "fetch_revisions",
        lambda _conn, _run_id: {
            "g-1:t01": {"verdict": "stands", "task": None},
            "g-2:t01": {"verdict": "unfixable", "task": None},
            "g-2:t02": {"verdict": "rewritten", "task": "Better"},
        },
    )
    monkeypatch.setattr(
        task_labels,
        "fetch_items",
        lambda _conn, _run_id: [
            {"id": "split-1", "task_id": "g-1:t01"},
            {"id": "split-2", "task_id": "g-2:t02"},
        ],
    )
    monkeypatch.setattr(
        task_labels,
        "materialize_parts",
        lambda _conn, run_id: materialized.append(run_id),
    )

    assert task_labels.label_map(
        object(), ["gen"], ["cuts"], "revision", ["granularity"]
    ) == {
        "g-1:t01": "T01",
        "g-2:t02": "T02",
        "split-1:t01": "T01 part 1",
        "split-1:t02": "T01 part 2",
        "split-2:t01": "T02 part 1",
    }
    assert materialized == ["granularity"]


def test_label_map_rejects_an_incomplete_revision_overlay(monkeypatch):
    monkeypatch.setattr(
        task_labels,
        "fetch_tasks_for_runs",
        lambda _conn, _run_ids: [{"id": "g:t01", "passage_id": "p1"}],
    )
    monkeypatch.setattr(
        task_labels,
        "fetch_passages_for_runs",
        lambda _conn, _run_ids: [{"id": "p1"}],
    )
    monkeypatch.setattr(task_labels, "fetch_revisions", lambda _conn, _run_id: {})

    with pytest.raises(SystemExit, match="no usable revision"):
        task_labels.label_map(object(), ["gen"], ["cuts"], "revision")


def test_label_map_filters_orphaned_parts(monkeypatch):
    monkeypatch.setattr(
        task_labels,
        "fetch_tasks_for_runs",
        lambda _conn, run_ids: (
            [{"id": "base:t01", "passage_id": "p1"}]
            if run_ids == ["gen"]
            else [{"id": "part:t01", "run_item_id": "split-orphan", "seq": 1}]
        ),
    )
    monkeypatch.setattr(task_labels, "fetch_passages_for_runs", lambda *_: [{"id": "p1"}])
    monkeypatch.setattr(
        task_labels,
        "fetch_revisions",
        lambda *_: {"base:t01": {"verdict": "stands", "task": None}},
    )
    monkeypatch.setattr(
        task_labels,
        "fetch_items",
        lambda *_: [{"id": "split-orphan", "task_id": "dropped:t01"}],
    )
    monkeypatch.setattr(task_labels, "materialize_parts", lambda *_: None)

    assert task_labels.label_map(object(), ["gen"], ["cuts"], "revision", ["split"]) == {
        "base:t01": "T01"
    }
