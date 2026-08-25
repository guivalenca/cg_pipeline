"""Read historical Group labels used by the dashboard overview.

Institution identity for Syllabus authoring comes from Companion. Course and
Group editing no longer belongs to Concept Universe, but old assignments stay
readable while those records exist.
"""

import psycopg


def syllabus_groups(conn: psycopg.Connection) -> dict[str, dict]:
    """Return Group and Institution labels for assigned Syllabi, keyed by id."""
    rows = conn.execute(
        "SELECT s.id, g.id, g.name, i.id, i.name"
        " FROM syllabus s"
        " JOIN study_group g ON g.id = s.group_id"
        " JOIN institution i ON i.id = g.institution_id"
    ).fetchall()
    keys = "group_id group_name institution_id institution_name".split()
    return {row[0]: dict(zip(keys, row[1:])) for row in rows}
