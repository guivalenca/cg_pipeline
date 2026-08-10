"""Environment-backed settings shared by provider adapters.

The project historically used ``OPEN_ROUTER_API_KEY`` while the CG Pipeline
uses ``OPENROUTER_API_KEY``.  Both spellings intentionally resolve to the same
setting so moving an existing ``.env`` does not silently disable a provider.
"""

import os
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=False)


def firecrawl_api_key() -> str | None:
    """Return the configured Firecrawl key, if any."""
    return os.environ.get("FIRECRAWL_API_KEY")


def private_pdf_figure_localization_enabled() -> bool:
    """Require an independent opt-in before exporting candidate page renders."""
    return (
        os.environ.get("OPENROUTER_ALLOW_PRIVATE_PDF_PAGE_UPLOADS", "").strip()
        == "1"
    )


def openrouter_api_key() -> str | None:
    """Accept the common OpenRouter key spellings used by both repositories."""
    return (
        os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("OPEN_ROUTER_API_KEY")
        or os.environ.get("MODEL_API_KEY")
    )


def acquisition_poll_seconds() -> float:
    """Delay between empty queue polls for the local/Railway worker."""
    try:
        value = float(os.environ.get("ACQUISITION_POLL_SECONDS", "1.0"))
    except ValueError:
        return 1.0
    return max(0.1, value)


def acquisition_lease_minutes() -> int:
    """How soon another worker may reclaim a job after a dead worker."""
    try:
        value = int(os.environ.get("ACQUISITION_STALE_MINUTES", "15"))
    except ValueError:
        return 15
    return max(1, value)


def article_image_model() -> str:
    """Vision-capable OpenRouter model for the optional article branch."""
    return (
        os.environ.get("CONCEPT_UNIVERSE_ARTICLE_IMAGE_MODEL", "").strip()
        or os.environ.get("CONCEPT_UNIVERSE_MANUAL_IMAGE_MODEL", "").strip()
        or "google/gemini-2.5-flash"
    )


def source_cleanup_model() -> str:
    """OpenRouter model used for cuts and passage cleanup after acquisition."""
    return (
        os.environ.get("CONCEPT_UNIVERSE_SOURCE_CLEANUP_MODEL", "").strip()
        or "deepseek/deepseek-v4-flash"
    )


def source_cleanup_fallback_model() -> str:
    """Independent structured-output fallback for a failed cleanup tool call."""
    return (
        os.environ.get("CONCEPT_UNIVERSE_SOURCE_CLEANUP_FALLBACK_MODEL", "").strip()
        or "google/gemini-2.5-flash"
    )


def openrouter_tool_provider_routing() -> dict[str, object]:
    """Keep tool calls private while allowing OpenRouter's Auto Exacto routing.

    ``require_parameters`` is deliberately absent. In live requests OpenRouter
    returned HTTP 404 for both DeepSeek and Gemini when that filter was paired
    with forced tools, despite both models supporting the request. The named
    ``tool_choice`` remains forced and the application validates/retries it.
    """
    return {
        "allow_fallbacks": True,
        "data_collection": "deny",
    }


def openrouter_multimodal_provider_routing() -> dict[str, object]:
    """Routing compatible with OpenRouter's normalized vision tool calls.

    The request itself still forces one named tool in ``ModelClient.call_tool``.
    ``require_parameters`` is intentionally absent: OpenRouter currently rejects
    Gemini vision requests with HTTP 404 when that metadata filter is enabled,
    even though the same endpoint honors the forced multimodal tool call.
    """
    return {
        "allow_fallbacks": True,
        "data_collection": "deny",
    }
