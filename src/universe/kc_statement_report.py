"""Read kc-statement runs side by side as learner knowledge statements.

    python -m universe.kc_statement_report r0097 --gen-runs r0052 \
        --granularity-run r0093 --revision-run r0094 --triage-run r0095 \
        --substance-run r0096

Reconstructs the selected task set exactly as the runner does, then lists
stated knowledge, unsure verdicts, and unusable results in that order.
"""

import argparse
import sys
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run, id_list
from universe.kc_statement import STAGE, select_tasks, statement_of
from universe.task_labels import label_map

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def verdict_label(statement: dict | str) -> str:
    return statement["verdict"] if isinstance(statement, dict) else statement


def _task(task: dict) -> list[str]:
    lines = ["> **Task:**"]
    lines += [f"> {line}" if line else ">" for line in task["body"].splitlines()]
    lines += [">", "> **Answer:**"]
    lines += [f"> {line}" if line else ">" for line in task["answer"].splitlines()]
    return lines


def render_runs(
    conn: psycopg.Connection,
    run_ids: list[str],
    gen_runs: list[str],
    revision_run: str | None = None,
    passages_from: list[str] | None = None,
    granularity_run: str | None = None,
    parts_revision_run: str | None = None,
    triage_run: str | None = None,
    substance_run: str | None = None,
) -> str:
    """Render statements from runs over the runner's reconstructed task set."""
    selection_args = argparse.Namespace(
        gen_runs=gen_runs,
        revision_run=revision_run,
        passages_from=passages_from,
        granularity_run=granularity_run,
        parts_revision_run=parts_revision_run,
        triage_run=triage_run,
        substance_run=substance_run,
    )
    tasks = select_tasks(conn, selection_args)
    judged_task_ids = {task["id"] for task in tasks}
    task_labels = (
        label_map(
            conn,
            tasks,
            gen_runs,
            [granularity_run] if granularity_run else None,
        )
        if passages_from and revision_run
        else {}
    )

    runs = []
    results = {}
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
            results[(run_id, item["task_id"])] = statement_of(item)
        if run_task_ids != judged_task_ids:
            missing = judged_task_ids - run_task_ids
            extra = run_task_ids - judged_task_ids
            message = f"{run_id}: task_id mismatch."
            if missing:
                message += f" Missing: {', '.join(sorted(missing))}."
            if extra:
                message += f" Extra: {', '.join(sorted(extra))}."
            raise SystemExit(message)

    lines = [f"# KC statements: {', '.join(run_ids)}", ""]
    for run in runs:
        labels = [
            verdict_label(results[(run["id"], task_id)])
            for task_id in judged_task_ids
        ]
        tally = {label: labels.count(label) for label in set(labels)}
        counts = ", ".join(f"{tally[label]} {label}" for label in sorted(tally))
        lines.append(f"- {run['id']}: {run['model']}, {counts}")
    lines.append("")

    lines += ["## Stated", ""]
    stated = [
        task
        for task in tasks
        if any(
            verdict_label(results[(run["id"], task["id"])]) == "stated"
            for run in runs
        )
    ]
    if not stated:
        lines += ["None.", ""]
    for task in stated:
        lines += [f"### {task_labels.get(task['id'], task['id'])}", ""]
        lines += _task(task)
        lines.append("")
        for run in runs:
            statement = results[(run["id"], task["id"])]
            if isinstance(statement, dict) and statement["verdict"] == "stated":
                lines.append(f"- {run['id']}: {statement['statement']}")
        lines.append("")

    lines += ["## Unsure", ""]
    unsure = [
        task
        for task in tasks
        if any(
            verdict_label(results[(run["id"], task["id"])]) == "unsure"
            for run in runs
        )
    ]
    if not unsure:
        lines += ["None.", ""]
    for task in unsure:
        lines += [f"### {task_labels.get(task['id'], task['id'])}", ""]
        lines += _task(task)
        lines.append("")
        for run in runs:
            statement = results[(run["id"], task["id"])]
            if isinstance(statement, dict) and statement["verdict"] == "unsure":
                reason = statement.get("reason", "No reason reported.")
                lines.append(f"- {run['id']}: {reason}")
        lines.append("")

    lines += ["## Errored or unparseable", ""]
    unusable = [
        task
        for task in tasks
        if any(
            verdict_label(results[(run["id"], task["id"])])
            in {"error", "unparseable"}
            for run in runs
        )
    ]
    if not unusable:
        lines += ["None.", ""]
    for task in unusable:
        lines += [f"### {task_labels.get(task['id'], task['id'])}", ""]
        lines += _task(task)
        lines.append("")
        for run in runs:
            statement = results[(run["id"], task["id"])]
            if verdict_label(statement) in {"error", "unparseable"}:
                lines.append(f"- {run['id']}: {verdict_label(statement)}")
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
    triage_run: str | None = None,
    substance_run: str | None = None,
    reports_dir: Path | None = None,
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"kc-statement-{'-'.join(run_ids)}.md"
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
            triage_run=triage_run,
            substance_run=substance_run,
        )
    )
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="universe.kc_statement_report", description=__doc__
    )
    parser.add_argument("run_ids", nargs="+", help="kc-statement run ids to compare")
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
        "--triage-run",
        help="task-triage run id; keep only tasks it judged supported",
    )
    parser.add_argument(
        "--substance-run",
        help="task-substance run id; drop tasks it judged non-substantive",
    )
    parser.add_argument(
        "--passages-from", type=id_list, help="comma-separated cuts run ids to filter by"
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
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
                triage_run=args.triage_run,
                substance_run=args.substance_run,
            ),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
