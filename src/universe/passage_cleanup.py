"""Run passage triage and element refinement to terminal, auditable states.

    python -m universe.passage_cleanup run --cuts-run r0017 \
        --model deepseek/deepseek-v3.2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import uuid

import psycopg
from psycopg.types.json import Jsonb

from universe.blocks import fetch_blocks
from universe.db import connect
from universe.harness import (
    PROMPTS_DIR,
    Target,
    execute,
    fetch_items,
    fetch_run,
    json_object,
    load_prompt,
    load_tool,
    positive_int,
)
from universe.model_client import DEFAULT_MAX_TOKENS, ModelClient
from universe.passage_refine import (
    RefinementDropsPassage,
    RefinementError,
    RefinementRemovesUnresolvedImage,
    materialize_revision,
    numbered_elements,
    state,
)
from universe.passages import fetch_passages_for_runs, materialize
from universe.triage import build_targets, cleanup_verdict_of

TRIAGE_STAGE = "passage-triage"
REFINE_STAGE = "passage-refine"
DEFAULT_WORKERS = 4


def _insert_result(
    conn: psycopg.Connection,
    cleanup_id: str,
    current: dict,
    verdict: str,
    decision_item_id: str | None,
    policy_reason: str | None = None,
) -> None:
    conn.execute(
        "INSERT INTO passage_cleanup_result"
        " (cleanup_id, passage_id, passage_revision_id, decision_run_item_id,"
        " verdict, policy_reason) VALUES (%s, %s, %s, %s, %s, %s)",
        (
            cleanup_id,
            current["passage"]["id"],
            current["revision_id"],
            decision_item_id,
            verdict,
            policy_reason,
        ),
    )


def _record_run(conn: psycopg.Connection, cleanup_id: str, run_id: str) -> None:
    conn.execute(
        "UPDATE passage_cleanup SET run_ids = run_ids || %s WHERE id = %s",
        (Jsonb([run_id]), cleanup_id),
    )
    conn.commit()


def _triage_batch(
    conn: psycopg.Connection,
    *,
    cleanup_id: str,
    round_number: int,
    states: list[dict],
    prompt,
    client: ModelClient,
    workers: int,
    atomic: bool,
) -> tuple[str, list[dict]]:
    passages = [current["passage"] for current in states]
    by_passage = {current["passage"]["id"]: current for current in states}
    targets = build_targets(conn, passages, by_passage)
    summary = execute(
        conn,
        prompt,
        client,
        targets,
        workers=workers,
        run_params={
            "cleanup_id": cleanup_id,
            "round": round_number,
            "atomic_passages": atomic,
        },
    )
    _record_run(conn, cleanup_id, summary["run_id"])
    return summary["run_id"], fetch_items(conn, summary["run_id"])


def _refine_batch(
    conn: psycopg.Connection,
    *,
    cleanup_id: str,
    round_number: int,
    states: list[dict],
    prompt,
    client: ModelClient,
    workers: int,
) -> tuple[str, list[dict]]:
    base_targets = build_targets(
        conn,
        [current["passage"] for current in states],
        {current["passage"]["id"]: current for current in states},
    )
    current_by_id = {current["passage"]["id"]: current for current in states}
    targets = [
        Target(
            target.source_id,
            target.source_title,
            target.artifact_id,
            "",
            passage_id=target.passage_id,
            extra_fields={
                "passage": numbered_elements(
                    current_by_id[target.passage_id]["elements"]
                )
            },
            passage_revision_id=target.passage_revision_id,
        )
        for target in base_targets
    ]
    summary = execute(
        conn,
        prompt,
        client,
        targets,
        workers=workers,
        run_params={
            "cleanup_id": cleanup_id,
            "round": round_number,
        },
    )
    _record_run(conn, cleanup_id, summary["run_id"])
    return summary["run_id"], fetch_items(conn, summary["run_id"])


def _validate_partition(conn: psycopg.Connection, passages: list[dict]) -> None:
    by_artifact: dict[str, list[dict]] = {}
    for passage in passages:
        by_artifact.setdefault(passage["artifact_id"], []).append(passage)
    for artifact_id, rows in by_artifact.items():
        versions = {passage["blocker_version"] for passage in rows}
        if len(versions) != 1:
            raise SystemExit(f"cuts run mixes blocker versions for {artifact_id}")
        version = next(iter(versions))
        element_seqs = [
            element["seq"] for element in fetch_blocks(conn, artifact_id, version)
        ]
        if not element_seqs:
            raise SystemExit(f"no elements for {artifact_id} at blocker version {version}")
        rows.sort(key=lambda item: item["first_seq"])
        expected = element_seqs[0]
        for passage in rows:
            if passage["first_seq"] != expected:
                raise SystemExit(
                    f"cuts run does not form one passage partition for {artifact_id}"
                )
            expected = passage["last_seq"] + 1
        if expected != element_seqs[-1] + 1:
            raise SystemExit(
                f"cuts run does not cover every element for {artifact_id}"
            )


def _write_canonical_artifacts(conn: psycopg.Connection, cleanup_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT p.id, p.artifact_id, p.blocker_version, p.first_seq, p.last_seq,"
        " r.passage_revision_id, r.verdict"
        " FROM passage_cleanup_result r JOIN passage p ON p.id = r.passage_id"
        " WHERE r.cleanup_id = %s"
        " ORDER BY p.artifact_id, p.first_seq",
        (cleanup_id,),
    ).fetchall()
    keys = (
        "id artifact_id blocker_version first_seq last_seq passage_revision_id verdict"
    ).split()
    grouped: dict[str, list[dict]] = {}
    for row in rows:
        passage = dict(zip(keys, row))
        grouped.setdefault(passage["artifact_id"], []).append(passage)

    written = []
    for source_artifact_id, results in grouped.items():
        elements = []
        unknown = []
        for result in results:
            if result["verdict"] == "drop":
                continue
            current = state(conn, result, result["passage_revision_id"])
            elements.extend(current["elements"])
            if result["verdict"] == "unknown":
                unknown.append(result["id"])
        body = "\n\n".join(element["body"] for element in elements).rstrip() + "\n"
        snapshot_id, source_metadata = conn.execute(
            "SELECT snapshot_id, metadata FROM artifact WHERE id = %s",
            (source_artifact_id,),
        ).fetchone()
        artifact_id = f"{source_artifact_id}:clean:{cleanup_id}"
        conn.execute(
            "INSERT INTO artifact"
            " (id, snapshot_id, kind, tool, tool_version, body, metadata)"
            " VALUES (%s, %s, 'markdown', 'passage-cleanup', 'v1', %s, %s)"
            " ON CONFLICT (id) DO NOTHING",
            (
                artifact_id,
                snapshot_id,
                body,
                Jsonb({
                    "source_markdown_artifact_id": source_artifact_id,
                    "cleanup_id": cleanup_id,
                    "unknown_passage_ids": unknown,
                    "body_sha256": hashlib.sha256(body.encode()).hexdigest(),
                    **(
                        {"visual_analysis": source_metadata["visual_analysis"]}
                        if (source_metadata or {}).get("visual_analysis")
                        else {}
                    ),
                }),
            ),
        )
        conn.execute(
            "INSERT INTO passage_cleanup_artifact"
            " (cleanup_id, source_artifact_id, canonical_artifact_id)"
            " VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
            (cleanup_id, source_artifact_id, artifact_id),
        )
        written.append(artifact_id)
    conn.commit()
    return written


def run_cleanup(
    conn: psycopg.Connection,
    *,
    cuts_run_id: str,
    model: str,
    triage_prompt,
    refine_prompt,
    triage_client: ModelClient,
    atomic_triage_client: ModelClient,
    refine_client: ModelClient,
    workers: int = DEFAULT_WORKERS,
) -> dict:
    cuts_run = fetch_run(conn, cuts_run_id)
    if cuts_run["stage"] != "passage-cuts":
        raise SystemExit(f"{cuts_run_id} is not a passage-cuts run")
    materialize(conn, cuts_run_id)
    passages = fetch_passages_for_runs(conn, [cuts_run_id])
    if not passages:
        raise SystemExit(f"{cuts_run_id} produced no passages")
    _validate_partition(conn, passages)

    cleanup_id = f"pc-{uuid.uuid4().hex}"
    conn.execute(
        "INSERT INTO passage_cleanup"
        " (id, cuts_run_id, model, triage_prompt_ref, refine_prompt_ref, status)"
        " VALUES (%s, %s, %s, %s, %s, 'running')",
        (
            cleanup_id,
            cuts_run_id,
            model,
            triage_prompt.ref,
            refine_prompt.ref,
        ),
    )
    conn.commit()

    active = [state(conn, passage) for passage in passages]
    errors: list[str] = []
    round_number = 0
    while active:
        round_number += 1
        atomic = [current for current in active if len(current["elements"]) == 1]
        composite = [current for current in active if len(current["elements"]) > 1]
        triage_items = []
        if composite:
            _, items = _triage_batch(
                conn,
                cleanup_id=cleanup_id,
                round_number=round_number,
                states=composite,
                prompt=triage_prompt,
                client=triage_client,
                workers=workers,
                atomic=False,
            )
            triage_items.extend(items)
        if atomic:
            _, items = _triage_batch(
                conn,
                cleanup_id=cleanup_id,
                round_number=round_number,
                states=atomic,
                prompt=triage_prompt,
                client=atomic_triage_client,
                workers=workers,
                atomic=True,
            )
            triage_items.extend(items)

        by_id = {current["passage"]["id"]: current for current in active}
        refinements = []
        for item in triage_items:
            current = by_id[item["passage_id"]]
            verdict = cleanup_verdict_of(item)
            if verdict == "unparseable":
                errors.append(f"{item['id']} has no usable triage verdict")
            elif verdict == "refine":
                if len(current["elements"]) == 1:
                    errors.append(f"{item['id']} tried to refine an atomic passage")
                else:
                    refinements.append(current)
            else:
                _insert_result(
                    conn,
                    cleanup_id,
                    current,
                    verdict,
                    item["id"],
                )
        conn.commit()
        if errors:
            break
        if not refinements:
            active = []
            break

        _, refine_items = _refine_batch(
            conn,
            cleanup_id=cleanup_id,
            round_number=round_number,
            states=refinements,
            prompt=refine_prompt,
            client=refine_client,
            workers=workers,
        )
        by_id = {current["passage"]["id"]: current for current in refinements}
        next_active = []
        for item in refine_items:
            current = by_id[item["passage_id"]]
            try:
                revision = materialize_revision(
                    conn,
                    passage=current["passage"],
                    refine_item=item,
                    parent_revision_id=current["revision_id"],
                )
            except RefinementDropsPassage:
                # A valid element-addressed plan may reveal that no teachable
                # content remains. That is the precise terminal meaning of
                # dropping this passage, not a pipeline failure.
                _insert_result(conn, cleanup_id, current, "drop", item["id"])
                continue
            except RefinementRemovesUnresolvedImage:
                # Unresolved visuals are protected source evidence. Preserve
                # the exact state the refiner saw instead of letting one
                # unsafe removal prevent publication of the whole source.
                _insert_result(
                    conn,
                    cleanup_id,
                    current,
                    "unknown",
                    item["id"],
                    policy_reason="unresolved_image_preserved",
                )
                continue
            except RefinementError as exc:
                errors.append(f"{item['id']}: {exc}")
                continue
            if revision is None:
                _insert_result(conn, cleanup_id, current, "unknown", item["id"])
            else:
                next_active.append(
                    state(conn, current["passage"], revision["id"])
                )
        conn.commit()
        if errors:
            break
        active = next_active

    if errors:
        conn.execute(
            "UPDATE passage_cleanup SET status = 'failed', finished_at = now()"
            " WHERE id = %s",
            (cleanup_id,),
        )
        conn.commit()
        return {"cleanup_id": cleanup_id, "status": "failed", "errors": errors}

    result_count = conn.execute(
        "SELECT count(*) FROM passage_cleanup_result WHERE cleanup_id = %s",
        (cleanup_id,),
    ).fetchone()[0]
    if result_count != len(passages):
        errors.append(
            f"cleanup produced {result_count} terminal result(s) for"
            f" {len(passages)} passage(s)"
        )
        conn.execute(
            "UPDATE passage_cleanup SET status = 'failed', finished_at = now()"
            " WHERE id = %s",
            (cleanup_id,),
        )
        conn.commit()
        return {"cleanup_id": cleanup_id, "status": "failed", "errors": errors}

    artifacts = _write_canonical_artifacts(conn, cleanup_id)
    conn.execute(
        "UPDATE passage_cleanup SET status = 'done', finished_at = now() WHERE id = %s",
        (cleanup_id,),
    )
    conn.commit()
    return {
        "cleanup_id": cleanup_id,
        "status": "done",
        "artifacts": artifacts,
        "passages": len(passages),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.passage_cleanup", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--cuts-run", required=True)
    run.add_argument("--model", required=True)
    run.add_argument("--triage-prompt", default="v004")
    run.add_argument("--refine-prompt", default="v002")
    run.add_argument(
        "--triage-tool",
        default=str(PROMPTS_DIR / TRIAGE_STAGE / "tool-v003.json"),
    )
    run.add_argument(
        "--atomic-triage-tool",
        default=str(PROMPTS_DIR / TRIAGE_STAGE / "tool-v003-atomic.json"),
    )
    run.add_argument(
        "--refine-tool",
        default=str(PROMPTS_DIR / REFINE_STAGE / "tool-v002.json"),
    )
    run.add_argument("--workers", type=positive_int, default=DEFAULT_WORKERS)
    run.add_argument("--temperature", type=float, default=0)
    run.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    run.add_argument("--extra", type=json_object)
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    triage_prompt = load_prompt(TRIAGE_STAGE, args.triage_prompt)
    refine_prompt = load_prompt(REFINE_STAGE, args.refine_prompt, require_body=False)
    shared = args.extra or {}

    def client(tool_path: str) -> ModelClient:
        extra = {**load_tool(tool_path), **shared}
        return ModelClient(
            args.model,
            temperature=args.temperature,
            max_tokens=args.max_tokens,
            extra=extra,
        )

    with connect() as conn:
        result = run_cleanup(
            conn,
            cuts_run_id=args.cuts_run,
            model=args.model,
            triage_prompt=triage_prompt,
            refine_prompt=refine_prompt,
            triage_client=client(args.triage_tool),
            atomic_triage_client=client(args.atomic_triage_tool),
            refine_client=client(args.refine_tool),
            workers=args.workers,
        )
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "done":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
