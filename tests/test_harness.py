"""Harness tests. The transport is faked, so nothing here touches a network."""

import hashlib
import threading
import time
import uuid

import psycopg
import pytest

from universe import harness
from universe.model_client import (
    DEFAULT_API_BASE,
    DEFAULT_ROUTING,
    EmbeddingClient,
    ModelClient,
    ModelError,
    is_transient_failure,
)

STAGE = "passage-cuts"
VERSION = "v001"


def fake_transport(reply: str = "one passage", fail_on: str | None = None, calls: list = None):
    """A transport that answers instantly, and refuses prompts containing `fail_on`."""

    def transport(url, headers, payload, timeout):
        prompt = payload["messages"][0]["content"]
        if calls is not None:
            calls.append(payload)
        if fail_on and fail_on in prompt:
            raise ModelError("upstream said no")
        return {
            "choices": [{"message": {"content": reply}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        }

    return transport


def client(**kwargs) -> ModelClient:
    return ModelClient("fake/model", api_base="https://example.invalid/v1", **kwargs)


class KeepOpen:
    """`with connect() as conn` must not close the session-scoped test connection."""

    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *exc):
        return False


@pytest.fixture(scope="session")
def targets(db) -> list[harness.Target]:
    """Two sources of the harness's own, independent of the fixture backfill."""
    for number, title in ((1, "Alpha lesson"), (2, "Beta lesson")):
        source_id = f"harness-src-{number}"
        snapshot_id = f"{source_id}:snap:test"
        db.execute(
            "INSERT INTO source (id, identity, title, media_type)"
            " VALUES (%s, '{\"kind\": \"test\"}', %s, 'article') ON CONFLICT DO NOTHING",
            (source_id, title),
        )
        db.execute(
            "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
            " VALUES (%s, %s, 'deadbeef', 'ok') ON CONFLICT DO NOTHING",
            (snapshot_id, source_id),
        )
        db.execute(
            "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
            " VALUES (%s, %s, 'markdown', 'test', %s) ON CONFLICT DO NOTHING",
            (f"{snapshot_id}:markdown", snapshot_id, f"BODY OF SOURCE {number}"),
        )
    db.commit()
    return harness.select_targets(db, ["harness-src-1", "harness-src-2"])


@pytest.fixture(scope="session")
def prompt() -> harness.Prompt:
    return harness.load_prompt(STAGE, VERSION)


def test_select_targets_returns_the_latest_artifact_per_source(targets):
    assert [target.source_id for target in targets] == ["harness-src-1", "harness-src-2"]
    assert targets[0].body == "BODY OF SOURCE 1"


def test_explicit_artifact_selection_accepts_only_the_current_publication(db):
    marker = uuid.uuid4().hex
    source_id = f"harness-publication-{marker}"
    snapshot_id = f"{source_id}:snapshot"
    publication_id = f"{snapshot_id}:published"
    intermediate_id = f"{snapshot_id}:intermediate"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Pinned publication', 'article')",
        (source_id, f'{{"kind":"test","value":"{marker}"}}'),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, %s, 'ok')",
        (snapshot_id, source_id, marker),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body, created_at)"
        " VALUES (%s, %s, 'markdown', 'legacy-import', '# Published', now()),"
        " (%s, %s, 'markdown', 'article-main-content-boundary',"
        " '# Intermediate', now() + interval '1 second')",
        (publication_id, snapshot_id, intermediate_id, snapshot_id),
    )
    db.commit()

    selected = harness.select_targets(db, artifact_ids=[publication_id])

    assert [target.artifact_id for target in selected] == [publication_id]
    with pytest.raises(SystemExit, match="not a current Source Publication"):
        harness.select_targets(db, artifact_ids=[intermediate_id])


def test_next_numeric_run_id_ignores_historical_non_numeric_ids(db):
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, finished_at)"
        " VALUES ('foreign-history', 'test', 'fake/model', 'test/v1',"
        " 'abc', 'done', now()) ON CONFLICT DO NOTHING"
    )
    db.commit()

    identifier = harness.next_run_id(db)

    assert identifier.startswith("r")
    assert identifier[1:].isdigit()


def test_prompt_ref_and_sha_come_from_the_file_on_disk(prompt):
    path = harness.PROMPTS_DIR / STAGE / f"{VERSION}.md"
    assert prompt.ref == f"{STAGE}/{VERSION}"
    assert prompt.sha == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "{{body}}" not in prompt.render("SOMETHING")


def test_run_records_the_stamp_the_items_and_the_usage(db, prompt, targets):
    calls: list = []
    summary = harness.execute(
        db, prompt, client(transport=fake_transport(calls=calls)), targets
    )
    assert summary["ok"] == 2 and summary["failed"] == 0 and summary["status"] == "done"

    run = harness.fetch_run(db, summary["run_id"])
    assert run["prompt_ref"] == f"{STAGE}/{VERSION}"
    assert run["prompt_sha"] == prompt.sha
    assert run["params"]["max_tokens"] > 0
    assert run["finished_at"] is not None

    items = harness.fetch_items(db, summary["run_id"])
    assert len(items) == 2
    assert all(item["response"] == "one passage" and item["error"] is None for item in items)
    assert all(item["usage"]["total_tokens"] == 120 for item in items)
    assert all(item["duration_ms"] is not None for item in items)

    # The artifact body reached the model inside the template, not on its own.
    sent = calls[0]["messages"][0]["content"]
    assert "BODY OF SOURCE" in sent and "Use the report_cuts tool" in sent


def test_parallel_run_persists_a_fast_paid_result_before_a_slow_sibling_finishes(
    test_database_url, db, prompt, targets
):
    """A crash behind one slow call must not erase already-paid sibling work."""
    slow_started = threading.Event()
    fast_finished = threading.Event()
    release_slow = threading.Event()
    marker = uuid.uuid4().hex
    result = {}

    def transport(url, headers, payload, timeout):
        rendered = payload["messages"][0]["content"]
        if "SOURCE 1" in rendered:
            slow_started.set()
            assert release_slow.wait(timeout=5)
        else:
            fast_finished.set()
        return fake_transport()(url, headers, payload, timeout)

    def run():
        with psycopg.connect(test_database_url) as conn:
            result.update(
                harness.execute(
                    conn,
                    prompt,
                    client(transport=transport),
                    targets,
                    workers=2,
                    run_params={"completion_order_test": marker},
                )
            )

    worker = threading.Thread(target=run)
    worker.start()
    try:
        assert slow_started.wait(timeout=5)
        assert fast_finished.wait(timeout=5)
        with psycopg.connect(test_database_url) as observer:
            deadline = time.monotonic() + 2
            while True:
                persisted = observer.execute(
                    "SELECT count(*) FROM run_item i JOIN run r ON r.id = i.run_id"
                    " WHERE r.params ->> 'completion_order_test' = %s",
                    (marker,),
                ).fetchone()[0]
                if persisted or time.monotonic() >= deadline:
                    break
                time.sleep(0.01)
        assert persisted == 1
    finally:
        release_slow.set()
        worker.join(timeout=5)

    assert not worker.is_alive()
    assert result["ok"] == 2


def test_run_records_explicit_upstream_inputs(db, prompt, targets):
    summary = harness.execute(
        db,
        prompt,
        client(transport=fake_transport()),
        targets[:1],
        run_params={"gen_runs": ["r0001"], "revision_run": "r0002"},
    )
    params = harness.fetch_run(db, summary["run_id"])["params"]
    assert params["gen_runs"] == ["r0001"]
    assert params["revision_run"] == "r0002"


def test_a_failing_item_is_recorded_without_killing_the_run(db, prompt, targets):
    summary = harness.execute(
        db, prompt, client(transport=fake_transport(fail_on="SOURCE 2")), targets
    )
    assert summary == {"run_id": summary["run_id"], "status": "done", "ok": 1, "failed": 1}

    items = harness.fetch_items(db, summary["run_id"])
    failed = [item for item in items if item["error"]]
    assert len(failed) == 1
    assert "upstream said no" in failed[0]["error"]
    assert failed[0]["response"] is None
    assert failed[0]["source_id"] == "harness-src-2"
    assert failed[0]["usage"]["retry_count"] == 0


def test_transient_failure_is_retried_inside_the_item_worker(
    db, prompt, targets, monkeypatch
):
    calls = 0
    sleeps = []

    def flaky(url, headers, payload, timeout):
        nonlocal calls
        calls += 1
        if calls < 3:
            raise ModelError("upstream unavailable", status_code=503)
        return fake_transport()(url, headers, payload, timeout)

    monkeypatch.setattr(harness.random, "random", lambda: 1.0)
    monkeypatch.setattr(harness.time, "sleep", sleeps.append)
    summary = harness.execute(db, prompt, client(transport=flaky), targets[:1])

    assert summary["ok"] == 1
    assert calls == 3
    assert sleeps == [2.0, 6.0]
    item = harness.fetch_items(db, summary["run_id"])[0]
    assert item["usage"]["retry_count"] == 2


def test_transient_failure_stops_after_four_total_attempts(
    db, prompt, targets, monkeypatch
):
    calls = 0
    sleeps = []

    def rate_limited(url, headers, payload, timeout):
        nonlocal calls
        calls += 1
        raise ModelError("rate limited", status_code=429)

    monkeypatch.setattr(harness.random, "random", lambda: 1.0)
    monkeypatch.setattr(harness.time, "sleep", sleeps.append)
    summary = harness.execute(db, prompt, client(transport=rate_limited), targets[:1])

    assert summary["failed"] == 1
    assert calls == 4
    assert sleeps == [2.0, 6.0, 18.0]
    item = harness.fetch_items(db, summary["run_id"])[0]
    assert item["usage"]["retry_count"] == 3


def test_non_transient_failure_is_not_retried(db, prompt, targets, monkeypatch):
    calls = 0
    sleeps = []

    def malformed(url, headers, payload, timeout):
        nonlocal calls
        calls += 1
        return {"choices": []}

    monkeypatch.setattr(harness.time, "sleep", sleeps.append)
    summary = harness.execute(db, prompt, client(transport=malformed), targets[:1])

    assert summary["failed"] == 1
    assert calls == 1
    assert sleeps == []


def test_a_response_that_is_not_text_fails_its_item_only(db, prompt, targets):
    """Content blocks instead of a string must not take the whole run down."""

    def blocks(url, headers, payload, timeout):
        if "SOURCE 2" in payload["messages"][0]["content"]:
            return {"choices": [{"message": {"content": [{"type": "text", "text": "hi"}]}}]}
        return fake_transport()(url, headers, payload, timeout)

    summary = harness.execute(db, prompt, client(transport=blocks), targets)
    assert summary["ok"] == 1 and summary["failed"] == 1

    items = harness.fetch_items(db, summary["run_id"])
    assert len(items) == 2
    failed = [item for item in items if item["error"]][0]
    assert "content is not text" in failed["error"]


def test_an_empty_selection_selects_nothing(db, targets):
    """Only None means "no restriction"; a falsy selection must not mean "all"."""
    assert harness.select_targets(db, [], None) == []
    assert harness.select_targets(db, None, 0) == []
    assert len(harness.select_targets(db, None, 1)) == 1


@pytest.mark.parametrize("selection", [["--sources", ""], ["--limit", "0"], ["--limit", "-1"]])
def test_the_cli_refuses_an_empty_selection(selection):
    argv = ["run", "--stage", STAGE, "--prompt", VERSION, "--model", "m", *selection]
    with pytest.raises(SystemExit):
        harness.build_parser().parse_args(argv)


def test_a_run_where_everything_fails_is_marked_failed(db, prompt, targets):
    summary = harness.execute(
        db, prompt, client(transport=fake_transport(fail_on="BODY")), targets
    )
    assert summary["status"] == "failed" and summary["ok"] == 0
    assert harness.fetch_run(db, summary["run_id"])["status"] == "failed"


def test_run_ids_are_readable_and_sortable(db, prompt, targets):
    first = harness.execute(db, prompt, client(transport=fake_transport()), targets[:1])
    second = harness.execute(db, prompt, client(transport=fake_transport()), targets[:1])
    assert first["run_id"].startswith("r") and len(first["run_id"]) == 5
    assert first["run_id"] < second["run_id"]


def test_report_holds_the_stamp_and_every_response(db, prompt, targets, tmp_path):
    summary = harness.execute(
        db, prompt, client(transport=fake_transport(fail_on="SOURCE 2")), targets
    )
    path = harness.write_report(db, summary["run_id"], tmp_path)
    html = path.read_text()

    assert path.name == f"{summary['run_id']}.html"
    assert html.startswith("<!doctype html>") and html.rstrip().endswith("</html>")
    assert prompt.sha[:12] in html
    assert f"{STAGE}/{VERSION}" in html and "fake/model" in html
    assert "Alpha lesson" in html and "one passage" in html
    assert "prefers-color-scheme" in html
    assert "pre class='error'" in html and "upstream said no" in html
    assert "total_tokens 120" in html


def test_compare_puts_shared_items_side_by_side_and_names_the_rest(db, prompt, targets, tmp_path):
    both = harness.execute(db, prompt, client(transport=fake_transport("left")), targets)
    one = harness.execute(
        db, prompt, client(transport=fake_transport("right")), targets[:1]
    )

    path = harness.write_comparison(db, both["run_id"], one["run_id"], tmp_path)
    html = path.read_text()

    assert path.name == f"{both['run_id']}-vs-{one['run_id']}.html"
    assert "left" in html and "right" in html
    assert "Alpha lesson" in html
    assert "1 artifact(s) in both runs" in html
    assert "Not compared." in html
    assert "harness-src-2:snap:test:markdown" in html


def test_list_shows_each_run_with_its_item_counts(db, prompt, targets, monkeypatch, capsys):
    summary = harness.execute(
        db, prompt, client(transport=fake_transport(fail_on="SOURCE 2")), targets
    )
    monkeypatch.setattr(harness, "connect", lambda *a, **k: KeepOpen(db))
    harness.main(["list"])

    out = capsys.readouterr().out
    lines = [
        line for line in out.splitlines()
        if line.startswith(f"{summary['run_id']} ")
    ]
    assert lines, out
    own_line = next(line for line in lines if line.split()[0] == summary["run_id"])
    assert STAGE in own_line and "fake/model" in own_line and "1/2" in own_line


def test_report_via_the_cli(db, prompt, targets, monkeypatch, capsys, tmp_path):
    summary = harness.execute(db, prompt, client(transport=fake_transport()), targets[:1])
    monkeypatch.setattr(harness, "connect", lambda *a, **k: KeepOpen(db))
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)
    harness.main(["report", summary["run_id"]])

    printed = capsys.readouterr().out.strip()
    assert printed == str(tmp_path / f"{summary['run_id']}.html")
    assert (tmp_path / f"{summary['run_id']}.html").exists()


def test_a_missing_prompt_version_is_a_clear_error():
    with pytest.raises(SystemExit, match="no prompt at"):
        harness.load_prompt(STAGE, "v999")


def test_extra_payload_is_sent_and_stamped():
    calls = []
    extra = {"thinking": {"type": "enabled"}, "reasoning_effort": "high"}
    c = client(transport=fake_transport(calls=calls), extra=extra)
    c.complete("hello")
    assert calls[0]["thinking"] == {"type": "enabled"}
    assert calls[0]["reasoning_effort"] == "high"
    assert c.params["thinking"] == {"type": "enabled"}
    assert c.params["reasoning_effort"] == "high"


def test_routing_defaults_are_sent_and_stamped():
    calls = []
    c = client(transport=fake_transport(calls=calls))
    c.complete("hello")

    assert calls[0]["provider"] == DEFAULT_ROUTING["provider"]
    assert c.params["provider"] == DEFAULT_ROUTING["provider"]


def test_explicit_extra_overrides_fields_inside_routing_defaults():
    calls = []
    extra = {"provider": {"ignore": ["OtherProvider"], "sort": "price"}}
    c = client(transport=fake_transport(calls=calls), extra=extra)
    c.complete("hello")

    assert calls[0]["provider"] == {
        "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
        "ignore": ["OtherProvider"],
        "sort": "price",
    }
    assert DEFAULT_ROUTING["provider"]["ignore"] == ["SiliconFlow"]


@pytest.mark.parametrize(
    ("error", "transient"),
    [
        (ModelError("rate limited", status_code=429), True),
        (ModelError("server failure", status_code=500), True),
        (ModelError("server failure", status_code=599), True),
        (ModelError("HTTP 502: bad gateway"), True),
        (TimeoutError("timed out"), True),
        (ConnectionResetError("reset"), True),
        (ModelError("bad request", status_code=400), False),
        (ModelError("not found", status_code=404), False),
        (ModelError("unexpected response shape"), False),
    ],
)
def test_transient_failure_classification(error, transient):
    assert is_transient_failure(error) is transient


def test_api_error_status_is_available_to_the_transient_classifier():
    def transport(url, headers, payload, timeout):
        return {"error": {"code": 429, "message": "rate limited"}}

    with pytest.raises(ModelError) as raised:
        client(transport=transport).complete("hello")

    assert is_transient_failure(raised.value)


def test_retry_backoff_schedule_is_exponential_and_capped():
    assert [
        harness.retry_backoff_seconds(retry_number, jitter=1.0)
        for retry_number in range(1, 6)
    ] == [2.0, 6.0, 18.0, 54.0, 54.0]
    assert harness.retry_backoff_seconds(1, jitter=0.0) == 1.6


def test_model_client_api_base_fallback_order(monkeypatch):
    monkeypatch.delenv("MODEL_API_BASE", raising=False)
    assert ModelClient("fake/model").api_base == DEFAULT_API_BASE

    monkeypatch.setenv("MODEL_API_BASE", "https://env.example/v1")
    assert ModelClient("fake/model").api_base == "https://env.example/v1"
    assert (
        ModelClient("fake/model", api_base="https://explicit.example/v1").api_base
        == "https://explicit.example/v1"
    )
    empty_client = ModelClient("fake/model", api_base="")
    assert empty_client.api_base == ""
    with pytest.raises(ModelError, match="MODEL_API_BASE is not set"):
        empty_client.complete("hello")


def test_model_client_api_key_fallback_order(monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPEN_ROUTER_API_KEY", raising=False)
    assert ModelClient("fake/model").api_key == ""

    monkeypatch.setenv("MODEL_API_KEY", "model-key")
    assert ModelClient("fake/model").api_key == "model-key"

    monkeypatch.delenv("MODEL_API_KEY")
    monkeypatch.setenv("OPENROUTER_API_KEY", "cg-openrouter-key")
    assert ModelClient("fake/model").api_key == "cg-openrouter-key"

    monkeypatch.delenv("OPENROUTER_API_KEY")
    monkeypatch.setenv("OPEN_ROUTER_API_KEY", "open-router-key")
    assert ModelClient("fake/model").api_key == "open-router-key"

    monkeypatch.setenv("MODEL_API_KEY", "model-key")
    assert ModelClient("fake/model", api_key="explicit-key").api_key == "explicit-key"


def test_embedding_client_embed_returns_ordered_vectors_and_usage():
    calls = []

    def transport(url, headers, payload, timeout):
        calls.append((url, headers, payload, timeout))
        return {
            "data": [
                {"index": 1, "embedding": [3.0, 4.0]},
                {"index": 0, "embedding": [1.0, 2.0]},
            ],
            "usage": {"prompt_tokens": 2, "total_tokens": 2},
        }

    client = EmbeddingClient(
        "fake/embedding-model",
        api_base="https://example.invalid/v1",
        transport=transport,
    )
    vectors, usage, duration_ms = client.embed(["hello", "world"])

    url, _, payload, _ = calls[0]
    assert url.endswith("/embeddings")
    assert payload == {
        "model": "fake/embedding-model",
        "input": ["hello", "world"],
    }
    assert vectors == [[1.0, 2.0], [3.0, 4.0]]
    assert usage == {"prompt_tokens": 2, "total_tokens": 2}
    assert duration_ms >= 0


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"error": {"message": "upstream failed"}}, "api error"),
        ({"data": [{"index": 0, "embedding": [1.0]}]}, "expected 2 embeddings, got 1"),
        (
            {"data": [{"index": 0}, {"index": 1, "embedding": [2.0]}]},
            "item without embedding",
        ),
        (
            {"data": [{"index": 0, "embedding": []}, {"index": 1, "embedding": [2.0]}]},
            "empty embedding vector",
        ),
    ],
)
def test_embedding_client_rejects_error_responses(body, message):
    def transport(url, headers, payload, timeout):
        return body

    client = EmbeddingClient(
        "fake/embedding-model",
        api_base="https://example.invalid/v1",
        transport=transport,
    )
    with pytest.raises(ModelError, match=message):
        client.embed(["hello", "world"])


def test_load_tool_includes_parallel_tool_calls_false(tmp_path):
    """Verify that load_tool includes parallel_tool_calls: False to prevent multiple calls."""
    tool_file = tmp_path / "test_tool.json"
    tool_file.write_text('{"name": "test", "description": "Test tool", "parameters": {"type": "object"}}')
    
    result = harness.load_tool(str(tool_file))
    
    assert "parallel_tool_calls" in result
    assert result["parallel_tool_calls"] is False
    assert "tools" in result
    assert "tool_choice" in result


def test_parallel_tool_calls_is_sent_in_request_payload(tmp_path):
    """Verify that parallel_tool_calls: false is actually sent to the model."""
    tool_file = tmp_path / "test_tool.json"
    tool_file.write_text('{"name": "test", "description": "Test tool", "parameters": {"type": "object"}}')
    
    tool_dict = harness.load_tool(str(tool_file))
    calls = []
    
    # Create a transport that returns a valid tool call response
    def tool_transport(url, headers, payload, timeout):
        calls.append(payload)
        return {
            "choices": [{
                "message": {
                    "tool_calls": [{
                        "function": {"name": "test", "arguments": '{"key": "value"}'}
                    }]
                },
                "finish_reason": "tool_calls"
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        }
    
    # Create a client with the tool dict merged into extra
    c = client(transport=tool_transport, extra=tool_dict)
    c.complete("hello")
    
    # Verify the payload sent includes parallel_tool_calls: false
    assert calls[0]["parallel_tool_calls"] is False
    assert calls[0]["tools"] is not None
    assert calls[0]["tool_choice"] is not None
