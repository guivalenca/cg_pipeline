"""Run the two-source regex experiment in its dedicated Postgres database.

This intentionally delegates every stage to the production pipeline CLI while
refusing to run unless DATABASE_URL names the experiment database.  The judge
comparison is a separate research step; this script stops before corpus-wide
embedding/judging so both sources share one frozen KC corpus.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

from universe.db import connect, database_url
from universe import defaults
from universe.ingest import next_step
from universe.passages import materialize as materialize_passages
from universe.tasks import materialize as materialize_tasks


PROJECT_DIR = Path(__file__).resolve().parents[1]
EXPERIMENT_DATABASE = "universe_judge_shadow_regex_20260807"
SOURCE_IDS = [
    "si-mod6-0016-expressoes-regulares",
    "si-mod6-0017-regexp-expressoes-regulares-dicionario-do-programador",
]
STOP_STAGES = {"task-embedding", "kc-judge", "grouped"}


def assert_isolated() -> None:
    url = database_url()
    if not url.rstrip("/").endswith(f"/{EXPERIMENT_DATABASE}"):
        raise SystemExit(
            "refusing to run outside the isolated experiment database: " + url
        )


def planned_step(source_id: str) -> dict:
    with connect() as conn:
        return next_step(conn, source_id)


def current_run_ids(stage: str, source_id: str) -> list[str]:
    """Current-recipe runs for one source, oldest first.

    Passage cutting has a deliberate two-step representation: the model run
    records block boundaries, then those boundaries are materialized as
    passage rows.  The production triage CLI normally performs the latter,
    but the progress planner cannot select triage until passages exist.  The
    shadow runner closes that loop explicitly and idempotently.
    """
    with connect() as conn:
        rows = conn.execute(
            "SELECT r.id, r.model, r.prompt_ref FROM run r"
            " WHERE r.stage = %s AND r.status = 'done' AND EXISTS ("
            "   SELECT 1 FROM run_item i"
            "   JOIN artifact a ON a.id = i.artifact_id"
            "   JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            "   WHERE i.run_id = r.id AND sn.source_id = %s)"
            " ORDER BY r.started_at, r.id",
            (stage, source_id),
        ).fetchall()
    return [
        run_id
        for run_id, model, prompt_ref in rows
        if defaults.run_generation(stage, model, prompt_ref) == "current"
    ]


def materialize_current_cuts(source_id: str) -> None:
    with connect() as conn:
        for run_id in current_run_ids("passage-cuts", source_id):
            counts = materialize_passages(conn, run_id)
            print(f"MATERIALIZED {source_id} {run_id} {counts}", flush=True)


def materialize_current_tasks(source_id: str) -> None:
    with connect() as conn:
        for run_id in current_run_ids("task-generation", source_id):
            counts = materialize_tasks(conn, run_id)
            print(f"MATERIALIZED {source_id} {run_id} {counts}", flush=True)


def run_one(source_id: str) -> str | None:
    step = planned_step(source_id)
    stage = step["stage"]
    if stage is None or stage in STOP_STAGES:
        return stage
    if not step["runnable"]:
        raise SystemExit(f"{source_id} {stage} is not runnable: {step['reason']}")
    print(f"RUN {source_id} {stage}", flush=True)
    argv = list(step["argv"])
    if stage == "task-modality":
        argv[argv.index("--workers") + 1] = "1"
    subprocess.run(
        argv,
        cwd=PROJECT_DIR,
        env=os.environ.copy(),
        check=True,
    )
    if stage == "passage-cuts":
        materialize_current_cuts(source_id)
    elif stage == "task-generation":
        materialize_current_tasks(source_id)
    print(f"DONE {source_id} {stage}", flush=True)
    return stage


def run_to_axes() -> None:
    while True:
        pending = []
        for source_id in SOURCE_IDS:
            stage = planned_step(source_id)["stage"]
            print(f"NEXT {source_id} {stage}", flush=True)
            if stage not in STOP_STAGES and stage is not None:
                pending.append(source_id)
        if not pending:
            return
        for source_id in pending:
            run_one(source_id)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=["status", "next", "run-to-axes"]
    )
    parser.add_argument("--source", choices=SOURCE_IDS)
    args = parser.parse_args()
    assert_isolated()

    if args.command == "status":
        for source_id in SOURCE_IDS:
            step = planned_step(source_id)
            print(source_id, step["stage"], step["stage_status"])
    elif args.command == "next":
        if not args.source:
            parser.error("next requires --source")
        run_one(args.source)
    else:
        run_to_axes()


if __name__ == "__main__":
    main()
