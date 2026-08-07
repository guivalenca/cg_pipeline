"""Freeze the isolated two-source regex KC corpus and all judge candidates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from universe.kc_judge import fetch_candidate_data, generate_candidates
from universe.db import connect

from run_shadow_regex_pipeline import assert_isolated


STATEMENT_RUNS = ["r0015", "r0016"]
EMBEDDING_RUN = "r0029"
MODALITY_RUNS = ["r0017", "r0018", "r0019", "r0020", "r0021", "r0025", "r0026"]
KNOWLEDGE_RUNS = ["r0027", "r0028"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    assert_isolated()

    with connect() as conn:
        items, similarities, _ = fetch_candidate_data(
            conn,
            STATEMENT_RUNS,
            EMBEDDING_RUN,
            MODALITY_RUNS,
            KNOWLEDGE_RUNS,
            "deepseek/deepseek-v4-pro",
            "kc-judge/v003-surmise-pair",
            include_judged=True,
        )
        sources = {
            task_id: {"source_id": source_id, "source_title": source_title}
            for task_id, source_id, source_title in conn.execute(
                "SELECT t.id, sn.source_id, s.title FROM task t"
                " JOIN passage p ON p.id = t.passage_id"
                " JOIN artifact a ON a.id = p.artifact_id"
                " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
                " JOIN source s ON s.id = sn.source_id"
                " WHERE t.id = ANY(%s)",
                ([item["id"] for item in items],),
            ).fetchall()
        }

    items = [{**item, **sources[item["id"]]} for item in items]
    by_id = {item["id"]: item for item in items}
    candidates = [
        {
            "a": a,
            "b": b,
            "similarity": similarity,
            "cross_source": by_id[a]["source_id"] != by_id[b]["source_id"],
            "modality": by_id[a]["modality"],
            "knowledge": by_id[a]["knowledge"],
        }
        for a, b, similarity in generate_candidates(items, similarities)
    ]
    payload = {
        "name": "Concept Universe two-source regex shadow judge corpus v001",
        "frozen_at": "2026-08-07",
        "isolation": {
            "database": "universe_judge_shadow_regex_20260807",
            "production_database_touched": False,
        },
        "pipeline_runs": {
            "statement_runs": STATEMENT_RUNS,
            "embedding_run": EMBEDDING_RUN,
            "modality_runs": MODALITY_RUNS,
            "knowledge_runs": KNOWLEDGE_RUNS,
        },
        "candidate_policy": {"semantic_floor": 0.70, "semantic_cap": 6, "lexical_k": 5},
        "items": items,
        "similarities": [
            {"a": a, "b": b, "similarity": similarity}
            for (a, b), similarity in sorted(similarities.items())
        ],
        "candidates": candidates,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    cross = sum(candidate["cross_source"] for candidate in candidates)
    print(
        f"wrote {len(items)} items and {len(candidates)} candidates"
        f" ({cross} cross-source) to {args.out}"
    )


if __name__ == "__main__":
    main()
