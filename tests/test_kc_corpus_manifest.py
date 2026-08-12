"""Behavior tests for immutable KC corpus manifests."""

from __future__ import annotations

import uuid

import pytest
from psycopg.types.json import Jsonb


def _publication(db, label: str):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"source-corpus-{label}-{marker}"
    snapshot_id = f"snapshot-corpus-{label}-{marker}"
    artifact_id = f"artifact-corpus-{label}-{marker}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, %s, 'article')",
        (
            source_id,
            Jsonb({"kind": "url", "value": f"https://example.com/{marker}"}),
            f"Corpus {label}",
        ),
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status) VALUES (%s, %s, %s, 'ok')",
        (snapshot_id, source_id, f"hash-{marker}"),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', %s)",
        (artifact_id, snapshot_id, f"# {label}"),
    )
    publication = current(db, source_id)
    assert publication is not None
    return publication


def _supersede(db, publication, label: str):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    snapshot_id = f"snapshot-corpus-{label}-{marker}"
    artifact_id = f"artifact-corpus-{label}-{marker}"
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status, created_at)"
        " VALUES (%s, %s, %s, 'ok', now() + interval '1 second')",
        (snapshot_id, publication.source_id, f"hash-{marker}"),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, created_at)"
        " VALUES (%s, %s, 'markdown', 'test', %s, now() + interval '1 second')",
        (artifact_id, snapshot_id, f"# {label}"),
    )
    replacement = current(db, publication.source_id)
    assert replacement is not None
    assert replacement.artifact_id == artifact_id
    return replacement


def test_create_is_order_independent_and_preserves_first_origin(db):
    from universe.kc_corpus_manifest import create, read

    publication_b = _publication(db, "b")
    publication_a = _publication(db, "a")

    created = create(
        db,
        [publication_b, publication_a],
        origin={"trigger": "validated-lesson", "lesson_id": "lesson-6"},
    )
    repeated = create(
        db,
        [publication_a, publication_b],
        origin={"trigger": "manual-retry"},
    )

    assert repeated == created
    assert read(db, created["id"]) == created
    assert created["origin"] == {
        "trigger": "validated-lesson",
        "lesson_id": "lesson-6",
    }
    assert created["publications"] == [
        {
            "source_id": publication_a.source_id,
            "artifact_id": publication_a.artifact_id,
        },
        {
            "source_id": publication_b.source_id,
            "artifact_id": publication_b.artifact_id,
        },
    ]
    assert created["id"] == f"kc-corpus-{created['manifest_sha256']}"
    assert len(created["manifest_sha256"]) == 64


def test_create_rejects_an_empty_corpus(db):
    from universe.kc_corpus_manifest import create

    with pytest.raises(ValueError, match="cannot be empty"):
        create(db, [])


def test_create_rejects_more_than_one_publication_for_a_source(db):
    from universe.kc_corpus_manifest import create

    publication = _publication(db, "duplicate")

    with pytest.raises(ValueError, match="one publication per Source"):
        create(db, [publication, publication])


def test_create_rejects_a_publication_that_is_no_longer_current(db):
    from universe.kc_corpus_manifest import create

    stale = _publication(db, "stale")
    _supersede(db, stale, "replacement")

    with pytest.raises(ValueError, match="is not the current publication"):
        create(db, [stale])


def test_a_new_publication_creates_a_new_manifest_without_mutating_the_old(db):
    from universe.kc_corpus_manifest import create, read

    original = _publication(db, "original")
    first = create(db, [original], origin={"attempt": 1})
    replacement = _supersede(db, original, "new-canonical")

    second = create(db, [replacement], origin={"attempt": 2})

    assert second["id"] != first["id"]
    assert read(db, first["id"]) == first
    assert read(db, first["id"])["origin"] == {"attempt": 1}
    assert read(db, second["id"])["publications"] == [
        {
            "source_id": replacement.source_id,
            "artifact_id": replacement.artifact_id,
        }
    ]


def test_read_returns_none_for_an_unknown_manifest(db):
    from universe.kc_corpus_manifest import read

    assert read(db, "kc-corpus-missing") is None
