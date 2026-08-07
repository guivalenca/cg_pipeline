"""Snapshot ledger metrics from the isolated two-source regex pipeline."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from universe.db import connect

from run_shadow_regex_pipeline import SOURCE_IDS, assert_isolated


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    assert_isolated()

    with connect() as conn:
        rows = conn.execute(
            "SELECT r.id, r.stage, r.model, r.prompt_ref, r.status,"
            " i.error, i.usage, i.duration_ms"
            " FROM run r LEFT JOIN run_item i ON i.run_id = r.id"
            " ORDER BY r.started_at, r.id, i.id"
        ).fetchall()
        stage_counts = {
            source_id: {
                "blocks": conn.execute(
                    "SELECT count(*) FROM block b JOIN artifact a ON a.id=b.artifact_id"
                    " JOIN source_snapshot sn ON sn.id=a.snapshot_id"
                    " WHERE sn.source_id=%s",
                    (source_id,),
                ).fetchone()[0],
                "passages": conn.execute(
                    "SELECT count(*) FROM passage p JOIN artifact a ON a.id=p.artifact_id"
                    " JOIN source_snapshot sn ON sn.id=a.snapshot_id"
                    " WHERE sn.source_id=%s",
                    (source_id,),
                ).fetchone()[0],
                "tasks_materialized": conn.execute(
                    "SELECT count(*) FROM task t JOIN passage p ON p.id=t.passage_id"
                    " JOIN artifact a ON a.id=p.artifact_id"
                    " JOIN source_snapshot sn ON sn.id=a.snapshot_id"
                    " WHERE sn.source_id=%s",
                    (source_id,),
                ).fetchone()[0],
                "final_kcs": conn.execute(
                    "SELECT count(DISTINCT e.task_id) FROM task_embedding e"
                    " JOIN run_item i ON i.id=e.run_item_id"
                    " JOIN task t ON t.id=e.task_id JOIN passage p ON p.id=t.passage_id"
                    " JOIN artifact a ON a.id=p.artifact_id"
                    " JOIN source_snapshot sn ON sn.id=a.snapshot_id"
                    " WHERE i.run_id='r0029' AND sn.source_id=%s",
                    (source_id,),
                ).fetchone()[0],
            }
            for source_id in SOURCE_IDS
        }

    runs: dict[str, dict] = {}
    for run_id, stage, model, prompt_ref, status, error, usage, duration_ms in rows:
        run = runs.setdefault(
            run_id,
            {
                "run_id": run_id,
                "stage": stage,
                "model": model,
                "prompt_ref": prompt_ref,
                "status": status,
                "items": 0,
                "errors": 0,
                "cost": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "reasoning_tokens": 0,
                "duration_ms_sum": 0,
                "providers": Counter(),
            },
        )
        if usage is None and error is None and duration_ms is None:
            continue
        run["items"] += 1
        run["errors"] += int(error is not None)
        run["duration_ms_sum"] += int(duration_ms or 0)
        if usage:
            run["cost"] += float(usage.get("cost") or 0)
            run["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            run["completion_tokens"] += int(usage.get("completion_tokens") or 0)
            run["reasoning_tokens"] += int(
                (usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0
            )
            if usage.get("provider"):
                run["providers"][usage["provider"]] += 1
    for run in runs.values():
        run["providers"] = dict(run["providers"])

    by_stage: dict[str, dict] = {}
    for run in runs.values():
        stage = by_stage.setdefault(
            run["stage"],
            {
                "stage": run["stage"],
                "runs": 0,
                "items": 0,
                "errors": 0,
                "cost": 0.0,
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "reasoning_tokens": 0,
                "duration_ms_sum": 0,
            },
        )
        stage["runs"] += 1
        for key in (
            "items", "errors", "cost", "prompt_tokens", "completion_tokens",
            "reasoning_tokens", "duration_ms_sum",
        ):
            stage[key] += run[key]

    payload = {
        "name": "Concept Universe regex shadow pipeline metrics v001",
        "database": "universe_judge_shadow_regex_20260807",
        "production_database_touched": False,
        "source_counts": stage_counts,
        "runs": list(runs.values()),
        "stages": list(by_stage.values()),
        "totals": {
            "runs": len(runs),
            "items": sum(run["items"] for run in runs.values()),
            "errors": sum(run["errors"] for run in runs.values()),
            "cost": sum(run["cost"] for run in runs.values()),
            "prompt_tokens": sum(run["prompt_tokens"] for run in runs.values()),
            "completion_tokens": sum(run["completion_tokens"] for run in runs.values()),
            "reasoning_tokens": sum(run["reasoning_tokens"] for run in runs.values()),
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload["totals"], indent=2))


if __name__ == "__main__":
    main()
