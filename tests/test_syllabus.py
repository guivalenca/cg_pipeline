"""Syllabus intake tests: parse, classify, import, and version workbooks."""

from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from universe.syllabus import (
    COLUMNS,
    book_scope_missing,
    canonical_url,
    diff_versions,
    import_workbook,
    media_type,
    parse_workbook,
)

WORKBOOK = Path(__file__).resolve().parents[1] / "data" / "GRAD CC07 - 2026-2A.xlsx"


class TestParseWorkbook:
    """Parse the reference workbook and validate its shape."""

    def test_parse_real_workbook(self):
        """Parse the reference workbook."""
        parsed = parse_workbook(WORKBOOK)

        assert parsed["syllabus_id"] == "grad-cc07-2026-2a"
        assert parsed["title"] == "GRAD CC07 - 2026-2A"
        assert len(parsed["items"]) == 194
        assert sum(
            item["kind"] == "Autoestudo" and bool(item["url"])
            for item in parsed["items"]
        ) == 130

    def test_parse_header_validation(self, tmp_path):
        """Missing/unknown columns raise clear errors."""
        path = tmp_path / "bad-header.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(["Mystery" if column == "URL" else column for column in COLUMNS])
        workbook.save(path)

        with pytest.raises(ValueError) as exc_info:
            parse_workbook(path)

        error = str(exc_info.value)
        assert "missing columns: URL" in error
        assert "unknown columns: Mystery" in error

    def test_parse_week_extraction(self):
        """Week values parse as integers."""
        items = parse_workbook(WORKBOOK)["items"]

        assert items[0]["week"] == 1
        assert all(isinstance(item["week"], int) for item in items)
        assert all(1 <= item["week"] <= 10 for item in items)

    def test_parse_uniqueness(self):
        """(Semana, Atividade) tuples are unique."""
        items = parse_workbook(WORKBOOK)["items"]
        keys = [(item["week"], item["title"]) for item in items]

        assert len(keys) == len(set(keys)) == 194
        assert all(tuple(item["fields"]) == COLUMNS for item in items)

    def test_parse_fields_complete(self):
        """All fields dict has all 21 columns."""
        items = parse_workbook(WORKBOOK)["items"]

        for item in items:
            assert set(item["fields"].keys()) == set(COLUMNS)
            # url attribute is stripped/normalized
            url_in_fields = item["fields"]["URL"]
            expected_url = (url_in_fields or "").strip() if url_in_fields else ""
            assert item["url"] == expected_url


class TestCanonicalUrl:
    """URL normalization: strip whitespace, fragment, utm params."""

    def test_strip_whitespace(self):
        assert canonical_url("  https://example.com  ") == "https://example.com"

    def test_remove_fragment(self):
        assert canonical_url("https://example.com#section") == "https://example.com"

    def test_remove_utm_params(self):
        url = "https://example.com?utm_source=twitter&utm_medium=social"
        assert canonical_url(url) == "https://example.com"

    def test_keep_other_params(self):
        url = "https://example.com?id=123&utm_source=social&name=test"
        assert canonical_url(url) == "https://example.com?id=123&name=test"

    def test_combined_cleanup(self):
        url = " https://example.com/read?a=1&utm_source=mail&b=two#page-2 "
        assert canonical_url(url) == "https://example.com/read?a=1&b=two"

    def test_no_params(self):
        assert canonical_url("https://example.com/page") == "https://example.com/page"


class TestMediaType:
    """Classify URLs by media type."""

    def test_youtube(self):
        assert media_type("https://youtube.com/watch?v=123") == "video"
        assert media_type("https://youtu.be/123") == "video"

    def test_vimeo(self):
        assert media_type("https://vimeo.com/123") == "video"

    def test_ted(self):
        assert media_type("https://ted.com/talks/123") == "video"

    def test_book_sophia(self):
        assert media_type("https://sophia.example.com/book") == "book"
        assert media_type("https://example.com/sophia/content") == "book"

    def test_book_inteli(self):
        assert media_type("https://integrada.minhabiblioteca.com.br/books/123") == "book"

    def test_article_default(self):
        assert media_type("https://example.com/article") == "article"
        assert media_type("") == "article"


class TestBookScopeMissing:
    """Flag incomplete book references."""

    def test_book_with_chapter(self):
        """Book with chapter specification is complete."""
        item = {
            "url": "https://integrada.minhabiblioteca.com.br/book",
            "title": "Reading",
            "description": "See chapter 5 for details",
        }
        assert book_scope_missing(item) is False

    def test_book_with_paginas(self):
        """Book with páginas is complete."""
        item = {
            "url": "https://integrada.minhabiblioteca.com.br/book",
            "title": "Study",
            "description": "Páginas 10-20",
        }
        assert book_scope_missing(item) is False

    def test_book_without_scope(self):
        """Book without chapter/pages spec is flagged."""
        item = {
            "url": "https://integrada.minhabiblioteca.com.br/book",
            "title": "Study Material",
            "description": "Read this textbook",
        }
        assert book_scope_missing(item) is True

    def test_non_book(self):
        """Non-book URLs always return False."""
        item = {
            "url": "https://example.com/article",
            "title": "Article",
            "description": "No scope info",
        }
        assert book_scope_missing(item) is False


class TestImportWorkbook:
    """Import workbooks and record immutable versions."""

    def test_import_first_version(self, db, tmp_path):
        """Import a new syllabus creates version 1."""
        path = tmp_path / "test.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-2026-1",
            "Semana 01",
            "1",
            "Lesson 1",
            "Autoestudo",
            "Description",
            None, None, "Sim", "0", None, None,
            "https://git.inteli.edu.br",
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        result = import_workbook(db, path)

        assert result["unchanged"] is False
        assert result["seq"] == 1
        assert result["syllabus_id"] == "test-2026-1"
        assert result["item_count"] == 1
        assert result["source_count"] == 1

        # Verify source was inserted
        source = db.execute(
            "SELECT id, title FROM source WHERE id LIKE 'src-%' ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        assert source is not None
        assert source[1] == "Lesson 1"

    def test_import_idempotent(self, db, tmp_path):
        """Re-importing identical file returns unchanged=True."""
        path = tmp_path / "test.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-IDEM",
            "Semana 01",
            "1",
            "Lesson",
            "Autoestudo",
            "Desc",
            None, None, "Sim", "0", None, None,
            "https://example.com/resource",
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        # First import
        result1 = import_workbook(db, path)
        assert result1["unchanged"] is False
        version1_id = result1["version_id"]

        # Second import of identical file
        result2 = import_workbook(db, path)
        assert result2["unchanged"] is True
        assert result2["version_id"] == version1_id
        assert result2["seq"] == 1
        assert result2["item_count"] == 0
        assert result2["source_count"] == 0

    def test_import_modified_reupload(self, db, tmp_path):
        """Modifying a file creates a new version."""
        path = tmp_path / "test.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-MOD",
            "Semana 01",
            "1",
            "Lesson A",
            "Autoestudo",
            "Original",
            None, None, "Sim", "0", None, None,
            "https://example.com/v1",
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        result1 = import_workbook(db, path)
        assert result1["seq"] == 1

        # Modify the file
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-MOD",
            "Semana 01",
            "1",
            "Lesson A",
            "Autoestudo",
            "Modified",
            None, None, "Sim", "0", None, None,
            "https://example.com/v2",
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        result2 = import_workbook(db, path)
        assert result2["seq"] == 2
        assert result2["unchanged"] is False
        assert result2["diff"]["changed"] == [
            {
                "week": 1,
                "title": "Lesson A",
                "url_a": "https://example.com/v1",
                "url_b": "https://example.com/v2",
                "description_a": "Original",
                "description_b": "Modified",
            }
        ]

    def test_source_dedup_across_versions(self, db, tmp_path):
        """Same URL across rows and versions creates one source."""
        path = tmp_path / "test.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        for i in range(1, 3):
            sheet.append([
                "TEST-DEDUP",
                f"Semana {i:02d}",
                str(i),
                f"Lesson {i}",
                "Autoestudo",
                f"Desc {i}",
                None, None, "Sim", "0", None, None,
                "https://shared-resource.example.com/material",
                "Não", None, "Não", "Não", "Não", "Não", None, "Não",
            ])
        workbook.save(path)

        first = import_workbook(db, path)

        workbook = load_workbook(path)
        sheet = workbook["Projetos"]
        sheet.append([
            "TEST-DEDUP",
            "Semana 03",
            "3",
            "Lesson 3",
            "Autoestudo",
            "Desc 3",
            None, None, "Sim", "0", None, None,
            "https://shared-resource.example.com/material",
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)
        second = import_workbook(db, path)

        assert first["source_count"] == 1
        assert second["source_count"] == 0
        assert db.execute(
            "SELECT count(*) FROM source WHERE identity->>'canonical_url' = %s",
            ("https://shared-resource.example.com/material",),
        ).fetchone()[0] == 1


class TestDiffVersions:
    """Compare syllabus versions."""

    def test_diff_versions_added(self, db, tmp_path):
        """New items show as added."""
        path = tmp_path / "v1.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-DIFF",
            "Semana 01",
            "1",
            "Item 1",
            "Encontro",
            "First",
            None, None, "Sim", "0", None, None, None,
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        result1 = import_workbook(db, path)
        v1_id = result1["version_id"]

        # Add a new item
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-DIFF",
            "Semana 01",
            "1",
            "Item 1",
            "Encontro",
            "First",
            None, None, "Sim", "0", None, None, None,
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        sheet.append([
            "TEST-DIFF",
            "Semana 02",
            "1",
            "Item 2",
            "Autoestudo",
            "Second",
            None, None, "Sim", "0", None, None,
            "https://example.com/new",
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        result2 = import_workbook(db, path)
        v2_id = result2["version_id"]

        diff = diff_versions(db, v1_id, v2_id)
        assert len(diff["added"]) == 1
        assert diff["added"][0]["title"] == "Item 2"

    def test_diff_versions_removed(self, db, tmp_path):
        """Removed items show as removed."""
        path = tmp_path / "v1.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        for i in range(1, 3):
            sheet.append([
                "TEST-REM",
                f"Semana {i:02d}",
                str(i),
                f"Item {i}",
                "Encontro",
                f"Desc {i}",
                None, None, "Sim", "0", None, None, None,
                "Não", None, "Não", "Não", "Não", "Não", None, "Não",
            ])
        workbook.save(path)

        result1 = import_workbook(db, path)
        v1_id = result1["version_id"]

        # Remove second item
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-REM",
            "Semana 01",
            "1",
            "Item 1",
            "Encontro",
            "Desc 1",
            None, None, "Sim", "0", None, None, None,
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        result2 = import_workbook(db, path)
        v2_id = result2["version_id"]

        diff = diff_versions(db, v1_id, v2_id)
        assert len(diff["removed"]) == 1
        assert diff["removed"][0]["title"] == "Item 2"

    def test_diff_versions_changed(self, db, tmp_path):
        """Changed URLs/descriptions show as changed."""
        path = tmp_path / "v1.xlsx"
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-CHG",
            "Semana 01",
            "1",
            "Study",
            "Autoestudo",
            "Original desc",
            None, None, "Sim", "0", None, None,
            "https://example.com/old",
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        result1 = import_workbook(db, path)
        v1_id = result1["version_id"]

        # Change description and URL
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = "Projetos"
        sheet.append(COLUMNS)
        sheet.append([
            "TEST-CHG",
            "Semana 01",
            "1",
            "Study",
            "Autoestudo",
            "Updated desc",
            None, None, "Sim", "0", None, None,
            "https://example.com/new",
            "Não", None, "Não", "Não", "Não", "Não", None, "Não",
        ])
        workbook.save(path)

        result2 = import_workbook(db, path)
        v2_id = result2["version_id"]

        diff = diff_versions(db, v1_id, v2_id)
        assert len(diff["changed"]) == 1
        assert diff["changed"][0]["title"] == "Study"
        assert diff["changed"][0]["url_a"] == "https://example.com/old"
        assert diff["changed"][0]["url_b"] == "https://example.com/new"
