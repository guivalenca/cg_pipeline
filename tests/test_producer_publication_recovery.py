"""Crash recovery at the Source Publication cleanup boundary."""

from dataclasses import dataclass

import pytest

from universe import harness, pipeline_lease, producer_publication
from universe.blocks import BLOCKER_VERSION
from universe.recipe_identity import recipe_identity


@dataclass
class StubClient:
    response: str
    calls: list[str]
    must_not_call: bool = False

    def __post_init__(self) -> None:
        identity = recipe_identity("passage-cuts")
        self.model = identity["model"]
        self.params = identity["model_params"]

    def complete(self, rendered: str):
        if self.must_not_call:
            raise AssertionError("publish-only recovery called the provider")
        self.calls.append(rendered)
        return self.response, {}, 1


def _seed_source(db) -> tuple[str, str]:
    source_id = "publication-recovery-source"
    snapshot_id = "publication-recovery-snapshot"
    artifact_id = "publication-recovery-artifact"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{}'::jsonb, 'Recovery source', 'markdown')",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'recovery-hash', 'ok')",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', 'Alpha.\n\nBeta.')",
        (artifact_id, snapshot_id),
    )
    for seq, body, start, end in (
        (1, "Alpha.", 0, 6),
        (2, "Beta.", 8, 13),
    ):
        db.execute(
            "INSERT INTO block"
            " (id, artifact_id, blocker_version, seq, kind, start_char, end_char, body)"
            " VALUES (%s, %s, %s, %s, 'paragraph', %s, %s, %s)",
            (f"recovery-block-{seq}", artifact_id, BLOCKER_VERSION, seq, start, end, body),
        )
    db.commit()
    return source_id, artifact_id


def _lease_environment(monkeypatch, lease: pipeline_lease.Lease) -> None:
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_SCOPE", lease.scope_key)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_STAGE", lease.stage)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_TOKEN", lease.token)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_OWNER", lease.owner_id)


def test_expired_owner_recovers_passage_publication_without_another_provider_call(
    db, monkeypatch
):
    source_id, artifact_id = _seed_source(db)
    identity = recipe_identity("passage-cuts")
    prompt = harness.load_prompt("passage-cuts", "v001")
    target = harness.Target(
        source_id,
        None,
        artifact_id,
        '<block n="1">Alpha.</block>\n\n<block n="2">Beta.</block>',
    )
    run_params = {"body_from": "blocks", "blocker_version": BLOCKER_VERSION}
    old = pipeline_lease.acquire(
        db,
        scope_key=f"source:{source_id}",
        stage="passage-cuts",
        owner_id="old-worker",
    )
    assert old is not None
    db.commit()
    _lease_environment(monkeypatch, old)

    real_finalize = producer_publication.finalize
    real_release = pipeline_lease.release
    monkeypatch.setattr(
        producer_publication,
        "finalize",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("simulated death")),
    )
    monkeypatch.setattr(pipeline_lease, "release", lambda *_args, **_kwargs: False)
    first_calls: list[str] = []
    with pytest.raises(RuntimeError, match="simulated death"):
        harness.execute(
            db,
            prompt,
            StubClient('{"cuts":[2]}', first_calls),
            [target],
            workers=1,
            run_params=run_params,
        )
    monkeypatch.setattr(producer_publication, "finalize", real_finalize)
    monkeypatch.setattr(pipeline_lease, "release", real_release)

    orphan = db.execute(
        "SELECT id FROM run WHERE stage = 'passage-cuts' AND status = 'publishing'"
    ).fetchone()[0]
    assert first_calls and db.execute(
        "SELECT count(*) FROM passage_origin WHERE run_id = %s", (orphan,)
    ).fetchone()[0] == 0

    db.execute(
        "UPDATE pipeline_lease SET"
        " heartbeat_at = clock_timestamp() - interval '2 seconds',"
        " expires_at = clock_timestamp() - interval '1 second'"
        " WHERE scope_key = %s AND stage = %s AND token = %s",
        (old.scope_key, old.stage, old.token),
    )
    db.commit()
    successor = pipeline_lease.acquire(
        db,
        scope_key=old.scope_key,
        stage=old.stage,
        owner_id="successor-worker",
    )
    assert successor is not None
    db.commit()
    _lease_environment(monkeypatch, successor)

    recovered = harness.execute(
        db,
        prompt,
        StubClient('{"cuts":[2]}', [], must_not_call=True),
        [target],
        workers=1,
        run_params=run_params,
    )

    assert identity["prompt_sha"] == prompt.sha
    assert recovered == {"run_id": orphan, "status": "done", "ok": 1, "failed": 0}
    assert db.execute(
        "SELECT count(*) FROM passage_origin WHERE run_id = %s", (orphan,)
    ).fetchone()[0] == 2
