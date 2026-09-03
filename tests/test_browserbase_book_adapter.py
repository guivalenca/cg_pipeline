"""Browserbase book Adapter lifecycle and provider-boundary contracts."""

import io
from contextlib import contextmanager

import pytest
from PIL import Image, ImageDraw

from universe.acquisition.book_acquisition import (
    BookAcquisitionError,
    BookCaptureRequest,
    CompletedBookPage,
)
from universe.acquisition.browserbase_book_adapter import (
    BrowserbaseBookAdapter,
    BrowserbasePageCapture,
    _PlaywrightBookReader,
    _capture_complete_page,
    _ensure_not_clipped,
    _layout_fits,
    _sanitize_reader_screenshot,
    _settle_reader_controls,
    _screenshot_frame,
    safe_browser_error,
)
from universe.acquisition.browserbase_lock import browserbase_context_lock_key


def _completed(ordinal, label, reader_id):
    return CompletedBookPage(
        ordinal=ordinal,
        source_asset_id=f"asset-{ordinal}",
        printed_page_label=label,
        reader_page_id=reader_id,
        image_sha256="a" * 64,
        exact_text_sha256="b" * 64,
    )


def test_book_adapter_holds_context_lock_skips_completed_prefix_and_releases_session():
    events = []
    lock_identities = []
    persisted = []

    @contextmanager
    def lock_factory(identity):
        lock_identities.append(identity)
        events.append("lock-acquired")
        yield
        events.append("lock-released")

    class Session:
        session_id = "must-not-be-persisted"
        browser = object()

        def release(self):
            events.append("session-released")

    class Reader:
        final_url = "https://reader.example/books/isbn/pageid/212?secret=query"

        def capture_page(self, *, ordinal, printed_page_label, preferred_reader_page_id):
            events.append(f"capture-{ordinal}")
            assert preferred_reader_page_id == ("211" if ordinal == 2 else "212")
            return BrowserbasePageCapture(
                reader_page_id=str(209 + ordinal),
                image_body=f"png-{ordinal}".encode(),
                exact_text=f"Exact text {printed_page_label} " + "word " * 20,
            )

    adapter = BrowserbaseBookAdapter(
        api_key="test-api-key",
        project_id="test-project",
        context_id="persistent-context",
        terminal_url="https://library.example/catalog",
        session_opener=lambda _config, _sink: Session(),
        reader_opener=lambda _session, _request, _credentials, _sink: Reader(),
        lock_factory=lock_factory,
    )
    request = BookCaptureRequest(
        source_id="source-book",
        title="Book",
        resource_code="isbn",
        scope_kind="pages",
        scope_value="198-200",
    )

    summary = adapter.capture(
        request,
        completed_pages=[_completed(1, "198", "210")],
        persist_page=lambda page: persisted.append(page) or _completed(
            page.ordinal, page.printed_page_label, page.reader_page_id
        ),
    )

    assert lock_identities == ["persistent-context"]
    assert [page.ordinal for page in persisted] == [2, 3]
    assert events == [
        "lock-acquired",
        "capture-2",
        "capture-3",
        "session-released",
        "lock-released",
    ]
    assert summary.final_url == "https://reader.example/books/isbn/pageid/212"
    assert summary.original_library_url == "https://library.example/catalog"
    assert "must-not-be-persisted" not in str(summary.diagnostics)


def test_book_adapter_resolves_chapter_scope_before_resuming_page_capture():
    requested_chapters = []
    captured_labels = []
    persisted = []

    class Session:
        browser = object()

        def release(self):
            pass

    class Reader:
        final_url = "https://reader.example/books/isbn/pageid/302"

        def resolve_chapter_page_labels(self, value):
            requested_chapters.append(value)
            return ("101", "102")

        def capture_page(
            self, *, ordinal, printed_page_label, preferred_reader_page_id
        ):
            captured_labels.append(printed_page_label)
            assert ordinal == 2
            assert preferred_reader_page_id == "302"
            return BrowserbasePageCapture(
                reader_page_id="302",
                image_body=b"page-102",
                exact_text="Exact text for printed page 102. " + "word " * 20,
            )

    adapter = BrowserbaseBookAdapter(
        api_key="test-api-key",
        context_id="persistent-context",
        session_opener=lambda _config, _sink: Session(),
        reader_opener=lambda _session, _request, _credentials, _sink: Reader(),
        lock_factory=lambda _identity: _null_context(),
    )
    request = BookCaptureRequest(
        source_id="source-chapter",
        title="Chapter-scoped book",
        resource_code="isbn",
        scope_kind="chapters",
        scope_value="5",
    )

    summary = adapter.capture(
        request,
        completed_pages=[_completed(1, "101", "301")],
        persist_page=lambda page: persisted.append(page) or _completed(
            page.ordinal, page.printed_page_label, page.reader_page_id
        ),
    )

    assert requested_chapters == ["5"]
    assert captured_labels == ["102"]
    assert "5" not in captured_labels
    assert [page.printed_page_label for page in persisted] == ["102"]
    assert summary.resolved_page_labels == ("101", "102")


def test_playwright_reader_resolves_chapter_through_the_visible_toc():
    toc_text = """
    Expandir tudo
    Chapter 5 Foundations 101
    5.1 First principles 101
    Chapter 6 Applications 103
    """

    class Locator:
        def __init__(self, page, *, body=False, action=None):
            self.page = page
            self.body = body
            self.action = action

        @property
        def first(self):
            return self

        def count(self):
            return 1 if self.body or self.action else 0

        def inner_text(self, **_kwargs):
            return self.page.body

        def click(self, **_kwargs):
            if self.action == "open-toc":
                self.page.body = toc_text

    class Page:
        url = "https://integrada.minhabiblioteca.com.br/reader/books/isbn"

        def __init__(self):
            self.body = "Reader shell with Sumário control"

        def locator(self, selector):
            return Locator(self, body=selector == "body")

        def get_by_role(self, _role, *, name):
            pattern = str(getattr(name, "pattern", name))
            action = "open-toc" if "Contents" in pattern else None
            return Locator(self, action=action)

        def get_by_text(self, _name):
            return Locator(self)

        def wait_for_timeout(self, _milliseconds):
            pass

    reader = _PlaywrightBookReader(
        Page(),
        BookCaptureRequest(
            "source-chapter", "Book", "isbn", "chapters", "5"
        ),
        lambda _event: None,
    )

    assert reader.resolve_chapter_page_labels("5") == ("101", "102")


def test_playwright_reader_retries_until_the_requested_toc_boundary_is_visible(
    monkeypatch,
):
    snapshots = iter(
        (
            "Expandir tudo\nChapter 1 Introduction 1\nChapter 2 Basics 10",
            "Expandir tudo\nChapter 5 Foundations 101\nChapter 6 Applications 103",
        )
    )
    reads = []

    def next_snapshot(_page):
        snapshot = next(snapshots)
        reads.append(snapshot)
        return snapshot

    monkeypatch.setattr(
        "universe.acquisition.browserbase_book_adapter._reader_table_of_contents_text",
        next_snapshot,
    )

    class Page:
        url = "https://integrada.minhabiblioteca.com.br/reader/books/isbn"

        def wait_for_timeout(self, _milliseconds):
            pass

    reader = _PlaywrightBookReader(
        Page(),
        BookCaptureRequest(
            "source-chapter", "Book", "isbn", "chapters", "5"
        ),
        lambda _event: None,
    )

    assert reader.resolve_chapter_page_labels("5") == ("101", "102")
    assert len(reads) == 2


def test_book_adapter_releases_session_and_sanitizes_transient_browser_failure():
    released = []

    class Session:
        browser = object()

        def release(self):
            released.append(True)

    class BrokenReader:
        final_url = ""

        def capture_page(self, **_kwargs):
            raise RuntimeError(
                "WebSocket wss://connect.browserbase.com?token=secret "
                "failed at https://reader.example/page?access_token=secret"
            )

    adapter = BrowserbaseBookAdapter(
        api_key="test-api-key",
        context_id="persistent-context",
        session_opener=lambda _config, _sink: Session(),
        reader_opener=lambda _session, _request, _credentials, _sink: BrokenReader(),
        lock_factory=lambda _identity: _null_context(),
    )

    with pytest.raises(BookAcquisitionError) as raised:
        adapter.capture(
            BookCaptureRequest(
                "source-book", "Book", "isbn", "pages", "198"
            ),
            completed_pages=[],
            persist_page=lambda page: page,
        )

    assert raised.value.retriable is True
    assert released == [True]
    assert "secret" not in safe_browser_error(raised.value)
    assert "wss://" not in safe_browser_error(raised.value)


@contextmanager
def _null_context():
    yield


def test_browserbase_context_lock_uses_concept_universe_namespace():
    key = browserbase_context_lock_key("persistent-context")

    assert key.startswith("concept-universe:browserbase-context:")
    assert "persistent-context" not in key


def test_reader_layout_requires_both_axes_and_every_visual_descendant_to_fit():
    complete = {
        "clientWidth": 2200,
        "clientHeight": 1800,
        "scrollWidth": 2200,
        "scrollHeight": 1800,
        "visualRight": 2198,
        "visualBottom": 1798,
    }

    assert _layout_fits(complete)
    assert not _layout_fits({**complete, "scrollHeight": 2200})
    assert not _layout_fits({**complete, "visualBottom": 1900})
    assert not _layout_fits({**complete, "visualRight": 2400})
    assert not _layout_fits({"clientWidth": 2200})


def test_reader_viewport_grows_until_a_long_page_is_fully_visible(monkeypatch):
    class Page:
        viewport_size = {"width": 2200, "height": 1800}

        def __init__(self):
            self.sizes = []

        def set_viewport_size(self, size):
            self.viewport_size = dict(size)
            self.sizes.append(dict(size))

        def wait_for_timeout(self, _milliseconds):
            pass

    page = Page()

    class Frame:
        def evaluate(self, _script):
            height = page.viewport_size["height"]
            required = 3200
            return {
                "clientWidth": page.viewport_size["width"],
                "clientHeight": height,
                "scrollWidth": page.viewport_size["width"],
                "scrollHeight": max(height, required),
                "visualRight": page.viewport_size["width"],
                "visualBottom": required,
            }

    frame = Frame()
    monkeypatch.setattr(
        "universe.acquisition.browserbase_book_adapter._fit_height",
        lambda _page: True,
    )
    monkeypatch.setattr(
        "universe.acquisition.browserbase_book_adapter._wait_for_reader_frame",
        lambda _page, _resource_code, _label: frame,
    )

    resolved = _ensure_not_clipped(page, frame, "205")

    assert resolved is frame
    assert page.sizes[-1]["height"] >= 3200


def test_page_screenshot_never_falls_back_to_a_clipped_body_or_viewport():
    class ImageLocator:
        first = None

        def __init__(self):
            self.first = self

        def bounding_box(self, **_kwargs):
            return {"width": 1200, "height": 1800}

        def screenshot(self, **_kwargs):
            raise TimeoutError("element screenshot timed out")

    class Frame:
        page = object()

        def locator(self, selector):
            assert selector == "#pbk-page"
            return ImageLocator()

    with pytest.raises(BookAcquisitionError) as raised:
        _screenshot_frame(Frame())

    assert raised.value.code == "book_page_screenshot_failed"
    assert raised.value.retriable is True


def _reader_capture_png(
    *, covered: bool, chrome_y: int = 240, sparse_content: bool = False
) -> bytes:
    image = Image.new("RGB", (200, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((50, 30, 150, 90), outline="black", width=3)
    if covered:
        draw.line((20, 224, 180, 224), fill="black", width=4)
    if sparse_content:
        for offset in range(31):
            x = 20 + (offset * 4)
            y = 200 + offset
            draw.rectangle((x, y, x + 1, y + 1), fill="black")
    draw.rectangle(
        (185, chrome_y - 12, 194, chrome_y - 4), outline="black", width=1
    )
    draw.line((0, chrome_y, 199, chrome_y), fill="black", width=3)
    control_top = min(292, chrome_y + 8)
    draw.rectangle((160, control_top, 190, min(298, control_top + 18)), outline="black", width=2)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _complete_reader_source_jpeg() -> bytes:
    image = Image.new("RGB", (200, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 30, 170, 270), outline="black", width=4)
    draw.line((0, 240, 199, 240), fill="black", width=3)
    draw.rectangle((80, 275, 120, 290), fill="black")
    output = io.BytesIO()
    image.save(output, format="JPEG", quality=95)
    return output.getvalue()


def test_reader_screenshot_removes_navigation_chrome_when_page_has_clearance():
    sanitized = _sanitize_reader_screenshot(_reader_capture_png(covered=False))

    assert sanitized is not None
    with Image.open(io.BytesIO(sanitized)) as image:
        assert image.size == (200, 192)


def test_reader_screenshot_rejects_page_content_covered_by_navigation_chrome():
    assert _sanitize_reader_screenshot(_reader_capture_png(covered=True)) is None


def test_reader_screenshot_rejects_sparse_content_inside_chrome_clearance():
    assert (
        _sanitize_reader_screenshot(
            _reader_capture_png(covered=False, sparse_content=True)
        )
        is None
    )


def test_reader_screenshot_finds_chrome_below_ninety_percent_of_tall_viewport():
    sanitized = _sanitize_reader_screenshot(
        _reader_capture_png(covered=False, chrome_y=280)
    )

    assert sanitized is not None
    with Image.open(io.BytesIO(sanitized)) as image:
        assert image.size == (200, 232)


def test_reader_capture_clears_hover_and_focus_before_screenshot():
    class Keyboard:
        presses = []

        def press(self, key):
            self.presses.append(key)

    class Mouse:
        moves = []

        def move(self, x, y):
            self.moves.append((x, y))

    class Page:
        keyboard = Keyboard()
        mouse = Mouse()
        waits = []

        def wait_for_timeout(self, milliseconds):
            self.waits.append(milliseconds)

    page = Page()

    _settle_reader_controls(page)

    assert page.keyboard.presses == ["Escape"]
    assert page.mouse.moves == [(1, 1)]
    assert page.waits == [250]


def test_capture_grows_viewport_when_bitmap_guard_finds_covered_content(monkeypatch):
    class Page:
        viewport_size = {"width": 2200, "height": 1800}

        def __init__(self):
            self.sizes = []

        def set_viewport_size(self, size):
            self.viewport_size = dict(size)
            self.sizes.append(dict(size))

        def wait_for_timeout(self, _milliseconds):
            pass

    page = Page()

    class ImageLocator:
        first = None

        def __init__(self):
            self.first = self

        def bounding_box(self, **_kwargs):
            return {"width": 1200, "height": page.viewport_size["height"]}

        def screenshot(self, **_kwargs):
            return _reader_capture_png(covered=page.viewport_size["height"] < 2800)

    class Frame:
        def evaluate(self, _script):
            return {
                "clientWidth": page.viewport_size["width"],
                "clientHeight": page.viewport_size["height"],
                "scrollWidth": page.viewport_size["width"],
                "scrollHeight": page.viewport_size["height"],
                "visualRight": page.viewport_size["width"],
                "visualBottom": page.viewport_size["height"],
            }

        def locator(self, selector):
            assert selector == "#pbk-page"
            return ImageLocator()

    frame = Frame()
    monkeypatch.setattr(
        "universe.acquisition.browserbase_book_adapter._fit_height",
        lambda _page: True,
    )
    monkeypatch.setattr(
        "universe.acquisition.browserbase_book_adapter._wait_for_reader_frame",
        lambda _page, _resource_code, _label: frame,
    )

    resolved, payload = _capture_complete_page(page, frame, "68")

    assert resolved is frame
    assert page.sizes[-1]["height"] >= 2800
    assert _sanitize_reader_screenshot(payload) == payload


def test_book_capture_uses_complete_reader_image_response_instead_of_chrome_composited_pixels(
    monkeypatch,
):
    clean_source = _complete_reader_source_jpeg()

    class Response:
        status = 200
        ok = True
        headers = {"content-type": "image/jpeg"}

        def body(self):
            return clean_source

    class Request:
        def get(self, url, *, headers, timeout):
            assert url == "https://jigsaw.minhabiblioteca.com.br/books/isbn/images/page"
            assert headers == {
                "Referer": "https://jigsaw.minhabiblioteca.com.br/books/isbn/pages/200/content"
            }
            assert timeout == 15_000
            return Response()

    class Context:
        request = Request()

    class Page:
        viewport_size = {"width": 2200, "height": 1800}
        context = Context()

        def set_viewport_size(self, _size):
            raise AssertionError("the complete reader resource should avoid viewport retries")

    class ImageLocator:
        first = None

        def __init__(self):
            self.first = self

        def evaluate(self, _script):
            return {
                "currentSrc": "/books/isbn/images/page",
                "naturalWidth": 200,
                "naturalHeight": 300,
            }

        def bounding_box(self, **_kwargs):
            return {"width": 200, "height": 300}

        def screenshot(self, **_kwargs):
            return _reader_capture_png(covered=True)

    class Frame:
        page = Page()
        url = "https://jigsaw.minhabiblioteca.com.br/books/isbn/pages/200/content"

        def evaluate(self, _script):
            return {
                "clientWidth": 200,
                "clientHeight": 300,
                "scrollWidth": 200,
                "scrollHeight": 300,
                "visualRight": 200,
                "visualBottom": 300,
            }

        def locator(self, selector):
            assert selector == "#pbk-page"
            return ImageLocator()

    monkeypatch.setattr(
        "universe.acquisition.browserbase_book_adapter._fit_height",
        lambda _page: True,
    )

    _, payload = _capture_complete_page(Page(), Frame(), "200")

    with Image.open(io.BytesIO(payload)) as captured:
        assert captured.format == "PNG"
        assert captured.size == (200, 300)
        assert captured.convert("L").getpixel((100, 282)) < 40
