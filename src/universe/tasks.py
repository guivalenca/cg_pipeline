"""Turn the tasks a generation run reported into task rows the next stages judge.

    python -m universe.tasks r0050 r0051

A task row is one entry of one report: its identity is the run item that
reported it plus its position there, so materializing twice writes nothing
new, and two generation runs never collide. Unlike passages there is no
content dedup: task texts almost never repeat across runs, and when they do,
judging both costs little and says something about agreement.
"""

import argparse

import psycopg

from universe.db import connect
from universe.harness import fetch_items, fetch_run
from universe.taskgen import STAGE as GENERATION_STAGE
from universe.taskgen import tasks_of


def task_id(run_item_id: str, seq: int) -> str:
    return f"{run_item_id}:t{seq:02d}"


def materialize(conn: psycopg.Connection, gen_run_id: str) -> dict:
    """Write the task rows a generation run implies."""
    run = fetch_run(conn, gen_run_id)
    if run["stage"] != GENERATION_STAGE:
        raise SystemExit(f"{gen_run_id} is a {run['stage']} run, not {GENERATION_STAGE}")

    counts = {"tasks_new": 0, "tasks_existing": 0}
    for item in fetch_items(conn, gen_run_id):
        if item["error"]:
            raise SystemExit(f"{item['id']} failed and has no tasks: {item['error']}")
        if not item["passage_id"]:
            raise SystemExit(f"{item['id']} is about a whole artifact, not a passage")
        tasks = tasks_of(item)
        if not isinstance(tasks, list):
            raise SystemExit(f"{item['id']} did not report usable tasks: {tasks}")
        for seq, entry in enumerate(tasks, 1):
            written = conn.execute(
                "INSERT INTO task (id, run_item_id, passage_id, seq, body, answer)"
                " VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (
                    task_id(item["id"], seq),
                    item["id"],
                    item["passage_id"],
                    seq,
                    entry["task"],
                    entry["answer"],
                ),
            ).rowcount
            counts["tasks_new" if written else "tasks_existing"] += 1
    conn.commit()
    return counts


def fetch_tasks_for_runs(conn: psycopg.Connection, gen_run_ids: list[str]) -> list[dict]:
    """Every task these generation runs reported, in report order."""
    rows = conn.execute(
        "SELECT t.id, t.run_item_id, t.passage_id, t.seq, t.body, t.answer,"
        " p.artifact_id"
        " FROM task t"
        " JOIN run_item i ON i.id = t.run_item_id"
        " JOIN passage p ON p.id = t.passage_id"
        " WHERE i.run_id = ANY(%s)"
        " ORDER BY t.run_item_id, t.seq",
        (gen_run_ids,),
    ).fetchall()
    keys = "id run_item_id passage_id seq body answer artifact_id".split()
    return [dict(zip(keys, row)) for row in rows]


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.tasks", description=__doc__)
    parser.add_argument("run_ids", nargs="+", help="task-generation run ids")
    args = parser.parse_args(argv)
    with connect() as conn:
        for run_id in args.run_ids:
            counts = materialize(conn, run_id)
            print(
                f"{run_id}: {counts['tasks_new']} new task(s),"
                f" {counts['tasks_existing']} already known"
            )


if __name__ == "__main__":
    main()
