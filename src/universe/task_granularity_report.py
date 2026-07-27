"""Read one task-granularity run as its decisions and resulting splits.

    python -m universe.task_granularity_report r0071 --gen-runs r0052
    python -m universe.task_granularity_report r0071 --gen-runs r0052 \
        --revision-run r0065

Generation and revision run ids are repeated here because model-run parameters
do not record which task rows were selected or which blind rewrites replaced
their bodies. The granularity run's task ids anchor the selection; replaying
those inputs reconstructs exactly what the model judged without consulting the
source it never saw.
"""

import argparse
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import REPORTS_DIR, fetch_items, fetch_run, id_list
from universe.task_granularity import STAGE, VERDICTS, granularity_of
from universe.task_labels import label_map
from universe.task_triage import apply_revisions, fetch_revisions
from universe.tasks import fetch_tasks_for_runs


def _blockquote(task: dict) -> list[str]:
    lines = ["> **Task:**"]
    lines += [f"> {line}" if line else ">" for line in task["body"].splitlines()]
    lines += [">", "> **Answer:**"]
    lines += [f"> {line}" if line else ">" for line in task["answer"].splitlines()]
    return lines


def _part(number: int, part: dict, label: str | None = None) -> list[str]:
    task_lines = part["task"].splitlines()
    prefix = f"{label}: " if label else ""
    lines = [f"{number}. {prefix}{task_lines[0]}"]
    lines += [f"   {line}" for line in task_lines[1:]]
    lines.append("")
    lines += [f"   > {line}" if line else "   >" for line in part["answer"].splitlines()]
    return lines


def collect(
    conn: psycopg.Connection,
    run_id: str,
    gen_runs: list[str],
    revision_run: str | None = None,
) -> tuple[dict, list[tuple[dict, dict | str]]]:
    """The run and every judged task with the body that entered its call."""
    run = fetch_run(conn, run_id)
    if run["stage"] != STAGE:
        raise SystemExit(f"{run_id} is a {run['stage']} run, not {STAGE}")

    items = fetch_items(conn, run_id)
    for item in items:
        if not item["task_id"]:
            raise SystemExit(f"{item['id']} is not about a task")

    available = {task["id"]: task for task in fetch_tasks_for_runs(conn, gen_runs)}
    missing = [item["task_id"] for item in items if item["task_id"] not in available]
    if missing:
        raise SystemExit(
            f"{len(missing)} judged task(s) are not from {', '.join(gen_runs)}:"
            f" {', '.join(missing)}"
        )
    tasks = [available[item["task_id"]] for item in items]

    if revision_run:
        revisions = fetch_revisions(conn, revision_run)
        tasks, dropped, unjudged = apply_revisions(tasks, revisions)
        if unjudged:
            names = ", ".join(task["id"] for task in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable revision in"
                f" {revision_run}: {names}; silence is not a verdict"
            )
        if dropped:
            names = ", ".join(task["id"] for task in dropped)
            raise SystemExit(
                f"{len(dropped)} task(s) judged by {run_id} were unfixable in"
                f" {revision_run}: {names}"
            )

    by_id = {task["id"]: task for task in tasks}
    return run, [
        (by_id[item["task_id"]], granularity_of(item))
        for item in items
        if item["task_id"] in by_id
    ]


def _label(granularity: dict | str) -> str:
    return granularity["verdict"] if isinstance(granularity, dict) else granularity


def render_run(
    conn: psycopg.Connection,
    run_id: str,
    gen_runs: list[str],
    revision_run: str | None = None,
    passages_from: list[str] | None = None,
) -> str:
    run, judged = collect(conn, run_id, gen_runs, revision_run)
    task_labels = (
        label_map(conn, gen_runs, passages_from, revision_run, [run_id])
        if passages_from and revision_run
        else {}
    )
    labels = VERDICTS + ("error", "unparseable")
    tally = {
        label: sum(1 for _, granularity in judged if _label(granularity) == label)
        for label in labels
    }
    counts = " / ".join(f"{tally[label]} {label}" for label in VERDICTS)
    counts += "".join(
        f" / {tally[label]} {label}"
        for label in ("error", "unparseable")
        if tally[label]
    )
    lines = [
        f"# Task granularity: {run_id}",
        "",
        f"{run['model']}, {run['prompt_ref']}, {len(judged)} tasks: {counts}",
        "",
        "## Composite",
        "",
    ]

    composites = [
        (task, granularity)
        for task, granularity in judged
        if isinstance(granularity, dict) and granularity["verdict"] == "composite"
    ]
    if not composites:
        lines += ["None.", ""]
    for task, granularity in composites:
        task_label = task_labels.get(task["id"], task["id"])
        lines += [f"### {task_label}", ""]
        lines += _blockquote(task)
        lines += ["", f"Split into {len(granularity['parts'])}:", ""]
        for number, part in enumerate(granularity["parts"], 1):
            part_label = (
                f"{task_label} part {number}" if task["id"] in task_labels else None
            )
            lines += _part(number, part, part_label)
            lines.append("")

    lines += ["## Unsure", ""]
    unsure = [
        task
        for task, granularity in judged
        if isinstance(granularity, dict) and granularity["verdict"] == "unsure"
    ]
    if not unsure:
        lines += ["None.", ""]
    for task in unsure:
        lines += [f"### {task_labels.get(task['id'], task['id'])}", ""]
        lines += _blockquote(task)
        lines.append("")

    lines += ["## Single", ""]
    singles = [
        task
        for task, granularity in judged
        if isinstance(granularity, dict) and granularity["verdict"] == "single"
    ]
    if singles:
        lines += [
            f"- {task_labels.get(task['id'], task['id'])}:"
            f" {' '.join(task['body'].split())}"
            for task in singles
        ]
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
    run_id: str,
    gen_runs: list[str],
    reports_dir: Path | None = None,
    revision_run: str | None = None,
    passages_from: list[str] | None = None,
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"task-granularity-{run_id}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_run(
            conn,
            run_id,
            gen_runs,
            revision_run=revision_run,
            passages_from=passages_from,
        )
    )
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="universe.task_granularity_report", description=__doc__
    )
    parser.add_argument("run_id")
    parser.add_argument(
        "--gen-runs",
        required=True,
        type=id_list,
        help="comma-separated task-generation run ids used by the granularity run",
    )
    parser.add_argument(
        "--revision-run",
        help="task-revision run id used by the granularity run",
    )
    parser.add_argument(
        "--passages-from",
        type=id_list,
        help="comma-separated cuts run ids used to select the labeled task chain",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    with connect() as conn:
        print(
            write_report(
                conn,
                args.run_id,
                args.gen_runs,
                revision_run=args.revision_run,
                passages_from=args.passages_from,
            )
        )


if __name__ == "__main__":
    main()
