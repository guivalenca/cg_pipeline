"""Focused API/static tests for the Source Publication pilot."""

import uuid
from pathlib import Path

import psycopg
from fastapi.testclient import TestClient
from openpyxl import Workbook, load_workbook

from adalove_workbook import activity, write_adalove_workbook
from universe.graph_identity import GRAPH_ID_CONFLICT_MESSAGE, subject_graph_id_for
from universe.web.acquisition_app import _markdown_renderer
from universe.web.app import create_app


def _namespace(graph_ids=()):
    return {
        "schema_version": "companion_graph_namespace.v1",
        "institutions": [{"slug": "web-inteli", "name": "Inteli Web"}],
        "graph_ids": list(graph_ids),
    }


def _app(database_url: str, *, graph_ids=()):
    return create_app(
        lambda: psycopg.connect(database_url),
        companion_namespace_provider=lambda: _namespace(graph_ids),
    )


def _upload(client: TestClient, path: Path, name: str, syllabus_id: str | None = None):
    data = {"name": name}
    if syllabus_id:
        data["syllabus_id"] = syllabus_id
    else:
        data["institution_id"] = "web-inteli"
    with path.open("rb") as workbook:
        return client.post(
            "/api/syllabi/upload",
            data=data,
            files={
                "file": (
                    path.name,
                    workbook,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )


def _five_subject_workbook(path: Path) -> Path:
    rows = []
    for index, (code, display_name) in enumerate(
        (
            ("COM", "Comunicação"),
            ("MTF", "Matemática"),
            ("NEG", "Negócios"),
            ("UEX", "User Experience"),
            ("LID", "Liderança"),
        ),
        1,
    ):
        lesson = activity(
            week=index,
            order=index * 2 - 1,
            kind="Class",
            title=f"Aula de {display_name}",
            subject=code,
        )
        rows.extend(
            [
                lesson,
                activity(
                    week=index,
                    order=index * 2,
                    kind="Self-study",
                    title=f"Fonte de {display_name}",
                    subject=None,
                    parent_uuid=lesson["Activity UUID"],
                    parent_title=lesson["Title"],
                    url=f"https://example.com/{code.lower()}",
                ),
            ]
        )
    rows.append(
        activity(
            week=6,
            order=11,
            kind="Orientation",
            title="Orientação não curricular",
            subject=None,
        )
    )
    return write_adalove_workbook(path, rows, project="GRAD PILOT")


def test_markdown_renderer_typesets_math_and_blocks_unsafe_media():
    html = _markdown_renderer().render(
        "| Formula | Value |\n| --- | --- |\n| Inline | $x^2$ |\n\n"
        "<script>alert('x')</script>\n\n"
        "![Remote](https://tracker.example/pixel.png)\n\n"
        "![Local](/api/source-assets/asset-safe)"
    )

    assert "<table>" in html and "<math" in html
    assert "<script>" not in html and "&lt;script&gt;" in html
    assert '<img src="https://tracker.example' not in html
    assert '<img src="/api/source-assets/asset-safe"' in html


def test_static_surface_has_only_the_syllabus_operator_route(test_database_url):
    with TestClient(_app(test_database_url)) as client:
        assert client.get("/", follow_redirects=False).headers["location"] == "/syllabi"
        assert client.get("/syllabi").status_code == 200
        assert client.get("/graph").status_code == 404

def test_six_sheet_workbook_exposes_five_curricular_subjects_and_sources(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Pilot syllabus {uuid.uuid4().hex[:8]}"
    workbook_path = _five_subject_workbook(tmp_path / "observer-export.xlsx")
    assert len(load_workbook(workbook_path, read_only=True).sheetnames) == 6

    with TestClient(_app(test_database_url)) as client:
        uploaded = _upload(client, workbook_path, name)
        assert uploaded.status_code == 201, uploaded.text
        result = uploaded.json()
        detail = client.get(f"/api/syllabi/{result['syllabus_id']}").json()

    assert [subject["code"] for subject in detail["lesson_subjects"]] == [
        "COM",
        "LID",
        "MTF",
        "NEG",
        "UEX",
    ]
    assert {lesson["kind"] for lesson in detail["lessons"]} == {"Class"}
    assert len(detail["lessons"]) == 5
    assert all(len(lesson["sources"]) == 1 for lesson in detail["lessons"])
    assert all(not source["has_markdown"] for lesson in detail["lessons"] for source in lesson["sources"])
    assert detail["metadata_complete"] is True
    assert {
        identity["lesson_subject_code"] for identity in detail["export_identities"]
    } == {"COM", "MTF", "NEG", "UEX", "LID"}

    with psycopg.connect(test_database_url) as conn:
        stored = conn.execute(
            "SELECT lesson_subject_code, graph_id FROM syllabus_subject"
            " WHERE syllabus_id = %s ORDER BY lesson_subject_code",
            (result["syllabus_id"],),
        ).fetchall()
    assert stored == [
        (code, subject_graph_id_for("web-inteli", result["syllabus_id"], code))
        for code in ("COM", "LID", "MTF", "NEG", "UEX")
    ]


def test_subject_graph_identity_conflict_is_operator_readable(
    test_database_url, tmp_path
):
    name = f"Conflict syllabus {uuid.uuid4().hex[:8]}"
    path = _five_subject_workbook(tmp_path / "conflict.xlsx")
    syllabus_id = name.casefold().replace(" ", "-")
    occupied = subject_graph_id_for("web-inteli", syllabus_id, "NEG")

    with TestClient(_app(test_database_url, graph_ids=(occupied,))) as client:
        response = _upload(client, path, name)

    assert response.status_code == 409
    assert response.json()["detail"] == {
        "code": "graph_id_conflict",
        "message": GRAPH_ID_CONFLICT_MESSAGE,
        "graph_id": occupied,
    }


def test_malformed_workbook_has_a_clear_validation_error(test_database_url, tmp_path):
    path = tmp_path / "malformed.xlsx"
    workbook = Workbook()
    workbook.active.title = "Activities"
    workbook.save(path)
    workbook.close()

    with TestClient(_app(test_database_url)) as client:
        response = _upload(client, path, f"Malformed {uuid.uuid4().hex[:8]}")

    assert response.status_code == 422
    assert "aba" in response.json()["detail"].casefold()


def test_source_review_is_persisted_through_the_operator_api(test_database_url, tmp_path):
    path = _five_subject_workbook(tmp_path / "review.xlsx")
    with TestClient(_app(test_database_url)) as client:
        uploaded = _upload(client, path, f"Review {uuid.uuid4().hex[:8]}").json()
        detail = client.get(f"/api/syllabi/{uploaded['syllabus_id']}").json()
        reference_id = detail["lessons"][0]["sources"][0]["reference_id"]
        response = client.patch(
            f"/api/syllabi/{uploaded['syllabus_id']}/sources/{reference_id}/review",
            json={"validated": True, "complexity": "simple"},
        )

        assert response.status_code == 422
        assert "publication" in response.json()["detail"].casefold()

        source_id = detail["lessons"][0]["sources"][0]["source_id"]
        with psycopg.connect(test_database_url) as conn:
            conn.execute(
                "INSERT INTO source_snapshot"
                " (id, source_id, content_hash, status) VALUES (%s, %s, %s, 'ok')",
                (f"snapshot-{reference_id}", source_id, "a" * 64),
            )
            conn.execute(
                "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
                " VALUES (%s, %s, 'markdown', 'legacy-import', '# Fonte')",
                (f"artifact-{reference_id}", f"snapshot-{reference_id}"),
            )
        response = client.patch(
            f"/api/syllabi/{uploaded['syllabus_id']}/sources/{reference_id}/review",
            json={"validated": True, "complexity": "simple"},
        )

        assert response.status_code == 200
        with psycopg.connect(test_database_url) as conn:
            conn.execute(
                "INSERT INTO source_snapshot"
                " (id, source_id, content_hash, status) VALUES (%s, %s, %s, 'ok')",
                (f"zz-snapshot-{reference_id}", source_id, "b" * 64),
            )
            conn.execute(
                "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
                " VALUES (%s, %s, 'markdown', 'legacy-import', '# Nova fonte')",
                (f"zz-artifact-{reference_id}", f"zz-snapshot-{reference_id}"),
            )
        refreshed = client.get(f"/api/syllabi/{uploaded['syllabus_id']}").json()

    assert response.status_code == 200
    assert response.json()["review"] == {"validated": True, "complexity": "simple"}
    assert refreshed["lessons"][0]["sources"][0]["review"] == {
        "validated": False,
        "complexity": "simple",
    }
