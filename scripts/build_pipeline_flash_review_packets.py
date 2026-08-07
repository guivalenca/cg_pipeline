"""Summarize the four-source benchmark and build blinded A/B review packets."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path


CLASSIFIER_STAGES = {
    "task-granularity",
    "task-revision",
    "task-triage",
    "task-substance",
    "task-knowledge",
}
GENERATIVE_STAGES = {"task-generation", "kc-statement"}


def parsed(raw: str | None) -> dict:
    if raw is None:
        return {}
    value = json.loads(raw)
    return value if isinstance(value, dict) else {}


def outcome(stage: str, raw: str | None) -> str | int | None:
    value = parsed(raw)
    if stage == "task-generation":
        tasks = value.get("tasks")
        return len(tasks) if isinstance(tasks, list) else None
    return value.get("verdict")


def usable(stage: str, raw: str | None) -> bool:
    value = parsed(raw)
    if stage == "task-generation":
        tasks = value.get("tasks")
        return isinstance(tasks, list) and all(
            isinstance(task, dict)
            and isinstance(task.get("task"), str) and bool(task["task"].strip())
            and isinstance(task.get("answer"), str) and bool(task["answer"].strip())
            for task in tasks
        )
    verdict = value.get("verdict")
    if stage == "task-granularity":
        if verdict not in {"single", "composite", "unsure"}:
            return False
        if verdict != "composite":
            return True
        parts = value.get("parts")
        return isinstance(parts, list) and bool(parts) and all(
            isinstance(part, dict)
            and isinstance(part.get("task"), str) and bool(part["task"].strip())
            and isinstance(part.get("answer"), str) and bool(part["answer"].strip())
            for part in parts
        )
    if stage == "task-revision":
        return verdict in {"stands", "unfixable"} or (
            verdict == "rewritten"
            and isinstance(value.get("task"), str) and bool(value["task"].strip())
        )
    if stage == "task-triage":
        return verdict in {"supported", "unsupported", "unsure"}
    if stage == "task-substance":
        if verdict not in {"works", "fixable", "does_not_work", "beyond_repair", "unsure"}:
            return False
        return verdict != "fixable" or any(
            isinstance(value.get(field), str) and value[field].strip()
            for field in ("task", "answer")
        )
    if stage == "kc-statement":
        return verdict == "unsure" or (
            verdict == "stated"
            and isinstance(value.get("statement"), str) and bool(value["statement"].strip())
        )
    if stage == "task-knowledge":
        return verdict in {"fact", "concept", "procedure", "unsure"} and (
            isinstance(value.get("reason"), str) and bool(value["reason"].strip())
        )
    return False


def output_order(case_id: str, reference: str, flash: str) -> tuple[str, str, str]:
    reference_is_a = hashlib.sha256(case_id.encode()).digest()[0] % 2 == 0
    if reference_is_a:
        return reference, flash, "A"
    return flash, reference, "B"


def packet_text(title: str, cases: list[dict], trials: dict[tuple[str, int], dict]) -> tuple[str, dict]:
    lines = [
        f"# {title}",
        "",
        "This is a blinded comparison. A and B are randomly ordered per case.",
        "Do not inspect the benchmark source JSON or the private mapping file.",
        "Read the referenced prompt file before judging a stage. Treat neither",
        "output as the gold answer. Judge correctness from the input and prompt.",
        "Return one JSON object per case with: case_id, winner (A/B/tie),",
        "severity_if_worse (none/minor/material/critical), confidence (low/medium/high),",
        "and a concise reason. Flag hallucination, lost coverage, wrong scope, or",
        "a wrong gate/classification explicitly.",
        "",
    ]
    mapping = {}
    for case in cases:
        flash = trials[(case["case_id"], 1)]["response"]
        output_a, output_b, reference_label = output_order(
            case["case_id"], case["reference_response"], flash
        )
        mapping[case["case_id"]] = {
            "reference": reference_label,
            "flash": "B" if reference_label == "A" else "A",
        }
        prompt_path = f"prompts/{case['stage']}/{case['prompt_ref'].split('/')[-1]}.md"
        lines.extend(
            [
                f"## {case['case_id']}",
                "",
                f"Stage: `{case['stage']}`",
                "",
                f"Source: {case['source_title']}",
                "",
                f"Prompt: `{prompt_path}`",
                "",
                "Input:",
                "```json",
                json.dumps(case["input"], ensure_ascii=False, indent=2),
                "```",
                "",
                "Output A:",
                "```json",
                output_a,
                "```",
                "",
                "Output B:",
                "```json",
                output_b,
                "```",
                "",
            ]
        )
    return "\n".join(lines), mapping


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("evals/pipeline-flash-benchmark-v001.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("evals/pipeline-flash-review-v001"))
    args = parser.parse_args()
    data = json.loads(args.input.read_text())
    cases = data["cases"]
    trials = {(row["case_id"], row["replicate"]): row for row in data["trials"]}

    stage_metrics = {}
    for stage in sorted({case["stage"] for case in cases}):
        selected = [case for case in cases if case["stage"] == stage]
        costs = {
            str(replicate): sum(
                float(trials[(case["case_id"], replicate)]["usage"].get("cost") or 0)
                for case in selected
            )
            for replicate in (1, 2)
        }
        reference_cost = sum(
            float(case["reference_usage"].get("cost") or 0) for case in selected
        )
        flash_single_cost = costs["1"]
        metric = {
            "cases": len(selected),
            "reference_cost": reference_cost,
            "flash_cost": costs,
            "flash_cost_total": sum(costs.values()),
            "flash_single_cost_ratio": (
                flash_single_cost / reference_cost if reference_cost else None
            ),
            "reference_usable": sum(
                usable(stage, case["reference_response"]) for case in selected
            ),
            "flash_1_usable": sum(
                usable(stage, trials[(case["case_id"], 1)]["response"])
                for case in selected
            ),
            "flash_2_usable": sum(
                usable(stage, trials[(case["case_id"], 2)]["response"])
                for case in selected
            ),
            "errors": sum(
                trials[(case["case_id"], replicate)]["error"] is not None
                for case in selected for replicate in (1, 2)
            ),
        }
        if stage in CLASSIFIER_STAGES:
            metric.update(
                {
                    "reference_vs_flash_1": sum(
                        outcome(stage, case["reference_response"])
                        == outcome(stage, trials[(case["case_id"], 1)]["response"])
                        for case in selected
                    ),
                    "reference_vs_flash_2": sum(
                        outcome(stage, case["reference_response"])
                        == outcome(stage, trials[(case["case_id"], 2)]["response"])
                        for case in selected
                    ),
                    "flash_internal_agreement": sum(
                        outcome(stage, trials[(case["case_id"], 1)]["response"])
                        == outcome(stage, trials[(case["case_id"], 2)]["response"])
                        for case in selected
                    ),
                }
            )
        elif stage == "task-generation":
            metric.update(
                {
                    "reference_vs_flash_1_same_task_count": sum(
                        outcome(stage, case["reference_response"])
                        == outcome(stage, trials[(case["case_id"], 1)]["response"])
                        for case in selected
                    ),
                    "reference_vs_flash_2_same_task_count": sum(
                        outcome(stage, case["reference_response"])
                        == outcome(stage, trials[(case["case_id"], 2)]["response"])
                        for case in selected
                    ),
                    "flash_same_task_count": sum(
                        outcome(stage, trials[(case["case_id"], 1)]["response"])
                        == outcome(stage, trials[(case["case_id"], 2)]["response"])
                        for case in selected
                    ),
                }
            )
        stage_metrics[stage] = metric

    classifier_cases = [case for case in cases if case["stage"] in CLASSIFIER_STAGES]
    generative_cases = [case for case in cases if case["stage"] in GENERATIVE_STAGES]
    review_cases = []
    for case in cases:
        stage = case["stage"]
        ref = outcome(stage, case["reference_response"])
        first = outcome(stage, trials[(case["case_id"], 1)]["response"])
        second = outcome(stage, trials[(case["case_id"], 2)]["response"])
        if stage in GENERATIVE_STAGES or ref != first or ref != second or first != second:
            review_cases.append(case)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    mapping = {}
    for name, title, selected in (
        ("generative", "Generative stages review", generative_cases),
        ("classifiers", "Gate and classification stages review", classifier_cases),
        ("adjudication", "Cross-cutting disagreement and generative-risk review", review_cases),
    ):
        text, packet_mapping = packet_text(title, selected, trials)
        (args.out_dir / f"{name}.md").write_text(text.rstrip() + "\n")
        mapping.update(packet_mapping)

    total_cost = sum(float(row["usage"].get("cost") or 0) for row in data["trials"])
    reference_cost = sum(
        float(case["reference_usage"].get("cost") or 0) for case in cases
    )
    flash_single_cost = sum(
        float(row["usage"].get("cost") or 0)
        for row in data["trials"] if row["replicate"] == 1
    )
    summary = {
        "cases": len(cases),
        "trials": len(data["trials"]),
        "errors": sum(row["error"] is not None for row in data["trials"]),
        "reference_cost": reference_cost,
        "flash_cost_total": total_cost,
        "flash_single_cost": flash_single_cost,
        "flash_single_cost_ratio": flash_single_cost / reference_cost,
        "flash_single_cost_reduction": 1 - flash_single_cost / reference_cost,
        "stages": stage_metrics,
        "review_packet_cases": {
            "generative": len(generative_cases),
            "classifiers": len(classifier_cases),
            "adjudication": len(review_cases),
        },
    }
    (args.out_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    )
    (args.out_dir / "mapping.private.json").write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
