"""Browser regressions for the syllabus curation interface."""

from contextlib import contextmanager
from pathlib import Path
import socket
import threading
import time
import uuid

import psycopg
from openpyxl import Workbook
from playwright.sync_api import expect, sync_playwright
import uvicorn

from universe.syllabus import (
    LEGACY_COLUMNS,
    get_syllabus_history,
    get_syllabus_version,
    import_workbook,
)
from universe.web.app import create_app


def _editable_workbook(path: Path) -> Path:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "All"
    sheet.append(LEGACY_COLUMNS)

    def append(**values):
        sheet.append([values.get(column) for column in LEGACY_COLUMNS])

    append(
        Week=1,
        Sort=1,
        Type="Class",
        Title="Primeira aula",
        Description="Descrição curta.",
    )
    append(
        Week=1,
        Sort=2,
        Type="Self-study",
        Title="Artigo da primeira aula",
        **{
            "Parent class": "Primeira aula",
            "Description": "Uma fonte de teste.",
            "URL": "https://example.com/primeira",
        },
    )
    append(
        Week=2,
        Sort=3,
        Type="Class",
        Title="Segunda aula",
        Description=(
            "Uma descrição longa o bastante para ocupar várias linhas no editor. "
            "Ela representa o conteúdo real que precisa permanecer inteiramente "
            "visível durante a curadoria da aula. " * 4
        ),
    )
    append(
        Week=2,
        Sort=4,
        Type="Self-study",
        Title="Livro da segunda aula",
        **{
            "Parent class": "Segunda aula",
            "Description": "Leitura do capítulo indicado.",
            "URL": "https://integrada.minhabiblioteca.com.br/reader/books/9788521622888",
            "Resource code": "9788521622888",
        },
    )
    workbook.save(path)
    workbook.close()
    return path


@contextmanager
def _serve(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(app, log_level="error", lifespan="on")
    )
    thread = threading.Thread(
        target=server.run, kwargs={"sockets": [sock]}, daemon=True
    )
    thread.start()
    deadline = time.monotonic() + 5
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.01)
    if not server.started:
        raise RuntimeError("test web server did not start")
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        sock.close()


def test_targeted_lesson_editor_stays_scoped_and_can_hide_that_lesson(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser editor {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(conn, _editable_workbook(tmp_path / "editor.xlsx"), name)

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        page.get_by_role("button", name="Editar somente esta aula").nth(1).click()

        expect(page.locator(".syl-lesson--editor")).to_have_count(1)
        expect(page.locator("[data-lesson-field='title']")).to_have_value("Segunda aula")
        expect(
            page.locator(".syl-lesson:not(.syl-lesson--editor) .syl-lesson-edit")
        ).to_have_count(1)

        page.get_by_role("button", name="Ocultar aula").click()
        expect(page.locator(".syl-lesson--editor")).to_have_class(
            "syl-lesson syl-lesson--editor is-hidden-lesson"
        )
        expect(page.get_by_role("button", name="Desocultar aula")).to_be_visible()
        page.get_by_role("button", name="Salvar nova versão").click()
        expect(page.locator("[data-status]")).to_contain_text("Versão 2 salva")
        browser.close()

    with psycopg.connect(test_database_url) as conn:
        latest = get_syllabus_version(conn, imported["syllabus_id"])
    assert [lesson["hidden"] for lesson in latest["lessons"]] == [False, True]


def test_lesson_description_expands_to_show_its_content_when_editing(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser autosize {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn, _editable_workbook(tmp_path / "autosize.xlsx"), name
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")
        page.get_by_role("button", name="Editar somente esta aula").nth(1).click()

        textarea = page.locator("[data-lesson-field='description']")
        dimensions = textarea.evaluate(
            "element => ({"
            "clientHeight: element.clientHeight, "
            "scrollHeight: element.scrollHeight, "
            "inlineHeight: element.style.height"
            "})"
        )
        assert dimensions["inlineHeight"]
        assert dimensions["clientHeight"] >= dimensions["scrollHeight"]
        browser.close()


def test_book_code_can_be_copied_exactly_from_the_source_card(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser copy {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn, _editable_workbook(tmp_path / "copy.xlsx"), name
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        page.get_by_role(
            "button", name="Copiar código do livro 9788521622888"
        ).click()

        assert page.evaluate("navigator.clipboard.readText()") == "9788521622888"
        expect(page.locator("[data-status]")).to_contain_text(
            "Código do livro copiado"
        )
        browser.close()


def test_a_fully_validated_lesson_can_be_unvalidated_from_its_compact_row(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser unvalidate {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn, _editable_workbook(tmp_path / "unvalidate.xlsx"), name
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        first_lesson = page.locator(".syl-lesson").first
        first_lesson.get_by_role("button", name="Validada").click()

        expect(first_lesson).to_have_class(
            "syl-lesson is-validated is-collapsed"
        )
        unvalidate = first_lesson.get_by_role("button", name="Desvalidar")
        expect(unvalidate).to_be_visible()
        unvalidate.click()

        expect(first_lesson.get_by_role("button", name="Validada")).to_be_visible()
        browser.close()


def test_sequential_lesson_edits_are_saved_as_one_syllabus_edition(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser serial edits {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn, _editable_workbook(tmp_path / "serial.xlsx"), name
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        page.get_by_role("button", name="Editar somente esta aula").first.click()
        page.locator("[data-lesson-field='title']").fill("Primeira aula revisada")
        page.locator(
            ".syl-lesson:not(.syl-lesson--editor) .syl-lesson-edit"
        ).click()
        expect(page.locator(".syl-lesson--editor")).to_have_count(1)
        page.locator("[data-lesson-field='title']").fill("Segunda aula revisada")

        page.get_by_role("button", name="Salvar nova versão").click()
        expect(page.locator("[data-status]")).to_contain_text("Versão 2 salva")
        browser.close()

    with psycopg.connect(test_database_url) as conn:
        history = get_syllabus_history(conn, imported["syllabus_id"])
        latest = get_syllabus_version(conn, imported["syllabus_id"])
    assert [version["seq"] for version in history["versions"]] == [2, 1]
    assert [lesson["title"] for lesson in latest["lessons"]] == [
        "Primeira aula revisada",
        "Segunda aula revisada",
    ]
