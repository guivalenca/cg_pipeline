"""Select blind-gold cases where the two leading judge configs were hard."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def directional(result: dict) -> tuple[bool, bool]:
    parsed = result["parsed"]
    return (
        parsed["verdict_a_to_b"] == "clear_yes",
        parsed["verdict_b_to_a"] == "clear_yes",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path)
    parser.add_argument("--pro", required=True, type=Path)
    parser.add_argument("--flash", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    data = json.loads(args.data.read_text())
    pro = {
        row["case_id"]: row for row in json.loads(args.pro.read_text())["results"]
    }
    flash = {
        row["case_id"]: row for row in json.loads(args.flash.read_text())["results"]
    }
    cases = []
    for case in data["cases"]:
        gold = (case["gold_a_clear_yes"], case["gold_b_clear_yes"])
        pro_prediction = directional(pro[case["id"]])
        flash_prediction = directional(flash[case["id"]])
        if (
            pro_prediction != flash_prediction
            or pro_prediction != gold
            or flash_prediction != gold
        ):
            cases.append(case)
    task_ids = sorted({task_id for case in cases for task_id in (case["a"], case["b"])})
    by_id = {item["id"]: item for item in data["items"]}
    payload = {
        **{key: value for key, value in data.items() if key not in {"cases", "items"}},
        "name": "Concept Universe regex judge hard-case stability subset v001",
        "selection": {
            "source_test_group": str(args.data),
            "rule": "Pro-v003 and Flash-low-v003 disagreed, or either differed from blind gold",
            "case_count": len(cases),
            "model_outputs_used_only_for_subset_selection": True,
            "gold_changed_after_selection": False,
        },
        "items": [by_id[task_id] for task_id in task_ids],
        "cases": cases,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(f"wrote {len(cases)} hard cases and {len(task_ids)} items to {args.out}")


if __name__ == "__main__":
    main()
