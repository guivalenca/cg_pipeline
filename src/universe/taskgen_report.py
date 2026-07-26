"""Read task-generation runs back side by side, a passage at a time.

    python -m universe.taskgen_report r0046 r0047 r0048

The overview table counts tasks per passage per run, so volume differences
between models are visible before reading anything. The body then walks the
passages in reading order: the passage text first, then every run's tasks
under it, so judging whether the tasks fit the passage never needs a scroll
to somewhere else.
"""

import argparse
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run
from universe.passage_report import thinking_label
from universe.passages import fetch_passages, passage_text
from universe.taskgen import tasks_of
from universe.triage_report import cell, short_label

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def count_label(tasks: list[dict] | str) -> str:
    return str(len(tasks)) if isinstance(tasks, list) else tasks


def collect(conn: psycopg.Connection, run_ids: list[str]) -> tuple[list[dict], dict]:
    """Each run with its label, and every (run, passage) task list."""
    runs, results = [], {}
    for run_id in run_ids:
        run = fetch_run(conn, run_id)
        version = run["prompt_ref"].rsplit("/", 1)[-1]
        runs.append(
            {
                "id": run_id,
                "label": f"{run['model']} {version} ({thinking_label(run['params'])})",
            }
        )
        for item in fetch_items(conn, run_id):
            if not item["passage_id"]:
                raise SystemExit(
                    f"{run_id} is not a task-generation run: item {item['id']} is about"
                    " a whole artifact, not a passage"
                )
            results[(run_id, item["passage_id"])] = tasks_of(item)
    return runs, results


def render_runs(conn: psycopg.Connection, run_ids: list[str]) -> str:
    runs, results = collect(conn, run_ids)
    passage_ids = sorted({passage_id for _, passage_id in results})
    passages = fetch_passages(conn, passage_ids)
    texts = {passage["id"]: passage_text(conn, passage) for passage in passages}

    header = "| passage | " + " | ".join(run["id"] for run in runs) + " |"
    lines = [f"# Task generation: {', '.join(run_ids)}", ""]
    lines += [f"- {run['id']}: {run['label']}" for run in runs]
    lines += ["", f"{len(passages)} passage(s), {len(runs)} run(s). Cells count tasks.", ""]
    lines += [header, "| - " * (len(runs) + 1) + "|"]
    for passage in passages:
        row = [cell(short_label(passage, texts[passage["id"]]))]
        row += [
            cell(count_label(results.get((run["id"], passage["id"]), "-"))) for run in runs
        ]
        lines.append("| " + " | ".join(row) + " |")
    totals = [
        str(
            sum(
                len(tasks)
                for (run_id, _), tasks in results.items()
                if run_id == run["id"] and isinstance(tasks, list)
            )
        )
        for run in runs
    ]
    lines.append("| " + " | ".join(["total"] + totals) + " |")

    lines += ["", "## The passages and their tasks", ""]
    for passage in passages:
        counted = ", ".join(
            f"{run['id']} {count_label(results.get((run['id'], passage['id']), '-'))}"
            for run in runs
        )
        span = (
            f"block {passage['first_seq']}"
            if passage["first_seq"] == passage["last_seq"]
            else f"blocks {passage['first_seq']} to {passage['last_seq']}"
        )
        lines += [f"### {span} ({counted})", "", f"`{passage['id']}`", ""]
        lines += [texts[passage["id"]], ""]
        for run in runs:
            tasks = results.get((run["id"], passage["id"]))
            if tasks is None:
                continue
            lines += [f"#### {run['id']}: {run['label']}", ""]
            if not isinstance(tasks, list):
                lines += [f"({tasks})", ""]
                continue
            for number, entry in enumerate(tasks, 1):
                lines += [f"{number}. {entry['task']}", f"   - {entry['answer']}"]
            lines.append("")
    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection, run_ids: list[str], reports_dir: Path | None = None
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"task-generation-{'-'.join(run_ids)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_runs(conn, run_ids))
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.taskgen_report", description=__doc__)
    parser.add_argument("run_ids", nargs="+")
    args = parser.parse_args(argv)
    with connect() as conn:
        print(write_report(conn, args.run_ids))


if __name__ == "__main__":
    main()
