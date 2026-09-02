import psycopg

from universe import lesson_build, lesson_build_plan, lesson_build_stage, pipeline_lease
from universe import lesson_build_worker


def test_pilot_registers_no_lesson_build_stages():
    assert lesson_build_plan.registered_stages() == ()
    assert lesson_build_plan.next_stage(completed=()) is None


def test_worker_completes_claimed_work_when_no_stage_is_registered(db):
    db.execute(
        "INSERT INTO syllabus (id, title) VALUES ('pilot', 'Pilot')"
    )
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES ('pilot:v0001', 'pilot', 1, 'upload')"
    )
    db.execute(
        "INSERT INTO syllabus_lesson (id, version_id, seq, kind, title)"
        " VALUES ('lesson-1', 'pilot:v0001', 1, 'Class', 'Aula')"
    )
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES ('source-1', '{}', 'Fonte', 'article')"
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status)"
        " VALUES ('snapshot-1', 'source-1', 'sha-source-1', 'ok')"
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES ('artifact-1', 'snapshot-1', 'markdown', 'test', '# Fonte')"
    )
    db.execute(
        "INSERT INTO lesson_build"
        " (id, version_id, lesson_id, request_key, requested_by)"
        " VALUES ('build-1', 'pilot:v0001', 'lesson-1', 'request-1', 'founder')"
    )
    db.execute(
        "INSERT INTO lesson_build_work"
        " (id, build_id, seq, source_id, snapshot_id, artifact_id, content_hash)"
        " VALUES ('work-1', 'build-1', 1, 'source-1', 'snapshot-1',"
        " 'artifact-1', 'sha-source-1')"
    )
    db.commit()

    result = lesson_build_worker.process_next(db)

    assert result == {
        "action": "completed",
        "build_id": "build-1",
        "work_id": "work-1",
        "status": "succeeded",
        "stage": None,
        "claim_count": 1,
    }
    assert db.execute(
        "SELECT status, stage, claim_token FROM lesson_build_work"
        " WHERE id = 'work-1'"
    ).fetchone() == ("succeeded", None, None)


def test_request_pins_validated_source_publications_as_lesson_work(db):
    db.execute(
        "INSERT INTO syllabus (id, title) VALUES ('request-pilot', 'Request Pilot')"
    )
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES ('request-pilot:v0001', 'request-pilot', 1, 'upload')"
    )
    db.execute(
        "INSERT INTO syllabus_lesson (id, version_id, seq, kind, title)"
        " VALUES ('request-lesson', 'request-pilot:v0001', 1, 'Class', 'Aula')"
    )
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES ('request-source', '{}', 'Fonte', 'article')"
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status)"
        " VALUES ('request-snapshot', 'request-source', 'request-hash', 'ok')"
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES ('request-artifact', 'request-snapshot', 'markdown',"
        " 'legacy-import', '# Fonte')"
    )
    db.execute(
        "INSERT INTO syllabus_source_reference"
        " (id, version_id, lesson_id, seq, title, media_type, source_id)"
        " VALUES ('request-reference', 'request-pilot:v0001',"
        " 'request-lesson', 1, 'Fonte', 'article', 'request-source')"
    )
    db.execute(
        "INSERT INTO syllabus_source_review"
        " (reference_id, is_validated, validated_artifact_id, validated_content_hash)"
        " VALUES ('request-reference', true, 'request-artifact', 'request-hash')"
    )
    db.commit()

    result = lesson_build.request(
        db,
        syllabus_id="request-pilot",
        version_id="request-pilot:v0001",
        lesson_id="request-lesson",
        request_key="operator-click-1",
    )

    assert result["status"] == "queued"
    assert result["work"] == [
        {
            "id": result["work"][0]["id"],
            "seq": 1,
            "source_id": "request-source",
            "snapshot_id": "request-snapshot",
            "artifact_id": "request-artifact",
            "content_hash": "request-hash",
            "status": "queued",
            "stage": None,
        }
    ]

    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES ('zz-request-snapshot', 'request-source', 'new-request-hash', 'ok')"
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES ('zz-request-artifact', 'zz-request-snapshot', 'markdown',"
        " 'legacy-import', '# Fonte nova')"
    )
    db.commit()

    try:
        lesson_build.request(
            db,
            syllabus_id="request-pilot",
            version_id="request-pilot:v0001",
            lesson_id="request-lesson",
            request_key="operator-click-2",
        )
    except lesson_build.LessonBuildNotReady as exc:
        assert exc.code == "references_not_validated"
    else:
        raise AssertionError("a changed Source Publication must be revalidated")


def test_worker_launches_and_observes_a_registered_stage_under_a_fenced_lease(
    db, monkeypatch
):
    db.execute(
        "UPDATE lesson_build_work SET status = 'succeeded', stage = NULL,"
        " failure_code = NULL, claimed_at = NULL, claim_token = NULL,"
        " lease_expires_at = NULL WHERE status IN ('queued', 'running')"
    )
    db.execute("INSERT INTO syllabus (id, title) VALUES ('launch', 'Launch')")
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES ('launch:v0001', 'launch', 1, 'upload')"
    )
    db.execute(
        "INSERT INTO syllabus_lesson (id, version_id, seq, kind, title)"
        " VALUES ('lesson-launch', 'launch:v0001', 1, 'Class', 'Aula')"
    )
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES ('source-launch', '{}', 'Fonte', 'article')"
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES ('snapshot-launch', 'source-launch', 'hash-launch', 'ok')"
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES ('artifact-launch', 'snapshot-launch', 'markdown', 'test', '# Fonte')"
    )
    db.execute(
        "INSERT INTO lesson_build"
        " (id, version_id, lesson_id, request_key, requested_by)"
        " VALUES ('build-launch', 'launch:v0001', 'lesson-launch', 'request', 'founder')"
    )
    db.execute(
        "INSERT INTO lesson_build_work"
        " (id, build_id, seq, source_id, snapshot_id, artifact_id, content_hash)"
        " VALUES ('work-launch', 'build-launch', 1, 'source-launch',"
        " 'snapshot-launch', 'artifact-launch', 'hash-launch')"
    )
    db.commit()
    monkeypatch.setattr(
        lesson_build_plan,
        "_STAGES",
        (lesson_build_plan.StagePlan("draft", "universe.future_stage"),),
    )
    launched = []

    class Process:
        pid = 1234

    def spawn(argv, lease):
        launched.append((argv, lease))
        return Process()

    first = lesson_build_worker.process_next(db, spawn=spawn)
    db.execute(
        "UPDATE lesson_build_work SET available_at = now() WHERE id = 'work-launch'"
    )
    db.commit()
    second = lesson_build_worker.process_next(db, spawn=spawn)

    assert first["action"] == "launched"
    assert first["stage"] == "draft"
    assert second["action"] == "observed"
    assert len(launched) == 1
    argv, lease = launched[0]
    assert argv[-5:] == [
        "work-launch",
        "universe.future_stage",
        "source-launch",
        "artifact-launch",
        "hash-launch",
    ]
    assert lease.scope_key == "lesson-build-work:work-launch"
    assert pipeline_lease.active(
        db, scope_key=lease.scope_key, stage="draft"
    ).token == lease.token
    assert db.execute(
        "SELECT status, stage, last_launched_stage FROM lesson_build_work"
        " WHERE id = 'work-launch'"
    ).fetchone() == ("running", "draft", "draft")
    pipeline_lease.release(db, lease)
    db.commit()


def test_stage_worker_records_completion_through_the_inherited_fence(db, monkeypatch):
    db.execute("INSERT INTO syllabus (id, title) VALUES ('complete', 'Complete')")
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES ('complete:v0001', 'complete', 1, 'upload')"
    )
    db.execute(
        "INSERT INTO syllabus_lesson (id, version_id, seq, kind, title)"
        " VALUES ('lesson-complete', 'complete:v0001', 1, 'Class', 'Aula')"
    )
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES ('source-complete', '{}', 'Fonte', 'article')"
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES ('snapshot-complete', 'source-complete', 'hash-complete', 'ok')"
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES ('artifact-complete', 'snapshot-complete', 'markdown', 'test', '# Fonte')"
    )
    db.execute(
        "INSERT INTO lesson_build"
        " (id, version_id, lesson_id, request_key, requested_by)"
        " VALUES ('build-complete', 'complete:v0001', 'lesson-complete',"
        " 'request', 'founder')"
    )
    db.execute(
        "INSERT INTO lesson_build_work"
        " (id, build_id, seq, source_id, snapshot_id, artifact_id, content_hash,"
        " status, stage, last_launched_stage, diagnostics)"
        " VALUES ('work-complete', 'build-complete', 1, 'source-complete',"
        " 'snapshot-complete', 'artifact-complete', 'hash-complete', 'running',"
        " 'draft', 'draft', '{\"completed_stages\": []}')"
    )
    lease = pipeline_lease.acquire(
        db,
        scope_key="lesson-build-work:work-complete",
        stage="draft",
        owner_id="test-stage-worker",
    )
    assert lease is not None
    db.commit()
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_SCOPE", lease.scope_key)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_STAGE", lease.stage)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_TOKEN", lease.token)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_OWNER", lease.owner_id)
    executed = []
    monkeypatch.setattr(
        lesson_build_stage,
        "execute_module",
        lambda module, argv: executed.append((module, argv)),
    )
    dsn = pipeline_lease.connection_dsn(db)
    monkeypatch.setattr(
        lesson_build_stage,
        "connect",
        lambda: psycopg.connect(dsn),
    )

    with pipeline_lease.supervise(db, stage="draft"):
        lesson_build_stage.main(
            [
                "work-complete",
                "universe.future_stage",
                "source-complete",
                "artifact-complete",
                "hash-complete",
            ]
        )

    assert executed == [
        (
            "universe.future_stage",
            ["source-complete", "artifact-complete", "hash-complete"],
        )
    ]
    assert db.execute(
        "SELECT status, stage, failure_code, diagnostics->'completed_stages'"
        " FROM lesson_build_work WHERE id = 'work-complete'"
    ).fetchone() == ("queued", None, None, ["draft"])
