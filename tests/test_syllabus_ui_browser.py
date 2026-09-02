"""Browser regressions for the syllabus curation interface."""

from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
import socket
import threading
import time
import uuid
from urllib.parse import quote, urlparse

import psycopg
from playwright.sync_api import expect, sync_playwright
import uvicorn

from adalove_workbook import activity, stable_uuid, write_adalove_workbook
from universe.syllabus import get_syllabus_history, get_syllabus_version, import_workbook
from universe.web.app import create_app


LOCAL_KC_STAGES = (
    "blocks",
    "passage-cuts",
    "passage-triage",
    "task-generation",
    "task-granularity",
    "task-revision",
    "task-triage",
    "task-substance",
    "kc-statement",
    "task-modality",
    "task-knowledge",
)


def _editable_workbook(path: Path) -> Path:
    first_lesson = activity(
        week=1,
        order=1,
        kind="Class",
        title="Primeira aula",
        description="Descrição curta.",
    )
    first_source = activity(
        week=1,
        order=2,
        kind="Self-study",
        title="Artigo da primeira aula",
        parent_uuid=first_lesson["Activity UUID"],
        parent_title=first_lesson["Title"],
        description="Uma fonte de teste.",
        url="https://example.com/primeira",
    )
    second_lesson = activity(
        week=2,
        order=3,
        kind="Class",
        title="Segunda aula",
        description=(
            "Uma descrição longa o bastante para ocupar várias linhas no editor. "
            "Ela representa o conteúdo real que precisa permanecer inteiramente "
            "visível durante a curadoria da aula. " * 4
        ),
    )
    second_source = activity(
        week=2,
        order=4,
        kind="Self-study",
        title="Livro da segunda aula",
        parent_uuid=second_lesson["Activity UUID"],
        parent_title=second_lesson["Title"],
        description="Leitura do capítulo indicado.",
        url="https://integrada.minhabiblioteca.com.br/reader/books/9788521622888",
        resource_code="9788521622888",
    )
    return write_adalove_workbook(
        path, [first_lesson, first_source, second_lesson, second_source]
    )


def _subject_filter_workbook(path: Path) -> Path:
    activities = [
        activity(
            week=1,
            order=1,
            kind="Class",
            title="Aula de comunicação",
            subject="COM",
        ),
        activity(
            week=1,
            order=2,
            kind="Orientation",
            title="Sprint Planning",
            subject=None,
        ),
        activity(
            week=1,
            order=3,
            kind="Deliverable",
            title="Apresentação do artefato",
            subject=None,
            **{"Grade weight": 3},
        ),
        activity(
            week=1,
            order=4,
            kind="Evaluation",
            title="Avaliação em pares",
            subject=None,
            **{"Grade weight": 2},
        ),
    ]
    return write_adalove_workbook(path, activities)


def _identity_conflict_workbook(path: Path, *, incoming: bool) -> Path:
    title = (
        "Estratégia comercial para novos mercados"
        if incoming
        else "Fundamentos de bancos de dados relacionais"
    )
    return write_adalove_workbook(
        path,
        [
            activity(
                week=9 if incoming else 2,
                order=1,
                kind="Class",
                title=title,
                activity_uuid=stable_uuid("activity", title),
                description=(
                    "Negociação, canais de venda e expansão internacional."
                    if incoming
                    else "Modelagem relacional, normalização e consultas SQL."
                ),
                subject="Negócios" if incoming else "Computação",
            )
        ],
        project="GRAD CC07",
    )


def _subject_workbook(path: Path) -> Path:
    lesson = activity(
        week=2,
        order=1,
        kind="Class",
        title="Programação e Desenvolvimento de Banco de Dados",
        description="Criação e manipulação de bancos relacionais.",
        subject="Computação",
        subjects=["Banco de dados relacional", "SQL Básico"],
    )
    source = activity(
        week=2,
        order=2,
        kind="Self-study",
        title="Tutorial MySQL",
        parent_uuid=lesson["Activity UUID"],
        parent_title=lesson["Title"],
        subject="Computação",
        url="https://example.com/mysql",
    )
    return write_adalove_workbook(
        path,
        [
            lesson,
            source,
            activity(
                week=2,
                order=3,
                kind="Orientation",
                title="Sprint Planning",
                subject=None,
            ),
            activity(
                week=2,
                order=4,
                kind="Deliverable",
                title="Entrega do artefato",
                subject=None,
            ),
            activity(
                week=2,
                order=5,
                kind="Evaluation",
                title="Avaliação geral",
                subject=None,
            ),
        ],
        project="GRAD CC07",
    )


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


def _route_detail(page, syllabus_id, mutate):
    """Keep the real projection, replacing only the not-yet-landed KC fields."""

    cached = {"payload": None}

    def handler(route):
        if urlparse(route.request.url).path != f"/api/syllabi/{syllabus_id}":
            route.continue_()
            return
        response = route.fetch()
        payload = response.json()
        status = response.status
        if "lessons" not in payload and cached["payload"] is not None:
            payload = deepcopy(cached["payload"])
            status = 200
        mutate(payload)
        cached["payload"] = deepcopy(payload)
        route.fulfill(status=status, json=payload)

    page.route(f"**/api/syllabi/{syllabus_id}*", handler)


def _snapshot(
    source_id,
    source_title,
    artifact_id,
    *,
    completed,
    statement=None,
    task=None,
    answer=None,
):
    stages = {
        name: {"status": "done" if index < completed else "pending"}
        for index, name in enumerate(LOCAL_KC_STAGES)
    }
    components = []
    if statement:
        components.append(
            {
                "id": f"task-{source_id}",
                "kind": "singleton",
                "canonical": {"verdict": "stated", "statement": statement},
                "members": [
                    {
                        "task_id": f"task-{source_id}",
                        "source_id": source_id,
                        "task": task,
                        "answer": answer,
                        "statement": statement,
                    }
                ],
            }
        )
    return {
        "source": {
            "id": source_id,
            "title": source_title,
            "artifact_id": artifact_id,
        },
        "stages": stages,
        "components": components,
        "relationships": [],
    }


def test_upload_dialog_derives_companion_identity_and_requires_a_new_name_on_conflict(
    test_database_url, applied_migrations, tmp_path
):
    workbook_path = _editable_workbook(tmp_path / "syllabus-identity.xlsx")
    marker = uuid.uuid4().hex[:10]
    name = f"Upload identity {marker}"
    occupied = f"graph-inteli-upload-identity-{marker}"
    namespace = {
        "schema_version": "companion_graph_namespace.v1",
        "institutions": [{"slug": "inteli", "name": "Inteli"}],
        "graph_ids": [occupied],
    }
    app = create_app(
        lambda: psycopg.connect(test_database_url),
        companion_namespace_provider=lambda: namespace,
    )

    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi")
        page.locator("[data-new-syllabus]").first.click()

        dialog = page.locator("[data-upload-dialog]")
        expect(dialog).to_be_visible()
        expect(dialog.locator("[data-new-upload-mode]")).to_be_visible()
        expect(dialog.locator("[data-version-upload-mode]")).to_be_hidden()
        expect(dialog.locator('[name="display_name"]')).to_have_count(0)
        expect(dialog.locator('[name="lesson_subject_ids"]')).to_have_count(0)
        expect(dialog.locator('[name="graph_id"]')).to_have_count(0)

        dialog.locator('[name="institution_id"]').select_option("inteli")
        dialog.locator('[name="name"]').fill(name)

        preview = dialog.locator("[data-graph-preview]")
        expect(preview).to_be_visible()
        expect(preview.locator("[data-graph-display-name]")).to_have_text(name)
        expect(preview.locator("[data-proposed-graph-id]")).to_have_text(occupied)

        conflict = dialog.locator("[data-graph-conflict]")
        expect(conflict).to_be_visible()
        expect(conflict).to_have_text(
            "Este ID já está em uso no Companion. Escolha outro nome para o syllabus."
        )
        expect(dialog.get_by_role("button", name="Adicionar syllabus")).to_be_disabled()

        dialog.locator('[name="name"]').fill("C")
        assert preview.evaluate("element => element.hidden") is False
        expect(preview.locator("[data-proposed-graph-id]")).to_have_text("Calculando…")
        expect(preview.locator("[data-proposed-graph-id]")).to_have_text("Continue digitando…")
        expect(preview.locator("[data-graph-id-status]")).to_have_text(
            "Continue digitando para gerar um ID válido."
        )
        assert preview.evaluate("element => element.hidden") is False

        changed_name = f"{name} changed"
        dialog.locator('[name="name"]').fill(changed_name)
        assert preview.evaluate("element => element.hidden") is False
        expect(preview.locator("[data-graph-display-name]")).to_have_text(changed_name)
        expect(preview.locator("[data-proposed-graph-id]")).to_have_text("Calculando…")
        expect(preview.locator("[data-graph-id-status]")).to_have_text(
            "Calculando e verificando o ID…"
        )
        assert conflict.evaluate("element => element.hidden") is True
        expect(preview.locator("[data-proposed-graph-id]")).to_have_text(f"{occupied}-changed")
        expect(preview.locator("[data-graph-id-status]")).to_have_text(
            "ID verificado e disponível."
        )
        expect(dialog.get_by_role("button", name="Adicionar syllabus")).to_be_enabled()

        dialog.locator('[name="file"]').set_input_files(workbook_path)
        dialog.get_by_role("button", name="Adicionar syllabus").click()

        page.wait_for_url("**/syllabi?id=*")
        expect(page.get_by_role("button", name="Enviar nova versão")).to_be_visible()
        browser.close()


def test_upload_dialog_blocks_an_existing_syllabus_and_can_open_it(
    test_database_url, applied_migrations, tmp_path
):
    workbook_path = _editable_workbook(tmp_path / "existing-syllabus.xlsx")
    marker = uuid.uuid4().hex[:10]
    name = f"Existing syllabus {marker}"
    with psycopg.connect(test_database_url) as conn:
        conn.execute(
            "INSERT INTO institution (id, name) VALUES ('inteli', 'Inteli')"
            " ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name"
        )
        imported = import_workbook(conn, workbook_path, name, institution_id="inteli")

    namespace = {
        "schema_version": "companion_graph_namespace.v1",
        "institutions": [{"slug": "inteli", "name": "Inteli"}],
        "graph_ids": [imported["syllabus_id"]],
    }
    app = create_app(
        lambda: psycopg.connect(test_database_url),
        companion_namespace_provider=lambda: namespace,
    )

    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi")
        page.locator("[data-new-syllabus]").first.click()
        dialog = page.locator("[data-upload-dialog]")
        dialog.locator('[name="institution_id"]').select_option("inteli")
        dialog.locator('[name="name"]').fill(name)

        conflict = dialog.locator("[data-syllabus-conflict]")
        expect(conflict).to_be_visible()
        expect(conflict.locator("p")).to_have_text(
            "Este nome já existe. Você está adicionando uma versão a esse syllabus."
        )
        expect(dialog.get_by_role("button", name="Adicionar syllabus")).to_be_disabled()
        actions = conflict.locator(".syl-graph-conflict__actions")
        assert actions.evaluate("element => getComputedStyle(element).display") == "grid"
        assert actions.locator(".button").count() == 1
        open_existing = dialog.get_by_role("link", name="Abrir syllabus e adicionar versão")
        assert "button--primary" not in (open_existing.get_attribute("class") or "")
        assert "button--quiet" not in (open_existing.get_attribute("class") or "")
        button_geometry = open_existing.evaluate(
            """element => {
                const style = getComputedStyle(element);
                const box = element.getBoundingClientRect();
                const range = document.createRange();
                range.selectNodeContents(element);
                const text = range.getBoundingClientRect();
                return {
                    display: style.display,
                    alignItems: style.alignItems,
                    verticalOffset: Math.abs(
                        (box.top + box.height / 2) - (text.top + text.height / 2)
                    ),
                };
            }"""
        )
        assert button_geometry["display"] == "flex"
        assert button_geometry["alignItems"] == "center"
        assert button_geometry["verticalOffset"] < 1

        dialog.locator('[name="name"]').fill(f"{name} changed")
        expect(conflict).to_be_hidden()
        dialog.locator('[name="name"]').fill(name)
        expect(conflict).to_be_visible()
        open_existing.click()

        page.wait_for_url(f"**/syllabi?id={imported['syllabus_id']}")
        new_version = page.get_by_role("button", name="Enviar nova versão")
        expect(new_version).to_be_visible()
        new_version.click()

        expect(dialog.locator("[data-new-upload-mode]")).to_be_hidden()
        version_mode = dialog.locator("[data-version-upload-mode]")
        expect(version_mode).to_be_visible()
        expect(version_mode.locator("[data-version-syllabus-name]")).to_have_text(name)
        expect(version_mode.locator("[data-version-institution]")).to_have_text("Inteli")
        expect(version_mode.locator("[data-version-graph-id]")).to_have_text(
            f"graph-inteli-{imported['syllabus_id']}"
        )
        expect(dialog.locator("[data-name-field]")).to_be_hidden()
        expect(dialog.locator("[data-syllabus-fields]")).to_be_hidden()
        expect(dialog.get_by_role("button", name="Comparar planilha")).to_be_enabled()
        browser.close()


def test_adalove_reconciliation_reviews_new_identity_then_carries_it_automatically(
    test_database_url, applied_migrations, tmp_path, adalove_workbook
):
    name = f"Browser stable identity {uuid.uuid4().hex[:8]}"
    original = adalove_workbook(
        tmp_path / "identity-original.xlsx", include_course_events=True
    )
    # The subject change arrives on a recreated activity (new Adalove UUID),
    # so identity goes to review; the later small edit keeps that new UUID.
    changed_subject = adalove_workbook(
        tmp_path / "identity-subject.xlsx",
        lesson_axis="Negócios",
        activity_uuid="browser-recreated-activity",
        include_course_events=True,
    )
    small_edit = adalove_workbook(
        tmp_path / "identity-small-edit.xlsx",
        lesson_axis="Negócios",
        activity_uuid="browser-recreated-activity",
        lesson_description=(
            "Criação e manipulação de bancos relacionais na nuvem."
        ),
        include_course_events=True,
    )
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(conn, original, name, require_syllabus_metadata=False)
        first = get_syllabus_version(conn, imported["syllabus_id"])
        first_id = first["lessons"][0]["id"]

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        page.get_by_role("button", name="Enviar nova versão").click()
        dialog = page.locator("[data-upload-dialog]")
        dialog.locator('[name="file"]').set_input_files(changed_subject)
        dialog.get_by_role("button", name="Comparar planilha").click()

        expect(
            page.get_by_role(
                "heading",
                name="Como esta entrada se relaciona com o syllabus atual?",
            )
        ).to_be_visible()
        expect(page.locator(".recon-identity-review")).to_contain_text(
            "A matéria mudou"
        )
        new_identity = page.get_by_role(
            "button", name="É uma aula nova + transicionar", exact=True
        )
        new_identity.click()
        expect(new_identity).to_be_focused()
        page.get_by_role("button", name="Criar versão 2", exact=False).click()
        page.wait_for_function("!location.search.includes('reconciliation=')")

        with psycopg.connect(test_database_url) as conn:
            second = get_syllabus_version(conn, imported["syllabus_id"])
            second_id = second["lessons"][0]["id"]
        assert second_id != first_id

        page.get_by_role("button", name="Enviar nova versão").click()
        dialog.locator('[name="file"]').set_input_files(small_edit)
        dialog.get_by_role("button", name="Comparar planilha").click()

        expect(page.locator(".recon-identity--automatic")).to_contain_text(
            "ID mantido automaticamente"
        )
        page.locator('[data-recon-choice="transition"]').click()
        page.get_by_role("button", name="Criar versão 3", exact=False).click()
        page.wait_for_function("!location.search.includes('reconciliation=')")

        with psycopg.connect(test_database_url) as conn:
            third = get_syllabus_version(conn, imported["syllabus_id"])
        assert third["lessons"][0]["id"] == second_id
        browser.close()


def test_reviewed_lesson_uses_one_coherent_action_and_labels_a_noop(
    test_database_url, applied_migrations, tmp_path, adalove_workbook
):
    original = adalove_workbook(tmp_path / "coherent-original.xlsx")
    rewritten = adalove_workbook(
        tmp_path / "coherent-rewritten.xlsx",
        lesson_title="Fundamentos de produto e estratégia comercial",
        lesson_description=(
            "Proposta de valor, precificação, negociação e canais de distribuição."
        ),
    )
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(conn, original, "Ações coerentes de reconciliação", require_syllabus_metadata=False)
        before = get_syllabus_version(conn, imported["syllabus_id"])

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")
        page.get_by_role("button", name="Enviar nova versão").click()
        dialog = page.locator("[data-upload-dialog]")
        dialog.locator('[name="file"]').set_input_files(rewritten)
        dialog.get_by_role("button", name="Comparar planilha").click()

        actions = page.locator("[data-recon-lesson-actions]")
        related = actions.get_by_role(
            "button", name="É a aula selecionada + transicionar", exact=True
        )
        keep = actions.get_by_role("button", name="Manter", exact=True)
        new = actions.get_by_role(
            "button", name="É uma aula nova + transicionar", exact=True
        )
        expect(related).to_be_visible()
        expect(keep).to_be_visible()
        expect(new).to_be_visible()
        expect(page.get_by_text("Candidata selecionada", exact=True)).to_have_count(0)
        expect(page.locator("[data-recon-identity-candidate]")).to_have_count(0)

        manual_toggle = page.get_by_role(
            "button", name="Montar uma versão manual", exact=False
        )
        manual_toggle.click()
        expect(manual_toggle).to_be_focused()
        expect(actions).to_be_hidden()
        manual = page.locator("[data-recon-manual-form]")
        manual.get_by_label("Título", exact=True).fill("Versão montada")
        use_manual = manual.get_by_role("button", name="Usar versão montada")
        expect(use_manual).to_be_disabled()
        manual_related = manual.get_by_role(
            "button", name="É a aula relacionada", exact=True
        )
        expect(manual_related).to_be_visible()
        expect(manual.get_by_role("button", name="É uma aula nova", exact=True)).to_be_visible()
        manual_related.click()
        expect(use_manual).to_be_enabled()
        use_manual.click()
        expect(actions).to_be_hidden()
        manual_toggle.click()
        expect(manual_toggle).to_be_focused()
        expect(actions).to_be_visible()
        expect(related).to_have_attribute("aria-pressed", "false")
        expect(keep).to_have_attribute("aria-pressed", "false")
        expect(new).to_have_attribute("aria-pressed", "false")
        expect(
            page.get_by_role("button", name="Concluir revisão", exact=True)
        ).to_be_enabled()

        new.click()
        expect(new).to_have_attribute("aria-pressed", "true")
        keep.click()
        expect(keep).to_have_attribute("aria-pressed", "true")
        expect(new).to_have_attribute("aria-pressed", "false")
        finish = page.get_by_role(
            "button", name="Concluir sem criar versão", exact=False
        )
        expect(finish).to_be_enabled()
        expect(page.get_by_role("button", name="Criar versão 2", exact=False)).to_have_count(0)
        finish.click()
        page.wait_for_function("!location.search.includes('reconciliation=')")
        browser.close()

    with psycopg.connect(test_database_url) as conn:
        after = get_syllabus_version(conn, imported["syllabus_id"])
    assert after["version"]["id"] == before["version"]["id"]


def test_keeping_removed_lesson_reserves_its_identity_in_both_selection_orders(
    test_database_url, applied_migrations, tmp_path
):
    original = _identity_conflict_workbook(
        tmp_path / "identity-owner-original.xlsx", incoming=False
    )
    incoming = _identity_conflict_workbook(
        tmp_path / "identity-owner-incoming.xlsx", incoming=True
    )
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(conn, original, "Reserva de identidade", require_syllabus_metadata=False)

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")
        page.get_by_role("button", name="Enviar nova versão").click()
        dialog = page.locator("[data-upload-dialog]")
        dialog.locator('[name="file"]').set_input_files(incoming)
        dialog.get_by_role("button", name="Comparar planilha").click()
        page.wait_for_function("location.search.includes('reconciliation=')")
        reconciliation_url = page.url

        page.locator('[data-recon-choice="keep"]').click()
        page.locator("[data-recon-lesson]").filter(
            has_text="Estratégia comercial para novos mercados"
        ).click()
        related = page.get_by_role(
            "button", name="É a aula selecionada + transicionar", exact=True
        )
        expect(related).to_be_disabled()
        expect(page.get_by_role("button", name="Concluir revisão")).to_be_disabled()

        page.goto(reconciliation_url)
        page.locator("[data-recon-lesson]").filter(
            has_text="Estratégia comercial para novos mercados"
        ).click()
        related = page.get_by_role(
            "button", name="É a aula selecionada + transicionar", exact=True
        )
        related.click()
        expect(related).to_have_attribute("aria-pressed", "true")

        page.locator("[data-recon-lesson]").filter(
            has_text="Fundamentos de bancos de dados relacionais"
        ).click()
        page.locator('[data-recon-choice="keep"]').click()
        page.locator("[data-recon-lesson]").filter(
            has_text="Estratégia comercial para novos mercados"
        ).click()
        related = page.get_by_role(
            "button", name="É a aula selecionada + transicionar", exact=True
        )
        expect(related).to_be_disabled()
        expect(related).to_have_attribute("aria-pressed", "false")
        expect(page.get_by_role("button", name="Concluir revisão")).to_be_disabled()
        browser.close()


def test_targeted_lesson_editor_stays_scoped_and_can_hide_that_lesson(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser editor {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "editor.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

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
        save = page.get_by_role("button", name="Salvar nova versão")
        expect(save).to_be_enabled()
        save.click()

        version_dialog = page.get_by_role("dialog", name="Registrar nova versão")
        expect(version_dialog).to_be_visible()
        reason = version_dialog.get_by_label("Razão da nova versão")
        expect(reason).to_have_attribute("maxlength", "500")
        reason.fill("A aula não faz parte do percurso curricular desta oferta.")
        expect(version_dialog.get_by_text("57/500", exact=True)).to_be_visible()
        version_dialog.get_by_role("button", name="Criar versão").click()
        expect(page.locator("[data-status]")).to_contain_text("Versão 2 salva")
        page.get_by_role("button", name="Versão 2").click()
        history_dialog = page.get_by_role("dialog", name="Versões do syllabus")
        expect(history_dialog).to_contain_text(
            "A aula não faz parte do percurso curricular desta oferta."
        )
        expect(history_dialog.get_by_text("Versão aberta", exact=True)).to_be_visible()
        history_dialog.get_by_role("button", name="Abrir versão 1").click()
        expect(page.get_by_role("button", name="Versão 1")).to_be_visible()
        expect(page.get_by_role("button", name="Editar syllabus")).to_be_disabled()
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
            conn,
            _editable_workbook(tmp_path / "autosize.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")
        page.get_by_role("button", name="Editar somente esta aula").nth(1).click()

        textarea = page.locator("[data-lesson-field='description']")
        expect(textarea).to_have_attribute("maxlength", "4000")
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
            conn,
            _editable_workbook(tmp_path / "copy.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            permissions=["clipboard-read", "clipboard-write"]
        )
        page = context.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        page.locator(".syl-lesson").nth(1).get_by_role(
            "button", name="Expandir aula Segunda aula"
        ).click()
        page.get_by_role(
            "button", name="Copiar código do livro 9788521622888"
        ).click()

        assert page.evaluate("navigator.clipboard.readText()") == "9788521622888"
        expect(page.locator("[data-status]")).to_contain_text(
            "Código do livro copiado"
        )
        browser.close()


def test_syllabus_costs_live_in_the_top_bar(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser heading {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "heading.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))

    def mutate_detail(payload):
        payload["usage"] = {
            "openrouter": {"cost_usd": 0.15, "calls": 2, "total_tokens": 150},
            "firecrawl": {
                "extractions": 1,
                "attempts": 2,
                "succeeded": 1,
                "failed": 0,
            },
        }

    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        _route_detail(page, imported["syllabus_id"], mutate_detail)
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        costs = page.locator(".admin-shell").get_by_label(
            "Consumo das fontes desta versão"
        )
        expect(costs).to_contain_text("OpenRouter")
        expect(costs).to_contain_text("US$ 0,15")
        expect(costs).to_contain_text("Firecrawl")
        expect(costs).to_contain_text("1 extração")
        expect(page.locator(".syl-view .syl-usage-strip")).to_have_count(0)

        browser.close()


def test_subject_filter_includes_curricular_kinds_and_omits_orientations(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser orientation {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _subject_filter_workbook(tmp_path / "orientation.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        subjects = page.locator("[data-filter-subject]")
        expect(subjects.get_by_role("option", name="COM")).to_have_count(1)
        expect(subjects.get_by_role("option", name="Artefatos")).to_have_count(1)
        expect(subjects.get_by_role("option", name="Avaliações")).to_have_count(1)
        expect(subjects.get_by_role("option", name="Orientação")).to_have_count(0)
        expect(page.get_by_text("Sprint Planning", exact=True)).to_have_count(0)
        subjects.select_option(label="Artefatos")

        expect(page.locator(".syl-lesson")).to_have_count(1)
        expect(page.locator(".syl-lesson h2")).to_have_text("Apresentação do artefato")
        browser.close()


def test_adalove_lesson_shows_subjects_and_its_parented_source(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser Adalove {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _subject_workbook(tmp_path / "adalove.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        lesson = page.locator(".syl-lesson").first
        lesson.get_by_role(
            "button", name="Expandir aula Programação e Desenvolvimento de Banco de Dados"
        ).click()

        expect(lesson.get_by_text("Criação e manipulação de bancos relacionais.")).to_be_visible()
        subjects = lesson.get_by_label("Assuntos")
        expect(subjects.get_by_text("Banco de dados relacional", exact=True)).to_be_visible()
        expect(subjects.get_by_text("SQL Básico", exact=True)).to_be_visible()
        expect(lesson.get_by_role("heading", name="Tutorial MySQL")).to_be_visible()
        expect(lesson.get_by_text("Pai inferido pela ordem da atividade")).to_be_visible()

        subject_filter = page.locator("[data-filter-subject]")
        for label in ("COM", "Artefatos", "Avaliações"):
            expect(subject_filter.get_by_role("option", name=label)).to_have_count(1)
        expect(subject_filter.get_by_role("option", name="Orientação")).to_have_count(0)
        expect(page.locator('.syl-lesson[data-subject="COM"]')).to_have_css(
            "border-left-color", "rgb(39, 93, 125)"
        )
        browser.close()


def test_a_fully_validated_lesson_can_be_unvalidated_from_its_compact_row(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser unvalidate {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "unvalidate.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        first_lesson = page.locator(".syl-lesson").first
        first_lesson.get_by_role(
            "button", name="Expandir aula Primeira aula"
        ).click()
        first_lesson.get_by_role("button", name="Validada").click()

        expect(first_lesson).to_have_class(
            "syl-lesson is-validated is-collapsed"
        )
        unvalidate = first_lesson.get_by_role("button", name="Desvalidar")
        expect(unvalidate).to_be_visible()
        unvalidate.click()

        expect(first_lesson).to_have_class("syl-lesson is-collapsed")
        first_lesson.get_by_role(
            "button", name="Expandir aula Primeira aula"
        ).click()
        expect(first_lesson.get_by_role("button", name="Validada")).to_be_visible()
        browser.close()


def test_syllabus_opens_with_every_lesson_collapsed(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser collapsed default {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "collapsed-default.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        lessons = page.locator(".syl-lesson")
        expect(lessons).to_have_count(2)
        expect(lessons.nth(0)).to_have_class("syl-lesson is-collapsed")
        expect(lessons.nth(1)).to_have_class("syl-lesson is-collapsed")
        expect(
            lessons.nth(0).get_by_role("button", name="Expandir aula Primeira aula")
        ).to_have_attribute("aria-expanded", "false")

        lessons.nth(0).get_by_role(
            "button", name="Expandir aula Primeira aula"
        ).click()
        expect(lessons.nth(0)).to_have_class("syl-lesson")
        expect(lessons.nth(1)).to_have_class("syl-lesson is-collapsed")
        browser.close()


def test_validating_the_last_source_refreshes_the_kc_offer(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser KC gate {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "kc-gate.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))

    def mutate_detail(payload):
        lesson = payload["lessons"][0]
        source = lesson["sources"][0]
        validated = bool(source.get("review", {}).get("validated"))
        source["has_markdown"] = True
        source["markdown"] = {"available": True}
        lesson["knowledge"] = {
            "lesson_id": lesson["id"],
            "active_reference_count": 1,
            "publication_count": 1,
            "eligibility": {
                "eligible": validated,
                "code": "ready" if validated else "references_not_validated",
            },
            "latest_build": None,
        }

    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _route_detail(page, imported["syllabus_id"], mutate_detail)
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        first_lesson = page.locator(".syl-lesson").first
        first_lesson.get_by_role(
            "button", name="Expandir aula Primeira aula"
        ).click()
        expect(
            first_lesson.get_by_role("button", name="Iniciar criação")
        ).to_have_count(0)

        first_lesson.get_by_role("button", name="Validada").click()

        expect(
            first_lesson.get_by_role("button", name="Iniciar criação")
        ).to_be_visible()
        expect(first_lesson).to_contain_text(
            "1 Source Publication pronta · 1 autoestudo validado"
        )
        browser.close()


def test_sequential_lesson_edits_are_saved_as_one_syllabus_edition(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser serial edits {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "serial.xlsx"),
            name,
            require_syllabus_metadata=False,
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
        version_dialog = page.get_by_role("dialog", name="Registrar nova versão")
        version_dialog.get_by_label("Razão da nova versão").fill(
            "Revisa os títulos de duas aulas."
        )
        version_dialog.get_by_role("button", name="Criar versão").click()
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


def test_kc_entry_points_confirm_before_post_and_poll_the_active_build(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser KC start {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "kc-start.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    current = {"build": None, "source_id": None, "reference_id": None}
    posts = []
    build_reads = []

    def mutate_detail(payload):
        lesson = payload["lessons"][0]
        source = lesson["sources"][0]
        current["source_id"] = source["source_id"]
        current["reference_id"] = source["reference_id"]
        source["review"] = {"validated": True, "complexity": "simple"}
        source["has_markdown"] = True
        source["markdown"] = {"available": True}
        lesson["knowledge"] = {
            "lesson_id": lesson["id"],
            "publication_count": 1,
            "eligibility": {"eligible": True, "code": "ready"},
            "latest_build": current["build"],
        }
        # Keep a non-KC source in its ordinary pre-extraction state so this
        # regression also proves those controls remain present.
        payload["lessons"][1]["sources"][0]["source_id"] = (
            payload["lessons"][1]["sources"][0].get("source_id")
            or "source-browser-book"
        )
        payload["knowledge_manifest_id"] = None

    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _route_detail(page, imported["syllabus_id"], mutate_detail)

        def offer_handler(route):
            lesson_id = urlparse(route.request.url).path.split("/")[-2]
            route.fulfill(
                status=200,
                json={
                    "lesson_id": lesson_id,
                    "publication_count": 1,
                    "eligibility": {"eligible": True, "code": "ready"},
                    "latest_build": current["build"],
                },
            )

        def start_handler(route):
            posts.append(route.request.post_data_json)
            source_id = current["source_id"]
            reference_id = current["reference_id"]
            current["build"] = {
                "id": "build-browser-start",
                "status": "running",
                "references": [
                    {
                        "reference_id": reference_id,
                        "work_id": "work-browser-start",
                    }
                ],
                "work": [
                    {
                        "id": "work-browser-start",
                        "source_id": source_id,
                        "artifact_id": "artifact-browser-start",
                        "reference_ids": [reference_id],
                        "status": "running",
                        "snapshot": _snapshot(
                            source_id,
                            "Artigo da primeira aula",
                            "artifact-browser-start",
                            completed=0,
                        ),
                    }
                ],
            }
            route.fulfill(status=202, json=current["build"])

        def build_handler(route):
            build_reads.append(route.request.url)
            source_id = current["source_id"]
            reference_id = current["reference_id"]
            current["build"] = {
                "id": "build-browser-start",
                "status": "running",
                "references": [
                    {
                        "reference_id": reference_id,
                        "work_id": "work-browser-start",
                    }
                ],
                "work": [
                    {
                        "id": "work-browser-start",
                        "source_id": source_id,
                        "artifact_id": "artifact-browser-start",
                        "reference_ids": [reference_id],
                        "status": "running",
                        "snapshot": _snapshot(
                            source_id,
                            "Artigo da primeira aula",
                            "artifact-browser-start",
                            completed=9,
                            statement="Explica por que feedback reduz incerteza.",
                            task="Por que ciclos curtos ajudam a equipe?",
                            answer="Eles antecipam evidência sobre a solução.",
                        ),
                    }
                ],
            }
            route.fulfill(status=200, json=current["build"])

        page.route("**/api/knowledge-builds/build-browser-start", build_handler)
        page.route("**/knowledge-builds", start_handler)
        page.route("**/knowledge", offer_handler)
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        first_lesson = page.locator(".syl-lesson").first
        expect(first_lesson.get_by_role("button", name="Visualizar")).to_be_visible()
        expect(
            first_lesson.get_by_role(
                "button", name="Ver KCs de Artigo da primeira aula"
            )
        ).to_have_count(0)
        expect(first_lesson.get_by_role("button", name="Desvalidar")).to_be_visible()
        expect(page.get_by_role("button", name="Universo")).to_be_disabled()
        page.locator(".syl-lesson").nth(1).get_by_role(
            "button", name="Expandir aula Segunda aula"
        ).click()
        expect(
            page.locator(".syl-lesson").nth(1).get_by_role(
                "button", name="Upload de PDF ou Imagem"
            )
        ).to_be_visible()

        expect(first_lesson).to_contain_text(
            "1 Source Publication pronta · 1 autoestudo validado"
        )
        first_lesson.get_by_role("button", name="Iniciar criação").click()
        dialog = page.locator("[data-knowledge-dialog]")
        expect(dialog).to_be_visible()
        expect(dialog).to_contain_text("1 Source Publication")
        expect(dialog.get_by_role("button", name="Confirmar e iniciar KCs")).to_be_visible()
        assert posts == []

        dialog.get_by_role("button", name="Confirmar e iniciar KCs").click()
        expect(dialog).to_contain_text("0/11 etapas locais")
        assert len(posts) == 1
        assert set(posts[0]) == {"request_key"}
        assert posts[0]["request_key"].startswith("syllabi-ui:")

        expect(dialog).to_contain_text("9/11 etapas locais", timeout=5_000)
        expect(dialog).to_contain_text("Explica por que feedback reduz incerteza.")
        expect(first_lesson).to_contain_text("9/11 etapas locais concluídas")
        expect(first_lesson.get_by_role("button", name="Acompanhar")).to_be_visible()
        expect(
            first_lesson.get_by_role(
                "button", name="Ver KCs de Artigo da primeira aula"
            )
        ).to_be_visible()
        assert build_reads
        assert dialog.locator("[data-knowledge-stage-details]").evaluate(
            "element => element.open"
        ) is False
        dialog.get_by_role("button", name="Fechar").click()
        expect(first_lesson.get_by_role("button", name="Acompanhar")).to_be_focused()
        browser.close()


def test_kc_modal_filters_one_publication_and_deduplicates_lesson_work(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser KC results {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "kc-results.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    shaped = {
        "offer": None,
        "build": None,
        "summary": None,
        "source_a": None,
        "reused_lesson_id": None,
    }

    def mutate_detail(payload):
        lesson = payload["lessons"][0]
        source_a = lesson["sources"][0]
        source_a["review"] = {"validated": True, "complexity": "simple"}
        source_a["has_markdown"] = True
        source_a["markdown"] = {"available": True}
        source_b = {
            **source_a,
            "source_id": "source-browser-neighbor",
            "reference_id": "reference-browser-neighbor",
            "title": "Fonte vizinha",
            "url": "https://example.com/vizinha",
            "review": {"validated": True, "complexity": "complex"},
        }
        lesson["sources"] = [source_a, source_b]
        shaped["source_a"] = source_a
        source_a_id = source_a["source_id"]
        reference_a_id = source_a["reference_id"]
        work_a = {
            "id": "work-a",
            "source_id": source_a_id,
            "artifact_id": "artifact-a",
            "reference_ids": [reference_a_id],
            "status": "succeeded",
            "snapshot": _snapshot(
                source_a_id,
                source_a["title"],
                "artifact-a",
                completed=9,
                statement="Distingue feedback de aprovação tardia.",
                task="Qual é a função do feedback?",
                answer="Reduzir incerteza enquanto ainda é barato mudar.",
            ),
        }
        duplicate_a = {**work_a, "id": "work-a-duplicate"}
        work_b = {
            "id": "work-b",
            "source_id": source_b["source_id"],
            "artifact_id": "artifact-b",
            "reference_ids": [source_b["reference_id"]],
            "status": "succeeded",
            "snapshot": _snapshot(
                source_b["source_id"],
                source_b["title"],
                "artifact-b",
                completed=11,
                statement="Relaciona descoberta contínua e decisões reversíveis.",
                task="O que torna uma decisão reversível?",
                answer="Baixo custo de correção após nova evidência.",
            ),
        }
        shaped["build"] = {
            "id": "build-browser-results",
            "status": "succeeded",
            "references": [
                {"reference_id": reference_a_id, "work_id": "work-a"},
                {
                    "reference_id": source_b["reference_id"],
                    "work_id": "work-b",
                },
            ],
            "work": [work_a, duplicate_a, work_b],
        }
        shaped["summary"] = {
            "id": shaped["build"]["id"],
            "status": "succeeded",
            "stage_progress": {"completed": 20, "total": 22},
            "references": shaped["build"]["references"],
            "work": [
                {
                    "id": "work-a",
                    "source_id": source_a_id,
                    "artifact_id": "artifact-a",
                    "reference_ids": [reference_a_id],
                    "status": "succeeded",
                    "kc_count": 1,
                },
                {
                    "id": "work-b",
                    "source_id": source_b["source_id"],
                    "artifact_id": "artifact-b",
                    "reference_ids": [source_b["reference_id"]],
                    "status": "succeeded",
                    "kc_count": 1,
                },
            ],
        }
        shaped["offer"] = {
            "lesson_id": lesson["id"],
            "publication_count": 2,
            "eligibility": {"eligible": True, "code": "ready"},
            "latest_build": shaped["summary"],
        }
        lesson["knowledge"] = shaped["offer"]
        source_a["knowledge"] = {
            "build_id": shaped["build"]["id"],
            "work_id": "work-a",
            "status": "succeeded",
            "current": True,
            "kc_count": 1,
        }
        source_b["knowledge"] = {
            "build_id": shaped["build"]["id"],
            "work_id": "work-b",
            "status": "succeeded",
            "current": True,
            "kc_count": 1,
        }
        reused_lesson = payload["lessons"][1]
        reused_source = reused_lesson["sources"][0]
        shaped["reused_lesson_id"] = reused_lesson["id"]
        reused_source["source_id"] = source_a_id
        reused_source["review"] = {"validated": True, "complexity": "simple"}
        reused_source["has_markdown"] = True
        reused_source["markdown"] = {"available": True}
        reused_source["knowledge"] = {
            "build_id": shaped["build"]["id"],
            "work_id": "work-a",
            "status": "succeeded",
            "current": True,
            "kc_count": 1,
        }
        reused_lesson["knowledge"] = {
            "lesson_id": reused_lesson["id"],
            "publication_count": 1,
            "eligibility": {"eligible": True, "code": "ready"},
            "latest_build": None,
        }
        payload["knowledge_manifest_id"] = "manifest-browser-results"

    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _route_detail(page, imported["syllabus_id"], mutate_detail)
        page.route(
            "**/api/knowledge-builds/build-browser-results",
            lambda route: route.fulfill(status=200, json=shaped["build"]),
        )
        def offer_handler(route):
            lesson_id = urlparse(route.request.url).path.split("/")[-2]
            offer = shaped["offer"]
            if lesson_id == shaped["reused_lesson_id"]:
                offer = {
                    "lesson_id": lesson_id,
                    "publication_count": 1,
                    "eligibility": {"eligible": True, "code": "ready"},
                    "latest_build": None,
                }
            route.fulfill(status=200, json=offer)

        page.route("**/knowledge", offer_handler)
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        first_lesson = page.locator(".syl-lesson").first
        expect(first_lesson).to_contain_text("2 KCs unitários produzidos")
        expect(first_lesson.get_by_role("button", name="Ver KCs da aula")).to_be_visible()
        universe = page.get_by_role("link", name="Universo", exact=True)
        expect(universe).to_have_attribute(
            "href",
            (
                "/graph?manifest_id=manifest-browser-results"
                f"&syllabus_id={imported['syllabus_id']}"
                f"&version_id={quote(imported['version_id'], safe='')}"
            ),
        )

        first_lesson.get_by_role(
            "button", name="Ver KCs de Artigo da primeira aula"
        ).click()
        dialog = page.locator("[data-knowledge-dialog]")
        expect(dialog).to_be_visible()
        expect(dialog.get_by_role("heading", name="KCs · Artigo da primeira aula")).to_be_visible()
        expect(dialog).to_contain_text("Distingue feedback de aprovação tardia.")
        expect(dialog).to_contain_text("Qual é a função do feedback?")
        expect(dialog).to_contain_text(
            "Reduzir incerteza enquanto ainda é barato mudar."
        )
        expect(dialog).to_contain_text("9/11 etapas locais")
        expect(dialog).to_contain_text("Artigo da primeira aula")
        expect(dialog).not_to_contain_text("Fonte vizinha")
        expect(dialog).not_to_contain_text(
            "Relaciona descoberta contínua e decisões reversíveis."
        )
        expect(dialog.locator(".syl-kc-item")).to_have_count(1)
        expect(dialog.locator(".syl-knowledge-work")).to_have_count(1)
        assert dialog.locator("[data-knowledge-stage-details]").evaluate(
            "element => element.open"
        ) is False

        page.keyboard.press("Escape")
        source_button = first_lesson.get_by_role(
            "button", name="Ver KCs de Artigo da primeira aula"
        )
        expect(source_button).to_be_focused()
        first_lesson.get_by_role("button", name="Ver KCs da aula").click()
        expect(dialog).to_contain_text("20/22 etapas locais")
        expect(dialog).to_contain_text(
            "Relaciona descoberta contínua e decisões reversíveis."
        )
        expect(dialog.locator(".syl-kc-item")).to_have_count(2)
        expect(dialog.locator(".syl-knowledge-work")).to_have_count(2)
        dialog.get_by_role("button", name="Fechar").click()
        expect(first_lesson.get_by_role("button", name="Ver KCs da aula")).to_be_focused()

        reused_lesson = page.locator(".syl-lesson").nth(1)
        reused_lesson.get_by_role("button", name="Ver KCs de Livro da segunda aula").click()
        expect(dialog.get_by_role("heading", name="KCs · Livro da segunda aula")).to_be_visible()
        expect(dialog).to_contain_text("9/11 etapas locais")
        expect(dialog).to_contain_text("Distingue feedback de aprovação tardia.")
        expect(dialog.locator(".syl-kc-item")).to_have_count(1)
        expect(dialog.locator(".syl-knowledge-work")).to_have_count(1)
        browser.close()


def test_universe_publication_is_a_second_explicit_checkpoint_with_shared_progress(
    test_database_url, applied_migrations, tmp_path
):
    name = f"Browser corpus checkpoint {uuid.uuid4().hex[:8]}"
    with psycopg.connect(test_database_url) as conn:
        imported = import_workbook(
            conn,
            _editable_workbook(tmp_path / "corpus-checkpoint.xlsx"),
            name,
            require_syllabus_metadata=False,
        )

    app = create_app(lambda: psycopg.connect(test_database_url))
    state = {
        "build": None,
        "published_build": None,
        "reads_after_start": 0,
        "auto_complete": True,
    }
    posts = []

    def mutate_detail(payload):
        build = state["build"]
        if build is not None:
            state["reads_after_start"] += 1
            if state["auto_complete"] and state["reads_after_start"] >= 2:
                build = {
                    **build,
                    "status": "succeeded",
                    "progress": {
                        "completed": 4,
                        "total": 4,
                        "pending": 0,
                        "partial": 0,
                        "running": 0,
                        "failed": 0,
                    },
                }
                state["build"] = build
                state["published_build"] = build
        payload["knowledge"] = {
            "eligibility": {"eligible": True, "code": "ready"},
            "complete_publication_count": 2,
            "publication_count": 2,
            "latest_build": build,
            "published_build": state["published_build"],
        }
        published_build = state["published_build"]
        if published_build and published_build.get("current", True):
            payload["knowledge_manifest_id"] = published_build["manifest_id"]
        else:
            payload.pop("knowledge_manifest_id", None)

    with _serve(app) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        _route_detail(page, imported["syllabus_id"], mutate_detail)

        def start_handler(route):
            posts.append(route.request.post_data_json)
            state["build"] = {
                "id": "syllabus-build-browser",
                "manifest_id": "manifest-browser-published",
                "status": "running",
                "current": True,
                "progress": {
                    "completed": 0,
                    "total": 4,
                    "pending": 4,
                    "partial": 0,
                    "running": 0,
                    "failed": 0,
                },
            }
            route.fulfill(status=202, json=state["build"])

        page.route("**/versions/*/knowledge-builds", start_handler)
        page.goto(f"{base_url}/syllabi?id={imported['syllabus_id']}")

        page.get_by_role("button", name="Publicar Universo").click()
        dialog = page.locator("[data-knowledge-dialog]")
        expect(dialog).to_be_visible()
        expect(dialog).to_contain_text("segundo checkpoint explícito")
        expect(dialog.get_by_role("button", name="Confirmar publicação")).to_be_visible()
        assert posts == []

        dialog.get_by_role("button", name="Confirmar publicação").click()
        expect(dialog).to_be_visible()
        expect(dialog).to_contain_text("0/4 etapas compartilhadas")
        expect(page.get_by_role("button", name="0/4 · Publicando Universo")).to_be_visible()
        assert len(posts) == 1
        assert set(posts[0]) == {"request_key"}

        universe = page.get_by_role("link", name="Universo", exact=True)
        expect(universe).to_be_visible(timeout=7_000)
        expected_href = (
            "/graph?manifest_id=manifest-browser-published"
            f"&syllabus_id={imported['syllabus_id']}"
            f"&version_id={quote(imported['version_id'], safe='')}"
        )
        expect(universe).to_have_attribute("href", expected_href)
        expect(dialog).to_contain_text("Universo publicado")
        expect(dialog).to_contain_text("4/4 etapas compartilhadas")
        expect(dialog.get_by_role("link", name="Abrir Universo")).to_have_attribute(
            "href", expected_href
        )
        dialog.locator("[data-knowledge-close]").first.click()
        expect(universe).to_be_focused()

        state["auto_complete"] = False
        state["reads_after_start"] = 0
        state["build"] = {
            "id": "syllabus-build-browser-republish",
            "manifest_id": "manifest-browser-republish",
            "status": "queued",
            "current": True,
            "progress": {
                "completed": 0,
                "total": 4,
                "pending": 4,
                "partial": 0,
                "running": 0,
                "failed": 0,
            },
        }
        page.reload()
        expect(page.get_by_role("link", name="Universo", exact=True)).to_have_attribute(
            "href", expected_href
        )
        republishing = page.get_by_role("button", name="0/4 · Publicando Universo")
        expect(republishing).to_be_visible()
        republishing.click()
        expect(dialog).to_contain_text("0/4 etapas compartilhadas")
        expect(dialog.get_by_role("link", name="Abrir Universo publicado")).to_have_attribute(
            "href", expected_href
        )
        dialog.locator("[data-knowledge-close]").first.click()

        state["build"] = {**state["build"], "status": "failed"}
        state["published_build"] = {
            **state["published_build"],
            "current": False,
        }
        page.reload()
        previous = page.get_by_role("link", name="Universo anterior")
        expect(previous).to_have_attribute("href", expected_href)
        expect(
            page.get_by_role("button", name="Publicar novo Universo")
        ).to_be_visible()
        browser.close()
