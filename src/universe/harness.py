"""Run a versioned prompt against stored artifacts and stamp what happened.

    python -m universe.harness run --stage passage-segmentation --prompt v001 \
        --model deepseek-chat --limit 3
    python -m universe.harness list
    python -m universe.harness report r0001
    python -m universe.harness compare r0001 r0002

Prompts live at prompts/<stage>/<vNNN>.md; `{{body}}` is where the artifact
body goes. Every run records the prompt's hash, so an edit without a version
bump is visible afterwards instead of silently rewriting history.
"""

import argparse
import hashlib
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from universe import report
from universe.db import connect
from universe.model_client import DEFAULT_MAX_TOKENS, ModelClient

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"
MAX_WORKERS = 4
PLACEHOLDER = "{{body}}"


@dataclass(frozen=True)
class Prompt:
    ref: str
    sha: str
    template: str

    def render(self, body: str) -> str:
        return self.template.replace(PLACEHOLDER, body)


@dataclass(frozen=True)
class Target:
    """One artifact the run will be pointed at."""

    source_id: str
    source_title: str | None
    artifact_id: str
    body: str


def load_prompt(stage: str, version: str) -> Prompt:
    path = PROMPTS_DIR / stage / (version if version.endswith(".md") else f"{version}.md")
    if not path.exists():
        raise SystemExit(f"no prompt at {path}")
    raw = path.read_bytes()
    template = raw.decode("utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit(f"{path} has no {PLACEHOLDER} placeholder")
    return Prompt(
        ref=f"{stage}/{path.stem}",
        sha=hashlib.sha256(raw).hexdigest(),
        template=template,
    )


def select_targets(
    conn: psycopg.Connection, source_ids: list[str] | None = None, limit: int | None = None
) -> list[Target]:
    """The latest artifact of each selected source, in source id order.

    An empty selection selects nothing: only `None` means "no restriction".
    """
    where, tail, params = "", "", []
    if source_ids is not None:
        where, params = "WHERE s.id = ANY(%s)", [source_ids]
    if limit is not None:
        tail, params = " LIMIT %s", params + [limit]
    rows = conn.execute(
        "SELECT DISTINCT ON (s.id) s.id, s.title, a.id, a.body"
        " FROM source s"
        " JOIN source_snapshot sn ON sn.source_id = s.id"
        " JOIN artifact a ON a.snapshot_id = sn.id"
        f" {where}"
        " ORDER BY s.id, a.created_at DESC, a.id DESC"
        f"{tail}",
        params,
    ).fetchall()
    return [Target(*row) for row in rows]


def next_run_id(conn: psycopg.Connection) -> str:
    number = conn.execute(
        "SELECT coalesce(max(substring(id from 2)::int), 0) + 1 FROM run"
    ).fetchone()[0]
    return f"r{number:04d}"


def execute(
    conn: psycopg.Connection,
    prompt: Prompt,
    client: ModelClient,
    targets: list[Target],
) -> dict:
    """Call the model once per target, writing each outcome as it lands."""
    run_id = next_run_id(conn)
    conn.execute(
        "INSERT INTO run (id, stage, model, prompt_ref, prompt_sha, params, status)"
        " VALUES (%s, %s, %s, %s, %s, %s, 'running')",
        (
            run_id,
            prompt.ref.split("/", 1)[0],
            client.model,
            prompt.ref,
            prompt.sha,
            Jsonb(client.params),
        ),
    )
    conn.commit()

    def call(indexed: tuple[int, Target]) -> tuple[int, Target, tuple | None, str | None]:
        index, target = indexed
        try:
            return index, target, client.complete(prompt.render(target.body)), None
        except Exception as exc:  # one bad call must not end the run
            return index, target, None, f"{type(exc).__name__}: {exc}"

    ok = failed = 0
    with ThreadPoolExecutor(max_workers=max(1, min(MAX_WORKERS, len(targets) or 1))) as pool:
        for index, target, result, error in pool.map(call, enumerate(targets, start=1)):
            text, usage, duration_ms = result if result else (None, None, None)
            conn.execute(
                "INSERT INTO run_item"
                " (id, run_id, artifact_id, response, usage, duration_ms, error)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    f"{run_id}-{index:04d}",
                    run_id,
                    target.artifact_id,
                    text,
                    Jsonb(usage) if usage is not None else None,
                    duration_ms,
                    error,
                ),
            )
            conn.commit()
            if error:
                failed += 1
                print(f"  {target.source_id}: {error}", file=sys.stderr)
            else:
                ok += 1

    status = "done" if ok else "failed"
    conn.execute(
        "UPDATE run SET status = %s, finished_at = now() WHERE id = %s", (status, run_id)
    )
    conn.commit()
    return {"run_id": run_id, "status": status, "ok": ok, "failed": failed}


# --- reading back -----------------------------------------------------------


def fetch_run(conn: psycopg.Connection, run_id: str) -> dict:
    row = conn.execute(
        "SELECT id, stage, model, prompt_ref, prompt_sha, params, status, started_at, finished_at"
        " FROM run WHERE id = %s",
        (run_id,),
    ).fetchone()
    if not row:
        raise SystemExit(f"no run {run_id}")
    keys = "id stage model prompt_ref prompt_sha params status started_at finished_at".split()
    return dict(zip(keys, row))


def fetch_items(conn: psycopg.Connection, run_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT i.id, i.artifact_id, s.id, s.title, i.response, i.usage, i.duration_ms, i.error"
        " FROM run_item i"
        " JOIN artifact a ON a.id = i.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " JOIN source s ON s.id = sn.source_id"
        " WHERE i.run_id = %s ORDER BY i.id",
        (run_id,),
    ).fetchall()
    keys = "id artifact_id source_id source_title response usage duration_ms error".split()
    return [dict(zip(keys, row)) for row in rows]


def fetch_runs(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT r.id, r.stage, r.model, r.prompt_ref, r.status,"
        " count(i.id) FILTER (WHERE i.error IS NULL),"
        " count(i.id) FILTER (WHERE i.error IS NOT NULL), r.started_at"
        " FROM run r LEFT JOIN run_item i ON i.run_id = r.id"
        " GROUP BY r.id ORDER BY r.id"
    ).fetchall()
    keys = "id stage model prompt_ref status ok failed started_at".split()
    return [dict(zip(keys, row)) for row in rows]


def write_report(conn: psycopg.Connection, run_id: str, reports_dir: Path | None = None) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"{run_id}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.render_run(fetch_run(conn, run_id), fetch_items(conn, run_id)))
    return path


def write_comparison(
    conn: psycopg.Connection, run_a: str, run_b: str, reports_dir: Path | None = None
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"{run_a}-vs-{run_b}.html"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        report.render_comparison(
            fetch_run(conn, run_a),
            fetch_items(conn, run_a),
            fetch_run(conn, run_b),
            fetch_items(conn, run_b),
        )
    )
    return path


# --- CLI --------------------------------------------------------------------


def cmd_run(args: argparse.Namespace) -> None:
    prompt = load_prompt(args.stage, args.prompt)
    with connect() as conn:
        targets = select_targets(conn, args.sources, args.limit)
        if not targets:
            raise SystemExit("no artifacts selected")
        client = ModelClient(
            args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            extra=args.extra,
        )
        print(f"{prompt.ref} ({prompt.sha[:12]}) on {len(targets)} artifact(s) via {args.model}")
        summary = execute(conn, prompt, client, targets)
        items = fetch_items(conn, summary["run_id"])

    usage = report.aggregate_usage(items)
    duration = sum(item["duration_ms"] or 0 for item in items)
    print(
        f"{summary['run_id']} {summary['status']}:"
        f" {summary['ok']} ok, {summary['failed']} failed,"
        f" {report.format_usage(usage) or 'no usage reported'},"
        f" {duration / 1000:.1f}s of model time"
    )


def cmd_list(args: argparse.Namespace) -> None:
    with connect() as conn:
        runs = fetch_runs(conn)
    if not runs:
        print("no runs yet")
        return
    header = f"{'id':<7} {'stage':<22} {'model':<26} {'prompt':<30} {'items':>9}  started"
    print(header)
    print("-" * len(header))
    for run in runs:
        started = run["started_at"].strftime("%Y-%m-%d %H:%M")
        items = f"{run['ok']}/{run['ok'] + run['failed']}"
        print(
            f"{run['id']:<7} {run['stage']:<22} {run['model']:<26}"
            f" {run['prompt_ref']:<30} {items:>9}  {started}"
        )


def cmd_report(args: argparse.Namespace) -> None:
    with connect() as conn:
        print(write_report(conn, args.run_id))


def cmd_compare(args: argparse.Namespace) -> None:
    with connect() as conn:
        print(write_comparison(conn, args.run_a, args.run_b))


def source_ids(value: str) -> list[str]:
    ids = [part.strip() for part in value.split(",") if part.strip()]
    if not ids:
        raise argparse.ArgumentTypeError("no source ids given")
    return ids


def json_object(value: str) -> dict:
    import json

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"not valid JSON: {exc}")
    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("must be a JSON object")
    return parsed


def positive_int(value: str) -> int:
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.harness", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="run a prompt version over artifacts")
    run.add_argument("--stage", required=True)
    run.add_argument("--prompt", required=True, help="prompt version, e.g. v001")
    run.add_argument("--model", required=True)
    selection = run.add_mutually_exclusive_group(required=True)
    selection.add_argument("--sources", type=source_ids, help="comma-separated source ids")
    selection.add_argument("--limit", type=positive_int, help="first N sources by id")
    selection.add_argument("--all", action="store_true")
    run.add_argument("--temperature", type=float)
    run.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    run.add_argument(
        "--extra",
        type=json_object,
        help="extra JSON merged into the request payload and stamped in run"
        " params, e.g. '{\"thinking\": {\"type\": \"enabled\"}}'",
    )
    run.set_defaults(func=cmd_run)

    sub.add_parser("list", help="list runs").set_defaults(func=cmd_list)

    report_cmd = sub.add_parser("report", help="write reports/RUN_ID.html")
    report_cmd.add_argument("run_id")
    report_cmd.set_defaults(func=cmd_report)

    compare = sub.add_parser("compare", help="write reports/RUN_A-vs-RUN_B.html")
    compare.add_argument("run_a")
    compare.add_argument("run_b")
    compare.set_defaults(func=cmd_compare)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
