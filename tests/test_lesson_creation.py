"""Vertical deterministic proof for the durable six-stage Lesson Build adapter."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import psycopg
import pytest

from concept_graph_creation.runtime.fixture_model import FixtureModelClient
from universe import lesson_build, lesson_creation, pipeline_lease


FIXTURE_ROOT = Path(__file__).parent / "fixtures/archived_cc_mod6_com/backtracking"
LESSON_ID = "lesson-2026-06-02-backtracking"


def _seed_archived_lesson(db) -> tuple[str, str]:
    ledger = json.loads((FIXTURE_ROOT / "subject_ledger.json").read_text())
    lesson = next(item for item in ledger["lessons"] if item["lesson_id"] == LESSON_ID)
    db.execute("INSERT INTO syllabus (id, title) VALUES ('creation', 'Criação')")
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES ('creation:v0001', 'creation', 1, 'upload')"
    )
    db.execute(
        "INSERT INTO syllabus_lesson"
        " (id, version_id, seq, kind, title, description, subjects)"
        " VALUES (%s, 'creation:v0001', 1, 'Class', %s, %s, %s)",
        (LESSON_ID, lesson["title"], lesson["description"], lesson["related_labels"]),
    )
    reference_ids = []
    for seq, item in enumerate(
        [
            entry
            for entry in ledger["self_studies"]
            if entry["lesson_id"] == LESSON_ID
            and entry["source_body_status"] == "usable_source_body"
        ],
        1,
    ):
        reference_id = str(item["self_study_id"])
        reference_ids.append(reference_id)
        source_id = f"creation-source-{reference_id}"
        snapshot_id = f"creation-snapshot-{reference_id}"
        artifact_id = f"creation-artifact-{reference_id}"
        body = (FIXTURE_ROOT / "source_bodies" / f"{reference_id}.md").read_text()
        content_hash = item["source_body"]["sha256"]
        metadata = item["workbook_metadata"]
        media_type = item["source_body"]["type"]
        db.execute(
            "INSERT INTO source (id, identity, title, media_type)"
            " VALUES (%s, '{}', %s, %s)",
            (source_id, metadata["title"], media_type),
        )
        db.execute(
            "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
            " VALUES (%s, %s, %s, 'ok')",
            (snapshot_id, source_id, content_hash),
        )
        db.execute(
            "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
            " VALUES (%s, %s, 'markdown', 'fixture', %s)",
            (artifact_id, snapshot_id, body),
        )
        db.execute(
            "INSERT INTO syllabus_source_reference"
            " (id, version_id, lesson_id, seq, title, description, url, media_type,"
            " resource_code, source_id)"
            " VALUES (%s, 'creation:v0001', %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                reference_id,
                LESSON_ID,
                seq,
                metadata["title"],
                metadata["description"],
                metadata["url"],
                media_type,
                metadata["resource_code"],
                source_id,
            ),
        )
        db.execute(
            "INSERT INTO syllabus_source_review"
            " (reference_id, is_validated, validated_artifact_id, validated_content_hash)"
            " VALUES (%s, true, %s, %s)",
            (reference_id, artifact_id, content_hash),
        )
    db.commit()
    build = lesson_build.request(
        db,
        syllabus_id="creation",
        version_id="creation:v0001",
        lesson_id=LESSON_ID,
        request_key="deterministic-browser-build",
        reference_ids=reference_ids,
    )
    return build["id"], build["work"][0]["id"]


def _run_fenced(db, monkeypatch, work_id, stage, model_call):
    lease = pipeline_lease.acquire(
        db,
        scope_key=f"lesson-build-work:{work_id}",
        stage=stage,
        owner_id=f"fixture-{stage}",
    )
    assert lease is not None
    db.commit()
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_SCOPE", lease.scope_key)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_STAGE", lease.stage)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_TOKEN", lease.token)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_OWNER", lease.owner_id)
    with pipeline_lease.supervise(db, stage=stage):
        return lesson_creation.run_stage(
            db,
            work_id=work_id,
            stage=stage,
            model_call=model_call,
        )


def test_selected_publications_run_through_all_six_checkpoint_families(
    db, monkeypatch, tmp_path
):
    build_id, work_id = _seed_archived_lesson(db)
    fixture = FixtureModelClient.from_file(FIXTURE_ROOT / "fixture-model.json")
    for stage in (
        "candidate-concepts",
        "lesson-reconciliation",
        "dependency-deferral",
        "lesson-segmentation",
    ):
        _run_fenced(db, monkeypatch, work_id, stage, fixture)
    fixture.assert_exhausted()

    segments_body = db.execute(
        "SELECT body FROM lesson_build_checkpoint"
        " WHERE build_id = %s AND path = %s ORDER BY created_at DESC LIMIT 1",
        (build_id, f"lessons/{LESSON_ID}/lesson_segments.json"),
    ).fetchone()[0]
    segments = json.loads(segments_body)["segments"]
    knowledge_fixture_path = tmp_path / "knowledge-fixture.json"
    knowledge_fixture_path.write_text(
        json.dumps(
            {
                "schema_version": "creation_fixture_model.v1",
                "responses": [
                    *[
                        {
                            "stage_name": "knowledge_type_classification",
                            "input_subset": {
                                "knowledge_type_classification_input.json": {
                                    "segment": {"segment_id": segment["segment_id"]}
                                }
                            },
                            "response": {
                                "classifications": [
                                    {
                                        "concept_id": concept_id,
                                        "knowledge_type": "conceptual",
                                        "rationale": "A compreensão conceitual organiza este trecho.",
                                        "confidence": 0.9,
                                    }
                                    for concept_id in segment["concept_ids"]
                                ]
                            },
                        }
                        for segment in segments
                    ],
                    {
                        "stage_name": "knowledge_type_quality_audit",
                        "input_subset": {},
                        "response": {
                            "scores": {
                                "taxonomy_fit": 3,
                                "teaching_mode_alignment": 3,
                                "segment_consistency": 3,
                                "factual_boundary": 3,
                                "applied_boundary": 3,
                            },
                            "reliability": "reliable",
                            "flags": [],
                            "findings": [],
                            "repair_plan": [],
                        },
                    },
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    knowledge_fixture = FixtureModelClient.from_file(knowledge_fixture_path)
    _run_fenced(db, monkeypatch, work_id, "knowledge-types", knowledge_fixture)
    knowledge_fixture.assert_exhausted()
    _run_fenced(db, monkeypatch, work_id, "lesson-fragment", lambda **_: "{}")

    build = lesson_build.read(db, build_id)
    assert lesson_creation.completed_stages(db, build_id) == (
        "candidate-concepts",
        "lesson-reconciliation",
        "dependency-deferral",
        "lesson-segmentation",
        "knowledge-types",
        "lesson-fragment",
    )
    assert {item["family"] for item in build["checkpoints"]} == {
        "candidate_concepts",
        "lesson_concepts",
        "lesson_segments",
        "knowledge_types",
        "lesson_fragment",
        "raw_artifacts",
    }
    final = next(
        item
        for item in build["checkpoints"]
        if item["path"] == "final_graph/runtime_graph.json"
    )
    _, final_body = lesson_build.checkpoint_body(db, build_id, final["id"])
    graph = json.loads(final_body)
    assert len(graph["concepts"]) == 10
    provider_calls = []

    class PaidClient:
        def _append_usage_event(self, _event):
            pass

        def call(self, **_kwargs):
            provider_calls.append("called")
            self._append_usage_event(
                {
                    "stage_name": "fixture-paid-call",
                    "route_alias": "Pro",
                    "requested_model": "requested/model",
                    "response_model": "response/model",
                    "response_provider": "provider-a",
                    "generation_id": "generation-1",
                    "outcome": "success",
                    "elapsed_seconds": 0.125,
                    "usage": {"cost": 0.01, "total_tokens": 42},
                }
            )
            return "{}"

    monkeypatch.setattr(
        lesson_creation.PipelineModelClient,
        "from_env",
        lambda **_kwargs: PaidClient(),
    )
    loaded = lesson_creation._load_build(db, work_id)
    database_url = pipeline_lease.connection_dsn(db)
    usage_lease = pipeline_lease.acquire(
        db,
        scope_key=f"lesson-build-work:{work_id}",
        stage="candidate-concepts",
        owner_id="usage-ledger-test",
    )
    assert usage_lease is not None
    db.commit()
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_SCOPE", usage_lease.scope_key)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_STAGE", usage_lease.stage)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_TOKEN", usage_lease.token)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_OWNER", usage_lease.owner_id)
    with pipeline_lease.supervise(db, stage=usage_lease.stage):
        paid_call = lesson_creation._live_model_call(
            database_url,
            loaded,
            "candidate-concepts",
            usage_lease.token,
        )
        paid_call(route=SimpleNamespace(alias="Pro", model="requested/model"))
    with_usage = lesson_build.read(db, build_id)
    assert with_usage["usage"] == {
        "calls": 1,
        "cost_usd": 0.01,
        "total_tokens": 42,
    }
    assert with_usage["attempts"][0]["requested_model"] == "requested/model"
    assert with_usage["attempts"][0]["response_model"] == "response/model"
    assert with_usage["attempts"][0]["provider"] == "provider-a"

    stale_lease = pipeline_lease.acquire(
        db,
        scope_key=f"lesson-build-work:{work_id}",
        stage="candidate-concepts",
        owner_id="stale-usage-test",
    )
    assert stale_lease is not None
    db.commit()
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_SCOPE", stale_lease.scope_key)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_STAGE", stale_lease.stage)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_TOKEN", stale_lease.token)
    monkeypatch.setenv("UNIVERSE_PIPELINE_LEASE_OWNER", stale_lease.owner_id)
    successor = None
    with pipeline_lease.supervise(db, stage=stale_lease.stage):
        stale_call = lesson_creation._live_model_call(
            database_url,
            loaded,
            "candidate-concepts",
            stale_lease.token,
        )
        with psycopg.connect(database_url) as takeover:
            takeover.execute(
                "UPDATE pipeline_lease SET heartbeat_at = clock_timestamp()"
                " - interval '2 seconds', expires_at = clock_timestamp()"
                " - interval '1 second' WHERE scope_key = %s AND stage = %s"
                " AND token = %s",
                (stale_lease.scope_key, stale_lease.stage, stale_lease.token),
            )
            successor = pipeline_lease.acquire(
                takeover,
                scope_key=stale_lease.scope_key,
                stage=stale_lease.stage,
                owner_id="successor-usage-test",
            )
            assert successor is not None
        with pytest.raises(pipeline_lease.LeaseLost):
            stale_call(route=SimpleNamespace(alias="Pro", model="requested/model"))
        with pytest.raises(pipeline_lease.LeaseLost):
            lesson_creation._record_usage_event(
                database_url,
                loaded,
                "candidate-concepts",
                stale_lease,
                {"outcome": "success", "usage": {}},
            )
    assert provider_calls == ["called"]
    assert db.execute(
        "SELECT count(*) FROM run_item WHERE lesson_build_id = %s",
        (build_id,),
    ).fetchone()[0] == 1
    with psycopg.connect(database_url) as cleanup:
        assert pipeline_lease.release(cleanup, successor) is True
