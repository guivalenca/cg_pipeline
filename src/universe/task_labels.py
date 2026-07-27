"""Human-readable, chain-relative labels for task reports."""

import psycopg

from universe.harness import fetch_items
from universe.passages import fetch_passages_for_runs
from universe.task_granularity import materialize_parts
from universe.task_triage import apply_revisions, fetch_revisions
from universe.tasks import fetch_tasks_for_runs


def label_map(
    conn: psycopg.Connection,
    gen_runs: list[str],
    passages_from: list[str],
    revision_run: str,
    granularity_runs: list[str] | None = None,
) -> dict[str, str]:
    """Chain-relative labels mapping task_id -> label (T01, T02, ..., or parts like 'T16 part 2'). Labels are stable for a fixed chain but recomputed per report."""
    tasks = fetch_tasks_for_runs(conn, gen_runs)
    drawn = {passage["id"] for passage in fetch_passages_for_runs(conn, passages_from)}
    tasks = [task for task in tasks if task["passage_id"] in drawn]

    tasks, _dropped, unjudged = apply_revisions(
        tasks, fetch_revisions(conn, revision_run)
    )
    if unjudged:
        names = ", ".join(task["id"] for task in unjudged)
        raise SystemExit(
            f"{len(unjudged)} task(s) have no usable revision in"
            f" {revision_run}: {names}; cannot assign chain-relative labels"
        )

    labels = {task["id"]: f"T{number:02d}" for number, task in enumerate(tasks, 1)}
    if not granularity_runs:
        return labels

    parent_by_item: dict[str, str] = {}
    for granularity_run in granularity_runs:
        materialize_parts(conn, granularity_run)
        for item in fetch_items(conn, granularity_run):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            parent_by_item[item["id"]] = item["task_id"]

    for part in fetch_tasks_for_runs(conn, granularity_runs):
        parent_id = parent_by_item.get(part["run_item_id"])
        if parent_id is None:
            raise SystemExit(
                f"{part['id']} has no granularity run item naming its parent task"
            )
        parent_label = labels.get(parent_id)
        if parent_label is None:
            raise SystemExit(
                f"{part['id']} names parent task {parent_id},"
                " which is outside the labeling chain"
            )
        labels[part["id"]] = f"{parent_label} part {part['seq']}"

    return labels
