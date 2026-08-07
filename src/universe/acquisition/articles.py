"""Acquire article Markdown through Firecrawl's synchronous scrape endpoint."""

import os
import time

import httpx

from universe.acquisition.gates import PAYWALL_HEURISTICS

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v2/scrape"
RETRY_BACKOFF_SECONDS = (2.0, 6.0, 18.0)
MAX_RETRIES = len(RETRY_BACKOFF_SECONDS)


class _TransientStatus(Exception):
    def __init__(self, status_code: int):
        self.status_code = status_code
        super().__init__(f"transient HTTP status {status_code}")


def _failure_after_retries(exc: Exception) -> str:
    if isinstance(exc, _TransientStatus) and 500 <= exc.status_code < 600:
        return "http_status_5xx"
    return "fetch_failed"


def fetch_article(source_row: dict) -> tuple[str | None, str | None]:
    """Return extracted Markdown or one stable acquisition failure code."""
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        return None, "missing_credentials"

    try:
        canonical_url = source_row["identity"]["canonical_url"]
    except (KeyError, TypeError):
        return None, "fetch_failed"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = httpx.post(
                FIRECRAWL_SCRAPE_URL,
                headers=headers,
                json={"url": canonical_url, "formats": ["markdown"]},
                timeout=30.0,
            )
            if response.status_code == 429 or 500 <= response.status_code < 600:
                raise _TransientStatus(response.status_code)
            if 400 <= response.status_code < 500:
                return None, "http_status_4xx"
            if response.status_code != 200:
                return None, "fetch_failed"

            markdown = response.json()["data"]["markdown"]
            if not isinstance(markdown, str) or not markdown.strip():
                return None, "empty_content"
            if any(pattern.search(markdown) for pattern in PAYWALL_HEURISTICS):
                return None, "bot_wall_detected"
            return markdown, None
        except (httpx.TransportError, _TransientStatus) as exc:
            if attempt == MAX_RETRIES:
                return None, _failure_after_retries(exc)
            time.sleep(RETRY_BACKOFF_SECONDS[attempt])
        except Exception:
            return None, "fetch_failed"

    return None, "fetch_failed"
