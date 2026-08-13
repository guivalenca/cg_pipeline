"""Read-only resolution of the task text an exact run chain consumed.

Task identity remains stable when revision rewrites its wording. This Module
keeps that distinction explicit: callers pin generation, split, and revision
witnesses, then receive effective body/answer evidence without mutating the
ledger or accidentally reloading the raw task row.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable

import psycopg

from universe.harness import fetch_items
from universe.tasks import fetch_tasks_for_runs


def _ids(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    return list(value)


def resolve_chain(
    conn: psycopg.Connection,
    *,
    generation_runs: Iterable[str],
    granularity_runs: Iterable[str] = (),
    revision_runs: Iterable[str] = (),
    task_ids: Iterable[str] | None = None,
) -> list[dict]:
    """Resolve exact post-split tasks and revision text without writes."""
    generation_runs = list(generation_runs)
    granularity_runs = list(granularity_runs)
    revision_runs = list(dict.fromkeys(revision_runs))
    originals = fetch_tasks_for_runs(conn, generation_runs)

    selected = originals
    if granularity_runs:
        from universe.task_granularity import granularity_of

        chosen: dict[str, tuple[str, dict]] = {}
        for run_id in granularity_runs:
            for item in fetch_items(conn, run_id):
                if not item["task_id"]:
                    raise RuntimeError(f"{item['id']} is not about a task")
                parsed = granularity_of(item)
                if isinstance(parsed, dict):
                    chosen[item["task_id"]] = (item["id"], parsed)
        missing = [task["id"] for task in originals if task["id"] not in chosen]
        if missing:
            raise RuntimeError(
                "post-split evidence has no usable granularity for "
                + ", ".join(missing)
            )
        parts_by_item: dict[str, list[dict]] = {}
        for part in fetch_tasks_for_runs(conn, granularity_runs):
            parts_by_item.setdefault(part["run_item_id"], []).append(part)
        selected = []
        for original in originals:
            item_id, verdict = chosen[original["id"]]
            if verdict["verdict"] == "composite":
                selected.extend(parts_by_item.get(item_id, []))
            else:
                selected.append(original)

    if revision_runs:
        from universe.task_triage import fetch_revisions

        revisions: dict = {}
        for run_id in revision_runs:
            revisions.update(fetch_revisions(conn, run_id))
        resolved = []
        for task in selected:
            revision = revisions.get(task["id"])
            if not isinstance(revision, dict):
                raise RuntimeError(
                    f"effective evidence has no usable revision for {task['id']}"
                )
            if revision["verdict"] == "unfixable":
                continue
            if revision["verdict"] == "rewritten":
                task = {**task, "body": revision["task"]}
            resolved.append(task)
        selected = resolved

    by_id = {task["id"]: task for task in selected}
    if task_ids is not None:
        requested = list(dict.fromkeys(task_ids))
        missing = [task_id for task_id in requested if task_id not in by_id]
        if missing:
            raise RuntimeError(
                "effective task evidence is missing " + ", ".join(missing)
            )
        selected = [by_id[task_id] for task_id in requested]
    return sorted(selected, key=lambda task: task["id"])


def _chain_from_params(params: dict) -> tuple[list[str], list[str], list[str]]:
    generation = _ids(params.get("gen_runs"))
    granularity = _ids(
        params.get("granularity_runs") or params.get("granularity_run")
    )
    revisions = _ids(params.get("revision_run")) + _ids(
        params.get("parts_revision_run")
    )
    return generation, granularity, list(dict.fromkeys(revisions))


def resolve_statement_tasks(
    conn: psycopg.Connection,
    statement_runs: Iterable[str],
    task_ids: Iterable[str] | None = None,
) -> list[dict]:
    """Resolve tasks chosen by newest usable stated verdicts and their chains."""
    from universe.kc_statement import statement_of

    statement_runs = list(statement_runs)
    rows = conn.execute(
        "SELECT i.task_id, i.id, i.response, i.error, r.id, r.params"
        " FROM run_item i JOIN run r ON r.id = i.run_id"
        " WHERE r.id = ANY(%s)"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (statement_runs,),
    ).fetchall()
    chosen: dict[str, tuple[str, dict]] = {}
    for task_id, item_id, response, error, run_id, params in rows:
        if task_id is None:
            raise RuntimeError(f"{item_id} is not about a task")
        if task_id in chosen:
            continue
        parsed = statement_of({"response": response, "error": error})
        if isinstance(parsed, dict):
            # ``unsure`` is a usable, suppressing verdict. It must block an
            # older stated answer rather than resurrecting stale evidence.
            chosen[task_id] = (run_id, parsed)

    stated = {
        task_id: run_id
        for task_id, (run_id, parsed) in chosen.items()
        if parsed["verdict"] == "stated"
    }
    requested = sorted(stated) if task_ids is None else list(dict.fromkeys(task_ids))
    missing = [task_id for task_id in requested if task_id not in stated]
    if missing:
        raise RuntimeError(
            "statement evidence is not currently stated for " + ", ".join(missing)
        )

    params_by_run = {
        run_id: (params or {})
        for run_id, params in conn.execute(
            "SELECT id, params FROM run WHERE id = ANY(%s)",
            (statement_runs,),
        ).fetchall()
    }
    resolved: dict[str, dict] = {}
    by_run: dict[str, list[str]] = {}
    for task_id in requested:
        by_run.setdefault(stated[task_id], []).append(task_id)
    for run_id, ids in by_run.items():
        generation, granularity, revisions = _chain_from_params(params_by_run[run_id])
        for task in resolve_chain(
            conn,
            generation_runs=generation,
            granularity_runs=granularity,
            revision_runs=revisions,
            task_ids=ids,
        ):
            resolved[task["id"]] = {**task, "statement_run_id": run_id}
    return [resolved[task_id] for task_id in sorted(requested)]


def effective_task_manifest(tasks: Iterable[dict]) -> list[tuple[str, str, str]]:
    """Canonical ordered evidence triples used for provenance fingerprints."""
    return sorted(
        (task["id"], task["body"], task["answer"])
        for task in tasks
    )


def effective_task_manifest_sha(tasks: Iterable[dict]) -> str:
    payload = json.dumps(
        effective_task_manifest(tasks),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def effective_task_run_params(tasks: Iterable[dict], **scope: object) -> dict:
    """Stamp one selected task scope with its exact effective evidence."""
    return {
        **scope,
        "effective_task_manifest_sha": effective_task_manifest_sha(tasks),
    }


def effective_task_manifest_for_run(
    conn: psycopg.Connection,
    run_id: str,
) -> list[tuple[str, str, str]]:
    """Resolve the task item scope stamped by one downstream run's chain."""
    row = conn.execute("SELECT params FROM run WHERE id = %s", (run_id,)).fetchone()
    if row is None:
        raise LookupError(f"no run {run_id}")
    task_ids = [
        item[0]
        for item in conn.execute(
            "SELECT DISTINCT task_id FROM run_item"
            " WHERE run_id = %s AND task_id IS NOT NULL ORDER BY task_id",
            (run_id,),
        ).fetchall()
    ]
    generation, granularity, revisions = _chain_from_params(row[0] or {})
    return effective_task_manifest(
        resolve_chain(
            conn,
            generation_runs=generation,
            granularity_runs=granularity,
            revision_runs=revisions,
            task_ids=task_ids,
        )
    )
