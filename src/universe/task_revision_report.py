"""Read task-revision runs back side by side, a task at a time.

    python -m universe.task_revision_report r0057 r0058

The overview table counts verdicts per run, so how much each model wanted
to touch is visible before reading anything. The body then walks the tasks
in passage order: the original task and its answer first, then every run's
verdict and rewrite under it, so judging a rewrite never needs a scroll.
"""

import argparse
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run
from universe.passage_report import thinking_label
from universe.passages import fetch_passages
from universe.task_revision import STAGE, VERDICTS, revision_of
from universe.tasks import fetch_tasks

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def collect(conn: psycopg.Connection, run_ids: list[str]) -> tuple[list[dict], dict]:
    """Each run with its label, and every (run, task) revision."""
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


def render_runs(conn: psycopg.Connection, run_ids: list[str]) -> str:
    runs, results = collect(conn, run_ids)
    task_ids = sorted({task_id for _, task_id in results})
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
        lines += [f"**{number}. {task['body']}**", "", f"- answer: {task['answer']}"]
        for run in runs:
            revision = results.get((run["id"], task["id"]))
            if revision is None:
                continue
            if not isinstance(revision, dict):
                lines.append(f"- {run['id']}: ({revision})")
            elif revision["verdict"] == "rewritten":
                lines.append(f"- {run['id']}: rewritten to: {revision['task']}")
            else:
                lines.append(f"- {run['id']}: {revision['verdict']}")
        lines.append("")
    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection, run_ids: list[str], reports_dir: Path | None = None
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"task-revision-{'-'.join(run_ids)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_runs(conn, run_ids))
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.task_revision_report", description=__doc__)
    parser.add_argument("run_ids", nargs="+")
    args = parser.parse_args(argv)
    with connect() as conn:
        print(write_report(conn, args.run_ids))


if __name__ == "__main__":
    main()
