"""Human-readable, chain-relative labels for task reports.

The preferred interface labels an exact, already-resolved effective task
scope.  A positional legacy adapter remains for extraction reports that still
provide generation, passage, and revision runs.
"""

import psycopg

from universe.harness import fetch_items
from universe.passages import fetch_passages_for_runs
from universe.task_granularity import materialize_parts
from universe.task_triage import apply_revisions, fetch_revisions
from universe.tasks import fetch_tasks_for_runs


def label_map(
    conn: psycopg.Connection,
    tasks: list[dict] | list[str] | None = None,
    gen_runs: list[str] | None = None,
    granularity_runs: list[str] | str | None = None,
    legacy_granularity_runs: list[str] | None = None,
    *,
    passages_from: list[str] | None = None,
    revision_run: str | None = None,
) -> dict[str, str]:
    """Map task ids to stable-in-chain labels through either supported form.

    Preferred form::

        label_map(conn, effective_tasks, generation_runs, granularity_runs)

    Legacy extraction form::

        label_map(
            conn, generation_runs, passage_runs, revision_run,
            granularity_runs,
        )

    The legacy form reconstructs its historical scope, then uses the original
    implementation so extraction report behavior stays unchanged.
    """
    if passages_from is not None or revision_run is not None:
        if revision_run is None:
            raise TypeError("revision_run is required with passages_from")
        if tasks is None:
            legacy_gen_runs = gen_runs
            legacy_passages = passages_from
        elif passages_from is None:
            legacy_gen_runs = tasks
            legacy_passages = gen_runs
        elif gen_runs is None:
            legacy_gen_runs = tasks
            legacy_passages = passages_from
        else:
            raise TypeError("legacy generation runs were specified twice")
        if legacy_gen_runs is None or legacy_passages is None:
            raise TypeError(
                "generation and passage runs are required with revision_run"
            )
        if isinstance(granularity_runs, str):
            raise TypeError("revision_run was specified twice")
        if granularity_runs is not None and legacy_granularity_runs is not None:
            raise TypeError("granularity runs were specified twice")
        return _legacy_label_map(
            conn,
            legacy_gen_runs,
            legacy_passages,
            revision_run,
            legacy_granularity_runs or granularity_runs,
        )
    if isinstance(granularity_runs, str):
        if tasks is None or gen_runs is None:
            raise TypeError(
                "generation and passage runs are required with a revision run"
            )
        return _legacy_label_map(
            conn,
            tasks,
            gen_runs,
            granularity_runs,
            legacy_granularity_runs,
        )
    if legacy_granularity_runs is not None:
        raise TypeError(
            "legacy_granularity_runs is only valid with a revision run"
        )
    if tasks is None or gen_runs is None:
        raise TypeError("tasks and gen_runs are required")
    return _effective_label_map(
        conn,
        tasks,
        gen_runs,
        granularity_runs,
    )


def _effective_label_map(
    conn: psycopg.Connection,
    tasks: list[dict],
    gen_runs: list[str],
    granularity_runs: list[str] | None,
) -> dict[str, str]:
    """Label only the effective tasks supplied by the caller."""
    selected = {task["id"]: task for task in tasks}
    originals = fetch_tasks_for_runs(conn, gen_runs)
    original_ids = {task["id"] for task in originals}

    parent_by_item: dict[str, str] = {}
    for granularity_run in granularity_runs or []:
        for item in fetch_items(conn, granularity_run):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            parent_by_item[item["id"]] = item["task_id"]

    parts_by_parent: dict[str, list[dict]] = {}
    unknown: list[str] = []
    for task in tasks:
        if task["id"] in original_ids:
            continue
        parent_id = parent_by_item.get(task["run_item_id"])
        if parent_id not in original_ids:
            unknown.append(task["id"])
            continue
        parts_by_parent.setdefault(parent_id, []).append(task)
    if unknown:
        raise SystemExit(
            "effective task(s) are outside the labeling chain: "
            + ", ".join(sorted(unknown))
        )

    labels: dict[str, str] = {}
    number = 0
    for original in originals:
        direct = selected.get(original["id"])
        parts = sorted(
            parts_by_parent.get(original["id"], []),
            key=lambda task: (task["seq"], task["id"]),
        )
        if direct is None and not parts:
            continue
        number += 1
        parent_label = f"T{number:02d}"
        if direct is not None:
            labels[direct["id"]] = parent_label
        for part in parts:
            labels[part["id"]] = f"{parent_label} part {part['seq']}"
    return labels


def _legacy_label_map(
    conn: psycopg.Connection,
    gen_runs: list[str],
    passages_from: list[str],
    revision_run: str,
    granularity_runs: list[str] | None = None,
) -> dict[str, str]:
    """Preserve the extraction reports' historical scope reconstruction."""
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

    surviving_task_ids = {task["id"] for task in tasks}
    for part in fetch_tasks_for_runs(conn, granularity_runs):
        parent_id = parent_by_item.get(part["run_item_id"])
        if parent_id not in surviving_task_ids:
            continue
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
