"""Syllabus facts: workbook adapters, immutable versions and source identity."""

import hashlib
import re
from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from universe.graph_identity import GraphIdConflict, graph_id_for
from universe.syllabus import (
    LEGACY_COLUMNS,
    PROJECT_COLUMNS,
    SyllabusVersionConflict,
    XLSX_MIME,
    canonical_url,
    curate_syllabus,
    get_syllabus_history,
    get_syllabus_version,
    get_syllabus_workbook,
    import_workbook,
    list_syllabi,
    parse_workbook,
    source_identity,
)

WORKBOOK = Path(__file__).resolve().parents[1] / "data" / "GRAD CC07 - 2026-2A.xlsx"


def project_row(
    *,
    project="INTERNAL WORKBOOK TITLE",
    week="Semana 01",
    seq="1",
    title="Lesson",
    kind="Encontro de instrução",
    description="Description",
    url=None,
    parent=None,
    subject="Computação",
    subjects=None,
):
    return [
        project,
        week,
        seq,
        title,
        kind,
        description,
        None,
        None,
        "Sim",
        "0",
        subject,
        subjects,
        url,
        "Não",
        parent,
        "Não",
        "Não",
        "Não",
        "Não",
        None,
        "Não",
    ]


def write_project(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Projetos"
    sheet.append(PROJECT_COLUMNS)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


def legacy_row(
    *,
    week=1,
    seq=1,
    kind="Class",
    title="Lesson",
    parent="",
    description="Description",
    url="",
    code="",
    subject="NEG",
    date="06/08/2026",
):
    values = {
        "Week": week,
        "Sort": seq,
        "Type": kind,
        "Title": title,
        "Date": date,
        "Date source": "own",
        "Parent class": parent,
        "Class date": date,
        "Professor": "Professor",
        "Axis": subject,
        "Related subjects": "",
        "Description": description,
        "URL": url,
        "Resource code": code,
        "Required": "yes",
        "Grade weight": 0,
    }
    return [values[column] for column in LEGACY_COLUMNS]


def write_legacy(path, rows):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "All"
    sheet.append(LEGACY_COLUMNS)
    for row in rows:
        sheet.append(row)
    workbook.save(path)


class TestWorkbookAdapters:
    @pytest.mark.skipif(
        not WORKBOOK.exists(),
        reason="local real-workbook smoke fixture is not versioned",
    )
    def test_real_21_column_workbook_becomes_lessons_with_sources(self):
        parsed = parse_workbook(WORKBOOK)

        assert parsed["format"] == "projetos-21"
        assert parsed["workbook_title"] == "GRAD CC07 - 2026-2A"
        assert parsed["lesson_count"] == 64
        assert parsed["source_count"] == 130
        assert sum(len(lesson["source_references"]) for lesson in parsed["lessons"]) == 130
        database_lesson = next(
            lesson
            for lesson in parsed["lessons"]
            if lesson["title"] == "Programação e Desenvolvimento de Banco de Dados"
        )
        assert database_lesson["subjects"] == [
            "Arquitetura de banco de dados on premisse",
            "Banco de dados relacional",
            "Linguagem de criação e manipulação de dados",
            "SQL Básico",
        ]
        assert "Tipos de ofertas de serviços na nuvem" in {
            source["title"] for source in database_lesson["source_references"]
        }
        first_source = next(
            source
            for lesson in parsed["lessons"]
            for source in lesson["source_references"]
        )
        assert set(first_source["fields"]) == set(PROJECT_COLUMNS)

    def test_project_workbook_promotes_subjects_and_attaches_parent_sources(
        self, tmp_path
    ):
        path = tmp_path / "project.xlsx"
        write_project(
            path,
            [
                project_row(
                    title="Aula de arquitetura",
                    subjects="Arquitetura de nuvem\n,Modelos de serviço em nuvem",
                ),
                project_row(
                    seq="2",
                    title="Leitura de arquitetura",
                    kind="Autoestudo",
                    parent="Aula de arquitetura",
                    subjects="Metadado do autoestudo não curricular",
                    url="https://example.com/architecture",
                ),
            ],
        )

        parsed = parse_workbook(path)

        assert parsed["lesson_count"] == 1
        lesson = parsed["lessons"][0]
        assert lesson["subjects"] == [
            "Arquitetura de nuvem",
            "Modelos de serviço em nuvem",
        ]
        assert [source["url"] for source in lesson["source_references"]] == [
            "https://example.com/architecture"
        ]

    def test_project_workbook_translates_subjects_and_lesson_kinds(self, tmp_path):
        path = tmp_path / "project-taxonomy.xlsx"
        write_project(
            path,
            [
                project_row(seq="1", title="Computação", subject="Computação"),
                project_row(seq="2", title="Experiência", subject="User Experience"),
                project_row(seq="3", title="Liderança", subject="Liderança"),
                project_row(seq="4", title="Negócios", subject="Negócios"),
                project_row(
                    seq="5", title="Planejamento", kind="Encontro de orientação",
                    subject=None,
                ),
                project_row(
                    seq="6", title="Entrega", kind="Desenvolvimento projeto",
                    subject=None,
                ),
                project_row(
                    seq="7", title="Avaliação", kind="Avaliação / pesquisa",
                    subject=None,
                ),
            ],
        )

        parsed = parse_workbook(path)

        assert [lesson["subject"] for lesson in parsed["lessons"][:4]] == [
            "COM", "UEX", "LID", "NEG",
        ]
        assert [lesson["kind"] for lesson in parsed["lessons"]] == [
            "Class", "Class", "Class", "Class",
            "Orientation", "Deliverable", "Evaluation",
        ]
        assert parsed["lessons"][0]["fields"]["Eixo"] == "Computação"

    @pytest.mark.parametrize(
        ("row", "message"),
        [
            (project_row(subject="Marketing"), "unsupported Eixo value 'Marketing'"),
            (
                project_row(kind="Workshop", subject=None),
                "unsupported Tipo da atividade value 'Workshop'",
            ),
            (project_row(subject=None), "Eixo is required for a Class"),
        ],
    )
    def test_project_workbook_rejects_unmapped_lesson_taxonomy(
        self, tmp_path, row, message
    ):
        path = tmp_path / "unmapped-project-taxonomy.xlsx"
        write_project(path, [row])

        with pytest.raises(ValueError, match=message):
            parse_workbook(path)

    def test_legacy_related_workbook_groups_self_study_under_lesson(self, tmp_path):
        path = tmp_path / "legacy.xlsx"
        write_legacy(
            path,
            [
                legacy_row(title="Contabilidade de custos", seq=10),
                legacy_row(
                    kind="Self-study",
                    title="Introdução aos custos",
                    parent="Contabilidade de custos",
                    seq=11,
                    description="Leia as páginas 11 à 18.",
                    url="https://philos.sophia.com.br/terminal/9418",
                    code="9788522485048",
                ),
            ],
        )

        parsed = parse_workbook(path)

        assert parsed["format"] == "related-16"
        assert parsed["lesson_count"] == 1
        lesson = parsed["lessons"][0]
        assert lesson["title"] == "Contabilidade de custos"
        assert lesson["subject"] == "NEG"
        assert lesson["lesson_date"].isoformat() == "2026-08-06"
        source = lesson["source_references"][0]
        assert source["media_type"] == "book"
        assert source["resource_code"] == "9788522485048"
        assert source["scope_kind"] == "pages"
        assert source["scope_value"] == "11-18"

    def test_related_workbook_with_aggregate_and_subject_sheets_prefers_all(self, tmp_path):
        path = tmp_path / "related-multisheet.xlsx"
        workbook = Workbook()
        all_sheet = workbook.active
        all_sheet.title = "All"
        all_sheet.append(LEGACY_COLUMNS)
        all_sheet.append(legacy_row(title="Aula agregada"))
        all_sheet.append(
            legacy_row(
                seq=2,
                kind="Self-study",
                title="Fonte agregada",
                parent="Aula agregada",
                url="https://example.com/all",
            )
        )
        subject_sheet = workbook.create_sheet("NEG")
        subject_sheet.append(LEGACY_COLUMNS)
        subject_sheet.append(legacy_row(title="Aula da matéria"))
        workbook.save(path)

        parsed = parse_workbook(path)

        assert parsed["format"] == "related-16"
        assert parsed["lesson_count"] == 1
        assert parsed["source_count"] == 1
        assert parsed["lessons"][0]["title"] == "Aula agregada"

    def test_unknown_parent_is_a_clear_input_error(self, tmp_path):
        path = tmp_path / "orphan.xlsx"
        write_project(
            path,
            [
                project_row(),
                project_row(
                    seq="2",
                    title="Reading",
                    kind="Autoestudo",
                    parent="Missing lesson",
                    url="https://example.com",
                ),
            ],
        )

        with pytest.raises(ValueError, match="refers to unknown lesson"):
            parse_workbook(path)

    def test_missing_required_columns_names_them(self, tmp_path):
        path = tmp_path / "invalid.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(["Mystery", "URL"])
        workbook.save(path)

        with pytest.raises(ValueError, match="unsupported syllabus workbook"):
            parse_workbook(path)


class TestSourceIdentity:
    def test_articles_drop_fragment_and_tracking(self):
        assert canonical_url(" https://EXAMPLE.com/read?a=1&utm_source=x#part ") == (
            "https://example.com/read?a=1"
        )
        assert source_identity("https://example.com/read#part") == {
            "kind": "article",
            "canonical_url": "https://example.com/read",
        }

    @pytest.mark.parametrize(
        "invalid_url",
        (
            "medium.com/read",
            "/relative/path",
            "mailto:reader@example.com",
            "javascript:alert(1)",
        ),
    )
    def test_articles_require_an_absolute_http_url(self, invalid_url):
        assert canonical_url(invalid_url) == ""
        assert source_identity(invalid_url) is None

    def test_youtube_identity_ignores_timestamp_and_url_form(self):
        watch = source_identity("https://www.youtube.com/watch?v=h4gw6gCP5ls&t=273s")
        short = source_identity("https://youtu.be/h4gw6gCP5ls?t=4")

        assert watch == short == {
            "kind": "video",
            "provider": "youtube",
            "video_id": "h4gw6gCP5ls",
        }

    def test_youtube_identity_repairs_textual_query_separators_from_xlsx(self):
        identity = source_identity(
            "https://www.youtube.com/watch?v=h4gw6gCP5ls%20e%20"
            "list=PL9iw99lS3Prg0hPSCiOz9AXeEmj8W8fL8%20e%20index=14%20e%20t=49s"
        )

        assert identity == {
            "kind": "video",
            "provider": "youtube",
            "video_id": "h4gw6gCP5ls",
        }

    @pytest.mark.parametrize(
        "url",
        (
            "https://www.youtube.com/watch?v=not-a-real-id",
            "https://youtu.be/too-short",
            "https://www.youtube.com/watch?v=h4gw6gCP5ls%20unexpected",
        ),
    )
    def test_youtube_identity_rejects_invalid_provider_ids(self, url):
        assert source_identity(url) is None

    def test_books_are_resource_code_plus_scope_not_gateway_url(self):
        gateway = "https://philos.sophia.com.br/terminal/9418"
        first = source_identity(
            gateway,
            media_kind="book",
            resource_code="978-85-224-8504-8",
            scope_kind="pages",
            scope_value="11 à 18",
        )
        other_scope = source_identity(
            gateway,
            media_kind="book",
            resource_code="9788522485048",
            scope_kind="pages",
            scope_value="19-20",
        )
        other_book = source_identity(
            gateway,
            media_kind="book",
            resource_code="9788569726760",
            scope_kind="pages",
            scope_value="11-18",
        )

        assert first == {
            "kind": "book",
            "resource_code": "9788522485048",
            "scope": {"kind": "pages", "value": "11-18"},
        }
        assert first != other_scope
        assert first != other_book

    def test_incomplete_book_reference_does_not_mint_a_false_source(self):
        assert source_identity(
            "https://philos.sophia.com.br/terminal/9418",
            media_kind="book",
            resource_code="9788522485048",
        ) is None


class TestVersionedImport:
    def test_new_named_import_requires_durable_metadata_by_default(self, db, tmp_path):
        path = tmp_path / "requires-metadata.xlsx"
        write_project(path, [project_row(project="Metadata required")])

        with pytest.raises(ValueError, match="instituição"):
            import_workbook(db, path, "Metadata required")

        assert db.execute(
            "SELECT 1 FROM syllabus WHERE id = 'metadata-required'"
        ).fetchone() is None

    def test_new_version_keeps_stored_graph_id_even_when_companion_lists_it(
        self, db, tmp_path
    ):
        db.execute(
            "INSERT INTO institution (id, name) VALUES ('inteli', 'Inteli')"
            " ON CONFLICT (id) DO NOTHING"
        )
        path = tmp_path / "own-graph-id.xlsx"
        write_project(path, [project_row(project="Own graph id")])
        first = import_workbook(db, path, "Own graph id", institution_id="inteli")
        minted = db.execute(
            "SELECT graph_id FROM syllabus WHERE id = %s", (first["syllabus_id"],)
        ).fetchone()[0]
        assert minted == graph_id_for("inteli", "Own graph id")

        write_project(
            path,
            [project_row(project="Own graph id", title="Lesson renamed")],
        )
        second = import_workbook(
            db,
            path,
            "Own graph id",
            syllabus_id=first["syllabus_id"],
            occupied_graph_ids={minted},
        )

        assert second["seq"] == 2
        assert second["version_id"] != first["version_id"]
        assert db.execute(
            "SELECT graph_id FROM syllabus WHERE id = %s", (first["syllabus_id"],)
        ).fetchone()[0] == minted

    def test_new_version_rejects_occupied_graph_id_when_syllabus_has_none(
        self, db, tmp_path
    ):
        db.execute(
            "INSERT INTO institution (id, name) VALUES ('inteli', 'Inteli')"
            " ON CONFLICT (id) DO NOTHING"
        )
        db.execute(
            "INSERT INTO syllabus (id, title, institution_id)"
            " VALUES ('no-graph-id', 'No graph id', 'inteli')"
        )
        db.execute(
            "INSERT INTO syllabus_version (id, syllabus_id, seq, origin)"
            " VALUES ('no-graph-id:v0001', 'no-graph-id', 1, 'upload')"
        )
        db.commit()
        derived = graph_id_for("inteli", "No graph id")
        path = tmp_path / "no-graph-id.xlsx"
        write_project(path, [project_row(project="No graph id")])

        with pytest.raises(GraphIdConflict) as raised:
            import_workbook(
                db,
                path,
                "No graph id",
                syllabus_id="no-graph-id",
                occupied_graph_ids={derived},
            )
        db.rollback()

        assert raised.value.graph_id == derived
        assert db.execute(
            "SELECT graph_id FROM syllabus WHERE id = 'no-graph-id'"
        ).fetchone()[0] is None
        assert db.execute(
            "SELECT count(*) FROM syllabus_version WHERE syllabus_id = 'no-graph-id'"
        ).fetchone()[0] == 1

    def test_name_is_manual_and_uploaded_xlsx_is_retained_exactly(self, db, tmp_path):
        path = tmp_path / "input.xlsx"
        write_project(
            path,
            [
                project_row(
                    project="DO NOT USE AS NAME",
                    subjects="Arquitetura de nuvem\n,Modelos de serviço em nuvem",
                )
            ],
        )
        original = path.read_bytes()
        run_count = db.execute("SELECT count(*) FROM run").fetchone()[0]

        result = import_workbook(
            db, path, "SI módulo 7 2026", require_syllabus_metadata=False
        )

        assert result["syllabus_id"] == "si-modulo-7-2026"
        assert result["seq"] == 1
        assert result["lesson_count"] == 1
        assert result["reference_count"] == 0
        assert db.execute("SELECT count(*) FROM run").fetchone()[0] == run_count
        stored = get_syllabus_workbook(db, result["version_id"])
        assert stored == {
            "file_name": "input.xlsx",
            "mime_type": XLSX_MIME,
            "sha256": hashlib.sha256(original).hexdigest(),
            "body": original,
        }
        assert list_syllabi(db)[0]["title"] == "SI módulo 7 2026"
        assert get_syllabus_version(db, result["syllabus_id"])["lessons"][0][
            "subjects"
        ] == ["Arquitetura de nuvem", "Modelos de serviço em nuvem"]

    def test_same_file_is_idempotent_within_one_syllabus(self, db, tmp_path):
        path = tmp_path / "same.xlsx"
        write_project(path, [project_row(project="UNRELATED")])

        first = import_workbook(
            db, path, "Idempotent syllabus", require_syllabus_metadata=False
        )
        second = import_workbook(
            db, path, "Idempotent syllabus", require_syllabus_metadata=False
        )

        assert second["unchanged"] is True
        assert second["version_id"] == first["version_id"]
        assert second["lesson_count"] == 1
        assert second["reference_count"] == 0
        assert second["source_count"] == 0
        assert second["new_source_count"] == 0
        assert get_syllabus_history(db, first["syllabus_id"])["versions"][0]["seq"] == 1

    def test_import_counts_reused_references_as_sources_without_calling_them_new(
        self, db, tmp_path
    ):
        path = tmp_path / "reused-source.xlsx"
        lesson = project_row(project="IGNORED")
        source = project_row(
            project="IGNORED",
            seq="2",
            title="Assigned article",
            kind="Autoestudo",
            parent="Lesson",
            url="https://example.com/reused",
        )
        write_project(path, [lesson, source])
        first = import_workbook(
            db, path, "Reused source syllabus", require_syllabus_metadata=False
        )

        source[5] = "Description changed without changing source identity"
        write_project(path, [lesson, source])
        second = import_workbook(
            db, path, "Reused source syllabus", require_syllabus_metadata=False
        )
        unchanged = import_workbook(
            db, path, "Reused source syllabus", require_syllabus_metadata=False
        )

        assert first["source_count"] == first["reference_count"] == 1
        assert first["new_source_count"] == 1
        assert second["source_count"] == second["reference_count"] == 1
        assert second["new_source_count"] == 0
        assert unchanged["source_count"] == unchanged["reference_count"] == 1
        assert unchanged["new_source_count"] == 0

    def test_upload_event_allocator_ignores_uuid_style_event_suffixes(
        self, db, tmp_path
    ):
        db.execute(
            "INSERT INTO curation_event (id, actor, action, subject)"
            " VALUES (%s, 'worker', 'source_acquisition_queued', '{}'::jsonb)",
            ("ce-acq-deadbeef999999999999999999999999",),
        )
        db.commit()
        path = tmp_path / "curation-id.xlsx"
        write_project(path, [project_row(project="IGNORED")])

        result = import_workbook(
            db, path, "Strict curation id syllabus", require_syllabus_metadata=False
        )

        event_id = db.execute(
            "SELECT id FROM curation_event"
            " WHERE action = 'syllabus_upload' AND subject->>'version_id' = %s",
            (result["version_id"],),
        ).fetchone()[0]
        assert re.fullmatch(r"ce\d+", event_id)

    def test_latest_and_history_are_full_immutable_versions(self, db, tmp_path):
        path = tmp_path / "versions.xlsx"
        lesson = project_row(project="IGNORED")
        source = project_row(
            project="IGNORED",
            seq="2",
            title="Assigned article",
            kind="Autoestudo",
            parent="Lesson",
            url="https://example.com/v1",
        )
        write_project(path, [lesson, source])
        first = import_workbook(
            db, path, "Versioned syllabus", require_syllabus_metadata=False
        )
        first_view = get_syllabus_version(db, first["syllabus_id"])

        source[12] = "https://example.com/v2"
        source[5] = "Changed description"
        write_project(path, [lesson, source])
        second = import_workbook(
            db, path, "Versioned syllabus", require_syllabus_metadata=False
        )

        latest = get_syllabus_version(db, first["syllabus_id"])
        historical = get_syllabus_version(db, first["syllabus_id"], first["version_id"])
        history = get_syllabus_history(db, first["syllabus_id"])
        assert [version["seq"] for version in history["versions"]] == [2, 1]
        assert latest["version"]["id"] == second["version_id"]
        assert latest["lessons"][0]["sources"][0]["url"] == "https://example.com/v2"
        assert historical["lessons"][0]["sources"][0]["url"] == "https://example.com/v1"
        assert first_view["lessons"] == historical["lessons"]

    def test_removed_reference_is_hidden_latest_but_source_and_artifact_survive(self, db, tmp_path):
        path = tmp_path / "removal.xlsx"
        lesson = project_row(project="IGNORED")
        source = project_row(
            project="IGNORED",
            seq="2",
            title="Assigned article",
            kind="Autoestudo",
            parent="Lesson",
            url="https://example.com/lasting",
        )
        write_project(path, [lesson, source])
        first = import_workbook(
            db, path, "Removal syllabus", require_syllabus_metadata=False
        )
        first_view = get_syllabus_version(db, first["syllabus_id"])
        source_id = first_view["lessons"][0]["sources"][0]["source_id"]
        db.execute(
            "INSERT INTO source_snapshot"
            " (id, source_id, content_hash, status) VALUES (%s, %s, %s, 'ok')",
            ("snap-lasting", source_id, "sha-lasting"),
        )
        db.execute(
            "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
            " VALUES ('art-lasting', 'snap-lasting', 'markdown', 'test', '# Preserved')"
        )
        db.commit()

        write_project(path, [lesson])
        import_workbook(
            db, path, "Removal syllabus", require_syllabus_metadata=False
        )

        latest = get_syllabus_version(db, first["syllabus_id"])
        historical = get_syllabus_version(db, first["syllabus_id"], first["version_id"])
        assert latest["lessons"][0]["sources"] == []
        assert historical["lessons"][0]["sources"][0]["source_id"] == source_id
        assert db.execute("SELECT body FROM artifact WHERE id = 'art-lasting'").fetchone()[0] == "# Preserved"

    def test_sophia_gateway_mints_distinct_sources_by_code_and_scope(self, db, tmp_path):
        path = tmp_path / "books.xlsx"
        gateway = "https://philos.sophia.com.br/terminal/9418"
        write_legacy(
            path,
            [
                legacy_row(title="Books lesson"),
                legacy_row(
                    seq=2,
                    kind="Self-study",
                    title="Book A",
                    parent="Books lesson",
                    description="Páginas 10-20",
                    url=gateway,
                    code="9780000000001",
                ),
                legacy_row(
                    seq=3,
                    kind="Self-study",
                    title="Book B",
                    parent="Books lesson",
                    description="Páginas 10-20",
                    url=gateway,
                    code="9780000000002",
                ),
                legacy_row(
                    seq=4,
                    kind="Self-study",
                    title="Book A later",
                    parent="Books lesson",
                    description="Páginas 21-30",
                    url=gateway,
                    code="9780000000001",
                ),
            ],
        )

        result = import_workbook(
            db, path, "Books syllabus", require_syllabus_metadata=False
        )
        view = get_syllabus_version(db, result["syllabus_id"])
        source_ids = {source["source_id"] for source in view["lessons"][0]["sources"]}

        assert len(source_ids) == 3
        assert None not in source_ids

    def test_book_without_scope_remains_visible_without_source(self, db, tmp_path):
        path = tmp_path / "incomplete-book.xlsx"
        gateway = "https://philos.sophia.com.br/terminal/9418"
        write_legacy(
            path,
            [
                legacy_row(title="Books lesson"),
                legacy_row(
                    seq=2,
                    kind="Self-study",
                    title="Book without scope",
                    parent="Books lesson",
                    description="Read this book",
                    url=gateway,
                    code="9780000000001",
                ),
            ],
        )

        result = import_workbook(
            db, path, "Incomplete books", require_syllabus_metadata=False
        )
        source = get_syllabus_version(db, result["syllabus_id"])["lessons"][0]["sources"][0]

        assert source["media_type"] == "book"
        assert source["resource_code"] == "9780000000001"
        assert source["scope"] is None
        assert source["source_id"] is None


class TestSyllabusCuration:
    def _import_related(self, db, tmp_path):
        path = tmp_path / "editable.xlsx"
        write_legacy(
            path,
            [
                legacy_row(title="Aula editável", description="Descrição original"),
                legacy_row(
                    seq=2,
                    kind="Self-study",
                    title="Fonte A",
                    parent="Aula editável",
                    description="Descrição A",
                    url="https://example.com/a",
                ),
                legacy_row(
                    seq=3,
                    kind="Self-study",
                    title="Fonte B",
                    parent="Aula editável",
                    description="Descrição B",
                    url="https://example.com/b",
                ),
            ],
        )
        return import_workbook(
            db, path, "Syllabus editável", require_syllabus_metadata=False
        )

    def test_editor_authors_new_complete_version_and_preserves_old_facts(self, db, tmp_path):
        imported = self._import_related(db, tmp_path)
        before = get_syllabus_version(db, imported["syllabus_id"])
        source_a = before["lessons"][0]["sources"][0]
        source_b = before["lessons"][0]["sources"][1]
        payload = [
            {
                "id": before["lessons"][0]["id"],
                "week": 2,
                "kind": "Class",
                "title": "Aula revisada",
                "subject": "NEG",
                "subjects": ["Custos fixos", "Custos variáveis"],
                "date": "2026-08-13",
                "description": "Descrição revisada",
                "sources": [
                    {
                        "reference_id": source_b["reference_id"],
                        "title": "Fonte B revisada",
                        "description": "Descrição B revisada",
                        "url": source_b["url"],
                        "media_type": "article",
                        "hidden": True,
                    },
                    {
                        "title": "Fonte nova",
                        "description": "Adicionada manualmente",
                        "url": "https://example.com/new",
                        "media_type": "article",
                        "hidden": False,
                    },
                ],
            }
        ]

        result = curate_syllabus(
            db, imported["syllabus_id"], imported["version_id"], payload,
            note="Reorganiza fontes e revisa a aula.",
        )

        assert result["seq"] == 2
        assert result["unchanged"] is False
        assert result["reference_count"] == 2
        latest = get_syllabus_version(db, imported["syllabus_id"])
        historical = get_syllabus_version(
            db, imported["syllabus_id"], imported["version_id"]
        )
        assert latest["lessons"][0]["title"] == "Aula revisada"
        assert latest["lessons"][0]["subjects"] == [
            "Custos fixos",
            "Custos variáveis",
        ]
        assert [source["title"] for source in latest["lessons"][0]["sources"]] == [
            "Fonte B revisada",
            "Fonte nova",
        ]
        assert latest["lessons"][0]["sources"][0]["hidden"] is True
        assert historical["lessons"][0]["title"] == "Aula editável"
        assert [source["title"] for source in historical["lessons"][0]["sources"]] == [
            "Fonte A",
            "Fonte B",
        ]
        assert db.execute("SELECT count(*) FROM source WHERE id = %s", (source_a["source_id"],)).fetchone()[0] == 1

    def test_curated_xlsx_round_trips_order_edits_and_visibility(self, db, tmp_path):
        imported = self._import_related(db, tmp_path)
        before = get_syllabus_version(db, imported["syllabus_id"])
        sources = before["lessons"][0]["sources"]
        payload = [
            {
                **{key: before["lessons"][0].get(key) for key in ("id", "week", "kind", "title", "subject", "description")},
                "subjects": ["Custos fixos", "Rentabilidade, ROI, EBITDA"],
                "date": "2026-08-06",
                "sources": [
                    {
                        **{key: sources[1].get(key) for key in (
                            "reference_id", "title", "description", "url", "media_type",
                            "resource_code", "scope_kind", "scope_value",
                        )},
                        "hidden": True,
                    },
                    {
                        **{key: sources[0].get(key) for key in (
                            "reference_id", "title", "description", "url", "media_type",
                            "resource_code", "scope_kind", "scope_value",
                        )},
                        "hidden": False,
                    },
                ],
            }
        ]
        curated = curate_syllabus(
            db, imported["syllabus_id"], imported["version_id"], payload,
            note="Reordena fontes e atualiza a visibilidade.",
        )
        workbook = get_syllabus_workbook(db, curated["version_id"])
        exported = tmp_path / workbook["file_name"]
        exported.write_bytes(workbook["body"])

        parsed = parse_workbook(exported)

        assert parsed["format"] == "related-16"
        assert parsed["lessons"][0]["subjects"] == [
            "Custos fixos",
            "Rentabilidade, ROI, EBITDA",
        ]
        assert [source["title"] for source in parsed["lessons"][0]["source_references"]] == [
            "Fonte B",
            "Fonte A",
        ]
        assert parsed["lessons"][0]["source_references"][0]["is_hidden"] is True
        assert parsed["lessons"][0]["source_references"][1]["is_hidden"] is False

    def test_stale_editor_cannot_overwrite_a_newer_version(self, db, tmp_path):
        imported = self._import_related(db, tmp_path)
        before = get_syllabus_version(db, imported["syllabus_id"])
        lesson = before["lessons"][0]
        payload = [{
            "id": lesson["id"], "week": lesson["week"], "kind": lesson["kind"],
            "title": "Primeira mudança", "subject": lesson["subject"],
            "date": str(lesson["date"] or ""), "description": lesson["description"],
            "sources": lesson["sources"],
        }]
        curate_syllabus(
            db, imported["syllabus_id"], imported["version_id"], payload,
            note="Primeira mudança concorrente.",
        )

        with pytest.raises(SyllabusVersionConflict, match="versão mais nova"):
            curate_syllabus(
                db, imported["syllabus_id"], imported["version_id"], payload,
                note="Tentativa sobre versão antiga.",
            )

    def test_saving_an_unchanged_projection_does_not_mint_noise_version(self, db, tmp_path):
        imported = self._import_related(db, tmp_path)
        before = get_syllabus_version(db, imported["syllabus_id"])
        history_before = get_syllabus_history(db, imported["syllabus_id"])["versions"]
        payload = []
        for lesson in before["lessons"]:
            payload.append(
                {
                    "id": lesson["id"],
                    "week": lesson["week"],
                    "kind": lesson["kind"],
                    "title": lesson["title"],
                    "subject": lesson["subject"],
                    "date": str(lesson["date"] or ""),
                    "description": lesson["description"],
                    "sources": lesson["sources"],
                }
            )

        result = curate_syllabus(
            db, imported["syllabus_id"], imported["version_id"], payload
        )

        assert result["unchanged"] is True
        assert result["version_id"] == imported["version_id"]
        assert get_syllabus_history(db, imported["syllabus_id"])["versions"] == history_before
