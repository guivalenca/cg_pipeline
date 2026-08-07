"""Write one canonical knowledge statement per committed composite KC.

Membership is upstream: this stage never accepts, rejects, splits, or merges a
group.  It reads only the member tasks and answers and attaches its result to
the exact grouping snapshot that supplied those members.
"""

import argparse
from html import escape
import json
from pathlib import Path

import psycopg

from universe import defaults, harness, report
from universe.db import connect
from universe.ingest import THINKING_EXTRA
from universe.model_client import ModelClient

STAGE = "kc-canonical-statement"
PROMPT_VERSION = "v001"
TOOL_PATH = Path(__file__).resolve().parents[2] / "prompts" / STAGE / "tool-v001.json"
DEFAULT_MODEL = "deepseek/deepseek-v4-pro"
DEFAULT_WORKERS = 8
DEFAULT_MAX_TOKENS = 1000
VERDICTS = {"stated", "unsure"}


def canonicalization_of(item: dict) -> dict | str:
    """The canonical statement reported by one call, or its failure class."""
    if item.get("error"):
        return "error"
    try:
        parsed = json.loads(item.get("response"))
    except (TypeError, json.JSONDecodeError):
        return "unparseable"
    if not isinstance(parsed, dict) or parsed.get("verdict") not in VERDICTS:
        return "unparseable"
    if parsed["verdict"] == "stated":
        statement = parsed.get("statement")
        if not isinstance(statement, str) or not (statement := statement.strip()):
            return "unparseable"
        return {"verdict": "stated", "statement": statement}
    reason = parsed.get("reason")
    result = {"verdict": "unsure"}
    if isinstance(reason, str) and (reason := reason.strip()):
        result["reason"] = reason
    return result


def latest_grouping_id(conn: psycopg.Connection) -> str:
    row = conn.execute(
        "SELECT id FROM kc_grouping ORDER BY computed_at DESC, id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise SystemExit("no grouping snapshot has been computed")
    return row[0]


def fetch_group_tasks(conn: psycopg.Connection, grouping_id: str) -> list[dict]:
    """Every composite and its immutable member task evidence."""
    exists = conn.execute(
        "SELECT 1 FROM kc_grouping WHERE id = %s", (grouping_id,)
    ).fetchone()
    if exists is None:
        raise SystemExit(f"no grouping snapshot {grouping_id}")
    rows = conn.execute(
        "SELECT g.id, m.task_id, t.body, t.answer"
        " FROM kc_group g"
        " JOIN kc_group_member m"
        "   ON m.grouping_id = g.grouping_id AND m.group_id = g.id"
        " JOIN task t ON t.id = m.task_id"
        " WHERE g.grouping_id = %s"
        " ORDER BY g.id, m.task_id",
        (grouping_id,),
    ).fetchall()
    groups: dict[str, list[dict]] = {}
    for group_id, task_id, body, answer in rows:
        groups.setdefault(group_id, []).append(
            {"id": task_id, "task": body, "answer": answer}
        )
    return [
        {"id": group_id, "tasks": tasks}
        for group_id, tasks in sorted(groups.items())
    ]


def tasks_markup(tasks: list[dict]) -> str:
    """Render member evidence without leaking earlier model interpretations."""
    return "\n".join(
        "<item>\n"
        f"<task>{escape(task['task'])}</task>\n"
        f"<answer>{escape(task['answer'])}</answer>\n"
        "</item>"
        for task in tasks
    )


def fetch_current_canonicalizations(
    conn: psycopg.Connection, grouping_id: str
) -> dict[str, dict]:
    """Newest usable result per group from today's canonical prompt generation."""
    rows = conn.execute(
        "SELECT c.group_id, r.model, r.prompt_ref, i.response, i.error"
        " FROM kc_canonicalization c"
        " JOIN run_item i ON i.id = c.run_item_id"
        " JOIN run r ON r.id = i.run_id"
        " WHERE c.grouping_id = %s"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (grouping_id,),
    ).fetchall()
    results = {}
    for group_id, model, prompt_ref, response, error in rows:
        if group_id in results:
            continue
        if defaults.run_generation(STAGE, model, prompt_ref) != "current":
            continue
        parsed = canonicalization_of({"response": response, "error": error})
        if isinstance(parsed, dict):
            results[group_id] = parsed
    return results


def _already_usable(
    conn: psycopg.Connection,
    grouping_id: str,
    *,
    model: str,
    prompt_ref: str,
    prompt_sha: str,
) -> set[str]:
    rows = conn.execute(
        "SELECT c.group_id, i.response, i.error"
        " FROM kc_canonicalization c"
        " JOIN run_item i ON i.id = c.run_item_id"
        " JOIN run r ON r.id = i.run_id"
        " WHERE c.grouping_id = %s AND r.model = %s"
        "   AND r.prompt_ref = %s AND r.prompt_sha = %s"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (grouping_id, model, prompt_ref, prompt_sha),
    ).fetchall()
    return {
        group_id
        for group_id, response, error in rows
        if isinstance(canonicalization_of({"response": response, "error": error}), dict)
    }


def run_canonicalization(
    conn: psycopg.Connection,
    grouping_id: str,
    client,
    *,
    workers: int = DEFAULT_WORKERS,
    force: bool = False,
) -> dict:
    """Call the canonical prompt once for each selected composite."""
    prompt = harness.load_prompt(STAGE, PROMPT_VERSION, require_body=False)
    groups = fetch_group_tasks(conn, grouping_id)
    completed = set() if force else _already_usable(
        conn,
        grouping_id,
        model=client.model,
        prompt_ref=prompt.ref,
        prompt_sha=prompt.sha,
    )
    pending = [group for group in groups if group["id"] not in completed]
    if not pending:
        return {
            "run_id": None,
            "status": "unchanged",
            "ok": 0,
            "failed": 0,
            "groups": len(groups),
            "skipped": len(groups),
        }

    targets = [
        harness.Target(
            group["id"],
            None,
            None,
            tasks_markup(group["tasks"]),
            extra_fields={"tasks": tasks_markup(group["tasks"])},
        )
        for group in pending
    ]
    summary = harness.execute(
        conn,
        prompt,
        client,
        targets,
        workers=workers,
        run_params={"grouping_id": grouping_id},
    )
    item_ids = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM run_item WHERE run_id = %s ORDER BY id",
            (summary["run_id"],),
        ).fetchall()
    ]
    if len(item_ids) != len(pending):
        raise RuntimeError("canonical run item count does not match its composites")
    for item_id, group in zip(item_ids, pending):
        conn.execute(
            "INSERT INTO kc_canonicalization (run_item_id, grouping_id, group_id)"
            " VALUES (%s, %s, %s)",
            (item_id, grouping_id, group["id"]),
        )
    conn.commit()
    return {
        **summary,
        "groups": len(groups),
        "skipped": len(completed),
    }


execute = run_canonicalization


def cmd_run(args: argparse.Namespace) -> None:
    grouping_id = args.grouping
    extra = dict(THINKING_EXTRA)
    # The stage requires one structured answer; this replaces the shared
    # auto choice while preserving thinking and provider routing.
    extra.update(harness.load_tool(str(TOOL_PATH)))
    client = ModelClient(
        args.model,
        max_tokens=args.max_tokens,
        extra=extra,
    )
    with connect() as conn:
        grouping_id = grouping_id or latest_grouping_id(conn)
        summary = run_canonicalization(
            conn,
            grouping_id,
            client,
            workers=args.workers,
            force=args.force,
        )
        if summary["run_id"] is None:
            print(
                f"{grouping_id}: {summary['groups']} composite(s) already canonicalized"
            )
            return
        rows = conn.execute(
            "SELECT i.response, i.usage, i.duration_ms, i.error"
            " FROM run_item i WHERE i.run_id = %s ORDER BY i.id",
            (summary["run_id"],),
        ).fetchall()

    parsed = [
        canonicalization_of({"response": response, "error": error})
        for response, _, _, error in rows
    ]
    tally = {
        label: sum(
            1
            for result in parsed
            if (result.get("verdict") if isinstance(result, dict) else result) == label
        )
        for label in ("stated", "unsure", "error", "unparseable")
    }
    usage = report.aggregate_usage(
        [
            {"usage": usage, "duration_ms": duration_ms}
            for _, usage, duration_ms, _ in rows
        ]
    )
    duration = sum(duration_ms or 0 for _, _, duration_ms, _ in rows)
    counts = ", ".join(f"{count} {label}" for label, count in tally.items())
    print(
        f"{summary['run_id']} {summary['status']} on {grouping_id}: {counts},"
        f" {report.format_usage(usage) or 'no usage reported'},"
        f" {duration / 1000:.1f}s of model time"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.kc_canonical_statement", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="write a canonical statement for each composite")
    run.add_argument("--grouping", help="grouping snapshot; defaults to the latest")
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--workers", type=harness.positive_int, default=DEFAULT_WORKERS)
    run.add_argument("--max-tokens", type=harness.positive_int, default=DEFAULT_MAX_TOKENS)
    run.add_argument("--force", action="store_true", help="repeat even usable results")
    run.set_defaults(func=cmd_run)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
