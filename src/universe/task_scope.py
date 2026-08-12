"""Resolve the exact effective task scope shared by KC-facing consumers."""

from __future__ import annotations

import json

import psycopg

from universe.harness import fetch_items
from universe.passages import fetch_passages_for_runs
from universe.post_split import tasks as post_split_tasks

_TRIAGE_VERDICTS = {"supported", "unsupported", "unsure"}


def _triage(item: dict) -> str | None:
    if item["error"]:
        return None
    try:
        parsed = json.loads(item["response"])
    except (TypeError, json.JSONDecodeError):
        return None
    verdict = parsed.get("verdict") if isinstance(parsed, dict) else None
    return verdict if verdict in _TRIAGE_VERDICTS else None


def effective_tasks(
    conn: psycopg.Connection,
    *,
    generation_runs: list[str],
    passages_from: list[str] | None = None,
    granularity_run: str | None = None,
    revision_run: str | None = None,
    parts_revision_run: str | None = None,
    triage_run: str | None = None,
    substance_run: str | None = None,
) -> list[dict]:
    """Post-split tasks after the exact revision and quality-gate witnesses."""
    if parts_revision_run and not granularity_run:
        raise SystemExit("--parts-revision-run requires --granularity-run")
    tasks = post_split_tasks(
        conn,
        generation_runs=generation_runs,
        granularity_runs=[granularity_run] if granularity_run else [],
    )

    if passages_from:
        drawn = {p["id"] for p in fetch_passages_for_runs(conn, passages_from)}
        tasks = [task for task in tasks if task["passage_id"] in drawn]

    revision_runs = [
        run_id
        for run_id in (revision_run, parts_revision_run)
        if run_id is not None
    ]
    if revision_runs:
        from universe.task_triage import apply_revisions, fetch_revisions

        revisions: dict = {}
        for run_id in revision_runs:
            revisions.update(fetch_revisions(conn, run_id))
        tasks, _, unjudged = apply_revisions(tasks, revisions)
        if unjudged:
            names = ", ".join(task["id"] for task in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable revision in"
                f" {', '.join(revision_runs)}: {names}; silence is not a verdict"
            )

    if triage_run:
        verdicts = {}
        for item in fetch_items(conn, triage_run):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            verdicts[item["task_id"]] = _triage(item)
        unjudged = [task for task in tasks if verdicts.get(task["id"]) is None]
        if unjudged:
            names = ", ".join(task["id"] for task in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable triage in"
                f" {triage_run}: {names}; silence is not a verdict"
            )
        tasks = [task for task in tasks if verdicts[task["id"]] == "supported"]

    if substance_run:
        from universe.task_substance import DROPPED, substance_of

        verdicts = {}
        for item in fetch_items(conn, substance_run):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            verdicts[item["task_id"]] = substance_of(item)
        unjudged = [
            task
            for task in tasks
            if not isinstance(verdicts.get(task["id"]), dict)
        ]
        if unjudged:
            names = ", ".join(task["id"] for task in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable substance in"
                f" {substance_run}: {names}; silence is not a verdict"
            )
        tasks = [
            task
            for task in tasks
            if verdicts[task["id"]]["verdict"] not in DROPPED
        ]
    return tasks
