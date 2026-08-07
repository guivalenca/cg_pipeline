"""Decode blinded reviews and aggregate benchmark results by stage."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path


REVIEW_FILES = {
    "generative": "review-generative-agent.json",
    "classifiers": "review-classifiers-agent.json",
    "adjudication": "review-adjudication-agent.json",
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark", type=Path,
        default=Path("evals/pipeline-flash-benchmark-v001.json"),
    )
    parser.add_argument(
        "--review-dir", type=Path,
        default=Path("evals/pipeline-flash-review-v001"),
    )
    parser.add_argument(
        "--out", type=Path,
        default=Path("evals/pipeline-flash-review-v001/results.json"),
    )
    args = parser.parse_args()
    benchmark = json.loads(args.benchmark.read_text())
    mapping = json.loads((args.review_dir / "mapping.private.json").read_text())
    cases = {case["case_id"]: case for case in benchmark["cases"]}

    decoded = []
    for evaluator, filename in REVIEW_FILES.items():
        payload = json.loads((args.review_dir / filename).read_text())
        for review in payload["cases"]:
            winner = review["winner"]
            if winner == "tie":
                model_winner = "tie"
            elif winner == mapping[review["case_id"]]["reference"]:
                model_winner = "pro"
            else:
                model_winner = "flash"
            decoded.append(
                {
                    **review,
                    "evaluator": evaluator,
                    "stage": cases[review["case_id"]]["stage"],
                    "model_winner": model_winner,
                }
            )

    by_case: dict[str, list[dict]] = defaultdict(list)
    for review in decoded:
        by_case[review["case_id"]].append(review)
    consensus = []
    for case_id, reviews in sorted(by_case.items()):
        votes = Counter(review["model_winner"] for review in reviews)
        if votes["pro"] > votes["flash"]:
            winner = "pro"
        elif votes["flash"] > votes["pro"]:
            winner = "flash"
        else:
            winner = "tie"
        severity = Counter(review["severity_if_worse"] for review in reviews)
        consensus.append(
            {
                "case_id": case_id,
                "stage": cases[case_id]["stage"],
                "source_id": cases[case_id]["source_id"],
                "winner": winner,
                "votes": dict(votes),
                "severity_votes": dict(severity),
                "reviews": len(reviews),
            }
        )

    stages = {}
    for stage in sorted({case["stage"] for case in benchmark["cases"]}):
        stage_cases = [case for case in consensus if case["stage"] == stage]
        stage_reviews = [review for review in decoded if review["stage"] == stage]
        stages[stage] = {
            "cases": len(stage_cases),
            "consensus_winners": dict(Counter(case["winner"] for case in stage_cases)),
            "all_review_votes": dict(Counter(review["model_winner"] for review in stage_reviews)),
            "material_or_critical_reviews": sum(
                review["severity_if_worse"] in {"material", "critical"}
                for review in stage_reviews
            ),
        }

    payload = {
        "name": "Decoded blinded review of four-source Flash-low benchmark v001",
        "method": {
            "primary_comparison": "stored Pro-high reference versus Flash-low replicate 1",
            "blinding": "A/B order randomized deterministically per case",
            "consensus": "directional majority; ties and balanced directional votes remain ties",
            "note": "The Pro output was a reference accepted by the user, not declared ground truth.",
        },
        "review_count": len(decoded),
        "case_count": len(consensus),
        "overall_consensus_winners": dict(Counter(case["winner"] for case in consensus)),
        "overall_review_votes": dict(Counter(review["model_winner"] for review in decoded)),
        "stages": stages,
        "cases": consensus,
        "decoded_reviews": decoded,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({key: payload[key] for key in ("review_count", "case_count", "overall_consensus_winners", "overall_review_votes", "stages")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
