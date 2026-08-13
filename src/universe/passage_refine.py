"""Element-addressed passage refinement with immutable lineage."""

from __future__ import annotations

import hashlib
import json
from typing import Any

import psycopg

from universe.blocks import fetch_blocks


class RefinementError(ValueError):
    """A tool response cannot be applied to the passage state it saw."""


class RefinementDropsPassage(RefinementError):
    """The refiner selected every remaining element, so the passage is empty."""


class RefinementRemovesUnresolvedImage(RefinementError):
    """The refiner selected protected visual evidence it could not assess."""


def raw_elements(conn: psycopg.Connection, passage: dict) -> list[dict]:
    elements = [
        block
        for block in fetch_blocks(
            conn, passage["artifact_id"], passage["blocker_version"]
        )
        if passage["first_seq"] <= block["seq"] <= passage["last_seq"]
    ]
    expected = list(range(passage["first_seq"], passage["last_seq"] + 1))
    if [element["seq"] for element in elements] != expected:
        raise RefinementError("passage does not resolve to a complete element range")
    return elements


def fetch_revision(conn: psycopg.Connection, revision_id: str) -> dict:
    row = conn.execute(
        "SELECT id, passage_id, parent_revision_id, refine_run_item_id,"
        " iteration, body, content_hash, created_at"
        " FROM passage_revision WHERE id = %s",
        (revision_id,),
    ).fetchone()
    if row is None:
        raise RefinementError(f"unknown passage revision {revision_id}")
    keys = (
        "id passage_id parent_revision_id refine_run_item_id iteration body"
        " content_hash created_at"
    ).split()
    return dict(zip(keys, row))


def dropped_block_ids(conn: psycopg.Connection, revision_id: str) -> set[str]:
    rows = conn.execute(
        "WITH RECURSIVE lineage AS ("
        " SELECT id, parent_revision_id FROM passage_revision WHERE id = %s"
        " UNION ALL"
        " SELECT p.id, p.parent_revision_id FROM passage_revision p"
        " JOIN lineage l ON p.id = l.parent_revision_id"
        ")"
        " SELECT d.block_id FROM passage_revision_drop d"
        " JOIN lineage l ON l.id = d.revision_id",
        (revision_id,),
    ).fetchall()
    return {row[0] for row in rows}


def effective_elements(
    conn: psycopg.Connection, passage: dict, revision_id: str | None = None
) -> list[dict]:
    elements = raw_elements(conn, passage)
    if revision_id is None:
        return elements
    revision = fetch_revision(conn, revision_id)
    if revision["passage_id"] != passage["id"]:
        raise RefinementError("passage revision belongs to another passage")
    dropped = dropped_block_ids(conn, revision_id)
    raw_ids = {element["id"] for element in elements}
    outside = dropped - raw_ids
    if outside:
        raise RefinementError("passage revision drops an element outside its passage")
    retained = [element for element in elements if element["id"] not in dropped]
    body = effective_body(retained)
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if revision["body"] != body or revision["content_hash"] != content_hash:
        raise RefinementError("stored passage revision does not match its element lineage")
    return retained


def effective_body(elements: list[dict]) -> str:
    return "\n\n".join(element["body"] for element in elements)


def numbered_elements(elements: list[dict]) -> str:
    rendered = []
    for number, element in enumerate(elements, 1):
        attributes = [f'n="{number}"', f'kind="{element["kind"]}"']
        if element.get("image_state"):
            attributes.append(f'image_state="{element["image_state"]}"')
        rendered.append(
            f"<element {' '.join(attributes)}>\n{element['body']}\n</element>"
        )
    return "\n\n".join(rendered)


def parse_drop_elements(response: str) -> list[int]:
    try:
        value = json.loads(response)
    except (TypeError, json.JSONDecodeError) as exc:
        raise RefinementError("refine response is not valid JSON") from exc
    if not isinstance(value, dict) or set(value) != {"drop_elements"}:
        raise RefinementError("refine response must contain only drop_elements")
    numbers = value["drop_elements"]
    if not isinstance(numbers, list) or not all(
        isinstance(number, int) and not isinstance(number, bool) for number in numbers
    ):
        raise RefinementError("drop_elements must be a list of integers")
    if len(numbers) != len(set(numbers)):
        raise RefinementError("drop_elements contains duplicates")
    return numbers


def validate_plan(
    elements: list[dict],
    numbers: list[int],
) -> list[dict]:
    if not numbers:
        return []
    if len(elements) <= 1:
        raise RefinementError("an atomic passage cannot be refined")
    outside = [number for number in numbers if number < 1 or number > len(elements)]
    if outside:
        raise RefinementError(f"drop_elements outside passage: {outside}")
    wanted = set(numbers)
    selected = [
        element for number, element in enumerate(elements, 1) if number in wanted
    ]
    if len(numbers) == len(elements):
        raise RefinementDropsPassage("refinement removes every passage element")
    if any(element.get("image_state") == "unresolved" for element in selected):
        raise RefinementRemovesUnresolvedImage(
            "an unresolved image cannot be removed"
        )
    return selected


def revision_id_for(passage_id: str, run_item_id: str) -> str:
    digest = hashlib.sha256(run_item_id.encode()).hexdigest()[:20]
    return f"{passage_id}:rev:{digest}"


def _stored_refine_item(conn: psycopg.Connection, run_item_id: str) -> dict:
    row = conn.execute(
        "SELECT r.stage, i.passage_id, i.passage_revision_id, i.response, i.error"
        " FROM run_item i JOIN run r ON r.id = i.run_id WHERE i.id = %s",
        (run_item_id,),
    ).fetchone()
    if row is None:
        raise RefinementError(f"unknown refine run item {run_item_id}")
    keys = "stage passage_id passage_revision_id response error".split()
    return dict(zip(keys, row))


def _revision_from_item(
    conn: psycopg.Connection, refine_run_item_id: str
) -> dict | None:
    row = conn.execute(
        "SELECT id FROM passage_revision WHERE refine_run_item_id = %s",
        (refine_run_item_id,),
    ).fetchone()
    return fetch_revision(conn, row[0]) if row else None


def materialize_revision(
    conn: psycopg.Connection,
    *,
    passage: dict,
    refine_item: dict,
    parent_revision_id: str | None,
) -> dict | None:
    """Apply one tool plan. Empty plans are explicit no-progress outcomes."""
    run_item_id = refine_item.get("id")
    if not isinstance(run_item_id, str) or not run_item_id:
        raise RefinementError("refine item has no identity")
    stored_item = _stored_refine_item(conn, run_item_id)
    if stored_item["stage"] != "passage-refine":
        raise RefinementError("run item is not from passage-refine")
    if stored_item["error"]:
        raise RefinementError(f"refine call failed: {stored_item['error']}")
    if stored_item["passage_id"] != passage["id"]:
        raise RefinementError("refine item belongs to another passage")
    if stored_item["passage_revision_id"] != parent_revision_id:
        raise RefinementError("refine item did not see the declared parent revision")

    existing = _revision_from_item(conn, run_item_id)
    if existing is not None:
        if (
            existing["passage_id"] != passage["id"]
            or existing["parent_revision_id"] != parent_revision_id
        ):
            raise RefinementError("stored refine result has incompatible lineage")
        # Recompute once on read so idempotency cannot conceal partial or
        # externally-mutated lineage.
        effective_elements(conn, passage, existing["id"])
        return existing

    numbers = parse_drop_elements(stored_item["response"])
    elements = effective_elements(conn, passage, parent_revision_id)
    selected = validate_plan(elements, numbers)
    if not selected:
        return None

    selected_ids = {element["id"] for element in selected}
    retained = [element for element in elements if element["id"] not in selected_ids]
    body = effective_body(retained)
    identifier = revision_id_for(passage["id"], run_item_id)
    parent = fetch_revision(conn, parent_revision_id) if parent_revision_id else None
    iteration = (parent["iteration"] if parent else 0) + 1
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()

    conn.execute(
        "INSERT INTO passage_revision"
        " (id, passage_id, parent_revision_id, refine_run_item_id, iteration,"
        "  body, content_hash)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s)"
        " ON CONFLICT (refine_run_item_id) DO NOTHING",
        (
            identifier,
            passage["id"],
            parent_revision_id,
            run_item_id,
            iteration,
            body,
            content_hash,
        ),
    )
    for element in selected:
        conn.execute(
            "INSERT INTO passage_revision_drop (revision_id, block_id)"
            " VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (identifier, element["id"]),
        )
    conn.commit()
    return fetch_revision(conn, identifier)


def state(
    conn: psycopg.Connection, passage: dict, revision_id: str | None = None
) -> dict[str, Any]:
    elements = effective_elements(conn, passage, revision_id)
    return {
        "passage": passage,
        "revision_id": revision_id,
        "elements": elements,
        "body": effective_body(elements),
    }
