"""Embed every task for grouping: one call per task, vectors into task_embedding.

    python -m universe.task_embedding run --prompt v001 \
        --model qwen/qwen3-embedding-8b --gen-runs r0052 --revision-run r0065

The input is the task and its answer concatenated by a versioned template.
Revision and post-split overlays match task-substance: revised bodies are
embedded, unfixable tasks are dropped, composite parents are replaced by
parts, and part revisions can be overlaid. The vector is the call's output
and lands in task_embedding, so the readable fact kept on the run item is the
rendered input itself; input_sha is its sha256, tying each vector to the exact
text it came from.
"""

import argparse
import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor

from psycopg.types.json import Jsonb

from universe import report
from universe.db import connect
from universe.harness import claim_run, fetch_items, id_list, load_prompt, positive_int
from universe.model_client import EmbeddingClient
from universe.passages import fetch_passages_for_runs
from universe.task_granularity import granularity_of, materialize_parts
from universe.task_triage import apply_revisions, fetch_revisions
from universe.tasks import fetch_tasks_for_runs, materialize

STAGE = "task-embedding"
DEFAULT_WORKERS = 4


def cmd_run(args: argparse.Namespace) -> None:
    if args.parts_revision_run and not args.granularity_run:
        raise SystemExit("--parts-revision-run requires --granularity-run")

    prompt = load_prompt(STAGE, args.prompt, require_body=False)
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
            base_revisions = fetch_revisions(conn, args.revision_run)
            tasks, revision_dropped, unjudged = apply_revisions(tasks, base_revisions)
            if unjudged:
                names = ", ".join(t["id"] for t in unjudged)
                raise SystemExit(
                    f"{len(unjudged)} task(s) have no usable revision in"
                    f" {args.revision_run}: {names}; silence is not a verdict"
                )
            rewritten = sum(
                1
                for task in tasks
                if isinstance(base_revisions[task["id"]], dict)
                and base_revisions[task["id"]]["verdict"] == "rewritten"
            )
            bodies = "body was" if rewritten == 1 else "bodies were"
            print(
                f"{args.revision_run}: {len(revision_dropped)} task(s) dropped as unfixable,"
                f" {rewritten} task {bodies} swapped by rewrites"
            )
        if args.granularity_run:
            granularity = {}
            for item in fetch_items(conn, args.granularity_run):
                if not item["task_id"]:
                    raise SystemExit(f"{item['id']} is not about a task")
                granularity[item["task_id"]] = granularity_of(item)
            unjudged = [task for task in tasks if not isinstance(granularity.get(task["id"]), dict)]
            if unjudged:
                names = ", ".join(task["id"] for task in unjudged)
                raise SystemExit(
                    f"{len(unjudged)} task(s) have no usable granularity in"
                    f" {args.granularity_run}: {names}; silence is not a verdict"
                )
            surviving_task_ids = {task["id"] for task in tasks}
            composite_count = sum(
                granularity[task["id"]]["verdict"] == "composite" for task in tasks
            )
            tasks = [task for task in tasks if granularity[task["id"]]["verdict"] != "composite"]
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
                    isinstance(part_revisions[task["id"]], dict)
                    and part_revisions[task["id"]]["verdict"] == "rewritten"
                    for task in revised_parts
                )
                tasks = tasks[: len(tasks) - parts_count] + revised_parts
                bodies = "body was" if rewritten == 1 else "bodies were"
                print(
                    f"{args.parts_revision_run}: {len(part_dropped)} task(s) dropped as"
                    f" unfixable, {rewritten} task {bodies} swapped by rewrites"
                )
        if not tasks:
            raise SystemExit(f"no tasks from {', '.join(args.gen_runs)}")

        rendered = [
            prompt.render_fields({"task": task["body"], "answer": task["answer"]})
            for task in tasks
        ]
        input_shas = [hashlib.sha256(text.encode()).hexdigest() for text in rendered]
        client = EmbeddingClient(args.model)
        print(
            f"{prompt.ref} ({prompt.sha[:12]}) on {len(tasks)} task(s)"
            f" via {args.model}, {args.workers} at a time"
        )
        run_id = claim_run(
            conn, STAGE, args.model, prompt.ref, prompt.sha,
            {
                "gen_runs": args.gen_runs,
                "revision_run": args.revision_run,
                "granularity_run": args.granularity_run,
                "parts_revision_run": args.parts_revision_run,
            },
        )

        def call(work: tuple[int, dict, str, str]) -> tuple:
            index, task, text, input_sha = work
            try:
                vectors, usage, duration_ms = client.embed([text])
                if len(vectors) != 1:
                    raise ValueError(f"expected one embedding, got {len(vectors)}")
                return index, task, text, input_sha, vectors[0], usage, duration_ms, None
            except Exception as exc:  # one bad call must not end the run
                return index, task, text, input_sha, None, None, None, (
                    f"{type(exc).__name__}: {exc}"
                )

        work = [
            (index, task, text, input_sha)
            for index, (task, text, input_sha) in enumerate(
                zip(tasks, rendered, input_shas), 1
            )
        ]
        ok = failed = 0
        dims_seen: set[int] = set()
        with ThreadPoolExecutor(
            max_workers=max(1, min(args.workers, len(tasks) or 1))
        ) as pool:
            for index, task, text, input_sha, vector, usage, duration_ms, error in pool.map(
                call, work
            ):
                item_id = f"{run_id}-{index:04d}"
                conn.execute(
                    "INSERT INTO run_item"
                    " (id, run_id, artifact_id, passage_id, task_id,"
                    "  response, usage, duration_ms, error)"
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        item_id,
                        run_id,
                        task["artifact_id"],
                        task["passage_id"],
                        task["id"],
                        # The item holds its response or its error, never both;
                        # a failed call's input is re-derivable from the stamped
                        # prompt and the task row.
                        text if error is None else None,
                        Jsonb(usage) if usage is not None else None,
                        duration_ms,
                        error,
                    ),
                )
                if error:
                    failed += 1
                    print(f"  {task['id']}: {error}", file=sys.stderr)
                else:
                    dims = len(vector)
                    conn.execute(
                        "INSERT INTO task_embedding"
                        " (run_item_id, task_id, model, input_sha, dims, embedding)"
                        " VALUES (%s, %s, %s, %s, %s, %s::vector)",
                        (
                            item_id,
                            task["id"],
                            args.model,
                            input_sha,
                            dims,
                            "[" + ",".join(map(repr, vector)) + "]",
                        ),
                    )
                    ok += 1
                    dims_seen.add(dims)
                conn.commit()

        status = "done" if ok else "failed"
        conn.execute(
            "UPDATE run SET status = %s, finished_at = now() WHERE id = %s",
            (status, run_id),
        )
        conn.commit()
        items = fetch_items(conn, run_id)

    usage = report.aggregate_usage(items)
    duration = sum(item["duration_ms"] or 0 for item in items)
    dims = ", ".join(map(str, sorted(dims_seen))) or "none"
    print(
        f"{run_id} {status}: {ok} embedded / {failed} failed,"
        f" dims seen {dims},"
        f" {report.format_usage(usage) or 'no usage reported'},"
        f" {duration / 1000:.1f}s of model time"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.task_embedding", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="embed every task and answer from the generation runs")
    run.add_argument("--prompt", required=True, help="prompt version, e.g. v001")
    run.add_argument("--model", required=True)
    run.add_argument(
        "--gen-runs",
        required=True,
        type=id_list,
        help="comma-separated task-generation run ids",
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
        "--revision-run",
        help="task-revision run id; rewrites applied and unfixables dropped",
    )
    run.add_argument(
        "--passages-from",
        type=id_list,
        help="comma-separated cuts run ids; only tasks of their passages get embedded",
    )
    run.add_argument("--workers", type=positive_int, default=DEFAULT_WORKERS)
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
