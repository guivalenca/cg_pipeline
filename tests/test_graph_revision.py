"""Behavioral tests for whole-Lesson review and immutable Graph Revisions."""

from __future__ import annotations

import hashlib
import json

import psycopg
import pytest

from universe import graph_revision, lesson_build, pipeline_lease


def _canonical(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _fragment(
    graph_id: str,
    lesson_id: str,
    build_label: str,
    *,
    idea: str = "Ideia compartilhada",
    extra_idea: str | None = None,
) -> dict:
    concept_id = f"concept-{lesson_id}-{build_label}"
    segment_id = f"segment-{lesson_id}-{build_label}"
    concepts = [
        {
            "concept_id": concept_id,
            "display_code": "COM-001",
            "label": idea,
            "knowledge_type": "conceptual",
            "description": idea,
            "coverage_criteria": [f"Explicar {idea.lower()}"],
            "common_misconceptions": [],
            "dependencies": {"blocking": [], "hard": [], "soft": []},
        }
    ]
    if extra_idea:
        concepts.append(
            {
                **concepts[0],
                "concept_id": f"concept-{lesson_id}-{build_label}-extra",
                "display_code": "COM-002",
                "label": extra_idea,
                "description": extra_idea,
                "coverage_criteria": [f"Explicar {extra_idea.lower()}"],
            }
        )
    return {
        "artifact_type": "runtime_graph",
        "schema_version": "runtime_graph.v0",
        "generated_at": "2026-09-02T12:00:00+00:00",
        "subject": {
            "course_id": "revision-course",
            "module_id": "revision:v0001",
            "pipeline_subject_id": "COM",
            "title": "Computação",
            "language": "pt-BR",
            "professors": [],
        },
        "concepts": concepts,
        "lessons": [
            {
                "lesson_id": lesson_id,
                "display_code": lesson_id,
                "date": "2026-09-02",
                "title": f"Aula {lesson_id}",
                "description": "",
                "segments": [
                    {
                        "segment_id": segment_id,
                        "display_code": f"{lesson_id}-S01",
                        "label": idea,
                        "instructional_role": "teach",
                        "concept_ids": [item["concept_id"] for item in concepts],
                        "teaching_notes": "",
                        "self_study_resource_ids": [],
                        "self_study_resource_refs": [],
                    }
                ],
            }
        ],
        "self_study_resources": [],
    }


def _seed_subject(db, namespace: str) -> tuple[str, str, str]:
    syllabus_id = f"{namespace}-syllabus"
    version_id = f"{syllabus_id}:v0001"
    graph_id = f"graph-{namespace}"
    db.execute(
        "INSERT INTO syllabus (id, title) VALUES (%s, %s)",
        (syllabus_id, f"Syllabus {namespace}"),
    )
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES (%s, %s, 1, 'upload')",
        (version_id, syllabus_id),
    )
    db.execute(
        "INSERT INTO syllabus_subject"
        " (syllabus_id, lesson_subject_code, graph_id) VALUES (%s, 'COM', %s)",
        (syllabus_id, graph_id),
    )
    db.commit()
    return syllabus_id, version_id, graph_id


def _seed_finished_build(
    db,
    *,
    version_id: str,
    graph_id: str,
    lesson_id: str,
    build_label: str,
    lesson_seq: int,
    idea: str = "Ideia compartilhada",
    extra_idea: str | None = None,
    concept_id_override: str | None = None,
) -> tuple[str, dict]:
    build_id = f"build-{version_id}-{lesson_id}-{build_label}"
    fragment = _fragment(
        graph_id,
        lesson_id,
        build_label,
        idea=idea,
        extra_idea=extra_idea,
    )
    if concept_id_override:
        original_concept_id = fragment["concepts"][0]["concept_id"]
        fragment["concepts"][0]["concept_id"] = concept_id_override
        segment_concept_ids = fragment["lessons"][0]["segments"][0]["concept_ids"]
        fragment["lessons"][0]["segments"][0]["concept_ids"] = [
            concept_id_override if item == original_concept_id else item
            for item in segment_concept_ids
        ]
    body = _canonical(fragment)
    db.execute(
        "INSERT INTO syllabus_lesson"
        " (id, version_id, seq, kind, title, subject)"
        " VALUES (%s, %s, %s, 'Class', %s, 'COM')"
        " ON CONFLICT (version_id, id) DO NOTHING",
        (lesson_id, version_id, lesson_seq, f"Aula {lesson_id}"),
    )
    db.execute(
        "INSERT INTO lesson_build"
        " (id, version_id, lesson_id, request_key, requested_by, manifest,"
        " manifest_sha256, lineage_id, status, is_active, finished_at)"
        " VALUES (%s, %s, %s, %s, 'founder', %s, %s, %s,"
        " 'succeeded', false, now())",
        (
            build_id,
            version_id,
            lesson_id,
            f"request-{build_id}",
            json.dumps(
                {
                    "schema_version": "lesson_build_manifest.v1",
                    "lineage_id": f"lineage-{build_id}",
                    "lesson": {
                        "id": lesson_id,
                        "subject_graph_id": graph_id,
                        "lesson_subject_code": "COM",
                        "week_order": lesson_seq,
                        "activity_order": lesson_seq,
                        "seq": lesson_seq,
                    },
                }
            ),
            hashlib.sha256(build_id.encode()).hexdigest(),
            f"lineage-{build_id}",
        ),
    )
    db.execute(
        "INSERT INTO lesson_build_checkpoint"
        " (id, build_id, stage, family, path, body, content_sha256,"
        " stage_fingerprint, is_stage_result)"
        " VALUES (%s, %s, 'lesson-fragment', 'lesson_fragment',"
        " 'final_graph/runtime_graph.json', %s, %s, %s, true)",
        (
            f"checkpoint-{build_id}",
            build_id,
            body,
            hashlib.sha256(body.encode()).hexdigest(),
            hashlib.sha256(f"fingerprint-{build_id}".encode()).hexdigest(),
        ),
    )
    db.commit()
    return build_id, fragment


def test_accepting_lessons_automatically_assembles_immutable_graph_history(db):
    _, version_id, graph_id = _seed_subject(db, "history")
    first_build, first_fragment = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="lesson-one",
        build_label="v1",
        lesson_seq=1,
    )

    first = graph_revision.accept(db, first_build, actor="founder")
    second_build, second_fragment = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="lesson-two",
        build_label="v1",
        lesson_seq=2,
    )
    second = graph_revision.accept(db, second_build, actor="founder")

    assert first["revision"]["number"] == 1
    assert second["revision"]["number"] == 2
    assert first["revision"]["graph_id"] == second["revision"]["graph_id"] == graph_id
    assert [lesson["lesson_id"] for lesson in second["graph"]["lessons"]] == [
        "lesson-one",
        "lesson-two",
    ]
    assert {item["concept_id"] for item in second["graph"]["concepts"]} == {
        first_fragment["concepts"][0]["concept_id"],
        second_fragment["concepts"][0]["concept_id"],
    }

    historical_path, historical_body = graph_revision.revision_body(
        db, first["revision"]["id"]
    )
    current_path, current_body = graph_revision.current_body(db, graph_id)

    assert historical_path == current_path == "graph.json"
    assert json.loads(historical_body)["lessons"] == first_fragment["lessons"]
    assert len(json.loads(current_body)["lessons"]) == 2
    assert historical_body == first["body"]
    assert historical_body != current_body
    assert first["revision"]["content_sha256"] == hashlib.sha256(
        historical_body.encode()
    ).hexdigest()
    assert second["revision"]["content_sha256"] == hashlib.sha256(
        current_body.encode()
    ).hexdigest()
    assert graph_revision.read_graph(db, graph_id)["current_revision"]["number"] == 2
    with pytest.raises(Exception, match="immutable"):
        db.execute(
            "UPDATE graph_revision SET graph_body = '{}' WHERE id = %s",
            (first["revision"]["id"],),
        )
    db.rollback()


def test_replacement_review_preserves_current_until_atomic_acceptance(db):
    _, version_id, graph_id = _seed_subject(db, "replacement")
    sibling_build, sibling_fragment = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="sibling",
        build_label="v1",
        lesson_seq=2,
    )
    graph_revision.accept(db, sibling_build, actor="founder")
    original_build, original_fragment = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="replace-me",
        build_label="v1",
        lesson_seq=1,
    )
    original = graph_revision.accept(db, original_build, actor="founder")
    _, before_body = graph_revision.current_body(db, graph_id)

    active_build, _ = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="replace-me",
        build_label="active",
        lesson_seq=1,
    )
    db.execute(
        "UPDATE lesson_build SET status = 'running', is_active = true,"
        " finished_at = NULL WHERE id = %s",
        (active_build,),
    )
    db.commit()
    with pytest.raises(graph_revision.WholeLessonReviewError, match="finished"):
        graph_revision.accept(db, active_build, actor="stale-worker")
    assert graph_revision.current_body(db, graph_id)[1] == before_body
    active_detail = lesson_build.read(db, active_build)
    assert active_detail["subject_graph"]["current_revision"]["id"] == (
        original["revision"]["id"]
    )
    db.execute(
        "UPDATE lesson_build SET status = 'failed', is_active = false,"
        " failure_code = 'stage_failed' WHERE id = %s",
        (active_build,),
    )
    db.commit()

    rejected_build, _ = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="replace-me",
        build_label="rejected",
        lesson_seq=1,
    )
    rejected = graph_revision.reject(db, rejected_build, actor="founder", note="Refazer")
    assert rejected["decision"] == "rejected"
    assert graph_revision.current_body(db, graph_id)[1] == before_body

    failed_build, _ = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="replace-me",
        build_label="failed",
        lesson_seq=1,
    )
    db.execute(
        "UPDATE lesson_build SET status = 'failed', failure_code = 'stage_failed'"
        " WHERE id = %s",
        (failed_build,),
    )
    db.commit()
    with pytest.raises(graph_revision.WholeLessonReviewError, match="finished"):
        graph_revision.accept(db, failed_build, actor="founder")
    assert graph_revision.current_body(db, graph_id)[1] == before_body

    replacement_build, replacement_fragment = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="replace-me",
        build_label="v2",
        lesson_seq=1,
        extra_idea="Ideia adicional",
    )
    replacement = graph_revision.accept(db, replacement_build, actor="founder")

    assert replacement["revision"]["number"] == original["revision"]["number"] + 1
    assert [lesson["lesson_id"] for lesson in replacement["graph"]["lessons"]] == [
        "replace-me",
        "sibling",
    ]
    replacement_concept_ids = {
        concept["concept_id"] for concept in replacement["graph"]["concepts"]
    }
    assert sibling_fragment["concepts"][0]["concept_id"] in replacement_concept_ids
    assert original_fragment["concepts"][0]["concept_id"] not in replacement_concept_ids
    assert replacement_fragment["concepts"][0]["concept_id"] in replacement_concept_ids
    assert original_fragment["lessons"][0]["lesson_id"] == (
        replacement_fragment["lessons"][0]["lesson_id"]
    )
    assert original_fragment["concepts"][0]["concept_id"] != (
        replacement_fragment["concepts"][0]["concept_id"]
    )
    assert original_fragment["lessons"][0]["segments"][0]["segment_id"] != (
        replacement_fragment["lessons"][0]["segments"][0]["segment_id"]
    )
    before_sibling = next(
        concept
        for concept in json.loads(before_body)["concepts"]
        if concept["concept_id"] == sibling_fragment["concepts"][0]["concept_id"]
    )
    after_sibling = next(
        concept
        for concept in replacement["graph"]["concepts"]
        if concept["concept_id"] == sibling_fragment["concepts"][0]["concept_id"]
    )
    assert after_sibling == before_sibling


def test_final_projection_keeps_repeated_ideas_lesson_local():
    first = _fragment("graph-local", "lesson-one", "build-a")
    second = _fragment("graph-local", "lesson-two", "build-b")

    assembled = graph_revision.assemble(
        "graph-local",
        [("lesson-one", first), ("lesson-two", second)],
    )

    assert [item["label"] for item in assembled["concepts"]] == [
        "Ideia compartilhada",
        "Ideia compartilhada",
    ]
    assert len({item["concept_id"] for item in assembled["concepts"]}) == 2
    repeated_body = _canonical(
        graph_revision.assemble(
            "graph-local",
            [("lesson-one", first), ("lesson-two", second)],
        )
    )
    assembled_body = _canonical(assembled)
    assert repeated_body.encode("utf-8") == assembled_body.encode("utf-8")
    assert hashlib.sha256(repeated_body.encode()).hexdigest() == hashlib.sha256(
        assembled_body.encode()
    ).hexdigest()


def test_failed_acceptance_rolls_back_accepted_lesson_ref_and_current_pointer(db):
    _, version_id, graph_id = _seed_subject(db, "atomic-failure")
    first_build, first_fragment = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="lesson-one",
        build_label="v1",
        lesson_seq=1,
    )
    graph_revision.accept(db, first_build, actor="founder")
    _, before_body = graph_revision.current_body(db, graph_id)
    conflicting_build, conflicting_fragment = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="lesson-two",
        build_label="v1",
        lesson_seq=2,
        concept_id_override=first_fragment["concepts"][0]["concept_id"],
    )
    assert conflicting_fragment["concepts"][0]["concept_id"] == (
        first_fragment["concepts"][0]["concept_id"]
    )

    with pytest.raises(ValueError, match="duplicate Concept IDs"):
        with psycopg.connect(pipeline_lease.connection_dsn(db)) as review_conn:
            graph_revision.accept(review_conn, conflicting_build, actor="founder")

    assert graph_revision.current_body(db, graph_id)[1] == before_body
    assert db.execute(
        "SELECT count(*) FROM accepted_lesson_ref WHERE build_id = %s",
        (conflicting_build,),
    ).fetchone()[0] == 0
    assert graph_revision.review_for_build(db, conflicting_build) is None


def test_current_graph_is_offered_before_a_build_exists_in_a_new_version(db):
    syllabus_id, version_id, graph_id = _seed_subject(db, "new-version")
    build_id, _ = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="stable-lesson",
        build_label="v1",
        lesson_seq=1,
    )
    accepted = graph_revision.accept(db, build_id, actor="founder")
    next_version_id = f"{syllabus_id}:v0002"
    db.execute(
        "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
        " VALUES (%s, %s, 2, 'upload')",
        (next_version_id, syllabus_id),
    )
    db.execute(
        "INSERT INTO syllabus_lesson"
        " (id, version_id, seq, kind, title, subject)"
        " VALUES ('stable-lesson', %s, 1, 'Class', 'Aula estável', 'COM')",
        (next_version_id,),
    )
    db.commit()

    offered = lesson_build.offer(
        db,
        syllabus_id=syllabus_id,
        version_id=next_version_id,
        lesson_id="stable-lesson",
    )

    assert offered["latest_build"] is None
    assert offered["subject_graph"]["current_revision"]["id"] == (
        accepted["revision"]["id"]
    )


def test_rejecting_a_finished_build_does_not_require_graph_projection(db):
    _, version_id, graph_id = _seed_subject(db, "reject-only")
    build_id, _ = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="lesson-reject-only",
        build_label="v1",
        lesson_seq=1,
    )
    db.execute(
        "UPDATE lesson_build SET manifest = jsonb_set("
        " manifest, '{lesson,subject_graph_id}', 'null'::jsonb) WHERE id = %s",
        (build_id,),
    )
    db.commit()

    review = graph_revision.reject(db, build_id, actor="founder")

    assert review["decision"] == "rejected"
    assert db.execute(
        "SELECT count(*) FROM graph_revision WHERE created_by_build_id = %s",
        (build_id,),
    ).fetchone()[0] == 0
