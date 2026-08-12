"""Turn the cuts a run reported into passage rows the next stages can address.

    python -m universe.passages r0017 r0034 r0029

Materializing is idempotent twice over: the same run written again inserts
nothing, and a range two runs agree on is one passage with two origins. That
is the whole point of deriving the id from the range instead of from the run:
four cuts runs over one artifact cost far fewer than four times the passages,
and every stage downstream pays only for what the runs actually disagreed on.

Passage text is the blocks of the range joined by blank lines, with no <block>
tags and no front matter, because the reader of a passage is a model being
asked about content, not about positions.
"""

import argparse

import psycopg

from universe import pipeline_lease
from universe.blocks import BLOCKER_VERSION, fetch_blocks
from universe.cuts import parse_cuts, passage_ranges, repair_cuts
from universe.db import connect
from universe.harness import fetch_items, fetch_run

CUTS_STAGE = "passage-cuts"


def passage_id(
    artifact_id: str, first_seq: int, last_seq: int, version: str = BLOCKER_VERSION
) -> str:
    """Identity is the range, not the run that drew it: that is what dedups."""
    return f"{artifact_id}:b{version}:p{first_seq:04d}-{last_seq:04d}"


def materialize(
    conn: psycopg.Connection,
    cuts_run_id: str,
    *,
    commit: bool = True,
) -> dict:
    """Write the passages a cuts run implies, and record it as their origin."""
    run = fetch_run(conn, cuts_run_id)
    if run["stage"] != CUTS_STAGE:
        raise SystemExit(f"{cuts_run_id} is a {run['stage']} run, not {CUTS_STAGE}")

    supervisor = pipeline_lease.current_supervisor(required=True)
    if supervisor is not None:
        supervisor.fence(conn)

    version = str(
        (run.get("params") or {}).get("blocker_version") or BLOCKER_VERSION
    )
    counts = {"passages_new": 0, "passages_existing": 0, "origins_new": 0}
    for item in fetch_items(conn, cuts_run_id):
        if item["error"]:
            if commit:
                raise SystemExit(
                    f"{item['id']} failed and has no cuts: {item['error']}"
                )
            continue

        blocks = fetch_blocks(conn, item["artifact_id"], version)
        if not blocks:
            if not commit:
                continue
            raise SystemExit(
                f"{item['artifact_id']} has no blocks at version {version};"
                " run universe.blocks first"
            )
        seqs = [block["seq"] for block in blocks]
        try:
            cuts = parse_cuts(item["response"])
        except ValueError as exc:
            if commit:
                raise SystemExit(
                    f"{item['id']} did not report usable cuts: {exc}"
                )
            continue

        # Deviations from the contract are repaired, not rejected: the report
        # is where a sloppy run is judged, and a range is a range either way.
        for first, last in passage_ranges(repair_cuts(cuts, seqs), seqs):
            identifier = passage_id(item["artifact_id"], first, last, version)
            written = conn.execute(
                "INSERT INTO passage"
                " (id, artifact_id, blocker_version, first_seq, last_seq)"
                " VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING",
                (identifier, item["artifact_id"], version, first, last),
            ).rowcount
            counts["passages_new" if written else "passages_existing"] += 1
            counts["origins_new"] += conn.execute(
                "INSERT INTO passage_origin (passage_id, run_id) VALUES (%s, %s)"
                " ON CONFLICT DO NOTHING",
                (identifier, cuts_run_id),
            ).rowcount
    if commit:
        conn.commit()
    return counts


def fetch_passages_for_runs(conn: psycopg.Connection, run_ids: list[str]) -> list[dict]:
    """The distinct passages any of these runs produced, in reading order."""
    rows = conn.execute(
        "SELECT DISTINCT p.id, p.artifact_id, p.blocker_version, p.first_seq, p.last_seq"
        " FROM passage p JOIN passage_origin o ON o.passage_id = p.id"
        " WHERE o.run_id = ANY(%s)"
        " ORDER BY p.artifact_id, p.first_seq, p.last_seq",
        (run_ids,),
    ).fetchall()
    keys = "id artifact_id blocker_version first_seq last_seq".split()
    return [dict(zip(keys, row)) for row in rows]


def count_ranges(conn: psycopg.Connection, run_ids: list[str]) -> int:
    """How many ranges these runs drew in total, duplicates included."""
    return conn.execute(
        "SELECT count(*) FROM passage_origin WHERE run_id = ANY(%s)", (run_ids,)
    ).fetchone()[0]


def fetch_passages(conn: psycopg.Connection, passage_ids: list[str]) -> list[dict]:
    rows = conn.execute(
        "SELECT id, artifact_id, blocker_version, first_seq, last_seq FROM passage"
        " WHERE id = ANY(%s) ORDER BY artifact_id, first_seq, last_seq",
        (passage_ids,),
    ).fetchall()
    keys = "id artifact_id blocker_version first_seq last_seq".split()
    return [dict(zip(keys, row)) for row in rows]


# --- the text a model actually reads ----------------------------------------


def source_text(conn: psycopg.Connection, artifact_id: str, version: str = BLOCKER_VERSION) -> str:
    """The whole artifact as its blocks, in order, with nothing marking them."""
    return "\n\n".join(block["body"] for block in fetch_blocks(conn, artifact_id, version))


def passage_text(conn: psycopg.Connection, passage: dict) -> str:
    """The blocks of one passage, in order, with nothing marking them."""
    blocks = fetch_blocks(conn, passage["artifact_id"], passage["blocker_version"])
    return "\n\n".join(
        block["body"]
        for block in blocks
        if passage["first_seq"] <= block["seq"] <= passage["last_seq"]
    )


# --- CLI --------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="universe.passages", description=__doc__)
    parser.add_argument("run_ids", nargs="+", help="passage-cuts run ids")
    args = parser.parse_args(argv)
    with connect() as conn:
        for run_id in args.run_ids:
            counts = materialize(conn, run_id)
            print(
                f"{run_id}: {counts['passages_new']} new passage(s),"
                f" {counts['passages_existing']} already known,"
                f" {counts['origins_new']} new origin(s)"
            )


if __name__ == "__main__":
    main()
