"""Thin HTML/API surface for versioned syllabi and explicit acquisition.

The page reads immutable syllabus versions and operational acquisition state.
Queueing is always source-local and explicit. For public articles the worker
publishes Markdown only after acquisition, visual enrichment and passage
cleanup. Task and Knowledge Component generation remain separate actions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import tempfile
from collections.abc import Callable
from contextlib import asynccontextmanager
from html import escape
from pathlib import Path
from urllib.parse import quote, urlsplit

import psycopg
from fastapi import Body, FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from latex2mathml import converter as latex2mathml
from markdown_it import MarkdownIt
from mdit_py_plugins.dollarmath import dollarmath_plugin

from universe import companion_seam, curation, kc_pipeline, lesson_knowledge, syllabus_knowledge
from universe.acquisition.image_jobs import (
    list_article_images_for_artifact,
)
from universe.acquisition.manual_uploads import (
    IMAGE_MIME_TYPES,
    MAX_IMAGE_COUNT,
    MAX_TOTAL_BYTES,
    ManualAsset,
    create_manual_upload_job,
    get_manual_asset,
)
from universe.acquisition.runner import enqueue_source, process_next_work_item
from universe.acquisition.videos import (
    VideoAdapter,
    YtDlpYouTubeAdapter,
    latest_preflight,
    refresh_preflight,
)
from universe.assets import AssetStore, asset_store_from_env
from universe.db import connect
from universe.graph_identity import (
    GRAPH_ID_CONFLICT_MESSAGE,
    GraphIdConflict,
    graph_id_for,
)
from universe.syllabus import (
    SyllabusAlreadyExists,
    SyllabusVersionConflict,
    curate_syllabus,
    get_syllabus_history,
    get_syllabus_version,
    get_syllabus_workbook,
    import_workbook,
    list_syllabi,
    slugify,
    update_source_review,
    validate_syllabus_id,
)
from universe.syllabus_reconciliation import (
    apply_reconciliation,
    create_reconciliation,
    get_reconciliation,
)
from universe.settings import acquisition_poll_seconds
from universe.source_publication import current as current_source_publication
from universe.source_publication import current_many as current_source_publications

STATIC_DIR = Path(__file__).with_name("static")
MAX_WORKBOOK_BYTES = 30 * 1024 * 1024
LOCAL_ASSET_URL = re.compile(r"^/api/source-assets/[A-Za-z0-9][A-Za-z0-9._:-]*$")
LOGGER = logging.getLogger(__name__)
MAX_RENDERED_MATH_CHARS = 20_000
UNSAFE_LATEX_COMMAND = re.compile(
    r"\\(?:class|href|html|includegraphics|style|url)\b",
    re.IGNORECASE,
)


def _render_safe_image(renderer, tokens, idx, options, env) -> str:
    """Render only same-origin, ledger-backed images as ``img`` elements.

    Firecrawl Markdown may contain arbitrary third-party image URLs. Loading
    them from the review dialog would leak the reviewer's IP/cookies and make
    the artifact non-deterministic. Keep those references visible as links;
    only immutable SourceAssets served by this application may auto-load.
    """
    token = tokens[idx]
    source = str(token.attrGet("src") or "")
    if token.children:
        alt = renderer.renderInlineAsText(token.children, options, env)
    else:
        alt = ""
    token.attrSet("alt", alt)
    if LOCAL_ASSET_URL.fullmatch(source):
        return renderer.renderToken(tokens, idx, options, env)

    try:
        parsed = urlsplit(source)
    except ValueError:
        parsed = None
    label = escape(alt.strip() or "Imagem externa", quote=False)
    if parsed is not None and parsed.scheme.lower() in {"http", "https"} and parsed.netloc:
        href = escape(source, quote=True)
        return (
            '<span class="syl-remote-image">'
            f'{label} — imagem remota não carregada '
            f'<a href="{href}" target="_blank" rel="noopener noreferrer">'
            "abrir imagem original</a></span>"
        )
    return f'<span class="syl-remote-image">{label} — imagem não carregada</span>'


def _has_balanced_latex_groups(source: str) -> bool:
    """Reject truncated brace groups before passing source to the converter."""
    depth = 0
    for index, character in enumerate(source):
        if character not in "{}":
            continue
        backslashes = 0
        cursor = index - 1
        while cursor >= 0 and source[cursor] == "\\":
            backslashes += 1
            cursor -= 1
        if backslashes % 2:
            continue
        if character == "{":
            depth += 1
        elif depth == 0:
            return False
        else:
            depth -= 1
    return depth == 0


def _render_math_source(source: str, *, display_mode: bool) -> str:
    """Render safe MathML, falling back to escaped LaTeX when conversion fails."""
    delimiter = "$$" if display_mode else "$"

    def fallback() -> str:
        original = f"{delimiter}{source}{delimiter}"
        return f'<code class="syl-math-source">{escape(original, quote=False)}</code>'

    if (
        not source
        or len(source) > MAX_RENDERED_MATH_CHARS
        or "\x00" in source
        or UNSAFE_LATEX_COMMAND.search(source)
        or not _has_balanced_latex_groups(source)
    ):
        return fallback()

    try:
        mathml = latex2mathml.convert(
            source,
            display="block" if display_mode else "inline",
        )
    except Exception:  # The source is third-party extracted LaTeX.
        return fallback()

    # The converter escapes text, but some LaTeX extensions can generate
    # navigable/style attributes. Never expose those through extracted source.
    if re.search(r'\s(?:href|src|style|on[a-z]+)="', mathml, re.IGNORECASE):
        return fallback()
    css_class = "syl-math-block" if display_mode else "syl-math-inline"
    return mathml.replace("<math ", f'<math class="{css_class}" ', 1)


def _render_math(source: str, options: dict) -> str:
    return _render_math_source(source, display_mode=bool(options["display_mode"]))


def _markdown_renderer() -> MarkdownIt:
    """Build the local renderer used by the native Markdown dialog.

    Raw HTML and linkification are disabled.  MarkdownIt's URL validator also
    refuses unsafe schemes such as ``javascript:``.  The browser receives only
    this rendered representation, never an instruction to execute source HTML.
    """
    renderer = MarkdownIt(
        "commonmark",
        {"html": False, "linkify": False, "typographer": False},
    ).enable("table")
    renderer.use(
        dollarmath_plugin,
        renderer=_render_math,
        allow_labels=False,
        allow_blank_lines=False,
    )
    renderer.add_render_rule("image", _render_safe_image)
    return renderer


MARKDOWN = _markdown_renderer()


def _acquisition_capability(media_type: str | None) -> dict:
    """Describe what the web surface can truthfully enqueue today.

    The durable runner keeps its own defensive unsupported-media failure, but
    the HTML/API boundary must not offer a job that is already known to have no
    Adapter.  Adding a new Adapter therefore requires making it explicit here
    instead of silently turning the queue button into a paid error generator.
    """
    if media_type == "article":
        return {
            "supported": True,
            "adapter": "firecrawl",
            "label": "Firecrawl",
        }
    if media_type == "book":
        return {
            "supported": True,
            "adapter": "browserbase-book",
            "label": "Browserbase + reconstrução ordenada",
        }
    if media_type == "video":
        return {
            "supported": True,
            "adapter": "youtube",
            "label": "YouTube",
        }
    kind = {"video": "vídeo", "book": "livro"}.get(media_type, "fonte")
    return {
        "supported": False,
        "adapter": None,
        "label": "Adapter indisponível",
        "reason": (
            f"O adapter de {kind} ainda não está disponível. "
            "Esta fonte não pode ser enfileirada por enquanto."
        ),
    }


def _diagnostic_message(diagnostics: dict, failure_code: str) -> str:
    provider_message = (
        diagnostics.get("target_message")
        or diagnostics.get("provider_message")
        or diagnostics.get("provider_warning")
        or diagnostics.get("message")
    )
    target_status = diagnostics.get("target_http_status")
    provider_status = diagnostics.get("provider_http_status") or diagnostics.get(
        "http_status"
    )
    status = target_status or provider_status
    category = diagnostics.get("category")
    labels = {
        "not_found": "A fonte retornou 404 (não encontrada).",
        "target_not_found": "A fonte retornou 404 (não encontrada).",
        "target_access_denied": "O site alvo recusou o acesso (401/403).",
        "source_access_denied": "O site alvo recusou o acesso (401/403).",
        "source_rate_limited": "O site alvo limitou temporariamente as chamadas.",
        "provider_authentication": "O Firecrawl recusou a autenticação da API.",
        "provider_access_denied": "O Firecrawl recusou esta chamada da API.",
        "provider_permission": "O Firecrawl recusou esta chamada da API (403).",
        "provider_resource_not_found": "O endpoint solicitado no Firecrawl não foi encontrado.",
        "provider_conflict": "O Firecrawl recusou a chamada por conflito de estado.",
        "provider_timeout": "O Firecrawl excedeu o tempo limite da chamada.",
        "provider_rejected": "O Firecrawl não conseguiu processar esta fonte.",
        "insufficient_credits": "A conta do Firecrawl está sem créditos suficientes.",
        "invalid_request": "O Firecrawl recusou os dados da chamada.",
        "payload_too_large": "A fonte excedeu o volume aceito pelo Firecrawl.",
        "extraction_rejected": "O Firecrawl recusou a extração desta fonte.",
        "rate_limited": "O provedor limitou temporariamente as chamadas.",
        "provider_unavailable": "O provedor de extração ficou indisponível.",
        "target_unavailable": "O site alvo ficou temporariamente indisponível.",
        "robots_blocked": "O site bloqueou a extração por robots.txt.",
        "anti_bot_blocked": "O site apresentou uma proteção anti-bot ou captcha.",
        "authentication_required": "A fonte exige login, assinatura ou autenticação.",
        "blocked_content": "O conteúdo parece estar atrás de paywall ou proteção anti-bot.",
        "error_page": "A fonte retornou uma página de erro no lugar do conteúdo.",
        "request_timeout": "A chamada excedeu o tempo limite.",
        "dns_failure": "O domínio da fonte não pôde ser localizado.",
        "tls_error": "A conexão segura com a fonte falhou.",
        "empty_content": "A extração terminou sem conteúdo utilizável.",
        "invalid_provider_response": "O Firecrawl retornou uma resposta inválida.",
        "transport_error": "A conexão terminou antes de a página ser obtida.",
        "invalid_source_url": "O link da fonte não é uma URL pública válida.",
        "unsupported_media_kind": "Esse tipo de fonte ainda não possui Adapter de aquisição.",
        "video_metadata_unavailable": "Os metadados do YouTube estão temporariamente indisponíveis.",
        "video_caption_download_failed": "A legenda enviada foi listada, mas não pôde ser baixada.",
        "video_caption_parse_failed": "A legenda enviada não contém trechos temporizados utilizáveis.",
        "video_audio_download_failed": "O áudio do vídeo não pôde ser baixado.",
        "video_ffmpeg_unavailable": "O preparador de áudio ffmpeg/ffprobe não está disponível.",
        "video_ffmpeg_failed": "O áudio não pôde ser dividido em trechos para transcrição.",
        "video_stt_authentication_failed": "O OpenRouter recusou a autenticação da transcrição.",
        "video_stt_rate_limited": "O OpenRouter limitou temporariamente a transcrição.",
        "video_stt_provider_failure": "O OpenRouter não concluiu um trecho da transcrição.",
        "video_stt_chunk_failed": "Um trecho da transcrição falhou; os demais foram preservados para a tentativa seletiva.",
        "video_stt_empty_transcript": "A transcrição retornou sem texto utilizável.",
        "video_stt_language_mismatch": "Um trecho da transcrição veio em outro idioma.",
        "video_transcript_assembly_failed": "A transcrição temporizada não pôde ser montada em Markdown.",
        "pdf_extractor_unavailable": "O leitor de PDF não está disponível no servidor.",
        "pdf_extraction_timeout": "A leitura do PDF excedeu o tempo limite.",
        "pdf_extraction_failed": "O PDF não pôde ser lido.",
        "invalid_pdf_extractor_result": "O leitor de PDF devolveu um resultado inválido.",
        "pdf_has_no_extractable_text": (
            "O PDF não contém texto extraível. Envie as páginas como imagens ordenadas."
        ),
        "external_document_export_disabled": (
            "O envio de PDFs privados ao Firecrawl não foi habilitado neste ambiente."
        ),
        "firecrawl_transport_error": "A conexão com o Firecrawl falhou durante o PDF.",
        "firecrawl_retries_exhausted": "O Firecrawl não concluiu o PDF após as tentativas.",
        "firecrawl_provider_error": "O Firecrawl recusou o processamento do PDF.",
        "asset_storage_read_failed": "O arquivo preservado não pôde ser lido do armazenamento.",
        "missing_inputs": "Os arquivos desta extração manual não foram encontrados.",
        "image_description_failed": "A descrição visual de uma das imagens falhou.",
        "invalid_image_description": "A descrição visual retornou um formato inválido.",
        "manual_adapter_error": "O processamento do material enviado falhou.",
    }
    if category == "access_denied":
        base = (
            "O site alvo recusou o acesso (401/403)."
            if target_status
            else "O Firecrawl recusou a autenticação ou o acesso da API (401/403)."
        )
    else:
        base = labels.get(category) or failure_code.replace("_", " ")
    if target_status and str(target_status) not in base:
        base = f"{base} HTTP da fonte: {target_status}."
    elif provider_status and str(provider_status) not in base:
        base = f"{base} HTTP do Firecrawl: {provider_status}."
    details = [provider_message] if provider_message else []
    if diagnostics.get("provider_code"):
        details.append(f"Código Firecrawl: {diagnostics['provider_code']}.")
    if diagnostics.get("request_id"):
        details.append(f"Request ID: {diagnostics['request_id']}.")
    if diagnostics.get("provider_job_id"):
        details.append(f"Job Firecrawl: {diagnostics['provider_job_id']}.")
    return " ".join([base, *details]).strip()


def _image_failure_message(diagnostics: dict, failure_code: str | None) -> str:
    """Translate one optional image failure without obscuring its exact code."""
    category = diagnostics.get("category")
    labels = {
        "not_found": "A imagem retornou 404 (não encontrada).",
        "access_denied": "O servidor da imagem recusou o acesso (401/403).",
        "rate_limited": "O servidor da imagem limitou temporariamente as chamadas.",
        "request_timeout": "O download da imagem excedeu o tempo limite.",
        "dns_failure": "O domínio da imagem não pôde ser localizado.",
        "transport_error": "A conexão terminou antes de obter a imagem.",
        "payload_too_large": "A imagem excede o limite de tamanho.",
        "invalid_image_type": "O endereço não retornou um formato de imagem reconhecido.",
        "invalid_image": "O arquivo retornado não é uma imagem válida.",
        "invalid_image_url": "O endereço da imagem não é uma URL pública válida.",
        "private_network_target": "O endereço da imagem aponta para uma rede privada e foi bloqueado.",
        "image_analysis_failed": "A chamada visual falhou antes de produzir uma resposta válida.",
        "image_analysis_unavailable": "A análise visual não produziu uma decisão confiável.",
        "unsupported_model_image_type": "A imagem foi preservada localmente, mas este formato ainda não pode ser analisado pelo modelo visual.",
        "model_routing_unavailable": "O OpenRouter não encontrou um provider compatível para analisar esta imagem.",
        "model_authentication": "O OpenRouter recusou a autenticação da análise visual.",
        "model_credits": "A chave do OpenRouter não possui créditos para a análise visual.",
        "model_rate_limited": "O OpenRouter limitou temporariamente a análise visual.",
        "model_unavailable": "O provider visual do OpenRouter ficou indisponível.",
        "image_processing_failed": "A imagem foi preservada quando possível, mas sua análise falhou.",
    }
    message = labels.get(category)
    if message is None:
        message = (failure_code or "image_processing_failed").replace("_", " ")
    status = diagnostics.get("http_status")
    if status and str(status) not in message:
        message = f"{message} HTTP {status}."
    provider_status = diagnostics.get("provider_http_status")
    if provider_status and str(provider_status) not in message:
        message = f"{message} HTTP OpenRouter: {provider_status}."
    return message


def _empty_image_branch() -> dict:
    return {
        "state": "none",
        "total": 0,
        "queued": 0,
        "running": 0,
        "downloaded": 0,
        "useful": 0,
        "not_important": 0,
        "filtered": 0,
        "failed": 0,
        "active": False,
        "attention": 0,
    }


def _summarize_image_counts(counts: dict[str, int]) -> dict:
    summary = _empty_image_branch()
    for status in (
        "queued",
        "running",
        "downloaded",
        "useful",
        "not_important",
        "filtered",
        "failed",
    ):
        summary[status] = int(counts.get(status, 0))
    summary["total"] = sum(summary[status] for status in counts if status in {
        "queued", "running", "downloaded", "useful", "not_important", "filtered", "failed"
    })
    summary["active"] = bool(
        summary["queued"] or summary["running"] or summary["downloaded"]
    )
    summary["attention"] = summary["failed"]
    if summary["active"]:
        summary["state"] = "processing"
    elif summary["failed"]:
        summary["state"] = "attention"
    elif summary["total"]:
        summary["state"] = "ready"
    return summary


def _latest_source_state(conn: psycopg.Connection, source_ids: list[str]) -> dict[str, dict]:
    """Return the latest pipeline, canonical Markdown and KC signal per source."""
    if not source_ids:
        return {}
    states = {source_id: {} for source_id in source_ids}

    jobs = conn.execute(
        "SELECT DISTINCT ON (source_id) source_id, id, status, provider,"
        " attempt_count, artifact_id, failure_code, diagnostics, created_at,"
        " claimed_at, finished_at, request_input"
        " FROM acquisition_job WHERE source_id = ANY(%s)"
        " ORDER BY source_id, created_at DESC, id DESC",
        (source_ids,),
    ).fetchall()
    job_keys = (
        "id", "status", "provider", "attempt_count", "artifact_id",
        "failure_code", "diagnostics", "created_at", "claimed_at", "finished_at",
        "request_input",
    )
    for row in jobs:
        job = dict(zip(job_keys, row[1:]))
        if job["failure_code"]:
            job["error"] = _diagnostic_message(
                job.get("diagnostics") or {}, job["failure_code"]
            )
        states[row[0]]["job"] = job

    preflight_rows = conn.execute(
        "SELECT DISTINCT ON (source_id) source_id, id, status, title, channel,"
        " duration_seconds, uploaded_caption_languages,"
        " selected_caption_language, route, failure_code, diagnostics, created_at"
        " FROM video_preflight WHERE source_id = ANY(%s)"
        " ORDER BY source_id, created_at DESC, id DESC",
        (source_ids,),
    ).fetchall()
    preflight_keys = (
        "id status title channel duration_seconds uploaded_caption_languages"
        " selected_caption_language route failure_code diagnostics created_at"
    ).split()
    for row in preflight_rows:
        states[row[0]]["video_preflight"] = dict(zip(preflight_keys, row[1:]))

    latest_job_by_source = {
        source_id: state["job"]
        for source_id, state in states.items()
        if state.get("job")
    }
    stt_counts_by_job: dict[str, dict[str, int]] = {}
    if latest_job_by_source:
        stt_rows = conn.execute(
            "SELECT jc.acquisition_job_id, count(*),"
            " count(*) FILTER (WHERE c.status = 'succeeded'),"
            " count(*) FILTER (WHERE c.status = 'failed'),"
            " count(*) FILTER (WHERE c.status = 'running')"
            " FROM video_stt_job_chunk jc"
            " JOIN video_stt_chunk c ON c.id = jc.chunk_id"
            " WHERE jc.acquisition_job_id = ANY(%s)"
            " GROUP BY jc.acquisition_job_id",
            ([job["id"] for job in latest_job_by_source.values()],),
        ).fetchall()
        stt_counts_by_job = {
            row[0]: {
                "chunks_total": row[1],
                "chunks_succeeded": row[2],
                "chunks_failed": row[3],
                "chunks_running": row[4],
            }
            for row in stt_rows
        }
    cleanup_by_job: dict[str, dict] = {}
    if latest_job_by_source:
        cleanup_rows = conn.execute(
            "SELECT acquisition_job_id, id, status, source_artifact_id,"
            " cuts_run_id, cleanup_id, canonical_artifact_id, failure_code,"
            " diagnostics, created_at, finished_at"
            " FROM source_cleanup_job WHERE acquisition_job_id = ANY(%s)",
            ([job["id"] for job in latest_job_by_source.values()],),
        ).fetchall()
        cleanup_keys = (
            "id status source_artifact_id cuts_run_id cleanup_id"
            " canonical_artifact_id failure_code diagnostics created_at finished_at"
        ).split()
        cleanup_by_job = {
            row[0]: dict(zip(cleanup_keys, row[1:])) for row in cleanup_rows
        }

    image_artifact_sources: dict[str, str] = {}
    for source_id, publication in current_source_publications(
        conn, source_ids
    ).items():
        job = latest_job_by_source.get(source_id)
        baseline_id = (
            publication.metadata.get("source_markdown_artifact_id")
            or publication.artifact_id
        )
        if (
            job
            and (job.get("diagnostics") or {}).get("pipeline_requires_cleanup")
            and job.get("artifact_id")
            and not publication.is_previous_attempt
        ):
            baseline_id = job["artifact_id"]
        image_artifact_sources[baseline_id] = source_id
        states[source_id]["has_markdown"] = True
        states[source_id]["markdown"] = {
            "available": True,
            "artifact_id": publication.artifact_id,
            "tool": publication.tool,
            "tool_version": publication.tool_version,
            "created_at": publication.created_at,
            "is_previous_version": publication.is_previous_attempt,
        }

    # Keep image progress visible while the intermediate Markdown itself is
    # withheld. Candidates are keyed to the base acquisition artifact.
    for source_id, job in latest_job_by_source.items():
        if (
            (job.get("diagnostics") or {}).get("pipeline_requires_cleanup")
            and job.get("artifact_id")
        ):
            image_artifact_sources[job["artifact_id"]] = source_id

    for source_id, job in latest_job_by_source.items():
        diagnostics = job.get("diagnostics") or {}
        strict = bool(
            diagnostics.get("pipeline_requires_cleanup")
        )
        if job["status"] == "queued":
            pipeline_status = "queued"
        elif job["status"] == "running":
            pipeline_status = "extracting"
        elif job["status"] == "failed":
            pipeline_status = "failed"
        elif strict:
            cleanup = cleanup_by_job.get(job["id"])
            if diagnostics.get("visual_incomplete"):
                pipeline_status = "attention"
                states[source_id]["job"]["error"] = (
                    "A estrutura textual foi preservada, mas uma ou mais figuras "
                    "precisam de atenção antes da limpeza."
                )
            elif cleanup and cleanup["status"] == "succeeded":
                pipeline_status = "ready"
            elif cleanup and cleanup["status"] == "failed":
                pipeline_status = "failed"
                if cleanup.get("failure_code") == "no_teachable_content_preserved":
                    states[source_id]["job"]["error"] = (
                        "A limpeza terminou sem preservar nenhum conteúdo ensinável; "
                        "o resultado não foi publicado."
                    )
                else:
                    states[source_id]["job"]["error"] = (
                        "A limpeza do Markdown falhou; o resultado intermediário não foi publicado."
                    )
            elif cleanup:
                pipeline_status = "cleaning"
            else:
                pipeline_status = (
                    "images"
                    if job.get("provider") in {"firecrawl/v2", "youtube/v1"}
                    else "cleaning"
                )
        elif job.get("provider") == "manual-upload/v1":
            image_diagnostics = diagnostics.get("images") or []
            pipeline_status = (
                "attention"
                if any(item.get("status") == "failed" for item in image_diagnostics)
                else "ready"
            )
            if pipeline_status == "attention":
                states[source_id]["job"]["error"] = (
                    "A evidência manual foi preservada, mas uma ou mais imagens não puderam ser analisadas."
                )
        else:
            pipeline_status = "ready" if states[source_id].get("has_markdown") else "idle"
        states[source_id]["pipeline"] = {"status": pipeline_status}

    if image_artifact_sources:
        image_rows = conn.execute(
            "SELECT markdown_artifact_id, status, count(*)"
            " FROM source_image_candidate"
            " WHERE markdown_artifact_id = ANY(%s)"
            " GROUP BY markdown_artifact_id, status",
            (list(image_artifact_sources),),
        ).fetchall()
        counts_by_source: dict[str, dict[str, int]] = {}
        for artifact_id, status, count in image_rows:
            source_id = image_artifact_sources[artifact_id]
            counts_by_source.setdefault(source_id, {})[status] = count
        for source_id, counts in counts_by_source.items():
            states[source_id]["image_branch"] = _summarize_image_counts(counts)

    for source_id, job in latest_job_by_source.items():
        if job.get("provider") != "youtube/v1":
            continue
        diagnostics = job.get("diagnostics") or {}
        request_input = job.get("request_input") or {}
        route = diagnostics.get("transcript_route") or request_input.get(
            "transcript_route"
        )
        branch = states[source_id].get("image_branch") or _empty_image_branch()
        cleanup = cleanup_by_job.get(job["id"])
        if job["status"] == "queued":
            stage = "queued"
        elif job["status"] == "running":
            stage = (
                "speech_and_frames"
                if route in {"automatic_stt", "openrouter_stt"}
                else (
                    "visual_understanding"
                    if route == "visual_only"
                    else "frame_extraction"
                )
            )
        elif job["status"] == "failed":
            stage = "attention"
        elif cleanup and cleanup["status"] in {"queued", "running"}:
            stage = "canonical_cleanup"
        elif cleanup and cleanup["status"] == "succeeded":
            stage = "ready"
        elif cleanup and cleanup["status"] == "failed":
            stage = "attention"
        elif branch.get("active"):
            stage = "frame_analysis"
        else:
            stage = "evidence_composition"
        analyzed = sum(
            int(branch.get(status) or 0)
            for status in ("useful", "not_important", "filtered", "failed")
        )
        states[source_id]["video_progress"] = {
            "stage": stage,
            "speech": (
                "creator_captions"
                if route == "uploaded_caption"
                else (
                    "stt"
                    if route in {"automatic_stt", "openrouter_stt"}
                    else "absent"
                )
            ),
            "frames_total": int(branch.get("total") or 0),
            "frames_analyzed": analyzed,
            "frames_useful": int(branch.get("useful") or 0),
            "frames_failed": int(branch.get("failed") or 0),
            "speech_diagnostics": stt_counts_by_job.get(job["id"], {}),
        }

    # Knowledge Components are an optional downstream interpretation.  Merely
    # acquiring Markdown never creates or queues them; this read only reflects
    # work that another Concept Universe process may already have stamped.
    # Associate knowledge only with each Source's newest Markdown Artifact.
    # KCs from an older acquisition must not make a new Markdown look done.
    latest_artifacts = {
        value["markdown"]["artifact_id"]: source_id
        for source_id, value in states.items()
        if value.get("markdown")
    }
    if latest_artifacts:
        kc_rows = conn.execute(
            "WITH latest_run AS ("
            " SELECT DISTINCT ON (ri.artifact_id) ri.artifact_id,"
            " r.id AS run_id, r.status"
            " FROM run_item ri JOIN run r ON r.id = ri.run_id"
            " WHERE ri.artifact_id = ANY(%s) AND r.stage = 'kc-statement'"
            " ORDER BY ri.artifact_id, r.started_at DESC, r.id DESC"
            ")"
            " SELECT latest_run.artifact_id, latest_run.run_id, latest_run.status,"
            " ri.response, ri.error"
            " FROM latest_run JOIN run_item ri"
            " ON ri.artifact_id = latest_run.artifact_id"
            " AND ri.run_id = latest_run.run_id"
            " ORDER BY latest_run.artifact_id, ri.created_at, ri.id",
            (list(latest_artifacts),),
        ).fetchall()
        summaries: dict[str, dict] = {}
        for artifact_id, run_id, run_status, response, error in kc_rows:
            source_id = latest_artifacts[artifact_id]
            summary = summaries.setdefault(
                source_id,
                {
                    "run_id": run_id,
                    "run_status": run_status,
                    "count": 0,
                    "failed_count": 0,
                    "invalid_count": 0,
                },
            )
            if error:
                summary["failed_count"] += 1
                continue
            if not response:
                summary["invalid_count"] += 1
                continue
            try:
                parsed = json.loads(response)
            except (TypeError, json.JSONDecodeError):
                summary["invalid_count"] += 1
                continue
            if not isinstance(parsed, dict) or parsed.get("verdict") not in {
                "stated", "unsure"
            }:
                summary["invalid_count"] += 1
                continue
            if parsed.get("verdict") == "stated":
                statement = parsed.get("statement")
                if isinstance(statement, str) and statement.strip():
                    summary["count"] += 1
                else:
                    summary["invalid_count"] += 1
        for source_id, summary in summaries.items():
            states[source_id]["has_kcs"] = summary["count"] > 0
            states[source_id]["kc_count"] = summary["count"]
            states[source_id]["kc_run_id"] = summary["run_id"]
            states[source_id]["kc_failed_count"] = summary["failed_count"]
            states[source_id]["kc_invalid_count"] = summary["invalid_count"]
            if summary["run_status"] == "running":
                kc_state = "running"
            elif summary["run_status"] == "failed":
                kc_state = "failed"
            elif summary["failed_count"] or summary["invalid_count"]:
                kc_state = "partial"
            else:
                kc_state = "ready"
            states[source_id]["kc_state"] = kc_state

    for source_id in source_ids:
        states[source_id].setdefault("has_markdown", False)
        states[source_id].setdefault("has_kcs", False)
        states[source_id].setdefault("kc_count", 0)
        states[source_id].setdefault("kc_failed_count", 0)
        states[source_id].setdefault("kc_invalid_count", 0)
        states[source_id].setdefault("kc_state", "not_started")
        states[source_id].setdefault("image_branch", _empty_image_branch())
        states[source_id].setdefault(
            "pipeline",
            {"status": "ready" if states[source_id]["has_markdown"] else "idle"},
        )
    return states


def _syllabus_usage(conn: psycopg.Connection, source_ids: list[str]) -> dict:
    """Summarize paid calls recorded for the sources visible in one version."""
    if not source_ids:
        return {}

    usage_rows = conn.execute(
        "SELECT ri.usage FROM run_item ri"
        " JOIN artifact a ON a.id = ri.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = ANY(%s)"
        " UNION ALL"
        " SELECT c.usage FROM source_image_analysis_call c"
        " JOIN artifact a ON a.id = c.markdown_artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = ANY(%s) AND c.status = 'succeeded'"
        " UNION ALL"
        " SELECT c.usage FROM pdf_page_analysis_call c"
        " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
        " WHERE j.source_id = ANY(%s) AND c.status = 'succeeded'"
        " UNION ALL"
        " SELECT c.usage FROM pdf_figure_localization_call c"
        " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
        " WHERE j.source_id = ANY(%s) AND c.status = 'succeeded'",
        (source_ids, source_ids, source_ids, source_ids),
    ).fetchall()
    cost = 0.0
    total_tokens = 0
    calls = 0
    for (raw_usage,) in usage_rows:
        usage = raw_usage or {}
        calls += 1
        raw_cost = usage.get("cost", usage.get("total_cost", 0))
        raw_tokens = usage.get("total_tokens", 0)
        if isinstance(raw_cost, (int, float)) and not isinstance(raw_cost, bool):
            cost += float(raw_cost)
        if isinstance(raw_tokens, (int, float)) and not isinstance(raw_tokens, bool):
            total_tokens += int(raw_tokens)

    firecrawl = conn.execute(
        "SELECT count(*),"
        " COALESCE(sum(COALESCE((diagnostics->>'provider_attempts')::integer,"
        " attempt_count)), 0),"
        " count(*) FILTER (WHERE status = 'succeeded'),"
        " count(*) FILTER (WHERE status = 'failed')"
        " FROM acquisition_job"
        " WHERE source_id = ANY(%s) AND provider = 'firecrawl/v2'",
        (source_ids,),
    ).fetchone()
    pdf_firecrawl = conn.execute(
        "SELECT count(*), COALESCE(sum(provider_attempts), 0),"
        " count(*) FILTER (WHERE c.status = 'succeeded'),"
        " count(*) FILTER (WHERE c.status = 'failed'),"
        " COALESCE(sum(CASE WHEN c.diagnostics->>'estimated_credits' ~ '^[0-9]+$'"
        " THEN (c.diagnostics->>'estimated_credits')::integer ELSE 0 END), 0)"
        " FROM pdf_document_parse_call c"
        " JOIN acquisition_job j ON j.id = c.acquisition_job_id"
        " WHERE j.source_id = ANY(%s)",
        (source_ids,),
    ).fetchone()

    summary = {}
    if calls:
        summary["openrouter"] = {
            "cost_usd": round(cost, 10),
            "calls": calls,
            "total_tokens": total_tokens,
        }
    firecrawl_count = int((firecrawl or (0,))[0] or 0) + int(
        (pdf_firecrawl or (0,))[0] or 0
    )
    if firecrawl_count:
        summary["firecrawl"] = {
            "extractions": firecrawl_count,
            "attempts": int((firecrawl or (0, 0))[1] or 0)
            + int((pdf_firecrawl or (0, 0))[1] or 0),
            "succeeded": int((firecrawl or (0, 0, 0))[2] or 0)
            + int((pdf_firecrawl or (0, 0, 0))[2] or 0),
            "failed": int((firecrawl or (0, 0, 0, 0))[3] or 0)
            + int((pdf_firecrawl or (0, 0, 0, 0))[3] or 0),
        }
        estimated_credits = int((pdf_firecrawl or (0, 0, 0, 0, 0))[4] or 0)
        if estimated_credits:
            summary["firecrawl"]["estimated_credits"] = estimated_credits
    return summary


def _reusable_source_knowledge(
    conn: psycopg.Connection,
    source_ids: list[str],
) -> dict[str, dict]:
    """Project completed local KC work by current Source Publication.

    A Source Publication is immutable and may be referenced by more than one
    lesson.  Reusing its completed interpretation is a read-model concern: it
    must not create another lesson build or another unit of paid work.  The
    checks below deliberately use only batch reads and require both the target
    work and every sibling in its owning build to remain complete and pinned to
    the exact publications that are current now.
    """
    source_ids = list(dict.fromkeys(source_ids))
    publications = {
        source_id: publication
        for source_id, publication in current_source_publications(
            conn, source_ids
        ).items()
        if not publication.is_previous_attempt
    }
    if not publications:
        return {}

    candidate_rows = conn.execute(
        "SELECT build.id, build.request_seq, work.id, work.source_id,"
        " work.snapshot_id, work.artifact_id, work.content_hash,"
        " work.publication_is_previous_attempt, work.status, work.stage,"
        " work.diagnostics"
        " FROM lesson_knowledge_work work"
        " JOIN lesson_knowledge_build build ON build.id = work.build_id"
        " WHERE work.source_id = ANY(%s) AND work.status = 'succeeded'"
        " ORDER BY work.source_id, build.request_seq DESC, work.seq, work.id",
        (list(publications),),
    ).fetchall()
    if not candidate_rows:
        return {}

    candidate_build_ids = list(dict.fromkeys(row[0] for row in candidate_rows))
    build_rows: dict[str, list[tuple]] = {}
    build_source_ids: list[str] = []
    for row in conn.execute(
        "SELECT build_id, source_id, snapshot_id, artifact_id, content_hash,"
        " publication_is_previous_attempt, status, stage, diagnostics"
        " FROM lesson_knowledge_work WHERE build_id = ANY(%s)"
        " ORDER BY build_id, seq, id",
        (candidate_build_ids,),
    ).fetchall():
        build_rows.setdefault(row[0], []).append(row[1:])
        build_source_ids.append(row[1])
    build_publications = current_source_publications(
        conn, list(dict.fromkeys(build_source_ids))
    )

    def complete_current(row: tuple) -> bool:
        (
            source_id,
            snapshot_id,
            artifact_id,
            content_hash,
            was_previous_attempt,
            status,
            stage,
            diagnostics,
        ) = row
        publication = build_publications.get(source_id)
        diagnostics = dict(diagnostics or {})
        try:
            completed = int(diagnostics.get("completed_stage_count"))
            total = int(diagnostics.get("total_stage_count"))
            kc_count = int(diagnostics.get("kc_count"))
        except (TypeError, ValueError):
            return False
        return bool(
            publication is not None
            and not publication.is_previous_attempt
            and not was_previous_attempt
            and publication.snapshot_id == snapshot_id
            and publication.artifact_id == artifact_id
            and publication.content_hash == content_hash
            and status == "succeeded"
            and stage in (None, "local-complete")
            and completed == len(kc_pipeline.LOCAL_STAGES)
            and total == len(kc_pipeline.LOCAL_STAGES)
            and kc_count >= 0
        )

    current_builds = {
        build_id
        for build_id, rows in build_rows.items()
        if rows and all(complete_current(row) for row in rows)
    }
    projected: dict[str, dict] = {}
    for (
        build_id,
        _,
        work_id,
        source_id,
        snapshot_id,
        artifact_id,
        content_hash,
        was_previous_attempt,
        status,
        stage,
        diagnostics,
    ) in candidate_rows:
        if source_id in projected or build_id not in current_builds:
            continue
        publication = publications.get(source_id)
        if (
            publication is None
            or was_previous_attempt
            or publication.snapshot_id != snapshot_id
            or publication.artifact_id != artifact_id
            or publication.content_hash != content_hash
            or status != "succeeded"
            or stage not in (None, "local-complete")
        ):
            continue
        diagnostics = dict(diagnostics or {})
        projected[source_id] = {
            "build_id": build_id,
            "work_id": work_id,
            "status": "succeeded",
            "current": True,
            "kc_count": int(diagnostics["kc_count"]),
            "snapshot": None,
        }
    return projected


def _enrich_version(conn: psycopg.Connection, detail: dict) -> dict:
    source_ids = list(
        dict.fromkeys(
            source["source_id"]
            for lesson in detail.get("lessons", [])
            for source in lesson.get("sources", [])
            if source.get("source_id")
        )
    )
    operational = _latest_source_state(conn, source_ids)
    usage = _syllabus_usage(conn, source_ids)
    if usage:
        detail["usage"] = usage
    version_id = detail.get("version", {}).get("id")
    lesson_ids = [
        lesson["id"]
        for lesson in detail.get("lessons", [])
        if lesson.get("id")
    ]
    offers = (
        lesson_knowledge.offer_many(
            conn,
            detail["id"],
            version_id,
            lesson_ids,
        )
        if version_id and lesson_ids
        else {}
    )
    if version_id:
        syllabus_offer = syllabus_knowledge.offer_summary(
            conn, detail["id"], version_id
        )
        detail["knowledge"] = syllabus_offer
        published_corpus = syllabus_offer.get("published_build")
        if (
            published_corpus
            and published_corpus.get("current") is True
        ):
            detail["knowledge_manifest_id"] = published_corpus["manifest_id"]
    reusable_knowledge = _reusable_source_knowledge(conn, source_ids)
    for lesson in detail.get("lessons", []):
        offer = offers.get(lesson.get("id"))
        if offer is not None:
            lesson["knowledge"] = offer
        work_by_reference = {
            reference["reference_id"]: work_by_id.get(reference["work_id"])
            for build in [offer.get("latest_build") if offer else None]
            if build
            for work_by_id in [
                {work["id"]: work for work in build.get("work", [])}
            ]
            for reference in build.get("references", [])
        }
        for source in lesson.get("sources", []):
            source["acquisition_capability"] = _acquisition_capability(
                source.get("media_type")
            )
            source.update(operational.get(source.get("source_id"), {}))
            work = work_by_reference.get(source.get("reference_id"))
            if work is not None:
                source["knowledge"] = {
                    "build_id": offer["latest_build"]["id"],
                    "work_id": work["id"],
                    "status": work["status"],
                    "current": work["current"],
                    "kc_count": work.get("kc_count", 0),
                    "snapshot": work.get("snapshot"),
                }
            elif offer is None or offer.get("latest_build") is None:
                reusable = reusable_knowledge.get(source.get("source_id"))
                if reusable is not None:
                    source["knowledge"] = reusable
    return detail


def _enrich_reconciliation(conn: psycopg.Connection, reconciliation: dict) -> dict:
    """Attach current extraction facts without changing the comparison plan."""
    source_ids = list(
        dict.fromkeys(
            source_id
            for lesson in reconciliation.get("lessons", [])
            for item in lesson.get("sources", [])
            for source_id in [(item.get("current") or {}).get("source_id")]
            if source_id
        )
    )
    operational = _latest_source_state(conn, source_ids)
    for lesson in reconciliation.get("lessons", []):
        for item in lesson.get("sources", []):
            source_id = (item.get("current") or {}).get("source_id")
            item["extraction"] = operational.get(source_id, {})
    base = get_syllabus_version(
        conn,
        reconciliation["syllabus_id"],
        reconciliation["base_version_id"],
    )
    reconciliation["syllabus_title"] = base["title"]
    reconciliation["current_version"] = base["version"]
    reconciliation["next_version_seq"] = int(base["version"]["seq"]) + 1
    return reconciliation


def _legacy_latest_projection(conn: psycopg.Connection, version_id: str) -> dict:
    """Expose the former flat syllabus shape as a read-only compatibility key."""
    rows = conn.execute(
        "SELECT id, week, seq, kind, title, description, url, parent_title, source_id"
        " FROM syllabus_item WHERE version_id = %s"
        " ORDER BY week NULLS LAST, seq NULLS LAST, id",
        (version_id,),
    ).fetchall()
    by_week: dict[int | None, list[dict]] = {}
    for row in rows:
        item = dict(
            zip(
                "id week seq kind title description url parent_title source_id".split(),
                row,
            )
        )
        source_id = item.get("source_id")
        if source_id and curation.source_is_skipped(conn, source_id):
            item["source_status"] = "skipped by founder"
        elif source_id:
            has_artifact, has_failed = conn.execute(
                "SELECT EXISTS (SELECT 1 FROM source_snapshot sn"
                " JOIN artifact a ON a.snapshot_id = sn.id"
                " WHERE sn.source_id = %s AND sn.status = 'ok'),"
                " EXISTS (SELECT 1 FROM source_snapshot"
                " WHERE source_id = %s AND status = 'failed')",
                (source_id, source_id),
            ).fetchone()
            item["source_status"] = (
                "ingested" if has_artifact else "failed" if has_failed else "pending"
            )
        else:
            item["source_status"] = "unlinked"
        by_week.setdefault(item.pop("week"), []).append(item)
    return {
        "version_id": version_id,
        "weeks": [
            {"week": week, "items": items} for week, items in by_week.items()
        ],
    }


def _graph_id_conflict_detail(graph_id: str) -> dict:
    return {
        "code": "graph_id_conflict",
        "message": GRAPH_ID_CONFLICT_MESSAGE,
        "graph_id": graph_id,
    }


def _workbook_error(exc: Exception) -> HTTPException:
    if isinstance(exc, companion_seam.CompanionSeamError):
        return HTTPException(status_code=502, detail=str(exc))
    if isinstance(exc, GraphIdConflict):
        return HTTPException(
            status_code=409,
            detail=_graph_id_conflict_detail(exc.graph_id),
        )
    if isinstance(exc, SyllabusAlreadyExists):
        return HTTPException(
            status_code=409,
            detail={
                "code": "syllabus_already_exists",
                "message": str(exc),
                "syllabus_id": exc.syllabus_id,
                "graph_id": exc.graph_id,
            },
        )
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Não foi possível registrar o syllabus.")


def _knowledge_error(exc: Exception) -> HTTPException:
    if isinstance(
        exc,
        (
            lesson_knowledge.LessonKnowledgeNotReady,
            syllabus_knowledge.SyllabusKnowledgeNotReady,
        ),
    ):
        return HTTPException(
            status_code=409,
            detail={
                "code": exc.code,
                "message": str(exc),
                "reference_ids": list(exc.reference_ids),
                "source_ids": list(exc.source_ids),
            },
        )
    if isinstance(exc, LookupError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=422, detail=str(exc))
    return HTTPException(status_code=500, detail="Não foi possível acessar os KCs.")


def _manual_upload_mime(file: UploadFile) -> str:
    mime_type = str(file.content_type or "").split(";", 1)[0].strip().lower()
    if mime_type == "image/jpg":
        return "image/jpeg"
    if mime_type not in {"", "application/octet-stream"}:
        return mime_type
    suffix = Path(file.filename or "").suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, mime_type)


async def _manual_assets_from_uploads(
    kind: str, files: list[UploadFile]
) -> list[ManualAsset]:
    if kind not in {"pdf", "images"}:
        raise HTTPException(
            status_code=422, detail="Escolha um PDF ou um conjunto ordenado de imagens."
        )
    if kind == "pdf" and len(files) != 1:
        raise HTTPException(status_code=422, detail="Envie exatamente um arquivo PDF.")
    if kind == "images" and not 1 <= len(files) <= MAX_IMAGE_COUNT:
        raise HTTPException(
            status_code=422,
            detail=f"Envie de 1 a {MAX_IMAGE_COUNT} imagens na ordem correta.",
        )

    assets: list[ManualAsset] = []
    total_bytes = 0
    for index, file in enumerate(files, 1):
        mime_type = _manual_upload_mime(file)
        if kind == "pdf" and mime_type != "application/pdf":
            raise HTTPException(status_code=415, detail="O arquivo selecionado não é um PDF.")
        if kind == "images" and mime_type not in IMAGE_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail="Use somente imagens PNG, JPEG ou WebP; não misture PDF e imagens.",
            )
        remaining = MAX_TOTAL_BYTES - total_bytes
        body = await file.read(remaining + 1)
        total_bytes += len(body)
        if total_bytes > MAX_TOTAL_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Os arquivos excedem o limite total de 30 MB.",
            )
        if not body:
            raise HTTPException(
                status_code=422,
                detail=f"O arquivo {Path(file.filename or str(index)).name} está vazio.",
            )
        assets.append(
            ManualAsset(
                filename=Path(file.filename or f"arquivo-{index}").name,
                mime_type=mime_type,
                body=body,
                kind="pdf" if kind == "pdf" else "screenshot",
            )
        )
    return assets


def _work_one(
    connect_factory: Callable[[], psycopg.Connection],
    asset_store_factory: Callable[[], AssetStore],
    video_adapter_factory: Callable[[], VideoAdapter] = YtDlpYouTubeAdapter,
) -> bool:
    """Process the oldest ready parent or image job without queue starvation."""
    store = asset_store_factory()
    with connect_factory() as conn:
        return process_next_work_item(
            conn,
            asset_store=store,
            video_adapter=video_adapter_factory(),
            lease_connection_factory=connect_factory,
        ) is not None


async def _worker_loop(
    connect_factory: Callable[[], psycopg.Connection],
    asset_store_factory: Callable[[], AssetStore],
    stop: asyncio.Event,
    video_adapter_factory: Callable[[], VideoAdapter] | None = None,
) -> None:
    """Continuously consume durable jobs without blocking the ASGI loop."""
    while not stop.is_set():
        worked = False
        try:
            args = (connect_factory, asset_store_factory)
            if video_adapter_factory is not None:
                args = (*args, video_adapter_factory)
            worked = await asyncio.to_thread(_work_one, *args)
        except psycopg.Error:
            LOGGER.exception("acquisition worker could not reach PostgreSQL")
        except Exception:
            # Storage/HTTP/model failures are recorded per job by their
            # adapters where possible. A factory/configuration failure must
            # still not kill the long-lived worker task forever.
            LOGGER.exception("acquisition worker iteration failed")
        if worked:
            await asyncio.sleep(0)
            continue
        try:
            await asyncio.wait_for(stop.wait(), timeout=acquisition_poll_seconds())
        # Python 3.10 raises ``asyncio.TimeoutError`` here; using only the
        # built-in name makes a normal empty-queue poll kill the worker.
        except asyncio.TimeoutError:
            pass


def create_app(
    connect_factory: Callable[[], psycopg.Connection] = connect,
    *,
    start_worker: bool = False,
    asset_store_factory: Callable[[], AssetStore] = asset_store_from_env,
    video_adapter_factory: Callable[[], VideoAdapter] = YtDlpYouTubeAdapter,
    companion_namespace_provider: Callable[[], dict] | None = None,
) -> FastAPI:
    namespace_provider = companion_namespace_provider or companion_seam.graph_namespace
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        stop = asyncio.Event()
        task = (
            asyncio.create_task(
                _worker_loop(
                    connect_factory,
                    asset_store_factory,
                    stop,
                    video_adapter_factory,
                )
            )
            if start_worker
            else None
        )
        try:
            yield
        finally:
            stop.set()
            if task is not None:
                await task

    app = FastAPI(title="Concept Universe Syllabi", lifespan=lifespan)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse("/syllabi", status_code=307)

    @app.get("/syllabi", include_in_schema=False)
    def syllabi_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "syllabi.html")

    @app.get("/graph", include_in_schema=False)
    def graph_page() -> FileResponse:
        return FileResponse(STATIC_DIR / "universe.html")

    @app.get("/api/syllabi")
    def syllabi_index() -> dict:
        with connect_factory() as conn:
            return {"syllabi": list_syllabi(conn)}

    @app.get("/api/companion/graph-namespace")
    def companion_graph_namespace() -> dict:
        try:
            return namespace_provider()
        except companion_seam.CompanionSeamError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    @app.get("/api/syllabi/graph-id-proposal")
    def syllabus_graph_id_proposal(
        institution_id: str = Query(...),
        name: str = Query(...),
    ) -> dict:
        clean_name = name.strip()
        if not clean_name:
            raise HTTPException(status_code=422, detail="Dê um nome ao syllabus.")
        try:
            graph_id = graph_id_for(institution_id, clean_name)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        try:
            syllabus_id = validate_syllabus_id(slugify(clean_name))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        with connect_factory() as conn:
            existing = conn.execute(
                "SELECT id, title, graph_id FROM syllabus WHERE id = %s",
                (syllabus_id,),
            ).fetchone()
            graph_owner = conn.execute(
                "SELECT id, title, graph_id FROM syllabus WHERE graph_id = %s",
                (graph_id,),
            ).fetchone()
        def serialize(row) -> dict | None:
            if row is None:
                return None
            return {"id": row[0], "title": row[1], "graph_id": row[2]}

        return {
            "display_name": clean_name,
            "graph_id": graph_id,
            "existing_syllabus": serialize(
                existing if existing is not None and existing[1] == clean_name else None
            ),
            "graph_owner": serialize(graph_owner),
        }

    @app.post("/api/syllabi/upload", status_code=201)
    async def upload_syllabus(
        name: str = Form(...),
        file: UploadFile = File(...),
        syllabus_id: str | None = Form(default=None),
        institution_id: str | None = Form(default=None),
    ) -> dict:
        clean_name = name.strip()
        if not clean_name:
            raise HTTPException(status_code=422, detail="Dê um nome ao syllabus.")
        filename = Path(file.filename or "syllabus.xlsx").name
        if Path(filename).suffix.lower() != ".xlsx":
            raise HTTPException(status_code=415, detail="Envie uma planilha .xlsx.")
        body = await file.read(MAX_WORKBOOK_BYTES + 1)
        if len(body) > MAX_WORKBOOK_BYTES:
            raise HTTPException(status_code=413, detail="A planilha excede o limite de 30 MB.")
        if not body:
            raise HTTPException(status_code=422, detail="A planilha enviada está vazia.")

        try:
            # Keep the sanitized original filename: it is part of the immutable
            # syllabus-version evidence stored by ``import_workbook``.
            with tempfile.TemporaryDirectory(prefix="universe-syllabus-") as directory:
                temporary_path = Path(directory) / filename
                temporary_path.write_bytes(body)
                with connect_factory() as conn:
                    namespace = None
                    if syllabus_id:
                        history = get_syllabus_history(conn, syllabus_id)
                        if history["title"] != clean_name:
                            raise ValueError("o nome de uma nova versão deve ser igual ao syllabus existente")
                    else:
                        namespace = namespace_provider()
                        companion_seam.remember_institution(
                            conn,
                            namespace,
                            str(institution_id or "").strip(),
                        )
                    return import_workbook(
                        conn,
                        temporary_path,
                        clean_name,
                        syllabus_id=syllabus_id,
                        institution_id=institution_id,
                        occupied_graph_ids=(namespace or {}).get("graph_ids", []),
                        require_syllabus_metadata=True,
                    )
        except HTTPException:
            raise
        except Exception as exc:
            raise _workbook_error(exc) from exc

    @app.post("/api/syllabi/{syllabus_id}/reconciliations", status_code=201)
    async def preview_syllabus_reconciliation(
        syllabus_id: str,
        file: UploadFile = File(...),
    ) -> dict:
        """Store an incoming workbook without publishing a Syllabus Version."""
        filename = Path(file.filename or "syllabus.xlsx").name
        if Path(filename).suffix.lower() != ".xlsx":
            raise HTTPException(status_code=415, detail="Envie uma planilha .xlsx.")
        body = await file.read(MAX_WORKBOOK_BYTES + 1)
        if len(body) > MAX_WORKBOOK_BYTES:
            raise HTTPException(status_code=413, detail="A planilha excede o limite de 30 MB.")
        if not body:
            raise HTTPException(status_code=422, detail="A planilha enviada está vazia.")
        try:
            with tempfile.TemporaryDirectory(prefix="universe-reconciliation-") as directory:
                temporary_path = Path(directory) / filename
                temporary_path.write_bytes(body)
                with connect_factory() as conn:
                    reconciliation = create_reconciliation(
                        conn, syllabus_id, temporary_path
                    )
                    return _enrich_reconciliation(conn, reconciliation)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except HTTPException:
            raise
        except Exception as exc:
            raise _workbook_error(exc) from exc

    @app.get("/api/syllabi/{syllabus_id}/reconciliations/{reconciliation_id}")
    def syllabus_reconciliation_detail(
        syllabus_id: str,
        reconciliation_id: str,
    ) -> dict:
        try:
            with connect_factory() as conn:
                reconciliation = get_reconciliation(
                    conn, syllabus_id, reconciliation_id
                )
                return _enrich_reconciliation(conn, reconciliation)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.post(
        "/api/syllabi/{syllabus_id}/reconciliations/{reconciliation_id}/apply",
        status_code=201,
    )
    def apply_syllabus_reconciliation(
        syllabus_id: str,
        reconciliation_id: str,
        payload: dict = Body(...),
    ) -> dict:
        try:
            with connect_factory() as conn:
                return apply_reconciliation(
                    conn,
                    syllabus_id,
                    reconciliation_id,
                    payload.get("decisions"),
                    payload.get("drafts"),
                )
        except SyllabusVersionConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/syllabi/{syllabus_id}")
    def syllabus_detail(
        syllabus_id: str,
        version_id: str | None = Query(default=None),
    ) -> dict:
        try:
            with connect_factory() as conn:
                history = get_syllabus_history(conn, syllabus_id)
                detail = get_syllabus_version(conn, syllabus_id, version_id)
                detail["versions"] = history["versions"]
                enriched = _enrich_version(conn, detail)
                enriched["latest"] = _legacy_latest_projection(
                    conn, detail["version"]["id"]
                )
                return enriched
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.get(
        "/api/syllabi/{syllabus_id}/versions/{version_id}/knowledge"
    )
    def syllabus_knowledge_offer(
        syllabus_id: str,
        version_id: str,
    ) -> dict:
        try:
            with connect_factory() as conn:
                return syllabus_knowledge.offer(conn, syllabus_id, version_id)
        except (LookupError, ValueError) as exc:
            raise _knowledge_error(exc) from exc

    @app.post(
        "/api/syllabi/{syllabus_id}/versions/{version_id}/knowledge-builds",
        status_code=202,
    )
    def request_syllabus_knowledge_build(
        syllabus_id: str,
        version_id: str,
        payload: dict = Body(...),
    ) -> dict:
        try:
            with connect_factory() as conn:
                return syllabus_knowledge.request(
                    conn,
                    syllabus_id,
                    version_id,
                    payload.get("request_key"),
                    actor="founder",
                )
        except (LookupError, ValueError) as exc:
            raise _knowledge_error(exc) from exc

    @app.get(
        "/api/syllabi/{syllabus_id}/versions/{version_id}"
        "/knowledge-builds/{build_id}"
    )
    def read_syllabus_knowledge_build(
        syllabus_id: str,
        version_id: str,
        build_id: str,
    ) -> dict:
        try:
            with connect_factory() as conn:
                build = syllabus_knowledge.read(
                    conn, syllabus_id, version_id, build_id
                )
        except (LookupError, ValueError) as exc:
            raise _knowledge_error(exc) from exc
        if build is None:
            raise HTTPException(
                status_code=404, detail="Syllabus Knowledge Build not found"
            )
        return build

    @app.get(
        "/api/syllabi/{syllabus_id}/versions/{version_id}"
        "/lessons/{lesson_id}/knowledge"
    )
    def lesson_knowledge_offer(
        syllabus_id: str,
        version_id: str,
        lesson_id: str,
    ) -> dict:
        try:
            with connect_factory() as conn:
                return lesson_knowledge.offer(
                    conn,
                    syllabus_id,
                    version_id,
                    lesson_id,
                )
        except (LookupError, ValueError) as exc:
            raise _knowledge_error(exc) from exc

    @app.post(
        "/api/syllabi/{syllabus_id}/versions/{version_id}"
        "/lessons/{lesson_id}/knowledge-builds",
        status_code=202,
    )
    def request_lesson_knowledge_build(
        syllabus_id: str,
        version_id: str,
        lesson_id: str,
        payload: dict = Body(...),
    ) -> dict:
        try:
            with connect_factory() as conn:
                return lesson_knowledge.request(
                    conn,
                    syllabus_id,
                    version_id,
                    lesson_id,
                    payload.get("request_key"),
                    actor="founder",
                )
        except (LookupError, ValueError) as exc:
            raise _knowledge_error(exc) from exc

    @app.get("/api/knowledge-builds/{build_id}")
    def read_lesson_knowledge_build(build_id: str) -> dict:
        try:
            with connect_factory() as conn:
                build = lesson_knowledge.read_by_id(conn, build_id)
        except (LookupError, ValueError) as exc:
            raise _knowledge_error(exc) from exc
        if build is None:
            raise HTTPException(status_code=404, detail="Knowledge Build not found")
        return build

    @app.patch("/api/syllabi/{syllabus_id}/sources/{reference_id}/review")
    def patch_source_review(
        syllabus_id: str,
        reference_id: str,
        payload: dict = Body(...),
    ) -> dict:
        try:
            with connect_factory() as conn:
                review = update_source_review(
                    conn, syllabus_id, reference_id, payload
                )
                return {"review": review}
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.post("/api/syllabi/{syllabus_id}/curate", status_code=201)
    def curate_syllabus_version(
        syllabus_id: str,
        payload: dict = Body(...),
    ) -> dict:
        """Save the editor's full projection as one new immutable version."""
        base_version_id = str(payload.get("base_version_id") or "").strip()
        if not base_version_id:
            raise HTTPException(status_code=422, detail="A versão de origem é obrigatória.")
        try:
            with connect_factory() as conn:
                return curate_syllabus(
                    conn,
                    syllabus_id,
                    base_version_id,
                    payload.get("lessons"),
                    note=payload.get("note"),
                )
        except SyllabusVersionConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @app.get("/api/syllabi/{syllabus_id}/versions/{version_id}/workbook")
    def download_syllabus_workbook(syllabus_id: str, version_id: str) -> Response:
        try:
            with connect_factory() as conn:
                # This also verifies that the requested Version belongs to the
                # Syllabus in the route rather than merely existing globally.
                get_syllabus_version(conn, syllabus_id, version_id)
                workbook = get_syllabus_workbook(conn, version_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        filename = Path(workbook["file_name"]).name
        return Response(
            content=workbook["body"],
            media_type=workbook["mime_type"],
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                "ETag": f'"{workbook["sha256"]}"',
            },
        )

    @app.post("/api/sources/{source_id}/queue", status_code=202)
    def queue_source(source_id: str) -> dict:
        try:
            with connect_factory() as conn:
                row = conn.execute(
                    "SELECT media_type FROM source WHERE id = %s", (source_id,)
                ).fetchone()
                if row is None:
                    raise ValueError(f"unknown source: {source_id}")
                capability = _acquisition_capability(row[0])
                if not capability["supported"]:
                    raise HTTPException(status_code=409, detail=capability["reason"])
                if row[0] == "video" and latest_preflight(conn, source_id) is not None:
                    refresh_preflight(
                        conn,
                        source_id,
                        adapter=video_adapter_factory(),
                    )
                job = enqueue_source(conn, source_id)
                return {"job": job}
        except HTTPException:
            raise
        except PermissionError as exc:
            raise HTTPException(
                status_code=409,
                detail="Autorize explicitamente a transcrição deste vídeo antes de enfileirar.",
            ) from exc
        except ValueError as exc:
            status = 404 if "unknown source" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    @app.post("/api/sources/{source_id}/video-preflight")
    def preflight_video_source(
        source_id: str,
        refresh: bool = Query(default=False),
    ) -> dict:
        """Run or reuse metadata-only YouTube readiness before any paid call."""
        try:
            with connect_factory() as conn:
                result = refresh_preflight(
                    conn,
                    source_id,
                    adapter=video_adapter_factory(),
                    force=refresh,
                )
        except ValueError as exc:
            status = 404 if "unknown source" in str(exc) else 422
            raise HTTPException(status_code=status, detail=str(exc)) from exc
        public_keys = (
            "id", "status", "title", "channel", "duration_seconds",
            "uploaded_caption_languages", "selected_caption_language", "route",
            "failure_code", "diagnostics", "deduplicated",
        )
        return {"video_preflight": {key: result.get(key) for key in public_keys}}

    @app.post(
        "/api/sources/{source_id}/authorize-transcription", status_code=202
    )
    def authorize_video_transcription(source_id: str) -> dict:
        """Persist explicit paid-STT authorization as the queued job input."""
        try:
            with connect_factory() as conn:
                if latest_preflight(conn, source_id) is not None:
                    refresh_preflight(
                        conn,
                        source_id,
                        adapter=video_adapter_factory(),
                    )
                job = enqueue_source(
                    conn,
                    source_id,
                    authorize_paid_transcription=True,
                )
                return {"job": job}
        except PermissionError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            status = 404 if "unknown source" in str(exc) else 409
            raise HTTPException(status_code=status, detail=str(exc)) from exc

    @app.post("/api/sources/{source_id}/manual-upload", status_code=202)
    async def manual_upload_source(
        source_id: str,
        kind: str = Form(...),
        files: list[UploadFile] = File(...),
    ) -> dict:
        """Queue one explicit PDF or ordered-image replacement for a Source."""
        with connect_factory() as conn:
            if conn.execute(
                "SELECT 1 FROM source WHERE id = %s", (source_id,)
            ).fetchone() is None:
                raise HTTPException(status_code=404, detail="Esta fonte não existe.")
            active = conn.execute(
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
            if active is not None:
                raise HTTPException(
                    status_code=409,
                    detail="Esta fonte já possui uma extração na fila ou em andamento.",
                )

        assets = await _manual_assets_from_uploads(kind, files)
        try:
            store = asset_store_factory()
            with connect_factory() as conn:
                job = create_manual_upload_job(
                    conn,
                    source_id,
                    assets,
                    input_kind=kind,
                    asset_store=store,
                )
            return {"job": job}
        except ValueError as exc:
            message = str(exc)
            if "active acquisition job" in message or "already has" in message:
                raise HTTPException(
                    status_code=409,
                    detail="Esta fonte já possui uma extração na fila ou em andamento.",
                ) from exc
            if "unknown source" in message:
                raise HTTPException(status_code=404, detail="Esta fonte não existe.") from exc
            raise HTTPException(
                status_code=422,
                detail=f"Os arquivos enviados não são válidos: {message}",
            ) from exc
        except Exception as exc:
            LOGGER.exception("manual source assets could not be persisted")
            raise HTTPException(
                status_code=503,
                detail="Não foi possível preservar os arquivos agora. Tente novamente.",
            ) from exc

    @app.get("/api/source-assets/{asset_id}")
    def source_asset(asset_id: str) -> Response:
        """Serve one immutable ledger asset without exposing storage internals."""
        with connect_factory() as conn:
            asset = get_manual_asset(conn, asset_id)
        if asset is None:
            raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
        try:
            body = asset_store_factory().get(asset["storage_key"])
        except Exception as exc:
            LOGGER.exception("source asset is unavailable: %s", asset_id)
            raise HTTPException(
                status_code=503,
                detail="O arquivo está temporariamente indisponível.",
            ) from exc
        filename = Path(asset["filename"]).name
        return Response(
            content=body,
            media_type=asset["mime_type"],
            headers={
                "Content-Disposition": f"inline; filename*=UTF-8''{quote(filename)}",
                "ETag": f'"{asset["sha256"]}"',
                "Cache-Control": "private, max-age=31536000, immutable",
                "Content-Security-Policy": "default-src 'none'; sandbox",
                "Cross-Origin-Resource-Policy": "same-origin",
                "X-Content-Type-Options": "nosniff",
            },
        )

    @app.get("/api/sources/{source_id}/markdown")
    def source_markdown(source_id: str) -> dict:
        with connect_factory() as conn:
            publication = current_source_publication(conn, source_id)
            latest_job = None
            cleanup = None
            if publication is None:
                latest_job = conn.execute(
                    "SELECT id, diagnostics FROM acquisition_job"
                    " WHERE source_id = %s"
                    " ORDER BY created_at DESC, id DESC LIMIT 1",
                    (source_id,),
                ).fetchone()
                if latest_job and (latest_job[1] or {}).get(
                    "pipeline_requires_cleanup"
                ):
                    cleanup = conn.execute(
                        "SELECT status FROM source_cleanup_job"
                        " WHERE acquisition_job_id = %s",
                        (latest_job[0],),
                    ).fetchone()
            images = (
                list_article_images_for_artifact(conn, publication.artifact_id)
                if publication
                else []
            )
        if publication is None:
            diagnostics = (latest_job[1] or {}) if latest_job else {}
            if diagnostics.get("visual_incomplete"):
                raise HTTPException(
                    status_code=409,
                    detail="Uma ou mais figuras da fonte precisam de atenção antes da publicação.",
                )
            if cleanup is not None and cleanup[0] in {"queued", "running"}:
                raise HTTPException(
                    status_code=409,
                    detail="O Markdown estruturado ainda está passando pela limpeza.",
                )
            if cleanup is not None:
                raise HTTPException(
                    status_code=409,
                    detail="A limpeza do Markdown precisa de atenção antes da publicação.",
                )
            raise HTTPException(status_code=404, detail="Esta fonte ainda não tem Markdown extraído.")
        artifact_id = publication.artifact_id
        body = publication.body
        tool = publication.tool
        tool_version = publication.tool_version
        created_at = publication.created_at
        for image in images:
            image["asset_url"] = (
                f"/api/source-assets/{image['asset_id']}"
                if image.get("asset_id")
                else None
            )
            image["error"] = (
                _image_failure_message(
                    image.get("diagnostics") or {}, image.get("failure_code")
                )
                if image.get("status") == "failed"
                else None
            )
        counts: dict[str, int] = {}
        for image in images:
            status = image.get("status")
            if isinstance(status, str):
                counts[status] = counts.get(status, 0) + 1
        return {
            "artifact_id": artifact_id,
            "tool": tool,
            "tool_version": tool_version,
            "created_at": created_at,
            "is_previous_version": publication.is_previous_attempt,
            "markdown": body,
            "html": MARKDOWN.render(body),
            "images": images,
            "image_branch": _summarize_image_counts(counts),
        }

    @app.exception_handler(psycopg.Error)
    async def database_error(_request, _exc: psycopg.Error) -> JSONResponse:
        return JSONResponse(
            {"detail": "Não foi possível acessar o banco de dados."},
            status_code=503,
        )

    return app


app = create_app(
    start_worker=os.environ.get("ACQUISITION_WORKER_IN_WEB", "0") == "1"
)
