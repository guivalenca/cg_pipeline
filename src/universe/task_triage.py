"""Judge one task at a time against the whole source that produced it.

    python -m universe.task_triage run --prompt v001 --model deepseek-v4-pro \
        --gen-runs r0050,r0051 --tool prompts/task-triage/tool-v001.json

The generation runs named here are materialized first, so what this stage
judges are task rows. One call per task: the whole source, then the task and
its expected answer. The source text is byte for byte the same across every
task of an artifact, and the template puts it first, which is what lets the
provider's prefix cache hit; every per-passage and per-task stage shares that
same prefix discipline.

A task judged unsupported is not corrected, it is discarded downstream, the
same way triage discards filler passages: volume is free and rows are
insert-only, so the cure for a bad task is its absence.
"""

import argparse

import psycopg

from universe import report
from universe.db import connect
from universe.harness import (
    Target,
    execute,
    fetch_items,
    fetch_sources,
    id_list,
    json_object,
    load_prompt,
    load_tool,
    positive_int,
)
from universe.model_client import DEFAULT_MAX_TOKENS, ModelClient
from universe.passages import fetch_passages_for_runs, source_text
from universe.tasks import fetch_tasks_for_runs, materialize

STAGE = "task-triage"
DEFAULT_WORKERS = 4


def build_targets(conn: psycopg.Connection, tasks: list[dict]) -> list[Target]:
    """One target per task: the whole source as body, task and answer beside it."""
    sources = fetch_sources(conn, sorted({t["artifact_id"] for t in tasks}))
    bodies: dict[str, str] = {}
    targets = []
    for task in tasks:
        artifact_id = task["artifact_id"]
        if artifact_id not in bodies:
            bodies[artifact_id] = source_text(conn, artifact_id)
        source_id, title = sources[artifact_id]
        targets.append(
            Target(
                source_id,
                title,
                artifact_id,
                bodies[artifact_id],
                task_id=task["id"],
                extra_fields={"task": task["body"], "answer": task["answer"]},
            )
        )
    return targets


def cmd_run(args: argparse.Namespace) -> None:
    prompt = load_prompt(STAGE, args.prompt)
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
        summary = execute(conn, prompt, client, targets, workers=args.workers)
        items = fetch_items(conn, summary["run_id"])

    usage = report.aggregate_usage(items)
    duration = sum(item["duration_ms"] or 0 for item in items)
    print(
        f"{summary['run_id']} {summary['status']}:"
        f" {summary['ok']} ok, {summary['failed']} failed,"
        f" {report.format_usage(usage) or 'no usage reported'},"
        f" {duration / 1000:.1f}s of model time"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.task_triage", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="judge every task the generation runs produced")
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
