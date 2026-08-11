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
    _capture_complete_page,
    _ensure_not_clipped,
    _layout_fits,
    _sanitize_reader_screenshot,
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


def _reader_capture_png(*, covered: bool) -> bytes:
    image = Image.new("RGB", (200, 300), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle((50, 30, 150, 90), outline="black", width=3)
    if covered:
        draw.line((20, 224, 180, 224), fill="black", width=4)
    draw.line((0, 240, 199, 240), fill="black", width=3)
    draw.rectangle((160, 250, 190, 270), outline="black", width=2)
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def test_reader_screenshot_removes_navigation_chrome_when_page_has_clearance():
    sanitized = _sanitize_reader_screenshot(_reader_capture_png(covered=False))

    assert sanitized is not None
    with Image.open(io.BytesIO(sanitized)) as image:
        assert image.size == (200, 236)


def test_reader_screenshot_rejects_page_content_covered_by_navigation_chrome():
    assert _sanitize_reader_screenshot(_reader_capture_png(covered=True)) is None


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
