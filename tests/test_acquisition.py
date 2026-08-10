"""Acquisition tests. Firecrawl is always faked; no test uses the network."""

import hashlib
import json
import re
import threading
from dataclasses import dataclass
from types import SimpleNamespace

import httpx
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

from universe.acquisition import articles, runner
from universe.acquisition.articles import fetch_article, fetch_article_detailed
from universe.acquisition.book_scope import extract_scope, is_missing_scope
from universe.acquisition.gates import GATE_CODES, PAYWALL_HEURISTICS, build_gate_report
from universe.acquisition.runner import (
    build_parser,
    claim_next_job,
    enqueue_source,
    process_next_job,
)
from universe.migrate import migrate
from universe.settings import openrouter_api_key


@dataclass
class FakeResponse:
    status_code: int
    payload: dict
    headers: dict[str, str] | None = None


@pytest.fixture
def fake_firecrawl(monkeypatch):
    calls = []
    sleeps = []
    clients = []

    def install(*outcomes):
        queued = list(outcomes)

        def respond(request):
            calls.append(request)
            outcome = queued.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return httpx.Response(
                outcome.status_code,
                json=outcome.payload,
                headers=outcome.headers,
                request=request,
            )

        client = httpx.Client(transport=httpx.MockTransport(respond))
        clients.append(client)
        monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
        monkeypatch.setattr(articles.httpx, "post", client.post)
        monkeypatch.setattr(articles.time, "sleep", sleeps.append)
        return calls, sleeps

    yield install
    for client in clients:
        client.close()


@pytest.fixture(scope="module")
def acquisition_db(test_database_url):
    """An isolated schema inside the shared test database."""
    schema = "acquisition_test"
    with psycopg.connect(test_database_url) as admin:
        admin.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA public")
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        admin.commit()

    scoped_url = make_conninfo(
        test_database_url, options=f"-csearch_path={schema},public"
    )
    with psycopg.connect(scoped_url) as conn:
        migrate(conn)
        yield conn


def add_source(conn, source_id, media_type="article", url=None):
    assert source_id.startswith("acqx-")
    conn.execute(
        "INSERT INTO source (id, identity, title, media_type) VALUES (%s, %s, %s, %s)",
        (
            source_id,
            Jsonb({"canonical_url": url or f"https://example.com/{source_id}"}),
            source_id,
            media_type,
        ),
    )
    conn.commit()


def test_gate_catalog_and_report_shape_are_stable():
    required = {
        "auth_wall_detected",
        "bot_wall_detected",
        "error_page_detected",
        "http_status_4xx",
        "http_status_5xx",
        "missing_credentials",
        "unsupported_media_kind",
        "missing_concrete_scope",
        "manual_access_required",
        "empty_content",
        "fetch_failed",
    }
    assert set(GATE_CODES) == required
    assert all(
        isinstance(gate["description"], str) and isinstance(gate["blocking"], bool)
        for gate in GATE_CODES.values()
    )
    assert len(PAYWALL_HEURISTICS) == 6
    assert all(isinstance(pattern, re.Pattern) for pattern in PAYWALL_HEURISTICS)
    assert build_gate_report("failed_gate", ["fetch_failed"], [], None) == {
        "status": "failed_gate",
        "failures": ["fetch_failed"],
        "warnings": [],
        "notes": "",
    }


@pytest.mark.parametrize(
    "text",
    [
        "Subscribe to continue reading",
        "Access denied",
        "Log in to view this article",
        '<form action="/login"><input type="password">',
        "403 Forbidden",
        "Please verify you are human",
        "Just a moment... Checking your browser before accessing example.com",
        "Enable JavaScript and cookies to continue",
    ],
)
def test_paywall_heuristics_recognize_blocked_pages(text):
    assert any(pattern.search(text) for pattern in PAYWALL_HEURISTICS)


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Leia o capítulo 5 antes da aula", "capítulo 5"),
        ("Read pages 12-34", "pages 12-34"),
    ],
)
def test_book_scope_returns_the_first_concrete_scope(description, expected):
    assert extract_scope(description) == expected


def test_missing_scope_applies_only_to_books(db):
    assert is_missing_scope(db, {"media_type": "book", "description": "Read this textbook"})
    assert not is_missing_scope(
        db, {"media_type": "book", "description": "Read chapter 2"}
    )
    assert not is_missing_scope(
        db, {"media_type": "article", "description": "Read this textbook"}
    )


def test_fetch_article_returns_markdown_from_the_sync_firecrawl_call(fake_firecrawl):
    calls, sleeps = fake_firecrawl(FakeResponse(200, {"data": {"markdown": "# Lesson"}}))

    assert fetch_article({"identity": {"canonical_url": "https://example.com/lesson"}}) == (
        "# Lesson",
        None,
    )
    assert sleeps == []
    assert len(calls) == 1
    assert calls[0].method == "POST"
    assert str(calls[0].url) == "https://api.firecrawl.dev/v2/scrape"
    assert calls[0].headers["Authorization"] == "Bearer test-key"
    assert calls[0].headers["Content-Type"] == "application/json"
    assert json.loads(calls[0].content) == {
        "url": "https://example.com/lesson",
        "formats": ["markdown", "images"],
        "timeout": 60_000,
    }


def test_fetch_article_rejects_empty_content(fake_firecrawl):
    fake_firecrawl(FakeResponse(200, {"data": {"markdown": "  "}}))
    assert fetch_article({"identity": {"canonical_url": "https://example.com"}}) == (
        None,
        "empty_content",
    )


def test_fetch_article_rejects_a_paywall_instead_of_storing_it(fake_firecrawl):
    fake_firecrawl(
        FakeResponse(200, {"data": {"markdown": "Subscribe to continue reading"}})
    )
    assert fetch_article({"identity": {"canonical_url": "https://example.com"}}) == (
        None,
        "auth_wall_detected",
    )


@pytest.mark.parametrize(
    ("body", "failure_code", "category"),
    [
        ("Please verify you are human", "bot_wall_detected", "anti_bot_blocked"),
        ("404 Not Found", "error_page_detected", "error_page"),
    ],
)
def test_fetch_article_distinguishes_block_and_error_pages(
    fake_firecrawl, body, failure_code, category
):
    fake_firecrawl(FakeResponse(200, {"data": {"markdown": body}}))

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com"}}
    )

    assert result.failure_code == failure_code
    assert result.diagnostics["category"] == category


def test_fetch_article_requires_an_explicit_environment_key(monkeypatch):
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    assert fetch_article({"identity": {"canonical_url": "https://example.com"}}) == (
        None,
        "missing_credentials",
    )


def test_fetch_article_retries_rate_limits_then_returns_content(fake_firecrawl):
    calls, sleeps = fake_firecrawl(
        FakeResponse(429, {}),
        FakeResponse(200, {"data": {"markdown": "Recovered"}}),
    )
    assert fetch_article({"identity": {"canonical_url": "https://example.com"}}) == (
        "Recovered",
        None,
    )
    assert len(calls) == 2
    assert sleeps == [2.0]


def test_fetch_article_honors_firecrawl_retry_after(fake_firecrawl):
    calls, sleeps = fake_firecrawl(
        FakeResponse(429, {"error": "Concurrency limit reached"}, {"Retry-After": "7"}),
        FakeResponse(200, {"data": {"markdown": "Recovered"}}),
    )

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com"}}
    )

    assert result.succeeded
    assert len(calls) == 2
    assert sleeps == [7.0]


@pytest.mark.parametrize("status", [401, 403])
def test_fetch_article_does_not_retry_permanent_http_errors(fake_firecrawl, status):
    calls, sleeps = fake_firecrawl(FakeResponse(status, {}))
    assert fetch_article({"identity": {"canonical_url": "https://example.com"}}) == (
        None,
        "http_status_4xx",
    )
    assert len(calls) == 1
    assert sleeps == []


def test_fetch_article_retries_connection_errors_then_fails(fake_firecrawl):
    request = httpx.Request("POST", "https://api.firecrawl.dev/v2/scrape")
    failures = [httpx.ConnectError("offline", request=request) for _ in range(4)]
    calls, sleeps = fake_firecrawl(*failures)

    assert fetch_article({"identity": {"canonical_url": "https://example.com"}}) == (
        None,
        "fetch_failed",
    )
    assert len(calls) == 4
    assert sleeps == [2.0, 6.0, 18.0]


def test_fetch_article_retries_timeouts_with_the_full_backoff(fake_firecrawl):
    request = httpx.Request("POST", "https://api.firecrawl.dev/v2/scrape")
    timeouts = [httpx.ReadTimeout("slow", request=request) for _ in range(3)]
    calls, sleeps = fake_firecrawl(
        *timeouts,
        FakeResponse(200, {"data": {"markdown": "Eventually ready"}}),
    )

    assert fetch_article({"identity": {"canonical_url": "https://example.com"}}) == (
        "Eventually ready",
        None,
    )
    assert len(calls) == 4
    assert sleeps == [2.0, 6.0, 18.0]


def test_fetch_article_reports_exhausted_server_failures(fake_firecrawl):
    calls, sleeps = fake_firecrawl(*(FakeResponse(503, {}) for _ in range(4)))
    assert fetch_article({"identity": {"canonical_url": "https://example.com"}}) == (
        None,
        "http_status_5xx",
    )
    assert len(calls) == 4
    assert sleeps == [2.0, 6.0, 18.0]


def test_firecrawl_preserves_a_top_level_provider_error(fake_firecrawl):
    fake_firecrawl(FakeResponse(404, {"error": "Page does not exist"}))

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com/missing"}}
    )

    assert result.failure_code == "http_status_4xx"
    assert result.attempts == 1
    assert result.diagnostics == {
        "category": "not_found",
        "http_status": 404,
        "provider_message": "Page does not exist",
    }


def test_firecrawl_does_not_mislabel_a_generic_provider_404_as_a_missing_page(
    fake_firecrawl,
):
    fake_firecrawl(FakeResponse(404, {"error": "Not Found", "code": "JOB_NOT_FOUND"}))

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com/present"}}
    )

    assert result.failure_code == "http_status_4xx"
    assert result.diagnostics["category"] == "provider_resource_not_found"
    assert result.diagnostics["provider_code"] == "JOB_NOT_FOUND"


def test_firecrawl_distinguishes_provider_auth_from_target_access_denial(
    fake_firecrawl,
):
    fake_firecrawl(
        FakeResponse(401, {"success": False, "error": "Unauthorized: Invalid token"})
    )

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com/private"}}
    )

    assert result.failure_code == "http_status_4xx"
    assert result.diagnostics == {
        "category": "provider_authentication",
        "http_status": 401,
        "provider_message": "Unauthorized: Invalid token",
    }


def test_firecrawl_keeps_success_false_reason_instead_of_calling_it_invalid_json(
    fake_firecrawl,
):
    fake_firecrawl(
        FakeResponse(
            200,
            {
                "success": False,
                "error": "Failed to scrape: blocked by robots.txt",
                "code": "SCRAPE_BLOCKED",
            },
        )
    )

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com/robots"}}
    )

    assert result.failure_code == "bot_wall_detected"
    assert result.diagnostics == {
        "category": "robots_blocked",
        "http_status": 200,
        "provider_message": "Failed to scrape: blocked by robots.txt",
        "provider_code": "SCRAPE_BLOCKED",
    }


def test_firecrawl_keeps_the_scrape_id_for_agentic_diagnosis(fake_firecrawl):
    fake_firecrawl(
        FakeResponse(
            200,
            {
                "success": False,
                "error": "Failed to scrape the target URL",
                "data": {"metadata": {"scrapeId": "scrape-123"}},
            },
        )
    )

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com/problem"}}
    )

    assert result.diagnostics["provider_job_id"] == "scrape-123"


def test_firecrawl_treats_explicit_target_robots_metadata_as_a_block(
    fake_firecrawl,
):
    fake_firecrawl(
        FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "markdown": "A generic shell",
                    "metadata": {
                        "statusCode": 200,
                        "error": "The target page was blocked by robots.txt",
                    },
                },
            },
        )
    )

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com/robots"}}
    )

    assert result.failure_code == "bot_wall_detected"
    assert result.diagnostics["category"] == "robots_blocked"
    assert result.diagnostics["target_http_status"] == 200


def test_firecrawl_reports_the_target_page_status_inside_a_successful_api_response(
    fake_firecrawl,
):
    fake_firecrawl(
        FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "markdown": "Not found",
                    "metadata": {
                        "statusCode": 404,
                        "sourceURL": "https://example.com/missing",
                    },
                },
            },
        )
    )

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com/missing"}}
    )

    assert result.failure_code == "http_status_4xx"
    assert result.diagnostics == {
        "category": "not_found",
        "target_http_status": 404,
        "resolved_url": "https://example.com/missing",
    }


def test_firecrawl_preserves_target_error_and_warning_metadata(fake_firecrawl):
    fake_firecrawl(
        FakeResponse(
            200,
            {
                "success": True,
                "data": {
                    "markdown": "Readable content",
                    "warning": "The page may have loaded partially",
                    "metadata": {
                        "statusCode": 200,
                        "error": "A secondary asset was blocked",
                    },
                },
            },
        )
    )

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.com/partial"}}
    )

    assert result.succeeded
    assert result.diagnostics["target_message"] == "A secondary asset was blocked"
    assert result.diagnostics["provider_warning"] == "The page may have loaded partially"


def test_openrouter_key_accepts_both_repository_spellings(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setenv("OPEN_ROUTER_API_KEY", "old-spelling")
    assert openrouter_api_key() == "old-spelling"

    monkeypatch.setenv("OPENROUTER_API_KEY", "pipeline-spelling")
    assert openrouter_api_key() == "pipeline-spelling"


def test_acquisition_cli_exposes_only_explicit_enqueue_and_one_job_work():
    parser = build_parser()
    args = parser.parse_args(["enqueue", "source-a"])
    assert args.source_id == "source-a"

    args = parser.parse_args(["work", "--job", "job-a"])
    assert args.job_id == "job-a"

    args = parser.parse_args(["work", "--forever"])
    assert args.forever is True

    with pytest.raises(SystemExit):
        parser.parse_args(["enqueue"])
    with pytest.raises(SystemExit):
        parser.parse_args(["enqueue", "source-a,source-b"])
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--syllabus", "course"])


def test_enqueue_api_refuses_batch_shaped_input(acquisition_db):
    with pytest.raises(ValueError, match="exactly one"):
        enqueue_source(acquisition_db, "source-a,source-b")


def test_enqueue_is_durable_before_any_provider_call(acquisition_db, fake_firecrawl):
    source_id = "acqx-acquisition-queued-first"
    add_source(acquisition_db, source_id)
    calls, _ = fake_firecrawl()

    job = enqueue_source(acquisition_db, source_id)

    assert calls == []
    assert job["status"] == "queued"
    assert job["attempt_count"] == 0
    assert acquisition_db.execute(
        "SELECT source_id, status FROM acquisition_job WHERE id = %s", (job["id"],)
    ).fetchone() == (source_id, "queued")
    assert acquisition_db.execute(
        "SELECT count(*) FROM source_snapshot WHERE source_id = %s", (source_id,)
    ).fetchone()[0] == 0
    assert acquisition_db.execute(
        "SELECT action, subject->>'source_id', subject->>'job_id'"
        " FROM curation_event WHERE action = 'source_acquisition_queued'"
        " AND subject->>'job_id' = %s",
        (job["id"],),
    ).fetchone() == ("source_acquisition_queued", source_id, job["id"])


def test_enqueue_deduplicates_an_active_double_click(acquisition_db):
    source_id = "acqx-acquisition-double-click"
    add_source(acquisition_db, source_id)

    first = enqueue_source(acquisition_db, source_id)
    second = enqueue_source(acquisition_db, source_id)

    assert first["id"] == second["id"]
    assert first["deduplicated"] is False
    assert second["deduplicated"] is True
    assert acquisition_db.execute(
        "SELECT count(*) FROM acquisition_job"
        " WHERE source_id = %s AND status IN ('queued', 'running')",
        (source_id,),
    ).fetchone()[0] == 1


def test_claim_marks_one_job_running_and_commits_before_fetch(acquisition_db):
    source_id = "acqx-acquisition-claim"
    add_source(acquisition_db, source_id)
    queued = enqueue_source(acquisition_db, source_id)

    claimed = claim_next_job(acquisition_db, job_id=queued["id"])

    assert claimed["id"] == queued["id"]
    assert claimed["status"] == "running"
    assert claimed["attempt_count"] == 1
    assert claimed["claimed_at"] is not None
    assert claim_next_job(acquisition_db, job_id=queued["id"]) is None


def test_database_rejects_a_legacy_status_only_finalizer(acquisition_db):
    """The migration fences an old worker that does not know claim tokens."""
    source_id = "acqx-acquisition-legacy-finalizer"
    add_source(acquisition_db, source_id)
    queued = enqueue_source(acquisition_db, source_id)
    claim_next_job(acquisition_db, job_id=queued["id"])
    snapshot_id = f"{source_id}:snap:legacy"
    artifact_id = f"{snapshot_id}:markdown"

    with pytest.raises(psycopg.errors.CheckViolation):
        acquisition_db.execute(
            "INSERT INTO source_snapshot"
            " (id, source_id, captured_at, content_hash, status)"
            " VALUES (%s, %s, now(), 'legacy-hash', 'ok')",
            (snapshot_id, source_id),
        )
        acquisition_db.execute(
            "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
            " VALUES (%s, %s, 'markdown', 'legacy-worker', '# stale')",
            (artifact_id, snapshot_id),
        )
        acquisition_db.execute(
            "UPDATE acquisition_job SET status = 'succeeded', artifact_id = %s"
            " WHERE id = %s AND status = 'running'",
            (artifact_id, queued["id"]),
        )
    acquisition_db.rollback()

    assert acquisition_db.execute(
        "SELECT count(*) FROM source_snapshot WHERE id = %s", (snapshot_id,)
    ).fetchone()[0] == 0
    assert runner.get_job(acquisition_db, queued["id"])["status"] == "running"


def test_worker_records_article_markdown_and_queues_cleanup_before_it_is_publishable(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-article-ok"
    markdown = "# Acquired lesson\n\nUseful content."
    add_source(acquisition_db, source_id)
    calls, _ = fake_firecrawl(FakeResponse(200, {"data": {"markdown": markdown}}))
    queued = enqueue_source(acquisition_db, source_id)

    job = process_next_job(acquisition_db, job_id=queued["id"])

    assert job["status"] == "succeeded"
    assert job["failure_code"] is None
    assert job["claim_token"] is None
    assert job["diagnostics"]["provider_attempts"] == 1
    assert job["diagnostics"]["pipeline_requires_cleanup"] is True
    assert len(calls) == 1

    content_hash = hashlib.sha256(markdown.encode()).hexdigest()
    snapshot_id = f"{source_id}:snap:{job['id']}:01"
    snapshot = acquisition_db.execute(
        "SELECT id, captured_at, content_hash, status, failure_note"
        " FROM source_snapshot WHERE source_id = %s",
        (source_id,),
    ).fetchone()
    assert snapshot[0] == snapshot_id
    assert snapshot[1] is not None
    assert snapshot[2:] == (content_hash, "ok", None)

    artifact = acquisition_db.execute(
        "SELECT id, snapshot_id, kind, tool, body FROM artifact"
        " WHERE snapshot_id = %s AND kind = 'markdown'",
        (snapshot_id,),
    ).fetchone()
    artifact_id = f"{snapshot_id}:markdown"
    assert artifact == (artifact_id, snapshot_id, "markdown", "firecrawl-v2", markdown)
    assert job["artifact_id"] == artifact_id

    cleanup = acquisition_db.execute(
        "SELECT acquisition_job_id, source_artifact_id, status"
        " FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()
    assert cleanup == (job["id"], artifact_id, "queued")
    duplicate = enqueue_source(acquisition_db, source_id)
    assert duplicate["id"] == job["id"]
    assert duplicate["deduplicated"] is True

    # The separate durable cleanup worker has not claimed this row yet.
    assert acquisition_db.execute(
        "SELECT count(*) FROM block WHERE artifact_id = %s", (artifact_id,)
    ).fetchone()[0] == 0
    assert acquisition_db.execute(
        "SELECT count(*) FROM passage WHERE artifact_id = %s", (artifact_id,)
    ).fetchone()[0] == 0
    assert acquisition_db.execute(
        "SELECT count(*) FROM task t JOIN passage p ON p.id = t.passage_id"
        " WHERE p.artifact_id = %s",
        (artifact_id,),
    ).fetchone()[0] == 0


def test_worker_records_a_failed_article_with_actionable_diagnostics(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-article-failed"
    add_source(acquisition_db, source_id)
    fake_firecrawl(FakeResponse(404, {"error": "No page at this URL"}))
    queued = enqueue_source(acquisition_db, source_id)

    job = process_next_job(acquisition_db, job_id=queued["id"])

    assert job["status"] == "failed"
    assert job["failure_code"] == "http_status_4xx"
    assert job["claim_token"] is None
    assert job["diagnostics"] == {
        "category": "provider_resource_not_found",
        "http_status": 404,
        "provider_attempts": 1,
        "provider_message": "No page at this URL",
    }
    snapshot_id = f"{source_id}:snap:failed:{job['id']}:01"
    assert acquisition_db.execute(
        "SELECT id, captured_at, content_hash, status, failure_note"
        " FROM source_snapshot WHERE source_id = %s",
        (source_id,),
    ).fetchone() == (snapshot_id, None, None, "failed", "http_status_4xx")
    assert acquisition_db.execute(
        "SELECT count(*) FROM artifact WHERE snapshot_id = %s", (snapshot_id,)
    ).fetchone()[0] == 0


@pytest.mark.parametrize("media_type", ["video", "book"])
def test_worker_records_unsupported_media_as_a_source_local_failure(
    acquisition_db, fake_firecrawl, media_type
):
    source_id = f"acqx-acquisition-{media_type}"
    add_source(acquisition_db, source_id, media_type=media_type)
    calls, _ = fake_firecrawl()
    queued = enqueue_source(acquisition_db, source_id)

    job = process_next_job(acquisition_db, job_id=queued["id"])

    assert calls == []
    assert job["status"] == "failed"
    assert job["failure_code"] == "unsupported_media_kind"
    snapshot_id = f"{source_id}:snap:failed:{job['id']}:01"
    assert acquisition_db.execute(
        "SELECT status, failure_note FROM source_snapshot WHERE id = %s", (snapshot_id,)
    ).fetchone() == ("failed", "unsupported_media_kind")


def test_each_failed_queue_attempt_gets_a_unique_snapshot(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-two-failures"
    add_source(acquisition_db, source_id)
    fake_firecrawl(FakeResponse(403, {}))
    first = process_next_job(
        acquisition_db, job_id=enqueue_source(acquisition_db, source_id)["id"]
    )
    fake_firecrawl(FakeResponse(404, {}))
    second = process_next_job(
        acquisition_db, job_id=enqueue_source(acquisition_db, source_id)["id"]
    )

    assert first["id"] != second["id"]
    snapshots = acquisition_db.execute(
        "SELECT id FROM source_snapshot WHERE source_id = %s ORDER BY id",
        (source_id,),
    ).fetchall()
    assert len(snapshots) == 2
    assert snapshots[0] != snapshots[1]
    assert all(":snap:failed:acq-" in row[0] for row in snapshots)


def test_a_failed_retry_preserves_the_last_good_markdown(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-last-good"
    markdown = "# Last known good"
    add_source(acquisition_db, source_id)
    fake_firecrawl(FakeResponse(200, {"data": {"markdown": markdown}}))
    successful = process_next_job(
        acquisition_db, job_id=enqueue_source(acquisition_db, source_id)["id"]
    )
    # This test isolates a later acquisition attempt. In production the UI
    # keeps re-extraction deduplicated until this downstream job is terminal.
    acquisition_db.execute(
        "DELETE FROM source_cleanup_job WHERE acquisition_job_id = %s",
        (successful["id"],),
    )
    acquisition_db.commit()
    fake_firecrawl(FakeResponse(404, {}))

    failed = process_next_job(
        acquisition_db, job_id=enqueue_source(acquisition_db, source_id)["id"]
    )

    assert successful["status"] == "succeeded"
    assert failed["status"] == "failed"
    assert acquisition_db.execute(
        "SELECT a.body FROM artifact a"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s AND sn.status = 'ok'"
        " ORDER BY a.created_at DESC LIMIT 1",
        (source_id,),
    ).fetchone()[0] == markdown


def test_each_successful_rerun_records_a_distinct_capture_and_artifact(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-idempotent"
    markdown = "Same body"
    add_source(acquisition_db, source_id)
    fake_firecrawl(FakeResponse(200, {"data": {"markdown": markdown}}))
    first = process_next_job(
        acquisition_db, job_id=enqueue_source(acquisition_db, source_id)["id"]
    )
    acquisition_db.execute(
        "DELETE FROM source_cleanup_job WHERE acquisition_job_id = %s", (first["id"],)
    )
    acquisition_db.commit()
    fake_firecrawl(FakeResponse(200, {"data": {"markdown": markdown}}))

    second = process_next_job(
        acquisition_db, job_id=enqueue_source(acquisition_db, source_id)["id"]
    )

    assert first["id"] != second["id"]
    assert first["artifact_id"] != second["artifact_id"]
    assert acquisition_db.execute(
        "SELECT count(*) FROM source_snapshot WHERE source_id = %s", (source_id,)
    ).fetchone()[0] == 2
    assert acquisition_db.execute(
        "SELECT count(*) FROM artifact a JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s AND a.kind = 'markdown'",
        (source_id,),
    ).fetchone()[0] == 2


def test_an_expired_worker_lease_is_reclaimed_source_locally(acquisition_db):
    source_id = "acqx-acquisition-expired-lease"
    add_source(acquisition_db, source_id)
    queued = enqueue_source(acquisition_db, source_id)
    first = claim_next_job(acquisition_db, job_id=queued["id"])
    acquisition_db.execute(
        "UPDATE acquisition_job SET lease_expires_at = now() - interval '1 second'"
        " WHERE id = %s",
        (queued["id"],),
    )
    acquisition_db.commit()

    reclaimed = claim_next_job(acquisition_db, job_id=queued["id"])

    assert first["attempt_count"] == 1
    assert first["claim_token"]
    assert reclaimed["id"] == queued["id"]
    assert reclaimed["attempt_count"] == 2
    assert reclaimed["claim_token"]
    assert reclaimed["claim_token"] != first["claim_token"]


@pytest.mark.parametrize(
    ("stale_markdown", "stale_failure", "suffix"),
    [
        ("# Stale capture", None, "success"),
        (None, "fetch_failed", "failure"),
    ],
)
def test_an_expired_worker_cannot_publish_after_a_new_worker_reclaims_the_job(
    acquisition_db,
    test_database_url,
    monkeypatch,
    stale_markdown,
    stale_failure,
    suffix,
):
    """A slow first worker must not publish into the second worker's lease."""
    source_id = f"acqx-acquisition-stale-worker-{suffix}"
    add_source(acquisition_db, source_id)
    queued = enqueue_source(acquisition_db, source_id)

    first_started = threading.Event()
    second_started = threading.Event()
    release_first = threading.Event()
    release_second = threading.Event()
    call_lock = threading.Lock()
    call_count = 0

    def controlled_fetch(_source):
        nonlocal call_count
        with call_lock:
            call_count += 1
            current = call_count
        if current == 1:
            first_started.set()
            assert release_first.wait(timeout=5)
            markdown, failure_code = stale_markdown, stale_failure
        else:
            second_started.set()
            assert release_second.wait(timeout=5)
            markdown, failure_code = "# Fresh capture", None
        return runner.Outcome(
            markdown,
            failure_code,
            runner.ARTICLE_PROVIDER,
            "firecrawl-v2",
            {"category": "success"},
        )

    monkeypatch.setattr(runner, "_fetch", controlled_fetch)
    results = {}
    errors = []
    worker_url = make_conninfo(
        test_database_url, options="-csearch_path=acquisition_test,public"
    )

    def work(label):
        try:
            with psycopg.connect(worker_url) as conn:
                results[label] = process_next_job(conn, job_id=queued["id"])
        except Exception as exc:  # surfaced by the assertions below
            errors.append(exc)

    first_worker = threading.Thread(target=work, args=("first",))
    first_worker.start()
    assert first_started.wait(timeout=5), errors

    acquisition_db.execute(
        "UPDATE acquisition_job SET lease_expires_at = now() - interval '1 second'"
        " WHERE id = %s",
        (queued["id"],),
    )
    acquisition_db.commit()

    second_worker = threading.Thread(target=work, args=("second",))
    second_worker.start()
    assert second_started.wait(timeout=5), errors

    # Worker one finishes while worker two owns the active lease.  Its output
    # must be discarded, not mistaken for worker two's result.
    release_first.set()
    first_worker.join(timeout=5)
    assert not first_worker.is_alive()
    assert results["first"]["status"] == "running"

    release_second.set()
    second_worker.join(timeout=5)
    assert not second_worker.is_alive()
    assert errors == []

    final_job = runner.get_job(acquisition_db, queued["id"])
    assert final_job["status"] == "succeeded"
    assert acquisition_db.execute(
        "SELECT a.body FROM artifact a"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s AND a.kind = 'markdown' ORDER BY a.created_at",
        (source_id,),
    ).fetchall() == [("# Fresh capture",)]
    assert results["second"]["artifact_id"] == final_job["artifact_id"]


def test_article_markdown_commits_and_queues_images_without_processing_them(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-image-branch"
    markdown = (
        "# Visual lesson\n\n"
        "![Revenue chart](https://cdn.example/revenue.png)\n\n"
        "Text remains independently useful."
    )
    image_urls = [
        "https://cdn.example/revenue.png",
        "https://cdn.example/diagram.webp",
    ]
    add_source(acquisition_db, source_id)
    fake_firecrawl(
        FakeResponse(
            200,
            {"data": {"markdown": markdown, "images": image_urls}},
        )
    )

    job = process_next_job(
        acquisition_db,
        job_id=enqueue_source(acquisition_db, source_id)["id"],
    )

    assert job["status"] == "succeeded"
    assert job["artifact_id"].endswith(":markdown")
    artifacts = acquisition_db.execute(
        "SELECT kind, body, metadata FROM artifact"
        " WHERE snapshot_id = (SELECT snapshot_id FROM artifact WHERE id = %s)"
        " ORDER BY kind",
        (job["artifact_id"],),
    ).fetchall()
    assert [(kind, body) for kind, body, _metadata in artifacts] == [
        ("markdown", markdown),
        ("raw-markdown", markdown),
    ]
    assert artifacts[0][2] == {
        "image_branch": "nonblocking",
        "raw_artifact_id": job["artifact_id"].replace(
            ":markdown", ":raw-markdown"
        ),
    }
    candidates = acquisition_db.execute(
        "SELECT ordinal, original_url, status, attempt_count"
        " FROM source_image_candidate WHERE acquisition_job_id = %s"
        " ORDER BY ordinal",
        (job["id"],),
    ).fetchall()
    assert candidates == [
        (1, "https://cdn.example/revenue.png", "queued", 0),
        (2, "https://cdn.example/diagram.webp", "queued", 0),
    ]
    assert acquisition_db.execute(
        "SELECT count(*) FROM source_asset WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone()[0] == 0


def test_article_logo_waits_for_source_level_image_analysis(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-filtered-image-branch"
    markdown = "# Lesson\n\n![Company logo](https://cdn.example/logo.png)\n"
    add_source(acquisition_db, source_id)
    fake_firecrawl(
        FakeResponse(
            200,
            {
                "data": {
                    "markdown": markdown,
                    "images": ["https://cdn.example/logo.png"],
                }
            },
        )
    )

    job = process_next_job(
        acquisition_db,
        job_id=enqueue_source(acquisition_db, source_id)["id"],
    )

    assert job["status"] == "succeeded"
    assert acquisition_db.execute(
        "SELECT status FROM source_image_candidate"
        " WHERE acquisition_job_id = %s",
        (job["id"],),
    ).fetchone() == ("queued",)
    assert acquisition_db.execute(
        "SELECT status FROM source_image_analysis_call"
        " WHERE markdown_artifact_id = %s",
        (job["artifact_id"],),
    ).fetchone() == ("waiting",)
    assert acquisition_db.execute(
        "SELECT id FROM artifact WHERE id = %s",
        (f"{job['artifact_id']}:images",),
    ).fetchone() is None
    assert job["artifact_id"].endswith(":markdown")


def test_stale_article_worker_rolls_back_raw_markdown_and_image_candidates(
    acquisition_db,
):
    source_id = "acqx-acquisition-stale-image-branch"
    add_source(acquisition_db, source_id)
    queued = enqueue_source(acquisition_db, source_id)
    stale_claim = claim_next_job(acquisition_db, job_id=queued["id"])
    acquisition_db.execute(
        "UPDATE acquisition_job SET claim_token = 'new-owner' WHERE id = %s",
        (queued["id"],),
    )
    acquisition_db.commit()

    result = runner._record_success(
        acquisition_db,
        stale_claim,
        runner.Outcome(
            "# Canonical",
            None,
            runner.ARTICLE_PROVIDER,
            "firecrawl-v2",
            {"category": "success"},
            raw_markdown=(
                "# Raw\n\n![Diagram](https://cdn.example/stale.png)"
            ),
            image_urls=("https://cdn.example/stale.png",),
        ),
    )

    assert result["status"] == "running"
    assert result["claim_token"] == "new-owner"
    assert acquisition_db.execute(
        "SELECT count(*) FROM source_snapshot WHERE source_id = %s",
        (source_id,),
    ).fetchone()[0] == 0
    assert acquisition_db.execute(
        "SELECT count(*) FROM source_image_candidate"
        " WHERE acquisition_job_id = %s",
        (queued["id"],),
    ).fetchone()[0] == 0


def test_shared_worker_dispatches_manual_provider_with_injected_asset_store(
    acquisition_db, monkeypatch
):
    source_id = "acqx-acquisition-manual-dispatch"
    add_source(acquisition_db, source_id)
    job_id = "acq-manual-dispatch"
    acquisition_db.execute(
        "INSERT INTO acquisition_job (id, source_id, provider) VALUES (%s, %s, %s)",
        (job_id, source_id, "manual-upload/v1"),
    )
    acquisition_db.commit()
    sentinel_store = object()
    calls = []

    def fake_manual_outcome(conn, job, *, asset_store=None):
        calls.append((conn, job.copy(), asset_store))
        return SimpleNamespace(
            markdown="# Uploaded source",
            raw_markdown=None,
            failure_code=None,
            provider="manual-upload/v1",
            tool="pdftotext",
            tool_version="manual-pdf-text.v1",
            diagnostics={
                "category": "success",
                "input_manifest_sha256": "a" * 64,
            },
        )

    monkeypatch.setattr(runner, "manual_upload_outcome", fake_manual_outcome)

    job = process_next_job(
        acquisition_db,
        job_id=job_id,
        asset_store=sentinel_store,
    )

    assert job["status"] == "succeeded"
    assert len(calls) == 1
    assert calls[0][1]["status"] == "running"
    assert calls[0][1]["claim_token"]
    assert calls[0][2] is sentinel_store
    assert acquisition_db.execute(
        "SELECT sn.content_hash, a.kind, a.tool, a.tool_version, a.body"
        " FROM source_snapshot sn JOIN artifact a ON a.snapshot_id = sn.id"
        " WHERE a.id = %s",
        (job["artifact_id"],),
    ).fetchone() == (
        "a" * 64,
        "markdown",
        "pdftotext",
        "manual-pdf-text.v1",
        "# Uploaded source",
    )


def test_stale_manual_worker_cannot_leave_visual_analysis_facts(acquisition_db):
    source_id = "acqx-acquisition-stale-manual-analysis"
    add_source(acquisition_db, source_id)
    job_id = "acq-stale-manual-analysis"
    asset_id = "asset-stale-manual-analysis"
    digest = "b" * 64
    acquisition_db.execute(
        "INSERT INTO acquisition_job (id, source_id, provider) VALUES (%s, %s, %s)",
        (job_id, source_id, "manual-upload/v1"),
    )
    acquisition_db.execute(
        "INSERT INTO source_asset"
        " (id, acquisition_job_id, source_id, ordinal, kind, filename, mime_type,"
        "  sha256, byte_size, storage_key, metadata)"
        " VALUES (%s, %s, %s, 1, 'screenshot', 'page.png', 'image/png',"
        "  %s, 100, %s, '{}')",
        (asset_id, job_id, source_id, digest, f"sha256/{digest[:2]}/{digest}"),
    )
    acquisition_db.commit()
    stale_claim = claim_next_job(acquisition_db, job_id=job_id)
    acquisition_db.execute(
        "UPDATE acquisition_job SET claim_token = 'new-manual-owner' WHERE id = %s",
        (job_id,),
    )
    acquisition_db.commit()
    diagnostics = {
        "input_mode": "images",
        "input_manifest_sha256": "c" * 64,
        "prompt_version": "manual-source-image-description.v1",
        "images": [
            {
                "asset_id": asset_id,
                "ordinal": 1,
                "kind": "screenshot",
                "requested_model": "fake/vision",
                "response_model": "fake/resolved",
                "provider": "Fake",
                "usage": {"total_tokens": 1},
                "duration_ms": 5,
                "result": {
                    "description": "A diagram.",
                    "visible_text": "Start",
                },
            }
        ],
    }

    result = runner._record_success(
        acquisition_db,
        stale_claim,
        runner.Outcome(
            "# Manual",
            None,
            "manual-upload/v1",
            "openrouter-vision",
            diagnostics,
            tool_version="manual-source-image-description.v1",
            content_hash="c" * 64,
        ),
    )

    assert result["status"] == "running"
    assert result["claim_token"] == "new-manual-owner"
    assert acquisition_db.execute(
        "SELECT count(*) FROM source_asset_analysis WHERE source_asset_id = %s",
        (asset_id,),
    ).fetchone()[0] == 0
    assert acquisition_db.execute(
        "SELECT count(*) FROM artifact a JOIN source_snapshot s"
        " ON s.id = a.snapshot_id WHERE s.source_id = %s",
        (source_id,),
    ).fetchone()[0] == 0


def test_cli_worker_runs_parent_when_it_is_the_oldest_ready_item(
    monkeypatch, capsys
):
    events = []

    class FakeConnect:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(runner, "connect", lambda: FakeConnect())
    monkeypatch.setattr(
        runner, "_oldest_ready_work_kind", lambda _conn: "acquisition"
    )

    def parent_job(_conn, *, job_id=None, asset_store=None):
        events.append(("parent", job_id, asset_store))
        return {
            "id": "acq-parent",
            "source_id": "source-parent",
            "status": "succeeded",
            "artifact_id": "artifact-parent",
            "failure_code": None,
        }

    monkeypatch.setattr(runner, "process_next_job", parent_job)
    monkeypatch.setattr(
        runner,
        "process_next_article_image",
        lambda _conn, *, asset_store=None: (
            events.append(("image", asset_store)) or None
        ),
    )

    runner.cmd_work(SimpleNamespace(job_id=None, forever=False))

    assert events == [("parent", None, None)]
    assert '"id": "acq-parent"' in capsys.readouterr().out


def test_cli_worker_runs_image_when_it_is_the_oldest_ready_item(
    monkeypatch, capsys
):
    events = []

    class FakeConnect:
        def __enter__(self):
            return object()

        def __exit__(self, *_args):
            return False

    monkeypatch.setattr(runner, "connect", lambda: FakeConnect())
    monkeypatch.setattr(
        runner, "_oldest_ready_work_kind", lambda _conn: "article_image"
    )
    monkeypatch.setattr(
        runner,
        "process_next_job",
        lambda _conn, *, job_id=None, asset_store=None: (
            events.append(("parent", job_id, asset_store)) or None
        ),
    )
    monkeypatch.setattr(
        runner,
        "process_next_article_image",
        lambda _conn, *, asset_store=None: events.append(("image", asset_store))
        or {
            "id": "image-1",
            "source_id": "source-1",
            "status": "useful",
            "asset_id": "asset-1",
            "failure_code": None,
        },
    )

    runner.cmd_work(SimpleNamespace(job_id=None, forever=False))

    assert events == [("image", None)]
    assert '"kind": "article_image"' in capsys.readouterr().out


def test_fair_worker_falls_back_when_the_oldest_image_claim_races(monkeypatch):
    conn = object()
    events = []
    monkeypatch.setattr(
        runner, "_oldest_ready_work_kind", lambda _conn: "article_image"
    )
    monkeypatch.setattr(
        runner,
        "process_next_article_image",
        lambda _conn, *, asset_store=None: events.append("image-raced") or None,
    )
    monkeypatch.setattr(
        runner,
        "process_next_job",
        lambda _conn, *, job_id=None, asset_store=None: events.append("parent")
        or {"id": "acq-fallback"},
    )

    result = runner.process_next_work_item(conn)

    assert result == ("acquisition", {"id": "acq-fallback"})
    assert events == ["image-raced", "parent"]


def test_fair_worker_selects_the_oldest_ready_row_across_both_queues(
    acquisition_db,
):
    image_source = "acqx-fair-image-source"
    parent_source = "acqx-fair-parent-source"
    add_source(acquisition_db, image_source)
    add_source(acquisition_db, parent_source)
    image_job = "acq-fair-image-parent"
    parent_job = "acq-fair-parent"
    snapshot_id = f"{image_source}:snap:fair"
    artifact_id = f"{snapshot_id}:markdown"
    acquisition_db.execute(
        "INSERT INTO acquisition_job (id, source_id, provider) VALUES (%s, %s, %s)",
        (image_job, image_source, runner.ARTICLE_PROVIDER),
    )
    acquisition_db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, captured_at, content_hash, status)"
        " VALUES (%s, %s, now(), 'fair-hash', 'ok')",
        (snapshot_id, image_source),
    )
    acquisition_db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', '# Fair')",
        (artifact_id, snapshot_id),
    )
    acquisition_db.execute(
        "UPDATE acquisition_job SET status = 'succeeded', artifact_id = %s,"
        " finished_at = now() WHERE id = %s",
        (artifact_id, image_job),
    )
    acquisition_db.execute(
        "INSERT INTO source_image_candidate"
        " (id, acquisition_job_id, source_id, snapshot_id, markdown_artifact_id,"
        "  ordinal, original_url, status, available_at)"
        " VALUES ('image-fair-oldest', %s, %s, %s, %s, 1,"
        "  'https://cdn.example/fair.png', 'queued', '2000-01-01')",
        (image_job, image_source, snapshot_id, artifact_id),
    )
    acquisition_db.execute(
        "INSERT INTO acquisition_job (id, source_id, provider, available_at)"
        " VALUES (%s, %s, %s, '2001-01-01')",
        (parent_job, parent_source, runner.ARTICLE_PROVIDER),
    )
    acquisition_db.commit()

    assert runner._oldest_ready_work_kind(acquisition_db) == "article_image"

    acquisition_db.execute(
        "UPDATE acquisition_job SET available_at = '1999-01-01' WHERE id = %s",
        (parent_job,),
    )
    acquisition_db.commit()
    assert runner._oldest_ready_work_kind(acquisition_db) == "acquisition"
    acquisition_db.execute(
        "UPDATE source_image_candidate SET status = 'filtered',"
        " filter_reason = 'test cleanup', finished_at = now()"
        " WHERE id = 'image-fair-oldest'"
    )
    acquisition_db.execute(
        "UPDATE acquisition_job SET status = 'failed', failure_code = 'test_cleanup',"
        " finished_at = now() WHERE id = %s",
        (parent_job,),
    )
    acquisition_db.commit()


class KeepOpen:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        return False


def test_enqueue_cli_prints_the_durable_job(
    acquisition_db, monkeypatch, capsys
):
    source_id = "acqx-acquisition-cli-enqueue"
    add_source(acquisition_db, source_id)
    monkeypatch.setattr(runner, "connect", lambda: KeepOpen(acquisition_db))

    runner.main(["enqueue", source_id])

    output = capsys.readouterr().out.strip()
    assert output.startswith(f"queued {source_id} as acq-")
