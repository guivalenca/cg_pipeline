#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import hashlib
import html as html_lib
import json
import os
import random
import re
import shutil
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx
from dotenv import load_dotenv
from PIL import Image, ImageStat, UnidentifiedImageError


FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"
DEFAULT_CONCURRENCY = 5
DEFAULT_FIRECRAWL_TIMEOUT_MS = 120_000
DEFAULT_MINIMAL_RETRY_TIMEOUT_MS = 240_000
DEFAULT_MINIMAL_RETRY_MAX_AGE_MS = 172_800_000
DEFAULT_HTTP_TIMEOUT_SECONDS = 300
DEFAULT_MAX_RETRIES = 3
DEFAULT_MIN_WORDS = 150
DEFAULT_MAX_WORDS_WARNING = 35_000
DEFAULT_MAX_IMAGES_WARNING = 150
DEFAULT_SCREENSHOT_VARIANCE_MIN = 2.0

TRANSIENT_HTTP_STATUS_CODES = {
    408,
    409,
    425,
    429,
    500,
    502,
    503,
    504,
    520,
    521,
    522,
    523,
    524,
}

ERROR_PAGE_RE = re.compile(
    r"\b("
    r"page not found|not found|deleted by author|"
    r"access denied|forbidden|unauthorized|service unavailable|bad gateway|"
    r"gateway timeout|too many requests|rate limit|captcha|cloudflare|blocked|"
    r"just a moment|security verification|not a bot|enable javascript|enable cookies"
    r")\b",
    re.IGNORECASE,
)

PAYWALL_RE = re.compile(
    r"\b("
    r"paywall|subscriber-only|members-only|member-only|premium article|"
    r"subscribe to continue|sign in to continue|login to continue|"
    r"create an account to continue|upgrade to continue|reading limit|"
    r"free member-only story|this story is for members"
    r")\b",
    re.IGNORECASE,
)

BOILERPLATE_RE = re.compile(
    r"\b("
    r"advertisement|cookie policy|privacy preferences|related articles|"
    r"recommended for you|write for us|newsletter|subscribe to our|"
    r"terms of content use|do not sell or share my personal information"
    r")\b",
    re.IGNORECASE,
)

BOT_WALL_RE = re.compile(
    r"\b("
    r"cloudflare|captcha|security check|security verification|just a moment|"
    r"verify you are human|blocked by|enable cookies|enable javascript"
    r")\b",
    re.IGNORECASE,
)

AUTH_WALL_RE = re.compile(
    r"\b("
    r"sign in|log in|required to access|unauthorized|authentication required|"
    r"subscribe to continue|join medium"
    r")\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Article:
    id: str
    title: str
    url: str


@dataclass(frozen=True)
class Route:
    strategy: str
    fetch_url: str
    request_params: dict[str, Any]
    notes: list[str]
    reject_reason: str | None = None
    screenshot_params: dict[str, Any] | None = None


@dataclass
class Result:
    article_id: str
    title: str
    url: str
    status: str
    strategy: str = "unknown"
    attempts: int = 0
    cache_key: str | None = None
    output_path: str | None = None
    artifact_dir: str | None = None
    warning_flags: list[str] | None = None
    gate_failures: list[str] | None = None
    error: str | None = None
    word_count: int = 0
    char_count: int = 0
    source: str = "unknown"


class TransientFetchError(Exception):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class PermanentFetchError(Exception):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_utc_now() -> str:
    return utc_now().isoformat().replace("+00:00", "Z")


def slugify(value: str, max_length: int = 90) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug[:max_length].rstrip("-") or "article")


def yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def yaml_frontmatter(data: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in data.items():
        if isinstance(value, list):
            if value:
                lines.append(f"{key}:")
                for item in value:
                    lines.append(f"  - {yaml_scalar(item)}")
            else:
                lines.append(f"{key}: []")
        elif isinstance(value, dict):
            if value:
                lines.append(f"{key}:")
                for child_key, child_value in value.items():
                    lines.append(f"  {child_key}: {yaml_scalar(child_value)}")
            else:
                lines.append(f"{key}: {{}}")
        else:
            lines.append(f"{key}: {yaml_scalar(value)}")
    lines.append("---")
    return "\n".join(lines)


def content_word_count(content: str) -> int:
    return len(re.findall(r"\b\w+\b", content, flags=re.UNICODE))


CODE_TABLE_RE = re.compile(
    r"\|\s*\|\s*\|\n"
    r"\|\s*-+\s*\|\s*-+\s*\|\n"
    r"\|\s*(?P<numbers>(?:\d+\s*(?:<br>\s*)?)+)\s*\|\s*(?P<code>[^|]*<br>[^|]*)\s*\|",
    re.IGNORECASE,
)


def code_fence_language(code: str) -> str:
    lowered = code.lower()
    if "from " in lowered or "import " in lowered or "model." in lowered or "dataset=" in lowered:
        return "python"
    if lowered.strip().startswith(("python ", "pip ", "conda ")):
        return "sh"
    return "text"


def normalize_line_number_code_tables(content: str) -> str:
    def replace(match: re.Match[str]) -> str:
        code = match.group("code")
        code = re.sub(r"<br\s*/?>", "\n", code, flags=re.IGNORECASE)
        code = html_lib.unescape(code)
        lines = [line.strip() for line in code.splitlines()]
        code_text = "\n".join(line for line in lines if line).strip()
        if not code_text:
            return match.group(0)
        language = code_fence_language(code_text)
        return f"```{language}\n{code_text}\n```"

    return CODE_TABLE_RE.sub(replace, content)


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


def load_articles(input_path: Path, only_ids: set[str] | None) -> tuple[list[Article], set[str]]:
    raw = load_json(input_path)
    if not isinstance(raw, list):
        raise SystemExit(f"Input JSON must be a list of objects: {input_path}")

    articles: list[Article] = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Input item #{idx} is not an object")
        missing = [key for key in ("id", "title", "url") if key not in item]
        if missing:
            raise SystemExit(f"Input item #{idx} is missing keys: {', '.join(missing)}")

        article_id = str(item["id"]).strip()
        title = str(item["title"]).strip()
        url = str(item["url"]).strip()
        if not article_id or not title or not url:
            raise SystemExit(f"Input item #{idx} has blank id, title, or url")
        seen_ids.add(article_id)
        if only_ids is None or article_id in only_ids:
            articles.append(Article(id=article_id, title=title, url=url))

    missing_requested = only_ids - seen_ids if only_ids is not None else set()
    return articles, missing_requested


def load_config(path: Path) -> dict[str, Any]:
    raw = load_json(path)
    if not isinstance(raw, dict):
        raise SystemExit(f"Config JSON must be an object: {path}")
    return raw


def hostname_for(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def host_config(config: dict[str, Any], section: str, hostname: str) -> dict[str, Any]:
    values = config.get(section)
    if not isinstance(values, dict):
        return {}
    host = hostname
    while host:
        match = values.get(host)
        if isinstance(match, dict):
            return match
        if "." not in host:
            break
        host = host.split(".", 1)[1]
    return {}


def blocked_reason(config: dict[str, Any], hostname: str) -> str | None:
    values = config.get("blocked_hosts")
    if not isinstance(values, dict):
        return None
    host = hostname
    while host:
        reason = values.get(host)
        if isinstance(reason, str):
            return reason
        if "." not in host:
            break
        host = host.split(".", 1)[1]
    return None


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    if path != "/":
        path = path.rstrip("/")
    query_pairs = sorted(parse_qsl(parsed.query, keep_blank_values=True))
    query = urlencode(query_pairs, doseq=True)
    return urlunparse((scheme, netloc, path, "", query, ""))


def github_blob_pdf_raw_url(url: str) -> str | None:
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() != "github.com":
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 5 or parts[2] != "blob" or not parts[-1].lower().endswith(".pdf"):
        return None
    owner, repo, branch = parts[0], parts[1], parts[3]
    pdf_path = "/".join(parts[4:])
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{pdf_path}"


def is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def screenshot_format(config: dict[str, Any], override: Any = None) -> dict[str, Any]:
    screenshot = override if isinstance(override, dict) else config.get("screenshot")
    if not isinstance(screenshot, dict):
        screenshot = {
            "type": "screenshot",
            "fullPage": True,
            "quality": 70,
            "viewport": {"width": 1440, "height": 1400},
        }
    return screenshot


def build_formats(
    config: dict[str, Any],
    *,
    include_screenshot: bool = True,
    override: Any = None,
) -> list[Any]:
    formats: list[Any] = ["markdown", "links", "images"]
    if include_screenshot:
        formats.append(screenshot_format(config, override))
    return formats


def route_article(
    article: Article,
    config: dict[str, Any],
    firecrawl_timeout_ms: int,
    refresh: bool,
) -> Route:
    normalized = normalize_url(article.url)
    hostname = hostname_for(normalized)
    reject_reason = blocked_reason(config, hostname)
    if reject_reason:
        return Route(
            strategy="rejected",
            fetch_url=normalized,
            request_params={},
            notes=[reject_reason],
            reject_reason=reject_reason,
        )

    fetch_url = github_blob_pdf_raw_url(normalized) or normalized
    notes: list[str] = []
    if fetch_url != normalized:
        notes.append("github_blob_pdf_rewritten_to_raw_url")

    strategy = "standard"
    merged: dict[str, Any] = {}
    for section, section_strategy in (
        ("special_hosts", "special"),
        ("interactive_hosts", "interactive_shell"),
        ("static_with_actions_hosts", "static_with_actions"),
        ("app_ui_hosts", "app_ui"),
    ):
        current = host_config(config, section, hostname)
        if current:
            strategy = str(current.get("strategy") or section_strategy)
            merged.update(current)
            break

    separate_screenshot = bool(merged.get("separateScreenshot", False))
    configured_formats = merged.get("formats")
    formats = (
        configured_formats
        if isinstance(configured_formats, list) and configured_formats
        else build_formats(
            config,
            include_screenshot=not separate_screenshot,
            override=merged.get("screenshot"),
        )
    )

    request_params: dict[str, Any] = {
        "url": fetch_url,
        "formats": formats,
        "onlyMainContent": bool(merged.get("onlyMainContent", config.get("onlyMainContent", True))),
        "onlyCleanContent": bool(merged.get("onlyCleanContent", config.get("onlyCleanContent", True))),
        "waitFor": int(merged.get("waitFor", config.get("waitFor", 0))),
        "timeout": firecrawl_timeout_ms,
        "removeBase64Images": True,
        "blockAds": True,
        "proxy": str(merged.get("proxy", config.get("proxy", "auto"))),
        "storeInCache": True,
        "maxAge": 0,
    }

    screenshot_params = None
    if separate_screenshot:
        screenshot_params = {
            "url": fetch_url,
            "formats": [screenshot_format(config, merged.get("screenshot"))],
            "onlyMainContent": False,
            "onlyCleanContent": False,
            "waitFor": int(merged.get("screenshotWaitFor", merged.get("waitFor", config.get("waitFor", 0)))),
            "timeout": firecrawl_timeout_ms,
            "removeBase64Images": True,
            "blockAds": True,
            "proxy": str(merged.get("proxy", config.get("proxy", "auto"))),
            "storeInCache": True,
            "maxAge": 0,
        }
        notes.append("separate_screenshot")

    location = config.get("location")
    if isinstance(location, dict):
        request_params["location"] = location

    exclude_tags = merged.get("excludeTags", config.get("excludeTags"))
    if isinstance(exclude_tags, list) and exclude_tags:
        request_params["excludeTags"] = exclude_tags

    include_tags = merged.get("includeTags")
    if isinstance(include_tags, list) and include_tags:
        request_params["includeTags"] = include_tags

    actions = merged.get("actions")
    if isinstance(actions, list) and actions:
        request_params["actions"] = actions

    pdf_config = {}
    pdf_overrides = config.get("pdf_overrides")
    if isinstance(pdf_overrides, dict):
        by_id = pdf_overrides.get(article.id)
        if isinstance(by_id, dict):
            pdf_config.update(by_id)
    if is_pdf_url(fetch_url) or pdf_config:
        strategy = "pdf"
        mode = str(pdf_config.get("mode", config.get("default_pdf_mode", "auto")))
        parser: dict[str, Any] = {"type": "pdf", "mode": mode}
        max_pages = pdf_config.get("maxPages")
        if isinstance(max_pages, int) and max_pages > 0:
            parser["maxPages"] = max_pages
        request_params["parsers"] = [parser]
        notes.append(f"pdf_mode_{mode}")
        pdf_notes = pdf_config.get("notes")
        if isinstance(pdf_notes, list):
            notes.extend(str(note) for note in pdf_notes)
    else:
        request_params["parsers"] = [{"type": "pdf", "mode": str(config.get("default_pdf_mode", "auto"))}]

    configured_notes = merged.get("notes")
    if isinstance(configured_notes, list):
        notes.extend(str(note) for note in configured_notes)

    return Route(
        strategy=strategy,
        fetch_url=fetch_url,
        request_params=request_params,
        notes=notes,
        screenshot_params=screenshot_params,
    )


def cache_key_for(route: Route) -> str:
    params = dict(route.request_params)
    params.pop("maxAge", None)
    params.pop("storeInCache", None)
    params.pop("timeout", None)
    material = {
        "endpoint": FIRECRAWL_SCRAPE_URL,
        "request_params": params,
        "strategy": route.strategy,
    }
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def exact_cache_key(route: Route, timeout_ms: int | None = None) -> str:
    params = dict(route.request_params)
    if timeout_ms is not None:
        params["timeout"] = timeout_ms
    material = {
        "endpoint": FIRECRAWL_SCRAPE_URL,
        "request_params": params,
        "strategy": route.strategy,
    }
    encoded = json.dumps(material, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def cache_candidate_keys(route: Route) -> list[str]:
    keys = [
        cache_key_for(route),
        exact_cache_key(route),
        exact_cache_key(route, DEFAULT_FIRECRAWL_TIMEOUT_MS),
        exact_cache_key(route, 240_000),
    ]
    unique: list[str] = []
    for key in keys:
        if key not in unique:
            unique.append(key)
    return unique


def output_markdown_path(output_root: Path, article: Article) -> Path:
    return output_root / article.id / f"{article.id}-{slugify(article.title)}.md"


def existing_markdown_path(output_root: Path, article: Article) -> Path | None:
    article_dir = output_root / article.id
    if not article_dir.exists():
        return None
    existing = sorted(article_dir.glob("*.md"))
    return existing[0] if existing else None


def retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        pass
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return max(0.0, (parsed - utc_now()).total_seconds())


async def fetch_firecrawl(
    client: httpx.AsyncClient,
    api_key: str,
    request_params: dict[str, Any],
    max_retries: int,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    max_attempts = max_retries + 1
    last_error: Exception | None = None
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "companion-firecrawl-acquisition/1.0",
    }

    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.post(FIRECRAWL_SCRAPE_URL, headers=headers, json=request_params)
            response_info = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url),
            }
            if response.status_code in TRANSIENT_HTTP_STATUS_CODES:
                retry_after = retry_after_seconds(response.headers.get("Retry-After"))
                raise TransientFetchError(
                    f"HTTP {response.status_code} from Firecrawl",
                    retry_after=retry_after,
                )
            if response.status_code >= 400:
                body = response.text[:1000].replace("\n", " ")
                raise PermanentFetchError(f"HTTP {response.status_code} from Firecrawl: {body}")

            try:
                payload = response.json()
            except json.JSONDecodeError as exc:
                raise PermanentFetchError(
                    f"Firecrawl returned non-JSON response: {response.text[:1000]}"
                ) from exc

            if not isinstance(payload, dict):
                raise PermanentFetchError("Firecrawl response was not a JSON object")
            if payload.get("success") is False:
                message = str(payload.get("error") or payload)
                code = str(payload.get("code") or "")
                if code in {"408", "429", "500", "502", "503", "504"}:
                    raise TransientFetchError(message)
                raise PermanentFetchError(message)

            return payload, response_info, attempt
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.NetworkError,
            httpx.TransportError,
            TransientFetchError,
        ) as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            retry_after = exc.retry_after if isinstance(exc, TransientFetchError) else None
            if retry_after is None:
                retry_after = min(45.0, 2.0 * (2 ** (attempt - 1))) + random.uniform(0, 1.0)
            await asyncio.sleep(retry_after)

    message = str(last_error) if last_error else "Unknown transient fetch error"
    raise TransientFetchError(f"Retries exhausted after {max_attempts} attempts: {message}")


def response_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    if "markdown" in payload:
        return payload
    raise PermanentFetchError(f"Firecrawl response missing data object: {payload}")


def screenshot_url_from_data(data: dict[str, Any]) -> str | None:
    value = data.get("screenshot")
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return value
    actions = data.get("actions")
    if isinstance(actions, dict):
        screenshots = actions.get("screenshots")
        if isinstance(screenshots, list):
            for item in screenshots:
                if isinstance(item, str) and item.startswith(("http://", "https://")):
                    return item
    return None


def minimal_retry_config(config: dict[str, Any], hostname: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    top_level = config.get("minimal_retry")
    if isinstance(top_level, dict):
        merged.update(top_level)
    merged.update(host_config(config, "minimal_retry_hosts", hostname))
    return merged


def minimal_retry_route(
    article: Article,
    config: dict[str, Any],
    original_route: Route,
    firecrawl_timeout_ms: int,
    retry_reason: str,
) -> Route:
    hostname = hostname_for(original_route.fetch_url)
    retry_config = minimal_retry_config(config, hostname)
    timeout_ms = int(
        retry_config.get(
            "timeout",
            max(firecrawl_timeout_ms, DEFAULT_MINIMAL_RETRY_TIMEOUT_MS),
        )
    )
    timeout_ms = min(300_000, max(timeout_ms, firecrawl_timeout_ms))
    location = retry_config.get(
        "location",
        {
            "country": "BR",
            "languages": ["pt-BR", "es-ES", "en-US"],
        },
    )

    request_params: dict[str, Any] = {
        "url": original_route.fetch_url,
        "formats": ["markdown"],
        "onlyMainContent": bool(retry_config.get("onlyMainContent", True)),
        "onlyCleanContent": bool(retry_config.get("onlyCleanContent", False)),
        "waitFor": int(retry_config.get("waitFor", 0)),
        "timeout": timeout_ms,
        "removeBase64Images": True,
        "blockAds": bool(retry_config.get("blockAds", True)),
        "proxy": str(retry_config.get("proxy", config.get("proxy", "auto"))),
        "storeInCache": True,
        "maxAge": int(retry_config.get("maxAge", DEFAULT_MINIMAL_RETRY_MAX_AGE_MS)),
    }
    if isinstance(location, dict):
        request_params["location"] = location

    notes = [
        "minimal_retry_markdown_only",
        "minimal_retry_no_screenshot_links_or_images",
        "minimal_retry_relaxed_clean_content",
        "minimal_retry_accepts_pt_br_and_es_es",
        f"minimal_retry_after_{retry_reason}",
        f"original_strategy_{original_route.strategy}",
    ]
    notes.extend(original_route.notes)
    return Route(
        strategy="firecrawl_minimal_retry",
        fetch_url=original_route.fetch_url,
        request_params=request_params,
        notes=notes,
        screenshot_params=None,
    )


async def download_screenshot(client: httpx.AsyncClient, url: str) -> tuple[bytes, str]:
    response = await client.get(url)
    response.raise_for_status()
    content_type = response.headers.get("content-type", "image/png").split(";", 1)[0].strip()
    return response.content, content_type


def screenshot_extension(content_type: str) -> str:
    if content_type == "image/jpeg":
        return ".jpg"
    if content_type == "image/webp":
        return ".webp"
    return ".png"


def screenshot_stats(image_bytes: bytes) -> dict[str, Any]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            stat = ImageStat.Stat(image)
            variance = sum(stat.var) / len(stat.var)
            extrema = image.getextrema()
            return {
                "width": image.width,
                "height": image.height,
                "variance": variance,
                "blank": variance < DEFAULT_SCREENSHOT_VARIANCE_MIN,
                "extrema": extrema,
            }
    except UnidentifiedImageError:
        return {"error": "unidentified_image", "blank": True}


def suspicious_flags(
    *,
    content: str,
    requested_title: str,
    firecrawl_title: str | None,
    min_words: int,
    strategy: str,
    route_notes: list[str],
) -> list[str]:
    flags: list[str] = []
    stripped = content.strip()
    words = content_word_count(stripped)
    probe = "\n".join([firecrawl_title or "", requested_title, stripped[:4000]])

    if not stripped:
        flags.append("empty_content")
    elif words < min_words:
        flags.append("short_content")
    elif words > DEFAULT_MAX_WORDS_WARNING:
        flags.append("very_long_content")

    image_markdown_count = len(re.findall(r"!\[[^\]]*\]\(", stripped))
    if image_markdown_count > DEFAULT_MAX_IMAGES_WARNING:
        flags.append("many_images")

    if ERROR_PAGE_RE.search(probe):
        flags.append("looks_like_error_page")
    if PAYWALL_RE.search(probe):
        flags.append("possible_paywall")
    if BOILERPLATE_RE.search(stripped):
        flags.append("possible_boilerplate")
    if BOT_WALL_RE.search(probe):
        flags.append("possible_bot_wall")
    if AUTH_WALL_RE.search(probe) and words < 1200:
        flags.append("possible_auth_wall")
    if strategy == "interactive_shell":
        flags.append("interactive_shell_review")
    for note in route_notes:
        if note.startswith("github_blob_pdf"):
            flags.append("rewritten_source_url")
        if note.startswith("pdf_mode_ocr"):
            flags.append("ocr_pdf")

    return sorted(set(flags))


def gate_report(
    *,
    data: dict[str, Any],
    content: str,
    article: Article,
    route: Route,
    screenshot_path: Path | None,
    screenshot_analysis: dict[str, Any] | None,
) -> dict[str, Any]:
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    status_code = metadata.get("statusCode")
    content_type = str(metadata.get("contentType") or "")
    resolved_url = str(metadata.get("url") or metadata.get("sourceURL") or route.fetch_url)
    title = str(metadata.get("title") or "")
    words = content_word_count(content)
    failures: list[str] = []
    warnings: list[str] = []

    if isinstance(status_code, int) and not (200 <= status_code < 300):
        failures.append(f"http_status_{status_code}")
    if metadata.get("error"):
        failures.append("metadata_error")
    if route.strategy == "pdf" and "pdf" not in content_type.lower() and not is_pdf_url(route.fetch_url):
        warnings.append("expected_pdf_but_metadata_not_pdf")
    if route.strategy != "pdf" and content_type and not any(
        token in content_type.lower() for token in ("html", "text", "json", "xml")
    ):
        warnings.append("unexpected_content_type")
    if BOT_WALL_RE.search("\n".join([title, content[:4000]])):
        failures.append("bot_wall_detected")
    if AUTH_WALL_RE.search("\n".join([title, content[:4000]])) and words < 1200:
        failures.append("auth_wall_detected")
    if ERROR_PAGE_RE.search("\n".join([title, content[:4000]])) and words < 1000:
        failures.append("error_page_detected")
    if screenshot_analysis:
        if screenshot_analysis.get("blank"):
            failures.append("blank_or_unreadable_screenshot")
    else:
        warnings.append("missing_screenshot")
    if route.strategy == "interactive_shell":
        warnings.append("interactive_shell_requires_manual_review")
    if title and ERROR_PAGE_RE.search(title):
        warnings.append("title_error_review")

    return {
        "status": "failed_gate" if failures else "passed_with_warnings" if warnings else "passed",
        "failures": sorted(set(failures)),
        "warnings": sorted(set(warnings)),
        "metadata_status_code": status_code,
        "metadata_content_type": content_type,
        "metadata_title": title,
        "resolved_url": resolved_url,
        "requested_url": article.url,
        "fetch_url": route.fetch_url,
        "strategy": route.strategy,
        "word_count": words,
        "screenshot_path": str(screenshot_path) if screenshot_path else None,
        "screenshot_analysis": screenshot_analysis or {},
    }


def render_markdown(
    *,
    article: Article,
    data: dict[str, Any],
    content: str,
    warnings: list[str],
    gate: dict[str, Any],
    route: Route,
    cache_key: str,
    fetched_at: str,
) -> str:
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    links = data.get("links") if isinstance(data.get("links"), list) else []
    images = data.get("images") if isinstance(data.get("images"), list) else []
    frontmatter = {
        "id": article.id,
        "title": article.title,
        "source_url": article.url,
        "fetch_url": route.fetch_url,
        "resolved_url": metadata.get("url") or metadata.get("sourceURL"),
        "firecrawl_title": metadata.get("title"),
        "description": metadata.get("description"),
        "fetched_at": fetched_at,
        "provider": "firecrawl",
        "strategy": route.strategy,
        "cache_key": cache_key,
        "firecrawl_status_code": metadata.get("statusCode"),
        "firecrawl_content_type": metadata.get("contentType"),
        "word_count": content_word_count(content),
        "char_count": len(content),
        "content_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "image_count": len(images),
        "link_count": len(links),
        "warnings": warnings,
        "gate_status": gate.get("status"),
        "gate_failures": gate.get("failures", []),
        "route_notes": route.notes,
    }
    return f"{yaml_frontmatter(frontmatter)}\n\n{content.rstrip()}\n"


def artifact_paths(output_root: Path, article: Article) -> dict[str, Path]:
    article_dir = output_root / article.id
    return {
        "dir": article_dir,
        "markdown": output_markdown_path(output_root, article),
        "raw_response": article_dir / "raw_response.json",
        "request": article_dir / "request.json",
        "metadata": article_dir / "metadata.json",
        "gate_report": article_dir / "gate_report.json",
    }


def cache_paths(cache_root: Path, cache_key: str) -> dict[str, Path]:
    cache_dir = cache_root / cache_key
    return {
        "dir": cache_dir,
        "raw_response": cache_dir / "raw_response.json",
        "request": cache_dir / "request.json",
        "http_response": cache_dir / "http_response.json",
        "screenshot": cache_dir / "screenshot",
    }


def cache_hit(cache_root: Path, cache_key: str) -> bool:
    paths = cache_paths(cache_root, cache_key)
    return paths["raw_response"].exists() and paths["request"].exists()


def copy_cache_artifacts(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in ("raw_response.json", "request.json", "http_response.json"):
        source = source_dir / name
        if source.exists():
            shutil.copyfile(source, target_dir / name)
    for source in source_dir.glob("screenshot.*"):
        shutil.copyfile(source, target_dir / source.name)


async def get_payload(
    *,
    client: httpx.AsyncClient,
    api_key: str,
    route: Route,
    cache_root: Path,
    cache_key: str,
    max_retries: int,
    refresh: bool,
) -> tuple[dict[str, Any], dict[str, Any], int, str]:
    paths = cache_paths(cache_root, cache_key)
    if not refresh and cache_hit(cache_root, cache_key):
        payload = load_json(paths["raw_response"])
        http_response = load_json(paths["http_response"]) if paths["http_response"].exists() else {}
        return payload, http_response, 0, "cache"

    if not refresh:
        for candidate_key in cache_candidate_keys(route):
            if candidate_key == cache_key:
                continue
            candidate = cache_paths(cache_root, candidate_key)
            if cache_hit(cache_root, candidate_key):
                copy_cache_artifacts(candidate["dir"], paths["dir"])
                payload = load_json(paths["raw_response"])
                http_response = load_json(paths["http_response"]) if paths["http_response"].exists() else {}
                return payload, http_response, 0, "cache"

    payload, http_response, attempts = await fetch_firecrawl(
        client=client,
        api_key=api_key,
        request_params=route.request_params,
        max_retries=max_retries,
    )
    atomic_write_text(paths["request"], json.dumps(route.request_params, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["raw_response"], json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["http_response"], json.dumps(http_response, ensure_ascii=False, indent=2) + "\n")
    return payload, http_response, attempts, "network"


def spacy_page_data_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme, parsed.netloc, f"/page-data{path}/page-data.json", "", "", ""))


def ast_text(node: Any) -> str:
    if isinstance(node, str):
        return node
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        return str(node.get("value") or "")
    children = node.get("children")
    if isinstance(children, list):
        return "".join(ast_text(child) for child in children)
    return ""


def ast_children_to_markdown(children: Any, *, list_depth: int = 0) -> str:
    if not isinstance(children, list):
        return ""
    return "".join(ast_node_to_markdown(child, list_depth=list_depth) for child in children)


def inline_children_to_markdown(children: Any) -> str:
    if not isinstance(children, list):
        return ""
    parts: list[str] = []
    for child in children:
        if not isinstance(child, dict):
            continue
        if child.get("type") == "text":
            parts.append(str(child.get("value") or ""))
            continue
        tag = child.get("tagName")
        text = inline_children_to_markdown(child.get("children"))
        props = child.get("properties") if isinstance(child.get("properties"), dict) else {}
        if tag == "code":
            parts.append(f"`{text}`")
        elif tag == "strong":
            parts.append(f"**{text}**")
        elif tag == "em":
            parts.append(f"_{text}_")
        elif tag == "a":
            href = props.get("href")
            parts.append(f"[{text}]({href})" if href else text)
        elif tag == "img":
            src = props.get("src")
            alt = props.get("alt") or ""
            if src:
                parts.append(f"![{alt}]({src})")
        elif tag == "br":
            parts.append("\n")
        else:
            parts.append(text)
    return "".join(parts)


def ast_node_to_markdown(node: Any, *, list_depth: int = 0) -> str:
    if not isinstance(node, dict):
        return ""
    if node.get("type") == "text":
        value = str(node.get("value") or "")
        return value if value.strip() else ""

    tag = node.get("tagName")
    props = node.get("properties") if isinstance(node.get("properties"), dict) else {}
    children = node.get("children")

    if tag == "exercise":
        number = props.get("id")
        title = props.get("title") or "Exercise"
        kind = props.get("type")
        suffix = f" ({kind})" if kind else ""
        heading = f"## {number}. {title}{suffix}\n\n" if number else f"## {title}{suffix}\n\n"
        return heading + ast_children_to_markdown(children) + "\n"
    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(str(tag)[1])
        return f"{'#' * level} {inline_children_to_markdown(children).strip()}\n\n"
    if tag == "p":
        text = inline_children_to_markdown(children).strip()
        return f"{text}\n\n" if text else ""
    if tag in {"ul", "ol"}:
        return ast_children_to_markdown(children, list_depth=list_depth + 1) + "\n"
    if tag == "li":
        text = inline_children_to_markdown(children).strip()
        nested = ast_children_to_markdown(
            [child for child in children or [] if isinstance(child, dict) and child.get("tagName") in {"ul", "ol"}],
            list_depth=list_depth + 1,
        )
        prefix = "  " * max(0, list_depth - 1) + "- "
        return f"{prefix}{text}\n{nested}"
    if tag in {"pre", "codeblock"}:
        code_id = props.get("id")
        if tag == "codeblock" and code_id:
            return f"> spaCy interactive code block: `{code_id}`\n\n"
        text = ast_text(node).strip("\n")
        return f"```\n{text}\n```\n\n" if text else ""
    if tag == "blockquote":
        text = ast_children_to_markdown(children).strip()
        return "\n".join(f"> {line}" for line in text.splitlines()) + "\n\n" if text else ""
    if tag == "slides":
        source = props.get("source")
        return f"> spaCy slide deck: `{source}`\n\n" if source else ""
    if tag == "choice":
        return "> spaCy multiple-choice exercise\n\n" + ast_children_to_markdown(children)
    if tag == "img":
        src = props.get("src")
        alt = props.get("alt") or ""
        return f"![{alt}]({src})\n\n" if src else ""
    return ast_children_to_markdown(children)


def render_spacy_page_data_markdown(page_data: dict[str, Any], article: Article) -> tuple[str, dict[str, Any]]:
    result = page_data.get("result") if isinstance(page_data.get("result"), dict) else {}
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    remark = data.get("markdownRemark") if isinstance(data.get("markdownRemark"), dict) else {}
    frontmatter = remark.get("frontmatter") if isinstance(remark.get("frontmatter"), dict) else {}
    html_ast = remark.get("htmlAst") if isinstance(remark.get("htmlAst"), dict) else {}
    children = html_ast.get("children")

    title = str(frontmatter.get("title") or article.title)
    description = str(frontmatter.get("description") or "")
    body = ast_children_to_markdown(children).strip()
    markdown = f"# {title}\n\n"
    if description:
        markdown += f"{description}\n\n"
    markdown += body
    metadata = {
        "title": title,
        "description": description or None,
        "statusCode": 200,
        "contentType": "application/json",
        "url": article.url,
        "sourceURL": article.url,
        "spacy_page_data_path": page_data.get("path"),
    }
    return markdown.rstrip() + "\n", metadata


async def fetch_json_with_retries(
    client: httpx.AsyncClient,
    url: str,
    max_retries: int,
) -> tuple[dict[str, Any], dict[str, Any], int]:
    max_attempts = max_retries + 1
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = await client.get(url)
            response_info = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "url": str(response.url),
            }
            if response.status_code in TRANSIENT_HTTP_STATUS_CODES:
                retry_after = retry_after_seconds(response.headers.get("Retry-After"))
                raise TransientFetchError(f"HTTP {response.status_code} from {url}", retry_after=retry_after)
            if response.status_code >= 400:
                raise PermanentFetchError(f"HTTP {response.status_code} from {url}: {response.text[:500]}")
            payload = response.json()
            if not isinstance(payload, dict):
                raise PermanentFetchError(f"JSON response was not an object: {url}")
            return payload, response_info, attempt
        except (
            httpx.TimeoutException,
            httpx.ConnectError,
            httpx.NetworkError,
            httpx.TransportError,
            TransientFetchError,
        ) as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            retry_after = exc.retry_after if isinstance(exc, TransientFetchError) else None
            if retry_after is None:
                retry_after = min(30.0, 1.5 * (2 ** (attempt - 1))) + random.uniform(0, 1.0)
            await asyncio.sleep(retry_after)
    message = str(last_error) if last_error else "Unknown JSON fetch error"
    raise TransientFetchError(f"Retries exhausted after {max_attempts} attempts: {message}")


async def get_spacy_course_payload(
    *,
    client: httpx.AsyncClient,
    article: Article,
    route: Route,
    cache_root: Path,
    cache_key: str,
    max_retries: int,
    refresh: bool,
) -> tuple[dict[str, Any], dict[str, Any], int, str]:
    paths = cache_paths(cache_root, cache_key)
    page_data_url = spacy_page_data_url(route.fetch_url)
    if not refresh and cache_hit(cache_root, cache_key):
        payload = load_json(paths["raw_response"])
        http_response = load_json(paths["http_response"]) if paths["http_response"].exists() else {}
        return payload, http_response, 0, "cache"

    page_data, http_response, attempts = await fetch_json_with_retries(
        client=client,
        url=page_data_url,
        max_retries=max_retries,
    )
    markdown, metadata = render_spacy_page_data_markdown(page_data, article)
    metadata["pageDataURL"] = page_data_url
    payload = {
        "success": True,
        "provider": "spacy_gatsby_page_data",
        "data": {
            "markdown": markdown,
            "metadata": metadata,
            "links": [],
            "images": [],
            "pageDataURL": page_data_url,
            "pageData": page_data,
        },
    }
    atomic_write_text(paths["request"], json.dumps({"url": page_data_url, "strategy": route.strategy}, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["raw_response"], json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["http_response"], json.dumps(http_response, ensure_ascii=False, indent=2) + "\n")
    return payload, http_response, attempts, "network"


async def persist_artifacts(
    *,
    client: httpx.AsyncClient,
    article: Article,
    route: Route,
    cache_root: Path,
    output_root: Path,
    cache_key: str,
    payload: dict[str, Any],
    http_response: dict[str, Any],
    min_words: int,
    api_key: str,
    max_retries: int,
    refresh: bool,
) -> Result:
    data = response_data(payload)
    content = data.get("markdown")
    if not isinstance(content, str):
        raise PermanentFetchError("Firecrawl response data.markdown was not a string")
    content = normalize_line_number_code_tables(content)
    data["markdown"] = content

    paths = artifact_paths(output_root, article)
    cache = cache_paths(cache_root, cache_key)
    paths["dir"].mkdir(parents=True, exist_ok=True)

    screenshot_path: Path | None = None
    screenshot_analysis: dict[str, Any] | None = None
    existing_screenshots = sorted(paths["dir"].glob("screenshot.*"))
    if not refresh and existing_screenshots:
        screenshot_path = existing_screenshots[0]
        screenshot_analysis = screenshot_stats(screenshot_path.read_bytes())

    screenshot_url = screenshot_url_from_data(data)
    if screenshot_path is None and screenshot_url:
        cached_screenshot_candidates = sorted(cache["dir"].glob("screenshot.*"))
        if cached_screenshot_candidates:
            cached = cached_screenshot_candidates[0]
            screenshot_path = paths["dir"] / cached.name
            shutil.copyfile(cached, screenshot_path)
            screenshot_analysis = screenshot_stats(screenshot_path.read_bytes())
        else:
            try:
                image_bytes, content_type = await download_screenshot(client, screenshot_url)
                ext = screenshot_extension(content_type)
                cache_screenshot = cache["dir"] / f"screenshot{ext}"
                atomic_write_bytes(cache_screenshot, image_bytes)
                screenshot_path = paths["dir"] / f"screenshot{ext}"
                atomic_write_bytes(screenshot_path, image_bytes)
                screenshot_analysis = screenshot_stats(image_bytes)
            except Exception as exc:
                screenshot_analysis = {"error": f"{type(exc).__name__}: {exc}", "blank": True}

    if screenshot_path is None and route.screenshot_params is not None:
        screenshot_cache_key = hashlib.sha256(
            json.dumps(route.screenshot_params, ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest()
        screenshot_cache = cache_paths(cache_root, f"{cache_key}-screenshot-{screenshot_cache_key}")
        screenshot_payload: dict[str, Any] | None = None
        if not refresh and screenshot_cache["raw_response"].exists():
            screenshot_payload = load_json(screenshot_cache["raw_response"])
        else:
            try:
                screenshot_payload, screenshot_http, _ = await fetch_firecrawl(
                    client=client,
                    api_key=api_key,
                    request_params=route.screenshot_params,
                    max_retries=max_retries,
                )
                atomic_write_text(
                    screenshot_cache["request"],
                    json.dumps(route.screenshot_params, ensure_ascii=False, indent=2) + "\n",
                )
                atomic_write_text(
                    screenshot_cache["raw_response"],
                    json.dumps(screenshot_payload, ensure_ascii=False, indent=2) + "\n",
                )
                atomic_write_text(
                    screenshot_cache["http_response"],
                    json.dumps(screenshot_http, ensure_ascii=False, indent=2) + "\n",
                )
            except Exception as exc:
                screenshot_analysis = {"error": f"{type(exc).__name__}: {exc}", "blank": True}

        if screenshot_payload is not None:
            atomic_write_text(
                paths["dir"] / "screenshot_response.json",
                json.dumps(screenshot_payload, ensure_ascii=False, indent=2) + "\n",
            )
            screenshot_data = response_data(screenshot_payload)
            separate_screenshot_url = screenshot_url_from_data(screenshot_data)
            if separate_screenshot_url:
                cached_screenshot_candidates = sorted(screenshot_cache["dir"].glob("screenshot.*"))
                if cached_screenshot_candidates:
                    cached = cached_screenshot_candidates[0]
                    screenshot_path = paths["dir"] / cached.name
                    shutil.copyfile(cached, screenshot_path)
                    screenshot_analysis = screenshot_stats(screenshot_path.read_bytes())
                else:
                    try:
                        image_bytes, content_type = await download_screenshot(client, separate_screenshot_url)
                        ext = screenshot_extension(content_type)
                        cache_screenshot = screenshot_cache["dir"] / f"screenshot{ext}"
                        atomic_write_bytes(cache_screenshot, image_bytes)
                        screenshot_path = paths["dir"] / f"screenshot{ext}"
                        atomic_write_bytes(screenshot_path, image_bytes)
                        screenshot_analysis = screenshot_stats(image_bytes)
                    except Exception as exc:
                        screenshot_analysis = {"error": f"{type(exc).__name__}: {exc}", "blank": True}

    gate = gate_report(
        data=data,
        content=content,
        article=article,
        route=route,
        screenshot_path=screenshot_path,
        screenshot_analysis=screenshot_analysis,
    )
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    warnings = suspicious_flags(
        content=content,
        requested_title=article.title,
        firecrawl_title=str(metadata.get("title")) if metadata.get("title") is not None else None,
        min_words=min_words,
        strategy=route.strategy,
        route_notes=route.notes,
    )
    warnings = sorted(set(warnings + list(gate.get("warnings", []))))

    fetched_at = iso_utc_now()
    markdown = render_markdown(
        article=article,
        data=data,
        content=content,
        warnings=warnings,
        gate=gate,
        route=route,
        cache_key=cache_key,
        fetched_at=fetched_at,
    )

    atomic_write_text(paths["request"], json.dumps(route.request_params, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["raw_response"], json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["metadata"], json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["gate_report"], json.dumps(gate, ensure_ascii=False, indent=2) + "\n")
    atomic_write_text(paths["markdown"], markdown)
    atomic_write_text(paths["dir"] / "http_response.json", json.dumps(http_response, ensure_ascii=False, indent=2) + "\n")

    status = "saved"
    gate_failures = list(gate.get("failures", []))
    if gate_failures:
        status = "saved_failed_gate"
    elif warnings:
        status = "saved_suspicious"

    return Result(
        article_id=article.id,
        title=article.title,
        url=article.url,
        status=status,
        strategy=route.strategy,
        output_path=str(paths["markdown"]),
        artifact_dir=str(paths["dir"]),
        warning_flags=warnings,
        gate_failures=gate_failures,
        word_count=content_word_count(content),
        char_count=len(content),
        cache_key=cache_key,
    )


async def process_article(
    *,
    client: httpx.AsyncClient,
    article: Article,
    output_root: Path,
    cache_root: Path,
    config: dict[str, Any],
    api_key: str,
    force: bool,
    refresh: bool,
    firecrawl_timeout_ms: int,
    max_retries: int,
    min_words: int,
) -> Result:
    if not force:
        existing = existing_markdown_path(output_root, article)
        if existing is not None:
            return Result(
                article_id=article.id,
                title=article.title,
                url=article.url,
                status="skipped",
                output_path=str(existing),
                artifact_dir=str(existing.parent),
                source="output",
            )

    route = route_article(article, config, firecrawl_timeout_ms=firecrawl_timeout_ms, refresh=refresh)
    if route.reject_reason:
        paths = artifact_paths(output_root, article)
        paths["dir"].mkdir(parents=True, exist_ok=True)
        report = {
            "status": "rejected",
            "failures": [route.reject_reason],
            "warnings": [],
            "requested_url": article.url,
            "fetch_url": route.fetch_url,
            "strategy": route.strategy,
        }
        atomic_write_text(paths["gate_report"], json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return Result(
            article_id=article.id,
            title=article.title,
            url=article.url,
            status="rejected",
            strategy=route.strategy,
            artifact_dir=str(paths["dir"]),
            gate_failures=[route.reject_reason],
            error=route.reject_reason,
        )

    cache_key = cache_key_for(route)
    if route.strategy == "spacy_course_gatsby":
        payload, http_response, attempts, source = await get_spacy_course_payload(
            client=client,
            article=article,
            route=route,
            cache_root=cache_root,
            cache_key=cache_key,
            max_retries=max_retries,
            refresh=refresh,
        )
    else:
        first_error: Exception | None = None
        try:
            payload, http_response, attempts, source = await get_payload(
                client=client,
                api_key=api_key,
                route=route,
                cache_root=cache_root,
                cache_key=cache_key,
                max_retries=max_retries,
                refresh=refresh,
            )
        except (TransientFetchError, httpx.TimeoutException, httpx.TransportError) as exc:
            first_error = exc
            retry_reason = re.sub(r"[^a-zA-Z0-9]+", "_", type(exc).__name__).strip("_")
            route = minimal_retry_route(
                article=article,
                config=config,
                original_route=route,
                firecrawl_timeout_ms=firecrawl_timeout_ms,
                retry_reason=retry_reason or "fetch_error",
            )
            cache_key = cache_key_for(route)
            payload, http_response, attempts, source = await get_payload(
                client=client,
                api_key=api_key,
                route=route,
                cache_root=cache_root,
                cache_key=cache_key,
                max_retries=max_retries,
                refresh=refresh,
            )
        if first_error is not None:
            attempts += max_retries + 1
            source = f"{source}_after_minimal_retry"
    result = await persist_artifacts(
        client=client,
        article=article,
        route=route,
        cache_root=cache_root,
        output_root=output_root,
        cache_key=cache_key,
        payload=payload,
        http_response=http_response,
        min_words=min_words,
        api_key=api_key,
        max_retries=max_retries,
        refresh=refresh,
    )
    result.attempts = attempts
    result.source = source
    return result


def result_event(result: Result) -> dict[str, Any]:
    return {
        "timestamp": iso_utc_now(),
        "id": result.article_id,
        "title": result.title,
        "url": result.url,
        "status": result.status,
        "strategy": result.strategy,
        "attempts": result.attempts,
        "source": result.source,
        "cache_key": result.cache_key,
        "output_path": result.output_path,
        "artifact_dir": result.artifact_dir,
        "warnings": result.warning_flags or [],
        "gate_failures": result.gate_failures or [],
        "error": result.error,
        "word_count": result.word_count,
        "char_count": result.char_count,
    }


def append_jsonl(path: Path, event: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


async def run_batch(args: argparse.Namespace, articles: list[Article], api_key: str, config: dict[str, Any]) -> list[Result]:
    output_root = args.output
    cache_root = args.cache
    output_root.mkdir(parents=True, exist_ok=True)
    cache_root.mkdir(parents=True, exist_ok=True)
    log_path = output_root / "run_log.jsonl"
    log_path.write_text("", encoding="utf-8")

    queue: asyncio.Queue[tuple[int, Article]] = asyncio.Queue()
    for idx, article in enumerate(articles, start=1):
        queue.put_nowait((idx, article))

    results: list[Result] = []
    print_lock = asyncio.Lock()
    result_lock = asyncio.Lock()
    total = len(articles)

    timeout = httpx.Timeout(
        connect=20.0,
        read=float(args.http_timeout),
        write=30.0,
        pool=20.0,
    )

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:

        async def worker(worker_id: int) -> None:
            while True:
                try:
                    idx, article = queue.get_nowait()
                except asyncio.QueueEmpty:
                    return

                async with print_lock:
                    print(f"[{idx}/{total}] id={article.id} fetch {article.url}", flush=True)

                try:
                    result = await process_article(
                        client=client,
                        article=article,
                        output_root=output_root,
                        cache_root=cache_root,
                        config=config,
                        api_key=api_key,
                        force=args.force,
                        refresh=args.refresh,
                        firecrawl_timeout_ms=args.firecrawl_timeout_ms,
                        max_retries=args.max_retries,
                        min_words=args.min_words,
                    )
                except Exception as exc:
                    result = Result(
                        article_id=article.id,
                        title=article.title,
                        url=article.url,
                        status="failed",
                        error=f"{type(exc).__name__}: {exc}",
                    )

                append_jsonl(log_path, result_event(result))

                async with result_lock:
                    results.append(result)

                async with print_lock:
                    if result.status == "skipped":
                        print(f"[skip] id={article.id} existing={result.output_path}", flush=True)
                    elif result.status in {"failed", "rejected"}:
                        print(f"[{result.status}] id={article.id} {result.error}", flush=True)
                    else:
                        warnings = ",".join(result.warning_flags or []) or "none"
                        gates = ",".join(result.gate_failures or []) or "none"
                        print(
                            f"[done] id={article.id} status={result.status} "
                            f"strategy={result.strategy} source={result.source} "
                            f"words={result.word_count} attempts={result.attempts} "
                            f"warnings={warnings} gates={gates}",
                            flush=True,
                        )
                queue.task_done()

        workers = [
            asyncio.create_task(worker(worker_id))
            for worker_id in range(1, min(args.concurrency, total) + 1)
        ]
        await asyncio.gather(*workers)

    return sorted(
        results,
        key=lambda item: (0, int(item.article_id)) if item.article_id.isdigit() else (1, item.article_id),
    )


def build_summary(results: list[Result], selected_count: int, output_root: Path, cache_root: Path) -> dict[str, Any]:
    statuses = sorted({result.status for result in results})
    counts = {status: sum(1 for result in results if result.status == status) for status in statuses}
    warning_counts: dict[str, int] = {}
    gate_failure_counts: dict[str, int] = {}
    strategy_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    for result in results:
        strategy_counts[result.strategy] = strategy_counts.get(result.strategy, 0) + 1
        source_counts[result.source] = source_counts.get(result.source, 0) + 1
        for warning in result.warning_flags or []:
            warning_counts[warning] = warning_counts.get(warning, 0) + 1
        for failure in result.gate_failures or []:
            gate_failure_counts[failure] = gate_failure_counts.get(failure, 0) + 1

    return {
        "timestamp": iso_utc_now(),
        "selected": selected_count,
        "counts": counts,
        "strategy_counts": dict(sorted(strategy_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "warning_counts": dict(sorted(warning_counts.items())),
        "gate_failure_counts": dict(sorted(gate_failure_counts.items())),
        "failed_ids": [result.article_id for result in results if result.status == "failed"],
        "rejected_ids": [result.article_id for result in results if result.status == "rejected"],
        "suspicious_ids": [
            result.article_id
            for result in results
            if result.status in {"saved_suspicious", "saved_failed_gate"}
        ],
        "output_root": str(output_root),
        "cache_root": str(cache_root),
        "results": [result_event(result) for result in results],
    }


def print_summary(summary: dict[str, Any]) -> None:
    print("\nSummary")
    print(f"  selected: {summary['selected']}")
    print("  counts:")
    for status, count in summary["counts"].items():
        print(f"    {status}: {count}")
    print("  strategies:")
    for strategy, count in summary["strategy_counts"].items():
        print(f"    {strategy}: {count}")
    print("  sources:")
    for source, count in summary["source_counts"].items():
        print(f"    {source}: {count}")
    print(f"  output_root: {summary['output_root']}")
    print(f"  cache_root: {summary['cache_root']}")
    if summary["warning_counts"]:
        print("  warning_counts:")
        for warning, count in summary["warning_counts"].items():
            print(f"    {warning}: {count}")
    if summary["gate_failure_counts"]:
        print("  gate_failure_counts:")
        for failure, count in summary["gate_failure_counts"].items():
            print(f"    {failure}: {count}")
    if summary["failed_ids"]:
        print(f"  failed_ids: {', '.join(summary['failed_ids'])}")
    if summary["rejected_ids"]:
        print(f"  rejected_ids: {', '.join(summary['rejected_ids'])}")
    if summary["suspicious_ids"]:
        print(f"  suspicious_ids: {', '.join(summary['suspicious_ids'])}")


def default_input_path(script_dir: Path) -> Path:
    candidates = [
        script_dir / "url.json",
        script_dir.parent / "url.json",
        script_dir.parent / "jina" / "url.json",
        script_dir.parent / "jina" / "__pycache__" / "url.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def parse_args(argv: list[str]) -> argparse.Namespace:
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="Scrape article URLs with Firecrawl into auditable LLM-ready markdown."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_input_path(script_dir),
        help="Path to JSON list of {id, title, url} objects.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=script_dir / "routes.json",
        help="Editable host-routing config.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "output",
        help="Output directory. Defaults to cg_pipeline/article/firecrawl/output.",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=script_dir / ".cache",
        help="Local request cache keyed by normalized URL plus Firecrawl params.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate artifacts even if output markdown exists; still uses local cache.",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Bypass local cache and ask Firecrawl for a fresh scrape. This can spend credits.",
    )
    parser.add_argument(
        "--only",
        help="Comma-separated article ids to process, for example: --only 6,22,36",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=f"Maximum concurrent Firecrawl requests. Default: {DEFAULT_CONCURRENCY}.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Retries for transient failures. Default: {DEFAULT_MAX_RETRIES}.",
    )
    parser.add_argument(
        "--firecrawl-timeout-ms",
        type=int,
        default=DEFAULT_FIRECRAWL_TIMEOUT_MS,
        help=f"Firecrawl timeout in milliseconds. Default: {DEFAULT_FIRECRAWL_TIMEOUT_MS}.",
    )
    parser.add_argument(
        "--http-timeout",
        type=int,
        default=DEFAULT_HTTP_TIMEOUT_SECONDS,
        help=f"Client read timeout in seconds. Default: {DEFAULT_HTTP_TIMEOUT_SECONDS}.",
    )
    parser.add_argument(
        "--min-words",
        type=int,
        default=DEFAULT_MIN_WORDS,
        help=f"Flag output as short below this word count. Default: {DEFAULT_MIN_WORDS}.",
    )
    args = parser.parse_args(argv)

    if args.concurrency < 1:
        raise SystemExit("--concurrency must be >= 1")
    if args.max_retries < 0:
        raise SystemExit("--max-retries must be >= 0")
    if not (1_000 <= args.firecrawl_timeout_ms <= 300_000):
        raise SystemExit("--firecrawl-timeout-ms must be between 1000 and 300000")
    if args.http_timeout * 1000 < args.firecrawl_timeout_ms:
        raise SystemExit("--http-timeout must be >= --firecrawl-timeout-ms")
    if args.min_words < 0:
        raise SystemExit("--min-words must be >= 0")

    args.input = args.input.resolve()
    args.config = args.config.resolve()
    args.output = args.output.resolve()
    args.cache = args.cache.resolve()
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])

    env_path = Path(__file__).resolve().parents[2] / ".env"
    load_dotenv(env_path)
    load_dotenv()

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print(
            f"Missing FIRECRAWL_API_KEY. Add it to {env_path} or export it in the environment.",
            file=sys.stderr,
        )
        return 2

    try:
        only_ids = parse_only_ids(args.only)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    config = load_config(args.config)
    articles, missing_requested = load_articles(args.input, only_ids)
    if missing_requested:
        print(f"Warning: requested ids not found: {', '.join(sorted(missing_requested))}")
    if not articles:
        print("No articles selected.")
        return 0

    print(
        f"Processing {len(articles)} article(s) with concurrency={args.concurrency}, "
        f"force={args.force}, refresh={args.refresh}, output={args.output}, cache={args.cache}"
    )

    results = asyncio.run(run_batch(args, articles, api_key, config))
    summary = build_summary(
        results,
        selected_count=len(articles),
        output_root=args.output,
        cache_root=args.cache,
    )
    summary_path = args.output / "summary.json"
    atomic_write_text(summary_path, json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    print_summary(summary)
    print(f"  summary_json: {summary_path}")
    print(f"  run_log_jsonl: {args.output / 'run_log.jsonl'}")
    return 1 if summary["failed_ids"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
