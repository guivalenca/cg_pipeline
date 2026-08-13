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
from universe.effective_evidence import effective_task_run_params
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
from universe.run_overlay import fold_newest_usable
from universe.task_scope import effective_tasks

STAGE = "kc-statement"
VERDICTS = {"stated", "unsure"}
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


def _usable_statement(item: dict) -> dict | None:
    parsed = statement_of(item)
    return parsed if isinstance(parsed, dict) else None


def fetch_usable_statements(
    conn: psycopg.Connection, run_ids: list[str]
) -> dict[str, str]:
    """Newest usable stated text per task across the named statement runs."""
    for run_id in run_ids:
        run = fetch_run(conn, run_id)
        if run["stage"] != STAGE:
            raise SystemExit(f"{run_id} is a {run['stage']} run, not {STAGE}")

    rows = conn.execute(
        "SELECT i.task_id, i.id, i.response, i.error,"
        " r.id, r.model, r.prompt_ref"
        " FROM run_item i JOIN run r ON r.id = i.run_id"
        " WHERE r.id = ANY(%s)"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (run_ids,),
    ).fetchall()
    for task_id, item_id, *_ in rows:
        if task_id is None:
            raise SystemExit(f"{item_id} is not about a task")
    selected, _, _ = fold_newest_usable(rows, _usable_statement)
    return {
        task_id: item["answer"]["statement"]
        for task_id, item in selected.items()
        if item["answer"]["verdict"] == "stated"
    }


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


def select_tasks(conn: psycopg.Connection, args: argparse.Namespace) -> list[dict]:
    """The tasks left after every requested chain overlay and filter."""
    return effective_tasks(
        conn,
        generation_runs=args.gen_runs,
        passages_from=args.passages_from,
        granularity_run=args.granularity_run,
        revision_run=args.revision_run,
        parts_revision_run=args.parts_revision_run,
        triage_run=args.triage_run,
        substance_run=args.substance_run,
    )


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
            run_params=effective_task_run_params(
                tasks,
                gen_runs=args.gen_runs,
                passages_from=args.passages_from,
                revision_run=args.revision_run,
                granularity_run=args.granularity_run,
                parts_revision_run=args.parts_revision_run,
                triage_run=args.triage_run,
                substance_run=args.substance_run,
            ),
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
