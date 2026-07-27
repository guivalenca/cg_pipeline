"""Compare task-embedding runs by their pairwise cosine similarities.

    python -m universe.task_embedding_report r0068 r0069 --top 40 \
        --percentiles 90,95,97.5

The same task has the same short label in every table, so the strongest
pairs, nearest neighbors, and threshold groups can be read across models
without carrying the database ids through every comparison.
"""

import argparse
import math
from pathlib import Path

import psycopg

from universe.db import connect
from universe.harness import REPORTS_DIR, fetch_run, positive_int
from universe.task_embedding import STAGE

DEFAULT_TOP = 40
DEFAULT_PERCENTILES = [90.0, 95.0, 97.5]


def percentile(values: list[float], p: float) -> float:
    """The linearly interpolated percentile of a sorted copy of values."""
    if not values:
        raise ValueError("percentile needs at least one value")
    if not 0 <= p <= 100:
        raise ValueError("percentile must be between 0 and 100")
    ordered = sorted(values)
    position = (len(ordered) - 1) * p / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def components(nodes: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    """Connected components, with nodes and groups in deterministic order."""
    neighbors = {node: set() for node in nodes}
    for left, right in edges:
        neighbors.setdefault(left, set()).add(right)
        neighbors.setdefault(right, set()).add(left)

    found = []
    unseen = set(neighbors)
    while unseen:
        root = min(unseen)
        group = []
        pending = [root]
        unseen.remove(root)
        while pending:
            node = pending.pop()
            group.append(node)
            additions = sorted(neighbors[node] & unseen, reverse=True)
            for neighbor in additions:
                unseen.remove(neighbor)
                pending.append(neighbor)
        found.append(sorted(group))
    return sorted(found, key=lambda group: group[0])


def parse_percentiles(value: str) -> list[float]:
    try:
        parsed = [float(part) for part in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("percentiles must be comma-separated numbers") from exc
    if not parsed or any(not 0 <= p <= 100 for p in parsed):
        raise argparse.ArgumentTypeError("percentiles must be between 0 and 100")
    return parsed


def fetch_similarities(
    conn: psycopg.Connection, run_id: str
) -> dict[tuple[str, str], float]:
    rows = conn.execute(
        "SELECT a.task_id, b.task_id, (1 - (a.embedding <=> b.embedding))::float"
        " FROM task_embedding a"
        " JOIN run_item ia ON ia.id = a.run_item_id"
        " JOIN task_embedding b ON b.task_id > a.task_id"
        " JOIN run_item ib ON ib.id = b.run_item_id"
        " WHERE ia.run_id = %s AND ib.run_id = %s",
        (run_id, run_id),
    ).fetchall()
    return {(left, right): similarity for left, right, similarity in rows}


def fetch_texts(conn: psycopg.Connection, run_id: str) -> dict[str, str]:
    rows = conn.execute(
        "SELECT i.task_id, i.response FROM run_item i"
        " JOIN task_embedding e ON e.run_item_id = i.id"
        " WHERE i.run_id = %s ORDER BY i.task_id",
        (run_id,),
    ).fetchall()
    return {task_id: text for task_id, text in rows}


def collect(conn: psycopg.Connection, run_ids: list[str]) -> tuple[list[dict], dict, dict]:
    runs, similarities, texts = [], {}, {}
    for run_id in run_ids:
        run = fetch_run(conn, run_id)
        if run["stage"] != STAGE:
            raise SystemExit(f"{run_id} is a {run['stage']} run, not {STAGE}")
        runs.append(run)
        similarities[run_id] = fetch_similarities(conn, run_id)
        texts[run_id] = fetch_texts(conn, run_id)

    expected_id = run_ids[0]
    expected = set(texts[expected_id])
    for run_id in run_ids[1:]:
        actual = set(texts[run_id])
        if actual != expected:
            missing = sorted(expected - actual)
            added = sorted(actual - expected)
            differences = []
            if missing:
                differences.append(f"missing from {run_id}: {', '.join(missing)}")
            if added:
                differences.append(f"only in {run_id}: {', '.join(added)}")
            raise SystemExit(
                f"task ids differ between {expected_id} and {run_id}: "
                + "; ".join(differences)
            )
    return runs, similarities, texts


def _similarity(value: float) -> str:
    return f"{value:.6f}"


def _blockquote(text: str) -> list[str]:
    return [f"> {line}" if line else ">" for line in text.rstrip("\n").split("\n")]


def render_runs(
    conn: psycopg.Connection,
    run_ids: list[str],
    top: int = DEFAULT_TOP,
    percentiles: list[float] | None = None,
) -> str:
    runs, similarities, texts = collect(conn, run_ids)
    task_ids = sorted(texts[run_ids[0]])
    labels = {task_id: f"T{index:02d}" for index, task_id in enumerate(task_ids, 1)}
    pair_count = len(task_ids) * (len(task_ids) - 1) // 2

    lines = [f"# Task embeddings: {' -> '.join(run_ids)}", ""]
    lines += [f"- {run['id']}: {run['model']}" for run in runs]
    lines += ["", f"{len(task_ids)} task(s), {pair_count} pair(s).", ""]

    lines += ["## Tasks", ""]
    first_texts = texts[run_ids[0]]
    for task_id in task_ids:
        lines += [f"### {labels[task_id]} · {task_id}", ""]
        lines += _blockquote(first_texts[task_id])
        lines.append("")

    pair_keys = sorted(similarities[run_ids[0]])
    rank_by_run = {}
    for run_id in run_ids:
        ordered = sorted(
            similarities[run_id], key=lambda pair: (-similarities[run_id][pair], pair)
        )
        rank_by_run[run_id] = {pair: rank for rank, pair in enumerate(ordered, 1)}
    means = {
        pair: sum(similarities[run_id][pair] for run_id in run_ids) / len(run_ids)
        for pair in pair_keys
    }
    strongest = sorted(pair_keys, key=lambda pair: (-means[pair], pair))[:top]

    lines += ["## Strongest pairs", "", "Ranked by mean similarity across runs.", ""]
    lines += [
        "| rank | pair | " + " | ".join(run_ids) + " |",
        "| - " * (len(run_ids) + 2) + "|",
    ]
    for rank, pair in enumerate(strongest, 1):
        pair_label = f"{labels[pair[0]]} x {labels[pair[1]]}"
        cells = [
            f"{_similarity(similarities[run_id][pair])}"
            f" ({rank_by_run[run_id][pair]})"
            for run_id in run_ids
        ]
        lines.append("| " + " | ".join([str(rank), pair_label] + cells) + " |")

    lines += ["", "## Nearest neighbor per task", ""]
    for run_id in run_ids:
        lines += [f"### {run_id}", "", "| task | partner | similarity |", "| - | - | - |"]
        values = similarities[run_id]
        for task_id in task_ids:
            candidates = []
            for pair, similarity in values.items():
                if task_id == pair[0]:
                    candidates.append((similarity, pair[1]))
                elif task_id == pair[1]:
                    candidates.append((similarity, pair[0]))
            if candidates:
                similarity, partner = min(candidates, key=lambda item: (-item[0], item[1]))
                lines.append(
                    f"| {labels[task_id]} | {labels[partner]} | {_similarity(similarity)} |"
                )
            else:
                lines.append(f"| {labels[task_id]} | - | - |")
        lines.append("")

    lines += ["## Groups by threshold", ""]
    cuts = DEFAULT_PERCENTILES if percentiles is None else percentiles
    for run_id in run_ids:
        lines += [f"### {run_id}", ""]
        values = similarities[run_id]
        distribution = list(values.values())
        if not distribution:
            lines += ["No task pairs.", ""]
            continue
        for cut in cuts:
            threshold = percentile(distribution, cut)
            edges = [pair for pair, similarity in values.items() if similarity >= threshold]
            groups = components(task_ids, edges)
            lines += [f"#### {cut:g}th percentile · threshold {_similarity(threshold)}", ""]
            for group in groups:
                if len(group) > 1:
                    lines.append("- " + " ".join(labels[task_id] for task_id in group))
            singletons = sum(1 for group in groups if len(group) == 1)
            lines += [f"- {singletons} singleton(s)", ""]
    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection,
    run_ids: list[str],
    top: int = DEFAULT_TOP,
    percentiles: list[float] | None = None,
    reports_dir: Path | None = None,
) -> Path:
    path = (reports_dir or REPORTS_DIR) / f"task-embedding-{'->'.join(run_ids)}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_runs(conn, run_ids, top, percentiles))
    return path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="universe.task_embedding_report", description=__doc__
    )
    parser.add_argument("run_ids", nargs="+")
    parser.add_argument("--top", type=positive_int, default=DEFAULT_TOP)
    parser.add_argument(
        "--percentiles", type=parse_percentiles, default=DEFAULT_PERCENTILES
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    with connect() as conn:
        print(write_report(conn, args.run_ids, args.top, args.percentiles))


if __name__ == "__main__":
    main()
