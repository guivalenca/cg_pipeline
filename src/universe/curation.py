"""Read append-only curation events that affect operational Source behavior."""

import psycopg

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
