"""The local administration HTTP surface against the real test database."""

from pathlib import Path

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

import universe.web.app as web_app
from universe import defaults
from universe.spine import STAGE_ORDER


WORKBOOK = Path(__file__).resolve().parents[1] / "data" / "GRAD CC07 - 2026-2A.xlsx"


@pytest.fixture(scope="module")
def client(db, test_database_url):
    """Point the app's short-lived connections at the migrated test database."""
    db.rollback()
    db.execute(
        "TRUNCATE source, run, syllabus, kc_grouping, curation_event CASCADE"
    )
    db.commit()
    original_connect = web_app.connect
    web_app.connect = lambda: psycopg.connect(test_database_url)
    try:
        with TestClient(web_app.create_app()) as test_client:
            yield test_client
    finally:
        web_app.connect = original_connect


def test_overview_is_empty_before_any_dashboard_work(client):
    response = client.get("/api/overview")

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        "corpora": [],
        "universe": {"mutual_pairs": 0, "composites": 0, "grouping_id": None},
        "attention": [],
        "ledger": {"runs": 0, "verdicts": 0},
    }


def test_empty_source_universe_and_run_shapes(client):
    assert client.get("/api/sources").json() == {"sources": []}
    assert client.get("/api/universe").json() == {
        "nodes": [],
        "edges": [],
        "groups": [],
        "grouping": None,
    }
    runs_payload = client.get("/api/runs").json()
    assert runs_payload["runs"] == []
    assert runs_payload["stage_defaults"]["kc-judge"]["prompt_ref"] == "kc-judge/v003-surmise-pair"
    assert runs_payload["stage_defaults"]["kc-canonical-statement"]["prompt_ref"] == (
        "kc-canonical-statement/v001"
    )
    assert "task-fact" in runs_payload["retired_stages"]


@pytest.fixture(scope="module")
def imported_syllabus(client):
    with WORKBOOK.open("rb") as workbook:
        response = client.post(
            "/api/syllabi/upload",
            files={
                "file": (
                    WORKBOOK.name,
                    workbook,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_and_idempotent_reupload(client, imported_syllabus):
    assert imported_syllabus["item_count"] == 194
    assert imported_syllabus["source_count"] == 130
    assert imported_syllabus["unchanged"] is False
    assert set(imported_syllabus["diff"]) == {"added", "removed", "changed"}

    with WORKBOOK.open("rb") as workbook:
        response = client.post(
            "/api/syllabi/upload",
            files={"file": (WORKBOOK.name, workbook)},
        )

    assert response.status_code == 200, response.text
    assert response.json()["unchanged"] is True
    assert response.json()["version_id"] == imported_syllabus["version_id"]


def test_syllabus_list_includes_version_counts(client, imported_syllabus):
    response = client.get("/api/syllabi")

    assert response.status_code == 200
    syllabi = response.json()["syllabi"]
    syllabus = next(
        item for item in syllabi if item["id"] == imported_syllabus["syllabus_id"]
    )
    assert len(syllabus["versions"]) == 1
    assert syllabus["versions"][0]["item_count"] == 194
    assert syllabus["versions"][0]["source_count"] == 128


def test_syllabus_detail_has_week_and_item_shapes(client, imported_syllabus):
    response = client.get(f"/api/syllabi/{imported_syllabus['syllabus_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert {"id", "title", "versions", "latest", "diff"} <= payload.keys()
    assert payload["latest"]["item_count"] == 194
    assert payload["latest"]["source_count"] == 128
    assert isinstance(payload["latest"]["weeks"], list)
    assert payload["latest"]["weeks"]
    assert all(isinstance(week["items"], list) for week in payload["latest"]["weeks"])
    required = {
        "id",
        "seq",
        "kind",
        "title",
        "description",
        "url",
        "parent_title",
        "source_id",
        "media_type",
        "source_status",
        "attention",
    }
    assert required <= payload["latest"]["weeks"][0]["items"][0].keys()


def test_missing_syllabus_and_source_are_json_404s(client):
    for route in ("/api/syllabi/missing", "/api/sources/missing"):
        response = client.get(route)

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
        assert "detail" in response.json()


@pytest.fixture(scope="module")
def source_states(db, imported_syllabus):
    """Seed the three source states and successful/failed stage facts.

    The ingested source carries a passage-triage retry chain (an older run
    that covered both passages, a newer one that half-failed) and a wholly
    failed task-generation run, so the dashboard's union semantics show.
    """
    del imported_syllabus
    triage = defaults.STAGE_DEFAULTS["passage-triage"]
    generation = defaults.STAGE_DEFAULTS["task-generation"]
    db.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES"
        " ('src-web-pending', '{\"url\": \"https://pending.test\"}',"
        "  'Pending source', 'article'),"
        " ('src-web-failed', '{\"url\": \"https://failed.test\"}',"
        "  'Failed source', 'article'),"
        " ('src-web-ingested', '{\"url\": \"https://ingested.test\"}',"
        "  'Ingested source', 'article')"
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, failure_note) VALUES"
        " ('snap-web-failed', 'src-web-failed', NULL, 'failed', 'timeout'),"
        " ('snap-web-ok', 'src-web-ingested', 'web-hash', 'ok', NULL)"
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES ('art-web', 'snap-web-ok', 'markdown', 'test', 'body')"
    )
    db.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq) VALUES"
        " ('pass-web-a', 'art-web', 'web-v1', 1, 1),"
        " ('pass-web-b', 'art-web', 'web-v1', 2, 2)"
    )
    cuts = defaults.STAGE_DEFAULTS["passage-cuts"]
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, started_at) VALUES"
        " ('r-web-cuts', 'passage-cuts', %(cm)s, %(cp)s, 'sha', 'done',"
        "  '2025-12-31 00:00:00+00'),"
        " ('r-web-tri-a', 'passage-triage', %(tm)s, %(tp)s, 'sha', 'done',"
        "  '2026-01-01 00:00:00+00'),"
        " ('r-web-tri-b', 'passage-triage', %(tm)s, %(tp)s, 'sha', 'done',"
        "  '2026-01-02 00:00:00+00'),"
        " ('r-web-gen-fail', 'task-generation', %(gm)s, %(gp)s, 'sha', 'failed',"
        "  '2026-01-03 00:00:00+00')",
        {
            "cm": cuts["model"], "cp": cuts["prompt_ref"],
            "tm": triage["model"], "tp": triage["prompt_ref"],
            "gm": generation["model"], "gp": generation["prompt_ref"],
        },
    )
    db.execute(
        "INSERT INTO passage_origin (passage_id, run_id) VALUES"
        " ('pass-web-a', 'r-web-cuts'), ('pass-web-b', 'r-web-cuts')"
    )
    db.execute(
        "INSERT INTO run_item"
        " (id, run_id, artifact_id, passage_id, response, error) VALUES"
        " ('ri-web-cuts', 'r-web-cuts', 'art-web', NULL, '{}', NULL),"
        " ('ri-web-tri-a1', 'r-web-tri-a', 'art-web', 'pass-web-a',"
        "  '{\"verdict\": \"not_filler\"}', NULL),"
        " ('ri-web-tri-a2', 'r-web-tri-a', 'art-web', 'pass-web-b',"
        "  '{\"verdict\": \"not_filler\"}', NULL),"
        " ('ri-web-tri-b1', 'r-web-tri-b', 'art-web', 'pass-web-a',"
        "  '{\"verdict\": \"not_filler\"}', NULL),"
        " ('ri-web-tri-b2', 'r-web-tri-b', 'art-web', 'pass-web-b',"
        "  NULL, '429 rate limited'),"
        " ('ri-web-gen-1', 'r-web-gen-fail', 'art-web', 'pass-web-a',"
        "  NULL, 'boom'),"
        " ('ri-web-gen-2', 'r-web-gen-fail', 'art-web', 'pass-web-b',"
        "  NULL, 'boom')"
    )
    db.commit()


def test_source_statuses_and_stage_aggregation(client, source_states):
    response = client.get("/api/sources")

    assert response.status_code == 200
    sources = {item["id"]: item for item in response.json()["sources"]}
    assert sources["src-web-pending"]["source_status"] == "pending"
    assert sources["src-web-failed"]["source_status"] == "failed"
    ingested = sources["src-web-ingested"]
    assert ingested["source_status"] == "ingested"
    # Every pipeline stage is reported, computed from the union of runs.
    assert set(ingested["stages"]) == set(STAGE_ORDER)
    assert ingested["stages"]["snapshot"]["status"] == "done"
    # The retry chain's union covers both passages: done, current recipe.
    assert ingested["stages"]["passage-triage"] == {
        "status": "done", "generation": "current",
    }
    assert ingested["stages"]["task-generation"]["status"] == "failed"
    # The src-web-* fixtures are linked to no syllabus: test corpus.
    assert ingested["corpus"] == {"id": None, "title": "Test corpus"}

    detail = client.get("/api/sources/src-web-ingested").json()
    assert {"snapshots", "artifacts", "stages", "tasks"} <= detail.keys()
    stages = {item["stage"]: item for item in detail["stages"]}
    # Union coverage, not the newest run alone, which failed on pass-web-b.
    assert stages["passage-triage"]["status"] == "done"
    assert stages["passage-triage"]["done"] == 2
    assert stages["passage-triage"]["total"] == 2
    assert stages["passage-triage"]["run_id"] == "r-web-tri-b"
    assert stages["task-generation"]["status"] == "failed"


def test_runs_include_item_and_error_counts(client, source_states):
    response = client.get("/api/runs")

    assert response.status_code == 200
    runs = {item["id"]: item for item in response.json()["runs"]}
    assert runs["r-web-tri-b"]["items"] == 2
    assert runs["r-web-tri-b"]["errors"] == 1
    assert runs["r-web-tri-b"]["generation"] == "current"
    assert runs["r-web-gen-fail"]["items"] == 2
    assert runs["r-web-gen-fail"]["errors"] == 2


def test_overview_keeps_syllabus_and_test_corpora_apart(client, source_states):
    payload = client.get("/api/overview").json()

    by_kind = {corpus["kind"]: corpus for corpus in payload["corpora"]}
    assert set(by_kind) == {"syllabus", "test"}
    syllabus_corpus = by_kind["syllabus"]
    assert syllabus_corpus["sources"] > 0
    assert syllabus_corpus["extracted"] == 0
    assert syllabus_corpus["not_acquired"] == syllabus_corpus["sources"]
    test_corpus = by_kind["test"]
    assert test_corpus["sources"] == 3
    assert test_corpus["extracted"] == 1
    assert test_corpus["failed"] == 1
    assert test_corpus["not_acquired"] == 1


@pytest.fixture(scope="module")
def graph_facts(db, source_states):
    """Seed two stated tasks, their verdict, and one committed group.

    Statement and judge facts use the current stage defaults, the way
    production writes them; judge run items carry no artifact.
    """
    del source_states
    statement = defaults.STAGE_DEFAULTS["kc-statement"]
    judge = defaults.STAGE_DEFAULTS["kc-judge"]
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, started_at) VALUES"
        " ('r-web-taskgen', 'task-generation', 'test', 'taskgen/v1', 'sha', 'done',"
        "  '2026-01-04 00:00:00+00'),"
        " ('r-web-statement', 'kc-statement', %s, %s, 'sha', 'done',"
        "  '2026-01-05 00:00:00+00'),"
        " ('r-web-judge', 'kc-judge', %s, %s, 'sha', 'done',"
        "  '2026-01-06 00:00:00+00')",
        (statement["model"], statement["prompt_ref"], judge["model"], judge["prompt_ref"]),
    )
    db.execute(
        "INSERT INTO run_item"
        " (id, run_id, artifact_id, passage_id, response) VALUES"
        " ('ri-web-gen-a', 'r-web-taskgen', 'art-web', 'pass-web-a', '{}'),"
        " ('ri-web-gen-b', 'r-web-taskgen', 'art-web', 'pass-web-b', '{}')"
    )
    db.execute(
        "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer) VALUES"
        " ('task-web-a', 'ri-web-gen-a', 'pass-web-a', 1, 'Question A', 'Answer A'),"
        " ('task-web-b', 'ri-web-gen-b', 'pass-web-b', 1, 'Question B', 'Answer B')"
    )
    db.execute(
        "INSERT INTO run_item"
        " (id, run_id, artifact_id, task_id, response) VALUES"
        " ('ri-web-statement-a', 'r-web-statement', 'art-web', 'task-web-a',"
        "  '{\"verdict\":\"stated\",\"statement\":\"Statement A\"}'),"
        " ('ri-web-statement-b', 'r-web-statement', 'art-web', 'task-web-b',"
        "  '{\"verdict\":\"stated\",\"statement\":\"Statement B\"}'),"
        " ('ri-web-judge', 'r-web-judge', NULL, 'task-web-a', '{}')"
    )
    db.execute(
        "UPDATE run SET params = '{\"build_key\":\"web-build\"}'"
        " WHERE id = 'r-web-judge'"
    )
    db.execute(
        "INSERT INTO kc_verdict"
        " (run_item_id, task_a_id, task_b_id, a_implies_b, b_implies_a,"
        "  judge_model, judge_prompt, build_key)"
        " VALUES ('ri-web-judge', 'task-web-a', 'task-web-b',"
        " 'clear_yes', 'clear_yes', %s, %s, 'web-build')",
        (judge["model"], judge["prompt_ref"]),
    )
    db.execute(
        "INSERT INTO kc_grouping (id, params) VALUES ('grouping-web', %s)",
        (
            Jsonb(
                {
                    "build_key": "web-build",
                    "statements_from": ["r-web-statement"],
                    "embedding_run": None,
                    "modality_runs": [],
                    "knowledge_runs": [],
                    "judge_model": judge["model"],
                    "judge_prompt": judge["prompt_ref"],
                }
            ),
        ),
    )
    db.execute(
        "INSERT INTO kc_group (grouping_id, id)"
        " VALUES ('grouping-web', 'group-web')"
    )
    db.execute(
        "INSERT INTO kc_group_member (grouping_id, group_id, task_id) VALUES"
        " ('grouping-web', 'group-web', 'task-web-a'),"
        " ('grouping-web', 'group-web', 'task-web-b')"
    )
    db.execute(
        "INSERT INTO kc_grouping_verdict (grouping_id, run_item_id)"
        " VALUES ('grouping-web', 'ri-web-judge')"
    )
    canonical = defaults.STAGE_DEFAULTS["kc-canonical-statement"]
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, started_at)"
        " VALUES ('r-web-canonical', 'kc-canonical-statement', %s, %s, 'sha',"
        " 'done', '2026-01-07 00:00:00+00')",
        (canonical["model"], canonical["prompt_ref"]),
    )
    db.execute(
        "INSERT INTO run_item (id, run_id, artifact_id, response)"
        " VALUES ('ri-web-canonical', 'r-web-canonical', NULL,"
        " '{\"verdict\":\"stated\",\"statement\":\"Canonical statement\"}')"
    )
    db.execute(
        "INSERT INTO kc_canonicalization (run_item_id, grouping_id, group_id)"
        " VALUES ('ri-web-canonical', 'grouping-web', 'group-web')"
    )
    db.commit()


def test_universe_returns_nodes_verdict_edges_and_latest_groups(client, graph_facts):
    response = client.get("/api/universe")

    assert response.status_code == 200
    payload = response.json()
    assert {item["statement"] for item in payload["nodes"]} == {
        "Statement A",
        "Statement B",
    }
    nodes = {item["id"]: item for item in payload["nodes"]}
    assert nodes["task-web-a"]["task"] == "Question A"
    assert nodes["task-web-a"]["answer"] == "Answer A"
    assert payload["edges"] == [
        {
            "a": "task-web-a",
            "b": "task-web-b",
            "ab": "clear_yes",
            "ba": "clear_yes",
            "mutual": True,
        }
    ]
    assert payload["groups"] == [
        {
            "id": "group-web",
            "members": ["task-web-a", "task-web-b"],
            "canonical_status": "stated",
            "canonical_statement": "Canonical statement",
            "canonical_reason": None,
        }
    ]
    assert payload["grouping"]["id"] == "grouping-web"

    detail = client.get("/api/sources/src-web-ingested").json()
    tasks = {item["id"]: item for item in detail["tasks"]}
    assert tasks["task-web-a"]["statement"] == "Statement A"
    assert tasks["task-web-a"]["group_id"] == "group-web"


def test_universe_snapshot_does_not_mix_in_a_newer_statement(client, db, graph_facts):
    """A rerun can make the live build stale without rewriting its labels."""
    statement = defaults.STAGE_DEFAULTS["kc-statement"]
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, finished_at)"
        " VALUES ('r-web-statement-new', 'kc-statement', %s, %s, 'new-sha',"
        " 'done', now())",
        (statement["model"], statement["prompt_ref"]),
    )
    db.execute(
        "INSERT INTO run_item"
        " (id, run_id, artifact_id, task_id, response)"
        " VALUES ('ri-web-statement-new', 'r-web-statement-new', 'art-web',"
        " 'task-web-a', '{\"verdict\":\"stated\",\"statement\":\"New statement A\"}')"
    )
    db.commit()

    try:
        payload = client.get("/api/universe").json()
        nodes = {node["id"]: node for node in payload["nodes"]}

        assert nodes["task-web-a"]["statement"] == "Statement A"
        assert payload["grouping"]["stale"] is True
        assert any(
            "knowledge statements" in reason
            for reason in payload["grouping"]["stale_reasons"]
        )
    finally:
        # Keep the module-scoped fixture's later expectations isolated.
        db.execute(
            "UPDATE run SET status = 'failed' WHERE id = 'r-web-statement-new'"
        )
        db.commit()


def test_source_detail_shows_judge_and_grouped_progress(client, graph_facts):
    """Judge coverage is read per stated task from the pair verdicts —
    artifact-less judge run items must not leave the stage pending forever —
    and grouped reflects the snapshot being newer than the verdicts."""
    detail = client.get("/api/sources/src-web-ingested").json()
    stages = {item["stage"]: item for item in detail["stages"]}
    assert stages["kc-judge"]["status"] == "done"
    assert (stages["kc-judge"]["done"], stages["kc-judge"]["total"]) == (2, 2)
    assert stages["kc-judge"]["run_id"] == "r-web-judge"
    assert stages["grouped"]["status"] == "done"
    assert (stages["grouped"]["done"], stages["grouped"]["total"]) == (2, 2)


def _detail_items(client, syllabus_id):
    payload = client.get(f"/api/syllabi/{syllabus_id}").json()
    return [
        item for week in payload["latest"]["weeks"] for item in week["items"]
    ]


def test_item_edit_overlays_detail_and_returns_effective_item(
    client, imported_syllabus
):
    syllabus_id = imported_syllabus["syllabus_id"]
    item = _detail_items(client, syllabus_id)[0]
    assert item["edited"] == {}
    assert item["edits"] == []

    response = client.post(
        f"/api/syllabi/items/{item['id']}/edit",
        json={"field": "title", "value": "Founder corrected title", "note": "fix"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["id"] == item["id"]
    assert payload["title"] == "Founder corrected title"
    assert payload["edited"] == {"title": True}
    assert payload["edits"][0]["field"] == "title"
    assert payload["edits"][0]["old"] == item["title"]
    assert payload["edits"][0]["new"] == "Founder corrected title"
    assert payload["edits"][0]["note"] == "fix"

    refreshed = next(
        candidate
        for candidate in _detail_items(client, syllabus_id)
        if candidate["id"] == item["id"]
    )
    assert refreshed["title"] == "Founder corrected title"
    assert refreshed["edited"] == {"title": True}
    assert refreshed["edits"][0]["old"] == item["title"]


def test_item_url_edit_relinks_item_to_new_source(client, imported_syllabus):
    syllabus_id = imported_syllabus["syllabus_id"]
    item = next(
        candidate
        for candidate in _detail_items(client, syllabus_id)
        if candidate["source_id"]
    )

    response = client.post(
        f"/api/syllabi/items/{item['id']}/edit",
        json={"field": "url", "value": "https://curation.web.test/replacement"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["url"] == "https://curation.web.test/replacement"
    assert payload["source_id"] != item["source_id"]
    assert payload["media_type"] == "article"
    assert payload["source_status"] == "pending"
    assert payload["edited"] == {"url": True}
    # The re-linked source is a real row the sources page can show.
    sources = {row["id"] for row in client.get("/api/sources").json()["sources"]}
    assert payload["source_id"] in sources
    refreshed = next(
        candidate
        for candidate in _detail_items(client, syllabus_id)
        if candidate["id"] == item["id"]
    )
    assert refreshed["source_id"] == payload["source_id"]
    assert refreshed["media_type"] == "article"


def test_item_edit_validation_errors(client, imported_syllabus):
    item = _detail_items(client, imported_syllabus["syllabus_id"])[0]

    unknown = client.post(
        "/api/syllabi/items/missing:v0001:0001/edit",
        json={"field": "title", "value": "X"},
    )
    assert unknown.status_code == 404

    bad_field = client.post(
        f"/api/syllabi/items/{item['id']}/edit",
        json={"field": "week", "value": "2"},
    )
    assert bad_field.status_code == 400

    empty_value = client.post(
        f"/api/syllabi/items/{item['id']}/edit",
        json={"field": "title", "value": "  "},
    )
    assert empty_value.status_code == 400


@pytest.mark.parametrize(
    ("route", "file_name"),
    [
        ("/", "index.html"),
        ("/structure", "structure.html"),
        ("/syllabi", "syllabi.html"),
        ("/sources", "sources.html"),
        ("/universe", "universe.html"),
        ("/runs", "runs.html"),
    ],
)
def test_page_routes_follow_static_file_availability(client, route, file_name):
    response = client.get(route)
    path = web_app.STATIC_DIR / file_name

    if not path.exists():
        assert response.status_code == 404
        return
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["cache-control"] == "no-store"
