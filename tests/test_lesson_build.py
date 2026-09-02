import psycopg
import pytest

from universe import (
    lesson_build,
    lesson_build_plan,
    lesson_build_stage,
    lesson_creation,
    pipeline_lease,
)
from universe import lesson_build_worker


def test_pilot_registers_the_six_lesson_creation_stages_in_order():
    assert [stage.name for stage in lesson_build_plan.registered_stages()] == [
        "candidate-concepts",
        "lesson-reconciliation",
        "dependency-deferral",
        "lesson-segmentation",
        "knowledge-types",
        "lesson-fragment",
    ]
    assert lesson_build_plan.next_stage(completed=()).name == "candidate-concepts"


def test_worker_completes_claimed_work_when_no_stage_is_registered(db, monkeypatch):
    monkeypatch.setattr(lesson_build_plan, "_STAGES", ())
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
        "INSERT INTO syllabus_source_reference"
        " (id, version_id, lesson_id, seq, title, media_type, source_id)"
        " VALUES ('request-reference-copy', 'request-pilot:v0001',"
        " 'request-lesson', 2, 'Fonte compartilhada', 'article', 'request-source')"
    )
    db.execute(
        "INSERT INTO syllabus_source_review"
        " (reference_id, is_validated, validated_artifact_id, validated_content_hash)"
        " VALUES ('request-reference', true, 'request-artifact', 'request-hash')"
    )
    db.execute(
        "INSERT INTO syllabus_source_review"
        " (reference_id, is_validated, validated_artifact_id, validated_content_hash)"
        " VALUES ('request-reference-copy', true, 'request-artifact', 'request-hash')"
    )
    db.commit()

    result = lesson_build.request(
        db,
        syllabus_id="request-pilot",
        version_id="request-pilot:v0001",
        lesson_id="request-lesson",
        request_key="operator-click-1",
        reference_ids=["request-reference", "request-reference-copy"],
    )

    assert result["status"] == "queued"
    assert result["manifest"]["lesson"] == {
        "id": "request-lesson",
        "title": "Aula",
        "kind": "Class",
        "description": None,
        "subjects": [],
        "lesson_subject_code": None,
        "subject_graph_id": None,
        "week": None,
        "seq": 1,
        "date": None,
        "fields": {},
        "activity_uuid": None,
        "folder_uuid": None,
        "week_order": None,
        "activity_order": None,
    }
    assert result["manifest"]["references"][0]["reference_id"] == (
        "request-reference"
    )
    assert [item["reference_id"] for item in result["manifest"]["references"]] == [
        "request-reference",
        "request-reference-copy",
    ]
    publication = result["manifest"]["references"][0]["publication"]
    assert {key: publication[key] for key in (
        "source_id", "snapshot_id", "artifact_id", "content_hash"
    )} == {
        "source_id": "request-source", "snapshot_id": "request-snapshot",
        "artifact_id": "request-artifact", "content_hash": "request-hash",
    }
    assert publication["created_at"]
    assert len(result["manifest_sha256"]) == 64
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

    frozen = lesson_build.read(db, result["id"])
    assert frozen["manifest_sha256"] == result["manifest_sha256"]
    assert frozen["manifest"]["references"][0]["publication"]["artifact_id"] == (
        "request-artifact"
    )

    try:
        lesson_build.request(
            db,
            syllabus_id="request-pilot",
            version_id="request-pilot:v0001",
            lesson_id="request-lesson",
            request_key="operator-click-2",
            reference_ids=["request-reference", "request-reference-copy"],
        )
    except lesson_build.LessonBuildNotReady as exc:
        assert exc.code == "references_not_validated"
    else:
        raise AssertionError("a changed Source Publication must be revalidated")


def test_request_freezes_only_the_operator_selected_references(db):
    db.execute("INSERT INTO syllabus (id, title) VALUES ('selected', 'Selecionado')")
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES ('selected:v0001', 'selected', 1, 'upload')"
    )
    db.execute(
        "INSERT INTO syllabus_lesson (id, version_id, seq, kind, title)"
        " VALUES ('selected-lesson', 'selected:v0001', 1, 'Class', 'Aula')"
    )
    for seq in (1, 2):
        db.execute(
            "INSERT INTO source (id, identity, title, media_type)"
            " VALUES (%s, '{}', %s, 'article')",
            (f"selected-source-{seq}", f"Fonte {seq}"),
        )
        db.execute(
            "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
            " VALUES (%s, %s, %s, 'ok')",
            (f"selected-snapshot-{seq}", f"selected-source-{seq}", f"hash-{seq}"),
        )
        db.execute(
            "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
            " VALUES (%s, %s, 'markdown', 'test', %s)",
            (f"selected-artifact-{seq}", f"selected-snapshot-{seq}", f"# Fonte {seq}"),
        )
        db.execute(
            "INSERT INTO syllabus_source_reference"
            " (id, version_id, lesson_id, seq, title, media_type, source_id)"
            " VALUES (%s, 'selected:v0001', 'selected-lesson', %s, %s,"
            " 'article', %s)",
            (f"selected-reference-{seq}", seq, f"Fonte {seq}", f"selected-source-{seq}"),
        )
        db.execute(
            "INSERT INTO syllabus_source_review"
            " (reference_id, is_validated, validated_artifact_id, validated_content_hash)"
            " VALUES (%s, true, %s, %s)",
            (f"selected-reference-{seq}", f"selected-artifact-{seq}", f"hash-{seq}"),
        )
    db.commit()

    result = lesson_build.request(
        db,
        syllabus_id="selected",
        version_id="selected:v0001",
        lesson_id="selected-lesson",
        reference_ids=["selected-reference-2"],
        request_key="selected-click",
    )

    assert [row["reference_id"] for row in result["manifest"]["references"]] == [
        "selected-reference-2"
    ]
    assert [row["source_id"] for row in result["work"]] == ["selected-source-2"]
    with pytest.raises(lesson_build.LessonBuildNotReady) as raised:
        lesson_build.request(
            db,
            syllabus_id="selected",
            version_id="selected:v0001",
            lesson_id="selected-lesson",
            reference_ids=["selected-reference-2"],
            request_key="selected-click-while-active",
        )
    assert raised.value.code == "build_already_active"
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES ('selected:v0002', 'selected', 2, 'upload')"
    )
    db.execute(
        "INSERT INTO syllabus_lesson (id, version_id, seq, kind, title)"
        " VALUES ('selected-lesson', 'selected:v0002', 1, 'Class', 'Aula revisada')"
    )
    db.execute(
        "INSERT INTO syllabus_source_reference"
        " (id, version_id, lesson_id, seq, title, media_type, source_id)"
        " VALUES ('selected-reference-v2', 'selected:v0002', 'selected-lesson',"
        " 1, 'Fonte 2', 'article', 'selected-source-2')"
    )
    db.execute(
        "INSERT INTO syllabus_source_review"
        " (reference_id, is_validated, validated_artifact_id, validated_content_hash)"
        " VALUES ('selected-reference-v2', true, 'selected-artifact-2', 'hash-2')"
    )
    db.commit()
    with pytest.raises(lesson_build.LessonBuildNotReady) as cross_version:
        lesson_build.request(
            db,
            syllabus_id="selected",
            version_id="selected:v0002",
            lesson_id="selected-lesson",
            reference_ids=["selected-reference-v2"],
            request_key="selected-click-new-version",
        )
    assert cross_version.value.code == "build_already_active"


def test_stage_checkpoint_is_fenced_and_prevents_repeating_completed_work(
    db, monkeypatch
):
    build_id, work_id = db.execute(
        "SELECT build.id, work.id FROM lesson_build build"
        " JOIN lesson_build_work work ON work.build_id = build.id"
        " WHERE build.request_key = 'selected-click'"
    ).fetchone()
    calls = []

    def execute(stage, run_dir, model_call, prompt_path, router):
        calls.append(stage)
        assert prompt_path.name == "self_study_extraction.md"
        frozen_route = router.resolve("Pro")
        assert frozen_route.model == "deepseek/deepseek-v4-pro"
        assert frozen_route.provider == "openrouter"
        (run_dir / "self_study_extraction_summary.json").write_text(
            '{"summary":{"extracted_self_study_count":1}}', encoding="utf-8"
        )

    monkeypatch.setattr(lesson_creation, "_execute_stage", execute)
    lease = pipeline_lease.acquire(
        db,
        scope_key=f"lesson-build-work:{work_id}",
        stage="candidate-concepts",
        owner_id="checkpoint-test",
    )
    assert lease is not None
    db.commit()
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_SCOPE", lease.scope_key)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_STAGE", lease.stage)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_TOKEN", lease.token)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_OWNER", lease.owner_id)
    with pipeline_lease.supervise(db, stage=lease.stage):
        first = lesson_creation.run_stage(
            db, work_id=work_id, stage="candidate-concepts", model_call=lambda **_: "{}"
        )
    second = lesson_creation.run_stage(
        db, work_id=work_id, stage="candidate-concepts", model_call=lambda **_: "{}"
    )

    assert first["reused"] is False
    assert second == {
        "stage": "candidate-concepts",
        "checkpoint_id": first["checkpoint_id"],
        "reused": True,
    }
    assert calls == ["candidate-concepts"]
    assert lesson_creation.completed_stages(db, build_id) == ("candidate-concepts",)
    monkeypatch.setattr(
        lesson_creation.lesson_build_identity,
        "path_sha256",
        lambda _path: "0" * 64,
    )
    with pytest.raises(RuntimeError, match="frozen prompt hash"):
        lesson_creation.run_stage(
            db, work_id=work_id, stage="candidate-concepts", model_call=lambda **_: "{}"
        )
    with pytest.raises(Exception, match="immutable"):
        db.execute(
            "UPDATE lesson_build_checkpoint SET body = '{}' WHERE id = %s",
            (first["checkpoint_id"],),
        )
    db.rollback()
    stage_fingerprint = db.execute(
        "SELECT stage_fingerprint FROM lesson_build_checkpoint WHERE id = %s",
        (first["checkpoint_id"],),
    ).fetchone()[0]
    db.execute(
        "INSERT INTO lesson_build_checkpoint"
        " (id, build_id, stage, family, path, body, content_sha256,"
        " stage_fingerprint, is_stage_result)"
        " VALUES ('malformed-checkpoint', %s, 'candidate-concepts',"
        " 'raw_artifacts', 'malformed.json', '{}', %s, %s, false)",
        (build_id, "0" * 64, stage_fingerprint),
    )
    db.commit()
    with pytest.raises(RuntimeError, match="content hash"):
        lesson_creation.completed_stages(db, build_id)
    db.execute(
        "UPDATE lesson_build_work SET status = 'succeeded', stage = NULL,"
        " failure_code = NULL, claimed_at = NULL, claim_token = NULL,"
        " lease_expires_at = NULL WHERE build_id <> %s",
        (build_id,),
    )
    db.execute(
        "UPDATE lesson_build SET is_active = false WHERE id <> %s",
        (build_id,),
    )
    db.execute(
        "UPDATE lesson_build_work SET status = 'queued', failure_code = NULL,"
        " available_at = now() WHERE build_id = %s",
        (build_id,),
    )
    db.execute(
        "UPDATE lesson_build SET status = 'queued', is_active = true WHERE id = %s",
        (build_id,),
    )
    db.commit()
    failed = lesson_build_worker.process_next(db, spawn=lambda _argv, _lease: None)
    assert failed["action"] == "attention"
    assert failed["status"] == "failed"
    assert db.execute(
        "SELECT status, failure_code, is_active FROM lesson_build WHERE id = %s",
        (build_id,),
    ).fetchone() == ("failed", "checkpoint_invalid", False)


def test_resume_reuses_lineage_while_regenerate_starts_fresh_work(db):
    build_id = db.execute(
        "SELECT id FROM lesson_build WHERE request_key = 'selected-click'"
    ).fetchone()[0]
    db.execute(
        "UPDATE lesson_build SET status = 'failed', is_active = false,"
        " failure_code = 'stage_failed', failure_message = 'falha' WHERE id = %s",
        (build_id,),
    )
    db.execute(
        "UPDATE lesson_build_work SET status = 'failed', failure_code = 'stage_failed'"
        " WHERE build_id = %s",
        (build_id,),
    )
    db.commit()

    resumed = lesson_build.resume(db, build_id)
    assert resumed["id"] == build_id
    assert resumed["status"] == "queued"
    assert resumed["checkpoints"]
    db.execute(
        "UPDATE lesson_build SET status = 'succeeded', is_active = false,"
        " finished_at = now() WHERE id = %s",
        (build_id,),
    )
    db.commit()
    regenerated = lesson_build.regenerate(
        db, build_id, request_key="selected-regenerate"
    )

    assert regenerated["id"] != build_id
    assert regenerated["lineage_id"] != resumed["lineage_id"]
    assert regenerated["previous_build_id"] == build_id
    assert regenerated["checkpoints"] == []


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
    db.execute(
        "UPDATE pipeline_lease SET heartbeat_at = clock_timestamp()"
        " - interval '2 seconds', expires_at = clock_timestamp()"
        " - interval '1 second' WHERE scope_key = %s AND stage = %s AND token = %s",
        (lease.scope_key, lease.stage, lease.token),
    )
    db.commit()
    db.execute(
        "UPDATE lesson_build_work SET available_at = now() WHERE id = 'work-launch'"
    )
    db.commit()
    recovered = lesson_build_worker.process_next(db, spawn=spawn)
    assert recovered["action"] == "launched"
    assert recovered["stage"] == "draft"
    assert len(launched) == 2
    assert launched[-1][1].token != lease.token
    assert pipeline_lease.release(db, lease) is False
    db.commit()
    pipeline_lease.release(db, launched[-1][1])
    db.commit()


def test_scheduler_claim_expiry_is_exclusive_and_fences_the_stale_token(db):
    db.execute(
        "UPDATE lesson_build_work SET status = 'succeeded', stage = NULL,"
        " failure_code = NULL, claimed_at = NULL, claim_token = NULL,"
        " lease_expires_at = NULL WHERE status IN ('queued', 'running')"
    )
    db.execute("INSERT INTO syllabus (id, title) VALUES ('claim', 'Claim')")
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES ('claim:v0001', 'claim', 1, 'upload')"
    )
    db.execute(
        "INSERT INTO syllabus_lesson (id, version_id, seq, kind, title)"
        " VALUES ('lesson-claim', 'claim:v0001', 1, 'Class', 'Aula')"
    )
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES ('source-claim', '{}', 'Fonte', 'article')"
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES ('snapshot-claim', 'source-claim', 'hash-claim', 'ok')"
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES ('artifact-claim', 'snapshot-claim', 'markdown', 'test', '# Fonte')"
    )
    db.execute(
        "INSERT INTO lesson_build"
        " (id, version_id, lesson_id, request_key, requested_by)"
        " VALUES ('build-claim', 'claim:v0001', 'lesson-claim', 'request', 'founder')"
    )
    db.execute(
        "INSERT INTO lesson_build_work"
        " (id, build_id, seq, source_id, snapshot_id, artifact_id, content_hash)"
        " VALUES ('work-claim', 'build-claim', 1, 'source-claim',"
        " 'snapshot-claim', 'artifact-claim', 'hash-claim')"
    )
    db.commit()

    first = lesson_build_worker._claim_next(db)
    assert first is not None
    with psycopg.connect(pipeline_lease.connection_dsn(db)) as contender:
        assert lesson_build_worker._claim_next(contender) is None
    db.execute(
        "UPDATE lesson_build_work SET claimed_at = clock_timestamp()"
        " - interval '2 seconds', lease_expires_at = clock_timestamp()"
        " - interval '1 second' WHERE id = 'work-claim'"
    )
    db.commit()
    successor = lesson_build_worker._claim_next(db)
    assert successor is not None
    assert successor["claim_token"] != first["claim_token"]
    assert successor["claim_count"] == 2

    assert lesson_build_worker._finish(
        db,
        first,
        status="queued",
        stage=None,
        diagnostics={"owner": "stale"},
    ) is False
    assert db.execute(
        "SELECT status, claim_token FROM lesson_build_work WHERE id = 'work-claim'"
    ).fetchone() == ("running", successor["claim_token"])
    assert lesson_build_worker._finish(
        db,
        successor,
        status="queued",
        stage=None,
        diagnostics={"owner": "successor"},
    ) is True


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
