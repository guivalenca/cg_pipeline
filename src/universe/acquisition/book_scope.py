"""Concrete chapter, page, and unit scope for book source references."""

from universe.syllabus import BOOK_SCOPE


def extract_scope(description: str) -> str | None:
    """Return the first concrete book scope written in ``description``."""
    match = BOOK_SCOPE.search(description or "")
    return match.group(0) if match else None


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
    # Scope is part of a book Source's identity.  Corrections author another
    # Syllabus Version and resolve another Source; there is no mutable global
    # scope override to consult here (ADR 0006 / ADR 0012).
    text = f"{item.get('description') or ''}"
    return BOOK_SCOPE.search(text) is None
