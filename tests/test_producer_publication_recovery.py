"""Crash recovery at the three model-producer publication boundaries.

The transport is local and deterministic.  These tests exercise PostgreSQL
transactions and lease takeover only; they never call a provider.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from universe import harness, pipeline_lease, producer_publication
from universe.blocks import BLOCKER_VERSION
from universe.recipe_identity import recipe_identity


@dataclass
class StubClient:
    stage: str
    response: str
    calls: list[str]
    must_not_call: bool = False

    def __post_init__(self) -> None:
        identity = recipe_identity(self.stage)
        self.model = identity["model"]
        self.params = identity["model_params"]

    def complete(self, rendered: str):
        if self.must_not_call:
            raise AssertionError("publish-only recovery called the provider")
        self.calls.append(rendered)
        return self.response, {}, 1


def _seed_source(db, tag: str) -> tuple[str, str, str]:
    source_id = f"pubrec-source-{tag}"
    snapshot_id = f"pubrec-snapshot-{tag}"
    artifact_id = f"pubrec-artifact-{tag}"
    passage_id = f"pubrec-passage-{tag}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\":\"test\"}', %s, 'markdown')",
        (source_id, f"Publication recovery {tag}"),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, %s, 'ok')",
        (snapshot_id, source_id, f"hash-{tag}"),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', 'Alpha.\n\nBeta.')",
        (artifact_id, snapshot_id),
    )
    for seq, body in ((1, "Alpha."), (2, "Beta.")):
        db.execute(
            "INSERT INTO block"
            " (id, artifact_id, blocker_version, seq, kind,"
            "  start_char, end_char, body)"
            " VALUES (%s, %s, %s, %s, 'paragraph', %s, %s, %s)",
            (
                f"pubrec-block-{tag}-{seq}",
                artifact_id,
                BLOCKER_VERSION,
                seq,
                0 if seq == 1 else 8,
                6 if seq == 1 else 13,
                body,
            ),
        )
    db.execute(
        "INSERT INTO passage"
        " (id, artifact_id, blocker_version, first_seq, last_seq)"
        " VALUES (%s, %s, %s, 1, 2)",
        (passage_id, artifact_id, BLOCKER_VERSION),
    )
    db.commit()
    return source_id, artifact_id, passage_id


def _case(db, stage: str, tag: str):
    source_id, artifact_id, passage_id = _seed_source(db, tag)
    version = recipe_identity(stage)["prompt_ref"].split("/", 1)[1]
    prompt = harness.load_prompt(stage, version, require_body=False)
    if stage == "passage-cuts":
        target = harness.Target(
            source_id,
            None,
            artifact_id,
            '<block n="1">Alpha.</block>\n\n<block n="2">Beta.</block>',
        )
        response = '{"cuts":[2]}'
        run_params = {
            "body_from": "blocks",
            "blocker_version": BLOCKER_VERSION,
        }

        def published(run_id: str) -> int:
            return db.execute(
                "SELECT count(*) FROM passage_origin WHERE run_id = %s",
                (run_id,),
            ).fetchone()[0]

        expected = 2
    elif stage == "task-generation":
        target = harness.Target(
            source_id,
            None,
            artifact_id,
            "Alpha. Beta.",
            passage_id=passage_id,
            extra_fields={"passage": "Alpha. Beta."},
        )
        response = '{"tasks":[{"task":"Explain alpha.","answer":"Alpha."}]}'
        run_params = {
            "cuts_runs": [f"cuts-{tag}"],
            "triage_runs": [f"triage-{tag}"],
            "skip_runs": [],
        }

        def published(run_id: str) -> int:
            return db.execute(
                "SELECT count(*) FROM task t JOIN run_item i ON i.id = t.run_item_id"
                " WHERE i.run_id = %s",
                (run_id,),
            ).fetchone()[0]

        expected = 1
    else:
        generation_run = f"pubrec-generation-{tag}"
        generation_item = f"{generation_run}-0001"
        parent_task = f"pubrec-parent-{tag}"
        db.execute(
            "INSERT INTO run"
            " (id, stage, model, prompt_ref, prompt_sha, params, status)"
            " VALUES (%s, 'fixture-generation', 'fixture', 'fixture/v1', 'sha', '{}', 'done')",
            (generation_run,),
        )
        db.execute(
            "INSERT INTO run_item"
            " (id, run_id, artifact_id, passage_id, response)"
            " VALUES (%s, %s, %s, %s, '{}')",
            (generation_item, generation_run, artifact_id, passage_id),
        )
        db.execute(
            "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
            " VALUES (%s, %s, %s, 1, 'Compare alpha and beta.', 'Both.')",
            (parent_task, generation_item, passage_id),
        )
        db.commit()
        target = harness.Target(
            source_id,
            None,
            artifact_id,
            "",
            task_id=parent_task,
            extra_fields={"task": "Compare alpha and beta.", "answer": "Both."},
        )
        response = (
            '{"verdict":"composite","parts":['
            '{"task":"Explain alpha.","answer":"Alpha."},'
            '{"task":"Explain beta.","answer":"Beta."}]}'
        )
        run_params = {"gen_runs": [generation_run]}

        def published(run_id: str) -> int:
            return db.execute(
                "SELECT count(*) FROM task t JOIN run_item i ON i.id = t.run_item_id"
                " WHERE i.run_id = %s",
                (run_id,),
            ).fetchone()[0]

        expected = 2
    return source_id, prompt, target, response, run_params, published, expected


def _lease_environment(monkeypatch, lease: pipeline_lease.Lease) -> None:
    monkeypatch.setenv("UNIVERSE_KC_LEASE_SCOPE", lease.scope_key)
    monkeypatch.setenv("UNIVERSE_KC_LEASE_STAGE", lease.stage)
    monkeypatch.setenv("UNIVERSE_KC_LEASE_TOKEN", lease.token)
    monkeypatch.setenv("UNIVERSE_KC_LEASE_OWNER", lease.owner_id)


@pytest.mark.parametrize(
    ("stage", "tag"),
    [
        ("passage-cuts", "cuts"),
        ("task-generation", "generation"),
        ("task-granularity", "granularity"),
    ],
)
def test_expired_owner_recovers_publication_without_another_provider_call(
    db, monkeypatch, stage, tag
):
    source_id, prompt, target, response, run_params, published, expected = _case(
        db, stage, tag
    )
    old = pipeline_lease.acquire(
        db,
        scope_key=f"source:{source_id}",
        stage=stage,
        owner_id=f"old-{tag}",
    )
    assert old is not None
    db.commit()
    _lease_environment(monkeypatch, old)

    real_finalize = producer_publication.finalize

    def crash_before_commit(*_args, **_kwargs):
        raise RuntimeError("simulated death during deterministic publication")

    monkeypatch.setattr(producer_publication, "finalize", crash_before_commit)
    first_calls: list[str] = []
    # Model results and the publishing phase survive, while the derived rows do
    # not. Keep the old lease row to exercise true expiry/takeover.
    real_release = pipeline_lease.release
    monkeypatch.setattr(pipeline_lease, "release", lambda *_args, **_kwargs: False)
    with pytest.raises(RuntimeError, match="simulated death"):
        harness.execute(
            db,
            prompt,
            StubClient(stage, response, first_calls),
            [target],
            workers=1,
            run_params=run_params,
        )
    monkeypatch.setattr(pipeline_lease, "release", real_release)
    monkeypatch.setattr(producer_publication, "finalize", real_finalize)

    orphan = db.execute(
        "SELECT id, status FROM run"
        " WHERE stage = %s AND params#>>'{pipeline_lease,token}' = %s",
        (stage, old.token),
    ).fetchone()
    assert orphan is not None
    assert orphan[1] == "publishing"
    assert published(orphan[0]) == 0
    assert len(first_calls) == 1

    db.execute(
        "UPDATE kc_pipeline_lease SET expires_at = clock_timestamp() - interval '1 second',"
        " heartbeat_at = clock_timestamp() - interval '2 seconds'"
        " WHERE scope_key = %s AND stage = %s AND token = %s",
        (old.scope_key, old.stage, old.token),
    )
    db.commit()
    successor = pipeline_lease.acquire(
        db,
        scope_key=old.scope_key,
        stage=stage,
        owner_id=f"successor-{tag}",
    )
    assert successor is not None and successor.token != old.token
    db.commit()
    _lease_environment(monkeypatch, successor)

    second_calls: list[str] = []
    recovered = harness.execute(
        db,
        prompt,
        StubClient(stage, response, second_calls, must_not_call=True),
        [target],
        workers=1,
        run_params=run_params,
    )

    assert recovered["run_id"] == orphan[0]
    assert recovered["status"] == "done"
    assert second_calls == []
    assert published(orphan[0]) == expected
    assert db.execute(
        "SELECT status FROM run WHERE id = %s", (orphan[0],)
    ).fetchone()[0] == "done"


def test_changed_upstream_manifest_cannot_adopt_a_publishing_run(db, monkeypatch):
    stage = "task-generation"
    source_id, prompt, target, response, run_params, _, _ = _case(
        db, stage, "changed-manifest"
    )
    old = pipeline_lease.acquire(
        db,
        scope_key=f"source:{source_id}",
        stage=stage,
        owner_id="old-changed-manifest",
    )
    assert old is not None
    db.commit()
    _lease_environment(monkeypatch, old)

    real_finalize = producer_publication.finalize
    monkeypatch.setattr(
        producer_publication,
        "finalize",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("crash")),
    )
    with pytest.raises(RuntimeError, match="crash"):
        harness.execute(
            db,
            prompt,
            StubClient(stage, response, []),
            [target],
            workers=1,
            run_params=run_params,
        )
    monkeypatch.setattr(producer_publication, "finalize", real_finalize)

    # The normal exception path released the old owner; a new stage lease may
    # run, but it must not adopt work selected from a different upstream set.
    successor = pipeline_lease.acquire(
        db,
        scope_key=old.scope_key,
        stage=stage,
        owner_id="successor-changed-manifest",
    )
    assert successor is not None
    db.commit()
    _lease_environment(monkeypatch, successor)
    new_calls: list[str] = []
    fresh = harness.execute(
        db,
        prompt,
        StubClient(stage, response, new_calls),
        [target],
        workers=1,
        run_params={**run_params, "triage_runs": ["different-current-triage"]},
    )

    assert len(new_calls) == 1
    assert fresh["status"] == "done"
    assert db.execute(
        "SELECT count(*) FROM run WHERE stage = %s AND status = 'publishing'",
        (stage,),
    ).fetchone()[0] >= 1
