"""Apply the blind manual directional labels to the frozen regex test group."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


LABELS = {
    1: (True, True), 2: (True, False), 3: (False, True), 4: (True, True),
    5: (True, True), 6: (False, False), 7: (False, True), 8: (True, True),
    9: (False, False), 10: (False, True), 11: (True, True), 12: (False, False),
    13: (False, True), 14: (False, True), 15: (True, True), 16: (False, True),
    17: (False, True), 18: (False, True), 19: (False, True), 20: (True, True),
    21: (True, True), 22: (False, False), 23: (False, True), 24: (False, True),
    25: (False, False), 26: (False, False), 27: (False, False), 28: (False, False),
    29: (False, True), 30: (False, False), 31: (False, True), 32: (False, True),
    33: (False, True), 34: (False, False), 35: (False, False), 36: (False, False),
    37: (False, False), 38: (False, False), 39: (False, False), 40: (False, True),
    41: (False, True), 42: (False, False), 43: (False, True), 44: (False, True),
    45: (False, False), 46: (False, False), 47: (False, False), 48: (False, False),
    49: (False, False), 50: (False, False), 51: (False, False), 52: (False, False),
    53: (False, False), 54: (False, False), 55: (False, False), 56: (False, False),
    57: (False, False), 58: (False, False), 59: (False, False), 60: (False, False),
}


def note(a_to_b: bool, b_to_a: bool) -> str:
    if a_to_b and b_to_a:
        return "The two tasks test the same fair-question demand in both directions."
    if a_to_b:
        return "A contains B's demand, but B does not establish all of A."
    if b_to_a:
        return "B contains A's demand, but A omits a fact, distinction, or operation required by B."
    return "The tasks have distinct demands or each leaves a required capability unestablished."


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.path.read_text())
    cases = payload["cases"]
    if len(cases) != 60 or set(LABELS) != set(range(1, 61)):
        raise SystemExit("gold mapping and frozen case set do not match")
    for index, case in enumerate(cases, 1):
        expected = f"regex-{index:03d}"
        if case["id"] != expected:
            raise SystemExit(f"expected {expected}, got {case['id']}")
        a_to_b, b_to_a = LABELS[index]
        case["gold_a_to_b"] = a_to_b
        case["gold_b_to_a"] = b_to_a
        case["gold_a_clear_yes"] = a_to_b
        case["gold_b_clear_yes"] = b_to_a
        case["gold_merge"] = a_to_b and b_to_a
        case["gold_notes"] = note(a_to_b, b_to_a)
        case["bucket"] = "gold"
    items = {}
    for case in cases:
        items[case["a"]] = case["item_a"]
        items[case["b"]] = case["item_b"]
    payload["items"] = [items[task_id] for task_id in sorted(items)]
    payload["gold_contract"] = {
        "reviewed_before_model_comparison": True,
        "direction_positive": "clear transfer: the target demand is fully carried by source mastery",
        "merge_positive": "both directions are positive",
        "ambiguous_cases": 0,
    }
    args.path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(
        f"applied gold: {sum(case['gold_merge'] for case in cases)} merges,"
        f" {sum(case['gold_a_to_b'] for case in cases) + sum(case['gold_b_to_a'] for case in cases)}"
        " positive directions"
    )


if __name__ == "__main__":
    main()
