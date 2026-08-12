"""Build mutual-clear_yes graph, extract complete cliques, materialize kc_group rows."""

import argparse
import hashlib

import psycopg
from psycopg.types.json import Jsonb

from universe import defaults, judge_manifest, pipeline_lease
from universe.db import connect


def compute_groups(verdicts: list[tuple[str, str, str, str]]) -> list[dict]:
    """Return the non-singleton perfect cliques in the mutual-clear graph."""
    adjacency: dict[str, set[str]] = {}
    for task_a, task_b, a_implies_b, b_implies_a in verdicts:
        if task_a == task_b:
            continue
        if a_implies_b != "clear_yes" or b_implies_a != "clear_yes":
            continue
        adjacency.setdefault(task_a, set()).add(task_b)
        adjacency.setdefault(task_b, set()).add(task_a)

    groups = []
    unseen = set(adjacency)
    while unseen:
        start = min(unseen)
        stack = [start]
        component = set()
        while stack:
            task_id = stack.pop()
            if task_id in component:
                continue
            component.add(task_id)
            stack.extend(adjacency[task_id] - component)
        unseen -= component

        members = sorted(component)
        if all(
            task_b in adjacency[task_a]
            for index, task_a in enumerate(members)
            for task_b in members[index + 1 :]
        ):
            digest = hashlib.sha256("\n".join(members).encode()).hexdigest()[:12]
            groups.append({"members": members, "id": f"kc-{digest}"})

    return sorted(groups, key=lambda group: group["members"])


def next_grouping_id(conn: psycopg.Connection) -> str:
    number = conn.execute(
        "SELECT coalesce(max(substring(id from 2)::int), 0) + 1 FROM kc_grouping"
        " WHERE id ~ '^g[0-9]+$'"
    ).fetchone()[0]
    return f"g{number:04d}"


def fetch_latest_verdicts(
    conn: psycopg.Connection,
    *,
    build_key: str | None = None,
    before=None,
) -> list[tuple[str, str, str, str]]:
    """The newest verdict per pair in one build (or across audit history).

    ``build_key`` is what live Universe consumers should pass.  Omitting it
    intentionally retains the old audit-ledger behavior for reports and
    backwards-compatible callers.  ``before`` gives legacy snapshots a
    coherent time boundary when they predate explicit build provenance.
    """
    return [record[:4] for record in _fetch_verdict_records(
        conn, build_key=build_key, before=before
    )]


def _fetch_verdict_records(
    conn: psycopg.Connection,
    *,
    build_key: str | None = None,
    before=None,
    run_item_ids: list[str] | None = None,
) -> list[tuple[str, str, str, str, str]]:
    """Verdicts plus their immutable run-item ids for snapshot manifests."""
    clauses = []
    params = []
    if build_key is not None:
        clauses.append("build_key = %s")
        params.append(build_key)
    if before is not None:
        clauses.append("created_at <= %s")
        params.append(before)
    if run_item_ids is not None:
        clauses.append("run_item_id = ANY(%s)")
        params.append(run_item_ids)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return conn.execute(
        "SELECT DISTINCT ON (task_a_id, task_b_id)"
        " task_a_id, task_b_id, a_implies_b, b_implies_a, run_item_id"
        " FROM kc_verdict" + where +
        " ORDER BY task_a_id, task_b_id, created_at DESC, run_item_id DESC",
        params,
    ).fetchall()


def fetch_grouping_verdicts(
    conn: psycopg.Connection, grouping_id: str
) -> list[tuple[str, str, str, str]]:
    """The exact edge facts committed into one grouping snapshot."""
    return conn.execute(
        "SELECT v.task_a_id, v.task_b_id, v.a_implies_b, v.b_implies_a"
        " FROM kc_grouping_verdict gv"
        " JOIN kc_verdict v ON v.run_item_id = gv.run_item_id"
        " WHERE gv.grouping_id = %s"
        " ORDER BY v.task_a_id, v.task_b_id",
        (grouping_id,),
    ).fetchall()


def _current_runs(conn: psycopg.Connection, stage: str) -> list[str]:
    """Completed runs from today's recipe for the legacy global dashboard."""
    rows = conn.execute(
        "SELECT id, model, prompt_ref FROM run"
        " WHERE stage = %s AND status = 'done' ORDER BY started_at, id",
        (stage,),
    ).fetchall()
    return [
        run_id
        for run_id, model, prompt_ref in rows
        if defaults.run_generation(stage, model, prompt_ref) == "current"
    ]


def current_build_inputs(conn: psycopg.Connection) -> dict:
    """Best-effort legacy-global inputs used only by the old dashboard.

    Product Universe reads are manifest-pinned through ``kc_progress``.  This
    compatibility projection must therefore never be used to authorize work.
    """
    embeddings = _current_runs(conn, "task-embedding")
    judge_runs = _current_runs(conn, "kc-judge")
    judge_run_id = judge_runs[-1] if judge_runs else None
    manifest = judge_manifest.read(conn, judge_run_id) if judge_run_id else None
    judge_params = (
        conn.execute("SELECT params FROM run WHERE id = %s", (judge_run_id,)).fetchone()[0]
        if judge_run_id
        else {}
    ) or {}
    judge = defaults.STAGE_DEFAULTS["kc-judge"]
    return {
        "build_key": manifest.build_key if manifest else judge_params.get("build_key"),
        "statements_from": _current_runs(conn, "kc-statement"),
        "embedding_run": embeddings[-1] if embeddings else None,
        "modality_runs": _current_runs(conn, "task-modality"),
        "knowledge_runs": _current_runs(conn, "task-knowledge"),
        "judge_run_id": judge_run_id if manifest else None,
        "candidate_count": manifest.count if manifest else None,
        "candidate_manifest_sha256": manifest.sha256 if manifest else None,
        "judge_model": judge["model"],
        "judge_prompt": judge["prompt_ref"],
    }


def grouping_staleness(
    conn: psycopg.Connection, grouping: dict | None
) -> tuple[bool, list[str]]:
    """Say whether today's reference chain differs from a pinned snapshot."""
    if grouping is None:
        return True, ["no grouping snapshot has been computed"]
    params = grouping.get("params") or {}
    pinned = {
        "build_key": params.get("build_key"),
        "statements_from": params.get("statements_from"),
        "embedding_run": params.get("embedding_run"),
        "modality_runs": params.get("modality_runs"),
        "knowledge_runs": params.get("knowledge_runs"),
        "judge_run_id": params.get("judge_run_id"),
        "candidate_count": params.get("candidate_count"),
        "candidate_manifest_sha256": params.get("candidate_manifest_sha256"),
        "judge_model": params.get("judge_model"),
        "judge_prompt": params.get("judge_prompt"),
    }
    # Hand-made and pre-0012 test snapshots have no provenance.  Preserve
    # their timestamp semantics; the migration pins every production snapshot.
    if not params.get("build_key"):
        row = conn.execute(
            "SELECT max(coalesce(finished_at, started_at)) FROM run"
            " WHERE status = 'done' AND stage IN"
            " ('kc-statement','task-modality','task-knowledge','task-embedding','kc-judge')"
        ).fetchone()
        newest = row[0] if row else None
        stale = newest is not None and newest > grouping["computed_at"]
        return (stale, ["newer pipeline outputs exist"] if stale else [])

    current = current_build_inputs(conn)
    labels = {
        "build_key": "judge build",
        "statements_from": "knowledge statements",
        "embedding_run": "embeddings",
        "modality_runs": "modality classifications",
        "knowledge_runs": "knowledge classifications",
        "judge_run_id": "certified judge run",
        "candidate_count": "candidate count",
        "candidate_manifest_sha256": "candidate manifest",
        "judge_model": "judge model",
        "judge_prompt": "judge prompt",
    }
    reasons = [
        f"current {labels[key]} differ from the snapshot"
        for key in pinned
        if pinned[key] != current[key]
    ]
    return bool(reasons), reasons


def build_context(conn: psycopg.Connection, judge_run_id: str) -> dict:
    """Read one certified judge run's exact grouping inputs."""
    manifest = judge_manifest.require(conn, judge_run_id)
    row = conn.execute(
        "SELECT model, prompt_ref, prompt_sha, params FROM run"
        " WHERE id = %s AND stage = 'kc-judge' AND status = 'done'",
        (judge_run_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"no certified judge run {judge_run_id}")
    model, prompt_ref, prompt_sha, params = row
    return {
        "judge_run_id": judge_run_id,
        "build_key": manifest.build_key,
        "statements_from": params.get("statements_from") or [],
        "embedding_run": params.get("embedding_run"),
        "modality_runs": params.get("modality_runs") or [],
        "knowledge_runs": params.get("knowledge_runs") or [],
        "judge_model": model,
        "judge_prompt": prompt_ref,
        "judge_prompt_sha": prompt_sha,
        "candidate_count": manifest.count,
        "candidate_manifest_sha256": manifest.sha256,
    }


def compute_snapshot(
    conn: psycopg.Connection,
    *,
    judge_run_id: str | None = None,
    dry_run: bool = False,
) -> tuple[str | None, list[dict]]:
    """Compute cliques from one certified manifest and persist a snapshot.

    Omitting ``judge_run_id`` retains the historical audit-ledger projection
    for direct library callers. The production CLI always requires an exact
    certified judge run.
    """
    manifest = (
        judge_manifest.require(conn, judge_run_id) if judge_run_id else None
    )
    context = build_context(conn, judge_run_id) if judge_run_id else {}
    records = _fetch_verdict_records(
        conn,
        run_item_ids=list(manifest.run_item_ids) if manifest is not None else None,
    )
    if manifest is not None and (
        manifest.count != len(records)
        or set(manifest.run_item_ids) != {record[4] for record in records}
    ):
        raise RuntimeError(
            f"certified judge run {judge_run_id} has an invalid candidate manifest"
        )
    verdicts = [record[:4] for record in records]
    groups = compute_groups(verdicts)
    if dry_run:
        return None, groups
    # Serialize the human-readable id allocation through commit. The grouped
    # stage normally has a corpus lease; this also removes the database PK
    # race for direct operational invocations.
    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
        ("universe:kc-grouping-id",),
    )
    grouping_id = next_grouping_id(conn)
    supervisor = pipeline_lease.current_supervisor(required=True)
    if supervisor is not None:
        supervisor.fence(conn)
    conn.execute(
        "INSERT INTO kc_grouping (id, params) VALUES (%s, %s)",
        (
            grouping_id,
            Jsonb(
                {
                    "rule": "mutual_clear_yes_perfect_clique",
                    "verdict_policy": (
                        "exact_certified_judge_manifest"
                        if manifest is not None
                        else "latest_per_pair_audit_history"
                    ),
                    "verdict_count": len(verdicts),
                    **context,
                }
            ),
        ),
    )
    for group in groups:
        conn.execute(
            "INSERT INTO kc_group (grouping_id, id) VALUES (%s, %s)",
            (grouping_id, group["id"]),
        )
        for task_id in group["members"]:
            conn.execute(
                "INSERT INTO kc_group_member (grouping_id, group_id, task_id)"
                " VALUES (%s, %s, %s)",
                (grouping_id, group["id"], task_id),
            )
    for *_, run_item_id in records:
        conn.execute(
            "INSERT INTO kc_grouping_verdict (grouping_id, run_item_id)"
            " VALUES (%s, %s)",
            (grouping_id, run_item_id),
        )
    conn.commit()
    return grouping_id, groups


def list_groups(conn: psycopg.Connection) -> list[tuple[str, str, int]]:
    """Return every materialized group with its member count."""
    return conn.execute(
        "SELECT g.grouping_id, g.id, count(m.task_id)::int"
        " FROM kc_group g"
        " LEFT JOIN kc_group_member m"
        "   ON m.grouping_id = g.grouping_id AND m.group_id = g.id"
        " GROUP BY g.grouping_id, g.id"
        " ORDER BY g.grouping_id, g.id"
    ).fetchall()


def cmd_compute(args: argparse.Namespace) -> None:
    with connect() as conn:
        grouping_id, groups = compute_snapshot(
            conn,
            judge_run_id=args.judge_run,
            dry_run=args.dry_run,
        )
    if args.dry_run:
        print(f"{len(groups)} group(s); no rows written")
    else:
        print(f"{grouping_id}: {len(groups)} group(s)")


def cmd_list(args: argparse.Namespace) -> None:
    with connect() as conn:
        groups = list_groups(conn)
    if not groups:
        print("no groups yet")
        return
    print(f"{'grouping':<10} {'group':<16} {'members':>7}")
    for grouping_id, group_id, count in groups:
        print(f"{grouping_id:<10} {group_id:<16} {count:>7}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.kc_groups", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    compute = sub.add_parser("compute", help="materialize a new clique snapshot")
    compute.add_argument(
        "--judge-run", required=True, help="exact certified kc-judge run to group"
    )
    compute.add_argument("--dry-run", action="store_true")
    compute.set_defaults(func=cmd_compute)
    sub.add_parser("list", help="show all materialized groups").set_defaults(func=cmd_list)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
