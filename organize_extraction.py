#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PIPELINE_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_ROOT = PIPELINE_ROOT / "extraction"
PRE_IMAGE_DIR_NAME = "pre-image"
POST_IMAGE_DIR_NAME = "post-image"

SOURCE_GROUPS = {
    "video": {
        "input": PIPELINE_ROOT / "video" / "url.json",
        "output": PIPELINE_ROOT / "video" / "output",
    },
    "article": {
        "input": PIPELINE_ROOT / "article" / "firecrawl" / "url.json",
        "output": PIPELINE_ROOT / "article" / "firecrawl" / "output",
    },
    "book": {
        "input": PIPELINE_ROOT / "book" / "url.json",
        "output": PIPELINE_ROOT / "book" / "output",
    },
}

BLOCKING_FAILURES = {
    "manual_access_required",
    "auth_wall_detected",
    "error_page_detected",
    "http_status_401",
    "http_status_403",
    "http_status_404",
    "http_status_410",
    "metadata_error",
    "acquisition_failed",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def slugify(value: str, max_length: int = 90) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return (slug[:max_length].rstrip("-") or "source")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def word_count(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text, flags=re.UNICODE))


def relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PIPELINE_ROOT.resolve()))
    except ValueError:
        return str(path.resolve())


def source_rows(source_groups: dict[str, dict[str, Path]] | None = None) -> list[dict[str, Any]]:
    source_groups = source_groups or SOURCE_GROUPS
    rows: list[dict[str, Any]] = []
    for source_type, config in source_groups.items():
        raw_rows = load_json(config["input"], [])
        for raw in raw_rows:
            row_id = str(raw["id"])
            rows.append(
                {
                    "id": row_id,
                    "type": source_type,
                    "title": str(raw.get("title") or ""),
                    "source_row": raw,
                    "artifact_dir": config["output"] / row_id,
                }
            )
    return sorted(rows, key=lambda item: int(item["id"]))


def source_markdown(artifact_dir: Path, row_id: str) -> Path | None:
    candidates = sorted(artifact_dir.glob(f"{row_id}-*.md"))
    return candidates[0] if candidates else None


def gate_info(artifact_dir: Path) -> dict[str, Any]:
    if not artifact_dir.exists():
        return {
            "status": "missing",
            "failures": ["missing_acquisition_artifact"],
            "warnings": [],
        }
    gate = load_json(artifact_dir / "gate_report.json", {})
    if not gate:
        return {
            "status": "missing",
            "failures": ["missing_gate_report"],
            "warnings": [],
        }
    failures = gate.get("failures") or gate.get("gate_failures") or []
    warnings = gate.get("warnings") or []
    if not isinstance(failures, list):
        failures = []
    if not isinstance(warnings, list):
        warnings = []
    return {
        "status": gate.get("status") or "missing",
        "failures": [str(item) for item in failures],
        "warnings": [str(item) for item in warnings],
    }


def is_blocked(gate: dict[str, Any], markdown_path: Path | None) -> bool:
    if markdown_path is None:
        return True
    status = str(gate["status"]).lower()
    failures = set(gate["failures"])
    return status in {"failed_gate", "needs_manual", "failed", "acquisition_failed"} or bool(
        failures & BLOCKING_FAILURES
    )


def remove_generated(output_root: Path) -> None:
    for path in output_root.iterdir():
        if path.name == "organize_extraction.py":
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def build_report(records: list[dict[str, Any]]) -> str:
    available = [record for record in records if record["available"]]
    blocked = [record for record in records if not record["available"]]
    warnings = Counter(warning for record in records for warning in record["warnings"])
    by_type = Counter(record["type"] for record in records)
    available_by_type = Counter(record["type"] for record in available)

    blocked_text = ", ".join(f"{item['type']}/{item['id']}" for item in blocked) or "none"
    warning_text = ", ".join(f"{key}: {value}" for key, value in sorted(warnings.items())) or "none"

    return "\n".join(
        [
            "# Extraction report",
            "",
            "Short version: this is good enough for MVP annotation.",
            "",
            f"- Total source rows: {len(records)}",
            f"- Markdown files exported: {len(available)}",
            f"- Blocked/unusable sources: {len(blocked)} ({blocked_text})",
            f"- Source mix: {dict(sorted(by_type.items()))}",
            f"- Exported mix: {dict(sorted(available_by_type.items()))}",
            f"- Warnings still worth keeping in mind: {warning_text}",
            "",
            "My call: do not run a separate cleaning agent for the MVP.",
            "Let the annotation/concept extraction agent do light cleanup as it reads each source.",
            "That means it can ignore obvious nav/OCR junk, but it should preserve page labels, timestamps, exercise numbers, examples, headings, and code blocks.",
            "",
            "The only sources I would not feed as content are the genuinely blocked ones:",
            *[f"- {item['type']}/{item['id']}: {item['title']} ({'; '.join(item['failures']) or item['status']})" for item in blocked],
            "",
        ]
    )


def organize(output_root: Path, source_groups: dict[str, dict[str, Path]] | None = None) -> list[dict[str, Any]]:
    source_groups = source_groups or SOURCE_GROUPS
    output_root.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []

    for row in source_rows(source_groups):
        artifact_dir = row["artifact_dir"]
        markdown_path = source_markdown(artifact_dir, row["id"])
        gate = gate_info(artifact_dir)
        blocked = is_blocked(gate, markdown_path)

        output_path: Path | None = None
        file_info: dict[str, Any] | None = None
        if not blocked and markdown_path is not None:
            output_name = f"{int(row['id']):04d}-{row['type']}-{slugify(row['title'])}.md"
            output_path = extraction_markdown_path(output_root, row["type"], output_name)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(markdown_path, output_path)
            text = output_path.read_text(encoding="utf-8", errors="replace")
            file_info = {
                "path": relative(output_path),
                "bytes": output_path.stat().st_size,
                "sha256": sha256_file(output_path),
                "word_count": word_count(text),
            }

        records.append(
            {
                "id": row["id"],
                "type": row["type"],
                "title": row["title"],
                "available": not blocked,
                "extraction_path": file_info["path"] if file_info else None,
                "source_markdown": relative(markdown_path) if markdown_path else None,
                "artifact_dir": relative(artifact_dir),
                "status": gate["status"],
                "warnings": gate["warnings"],
                "failures": gate["failures"],
                "file": file_info,
                "image_preprocessing": image_preprocessing_info(row, file_info),
                "source_row": row["source_row"],
            }
        )

    return records


def extraction_markdown_path(output_root: Path, source_type: str, output_name: str) -> Path:
    if source_type == "article":
        return output_root / PRE_IMAGE_DIR_NAME / output_name
    return output_root / POST_IMAGE_DIR_NAME / output_name


def image_preprocessing_info(row: dict[str, Any], file_info: dict[str, Any] | None) -> dict[str, Any] | None:
    if row["type"] != "article" or not file_info:
        return None
    return {
        "status": "pending",
        "pre_image_path": file_info["path"],
        "post_image_path": None,
        "manifest_path": None,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the flat MVP extraction folder.")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help="Folder that receives only extracted markdown files.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous generated extraction files before copying markdown.",
    )
    parser.add_argument(
        "--preprocess-article-images",
        action="store_true",
        help="After organizing, run Gemini image preprocessing for article markdown.",
    )
    parser.add_argument("--article-input", type=Path, default=SOURCE_GROUPS["article"]["input"])
    parser.add_argument("--article-output", type=Path, default=SOURCE_GROUPS["article"]["output"])
    parser.add_argument("--book-input", type=Path, default=SOURCE_GROUPS["book"]["input"])
    parser.add_argument("--book-output", type=Path, default=SOURCE_GROUPS["book"]["output"])
    parser.add_argument("--video-input", type=Path, default=SOURCE_GROUPS["video"]["input"])
    parser.add_argument("--video-output", type=Path, default=SOURCE_GROUPS["video"]["output"])
    parser.add_argument("--index-path", type=Path, default=PIPELINE_ROOT / "index.json")
    parser.add_argument("--report-path", type=Path, default=PIPELINE_ROOT / "extraction_report.md")
    parser.add_argument("--image-model", default="gemini-2.5-flash", help=argparse.SUPPRESS)
    parser.add_argument(
        "--image-prompt",
        type=Path,
        default=PIPELINE_ROOT / "article" / "prompts" / "image_preprocessing.md",
        help=argparse.SUPPRESS,
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_root = args.output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    if args.clean:
        remove_generated(output_root)

    source_groups = {
        "video": {"input": args.video_input.resolve(), "output": args.video_output.resolve()},
        "article": {"input": args.article_input.resolve(), "output": args.article_output.resolve()},
        "book": {"input": args.book_input.resolve(), "output": args.book_output.resolve()},
    }
    records = organize(output_root, source_groups)
    index = {
        "generated_at": now_utc(),
        "extraction_dir": relative(output_root),
        "available_count": sum(1 for record in records if record["available"]),
        "blocked_count": sum(1 for record in records if not record["available"]),
        "records": records,
    }

    args.index_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.index_path.resolve(), index)
    args.report_path.resolve().write_text(build_report(records), encoding="utf-8")

    image_preprocessing_summary = None
    if args.preprocess_article_images:
        from article.preprocess_images import GeminiImageAnalyzer, process_extraction_articles

        image_preprocessing_summary = process_extraction_articles(
            extraction_root=output_root,
            index_path=PIPELINE_ROOT / "index.json",
            analyzer=GeminiImageAnalyzer(model=args.image_model, prompt_path=args.image_prompt),
        )

    print(
        json.dumps(
            {
                "extraction_dir": relative(output_root),
                "markdown_files": index["available_count"],
                "blocked": index["blocked_count"],
                "index": relative(args.index_path.resolve()),
                "report": relative(args.report_path.resolve()),
                "image_preprocessing": image_preprocessing_summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
