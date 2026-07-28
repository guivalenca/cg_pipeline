"""Consolidate judgments into the four task grain classes.

    python -m universe.task_axes derive \
        --modality-runs r0109,r0110,r0111 \
        --knowledge-runs r0113,r0114,r0115

Each axis is decided by an odd-run majority. Disagreement remains visible as
a split flag, while missing judgments, ties, and unsure majorities stop the
derivation instead of silently becoming one of concept-explain, concept-apply,
procedure-explain, or procedure-do.
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Callable

import psycopg

from universe.db import connect
from universe.harness import fetch_items, id_list
from universe.task_knowledge import VERDICTS as KNOWLEDGE_VERDICTS
from universe.task_knowledge import knowledge_of
from universe.task_modality import VERDICTS as MODALITY_VERDICTS
from universe.task_modality import modality_of


def _result_of(item: dict) -> object:
    """Accept the explicit public shape and a flattened parser result."""
    if "result" in item:
        return item["result"]
    return item if "verdict" in item else None


def _missing_tasks(
    items: list[dict],
    task_ids: set[str],
    verdicts: set[str],
) -> set[str]:
    grouped: dict[str, list[dict]] = {}
    for item in items:
        grouped.setdefault(item["task_id"], []).append(item)

    run_ids = {item["run_id"] for item in items if item.get("run_id") is not None}
    expected_count = len(run_ids) if run_ids else max(map(len, grouped.values()), default=0)
    missing = set()
    for task_id in task_ids:
        task_items = grouped.get(task_id, [])
        task_run_ids = {
            item["run_id"] for item in task_items if item.get("run_id") is not None
        }
        results = [_result_of(item) for item in task_items]
        usable = all(
            isinstance(result, dict) and result.get("verdict") in verdicts
            for result in results
        )
        wrong_runs = bool(run_ids) and (
            task_run_ids != run_ids or len(task_items) != expected_count
        )
        if (
            not usable
            or len(task_items) != expected_count
            or expected_count == 0
            or expected_count % 2 == 0
            or wrong_runs
        ):
            missing.add(task_id)
    return missing


def _votes_by_task(items: list[dict]) -> dict[str, list[str]]:
    votes: dict[str, list[str]] = {}
    for item in items:
        result = _result_of(item)
        assert isinstance(result, dict)
        votes.setdefault(item["task_id"], []).append(result["verdict"])
    return votes


def _majority(votes: list[str]) -> dict | None:
    counts = Counter(votes)
    verdict, count = counts.most_common(1)[0]
    if count <= len(votes) // 2:
        return None
    return {
        "verdict": verdict,
        "split": count != len(votes),
        "votes": votes,
    }


def derive_axes(modality_items: list[dict], knowledge_items: list[dict]) -> list[dict]:
    """Return majority task axes and their derived grain classes.

    Each input record has ``task_id`` and ``result``, where ``result`` is the
    return value of ``modality_of`` or ``knowledge_of``. A flattened successful
    parser result is accepted too. Optional ``run_id`` fields make absent
    per-run records detectable; otherwise the largest per-task vote count is
    treated as the number of runs.
    """
    if any(
        isinstance(result := _result_of(item), dict)
        and result.get("verdict") == "fact"
        for item in knowledge_items
    ):
        raise SystemExit(
            "Fact verdict encountered from retired task-fact module; "
            "cannot mix retired-class runs into derivation"
        )

    task_ids = {item["task_id"] for item in modality_items + knowledge_items}
    missing = _missing_tasks(modality_items, task_ids, MODALITY_VERDICTS)
    missing |= _missing_tasks(knowledge_items, task_ids, KNOWLEDGE_VERDICTS)
    if missing:
        names = ", ".join(sorted(missing))
        raise SystemExit(f"silence is not a verdict: {names}")

    modality_votes = _votes_by_task(modality_items)
    knowledge_votes = _votes_by_task(knowledge_items)
    majorities: dict[str, tuple[dict, dict]] = {}
    no_majority = set()
    for task_id in task_ids:
        modality = _majority(modality_votes[task_id])
        knowledge = _majority(knowledge_votes[task_id])
        if modality is None or knowledge is None:
            no_majority.add(task_id)
        else:
            majorities[task_id] = (modality, knowledge)
    if no_majority:
        names = ", ".join(sorted(no_majority))
        raise SystemExit(f"three-way split has no majority: {names}")

    unsure = {
        task_id
        for task_id, (modality, knowledge) in majorities.items()
        if modality["verdict"] == "unsure" or knowledge["verdict"] == "unsure"
    }
    if unsure:
        names = ", ".join(sorted(unsure))
        raise SystemExit(f"unsure majority: {names}")

    classes = {
        ("concept", "explain"): "concept-explain",
        ("concept", "do"): "concept-apply",
        ("procedure", "do"): "procedure-do",
        ("procedure", "explain"): "procedure-explain",
    }
    derived = []
    for task_id in sorted(task_ids):
        modality, knowledge = majorities[task_id]
        derived.append(
            {
                "task_id": task_id,
                "modality": modality,
                "knowledge": knowledge,
                "grain_class": classes[
                    (knowledge["verdict"], modality["verdict"])
                ],
            }
        )
    return derived


def _fetch_axis_runs(
    conn: psycopg.Connection,
    run_ids: list[str],
    parser: Callable[[dict], dict | str],
) -> list[tuple[str, dict[str, object]]]:
    runs = []
    for run_id in run_ids:
        results = {}
        for item in fetch_items(conn, run_id):
            task_id = item["task_id"]
            if not task_id:
                raise SystemExit(f"{item['id']} is not about a task")
            if task_id in results:
                raise SystemExit(f"{run_id} has more than one verdict for {task_id}")
            results[task_id] = parser(item)
        runs.append((run_id, results))
    return runs


def _records(
    runs: list[tuple[str, dict[str, object]]],
    task_ids: set[str],
) -> list[dict]:
    return [
        {
            "task_id": task_id,
            "run_id": run_id,
            "result": results.get(task_id),
        }
        for run_id, results in runs
        for task_id in sorted(task_ids)
    ]


def _vote_label(axis: dict) -> str:
    if not axis["split"]:
        return axis["verdict"]
    majority = axis["votes"].count(axis["verdict"])
    return f"{axis['verdict']} {majority}-{len(axis['votes']) - majority}"


def _print_table(axes: list[dict]) -> None:
    rows = [
        [
            item["task_id"],
            _vote_label(item["modality"]),
            _vote_label(item["knowledge"]),
            item["grain_class"],
        ]
        for item in axes
    ]
    headers = ["task_id", "modality", "knowledge", "grain_class"]
    widths = [
        max(len(row[index]) for row in [headers, *rows])
        for index in range(len(headers))
    ]
    for row in [headers, *rows]:
        print("  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip())


def cmd_derive(args: argparse.Namespace) -> None:
    with connect() as conn:
        modality_runs = _fetch_axis_runs(conn, args.modality_runs, modality_of)
        knowledge_runs = _fetch_axis_runs(conn, args.knowledge_runs, knowledge_of)

    task_ids = {
        task_id
        for _, results in modality_runs + knowledge_runs
        for task_id in results
    }
    axes = derive_axes(
        _records(modality_runs, task_ids),
        _records(knowledge_runs, task_ids),
    )
    _print_table(axes)
    if args.out:
        args.out.write_text(json.dumps(axes, indent=2) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.task_axes", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    derive = sub.add_parser("derive", help="consolidate repeated task-axis judgments")
    derive.add_argument(
        "--modality-runs",
        required=True,
        type=id_list,
        help="comma-separated task-modality run ids",
    )
    derive.add_argument(
        "--knowledge-runs",
        required=True,
        type=id_list,
        help="comma-separated task-knowledge run ids",
    )
    derive.add_argument("--out", type=Path, help="optional JSON export path")
    derive.set_defaults(func=cmd_derive)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
