"""Read task-generation runs back side by side, a passage at a time.

    python -m universe.taskgen_report r0046 r0047 r0048
    python -m universe.taskgen_report r0046 r0047 --passages-from r0017

The overview table counts tasks per passage per run, so volume differences
between models are visible before reading anything. The body then walks the
passages in reading order, grouping runs by the exact raw or revised state
their items read. Each task list therefore sits under its actual input body.

`--passages-from` narrows the report to the passages certain cuts runs drew,
which is how one generation run over a union of divisions is read back as
one report per division, without the divisions ever costing separate calls.
"""

import argparse
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run, id_list
from universe.passage_report import passage_state_text, thinking_label
from universe.passages import fetch_passages, fetch_passages_for_runs
from universe.taskgen import tasks_of
from universe.triage_report import cell, short_label

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def count_label(tasks: list[dict] | str) -> str:
    return str(len(tasks)) if isinstance(tasks, list) else tasks


def collect(conn: psycopg.Connection, run_ids: list[str]) -> tuple[list[dict], dict]:
    """Each run and every task list with the exact passage state it read."""
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
            results[(run_id, item["passage_id"])] = {
                "tasks": tasks_of(item),
                "revision_id": item["passage_revision_id"],
            }
    return runs, results


def render_runs(
    conn: psycopg.Connection, run_ids: list[str], passages_from: list[str] | None = None
) -> str:
    runs, results = collect(conn, run_ids)
    passage_ids = sorted({passage_id for _, passage_id in results})
    if passages_from:
        drawn = {p["id"] for p in fetch_passages_for_runs(conn, passages_from)}
        passage_ids = [passage_id for passage_id in passage_ids if passage_id in drawn]
        if not passage_ids:
            raise SystemExit(
                f"no passage of {', '.join(run_ids)} was drawn by {', '.join(passages_from)}"
            )
    passages = fetch_passages(conn, passage_ids)
    passage_by_id = {passage["id"]: passage for passage in passages}
    states = {
        (passage_id, result["revision_id"])
        for (_, passage_id), result in results.items()
        if passage_id in passage_ids
    }
    texts = {
        key: passage_state_text(conn, passage_by_id[key[0]], key[1])
        for key in states
    }

    header = "| passage | " + " | ".join(run["id"] for run in runs) + " |"
    title = f"# Task generation: {', '.join(run_ids)}"
    if passages_from:
        title += f" (passages of {', '.join(passages_from)})"
    lines = [title, ""]
    lines += [f"- {run['id']}: {run['label']}" for run in runs]
    lines += ["", f"{len(passages)} passage(s), {len(runs)} run(s). Cells count tasks.", ""]
    lines += [header, "| - " * (len(runs) + 1) + "|"]
    for passage in passages:
        available = [
            results[(run["id"], passage["id"])]
            for run in runs
            if (run["id"], passage["id"]) in results
        ]
        opening_state = available[0]["revision_id"]
        row = [cell(short_label(passage, texts[(passage["id"], opening_state)]))]
        row += [
            cell(
                count_label(
                    results.get((run["id"], passage["id"]), {}).get(
                        "tasks", "-"
                    )
                )
            )
            for run in runs
        ]
        lines.append("| " + " | ".join(row) + " |")
    # Totals honour the same cut as the rows: only the passages on display.
    shown = set(passage_ids)
    totals = [
        str(
            sum(
                len(result["tasks"])
                for (run_id, passage_id), result in results.items()
                if run_id == run["id"]
                and passage_id in shown
                and isinstance(result["tasks"], list)
            )
        )
        for run in runs
    ]
    lines.append("| " + " | ".join(["total"] + totals) + " |")

    lines += ["", "## The passages and their tasks", ""]
    for passage in passages:
        span = (
            f"block {passage['first_seq']}"
            if passage["first_seq"] == passage["last_seq"]
            else f"blocks {passage['first_seq']} to {passage['last_seq']}"
        )
        grouped: dict[str | None, list[tuple[dict, dict]]] = {}
        for run in runs:
            result = results.get((run["id"], passage["id"]))
            if result is not None:
                grouped.setdefault(result["revision_id"], []).append((run, result))
        for revision_id, entries in grouped.items():
            counted = ", ".join(
                f"{run['id']} {count_label(result['tasks'])}"
                for run, result in entries
            )
            lines += [f"### {span} ({counted})", "", f"`{passage['id']}`", ""]
            if revision_id is not None:
                lines += [f"revision: `{revision_id}`", ""]
            lines += [texts[(passage["id"], revision_id)], ""]
            for run, result in entries:
                tasks = result["tasks"]
                lines += [f"#### {run['id']}: {run['label']}", ""]
                if not isinstance(tasks, list):
                    lines += [f"({tasks})", ""]
                    continue
                for number, entry in enumerate(tasks, 1):
                    lines += [
                        f"{number}. {entry['task']}",
                        f"   - {entry['answer']}",
                    ]
                lines.append("")
    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection,
    run_ids: list[str],
    reports_dir: Path | None = None,
    passages_from: list[str] | None = None,
) -> Path:
    name = f"task-generation-{'-'.join(run_ids)}"
    if passages_from:
        name += f"-of-{'-'.join(passages_from)}"
    path = (reports_dir or REPORTS_DIR) / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_runs(conn, run_ids, passages_from))
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.taskgen_report", description=__doc__)
    parser.add_argument("run_ids", nargs="+")
    parser.add_argument(
        "--passages-from",
        type=id_list,
        help="comma-separated cuts run ids; only their passages enter the report",
    )
    args = parser.parse_args(argv)
    with connect() as conn:
        print(write_report(conn, args.run_ids, passages_from=args.passages_from))


if __name__ == "__main__":
    main()
