"""Record founder edits to syllabus items as insert-only curation events.

An edit never rewrites the imported workbook fact.  ``record_edit`` appends
one ``curation_event`` row that carries both the value the founder saw at
write time (``old``) and the value they chose (``new``); the stored
``syllabus_item`` stays exactly as received.  Reading back is a recompute:
``edit_history`` lists an item's events newest first, and
``effective_fields`` reduces them to the overlay the dashboard lays on top
of the stored item.  A URL edit resolves-or-mints the canonical source
through the same seam workbook import uses, so the effective item points at
a real source row.
"""

import psycopg
from psycopg.types.json import Jsonb

from universe.syllabus import next_curation_event_id, resolve_source

EDITABLE_FIELDS = ("title", "url", "description")
EDIT_ACTION = "syllabus_item_edit"
SOURCE_SKIP_ACTION = "source_skip"
SOURCE_UNSKIP_ACTION = "source_unskip"
SOURCE_SKIP_ACTIONS = (SOURCE_SKIP_ACTION, SOURCE_UNSKIP_ACTION)
SOURCE_SCOPE_OVERRIDE_ACTION = "source_scope_override"
SOURCE_SCOPE_OVERRIDE_CLEARED_ACTION = "source_scope_override_cleared"
SOURCE_SCOPE_OVERRIDE_ACTIONS = (
    SOURCE_SCOPE_OVERRIDE_ACTION,
    SOURCE_SCOPE_OVERRIDE_CLEARED_ACTION,
)


def latest_source_event(
    conn: psycopg.Connection, source_id: str, actions: tuple[str, ...]
) -> dict | None:
    """Return the newest event for one source among related action types."""
    row = conn.execute(
        "SELECT action, subject, note, created_at FROM curation_event"
        " WHERE action = ANY(%s) AND subject->>'source_id' = %s"
        " ORDER BY created_at DESC,"
        " substring(id from '[0-9]+$')::int DESC NULLS LAST, id DESC LIMIT 1",
        (list(actions), source_id),
    ).fetchone()
    if row is None:
        return None
    return dict(zip(("action", "subject", "note", "created_at"), row))


def source_is_skipped(conn: psycopg.Connection, source_id: str) -> bool:
    """A source is skipped only when its newest skip-related event is a skip."""
    event = latest_source_event(conn, source_id, SOURCE_SKIP_ACTIONS)
    return bool(event and event["action"] == SOURCE_SKIP_ACTION)


def record_edit(
    conn: psycopg.Connection,
    item_id: str,
    field: str,
    value: str,
    actor: str,
    note: str | None = None,
) -> dict:
    """Append one edit event for a syllabus item and return its subject.

    Raises ``ValueError`` for a non-editable field or empty value and
    ``LookupError`` for an unknown item.  The ``old`` value recorded is the
    effective value at write time, so successive edits chain naturally.
    """
    if field not in EDITABLE_FIELDS:
        raise ValueError(f"field must be one of: {', '.join(EDITABLE_FIELDS)}")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("value must be a non-empty string")
    value = value.strip()
    row = conn.execute(
        "SELECT title, url, description FROM syllabus_item WHERE id = %s",
        (item_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown syllabus item {item_id!r}")
    stored = dict(zip(("title", "url", "description"), row))
    overlay = effective_fields(conn, [item_id]).get(item_id, {})
    subject = {
        "item_id": item_id,
        "field": field,
        "old": overlay.get(field, stored[field]),
        "new": value,
    }
    if field == "url":
        title = overlay.get("title") or stored["title"]
        subject["source_id"], _created = resolve_source(conn, value, title)
    event_id = next_curation_event_id(conn)
    conn.execute(
        "INSERT INTO curation_event (id, actor, action, subject, note)"
        " VALUES (%s, %s, %s, %s, %s)",
        (event_id, actor, EDIT_ACTION, Jsonb(subject), note),
    )
    conn.commit()
    return {"event_id": event_id, **subject}


def edit_history(conn: psycopg.Connection, item_ids) -> dict[str, list[dict]]:
    """List each item's edit events newest first: field, old, new, at, note."""
    return {
        item_id: [
            {
                "field": event["field"],
                "old": event["old"],
                "new": event["new"],
                "at": event["at"],
                "note": event["note"],
            }
            for event in events
        ]
        for item_id, events in _events(conn, item_ids).items()
    }


def effective_fields(conn: psycopg.Connection, item_ids) -> dict[str, dict]:
    """Reduce each item's events to {field: newest edited value}.

    A URL edit also carries the ``source_id`` it resolved to, so the
    effective item can point at the re-linked source.
    """
    result: dict[str, dict] = {}
    for item_id, events in _events(conn, item_ids).items():
        overlay = result.setdefault(item_id, {})
        for event in events:  # newest first: the first write per field wins
            if event["field"] in overlay:
                continue
            overlay[event["field"]] = event["new"]
            if event["field"] == "url":
                overlay["source_id"] = event["source_id"]
    return result


def _events(conn: psycopg.Connection, item_ids) -> dict[str, list[dict]]:
    """Fetch edit events for the given items, newest first per item."""
    if not item_ids:
        return {}
    rows = conn.execute(
        "SELECT subject->>'item_id', subject->>'field', subject->>'old',"
        " subject->>'new', subject->>'source_id', note, created_at"
        " FROM curation_event"
        " WHERE action = %s AND subject->>'item_id' = ANY(%s)"
        " ORDER BY created_at DESC, substring(id from '[0-9]+$')::int DESC",
        (EDIT_ACTION, list(item_ids)),
    ).fetchall()
    events: dict[str, list[dict]] = {}
    for item_id, field, old, new, source_id, note, at in rows:
        events.setdefault(item_id, []).append(
            {
                "field": field,
                "old": old,
                "new": new,
                "source_id": source_id,
                "note": note,
                "at": at,
            }
        )
    return events
