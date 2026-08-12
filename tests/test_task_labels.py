"""Chain-relative labels for effective scopes and legacy extraction reports."""

import pytest

from universe import task_labels


def test_label_map_accepts_the_effective_scope_interface_by_keyword(monkeypatch):
    selected = [{"id": "gen:a", "run_item_id": "gen-i1", "seq": 1}]
    monkeypatch.setattr(
        task_labels, "fetch_tasks_for_runs", lambda _conn, _runs: selected
    )

    assert task_labels.label_map(
        object(), tasks=selected, gen_runs=["gen"], granularity_runs=None
    ) == {"gen:a": "T01"}


def test_label_map_preserves_the_legacy_scope_interface_by_keyword(monkeypatch):
    base = [{"id": "gen:a", "passage_id": "p1"}]
    monkeypatch.setattr(
        task_labels, "fetch_tasks_for_runs", lambda _conn, _runs: base
    )
    monkeypatch.setattr(
        task_labels,
        "fetch_passages_for_runs",
        lambda _conn, _runs: [{"id": "p1"}],
    )
    monkeypatch.setattr(
        task_labels,
        "fetch_revisions",
        lambda _conn, _run: {"gen:a": {"verdict": "stands", "task": None}},
    )

    assert task_labels.label_map(
        object(),
        gen_runs=["gen"],
        passages_from=["cuts"],
        revision_run="revision",
    ) == {"gen:a": "T01"}


def test_label_map_numbers_only_effective_roots_and_keeps_part_lineage(monkeypatch):
    originals = [
        {"id": "gen:a", "run_item_id": "gen-i1", "seq": 1},
        {"id": "gen:b", "run_item_id": "gen-i1", "seq": 2},
        {"id": "gen:c", "run_item_id": "gen-i1", "seq": 3},
        {"id": "gen:dropped", "run_item_id": "gen-i1", "seq": 4},
    ]
    effective = [
        {"id": "gen:a", "run_item_id": "gen-i1", "seq": 1},
        {"id": "split-b:t01", "run_item_id": "split-b", "seq": 1},
        {"id": "split-b:t02", "run_item_id": "split-b", "seq": 2},
        {"id": "gen:c", "run_item_id": "gen-i1", "seq": 3},
    ]
    monkeypatch.setattr(
        task_labels, "fetch_tasks_for_runs", lambda _conn, _runs: originals
    )
    monkeypatch.setattr(
        task_labels,
        "fetch_items",
        lambda _conn, _run: [{"id": "split-b", "task_id": "gen:b"}],
    )

    assert task_labels.label_map(object(), effective, ["gen"], ["split"]) == {
        "gen:a": "T01",
        "split-b:t01": "T02 part 1",
        "split-b:t02": "T02 part 2",
        "gen:c": "T03",
    }


def test_label_map_does_not_reconstruct_or_add_unselected_parts(monkeypatch):
    originals = [{"id": "gen:a", "run_item_id": "gen-i1", "seq": 1}]
    selected = [{"id": "gen:a", "run_item_id": "gen-i1", "seq": 1}]
    monkeypatch.setattr(
        task_labels, "fetch_tasks_for_runs", lambda _conn, _runs: originals
    )
    monkeypatch.setattr(task_labels, "fetch_items", lambda *_args: [])

    assert task_labels.label_map(object(), selected, ["gen"], ["split"]) == {
        "gen:a": "T01"
    }


def test_label_map_rejects_effective_tasks_outside_the_named_chain(monkeypatch):
    monkeypatch.setattr(task_labels, "fetch_tasks_for_runs", lambda *_args: [])
    monkeypatch.setattr(task_labels, "fetch_items", lambda *_args: [])

    with pytest.raises(SystemExit, match="outside the labeling chain"):
        task_labels.label_map(
            object(),
            [{"id": "orphan", "run_item_id": "unknown", "seq": 1}],
            ["gen"],
            ["split"],
        )


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
