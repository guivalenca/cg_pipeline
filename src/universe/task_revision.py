"""Judge each task alone, the way the learner will meet it: no source in the call.

    python -m universe.task_revision run --prompt v004 --model deepseek-v4-pro \
        --gen-runs r0052 --tool prompts/task-revision/tool-v003.json

One call per task, carrying only the task and its expected answer. A task
that points at a text it cannot show fails that reading; the model rewrites
it with the smallest change that makes it stand, or declares it unfixable
rather than guess the referent. Verdicts and rewrites live in the run items,
the same way triage verdicts do: a revision annotates an existing task, it
does not create a new entity.
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
    fetch_sources,
    id_list,
    json_object,
    load_prompt,
    load_tool,
    positive_int,
)
from universe.model_client import DEFAULT_MAX_TOKENS, ModelClient
from universe.passages import fetch_passages_for_runs
from universe.post_split import tasks as post_split_tasks
from universe.tasks import materialize

STAGE = "task-revision"
VERDICTS = ("stands", "rewritten", "unfixable")
DEFAULT_WORKERS = 16


def revision_of(item: dict) -> dict | str:
    """The verdict and rewrite the item reported, or the reason there is none."""
    if item["error"]:
        return "error"
    try:
        parsed = json.loads(item["response"])
    except (TypeError, json.JSONDecodeError):
        return "unparseable"
    if not isinstance(parsed, dict) or parsed.get("verdict") not in VERDICTS:
        return "unparseable"
    rewrite = parsed.get("task")
    if parsed["verdict"] == "rewritten" and not (isinstance(rewrite, str) and rewrite.strip()):
        return "unparseable"
    return {"verdict": parsed["verdict"], "task": rewrite if parsed["verdict"] == "rewritten" else None}


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
    gen_runs = args.gen_runs or []
    granularity_runs = args.granularity_runs or []
    if not gen_runs and not granularity_runs:
        raise SystemExit("at least one of --gen-runs or --granularity-runs is required")

    prompt = load_prompt(STAGE, args.prompt, require_body=False)
    extra = dict(load_tool(args.tool)) if args.tool else {}
    extra.update(args.extra or {})
    with connect() as conn:
        for run_id in gen_runs:
            counts = materialize(conn, run_id)
            print(
                f"{run_id}: {counts['tasks_new']} new task(s),"
                f" {counts['tasks_existing']} already known"
            )
        if granularity_runs:
            # Local import avoids the task_revision -> task_granularity ->
            # task_triage -> task_revision import cycle.
            from universe.task_granularity import materialize_parts

            for run_id in granularity_runs:
                counts = materialize_parts(conn, run_id)
                print(
                    f"{run_id}: {counts['tasks_new']} new task(s),"
                    f" {counts['tasks_existing']} already known"
                )
        # Composite parents are replaced by the parts produced by their exact
        # granularity verdict. They are not learner tasks that survive beside
        # those parts, so revision must consume the shared post-split scope.
        tasks = post_split_tasks(
            conn,
            generation_runs=gen_runs,
            granularity_runs=granularity_runs,
        )
        if args.passages_from:
            drawn = {p["id"] for p in fetch_passages_for_runs(conn, args.passages_from)}
            outside = sum(1 for t in tasks if t["passage_id"] not in drawn)
            tasks = [t for t in tasks if t["passage_id"] in drawn]
            print(
                f"{outside} task(s) outside the passages of"
                f" {', '.join(args.passages_from)}, skipped"
            )
        if not tasks:
            raise SystemExit(
                f"no post-split tasks from {', '.join(gen_runs + granularity_runs)}"
            )

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
            run_params={"gen_runs": gen_runs, "passages_from": args.passages_from, "granularity_runs": granularity_runs},
        )
        items = fetch_items(conn, summary["run_id"])

    verdicts = [revision_of(item) for item in items]
    tally = {
        label: sum(
            1
            for v in verdicts
            if (v["verdict"] if isinstance(v, dict) else v) == label
        )
        for label in VERDICTS + ("error", "unparseable")
    }
    counted = ", ".join(f"{count} {label}" for label, count in tally.items() if count)
    usage = report.aggregate_usage(items)
    duration = sum(item["duration_ms"] or 0 for item in items)
    print(
        f"{summary['run_id']} {summary['status']}:"
        f" {counted or 'nothing reported'},"
        f" {report.format_usage(usage) or 'no usage reported'},"
        f" {duration / 1000:.1f}s of model time"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.task_revision", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="judge and rewrite every task on its own")
    run.add_argument("--prompt", required=True, help="prompt version, e.g. v001")
    run.add_argument("--model", required=True)
    run.add_argument(
        "--gen-runs", type=id_list, help="comma-separated task-generation run ids"
    )
    run.add_argument(
        "--granularity-runs",
        type=id_list,
        help="comma-separated task-granularity run ids whose parts get revised",
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
