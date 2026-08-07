"""Build a deterministic, similarity-stratified judge test group."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def evenly_spaced(rows: list[dict], count: int) -> list[dict]:
    if count >= len(rows):
        return rows
    if count == 1:
        return [rows[len(rows) // 2]]
    indices = [round(index * (len(rows) - 1) / (count - 1)) for index in range(count)]
    return [rows[index] for index in indices]


def band(candidate: dict) -> str:
    similarity = candidate["similarity"]
    if similarity >= 0.90:
        return "ge_090"
    if similarity >= 0.80:
        return "080_089"
    if similarity >= 0.70:
        return "070_079"
    return "lexical_lt_070"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    args = parser.parse_args()

    corpus = json.loads(args.corpus.read_text())
    by_id = {item["id"]: item for item in corpus["items"]}
    candidates = sorted(
        corpus["candidates"],
        key=lambda row: (-row["similarity"], row["a"], row["b"]),
    )
    selected = [candidate for candidate in candidates if band(candidate) == "ge_090"]
    allocations = {
        "080_089": {True: 8, False: 8},
        "070_079": {True: 8, False: 7},
        "lexical_lt_070": {True: 8, False: 7},
    }
    for label, relation_counts in allocations.items():
        for cross_source, count in relation_counts.items():
            rows = [
                candidate
                for candidate in candidates
                if band(candidate) == label
                and candidate["cross_source"] is cross_source
            ]
            selected.extend(evenly_spaced(rows, count))

    do_pair = next(candidate for candidate in candidates if candidate["modality"] == "do")
    selected_pairs = {(row["a"], row["b"]) for row in selected}
    if (do_pair["a"], do_pair["b"]) not in selected_pairs:
        replace_at = next(
            index
            for index in range(len(selected) - 1, -1, -1)
            if not selected[index]["cross_source"]
            and band(selected[index]) == "lexical_lt_070"
        )
        selected[replace_at] = do_pair

    unique = {(row["a"], row["b"]): row for row in selected}
    if len(unique) != 60:
        raise SystemExit(f"expected 60 unique cases, got {len(unique)}")
    selected = sorted(unique.values(), key=lambda row: (-row["similarity"], row["a"], row["b"]))

    cases = []
    for index, candidate in enumerate(selected, 1):
        cases.append(
            {
                "id": f"regex-{index:03d}",
                **candidate,
                "band": band(candidate),
                "item_a": by_id[candidate["a"]],
                "item_b": by_id[candidate["b"]],
                "gold_a_to_b": None,
                "gold_b_to_a": None,
                "gold_merge": None,
                "gold_notes": None,
            }
        )

    payload = {
        "name": "Concept Universe regex judge test group v001",
        "frozen_at": corpus["frozen_at"],
        "source_corpus": str(args.corpus),
        "selection": {
            "method": "deterministic similarity strata, balanced cross/within source below 0.90",
            "size": 60,
            "model_outputs_seen_before_gold": False,
        },
        "cases": cases,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# Regex judge test group — blind gold review",
        "",
        "Gold was selected before running any compared judge configuration.",
        "",
    ]
    for case in cases:
        a, b = case["item_a"], case["item_b"]
        lines.extend(
            [
                f"## {case['id']} — sim {case['similarity']:.4f} — {case['band']} — "
                f"{'cross-source' if case['cross_source'] else 'within-source'}",
                "",
                f"Axes: `{case['modality']}` / `{case['knowledge']}`",
                "",
                f"A source: {a['source_title']}",
                "",
                f"A statement: {a['statement']}",
                "",
                f"A task: {a['body']}",
                "",
                f"A answer: {a['answer']}",
                "",
                f"B source: {b['source_title']}",
                "",
                f"B statement: {b['statement']}",
                "",
                f"B task: {b['body']}",
                "",
                f"B answer: {b['answer']}",
                "",
                "Gold A→B: TODO",
                "",
                "Gold B→A: TODO",
                "",
                "Gold merge: TODO",
                "",
                "Notes: TODO",
                "",
            ]
        )
    args.review.parent.mkdir(parents=True, exist_ok=True)
    args.review.write_text("\n".join(lines))
    print(f"wrote {len(cases)} cases to {args.out} and {args.review}")


if __name__ == "__main__":
    main()
