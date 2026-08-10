"""Concrete chapter, page, and unit scope for book source references."""

import psycopg

from universe import curation
from universe.syllabus import BOOK_SCOPE


def extract_scope(description: str) -> str | None:
    """Return the first concrete book scope written in ``description``."""
    match = BOOK_SCOPE.search(description or "")
    return match.group(0) if match else None


def get_override(conn: psycopg.Connection, source_id: str) -> str | None:
    """Return the latest operational scope override for legacy dashboards."""
    event = curation.latest_source_event(
        conn, source_id, curation.SOURCE_SCOPE_OVERRIDE_ACTIONS
    )
    if (
        event is None
        or event["action"] == curation.SOURCE_SCOPE_OVERRIDE_CLEARED_ACTION
    ):
        return None
    return event["subject"].get("value")


def is_missing_scope(source_row: dict, conn=None) -> bool:
    """Say whether a book source lacks an explicit chapter, page, or unit."""
    # Keep accepting the original ``(conn, source_row)`` call shape while
    # callers migrate to the source-first API.
    if not isinstance(source_row, dict):
        source_row, conn = conn, source_row
    source = source_row.get("source") or source_row
    item = source_row.get("item") or source_row
    if source.get("media_type") != "book":
        return False
    if conn:
        source_id = source.get("id") or source.get("source_id")
        if source_id and get_override(conn, source_id) is not None:
            return False
    text = f"{item.get('description') or ''}"
    return BOOK_SCOPE.search(text) is None
