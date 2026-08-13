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

`--revision-run` overlays a task-revision run before judging: a rewritten
task is judged with its rewritten text, an unfixable one is dropped, and a
task the revision run never saw stops the run, because silence is not a
verdict. The revision rewrote without ever seeing the source; this pass has
the source, so an invented referent that contradicts it is caught here.
"""

import argparse

import psycopg

from universe import report
from universe.db import connect
from universe.effective_evidence import effective_task_manifest_sha
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
from universe.passages import fetch_passages_for_runs, source_text
from universe.post_split import tasks as post_split_tasks
from universe.task_revision import STAGE as REVISION_STAGE
from universe.task_revision import revision_of

STAGE = "task-triage"
DEFAULT_WORKERS = 16


def fetch_revisions(conn: psycopg.Connection, revision_run_id: str) -> dict[str, dict | str]:
    """Every revision the run reported, keyed by the task it was about."""
    run = fetch_run(conn, revision_run_id)
    if run["stage"] != REVISION_STAGE:
        raise SystemExit(f"{revision_run_id} is a {run['stage']} run, not {REVISION_STAGE}")
    revisions: dict[str, dict | str] = {}
    for item in fetch_items(conn, revision_run_id):
        if not item["task_id"]:
            raise SystemExit(f"{item['id']} is not about a task")
        revisions[item["task_id"]] = revision_of(item)
    return revisions


def apply_revisions(
    tasks: list[dict], revisions: dict[str, dict | str]
) -> tuple[list[dict], list[dict], list[dict]]:
    """The tasks as the revision run left them: revised, dropped, or unjudged."""
    kept, dropped, unjudged = [], [], []
    for task in tasks:
        revision = revisions.get(task["id"])
        if not isinstance(revision, dict):
            unjudged.append(task)
        elif revision["verdict"] == "unfixable":
            dropped.append(task)
        elif revision["verdict"] == "rewritten":
            kept.append({**task, "body": revision["task"]})
        else:
            kept.append(task)
    return kept, dropped, unjudged


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
        tasks = post_split_tasks(
            conn,
            generation_runs=args.gen_runs,
            granularity_runs=args.granularity_runs,
        )
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
                    f" {args.revision_run}: {names}; revise them first"
                )
            rewritten = sum(
                1 for t in tasks if isinstance(revisions[t["id"]], dict)
                and revisions[t["id"]]["verdict"] == "rewritten"
            )
            print(
                f"{args.revision_run}: {rewritten} task(s) judged as rewritten,"
                f" {len(dropped)} dropped as unfixable"
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
                "granularity_runs": args.granularity_runs or [],
                "effective_task_manifest_sha": effective_task_manifest_sha(tasks),
            },
        )
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
    run.add_argument(
        "--revision-run",
        help="task-revision run id; tasks are judged as it left them,"
        " rewrites applied and unfixables dropped",
    )
    run.add_argument(
        "--granularity-run",
        "--granularity-runs",
        dest="granularity_runs",
        type=id_list,
        help="comma-separated task-granularity run ids; judge their materialized parts",
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
