"""The founder's organizational structure: institutions, courses, groups.

Inherited from Companion: institutions own courses (academic identity only)
and groups, and the group is the sole content authority — a syllabus is
assigned to a group, never to a course.  There is no semester or period
entity.  Everything here is created manually by the founder; nothing is
ever derived from a file name.

The public surface is four writes and one read: ``create_institution``,
``create_course``, ``create_group``, ``assign_syllabus``, and
``structure``, which returns the whole tree the dashboard shows.  Bad
input raises ``ValueError`` with a plain-language message; a reference to
a record that does not exist raises ``LookupError``.
"""

import re

import psycopg
from psycopg.types.json import Jsonb

from universe.syllabus import next_curation_event_id, slugify

INSTITUTION_SLUG = re.compile(r"^[a-z][a-z0-9-]{1,63}$")
COURSE_ID = re.compile(r"^[a-z][a-z0-9-]{1,127}$")


def _clean_name(name: str, what: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{what} name cannot be empty")
    return name.strip()


def _institution(conn: psycopg.Connection, institution_id: str) -> tuple[str, str]:
    row = conn.execute(
        "SELECT id, name FROM institution WHERE id = %s", (institution_id,)
    ).fetchone()
    if row is None:
        raise LookupError(f"no institution with id {institution_id!r}")
    return row


def create_institution(conn: psycopg.Connection, slug: str, name: str) -> dict:
    """Create an institution; its immutable id is the human slug."""
    if not isinstance(slug, str) or not INSTITUTION_SLUG.fullmatch(slug):
        raise ValueError(
            "institution slug must be lowercase letters, digits and hyphens,"
            " start with a letter, and be 2 to 64 characters"
        )
    name = _clean_name(name, "institution")
    try:
        conn.execute(
            "INSERT INTO institution (id, name) VALUES (%s, %s)", (slug, name)
        )
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise ValueError(f"an institution with slug {slug!r} already exists") from None
    conn.commit()
    return {"id": slug, "name": name}


def create_course(conn: psycopg.Connection, institution_id: str, name: str) -> dict:
    """Create a course; its id composes the institution slug and the name."""
    _institution(conn, institution_id)
    name = _clean_name(name, "course")
    name_slug = slugify(name)
    course_id = f"{institution_id}-{name_slug}"
    if not name_slug or not COURSE_ID.fullmatch(course_id):
        raise ValueError(
            f"course name {name!r} does not form a valid course id"
            f" ({course_id!r} must be lowercase text of at most 128 characters)"
        )
    try:
        conn.execute(
            "INSERT INTO course (id, institution_id, name) VALUES (%s, %s, %s)",
            (course_id, institution_id, name),
        )
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise ValueError(
            f"this institution already has a course named {name!r}"
        ) from None
    conn.commit()
    return {"id": course_id, "institution_id": institution_id, "name": name}


def create_group(
    conn: psycopg.Connection,
    institution_id: str,
    name: str,
    course_id: str | None = None,
) -> dict:
    """Create a group — the content authority a syllabus is assigned to.

    The name is free text, unique per institution regardless of case.  A
    group may point at the course it teaches, but never has to.
    """
    _institution(conn, institution_id)
    name = _clean_name(name, "group")
    if course_id is not None:
        row = conn.execute(
            "SELECT institution_id FROM course WHERE id = %s", (course_id,)
        ).fetchone()
        if row is None:
            raise LookupError(f"no course with id {course_id!r}")
        if row[0] != institution_id:
            raise ValueError(
                f"course {course_id!r} belongs to another institution"
            )
    group_id = f"g-{institution_id}-{slugify(name)}"
    if group_id == f"g-{institution_id}-":
        raise ValueError(f"group name {name!r} has no usable characters")
    try:
        conn.execute(
            "INSERT INTO study_group (id, institution_id, name, course_id)"
            " VALUES (%s, %s, %s, %s)",
            (group_id, institution_id, name, course_id),
        )
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise ValueError(
            f"this institution already has a group named {name!r}"
            " (group names are compared ignoring case)"
        ) from None
    conn.commit()
    return {
        "id": group_id,
        "institution_id": institution_id,
        "name": name,
        "course_id": course_id,
    }


def assign_syllabus(
    conn: psycopg.Connection, syllabus_id: str, group_id: str | None
) -> dict:
    """Record the founder's manual choice of which group a syllabus belongs to.

    A ``group_id`` of ``None`` clears the assignment: the syllabus goes back
    to "not assigned to a group yet" and the change is recorded in the same
    curation ledger as an assignment.
    """
    if conn.execute(
        "SELECT 1 FROM syllabus WHERE id = %s", (syllabus_id,)
    ).fetchone() is None:
        raise LookupError(f"no syllabus with id {syllabus_id!r}")
    if group_id is None:
        group = (None, None, None)
    else:
        group = conn.execute(
            "SELECT g.name, i.id, i.name FROM study_group g"
            " JOIN institution i ON i.id = g.institution_id WHERE g.id = %s",
            (group_id,),
        ).fetchone()
        if group is None:
            raise LookupError(f"no group with id {group_id!r}")
    conn.execute(
        "UPDATE syllabus SET group_id = %s WHERE id = %s", (group_id, syllabus_id)
    )
    event_id = next_curation_event_id(conn)
    conn.execute(
        "INSERT INTO curation_event (id, actor, action, subject)"
        " VALUES (%s, 'founder', 'syllabus_group_assign', %s)",
        (event_id, Jsonb({"syllabus_id": syllabus_id, "group_id": group_id})),
    )
    conn.commit()
    return {
        "syllabus_id": syllabus_id,
        "group_id": group_id,
        "group_name": group[0],
        "institution_id": group[1],
        "institution_name": group[2],
    }


def syllabus_groups(conn: psycopg.Connection) -> dict[str, dict]:
    """Group and institution names for every assigned syllabus, by syllabus id."""
    rows = conn.execute(
        "SELECT s.id, g.id, g.name, i.id, i.name"
        " FROM syllabus s"
        " JOIN study_group g ON g.id = s.group_id"
        " JOIN institution i ON i.id = g.institution_id"
    ).fetchall()
    keys = "group_id group_name institution_id institution_name".split()
    return {row[0]: dict(zip(keys, row[1:])) for row in rows}


def _latest_version_counts(conn: psycopg.Connection) -> dict[str, tuple[int, int]]:
    """Item and distinct-source counts of each syllabus's latest version."""
    rows = conn.execute(
        "SELECT v.syllabus_id, count(i.id),"
        " count(DISTINCT i.source_id) FILTER (WHERE i.source_id IS NOT NULL)"
        " FROM syllabus_version v"
        " JOIN (SELECT syllabus_id, max(seq) AS seq FROM syllabus_version"
        "       GROUP BY syllabus_id) latest"
        "   ON latest.syllabus_id = v.syllabus_id AND latest.seq = v.seq"
        " LEFT JOIN syllabus_item i ON i.version_id = v.id"
        " GROUP BY v.syllabus_id"
    ).fetchall()
    return {syllabus_id: (items, sources) for syllabus_id, items, sources in rows}


def structure(conn: psycopg.Connection) -> list[dict]:
    """The full tree: institutions -> courses and groups -> assigned syllabi."""
    counts = _latest_version_counts(conn)
    syllabi_by_group: dict[str, list[dict]] = {}
    for syllabus_id, title, group_id in conn.execute(
        "SELECT id, title, group_id FROM syllabus"
        " WHERE group_id IS NOT NULL ORDER BY created_at, id"
    ).fetchall():
        items, sources = counts.get(syllabus_id, (0, 0))
        syllabi_by_group.setdefault(group_id, []).append(
            {
                "id": syllabus_id,
                "title": title,
                "item_count": items,
                "source_count": sources,
            }
        )

    courses_by_institution: dict[str, list[dict]] = {}
    for course_id, institution_id, name in conn.execute(
        "SELECT id, institution_id, name FROM course ORDER BY created_at, id"
    ).fetchall():
        courses_by_institution.setdefault(institution_id, []).append(
            {"id": course_id, "name": name}
        )

    groups_by_institution: dict[str, list[dict]] = {}
    for group_id, institution_id, name, course_id in conn.execute(
        "SELECT id, institution_id, name, course_id FROM study_group"
        " ORDER BY created_at, id"
    ).fetchall():
        groups_by_institution.setdefault(institution_id, []).append(
            {
                "id": group_id,
                "name": name,
                "course_id": course_id,
                "syllabi": syllabi_by_group.get(group_id, []),
            }
        )

    return [
        {
            "id": institution_id,
            "name": name,
            "courses": courses_by_institution.get(institution_id, []),
            "groups": groups_by_institution.get(institution_id, []),
        }
        for institution_id, name in conn.execute(
            "SELECT id, name FROM institution ORDER BY created_at, id"
        ).fetchall()
    ]
