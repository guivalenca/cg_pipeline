"""Ask what tasks each passage that survived triage supports.

    python -m universe.taskgen run --prompt v001 --model deepseek-v4-flash \
        --cuts-runs r0017,r0031 --triage-runs r0043,r0045 \
        --tool prompts/task-generation/tool-v001.json

Passages come from the cuts runs, materialized first so a range several runs
agree on is one passage. The triage runs then decide who gets a call: only a
passage every named triage run judged not_filler goes out. A passage with no
verdict at all stops the run, because silence is not a verdict; a passage any
run called filler or unsure is dropped and said so.

The call itself is the triage shape reused: the whole source first, byte for
byte the same across an artifact's passages so the provider's prefix cache
hits, and the passage in focus at the end.
"""

import argparse
import json

import psycopg

from universe import report
from universe.db import connect
from universe.harness import (
    execute,
    fetch_items,
    fetch_run,
    id_list,
    json_object,
    load_prompt,
    load_tool,
    positive_int,
)
from universe.model_client import DEFAULT_MAX_TOKENS, ModelClient
from universe.passages import fetch_passages_for_runs, materialize
from universe.triage import build_targets, verdict_of

STAGE = "task-generation"
TRIAGE_STAGE = "passage-triage"
KEEP = "not_filler"
DEFAULT_WORKERS = 16


def tasks_of(item: dict) -> list[dict] | str:
    """The tasks the item reported, or the reason there are none."""
    if item["error"]:
        return "error"
    try:
        tasks = json.loads(item["response"]).get("tasks")
    except (AttributeError, TypeError, json.JSONDecodeError):
        return "unparseable"
    if not isinstance(tasks, list):
        return "unparseable"
    for entry in tasks:
        if not isinstance(entry, dict) or not entry.get("task") or not entry.get("answer"):
            return "unparseable"
    return [{"task": entry["task"], "answer": entry["answer"]} for entry in tasks]


def fetch_verdicts(conn: psycopg.Connection, run_ids: list[str]) -> dict[str, set[str]]:
    """Every verdict these triage runs gave, folded per passage."""
    verdicts: dict[str, set[str]] = {}
    for run_id in run_ids:
        run = fetch_run(conn, run_id)
        if run["stage"] != TRIAGE_STAGE:
            raise SystemExit(f"{run_id} is a {run['stage']} run, not {TRIAGE_STAGE}")
        for item in fetch_items(conn, run_id):
            if not item["passage_id"]:
                raise SystemExit(
                    f"{item['id']} is about a whole artifact, not a passage;"
                    f" {run_id} cannot gate task generation"
                )
            verdicts.setdefault(item["passage_id"], set()).add(verdict_of(item))
    return verdicts


def split_by_verdict(
    passages: list[dict], verdicts: dict[str, set[str]]
) -> tuple[list[dict], list[dict], list[dict]]:
    """Who gets a call: only a passage every triage verdict agreed to keep."""
    kept, dropped, unjudged = [], [], []
    for passage in passages:
        seen = verdicts.get(passage["id"])
        if not seen:
            unjudged.append(passage)
        elif seen == {KEEP}:
            kept.append(passage)
        else:
            dropped.append(passage)
    return kept, dropped, unjudged


def span(passage: dict) -> str:
    return f"{passage['first_seq']}-{passage['last_seq']}"


def cmd_run(args: argparse.Namespace) -> None:
    prompt = load_prompt(STAGE, args.prompt)
    extra = dict(load_tool(args.tool)) if args.tool else {}
    extra.update(args.extra or {})
    with connect() as conn:
        for run_id in args.cuts_runs:
            counts = materialize(conn, run_id)
            print(
                f"{run_id}: {counts['passages_new']} new passage(s),"
                f" {counts['passages_existing']} already known"
            )
        passages = fetch_passages_for_runs(conn, args.cuts_runs)
        if not passages:
            raise SystemExit(f"no passages from {', '.join(args.cuts_runs)}")

        verdicts = fetch_verdicts(conn, args.triage_runs)
        kept, dropped, unjudged = split_by_verdict(passages, verdicts)
        if unjudged:
            spans = ", ".join(span(p) for p in unjudged)
            raise SystemExit(
                f"{len(unjudged)} passage(s) have no verdict in"
                f" {', '.join(args.triage_runs)}: {spans}; triage them first"
            )
        for passage in dropped:
            print(f"  {span(passage)} dropped: {', '.join(sorted(verdicts[passage['id']]))}")
        if not kept:
            raise SystemExit("no passage survived triage")

        targets = build_targets(conn, kept)
        client = ModelClient(
            args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            extra=extra or None,
        )
        print(
            f"{prompt.ref} ({prompt.sha[:12]}) on {len(targets)} of {len(passages)}"
            f" passage(s) via {args.model}, {args.workers} at a time"
        )
        summary = execute(conn, prompt, client, targets, workers=args.workers)
        items = fetch_items(conn, summary["run_id"])

    usage = report.aggregate_usage(items)
    duration = sum(item["duration_ms"] or 0 for item in items)
    counts = [tasks for tasks in map(tasks_of, items) if isinstance(tasks, list)]
    print(
        f"{summary['run_id']} {summary['status']}:"
        f" {summary['ok']} ok, {summary['failed']} failed,"
        f" {sum(len(tasks) for tasks in counts)} task(s) reported,"
        f" {report.format_usage(usage) or 'no usage reported'},"
        f" {duration / 1000:.1f}s of model time"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.taskgen", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="generate tasks for every passage triage kept")
    run.add_argument("--prompt", required=True, help="prompt version, e.g. v001")
    run.add_argument("--model", required=True)
    run.add_argument(
        "--cuts-runs", required=True, type=id_list, help="comma-separated passage-cuts run ids"
    )
    run.add_argument(
        "--triage-runs",
        required=True,
        type=id_list,
        help="comma-separated passage-triage run ids that gate the passages",
    )
    run.add_argument(
        "--tool",
        required=True,
        help="path to a tool definition JSON; every call is forced through it",
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
