"""Read triage runs back as one matrix: a row per passage, a column per run.

    python -m universe.triage_report r0041 r0042

The point of the layout is disagreement. Every run that judged a passage sits
on the same line, so a passage the models split over is visible without
reading anything. The appendix groups judgments by the exact raw or revised
state their run items addressed; two revisions of one passage are never shown
against one shared, misleading body.

Rendered from the database, like every report here: the file is disposable and
the run rows are what keep.
"""

import argparse
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run
from universe.passage_report import passage_state_text, thinking_label
from universe.passages import fetch_passages
from universe.triage import verdict_of

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
LABEL_WORDS = 8


def cell(text: str) -> str:
    """Table cells are one line and own no pipes."""
    return " ".join(text.split()).replace("|", "\\|")


def short_label(passage: dict, text: str) -> str:
    """The range, plus enough of the first block to recognise the passage."""
    opening = " ".join(text.split("\n\n", 1)[0].split()[:LABEL_WORDS])
    return f"{passage['first_seq']}-{passage['last_seq']} {opening}"


def collect(conn: psycopg.Connection, run_ids: list[str]) -> tuple[list[dict], dict]:
    """Each run and every decision, including the exact state it judged."""
    runs, decisions = [], {}
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
                    f"{run_id} is not a triage run: item {item['id']} is about a whole"
                    " artifact, not a passage"
                )
            decisions[(run_id, item["passage_id"])] = {
                "verdict": verdict_of(item),
                "revision_id": item["passage_revision_id"],
            }
    return runs, decisions


def render_runs(conn: psycopg.Connection, run_ids: list[str]) -> str:
    runs, decisions = collect(conn, run_ids)
    passage_ids = sorted({passage_id for _, passage_id in decisions})
    passages = fetch_passages(conn, passage_ids)
    passage_by_id = {passage["id"]: passage for passage in passages}
    states = {
        (passage_id, decision["revision_id"])
        for (_, passage_id), decision in decisions.items()
    }
    texts = {
        key: passage_state_text(conn, passage_by_id[key[0]], key[1])
        for key in states
    }

    header = "| passage | " + " | ".join(run["id"] for run in runs) + " |"
    lines = [f"# Passage triage: {', '.join(run_ids)}", ""]
    lines += [f"- {run['id']}: {run['label']}" for run in runs]
    lines += ["", f"{len(passages)} passage(s), {len(runs)} run(s).", ""]
    lines += [header, "| - " * (len(runs) + 1) + "|"]
    for passage in passages:
        available = [
            decisions[(run["id"], passage["id"])]
            for run in runs
            if (run["id"], passage["id"]) in decisions
        ]
        opening_state = available[0]["revision_id"]
        row = [cell(short_label(passage, texts[(passage["id"], opening_state)]))]
        row += [
            cell(
                decisions.get((run["id"], passage["id"]), {}).get(
                    "verdict", "-"
                )
            )
            for run in runs
        ]
        lines.append("| " + " | ".join(row) + " |")

    # Every verdict any run returned, so a run that invented one is visible.
    names = sorted({decision["verdict"] for decision in decisions.values()})
    lines += ["", "## Verdicts per run", ""]
    lines += [header.replace("| passage |", "| verdict |"), "| - " * (len(runs) + 1) + "|"]
    for name in names:
        counts = [
            str(
                sum(
                    1
                    for (run_id, _), decision in decisions.items()
                    if run_id == run["id"] and decision["verdict"] == name
                )
            )
            for run in runs
        ]
        lines.append("| " + " | ".join([cell(name)] + counts) + " |")

    lines += ["", "## The passages", ""]
    for passage in passages:
        span = (
            f"block {passage['first_seq']}"
            if passage["first_seq"] == passage["last_seq"]
            else f"blocks {passage['first_seq']} to {passage['last_seq']}"
        )
        grouped: dict[str | None, list[tuple[dict, dict]]] = {}
        for run in runs:
            decision = decisions.get((run["id"], passage["id"]))
            if decision is not None:
                grouped.setdefault(decision["revision_id"], []).append(
                    (run, decision)
                )
        for revision_id, entries in grouped.items():
            judged = ", ".join(
                f"{run['id']} {decision['verdict']}"
                for run, decision in entries
            )
            lines += [f"### {span} ({judged})", "", f"`{passage['id']}`", ""]
            if revision_id is not None:
                lines += [f"revision: `{revision_id}`", ""]
            lines += [texts[(passage["id"], revision_id)], ""]
    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection, run_ids: list[str], reports_dir: Path | None = None
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"passage-triage-{'-'.join(run_ids)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_runs(conn, run_ids))
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.triage_report", description=__doc__)
    parser.add_argument("run_ids", nargs="+")
    args = parser.parse_args(argv)
    with connect() as conn:
        print(write_report(conn, args.run_ids))


if __name__ == "__main__":
    main()
