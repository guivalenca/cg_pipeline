"""Pipeline scope is defined by Source Publications and explicit corpus pins."""

from __future__ import annotations

import uuid
from copy import deepcopy

from psycopg.types.json import Jsonb

from universe.recipe_identity import recipe_identity


def _publication(db, label: str):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"scope-source-{label}-{marker}"
    snapshot_id = f"scope-snapshot-{label}-{marker}"
    artifact_id = f"scope-artifact-{label}-{marker}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, %s, 'article')",
        (
            source_id,
            Jsonb({"kind": "url", "value": f"https://example.com/{marker}"}),
            f"Scope {label}",
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
    assert publication.artifact_id == artifact_id
    return publication


def _supersede(db, publication, label: str):
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    snapshot_id = f"scope-snapshot-{label}-{marker}"
    artifact_id = f"scope-artifact-{label}-{marker}"
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


def _run(db, label: str, artifact_ids: list[str], *, live_recipe: bool = True):
    marker = uuid.uuid4().hex[:10]
    run_id = f"scope-run-{label}-{marker}"
    recipe = recipe_identity("passage-cuts")
    params = deepcopy(recipe["model_params"])
    params.update(recipe["input_contract"])
    prompt_sha = recipe["prompt_sha"] if live_recipe else "0" * 64
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, 'passage-cuts', %s, %s, %s, %s, 'done')",
        (
            run_id,
            recipe["model"],
            recipe["prompt_ref"],
            prompt_sha,
            Jsonb(params),
        ),
    )
    for index, artifact_id in enumerate(artifact_ids, 1):
        db.execute(
            "INSERT INTO run_item (id, run_id, artifact_id, response)"
            " VALUES (%s, %s, %s, '{}')",
            (f"{run_id}:i{index}", run_id, artifact_id),
        )
    return run_id


def _strict_cleanup_publication(db):
    """Return (intermediate artifact id, canonical Publication)."""
    from universe.source_publication import current

    marker = uuid.uuid4().hex[:10]
    source_id = f"scope-strict-source-{marker}"
    snapshot_id = f"scope-strict-snapshot-{marker}"
    intermediate_id = f"scope-strict-intermediate-{marker}"
    canonical_id = f"scope-strict-canonical-{marker}"
    acquisition_id = f"scope-strict-acquisition-{marker}"
    cuts_run_id = f"scope-strict-cuts-{marker}"
    cleanup_id = f"scope-strict-cleanup-{marker}"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, 'Strict scope', 'article')",
        (
            source_id,
            Jsonb({"kind": "url", "value": f"https://example.com/{marker}"}),
        ),
    )
    db.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, content_hash, status) VALUES (%s, %s, %s, 'ok')",
        (snapshot_id, source_id, f"hash-{marker}"),
    )
    db.execute(
        "INSERT INTO artifact"
        " (id, snapshot_id, kind, tool, body, metadata, created_at)"
        " VALUES (%s, %s, 'markdown', 'firecrawl', '# Intermediate', '{}', now()),"
        "        (%s, %s, 'markdown', 'passage-cleanup', '# Canonical',"
        "         %s, now() + interval '1 second')",
        (
            intermediate_id,
            snapshot_id,
            canonical_id,
            snapshot_id,
            Jsonb(
                {
                    "source_markdown_artifact_id": intermediate_id,
                    "cleanup_id": cleanup_id,
                }
            ),
        ),
    )
    db.execute(
        "INSERT INTO acquisition_job"
        " (id, source_id, status, provider, artifact_id, diagnostics, finished_at)"
        " VALUES (%s, %s, 'succeeded', 'test', %s, %s, now())",
        (
            acquisition_id,
            source_id,
            intermediate_id,
            Jsonb({"pipeline_requires_cleanup": True}),
        ),
    )
    db.execute(
        "INSERT INTO run"
        " (id, stage, model, prompt_ref, prompt_sha, status, finished_at)"
        " VALUES (%s, 'passage-cuts', 'test', 'test/v1', 'test', 'done', now())",
        (cuts_run_id,),
    )
    db.execute(
        "INSERT INTO passage_cleanup"
        " (id, cuts_run_id, model, triage_prompt_ref, refine_prompt_ref,"
        "  status, finished_at)"
        " VALUES (%s, %s, 'test', 'test/triage', 'test/refine', 'done', now())",
        (cleanup_id, cuts_run_id),
    )
    db.execute(
        "INSERT INTO source_cleanup_job"
        " (id, acquisition_job_id, source_id, source_artifact_id, status,"
        "  cuts_run_id, cleanup_id, canonical_artifact_id, finished_at)"
        " VALUES (%s, %s, %s, %s, 'succeeded', %s, %s, %s, now())",
        (
            f"scope-strict-job-{marker}",
            acquisition_id,
            source_id,
            intermediate_id,
            cuts_run_id,
            cleanup_id,
            canonical_id,
        ),
    )
    publication = current(db, source_id)
    assert publication is not None
    assert publication.artifact_id == canonical_id
    return intermediate_id, publication


def test_default_scope_rejects_cleanup_intermediate_and_selects_publication(db):
    from universe.pipeline_scope import eligible_run_ids

    intermediate_id, publication = _strict_cleanup_publication(db)
    intermediate_run = _run(db, "intermediate", [intermediate_id])
    publication_run = _run(db, "canonical", [publication.artifact_id])

    eligible = eligible_run_ids(db, "passage-cuts")

    assert intermediate_run not in eligible
    assert publication_run in eligible


def test_current_scope_moves_forward_but_explicit_pins_keep_history(db):
    from universe.kc_corpus_manifest import create
    from universe.pipeline_scope import eligible_run_ids

    historical = _publication(db, "historical")
    manifest = create(db, [historical], origin={"test": "historical-pin"})
    historical_run = _run(db, "historical", [historical.artifact_id])
    current = _supersede(db, historical, "current")
    current_run = _run(db, "current", [current.artifact_id])

    default = eligible_run_ids(db, "passage-cuts")

    assert historical_run not in default
    assert current_run in default
    assert eligible_run_ids(
        db, "passage-cuts", artifact_id=historical.artifact_id
    ) == [historical_run]
    assert eligible_run_ids(
        db, "passage-cuts", corpus_manifest_id=manifest["id"]
    ) == [historical_run]


def test_artifact_scope_rejects_a_run_mixed_with_another_source(db):
    from universe.pipeline_scope import eligible_run_ids

    target = _publication(db, "pure-target")
    external = _publication(db, "mixed-external")
    pure_run = _run(db, "pure", [target.artifact_id])
    mixed_run = _run(db, "mixed", [target.artifact_id, external.artifact_id])

    eligible = eligible_run_ids(
        db, "passage-cuts", artifact_id=target.artifact_id
    )

    assert eligible == [pure_run]
    assert mixed_run not in eligible


def test_corpus_manifest_scope_excludes_external_source_and_mixed_run(db):
    from universe.kc_corpus_manifest import create
    from universe.pipeline_scope import (
        corpus_publication_artifacts,
        eligible_run_ids,
    )

    member = _publication(db, "manifest-member")
    external = _publication(db, "manifest-external")
    manifest = create(db, [member], origin={"test": "lesson-corpus"})
    member_run = _run(db, "member", [member.artifact_id])
    external_run = _run(db, "external", [external.artifact_id])
    mixed_run = _run(db, "manifest-mixed", [
        member.artifact_id,
        external.artifact_id,
    ])

    publications = corpus_publication_artifacts(db, manifest["id"])
    eligible = eligible_run_ids(
        db, "passage-cuts", corpus_manifest_id=manifest["id"]
    )

    assert publications == {member.source_id: member.artifact_id}
    assert eligible == [member_run]
    assert external_run not in eligible
    assert mixed_run not in eligible


def test_publication_scope_still_requires_the_current_recipe(db):
    from universe.pipeline_scope import eligible_run_ids

    publication = _publication(db, "recipe")
    stale_recipe_run = _run(
        db, "stale-recipe", [publication.artifact_id], live_recipe=False
    )
    live_recipe_run = _run(db, "live-recipe", [publication.artifact_id])

    eligible = eligible_run_ids(
        db, "passage-cuts", artifact_id=publication.artifact_id
    )

    assert eligible == [live_recipe_run]
    assert stale_recipe_run not in eligible
