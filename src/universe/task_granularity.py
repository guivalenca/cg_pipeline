"""Judge whether each learner task is one task, with no source in the call.

    python -m universe.task_granularity run --prompt v001 \
        --model deepseek-v4-pro --gen-runs r0052 \
        --tool prompts/task-granularity/tool-v001.json

One call per task, carrying only the task and its expected answer. Granularity
belongs to what the learner is asked to do, not to the source it came from:
including that source would add context the learner does not need and could
blur whether the task itself packs independently answerable demands. Composite
tasks are split in the verdict stored on the run item; the original task row
remains insert-only.
"""

import argparse
import json

import psycopg

from universe import report
from universe.db import connect
from universe.harness import (
    Target,
    execute,
    fetch_items,
    fetch_run,
    fetch_sources,
    id_list,
    json_object,
    load_prompt,
    load_tool,
    positive_int,
)
from universe.model_client import DEFAULT_MAX_TOKENS, ModelClient
from universe.passages import fetch_passages_for_runs
from universe.task_triage import apply_revisions, fetch_revisions
from universe.tasks import fetch_tasks, fetch_tasks_for_runs, materialize, task_id

STAGE = "task-granularity"
VERDICTS = ("single", "composite", "unsure")
DEFAULT_WORKERS = 4


def granularity_of(item: dict) -> dict | str:
    """The verdict and split parts the item reported, or why there is none."""
    if item["error"]:
        return "error"
    try:
        parsed = json.loads(item["response"])
    except (TypeError, json.JSONDecodeError):
        return "unparseable"
    if not isinstance(parsed, dict) or parsed.get("verdict") not in VERDICTS:
        return "unparseable"
    if parsed["verdict"] != "composite":
        return {"verdict": parsed["verdict"], "parts": None}
    parts = parsed.get("parts")
    if not (
        isinstance(parts, list)
        and parts
        and all(
            isinstance(part, dict)
            and isinstance(part.get("task"), str)
            and part["task"].strip()
            and isinstance(part.get("answer"), str)
            and part["answer"].strip()
            for part in parts
        )
    ):
        return "unparseable"
    return {
        "verdict": "composite",
        "parts": [{"task": part["task"], "answer": part["answer"]} for part in parts],
    }


def materialize_parts(conn: psycopg.Connection, run_id: str) -> dict:
    """Write the task rows implied by a task-granularity run's splits."""
    run = fetch_run(conn, run_id)
    if run["stage"] != STAGE:
        raise SystemExit(f"{run_id} is a {run['stage']} run, not {STAGE}")

    counts = {"tasks_new": 0, "tasks_existing": 0}
    for item in fetch_items(conn, run_id):
        if item["error"]:
            raise SystemExit(f"{item['id']} failed and has no parts: {item['error']}")
        granularity = granularity_of(item)
        if not isinstance(granularity, dict):
            raise SystemExit(
                f"{item['id']} did not report usable granularity: {granularity}"
            )
        if granularity["verdict"] != "composite":
            continue

        parents = fetch_tasks(conn, [item["task_id"]])
        if len(parents) != 1:
            raise SystemExit(f"{item['id']} names unknown parent task {item['task_id']}")
        for seq, part in enumerate(granularity["parts"], 1):
            written = conn.execute(
                "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
                " VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (
                    task_id(item["id"], seq),
                    item["id"],
                    parents[0]["passage_id"],
                    seq,
                    part["task"],
                    part["answer"],
                ),
            ).rowcount
            counts["tasks_new" if written else "tasks_existing"] += 1
    conn.commit()
    return counts


def build_targets(conn: psycopg.Connection, tasks: list[dict]) -> list[Target]:
    """One target per task: nothing but the task and its answer in the call."""
    sources = fetch_sources(conn, sorted({t["artifact_id"] for t in tasks}))
    targets = []
    for task in tasks:
        source_id, title = sources[task["artifact_id"]]
        targets.append(
            Target(
                source_id,
                title,
                task["artifact_id"],
                task["body"],
                task_id=task["id"],
                extra_fields={"task": task["body"], "answer": task["answer"]},
            )
        )
    return targets


def cmd_run(args: argparse.Namespace) -> None:
    prompt = load_prompt(STAGE, args.prompt, require_body=False)
    extra = dict(load_tool(args.tool)) if args.tool else {}
    extra.update(args.extra or {})
    with connect() as conn:
        for run_id in args.gen_runs:
            counts = materialize(conn, run_id)
            print(
                f"{run_id}: {counts['tasks_new']} new task(s),"
                f" {counts['tasks_existing']} already known"
            )
        tasks = fetch_tasks_for_runs(conn, args.gen_runs)
        if args.passages_from:
            drawn = {p["id"] for p in fetch_passages_for_runs(conn, args.passages_from)}
            outside = sum(1 for t in tasks if t["passage_id"] not in drawn)
            tasks = [t for t in tasks if t["passage_id"] in drawn]
            print(
                f"{outside} task(s) outside the passages of"
                f" {', '.join(args.passages_from)}, skipped"
            )
        if args.revision_run:
            revisions = fetch_revisions(conn, args.revision_run)
            tasks, dropped, unjudged = apply_revisions(tasks, revisions)
            if unjudged:
                names = ", ".join(t["id"] for t in unjudged)
                raise SystemExit(
                    f"{len(unjudged)} task(s) have no usable revision in"
                    f" {args.revision_run}: {names}; silence is not a verdict"
                )
            rewritten = sum(
                1
                for task in tasks
                if isinstance(revisions[task["id"]], dict)
                and revisions[task["id"]]["verdict"] == "rewritten"
            )
            bodies = "body was" if rewritten == 1 else "bodies were"
            print(
                f"{args.revision_run}: {len(dropped)} task(s) dropped as unfixable,"
                f" {rewritten} task {bodies} swapped by rewrites"
            )
        if not tasks:
            raise SystemExit(f"no tasks from {', '.join(args.gen_runs)}")

        targets = build_targets(conn, tasks)
        client = ModelClient(
            args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            extra=extra or None,
        )
        print(
            f"{prompt.ref} ({prompt.sha[:12]}) on {len(targets)} task(s)"
            f" via {args.model}, {args.workers} at a time"
        )
        summary = execute(
            conn, prompt, client, targets, workers=args.workers,
            run_params={"gen_runs": args.gen_runs, "passages_from": args.passages_from, "revision_run": args.revision_run},
        )
        items = fetch_items(conn, summary["run_id"])

    verdicts = [granularity_of(item) for item in items]
    tally = {
        label: sum(
            1
            for verdict in verdicts
            if (verdict["verdict"] if isinstance(verdict, dict) else verdict) == label
        )
        for label in VERDICTS + ("error", "unparseable")
    }
    counted = ", ".join(f"{count} {label}" for label, count in tally.items() if count)
    parts = sum(
        len(verdict["parts"])
        for verdict in verdicts
        if isinstance(verdict, dict) and verdict["verdict"] == "composite"
    )
    split = f", {parts} part(s) produced" if tally["composite"] else ""
    usage = report.aggregate_usage(items)
    duration = sum(item["duration_ms"] or 0 for item in items)
    print(
        f"{summary['run_id']} {summary['status']}:"
        f" {counted or 'nothing reported'}{split},"
        f" {report.format_usage(usage) or 'no usage reported'},"
        f" {duration / 1000:.1f}s of model time"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.task_granularity", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="judge and split every task on its own")
    run.add_argument("--prompt", required=True, help="prompt version, e.g. v001")
    run.add_argument("--model", required=True)
    run.add_argument(
        "--gen-runs", required=True, type=id_list, help="comma-separated task-generation run ids"
    )
    run.add_argument(
        "--tool",
        required=True,
        help="path to a tool definition JSON; every call is forced through it",
    )
    run.add_argument(
        "--passages-from",
        type=id_list,
        help="comma-separated cuts run ids; only tasks of their passages get calls",
    )
    run.add_argument(
        "--revision-run",
        help="task-revision run id; rewrites applied and unfixables dropped",
    )
    run.add_argument("--workers", type=positive_int, default=DEFAULT_WORKERS)
    run.add_argument("--temperature", type=float)
    run.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    run.add_argument(
        "--extra", type=json_object, help="extra JSON merged into the payload and stamped"
    )
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
