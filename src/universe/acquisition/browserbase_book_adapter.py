"""Browserbase Implementation of the ordered book capture Adapter."""

from __future__ import annotations

import io
import json
import os
import re
import time
from contextlib import AbstractContextManager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import urljoin, urlsplit, urlunsplit

from PIL import Image, UnidentifiedImageError

from universe.acquisition.book_acquisition import (
    BookAcquisitionError,
    BookCaptureRequest,
    BookCaptureSummary,
    CapturedBookPage,
    CompletedBookPage,
    book_page_labels,
)
from universe.acquisition.browserbase_lock import (
    BrowserbaseContextLock,
    BrowserbaseContextLockTimeout,
)
from universe.acquisition.browserbase_session import (
    BrowserbaseSessionConfig,
    BrowserbaseSessionError,
    create_browserbase_context,
    open_browserbase_session,
)


CAPTURE_VERSION = "browserbase-book-capture.v5"
DEFAULT_TERMINAL_URL = "https://philos.sophia.com.br/terminal/9418"
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONTEXT_FILE = PROJECT_ROOT / ".data" / "browserbase_context.json"
EventSink = Callable[[dict[str, Any]], None]


@dataclass(frozen=True)
class LibraryCredentials:
    username: str = ""
    password: str = ""


@dataclass(frozen=True)
class BrowserbasePageCapture:
    reader_page_id: str
    image_body: bytes
    exact_text: str


class BrowserbaseBookAdapter:
    """Hold one context lease while a reader publishes durable page callbacks."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        project_id: str | None = None,
        context_id: str | None = None,
        context_file: str | Path | None = None,
        region: str | None = None,
        terminal_url: str | None = None,
        credentials: LibraryCredentials | None = None,
        session_opener: Callable[[BrowserbaseSessionConfig, EventSink], Any]
        | None = None,
        reader_opener: Callable[[Any, BookCaptureRequest, LibraryCredentials, EventSink], Any]
        | None = None,
        lock_factory: Callable[[str], AbstractContextManager[Any]] | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self.api_key = str(api_key or os.getenv("BROWSERBASE_API_KEY", "")).strip()
        self.project_id = str(
            project_id or os.getenv("BROWSERBASE_PROJECT_ID", "")
        ).strip()
        self.context_id = str(
            context_id or os.getenv("BROWSERBASE_CONTEXT_ID", "")
        ).strip()
        configured_context_file = str(
            context_file or os.getenv("BROWSERBASE_CONTEXT_FILE", "")
        ).strip()
        self.context_file = (
            Path(configured_context_file).expanduser().resolve()
            if configured_context_file
            else DEFAULT_CONTEXT_FILE
        )
        self.region = str(
            region or os.getenv("BROWSERBASE_REGION", "us-west-2")
        ).strip()
        self.terminal_url = str(
            terminal_url or os.getenv("SOPHIA_TERMINAL_URL", DEFAULT_TERMINAL_URL)
        ).strip()
        self.credentials = credentials or LibraryCredentials(
            username=(
                os.getenv("CG_PIPELINE_LIBRARY_USERNAME", "").strip()
                or os.getenv("LIBRARY_USERNAME", "").strip()
            ),
            password=(
                os.getenv("CG_PIPELINE_LIBRARY_PASSWORD", "").strip()
                or os.getenv("LIBRARY_PASSWORD", "").strip()
            ),
        )
        self._session_opener = session_opener or open_browserbase_session
        self._reader_opener = reader_opener or _open_playwright_reader
        self._lock_factory = lock_factory or self._context_lock
        self._sink = event_sink or (lambda _event: None)

    def capture(
        self,
        request: BookCaptureRequest,
        *,
        completed_pages: Sequence[CompletedBookPage],
        persist_page: Callable[[CapturedBookPage], CompletedBookPage],
    ) -> BookCaptureSummary:
        if not self.api_key:
            raise BookAcquisitionError(
                "browserbase_not_configured", "configuration"
            )
        labels = book_page_labels(request.scope_value)
        if labels is None:
            raise BookAcquisitionError(
                "book_scope_invalid", "missing_concrete_scope"
            )
        _validate_completed_prefix(completed_pages, labels)
        lock_identity = self.context_id or f"context-file:{self.context_file}"
        events: list[dict[str, Any]] = []

        def emit(event: dict[str, Any]) -> None:
            safe = _safe_event(event)
            events.append(safe)
            try:
                self._sink(safe)
            except Exception:
                pass

        try:
            with self._lock_factory(lock_identity):
                context_id = self._resolved_context_id()
                config = BrowserbaseSessionConfig(
                    api_key=self.api_key,
                    project_id=self.project_id,
                    context_id=context_id,
                    region=self.region,
                    timeout_seconds=max(
                        60, int(os.getenv("BROWSERBASE_TIMEOUT_SECONDS", "3600"))
                    ),
                    viewport_width=2200,
                    viewport_height=1800,
                    proxy_enabled=_env_flag("BROWSERBASE_PROXY_ENABLED"),
                    proxy_geolocation={
                        key: value
                        for key, value in {
                            "city": os.getenv("BROWSERBASE_PROXY_CITY", ""),
                            "state": os.getenv("BROWSERBASE_PROXY_STATE", ""),
                            "country": os.getenv("BROWSERBASE_PROXY_COUNTRY", ""),
                        }.items()
                        if value.strip()
                    },
                    user_metadata={
                        "source_kind": "book",
                        "source_id": request.source_id,
                        "resource_code": request.resource_code,
                    },
                )
                session = self._session_opener(config, emit)
                try:
                    reader = self._reader_opener(
                        session, request, self.credentials, emit
                    )
                    previous_reader_id = (
                        completed_pages[-1].reader_page_id if completed_pages else ""
                    )
                    for ordinal, printed_label in enumerate(labels, 1):
                        if ordinal <= len(completed_pages):
                            continue
                        preferred = _next_reader_id(previous_reader_id)
                        capture = reader.capture_page(
                            ordinal=ordinal,
                            printed_page_label=printed_label,
                            preferred_reader_page_id=preferred,
                        )
                        if not isinstance(capture, BrowserbasePageCapture):
                            raise BookAcquisitionError(
                                "book_page_invalid", "invalid_reader_result"
                            )
                        persisted = persist_page(
                            CapturedBookPage(
                                ordinal=ordinal,
                                printed_page_label=printed_label,
                                reader_page_id=str(capture.reader_page_id or "").strip(),
                                image_body=capture.image_body,
                                mime_type="image/png",
                                exact_text=capture.exact_text,
                            )
                        )
                        previous_reader_id = persisted.reader_page_id
                    final_url = _public_url(str(getattr(reader, "final_url", "")))
                finally:
                    session.release()
        except BookAcquisitionError:
            raise
        except BrowserbaseContextLockTimeout:
            raise BookAcquisitionError(
                "browserbase_context_busy",
                "context_lock_timeout",
                retriable=True,
                retry_after_seconds=5,
            ) from None
        except BrowserbaseSessionError as exc:
            raise BookAcquisitionError(
                "browserbase_session_failed",
                "transient_browser",
                retriable=True,
                retry_after_seconds=5,
            ) from exc
        except Exception as exc:
            category = "manual_intervention" if _manual_access_error(exc) else "transient_browser"
            raise BookAcquisitionError(
                "browserbase_manual_intervention_required"
                if category == "manual_intervention"
                else "book_capture_interrupted",
                category,
                retriable=category == "transient_browser",
                retry_after_seconds=5 if category == "transient_browser" else 0,
            ) from exc

        return BookCaptureSummary(
            final_url=final_url,
            original_library_url=_public_url(self.terminal_url),
            capture_version=CAPTURE_VERSION,
            diagnostics={
                "session_restarts": 0,
                "page_attempts": len(labels) - len(completed_pages),
                "reader_kind": "minha-biblioteca",
                "warnings": [
                    event["kind"]
                    for event in events
                    if event.get("kind", "").endswith("_warning")
                ],
            },
        )

    def _resolved_context_id(self) -> str:
        if self.context_id:
            return self.context_id
        stored = _read_context_id(self.context_file)
        if stored:
            self.context_id = stored
            return stored
        created = create_browserbase_context(self.api_key)
        _write_context_id(self.context_file, created)
        self.context_id = created
        return created

    def _context_lock(self, identity: str) -> BrowserbaseContextLock:
        return BrowserbaseContextLock(
            identity=identity,
            lock_file=self.context_file.with_suffix(self.context_file.suffix + ".lock"),
            event_sink=self._sink,
            wait_seconds=max(
                0.0, float(os.getenv("BROWSERBASE_LOCK_WAIT_SECONDS", "3720"))
            ),
        )


class _PlaywrightBookReader:
    def __init__(self, page: Any, request: BookCaptureRequest, sink: EventSink) -> None:
        self.page = page
        self.request = request
        self.sink = sink

    @property
    def final_url(self) -> str:
        return str(getattr(self.page, "url", ""))

    def capture_page(
        self,
        *,
        ordinal: int,
        printed_page_label: str,
        preferred_reader_page_id: str,
    ) -> BrowserbasePageCapture:
        _wait_for_captcha(self.page)
        frame = None
        if preferred_reader_page_id:
            try:
                _navigate(
                    self.page,
                    f"https://integrada.minhabiblioteca.com.br/reader/books/"
                    f"{self.request.resource_code}/pageid/{preferred_reader_page_id}",
                )
                frame = _wait_for_reader_frame(
                    self.page, self.request.resource_code, printed_page_label
                )
            except Exception:
                frame = None
        if frame is None:
            _navigate_printed_page(
                self.page,
                printed_page_label,
                resource_code=self.request.resource_code,
            )
            frame = _wait_for_reader_frame(
                self.page, self.request.resource_code, printed_page_label
            )
        frame, image_body = _capture_complete_page(
            self.page, frame, printed_page_label
        )
        exact_text = _reader_text(frame)
        if _word_count(exact_text) < 20 and not _intentional_blank(exact_text):
            raise BookAcquisitionError(
                "book_reader_text_sparse",
                "transient_browser",
                retriable=True,
                retry_after_seconds=5,
            )
        reader_id = _reader_page_id(self.page.url) or _reader_page_id(frame.url)
        if not reader_id:
            raise BookAcquisitionError(
                "book_reader_page_id_missing", "invalid_reader_state"
            )
        return BrowserbasePageCapture(reader_id, image_body, exact_text)


def _open_playwright_reader(
    session: Any,
    request: BookCaptureRequest,
    credentials: LibraryCredentials,
    sink: EventSink,
) -> _PlaywrightBookReader:
    browser = session.browser
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    for page in list(context.pages):
        if _is_reader_url(page.url, request.resource_code):
            page.bring_to_front()
            _wait_for_captcha(page)
            if _reader_ready(page):
                _fit_height(page)
                return _PlaywrightBookReader(page, request, sink)

    terminal_url = os.getenv("SOPHIA_TERMINAL_URL", DEFAULT_TERMINAL_URL).strip()
    page = context.new_page()
    _navigate(page, terminal_url, ready_selector="#PalavraChave")
    _wait_for_captcha(page)
    if not _sophia_authenticated(page):
        if not credentials.username or not credentials.password:
            raise BookAcquisitionError(
                "library_credentials_required", "manual_intervention"
            )
        _login_sophia(page, credentials)
    _search_sophia(page, request.resource_code)
    html = page.locator("body").inner_html(timeout=30_000)
    code = _extract_sophia_code(html, request.resource_code)
    if not code:
        raise BookAcquisitionError(
            "sophia_sso_result_missing", "manual_intervention"
        )
    reader_url = _fetch_reader_url(
        context.request,
        _sophia_sso_url(terminal_url, code),
        request.resource_code,
    )
    reader_page = context.new_page()
    _navigate(reader_page, reader_url)
    _wait_for_captcha(reader_page)
    for _ in range(30):
        if _is_reader_url(reader_page.url, request.resource_code) and _reader_ready(
            reader_page
        ):
            _fit_height(reader_page)
            return _PlaywrightBookReader(reader_page, request, sink)
        reader_page.wait_for_timeout(1000)
    raise BookAcquisitionError(
        "reader_manual_intervention_required", "manual_intervention"
    )


def _navigate(page: Any, url: str, *, ready_selector: str = "body") -> None:
    last_error: Exception | None = None
    for delay in (0.0, 1.0, 2.0):
        if delay:
            page.wait_for_timeout(int(delay * 1000))
        try:
            response = page.goto(url, wait_until="commit", timeout=60_000)
            status = int(getattr(response, "status", 0) or 0)
            if status == 429 or status >= 500:
                raise RuntimeError(f"navigation status {status}")
            page.locator(ready_selector).wait_for(timeout=30_000)
            return
        except Exception as exc:
            last_error = exc
    raise RuntimeError("browser navigation failed") from last_error


def _navigate_printed_page(page: Any, label: str, *, resource_code: str) -> None:
    _assert_reader_access(page)
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    candidates = [
        page.get_by_role(
            "textbox", name=re.compile(r"Ir\s+para\s+P[aá]gina|Go\s+to\s+Page|Page", re.I)
        ).first,
        page.locator(
            'input[aria-label*="Ir para Página"], input[aria-label*="Página"], '
            'input[placeholder*="Página"], input[title*="Página"]'
        ).first,
        page.locator("input").first,
    ]
    page_input = candidates[-1]
    for candidate in candidates:
        try:
            if candidate.count():
                page_input = candidate
                break
        except Exception:
            continue
    page_input.fill(label, timeout=10_000)
    page_input.press("Enter")
    page.wait_for_timeout(2500)
    _assert_reader_access(page)


def _wait_for_reader_frame(page: Any, resource_code: str, label: str) -> Any:
    for _ in range(30):
        _assert_reader_access(page)
        candidates: list[tuple[Any, str]] = []
        for frame in page.frames:
            url = str(getattr(frame, "url", ""))
            if "/pages/" not in url or (resource_code and resource_code not in url):
                continue
            text = _reader_text(frame)
            if text:
                candidates.append((frame, text))
        for frame, text in candidates:
            if re.search(rf"(^|\s){re.escape(label)}(\s|$)", text[:300]):
                return frame
        if candidates:
            try:
                if page.locator("input").first.input_value(timeout=1000) == label:
                    return candidates[0][0]
            except Exception:
                pass
        for frame in page.frames:
            if f"/books/{resource_code}/epub/" in str(getattr(frame, "url", "")):
                if _word_count(_reader_text(frame)) >= 20:
                    return frame
        page.wait_for_timeout(1000)
    raise RuntimeError("reader page frame not identified")


def _reader_text(frame: Any) -> str:
    try:
        value = frame.locator("#pdf-ax-text").inner_text(timeout=3000)
    except Exception:
        try:
            value = frame.locator("body").inner_text(timeout=3000)
        except Exception:
            value = ""
    return _normalize_text(value)


def _screenshot_frame(frame: Any) -> bytes:
    timeout = int(os.getenv("BOOK_SCREENSHOT_TIMEOUT_MS", "15000"))
    image = frame.locator("#pbk-page").first
    try:
        box = image.bounding_box(timeout=5000)
    except Exception:
        box = None
    if not box or box.get("width", 0) <= 10 or box.get("height", 0) <= 10:
        raise BookAcquisitionError(
            "book_page_screenshot_unavailable",
            "transient_browser",
            retriable=True,
            retry_after_seconds=5,
        )
    try:
        payload: Any = image.screenshot(timeout=timeout)
    except Exception as exc:
        raise BookAcquisitionError(
            "book_page_screenshot_failed",
            "transient_browser",
            retriable=True,
            retry_after_seconds=5,
        ) from exc
    if not isinstance(payload, bytes) or not payload:
        raise BookAcquisitionError(
            "book_page_screenshot_failed",
            "transient_browser",
            retriable=True,
            retry_after_seconds=5,
        )
    return payload


def _fitted_reader_frames(page: Any, frame: Any, label: str):
    size = getattr(page, "viewport_size", None) or {}
    current_width = int(size.get("width") or 2200)
    current_height = int(size.get("height") or 1800)
    candidates = [
        (current_width, current_height),
        (max(current_width, 2200), max(current_height, 2200)),
        (max(current_width, 2600), max(current_height, 2800)),
        (max(current_width, 3000), max(current_height, 3400)),
        (max(current_width, 3400), max(current_height, 4200)),
    ]
    seen: set[tuple[int, int]] = set()
    for width, height in candidates:
        if (width, height) in seen:
            continue
        seen.add((width, height))
        if width != current_width or height != current_height:
            page.set_viewport_size({"width": width, "height": height})
            page.wait_for_timeout(1000)
            _fit_height(page)
            frame = _wait_for_reader_frame(page, "", label)
            current_width = width
            current_height = height
        metrics = _overflow_metrics(frame)
        if metrics and _layout_fits(metrics):
            yield frame


def _ensure_not_clipped(page: Any, frame: Any, label: str) -> Any:
    for fitted in _fitted_reader_frames(page, frame, label):
        return fitted
    raise BookAcquisitionError(
        "book_page_clipped",
        "invalid_reader_state",
        retriable=True,
        retry_after_seconds=5,
    )


def _capture_complete_page(
    page: Any, frame: Any, label: str
) -> tuple[Any, bytes]:
    """Capture page pixels only after both DOM and bitmap checks pass.

    The reader can report a fitting ``#pbk-page`` while a rotated or unusually
    tall page is still covered by its navigation strip.  A screenshot-level
    check removes the strip when content has safe clearance and otherwise
    advances to the next larger viewport candidate.
    """
    for fitted in _fitted_reader_frames(page, frame, label):
        source = _reader_page_image(fitted)
        if source is not None:
            return fitted, source
        _settle_reader_controls(page)
        sanitized = _sanitize_reader_screenshot(_screenshot_frame(fitted))
        if sanitized is not None:
            return fitted, sanitized
    raise BookAcquisitionError(
        "book_page_clipped",
        "invalid_reader_state",
        retriable=True,
        retry_after_seconds=5,
    )


def _reader_page_image(frame: Any) -> bytes | None:
    """Acquire the reader's page resource without parent-frame compositor UI."""
    try:
        image = frame.locator("#pbk-page").first
        metadata = image.evaluate(
            """node => ({
              currentSrc: node.currentSrc || node.src || '',
              naturalWidth: node.naturalWidth || 0,
              naturalHeight: node.naturalHeight || 0,
            })"""
        )
        if not isinstance(metadata, Mapping):
            return None
        natural_width = int(metadata.get("naturalWidth") or 0)
        natural_height = int(metadata.get("naturalHeight") or 0)
        if (
            natural_width < 40
            or natural_height < 40
            or natural_width * natural_height > 40_000_000
        ):
            return None
        frame_url = str(getattr(frame, "url", "") or "")
        source_url = urljoin(frame_url, str(metadata.get("currentSrc") or ""))
        if not _allowed_reader_page_image(source_url, frame_url):
            return None
        timeout = int(os.getenv("BOOK_SCREENSHOT_TIMEOUT_MS", "15000"))
        response = frame.page.context.request.get(
            source_url,
            headers={"Referer": frame_url},
            timeout=timeout,
        )
        if not bool(getattr(response, "ok", False)):
            return None
        body = response.body()
        if not isinstance(body, bytes) or not body or len(body) > 32 * 1024 * 1024:
            return None
        with Image.open(io.BytesIO(body)) as source:
            source.load()
            if source.size != (natural_width, natural_height):
                return None
            normalized = source.convert("RGB")
        output = io.BytesIO()
        normalized.save(output, format="PNG", optimize=True)
        return output.getvalue()
    except (AttributeError, OSError, TypeError, ValueError, UnidentifiedImageError):
        return None


def _allowed_reader_page_image(source_url: str, frame_url: str) -> bool:
    source = urlsplit(source_url)
    frame = urlsplit(frame_url)
    if (
        source.scheme != "https"
        or source.hostname != "jigsaw.minhabiblioteca.com.br"
        or frame.scheme != "https"
        or frame.hostname != "jigsaw.minhabiblioteca.com.br"
    ):
        return False
    source_match = re.match(r"^/books/([^/]+)/images/", source.path)
    frame_match = re.match(r"^/books/([^/]+)/pages/[^/]+/content$", frame.path)
    return bool(
        source_match
        and frame_match
        and source_match.group(1) == frame_match.group(1)
    )


def _settle_reader_controls(page: Any) -> None:
    """Clear focus and hover UI that can otherwise leak into page pixels."""
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    try:
        page.mouse.move(1, 1)
        page.wait_for_timeout(250)
    except Exception:
        pass


def _sanitize_reader_screenshot(payload: bytes) -> bytes | None:
    """Remove Minha Biblioteca navigation chrome or reject covered content."""
    try:
        with Image.open(io.BytesIO(payload)) as source:
            source.load()
            image = source.convert("RGB")
    except (UnidentifiedImageError, OSError):
        return None
    width, height = image.size
    if width < 40 or height < 40:
        return None
    gray = image.convert("L")
    boundary = _reader_chrome_boundary(gray)
    if boundary is None:
        margin = max(8, min(width, height) // 100)
        bottom = gray.crop((0, height - margin, width, height))
        if sum(bottom.histogram()[:210]) > width * 2:
            return None
        return payload

    guard_top = max(0, boundary - max(48, height // 35))
    guard_bottom = max(guard_top + 1, boundary - 6)
    guard = gray.crop((0, guard_top, width, guard_bottom))
    row_counts = [
        sum(guard.getpixel((x, y)) < 210 for x in range(width))
        for y in range(guard.height)
    ]
    if row_counts and (
        max(row_counts) > width * 0.12 or sum(row_counts) > width * 0.25
    ):
        return None

    cleaned = image.crop((0, 0, width, max(1, guard_top)))
    output = io.BytesIO()
    cleaned.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _reader_chrome_boundary(gray: Image.Image) -> int | None:
    """Locate the reader's near-full-width lower navigation divider."""
    width, height = gray.size
    start = int(height * 0.62)
    stop = int(height * 0.98)
    threshold = int(width * 0.75)
    previous = False
    boundary = None
    for y in range(start, stop):
        dark = sum(gray.getpixel((x, y)) < 210 for x in range(width))
        current = dark >= threshold
        if current and previous:
            boundary = y - 1
        previous = current
    return boundary


def _layout_fits(metrics: Mapping[str, Any]) -> bool:
    try:
        client_width = int(metrics["clientWidth"])
        client_height = int(metrics["clientHeight"])
        scroll_width = int(metrics["scrollWidth"])
        scroll_height = int(metrics["scrollHeight"])
        visual_right = int(metrics["visualRight"])
        visual_bottom = int(metrics["visualBottom"])
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        client_width > 10
        and client_height > 10
        and scroll_width <= client_width + 8
        and scroll_height <= client_height + 8
        and visual_right <= client_width + 8
        and visual_bottom <= client_height + 8
    )


def _overflow_metrics(frame: Any) -> Mapping[str, Any] | None:
    try:
        result = frame.evaluate(
            """() => {
              const p = document.querySelector('#pbk-page');
              if (!p) return null;
              const root = p.getBoundingClientRect();
              let visualRight = Math.max(p.clientWidth || 0, p.scrollWidth || 0);
              let visualBottom = Math.max(p.clientHeight || 0, p.scrollHeight || 0);
              for (const node of p.querySelectorAll('canvas,img,svg,object,embed')) {
                const style = getComputedStyle(node);
                if (style.display === 'none' || style.visibility === 'hidden') continue;
                const box = node.getBoundingClientRect();
                if (box.width <= 1 || box.height <= 1) continue;
                visualRight = Math.max(visualRight, box.right - root.left);
                visualBottom = Math.max(visualBottom, box.bottom - root.top);
              }
              return {
                clientWidth: Math.round(p.clientWidth || root.width || 0),
                clientHeight: Math.round(p.clientHeight || root.height || 0),
                scrollWidth: Math.round(p.scrollWidth || 0),
                scrollHeight: Math.round(p.scrollHeight || 0),
                visualRight: Math.round(visualRight),
                visualBottom: Math.round(visualBottom),
              };
            }"""
        )
    except Exception:
        return None
    return result if isinstance(result, Mapping) else None


def _fit_height(page: Any) -> bool:
    candidates = [
        page.get_by_role("button", name=re.compile("Preferências do leitor|Aa", re.I)).first,
        page.locator('[aria-label*="Preferências"], [title*="Preferências"]').first,
    ]
    for control in candidates:
        try:
            control.click(timeout=5000)
            page.get_by_text(re.compile("Ajustar-se à altura", re.I)).first.click(timeout=5000)
            page.keyboard.press("Escape")
            page.wait_for_timeout(1000)
            return True
        except Exception:
            continue
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    return False


def _reader_ready(page: Any) -> bool:
    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception:
        body = ""
    if _manual_access_text(body, page.url):
        return False
    return bool(
        "Ir para Página" in body
        or ("Sumário" in body and "Pesquisar em todo o livro" in body)
        or any(_word_count(_reader_text(frame)) >= 20 for frame in page.frames)
    )


def _assert_reader_access(page: Any) -> None:
    try:
        body = page.locator("body").inner_text(timeout=1000)
    except Exception:
        body = ""
    if _manual_access_text(body, page.url):
        raise BookAcquisitionError(
            "reader_manual_intervention_required", "manual_intervention"
        )


def _wait_for_captcha(page: Any) -> None:
    try:
        body = page.locator("body").inner_text(timeout=3000)
    except Exception:
        body = ""
    if not re.search(r"captcha|verify.*human|cloudflare|turnstile", f"{body}\n{page.url}", re.I):
        return
    for _ in range(45):
        page.wait_for_timeout(1000)
        try:
            body = page.locator("body").inner_text(timeout=3000)
        except Exception:
            body = ""
        if not re.search(r"captcha|verify.*human|cloudflare|turnstile", f"{body}\n{page.url}", re.I):
            return
    raise BookAcquisitionError(
        "browserbase_captcha_timeout", "manual_intervention"
    )


def _sophia_authenticated(page: Any) -> bool:
    try:
        body = _normalize_text(page.locator("body").inner_text(timeout=10_000))
    except Exception:
        return False
    return bool(body) and (
        not re.search(r"(^|\s)Entrar(\s|$)", body, re.I)
        or bool(re.search(r"Sair|Minha conta|Meus dados", body, re.I))
    )


def _login_sophia(page: Any, credentials: LibraryCredentials) -> None:
    opened = page.evaluate(
        "() => { if(typeof window.abrirPopupLogin==='function'){window.abrirPopupLogin();return true;}return false;}"
    )
    if not opened:
        page.get_by_role("button", name=re.compile("entrar", re.I)).first.click(timeout=10_000)
    login_frame = None
    for _ in range(30):
        for frame in page.frames:
            if "/login/loginModal" in frame.url:
                login_frame = frame
                break
        if login_frame is not None:
            break
        page.wait_for_timeout(1000)
    if login_frame is None:
        raise BookAcquisitionError("sophia_login_form_missing", "manual_intervention")
    login_frame.locator("#login-identificacao").fill(credentials.username, timeout=30_000)
    login_frame.locator("#login-senha").fill(credentials.password, timeout=30_000)
    login_frame.locator('button[type="submit"], input[type="submit"]').first.click(timeout=30_000)
    page.wait_for_timeout(4000)
    _wait_for_captcha(page)
    if not _sophia_authenticated(page):
        raise BookAcquisitionError("sophia_login_failed", "manual_intervention")


def _search_sophia(page: Any, resource_code: str) -> None:
    field = page.locator("#PalavraChave")
    field.fill(resource_code, timeout=30_000)
    field.press("Enter")
    page.wait_for_timeout(2000)


def _extract_sophia_code(html: str, resource_code: str) -> str:
    normalized = str(html or "").replace("&quot;", '"').replace("&#34;", '"')
    pattern = re.compile(r'\{[^{}]*"Codigo"\s*:\s*(\d+)[^{}]*"URL"\s*:\s*"([^"]+)"[^{}]*\}')
    for match in pattern.finditer(normalized):
        if f"/books/{resource_code}" in match.group(2):
            return match.group(1)
    index = normalized.find(f"/books/{resource_code}")
    if index >= 0:
        local = normalized[max(0, index - 800) : index + 800]
        match = re.search(r'"Codigo"\s*:\s*(\d+)', local)
        if match:
            return match.group(1)
    return ""


def _sophia_sso_url(terminal_url: str, code: str) -> str:
    parts = urlsplit(terminal_url)
    match = re.match(r"^(/terminal/\d+)", parts.path)
    base = match.group(1) if match else "/terminal/9418"
    return urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            f"{base}/IntegracaoDigital/ExecutarSingleSignOn",
            f"codigoSubcampo={code}",
            "",
        )
    )


def _fetch_reader_url(request: Any, sso_url: str, resource_code: str) -> str:
    for attempt in range(3):
        response = request.get(sso_url, timeout=60_000)
        if response.ok:
            candidate = _extract_url_candidate(response.text()) or _extract_url_candidate(
                str(getattr(response, "url", ""))
            )
            if _allowed_reader_handoff(candidate, resource_code):
                return candidate
        if attempt < 2:
            time.sleep(1.5 * (attempt + 1))
    raise BookAcquisitionError("sophia_sso_failed", "manual_intervention")


def _extract_url_candidate(value: str) -> str:
    text = str(value or "").strip()
    if re.match(r"^https?://", text, re.I):
        return re.sub(r"[),.;]+$", "", text)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if payload is not None:
        found = _find_url(payload)
        if found:
            return found
    match = re.search(
        r"https://[a-z0-9.-]*minhabiblioteca\.com\.br/[^\s\"'<>\\]+",
        text.replace("\\/", "/").replace("&amp;", "&"),
        re.I,
    )
    return re.sub(r"[),.;]+$", "", match.group(0)) if match else ""


def _find_url(value: Any) -> str:
    if isinstance(value, str):
        return _extract_url_candidate(value)
    if isinstance(value, list):
        for item in value:
            found = _find_url(item)
            if found:
                return found
    if isinstance(value, dict):
        for item in value.values():
            found = _find_url(item)
            if found:
                return found
    return ""


def _allowed_reader_handoff(url: str, resource_code: str) -> bool:
    parts = urlsplit(str(url or ""))
    return bool(
        (parts.hostname == "integrada.minhabiblioteca.com.br" and f"/books/{resource_code}" in parts.path)
        or (parts.hostname == "jigsaw.minhabiblioteca.com.br" and parts.path.startswith("/auth/redirects/"))
    )


def _validate_completed_prefix(
    completed: Sequence[CompletedBookPage], labels: Sequence[str]
) -> None:
    if len(completed) > len(labels):
        raise BookAcquisitionError("book_page_conflict", "capture_conflict")
    for ordinal, page in enumerate(completed, 1):
        if page.ordinal != ordinal or page.printed_page_label != labels[ordinal - 1]:
            raise BookAcquisitionError("book_page_conflict", "capture_conflict")


def _next_reader_id(value: str) -> str:
    return str(int(value) + 1) if str(value or "").isdigit() else ""


def _reader_page_id(url: str) -> str:
    match = re.search(r"/pageid/([^/?#]+)", str(url or ""))
    return match.group(1) if match else ""


def _is_reader_url(url: str, resource_code: str) -> bool:
    parts = urlsplit(str(url or ""))
    return bool(
        parts.hostname == "integrada.minhabiblioteca.com.br"
        and f"/reader/books/{resource_code}" in parts.path
    )


def _manual_access_text(body: str, url: str) -> bool:
    parts = urlsplit(str(url or ""))
    if parts.hostname == "login.vitalsource.com":
        return True
    text = _normalize_text(body)
    if "Ir para Página" in text:
        return False
    return bool(re.search(r"entrar|login|senha|captcha|mfa|access denied|n[aã]o tem acesso", text, re.I))


def _intentional_blank(text: str) -> bool:
    return bool(re.search(r"p[aá]gina foi deixada em branco intencionalmente", text, re.I))


def _normalize_text(value: str) -> str:
    return re.sub(
        r"\n{3,}",
        "\n\n",
        re.sub(r"[ \t]+\n", "\n", str(value or "").replace("\r\n", "\n")),
    ).strip()


def _word_count(value: str) -> int:
    return len(_normalize_text(value).split())


def _public_url(value: str) -> str:
    parts = urlsplit(str(value or "").strip())
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        return ""
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def safe_browser_error(value: object) -> str:
    message = str(value or "")
    message = re.sub(r"wss?://\S+", "[redacted browser transport]", message)
    message = re.sub(
        r"https?://[^\s'\"<>]+",
        lambda match: _public_url(match.group(0)) or "[redacted URL]",
        message,
    )
    message = re.sub(r"(?i)(token|key|secret|password)=[^\s&]+", r"\1=[redacted]", message)
    return message[:500]


def _manual_access_error(exc: Exception) -> bool:
    return bool(
        re.search(
            r"login|captcha|mfa|password|access denied|manual intervention",
            safe_browser_error(exc),
            re.I,
        )
    )


def _safe_event(event: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "kind",
        "provider",
        "stage",
        "attempt",
        "status_code",
        "failure_kind",
        "retry_after_seconds",
        "lock_backend",
        "wait_seconds",
    }
    return {key: event[key] for key in allowed if key in event}


def _env_flag(name: str) -> bool:
    return os.getenv(name, "0").strip().lower() not in {"", "0", "false", "no", "off"}


def _read_context_id(path: Path) -> str:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ""
    return str(payload.get("context_id") or "").strip() if isinstance(payload, dict) else ""


def _write_context_id(path: Path, context_id: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps({"context_id": context_id}, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)
