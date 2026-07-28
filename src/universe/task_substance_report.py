"""Read task-substance runs side by side, comparing verdicts across runs.

    python -m universe.task_substance_report r0072 r0073 --gen-runs r0052 \
        --revision-run r0065 [--passages-from r0017]

Reconstructs the judged texts exactly as the runner does (applying
--passages-from filter and --revision-run overlay), then lays out repairs,
uncertain cases, and rejected pairs side by side, with working pairs listed
compactly at the end.
"""

import argparse
import sys
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run, id_list
from universe.passages import fetch_passages_for_runs
from universe.task_granularity import granularity_of, materialize_parts
from universe.task_labels import label_map
from universe.task_substance import DROPPED, KEPT, STAGE, substance_of
from universe.task_triage import apply_revisions, fetch_revisions
from universe.tasks import fetch_tasks_for_runs, materialize

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def verdict_label(substance: dict | str) -> str:
    return substance["verdict"] if isinstance(substance, dict) else substance


def render_verdict(run_id: str, substance: dict | str) -> list[str]:
    lines = [f"- {run_id}: {verdict_label(substance)}"]
    if isinstance(substance, dict) and substance.get("reason"):
        lines[0] += f" — {substance['reason']}"
    if isinstance(substance, dict) and substance["verdict"] == "fixable":
        if "task" in substance:
            lines.append(f"  > Corrected task: {substance['task']}")
        if "answer" in substance:
            lines.append(f"  > Corrected answer: {substance['answer']}")
    return lines


def render_runs(
    conn: psycopg.Connection,
    run_ids: list[str],
    gen_runs: list[str],
    revision_run: str | None = None,
    passages_from: list[str] | None = None,
    granularity_run: str | None = None,
    parts_revision_run: str | None = None,
) -> str:
    """Render side-by-side report comparing verdicts across runs."""
    # Materialize and fetch the task set to be judged
    for run_id in gen_runs:
        materialize(conn, run_id)
    tasks = fetch_tasks_for_runs(conn, gen_runs)

    # Apply passages filter if specified
    if passages_from:
        drawn = {p["id"] for p in fetch_passages_for_runs(conn, passages_from)}
        tasks = [t for t in tasks if t["passage_id"] in drawn]

    # Apply revision-run overlay if specified
    if revision_run:
        revisions = fetch_revisions(conn, revision_run)
        tasks, dropped, unjudged = apply_revisions(tasks, revisions)
        if unjudged:
            names = ", ".join(t["id"] for t in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable revision in"
                f" {revision_run}: {names}; silence is not a verdict"
            )

    if parts_revision_run and not granularity_run:
        raise SystemExit("--parts-revision-run requires --granularity-run")

    if granularity_run:
        granularity = {}
        for item in fetch_items(conn, granularity_run):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            granularity[item["task_id"]] = granularity_of(item)
        unjudged = [
            task
            for task in tasks
            if not isinstance(granularity.get(task["id"]), dict)
        ]
        if unjudged:
            names = ", ".join(task["id"] for task in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable granularity in"
                f" {granularity_run}: {names}; silence is not a verdict"
            )
        surviving_task_ids = {task["id"] for task in tasks}
        tasks = [
            task
            for task in tasks
            if granularity[task["id"]]["verdict"] != "composite"
        ]
        materialize_parts(conn, granularity_run)
        parent_by_part_run_item = {
            item["id"]: item["task_id"] for item in fetch_items(conn, granularity_run)
        }
        part_tasks = [
            task for task in fetch_tasks_for_runs(conn, [granularity_run])
            if parent_by_part_run_item[task["run_item_id"]] in surviving_task_ids
        ]
        if parts_revision_run:
            revisions = fetch_revisions(conn, parts_revision_run)
            part_tasks, dropped, unjudged = apply_revisions(part_tasks, revisions)
            if unjudged:
                names = ", ".join(task["id"] for task in unjudged)
                raise SystemExit(
                    f"{len(unjudged)} task(s) have no usable revision in"
                    f" {parts_revision_run}: {names}; silence is not a verdict"
                )
        tasks.extend(part_tasks)

    task_labels = (
        label_map(
            conn,
            gen_runs,
            passages_from,
            revision_run,
            [granularity_run] if granularity_run else None,
        )
        if passages_from and revision_run
        else {}
    )

    # Build set of task_ids we're judging
    judged_task_ids = {t["id"] for t in tasks}
    task_dict = {t["id"]: t for t in tasks}

    # Collect results from each run
    runs = []
    results = {}  # (run_id, task_id) -> verdict dict or str
    for run_id in run_ids:
        run = fetch_run(conn, run_id)
        if run["stage"] != STAGE:
            raise SystemExit(f"{run_id} is a {run['stage']} run, not {STAGE}")
        runs.append({"id": run_id, "model": run["model"]})

        run_task_ids = set()
        for item in fetch_items(conn, run_id):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            run_task_ids.add(item["task_id"])
            results[(run_id, item["task_id"])] = substance_of(item)

        # Validate that run's task_ids match the reconstructed set
        if run_task_ids != judged_task_ids:
            missing = judged_task_ids - run_task_ids
            extra = run_task_ids - judged_task_ids
            msg = f"{run_id}: task_id mismatch."
            if missing:
                msg += f" Missing: {', '.join(sorted(missing))}."
            if extra:
                msg += f" Extra: {', '.join(sorted(extra))}."
            raise SystemExit(msg)

    # Build tally per run
    lines = [f"# Task substance: {', '.join(run_ids)}", ""]
    for run in runs:
        labels = sorted(
            verdict_label(substance)
            for (run_id, _), substance in results.items()
            if run_id == run["id"]
        )
        tally = {label: labels.count(label) for label in set(labels)}
        tally_str = ", ".join(f"{tally[label]} {label}" for label in sorted(tally))
        lines.append(f"- {run['id']}: {run['model']}, {tally_str}")

    lines.append("")

    # Classify each task by the strongest verdict it received.
    dropped_tasks = set()
    fixable_tasks = set()
    unsure_tasks = set()
    no_verdict_tasks = {}
    for task_id in judged_task_ids:
        failed_runs = [
            (run["id"], verdict_label(results.get((run["id"], task_id))))
            for run in runs
            if verdict_label(results.get((run["id"], task_id))) in {"error", "unparseable"}
        ]
        if failed_runs:
            no_verdict_tasks[task_id] = failed_runs
            continue
        has_dropped = any(
            verdict_label(results.get((run["id"], task_id))) in DROPPED
            for run in runs
        )
        has_fixable = any(
            verdict_label(results.get((run["id"], task_id))) == "fixable"
            for run in runs
        )
        has_unsure = any(
            verdict_label(results.get((run["id"], task_id))) == "unsure"
            for run in runs
        )
        if has_dropped:
            dropped_tasks.add(task_id)
        elif has_fixable:
            fixable_tasks.add(task_id)
        elif has_unsure:
            unsure_tasks.add(task_id)

    lines.append("## No verdict")
    lines.append("")
    if no_verdict_tasks:
        for task_id in sorted(no_verdict_tasks):
            task = task_dict[task_id]
            lines.append(f"### {task_labels.get(task_id, task_id)}")
            lines.append("")
            lines.append(f"> {task['body']}")
            lines.append(f">\n> {task['answer']}")
            lines.append("")
            for run in runs:
                lines += render_verdict(run["id"], results.get((run["id"], task_id)))
            lines.append("")
    else:
        lines.append("None.")
    lines.append("")

    lines.append("## Dropped")
    lines.append("")
    if dropped_tasks:
        for task_id in sorted(dropped_tasks):
            task = task_dict[task_id]
            lines.append(f"### {task_labels.get(task_id, task_id)}")
            lines.append("")
            lines.append(f"> {task['body']}")
            lines.append(f">\n> {task['answer']}")
            lines.append("")
            for run in runs:
                lines += render_verdict(run["id"], results.get((run["id"], task_id)))
            lines.append("")
    else:
        lines.append("None.")
        lines.append("")

    lines.append("## Fixable")
    lines.append("")
    if fixable_tasks:
        for task_id in sorted(fixable_tasks):
            task = task_dict[task_id]
            lines.append(f"### {task_labels.get(task_id, task_id)}")
            lines.append("")
            lines.append(f"> {task['body']}")
            lines.append(f">\n> {task['answer']}")
            lines.append("")
            for run in runs:
                lines += render_verdict(run["id"], results.get((run["id"], task_id)))
            lines.append("")
    else:
        lines.append("None.")
        lines.append("")

    lines.append("## Unsure")
    lines.append("")
    if unsure_tasks:
        for task_id in sorted(unsure_tasks):
            task = task_dict[task_id]
            lines.append(f"### {task_labels.get(task_id, task_id)}")
            lines.append("")
            lines.append(f"> {task['body']}")
            lines.append(f">\n> {task['answer']}")
            lines.append("")
            for run in runs:
                lines += render_verdict(run["id"], results.get((run["id"], task_id)))
            lines.append("")
    else:
        lines.append("None.")
        lines.append("")

    lines.append("## Works everywhere")
    lines.append("")
    works_tasks = {
        task_id
        for task_id in judged_task_ids
        if task_id not in (set(no_verdict_tasks) | dropped_tasks | fixable_tasks | unsure_tasks)
    }
    if works_tasks:
        for task_id in sorted(works_tasks):
            task = task_dict[task_id]
            lines.append(f"- {task_labels.get(task_id, task_id)}: {task['body']}")
    else:
        lines.append("None.")
    lines.append("")
    if task_labels:
        lines += ["## Label map", ""]
        lines += [f"- {label} = {task_id}" for task_id, label in task_labels.items()]
        lines.append("")

    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection,
    run_ids: list[str],
    gen_runs: list[str],
    revision_run: str | None = None,
    passages_from: list[str] | None = None,
    granularity_run: str | None = None,
    parts_revision_run: str | None = None,
    reports_dir: Path | None = None,
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"task-substance-{'-'.join(run_ids)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_runs(
            conn,
            run_ids,
            gen_runs,
            revision_run=revision_run,
            passages_from=passages_from,
            granularity_run=granularity_run,
            parts_revision_run=parts_revision_run,
        )
    )
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.task_substance_report", description=__doc__)
    parser.add_argument("run_ids", nargs="+", help="task-substance run ids to compare")
    parser.add_argument("--gen-runs", type=id_list, required=True, help="task-generation run ids")
    parser.add_argument("--revision-run", help="task-revision run id for overlay")
    parser.add_argument(
        "--granularity-run",
        help="task-granularity run id; replace composite tasks with its parts",
    )
    parser.add_argument(
        "--parts-revision-run",
        help="task-revision run id; overlay rewrites and drop unfixable parts",
    )
    parser.add_argument(
        "--passages-from", type=id_list, help="comma-separated cuts run ids to filter by"
    )
    args = parser.parse_args(argv)
    with connect() as conn:
        print(
            write_report(
                conn,
                args.run_ids,
                args.gen_runs,
                revision_run=args.revision_run,
                passages_from=args.passages_from,
                granularity_run=args.granularity_run,
                parts_revision_run=args.parts_revision_run,
            ),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
