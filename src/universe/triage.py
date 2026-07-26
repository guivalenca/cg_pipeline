"""Judge one passage at a time, with its whole source in context.

    python -m universe.triage run --prompt v001 --model deepseek-chat \
        --cuts-runs r0017,r0034,r0029 --tool prompts/passage-triage/tool-v001.json

The cuts runs named here are materialized first, so what this stage judges are
passage rows rather than one run's opinion, and a range several runs agree on
is judged once. The printed summary says how many ranges went in and how many
unique passages came out; the gap is what the agreement between runs saved.

The prompt gets two fields: `{{body}}`, the whole source as its blocks with no
dividers, and `{{passage}}`, the stretch in focus. The source text is built
once per artifact and handed to every passage of it byte for byte, and the
template puts it before the passage, which is what lets the provider's prefix
cache hit across a whole artifact's calls. Reordering the template throws that
away.
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
from universe.passages import (
    count_ranges,
    fetch_passages_for_runs,
    materialize,
    passage_text,
    source_text,
)

STAGE = "passage-triage"
DEFAULT_WORKERS = 4


def verdict_of(item: dict) -> str:
    """The verdict the item reported, or the reason there is none."""
    if item["error"]:
        return "error"
    try:
        verdict = json.loads(item["response"]).get("verdict")
    except (AttributeError, TypeError, json.JSONDecodeError):
        return "unparseable"
    return verdict if isinstance(verdict, str) and verdict else "unparseable"


def judged_passages(conn: psycopg.Connection, run_ids: list[str]) -> set[str]:
    """The passages these runs already answered for; errors do not count."""
    rows = conn.execute(
        "SELECT DISTINCT passage_id FROM run_item"
        " WHERE run_id = ANY(%s) AND passage_id IS NOT NULL AND error IS NULL",
        (run_ids,),
    ).fetchall()
    return {row[0] for row in rows}


def build_targets(conn: psycopg.Connection, passages: list[dict]) -> list[Target]:
    """One target per passage: the whole source as body, the passage beside it."""
    sources = fetch_sources(conn, sorted({p["artifact_id"] for p in passages}))
    bodies: dict[str, str] = {}
    targets = []
    for passage in passages:
        artifact_id = passage["artifact_id"]
        if artifact_id not in bodies:
            bodies[artifact_id] = source_text(conn, artifact_id, passage["blocker_version"])
        source_id, title = sources[artifact_id]
        targets.append(
            Target(
                source_id,
                title,
                artifact_id,
                bodies[artifact_id],
                passage_id=passage["id"],
                extra_fields={"passage": passage_text(conn, passage)},
            )
        )
    return targets


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
        ranges = count_ranges(conn, args.cuts_runs)
        if args.skip_runs:
            already = judged_passages(conn, args.skip_runs)
            skipped = sum(1 for p in passages if p["id"] in already)
            passages = [p for p in passages if p["id"] not in already]
            print(f"{skipped} passage(s) already judged in {', '.join(args.skip_runs)}, skipped")
            if not passages:
                raise SystemExit("every passage is already judged; nothing to run")

        targets = build_targets(conn, passages)
        client = ModelClient(
            args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            extra=extra or None,
        )
        print(
            f"{prompt.ref} ({prompt.sha[:12]}) on {len(targets)} passage(s)"
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
    print(
        f"{len(passages)} unique passage(s) judged out of {ranges} range(s)"
        f" drawn by {len(args.cuts_runs)} cuts run(s): {ranges - len(passages)} deduplicated"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.triage", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="judge every passage the cuts runs produced")
    run.add_argument("--prompt", required=True, help="prompt version, e.g. v001")
    run.add_argument("--model", required=True)
    run.add_argument(
        "--cuts-runs", required=True, type=id_list, help="comma-separated passage-cuts run ids"
    )
    run.add_argument(
        "--tool",
        required=True,
        help="path to a tool definition JSON; every call is forced through it",
    )
    run.add_argument(
        "--skip-runs",
        type=id_list,
        help="triage run ids whose already-judged passages get no new call",
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
