"""Judge whether a task-and-answer pair can show learning.

    python -m universe.task_substance run --prompt v004 --model deepseek/deepseek-v4-pro \
        --gen-runs r0052 --tool prompts/task-substance/tool-v004.json

One call per task, carrying only the task and its expected answer. A pair may
work as-is, be repairable, or be beyond repair. Silence remains an error,
distinct from an unsure verdict.
"""

import argparse
import json

import psycopg

from universe import report
from universe.db import connect
from universe.effective_evidence import effective_task_manifest_sha
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
from universe.task_scope import effective_tasks

STAGE = "task-substance"
LEGACY_VERDICTS = {"substantive", "trivial", "unsure"}
NEW_VERDICTS = {"works", "fixable", "does_not_work", "beyond_repair", "unsure"}
REASON_VERDICTS = {"works", "does_not_work", "unsure"}
KEPT = {"works", "fixable", "unsure", "substantive"}
DROPPED = {"does_not_work", "beyond_repair", "trivial"}
DEFAULT_WORKERS = 16


def substance_of(item: dict) -> dict | str:
    """The verdict and any delivered correction, or why neither is usable."""
    if item["error"]:
        return "error"
    try:
        parsed = json.loads(item["response"])
    except (TypeError, json.JSONDecodeError):
        return "unparseable"
    if not isinstance(parsed, dict) or parsed.get("verdict") not in LEGACY_VERDICTS | NEW_VERDICTS:
        return "unparseable"
    verdict = parsed["verdict"]
    if verdict != "fixable":
        result = {"verdict": verdict}
        if verdict in REASON_VERDICTS and isinstance((reason := parsed.get("reason")), str):
            if reason := reason.strip():
                result["reason"] = reason
        return result
    correction = {
        name: value.strip()
        for name in ("task", "answer")
        if isinstance((value := parsed.get(name)), str) and value.strip()
    }
    if not correction:
        return "unparseable"
    return {"verdict": verdict, **correction}


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
    if args.parts_revision_run and not args.granularity_run:
        raise SystemExit("--parts-revision-run requires --granularity-run")
    if not args.triage_run:
        raise SystemExit(
            "--triage-run is required; unsupported tasks must be dropped"
            " before substance calls"
        )

    prompt = load_prompt(STAGE, args.prompt, require_body=False)
    extra = dict(load_tool(args.tool)) if args.tool else {}
    extra.update(args.extra or {})
    with connect() as conn:
        tasks = effective_tasks(
            conn,
            generation_runs=args.gen_runs,
            passages_from=args.passages_from,
            granularity_run=args.granularity_run,
            revision_run=args.revision_run,
            parts_revision_run=args.parts_revision_run,
            triage_run=args.triage_run,
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
            run_params={
                "gen_runs": args.gen_runs,
                "passages_from": args.passages_from,
                "revision_run": args.revision_run,
                "granularity_run": args.granularity_run,
                "parts_revision_run": args.parts_revision_run,
                "triage_run": args.triage_run,
                "effective_task_manifest_sha": effective_task_manifest_sha(tasks),
            },
        )
        items = fetch_items(conn, summary["run_id"])

    verdicts = [substance_of(item) for item in items]
    labels = sorted({v["verdict"] if isinstance(v, dict) else v for v in verdicts})
    tally = {
        label: sum(
            1
            for v in verdicts
            if (v["verdict"] if isinstance(v, dict) else v) == label
        )
        for label in labels
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
    parser = argparse.ArgumentParser(prog="universe.task_substance", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="judge every task for subject knowledge required")
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
        required=True,
        help="task-triage run id; only explicitly supported tasks receive calls",
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
