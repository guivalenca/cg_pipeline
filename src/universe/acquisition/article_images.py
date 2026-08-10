"""Pure article-image interpretation and canonical Markdown rewriting."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit

from universe.model_client import ModelClient, ModelError


MARKDOWN_IMAGE = re.compile(
    r"!\[(?P<alt>[^\]\n]*)\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
LINKED_MARKDOWN_IMAGE = re.compile(
    r"\[!\[(?P<alt>[^\]\n]*)\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)\]"
    r"\((?P<link_url>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
WEB_CHROME_ALT = re.compile(
    r"^(?:"
    r"(?:site|company|brand)?\s*logo|favicon|"
    r"(?:author|profile|user)\s+(?:avatar|photo)|"
    r"share(?:\s+this)?\s+on\s+(?:facebook|instagram|linkedin|twitter|whatsapp|tiktok)|"
    r"(?:facebook|instagram|linkedin|twitter|whatsapp|tiktok)\s+(?:logo|icon|share button)|"
    r"(?:menu|search|close|social)\s+(?:icon|button)|"
    r"add\s+as\s+favorite\s+google\s+source"
    r")$",
    re.IGNORECASE,
)
WEB_CHROME_FILENAME = re.compile(
    r"^(?:"
    r"logo|favicon|avatar|(?:author|profile|user)[-_]?(?:avatar|photo)|"
    r"(?:facebook|instagram|linkedin|twitter|whatsapp|tiktok)"
    r"(?:[-_]?(?:logo|icon|share))?|"
    r"share[-_]?(?:button|icon|facebook|instagram|linkedin|twitter|whatsapp|tiktok)|"
    r"(?:close|menu|search|preloader|loader|loading|spinner)"
    r"(?:[-_]?(?:icon|button))?"
    r")(?:[-_]?\d+x\d+)?\.(?:avif|gif|jpe?g|png|svg|webp)$",
    re.IGNORECASE,
)

ARTICLE_IMAGE_PROMPT_VERSION = "article-image-analysis.v2"
ARTICLE_IMAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "report_article_image",
        "description": (
            "Report whether one article image carries pedagogical information and "
            "faithfully describe its visible content."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "pedagogical_importance": {
                    "type": "string",
                    "enum": ["important", "not_important", "unavailable"],
                    "description": (
                        "Use not_important for purely decorative content, website "
                        "chrome, advertisements, calls to action, or recommended "
                        "content that does not explain the primary article. Preserve "
                        "uncertain content as important."
                    ),
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Faithful explanation of the visual and its relationships; "
                        "blank only when it is not important or unavailable."
                    ),
                },
                "visible_text": {
                    "type": "string",
                    "description": (
                        "Verbatim meaningful legible text in reading order; blank if none."
                    ),
                },
                "reason": {
                    "type": "string",
                    "description": "Evidence supporting the importance decision.",
                },
                "confidence": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                },
            },
            "required": [
                "pedagogical_importance",
                "description",
                "visible_text",
                "reason",
                "confidence",
            ],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class ArticleImageReference:
    ordinal: int
    alt_text: str
    source_url: str
    original_markdown: str
    start_char: int
    end_char: int
    document_sha256: str
    link_url: str | None = None

    @property
    def raw_sha256(self) -> str:
        return _sha256(self.original_markdown)

    @property
    def reference_id(self) -> str:
        """Stable identity for this exact occurrence in the raw Markdown."""
        return (
            f"article-image-ref:{self.ordinal:04d}:"
            f"{self.raw_sha256[:16]}:{self.document_sha256[:16]}"
        )


@dataclass(frozen=True)
class ArticleImageAnalysis:
    pedagogical_importance: str
    description: str
    visible_text: str
    reason: str
    confidence: str
    limitations: str = ""


@dataclass(frozen=True)
class ArticleImageModelResult:
    analysis: ArticleImageAnalysis
    requested_model: str
    response_model: str | None
    provider: str
    usage: Mapping[str, Any]
    duration_ms: int
    reference_id: str
    source_url: str
    model_image_url: str
    input_sha256: str
    asset_sha256: str | None = None
    prompt_version: str = ARTICLE_IMAGE_PROMPT_VERSION


@dataclass(frozen=True)
class ArticleImageAssociation:
    raw_markdown: str
    canonical_markdown: str
    manifest: Mapping[str, Any]


def extract_markdown_images(markdown: str) -> list[ArticleImageReference]:
    """Return exact Markdown image spans in document order."""
    document_sha256 = _sha256(markdown)
    matches: list[tuple[int, int, str, str, str | None]] = []
    for match in LINKED_MARKDOWN_IMAGE.finditer(markdown):
        matches.append(
            (
                match.start(),
                match.end(),
                match.group("alt"),
                match.group("url"),
                match.group("link_url"),
            )
        )

    linked_spans = [(start, end) for start, end, *_ in matches]
    for match in MARKDOWN_IMAGE.finditer(markdown):
        if any(start <= match.start() and match.end() <= end for start, end in linked_spans):
            continue
        matches.append(
            (
                match.start(),
                match.end(),
                match.group("alt"),
                match.group("url"),
                None,
            )
        )

    return [
        ArticleImageReference(
            ordinal=ordinal,
            alt_text=alt_text.strip(),
            source_url=source_url.strip(),
            original_markdown=markdown[start:end],
            start_char=start,
            end_char=end,
            document_sha256=document_sha256,
            link_url=link_url.strip() if link_url else None,
        )
        for ordinal, (start, end, alt_text, source_url, link_url) in enumerate(
            sorted(matches),
            start=1,
        )
    ]


def deterministic_image_analysis(
    reference: ArticleImageReference,
) -> ArticleImageAnalysis | None:
    """Remove only strong URL/alt/link evidence of website chrome."""
    return deterministic_image_metadata_analysis(
        reference.source_url, reference.alt_text
    )


def deterministic_image_metadata_analysis(
    source_url: str, alt_text: str = ""
) -> ArticleImageAnalysis | None:
    """Classify only exact, auditable interface markers without fuzzy guessing."""
    filename = urlsplit(source_url).path.rsplit("/", 1)[-1]
    if not (
        WEB_CHROME_ALT.fullmatch(alt_text.strip())
        or WEB_CHROME_FILENAME.fullmatch(filename)
    ):
        return None
    return ArticleImageAnalysis(
        pedagogical_importance="not_important",
        description="",
        visible_text="",
        reason="Strong filename or label evidence identifies website chrome.",
        confidence="high",
    )


def analyze_article_image(
    reference: ArticleImageReference,
    *,
    client: ModelClient,
    image_url: str | None = None,
    context: str = "",
    asset_sha256: str | None = None,
) -> ArticleImageModelResult:
    """Analyze one independent image sub-job through a forced tool call."""
    model_image_url = (image_url or reference.source_url).strip()
    if not model_image_url:
        raise ValueError("article image analysis requires an image URL")
    if asset_sha256 is not None and not re.fullmatch(r"[0-9a-f]{64}", asset_sha256):
        raise ValueError("article image analysis requires a valid asset hash")
    normalized_context = context.strip()
    prompt = "\n".join(
        (
            "Analyze this image from an educational article.",
            "Use the principal language of the source.",
            "Do not invent hidden details.",
            "Judge relevance to the primary article, not to the website or its business.",
            "Classify as not_important when the visual is clearly an advertisement, "
            "call to action, subscription or course promotion, related/recommended "
            "content card, author portrait, or website chrome, even when it contains "
            "legible text or promotes educational material.",
            "For not_important return blank description and visible_text fields.",
            "If relevance to the primary article is genuinely uncertain, preserve it "
            "as important with low confidence.",
            f"Markdown alt text: {reference.alt_text or '(blank)'}",
            f"Source image URL: {reference.source_url}",
            f"Surrounding article context:\n{normalized_context}",
        )
    )
    arguments, raw_usage, duration_ms = client.call_tool(
        [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": model_image_url, "detail": "high"},
                    },
                ],
            }
        ],
        ARTICLE_IMAGE_TOOL,
    )
    analysis = _parse_image_analysis(arguments)
    response_model = raw_usage.get("response_model")
    provider = raw_usage.get("provider") or "openrouter"
    usage = {
        key: value
        for key, value in raw_usage.items()
        if key not in {"provider", "response_model"}
    }
    return ArticleImageModelResult(
        analysis=analysis,
        requested_model=client.model,
        response_model=str(response_model) if response_model else None,
        provider=str(provider),
        usage=usage,
        duration_ms=duration_ms,
        reference_id=reference.reference_id,
        source_url=reference.source_url,
        model_image_url=model_image_url,
        input_sha256=_analysis_input_sha256(
            reference=reference,
            model_image_url=model_image_url,
            context=normalized_context,
            asset_sha256=asset_sha256,
        ),
        asset_sha256=asset_sha256,
    )


def _parse_image_analysis(arguments: Mapping[str, Any]) -> ArticleImageAnalysis:
    fields = {
        "pedagogical_importance",
        "description",
        "visible_text",
        "reason",
        "confidence",
    }
    if set(arguments) != fields or any(
        not isinstance(arguments.get(field), str) for field in fields
    ):
        raise ModelError("report_article_image returned an invalid object")
    importance = arguments["pedagogical_importance"].strip()
    description = arguments["description"].strip()
    visible_text = arguments["visible_text"].strip()
    reason = arguments["reason"].strip()
    confidence = arguments["confidence"].strip()
    # A model occasionally calls an image decorative while simultaneously
    # extracting meaningful text or a description from it.  That contradiction
    # is evidence against deletion.  Fail open: preserve it as potentially
    # important and lower confidence rather than throwing away the visual fact.
    if importance != "important" and (description or visible_text):
        importance = "important"
        description = description or "The image contains meaningful legible text."
        reason = (
            f"{reason} Preserved because the response also contained derived visual content."
        ).strip()
        confidence = "low"
    analysis = ArticleImageAnalysis(
        pedagogical_importance=importance,
        description=description,
        visible_text=visible_text,
        reason=reason,
        confidence=confidence,
    )
    if analysis.pedagogical_importance not in {
        "important",
        "not_important",
        "unavailable",
    }:
        raise ModelError("report_article_image returned invalid pedagogical_importance")
    if analysis.confidence not in {"low", "medium", "high"}:
        raise ModelError("report_article_image returned invalid confidence")
    if not analysis.reason:
        raise ModelError("report_article_image returned an empty reason")
    if analysis.pedagogical_importance == "important" and not analysis.description:
        raise ModelError("important article image requires a description")
    if analysis.pedagogical_importance != "important" and (
        analysis.description or analysis.visible_text
    ):
        raise ModelError("non-important article image cannot carry derived content")
    return analysis


def associate_article_images(
    raw_markdown: str,
    *,
    analyses: Mapping[int, ArticleImageAnalysis | ArticleImageModelResult],
    local_url_for: Callable[[ArticleImageReference], str | None],
) -> ArticleImageAssociation:
    """Optionally associate completed image sub-jobs with an article artifact.

    This function has no acquisition lifecycle role: raw article Markdown can
    be finalized before it is called, and missing analyses preserve images.
    """
    references = extract_markdown_images(raw_markdown)
    known_ordinals = {reference.ordinal for reference in references}
    unknown_ordinals = set(analyses) - known_ordinals
    if unknown_ordinals:
        raise ValueError(f"image analyses reference unknown ordinals: {unknown_ordinals}")

    prepared: list[tuple[ArticleImageReference, str, dict[str, Any]]] = []
    for reference in references:
        supplied = analyses.get(reference.ordinal)
        model_result = supplied if isinstance(supplied, ArticleImageModelResult) else None
        if model_result:
            _validate_model_result_binding(reference, model_result)
        analysis = model_result.analysis if model_result else supplied
        decision_source = "model" if model_result else "supplied"
        if analysis is not None:
            _validate_association_analysis(analysis)

        if (
            analysis
            and analysis.pedagogical_importance == "not_important"
            and analysis.confidence == "high"
        ):
            replacement = ""
            local_url = None
            action = "removed_decorative"
        else:
            local_url = local_url_for(reference)
            has_local_url = isinstance(local_url, str) and bool(local_url.strip())
            if has_local_url:
                local_url = local_url.strip()
                local_image = f"![{reference.alt_text}]({local_url})"
                if reference.link_url:
                    local_image = f"[{local_image}]({reference.link_url})"
            else:
                local_url = None
                local_image = reference.original_markdown
            if analysis and analysis.pedagogical_importance == "important":
                summary_lines = []
                if analysis.description:
                    summary_lines.append(f"Image description: {analysis.description}")
                if analysis.visible_text:
                    summary_lines.append(f"OCR: {analysis.visible_text}")
                if analysis.limitations:
                    summary_lines.append(f"Image limitations: {analysis.limitations}")
                replacement = local_image + "\n" + "\n".join(summary_lines)
                action = "summarized" if has_local_url else "summarized_without_local"
            elif analysis and analysis.pedagogical_importance == "not_important":
                replacement = local_image
                action = f"preserved_{analysis.confidence}_confidence"
            elif analysis and analysis.pedagogical_importance == "unavailable":
                replacement = local_image + "\nImage analysis: unresolved"
                action = (
                    "preserved_unavailable"
                    if has_local_url
                    else "preserved_original_missing_local"
                )
            else:
                replacement = local_image + "\nImage analysis: unresolved"
                action = (
                    "preserved_unanalyzed"
                    if has_local_url
                    else "preserved_original_missing_local"
                )

        item: dict[str, Any] = {
            "ordinal": reference.ordinal,
            "source_url": reference.source_url,
            "local_url": local_url,
            "start_char": reference.start_char,
            "end_char": reference.end_char,
            "reference_id": reference.reference_id,
            "raw_reference_sha256": reference.raw_sha256,
            "replacement_sha256": _sha256(replacement),
            "action": action,
            "decision_source": decision_source,
            "analysis": asdict(analysis) if analysis else None,
        }
        if model_result:
            item["model"] = {
                "requested": model_result.requested_model,
                "response": model_result.response_model,
                "provider": model_result.provider,
                "prompt_version": model_result.prompt_version,
                "usage": dict(model_result.usage),
                "duration_ms": model_result.duration_ms,
                "reference_id": model_result.reference_id,
                "source_url": model_result.source_url,
                # Local assets reach the model as data URLs. Persisting that
                # transport value would duplicate the binary inside JSON.
                "model_image_transport": _model_image_transport(
                    model_result.model_image_url
                ),
                "input_sha256": model_result.input_sha256,
                "asset_sha256": model_result.asset_sha256,
            }
        prepared.append((reference, replacement, item))

    canonical_markdown = raw_markdown
    for reference, replacement, _item in reversed(prepared):
        canonical_markdown = (
            canonical_markdown[: reference.start_char]
            + replacement
            + canonical_markdown[reference.end_char :]
        )
    manifest = {
        "schema_version": "article-image-association.v1",
        "raw_sha256": _sha256(raw_markdown),
        "canonical_sha256": _sha256(canonical_markdown),
        "image_count": len(references),
        "images": [item for _reference, _replacement, item in prepared],
    }
    return ArticleImageAssociation(
        raw_markdown=raw_markdown,
        canonical_markdown=canonical_markdown,
        manifest=manifest,
    )


def _validate_association_analysis(analysis: ArticleImageAnalysis) -> None:
    if analysis.pedagogical_importance not in {
        "important",
        "not_important",
        "unavailable",
    }:
        raise ValueError("invalid article image importance")
    if analysis.confidence not in {"low", "medium", "high"} or not analysis.reason:
        raise ValueError("invalid article image confidence or reason")
    if analysis.pedagogical_importance == "important" and not (
        analysis.description or analysis.visible_text or analysis.limitations
    ):
        raise ValueError("important article image requires derived content")
    if analysis.pedagogical_importance != "important" and (
        analysis.description or analysis.visible_text
    ):
        raise ValueError("non-important article image cannot carry derived content")


def _validate_model_result_binding(
    reference: ArticleImageReference,
    result: ArticleImageModelResult,
) -> None:
    """Fail closed if a durable image result is attached to another occurrence."""
    if (
        result.reference_id != reference.reference_id
        or result.source_url != reference.source_url
    ):
        raise ValueError(
            "article image model result does not match the Markdown reference"
        )
    if not result.model_image_url.strip() or not re.fullmatch(
        r"[0-9a-f]{64}", result.input_sha256
    ):
        raise ValueError("article image model result has invalid input identity")
    if result.asset_sha256 is not None and not re.fullmatch(
        r"[0-9a-f]{64}", result.asset_sha256
    ):
        raise ValueError("article image model result has invalid asset hash")


def _analysis_input_sha256(
    *,
    reference: ArticleImageReference,
    model_image_url: str,
    context: str,
    asset_sha256: str | None,
) -> str:
    identity = {
        "prompt_version": ARTICLE_IMAGE_PROMPT_VERSION,
        "reference_id": reference.reference_id,
        "raw_reference_sha256": reference.raw_sha256,
        "source_url": reference.source_url,
        "model_image_url": model_image_url,
        "context_sha256": _sha256(context),
        "asset_sha256": asset_sha256,
    }
    return _sha256(json.dumps(identity, ensure_ascii=False, sort_keys=True))


def _model_image_transport(value: str) -> str:
    lowered = value.strip().lower()
    if lowered.startswith("data:"):
        return "data_url"
    if lowered.startswith(("https://", "http://")):
        return "remote_url"
    return "other"


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
