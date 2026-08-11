"""Manual source acquisition from one PDF or ordered raster images.

The module is deliberately independent of the web layer: callers persist one
explicit source-local job with :func:`create_manual_upload_job`, then execute
that exact job with :func:`acquire_manual_upload`.  Successful execution stops
at an immutable Markdown artifact and never starts KC extraction.
"""

from __future__ import annotations

import hashlib
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
from universe.acquisition.ordered_reconstruction import (
    ORDERED_RECONSTRUCTION_TOOL,
    ORDERED_RECONSTRUCTION_VERSION,
    PdfBuilder,
    ordered_page_from_asset,
    reconstruct_ordered_document,
)
from universe.settings import acquisition_lease_minutes


MAX_TOTAL_BYTES = 30 * 1024 * 1024
MAX_IMAGE_COUNT = 50
MAX_IMAGE_PIXELS = 40_000_000
IMAGE_MIME_TYPES = {"image/png", "image/jpeg", "image/webp"}
MANUAL_PROVIDER = "manual-upload/v1"
SAFE_METADATA_KEYS = {
    "caption",
    "captured_at",
    "height",
    "label",
    "notes",
    "page_number",
    "width",
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
        " WHERE acquisition_job_id = %s"
        " AND kind IN ('pdf', 'screenshot', 'image')"
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
    ordered_pdf_builder: PdfBuilder | None = None,
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
        ordered_pdf_builder=ordered_pdf_builder,
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
    ordered_pdf_builder: PdfBuilder | None = None,
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
            result = reconstruct_ordered_document(
                conn,
                job=claimed_job,
                title=source[0] if source else "Fonte reconstruída por imagens",
                pages=[ordered_page_from_asset(asset) for asset in assets],
                input_mode="ordered_images",
                asset_store=store,
                document_parser=pdf_document_parser,
                **(
                    {"image_downloader": pdf_image_downloader}
                    if pdf_image_downloader is not None
                    else {}
                ),
                figure_locator=pdf_figure_locator,
                pdf_builder=ordered_pdf_builder,
            )
            markdown = result.enriched_markdown
            raw_markdown = result.raw_markdown
            diagnostics = result.diagnostics
            tool = ORDERED_RECONSTRUCTION_TOOL
            tool_version = ORDERED_RECONSTRUCTION_VERSION
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
