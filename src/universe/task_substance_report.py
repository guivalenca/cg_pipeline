"""Read task-substance runs side by side, comparing verdicts across runs.

    python -m universe.task_substance_report r0072 r0073 --gen-runs r0052 \
        --revision-run r0065 [--passages-from r0017]

Reconstructs the judged texts exactly as the runner does (applying
--passages-from filter and --revision-run overlay), then lays out
flagged tasks (trivial, unsure) side by side, with substantive tasks
listed compactly at the end.
"""

import argparse
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run, id_list
from universe.passages import fetch_passages_for_runs
from universe.task_substance import STAGE, VERDICTS, substance_of
from universe.task_triage import apply_revisions, fetch_revisions
from universe.tasks import fetch_tasks_for_runs, materialize

REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"


def verdict_label(substance: dict | str) -> str:
    return substance["verdict"] if isinstance(substance, dict) else substance


def render_runs(
    conn: psycopg.Connection,
    run_ids: list[str],
    gen_runs: list[str],
    revision_run: str | None = None,
    passages_from: list[str] | None = None,
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
        tally = {label: 0 for label in VERDICTS + ("error", "unparseable")}
        for (run_id, _), substance in results.items():
            if run_id == run["id"]:
                tally[verdict_label(substance)] += 1
        counts = [f"{tally[v]} {v}" for v in VERDICTS if tally[v]]
        errors = []
        if tally["error"]:
            errors.append(f"{tally['error']} error")
        if tally["unparseable"]:
            errors.append(f"{tally['unparseable']} unparseable")
        tally_str = ", ".join(counts + errors)
        lines.append(f"- {run['id']}: {run['model']}, {tally_str}")

    lines.append("")

    # Find flagged tasks: trivial and unsure
    trivial_tasks = set()
    unsure_tasks = set()
    for task_id in judged_task_ids:
        has_trivial = any(
            verdict_label(results.get((run["id"], task_id))) == "trivial"
            for run in runs
        )
        has_unsure = any(
            verdict_label(results.get((run["id"], task_id))) == "unsure"
            for run in runs
        )
        if has_trivial:
            trivial_tasks.add(task_id)
        elif has_unsure:
            unsure_tasks.add(task_id)

    # Section: Trivial tasks
    lines.append("## Trivial")
    lines.append("")
    if trivial_tasks:
        for task_id in sorted(trivial_tasks):
            task = task_dict[task_id]
            lines.append(f"### {task_id}")
            lines.append("")
            lines.append(f"> {task['body']}")
            lines.append(f">\n> {task['answer']}")
            lines.append("")
            for run in runs:
                verdict = verdict_label(results.get((run["id"], task_id)))
                lines.append(f"- {run['id']}: {verdict}")
            lines.append("")
    else:
        lines.append("None.")
        lines.append("")

    # Section: Unsure tasks (only if no trivial verdict for the task)
    lines.append("## Unsure")
    lines.append("")
    if unsure_tasks:
        for task_id in sorted(unsure_tasks):
            task = task_dict[task_id]
            lines.append(f"### {task_id}")
            lines.append("")
            lines.append(f"> {task['body']}")
            lines.append(f">\n> {task['answer']}")
            lines.append("")
            for run in runs:
                verdict = verdict_label(results.get((run["id"], task_id)))
                lines.append(f"- {run['id']}: {verdict}")
            lines.append("")
    else:
        lines.append("None.")
        lines.append("")

    # Section: Substantive everywhere
    lines.append("## Substantive everywhere")
    lines.append("")
    substantive_tasks = judged_task_ids - trivial_tasks - unsure_tasks
    if substantive_tasks:
        for task_id in sorted(substantive_tasks):
            task = task_dict[task_id]
            lines.append(f"- {task_id}: {task['body']}")
    else:
        lines.append("None.")
    lines.append("")

    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection,
    run_ids: list[str],
    gen_runs: list[str],
    revision_run: str | None = None,
    passages_from: list[str] | None = None,
    reports_dir: Path | None = None,
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"task-substance-{'-'.join(run_ids)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        render_runs(conn, run_ids, gen_runs, revision_run=revision_run, passages_from=passages_from)
    )
    return path


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.task_substance_report", description=__doc__)
    parser.add_argument("run_ids", nargs="+", help="task-substance run ids to compare")
    parser.add_argument("--gen-runs", type=id_list, required=True, help="task-generation run ids")
    parser.add_argument("--revision-run", help="task-revision run id for overlay")
    parser.add_argument(
        "--passages-from", type=id_list, help="comma-separated cuts run ids to filter by"
    )
    args = parser.parse_args(argv)
    with connect() as conn:
        print(write_report(conn, args.run_ids, args.gen_runs, args.revision_run, args.passages_from))


if __name__ == "__main__":
    main()
