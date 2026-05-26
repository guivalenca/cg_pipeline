#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
from queue import Empty, Queue
import re
from threading import Lock, Thread
from typing import Any, Protocol
from urllib.parse import urlparse


PIPELINE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXTRACTION_ROOT = PIPELINE_ROOT / "extraction"
DEFAULT_PRE_IMAGE_DIR = DEFAULT_EXTRACTION_ROOT / "pre-image"
DEFAULT_POST_IMAGE_DIR = DEFAULT_EXTRACTION_ROOT / "post-image"
DEFAULT_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "image_preprocessing.md"
DEFAULT_MANIFEST_DIR = PIPELINE_ROOT / "article" / "image-preprocessing"
DEFAULT_MODEL = "gpt-5.4-mini"
DEFAULT_INITIAL_CONCURRENCY = 60
DEFAULT_MIN_CONCURRENCY = 1
DEFAULT_CONCURRENCY_STEP = 10
DEFAULT_IMAGE_DETAIL = "high"
PROMPT_VERSION = "article_image_preprocessing_v1"

MARKDOWN_IMAGE_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
LINKED_MARKDOWN_IMAGE_RE = re.compile(
    r"\[!\[(?P<alt>[^\]]*)\]\((?P<url>[^)\s]+)(?:\s+\"[^\"]*\")?\)\]"
    r"\((?P<link_url>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
)
HTML_IMG_RE = re.compile(r"<img\b[^>]*>", flags=re.IGNORECASE)
HTML_ATTR_RE = re.compile(r"(?P<name>[a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?P<quote>['\"])(?P<value>.*?)(?P=quote)")


@dataclass(frozen=True)
class ImageReference:
    index: int
    kind: str
    original_text: str
    alt_text: str
    url: str
    start: int
    end: int
    link_url: str | None = None


@dataclass(frozen=True)
class ImageAnalysis:
    original_url: str
    pedagogical_importance: str
    reason: str
    replacement_text: str = ""
    confidence: str = ""
    error: str = ""


@dataclass(frozen=True)
class ImagePreprocessResult:
    markdown: str
    manifest: dict[str, Any]


class ImageAnalyzer(Protocol):
    def analyze_images(self, *, markdown: str, image_urls: list[str]) -> list[ImageAnalysis]:
        ...


class OpenAIImageAnalyzer:
    def __init__(
        self,
        *,
        model: str = DEFAULT_MODEL,
        prompt_path: Path = DEFAULT_PROMPT_PATH,
        temperature: float = 0.1,
        max_output_tokens: int = 8192,
        initial_concurrency: int = DEFAULT_INITIAL_CONCURRENCY,
        min_concurrency: int = DEFAULT_MIN_CONCURRENCY,
        concurrency_step: int = DEFAULT_CONCURRENCY_STEP,
        image_detail: str = DEFAULT_IMAGE_DETAIL,
        client: Any | None = None,
    ) -> None:
        self.model = model
        self.prompt_path = prompt_path
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.initial_concurrency = max(1, initial_concurrency)
        self.min_concurrency = max(1, min_concurrency)
        self.concurrency_step = max(1, concurrency_step)
        self.image_detail = image_detail
        self._client = client
        self.last_queue_stats: dict[str, Any] = {}

    def analyze_images(self, *, markdown: str, image_urls: list[str]) -> list[ImageAnalysis]:
        if not image_urls:
            return []

        analyses: dict[str, ImageAnalysis] = {}
        unsupported_urls = [image_url for image_url in image_urls if not is_openai_supported_image_url(image_url)]
        for image_url in unsupported_urls:
            reason = f"OpenAI image input does not support {infer_image_mime_type(image_url)} for this URL."
            analyses[image_url] = ImageAnalysis(
                original_url=image_url,
                pedagogical_importance="unavailable",
                reason=reason,
                confidence="low",
                error=reason,
            )

        queue_urls = [image_url for image_url in image_urls if image_url not in analyses]
        queued_analyses, failed_analyses, stats = self._analyze_image_queue(markdown=markdown, image_urls=queue_urls)
        analyses.update(queued_analyses)
        analyses.update(failed_analyses)
        self.last_queue_stats = {
            **stats,
            "unsupported_count": len(unsupported_urls),
        }

        return [
            analyses.get(image_url)
            or ImageAnalysis(
                original_url=image_url,
                pedagogical_importance="unavailable",
                reason="OpenAI response did not include a decision for this image.",
                confidence="low",
                error="OpenAI response did not include a decision for this image.",
            )
            for image_url in image_urls
        ]

    def _analyze_image_queue(
        self,
        *,
        markdown: str,
        image_urls: list[str],
    ) -> tuple[dict[str, ImageAnalysis], dict[str, ImageAnalysis], dict[str, Any]]:
        if not image_urls:
            return {}, {}, {
                "initial_concurrency": self.initial_concurrency,
                "final_concurrency": self.initial_concurrency,
                "rounds": [],
            }

        pending = list(image_urls)
        analyses: dict[str, ImageAnalysis] = {}
        final_failures: dict[str, ImageAnalysis] = {}
        concurrency = self.initial_concurrency
        rounds: list[dict[str, int]] = []

        while pending:
            workers = min(max(self.min_concurrency, concurrency), len(pending))
            successes, failures = self._drain_image_queue(markdown=markdown, image_urls=pending, workers=workers)

            analyses.update(successes)
            rounds.append(
                {
                    "concurrency": workers,
                    "submitted_count": len(pending),
                    "success_count": len(successes),
                    "failure_count": len(failures),
                }
            )

            if not failures:
                pending = []
                continue

            next_concurrency = max(self.min_concurrency, concurrency - self.concurrency_step)
            if concurrency <= self.min_concurrency:
                for image_url, error in failures.items():
                    final_failures[image_url] = ImageAnalysis(
                        original_url=image_url,
                        pedagogical_importance="unavailable",
                        reason=f"OpenAI image analysis failed after concurrency retries: {error}",
                        confidence="low",
                        error=error,
                    )
                pending = []
                continue

            concurrency = next_concurrency
            pending = list(failures)

        return analyses, final_failures, {
            "initial_concurrency": self.initial_concurrency,
            "final_concurrency": concurrency,
            "rounds": rounds,
        }

    def _drain_image_queue(
        self,
        *,
        markdown: str,
        image_urls: list[str],
        workers: int,
    ) -> tuple[dict[str, ImageAnalysis], dict[str, str]]:
        work: Queue[str] = Queue()
        for image_url in image_urls:
            work.put(image_url)

        successes: dict[str, ImageAnalysis] = {}
        failures: dict[str, str] = {}
        lock = Lock()

        def worker() -> None:
            while True:
                try:
                    image_url = work.get_nowait()
                except Empty:
                    return
                try:
                    analysis = self._analyze_single_image(markdown=markdown, image_url=image_url)
                    with lock:
                        successes[image_url] = analysis
                except Exception as exc:  # noqa: BLE001 - preserve provider failure details in manifests.
                    with lock:
                        failures[image_url] = str(exc)
                finally:
                    work.task_done()

        threads = [Thread(target=worker, daemon=True) for _ in range(workers)]
        for thread in threads:
            thread.start()
        work.join()
        for thread in threads:
            thread.join()
        return successes, failures

    def _analyze_single_image(self, *, markdown: str, image_url: str) -> ImageAnalysis:
        response = self._get_client().responses.create(
            model=self.model,
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": self._build_prompt(markdown=markdown, image_urls=[image_url])},
                        {"type": "input_image", "image_url": image_url, "detail": self.image_detail},
                    ],
                }
            ],
            max_output_tokens=self.max_output_tokens,
            temperature=self.temperature,
            text=self._text_format(),
        )
        return parse_openai_image_response(_response_output_text(response), image_urls=[image_url])[0]

    def _build_prompt(self, *, markdown: str, image_urls: list[str]) -> str:
        prompt = self.prompt_path.read_text(encoding="utf-8")
        source_excerpt = markdown[:24000]
        return "\n\n".join(
            [
                prompt.rstrip(),
                "## Supplied Image URLs",
                json.dumps(image_urls, ensure_ascii=False, indent=2),
                "## Source Body Context",
                source_excerpt,
            ]
        )

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        load_pipeline_env()
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai is not installed; install requirements.txt") from exc
        api_key = (
            os.environ.get("OPENAI_API_KEY_ADMIN", "").strip()
            or os.environ.get("OPENAI_API_KEY", "").strip()
        )
        self._client = OpenAI(api_key=api_key) if api_key else OpenAI()
        return self._client

    def _text_format(self) -> dict[str, Any]:
        return {
            "format": {
                "type": "json_schema",
                "name": "article_image_preprocessing",
                "strict": True,
                "schema": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["images"],
                    "properties": {
                        "images": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "original_url",
                                    "pedagogical_importance",
                                    "reason",
                                    "replacement_text",
                                    "confidence",
                                ],
                                "properties": {
                                    "original_url": {"type": "string"},
                                    "pedagogical_importance": {
                                        "type": "string",
                                        "enum": ["important", "not_important", "unavailable"],
                                    },
                                    "reason": {"type": "string"},
                                    "replacement_text": {"type": "string"},
                                    "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
                                },
                            },
                        },
                    },
                },
            }
        }


class UnavailableImageAnalyzer:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def analyze_images(self, *, markdown: str, image_urls: list[str]) -> list[ImageAnalysis]:
        return [
            ImageAnalysis(
                original_url=image_url,
                pedagogical_importance="unavailable",
                reason=self.reason,
                replacement_text="",
                confidence="low",
            )
            for image_url in image_urls
        ]


def preprocess_markdown_images(markdown: str, *, analyzer: ImageAnalyzer) -> ImagePreprocessResult:
    references = extract_image_references(markdown)
    image_urls = _dedupe_preserving_order(reference.url for reference in references if _is_http_url(reference.url))
    analyses = analyzer.analyze_images(markdown=markdown, image_urls=image_urls) if image_urls else []
    analyses_by_url = {analysis.original_url: analysis for analysis in analyses}

    rewritten = markdown
    rewritten_refs: list[dict[str, Any]] = []
    summary = {
        "image_reference_count": len(references),
        "important_count": 0,
        "not_important_count": 0,
        "unavailable_count": 0,
    }
    for reference in reversed(references):
        analysis = analyses_by_url.get(reference.url) or ImageAnalysis(
            original_url=reference.url,
            pedagogical_importance="unavailable",
            reason="No OpenAI analysis was returned for this image URL.",
            confidence="low",
            error="No OpenAI analysis was returned for this image URL.",
        )
        normalized = normalize_analysis(analysis, reference.url)
        replacement = replacement_markdown(reference, normalized)
        rewritten = rewritten[: reference.start] + replacement + rewritten[reference.end :]
        rewritten_refs.append(
            {
                **asdict(reference),
                "analysis": asdict(normalized),
                "replacement": replacement,
            }
        )
        if normalized.pedagogical_importance == "important":
            summary["important_count"] += 1
        elif normalized.pedagogical_importance == "not_important":
            summary["not_important_count"] += 1
        else:
            summary["unavailable_count"] += 1

    manifest = {
        "artifact_type": "article_image_preprocessing_manifest",
        "schema_version": "article_image_preprocessing_manifest.v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt_version": PROMPT_VERSION,
        "summary": summary,
        "images": list(reversed(rewritten_refs)),
    }
    analysis_errors = _analysis_errors(rewritten_refs)
    if analysis_errors:
        manifest["analysis_errors"] = analysis_errors
    return ImagePreprocessResult(markdown=rewritten, manifest=manifest)


def process_extraction_articles(
    *,
    extraction_root: Path,
    index_path: Path,
    manifest_root: Path = DEFAULT_MANIFEST_DIR,
    analyzer: ImageAnalyzer,
    only_ids: set[str] | None = None,
) -> dict[str, Any]:
    index = json.loads(index_path.read_text(encoding="utf-8"))
    pipeline_root = index_path.resolve().parent
    processed_count = 0
    skipped_count = 0
    error_count = 0
    manifest_paths: list[str] = []

    for record in index.get("records", []):
        if record.get("type") != "article" or record.get("available") is not True:
            skipped_count += 1
            continue
        if only_ids is not None and str(record.get("id")) not in only_ids:
            skipped_count += 1
            continue
        file_info = record.get("file") or {}
        image_preprocessing = record.get("image_preprocessing") or {}
        pre_image_rel = article_pre_image_path(
            record=record,
            file_info=file_info,
            image_preprocessing=image_preprocessing,
            extraction_root=extraction_root,
            pipeline_root=pipeline_root,
        )
        if not pre_image_rel:
            skipped_count += 1
            continue
        pre_image_path = pipeline_root / pre_image_rel
        post_image_path = extraction_root / "post-image" / pre_image_path.name
        manifest_path = manifest_root / pre_image_path.with_suffix(".manifest.json").name

        result = process_article_file(
            input_path=pre_image_path,
            output_path=post_image_path,
            manifest_path=manifest_path,
            analyzer=analyzer,
            pipeline_root=pipeline_root,
        )
        post_image_rel = _relative_to(post_image_path, pipeline_root)
        manifest_rel = _relative_to(manifest_path, pipeline_root)
        status = "processed_with_errors" if result.manifest.get("analysis_error") else "processed"
        if status == "processed_with_errors":
            error_count += 1
        record["extraction_path"] = post_image_rel
        record["file"] = file_info_for(post_image_path, pipeline_root=pipeline_root)
        record["image_preprocessing"] = {
            "status": status,
            "pre_image_path": _relative_to(pre_image_path, pipeline_root),
            "post_image_path": post_image_rel,
            "manifest_path": manifest_rel,
            "summary": result.manifest["summary"],
        }
        if result.manifest.get("analysis_error"):
            record["image_preprocessing"]["analysis_error"] = result.manifest["analysis_error"]
        processed_count += 1
        manifest_paths.append(manifest_rel)

    index["generated_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _atomic_write_text(index_path, json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    summary = {
        "artifact_type": "article_image_preprocessing_run_summary",
        "schema_version": "article_image_preprocessing_run_summary.v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "processed_count": processed_count,
        "skipped_count": skipped_count,
        "error_count": error_count,
        "manifest_paths": manifest_paths,
    }
    summary_path = manifest_root / "summary.json"
    summary["summary_path"] = str(summary_path)
    _atomic_write_text(summary_path, json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return summary


def process_article_file(
    *,
    input_path: Path,
    output_path: Path,
    manifest_path: Path,
    analyzer: ImageAnalyzer,
    pipeline_root: Path | None = None,
) -> ImagePreprocessResult:
    markdown = input_path.read_text(encoding="utf-8", errors="replace")
    analysis_error: str | None = None
    try:
        result = preprocess_markdown_images(markdown, analyzer=analyzer)
    except Exception as exc:
        analysis_error = str(exc)
        result = preprocess_markdown_images(markdown, analyzer=UnavailableImageAnalyzer(analysis_error))
    manifest = {
        **result.manifest,
        "input_path": _relative_to(input_path, pipeline_root) if pipeline_root else str(input_path),
        "output_path": _relative_to(output_path, pipeline_root) if pipeline_root else str(output_path),
        "input_sha256": hashlib.sha256(markdown.encode("utf-8")).hexdigest(),
        "output_sha256": hashlib.sha256(result.markdown.encode("utf-8")).hexdigest(),
    }
    if not analysis_error and result.manifest.get("analysis_errors"):
        analysis_error = summarize_analysis_errors(result.manifest["analysis_errors"])
    if analysis_error:
        manifest["analysis_error"] = analysis_error
    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(output_path, result.markdown)
    _atomic_write_text(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return ImagePreprocessResult(markdown=result.markdown, manifest=manifest)


def parse_openai_image_response(raw: str, *, image_urls: list[str]) -> list[ImageAnalysis]:
    payload_text = _strip_json_fence(raw).strip()
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"OpenAI image preprocessing response was not valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("OpenAI image preprocessing response must be a JSON object")
    raw_images = payload.get("images")
    if not isinstance(raw_images, list):
        raise ValueError("OpenAI image preprocessing response must include an images list")

    parsed_by_url: dict[str, ImageAnalysis] = {}
    for item in raw_images:
        if not isinstance(item, dict):
            continue
        original_url = str(item.get("original_url") or "").strip()
        if not original_url:
            continue
        parsed_by_url[original_url] = normalize_analysis(
            ImageAnalysis(
                original_url=original_url,
                pedagogical_importance=str(item.get("pedagogical_importance") or "unavailable"),
                reason=str(item.get("reason") or ""),
                replacement_text=str(item.get("replacement_text") or ""),
                confidence=str(item.get("confidence") or ""),
                error=str(item.get("error") or ""),
            ),
            original_url,
        )

    analyses: list[ImageAnalysis] = []
    for image_url in image_urls:
        analyses.append(
            parsed_by_url.get(image_url)
            or ImageAnalysis(
                original_url=image_url,
                pedagogical_importance="unavailable",
                reason="OpenAI response did not include a decision for this image.",
                replacement_text="",
                confidence="low",
                error="OpenAI response did not include a decision for this image.",
            )
        )
    return analyses


def file_info_for(path: Path, *, pipeline_root: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "path": _relative_to(path, pipeline_root),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "word_count": len(re.findall(r"\b\w+\b", text, flags=re.UNICODE)),
    }


def article_pre_image_path(
    *,
    record: dict[str, Any],
    file_info: dict[str, Any],
    image_preprocessing: dict[str, Any],
    extraction_root: Path,
    pipeline_root: Path,
) -> str:
    candidates = [
        str(image_preprocessing.get("pre_image_path") or ""),
        str(file_info.get("path") or ""),
        str(record.get("extraction_path") or ""),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = pipeline_root / candidate
        if "/pre-image/" in candidate.replace("\\", "/") and candidate_path.is_file():
            return candidate
        recovered = extraction_root / "pre-image" / Path(candidate).name
        if recovered.is_file():
            return _relative_to(recovered, pipeline_root)
    return next((candidate for candidate in candidates if candidate), "")


def extract_image_references(markdown: str) -> list[ImageReference]:
    matches: list[tuple[int, int, str, str, str, str | None]] = []

    for match in LINKED_MARKDOWN_IMAGE_RE.finditer(markdown):
        matches.append(
            (
                match.start(),
                match.end(),
                "linked_markdown_image",
                html.unescape(match.group("alt") or ""),
                html.unescape(match.group("url") or ""),
                html.unescape(match.group("link_url") or ""),
            )
        )

    linked_spans = [(start, end) for start, end, *_ in matches]
    for match in MARKDOWN_IMAGE_RE.finditer(markdown):
        if _overlaps_any(match.start(), match.end(), linked_spans):
            continue
        matches.append(
            (
                match.start(),
                match.end(),
                "markdown_image",
                html.unescape(match.group("alt") or ""),
                html.unescape(match.group("url") or ""),
                None,
            )
        )

    existing_spans = [(start, end) for start, end, *_ in matches]
    for match in HTML_IMG_RE.finditer(markdown):
        if _overlaps_any(match.start(), match.end(), existing_spans):
            continue
        attrs = _html_attrs(match.group(0))
        src = attrs.get("src")
        if not src:
            continue
        matches.append(
            (
                match.start(),
                match.end(),
                "html_image",
                html.unescape(attrs.get("alt") or ""),
                html.unescape(src),
                None,
            )
        )

    references: list[ImageReference] = []
    for index, (start, end, kind, alt_text, url, link_url) in enumerate(sorted(matches), start=1):
        references.append(
            ImageReference(
                index=index,
                kind=kind,
                original_text=markdown[start:end],
                alt_text=alt_text.strip(),
                url=url.strip(),
                start=start,
                end=end,
                link_url=link_url.strip() if link_url else None,
            )
        )
    return references


def normalize_analysis(analysis: ImageAnalysis, expected_url: str) -> ImageAnalysis:
    importance = analysis.pedagogical_importance.strip().lower()
    if importance not in {"important", "not_important", "unavailable"}:
        importance = "unavailable"
    return ImageAnalysis(
        original_url=analysis.original_url.strip() or expected_url,
        pedagogical_importance=importance,
        reason=analysis.reason.strip(),
        replacement_text=analysis.replacement_text.strip(),
        confidence=analysis.confidence.strip(),
        error=analysis.error.strip(),
    )


def replacement_markdown(reference: ImageReference, analysis: ImageAnalysis) -> str:
    label = _image_label(reference)
    if analysis.pedagogical_importance == "important":
        summary = analysis.replacement_text or analysis.reason or "This image contains pedagogically relevant source information."
        return f"Image summary: {summary} [Original image: {label}]({reference.url})"
    if analysis.pedagogical_importance == "not_important":
        return f"[Image: {label}]({reference.url})"
    return f"[Unavailable image: {label}]({reference.url})"


def infer_image_mime_type(image_url: str) -> str:
    suffix = Path(urlparse(image_url).path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
        ".bmp": "image/bmp",
    }.get(suffix, "image/png")


def is_openai_supported_image_url(image_url: str) -> bool:
    suffix = Path(urlparse(image_url).path).suffix.lower()
    return suffix not in {".svg", ".bmp"}


def parse_only_ids(value: str | None) -> set[str] | None:
    if not value:
        return None
    ids = {part.strip() for part in value.split(",") if part.strip()}
    if not ids:
        raise ValueError("--only must include at least one id")
    return ids


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess article images from extraction/pre-image into extraction/post-image."
    )
    parser.add_argument("--extraction-root", type=Path, default=DEFAULT_EXTRACTION_ROOT)
    parser.add_argument("--index", type=Path, default=PIPELINE_ROOT / "index.json")
    parser.add_argument("--manifest-root", type=Path, default=DEFAULT_MANIFEST_DIR)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT_PATH)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--temperature", type=float, default=0.1)
    parser.add_argument("--max-output-tokens", type=int, default=8192)
    parser.add_argument("--initial-concurrency", type=int, default=DEFAULT_INITIAL_CONCURRENCY)
    parser.add_argument("--min-concurrency", type=int, default=DEFAULT_MIN_CONCURRENCY)
    parser.add_argument("--concurrency-step", type=int, default=DEFAULT_CONCURRENCY_STEP)
    parser.add_argument("--image-detail", default=DEFAULT_IMAGE_DETAIL, choices=["low", "high", "original", "auto"])
    parser.add_argument("--only", help="Comma-separated article ids to process.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    load_pipeline_env()
    try:
        only_ids = parse_only_ids(args.only)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    analyzer = OpenAIImageAnalyzer(
        model=args.model,
        prompt_path=args.prompt,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        initial_concurrency=args.initial_concurrency,
        min_concurrency=args.min_concurrency,
        concurrency_step=args.concurrency_step,
        image_detail=args.image_detail,
    )
    summary = process_extraction_articles(
        extraction_root=args.extraction_root.resolve(),
        index_path=args.index.resolve(),
        manifest_root=args.manifest_root.resolve(),
        analyzer=analyzer,
        only_ids=only_ids,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def load_pipeline_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    for env_path in (PIPELINE_ROOT / ".env", Path.cwd() / ".env"):
        if env_path.exists():
            load_dotenv(env_path, override=False)


def summarize_analysis_errors(analysis_errors: list[dict[str, str]]) -> str:
    counts: dict[str, int] = {}
    for item in analysis_errors:
        error = item.get("error", "").strip() or item.get("reason", "").strip() or "Unknown OpenAI analysis error"
        counts[error] = counts.get(error, 0) + 1
    parts = [f"{count}x {error}" for error, count in sorted(counts.items())]
    return "OpenAI image analysis errors: " + "; ".join(parts)


def _analysis_errors(rewritten_refs: list[dict[str, Any]]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for rewritten_ref in reversed(rewritten_refs):
        analysis = rewritten_ref.get("analysis") or {}
        error = str(analysis.get("error") or "").strip()
        if not error:
            continue
        original_url = str(analysis.get("original_url") or rewritten_ref.get("url") or "").strip()
        key = (original_url, error)
        if key in seen:
            continue
        seen.add(key)
        errors.append(
            {
                "original_url": original_url,
                "error": error,
                "reason": str(analysis.get("reason") or "").strip(),
            }
        )
    return errors


def _response_output_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text:
        return str(output_text)
    if isinstance(response, dict) and response.get("output_text"):
        return str(response["output_text"])

    chunks: list[str] = []
    for output_item in _iter_response_items(response, "output"):
        for content_item in _iter_response_items(output_item, "content"):
            text = _response_item_value(content_item, "text")
            if text:
                chunks.append(str(text))
    return "".join(chunks)


def _iter_response_items(value: Any, name: str) -> list[Any]:
    if isinstance(value, dict):
        items = value.get(name) or []
    else:
        items = getattr(value, name, []) or []
    return list(items) if isinstance(items, list) else []


def _response_item_value(value: Any, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _image_label(reference: ImageReference) -> str:
    if reference.alt_text:
        return _collapse_space(reference.alt_text)
    parsed = urlparse(reference.url)
    name = Path(parsed.path).name
    return name or reference.url


def _collapse_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _html_attrs(tag: str) -> dict[str, str]:
    return {match.group("name").lower(): html.unescape(match.group("value")) for match in HTML_ATTR_RE.finditer(tag)}


def _overlaps_any(start: int, end: int, spans: list[tuple[int, int]]) -> bool:
    return any(start < span_end and end > span_start for span_start, span_end in spans)


def _is_http_url(value: str) -> bool:
    return value.startswith(("http://", "https://"))


def _dedupe_preserving_order(values: Any) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _strip_json_fence(raw: str) -> str:
    text = raw.strip()
    if not text.startswith("```"):
        return text
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    return text


def _relative_to(path: Path, root: Path) -> str:
    return str(path.resolve().relative_to(root.resolve()))


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


if __name__ == "__main__":
    raise SystemExit(main())
