"""Harness tests. The transport is faked, so nothing here touches a network."""

import hashlib

import pytest

from universe import harness
from universe.model_client import ModelClient, ModelError

STAGE = "passage-segmentation"
VERSION = "v001"


def fake_transport(reply: str = "one passage", fail_on: str | None = None, calls: list = None):
    """A transport that answers instantly, and refuses prompts containing `fail_on`."""

    def transport(url, headers, payload, timeout):
        prompt = payload["messages"][0]["content"]
        if calls is not None:
            calls.append(payload)
        if fail_on and fail_on in prompt:
            raise ModelError("HTTP 502: upstream said no")
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


def test_prompt_ref_and_sha_come_from_the_file_on_disk(prompt):
    path = harness.PROMPTS_DIR / STAGE / f"{VERSION}.md"
    assert prompt.ref == f"{STAGE}/{VERSION}"
    assert prompt.sha == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "{{body}}" not in prompt.render("SOMETHING")


def test_run_records_the_stamp_the_items_and_the_usage(db, prompt, targets):
    calls: list = []
    summary = harness.execute(
        db, STAGE, prompt, client(transport=fake_transport(calls=calls)), targets
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
    assert "BODY OF SOURCE" in sent and "Passage segmentation" in sent


def test_a_failing_item_is_recorded_without_killing_the_run(db, prompt, targets):
    summary = harness.execute(
        db, STAGE, prompt, client(transport=fake_transport(fail_on="SOURCE 2")), targets
    )
    assert summary == {"run_id": summary["run_id"], "status": "done", "ok": 1, "failed": 1}

    items = harness.fetch_items(db, summary["run_id"])
    failed = [item for item in items if item["error"]]
    assert len(failed) == 1
    assert "upstream said no" in failed[0]["error"]
    assert failed[0]["response"] is None
    assert failed[0]["source_id"] == "harness-src-2"


def test_a_run_where_everything_fails_is_marked_failed(db, prompt, targets):
    summary = harness.execute(
        db, STAGE, prompt, client(transport=fake_transport(fail_on="BODY")), targets
    )
    assert summary["status"] == "failed" and summary["ok"] == 0
    assert harness.fetch_run(db, summary["run_id"])["status"] == "failed"


def test_run_ids_are_readable_and_sortable(db, prompt, targets):
    first = harness.execute(db, STAGE, prompt, client(transport=fake_transport()), targets[:1])
    second = harness.execute(db, STAGE, prompt, client(transport=fake_transport()), targets[:1])
    assert first["run_id"].startswith("r") and len(first["run_id"]) == 5
    assert first["run_id"] < second["run_id"]


def test_report_holds_the_stamp_and_every_response(db, prompt, targets, tmp_path):
    summary = harness.execute(
        db, STAGE, prompt, client(transport=fake_transport(fail_on="SOURCE 2")), targets
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
    both = harness.execute(db, STAGE, prompt, client(transport=fake_transport("left")), targets)
    one = harness.execute(
        db, STAGE, prompt, client(transport=fake_transport("right")), targets[:1]
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
    harness.execute(db, STAGE, prompt, client(transport=fake_transport(fail_on="SOURCE 2")), targets)
    monkeypatch.setattr(harness, "connect", lambda *a, **k: KeepOpen(db))
    harness.main(["list"])

    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.startswith("r")]
    assert lines, out
    assert STAGE in lines[-1] and "fake/model" in lines[-1] and "1/2" in lines[-1]


def test_report_via_the_cli(db, prompt, targets, monkeypatch, capsys, tmp_path):
    summary = harness.execute(db, STAGE, prompt, client(transport=fake_transport()), targets[:1])
    monkeypatch.setattr(harness, "connect", lambda *a, **k: KeepOpen(db))
    monkeypatch.setattr(harness, "REPORTS_DIR", tmp_path)
    harness.main(["report", summary["run_id"]])

    printed = capsys.readouterr().out.strip()
    assert printed == str(tmp_path / f"{summary['run_id']}.html")
    assert (tmp_path / f"{summary['run_id']}.html").exists()


def test_a_missing_prompt_version_is_a_clear_error():
    with pytest.raises(SystemExit, match="no prompt at"):
        harness.load_prompt(STAGE, "v999")
