"""Embed tasks for grouping: one call per task, vectors into task_embedding.

    python -m universe.task_embedding run --prompt v001 \
        --model qwen/qwen3-embedding-8b --gen-runs r0052 --revision-run r0065
    python -m universe.task_embedding run --prompt v002 \
        --model qwen/qwen3-embedding-8b --statements-from r0101,r0102

The input is either the task and answer or its selected KC statement, rendered
by a versioned template. Statement runs define the exact grouping scope.
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
from concurrent.futures import ThreadPoolExecutor, as_completed

from psycopg.types.json import Jsonb

from universe import pipeline_lease, report
from universe.db import connect
from universe.effective_evidence import effective_task_run_params
from universe.harness import claim_run, fetch_items, id_list, load_prompt, positive_int
from universe.kc_statement import fetch_usable_statements
from universe.model_client import EmbeddingClient
from universe.task_scope import effective_tasks
from universe.tasks import fetch_tasks

STAGE = "task-embedding"
DEFAULT_WORKERS = 16


def statement_embedding_inputs(
    conn, statement_runs: list[str], prompt
) -> tuple[list[dict], list[str]]:
    """Tasks and rendered statement-only inputs selected by statement runs."""
    statements = fetch_usable_statements(conn, statement_runs)
    tasks = fetch_tasks(conn, sorted(statements))
    rendered = [
        prompt.render_fields({"statement": statements[task["id"]]})
        for task in tasks
    ]
    return tasks, rendered


def task_answer_embedding_inputs(
    conn, args: argparse.Namespace, prompt
) -> tuple[list[dict], list[str]]:
    """Legacy task+answer inputs from the shared post-split task scope."""
    tasks = effective_tasks(
        conn,
        generation_runs=args.gen_runs,
        passages_from=args.passages_from,
        granularity_run=args.granularity_run,
        revision_run=args.revision_run,
        parts_revision_run=args.parts_revision_run,
    )
    rendered = [
        prompt.render_fields({"task": task["body"], "answer": task["answer"]})
        for task in tasks
    ]
    return tasks, rendered


def cmd_run(args: argparse.Namespace) -> None:
    if not args.gen_runs and not args.statements_from:
        raise SystemExit("one of --gen-runs or --statements-from is required")
    if args.statements_from and args.gen_runs:
        print("note: --statements-from was given; --gen-runs is ignored")
    if (
        not args.statements_from
        and args.parts_revision_run
        and not args.granularity_run
    ):
        raise SystemExit("--parts-revision-run requires --granularity-run")

    prompt = load_prompt(STAGE, args.prompt, require_body=False)
    with connect() as conn:
        if args.statements_from:
            tasks, rendered = statement_embedding_inputs(
                conn, args.statements_from, prompt
            )
        else:
            tasks, rendered = task_answer_embedding_inputs(conn, args, prompt)
        if not tasks:
            source_runs = args.statements_from or args.gen_runs
            raise SystemExit(f"no tasks from {', '.join(source_runs)}")

        empty = [task["id"] for task, text in zip(tasks, rendered) if not text.strip()]
        if empty:
            # The provider rejects empty inputs; an empty rendering means a
            # broken task row, which must stop the run, not become a vector.
            raise SystemExit(f"{len(empty)} task(s) render to empty input: {', '.join(empty)}")
        input_shas = [hashlib.sha256(text.encode()).hexdigest() for text in rendered]
        client = EmbeddingClient(args.model)
        supervisor = pipeline_lease.current_supervisor(required=True)
        print(
            f"{prompt.ref} ({prompt.sha[:12]}) on {len(tasks)} task(s)"
            f" via {args.model}, {args.workers} at a time"
        )
        run_params = {
            "gen_runs": args.gen_runs,
            "statements_from": args.statements_from,
            "passages_from": args.passages_from,
            "revision_run": args.revision_run,
            "granularity_run": args.granularity_run,
            "parts_revision_run": args.parts_revision_run,
        }
        if not args.statements_from:
            run_params = effective_task_run_params(tasks, **run_params)
        run_id = claim_run(
            conn, STAGE, args.model, prompt.ref, prompt.sha, run_params
        )

        def call(work: tuple[int, dict, str, str]) -> tuple:
            index, task, text, input_sha = work
            try:
                if supervisor is not None:
                    supervisor.before_provider_call()
                vectors, usage, duration_ms = client.embed([text])
                if len(vectors) != 1:
                    raise ValueError(f"expected one embedding, got {len(vectors)}")
                return index, task, text, input_sha, vectors[0], usage, duration_ms, None
            except pipeline_lease.LeaseLost:
                raise
            except Exception as exc:  # one bad call must not end the run
                return (
                    index,
                    task,
                    text,
                    input_sha,
                    None,
                    getattr(exc, "usage", None),
                    getattr(exc, "duration_ms", None),
                    f"{type(exc).__name__}: {exc}",
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
            futures = [pool.submit(call, item) for item in work]
            for future in as_completed(futures):
                index, task, text, input_sha, vector, usage, duration_ms, error = (
                    future.result()
                )
                item_id = f"{run_id}-{index:04d}"
                if supervisor is not None:
                    supervisor.fence(conn)
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
        if supervisor is not None:
            supervisor.fence(conn)
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

    run = sub.add_parser("run", help="embed task answers or selected KC statements")
    run.add_argument("--prompt", required=True, help="prompt version, e.g. v001")
    run.add_argument("--model", required=True)
    run.add_argument(
        "--gen-runs",
        type=id_list,
        help="comma-separated task-generation run ids",
    )
    run.add_argument(
        "--statements-from",
        type=id_list,
        help="comma-separated kc-statement run ids; their stated tasks are the exact scope",
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
