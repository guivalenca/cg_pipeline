"""Acquisition tests. Firecrawl is always faked; no test uses the network."""

import hashlib
import json
import re
from dataclasses import dataclass

import httpx
import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import make_conninfo
from psycopg.types.json import Jsonb

from universe.acquisition import articles, runner
from universe.acquisition.articles import fetch_article
from universe.acquisition.book_scope import extract_scope, is_missing_scope
from universe.acquisition.gates import GATE_CODES, PAYWALL_HEURISTICS, build_gate_report
from universe.acquisition.runner import acquire, build_parser
from universe.migrate import migrate


@dataclass
class FakeResponse:
    status_code: int
    payload: dict


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
        "formats": ["markdown"],
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
        "bot_wall_detected",
    )


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


def test_acquisition_cli_requires_one_target_selector():
    parser = build_parser()
    args = parser.parse_args(
        ["run", "--sources", "source-a,source-b", "--only-missing", "--workers", "2"]
    )
    assert args.source_ids == ["source-a", "source-b"]
    assert args.syllabus_id is None
    assert args.only_missing is True
    assert args.workers == 2

    with pytest.raises(SystemExit):
        parser.parse_args(["run"])
    with pytest.raises(SystemExit):
        parser.parse_args(["run", "--sources", "source-a", "--syllabus", "course"])


def test_runner_records_a_successful_article_end_to_end(acquisition_db, fake_firecrawl):
    source_id = "acqx-acquisition-article-ok"
    markdown = "# Acquired lesson\n\nUseful content."
    add_source(acquisition_db, source_id)
    calls, _ = fake_firecrawl(FakeResponse(200, {"data": {"markdown": markdown}}))

    summary = acquire(acquisition_db, source_ids=[source_id])

    assert summary["sources_processed"] == 1
    assert summary["snapshots_ok"] == 1
    assert summary["snapshots_failed"] == 0
    assert len(calls) == 1

    content_hash = hashlib.sha256(markdown.encode()).hexdigest()
    snapshot_id = f"{source_id}:snap:{content_hash[:12]}"
    snapshot = acquisition_db.execute(
        "SELECT id, captured_at, content_hash, status, failure_note"
        " FROM source_snapshot WHERE source_id = %s",
        (source_id,),
    ).fetchone()
    assert snapshot == (snapshot_id, None, content_hash, "ok", None)

    artifact = acquisition_db.execute(
        "SELECT id, snapshot_id, kind, tool, body FROM artifact WHERE snapshot_id = %s",
        (snapshot_id,),
    ).fetchone()
    artifact_id = f"{snapshot_id}:markdown"
    assert artifact == (artifact_id, snapshot_id, "markdown", "firecrawl-v2", markdown)

    run_id = summary["run_ids"][0]
    run_row = acquisition_db.execute(
        "SELECT stage, model, status, finished_at FROM run WHERE id = %s", (run_id,)
    ).fetchone()
    assert run_row[:3] == ("acquisition", "firecrawl/v2", "done")
    assert run_row[3] is not None
    item = acquisition_db.execute(
        "SELECT id, artifact_id, response, error FROM run_item WHERE run_id = %s",
        (run_id,),
    ).fetchone()
    assert item[:2] == (f"{run_id}-0001", artifact_id)
    assert json.loads(item[2]) == {
        "status": "passed",
        "failures": [],
        "warnings": [],
        "notes": "",
    }
    assert item[3] is None


def test_runner_records_a_failed_article_without_an_artifact(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-article-failed"
    add_source(acquisition_db, source_id)
    fake_firecrawl(FakeResponse(403, {}))

    summary = acquire(acquisition_db, source_ids=[source_id])

    assert summary["snapshots_ok"] == 0
    assert summary["snapshots_failed"] == 1
    snapshot_id = f"{source_id}:snap:failed"
    assert acquisition_db.execute(
        "SELECT id, captured_at, content_hash, status, failure_note"
        " FROM source_snapshot WHERE source_id = %s",
        (source_id,),
    ).fetchone() == (snapshot_id, None, None, "failed", "http_status_4xx")
    assert acquisition_db.execute(
        "SELECT count(*) FROM artifact WHERE snapshot_id = %s", (snapshot_id,)
    ).fetchone()[0] == 0

    run_id = summary["run_ids"][0]
    assert acquisition_db.execute(
        "SELECT stage, model, status, finished_at IS NOT NULL FROM run WHERE id = %s",
        (run_id,),
    ).fetchone() == ("acquisition", "firecrawl/v2", "failed", True)
    item = acquisition_db.execute(
        "SELECT artifact_id, response, error FROM run_item WHERE run_id = %s", (run_id,)
    ).fetchone()
    assert item[0] is None and item[2] is None
    assert json.loads(item[1]) == {
        "status": "failed_gate",
        "failures": ["http_status_4xx"],
        "warnings": [],
        "notes": GATE_CODES["http_status_4xx"]["description"],
    }


@pytest.mark.parametrize("media_type", ["video", "book"])
def test_runner_records_unsupported_media_as_a_failed_gate(
    acquisition_db, fake_firecrawl, media_type
):
    source_id = f"acqx-acquisition-{media_type}"
    add_source(acquisition_db, source_id, media_type=media_type)
    calls, _ = fake_firecrawl()

    summary = acquire(acquisition_db, source_ids=[source_id])

    assert calls == []
    assert summary["snapshots_failed"] == 1
    snapshot_id = f"{source_id}:snap:failed"
    assert acquisition_db.execute(
        "SELECT status, failure_note FROM source_snapshot WHERE id = %s", (snapshot_id,)
    ).fetchone() == ("failed", "unsupported_media_kind")
    response = acquisition_db.execute(
        "SELECT i.response FROM run_item i WHERE i.run_id = %s",
        (summary["run_ids"][0],),
    ).fetchone()[0]
    assert acquisition_db.execute(
        "SELECT model FROM run WHERE id = %s", (summary["run_ids"][0],)
    ).fetchone()[0] == "none"
    assert json.loads(response) == {
        "status": "failed_gate",
        "failures": ["unsupported_media_kind"],
        "warnings": [],
        "notes": GATE_CODES["unsupported_media_kind"]["description"],
    }


def test_runner_only_missing_skips_a_source_with_any_ok_snapshot(
    acquisition_db, fake_firecrawl
):
    source_id = "acqx-acquisition-already-ok"
    add_source(acquisition_db, source_id)
    acquisition_db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'existing-hash', 'ok')",
        (f"{source_id}:snap:existing", source_id),
    )
    acquisition_db.commit()
    calls, _ = fake_firecrawl()

    summary = acquire(acquisition_db, source_ids=[source_id], only_missing=True)

    assert summary == {
        "sources_processed": 0,
        "snapshots_ok": 0,
        "snapshots_failed": 0,
        "skipped": 1,
        "run_ids": [],
    }
    assert calls == []


def test_runner_syllabus_uses_the_latest_version_and_all_linked_sources(
    acquisition_db, fake_firecrawl
):
    syllabus_id = "acquisition-syllabus"
    version_id = f"{syllabus_id}:v0001"
    article_id = "acqx-acquisition-syllabus-article"
    book_id = "acqx-acquisition-syllabus-book"
    video_id = "acqx-acquisition-syllabus-video"
    add_source(acquisition_db, article_id)
    add_source(acquisition_db, book_id, media_type="book")
    add_source(acquisition_db, video_id, media_type="video")
    acquisition_db.execute(
        "INSERT INTO syllabus (id, title) VALUES (%s, 'Acquisition syllabus')",
        (syllabus_id,),
    )
    acquisition_db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES (%s, %s, 1, 'upload')",
        (version_id, syllabus_id),
    )
    for seq, source_id in enumerate((article_id, book_id, video_id), 1):
        acquisition_db.execute(
            "INSERT INTO syllabus_item"
            " (id, version_id, week, seq, kind, title, description, source_id)"
            " VALUES (%s, %s, 1, %s, 'Autoestudo', %s, 'Read it', %s)",
            (f"{version_id}:{seq:04d}", version_id, seq, source_id, source_id),
        )
    acquisition_db.commit()
    calls, _ = fake_firecrawl(
        FakeResponse(200, {"data": {"markdown": "Syllabus article"}})
    )

    summary = acquire(acquisition_db, syllabus_id=syllabus_id)

    assert summary["sources_processed"] == 3
    assert summary["snapshots_ok"] == 1
    assert summary["snapshots_failed"] == 2
    assert len(calls) == 1
    acquired = acquisition_db.execute(
        "SELECT source_id, status, failure_note FROM source_snapshot"
        " WHERE source_id = ANY(%s) ORDER BY source_id",
        ([article_id, book_id, video_id],),
    ).fetchall()
    assert acquired == [
        (article_id, "ok", None),
        (book_id, "failed", "unsupported_media_kind"),
        (video_id, "failed", "unsupported_media_kind"),
    ]
    item_ids = acquisition_db.execute(
        "SELECT id FROM run_item WHERE run_id = ANY(%s) ORDER BY id",
        (summary["run_ids"],),
    ).fetchall()
    assert {item_id.rsplit("-", 1)[1] for item_id, in item_ids} == {
        "0001",
        "0002",
        "0003",
    }


def test_runner_reuses_content_addressed_rows_on_rerun(acquisition_db, fake_firecrawl):
    source_id = "acqx-acquisition-idempotent"
    markdown = "Same body"
    add_source(acquisition_db, source_id)
    fake_firecrawl(FakeResponse(200, {"data": {"markdown": markdown}}))
    first = acquire(acquisition_db, source_ids=[source_id])
    fake_firecrawl(FakeResponse(200, {"data": {"markdown": markdown}}))

    second = acquire(acquisition_db, source_ids=[source_id])

    assert first["run_ids"] != second["run_ids"]
    assert acquisition_db.execute(
        "SELECT count(*) FROM source_snapshot WHERE source_id = %s", (source_id,)
    ).fetchone()[0] == 1
    assert acquisition_db.execute(
        "SELECT count(*) FROM artifact a JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s",
        (source_id,),
    ).fetchone()[0] == 1


def test_runner_batches_same_model_items_under_one_run(acquisition_db, fake_firecrawl):
    source_ids = ["acqx-acquisition-batch-a", "acqx-acquisition-batch-b"]
    for source_id in source_ids:
        add_source(acquisition_db, source_id)
    fake_firecrawl(
        FakeResponse(200, {"data": {"markdown": "Body A"}}),
        FakeResponse(200, {"data": {"markdown": "Body B"}}),
    )

    summary = acquire(acquisition_db, source_ids=source_ids)

    assert len(summary["run_ids"]) == 1
    run_id = summary["run_ids"][0]
    assert acquisition_db.execute(
        "SELECT id FROM run_item WHERE run_id = %s ORDER BY id", (run_id,)
    ).fetchall() == [(f"{run_id}-0001",), (f"{run_id}-0002",)]


def test_runner_keeps_passed_and_failed_articles_in_one_firecrawl_run(
    acquisition_db, fake_firecrawl
):
    source_ids = ["acqx-acquisition-mixed-ok", "acqx-acquisition-mixed-failed"]
    for source_id in source_ids:
        add_source(acquisition_db, source_id)
    fake_firecrawl(
        FakeResponse(200, {"data": {"markdown": "Body"}}),
        FakeResponse(403, {}),
    )

    summary = acquire(acquisition_db, source_ids=source_ids)

    assert len(summary["run_ids"]) == 1
    run_id = summary["run_ids"][0]
    assert acquisition_db.execute(
        "SELECT model, status FROM run WHERE id = %s", (run_id,)
    ).fetchone() == ("firecrawl/v2", "done")
    reports = [
        json.loads(row[0])
        for row in acquisition_db.execute(
            "SELECT response FROM run_item WHERE run_id = %s ORDER BY id", (run_id,)
        ).fetchall()
    ]
    assert reports == [
        {"status": "passed", "failures": [], "warnings": [], "notes": ""},
        {
            "status": "failed_gate",
            "failures": ["http_status_4xx"],
            "warnings": [],
            "notes": GATE_CODES["http_status_4xx"]["description"],
        },
    ]


class KeepOpen:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        return False


def test_runner_cli_prints_processed_and_snapshot_counts(
    acquisition_db, fake_firecrawl, monkeypatch, capsys
):
    source_id = "acqx-acquisition-cli-output"
    add_source(acquisition_db, source_id)
    fake_firecrawl(FakeResponse(200, {"data": {"markdown": "CLI body"}}))
    monkeypatch.setattr(runner, "connect", lambda: KeepOpen(acquisition_db))

    runner.main(["run", "--sources", source_id])

    assert capsys.readouterr().out.splitlines() == [
        "sources processed: 1",
        "snapshots ok: 1",
        "snapshots failed: 0",
    ]
