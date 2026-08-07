"""State what answering each task shows a learner now knows or can do.

    python -m universe.kc_statement run --prompt v001 --model deepseek/deepseek-v4-pro --gen-runs r0052 --granularity-run r0093 --revision-run r0094 --triage-run r0095 --substance-run r0096 --tool prompts/kc-statement/tool-v001.json

One blind call per task carries only the task and answer, never the source. An
unsure verdict is a downstream filter verdict; triage and substance filters
select the surviving set.
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
from universe.task_granularity import granularity_of, materialize_parts
from universe.task_substance import DROPPED, substance_of
from universe.task_triage import apply_revisions, fetch_revisions
from universe.tasks import fetch_tasks_for_runs, materialize

STAGE = "kc-statement"
VERDICTS = {"stated", "unsure"}
TRIAGE_VERDICTS = {"supported", "unsupported", "unsure"}
DEFAULT_WORKERS = 16


def statement_of(item: dict) -> dict | str:
    """The statement the item reported, or why none is usable."""
    if item["error"]:
        return "error"
    try:
        parsed = json.loads(item["response"])
    except (TypeError, json.JSONDecodeError):
        return "unparseable"
    if not isinstance(parsed, dict) or parsed.get("verdict") not in VERDICTS:
        return "unparseable"
    verdict = parsed["verdict"]
    if verdict == "stated":
        statement = parsed.get("statement")
        if not isinstance(statement, str) or not (statement := statement.strip()):
            return "unparseable"
        return {"verdict": verdict, "statement": statement}
    result = {"verdict": verdict}
    if isinstance((reason := parsed.get("reason")), str):
        if reason := reason.strip():
            result["reason"] = reason
    return result


def fetch_usable_statements(
    conn: psycopg.Connection, run_ids: list[str]
) -> dict[str, str]:
    """Newest usable stated text per task across the named statement runs."""
    for run_id in run_ids:
        run = fetch_run(conn, run_id)
        if run["stage"] != STAGE:
            raise SystemExit(f"{run_id} is a {run['stage']} run, not {STAGE}")

    rows = conn.execute(
        "SELECT i.id, i.task_id, i.response, i.error"
        " FROM run_item i JOIN run r ON r.id = i.run_id"
        " WHERE r.id = ANY(%s)"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (run_ids,),
    ).fetchall()
    statements: dict[str, str] = {}
    for item_id, task_id, response, error in rows:
        if task_id is None:
            raise SystemExit(f"{item_id} is not about a task")
        parsed = statement_of({"response": response, "error": error})
        if (
            task_id not in statements
            and isinstance(parsed, dict)
            and parsed["verdict"] == "stated"
        ):
            statements[task_id] = parsed["statement"]
    return statements


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


def _triage_of(item: dict) -> str:
    if item["error"]:
        return "error"
    try:
        parsed = json.loads(item["response"])
    except (TypeError, json.JSONDecodeError):
        return "unparseable"
    if not isinstance(parsed, dict) or parsed.get("verdict") not in TRIAGE_VERDICTS:
        return "unparseable"
    return parsed["verdict"]


def select_tasks(conn: psycopg.Connection, args: argparse.Namespace) -> list[dict]:
    """The tasks left after every requested chain overlay and filter."""
    if args.parts_revision_run and not args.granularity_run:
        raise SystemExit("--parts-revision-run requires --granularity-run")

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
        base_revisions = fetch_revisions(conn, args.revision_run)
        tasks, revision_dropped, unjudged = apply_revisions(tasks, base_revisions)
        if unjudged:
            names = ", ".join(t["id"] for t in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable revision in"
                f" {args.revision_run}: {names}; silence is not a verdict"
            )
    if args.granularity_run:
        granularity = {}
        for item in fetch_items(conn, args.granularity_run):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            granularity[item["task_id"]] = granularity_of(item)
        unjudged = [
            task
            for task in tasks
            if not isinstance(granularity.get(task["id"]), dict)
        ]
        if unjudged:
            names = ", ".join(task["id"] for task in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable granularity in"
                f" {args.granularity_run}: {names}; silence is not a verdict"
            )

        surviving_task_ids = {task["id"] for task in tasks}
        rewritten_composites = [
            task["id"]
            for task in tasks
            if granularity[task["id"]]["verdict"] == "composite"
            and args.revision_run
            and isinstance(base_revisions[task["id"]], dict)
            and base_revisions[task["id"]]["verdict"] == "rewritten"
        ]
        if rewritten_composites:
            print(
                f"warning: {len(rewritten_composites)} rewritten composite parent(s)"
                " whose rewrites are superseded by their parts"
            )
        composite_count = sum(
            granularity[task["id"]]["verdict"] == "composite" for task in tasks
        )
        tasks = [
            task
            for task in tasks
            if granularity[task["id"]]["verdict"] != "composite"
        ]
        materialize_parts(conn, args.granularity_run)
        parent_by_part_run_item = {
            item["id"]: item["task_id"] for item in fetch_items(conn, args.granularity_run)
        }
        part_tasks = [
            task for task in fetch_tasks_for_runs(conn, [args.granularity_run])
            if parent_by_part_run_item[task["run_item_id"]] in surviving_task_ids
        ]
        parts_count = len(part_tasks)
        tasks.extend(part_tasks)
        print(
            f"{args.granularity_run}: {composite_count} composite task(s)"
            f" replaced by {parts_count} part(s)"
        )

        if args.parts_revision_run:
            part_revisions = fetch_revisions(conn, args.parts_revision_run)
            revised_parts, part_dropped, unjudged = apply_revisions(part_tasks, part_revisions)
            if unjudged:
                names = ", ".join(task["id"] for task in unjudged)
                raise SystemExit(
                    f"{len(unjudged)} task(s) have no usable revision in"
                    f" {args.parts_revision_run}: {names}; silence is not a verdict"
                )
            rewritten = sum(
                1
                for task in revised_parts
                if isinstance(part_revisions[task["id"]], dict)
                and part_revisions[task["id"]]["verdict"] == "rewritten"
            )
            tasks = tasks[: len(tasks) - parts_count] + revised_parts
            bodies = "body was" if rewritten == 1 else "bodies were"
            print(
                f"{args.parts_revision_run}: {len(part_dropped)} task(s) dropped as"
                f" unfixable, {rewritten} task {bodies} swapped by rewrites"
            )
    if args.revision_run:
        rewritten = sum(
            1
            for task in tasks
            if task["id"] in base_revisions
            and isinstance(base_revisions[task["id"]], dict)
            and base_revisions[task["id"]]["verdict"] == "rewritten"
        )
        bodies = "body was" if rewritten == 1 else "bodies were"
        print(
            f"{args.revision_run}: {len(revision_dropped)} task(s) dropped as unfixable,"
            f" {rewritten} task {bodies} swapped by rewrites"
        )
    if args.triage_run:
        triage = {}
        for item in fetch_items(conn, args.triage_run):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            triage[item["task_id"]] = _triage_of(item)
        unjudged = [
            task for task in tasks if triage.get(task["id"]) not in TRIAGE_VERDICTS
        ]
        if unjudged:
            names = ", ".join(task["id"] for task in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable triage in"
                f" {args.triage_run}: {names}; silence is not a verdict"
            )
        dropped = sum(triage[task["id"]] != "supported" for task in tasks)
        tasks = [task for task in tasks if triage[task["id"]] == "supported"]
        print(
            f"{args.triage_run}: {dropped} task(s) dropped as"
            " unsupported/unsure by triage"
        )
    if args.substance_run:
        substances = {}
        for item in fetch_items(conn, args.substance_run):
            if not item["task_id"]:
                raise SystemExit(f"{item['id']} is not about a task")
            substances[item["task_id"]] = substance_of(item)
        unjudged = [
            task
            for task in tasks
            if not isinstance(substances.get(task["id"]), dict)
        ]
        if unjudged:
            names = ", ".join(task["id"] for task in unjudged)
            raise SystemExit(
                f"{len(unjudged)} task(s) have no usable substance in"
                f" {args.substance_run}: {names}; silence is not a verdict"
            )
        dropped = sum(
            substances[task["id"]]["verdict"] in DROPPED for task in tasks
        )
        tasks = [
            task
            for task in tasks
            if substances[task["id"]]["verdict"] not in DROPPED
        ]
        print(f"{args.substance_run}: {dropped} task(s) dropped by substance")
    return tasks


def cmd_run(args: argparse.Namespace) -> None:
    if args.parts_revision_run and not args.granularity_run:
        raise SystemExit("--parts-revision-run requires --granularity-run")

    prompt = load_prompt(STAGE, args.prompt, require_body=False)
    extra = dict(load_tool(args.tool))
    extra.update(args.extra or {})
    with connect() as conn:
        tasks = select_tasks(conn, args)
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
            run_params={
                "gen_runs": args.gen_runs,
                "passages_from": args.passages_from,
                "revision_run": args.revision_run,
                "granularity_run": args.granularity_run,
                "parts_revision_run": args.parts_revision_run,
                "triage_run": args.triage_run,
                "substance_run": args.substance_run,
            },
        )
        items = fetch_items(conn, summary["run_id"])

    statements = [statement_of(item) for item in items]
    tally = {
        label: sum(
            1
            for statement in statements
            if (statement["verdict"] if isinstance(statement, dict) else statement)
            == label
        )
        for label in ("stated", "unsure", "error", "unparseable")
    }
    counted = ", ".join(f"{tally[label]} {label}" for label in tally)
    usage = report.aggregate_usage(items)
    duration = sum(item["duration_ms"] or 0 for item in items)
    print(
        f"{summary['run_id']} {summary['status']}:"
        f" {counted},"
        f" {report.format_usage(usage) or 'no usage reported'},"
        f" {duration / 1000:.1f}s of model time"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.kc_statement", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="state what answering every task demonstrates")
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
        help="task-revision run id; overlay its rewrites and drop unfixables",
    )
    run.add_argument(
        "--granularity-run",
        help="task-granularity run id; replace composite tasks with its parts",
    )
    run.add_argument(
        "--parts-revision-run",
        help="task-revision run id; overlay rewrites and drop unfixable parts",
    )
    run.add_argument(
        "--triage-run",
        help="task-triage run id; keep only tasks it judged supported",
    )
    run.add_argument(
        "--substance-run",
        help="task-substance run id; drop tasks it judged non-substantive",
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
