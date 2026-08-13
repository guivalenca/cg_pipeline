"""Browser contract for manifest pinning, graph behavior and return context."""

from contextlib import contextmanager
import hashlib
import socket
import threading
import time
from urllib.parse import urlencode, urlsplit

from playwright.sync_api import expect, sync_playwright
import uvicorn

from universe.web.app import create_app


@contextmanager
def _serve(app):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(128)
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="error", lifespan="on"))
    thread = threading.Thread(
        target=server.run,
        kwargs={"sockets": [sock]},
        daemon=True,
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


def _group_id(*task_ids):
    digest = hashlib.sha256("\n".join(sorted(task_ids)).encode()).hexdigest()[:12]
    return f"kc-{digest}"


def _graph_payload():
    group_id = _group_id("task-a", "task-b")
    return {
        "manifest": {"id": "manifest-browser"},
        "nodes": [
            {
                "id": "task-a",
                "statement": "Distingue feedback de aprovação tardia.",
                "modality": "explain",
                "knowledge": "concept",
                "source_id": "source-a",
                "source_title": "Artigo da aula",
                "task": "Qual é a função do feedback?",
                "answer": "Reduzir incerteza enquanto ainda é barato mudar.",
                "group_id": group_id,
            },
            {
                "id": "task-b",
                "statement": "Feedback antecipa evidência para a decisão.",
                "modality": "explain",
                "knowledge": "concept",
                "source_id": "source-b",
                "source_title": "Vídeo da aula",
                "task": "Quando o feedback ajuda uma decisão?",
                "answer": "Antes de a correção ficar cara.",
                "group_id": group_id,
            },
        ],
        "edges": [
            {
                "a": "task-a",
                "b": "task-b",
                "ab": "clear_yes",
                "ba": "clear_yes",
                "mutual": True,
            }
        ],
        "groups": [
            {
                "id": group_id,
                "members": ["task-a", "task-b"],
                "canonical_status": "stated",
                "canonical_statement": "Feedback reduz o custo de corrigir decisões.",
                "canonical_reason": None,
            }
        ],
        "grouping": {
            "id": "g-browser",
            "stale": False,
            "stale_reasons": [],
        },
    }


def test_graph_renders_exact_nodes_edge_group_detail_and_return_context():
    manifest_id = "kc-corpus-" + "a" * 64
    query = urlencode(
        {
            "manifest_id": manifest_id,
            "syllabus_id": "si-module-7-2026",
            "version_id": "sv-module-7-v2",
            "back": "/syllabi?view=kcs",
        }
    )
    requested = []

    with _serve(create_app(lambda: None)) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.emulate_media(reduced_motion="reduce")

        def fulfill_universe(route):
            requested.append(route.request.url)
            route.fulfill(status=200, json=_graph_payload())

        page.route("**/api/universe?*", fulfill_universe)
        page.goto(f"{base_url}/graph?{query}")

        back = page.locator("[data-universe-back]")
        expect(back).to_be_visible()
        expect(back).to_have_attribute(
            "href",
            "/syllabi?view=kcs&id=si-module-7-2026&version_id=sv-module-7-v2",
        )
        expect(back).to_have_text("← Voltar ao syllabus")
        expect(page.locator(".u-node")).to_have_count(2)
        expect(page.locator(".u-edge--mutual")).to_have_count(1)
        expect(page.locator(".u-hull")).to_have_count(1)

        page.locator('.u-node[data-id="task-a"]').click(force=True)
        detail = page.locator("[data-detail]")
        expect(detail).to_contain_text("Feedback reduz o custo de corrigir decisões.")
        expect(detail).to_contain_text("Qual é a função do feedback?")
        expect(detail).to_contain_text(
            "Reduzir incerteza enquanto ainda é barato mudar."
        )
        expect(detail.locator(".universe-member-card")).to_have_count(2)
        browser.close()

    assert len(requested) == 1
    request = urlsplit(requested[0])
    assert request.path == "/api/universe"
    assert request.query == f"manifest_id={manifest_id}"


def test_graph_without_a_manifest_returns_to_syllabi_without_fetching_universe():
    requested = []

    with _serve(create_app(lambda: None)) as base_url, sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.route(
            "**/api/universe?*",
            lambda route: (requested.append(route.request.url), route.abort()),
        )
        page.route(
            "**/api/syllabi",
            lambda route: route.fulfill(status=200, json={"syllabi": []}),
        )

        page.goto(f"{base_url}/graph")

        expect(page).to_have_url(f"{base_url}/syllabi")
        browser.close()

    assert requested == []
