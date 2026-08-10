"""Manual source acquisition from one PDF or ordered raster images.

The module is deliberately independent of the web layer: callers persist one
explicit source-local job with :func:`create_manual_upload_job`, then execute
that exact job with :func:`acquire_manual_upload`.  Successful execution stops
at an immutable Markdown artifact and never starts KC extraction.
"""

from __future__ import annotations

import base64
import hashlib
import os
import re
import subprocess
import uuid
from dataclasses import dataclass, field, replace
from typing import Any, Mapping, Sequence

import psycopg
from psycopg.types.json import Jsonb

from universe.assets import AssetStore, asset_store_from_env
from universe.acquisition.pdfs import (
    PDF_PAGE_TOOL,
    PDF_PAGE_TOOL_VERSION,
    PdfExtractionError,
    acquire_pdf_document,
    extract_pdf_pages_with_poppler,
    parse_pdf_with_firecrawl,
)
from universe.model_client import ModelClient, ModelError
from universe.settings import (
    acquisition_lease_minutes,
    openrouter_multimodal_provider_routing,
)


MAX_TOTAL_BYTES = 30 * 1024 * 1024
MAX_IMAGE_COUNT = 50
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
MANUAL_PROVIDER = "manual-upload/v1"
DEFAULT_IMAGE_MODEL = "google/gemini-2.5-flash"
PDF_TOOL_VERSION = "manual-pdf-text.v1"
SAFE_METADATA_KEYS = {
    "caption",
    "captured_at",
    "height",
    "label",
    "notes",
    "page_number",
    "width",
}
IMAGE_DESCRIPTION_PROMPT_VERSION = "manual-source-image-description.v1"
IMAGE_DESCRIPTION_TOOL = {
    "type": "function",
    "function": {
        "name": "describe_source_image",
        "description": (
            "Describe one source image for a faithful educational Markdown reconstruction."
        ),
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": (
                        "Faithful explanation of the visual content, relationships, and educational meaning."
                    ),
                },
                "visible_text": {
                    "type": "string",
                    "description": (
                        "Verbatim transcription of meaningful legible text, preserving reading order; blank if none."
                    ),
                },
            },
            "required": ["description", "visible_text"],
            "additionalProperties": False,
        },
    },
}


@dataclass(frozen=True)
class ManualAsset:
    """One user-provided immutable input, before or after validation."""

    filename: str
    mime_type: str
    body: bytes
    kind: str
    metadata: Mapping[str, Any] = field(default_factory=dict)
    ordinal: int | None = None
    sha256: str | None = None


@dataclass(frozen=True)
class ImageDescription:
    description: str
    visible_text: str
    requested_model: str
    response_model: str | None
    provider: str
    usage: dict[str, Any]
    duration_ms: int


class ManualAcquisitionError(RuntimeError):
    def __init__(self, code: str, category: str):
        self.code = code
        self.category = category
        super().__init__(code)


@dataclass(frozen=True)
class ManualOutcome:
    markdown: str | None
    failure_code: str | None
    provider: str
    tool: str
    tool_version: str | None
    diagnostics: dict[str, Any]
    raw_markdown: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.markdown is not None and self.failure_code is None


class OpenRouterImageDescriber:
    """Describe one ordered image through a forced structured tool call."""

    def __init__(
        self,
        *,
        model: str | None = None,
        client: ModelClient | None = None,
    ) -> None:
        resolved_model = (
            model
            or os.environ.get("CONCEPT_UNIVERSE_MANUAL_IMAGE_MODEL", "").strip()
            or DEFAULT_IMAGE_MODEL
        )
        self.client = client or ModelClient(
            resolved_model,
            temperature=0,
            max_tokens=2500,
            extra={
                "provider": openrouter_multimodal_provider_routing()
            },
        )

    def describe(self, asset: ManualAsset) -> ImageDescription:
        if asset.mime_type not in IMAGE_MIME_TYPES:
            raise ValueError("image describer requires a validated raster asset")
        encoded = base64.b64encode(asset.body).decode("ascii")
        prompt = (
            "Reconstruct this uploaded educational source image faithfully. "
            "Write the visual description in the principal language visible in the image. "
            "Explain diagrams, charts, spatial relationships, labels and pedagogically relevant visuals; "
            "do not invent obscured details. Transcribe all meaningful legible text verbatim in reading "
            "order. Use the forced tool exactly once."
        )
        arguments, raw_usage, duration_ms = self.client.call_tool(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{asset.mime_type};base64,{encoded}",
                                "detail": "high",
                            },
                        },
                    ],
                }
            ],
            IMAGE_DESCRIPTION_TOOL,
        )
        unexpected = set(arguments) - {"description", "visible_text"}
        description = arguments.get("description")
        visible_text = arguments.get("visible_text")
        if unexpected or not isinstance(description, str) or not description.strip():
            raise ModelError("describe_source_image returned an invalid description")
        if not isinstance(visible_text, str):
            raise ModelError("describe_source_image returned invalid visible_text")
        response_model = raw_usage.get("response_model")
        provider = raw_usage.get("provider") or "openrouter"
        usage = {
            key: value
            for key, value in raw_usage.items()
            if key not in {"provider", "response_model"}
        }
        return ImageDescription(
            description=description.strip(),
            visible_text=visible_text.strip(),
            requested_model=self.client.model,
            response_model=(str(response_model) if response_model else None),
            provider=str(provider),
            usage=usage,
            duration_ms=duration_ms,
        )


ASSET_COLUMNS = (
    "id",
    "acquisition_job_id",
    "source_id",
    "ordinal",
    "kind",
    "filename",
    "mime_type",
    "sha256",
    "byte_size",
    "storage_key",
    "metadata",
    "created_at",
)


def create_manual_upload_job(
    conn: psycopg.Connection,
    source_id: str,
    assets: Sequence[ManualAsset],
    *,
    actor: str = "founder",
    input_kind: str | None = None,
    asset_store: AssetStore | None = None,
) -> dict:
    """Persist one explicit manual acquisition and its immutable inputs.

    ``input_kind`` accepts the web form vocabulary (``pdf`` or ``images``)
    and is optional for non-web callers because the assets are unambiguous.
    The transaction commits before this function returns; no extractor or
    model is called here.
    """
    source_id = str(source_id or "").strip()
    if not source_id:
        raise ValueError("manual upload requires one source id")
    validated = validate_manual_assets(assets)
    input_mode = "pdf" if validated[0].kind == "pdf" else "images"
    if input_kind is not None and input_kind != input_mode:
        raise ValueError(f"input kind {input_kind!r} does not match uploaded files")
    if conn.execute(
        "SELECT 1 FROM source WHERE id = %s FOR UPDATE", (source_id,)
    ).fetchone() is None:
        conn.rollback()
        raise ValueError(f"unknown source {source_id}")

    existing = conn.execute(
        "SELECT j.id FROM acquisition_job j WHERE j.source_id = %s AND ("
        " j.status IN ('queued', 'running')"
        " OR EXISTS (SELECT 1 FROM source_cleanup_job c"
        "   WHERE c.acquisition_job_id = j.id"
        "   AND c.status IN ('queued', 'running'))"
        " OR EXISTS (SELECT 1 FROM source_image_candidate i"
        "   WHERE i.acquisition_job_id = j.id"
        "   AND i.status IN ('queued', 'running', 'downloaded'))"
        ") ORDER BY j.created_at DESC, j.id DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    if existing is not None:
        conn.rollback()
        raise ValueError(f"source already has an active acquisition job ({existing[0]})")

    job_id = f"acq-{uuid.uuid4().hex}"
    diagnostics = {
        "asset_count": len(validated),
        "input_mode": input_mode,
        "input_manifest_sha256": _input_manifest_sha(validated),
    }
    store = asset_store or asset_store_from_env()
    try:
        inserted = conn.execute(
            "INSERT INTO acquisition_job (id, source_id, provider, diagnostics)"
            " VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
            (job_id, source_id, MANUAL_PROVIDER, Jsonb(diagnostics)),
        ).fetchone()
        if inserted is None:
            raise ValueError("source already has an active acquisition job")

        for asset in validated:
            assert asset.ordinal is not None and asset.sha256 is not None
            stored_asset = store.put(asset.body, sha256=asset.sha256)
            conn.execute(
                "INSERT INTO source_asset"
                " (id, acquisition_job_id, source_id, ordinal, kind, filename,"
                "  mime_type, sha256, byte_size, storage_key, metadata)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    f"asset-{uuid.uuid4().hex}",
                    job_id,
                    source_id,
                    asset.ordinal,
                    asset.kind,
                    asset.filename,
                    asset.mime_type,
                    asset.sha256,
                    len(asset.body),
                    stored_asset.key,
                    Jsonb(_safe_metadata(asset.metadata)),
                ),
            )
        conn.execute(
            "INSERT INTO curation_event (id, actor, action, subject)"
            " VALUES (%s, %s, 'source_manual_upload_queued', %s)",
            (
                f"ce-acq-{uuid.uuid4().hex}",
                actor,
                Jsonb(
                    {
                        "source_id": source_id,
                        "job_id": job_id,
                        "input_mode": input_mode,
                        "asset_count": len(validated),
                    }
                ),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        # Content-addressed objects are shared.  Deleting one here can race a
        # concurrent transaction that has already referenced the same bytes.
        # An unreferenced object is safe and can be collected by a later
        # ledger/object reconciliation pass.
        raise
    from universe.acquisition.runner import get_job

    job = get_job(conn, job_id)
    assert job is not None
    return job


def list_manual_assets(
    conn: psycopg.Connection,
    job_id: str,
    *,
    include_body: bool = False,
    asset_store: AssetStore | None = None,
) -> list[dict[str, Any]]:
    """Return the job's inputs in the user's explicit order."""
    rows = conn.execute(
        "SELECT id, acquisition_job_id, source_id, ordinal, kind, filename,"
        " mime_type, sha256, byte_size, storage_key, metadata, created_at"
        " FROM source_asset"
        " WHERE acquisition_job_id = %s AND kind NOT IN ('pdf_page', 'pdf_figure')"
        " ORDER BY ordinal, id",
        (job_id,),
    ).fetchall()
    assets = [dict(zip(ASSET_COLUMNS, row)) for row in rows]
    if include_body:
        store = asset_store or asset_store_from_env()
        for asset in assets:
            asset["body"] = store.get(asset["storage_key"])
    return assets


def get_manual_asset(
    conn: psycopg.Connection,
    asset_id: str,
    *,
    include_body: bool = False,
    asset_store: AssetStore | None = None,
) -> dict[str, Any] | None:
    """Read one immutable asset for the authenticated content endpoint."""
    row = conn.execute(
        "SELECT id, acquisition_job_id, source_id, ordinal, kind, filename,"
        " mime_type, sha256, byte_size, storage_key, metadata, created_at"
        " FROM source_asset WHERE id = %s",
        (asset_id,),
    ).fetchone()
    if row is None:
        return None
    asset = dict(zip(ASSET_COLUMNS, row))
    if include_body:
        store = asset_store or asset_store_from_env()
        asset["body"] = store.get(asset["storage_key"])
    return asset


def extract_pdf_text_with_pdftotext(body: bytes) -> str:
    """Extract a text-based PDF without materializing an attacker filename."""
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-", "-"],
            input=body,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise ManualAcquisitionError(
            "manual_pdf_extractor_missing", "pdf_extractor_unavailable"
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise ManualAcquisitionError(
            "manual_pdf_extraction_failed", "pdf_extraction_timeout"
        ) from exc
    if result.returncode != 0:
        raise ManualAcquisitionError(
            "manual_pdf_extraction_failed", "pdf_extraction_failed"
        )
    return result.stdout.decode("utf-8", errors="replace")


def acquire_manual_upload(
    conn: psycopg.Connection,
    job_id: str,
    *,
    pdf_document_parser=parse_pdf_with_firecrawl,
    pdf_image_downloader=None,
    pdf_figure_locator=None,
    pdf_page_extractor=extract_pdf_pages_with_poppler,
    image_describer: Any | None = None,
    asset_store: AssetStore | None = None,
) -> dict:
    """Process one manual-upload job and stop at an immutable Markdown artifact."""
    job = _claim_manual_job(conn, job_id)
    if job is None:
        from universe.acquisition.runner import get_job

        existing = get_job(conn, job_id)
        if existing is None:
            raise ValueError(f"unknown manual acquisition job {job_id}")
        if existing["provider"] != MANUAL_PROVIDER:
            raise ValueError(f"job {job_id} is not a manual upload")
        return existing
    outcome = manual_upload_outcome(
        conn,
        job,
        pdf_document_parser=pdf_document_parser,
        pdf_image_downloader=pdf_image_downloader,
        pdf_figure_locator=pdf_figure_locator,
        pdf_page_extractor=pdf_page_extractor,
        image_describer=image_describer,
        asset_store=asset_store,
    )
    if not outcome.succeeded:
        from universe.acquisition.runner import Outcome, _record_failure

        return _record_failure(
            conn,
            job,
            Outcome(
                None,
                outcome.failure_code or "manual_acquisition_failed",
                outcome.provider,
                outcome.tool,
                outcome.diagnostics,
                tool_version=outcome.tool_version,
            ),
        )
    from universe.acquisition.runner import Outcome, _record_success

    return _record_success(
        conn,
        job,
        Outcome(
            outcome.markdown,
            None,
            outcome.provider,
            outcome.tool,
            outcome.diagnostics,
            tool_version=outcome.tool_version,
            content_hash=outcome.diagnostics.get("input_manifest_sha256"),
            raw_markdown=outcome.raw_markdown,
        ),
    )


def manual_upload_outcome(
    conn: psycopg.Connection,
    claimed_job: Mapping[str, Any],
    *,
    pdf_document_parser=parse_pdf_with_firecrawl,
    pdf_image_downloader=None,
    pdf_figure_locator=None,
    pdf_page_extractor=extract_pdf_pages_with_poppler,
    image_describer: Any | None = None,
    asset_store: AssetStore | None = None,
) -> ManualOutcome:
    """Build an Outcome for a job already claimed by the shared worker.

    This seam neither claims nor finalizes the job. It lets ``process_next_job``
    dispatch on ``provider`` without a second lease transition.
    """
    if claimed_job.get("provider") != MANUAL_PROVIDER:
        raise ValueError("manual_upload_outcome requires a manual-upload job")
    if claimed_job.get("status") != "running" or not claimed_job.get("claim_token"):
        raise ValueError("manual_upload_outcome requires a currently claimed job")
    job_id = str(claimed_job["id"])
    source = conn.execute(
        "SELECT title FROM source WHERE id = %s", (claimed_job["source_id"],)
    ).fetchone()
    assets = list_manual_assets(conn, job_id)
    conn.commit()
    store = asset_store or asset_store_from_env()
    manifest_sha = _input_manifest_sha(assets) if assets else None
    try:
        if not assets:
            raise ManualAcquisitionError("manual_assets_missing", "missing_inputs")
        for asset in assets:
            try:
                asset["body"] = store.get(asset["storage_key"])
            except Exception as exc:
                raise ManualAcquisitionError(
                    "manual_asset_unavailable", "asset_storage_read_failed"
                ) from exc
        if assets[0]["kind"] == "pdf":
            result = acquire_pdf_document(
                conn,
                job=claimed_job,
                title=_markdown_inline(source[0] if source else assets[0]["filename"]),
                pdf_asset=assets[0],
                asset_store=store,
                document_parser=pdf_document_parser,
                **(
                    {"image_downloader": pdf_image_downloader}
                    if pdf_image_downloader is not None
                    else {}
                ),
                figure_locator=pdf_figure_locator,
                page_extractor=pdf_page_extractor,
            )
            markdown = result.enriched_markdown
            raw_markdown = result.raw_markdown
            diagnostics = result.diagnostics
            tool = PDF_PAGE_TOOL
            tool_version = PDF_PAGE_TOOL_VERSION
        else:
            markdown, diagnostics, tool, tool_version = _acquire_images(
                source[0] if source else None,
                assets,
                image_describer or OpenRouterImageDescriber(),
            )
            raw_markdown = None
        diagnostics.update(
            {
                "input_manifest_sha256": manifest_sha,
                "tool_version": tool_version,
            }
        )
        return ManualOutcome(
            markdown,
            None,
            MANUAL_PROVIDER,
            tool,
            tool_version,
            diagnostics,
            raw_markdown,
        )
    except (ManualAcquisitionError, PdfExtractionError) as exc:
        diagnostics = {
            "category": exc.category,
            "input_mode": _input_mode(assets),
            "input_manifest_sha256": manifest_sha,
            "tool_version": None,
        }
        return ManualOutcome(
            None, exc.code, MANUAL_PROVIDER, "none", None, diagnostics
        )
    except Exception as exc:  # never retain request media, response bodies, or keys
        diagnostics = {
            "category": "manual_adapter_error",
            "exception": type(exc).__name__,
            "input_mode": _input_mode(assets),
            "input_manifest_sha256": manifest_sha,
            "tool_version": None,
        }
        return ManualOutcome(
            None,
            "manual_acquisition_failed",
            MANUAL_PROVIDER,
            "none",
            None,
            diagnostics,
        )


def _claim_manual_job(conn: psycopg.Connection, job_id: str) -> dict | None:
    claim_token = uuid.uuid4().hex
    row = conn.execute(
        "UPDATE acquisition_job SET status = 'running',"
        " attempt_count = attempt_count + 1, claimed_at = now(), claim_token = %s,"
        " lease_expires_at = now() + (%s * interval '1 minute'), updated_at = now(),"
        " diagnostics = '{}'::jsonb"
        " WHERE id = %s AND provider = %s AND"
        " (status = 'queued' OR (status = 'running' AND lease_expires_at < now()))"
        " RETURNING id, source_id, status, provider, attempt_count, artifact_id,"
        " failure_code, diagnostics, created_at, claimed_at, claim_token, finished_at",
        (claim_token, acquisition_lease_minutes(), job_id, MANUAL_PROVIDER),
    ).fetchone()
    conn.commit()
    if row is None:
        return None
    columns = (
        "id",
        "source_id",
        "status",
        "provider",
        "attempt_count",
        "artifact_id",
        "failure_code",
        "diagnostics",
        "created_at",
        "claimed_at",
        "claim_token",
        "finished_at",
    )
    return dict(zip(columns, row))


def _acquire_pdf(title: str | None, asset: dict, extractor) -> tuple[str, dict, str, str]:
    extracted = extractor(bytes(asset["body"]))
    if not isinstance(extracted, str):
        raise ManualAcquisitionError(
            "manual_pdf_extraction_failed", "invalid_pdf_extractor_result"
        )
    text = extracted.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        raise ManualAcquisitionError("manual_pdf_no_text", "pdf_has_no_extractable_text")
    heading = _markdown_inline(title or asset["filename"])
    markdown = (
        f"# {heading}\n\n"
        f"[Abrir PDF original](/api/source-assets/{asset['id']})\n\n"
        f"{text}\n"
    )
    diagnostics = {
        "asset_count": 1,
        "asset_ids": [asset["id"]],
        "input_mode": "pdf",
        "total_bytes": asset["byte_size"],
        "extractor": {"tool": "pdftotext", "tool_version": PDF_TOOL_VERSION},
    }
    return markdown, diagnostics, "pdftotext", PDF_TOOL_VERSION


def _acquire_images(
    title: str | None, assets: list[dict], describer: Any
) -> tuple[str, dict, str, str]:
    sections = [f"# {_markdown_inline(title or 'Fonte reconstruída por imagens')}"]
    descriptions: list[ImageDescription] = []
    image_diagnostics: list[dict[str, Any]] = []
    for asset in assets:
        manual_asset = ManualAsset(
            filename=asset["filename"],
            mime_type=asset["mime_type"],
            body=bytes(asset["body"]),
            kind=asset["kind"],
            metadata=asset["metadata"],
            ordinal=asset["ordinal"],
            sha256=asset["sha256"],
        )
        label_kind = "Screenshot" if asset["kind"] == "screenshot" else "Image"
        label = f"{label_kind} {asset['ordinal']} — {_markdown_inline(asset['filename'])}"
        image_line = f"![{_markdown_alt(label)}](/api/source-assets/{asset['id']})"
        try:
            description = describer.describe(manual_asset)
        except Exception as exc:
            sections.append(
                "\n".join(
                    [
                        f"## {label}",
                        "",
                        image_line,
                        "",
                        "Image analysis: unresolved.",
                    ]
                )
            )
            image_diagnostics.append(
                {
                    "asset_id": asset["id"],
                    "ordinal": asset["ordinal"],
                    "kind": asset["kind"],
                    "status": "failed",
                    "failure_code": "manual_image_description_failed",
                    "diagnostics": {
                        "category": "image_description_failed",
                        "exception": type(exc).__name__,
                    },
                }
            )
            continue
        if not isinstance(description, ImageDescription):
            sections.append(
                "\n".join(
                    [
                        f"## {label}",
                        "",
                        image_line,
                        "",
                        "Image analysis: unresolved.",
                    ]
                )
            )
            image_diagnostics.append(
                {
                    "asset_id": asset["id"],
                    "ordinal": asset["ordinal"],
                    "kind": asset["kind"],
                    "status": "failed",
                    "failure_code": "manual_image_description_failed",
                    "diagnostics": {"category": "invalid_image_description"},
                }
            )
            continue
        descriptions.append(description)
        visible_text = _markdown_visual_field(description.visible_text) or "No legible text."
        sections.append(
            "\n".join(
                [
                    f"## {label}",
                    "",
                    image_line,
                    "",
                    f"Image summary: {_markdown_visual_field(description.description)}",
                    "",
                    f"Visible text: {visible_text}",
                ]
            )
        )
        image_diagnostics.append(
            {
                "asset_id": asset["id"],
                "ordinal": asset["ordinal"],
                "kind": asset["kind"],
                "status": "succeeded",
                "requested_model": description.requested_model,
                "response_model": description.response_model,
                "provider": description.provider,
                "usage": description.usage,
                "duration_ms": description.duration_ms,
                "result": {
                    "description": description.description,
                    "visible_text": description.visible_text,
                },
            }
        )
    markdown = "\n\n".join(sections).rstrip() + "\n"
    diagnostics = {
        "asset_count": len(assets),
        "asset_ids": [asset["id"] for asset in assets],
        "input_mode": "images",
        "total_bytes": sum(asset["byte_size"] for asset in assets),
        "model": _single_or_list([item.requested_model for item in descriptions]),
        "prompt_version": IMAGE_DESCRIPTION_PROMPT_VERSION,
        "provider": _single_or_list([item.provider for item in descriptions]),
        "usage": _sum_usage([item.usage for item in descriptions]),
        "images": image_diagnostics,
    }
    return (
        markdown,
        diagnostics,
        "openrouter-vision",
        IMAGE_DESCRIPTION_PROMPT_VERSION,
    )


def _record_manual_success(
    conn: psycopg.Connection,
    job: dict,
    assets: list[dict],
    markdown: str,
    diagnostics: dict,
    *,
    tool: str,
    tool_version: str,
) -> dict:
    snapshot_id = f"{job['source_id']}:snap:{job['id']}:{job['attempt_count']:02d}"
    artifact_id = f"{snapshot_id}:markdown"
    content_hash = _input_manifest_sha(assets)
    conn.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, captured_at, content_hash, status, failure_note)"
        " VALUES (%s, %s, now(), %s, 'ok', NULL)",
        (snapshot_id, job["source_id"], content_hash),
    )
    conn.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, tool_version, body)"
        " VALUES (%s, %s, 'markdown', %s, %s, %s)",
        (artifact_id, snapshot_id, tool, tool_version, markdown),
    )
    persist_manual_image_analyses(conn, job, diagnostics)
    updated = conn.execute(
        "UPDATE acquisition_job SET status = 'succeeded', artifact_id = %s,"
        " diagnostics = %s, finished_at = now(), lease_expires_at = NULL,"
        " claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (artifact_id, Jsonb(diagnostics), job["id"], job["claim_token"]),
    )
    if updated.rowcount != 1:
        conn.rollback()
    else:
        conn.commit()
    from universe.acquisition.runner import get_job

    result = get_job(conn, job["id"])
    assert result is not None
    return result


def persist_manual_image_analyses(
    conn: psycopg.Connection,
    job: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
) -> list[str]:
    """Persist per-image vision outcomes inside the caller's claim transaction."""
    if diagnostics.get("input_mode") != "images":
        return []
    prompt_version = diagnostics.get("prompt_version")
    images = diagnostics.get("images")
    if not isinstance(prompt_version, str) or not prompt_version:
        raise ValueError("manual image diagnostics require a prompt version")
    if not isinstance(images, list) or not images:
        raise ValueError("manual image diagnostics require per-image results")

    inserted_ids: list[str] = []
    for item in images:
        if not isinstance(item, Mapping):
            raise ValueError("manual image analysis must be an object")
        asset_id = item.get("asset_id")
        ordinal = item.get("ordinal")
        status = item.get("status", "succeeded")
        result = item.get("result") or {}
        failure_code = item.get("failure_code")
        analysis_diagnostics = item.get("diagnostics") or {}
        if (
            not isinstance(asset_id, str)
            or not asset_id
            or not isinstance(ordinal, int)
            or ordinal < 1
            or not isinstance(result, Mapping)
            or not isinstance(analysis_diagnostics, Mapping)
            or status not in {"succeeded", "failed"}
        ):
            raise ValueError("manual image diagnostics contain an invalid result")
        if status == "succeeded" and (
            failure_code is not None
            or not isinstance(result.get("description"), str)
            or not result["description"].strip()
            or not isinstance(result.get("visible_text"), str)
        ):
            raise ValueError("manual image diagnostics contain an invalid result")
        if status == "failed" and (
            not isinstance(failure_code, str) or not failure_code
        ):
            raise ValueError("manual image diagnostics contain an invalid failure")
        identity = hashlib.sha256(
            f"{job['id']}:{asset_id}:{prompt_version}".encode("utf-8")
        ).hexdigest()[:32]
        analysis_id = f"analysis-manual-{identity}"
        inserted = conn.execute(
            "INSERT INTO source_asset_analysis"
            " (id, source_asset_id, purpose, status, prompt_version,"
            "  requested_model, response_model, provider, result, usage,"
            "  duration_ms, failure_code, diagnostics)"
            " SELECT %s, a.id, 'manual_image_description', %s, %s,"
            "  %s, %s, %s, %s, %s, %s, %s, %s"
            " FROM source_asset a"
            " WHERE a.id = %s AND a.acquisition_job_id = %s AND a.source_id = %s"
            " ON CONFLICT (id) DO NOTHING RETURNING id",
            (
                analysis_id,
                status,
                prompt_version,
                item.get("requested_model"),
                item.get("response_model"),
                item.get("provider"),
                Jsonb(dict(result)),
                Jsonb(dict(item.get("usage") or {})),
                item.get("duration_ms"),
                failure_code,
                Jsonb(
                    {
                        "ordinal": ordinal,
                        "kind": item.get("kind"),
                        **dict(analysis_diagnostics),
                    }
                ),
                asset_id,
                job["id"],
                job["source_id"],
            ),
        ).fetchone()
        if inserted is None:
            existing = conn.execute(
                "SELECT source_asset_id FROM source_asset_analysis WHERE id = %s",
                (analysis_id,),
            ).fetchone()
            if existing != (asset_id,):
                raise ValueError("manual image analysis asset lineage mismatch")
        inserted_ids.append(analysis_id)
    return inserted_ids


def _record_manual_failure(
    conn: psycopg.Connection,
    job: dict,
    failure_code: str,
    diagnostics: dict,
) -> dict:
    snapshot_id = (
        f"{job['source_id']}:snap:failed:{job['id']}:{job['attempt_count']:02d}"
    )
    conn.execute(
        "INSERT INTO source_snapshot"
        " (id, source_id, captured_at, content_hash, status, failure_note)"
        " VALUES (%s, %s, NULL, NULL, 'failed', %s)",
        (snapshot_id, job["source_id"], failure_code),
    )
    updated = conn.execute(
        "UPDATE acquisition_job SET status = 'failed', failure_code = %s,"
        " diagnostics = %s, finished_at = now(), lease_expires_at = NULL,"
        " claim_token = NULL, updated_at = now()"
        " WHERE id = %s AND status = 'running' AND claim_token = %s",
        (failure_code, Jsonb(diagnostics), job["id"], job["claim_token"]),
    )
    if updated.rowcount != 1:
        conn.rollback()
    else:
        conn.commit()
    from universe.acquisition.runner import get_job

    result = get_job(conn, job["id"])
    assert result is not None
    return result


def _input_mode(assets: Sequence[dict]) -> str | None:
    if not assets:
        return None
    return "pdf" if assets[0].get("kind") == "pdf" else "images"


def _input_manifest_sha(assets: Sequence[Mapping[str, Any] | ManualAsset]) -> str:
    """Hash the ordered capture manifest, not model-produced Markdown."""
    manifest = "\n".join(
        f"{_asset_field(asset, 'ordinal')}:{_asset_field(asset, 'kind')}:"
        f"{_asset_field(asset, 'mime_type')}:{_asset_field(asset, 'sha256')}"
        for asset in assets
    )
    return hashlib.sha256(manifest.encode("utf-8")).hexdigest()


def _asset_field(asset: Mapping[str, Any] | ManualAsset, key: str) -> Any:
    return asset[key] if isinstance(asset, Mapping) else getattr(asset, key)


def _markdown_inline(value: str) -> str:
    return re.sub(r"\s+", " ", str(value)).strip().replace("#", "\\#")


def _markdown_alt(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _markdown_visual_field(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _single_or_list(values: Sequence[str]) -> str | list[str]:
    unique = list(dict.fromkeys(values))
    return unique[0] if len(unique) == 1 else unique


def _sum_usage(items: Sequence[Mapping[str, Any]]) -> dict[str, int | float]:
    totals: dict[str, int | float] = {}
    for item in items:
        for key, value in item.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                totals[key] = totals.get(key, 0) + value
    return totals


def validate_manual_assets(
    assets: Sequence[ManualAsset],
    *,
    max_total_bytes: int = MAX_TOTAL_BYTES,
    max_image_pixels: int = MAX_IMAGE_PIXELS,
) -> list[ManualAsset]:
    """Validate one PDF or 1-50 ordered PNG/JPEG/WEBP inputs."""
    items = list(assets)
    if not items:
        raise ValueError("manual input requires at least one file")
    if sum(len(item.body) for item in items if isinstance(item.body, bytes)) > max_total_bytes:
        raise ValueError("manual input exceeds the total size limit")

    is_pdf_mode = len(items) == 1 and items[0].kind == "pdf"
    if is_pdf_mode:
        item = items[0]
        mime_type = _canonical_mime(item.mime_type)
        if mime_type != "application/pdf":
            raise ValueError("manual PDF input must use application/pdf")
        if not isinstance(item.body, bytes) or not item.body.startswith(b"%PDF-"):
            raise ValueError("file does not contain a valid PDF signature")
        return [_validated(item, 1, mime_type)]

    if len(items) > MAX_IMAGE_COUNT:
        raise ValueError(f"manual image input accepts at most {MAX_IMAGE_COUNT} files")
    validated: list[ManualAsset] = []
    for ordinal, item in enumerate(items, 1):
        mime_type = _canonical_mime(item.mime_type)
        if item.kind not in {"screenshot", "image"} or mime_type not in IMAGE_MIME_TYPES:
            raise ValueError("manual images must be PNG, JPEG or WEBP and use image/screenshot kind")
        dimensions = _image_dimensions(item.body, mime_type)
        if dimensions is None:
            raise ValueError(f"{item.filename!r} does not match its declared raster MIME type")
        width, height = dimensions
        if width * height > max_image_pixels:
            raise ValueError(f"{item.filename!r} exceeds the image pixel limit")
        metadata = dict(item.metadata)
        metadata.update({"width": width, "height": height})
        validated.append(_validated(replace(item, metadata=metadata), ordinal, mime_type))
    return validated


def _validated(item: ManualAsset, ordinal: int, mime_type: str) -> ManualAsset:
    if not isinstance(item.body, bytes) or not item.body:
        raise ValueError("manual input cannot be empty")
    filename = _safe_filename(item.filename)
    return replace(
        item,
        filename=filename,
        mime_type=mime_type,
        ordinal=ordinal,
        sha256=hashlib.sha256(item.body).hexdigest(),
    )


def _canonical_mime(value: str) -> str:
    mime_type = str(value or "").split(";", 1)[0].strip().lower()
    return "image/jpeg" if mime_type == "image/jpg" else mime_type


def _safe_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    """Keep presentation metadata only; never persist request logs or secrets."""
    result: dict[str, Any] = {}
    for key in SAFE_METADATA_KEYS:
        item = value.get(key)
        if isinstance(item, str):
            result[key] = item[:1000]
        elif isinstance(item, (int, float, bool)) or item is None:
            result[key] = item
    return result


def _safe_filename(value: str) -> str:
    filename = str(value or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    filename = re.sub(r"[\x00-\x1f\x7f]", "", filename)[:255]
    if not filename or filename in {".", ".."}:
        raise ValueError("manual input filename cannot be blank")
    return filename


def _image_dimensions(body: bytes, mime_type: str) -> tuple[int, int] | None:
    if not isinstance(body, bytes):
        return None
    if mime_type == "image/png":
        if len(body) < 24 or body[:8] != b"\x89PNG\r\n\x1a\n" or body[12:16] != b"IHDR":
            return None
        width, height = int.from_bytes(body[16:20], "big"), int.from_bytes(body[20:24], "big")
    elif mime_type == "image/jpeg":
        dimensions = _jpeg_dimensions(body)
        if dimensions is None:
            return None
        width, height = dimensions
    else:
        dimensions = _webp_dimensions(body)
        if dimensions is None:
            return None
        width, height = dimensions
    return (width, height) if width > 0 and height > 0 else None


def _jpeg_dimensions(body: bytes) -> tuple[int, int] | None:
    if len(body) < 4 or body[:3] != b"\xff\xd8\xff":
        return None
    position = 2
    sof_markers = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while position + 4 <= len(body):
        if body[position] != 0xFF:
            position += 1
            continue
        while position < len(body) and body[position] == 0xFF:
            position += 1
        if position >= len(body):
            return None
        marker = body[position]
        position += 1
        if marker in {0xD8, 0xD9}:
            continue
        if position + 2 > len(body):
            return None
        segment_length = int.from_bytes(body[position : position + 2], "big")
        if segment_length < 2 or position + segment_length > len(body):
            return None
        if marker in sof_markers:
            if segment_length < 7:
                return None
            height = int.from_bytes(body[position + 3 : position + 5], "big")
            width = int.from_bytes(body[position + 5 : position + 7], "big")
            return width, height
        position += segment_length
    return None


def _webp_dimensions(body: bytes) -> tuple[int, int] | None:
    if len(body) < 30 or body[:4] != b"RIFF" or body[8:12] != b"WEBP":
        return None
    kind = body[12:16]
    if kind == b"VP8X":
        return 1 + int.from_bytes(body[24:27], "little"), 1 + int.from_bytes(body[27:30], "little")
    if kind == b"VP8 " and len(body) >= 30 and body[23:26] == b"\x9d\x01\x2a":
        return int.from_bytes(body[26:28], "little") & 0x3FFF, int.from_bytes(body[28:30], "little") & 0x3FFF
    if kind == b"VP8L" and len(body) >= 25 and body[20] == 0x2F:
        bits = int.from_bytes(body[21:25], "little")
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None
