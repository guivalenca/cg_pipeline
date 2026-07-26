"""Read triage runs back as one matrix: a row per passage, a column per run.

    python -m universe.triage_report r0041 r0042

The point of the layout is disagreement. Every run that judged a passage sits
on the same line, so a passage the models split over is visible without
reading anything; the appendix then carries the passage in full, with those
verdicts repeated in its title, so the eye that stopped on a row can settle
the question there and then.

Rendered from the database, like every report here: the file is disposable and
the run rows are what keep.
"""

import argparse
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run
from universe.passage_report import thinking_label
from universe.passages import fetch_passages, passage_text
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
    """Each run with its column label, and every (run, passage) verdict."""
    runs, verdicts = [], {}
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
            verdicts[(run_id, item["passage_id"])] = verdict_of(item)
    return runs, verdicts


def render_runs(conn: psycopg.Connection, run_ids: list[str]) -> str:
    runs, verdicts = collect(conn, run_ids)
    passage_ids = sorted({passage_id for _, passage_id in verdicts})
    passages = fetch_passages(conn, passage_ids)
    texts = {passage["id"]: passage_text(conn, passage) for passage in passages}

    header = "| passage | " + " | ".join(run["id"] for run in runs) + " |"
    lines = [f"# Passage triage: {', '.join(run_ids)}", ""]
    lines += [f"- {run['id']}: {run['label']}" for run in runs]
    lines += ["", f"{len(passages)} passage(s), {len(runs)} run(s).", ""]
    lines += [header, "| - " * (len(runs) + 1) + "|"]
    for passage in passages:
        row = [cell(short_label(passage, texts[passage["id"]]))]
        row += [cell(verdicts.get((run["id"], passage["id"]), "-")) for run in runs]
        lines.append("| " + " | ".join(row) + " |")

    # Every verdict any run returned, so a run that invented one is visible.
    names = sorted({verdict for verdict in verdicts.values()})
    lines += ["", "## Verdicts per run", ""]
    lines += [header.replace("| passage |", "| verdict |"), "| - " * (len(runs) + 1) + "|"]
    for name in names:
        counts = [
            str(sum(1 for (run_id, _), v in verdicts.items() if run_id == run["id"] and v == name))
            for run in runs
        ]
        lines.append("| " + " | ".join([cell(name)] + counts) + " |")

    lines += ["", "## The passages", ""]
    for passage in passages:
        judged = ", ".join(
            f"{run['id']} {verdicts.get((run['id'], passage['id']), '-')}" for run in runs
        )
        span = (
            f"block {passage['first_seq']}"
            if passage["first_seq"] == passage["last_seq"]
            else f"blocks {passage['first_seq']} to {passage['last_seq']}"
        )
        lines += [f"### {span} ({judged})", "", f"`{passage['id']}`", "", texts[passage["id"]], ""]
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
