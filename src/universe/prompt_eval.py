"""Run the frozen modality/judge prompt comparison without touching the ledger."""

import argparse
import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from universe import harness
from universe.ingest import MODALITY_EXTRA
from universe.kc_judge import parse_verdicts
from universe.kc_judge_bench import DEFAULT_EXTRA, DEFAULT_MODEL
from universe.model_client import ModelClient, is_transient_failure
from universe.task_modality import modality_of


PROJECT_DIR = Path(__file__).resolve().parents[2]
MODALITY_TOOL = PROJECT_DIR / "prompts/task-modality/tool-v001.json"
JUDGE_TOOL = PROJECT_DIR / "prompts/kc-judge/tool-v002.json"


def _client(model: str, stage: str) -> ModelClient:
    extra = dict(MODALITY_EXTRA if stage == "modality" else DEFAULT_EXTRA)
    extra.update(harness.load_tool(str(MODALITY_TOOL if stage == "modality" else JUDGE_TOOL)))
    return ModelClient(model, extra=extra)


def _call(client: ModelClient, rendered: str):
    for attempt in range(2):
        try:
            return client.complete(rendered)
        except Exception as exc:
            if attempt == 0 and is_transient_failure(exc):
                time.sleep(2)
                continue
            raise


def _jobs(data: dict, stage: str, prompt_name: str, prompt) -> list[dict]:
    cases = data[f"{stage}_cases"]
    repeated = set(data["repeat_cases"][stage])
    jobs = []
    for case in cases:
        repetitions = 2 if case["id"] in repeated else 1
        for repetition in range(1, repetitions + 1):
            if stage == "modality":
                item = data["items"][case["item"]]
                fields = {"task": item["task"], "answer": item["answer"]}
            else:
                a, b = data["items"][case["a"]], data["items"][case["b"]]
                fields = {
                    "a_statement": a["statement"],
                    "a_task": a["task"],
                    "a_answer": a["answer"],
                    "b_statement": b["statement"],
                    "b_task": b["task"],
                    "b_answer": b["answer"],
                }
            jobs.append(
                {
                    "stage": stage,
                    "prompt": prompt_name,
                    "case": case,
                    "repetition": repetition,
                    "rendered": prompt.render_fields(fields),
                }
            )
    return jobs


def _run_job(job: dict, client: ModelClient) -> dict:
    result = {key: job[key] for key in ("stage", "prompt", "repetition")}
    result["case_id"] = job["case"]["id"]
    try:
        response, usage, duration_ms = _call(client, job["rendered"])
        if job["stage"] == "modality":
            parsed = modality_of({"response": response, "error": None})
            if not isinstance(parsed, dict):
                raise ValueError(f"unusable modality response: {parsed}")
        else:
            parsed = parse_verdicts(response)
        result.update(
            {
                "parsed": parsed,
                "usage": usage,
                "duration_ms": duration_ms,
                "error": None,
            }
        )
    except Exception as exc:
        result.update(
            {
                "parsed": None,
                "usage": None,
                "duration_ms": None,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    return result


def _scores(data: dict, results: list[dict], prompt_name: str) -> dict:
    primary = {
        (result["stage"], result["case_id"]): result
        for result in results
        if result["prompt"] == prompt_name and result["repetition"] == 1
    }
    modality_correct = 0
    modality_total = len(data["modality_cases"])
    critical_correct = critical_total = 0
    for case in data["modality_cases"]:
        result = primary[("modality", case["id"])]
        correct = bool(result["parsed"] and result["parsed"].get("verdict") == case["gold"])
        modality_correct += correct
        if case.get("critical"):
            critical_total += 1
            critical_correct += correct

    direction_correct = 0
    merge_correct = 0
    false_merges = missed_merges = 0
    modality_by_item = {
        case["item"]: (primary[("modality", case["id"])]["parsed"] or {}).get("verdict")
        for case in data["modality_cases"]
    }
    integrated_merge_correct = 0
    integrated_false_merges = integrated_missed_merges = 0
    for case in data["judge_cases"]:
        parsed = primary[("judge", case["id"])]["parsed"] or {}
        predicted_a = parsed.get("verdict_a_to_b") == "clear_yes"
        predicted_b = parsed.get("verdict_b_to_a") == "clear_yes"
        direction_correct += predicted_a == case["gold_a_clear_yes"]
        direction_correct += predicted_b == case["gold_b_clear_yes"]
        predicted_merge = predicted_a and predicted_b
        merge_correct += predicted_merge == case["gold_merge"]
        false_merges += predicted_merge and not case["gold_merge"]
        missed_merges += not predicted_merge and case["gold_merge"]
        same_modality = (
            modality_by_item.get(case["a"]) is not None
            and modality_by_item.get(case["a"]) == modality_by_item.get(case["b"])
        )
        integrated_merge = predicted_merge and same_modality
        integrated_merge_correct += integrated_merge == case["gold_merge"]
        integrated_false_merges += integrated_merge and not case["gold_merge"]
        integrated_missed_merges += not integrated_merge and case["gold_merge"]

    consistency = []
    for stage, case_ids in data["repeat_cases"].items():
        for case_id in case_ids:
            repeated = [
                result
                for result in results
                if result["prompt"] == prompt_name
                and result["stage"] == stage
                and result["case_id"] == case_id
            ]
            if stage == "modality":
                labels = [
                    (result["parsed"] or {}).get("verdict") for result in repeated
                ]
            else:
                labels = [
                    (
                        (result["parsed"] or {}).get("verdict_a_to_b"),
                        (result["parsed"] or {}).get("verdict_b_to_a"),
                    )
                    for result in repeated
                ]
            consistency.append(len(set(labels)) == 1)

    modality_accuracy = modality_correct / modality_total
    direction_accuracy = direction_correct / (2 * len(data["judge_cases"]))
    merge_accuracy = merge_correct / len(data["judge_cases"])
    negative_merges = sum(not case["gold_merge"] for case in data["judge_cases"])
    false_merge_safety = 1 - false_merges / negative_merges
    quality = 100 * (
        0.35 * modality_accuracy
        + 0.25 * direction_accuracy
        + 0.25 * merge_accuracy
        + 0.15 * false_merge_safety
    )
    return {
        "quality_score": round(quality, 1),
        "modality_accuracy": round(modality_accuracy, 4),
        "critical_modality_accuracy": round(critical_correct / critical_total, 4),
        "judge_direction_accuracy": round(direction_accuracy, 4),
        "judge_merge_accuracy": round(merge_accuracy, 4),
        "false_merges": false_merges,
        "missed_merges": missed_merges,
        "integrated_merge_accuracy": round(
            integrated_merge_correct / len(data["judge_cases"]), 4
        ),
        "integrated_false_merges": integrated_false_merges,
        "integrated_missed_merges": integrated_missed_merges,
        "repeat_consistency": round(sum(consistency) / len(consistency), 4),
        "failed_calls": sum(
            result["error"] is not None
            for result in results
            if result["prompt"] == prompt_name
        ),
    }


def run(args) -> dict:
    data = json.loads(Path(args.data).read_text())
    prompts = {
        "current": {
            "modality": harness.load_prompt("task-modality", "v002", require_body=False),
            "judge": harness.load_prompt("kc-judge", "v002-surmise-pair", require_body=False),
        },
        "candidate": {
            "modality": harness.load_prompt("task-modality", "v003", require_body=False),
            "judge": harness.load_prompt("kc-judge", "v003-surmise-pair", require_body=False),
        },
    }
    clients = {
        (prompt_name, stage): _client(args.model, stage)
        for prompt_name in prompts
        for stage in ("modality", "judge")
    }
    jobs = [
        job
        for prompt_name, stage_prompts in prompts.items()
        for stage, prompt in stage_prompts.items()
        for job in _jobs(data, stage, prompt_name, prompt)
    ]
    results = []
    if args.resume and Path(args.out).exists():
        results = json.loads(Path(args.out).read_text()).get("results") or []
    completed = {
        (row["prompt"], row["stage"], row["case_id"], row["repetition"])
        for row in results
    }
    pending_jobs = [
        job
        for job in jobs
        if (job["prompt"], job["stage"], job["case"]["id"], job["repetition"])
        not in completed
    ]
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_run_job, job, clients[(job["prompt"], job["stage"])]): job
            for job in pending_jobs
        }
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: (row["prompt"], row["stage"], row["case_id"], row["repetition"]))
    scores = {name: _scores(data, results, name) for name in prompts}
    decision = (
        scores["candidate"]["quality_score"] > scores["current"]["quality_score"]
        and scores["candidate"]["integrated_false_merges"]
        <= scores["current"]["integrated_false_merges"]
        and scores["candidate"]["repeat_consistency"] >= scores["current"]["repeat_consistency"]
    )
    payload = {
        "dataset": data["name"],
        "model": args.model,
        "call_count": len(jobs),
        "calls_executed": len(pending_jobs),
        "scores": scores,
        "candidate_passes_promotion_gate": decision,
        "results": results,
    }
    Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return payload


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="universe.prompt_eval", description=__doc__)
    parser.add_argument("--data", default="evals/prompt-quality-v001.json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    payload = run(args)
    print(
        json.dumps(
            {
                key: payload[key]
                for key in (
                    "model",
                    "call_count",
                    "calls_executed",
                    "scores",
                    "candidate_passes_promotion_gate",
                )
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
