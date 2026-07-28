"""Read task-revision runs back side by side, a task at a time.

    python -m universe.task_revision_report r0057 r0058

The overview table counts verdicts per run, so how much each model wanted
to touch is visible before reading anything. The body then walks the tasks
in passage order: the original task and its answer first, then every run's
verdict and rewrite under it, so judging a rewrite never needs a scroll.
"""

import argparse
import sys
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run, id_list
from universe.passage_report import thinking_label
from universe.passages import fetch_passages
from universe.task_granularity import materialize_parts
from universe.task_labels import label_map
from universe.task_revision import STAGE, VERDICTS, revision_of
from universe.tasks import fetch_tasks

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def collect(
    conn: psycopg.Connection,
    run_ids: list[str],
    granularity_runs: list[str] | None = None,
) -> tuple[list[dict], dict]:
    """Each run with its label, and every (run, task) revision."""
    for granularity_run in granularity_runs or []:
        materialize_parts(conn, granularity_run)

    runs, results = [], {}
    for run_id in run_ids:
        run = fetch_run(conn, run_id)
        if run["stage"] != STAGE:
            raise SystemExit(f"{run_id} is a {run['stage']} run, not {STAGE}")
        version = run["prompt_ref"].rsplit("/", 1)[-1]
        runs.append(
            {
                "id": run_id,
                "label": f"{run['model']} {version} ({thinking_label(run['params'])})",
            }
        )
        for item in fetch_items(conn, run_id):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            results[(run_id, item["task_id"])] = revision_of(item)
    return runs, results


def verdict_label(revision: dict | str) -> str:
    return revision["verdict"] if isinstance(revision, dict) else revision


def render_runs(
    conn: psycopg.Connection,
    run_ids: list[str],
    granularity_runs: list[str] | None = None,
    gen_runs: list[str] | None = None,
    passages_from: list[str] | None = None,
    revision_run: str | None = None,
) -> str:
    runs, results = collect(conn, run_ids, granularity_runs)
    task_labels = (
        label_map(conn, gen_runs, passages_from, revision_run, granularity_runs)
        if gen_runs and passages_from and revision_run
        else {}
    )
    task_ids_by_run = {
        run["id"]: {task_id for run_id, task_id in results if run_id == run["id"]}
        for run in runs
    }
    expected_task_ids = task_ids_by_run[runs[0]["id"]]
    for run in runs[1:]:
        actual_task_ids = task_ids_by_run[run["id"]]
        if actual_task_ids != expected_task_ids:
            missing = expected_task_ids - actual_task_ids
            extra = actual_task_ids - expected_task_ids
            msg = f"{run['id']}: task_id mismatch."
            if missing:
                msg += f" Missing: {', '.join(sorted(missing))}."
            if extra:
                msg += f" Extra: {', '.join(sorted(extra))}."
            raise SystemExit(msg)
    task_ids = sorted(expected_task_ids)
    tasks = fetch_tasks(conn, task_ids)
    passages = {p["id"]: p for p in fetch_passages(conn, sorted({t["passage_id"] for t in tasks}))}

    lines = [f"# Task revision: {', '.join(run_ids)}", ""]
    lines += [f"- {run['id']}: {run['label']}" for run in runs]
    lines += ["", f"{len(tasks)} task(s), {len(runs)} run(s).", ""]
    labels = list(VERDICTS) + ["error", "unparseable"]
    lines += ["| run | " + " | ".join(labels) + " |", "| - " * (len(labels) + 1) + "|"]
    for run in runs:
        tally = {label: 0 for label in labels}
        for (run_id, _), revision in results.items():
            if run_id == run["id"]:
                tally[verdict_label(revision)] += 1
        lines.append(
            "| " + " | ".join([run["id"]] + [str(tally[label]) for label in labels]) + " |"
        )

    lines += ["", "## The tasks and their revisions", ""]
    seen_passage = None
    for number, task in enumerate(tasks, 1):
        if task["passage_id"] != seen_passage:
            seen_passage = task["passage_id"]
            passage = passages[task["passage_id"]]
            span = (
                f"block {passage['first_seq']}"
                if passage["first_seq"] == passage["last_seq"]
                else f"blocks {passage['first_seq']} to {passage['last_seq']}"
            )
            lines += [f"### {span}", ""]
        task_label = task_labels.get(task["id"])
        heading = (
            f"{task_label}: {task['body']}"
            if task_label
            else f"{number}. {task['body']}"
        )
        lines += [f"**{heading}**", "", f"- answer: {task['answer']}"]
        for run in runs:
            revision = results.get((run["id"], task["id"]))
            if not isinstance(revision, dict):
                lines.append(f"- {run['id']}: ({revision})")
            elif revision["verdict"] == "rewritten":
                lines.append(f"- {run['id']}: rewritten to: {revision['task']}")
            else:
                lines.append(f"- {run['id']}: {revision['verdict']}")
        lines.append("")
    if task_labels:
        lines += ["## Label map", ""]
        lines += [f"- {label} = {task_id}" for task_id, label in task_labels.items()]
        lines.append("")
    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection,
    run_ids: list[str],
    reports_dir: Path | None = None,
    granularity_runs: list[str] | None = None,
    gen_runs: list[str] | None = None,
    passages_from: list[str] | None = None,
    revision_run: str | None = None,
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"task-revision-{'-'.join(run_ids)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_runs(
            conn,
            run_ids,
            granularity_runs,
            gen_runs=gen_runs,
            passages_from=passages_from,
            revision_run=revision_run,
        )
    )
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.task_revision_report", description=__doc__)
    parser.add_argument("run_ids", nargs="+")
    parser.add_argument(
        "--granularity-run",
        "--granularity-runs",
        dest="granularity_runs",
        type=id_list,
        help="task-granularity run ids whose materialized parts were revised",
    )
    parser.add_argument(
        "--gen-runs",
        type=id_list,
        help="comma-separated generation run ids for chain-relative labels",
    )
    parser.add_argument(
        "--passages-from",
        type=id_list,
        help="comma-separated cuts run ids for chain-relative labels",
    )
    parser.add_argument(
        "--revision-run",
        help="base task-revision run id for chain-relative labels",
    )
    parser.add_argument(
        "--parts-revision-run",
        help="parts revision run id; must also be one of the reported run ids",
    )
    parser.add_argument("--output-dir", type=Path, help="directory for the report")
    args = parser.parse_args(argv)
    if args.parts_revision_run and args.parts_revision_run not in args.run_ids:
        parser.error("--parts-revision-run must be one of the reported run ids")
    with connect() as conn:
        print(
            write_report(
                conn,
                args.run_ids,
                reports_dir=args.output_dir,
                granularity_runs=args.granularity_runs,
                gen_runs=args.gen_runs,
                passages_from=args.passages_from,
                revision_run=args.revision_run,
            ),
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
