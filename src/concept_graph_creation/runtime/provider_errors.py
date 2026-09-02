from __future__ import annotations


_TRANSIENT_HTTP_CODES = (408, 425, 429, 500, 502, 503, 504, 529)
_TRANSIENT_MESSAGE_MARKERS = (
    "OpenRouter request timed out",
    "OpenRouter request exceeded total wall-clock deadline",
    "OpenRouter request failed",
    "OpenRouter returned an empty message",
    "OpenRouter returned no streaming events",
    "RemoteDisconnected",
    "IncompleteRead",
)


def transient_provider_error_reason(exc: BaseException) -> str | None:
    """Return the stable OpenRouter pressure marker for a retryable provider failure."""
    message = str(exc)
    for prefix in ("OpenRouter HTTP", "OpenRouter streaming error"):
        for code in _TRANSIENT_HTTP_CODES:
            marker = f"{prefix} {code}"
            if marker in message:
                return marker
    for marker in _TRANSIENT_MESSAGE_MARKERS:
        if marker in message:
            return marker
    return None


def is_transient_provider_error(exc: BaseException) -> bool:
    return transient_provider_error_reason(exc) is not None
