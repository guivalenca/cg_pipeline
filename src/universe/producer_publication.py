"""Atomic, restartable publication boundary for model producers.

Provider results first reach ``publishing`` only after every target has one
durable run item.  Their deterministic representation and terminal run status
then commit together.  A successor stage lease can adopt that exact phase only
when today's rendered target manifest, recipe, upstream references, and current
Markdown artifact still match byte for byte.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from typing import Any

import psycopg

from universe import pipeline_lease


PRODUCER_STAGES = frozenset(
    {"passage-cuts", "task-generation", "task-granularity"}
)
TARGET_MANIFEST_VERSION = 1


class PublicationNotReady(RuntimeError):
    """A producer run cannot safely cross the publication boundary."""


def is_producer(stage: str) -> bool:
    return stage in PRODUCER_STAGES


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def target_manifest(targets: Sequence, rendered: Sequence[str]) -> dict:
    """Fingerprint the exact ordered inputs whose provider calls are expected."""
    if len(targets) != len(rendered):
        raise ValueError("targets and rendered prompts must have equal length")
    entries = [
        {
            "index": index,
            "artifact_id": target.artifact_id,
            "passage_id": target.passage_id,
            "task_id": target.task_id,
            "input_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        for index, (target, text) in enumerate(zip(targets, rendered), 1)
    ]
    return {
        "version": TARGET_MANIFEST_VERSION,
        "count": len(entries),
        "sha256": hashlib.sha256(_canonical(entries)).hexdigest(),
        "targets": entries,
    }


def _valid_manifest(manifest: object) -> bool:
    if not isinstance(manifest, dict) or set(manifest) != {
        "version",
        "count",
        "sha256",
        "targets",
    }:
        return False
    targets = manifest.get("targets")
    if (
        manifest.get("version") != TARGET_MANIFEST_VERSION
        or not isinstance(targets, list)
        or manifest.get("count") != len(targets)
        or manifest.get("sha256")
        != hashlib.sha256(_canonical(targets)).hexdigest()
    ):
        return False
    for index, target in enumerate(targets, 1):
        if not isinstance(target, dict) or set(target) != {
            "index",
            "artifact_id",
            "passage_id",
            "task_id",
            "input_sha256",
        }:
            return False
        if (
            target["index"] != index
            or not isinstance(target["artifact_id"], str)
            or not target["artifact_id"]
            or target["passage_id"] is not None
            and not isinstance(target["passage_id"], str)
            or target["task_id"] is not None
            and not isinstance(target["task_id"], str)
            or not isinstance(target["input_sha256"], str)
            or len(target["input_sha256"]) != 64
        ):
            return False
    return True


def _parseable(stage: str, item: dict) -> bool:
    if item["error"] is not None:
        return True
    if stage == "passage-cuts":
        from universe.cuts import parse_cuts

        try:
            parse_cuts(item["response"])
        except (TypeError, ValueError):
            return False
        return True
    if stage == "task-generation":
        from universe.taskgen import tasks_of

        return isinstance(tasks_of(item), list)
    if stage == "task-granularity":
        from universe.task_granularity import granularity_of

        return isinstance(granularity_of(item), dict)
    return False


def _complete_items(
    conn: psycopg.Connection,
    *,
    run_id: str,
    stage: str,
    manifest: dict,
) -> tuple[int, int] | None:
    """Return transport ok/failed counts iff every exact target is durable."""
    if not _valid_manifest(manifest):
        return None
    rows = conn.execute(
        "SELECT id, artifact_id, passage_id, task_id, response, error"
        " FROM run_item WHERE run_id = %s ORDER BY id",
        (run_id,),
    ).fetchall()
    expected = manifest["targets"]
    if len(rows) != len(expected):
        return None
    ok = failed = 0
    for target, row in zip(expected, rows):
        item_id, artifact_id, passage_id, task_id, response, error = row
        if (
            item_id != f"{run_id}-{target['index']:04d}"
            or artifact_id != target["artifact_id"]
            or passage_id != target["passage_id"]
            or task_id != target["task_id"]
        ):
            return None
        item = {"response": response, "error": error}
        if not _parseable(stage, item):
            return None
        if error is None:
            ok += 1
        else:
            failed += 1
    return ok, failed


def _current_source_scope(
    conn: psycopg.Connection,
    *,
    manifest: dict,
    supervisor: pipeline_lease.LeaseSupervisor,
) -> bool:
    """Every target belongs to one source's latest usable Markdown artifact."""
    artifacts = sorted({target["artifact_id"] for target in manifest["targets"]})
    if not artifacts or not supervisor.enabled or supervisor.lease is None:
        return False
    rows = conn.execute(
        "SELECT a.id, s.id, a.id = ("
        " SELECT a2.id FROM source_snapshot sn2"
        " JOIN artifact a2 ON a2.snapshot_id = sn2.id"
        " WHERE sn2.source_id = s.id AND sn2.status = 'ok'"
        " AND a2.kind = 'markdown'"
        " ORDER BY a2.created_at DESC, a2.id DESC LIMIT 1)"
        " FROM artifact a"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " JOIN source s ON s.id = sn.source_id"
        " WHERE a.id = ANY(%s) AND a.kind = 'markdown'",
        (artifacts,),
    ).fetchall()
    sources = {source_id for _, source_id, _ in rows}
    return (
        len(rows) == len(artifacts)
        and len(sources) == 1
        and all(is_current for _, _, is_current in rows)
        and supervisor.lease.scope_key == f"source:{next(iter(sources))}"
    )


def _without_old_lease(params: dict) -> dict:
    normalized = dict(params)
    normalized.pop("pipeline_lease", None)
    return normalized


def _publisher(
    stage: str,
) -> Callable[..., dict] | None:
    if stage == "passage-cuts":
        from universe.passages import materialize

        return materialize
    if stage == "task-generation":
        from universe.tasks import materialize

        return materialize
    if stage == "task-granularity":
        from universe.task_granularity import materialize_parts

        return materialize_parts
    return None


def publish(
    conn: psycopg.Connection,
    *,
    stage: str,
    run_id: str,
    commit: bool = True,
) -> dict | None:
    """Publish one producer run, or no-op for a non-producer stage.

    ``commit=False`` is the harness seam: derived rows and the final run status
    then become visible atomically. Recovery/operations callers retain the
    materializers' historical committing behavior by using the default.
    """
    publisher = _publisher(stage)
    if publisher is None:
        return None
    return publisher(conn, run_id, commit=commit)


def finalize(
    conn: psycopg.Connection,
    *,
    stage: str,
    run_id: str,
    status: str,
) -> dict:
    """Atomically publish derived rows and close one ``publishing`` run."""
    if not is_producer(stage) or status not in {"done", "failed"}:
        raise ValueError("producer finalization requires a producer and terminal status")
    open_run = conn.execute(
        "SELECT id FROM run"
        " WHERE id = %s AND stage = %s AND status = 'publishing'"
        " FOR UPDATE",
        (run_id, stage),
    ).fetchone()
    if open_run is None:
        raise PublicationNotReady(
            f"{run_id} is no longer an open {stage} publication"
        )
    publication = publish(conn, stage=stage, run_id=run_id, commit=False)
    if publication is None:  # pragma: no cover - guarded by is_producer
        raise PublicationNotReady(f"{stage} has no deterministic publisher")
    closed = conn.execute(
        "UPDATE run SET status = %s, finished_at = now()"
        " WHERE id = %s AND stage = %s AND status = 'publishing'"
        " RETURNING id",
        (status, run_id, stage),
    ).fetchone()
    if closed is None:
        raise PublicationNotReady(
            f"{run_id} is no longer an open {stage} publication"
        )
    conn.commit()
    return publication


def recover(
    conn: psycopg.Connection,
    *,
    stage: str,
    model: str,
    prompt_ref: str,
    prompt_sha: str,
    params: dict,
    supervisor: pipeline_lease.LeaseSupervisor,
) -> dict | None:
    """Finish an exact orphan publication under the caller's successor lease.

    Returns the normal harness summary shape, or ``None`` when no candidate is
    unambiguously reusable.  A mismatch always falls through to a fresh model
    run; recovery never guesses at a changed target or upstream manifest.
    """
    if (
        not is_producer(stage)
        or not supervisor.enabled
        or supervisor.lease is None
        or supervisor.lease.stage != stage
    ):
        return None
    expected_manifest = params.get("target_manifest")
    if not _valid_manifest(expected_manifest):
        return None

    # Lazy import avoids producer_publication -> recipe_identity -> harness at
    # module import time. At runtime the harness is fully initialized.
    from universe.recipe_identity import matches_recipe

    rows = conn.execute(
        "SELECT id, model, prompt_ref, prompt_sha, params"
        " FROM run WHERE stage = %s AND status = 'publishing'"
        " ORDER BY started_at DESC, id DESC",
        (stage,),
    ).fetchall()
    for run_id, seen_model, seen_ref, seen_sha, seen_params in rows:
        seen_params = seen_params or {}
        if (
            seen_model != model
            or seen_ref != prompt_ref
            or seen_sha != prompt_sha
            or _without_old_lease(seen_params) != params
            or not matches_recipe(
                stage,
                model=seen_model,
                prompt_ref=seen_ref,
                prompt_sha=seen_sha,
                params=seen_params,
            )
            or not _current_source_scope(
                conn,
                manifest=expected_manifest,
                supervisor=supervisor,
            )
        ):
            continue
        counts = _complete_items(
            conn,
            run_id=run_id,
            stage=stage,
            manifest=expected_manifest,
        )
        if counts is None:
            continue
        ok, failed = counts
        status = "done" if ok else "failed"
        finalize(conn, stage=stage, run_id=run_id, status=status)
        return {
            "run_id": run_id,
            "status": status,
            "ok": ok,
            "failed": failed,
        }
    return None
