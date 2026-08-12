"""Select the one post-granularity task scope every downstream stage shares.

Composite parents are instructions to create replacement tasks, not learners'
tasks that remain beside their parts. This Module publishes generation and
split rows idempotently, then returns originals with each composite replaced
by the parts of its exact chosen granularity item.
"""

from __future__ import annotations

import psycopg

from universe.harness import fetch_items
from universe.tasks import fetch_tasks_for_runs, materialize


def tasks(
    conn: psycopg.Connection,
    *,
    generation_runs: list[str],
    granularity_runs: list[str] | None = None,
) -> list[dict]:
    """Materialize and return the exact post-split task scope."""
    granularity_runs = list(granularity_runs or [])
    for run_id in generation_runs:
        materialize(conn, run_id)
    originals = fetch_tasks_for_runs(conn, generation_runs)
    if not granularity_runs:
        return originals

    # Local import avoids task_triage -> post_split -> task_granularity ->
    # task_triage at import time.
    from universe.task_granularity import granularity_of, materialize_parts

    chosen: dict[str, tuple[str, dict]] = {}
    for run_id in granularity_runs:
        materialize_parts(conn, run_id)
        for item in fetch_items(conn, run_id):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            verdict = granularity_of(item)
            if isinstance(verdict, dict):
                chosen[item["task_id"]] = (item["id"], verdict)

    if originals:
        missing = [task["id"] for task in originals if task["id"] not in chosen]
        if missing:
            raise SystemExit(
                f"{len(missing)} task(s) have no usable granularity in"
                f" {', '.join(granularity_runs)}: {', '.join(missing)};"
                " silence is not a verdict"
            )

    parts_by_item: dict[str, list[dict]] = {}
    for part in fetch_tasks_for_runs(conn, granularity_runs):
        parts_by_item.setdefault(part["run_item_id"], []).append(part)

    selected: list[dict] = []
    for original in originals:
        item_id, verdict = chosen[original["id"]]
        if verdict["verdict"] == "composite":
            selected.extend(parts_by_item.get(item_id, []))
        else:
            selected.append(original)
    if not originals:
        selected = [
            part
            for item_id, verdict in chosen.values()
            if verdict["verdict"] == "composite"
            for part in parts_by_item.get(item_id, [])
        ]
    return selected
