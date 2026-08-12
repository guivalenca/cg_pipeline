"""Explicit corpus orchestration never derives participants implicitly."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest

from universe import kc_corpus_manifest, kc_pipeline, kc_progress
from universe.source_publication import current as current_publication

from test_kc_pipeline_orchestration import (
    opt,
    seed_complete_single_task_source,
    seed_source,
)


def _tag(label: str) -> str:
    return f"corpus_{label}_{uuid.uuid4().hex[:8]}"


def _manifest(db, *source_ids: str) -> dict:
    publications = [current_publication(db, source_id) for source_id in source_ids]
    assert all(publication is not None for publication in publications)
    return kc_corpus_manifest.create(
        db,
        publications,
        origin={"test": "explicit-corpus-target"},
    )


def _supersede(db, source_id: str, label: str) -> str:
    marker = uuid.uuid4().hex[:10]
    snapshot_id = f"kcpipe-corpus-snapshot-{label}-{marker}"
    artifact_id = f"kcpipe-corpus-artifact-{label}-{marker}"
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, %s, 'ok', now() + interval '1 second')",
        (snapshot_id, source_id, f"hash-{marker}"),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, created_at)"
        " VALUES (%s, %s, 'markdown', 'test', '# New publication',"
        " now() + interval '1 second')",
        (artifact_id, snapshot_id),
    )
    db.commit()
    publication = current_publication(db, source_id)
    assert publication is not None
    assert publication.artifact_id == artifact_id
    return artifact_id


def test_corpus_waits_for_every_pinned_publication_to_finish_locally(db):
    complete = seed_complete_single_task_source(db, _tag("complete"))
    incomplete_source, _ = seed_source(db, _tag("incomplete"))
    manifest = _manifest(db, complete["source_id"], incomplete_source)
    target = kc_pipeline.CorpusManifestTarget(manifest["id"])

    progress = kc_progress.corpus_progress(db, manifest["id"])
    step = kc_pipeline.next_step(db, target)
    local_step = kc_pipeline.next_step(db, complete["source_id"])

    assert tuple(progress["stages"]) == kc_pipeline.SHARED_STAGES
    assert progress["ready"] is False
    assert progress["statements_from"] == []
    assert [
        publication["source_id"]
        for publication in progress["publications"]
        if not publication["local_complete"]
    ] == [incomplete_source]
    assert step["stage"] == "task-embedding"
    assert step["runnable"] is False
    assert incomplete_source in step["reason"]
    assert local_step["stage"] is None


def test_manifest_pin_uses_historical_member_and_excludes_external_source(db):
    member = seed_complete_single_task_source(db, _tag("member"))
    external = seed_complete_single_task_source(db, _tag("external"))
    manifest = _manifest(db, member["source_id"])
    _supersede(db, member["source_id"], "member")
    target = kc_pipeline.CorpusManifestTarget(manifest["id"])

    progress = kc_progress.corpus_progress(db, manifest["id"])
    step = kc_pipeline.next_step(db, target)

    assert progress["ready"] is True
    assert progress["task_ids"] == [member["task_id"]]
    assert progress["statements_from"] == [member["statement"]]
    assert external["task_id"] not in progress["task_ids"]
    assert external["statement"] not in progress["statements_from"]
    assert step["stage"] == "task-embedding"
    assert step["runnable"] is True
    assert opt(step["argv"], "--statements-from") == member["statement"]


def test_local_and_corpus_snapshots_expose_disjoint_stage_sets(db):
    complete = seed_complete_single_task_source(db, _tag("snapshots"))
    manifest = _manifest(db, complete["source_id"])

    local = kc_pipeline.read_snapshot(db, complete["source_id"])
    corpus = kc_pipeline.read_snapshot(
        db, kc_pipeline.CorpusManifestTarget(manifest["id"])
    )

    assert tuple(local["stages"]) == kc_pipeline.LOCAL_STAGES
    assert local["next_stage"] is None
    assert tuple(corpus["stages"]) == kc_pipeline.SHARED_STAGES
    assert corpus["corpus"]["id"] == manifest["id"]
    assert corpus["next_stage"] == "task-embedding"


def test_local_snapshot_exposes_stated_unitary_kc_with_source_evidence(db):
    tag = _tag("unitary")
    complete = seed_complete_single_task_source(db, tag)

    snapshot = kc_pipeline.read_snapshot(db, complete["source_id"])

    assert snapshot["grouping_id"] is None
    assert snapshot["relationships"] == []
    assert len(snapshot["components"]) == 1
    component = snapshot["components"][0]
    assert component["id"] == complete["task_id"]
    assert component["kind"] == "singleton"
    assert component["canonical"] == {
        "verdict": "stated",
        "statement": f"Statement {tag}",
    }
    assert component["members"] == [
        {
            "task_id": complete["task_id"],
            "source_id": complete["source_id"],
            "task": "Q raw",
            "answer": "A",
            "statement": f"Statement {tag}",
        }
    ]


@dataclass
class _FakeProcess:
    pid: int = 4242


def test_corpus_advance_claims_manifest_specific_scope(db):
    complete = seed_complete_single_task_source(db, _tag("lease"))
    manifest = _manifest(db, complete["source_id"])
    target = kc_pipeline.CorpusManifestTarget(manifest["id"])
    launched = []

    def spawn(argv, lease):
        launched.append((argv, lease))
        return _FakeProcess()

    result = kc_pipeline.advance(db, target, spawn=spawn)

    assert result["stage"] == "task-embedding"
    assert len(launched) == 1
    assert launched[0][1].scope_key == f"corpus:{manifest['id']}"


def test_local_advance_never_falls_through_to_shared_work(db):
    complete = seed_complete_single_task_source(db, _tag("local-only"))
    launched = []

    with pytest.raises(kc_pipeline.StepNotRunnable, match="local stage"):
        kc_pipeline.advance(
            db,
            complete["source_id"],
            spawn=lambda argv, lease: launched.append((argv, lease)),
        )

    assert launched == []
