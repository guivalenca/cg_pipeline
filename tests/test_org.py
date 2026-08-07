"""Organizational structure: institutions, courses, groups, assignment.

Namespace-tolerant: every record here carries an `orgx` prefix, nothing is
cleaned up, and assertions filter to this module's own records.
"""

import psycopg
import pytest
from fastapi.testclient import TestClient

import universe.web.app as web_app
from universe import org


@pytest.fixture(scope="module")
def institution(db):
    return org.create_institution(db, "orgx-uni", "Orgx University")


@pytest.fixture(scope="module")
def course(db, institution):
    return org.create_course(db, institution["id"], "Ciência da Computação Orgx")


@pytest.fixture(scope="module")
def group(db, institution, course):
    return org.create_group(db, institution["id"], "Orgx 2026-2A", course["id"])


@pytest.fixture(scope="module")
def assigned_syllabus(db, group):
    db.execute(
        "INSERT INTO syllabus (id, title)"
        " VALUES ('orgx-syllabus', 'Orgx Syllabus') ON CONFLICT DO NOTHING"
    )
    db.commit()
    return org.assign_syllabus(db, "orgx-syllabus", group["id"])


def test_create_institution_returns_slug_identity(institution):
    assert institution == {"id": "orgx-uni", "name": "Orgx University"}


def test_institution_slug_and_name_validation(db):
    for bad_slug in ("Orgx-Uni", "1orgx", "a", "orgx uni", ""):
        with pytest.raises(ValueError, match="slug"):
            org.create_institution(db, bad_slug, "Valid Name")
    with pytest.raises(ValueError, match="name"):
        org.create_institution(db, "orgx-noname", "   ")


def test_institution_slug_is_unique(db, institution):
    with pytest.raises(ValueError, match="already exists"):
        org.create_institution(db, institution["id"], "Another Name")


def test_course_id_composes_institution_and_normalized_name(course):
    assert course["id"] == "orgx-uni-ciencia-da-computacao-orgx"
    assert course["institution_id"] == "orgx-uni"
    assert course["name"] == "Ciência da Computação Orgx"


def test_course_requires_existing_institution_and_usable_name(db, institution):
    with pytest.raises(LookupError, match="orgx-ghost"):
        org.create_course(db, "orgx-ghost", "Algorithms")
    with pytest.raises(ValueError, match="course id"):
        org.create_course(db, institution["id"], "###")


def test_course_name_is_unique_per_institution(db, institution, course):
    with pytest.raises(ValueError, match="already has a course"):
        org.create_course(db, institution["id"], "Ciencia da Computacao Orgx")


def test_group_is_minted_with_g_prefix_and_optional_course(db, institution, group):
    assert group == {
        "id": "g-orgx-uni-orgx-2026-2a",
        "institution_id": "orgx-uni",
        "name": "Orgx 2026-2A",
        "course_id": "orgx-uni-ciencia-da-computacao-orgx",
    }
    courseless = org.create_group(db, institution["id"], "Orgx courseless group")
    assert courseless["course_id"] is None


def test_group_name_is_unique_per_institution_ignoring_case(db, institution, group):
    with pytest.raises(ValueError, match="already has a group"):
        org.create_group(db, institution["id"], "ORGX 2026-2a")


def test_group_references_are_validated(db, institution, course):
    with pytest.raises(LookupError, match="orgx-ghost"):
        org.create_group(db, "orgx-ghost", "Whatever")
    with pytest.raises(LookupError, match="no course"):
        org.create_group(db, institution["id"], "Orgx bad course", "orgx-ghost-course")
    other = org.create_institution(db, "orgx-other-uni", "Orgx Other University")
    with pytest.raises(ValueError, match="another institution"):
        org.create_group(db, other["id"], "Orgx cross group", course["id"])
    with pytest.raises(ValueError, match="name"):
        org.create_group(db, institution["id"], "  ")


def test_assignment_is_recorded_with_plain_names(db, assigned_syllabus):
    assert assigned_syllabus == {
        "syllabus_id": "orgx-syllabus",
        "group_id": "g-orgx-uni-orgx-2026-2a",
        "group_name": "Orgx 2026-2A",
        "institution_id": "orgx-uni",
        "institution_name": "Orgx University",
    }
    stored = db.execute(
        "SELECT group_id FROM syllabus WHERE id = 'orgx-syllabus'"
    ).fetchone()
    assert stored == ("g-orgx-uni-orgx-2026-2a",)
    events = db.execute(
        "SELECT count(*) FROM curation_event"
        " WHERE action = 'syllabus_group_assign'"
        "   AND subject->>'syllabus_id' = 'orgx-syllabus'"
    ).fetchone()
    assert events[0] >= 1


def test_assignment_clears_with_none_and_stays_reassignable(db, group):
    db.execute(
        "INSERT INTO syllabus (id, title)"
        " VALUES ('orgx-clearable', 'Orgx Clearable') ON CONFLICT DO NOTHING"
    )
    db.commit()
    org.assign_syllabus(db, "orgx-clearable", group["id"])

    cleared = org.assign_syllabus(db, "orgx-clearable", None)
    assert cleared == {
        "syllabus_id": "orgx-clearable",
        "group_id": None,
        "group_name": None,
        "institution_id": None,
        "institution_name": None,
    }
    assert db.execute(
        "SELECT group_id FROM syllabus WHERE id = 'orgx-clearable'"
    ).fetchone() == (None,)
    events = db.execute(
        "SELECT count(*) FROM curation_event"
        " WHERE action = 'syllabus_group_assign'"
        "   AND subject->>'syllabus_id' = 'orgx-clearable'"
        "   AND subject->'group_id' = 'null'::jsonb"
    ).fetchone()
    assert events[0] >= 1

    # Reassignment after a clear is just another assignment, and the clear
    # works again afterwards (leaving this syllabus out of the shared tree).
    again = org.assign_syllabus(db, "orgx-clearable", group["id"])
    assert again["group_id"] == group["id"]
    assert org.assign_syllabus(db, "orgx-clearable", None)["group_id"] is None


def test_assignment_requires_existing_syllabus_and_group(db, group):
    with pytest.raises(LookupError, match="no syllabus"):
        org.assign_syllabus(db, "orgx-ghost-syllabus", group["id"])
    with pytest.raises(LookupError, match="no group"):
        org.assign_syllabus(db, "orgx-syllabus", "g-orgx-ghost")


def test_structure_tree_shape_and_unassigned_syllabus_untouched(
    db, institution, course, group, assigned_syllabus
):
    db.execute(
        "INSERT INTO syllabus (id, title)"
        " VALUES ('orgx-unassigned', 'Orgx Unassigned') ON CONFLICT DO NOTHING"
    )
    db.commit()

    tree = org.structure(db)
    mine = next(node for node in tree if node["id"] == institution["id"])
    assert mine["name"] == "Orgx University"
    assert {"id": course["id"], "name": course["name"]} in mine["courses"]
    groups = {node["id"]: node for node in mine["groups"]}
    assert group["id"] in groups
    assert groups[group["id"]]["course_id"] == course["id"]
    assert groups[group["id"]]["syllabi"] == [
        {
            "id": "orgx-syllabus",
            "title": "Orgx Syllabus",
            "item_count": 0,
            "source_count": 0,
        }
    ]

    every_syllabus = {
        syllabus["id"]
        for node in tree
        for group_node in node["groups"]
        for syllabus in group_node["syllabi"]
    }
    assert "orgx-unassigned" not in every_syllabus
    assert db.execute(
        "SELECT group_id FROM syllabus WHERE id = 'orgx-unassigned'"
    ).fetchone() == (None,)


# --- The HTTP surface ---


@pytest.fixture(scope="module")
def client(db, test_database_url):
    original_connect = web_app.connect
    web_app.connect = lambda: psycopg.connect(test_database_url)
    try:
        with TestClient(web_app.create_app()) as test_client:
            yield test_client
    finally:
        web_app.connect = original_connect


def test_api_creates_the_whole_hierarchy(client):
    institution = client.post(
        "/api/org/institutions",
        json={"slug": "orgx-api-uni", "name": "Orgx API University"},
    )
    assert institution.status_code == 200, institution.text

    course = client.post(
        "/api/org/courses",
        json={"institution_id": "orgx-api-uni", "name": "Orgx API Course"},
    )
    assert course.status_code == 200, course.text
    course_id = course.json()["id"]

    group = client.post(
        "/api/org/groups",
        json={
            "institution_id": "orgx-api-uni",
            "name": "Orgx API Group",
            "course_id": course_id,
        },
    )
    assert group.status_code == 200, group.text

    tree = client.get("/api/org")
    assert tree.status_code == 200
    mine = next(
        node for node in tree.json()["institutions"] if node["id"] == "orgx-api-uni"
    )
    assert [item["id"] for item in mine["courses"]] == [course_id]
    assert [item["id"] for item in mine["groups"]] == [group.json()["id"]]


def test_api_errors_are_plain_400s_and_404s(client):
    duplicate = client.post(
        "/api/org/institutions",
        json={"slug": "orgx-api-uni", "name": "Twice"},
    )
    assert duplicate.status_code == 400
    assert "already exists" in duplicate.json()["detail"]

    missing_name = client.post(
        "/api/org/groups", json={"institution_id": "orgx-api-uni"}
    )
    assert missing_name.status_code == 400
    assert missing_name.json()["detail"] == "name is required"

    ghost_institution = client.post(
        "/api/org/courses",
        json={"institution_id": "orgx-api-ghost", "name": "Anything"},
    )
    assert ghost_institution.status_code == 404
    assert "orgx-api-ghost" in ghost_institution.json()["detail"]


def test_api_assigns_syllabus_to_group(client, db, group):
    db.execute(
        "INSERT INTO syllabus (id, title)"
        " VALUES ('orgx-api-syllabus', 'Orgx API Syllabus') ON CONFLICT DO NOTHING"
    )
    db.commit()

    response = client.post(
        "/api/syllabi/orgx-api-syllabus/assign-group",
        json={"group_id": group["id"]},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["group_name"] == group["name"]
    assert payload["institution_name"] == "Orgx University"

    ghost_group = client.post(
        "/api/syllabi/orgx-api-syllabus/assign-group",
        json={"group_id": "g-orgx-ghost"},
    )
    assert ghost_group.status_code == 404

    ghost_syllabus = client.post(
        "/api/syllabi/orgx-ghost/assign-group", json={"group_id": group["id"]}
    )
    assert ghost_syllabus.status_code == 404


def test_api_clears_assignment_with_null_group(client, db):
    cleared = client.post(
        "/api/syllabi/orgx-api-syllabus/assign-group", json={"group_id": None}
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["group_id"] is None
    assert db.execute(
        "SELECT group_id FROM syllabus WHERE id = 'orgx-api-syllabus'"
    ).fetchone() == (None,)

    # The key must be sent: an empty payload is a mistake, not a clear.
    missing_key = client.post(
        "/api/syllabi/orgx-api-syllabus/assign-group", json={}
    )
    assert missing_key.status_code == 400
    assert missing_key.json()["detail"] == "group_id is required"

    blank = client.post(
        "/api/syllabi/orgx-api-syllabus/assign-group", json={"group_id": "  "}
    )
    assert blank.status_code == 400
