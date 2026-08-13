"""A model child owns and fences its lease without any scheduler heartbeat."""

import sys

import psycopg
import pytest

from universe import harness, kc_pipeline, pipeline_lease, pipeline_worker

from test_kc_pipeline_orchestration import seed_source


def _lease_environment(monkeypatch, lease: pipeline_lease.Lease) -> None:
    monkeypatch.setenv("UNIVERSE_KC_LEASE_SCOPE", lease.scope_key)
    monkeypatch.setenv("UNIVERSE_KC_LEASE_STAGE", lease.stage)
    monkeypatch.setenv("UNIVERSE_KC_LEASE_TOKEN", lease.token)
    monkeypatch.setenv("UNIVERSE_KC_LEASE_OWNER", lease.owner_id)


def _expire(conn, lease: pipeline_lease.Lease) -> None:
    conn.execute(
        "UPDATE kc_pipeline_lease SET"
        " heartbeat_at = clock_timestamp() - interval '10 minutes',"
        " expires_at = clock_timestamp() - interval '1 second'"
        " WHERE scope_key = %s AND stage = %s AND token = %s",
        (lease.scope_key, lease.stage, lease.token),
    )


def test_model_child_renews_its_own_token_without_a_parent_heartbeat(
    db, monkeypatch
):
    lease = pipeline_lease.acquire(
        db,
        scope_key="source:child-heartbeat",
        stage="passage-cuts",
        owner_id="scheduler-that-is-now-gone",
        ttl_seconds=30,
    )
    assert lease is not None
    db.commit()
    _lease_environment(monkeypatch, lease)

    with harness.supervise_lease(
        db, "passage-cuts", heartbeat_interval=3600
    ) as child:
        db.execute(
            "UPDATE kc_pipeline_lease SET"
            " heartbeat_at = clock_timestamp(),"
            " expires_at = clock_timestamp() + interval '1 second'"
            " WHERE scope_key = %s AND stage = %s AND token = %s",
            (lease.scope_key, lease.stage, lease.token),
        )
        shortened_expiry = db.execute(
            "SELECT expires_at FROM kc_pipeline_lease"
            " WHERE scope_key = %s AND stage = %s",
            (lease.scope_key, lease.stage),
        ).fetchone()[0]
        db.commit()

        renewed = child.heartbeat_now(ttl_seconds=120)

        assert renewed.token == lease.token
        assert renewed.expires_at > shortened_expiry


def test_takeover_stops_provider_work_and_fences_run_item_persistence(
    db, test_database_url, monkeypatch
):
    source_id, artifact_id = seed_source(db, "child_fence", blocks=False)
    lease = pipeline_lease.acquire(
        db,
        scope_key=f"source:{source_id}",
        stage="passage-cuts",
        owner_id="dead-parent",
        ttl_seconds=30,
    )
    assert lease is not None
    db.commit()
    _lease_environment(monkeypatch, lease)

    calls = []

    class TakeoverDuringCall:
        model = "fake/model"
        params = {}

        def complete(self, _rendered):
            calls.append("provider-started")
            with psycopg.connect(test_database_url) as successor_conn:
                _expire(successor_conn, lease)
                successor = pipeline_lease.acquire(
                    successor_conn,
                    scope_key=lease.scope_key,
                    stage=lease.stage,
                    owner_id="recovery-scheduler",
                    ttl_seconds=300,
                )
                assert successor is not None
                assert successor.token != lease.token
            return "untrusted result", {}, 1

    prompt = harness.load_prompt("passage-cuts", "v001")
    target = harness.Target(
        source_id,
        None,
        artifact_id,
        "The source body.",
    )

    with pytest.raises(pipeline_lease.LeaseLost, match="lease ownership lost"):
        harness.execute(db, prompt, TakeoverDuringCall(), [target], workers=1)

    run = db.execute(
        "SELECT id, status FROM run"
        " WHERE params#>>'{pipeline_lease,token}' = %s",
        (lease.token,),
    ).fetchone()
    assert run is not None
    assert run[1] == "running"
    assert db.execute(
        "SELECT count(*) FROM run_item WHERE run_id = %s", (run[0],)
    ).fetchone()[0] == 0
    assert calls == ["provider-started"]


def test_production_spawn_wraps_every_stage_and_privately_pins_the_database(
    db, monkeypatch
):
    lease = pipeline_lease.acquire(
        db,
        scope_key="source:wrapped-worker",
        stage="blocks",
        owner_id="scheduler",
    )
    assert lease is not None
    db.commit()
    captured = {}

    def popen(argv, *, cwd, env):
        captured.update(argv=argv, cwd=cwd, env=env)
        return object()

    monkeypatch.setattr(kc_pipeline.subprocess, "Popen", popen)
    secret_dsn = "host=database-a dbname=universe user=worker password=private"

    kc_pipeline._spawn(
        [sys.executable, "-m", "universe.blocks", "artifact-1"],
        lease,
        database_url=secret_dsn,
    )

    assert captured["argv"][:3] == [
        sys.executable,
        "-m",
        "universe.pipeline_worker",
    ]
    assert captured["argv"][3:6] == ["blocks", "universe.blocks", "--"]
    assert secret_dsn not in captured["argv"]
    assert captured["env"]["DATABASE_URL"] == secret_dsn


def test_pipeline_worker_is_the_authoritative_same_process_owner(
    db, monkeypatch
):
    lease = pipeline_lease.acquire(
        db,
        scope_key="source:worker-owner",
        stage="blocks",
        owner_id="scheduler",
    )
    assert lease is not None
    db.commit()
    _lease_environment(monkeypatch, lease)
    seen = []

    class KeepOpen:
        def __enter__(self):
            return db

        def __exit__(self, *_args):
            return False

    def execute_module(module_name, argv):
        held = pipeline_lease.current_supervisor(required=True)
        seen.append((module_name, argv, held.lease.token))

    monkeypatch.setattr(pipeline_worker, "connect", lambda: KeepOpen())
    monkeypatch.setattr(pipeline_worker, "execute_module", execute_module)

    pipeline_worker.main(["blocks", "universe.blocks", "--", "artifact-1"])

    assert seen == [("universe.blocks", ["artifact-1"], lease.token)]
    assert pipeline_lease.active(
        db, scope_key=lease.scope_key, stage=lease.stage
    ) is None


def test_fenced_process_escalates_from_terminate_to_kill():
    calls = []

    class IgnoresTerminate:
        alive = True

        def poll(self):
            return None if self.alive else -9

        def terminate(self):
            calls.append("terminate")

        def wait(self, timeout):
            calls.append(("wait", timeout))
            if self.alive:
                raise TimeoutError

        def kill(self):
            calls.append("kill")
            self.alive = False

    process = IgnoresTerminate()
    kc_pipeline._terminate_process(process, timeout=0.01)

    assert calls == [
        "terminate",
        ("wait", 0.01),
        "kill",
        ("wait", 0.01),
    ]
