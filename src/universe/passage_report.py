"""Render passage-cuts runs as the passages they imply, for human judgment.

    python -m universe.passage_report r0011 r0012 r0013 r0014

One markdown file per invocation, rendered from the database: each run's cuts
are applied to the artifact's blocks and every passage is shown in full. The
report also checks the cuts against the deterministic rules the model cannot
be trusted with: ascending, unique, inside the block range, first block never
a cut. Deviations are listed, then repaired for rendering so a sloppy but
usable answer can still be judged.
"""

import argparse
import json
from pathlib import Path

import psycopg

from universe.blocks import BLOCKER_VERSION, fetch_blocks
from universe.cuts import check_cuts, parse_cuts, passage_ranges, repair_cuts
from universe.db import connect
from universe.harness import fetch_items, fetch_run

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def thinking_label(params: dict) -> str:
    thinking = (params or {}).get("thinking", {}).get("type", "absent")
    effort = (params or {}).get("reasoning_effort")
    return f"thinking {thinking}" + (f", effort {effort}" if effort else "")


def render_runs(conn: psycopg.Connection, run_ids: list[str]) -> str:
    lines = [f"# Passage cuts: {', '.join(run_ids)}", ""]
    overview = [
        "| run | model | prompt | thinking | cuts | passages | problems |",
        "| - | - | - | - | - | - | - |",
    ]
    sections = []

    for run_id in run_ids:
        run = fetch_run(conn, run_id)
        version = run["prompt_ref"].rsplit("/", 1)[-1]
        for item in fetch_items(conn, run_id):
            title = f"{run_id} {run['model']} {version} ({thinking_label(run['params'])})"
            meta = f"| {run_id} | {run['model']} | {version} | {thinking_label(run['params'])}"
            if item["error"]:
                overview.append(f"{meta} | - | - | call failed |")
                sections += [f"## {title}", "", f"Call failed: `{item['error']}`", ""]
                continue

            blocks = fetch_blocks(conn, item["artifact_id"], BLOCKER_VERSION)
            seqs = [block["seq"] for block in blocks]
            by_seq = {block["seq"]: block for block in blocks}
            try:
                cuts = parse_cuts(item["response"])
            except (ValueError, json.JSONDecodeError) as exc:
                overview.append(f"{meta} | - | - | unparseable |")
                sections += [f"## {title}", "", f"Unparseable response: `{exc}`", "", f"```\n{item['response']}\n```", ""]
                continue

            problems = check_cuts(cuts, seqs)
            usable = repair_cuts(cuts, seqs)
            ranges = passage_ranges(usable, seqs)
            overview.append(
                f"{meta} | {len(cuts)} | {len(ranges)} | {'; '.join(problems) or 'none'} |"
            )

            sections += [f"## {title}", ""]
            sections += [f"- source: {item['source_id']}", f"- blocks: {len(seqs)}", f"- cuts as returned: {cuts}"]
            if problems:
                sections.append(f"- contract problems: {'; '.join(problems)} (repaired below)")
            sections.append("")
            for number, (first, last) in enumerate(ranges, start=1):
                span = f"block {first}" if first == last else f"blocks {first} to {last}"
                sections += [f"### Passage {number} ({span})", ""]
                for seq in range(first, last + 1):
                    sections += [by_seq[seq]["body"], ""]

    return "\n".join(lines + overview + [""] + sections)


def write_report(conn: psycopg.Connection, run_ids: list[str], reports_dir: Path | None = None) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"passage-cuts-{'-'.join(run_ids)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_runs(conn, run_ids))
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.passage_report", description=__doc__)
    parser.add_argument("run_ids", nargs="+")
    args = parser.parse_args(argv)
    with connect() as conn:
        print(write_report(conn, args.run_ids))


if __name__ == "__main__":
    main()
