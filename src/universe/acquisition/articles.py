"""Acquire article Markdown through Firecrawl's synchronous scrape endpoint.

The stable failure code drives UI actions.  Structured diagnostics retain the
useful distinction between a 404, an access denial, a rate limit and a broken
provider response without exposing response bodies or making callers parse an
exception string.
"""

import re
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import httpx

from universe.acquisition.gates import PAYWALL_HEURISTICS
from universe.settings import firecrawl_api_key

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"
RETRY_BACKOFF_SECONDS = (2.0, 6.0, 18.0)
MAX_RETRIES = len(RETRY_BACKOFF_SECONDS)
RETRYABLE_STATUSES = {408, 429, 500, 502, 503, 504}

AUTH_WALL = re.compile(
    r"\bpaywall\b|\b(?:subscribe|subscription)\s+(?:to\s+)?(?:continue|read|unlock)|"
    r"\b(?:premium|subscriber[- ]only|members?[- ]only)\s+content\b|"
    r"\b(?:sign|log)\s*in\s+(?:to\s+)?(?:continue|read|view|access)\b|"
    r"<(?:form|input)\b[^>]*(?:login|password|sign[-_ ]?in)",
    re.I,
)
BOT_WALL = re.compile(
    r"\bcaptcha\b|verify\s+you(?:'re| are)\s+human|checking\s+your\s+browser|"
    r"enable\s+javascript\s+and\s+cookies\s+to\s+continue|anti[- ]?bot|"
    r"blocked\s+by\s+(?:the\s+)?(?:site|website|source)",
    re.I,
)
ERROR_PAGE = re.compile(
    r"\b40[134]\s+(?:error|forbidden|not found)\b|\binternal server error\b|"
    r"\bsomething went wrong\b",
    re.I,
)


@dataclass(frozen=True)
class ArticleFetch:
    markdown: str | None
    failure_code: str | None
    attempts: int
    diagnostics: dict[str, Any]
    raw_markdown: str | None = None
    image_urls: tuple[str, ...] = ()

    @property
    def succeeded(self) -> bool:
        return self.markdown is not None and self.failure_code is None


class _TransientStatus(Exception):
    def __init__(self, status_code: int, diagnostics: dict[str, Any]):
        self.status_code = status_code
        self.diagnostics = diagnostics
        super().__init__(f"transient HTTP status {status_code}")


def _failure_after_retries(exc: Exception) -> str:
    if isinstance(exc, _TransientStatus) and 500 <= exc.status_code < 600:
        return "http_status_5xx"
    return "fetch_failed"


def _safe_payload_message(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    for key in ("error", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()[:300]
    return None


def _safe_provider_message(response: httpx.Response) -> str | None:
    """Read Firecrawl's short error message, never an arbitrary page body."""
    try:
        payload = response.json()
    except (ValueError, TypeError):
        return None
    return _safe_payload_message(payload)


def _message_category(message: str | None, fallback: str) -> str:
    """Classify only explicit provider evidence; retain a safe fallback."""
    if not message:
        return fallback
    normalized = message.casefold()
    if "robots.txt" in normalized or "blocked by robots" in normalized:
        return "robots_blocked"
    if any(
        marker in normalized
        for marker in ("captcha", "anti-bot", "anti bot", "verify you are human")
    ):
        return "anti_bot_blocked"
    if any(marker in normalized for marker in ("paywall", "subscribe to", "login required")):
        return "authentication_required"
    missing_markers = ("404" in normalized or "not found" in normalized or "does not exist" in normalized)
    target_markers = ("page", "website", "site", "target", "source", "url")
    if missing_markers and any(marker in normalized for marker in target_markers):
        return "not_found"
    if "timed out" in normalized or "timeout" in normalized:
        return "request_timeout"
    if any(marker in normalized for marker in ("dns", "enotfound", "name resolution")):
        return "dns_failure"
    if any(marker in normalized for marker in ("tls", "ssl", "certificate")):
        return "tls_error"
    if "access denied" in normalized or "forbidden" in normalized:
        return "source_access_denied"
    return fallback


def _provider_code(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    value = payload.get("code")
    return value.strip()[:120] if isinstance(value, str) and value.strip() else None


def _provider_job_id(payload: Any) -> str | None:
    """Retain the safe Firecrawl identifier used by its support/ask endpoint."""
    if not isinstance(payload, dict):
        return None
    candidates: list[Any] = [
        payload.get("scrapeId"),
        payload.get("jobId"),
        payload.get("id"),
    ]
    data = payload.get("data")
    if isinstance(data, dict):
        metadata = data.get("metadata")
        if isinstance(metadata, dict):
            candidates.append(metadata.get("scrapeId"))
    for value in candidates:
        if isinstance(value, str) and value.strip():
            return value.strip()[:200]
    return None


def _failure_code_for_category(category: str, default: str = "fetch_failed") -> str:
    if category == "authentication_required":
        return "auth_wall_detected"
    if category in {"anti_bot_blocked", "robots_blocked", "source_access_denied"}:
        return "bot_wall_detected"
    if category == "error_page":
        return "error_page_detected"
    return default


def _http_diagnostics(response: httpx.Response) -> dict[str, Any]:
    status = response.status_code
    categories = {
        400: "invalid_request",
        401: "provider_authentication",
        402: "insufficient_credits",
        403: "provider_permission",
        404: "provider_resource_not_found",
        408: "request_timeout",
        409: "provider_conflict",
        413: "payload_too_large",
        422: "extraction_rejected",
        429: "rate_limited",
        500: "provider_unavailable",
        502: "provider_unavailable",
        503: "provider_unavailable",
        504: "provider_timeout",
    }
    category = categories.get(status, "http_error")
    message = _safe_provider_message(response)
    # A synchronous scrape can return explicit target evidence in its error
    # string. Do not otherwise confuse Firecrawl's own HTTP status with the
    # target website's status.
    if status == 404:
        category = _message_category(message, category)
    result: dict[str, Any] = {"category": category, "http_status": status}
    if message:
        result["provider_message"] = message
    try:
        payload = response.json()
    except (ValueError, TypeError):
        payload = None
    code = _provider_code(payload)
    if code:
        result["provider_code"] = code
    provider_job_id = _provider_job_id(payload)
    if provider_job_id:
        result["provider_job_id"] = provider_job_id
    retry_after = response.headers.get("retry-after")
    if retry_after:
        try:
            seconds = float(retry_after)
        except ValueError:
            seconds = None
        if seconds is not None and 0 <= seconds <= 300:
            result["retry_after_seconds"] = seconds
    request_id = response.headers.get("x-request-id")
    if request_id:
        result["request_id"] = request_id[:200]
    return result


def _payload_failure_diagnostics(payload: dict[str, Any]) -> dict[str, Any]:
    message = _safe_payload_message(payload)
    result: dict[str, Any] = {
        "category": _message_category(message, "provider_rejected"),
        "http_status": 200,
    }
    if message:
        result["provider_message"] = message
    code = _provider_code(payload)
    if code:
        result["provider_code"] = code
    provider_job_id = _provider_job_id(payload)
    if provider_job_id:
        result["provider_job_id"] = provider_job_id
    return result


def _retry_delay(attempt: int, diagnostics: dict[str, Any] | None = None) -> float:
    retry_after = (diagnostics or {}).get("retry_after_seconds")
    if isinstance(retry_after, (int, float)) and 0 <= retry_after <= 300:
        return float(retry_after)
    return RETRY_BACKOFF_SECONDS[attempt]


def _blocked_markdown(markdown: str) -> tuple[str, dict[str, Any]] | None:
    if AUTH_WALL.search(markdown):
        return "auth_wall_detected", {
            "category": "authentication_required",
            "http_status": 200,
        }
    if BOT_WALL.search(markdown):
        return "bot_wall_detected", {
            "category": "anti_bot_blocked",
            "http_status": 200,
        }
    if ERROR_PAGE.search(markdown):
        return "error_page_detected", {
            "category": "error_page",
            "http_status": 200,
        }
    if any(pattern.search(markdown) for pattern in PAYWALL_HEURISTICS):
        return "bot_wall_detected", {"category": "blocked_content", "http_status": 200}
    return None


def _target_diagnostics(payload: dict) -> dict[str, Any]:
    """Keep Firecrawl's safe target-page metadata separate from API status."""
    data = payload.get("data") if isinstance(payload, dict) else None
    metadata = data.get("metadata") if isinstance(data, dict) else None
    if not isinstance(metadata, dict):
        return {}
    result: dict[str, Any] = {}
    raw_status = metadata.get("statusCode") or metadata.get("status_code")
    try:
        status = int(raw_status) if raw_status is not None else None
    except (TypeError, ValueError):
        status = None
    if status is not None:
        result["target_http_status"] = status
        if status == 404:
            result["category"] = "not_found"
        elif status in (401, 403):
            result["category"] = "source_access_denied"
        elif status == 429:
            result["category"] = "source_rate_limited"
        elif 500 <= status < 600:
            result["category"] = "target_unavailable"
        elif status >= 400:
            result["category"] = "http_error"
    for source_key, target_key in (
        ("sourceURL", "resolved_url"),
        ("url", "resolved_url"),
        ("contentType", "content_type"),
        ("title", "page_title"),
    ):
        value = metadata.get(source_key)
        if isinstance(value, str) and value.strip() and target_key not in result:
            result[target_key] = value.strip()[:500]
    target_error = metadata.get("error")
    if isinstance(target_error, str) and target_error.strip():
        result["target_message"] = target_error.strip()[:500]
        signal_category = _message_category(target_error, "")
        if signal_category:
            result["signal_category"] = signal_category
    provider_job_id = _provider_job_id(payload)
    if provider_job_id:
        result["provider_job_id"] = provider_job_id
    warning = None
    if isinstance(data, dict):
        warning = data.get("warning")
    warning = warning or payload.get("warning")
    if isinstance(warning, str) and warning.strip():
        result["provider_warning"] = warning.strip()[:500]
    return result


def _canonical_url(source_row: dict) -> str | None:
    try:
        value = source_row["identity"]["canonical_url"]
    except (KeyError, TypeError):
        return None
    if not isinstance(value, str):
        return None
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    return value.strip()


def _ordered_image_urls(value: Any) -> tuple[str, ...]:
    """Keep Firecrawl's valid string URLs once, in provider order."""
    if not isinstance(value, list):
        return ()
    ordered: list[str] = []
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, str):
            continue
        image_url = item.strip()
        if not image_url or image_url in seen:
            continue
        ordered.append(image_url)
        seen.add(image_url)
    return tuple(ordered)


def fetch_article_detailed(source_row: dict) -> ArticleFetch:
    """Return Markdown or a stable code plus safe, actionable diagnostics."""
    api_key = firecrawl_api_key()
    if not api_key:
        return ArticleFetch(
            None,
            "missing_credentials",
            0,
            {"category": "configuration", "setting": "FIRECRAWL_API_KEY"},
        )

    canonical_url = _canonical_url(source_row)
    if canonical_url is None:
        return ArticleFetch(
            None,
            "fetch_failed",
            0,
            {"category": "invalid_source_url"},
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for attempt in range(MAX_RETRIES + 1):
        attempts = attempt + 1
        try:
            response = httpx.post(
                FIRECRAWL_SCRAPE_URL,
                headers=headers,
                json={
                    "url": canonical_url,
                    "formats": ["markdown", "images"],
                    "timeout": 60_000,
                },
                timeout=75.0,
            )
            if response.status_code in RETRYABLE_STATUSES:
                raise _TransientStatus(response.status_code, _http_diagnostics(response))
            if 400 <= response.status_code < 500:
                return ArticleFetch(
                    None,
                    "http_status_4xx",
                    attempts,
                    _http_diagnostics(response),
                )
            if response.status_code != 200:
                return ArticleFetch(
                    None,
                    "fetch_failed",
                    attempts,
                    _http_diagnostics(response),
                )

            try:
                payload = response.json()
                if not isinstance(payload, dict):
                    raise KeyError("invalid Firecrawl payload")
                if payload.get("success") is False:
                    diagnostics = _payload_failure_diagnostics(payload)
                    return ArticleFetch(
                        None,
                        _failure_code_for_category(diagnostics["category"]),
                        attempts,
                        diagnostics,
                    )
                target = _target_diagnostics(payload)
                target_status = target.get("target_http_status")
                if target_status == 429 or (
                    isinstance(target_status, int) and target_status >= 500
                ):
                    raise _TransientStatus(target_status, target)
                if isinstance(target_status, int) and 400 <= target_status < 500:
                    return ArticleFetch(
                        None,
                        "http_status_4xx",
                        attempts,
                        target,
                    )
                target_signal = target.get("signal_category")
                if target_signal in {
                    "authentication_required",
                    "anti_bot_blocked",
                    "robots_blocked",
                    "source_access_denied",
                    "not_found",
                    "request_timeout",
                    "dns_failure",
                    "tls_error",
                }:
                    diagnostics = dict(target)
                    diagnostics["category"] = target_signal
                    return ArticleFetch(
                        None,
                        _failure_code_for_category(
                            target_signal,
                            "error_page_detected"
                            if target_signal == "not_found"
                            else "fetch_failed",
                        ),
                        attempts,
                        diagnostics,
                    )
                data = payload["data"]
                if not isinstance(data, dict):
                    raise KeyError("invalid Firecrawl data")
                markdown = data["markdown"]
                image_urls = _ordered_image_urls(data.get("images"))
            except (ValueError, TypeError, KeyError):
                return ArticleFetch(
                    None,
                    "fetch_failed",
                    attempts,
                    {"category": "invalid_provider_response", "http_status": 200},
                )
            if not isinstance(markdown, str) or not markdown.strip():
                return ArticleFetch(
                    None,
                    "empty_content",
                    attempts,
                    {"category": "empty_content", "http_status": 200},
                )
            blocked = _blocked_markdown(markdown)
            if blocked:
                failure_code, diagnostics = blocked
                return ArticleFetch(
                    None,
                    failure_code,
                    attempts,
                    diagnostics,
                )
            success_diagnostics = {
                "category": "success",
                "http_status": 200,
                "markdown_chars": len(markdown),
                "image_count": len(image_urls),
            }
            success_diagnostics.update(_target_diagnostics(payload))
            success_diagnostics["category"] = "success"
            success_diagnostics.setdefault("resolved_url", canonical_url)
            return ArticleFetch(
                markdown,
                None,
                attempts,
                success_diagnostics,
                raw_markdown=markdown,
                image_urls=image_urls,
            )
        except (httpx.TransportError, _TransientStatus) as exc:
            if attempt == MAX_RETRIES:
                if isinstance(exc, _TransientStatus):
                    diagnostic = dict(exc.diagnostics)
                else:
                    diagnostic = {
                        "category": "transport_error",
                        "exception": type(exc).__name__,
                    }
                diagnostic["retries_exhausted"] = True
                return ArticleFetch(
                    None,
                    _failure_after_retries(exc),
                    attempts,
                    diagnostic,
                )
            time.sleep(
                _retry_delay(
                    attempt,
                    exc.diagnostics if isinstance(exc, _TransientStatus) else None,
                )
            )
        except Exception as exc:
            return ArticleFetch(
                None,
                "fetch_failed",
                attempts,
                {"category": "unexpected_error", "exception": type(exc).__name__},
            )

    return ArticleFetch(None, "fetch_failed", MAX_RETRIES + 1, {"category": "unknown"})


def fetch_article(source_row: dict) -> tuple[str | None, str | None]:
    """Compatibility wrapper returning the original two-value result."""
    result = fetch_article_detailed(source_row)
    return result.markdown, result.failure_code
