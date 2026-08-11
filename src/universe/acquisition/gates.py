"""Stable acquisition gate codes and reports."""

import re
from typing import Literal

GATE_CODES = {
    "auth_wall_detected": {
        "description": "The source needs a signed-in account before it can be read.",
        "blocking": True,
    },
    "bot_wall_detected": {
        "description": "The source blocked the automated reader.",
        "blocking": True,
    },
    "error_page_detected": {
        "description": "The source returned an error page instead of its content.",
        "blocking": True,
    },
    "http_status_4xx": {
        "description": "The source rejected the request or could not be found.",
        "blocking": True,
    },
    "http_status_5xx": {
        "description": "The source service failed while we were fetching it.",
        "blocking": True,
    },
    "missing_credentials": {
        "description": "Firecrawl credentials are not configured.",
        "blocking": True,
    },
    "unsupported_media_kind": {
        "description": "This kind of source does not have a fetcher yet.",
        "blocking": True,
    },
    "missing_concrete_scope": {
        "description": "The book needs a chapter, page range, or unit to fetch.",
        "blocking": True,
    },
    "manual_access_required": {
        "description": "A person must open this source and provide the content.",
        "blocking": True,
    },
    "empty_content": {
        "description": "The fetch completed but returned no readable content.",
        "blocking": True,
    },
    "fetch_failed": {
        "description": "The source could not be fetched after the available attempts.",
        "blocking": True,
    },
    "video_metadata_unavailable": {
        "description": "YouTube metadata could not be read; retry preflight.",
        "blocking": True,
    },
    "video_caption_download_failed": {
        "description": "The listed publisher caption track could not be downloaded.",
        "blocking": True,
    },
    "video_caption_parse_failed": {
        "description": "The publisher caption track contained no usable timed cues.",
        "blocking": True,
    },
    "video_duration_approval_required": {
        "description": "Paid transcription requires explicit operator authorization.",
        "blocking": True,
    },
    "video_duration_unknown": {
        "description": "The video duration is unknown and requires operator review.",
        "blocking": True,
    },
    "video_audio_download_failed": {
        "description": "The YouTube audio-only download failed.",
        "blocking": True,
    },
    "video_ffmpeg_unavailable": {
        "description": "ffmpeg and ffprobe are required for bounded audio chunks.",
        "blocking": True,
    },
    "video_ffmpeg_failed": {
        "description": "ffmpeg could not normalize and split the source audio.",
        "blocking": True,
    },
    "video_stt_authentication_failed": {
        "description": "OpenRouter rejected or lacks transcription credentials.",
        "blocking": True,
    },
    "video_stt_rate_limited": {
        "description": "OpenRouter rate-limited a speech-to-text chunk.",
        "blocking": True,
    },
    "video_stt_provider_failure": {
        "description": "OpenRouter could not route or complete a speech-to-text chunk.",
        "blocking": True,
    },
    "video_stt_chunk_failed": {
        "description": "One or more independently retryable transcript chunks failed.",
        "blocking": True,
    },
    "video_stt_empty_transcript": {
        "description": "Speech-to-text returned no usable transcript text.",
        "blocking": True,
    },
    "video_stt_language_mismatch": {
        "description": "A transcript chunk did not preserve the expected language.",
        "blocking": True,
    },
    "video_transcript_assembly_failed": {
        "description": "Timed transcript facts could not be assembled into Markdown.",
        "blocking": True,
    },
}

PAYWALL_HEURISTICS = [
    re.compile(
        r"\bpaywall\b|\b(?:subscribe|subscription)\s+(?:to\s+)?(?:continue|read|unlock)",
        re.I,
    ),
    re.compile(r"\b(?:premium|subscriber[- ]only|members?[- ]only)\s+content\b", re.I),
    re.compile(r"\baccess\s+(?:is\s+)?denied\b", re.I),
    re.compile(r"\b(?:sign|log)\s*in\s+(?:to\s+)?(?:continue|read|view|access)\b", re.I),
    re.compile(r"<(?:form|input)\b[^>]*(?:login|password|sign[-_ ]?in)", re.I),
    re.compile(
        r"\b(?:40[134]\s+(?:error|forbidden|not found)|internal server error|"
        r"something went wrong|captcha|verify\s+you(?:'re| are)\s+human|"
        r"checking\s+your\s+browser|enable\s+javascript\s+and\s+cookies\s+to\s+continue)\b",
        re.I,
    ),
]


def build_gate_report(
    status: Literal["passed", "passed_with_warnings", "failed_gate"],
    failures: list[str],
    warnings: list[str],
    notes: str | None,
) -> dict:
    """Return the uniform report stamped on every acquisition run item."""
    return {
        "status": status,
        "failures": failures,
        "warnings": warnings,
        "notes": notes or "",
    }
