"""Manifest-pinned Universe HTTP and static interface."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from universe.web import dashboard_app
from universe.web.app import create_app


STATIC_DIR = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "universe"
    / "web"
    / "static"
)
MANIFEST_ID = "kc-corpus-" + "a" * 64


class _Rows:
    def __init__(self, *, one=None, all=()):
        self._one = one
        self._all = list(all)

    def fetchone(self):
        return self._one

    def fetchall(self):
        return self._all


class _GroupingConnection:
    def __init__(
        self,
        params,
        *,
        source_rows=(("source-a", "Source A"),),
        member_rows=(),
        edge_rows=(),
    ):
        self.params = params
        self.source_rows = list(source_rows)
        self.member_rows = list(member_rows)
        self.edge_rows = list(edge_rows)
        self.queries = []

    def execute(self, query, params=()):
        self.queries.append((query, params))
        if "FROM kc_grouping WHERE id = %s" in query:
            assert params == ("g-sealed",)
            return _Rows(one=("g-sealed", "computed-at", self.params))
        if "SELECT id, title FROM source" in query:
            return _Rows(all=self.source_rows)
        if "FROM kc_group g LEFT JOIN kc_group_member" in query:
            return _Rows(all=self.member_rows)
        if "FROM kc_grouping_verdict gv" in query:
            return _Rows(all=self.edge_rows)
        raise AssertionError(f"unexpected query: {query}")


def _binding_params(**overrides):
    values = {
        "build_key": "build-key",
        "embedding_run": "embedding-run",
        "judge_run_id": "judge-run",
        "candidate_count": 1,
        "candidate_manifest_sha256": "b" * 64,
    }
    values.update(overrides)
    return values


def _member(task_id="task-a", *, source_id="source-a", task="Effective question"):
    return {
        "task_id": task_id,
        "source_id": source_id,
        "task": task,
        "answer": f"Answer for {task_id}",
        "statement": f"Statement for {task_id}",
    }


def _snapshot(*, components=None):
    return {
        "corpus": {
            "id": MANIFEST_ID,
            "manifest_sha256": "a" * 64,
            "origin": {"syllabus_id": "syllabus-a"},
            "created_at": "created-at",
            "publications": [
                {"source_id": "source-a", "artifact_id": "artifact-a"}
            ],
        },
        "status": "complete",
        "next_stage": None,
        "stages": {
            "task-embedding": {"run_id": "embedding-run"},
            "kc-judge": {"run_id": "judge-run"},
            "grouped": {
                "status": "done",
                "grouping_id": "g-sealed",
                "build_key": "build-key",
                "judge_run_id": "judge-run",
                "candidate_count": 1,
                "candidate_manifest_sha256": "b" * 64,
            },
            "kc-canonical-statement": {"status": "done"},
        },
        "grouping_id": "g-sealed",
        "components": components
        if components is not None
        else [
            {
                "id": "task-a",
                "kind": "singleton",
                "canonical": {
                    "verdict": "stated",
                    "statement": "Statement for task-a",
                },
                "members": [_member()],
            }
        ],
        "relationships": [],
    }


def _axes(*task_ids):
    return {
        task_id: {"modality": "explain", "knowledge": "concept"}
        for task_id in task_ids
    }


def _pin_snapshot(monkeypatch, snapshot):
    seen = []

    def read(_conn, target):
        seen.append(target.manifest_id)
        return snapshot

    monkeypatch.setattr(dashboard_app.kc_pipeline, "read_corpus_snapshot", read)
    return seen


def _group_id(*task_ids):
    digest = hashlib.sha256("\n".join(sorted(task_ids)).encode()).hexdigest()[:12]
    return f"kc-{digest}"


def test_graph_and_compatibility_alias_serve_the_existing_universe_page():
    expected = (STATIC_DIR / "universe.html").read_bytes()
    app = create_app(lambda: None)

    with TestClient(app) as client:
        graph = client.get("/graph")
        compatibility = client.get("/universe")

    assert graph.status_code == 200
    assert compatibility.status_code == 200
    assert graph.content == expected
    assert compatibility.content == expected
    assert b"/static/universe.js?v=7" in graph.content
    assert b"/static/universe.css?v=6" in graph.content
    assert b"Visualiza\xc3\xa7\xc3\xa3o ainda n\xc3\xa3o conectada" not in graph.content


def test_universe_api_requires_a_manifest_before_opening_a_connection(monkeypatch):
    opened = []

    def unexpected_connection():
        opened.append(True)
        raise AssertionError("a missing manifest must fail before database access")

    monkeypatch.setattr(dashboard_app, "connect", unexpected_connection)

    with TestClient(dashboard_app.create_app()) as client:
        response = client.get("/api/universe")

    assert response.status_code == 422
    assert opened == []


def test_universe_rejects_a_grouping_with_a_mismatched_manifest_witness(monkeypatch):
    snapshot = _snapshot()
    _pin_snapshot(monkeypatch, snapshot)
    conn = _GroupingConnection(
        _binding_params(candidate_manifest_sha256="wrong-manifest-sha")
    )

    with pytest.raises(HTTPException) as rejected:
        dashboard_app._universe(conn, MANIFEST_ID)

    assert rejected.value.status_code == 409
    assert "not bound" in rejected.value.detail


def test_universe_uses_effective_snapshot_evidence_instead_of_raw_task_rows(
    monkeypatch,
):
    snapshot = _snapshot()
    seen = _pin_snapshot(monkeypatch, snapshot)
    monkeypatch.setattr(
        dashboard_app,
        "_task_axes",
        lambda _conn, _grouping: _axes("task-a"),
    )
    conn = _GroupingConnection(_binding_params())

    result = dashboard_app._universe(conn, MANIFEST_ID)

    assert seen == [MANIFEST_ID]
    assert result["manifest"]["id"] == MANIFEST_ID
    assert result["nodes"] == [
        {
            "id": "task-a",
            "statement": "Statement for task-a",
            "modality": "explain",
            "knowledge": "concept",
            "source_id": "source-a",
            "source_title": "Source A",
            "task": "Effective question",
            "answer": "Answer for task-a",
            "group_id": None,
        }
    ]
    assert not any("FROM task" in query for query, _ in conn.queries)
    assert not any("ORDER BY computed_at DESC" in query for query, _ in conn.queries)


def test_universe_accepts_only_the_groups_recomputed_from_exact_edges(monkeypatch):
    group_id = _group_id("task-a", "task-b")
    components = [
        {
            "id": group_id,
            "kind": "composite",
            "canonical": {
                "verdict": "stated",
                "statement": "Canonical composite",
            },
            "members": [_member("task-a"), _member("task-b")],
        }
    ]
    _pin_snapshot(monkeypatch, _snapshot(components=components))
    monkeypatch.setattr(
        dashboard_app,
        "_task_axes",
        lambda _conn, _grouping: _axes("task-a", "task-b"),
    )
    edge = ("task-a", "task-b", "clear_yes", "clear_yes")
    conn = _GroupingConnection(
        _binding_params(),
        member_rows=[(group_id, "task-a"), (group_id, "task-b")],
        edge_rows=[edge],
    )

    result = dashboard_app._universe(conn, MANIFEST_ID)

    assert result["edges"] == [
        {
            "a": "task-a",
            "b": "task-b",
            "ab": "clear_yes",
            "ba": "clear_yes",
            "mutual": True,
        }
    ]
    assert result["groups"] == [
        {
            "id": group_id,
            "members": ["task-a", "task-b"],
            "canonical_status": "stated",
            "canonical_statement": "Canonical composite",
            "canonical_reason": None,
        }
    ]
    assert {node["group_id"] for node in result["nodes"]} == {group_id}


@pytest.mark.parametrize(
    ("components", "member_rows", "edge_rows", "detail"),
    [
        (
            _snapshot()["components"],
            [("kc-a", "task-outside")],
            [],
            "outside",
        ),
        (
            _snapshot()["components"],
            [],
            [("task-a", "task-outside", "clear_yes", "clear_yes")],
            "outside",
        ),
        (
            [
                {
                    "id": "kc-one",
                    "kind": "composite",
                    "canonical": {"verdict": "pending"},
                    "members": [_member("task-a"), _member("task-b")],
                },
                {
                    "id": "kc-two",
                    "kind": "composite",
                    "canonical": {"verdict": "pending"},
                    "members": [_member("task-a"), _member("task-c")],
                },
            ],
            [
                ("kc-one", "task-a"),
                ("kc-one", "task-b"),
                ("kc-two", "task-a"),
                ("kc-two", "task-c"),
            ],
            [],
            "more than one group",
        ),
    ],
)
def test_universe_fails_closed_for_out_of_scope_or_duplicate_membership(
    monkeypatch,
    components,
    member_rows,
    edge_rows,
    detail,
):
    _pin_snapshot(monkeypatch, _snapshot(components=components))
    task_ids = sorted(
        {
            member["task_id"]
            for component in components
            for member in component["members"]
        }
    )
    monkeypatch.setattr(
        dashboard_app,
        "_task_axes",
        lambda _conn, _grouping: _axes(*task_ids),
    )
    conn = _GroupingConnection(
        _binding_params(),
        member_rows=member_rows,
        edge_rows=edge_rows,
    )

    with pytest.raises(HTTPException) as rejected:
        dashboard_app._universe(conn, MANIFEST_ID)

    assert rejected.value.status_code == 409
    assert detail in rejected.value.detail


def test_universe_rejects_in_manifest_groups_that_do_not_follow_the_rule(monkeypatch):
    components = [
        {
            "id": "kc-invented",
            "kind": "composite",
            "canonical": {"verdict": "pending"},
            "members": [_member("task-a"), _member("task-b")],
        }
    ]
    _pin_snapshot(monkeypatch, _snapshot(components=components))
    monkeypatch.setattr(
        dashboard_app,
        "_task_axes",
        lambda _conn, _grouping: _axes("task-a", "task-b"),
    )
    conn = _GroupingConnection(
        _binding_params(),
        member_rows=[("kc-invented", "task-a"), ("kc-invented", "task-b")],
        edge_rows=[],
    )

    with pytest.raises(HTTPException) as rejected:
        dashboard_app._universe(conn, MANIFEST_ID)

    assert rejected.value.status_code == 409
    assert "derived from its certified verdicts" in rejected.value.detail
