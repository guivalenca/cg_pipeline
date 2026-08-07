"""Reproducible cost/quality research for the KC identity judge.

This module is deliberately outside the production runner.  It freezes the
current corpus plus reviewed gold pairs, measures candidate policies without
model calls, and can benchmark an alternative model configuration on exactly
the same pair inputs.

    python -m universe.judge_cost_eval snapshot --out evals/kc-judge-cost-v001.json
    python -m universe.judge_cost_eval evaluate \
        --data evals/kc-judge-cost-v001.json \
        --model deepseek/deepseek-v4-flash-0731 \
        --out reports/kc-judge-cost-flash.json
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from universe import harness
from universe.db import connect
from universe.kc_judge import (
    STAGE,
    bm25_score,
    fetch_candidate_data,
    parse_verdicts,
)
from universe.kc_judge_bench import DEFAULT_EXTRA
from universe.model_client import ModelClient, is_transient_failure


PROJECT_DIR = Path(__file__).resolve().parents[2]
PROMPT_QUALITY_DATA = PROJECT_DIR / "evals/prompt-quality-v001.json"
JUDGE_TOOL = PROJECT_DIR / "prompts/kc-judge/tool-v002.json"

CLEAN_GROUPS = {
    "kc-26960cf45080",
    "kc-5b27b0c4edd9",
    "kc-5c1626e0cd55",
    "kc-7b4726639b7c",
    "kc-930086e39837",
    "kc-9f32993c76cc",
    "kc-c4c0c3ebb1ab",
    "kc-c5cc8359f1cc",
    "kc-f2869532473f",
    "kc-f60fec4c46ec",
}
FALSE_GROUPS = {"kc-7947f7a84a32"}
AMBIGUOUS_GROUPS = {"kc-82710b2a02a5"}


def normalized_pair(a: str, b: str) -> tuple[str, str]:
    return tuple(sorted((a, b)))


def _latest_grouping(conn) -> tuple[str, dict]:
    row = conn.execute(
        "SELECT id, params FROM kc_grouping ORDER BY computed_at DESC, id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        raise SystemExit("no grouping snapshot found")
    return row[0], row[1]


def _group_members(conn, grouping_id: str) -> dict[str, list[str]]:
    rows = conn.execute(
        "SELECT group_id, array_agg(task_id ORDER BY task_id)"
        " FROM kc_group_member WHERE grouping_id = %s"
        " GROUP BY group_id ORDER BY group_id",
        (grouping_id,),
    ).fetchall()
    return {group_id: members for group_id, members in rows}


def _production_verdicts(conn, grouping_id: str) -> dict[tuple[str, str], dict]:
    rows = conn.execute(
        "SELECT v.task_a_id, v.task_b_id, v.a_implies_b, v.b_implies_a,"
        " i.usage, i.run_id"
        " FROM kc_grouping_verdict gv"
        " JOIN kc_verdict v ON v.run_item_id = gv.run_item_id"
        " JOIN run_item i ON i.id = v.run_item_id"
        " WHERE gv.grouping_id = %s",
        (grouping_id,),
    ).fetchall()
    return {
        normalized_pair(a, b): {
            "verdict_a_to_b": ab,
            "verdict_b_to_a": ba,
            "usage": usage,
            "run_id": run_id,
        }
        for a, b, ab, ba, usage, run_id in rows
    }


def _source_metadata(conn, task_ids: list[str]) -> dict[str, dict]:
    """Resolve the source behind each frozen task for incremental simulations."""
    rows = conn.execute(
        "SELECT t.id, p.artifact_id, sn.source_id, s.title"
        " FROM task t"
        " JOIN passage p ON p.id = t.passage_id"
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " JOIN source s ON s.id = sn.source_id"
        " WHERE t.id = ANY(%s)",
        (task_ids,),
    ).fetchall()
    return {
        task_id: {
            "artifact_id": artifact_id,
            "source_id": source_id,
            "source_title": source_title,
        }
        for task_id, artifact_id, source_id, source_title in rows
    }


def build_snapshot(conn) -> dict:
    grouping_id, params = _latest_grouping(conn)
    items, similarities, _ = fetch_candidate_data(
        conn,
        params["statements_from"],
        params["embedding_run"],
        params["modality_runs"],
        params["knowledge_runs"],
        params["judge_model"],
        params["judge_prompt"],
        build_key=params["build_key"],
        include_judged=True,
    )
    source_metadata = _source_metadata(conn, [item["id"] for item in items])
    items = [{**item, **source_metadata[item["id"]]} for item in items]
    by_id = {item["id"]: item for item in items}
    groups = _group_members(conn, grouping_id)
    production = _production_verdicts(conn, grouping_id)
    prior = json.loads(PROMPT_QUALITY_DATA.read_text())

    cases: dict[tuple[str, str], dict] = {}
    for case in prior["judge_cases"]:
        pair = normalized_pair(case["a"], case["b"])
        cases[pair] = {
            "id": case["id"],
            "a": pair[0],
            "b": pair[1],
            "bucket": "gold",
            "gold_a_clear_yes": (
                case["gold_a_clear_yes"] if pair[0] == case["a"]
                else case["gold_b_clear_yes"]
            ),
            "gold_b_clear_yes": (
                case["gold_b_clear_yes"] if pair[0] == case["a"]
                else case["gold_a_clear_yes"]
            ),
            "gold_merge": case["gold_merge"],
            "origin": "prompt-quality-v001",
        }

    reviewed_groups = [
        (group_id, "clean", True) for group_id in sorted(CLEAN_GROUPS)
    ] + [
        (group_id, "false", False) for group_id in sorted(FALSE_GROUPS)
    ] + [
        (group_id, "ambiguous", None) for group_id in sorted(AMBIGUOUS_GROUPS)
    ]
    for group_id, review, gold_merge in reviewed_groups:
        members = groups[group_id]
        if len(members) != 2:
            raise SystemExit(f"research snapshot expects pair group {group_id}")
        pair = normalized_pair(*members)
        if pair in cases:
            cases[pair]["reviewed_group"] = group_id
            continue
        cases[pair] = {
            "id": group_id,
            "a": pair[0],
            "b": pair[1],
            "bucket": "ambiguous" if review == "ambiguous" else "gold",
            "gold_a_clear_yes": True if review == "clean" else None,
            "gold_b_clear_yes": True if review == "clean" else None,
            "gold_merge": gold_merge,
            "origin": "g0003-manual-review",
            "reviewed_group": group_id,
        }

    frozen_cases = []
    for pair, case in sorted(cases.items(), key=lambda row: row[1]["id"]):
        if pair[0] not in by_id or pair[1] not in by_id:
            raise SystemExit(f"case {case['id']} references a task outside the live corpus")
        case = dict(case)
        case["similarity"] = similarities.get(pair)
        case["production"] = production.get(pair)
        frozen_cases.append(case)

    return {
        "name": "Concept Universe KC judge cost benchmark v001",
        "frozen_at": "2026-08-07",
        "grouping_id": grouping_id,
        "build": params,
        "metric_contract": {
            "primary": "candidate recall over unambiguous gold composite pairs",
            "hard_guardrails": [
                "100% candidate recall on gold composites",
                "zero new false composites on scored judge cases",
            ],
            "efficiency": "candidate calls and measured OpenRouter cost",
            "ambiguous_policy": "reported separately and excluded from promotion score",
        },
        "items": items,
        "similarities": [
            {"a": pair[0], "b": pair[1], "similarity": similarity}
            for pair, similarity in sorted(similarities.items())
        ],
        "cases": frozen_cases,
    }


def candidate_pairs(
    data: dict,
    *,
    floor: float = 0.70,
    semantic_cap: int = 6,
    lexical_k: int = 5,
    lexical_positive_only: bool = False,
    reciprocal_semantic: bool = False,
) -> tuple[set[tuple[str, str]], dict[tuple[str, str], set[str]]]:
    items = sorted(data["items"], key=lambda item: item["id"])
    by_id = {item["id"]: item for item in items}
    ids = [item["id"] for item in items]
    similarities = {
        normalized_pair(row["a"], row["b"]): row["similarity"]
        for row in data["similarities"]
    }
    semantic_neighbors: dict[str, list[str]] = {}
    for task_id in ids:
        neighbors = [
            (other_id, similarities.get(normalized_pair(task_id, other_id), 0.0))
            for other_id in ids if other_id != task_id
        ]
        neighbors = [row for row in neighbors if row[1] >= floor]
        neighbors.sort(key=lambda row: (-row[1], row[0]))
        semantic_neighbors[task_id] = [row[0] for row in neighbors[:semantic_cap]]

    proposed: dict[tuple[str, str], set[str]] = defaultdict(set)
    for task_id, neighbors in semantic_neighbors.items():
        for other_id in neighbors:
            if reciprocal_semantic and task_id not in semantic_neighbors.get(other_id, []):
                continue
            proposed[normalized_pair(task_id, other_id)].add("semantic")

    tokens = {
        item["id"]: re.findall(r"[a-z0-9_]+", item["statement"].lower())
        for item in items
    }
    all_docs = [tokens[task_id] for task_id in ids]
    for task_id in ids:
        scores = []
        for other_id in ids:
            if other_id == task_id:
                continue
            score = bm25_score(tokens[task_id], tokens[other_id], all_docs)
            scores.append((score, other_id))
        scores.sort(reverse=True)
        for score, other_id in scores[:lexical_k]:
            if lexical_positive_only and score <= 0:
                continue
            proposed[normalized_pair(task_id, other_id)].add("lexical")

    compatible = {
        pair: generators
        for pair, generators in proposed.items()
        if by_id[pair[0]]["modality"] == by_id[pair[1]]["modality"]
        and by_id[pair[0]]["knowledge"] == by_id[pair[1]]["knowledge"]
    }
    return set(compatible), compatible


def score_candidate_policy(data: dict, pairs: set[tuple[str, str]]) -> dict:
    positives = {
        normalized_pair(case["a"], case["b"])
        for case in data["cases"]
        if case["bucket"] == "gold" and case["gold_merge"] is True
    }
    negatives = {
        normalized_pair(case["a"], case["b"])
        for case in data["cases"]
        if case["bucket"] == "gold" and case["gold_merge"] is False
    }
    retained = positives & pairs
    return {
        "candidate_count": len(pairs),
        "gold_positive_count": len(positives),
        "gold_positive_retained": len(retained),
        "gold_positive_recall": len(retained) / len(positives),
        "missing_positive_ids": sorted(
            case["id"] for case in data["cases"]
            if case["bucket"] == "gold" and case["gold_merge"] is True
            and normalized_pair(case["a"], case["b"]) not in pairs
        ),
        "known_negative_candidates": len(negatives & pairs),
    }


def _rendered_prompt(data: dict, case: dict, prompt) -> str:
    by_id = {item["id"]: item for item in data["items"]}
    a, b = by_id[case["a"]], by_id[case["b"]]
    return prompt.render_fields({
        "a_statement": a["statement"], "a_task": a["body"], "a_answer": a["answer"],
        "b_statement": b["statement"], "b_task": b["body"], "b_answer": b["answer"],
    })


def evaluate_model(
    data: dict,
    model: str,
    extra: dict,
    workers: int,
    existing_results: list[dict] | None = None,
    prompt_version: str = "v003-surmise-pair",
    limit: int | None = None,
) -> dict:
    prompt = harness.load_prompt(STAGE, prompt_version, require_body=False)
    # The tool is forced by default. Research configurations may explicitly
    # relax only tool_choice (while retaining the declared tool and strict
    # parser) to test providers that support reasoning plus tools but reject
    # forced tool choice during thinking.
    request_extra = {**DEFAULT_EXTRA, **harness.load_tool(str(JUDGE_TOOL)), **extra}
    request_extra = {
        key: value for key, value in request_extra.items() if value is not None
    }
    client = ModelClient(model, extra=request_extra)
    cases = [case for case in data["cases"] if case["bucket"] == "gold"]
    completed = {
        result["case_id"]: result
        for result in (existing_results or [])
        if result.get("parsed") and not result.get("error")
    }
    cases_to_run = [case for case in cases if case["id"] not in completed]
    if limit is not None:
        cases_to_run = cases_to_run[:limit]

    def run_case(case: dict) -> dict:
        rendered = _rendered_prompt(data, case, prompt)
        for attempt in range(2):
            try:
                response, usage, duration_ms = client.complete(rendered)
                return {
                    "case_id": case["id"],
                    "parsed": parse_verdicts(response),
                    "usage": usage,
                    "duration_ms": duration_ms,
                    "attempts": attempt + 1,
                    "error": None,
                }
            except Exception as exc:
                if attempt == 0 and is_transient_failure(exc):
                    continue
                return {
                    "case_id": case["id"], "parsed": None, "usage": None,
                    "duration_ms": None, "attempts": attempt + 1,
                    "error": f"{type(exc).__name__}: {exc}",
                }

    results = list(completed.values())
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(cases_to_run)))) as pool:
        futures = [pool.submit(run_case, case) for case in cases_to_run]
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: row["case_id"])
    return {
        "dataset": data["name"],
        "model": model,
        "prompt_ref": prompt.ref,
        "extra": request_extra,
        "resumed_cases": len(completed),
        "calls_executed": len(cases_to_run),
        "results": results,
        "scores": score_model_results(data, results),
    }


def score_model_results(data: dict, results: list[dict]) -> dict:
    cases = {case["id"]: case for case in data["cases"] if case["bucket"] == "gold"}
    by_case = {result["case_id"]: result for result in results}
    merge_correct = false_merges = missed_merges = scored_cases = 0
    direction_correct = direction_total = 0
    for case_id, case in cases.items():
        parsed = (by_case.get(case_id) or {}).get("parsed")
        if not parsed:
            continue
        scored_cases += 1
        ab = parsed.get("verdict_a_to_b") == "clear_yes"
        ba = parsed.get("verdict_b_to_a") == "clear_yes"
        predicted_merge = ab and ba
        merge_correct += predicted_merge == case["gold_merge"]
        false_merges += predicted_merge and case["gold_merge"] is False
        missed_merges += not predicted_merge and case["gold_merge"] is True
        if case.get("gold_a_clear_yes") is not None:
            direction_total += 2
            direction_correct += ab == case["gold_a_clear_yes"]
            direction_correct += ba == case["gold_b_clear_yes"]

    usages = [result["usage"] for result in results if result.get("usage")]
    total_cost = sum(float(usage.get("cost") or 0) for usage in usages)
    providers: dict[str, int] = {}
    for usage in usages:
        provider = str(usage.get("provider") or "unknown")
        providers[provider] = providers.get(provider, 0) + 1
    return {
        "cases": len(cases),
        "scored_cases": scored_cases,
        "successful_calls": scored_cases,
        "failed_calls": len(cases) - scored_cases,
        "merge_accuracy": merge_correct / scored_cases if scored_cases else None,
        "false_merges": false_merges,
        "missed_merges": missed_merges,
        "direction_accuracy": (
            direction_correct / direction_total if direction_total else None
        ),
        "total_cost": total_cost,
        "mean_cost_per_call": total_cost / len(usages) if usages else None,
        "prompt_tokens": sum(int(usage.get("prompt_tokens") or 0) for usage in usages),
        "completion_tokens": sum(int(usage.get("completion_tokens") or 0) for usage in usages),
        "reasoning_tokens": sum(
            int((usage.get("completion_tokens_details") or {}).get("reasoning_tokens") or 0)
            for usage in usages
        ),
        "providers": providers,
        "attempts": sum(int(result.get("attempts") or 1) for result in results),
    }


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="universe.judge_cost_eval", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--out", required=True)
    evaluate = sub.add_parser("evaluate")
    evaluate.add_argument("--data", required=True)
    evaluate.add_argument("--model", required=True)
    evaluate.add_argument(
        "--prompt", default="v003-surmise-pair", help="prompt version under prompts/kc-judge"
    )
    evaluate.add_argument("--extra", type=json.loads, default={})
    evaluate.add_argument("--workers", type=int, default=4)
    evaluate.add_argument("--limit", type=int)
    evaluate.add_argument(
        "--resume", help="Reuse successful cases from a prior matching result JSON"
    )
    evaluate.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if args.command == "snapshot":
        with connect() as conn:
            payload = build_snapshot(conn)
    else:
        prior = json.loads(Path(args.resume).read_text()) if args.resume else None
        if prior and prior.get("model") != args.model:
            raise SystemExit("--resume model does not match --model")
        payload = evaluate_model(
            json.loads(Path(args.data).read_text()),
            args.model,
            args.extra,
            args.workers,
            prior.get("results") if prior else None,
            args.prompt,
            args.limit,
        )
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(payload.get("scores") or {
        "items": len(payload["items"]), "cases": len(payload["cases"])
    }, indent=2))


if __name__ == "__main__":
    main()
