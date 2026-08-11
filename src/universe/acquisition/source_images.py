"""One source-level multimodal call for all downloaded article images."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from universe.model_client import ModelClient, ModelError

PROMPTS_DIR = Path(__file__).resolve().parents[3] / "prompts"
PROMPT_PATH = PROMPTS_DIR / "source-image-analysis" / "v003.md"
TOOL_PATH = PROMPTS_DIR / "source-image-analysis" / "tool-v001.json"
PROMPT_REF = "source-image-analysis/v003"

RETAIN_REASONS = {"information", "context", "insufficient_evidence"}
DROP_REASONS = {"decoration", "interface", "advertising", "no_unique_content"}


@dataclass(frozen=True)
class SourceImageInput:
    image_id: str
    alt_text: str
    source_url: str
    model_image_url: str
    asset_sha256: str
    model_input_sha256: str


@dataclass(frozen=True)
class SourceImageAnalysis:
    image_id: str
    retain: bool
    reason_code: str
    ocr: str | None
    description: str | None
    limitations: str | None


@dataclass(frozen=True)
class SourceImageBatchResult:
    analyses: Mapping[str, SourceImageAnalysis]
    unresolved: Mapping[str, str]
    requested_model: str
    response_model: str | None
    provider: str
    usage: Mapping[str, Any]
    duration_ms: int
    prompt_ref: str
    prompt_sha: str
    input_manifest_hash: str


def prompt_stamp() -> tuple[str, str, str]:
    raw = PROMPT_PATH.read_bytes()
    return PROMPT_REF, hashlib.sha256(raw).hexdigest(), raw.decode("utf-8")


def load_source_image_tool() -> dict:
    function = json.loads(TOOL_PATH.read_text())
    return {"type": "function", "function": function}


def input_manifest_hash(markdown: str, images: list[SourceImageInput]) -> str:
    manifest = {
        "source_sha256": hashlib.sha256(markdown.encode()).hexdigest(),
        "images": [
            {
                "image_id": image.image_id,
                "asset_sha256": image.asset_sha256,
                "model_input_sha256": image.model_input_sha256,
                "source_url": image.source_url,
            }
            for image in images
        ],
    }
    return hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ModelError(f"source image {field} must be text or null")
    stripped = value.strip()
    return stripped or None


def _parse_one(value: Any, expected_ids: set[str]) -> SourceImageAnalysis:
    fields = {"image_id", "retain", "reason_code", "ocr", "description", "limitations"}
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ModelError("source image result has an invalid shape")
    image_id = value["image_id"]
    retain = value["retain"]
    reason = value["reason_code"]
    if not isinstance(image_id, str) or image_id not in expected_ids:
        raise ModelError("source image result references an unknown image_id")
    if not isinstance(retain, bool) or not isinstance(reason, str):
        raise ModelError("source image decision is invalid")
    if retain and reason not in RETAIN_REASONS:
        raise ModelError("retained source image has an incompatible reason_code")
    if not retain and reason not in DROP_REASONS:
        raise ModelError("discarded source image has an incompatible reason_code")
    ocr = _optional_text(value["ocr"], "ocr")
    description = _optional_text(value["description"], "description")
    limitations = _optional_text(value["limitations"], "limitations")
    if retain and not (ocr or description or limitations):
        raise ModelError("retained source image has no usable analysis")
    if reason == "insufficient_evidence" and not retain:
        raise ModelError("insufficient evidence must preserve the source image")
    return SourceImageAnalysis(
        image_id=image_id,
        retain=retain,
        reason_code=reason,
        ocr=ocr,
        description=description,
        limitations=limitations,
    )


def reconcile_source_image_results(
    arguments: Mapping[str, Any], expected_ids: list[str]
) -> tuple[dict[str, SourceImageAnalysis], dict[str, str]]:
    if not isinstance(arguments, Mapping) or set(arguments) != {"images"}:
        raise ModelError("report_source_images returned an invalid object")
    values = arguments["images"]
    if not isinstance(values, list):
        raise ModelError("report_source_images images must be an array")
    expected = set(expected_ids)
    analyses: dict[str, SourceImageAnalysis] = {}
    unresolved: dict[str, str] = {}
    seen: set[str] = set()
    for value in values:
        raw_id = value.get("image_id") if isinstance(value, Mapping) else None
        if not isinstance(raw_id, str) or raw_id not in expected:
            continue
        if raw_id in seen:
            analyses.pop(raw_id, None)
            unresolved[raw_id] = "duplicate_result"
            continue
        seen.add(raw_id)
        try:
            analyses[raw_id] = _parse_one(value, expected)
        except ModelError:
            unresolved[raw_id] = "invalid_result"
    for image_id in expected_ids:
        if image_id not in analyses and image_id not in unresolved:
            unresolved[image_id] = "missing_result"
    return analyses, unresolved


def analyze_source_images(
    markdown: str,
    images: list[SourceImageInput],
    *,
    client: ModelClient,
    prompt_spec: tuple[str, str, str] | None = None,
) -> SourceImageBatchResult:
    if not images:
        raise ValueError("source image analysis requires at least one image")
    ids = [image.image_id for image in images]
    if len(ids) != len(set(ids)):
        raise ValueError("source image inputs contain duplicate image_id values")
    prompt_ref, prompt_sha, template = prompt_spec or prompt_stamp()
    prompt = template.replace("{{body}}", markdown)
    content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
    for image in images:
        content.extend(
            [
                {
                    "type": "text",
                    "text": (
                        f"image_id: {image.image_id}\n"
                        f"alt_text: {image.alt_text or '(blank)'}\n"
                        f"source_url: {image.source_url}"
                    ),
                },
                {
                    "type": "image_url",
                    "image_url": {"url": image.model_image_url, "detail": "high"},
                },
            ]
        )
    arguments, raw_usage, duration_ms = client.call_tool(
        [{"role": "user", "content": content}], load_source_image_tool()
    )
    analyses, unresolved = reconcile_source_image_results(arguments, ids)
    response_model = raw_usage.get("response_model")
    provider = raw_usage.get("provider") or "openrouter"
    usage = {
        key: value
        for key, value in raw_usage.items()
        if key not in {"provider", "response_model"}
    }
    return SourceImageBatchResult(
        analyses=analyses,
        unresolved=unresolved,
        requested_model=client.model,
        response_model=str(response_model) if response_model else None,
        provider=str(provider),
        usage=usage,
        duration_ms=duration_ms,
        prompt_ref=prompt_ref,
        prompt_sha=prompt_sha,
        input_manifest_hash=input_manifest_hash(markdown, images),
    )
