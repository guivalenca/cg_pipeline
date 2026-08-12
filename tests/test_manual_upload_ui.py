"""Static contract checks for the per-source manual acquisition dialog."""

from pathlib import Path


STATIC = Path(__file__).parents[1] / "src" / "universe" / "web" / "static"


def test_manual_upload_dialog_makes_scope_and_consent_explicit() -> None:
    html = (STATIC / "syllabi.html").read_text(encoding="utf-8")

    assert "data-manual-dialog" in html
    assert 'data-manual-kind="pdf"' in html
    assert 'data-manual-kind="images"' in html
    assert "De 1 a 50 screenshots" in html
    assert "envio do arquivo à Firecrawl" in html
    assert "envio de todas as páginas ao OpenRouter/Gemini" in html
    assert "Screenshots são reunidos, na ordem escolhida, em um PDF" in html
    assert "KCs não serão gerados automaticamente" in html
    assert "Processar e criar Markdown" in html


def test_manual_upload_posts_ordered_files_to_one_source() -> None:
    javascript = (STATIC / "syllabi.js").read_text(encoding="utf-8")

    assert "data-manual-source" in javascript
    assert "/api/sources/${encodeURIComponent(sourceId)}/manual-upload" in javascript
    assert "data.append('kind', manual.kind)" in javascript
    assert "manual.items.forEach((item) => data.append('files', item.file, item.file.name))" in javascript
    assert "response.status !== 202" in javascript
    assert "replaceSourceState(sourceId, body)" in javascript
    assert "renderDetail()" in javascript


def test_book_queue_starts_without_redundant_confirmation() -> None:
    javascript = (STATIC / "syllabi.js").read_text(encoding="utf-8")

    assert "O Browserbase abrirá o leitor autenticado" not in javascript
    assert "Firecrawl como um PDF ordenado" not in javascript
    assert "OpenRouter/Gemini para localizar figuras" not in javascript
    assert javascript.count("window.confirm") == 1


def test_manual_upload_rejects_mixed_or_unsupported_files_in_browser() -> None:
    javascript = (STATIC / "syllabi.js").read_text(encoding="utf-8")

    assert "PDF e imagens não podem ser misturados" in javascript
    assert "image/png" in javascript
    assert "image/jpeg" in javascript
    assert "image/webp" in javascript
    assert "manual.items.length + files.length > 50" in javascript
    assert "data-manual-up" in javascript
    assert "data-manual-down" in javascript
    assert "data-manual-remove" in javascript


def test_article_image_progress_distinguishes_raw_and_canonical_markdown() -> None:
    javascript = (STATIC / "syllabi.js").read_text(encoding="utf-8")
    html = (STATIC / "syllabi.html").read_text(encoding="utf-8")

    assert "source.image_branch?.active" in javascript
    assert "O Markdown final só será publicado" in javascript
    assert "depois da análise visual e da limpeza" in javascript
    assert "Evidências visuais" in javascript
    assert "data-markdown-body" in javascript
    assert "renderedMarkdown + renderImageSidecar(body)" in javascript
    assert "image.error || image.failure_code" in javascript
    assert "Imagem preservada" in javascript
    assert "safeAssetUrl(image.asset_url)" in javascript
    assert "data-markdown-heading" in html
    assert "'[data-markdown-heading]'" in javascript


def test_sidecar_auto_loads_only_same_origin_ledger_assets() -> None:
    javascript = (STATIC / "syllabi.js").read_text(encoding="utf-8")

    assert "function safeAssetUrl" in javascript
    assert "^\\/api\\/source-assets\\/" in javascript
    assert "safeAssetUrl(image.asset_url)" in javascript
    assert "safeUrl(image.original_url)" in javascript
    assert 'target="_blank" rel="noopener noreferrer"' in javascript
