#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import unicodedata
from typing import Any
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_PATH = SCRIPT_DIR / "url.json"
DEFAULT_OUTPUT_ROOT = SCRIPT_DIR / "output"
DEFAULT_CACHE_ROOT = SCRIPT_DIR / "cache"
DEFAULT_SOPHIA_TERMINAL_URL = "https://philos.sophia.com.br/terminal/9418"
DEFAULT_BROWSERBASE_REGION = "us-west-2"
DEFAULT_BROWSERBASE_TIMEOUT_SECONDS = 3600
SCOPE_PROMPT_VERSION = "book_scope_deepseek_v1"
CAPTURE_VERSION = "browserbase_book_capture_v2"


SCOPE_SYSTEM_PROMPT = """You normalize workbook Assigned Scope text.

The user message is a book self-study description.
Return JSON only with:
- status: proposed_scope or needs_human_scope
- kind: one of pages, chapters, sections, exercises, mixed
- value: only the acquisition range, not a summary
- reason: optional short reason when status is needs_human_scope

For book-library sources, write acquisition-oriented values such as
"pages 25, 43, 51, 54" or "pages 42-55; exercises 7-10".
Hyphen/dash page notation means an inclusive range. If the intended scope is
only two endpoint pages, write a page list such as "pages 103, 116".
When the description names exercise-page pairs, preserve the mapping for each
pair, such as "exercise 4 page 18" or "page 18 exercise 4".
Do not infer page ranges from title or outside book knowledge.
If no usable concrete scope is present, return:
{"status":"needs_human_scope","kind":"","value":"","reason":"missing concrete pages"}.
"""


class AcquisitionFailure(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        retriable: bool = False,
        gate_failures: list[str] | None = None,
        needs_manual: bool = False,
    ) -> None:
        super().__init__(message)
        self.retriable = retriable
        self.gate_failures = gate_failures or []
        self.needs_manual = needs_manual


@dataclass(frozen=True)
class BookRef:
    id: str
    title: str
    resource_code: str
    description: str
    url: str = DEFAULT_SOPHIA_TERMINAL_URL


@dataclass(frozen=True)
class ScopeResult:
    status: str
    kind: str
    value: str
    reason: str = ""
    source: str = "deepseek"


@dataclass(frozen=True)
class LibraryCredentials:
    username: str
    password: str
    terminal_url: str = DEFAULT_SOPHIA_TERMINAL_URL


@dataclass(frozen=True)
class PageCapture:
    page_index: int
    requested_label: str
    reader_pageid: str
    image: str
    markdown: str
    text_sha256: str
    reader_word_count: int


@dataclass
class CaptureBundle:
    status: str
    final_url: str
    source_identity: dict[str, Any]
    pages: list[PageCapture]
    warnings: list[str] = field(default_factory=list)
    blocking_errors: list[str] = field(default_factory=list)


@dataclass
class Result:
    book_id: str
    title: str
    resource_code: str
    status: str
    output_path: str | None = None
    artifact_dir: str | None = None
    cache_key: str | None = None
    warning_flags: list[str] = field(default_factory=list)
    gate_failures: list[str] = field(default_factory=list)
    error: str | None = None
    page_count: int = 0
    source: str = "unknown"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def atomic_write_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_bytes(payload)
    tmp_path.replace(path)


def slugify(value: str, max_length: int = 90) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug[:max_length].rstrip("-") or "book")


def stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def parse_only_ids(value: str | None) -> set[str] | None:
    if not value:
        return None
    ids = {part.strip() for part in value.split(",") if part.strip()}
    if not ids:
        raise ValueError("--only must include at least one id")
    return ids


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"JSON file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"JSON file is not valid: {path}: {exc}") from exc


def load_books(input_path: Path, only_ids: set[str] | None) -> tuple[list[BookRef], set[str]]:
    raw = load_json(input_path)
    if not isinstance(raw, list):
        raise SystemExit(f"Input JSON must be a list of objects: {input_path}")

    books: list[BookRef] = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Input item #{idx} is not an object")
        missing = [
            key
            for key in ("id", "title", "resource_code", "description")
            if key not in item
        ]
        if missing:
            raise SystemExit(f"Input item #{idx} is missing keys: {', '.join(missing)}")

        book_id = str(item["id"]).strip()
        title = str(item["title"]).strip()
        resource_code = str(item["resource_code"]).strip()
        description = str(item["description"]).strip()
        url = str(item.get("url") or DEFAULT_SOPHIA_TERMINAL_URL).strip()
        if not book_id or not title or not resource_code or not description:
            raise SystemExit(
                f"Input item #{idx} has blank id, title, resource_code, or description"
            )
        seen_ids.add(book_id)
        if only_ids is None or book_id in only_ids:
            books.append(
                BookRef(
                    id=book_id,
                    title=title,
                    resource_code=resource_code,
                    description=description,
                    url=url,
                )
            )

    missing_requested = only_ids - seen_ids if only_ids is not None else set()
    return books, missing_requested


def requested_page_labels(scope_value: str) -> list[str]:
    value = str(scope_value or "").strip()
    page_word = r"(?:p[aá]g\.?(?:ina)?|pagina|page|p\.)s?"
    segmented_page_labels: list[int] = []
    for segment in split_scope_segments(value):
        if not re.search(
            r"\b(?:exerc[ií]cio|exercicio|exercise|ex\.)",
            segment,
            flags=re.IGNORECASE,
        ):
            continue
        page_match = re.search(
            rf"\b{page_word}\s*(?:n[ºo.]?\s*)?(\d+)\b",
            segment,
            flags=re.IGNORECASE,
        )
        if page_match:
            segmented_page_labels.append(int(page_match.group(1)))
    if segmented_page_labels:
        return dedupe_page_labels(segmented_page_labels)

    paired_pages = re.findall(
        r"\b(?:exerc[ií]cio|exercicio|exercise|ex\.)s?\s*(?:n[ºo.]?\s*)?\d+"
        rf"\D{{0,80}}?\b{page_word}\s*(?:n[ºo.]?\s*)?(\d+)\b",
        value,
        flags=re.IGNORECASE,
    )
    if paired_pages:
        return dedupe_page_labels(int(page) for page in paired_pages)

    page_labels: list[int] = []
    for segment in split_scope_segments(value):
        if not re.search(rf"\b{page_word}\b", segment, flags=re.IGNORECASE):
            continue
        page_list_match = re.search(
            rf"\b{page_word}\s*(?:n[ºo.]?\s*)?"
            r"(?P<pages>\d+(?:\s*(?:,|e|and)\s*\d+)*"
            r"(?:\s*(?:-|a|até|to|through|\u2010|\u2011|\u2012|\u2013|\u2014|\u2212)\s*\d+)?)",
            segment,
            flags=re.IGNORECASE,
        )
        if not page_list_match:
            continue
        pages_text = page_list_match.group("pages")
        range_match = re.search(
            r"\b(\d+)\s*(?:-|a|até|to|through|\u2010|\u2011|\u2012|\u2013|\u2014|\u2212)\s*(\d+)\b",
            pages_text,
            flags=re.IGNORECASE,
        )
        if range_match:
            start, end = int(range_match.group(1)), int(range_match.group(2))
            if start <= end and end - start <= 300:
                page_labels.extend(range(start, end + 1))
            continue
        page_labels.extend(int(match) for match in re.findall(r"\d+", pages_text))
    return dedupe_page_labels(page_labels)


def split_scope_segments(value: str) -> list[str]:
    return [
        segment
        for segment in re.split(
            r";|\n|,(?=\s*(?:exerc[ií]cio|exercicio|exercise|ex\.))",
            value,
            flags=re.IGNORECASE,
        )
        if segment.strip()
    ]


def dedupe_page_labels(labels: Any) -> list[str]:
    deduped: list[str] = []
    seen: set[int] = set()
    for label in labels:
        label_int = int(label)
        if label_int <= 0 or label_int in seen:
            continue
        seen.add(label_int)
        deduped.append(str(label_int))
    return deduped


class DeepSeekScopeNormalizer:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.deepseek.com",
    ) -> None:
        load_dotenv(SCRIPT_DIR.parent / ".env")
        load_dotenv()
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY_ADMIN", "").strip()
        self.model = model or os.environ.get("DEEPSEEK_MODEL", "").strip() or "deepseek-chat"
        self.base_url = base_url
        if not self.api_key:
            raise AcquisitionFailure(
                "Required environment variable DEEPSEEK_API_KEY_ADMIN is not set",
                needs_manual=True,
            )

    def normalize(self, book: BookRef) -> ScopeResult:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise AcquisitionFailure("The openai package is required for DeepSeek") from exc

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": SCOPE_SYSTEM_PROMPT},
                {"role": "user", "content": book.description},
            ],
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content or ""
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AcquisitionFailure(f"DeepSeek returned invalid scope JSON: {text[:200]!r}") from exc
        if not isinstance(payload, dict):
            raise AcquisitionFailure("DeepSeek scope JSON was not an object")
        result = ScopeResult(
            status=str(payload.get("status") or "").strip() or "needs_human_scope",
            kind=str(payload.get("kind") or "").strip(),
            value=str(payload.get("value") or "").strip(),
            reason=str(payload.get("reason") or "").strip(),
        )
        if result.status == "needs_human_scope" or not result.kind or not result.value:
            raise AcquisitionFailure(
                f"DeepSeek could not determine concrete pages for {book.id}: {result.reason}",
                needs_manual=True,
                gate_failures=["missing_concrete_scope"],
            )
        if not requested_page_labels(result.value):
            raise AcquisitionFailure(
                f"Normalized scope does not contain concrete page labels: {result.value}",
                needs_manual=True,
                gate_failures=["missing_page_labels"],
            )
        return result


class BrowserbaseBookAcquirer:
    def __init__(
        self,
        *,
        api_key: str | None = None,
        project_id: str | None = None,
        context_id: str | None = None,
        context_file: Path | None = None,
        region: str = DEFAULT_BROWSERBASE_REGION,
        timeout_seconds: int = DEFAULT_BROWSERBASE_TIMEOUT_SECONDS,
        viewport_width: int = 2200,
        viewport_height: int = 1800,
        credentials: LibraryCredentials | None = None,
    ) -> None:
        load_dotenv(SCRIPT_DIR.parent / ".env")
        load_dotenv()
        self.api_key = api_key or os.environ.get("BROWSERBASE_API_KEY", "").strip()
        self.project_id = project_id or os.environ.get("BROWSERBASE_PROJECT_ID", "").strip()
        self.context_id = context_id or os.environ.get("BROWSERBASE_CONTEXT_ID", "").strip()
        configured_context_file = os.environ.get("CG_PIPELINE_BROWSERBASE_CONTEXT_FILE", "").strip()
        self.context_file = (
            context_file
            or (Path(configured_context_file) if configured_context_file else SCRIPT_DIR / "browserbase_context.json")
        )
        self.region = region
        self.timeout_seconds = timeout_seconds
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.credentials = credentials or library_credentials_from_env()
        if not self.api_key:
            raise AcquisitionFailure(
                "Required environment variable BROWSERBASE_API_KEY is not set",
                needs_manual=True,
            )

    def capture(
        self,
        *,
        book: BookRef,
        scope: ScopeResult,
        requested_pages: list[str],
        artifact_dir: Path,
    ) -> CaptureBundle:
        warnings: list[str] = []
        source_identity: dict[str, Any] | None = None
        pages = load_partial_page_captures(artifact_dir, requested_pages)
        session_restarts = 0
        while len(pages) < len(requested_pages):
            browser = None
            playwright = None
            try:
                session, browser, playwright = self._connect()
                del session
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                page = open_reader(context, book, self.credentials)
                page.set_viewport_size(
                    {"width": self.viewport_width, "height": self.viewport_height}
                )
                if not configure_reader_fit_height(page):
                    warnings.append("reader_fit_height_not_confirmed")
                if source_identity is None:
                    source_identity = source_identity_from_page(page, book)
                pages = load_partial_page_captures(artifact_dir, requested_pages)
                start_index = len(pages) + 1
                capture_requested_pages(
                    page,
                    book=book,
                    requested_pages=requested_pages[start_index - 1 :],
                    artifact_dir=artifact_dir,
                    warnings=warnings,
                    start_index=start_index,
                )
                pages = load_partial_page_captures(artifact_dir, requested_pages)
                final_url = page.url
                if len(pages) >= len(requested_pages):
                    return CaptureBundle(
                        status="fetched_with_warnings" if warnings else "fetched",
                        final_url=final_url,
                        source_identity=source_identity or source_identity_from_book(book),
                        pages=pages,
                        warnings=warnings,
                    )
            except AcquisitionFailure:
                raise
            except Exception as exc:
                pages = load_partial_page_captures(artifact_dir, requested_pages)
                if (
                    is_retriable_browserbase_disconnect(str(exc))
                    and session_restarts < 4
                ):
                    session_restarts += 1
                    warnings.append(
                        f"browserbase_session_restarted_after_page_{len(pages):04d}"
                    )
                    continue
                raise AcquisitionFailure(
                    str(exc),
                    gate_failures=["browserbase_capture_failed"],
                    needs_manual=is_manual_access_message(str(exc)),
                ) from exc
            finally:
                if browser is not None:
                    try:
                        browser.close()
                    except Exception:
                        pass
                if playwright is not None:
                    try:
                        playwright.stop()
                    except Exception:
                        pass
        raise AcquisitionFailure(
            "Browserbase capture ended before all requested pages were captured",
            gate_failures=["browserbase_capture_incomplete"],
        )

    def _connect(self) -> tuple[Any, Any, Any]:
        try:
            from browserbase import Browserbase
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise AcquisitionFailure(
                "Browserbase acquisition requires the browserbase and playwright packages",
                needs_manual=True,
            ) from exc

        browserbase = Browserbase(api_key=self.api_key)
        context_id = self._context_id(browserbase)
        session_kwargs: dict[str, Any] = {
            "region": self.region,
            "timeout": self.timeout_seconds,
            "keep_alive": False,
            "browser_settings": {
                "viewport": {
                    "width": self.viewport_width,
                    "height": self.viewport_height,
                },
                "context": {
                    "id": context_id,
                    "persist": True,
                },
            },
        }
        if self.project_id:
            session_kwargs["project_id"] = self.project_id
        session = browserbase.sessions.create(**session_kwargs)
        playwright = sync_playwright().start()
        browser = playwright.chromium.connect_over_cdp(session.connect_url)
        return session, browser, playwright

    def _context_id(self, browserbase: Any) -> str:
        if self.context_id:
            return self.context_id
        context_id = read_context_id(self.context_file)
        if context_id:
            self.context_id = context_id
            return context_id
        context = browserbase.contexts.create()
        context_id = str(context.id)
        write_context_id(self.context_file, context_id)
        self.context_id = context_id
        return context_id


def is_retriable_browserbase_disconnect(message: str) -> bool:
    return bool(
        re.search(
            r"Target page, context or browser has been closed|Browser has been closed|"
            r"Connection closed|WebSocket|ECONNRESET|Session.*closed",
            str(message or ""),
            re.I,
        )
    )


def load_partial_page_captures(
    artifact_dir: Path,
    requested_pages: list[str],
) -> list[PageCapture]:
    captures: list[PageCapture] = []
    for page_index, requested_label in enumerate(requested_pages, start=1):
        page_name = f"page_{page_index:04d}"
        image_path = artifact_dir / "evidence" / f"{page_name}.png"
        markdown_path = artifact_dir / "pages" / f"{page_name}.md"
        if not image_path.exists() or not markdown_path.exists():
            break
        page_text = markdown_path.read_text(encoding="utf-8").rstrip("\n")
        reader_pageid_match = re.search(r"^Reader pageid:\s*(.+)$", page_text, re.M)
        reader_text_match = re.search(r"^### Reader text\n\n(.*)$", page_text, re.S | re.M)
        reader_text = reader_text_match.group(1).strip() if reader_text_match else page_text
        captures.append(
            PageCapture(
                page_index=page_index,
                requested_label=requested_label,
                reader_pageid=reader_pageid_match.group(1).strip()
                if reader_pageid_match
                else "",
                image=str(image_path.relative_to(artifact_dir)),
                markdown=str(markdown_path.relative_to(artifact_dir)),
                text_sha256=hashlib.sha256(page_text.encode("utf-8")).hexdigest(),
                reader_word_count=word_count(reader_text),
            )
        )
    return captures


def library_credentials_from_env() -> LibraryCredentials:
    file_credentials = library_credentials_from_file()
    if file_credentials is not None:
        return file_credentials
    openclaw_credentials = library_credentials_from_openclaw_provider()
    if openclaw_credentials is not None:
        return openclaw_credentials

    username = (
        os.environ.get("CG_PIPELINE_LIBRARY_USERNAME", "").strip()
        or os.environ.get("LIBRARY_USERNAME", "").strip()
    )
    password = (
        os.environ.get("CG_PIPELINE_LIBRARY_PASSWORD", "").strip()
        or os.environ.get("LIBRARY_PASSWORD", "").strip()
    )
    terminal_url = (
        os.environ.get("SOPHIA_TERMINAL_URL", "").strip()
        or DEFAULT_SOPHIA_TERMINAL_URL
    )
    if not username or not password:
        raise AcquisitionFailure(
            "Library credentials require CG_PIPELINE_LIBRARY_USERNAME/CG_PIPELINE_LIBRARY_PASSWORD, "
            "CG_PIPELINE_LIBRARY_CREDENTIALS_FILE, or an OpenClaw concept_graph_library provider",
            needs_manual=True,
        )
    return LibraryCredentials(username=username, password=password, terminal_url=terminal_url)


def library_credentials_from_file(path: Path | None = None) -> LibraryCredentials | None:
    configured_path = path or env_path("CG_PIPELINE_LIBRARY_CREDENTIALS_FILE")
    if configured_path is None:
        return None
    return credentials_from_json_file(configured_path, provider_name=str(configured_path))


def library_credentials_from_openclaw_provider(
    provider_name: str | None = None,
    config_path: Path | None = None,
) -> LibraryCredentials | None:
    provider_name = (
        provider_name
        or os.environ.get("CG_PIPELINE_LIBRARY_SECRET_PROVIDER", "").strip()
        or "concept_graph_library"
    )
    config_path = config_path or env_path("OPENCLAW_CONFIG_PATH") or Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return None
    payload = load_json(config_path)
    if not isinstance(payload, dict):
        return None
    providers = payload.get("secrets", {}).get("providers", {})
    provider = providers.get(provider_name) if isinstance(providers, dict) else None
    if not isinstance(provider, dict):
        return None
    if provider.get("source") != "file" or provider.get("mode") != "json":
        raise AcquisitionFailure(
            f"Secret provider {provider_name} must be a JSON file provider for library access",
            needs_manual=True,
        )
    provider_path = str(provider.get("path") or "").strip()
    if not provider_path:
        raise AcquisitionFailure(
            f"Secret provider {provider_name} is missing a file path",
            needs_manual=True,
        )
    secret_path = expand_home_path(provider_path)
    max_bytes = int(provider.get("maxBytes") or 8192)
    if secret_path.stat().st_size > max_bytes:
        raise AcquisitionFailure(
            f"Secret provider {provider_name} exceeds its configured size limit",
            needs_manual=True,
        )
    return credentials_from_json_file(secret_path, provider_name=provider_name)


def credentials_from_json_file(path: Path, *, provider_name: str) -> LibraryCredentials:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise AcquisitionFailure(
            f"Library credential provider {provider_name} must contain a JSON object",
            needs_manual=True,
        )
    username = first_non_empty(
        payload.get("CG_PIPELINE_LIBRARY_USERNAME"),
        payload.get("LIBRARY_USERNAME"),
        payload.get("username"),
        payload.get("login"),
        payload.get("identificacao"),
    )
    password = first_non_empty(
        payload.get("CG_PIPELINE_LIBRARY_PASSWORD"),
        payload.get("LIBRARY_PASSWORD"),
        payload.get("password"),
        payload.get("senha"),
    )
    terminal_url = first_non_empty(payload.get("SOPHIA_TERMINAL_URL")) or DEFAULT_SOPHIA_TERMINAL_URL
    if not username or not password:
        raise AcquisitionFailure(
            f"Library credential provider {provider_name} is missing username/password fields",
            needs_manual=True,
        )
    return LibraryCredentials(username=username, password=password, terminal_url=terminal_url)


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def env_path(name: str) -> Path | None:
    value = os.environ.get(name, "").strip()
    return expand_home_path(value) if value else None


def expand_home_path(value: str) -> Path:
    return Path(value).expanduser()


def read_context_id(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("context_id", "")).strip() if isinstance(payload, dict) else ""


def write_context_id(path: Path, context_id: str) -> None:
    atomic_write_text(path, json.dumps({"context_id": context_id}, indent=2) + "\n")


def open_reader(context: Any, book: BookRef, credentials: LibraryCredentials) -> Any:
    for candidate in list(context.pages):
        if is_reader_book_page(candidate.url, book.resource_code):
            candidate.bring_to_front()
            if reader_is_authenticated(candidate):
                return candidate
    page = open_reader_through_sophia(context, book, credentials)
    if not reader_is_authenticated(page):
        if reader_access_denied(page):
            raise AcquisitionFailure(
                "Reader access denied for this book",
                needs_manual=True,
                gate_failures=["manual_access_required"],
            )
        raise AcquisitionFailure(
            "Reader requires manual login, MFA, CAPTCHA, or renewed access",
            needs_manual=True,
            gate_failures=["manual_access_required"],
        )
    if not is_reader_book_page(page.url, book.resource_code):
        raise AcquisitionFailure(
            "Sophia SSO did not open the expected Minha Biblioteca reader",
            needs_manual=True,
            gate_failures=["wrong_reader_url"],
        )
    return page


def open_reader_through_sophia(
    context: Any,
    book: BookRef,
    credentials: LibraryCredentials,
) -> Any:
    sophia_page = open_sophia_terminal(context, credentials.terminal_url or book.url)
    ensure_sophia_authenticated(sophia_page, credentials)
    search_sophia_resource(sophia_page, book.resource_code)
    subfield_code = extract_sophia_subfield_code(
        sophia_page.locator("body").inner_html(timeout=30000),
        book.resource_code,
    )
    if not subfield_code:
        raise AcquisitionFailure(
            f"Sophia did not expose a Minha Biblioteca SSO result for {book.resource_code}",
            needs_manual=True,
            gate_failures=["sophia_missing_sso_result"],
        )
    reader_url = fetch_sophia_reader_url_with_retry(
        context.request,
        sophia_sso_url(credentials.terminal_url or book.url, subfield_code),
        book.resource_code,
    )
    reader_page = context.new_page()
    reader_page.goto(reader_url, wait_until="domcontentloaded", timeout=60000)
    reader_page.wait_for_timeout(3000)
    return reader_page


def open_sophia_terminal(context: Any, terminal_url: str) -> Any:
    existing_pages = [page for page in list(context.pages) if is_sophia_terminal_url(page.url)]
    for candidate in existing_pages:
        if sophia_appears_authenticated(candidate):
            candidate.bring_to_front()
            try:
                candidate.locator("#PalavraChave").wait_for(timeout=5000)
            except Exception:
                candidate.goto(terminal_url, wait_until="domcontentloaded", timeout=60000)
                candidate.locator("#PalavraChave").wait_for(timeout=30000)
            return candidate
    page = existing_pages[0] if existing_pages else context.new_page()
    page.bring_to_front()
    page.goto(terminal_url, wait_until="domcontentloaded", timeout=60000)
    page.locator("#PalavraChave").wait_for(timeout=30000)
    return page


def ensure_sophia_authenticated(page: Any, credentials: LibraryCredentials) -> None:
    if sophia_appears_authenticated(page):
        return
    open_sophia_login_modal(page)
    login_frame = wait_for_sophia_login_frame(page)
    login_frame.locator("#login-identificacao").fill(credentials.username, timeout=30000)
    login_frame.locator("#login-senha").fill(credentials.password, timeout=30000)
    login_frame.locator('button[type="submit"], input[type="submit"]').first.click(
        timeout=30000
    )
    page.wait_for_timeout(2000)
    if any("/login/loginModal" in frame.url for frame in page.frames):
        try:
            login_frame.locator("#login-senha").press("Enter", timeout=10000)
        except Exception:
            pass
    try:
        page.wait_for_function(
            "() => !document.querySelector('iframe[src*=\"loginModal\"]')",
            timeout=30000,
        )
    except Exception:
        pass
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(2000)
    if not sophia_appears_authenticated(page):
        raise AcquisitionFailure(
            "Sophia login did not complete or requires manual access",
            needs_manual=True,
            gate_failures=["sophia_login_failed"],
        )


def sophia_appears_authenticated(page: Any) -> bool:
    try:
        body_text = normalize_text(page.locator("body").inner_text(timeout=10000))
    except Exception:
        return False
    if not body_text:
        return False
    if re.search(r"captcha|mfa|c[oó]digo de verifica[cç][aã]o", body_text, re.I):
        raise AcquisitionFailure(
            "Sophia login requires manual verification",
            needs_manual=True,
            gate_failures=["sophia_manual_verification"],
        )
    return not re.search(r"(^|\n|\s)Entrar(\s|\n|$)", body_text, re.I) or bool(
        re.search(r"Sair|Minha conta|Meus dados", body_text, re.I)
    )


def open_sophia_login_modal(page: Any) -> None:
    opened = page.evaluate(
        "() => { if (typeof window.abrirPopupLogin === 'function') { "
        "window.abrirPopupLogin(); return true; } return false; }"
    )
    if not opened:
        page.get_by_role("button", name=re.compile("entrar", re.I)).first.click(timeout=10000)


def wait_for_sophia_login_frame(page: Any) -> Any:
    for _ in range(30):
        for frame in page.frames:
            if "/login/loginModal" in frame.url:
                frame.locator("#login-identificacao").wait_for(timeout=10000)
                frame.locator("#login-senha").wait_for(timeout=10000)
                return frame
        page.wait_for_timeout(1000)
    raise AcquisitionFailure(
        "Sophia login modal did not expose the expected fields",
        needs_manual=True,
        gate_failures=["sophia_login_form_missing"],
    )


def search_sophia_resource(page: Any, resource_code: str) -> None:
    previous_url = page.url
    page.locator("#PalavraChave").fill(resource_code, timeout=30000)
    page.locator("#PalavraChave").press("Enter")
    try:
        page.wait_for_function(
            "({code, previous}) => window.location.href !== previous || "
            "document.body.innerText.includes(code) || "
            "document.querySelector('.btn-conteudo-digital')",
            {"code": resource_code, "previous": previous_url},
            timeout=30000,
        )
    except Exception:
        pass
    try:
        page.wait_for_load_state("domcontentloaded", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(1500)


def reader_is_authenticated(page: Any) -> bool:
    page.wait_for_timeout(3000)
    try:
        body_text = page.locator("body").inner_text(timeout=10000)
    except Exception:
        body_text = ""
    if reader_needs_manual_access(body_text, page.url):
        return False
    if reader_shell_loaded(body_text):
        return True
    try:
        page.locator("input").first.wait_for(timeout=30000)
        return True
    except Exception:
        return any(epub_content_frame_text(frame) for frame in page.frames)


def reader_access_denied(page: Any) -> bool:
    snippets: list[str] = []
    try:
        snippets.append(page.locator("body").inner_text(timeout=3000))
    except Exception:
        pass
    for frame in page.frames:
        try:
            snippets.append(frame.locator("body").inner_text(timeout=1000))
        except Exception:
            pass
    return any(epub_access_denied_text(snippet) for snippet in snippets)


def reader_shell_loaded(body_text: str) -> bool:
    text = normalize_text(body_text)
    return bool(
        "Ir para Página" in text
        or (
            "Sumário" in text
            and "Pesquisar em todo o livro" in text
            and "Voltar à biblioteca" not in text
        )
    )


def configure_reader_fit_height(page: Any) -> bool:
    controls = [
        page.get_by_role("button", name=re.compile("Preferências do leitor|Aa", re.I)).first,
        page.locator('[aria-label*="Preferências"], [title*="Preferências"]').first,
    ]
    for control in controls:
        try:
            control.click(timeout=5000)
            break
        except Exception:
            pass
    try:
        page.get_by_text(re.compile("Ajustar-se à altura", re.I)).first.click(timeout=5000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
        return True
    except Exception:
        try:
            page.keyboard.press("Escape")
        except Exception:
            pass
        return False


def capture_requested_pages(
    page: Any,
    *,
    book: BookRef,
    requested_pages: list[str],
    artifact_dir: Path,
    warnings: list[str],
    start_index: int = 1,
) -> list[PageCapture]:
    evidence_dir = artifact_dir / "evidence"
    pages_dir = artifact_dir / "pages"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_captures: list[PageCapture] = []
    for offset, requested_label in enumerate(requested_pages):
        page_index = start_index + offset
        page_name = f"page_{page_index:04d}"
        image_path = evidence_dir / f"{page_name}.png"
        markdown_path = pages_dir / f"{page_name}.md"

        navigate_to_printed_page(page, requested_label, book_title=book.title)
        reader_pageid = reader_pageid_from_url(page.url)
        page_frame = frame_for_printed_page(page, book.resource_code, requested_label)
        reader_pageid = reader_pageid or reader_pageid_from_url(page_frame.url)
        page_frame = ensure_page_frame_not_horizontally_clipped(
            page,
            page_frame,
            requested_label,
        )
        reader_text = reader_text_from_frame(page_frame)
        screenshot_page_image(page_frame, image_path)
        reader_word_count = word_count(reader_text)
        intentional_blank = is_intentional_blank_page(reader_text)
        if reader_word_count < 20 and not intentional_blank:
            raise AcquisitionFailure(
                f"Page {requested_label} did not produce enough text for reliable extraction",
                needs_manual=True,
                gate_failures=["sparse_reader_text"],
            )
        if intentional_blank:
            warnings.append(f"intentional_blank_page_{page_index:04d}")
        elif reader_word_count < 40:
            warnings.append(f"reader_low_word_count_page_{page_index:04d}")

        page_text = "\n".join(
            [
                f"## Page {requested_label}",
                "",
                f"Reader pageid: {reader_pageid}",
                "",
                "### Reader text",
                "",
                reader_text,
                "",
            ]
        )
        atomic_write_text(markdown_path, page_text + "\n")
        page_captures.append(
            PageCapture(
                page_index=page_index,
                requested_label=requested_label,
                reader_pageid=reader_pageid,
                image=str(image_path.relative_to(artifact_dir)),
                markdown=str(markdown_path.relative_to(artifact_dir)),
                text_sha256=hashlib.sha256(page_text.encode("utf-8")).hexdigest(),
                reader_word_count=reader_word_count,
            )
        )
    return page_captures


def navigate_to_printed_page(page: Any, requested_label: str, *, book_title: str = "") -> None:
    assert_reader_still_accessible(page)
    if navigate_via_table_of_contents(page, requested_label, book_title=book_title):
        return
    page_input = page.locator("input").first
    previous_url = page.url
    try:
        page_input.scroll_into_view_if_needed()
    except Exception:
        pass
    page_input.click(timeout=10000)
    try:
        page_input.press("Control+A")
    except Exception:
        pass
    page_input.fill(requested_label)
    page_input.press("Enter")
    page.wait_for_timeout(2500)
    assert_reader_still_accessible(page)
    try:
        page.wait_for_function(
            "({label, previous}) => { const input = document.querySelector('input'); "
            "return (input && input.value === label) || window.location.href !== previous; }",
            {"label": requested_label, "previous": previous_url},
            timeout=30000,
        )
    except Exception:
        pass
    wait_for_printed_page_frame(page, requested_label)


def navigate_via_table_of_contents(
    page: Any,
    requested_label: str,
    *,
    book_title: str = "",
) -> bool:
    previous_url = page.url
    label_at_end = re.compile(rf"(^|\s){re.escape(requested_label)}$", re.I)
    title_label = toc_title_label_pattern(book_title, requested_label)
    candidates = [
        page.get_by_text(title_label).first if title_label else None,
        page.get_by_role("button", name=title_label).first if title_label else None,
        page.locator("button, [role=button], a").filter(has_text=title_label).first
        if title_label
        else None,
        page.get_by_text(label_at_end).first,
        page.get_by_role(
            "button",
            name=re.compile(rf"p[aá]gina\s+{re.escape(requested_label)}$", re.I),
        ).first,
        page.get_by_role("button", name=label_at_end).first,
        page.locator("button, [role=button], a").filter(has_text=label_at_end).first,
    ]
    for candidate in candidates:
        if candidate is None:
            continue
        try:
            if candidate.count() == 0:
                continue
            candidate.click(timeout=10000)
            try:
                page.wait_for_function(
                    "(previous) => window.location.href !== previous",
                    previous_url,
                    timeout=30000,
                )
            except Exception:
                pass
            page.wait_for_timeout(2500)
            wait_for_printed_page_frame(page, requested_label)
            return True
        except Exception:
            continue
    return False


def toc_title_label_pattern(book_title: str, requested_label: str) -> re.Pattern[str] | None:
    title = re.sub(r"^\(\s*Livro\s*\)\s*", "", str(book_title or ""), flags=re.I).strip()
    title = re.sub(r"\s+", " ", title)
    if len(title) < 4:
        return None
    return re.compile(rf"{re.escape(title)}[\s\S]*{re.escape(requested_label)}", re.I)


def wait_for_printed_page_frame(page: Any, requested_label: str) -> Any:
    for _ in range(30):
        assert_reader_still_accessible(page)
        try:
            return frame_for_printed_page(page, "", requested_label)
        except AcquisitionFailure:
            page.wait_for_timeout(1000)
    raise AcquisitionFailure(
        f"Timed out waiting for requested page {requested_label}",
        needs_manual=True,
        gate_failures=["page_navigation_timeout"],
    )


def assert_reader_still_accessible(page: Any) -> None:
    try:
        body_text = page.locator("body").inner_text(timeout=1000)
    except Exception:
        body_text = ""
    if reader_needs_manual_access(body_text, page.url):
        raise AcquisitionFailure(
            "Reader requires manual login, MFA, CAPTCHA, or renewed access",
            needs_manual=True,
            gate_failures=["manual_access_required"],
        )


def frame_for_printed_page(page: Any, resource_code: str, requested_label: str) -> Any:
    frames = [
        frame
        for frame in page.frames
        if "/pages/" in frame.url and (not resource_code or resource_code in frame.url)
    ]
    candidates: list[tuple[Any, str]] = []
    for frame in frames:
        try:
            text = normalize_text(frame.locator("#pdf-ax-text").inner_text(timeout=3000))
        except Exception:
            text = ""
        if text:
            candidates.append((frame, text))
    for frame, text in candidates:
        if re.search(rf"^{re.escape(requested_label)}(\s|$)", text.strip()):
            return frame
    for frame, text in candidates:
        if re.search(rf"(^|\n|\s){re.escape(requested_label)}(\s|$)", text[:240]):
            return frame
    try:
        input_value = page.locator("input").first.input_value(timeout=3000)
    except Exception:
        input_value = ""
    if input_value == requested_label and candidates:
        return candidates[0][0]
    epub_frame = epub_content_frame(page, resource_code)
    if epub_frame is not None:
        return epub_frame
    raise AcquisitionFailure(
        f"Could not identify reader frame for requested page {requested_label}",
        needs_manual=True,
        gate_failures=["page_frame_not_identified"],
    )


def reader_text_from_frame(frame: Any) -> str:
    try:
        return normalize_text(frame.locator("#pdf-ax-text").inner_text(timeout=3000))
    except Exception:
        return epub_content_frame_text(frame)


def epub_content_frame(page: Any, resource_code: str) -> Any | None:
    for frame in page.frames:
        if f"/books/{resource_code}/epub/" not in frame.url:
            continue
        text = epub_content_frame_text(frame)
        if word_count(text) >= 20 and not epub_access_denied_text(text):
            return frame
    return None


def epub_content_frame_text(frame: Any) -> str:
    try:
        return normalize_text(frame.locator("body").inner_text(timeout=3000))
    except Exception:
        return ""


def epub_access_denied_text(text: str) -> bool:
    return bool(
        re.search(
            r"don't have access|n[aã]o tem acesso|erro de acesso ao livro|sorry, you don't have access",
            normalize_text(text),
            re.I,
        )
    )


def ensure_page_frame_not_horizontally_clipped(
    page: Any,
    frame: Any,
    requested_label: str,
) -> Any:
    current_size = page_viewport_size(page)
    current_width = int(current_size.get("width") or 0)
    current_height = int(current_size.get("height") or 1800)
    candidate_widths = sorted(
        {
            width
            for width in (current_width, 2200, 2600, 3000, 3400)
            if width >= max(current_width, 1)
        }
    )
    last_metrics: dict[str, Any] | None = None
    for width in candidate_widths:
        if width != current_width:
            page.set_viewport_size({"width": width, "height": current_height})
            page.wait_for_timeout(1000)
            configure_reader_fit_height(page)
            frame = wait_for_printed_page_frame(page, requested_label)
            current_width = width
        last_metrics = reader_page_overflow_metrics(frame)
        if not page_overflows_horizontally(last_metrics):
            return frame
    raise AcquisitionFailure(
        (
            f"Page {requested_label} is horizontally clipped in the reader viewport"
            f" (metrics={last_metrics})"
        ),
        gate_failures=["page_image_horizontally_clipped"],
    )


def page_viewport_size(page: Any) -> dict[str, int]:
    try:
        size = page.viewport_size
    except Exception:
        size = None
    if isinstance(size, dict):
        return {
            "width": int(size.get("width") or 0),
            "height": int(size.get("height") or 0),
        }
    return {"width": 0, "height": 1800}


def reader_page_overflow_metrics(frame: Any) -> dict[str, Any] | None:
    try:
        metrics = frame.evaluate(
            """
            () => {
              const page = document.querySelector("#pbk-page");
              if (!page) return null;
              const rect = page.getBoundingClientRect();
              const style = window.getComputedStyle(page);
              return {
                clientWidth: Math.round(page.clientWidth || 0),
                scrollWidth: Math.round(page.scrollWidth || 0),
                scrollLeft: Math.round(page.scrollLeft || 0),
                rectWidth: Math.round(rect.width || 0),
                overflowX: style.overflowX || ""
              };
            }
            """
        )
    except Exception:
        return None
    return metrics if isinstance(metrics, dict) else None


def page_overflows_horizontally(metrics: dict[str, Any] | None) -> bool:
    if not metrics:
        return False
    try:
        client_width = int(metrics.get("clientWidth") or 0)
        scroll_width = int(metrics.get("scrollWidth") or 0)
    except (TypeError, ValueError):
        return False
    return client_width > 0 and scroll_width > client_width + 8


def screenshot_page_image(frame: Any, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_name(f".{output_path.name}.{os.getpid()}.tmp.png")
    if tmp_path.exists():
        tmp_path.unlink()
    image = frame.locator("#pbk-page").first
    try:
        try:
            box = image.bounding_box(timeout=5000)
        except Exception:
            box = None
        if box and box.get("width", 0) > 10 and box.get("height", 0) > 10:
            image.screenshot(path=str(tmp_path))
        else:
            body = frame.locator("body").first
            try:
                body_box = body.bounding_box(timeout=3000)
            except Exception:
                body_box = None
            if body_box and body_box.get("width", 0) > 10 and body_box.get("height", 0) > 10:
                body.screenshot(path=str(tmp_path))
            else:
                frame.page.screenshot(path=str(tmp_path), full_page=False)
        tmp_path.replace(output_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def normalize_text(text: str) -> str:
    return re.sub(
        r"\n{3,}",
        "\n\n",
        re.sub(r"[ \t]+\n", "\n", str(text or "").replace("\r\n", "\n")),
    ).strip()


def word_count(text: str) -> int:
    return len([word for word in normalize_text(text).split() if word])


def is_intentional_blank_page(text: str) -> bool:
    return bool(
        re.search(
            r"p[aá]gina foi deixada em branco intencionalmente",
            normalize_text(text),
            re.I,
        )
    )


def is_manual_access_message(message: str) -> bool:
    return bool(re.search(r"login|captcha|mfa|senha|manual|access|acesso", message, re.I))


def is_reader_book_page(url: str, resource_code: str) -> bool:
    parsed = urlparse(str(url or ""))
    return (
        parsed.hostname == "integrada.minhabiblioteca.com.br"
        and f"/reader/books/{resource_code}" in parsed.path
    )


def is_sophia_terminal_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    return parsed.hostname == "philos.sophia.com.br" and parsed.path.startswith("/terminal/9418")


def reader_needs_manual_access(body_text: str, url: str) -> bool:
    text = normalize_text(body_text)
    if is_login_url(url):
        return True
    if epub_access_denied_text(text):
        return True
    if "Ir para Página" in text:
        return False
    return bool(
        re.search(
            r"entrar|login|senha|captcha|mfa|ingresse novamente|atualize sua lista de livros",
            text,
            re.I,
        )
    )


def is_login_url(url: str) -> bool:
    parsed = urlparse(str(url or ""))
    host = parsed.hostname or ""
    return bool(
        re.match(r"^login\.vitalsource\.com$", host, flags=re.I)
        or (re.search(r"(^|\.)vitalsource\.com$", host, flags=re.I) and "login" in parsed.path)
    )


def is_minha_biblioteca_book_url(url: str, resource_code: str) -> bool:
    parsed = urlparse(str(url or ""))
    return (
        parsed.hostname == "integrada.minhabiblioteca.com.br"
        and f"/books/{resource_code}" in parsed.path
    )


def is_allowed_sophia_sso_handoff_url(url: str, resource_code: str) -> bool:
    if is_minha_biblioteca_book_url(url, resource_code):
        return True
    parsed = urlparse(str(url or ""))
    return (
        parsed.hostname == "jigsaw.minhabiblioteca.com.br"
        and parsed.path.startswith("/auth/redirects/")
    )


def reader_pageid_from_url(url: str) -> str:
    match = re.search(r"/pageid/([^/?#]+)", str(url or ""))
    if match:
        return match.group(1)
    parsed = urlparse(str(url or ""))
    epub_match = re.search(r"/epub/([^?#]+)", parsed.path)
    if epub_match:
        return epub_match.group(1)
    epub_cfi_match = re.search(r"/epubcfi/([^?#]+)", parsed.path)
    if epub_cfi_match:
        return f"epubcfi-{hashlib.sha256(str(url).encode('utf-8')).hexdigest()[:16]}"
    return ""


def extract_sophia_subfield_code(html: str, resource_code: str) -> str:
    normalized = str(html or "").replace("&quot;", '"').replace("&#34;", '"')
    item_pattern = re.compile(
        r'\{[^{}]*"Codigo"\s*:\s*(\d+)[^{}]*"URL"\s*:\s*"([^"]+)"[^{}]*\}'
    )
    for match in item_pattern.finditer(normalized):
        if is_minha_biblioteca_book_url(match.group(2), resource_code):
            return match.group(1)
    resource_index = normalized.find(f"/books/{resource_code}")
    if resource_index >= 0:
        local = normalized[max(0, resource_index - 800) : resource_index + 800]
        code_match = re.search(r'"Codigo"\s*:\s*(\d+)', local)
        if code_match:
            return code_match.group(1)
    return ""


def sophia_sso_url(terminal_url: str, subfield_code: str) -> str:
    parsed = urlparse(terminal_url)
    match = re.match(r"^(/terminal/\d+)", parsed.path)
    base_path = match.group(1) if match else "/terminal/9418"
    return urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            f"{base_path}/IntegracaoDigital/ExecutarSingleSignOn",
            "",
            f"codigoSubcampo={subfield_code}",
            "",
        )
    )


def fetch_sophia_reader_url_with_retry(
    request: Any,
    sso_url: str,
    resource_code: str,
    *,
    attempts: int = 3,
    retry_delay_ms: int = 1500,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        response = request.get(sso_url, timeout=60000)
        response_text = response.text()
        if not response.ok:
            last_error = AcquisitionFailure(
                "Sophia SSO handoff failed",
                needs_manual=True,
                gate_failures=["sophia_sso_failed"],
            )
        else:
            try:
                return extract_reader_url_from_sophia_sso_response(response_text, resource_code)
            except AcquisitionFailure as exc:
                last_error = exc
        if attempt < attempts:
            time.sleep((retry_delay_ms * attempt) / 1000)
    raise last_error or AcquisitionFailure(
        "Sophia SSO handoff failed",
        needs_manual=True,
        gate_failures=["sophia_sso_failed"],
    )


def extract_reader_url_from_sophia_sso_response(response_text: str, resource_code: str) -> str:
    candidate = extract_url_candidate(response_text)
    if not candidate or not is_allowed_sophia_sso_handoff_url(candidate, resource_code):
        raise AcquisitionFailure(
            "Sophia SSO response did not return the expected Minha Biblioteca URL",
            needs_manual=True,
            gate_failures=["sophia_sso_bad_url"],
        )
    return candidate


def extract_url_candidate(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if re.match(r"^https?://", text, flags=re.I):
        return strip_trailing_punctuation(text)
    try:
        parsed = json.loads(text)
        candidate = find_url_in_json(parsed)
        if candidate:
            return candidate
    except json.JSONDecodeError:
        pass
    unescaped = text.replace("\\/", "/").replace("&amp;", "&")
    match = re.search(
        r"https://[a-z0-9.-]*minhabiblioteca\.com\.br/[^\s\"'<>\\]+",
        unescaped,
        flags=re.I,
    )
    return strip_trailing_punctuation(match.group(0)) if match else ""


def find_url_in_json(value: Any) -> str:
    if isinstance(value, str):
        return extract_url_candidate(value)
    if isinstance(value, list):
        for item in value:
            candidate = find_url_in_json(item)
            if candidate:
                return candidate
    if isinstance(value, dict):
        for item in value.values():
            candidate = find_url_in_json(item)
            if candidate:
                return candidate
    return ""


def strip_trailing_punctuation(url: str) -> str:
    return re.sub(r"[),.;]+$", "", str(url or ""))


def source_identity_from_page(page: Any, book: BookRef) -> dict[str, Any]:
    try:
        body_text = page.locator("body").inner_text(timeout=10000)
    except Exception:
        body_text = ""
    lines = [line.strip() for line in body_text.splitlines() if line.strip()]
    try:
        title = re.sub(r"^Minha Biblioteca:\s*", "", page.title(), flags=re.I)
    except Exception:
        title = ""
    title = title or book.title
    title_index = lines.index(title) if title in lines else -1
    authors = [lines[title_index + 1]] if title_index >= 0 and title_index + 1 < len(lines) else []
    return {
        "title": title,
        "authors": authors,
        "isbn_or_resource_code": book.resource_code,
    }


def source_identity_from_book(book: BookRef) -> dict[str, Any]:
    return {
        "title": book.title,
        "authors": [],
        "isbn_or_resource_code": book.resource_code,
    }


def cache_key_for(book: BookRef, scope: ScopeResult) -> str:
    return stable_hash(
        {
            "book_id": book.id,
            "resource_code": book.resource_code,
            "url": book.url,
            "scope": {
                "status": scope.status,
                "kind": scope.kind,
                "value": scope.value,
            },
            "scope_prompt_version": SCOPE_PROMPT_VERSION,
            "capture_version": CAPTURE_VERSION,
        }
    )


def artifact_paths(output_root: Path, book: BookRef) -> dict[str, Path]:
    book_dir = output_root / book.id
    return {
        "dir": book_dir,
        "markdown": book_dir / f"{book.id}-{slugify(book.title)}.md",
        "request": book_dir / "request.json",
        "metadata": book_dir / "metadata.json",
        "gate_report": book_dir / "gate_report.json",
        "source_manifest": book_dir / "source_manifest.json",
        "page_manifest": book_dir / "page_manifest.json",
        "acquisition_result": book_dir / "acquisition_result.json",
    }


def cache_dir_for(cache_root: Path, cache_key: str) -> Path:
    return cache_root / cache_key


def existing_markdown_path(output_root: Path, book: BookRef) -> Path | None:
    book_dir = output_root / book.id
    if not book_dir.exists():
        return None
    matches = sorted(book_dir.glob("*.md"))
    return matches[0] if matches else None


def page_capture_as_dict(page: PageCapture) -> dict[str, Any]:
    return {
        "page_index": page.page_index,
        "requested_label": page.requested_label,
        "reader_pageid": page.reader_pageid,
        "image": page.image,
        "markdown": page.markdown,
        "text_sha256": page.text_sha256,
        "reader_word_count": page.reader_word_count,
    }


def scope_as_dict(scope: ScopeResult) -> dict[str, Any]:
    return {
        "status": scope.status,
        "kind": scope.kind,
        "value": scope.value,
        "reason": scope.reason,
        "source": scope.source,
    }


def book_as_dict(book: BookRef) -> dict[str, Any]:
    return {
        "id": book.id,
        "title": book.title,
        "url": book.url,
        "resource_code": book.resource_code,
        "description": book.description,
    }


def combined_markdown_from_pages(artifact_dir: Path, book: BookRef, bundle: CaptureBundle, scope: ScopeResult) -> str:
    source_title = str(bundle.source_identity.get("title") or book.title)
    frontmatter = [
        "---",
        f"id: {json.dumps(book.id, ensure_ascii=False)}",
        f"title: {json.dumps(book.title, ensure_ascii=False)}",
        f"source_title: {json.dumps(source_title, ensure_ascii=False)}",
        f"resource_code: {json.dumps(book.resource_code, ensure_ascii=False)}",
        f"scope_kind: {json.dumps(scope.kind, ensure_ascii=False)}",
        f"scope_value: {json.dumps(scope.value, ensure_ascii=False)}",
        f"final_url: {json.dumps(bundle.final_url, ensure_ascii=False)}",
        f"captured_at: {json.dumps(iso_utc_now(), ensure_ascii=False)}",
        "---",
        "",
        f"# {book.title}",
        "",
    ]
    page_markdown = []
    for page in bundle.pages:
        page_markdown.append((artifact_dir / page.markdown).read_text(encoding="utf-8").strip())
    return "\n".join(frontmatter) + "\n\n".join(page_markdown).rstrip() + "\n"


def gate_report(
    *,
    book: BookRef,
    scope: ScopeResult,
    requested_pages: list[str],
    bundle: CaptureBundle,
) -> dict[str, Any]:
    failures: list[str] = []
    warnings = list(bundle.warnings)
    page_labels = [page.requested_label for page in bundle.pages]
    if bundle.status not in {"fetched", "fetched_with_warnings"}:
        failures.append("capture_not_fetched")
    if page_labels != requested_pages:
        failures.append("page_coverage_mismatch")
    if not bundle.pages:
        failures.append("empty_page_manifest")
    for page in bundle.pages:
        if not page.reader_pageid:
            failures.append("missing_reader_pageid")
        if page.reader_word_count < 20:
            warnings.append(f"low_reader_word_count_page_{page.page_index:04d}")
    return {
        "status": "failed_gate" if failures else "passed_with_warnings" if warnings else "passed",
        "book_id": book.id,
        "resource_code": book.resource_code,
        "scope": scope_as_dict(scope),
        "requested_pages": requested_pages,
        "captured_pages": page_labels,
        "failures": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
    }


def write_bundle_artifacts(
    *,
    book: BookRef,
    scope: ScopeResult,
    requested_pages: list[str],
    bundle: CaptureBundle,
    cache_key: str,
    artifact_dir: Path,
    source: str,
) -> Result:
    paths = artifact_paths(artifact_dir.parent, book)
    gate = gate_report(book=book, scope=scope, requested_pages=requested_pages, bundle=bundle)
    metadata = {
        "schema_version": "1.0",
        "book_id": book.id,
        "title": book.title,
        "url": book.url,
        "resource_code": book.resource_code,
        "scope": scope_as_dict(scope),
        "requested_pages": requested_pages,
        "final_url": bundle.final_url,
        "status": bundle.status,
        "capture_version": CAPTURE_VERSION,
        "captured_at": iso_utc_now(),
        "cache_key": cache_key,
        "source": source,
    }
    page_manifest = {
        "schema_version": "1.0",
        "pages": [page_capture_as_dict(page) for page in bundle.pages],
    }
    source_manifest = {
        "schema_version": "1.0",
        "book_id": book.id,
        "resource_kind": "book_library",
        "source_identity": bundle.source_identity,
        "coverage_used": {
            "mode": "assigned-scope",
            "scope": {"kind": scope.kind, "value": scope.value},
        },
        "artifacts": {
            "markdown": paths["markdown"].name,
            "page_manifest": "page_manifest.json",
            "evidence_dir": "evidence",
            "pages_dir": "pages",
            "gate_report": "gate_report.json",
        },
        "credential_fields_redacted": True,
    }
    acquisition_result = {
        "schema_version": "1.0",
        "book_id": book.id,
        "status": bundle.status,
        "resource_kind": "book_library",
        "final_url": bundle.final_url,
        "source_identity": bundle.source_identity,
        "access_mode": "virtual_library_browserbase",
        "coverage_used": source_manifest["coverage_used"],
        "page_manifest": [
            {
                "page_index": page.page_index,
                "requested_label": page.requested_label,
                "reader_pageid": page.reader_pageid,
            }
            for page in bundle.pages
        ],
        "warnings": bundle.warnings,
        "blocking_errors": bundle.blocking_errors,
        "credential_fields_redacted": True,
    }
    markdown = combined_markdown_from_pages(artifact_dir, book, bundle, scope)
    atomic_write_text(paths["request"], json.dumps(book_as_dict(book), ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["metadata"], json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["gate_report"], json.dumps(gate, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["source_manifest"], json.dumps(source_manifest, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["page_manifest"], json.dumps(page_manifest, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["acquisition_result"], json.dumps(acquisition_result, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["markdown"], markdown)
    status = "acquisition_failed" if gate["failures"] else "saved_with_warnings" if gate["warnings"] else "saved"
    return Result(
        book_id=book.id,
        title=book.title,
        resource_code=book.resource_code,
        status=status,
        output_path=str(paths["markdown"]),
        artifact_dir=str(paths["dir"]),
        cache_key=cache_key,
        warning_flags=list(gate["warnings"]),
        gate_failures=list(gate["failures"]),
        page_count=len(bundle.pages),
        source=source,
    )


def copy_tree_contents(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        destination = target / child.name
        if child.is_dir():
            shutil.copytree(child, destination)
        else:
            shutil.copy2(child, destination)


def load_cached_bundle(cache_dir: Path) -> CaptureBundle | None:
    result_path = cache_dir / "acquisition_result.json"
    page_manifest_path = cache_dir / "page_manifest.json"
    source_manifest_path = cache_dir / "source_manifest.json"
    if not (result_path.exists() and page_manifest_path.exists() and source_manifest_path.exists()):
        return None
    result = load_json(result_path)
    page_manifest = load_json(page_manifest_path)
    source_manifest = load_json(source_manifest_path)
    if not isinstance(result, dict) or not isinstance(page_manifest, dict) or not isinstance(source_manifest, dict):
        return None
    pages = []
    for page in page_manifest.get("pages", []):
        if not isinstance(page, dict):
            return None
        pages.append(
            PageCapture(
                page_index=int(page.get("page_index", 0)),
                requested_label=str(page.get("requested_label", "")),
                reader_pageid=str(page.get("reader_pageid", "")),
                image=str(page.get("image", "")),
                markdown=str(page.get("markdown", "")),
                text_sha256=str(page.get("text_sha256", "")),
                reader_word_count=int(page.get("reader_word_count", 0)),
            )
        )
    return CaptureBundle(
        status=str(result.get("status", "")),
        final_url=str(result.get("final_url", "")),
        source_identity=dict(source_manifest.get("source_identity", {})),
        pages=pages,
        warnings=list(result.get("warnings", [])),
        blocking_errors=list(result.get("blocking_errors", [])),
    )


def write_failure_artifacts(
    *,
    output_root: Path,
    book: BookRef,
    scope: ScopeResult | None,
    error: str,
    gate_failures: list[str],
    status: str = "acquisition_failed",
) -> Result:
    paths = artifact_paths(output_root, book)
    paths["dir"].mkdir(parents=True, exist_ok=True)
    gate = {
        "status": "failed_gate",
        "book_id": book.id,
        "resource_code": book.resource_code,
        "scope": scope_as_dict(scope) if scope else None,
        "failures": sorted(set(gate_failures or ["acquisition_failed"])),
        "warnings": [],
        "error": error,
    }
    metadata = {
        "schema_version": "1.0",
        "book_id": book.id,
        "title": book.title,
        "url": book.url,
        "resource_code": book.resource_code,
        "scope": scope_as_dict(scope) if scope else None,
        "status": status,
        "error": error,
        "captured_at": iso_utc_now(),
    }
    atomic_write_text(paths["request"], json.dumps(book_as_dict(book), ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["metadata"], json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["gate_report"], json.dumps(gate, ensure_ascii=False, indent=2) + "\n")
    return Result(
        book_id=book.id,
        title=book.title,
        resource_code=book.resource_code,
        status=status,
        artifact_dir=str(paths["dir"]),
        gate_failures=list(gate["failures"]),
        error=error,
    )


def extract_book(
    book: BookRef,
    *,
    output_root: Path,
    cache_root: Path,
    force: bool,
    refresh_cache: bool,
    normalizer: Any | None = None,
    acquirer: Any | None = None,
) -> Result:
    existing = existing_markdown_path(output_root, book)
    if existing and not force:
        return Result(
            book_id=book.id,
            title=book.title,
            resource_code=book.resource_code,
            status="skipped_existing",
            output_path=str(existing),
            artifact_dir=str(existing.parent),
            source="output",
        )

    normalizer = normalizer or DeepSeekScopeNormalizer()
    scope: ScopeResult | None = None
    try:
        scope = normalizer.normalize(book)
        requested_pages = requested_page_labels(scope.value)
        if not requested_pages:
            raise AcquisitionFailure(
                f"Scope did not resolve to concrete pages: {scope.value}",
                needs_manual=True,
                gate_failures=["missing_page_labels"],
            )
        cache_key = cache_key_for(book, scope)
        cache_dir = cache_dir_for(cache_root, cache_key)
        output_dir = output_root / book.id
        if not refresh_cache:
            cached = load_cached_bundle(cache_dir)
            if cached is not None:
                copy_tree_contents(cache_dir, output_dir)
                return write_bundle_artifacts(
                    book=book,
                    scope=scope,
                    requested_pages=requested_pages,
                    bundle=cached,
                    cache_key=cache_key,
                    artifact_dir=output_dir,
                    source="cache",
                )

        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        acquirer = acquirer or BrowserbaseBookAcquirer()
        bundle = acquirer.capture(
            book=book,
            scope=scope,
            requested_pages=requested_pages,
            artifact_dir=output_dir,
        )
        result = write_bundle_artifacts(
            book=book,
            scope=scope,
            requested_pages=requested_pages,
            bundle=bundle,
            cache_key=cache_key,
            artifact_dir=output_dir,
            source="network",
        )
        copy_tree_contents(output_dir, cache_dir)
        return result
    except AcquisitionFailure as exc:
        status = "needs_manual" if exc.needs_manual else "acquisition_failed"
        return write_failure_artifacts(
            output_root=output_root,
            book=book,
            scope=scope,
            error=str(exc),
            gate_failures=exc.gate_failures or ["acquisition_failed"],
            status=status,
        )
    except Exception as exc:
        return write_failure_artifacts(
            output_root=output_root,
            book=book,
            scope=scope,
            error=str(exc),
            gate_failures=["unexpected_error"],
        )


def result_as_dict(result: Result) -> dict[str, Any]:
    return {
        "book_id": result.book_id,
        "title": result.title,
        "resource_code": result.resource_code,
        "status": result.status,
        "output_path": result.output_path,
        "artifact_dir": result.artifact_dir,
        "cache_key": result.cache_key,
        "warning_flags": result.warning_flags,
        "gate_failures": result.gate_failures,
        "error": result.error,
        "page_count": result.page_count,
        "source": result.source,
    }


def run_books(args: argparse.Namespace, books: list[BookRef]) -> list[Result]:
    output_root = args.output
    cache_root = args.cache
    output_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    log_path = output_root / "run_log.jsonl"
    if log_path.exists() and args.force:
        log_path.unlink()

    results: list[Result] = []
    for book in books:
        result = extract_book(
            book,
            output_root=output_root,
            cache_root=cache_root,
            force=args.force,
            refresh_cache=args.refresh_cache,
        )
        results.append(result)
        atomic_write_text(
            log_path,
            "".join(
                json.dumps(result_as_dict(existing), ensure_ascii=False) + "\n"
                for existing in results
            ),
        )
        if result.status == "skipped_existing":
            print(f"[skip] id={result.book_id} existing={result.output_path}", flush=True)
        elif result.status in {"acquisition_failed", "needs_manual"}:
            print(f"[{result.status}] id={result.book_id} error={result.error}", flush=True)
        else:
            print(
                f"[{result.status}] id={result.book_id} pages={result.page_count} source={result.source}",
                flush=True,
            )
    return results


def build_summary(results: list[Result], selected_count: int, output_root: Path, cache_root: Path) -> dict[str, Any]:
    counts: dict[str, int] = {}
    warning_counts: dict[str, int] = {}
    gate_failure_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
        source_counts[result.source] = source_counts.get(result.source, 0) + 1
        for warning in result.warning_flags:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
        for failure in result.gate_failures:
            gate_failure_counts[failure] = gate_failure_counts.get(failure, 0) + 1
    return {
        "schema_version": "1.0",
        "generated_at": iso_utc_now(),
        "selected": selected_count,
        "counts": counts,
        "source_counts": source_counts,
        "warning_counts": warning_counts,
        "gate_failure_counts": gate_failure_counts,
        "failed_ids": [
            result.book_id
            for result in results
            if result.status in {"acquisition_failed", "needs_manual"}
        ],
        "output_root": str(output_root),
        "cache_root": str(cache_root),
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("Book acquisition summary")
    print(f"  selected: {summary['selected']}")
    for status, count in summary["counts"].items():
        print(f"  {status}: {count}")
    for source, count in summary["source_counts"].items():
        print(f"  source[{source}]: {count}")
    print(f"  output_root: {summary['output_root']}")
    print(f"  cache_root: {summary['cache_root']}")
    if summary["warning_counts"]:
        print("  warnings:")
        for warning, count in summary["warning_counts"].items():
            print(f"    {warning}: {count}")
    if summary["gate_failure_counts"]:
        print("  gate_failures:")
        for failure, count in summary["gate_failure_counts"].items():
            print(f"    {failure}: {count}")
    if summary["failed_ids"]:
        print(f"  failed_ids: {', '.join(summary['failed_ids'])}")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Acquire Minha Biblioteca pages through Browserbase.",
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Output directory. Defaults to cg_pipeline/book/output.",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=DEFAULT_CACHE_ROOT,
        help="Local capture cache keyed by book identity and normalized scope.",
    )
    parser.add_argument("--only", help="Comma-separated ids to process.")
    parser.add_argument("--force", action="store_true", help="Rewrite output artifacts even if markdown exists.")
    parser.add_argument("--refresh-cache", action="store_true", help="Capture again instead of replaying cache.")
    return parser


def normalize_args(args: argparse.Namespace) -> argparse.Namespace:
    args.input = args.input.resolve()
    args.output = args.output.resolve()
    args.cache = args.cache.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    load_dotenv(SCRIPT_DIR.parent / ".env")
    load_dotenv()
    parser = build_arg_parser()
    args = normalize_args(parser.parse_args(argv))
    try:
        only_ids = parse_only_ids(args.only)
    except ValueError as exc:
        parser.error(str(exc))
    books, missing_requested = load_books(args.input, only_ids)
    if missing_requested:
        print(f"Requested ids not found in input: {', '.join(sorted(missing_requested))}", file=sys.stderr)
        return 2
    print(
        f"Book acquisition: selected={len(books)}, force={args.force}, "
        f"refresh_cache={args.refresh_cache}, output={args.output}, cache={args.cache}"
    )
    results = run_books(args, books)
    summary = build_summary(results, selected_count=len(books), output_root=args.output, cache_root=args.cache)
    summary_path = args.output / "summary.json"
    atomic_write_text(summary_path, json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print_summary(summary)
    print(f"  summary_json: {summary_path}")
    print(f"  run_log_jsonl: {args.output / 'run_log.jsonl'}")
    return 1 if summary["failed_ids"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
