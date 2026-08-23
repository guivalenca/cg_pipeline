"""Versioned syllabus intake and its small domain-facing read interface.

A syllabus is named by a person.  An XLSX file is only one input adapter that
authors a complete immutable version of it.  The adapters in this module
translate both institution workbook formats into the same shape::

    syllabus -> version -> lesson -> source reference -> source

Import never queues acquisition.  A removed reference simply disappears from
the next version; the older version and every Source/Snapshot/Artifact fact
remain in their append-only ledgers (ADRs 0001 and 0006).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from urllib.parse import parse_qsl, unquote_plus, urlencode, urlparse, urlunparse

import psycopg
from openpyxl import Workbook, load_workbook
from psycopg.types.json import Jsonb

from universe.db import connect

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HIDDEN_COLUMN = "Hidden"

PROJECT_COLUMNS = (
    "Projeto",
    "Semana",
    "Ordem",
    "Atividade",
    "Tipo da atividade",
    "Descrição da atividade",
    "Questão do autoestudo",
    "Barema do autoestudo",
    "Atividade obrigatória",
    "Peso da atividade",
    "Eixo",
    "Assuntos",
    "URL",
    "Ponderada aplicada em sala",
    "Encontro pai",
    "Prova",
    "Prova substitutiva",
    "Material de estudo",
    "Material em vídeo",
    "Duração em minutos",
    "Atividade verificada",
)

LEGACY_COLUMNS = (
    "Week",
    "Sort",
    "Type",
    "Title",
    "Date",
    "Date source",
    "Parent class",
    "Class date",
    "Professor",
    "Axis",
    "Related subjects",
    "Description",
    "URL",
    "Resource code",
    "Required",
    "Grade weight",
)

# Compatibility for callers that imported the old constant.
COLUMNS = PROJECT_COLUMNS
WEEK = re.compile(r"^Semana\s+(\d+)$", re.IGNORECASE)
PROJECT_SUBJECT_CODES = {
    "com": "COM",
    "computacao": "COM",
    "lid": "LID",
    "lideranca": "LID",
    "neg": "NEG",
    "negocios": "NEG",
    "uex": "UEX",
    "user experience": "UEX",
}
PROJECT_LESSON_KINDS = {
    "class": "Class",
    "avaliacao / pesquisa": "Evaluation",
    "deliverable": "Deliverable",
    "desenvolvimento projeto": "Deliverable",
    "encontro": "Class",
    "encontro de instrucao": "Class",
    "encontro de orientacao": "Orientation",
    "evaluation": "Evaluation",
    "orientation": "Orientation",
}
BOOK_SCOPE = re.compile(
    r"(?P<label>cap[ií]tulos?|cap\.?|chapters?|p[aá]ginas?|p[aá]gs?\.?|pag(?:es?)?\.?|"
    r"p\.|pages?|unidades?|units?|exerc[ií]cios?|exercises?)"
    r"\s*(?:n(?:[º°o]|ro)?\.?\s*)?"
    r"(?P<value>\d+(?:\s*(?:[-–—]|a|à|at[eé]|to)\s*\d+)?"
    r"(?:\s*[,;]\s*\d+(?:\s*(?:[-–—]|a|à|at[eé]|to)\s*\d+)?)*)",
    re.IGNORECASE,
)
RESOURCE_CODE = re.compile(
    r"(?:reader/)?books?/([0-9Xx-]{8,})|(?:^|/)books?/([0-9Xx-]{8,})",
    re.IGNORECASE,
)
ISBN = re.compile(r"\bISBN\s*[:#]?\s*([0-9Xx\-\s]{10,22})", re.IGNORECASE)
PAGE_ID = re.compile(r"/pageid/(\d+)", re.IGNORECASE)
YOUTUBE_VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_TEXTUAL_QUERY = re.compile(
    r"^(?P<video_id>[A-Za-z0-9_-]{11})"
    r"(?:\s+e\s+(?:list|index|t)=[^\s]+)+$",
    re.IGNORECASE,
)
SYLLABUS_ID = re.compile(r"^[a-z][a-z0-9_.-]{1,127}$")


def _display_name(value: str | None, *, what: str) -> str:
    display_name = str(value or "").strip()
    if not display_name:
        raise ValueError(f"Informe {what}.")
    if len(display_name) > 255 or any(
        unicodedata.category(character) == "Cc" for character in display_name
    ):
        raise ValueError(f"{what.capitalize()} deve ter no máximo 255 caracteres.")
    return display_name


def _syllabus_metadata(
    conn: psycopg.Connection,
    institution_id: str | None,
    display_name: str | None,
    lesson_subject_ids: list[str] | tuple[str, ...] | None,
    *,
    required: bool,
) -> dict | None:
    clean_institution_id = str(institution_id or "").strip()
    clean_display_name = str(display_name or "").strip()
    if lesson_subject_ids is None:
        clean_subject_ids: list[str] = []
    elif isinstance(lesson_subject_ids, (list, tuple)):
        clean_subject_ids = [str(value or "").strip() for value in lesson_subject_ids]
    else:
        raise ValueError("A seleção de matérias deve ser uma lista.")
    if any(not value for value in clean_subject_ids):
        raise ValueError("A seleção de matérias contém um valor vazio.")
    if len(set(clean_subject_ids)) != len(clean_subject_ids):
        raise ValueError("Cada matéria deve ser selecionada uma única vez.")

    if not clean_institution_id and not clean_display_name and not clean_subject_ids:
        if required:
            raise ValueError(
                "Selecione a instituição, informe o nome da unidade curricular e "
                "escolha ao menos uma matéria."
            )
        return None
    if not clean_institution_id:
        raise ValueError("Selecione uma instituição.")
    if not clean_subject_ids:
        raise ValueError("Selecione ao menos uma matéria da instituição.")
    clean_display_name = _display_name(
        clean_display_name,
        what="o nome da unidade curricular",
    )

    institution = conn.execute(
        "SELECT id, name FROM institution WHERE id = %s",
        (clean_institution_id,),
    ).fetchone()
    if institution is None:
        raise ValueError("Selecione uma instituição existente.")
    rows = conn.execute(
        "SELECT id, institution_id, code, display_name FROM lesson_subject"
        " WHERE id = ANY(%s)",
        (clean_subject_ids,),
    ).fetchall()
    by_id = {row[0]: row for row in rows}
    if any(
        subject_id not in by_id or by_id[subject_id][1] != clean_institution_id
        for subject_id in clean_subject_ids
    ):
        raise ValueError("Selecione apenas matérias da instituição escolhida.")
    subjects = [
        {
            "id": by_id[subject_id][0],
            "code": by_id[subject_id][2],
            "display_name": by_id[subject_id][3],
        }
        for subject_id in clean_subject_ids
    ]
    subjects.sort(key=lambda subject: (subject["code"], subject["id"]))
    return {
        "institution": {"id": institution[0], "name": institution[1]},
        "display_name": clean_display_name,
        "lesson_subjects": subjects,
    }


def slugify(text: str) -> str:
    """Return a lowercase ASCII slug suitable for a stable syllabus id."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_text.lower())).strip("-")


def canonical_url(url: str) -> str:
    """Canonicalize an article URL without retaining tracking or fragments."""
    raw = (url or "").strip()
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return ""
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not unquote_plus(key).lower().startswith("utm_")
    ]
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            urlencode(query, doseq=True),
            "",
        )
    )


def media_type(url: str, resource_code: str | None = None) -> str:
    """Classify an assigned material without trusting its gateway URL alone."""
    if _clean_code(resource_code):
        return "book"
    raw = (url or "").strip()
    host = (urlparse(raw).hostname or "").lower()
    if any(
        host == candidate or host.endswith(f".{candidate}")
        for candidate in ("youtube.com", "youtu.be", "vimeo.com", "ted.com")
    ):
        return "video"
    if (
        host == "integrada.minhabiblioteca.com.br"
        or host.endswith(".integrada.minhabiblioteca.com.br")
        or "sophia" in raw.lower()
    ):
        return "book"
    return "article"


def extract_book_scope(text: str, url: str = "") -> tuple[str, str] | None:
    """Extract one explicit book scope into a stable ``(kind, value)`` pair."""
    match = BOOK_SCOPE.search(text or "")
    if match:
        label = _ascii(match.group("label")).lower().rstrip(".")
        if label.startswith(("cap", "chapter")):
            kind = "chapters"
        elif label.startswith(("unidade", "unit")):
            kind = "units"
        elif label.startswith(("exercicio", "exercise")):
            kind = "exercises"
        else:
            kind = "pages"
        return kind, _normalize_scope_value(match.group("value"))
    page = PAGE_ID.search(url or "")
    if page:
        return "pages", page.group(1)
    return None


def book_scope_missing(item: dict) -> bool:
    """Say whether a linked book lacks an explicit page/chapter/unit scope."""
    resource_code = item.get("resource_code")
    if media_type(item.get("url") or "", resource_code) != "book":
        return False
    if item.get("scope_kind") and item.get("scope_value"):
        return False
    text = f"{item.get('title') or ''}\n{item.get('description') or ''}"
    return extract_book_scope(text, item.get("url") or "") is None


def source_identity(
    url: str,
    *,
    media_kind: str | None = None,
    resource_code: str | None = None,
    scope_kind: str | None = None,
    scope_value: str | None = None,
) -> dict | None:
    """Return the stable identity of a logical assigned source.

    Articles use canonical URL, videos use provider + provider id, and books
    use resource code + normalized assigned scope.  An incomplete book has no
    logical Source yet: its syllabus reference remains visible and actionable.
    """
    kind = media_kind or media_type(url, resource_code)
    if kind == "book":
        code = _clean_code(resource_code) or _resource_code_from_url(url)
        if not code or not scope_kind or not scope_value:
            return None
        return {
            "kind": "book",
            "resource_code": code,
            "scope": {"kind": scope_kind, "value": _normalize_scope_value(scope_value)},
        }
    if kind == "video":
        provider, video_id = _video_identity(url)
        if not video_id:
            return None
        return {"kind": "video", "provider": provider, "video_id": video_id}
    canonical = canonical_url(url)
    return {"kind": "article", "canonical_url": canonical} if canonical else None


def youtube_video_id(value: object) -> str | None:
    """Return one real YouTube id, repairing the XLSX textual-query form."""
    candidate = unquote_plus(str(value or "")).strip()
    if YOUTUBE_VIDEO_ID.fullmatch(candidate):
        return candidate
    textual_query = YOUTUBE_TEXTUAL_QUERY.fullmatch(candidate)
    return textual_query.group("video_id") if textual_query else None


def _video_identity(url: str) -> tuple[str, str | None]:
    parsed = urlparse((url or "").strip())
    host = (parsed.hostname or "").lower().removeprefix("www.")
    parts = [part for part in parsed.path.split("/") if part]
    if host == "youtu.be":
        return "youtube", youtube_video_id(parts[0]) if parts else None
    if host.endswith("youtube.com"):
        query = dict(parse_qsl(parsed.query))
        if query.get("v"):
            return "youtube", youtube_video_id(query["v"])
        if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live"}:
            return "youtube", youtube_video_id(parts[1])
        return "youtube", None
    if host.endswith("vimeo.com"):
        video_id = next((part for part in reversed(parts) if part.isdigit()), None)
        return "vimeo", video_id
    if host.endswith("ted.com"):
        return "ted", "/".join(parts) or None
    return host or "video", canonical_url(url) or None


def _resource_code_from_url(url: str) -> str | None:
    parsed = urlparse((url or "").strip())
    searchable = f"{parsed.path}/{parsed.fragment}"
    match = RESOURCE_CODE.search(searchable)
    if not match:
        return None
    return _clean_code(next(group for group in match.groups() if group))


def _resource_code(url: str, explicit: str | None, text: str) -> str | None:
    code = _clean_code(explicit) or _resource_code_from_url(url)
    if code:
        return code
    match = ISBN.search(text or "")
    return _clean_code(match.group(1)) if match else None


def _clean_code(value: str | None) -> str | None:
    cleaned = re.sub(r"[^0-9Xx]", "", str(value or ""))
    return cleaned.upper() or None


def _normalize_scope_value(value: str) -> str:
    normalized = re.sub(r"\s*(?:[-–—]|\ba\b|\bà\b|\bat[eé]\b|\bto\b)\s*", "-", value, flags=re.I)
    normalized = re.sub(r"\s*([,;])\s*", r"\1", normalized)
    return normalized.strip()


def _ascii(value: str) -> str:
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()


def _text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    result = str(value).strip()
    return result or None


def _project_subject(value: object, *, row_number: int) -> str | None:
    """Translate an institutional Eixo label to the shared subject code."""
    subject = _text(value)
    if not subject:
        return None
    code = PROJECT_SUBJECT_CODES.get(_ascii(subject).casefold())
    if code is None:
        raise ValueError(f"row {row_number}: unsupported Eixo value {subject!r}")
    return code


def _project_lesson_kind(value: object, *, row_number: int) -> str:
    """Translate a Projetos activity label to the shared lesson taxonomy."""
    kind = _text(value)
    canonical = PROJECT_LESSON_KINDS.get(_ascii(kind or "").casefold())
    if canonical is None:
        raise ValueError(
            f"row {row_number}: unsupported Tipo da atividade value {kind!r}"
        )
    return canonical


def parse_subjects(value: object) -> list[str]:
    """Turn one workbook subjects cell into an ordered list.

    The Projetos workbook separates topics with newlines and prefixes every
    line after the first with a comma. Commas inside a topic remain content.
    """
    values = value if isinstance(value, (list, tuple)) else [value]
    subjects: list[str] = []
    for raw in values:
        for line in re.split(r"[\r\n]+", str(raw or "")):
            subject = re.sub(r"^\s*,\s*", "", line).strip()
            if subject and subject not in subjects:
                subjects.append(subject)
    return subjects


def _as_int(value, *, row_number: int, column: str) -> int:
    text = _text(value)
    try:
        return int(float(text or ""))
    except ValueError as exc:
        raise ValueError(f"row {row_number}: invalid {column} value {text!r}") from exc


def _as_date(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = _text(value)
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _as_bool(value) -> bool:
    """Parse the optional XLSX/UI visibility marker conservatively."""
    text = (_text(value) or "").casefold()
    return text in {"1", "true", "yes", "sim", "hidden", "oculta", "oculto"}


def _header(sheet) -> tuple[str | None, ...]:
    return tuple(_text(value) for value in next(sheet.iter_rows(max_row=1, values_only=True), ()))


def _require_columns(header: tuple[str | None, ...], required: tuple[str, ...], label: str) -> None:
    missing = [column for column in required if column not in header]
    if missing:
        raise ValueError(f"invalid {label} workbook header; missing columns: {', '.join(missing)}")


def parse_workbook(path: str | Path) -> dict:
    """Parse either supported XLSX format without touching the database."""
    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        project_sheets = [sheet for sheet in workbook.worksheets if set(PROJECT_COLUMNS) <= set(_header(sheet))]
        legacy_sheets = [sheet for sheet in workbook.worksheets if set(LEGACY_COLUMNS) <= set(_header(sheet))]
        if project_sheets:
            preferred = next((sheet for sheet in project_sheets if sheet.title == "Projetos"), project_sheets[0])
            return _parse_project_sheet(preferred)
        if legacy_sheets:
            preferred = next((sheet for sheet in legacy_sheets if sheet.title.casefold() == "all"), legacy_sheets[0])
            return _parse_legacy_sheet(preferred)
        observed = ", ".join(workbook.sheetnames)
        raise ValueError(
            "unsupported syllabus workbook; expected the 21-column Projetos or "
            f"16-column related format (sheets: {observed})"
        )
    finally:
        workbook.close()


def _parse_project_sheet(sheet) -> dict:
    header = _header(sheet)
    _require_columns(header, PROJECT_COLUMNS, "Projetos")
    rows = sheet.iter_rows(values_only=True)
    next(rows, None)
    lessons, references = [], []
    workbook_title = None
    for row_number, raw in enumerate(rows, start=2):
        if not any(_text(value) for value in raw):
            continue
        fields = {column: _text(value) for column, value in zip(header, raw)}
        workbook_title = workbook_title or fields.get("Projeto")
        week_text = fields.get("Semana") or ""
        week_match = WEEK.fullmatch(week_text)
        if not week_match:
            raise ValueError(
                f"row {row_number}: invalid Semana value {week_text!r}; expected 'Semana XX'"
            )
        common = {
            "week": int(week_match.group(1)),
            "seq": _as_int(fields.get("Ordem"), row_number=row_number, column="Ordem"),
            "title": fields.get("Atividade") or "",
            "description": fields.get("Descrição da atividade"),
            "fields": fields,
            "is_hidden": _as_bool(fields.get(HIDDEN_COLUMN)),
            "row_number": row_number,
        }
        if not common["title"]:
            raise ValueError(f"row {row_number}: Atividade is empty")
        if (fields.get("Tipo da atividade") or "").casefold() == "autoestudo":
            references.append(
                {
                    **common,
                    "parent_title": fields.get("Encontro pai"),
                    "url": fields.get("URL"),
                    "resource_code": None,
                    "is_hidden": _as_bool(fields.get(HIDDEN_COLUMN)),
                }
            )
        else:
            lesson_kind = _project_lesson_kind(
                fields.get("Tipo da atividade"), row_number=row_number
            )
            lesson_subject = _project_subject(
                fields.get("Eixo"), row_number=row_number
            )
            if lesson_kind == "Class" and lesson_subject is None:
                raise ValueError(f"row {row_number}: Eixo is required for a Class")
            lessons.append(
                {
                    **common,
                    "kind": lesson_kind,
                    "subject": lesson_subject,
                    "subjects": parse_subjects(fields.get("Assuntos")),
                    "lesson_date": None,
                }
            )
    return _assemble_parsed("projetos-21", workbook_title, lessons, references)


def _parse_legacy_sheet(sheet) -> dict:
    header = _header(sheet)
    _require_columns(header, LEGACY_COLUMNS, "related")
    rows = sheet.iter_rows(values_only=True)
    next(rows, None)
    lessons, references = [], []
    for row_number, raw in enumerate(rows, start=2):
        if not any(_text(value) for value in raw):
            continue
        fields = {column: _text(value) for column, value in zip(header, raw)}
        common = {
            "week": _as_int(fields.get("Week"), row_number=row_number, column="Week"),
            "seq": _as_int(fields.get("Sort"), row_number=row_number, column="Sort"),
            "title": fields.get("Title") or "",
            "description": fields.get("Description"),
            "fields": fields,
            "is_hidden": _as_bool(fields.get(HIDDEN_COLUMN)),
            "row_number": row_number,
        }
        if not common["title"]:
            raise ValueError(f"row {row_number}: Title is empty")
        if (fields.get("Type") or "").casefold() == "self-study":
            references.append(
                {
                    **common,
                    "parent_title": fields.get("Parent class"),
                    "url": fields.get("URL"),
                    "resource_code": fields.get("Resource code"),
                    "is_hidden": _as_bool(fields.get(HIDDEN_COLUMN)),
                }
            )
        else:
            lessons.append(
                {
                    **common,
                    "kind": fields.get("Type") or "Activity",
                    "subject": fields.get("Axis"),
                    "subjects": parse_subjects(fields.get("Related subjects")),
                    "lesson_date": _as_date(fields.get("Date")),
                }
            )
    return _assemble_parsed("related-16", None, lessons, references)


def _assemble_parsed(format_name: str, workbook_title: str | None, lessons: list[dict], references: list[dict]) -> dict:
    if not lessons:
        raise ValueError("syllabus workbook has no lessons")
    lessons.sort(key=lambda item: (item["week"], item["seq"], item["row_number"]))
    for lesson_index, lesson in enumerate(lessons):
        lesson["source_references"] = []
        lesson["_index"] = lesson_index

    for reference in references:
        parent = (reference.get("parent_title") or "").strip()
        candidates = [
            lesson
            for lesson in lessons
            if lesson["week"] == reference["week"] and lesson["title"].strip() == parent
        ]
        if not candidates and not parent:
            # Some related workbooks omit Parent class for a source but retain
            # the same Week, Axis and Professor as its lesson. Infer only when
            # that institutional metadata identifies exactly one lesson; an
            # ambiguous orphan remains an explicit workbook error.
            reference_fields = reference.get("fields") or {}
            professor = _text(reference_fields.get("Professor"))
            axis = _text(reference_fields.get("Axis"))
            inferred = [
                lesson
                for lesson in lessons
                if lesson["week"] == reference["week"]
                and professor
                and professor == _text((lesson.get("fields") or {}).get("Professor"))
                and axis
                and axis == _text(lesson.get("subject"))
            ]
            if len(inferred) == 1:
                candidates = inferred
        if not candidates:
            raise ValueError(
                f"row {reference['row_number']}: source {reference['title']!r} refers to "
                f"unknown lesson {parent!r} in week {reference['week']}"
            )
        preceding = [lesson for lesson in candidates if lesson["seq"] <= reference["seq"]]
        lesson = max(preceding or candidates, key=lambda item: item["seq"])
        url = reference.get("url") or ""
        code = _resource_code(
            url,
            reference.get("resource_code"),
            f"{reference['title']}\n{reference.get('description') or ''}",
        )
        kind = media_type(url, code)
        scope = (
            extract_book_scope(
                f"{reference['title']}\n{reference.get('description') or ''}", url
            )
            if kind == "book"
            else None
        )
        lesson["source_references"].append(
            {
                "seq": reference["seq"],
                "title": reference["title"],
                "description": reference.get("description"),
                "url": url or None,
                "media_type": kind,
                "resource_code": code,
                "scope_kind": scope[0] if scope else None,
                "scope_value": scope[1] if scope else None,
                "is_hidden": bool(reference.get("is_hidden")),
                "fields": reference["fields"],
                "row_number": reference["row_number"],
            }
        )
    for lesson in lessons:
        lesson["source_references"].sort(key=lambda item: (item["seq"], item["row_number"]))
        lesson.pop("_index", None)
    return {
        "format": format_name,
        "workbook_title": workbook_title,
        "lessons": lessons,
        "lesson_count": len(lessons),
        "source_count": len(references),
    }


# --- Database write/read interface -------------------------------------------------


def next_curation_event_id(conn: psycopg.Connection) -> str:
    """Allocate the next append-only curation event id."""
    conn.execute("LOCK TABLE curation_event IN SHARE ROW EXCLUSIVE MODE")
    number = conn.execute(
        "SELECT coalesce(max(substring(id from '^ce([0-9]+)$')::bigint), 0) + 1"
        " FROM curation_event WHERE id ~ '^ce[0-9]+$'"
    ).fetchone()[0]
    return f"ce{number:04d}"


def _version_counts(conn: psycopg.Connection, version_id: str) -> tuple[int, int]:
    """Return lesson and source-reference counts for a complete version."""
    return conn.execute(
        "SELECT"
        " (SELECT count(*) FROM syllabus_lesson WHERE version_id = %s),"
        " (SELECT count(*) FROM syllabus_source_reference WHERE version_id = %s)",
        (version_id, version_id),
    ).fetchone()


def resolve_source(
    conn: psycopg.Connection,
    url: str,
    title: str,
    *,
    media_kind: str | None = None,
    resource_code: str | None = None,
    scope_kind: str | None = None,
    scope_value: str | None = None,
) -> tuple[str | None, bool]:
    """Resolve or mint a logical Source from a media-aware identity."""
    if (
        media_kind is None
        and resource_code is None
        and scope_kind is None
        and scope_value is None
    ):
        canonical = canonical_url(url)
        if not canonical:
            return None, False
        identity = {"canonical_url": canonical}
        encoded = json.dumps(
            identity, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        source_id = "src-" + hashlib.sha256(encoded.encode()).hexdigest()[:16]
        cursor = conn.execute(
            "INSERT INTO source (id, identity, title, media_type)"
            " VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
            (source_id, Jsonb(identity), title, media_type(url)),
        )
        return source_id, bool(cursor.rowcount)
    identity = source_identity(
        url,
        media_kind=media_kind,
        resource_code=resource_code,
        scope_kind=scope_kind,
        scope_value=scope_value,
    )
    if identity is None:
        return None, False
    encoded = json.dumps(identity, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_id = "src-" + hashlib.sha256(encoded.encode()).hexdigest()[:16]
    cursor = conn.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (source_id, Jsonb(identity), title, identity["kind"]),
    )
    return source_id, bool(cursor.rowcount)


def import_workbook(
    conn: psycopg.Connection,
    path: str | Path,
    name: str | None = None,
    *,
    syllabus_id: str | None = None,
    institution_id: str | None = None,
    display_name: str | None = None,
    lesson_subject_ids: list[str] | tuple[str, ...] | None = None,
    require_syllabus_metadata: bool = True,
    actor: str = "founder",
) -> dict:
    """Author one complete uploaded version under a manually named syllabus.

    New named Syllabi require durable Institution and Lesson Subject metadata.
    Passing ``require_syllabus_metadata=False`` is the explicit compatibility
    path for historical fixtures and migrations that predate that model.
    """
    if name is None:
        return _import_legacy_flat_workbook(conn, path, actor=actor)
    name = (name or "").strip()
    if not name:
        raise ValueError("syllabus name is required")
    resolved_id = (syllabus_id or slugify(name)).strip()
    if not resolved_id:
        raise ValueError("syllabus id is empty after normalizing its name")
    syllabus_exists = conn.execute(
        "SELECT 1 FROM syllabus WHERE id = %s",
        (resolved_id,),
    ).fetchone() is not None
    metadata = _syllabus_metadata(
        conn,
        institution_id,
        display_name,
        lesson_subject_ids,
        required=require_syllabus_metadata and not syllabus_exists,
    )
    if metadata is not None and SYLLABUS_ID.fullmatch(resolved_id) is None:
        raise ValueError(
            "O identificador do syllabus deve começar com letra minúscula, ter "
            "de 2 a 128 caracteres e usar apenas letras minúsculas, números, "
            "ponto, hífen ou sublinhado."
        )
    path = Path(path)
    file_body = path.read_bytes()
    file_sha = hashlib.sha256(file_body).hexdigest()
    parsed = parse_workbook(path)

    _validate_selected_lesson_subjects(conn, resolved_id, parsed["lessons"])

    if metadata is not None:
        selected_codes = {
            subject["code"] for subject in metadata["lesson_subjects"]
        }
        missing_codes = sorted(
            {
                lesson["subject"]
                for lesson in parsed["lessons"]
                if lesson.get("subject")
            }
            - selected_codes
        )
        if missing_codes:
            raise ValueError(
                "Selecione as matérias usadas pela planilha: "
                + ", ".join(missing_codes)
                + "."
            )

    inserted = conn.execute(
        "INSERT INTO syllabus"
        " (id, title, institution_id, display_name)"
        " VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (
            resolved_id,
            name,
            metadata["institution"]["id"] if metadata else None,
            metadata["display_name"] if metadata else None,
        ),
    ).rowcount
    stored = conn.execute(
        "SELECT title, institution_id, display_name, group_id"
        " FROM syllabus WHERE id = %s FOR UPDATE",
        (resolved_id,),
    ).fetchone()
    if stored[0] != name:
        raise ValueError(
            f"syllabus id {resolved_id!r} already belongs to {stored[0]!r}, not {name!r}"
        )
    stored_subject_ids = [
        row[0]
        for row in conn.execute(
            "SELECT lesson_subject_id FROM syllabus_lesson_subject"
            " WHERE syllabus_id = %s ORDER BY lesson_subject_id",
            (resolved_id,),
        ).fetchall()
    ]
    requested_subject_ids = (
        [subject["id"] for subject in metadata["lesson_subjects"]]
        if metadata
        else []
    )
    if metadata and not inserted:
        if stored[1] not in {None, metadata["institution"]["id"]}:
            raise ValueError("a instituição não corresponde ao syllabus existente")
        if stored[2] not in {None, metadata["display_name"]}:
            raise ValueError("o nome não corresponde ao syllabus existente")
        if stored_subject_ids and set(stored_subject_ids) != set(requested_subject_ids):
            raise ValueError("as matérias não correspondem ao syllabus existente")
        if stored[3] is not None:
            group_institution = conn.execute(
                "SELECT institution_id FROM study_group WHERE id = %s",
                (stored[3],),
            ).fetchone()
            if group_institution and group_institution[0] != metadata["institution"]["id"]:
                raise ValueError("a instituição não corresponde ao grupo do syllabus")
        conn.execute(
            "UPDATE syllabus SET institution_id = %s, display_name = %s"
            " WHERE id = %s",
            (
                metadata["institution"]["id"],
                metadata["display_name"],
                resolved_id,
            ),
        )
    if metadata and not stored_subject_ids:
        for subject in metadata["lesson_subjects"]:
            conn.execute(
                "INSERT INTO syllabus_lesson_subject"
                " (syllabus_id, lesson_subject_id, institution_id)"
                " VALUES (%s, %s, %s)",
                (
                    resolved_id,
                    subject["id"],
                    metadata["institution"]["id"],
                ),
            )
    previous = _latest_version_row(conn, resolved_id)
    if previous and previous["file_sha"] == file_sha:
        lesson_count, reference_count = _version_counts(conn, previous["id"])
        conn.commit()
        return {
            "syllabus_id": resolved_id,
            "version_id": previous["id"],
            "seq": previous["seq"],
            "unchanged": True,
            "lesson_count": lesson_count,
            "reference_count": reference_count,
            "source_count": reference_count,
            "new_source_count": 0,
            "diff": {},
        }

    next_seq = (previous["seq"] if previous else 0) + 1
    version_id = f"{resolved_id}:v{next_seq:04d}"
    conn.execute(
        "INSERT INTO syllabus_version"
        " (id, syllabus_id, seq, origin, input_format, file_name, file_mime, file_sha, file_body)"
        " VALUES (%s, %s, %s, 'upload', %s, %s, %s, %s, %s)",
        (
            version_id,
            resolved_id,
            next_seq,
            parsed["format"],
            path.name,
            XLSX_MIME,
            file_sha,
            file_body,
        ),
    )

    new_sources = 0
    reference_count = 0
    for lesson_number, lesson in enumerate(parsed["lessons"], start=1):
        lesson_id = f"{version_id}:lesson:{lesson_number:04d}"
        conn.execute(
            "INSERT INTO syllabus_lesson"
            " (id, version_id, week, seq, kind, title, subject, subjects, lesson_date,"
            "  description, is_hidden, fields)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                lesson_id,
                version_id,
                lesson["week"],
                lesson["seq"],
                lesson["kind"],
                lesson["title"],
                lesson.get("subject"),
                lesson.get("subjects") or [],
                lesson.get("lesson_date"),
                lesson.get("description"),
                bool(lesson.get("is_hidden")),
                Jsonb(lesson["fields"]),
            ),
        )
        for reference in lesson["source_references"]:
            reference_count += 1
            reference_id = f"{version_id}:source:{reference_count:04d}"
            source_id, created = resolve_source(
                conn,
                reference.get("url") or "",
                reference["title"],
                media_kind=reference["media_type"],
                resource_code=reference.get("resource_code"),
                scope_kind=reference.get("scope_kind"),
                scope_value=reference.get("scope_value"),
            )
            new_sources += int(created)
            conn.execute(
                "INSERT INTO syllabus_source_reference"
                " (id, version_id, lesson_id, seq, title, description, url, media_type,"
                "  resource_code, scope_kind, scope_value, source_id, is_hidden, fields)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    reference_id,
                    version_id,
                    lesson_id,
                    reference["seq"],
                    reference["title"],
                    reference.get("description"),
                    reference.get("url"),
                    reference["media_type"],
                    reference.get("resource_code"),
                    reference.get("scope_kind"),
                    reference.get("scope_value"),
                    source_id,
                    bool(reference.get("is_hidden")),
                    Jsonb(reference["fields"]),
                ),
            )

    event_id = next_curation_event_id(conn)
    conn.execute(
        "INSERT INTO curation_event (id, actor, action, subject)"
        " VALUES (%s, %s, 'syllabus_upload', %s)",
        (
            event_id,
            actor,
            Jsonb(
                {
                    "syllabus_id": resolved_id,
                    "version_id": version_id,
                    "file_sha": file_sha,
                    "input_format": parsed["format"],
                }
            ),
        ),
    )
    diff = diff_versions(conn, previous["id"], version_id) if previous else {}
    conn.commit()
    return {
        "syllabus_id": resolved_id,
        "version_id": version_id,
        "seq": next_seq,
        "unchanged": False,
        "lesson_count": parsed["lesson_count"],
        "reference_count": reference_count,
        "source_count": reference_count,
        "new_source_count": new_sources,
        "diff": diff,
    }


def _import_legacy_flat_workbook(
    conn: psycopg.Connection,
    path: str | Path,
    *,
    actor: str,
) -> dict:
    """Preserve the former unnamed-import API beside the richer model.

    This bridge is intentionally used only when no explicit syllabus name is
    supplied. It keeps old curation facts addressable through ``syllabus_item``
    while all current browser uploads author lesson/reference versions.
    """
    path = Path(path)
    file_body = path.read_bytes()
    file_sha = hashlib.sha256(file_body).hexdigest()
    workbook = load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook["Projetos"] if "Projetos" in workbook.sheetnames else workbook.active
        rows = sheet.iter_rows(values_only=True)
        header = tuple(_text(value) for value in next(rows, ()))
        _require_columns(header, PROJECT_COLUMNS, "Projetos")
        items = []
        workbook_name = None
        for row_number, raw in enumerate(rows, start=2):
            if not any(_text(value) for value in raw):
                continue
            fields = {column: _text(value) for column, value in zip(header, raw)}
            workbook_name = workbook_name or fields.get("Projeto")
            week_match = WEEK.fullmatch(fields.get("Semana") or "")
            if not week_match:
                raise ValueError(f"row {row_number}: invalid Semana value")
            items.append(
                {
                    "week": int(week_match.group(1)),
                    "seq": _as_int(
                        fields.get("Ordem"), row_number=row_number, column="Ordem"
                    ),
                    "kind": fields.get("Tipo da atividade") or "Atividade",
                    "title": fields.get("Atividade") or "",
                    "description": fields.get("Descrição da atividade"),
                    "parent_title": fields.get("Encontro pai"),
                    "url": fields.get("URL"),
                    "fields": fields,
                }
            )
    finally:
        workbook.close()
    if not workbook_name or not items:
        raise ValueError("syllabus workbook has no named items")

    syllabus_id = slugify(workbook_name)
    conn.execute(
        "INSERT INTO syllabus (id, title) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING",
        (syllabus_id, workbook_name),
    )
    previous = _latest_version_row(conn, syllabus_id)
    if previous and previous["file_sha"] == file_sha:
        conn.commit()
        return {
            "syllabus_id": syllabus_id,
            "version_id": previous["id"],
            "seq": previous["seq"],
            "unchanged": True,
            "item_count": 0,
            "source_count": 0,
            "diff": {},
        }

    seq = (previous["seq"] if previous else 0) + 1
    version_id = f"{syllabus_id}:v{seq:04d}"
    conn.execute(
        "INSERT INTO syllabus_version"
        " (id, syllabus_id, seq, origin, input_format, file_name, file_mime,"
        "  file_sha, file_body)"
        " VALUES (%s, %s, %s, 'upload', 'legacy-flat', %s, %s, %s, %s)",
        (version_id, syllabus_id, seq, path.name, XLSX_MIME, file_sha, file_body),
    )
    source_count = 0
    for index, item in enumerate(
        sorted(items, key=lambda value: (value["week"], value["seq"], value["title"])),
        start=1,
    ):
        source_id = None
        if item["kind"].casefold() == "autoestudo" and item["url"]:
            source_id, created = resolve_source(conn, item["url"], item["title"])
            source_count += int(created)
        conn.execute(
            "INSERT INTO syllabus_item"
            " (id, version_id, week, seq, kind, title, description, parent_title,"
            "  url, source_id, fields)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                f"{version_id}:{index:04d}", version_id, item["week"], item["seq"],
                item["kind"], item["title"], item["description"],
                item["parent_title"], item["url"], source_id, Jsonb(item["fields"]),
            ),
        )
    event_id = next_curation_event_id(conn)
    conn.execute(
        "INSERT INTO curation_event (id, actor, action, subject)"
        " VALUES (%s, %s, 'syllabus_upload', %s)",
        (event_id, actor, Jsonb({"syllabus_id": syllabus_id, "version_id": version_id, "file_sha": file_sha})),
    )
    conn.commit()
    return {
        "syllabus_id": syllabus_id,
        "version_id": version_id,
        "seq": seq,
        "unchanged": False,
        "item_count": len(items),
        "source_count": source_count,
        "diff": {},
    }


def _latest_version_row(conn: psycopg.Connection, syllabus_id: str) -> dict | None:
    row = conn.execute(
        "SELECT id, seq, origin, input_format, file_name, file_sha, note, created_at"
        " FROM syllabus_version WHERE syllabus_id = %s ORDER BY seq DESC LIMIT 1",
        (syllabus_id,),
    ).fetchone()
    if row is None:
        return None
    return dict(
        zip(
            ("id", "seq", "origin", "input_format", "file_name", "file_sha", "note", "created_at"),
            row,
        )
    )


def _lesson_subjects_by_syllabus(
    conn: psycopg.Connection,
    syllabus_ids: list[str] | tuple[str, ...] | None = None,
) -> dict[str, list[dict]]:
    query = (
        "SELECT selected.syllabus_id, subject.id, subject.code, subject.display_name"
        " FROM syllabus_lesson_subject selected"
        " JOIN lesson_subject subject ON subject.id = selected.lesson_subject_id"
    )
    params: tuple = ()
    if syllabus_ids is not None:
        if not syllabus_ids:
            return {}
        query += " WHERE selected.syllabus_id = ANY(%s)"
        params = (list(syllabus_ids),)
    query += " ORDER BY selected.syllabus_id, subject.code, subject.id"
    result: dict[str, list[dict]] = {}
    for syllabus_id, subject_id, code, display_name in conn.execute(
        query, params
    ).fetchall():
        result.setdefault(syllabus_id, []).append(
            {"id": subject_id, "code": code, "display_name": display_name}
        )
    return result


def _syllabus_payload(row: tuple, lesson_subjects: list[dict]) -> dict:
    syllabus_id, title, display_name, institution_id, institution_name, created_at = row
    institution = (
        {"id": institution_id, "name": institution_name}
        if institution_id is not None
        else None
    )
    metadata_complete = bool(
        institution_id
        and display_name
        and lesson_subjects
        and SYLLABUS_ID.fullmatch(syllabus_id)
    )
    bridge = (
        {
            "graph_id": syllabus_id,
            "display_name": display_name,
            "institution_slug": institution_id,
        }
        if metadata_complete
        else None
    )
    return {
        "id": syllabus_id,
        "title": title,
        "display_name": display_name,
        "institution_id": institution_id,
        "institution": institution,
        "lesson_subjects": lesson_subjects,
        "metadata_complete": metadata_complete,
        # Temporary compatibility values are derived from durable identities.
        # Neither value is stored as a second content identity.
        "graph_id": syllabus_id if metadata_complete else None,
        "institution_slug": institution_id if metadata_complete else None,
        "temporary_bridge": bridge,
        "created_at": created_at,
    }


def list_syllabi(conn: psycopg.Connection) -> list[dict]:
    """List syllabi with a compact summary of only their latest version."""
    rows = conn.execute(
        "SELECT syllabus.id, syllabus.title, syllabus.display_name,"
        " institution.id, institution.name, syllabus.created_at"
        " FROM syllabus LEFT JOIN institution"
        " ON institution.id = syllabus.institution_id"
        " ORDER BY syllabus.created_at DESC, syllabus.id"
    ).fetchall()
    subjects = _lesson_subjects_by_syllabus(
        conn, [row[0] for row in rows]
    )
    result = []
    for row in rows:
        syllabus_id = row[0]
        latest = _latest_version_row(conn, syllabus_id)
        if latest:
            lesson_count, source_count = _version_counts(conn, latest["id"])
            latest = {**latest, "lesson_count": lesson_count, "source_count": source_count}
        result.append({**_syllabus_payload(row, subjects.get(syllabus_id, [])), "latest": latest})
    return result


def get_syllabus_history(conn: psycopg.Connection, syllabus_id: str) -> dict:
    """Return immutable versions newest first, each with full-state counts."""
    syllabus = conn.execute(
        "SELECT syllabus.id, syllabus.title, syllabus.display_name,"
        " institution.id, institution.name, syllabus.created_at"
        " FROM syllabus LEFT JOIN institution"
        " ON institution.id = syllabus.institution_id"
        " WHERE syllabus.id = %s",
        (syllabus_id,),
    ).fetchone()
    if syllabus is None:
        raise LookupError(f"unknown syllabus {syllabus_id!r}")
    rows = conn.execute(
        "SELECT sv.id, sv.seq, sv.origin, sv.input_format, sv.file_name, sv.file_sha,"
        " sv.note, sv.created_at,"
        " (SELECT count(*) FROM syllabus_lesson sl WHERE sl.version_id = sv.id),"
        " (SELECT count(*) FROM syllabus_source_reference sr WHERE sr.version_id = sv.id)"
        " FROM syllabus_version sv WHERE sv.syllabus_id = %s ORDER BY sv.seq DESC",
        (syllabus_id,),
    ).fetchall()
    versions = [
        dict(
            zip(
                (
                    "id", "seq", "origin", "input_format", "file_name", "file_sha",
                    "note", "created_at", "lesson_count", "source_count",
                ),
                row,
            )
        )
        for row in rows
    ]
    subjects = _lesson_subjects_by_syllabus(conn, [syllabus_id])
    return {
        **_syllabus_payload(syllabus, subjects.get(syllabus_id, [])),
        "versions": versions,
    }


def get_syllabus_workbook(conn: psycopg.Connection, version_id: str) -> dict:
    """Return the exact uploaded XLSX for download or audit."""
    row = conn.execute(
        "SELECT file_name, file_mime, file_sha, file_body"
        " FROM syllabus_version WHERE id = %s",
        (version_id,),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown syllabus version {version_id!r}")
    if row[3] is None:
        raise LookupError(f"syllabus version {version_id!r} has no uploaded workbook")
    return {"file_name": row[0], "mime_type": row[1], "sha256": row[2], "body": bytes(row[3])}


def get_syllabus_version(
    conn: psycopg.Connection, syllabus_id: str, version_id: str | None = None
) -> dict:
    """Return one full version; omitting ``version_id`` means latest."""
    syllabus = conn.execute(
        "SELECT syllabus.id, syllabus.title, syllabus.display_name,"
        " institution.id, institution.name, syllabus.created_at"
        " FROM syllabus LEFT JOIN institution"
        " ON institution.id = syllabus.institution_id"
        " WHERE syllabus.id = %s",
        (syllabus_id,),
    ).fetchone()
    if syllabus is None:
        raise LookupError(f"unknown syllabus {syllabus_id!r}")
    if version_id is None:
        version = _latest_version_row(conn, syllabus_id)
    else:
        row = conn.execute(
            "SELECT id, seq, origin, input_format, file_name, file_sha, note, created_at"
            " FROM syllabus_version WHERE syllabus_id = %s AND id = %s",
            (syllabus_id, version_id),
        ).fetchone()
        version = (
            dict(zip(("id", "seq", "origin", "input_format", "file_name", "file_sha", "note", "created_at"), row))
            if row
            else None
        )
    if version is None:
        raise LookupError(f"unknown version {version_id!r} for syllabus {syllabus_id!r}")

    lesson_rows = conn.execute(
        "SELECT sl.id, sl.week, sl.seq, sl.kind, sl.title, sl.subject, sl.subjects,"
        " sl.lesson_date, sl.description, sl.fields, sl.created_at, sl.is_hidden"
        " FROM syllabus_lesson sl"
        " WHERE sl.version_id = %s ORDER BY sl.week NULLS LAST, sl.seq, sl.id",
        (version["id"],),
    ).fetchall()
    lessons = []
    for row in lesson_rows:
        lesson = dict(
            zip(
                (
                    "id", "week", "seq", "kind", "title", "subject", "subjects",
                    "date", "description", "fields", "created_at", "hidden",
                ),
                row,
            )
        )
        reference_rows = conn.execute(
            "SELECT sr.id, sr.source_id, sr.seq, sr.title, sr.description, sr.url,"
            " sr.media_type, sr.resource_code, sr.scope_kind, sr.scope_value, sr.is_hidden,"
            " sr.fields, sr.created_at, s.identity,"
            " coalesce(rr.is_validated, false), rr.complexity"
            " FROM syllabus_source_reference sr"
            " LEFT JOIN source s ON s.id = sr.source_id"
            " LEFT JOIN syllabus_source_review rr ON rr.reference_id = sr.id"
            " WHERE sr.lesson_id = %s ORDER BY sr.seq, sr.id",
            (lesson["id"],),
        ).fetchall()
        sources = []
        for reference_row in reference_rows:
            source = dict(
                zip(
                    (
                        "reference_id", "source_id", "seq", "title", "description", "url",
                        "media_type", "resource_code", "scope_kind", "scope_value", "hidden",
                        "fields", "created_at", "identity",
                        "validated", "complexity",
                    ),
                    reference_row,
                )
            )
            source["review"] = {
                "validated": source.pop("validated"),
                "complexity": source.pop("complexity"),
            }
            source["scope"] = (
                {"kind": source["scope_kind"], "value": source["scope_value"]}
                if source["scope_kind"]
                else None
            )
            sources.append(source)
        lesson["sources"] = sources
        lessons.append(lesson)
    subjects = _lesson_subjects_by_syllabus(conn, [syllabus_id]).get(
        syllabus_id, []
    )
    by_code = {subject["code"]: subject for subject in subjects}
    for lesson in lessons:
        lesson["lesson_subject"] = by_code.get(lesson["subject"])
    return {
        **_syllabus_payload(syllabus, subjects),
        "version": version,
        "lessons": lessons,
    }


def update_source_review(
    conn: psycopg.Connection,
    syllabus_id: str,
    reference_id: str,
    changes: object,
) -> dict:
    """Update the small operational review state for one source reference."""
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Informe ao menos um marcador do autoestudo.")
    unknown = set(changes) - {"validated", "complexity"}
    if unknown:
        raise ValueError("A revisão contém campos desconhecidos.")
    reference = conn.execute(
        "SELECT 1 FROM syllabus_source_reference sr"
        " JOIN syllabus_version sv ON sv.id = sr.version_id"
        " WHERE sr.id = %s AND sv.syllabus_id = %s",
        (reference_id, syllabus_id),
    ).fetchone()
    if reference is None:
        raise LookupError(
            f"unknown source reference {reference_id!r} for syllabus {syllabus_id!r}"
        )

    current = conn.execute(
        "SELECT is_validated, complexity FROM syllabus_source_review WHERE reference_id = %s",
        (reference_id,),
    ).fetchone() or (False, None)
    validated, complexity = current
    if "validated" in changes:
        if not isinstance(changes["validated"], bool):
            raise ValueError("O marcador de validação deve ser verdadeiro ou falso.")
        validated = changes["validated"]
    if "complexity" in changes:
        complexity = changes["complexity"]
        if complexity not in {None, "simple", "complex"}:
            raise ValueError("A complexidade deve ser simples, complexa ou vazia.")

    conn.execute(
        "INSERT INTO syllabus_source_review (reference_id, is_validated, complexity)"
        " VALUES (%s, %s, %s)"
        " ON CONFLICT (reference_id) DO UPDATE SET"
        " is_validated = excluded.is_validated, complexity = excluded.complexity,"
        " updated_at = now()",
        (reference_id, validated, complexity),
    )
    conn.commit()
    return {"validated": validated, "complexity": complexity}


class SyllabusVersionConflict(ValueError):
    """Raised when a curator tries to save over a newer immutable version."""


def _clean_edit_text(value, *, field: str, required: bool = False, limit: int = 20_000) -> str | None:
    text = _text(value)
    if required and not text:
        raise ValueError(f"{field} is required")
    if text and len(text) > limit:
        raise ValueError(f"{field} exceeds {limit} characters")
    return text


def _clean_subjects(value: object, *, lesson_index: int) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, (str, list, tuple)):
        raise ValueError(f"lesson {lesson_index}: subjects must be a list")
    subjects = parse_subjects(value)
    if len(subjects) > 200:
        raise ValueError(f"lesson {lesson_index}: subjects exceed the limit of 200")
    for subject in subjects:
        _clean_edit_text(
            subject,
            field=f"lesson {lesson_index} subject",
            required=True,
            limit=500,
        )
    return subjects


def _base_fields(item: dict | None) -> dict:
    fields = (item or {}).get("fields") or {}
    return dict(fields) if isinstance(fields, dict) else {}


def _normalize_curation_projection(base: dict, submitted_lessons: object) -> list[dict]:
    """Validate an editor payload and inherit non-editable workbook metadata.

    The browser submits the complete desired projection, but arbitrary client
    ``fields`` are never trusted. Existing rows inherit their original field
    bag by id; newly authored rows start empty and receive the canonical typed
    values below. This keeps professor/assessment metadata lossless without
    letting stale form state overwrite unrelated columns.
    """
    if not isinstance(submitted_lessons, list) or not submitted_lessons:
        raise ValueError("the syllabus must contain at least one lesson")
    if len(submitted_lessons) > 500:
        raise ValueError("the syllabus exceeds the limit of 500 lessons")

    base_lessons = {lesson["id"]: lesson for lesson in base.get("lessons", [])}
    base_references = {
        source["reference_id"]: source
        for lesson in base.get("lessons", [])
        for source in lesson.get("sources", [])
    }
    normalized: list[dict] = []
    source_total = 0
    for lesson_index, raw_lesson in enumerate(submitted_lessons, 1):
        if not isinstance(raw_lesson, dict):
            raise ValueError(f"lesson {lesson_index} is invalid")
        base_lesson = base_lessons.get(str(raw_lesson.get("id") or ""))
        try:
            week = int(raw_lesson.get("week")) if raw_lesson.get("week") not in {None, ""} else None
        except (TypeError, ValueError) as exc:
            raise ValueError(f"lesson {lesson_index}: week must be a whole number") from exc
        if week is not None and not 0 < week <= 1000:
            raise ValueError(f"lesson {lesson_index}: week must be between 1 and 1000")
        lesson_date = _as_date(raw_lesson.get("date"))
        if raw_lesson.get("date") and lesson_date is None:
            raise ValueError(f"lesson {lesson_index}: date must use YYYY-MM-DD")
        raw_sources = raw_lesson.get("sources", [])
        if not isinstance(raw_sources, list) or len(raw_sources) > 500:
            raise ValueError(f"lesson {lesson_index}: invalid source list")
        source_total += len(raw_sources)
        if source_total > 5000:
            raise ValueError("the syllabus exceeds the limit of 5000 sources")

        lesson = {
            "week": week,
            "seq": lesson_index,
            "kind": _clean_edit_text(
                raw_lesson.get("kind") or (base_lesson or {}).get("kind") or "Class",
                field=f"lesson {lesson_index} kind",
                required=True,
                limit=200,
            ),
            "title": _clean_edit_text(
                raw_lesson.get("title"),
                field=f"lesson {lesson_index} title",
                required=True,
                limit=1000,
            ),
            "subject": _clean_edit_text(
                raw_lesson.get("subject"), field=f"lesson {lesson_index} subject", limit=500
            ),
            "subjects": _clean_subjects(
                raw_lesson.get(
                    "subjects", (base_lesson or {}).get("subjects") or []
                ),
                lesson_index=lesson_index,
            ),
            "lesson_date": lesson_date,
            "description": _clean_edit_text(
                raw_lesson.get("description"),
                field=f"lesson {lesson_index} description",
                limit=4000,
            ),
            "is_hidden": bool(raw_lesson.get("hidden")),
            "fields": _base_fields(base_lesson),
            "source_references": [],
        }
        for source_index, raw_source in enumerate(raw_sources, 1):
            if not isinstance(raw_source, dict):
                raise ValueError(f"lesson {lesson_index}, source {source_index} is invalid")
            base_source = base_references.get(str(raw_source.get("reference_id") or ""))
            kind = str(raw_source.get("media_type") or "article").strip().lower()
            if kind not in {"article", "video", "book"}:
                raise ValueError(
                    f"lesson {lesson_index}, source {source_index}: invalid media type"
                )
            code = _clean_code(raw_source.get("resource_code"))
            scope_kind = _clean_edit_text(
                raw_source.get("scope_kind"),
                field=f"lesson {lesson_index}, source {source_index} scope kind",
                limit=100,
            )
            scope_value = _clean_edit_text(
                raw_source.get("scope_value"),
                field=f"lesson {lesson_index}, source {source_index} scope value",
                limit=500,
            )
            if bool(scope_kind) != bool(scope_value):
                raise ValueError(
                    f"lesson {lesson_index}, source {source_index}: scope kind and value must be provided together"
                )
            if scope_value:
                scope_value = _normalize_scope_value(scope_value)
            reference = {
                    "seq": source_index,
                    "title": _clean_edit_text(
                        raw_source.get("title"),
                        field=f"lesson {lesson_index}, source {source_index} title",
                        required=True,
                        limit=1000,
                    ),
                    "description": _clean_edit_text(
                        raw_source.get("description"),
                        field=f"lesson {lesson_index}, source {source_index} description",
                        limit=4000,
                    ),
                    "url": _clean_edit_text(
                        raw_source.get("url"),
                        field=f"lesson {lesson_index}, source {source_index} URL",
                        limit=8000,
                    ),
                    "media_type": kind,
                    "resource_code": code,
                    "scope_kind": scope_kind,
                    "scope_value": scope_value,
                    "is_hidden": bool(raw_source.get("hidden")),
                    "fields": _base_fields(base_source),
                    "_base_review": dict((base_source or {}).get("review") or {}),
                }
            reference["_content_unchanged"] = bool(
                base_source
                and _projection_signature(
                    [{"source_references": [reference]}]
                ) == _projection_signature(
                    [{"sources": [base_source]}]
                )
            )
            lesson["source_references"].append(reference)
        normalized.append(lesson)
    return normalized


def _projection_signature(lessons: list[dict]) -> list[dict]:
    """Return only the authored syllabus meaning, excluding row ids/field bags."""
    return [
        {
            "week": lesson.get("week"),
            "kind": lesson.get("kind"),
            "title": lesson.get("title"),
            "subject": lesson.get("subject"),
            "subjects": list(lesson.get("subjects") or []),
            "date": str(lesson.get("lesson_date") or lesson.get("date") or ""),
            "description": lesson.get("description"),
            "hidden": bool(lesson.get("is_hidden", lesson.get("hidden", False))),
            "sources": [
                {
                    "title": source.get("title"),
                    "description": source.get("description"),
                    "url": source.get("url"),
                    "media_type": source.get("media_type"),
                    "resource_code": source.get("resource_code"),
                    "scope_kind": source.get("scope_kind"),
                    "scope_value": source.get("scope_value"),
                    "hidden": bool(source.get("is_hidden", source.get("hidden", False))),
                }
                for source in lesson.get("source_references", lesson.get("sources", []))
            ],
        }
        for lesson in lessons
    ]


def _validate_selected_lesson_subjects(
    conn: psycopg.Connection,
    syllabus_id: str,
    lessons: list[dict],
) -> None:
    selected_codes = {
        row[0]
        for row in conn.execute(
            "SELECT subject.code FROM syllabus_lesson_subject selected"
            " JOIN lesson_subject subject ON subject.id = selected.lesson_subject_id"
            " WHERE selected.syllabus_id = %s",
            (syllabus_id,),
        ).fetchall()
    }
    if not selected_codes:
        return
    unselected = sorted(
        {
            lesson.get("subject")
            for lesson in lessons
            if lesson.get("subject")
        }
        - selected_codes
    )
    if unselected:
        raise ValueError(
            "As matérias das aulas devem pertencer ao syllabus: "
            + ", ".join(unselected)
            + "."
        )


def _project_export_row(
    fields: dict, *, syllabus_title: str, week: int | None, order: int,
    kind: str, title: str, description: str | None, subject: str | None,
    subjects: list[str] | None = None,
    parent: str | None = None, url: str | None = None, hidden: bool = False,
) -> list:
    values = dict(fields)
    updates = {
        "Projeto": values.get("Projeto") or syllabus_title,
        "Semana": f"Semana {week:02d}" if week is not None else None,
        "Ordem": order,
        "Atividade": title,
        "Tipo da atividade": kind,
        "Descrição da atividade": description,
        "Eixo": subject,
        "URL": url,
        "Encontro pai": parent,
        HIDDEN_COLUMN: "yes" if hidden else "no",
    }
    if subjects is not None:
        updates["Assuntos"] = "\n,".join(subjects) or None
    values.update(updates)
    return [values.get(column) for column in (*PROJECT_COLUMNS, HIDDEN_COLUMN)]


def _legacy_export_row(
    fields: dict, *, week: int | None, order: int, kind: str, title: str,
    lesson_date: date | None, description: str | None, subject: str | None,
    subjects: list[str] | None = None,
    parent: str | None = None, url: str | None = None,
    resource_code: str | None = None, hidden: bool = False,
) -> list:
    values = dict(fields)
    formatted_date = lesson_date.strftime("%d/%m/%Y") if lesson_date else None
    updates = {
        "Week": week,
        "Sort": order,
        "Type": kind,
        "Title": title,
        "Date": formatted_date,
        "Date source": "inherited" if parent else (values.get("Date source") or "own"),
        "Parent class": parent,
        "Class date": formatted_date if parent else None,
        "Axis": subject,
        "Description": description,
        "URL": url,
        "Resource code": resource_code,
        HIDDEN_COLUMN: "yes" if hidden else "no",
    }
    if subjects is not None:
        updates["Related subjects"] = "\n".join(subjects) or None
    values.update(updates)
    return [values.get(column) for column in (*LEGACY_COLUMNS, HIDDEN_COLUMN)]


def compile_syllabus_workbook(
    syllabus_title: str, input_format: str | None, lessons: list[dict]
) -> bytes:
    """Compile one complete curation projection into a portable XLSX."""
    workbook = Workbook()
    sheet = workbook.active
    project_format = input_format == "projetos-21"
    sheet.title = "Projetos" if project_format else "All"
    sheet.append((*PROJECT_COLUMNS, HIDDEN_COLUMN) if project_format else (*LEGACY_COLUMNS, HIDDEN_COLUMN))
    order = 0
    for lesson in lessons:
        order += 1
        if project_format:
            sheet.append(
                _project_export_row(
                    lesson["fields"], syllabus_title=syllabus_title,
                    week=lesson["week"], order=order, kind=lesson["kind"],
                    title=lesson["title"], description=lesson.get("description"),
                    subject=lesson.get("subject"),
                    subjects=lesson.get("subjects") or [],
                    hidden=bool(lesson.get("is_hidden", lesson.get("hidden", False))),
                )
            )
        else:
            sheet.append(
                _legacy_export_row(
                    lesson["fields"], week=lesson["week"], order=order,
                    kind=lesson["kind"], title=lesson["title"],
                    lesson_date=lesson.get("lesson_date"),
                    description=lesson.get("description"), subject=lesson.get("subject"),
                    subjects=lesson.get("subjects") or [],
                    hidden=bool(lesson.get("is_hidden", lesson.get("hidden", False))),
                )
            )
        for source in lesson["source_references"]:
            order += 1
            if project_format:
                sheet.append(
                    _project_export_row(
                        source["fields"], syllabus_title=syllabus_title,
                        week=lesson["week"], order=order, kind="Autoestudo",
                        title=source["title"], description=source.get("description"),
                        subject=lesson.get("subject"), parent=lesson["title"],
                        url=source.get("url"), hidden=source["is_hidden"],
                    )
                )
            else:
                sheet.append(
                    _legacy_export_row(
                        source["fields"], week=lesson["week"], order=order,
                        kind="Self-study", title=source["title"],
                        lesson_date=lesson.get("lesson_date"),
                        description=source.get("description"), subject=lesson.get("subject"),
                        parent=lesson["title"], url=source.get("url"),
                        resource_code=source.get("resource_code"), hidden=source["is_hidden"],
                    )
                )
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    return stream.getvalue()


def curate_syllabus(
    conn: psycopg.Connection,
    syllabus_id: str,
    base_version_id: str,
    lessons: object,
    *,
    actor: str = "founder",
    note: str | None = None,
) -> dict:
    """Author a full immutable curation version from the latest projection."""
    syllabus = conn.execute(
        "SELECT id, title FROM syllabus WHERE id = %s FOR UPDATE", (syllabus_id,)
    ).fetchone()
    if syllabus is None:
        raise LookupError(f"unknown syllabus {syllabus_id!r}")
    latest = _latest_version_row(conn, syllabus_id)
    if latest is None:
        raise LookupError(f"syllabus {syllabus_id!r} has no version")
    if latest["id"] != base_version_id:
        raise SyllabusVersionConflict(
            "Este syllabus recebeu uma versão mais nova. Recarregue antes de salvar suas mudanças."
        )
    base = get_syllabus_version(conn, syllabus_id, base_version_id)
    normalized = _normalize_curation_projection(base, lessons)
    _validate_selected_lesson_subjects(conn, syllabus_id, normalized)
    if _projection_signature(normalized) == _projection_signature(base["lessons"]):
        conn.commit()
        lesson_count, source_count = _version_counts(conn, base_version_id)
        return {
            "syllabus_id": syllabus_id,
            "version_id": base_version_id,
            "seq": latest["seq"],
            "unchanged": True,
            "lesson_count": lesson_count,
            "reference_count": source_count,
            "source_count": source_count,
            "new_source_count": 0,
            "diff": {"added": [], "removed": [], "changed": []},
        }

    raw_note = str(note or "").strip()
    if not raw_note:
        raise ValueError("A razão da nova versão é obrigatória.")
    if len(raw_note) > 500:
        raise ValueError(
            "A razão da nova versão deve ter no máximo 500 caracteres."
        )

    next_seq = latest["seq"] + 1
    version_id = f"{syllabus_id}:v{next_seq:04d}"
    body = compile_syllabus_workbook(syllabus[1], latest.get("input_format"), normalized)
    file_name = f"{syllabus_id}-v{next_seq:04d}.xlsx"
    file_sha = hashlib.sha256(body).hexdigest()
    clean_note = _clean_edit_text(
        raw_note, field="curation note", required=True, limit=500
    )
    conn.execute(
        "INSERT INTO syllabus_version"
        " (id, syllabus_id, seq, origin, input_format, file_name, file_mime, file_sha,"
        "  file_body, note)"
        " VALUES (%s, %s, %s, 'curation', %s, %s, %s, %s, %s, %s)",
        (
            version_id, syllabus_id, next_seq, latest.get("input_format") or "related-16",
            file_name, XLSX_MIME, file_sha, body, clean_note,
        ),
    )

    reference_count = 0
    new_sources = 0
    for lesson_number, lesson in enumerate(normalized, 1):
        lesson_id = f"{version_id}:lesson:{lesson_number:04d}"
        conn.execute(
            "INSERT INTO syllabus_lesson"
            " (id, version_id, week, seq, kind, title, subject, subjects, lesson_date,"
            "  description, is_hidden, fields)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                lesson_id, version_id, lesson["week"], lesson_number, lesson["kind"],
                lesson["title"], lesson.get("subject"), lesson.get("subjects") or [],
                lesson.get("lesson_date"), lesson.get("description"),
                lesson["is_hidden"], Jsonb(lesson["fields"]),
            ),
        )
        for source_number, reference in enumerate(lesson["source_references"], 1):
            reference_count += 1
            reference_id = f"{version_id}:source:{reference_count:04d}"
            source_id, created = resolve_source(
                conn,
                reference.get("url") or "",
                reference["title"],
                media_kind=reference["media_type"],
                resource_code=reference.get("resource_code"),
                scope_kind=reference.get("scope_kind"),
                scope_value=reference.get("scope_value"),
            )
            new_sources += int(created)
            conn.execute(
                "INSERT INTO syllabus_source_reference"
                " (id, version_id, lesson_id, seq, title, description, url, media_type,"
                "  resource_code, scope_kind, scope_value, source_id, is_hidden, fields)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    reference_id, version_id, lesson_id, source_number,
                    reference["title"], reference.get("description"), reference.get("url"),
                    reference["media_type"], reference.get("resource_code"),
                    reference.get("scope_kind"), reference.get("scope_value"), source_id,
                    reference["is_hidden"], Jsonb(reference["fields"]),
                ),
            )
            base_review = reference.get("_base_review") or {}
            complexity = base_review.get("complexity")
            validated = bool(
                base_review.get("validated") and reference.get("_content_unchanged")
            )
            if complexity is not None or validated:
                conn.execute(
                    "INSERT INTO syllabus_source_review"
                    " (reference_id, is_validated, complexity) VALUES (%s, %s, %s)",
                    (reference_id, validated, complexity),
                )

    diff = diff_versions(conn, base_version_id, version_id)
    event_id = next_curation_event_id(conn)
    conn.execute(
        "INSERT INTO curation_event (id, actor, action, subject, note)"
        " VALUES (%s, %s, 'syllabus_curated', %s, %s)",
        (
            event_id,
            actor,
            Jsonb(
                {
                    "syllabus_id": syllabus_id,
                    "base_version_id": base_version_id,
                    "version_id": version_id,
                    "diff": diff,
                }
            ),
            clean_note,
        ),
    )
    conn.commit()
    return {
        "syllabus_id": syllabus_id,
        "version_id": version_id,
        "seq": next_seq,
        "unchanged": False,
        "lesson_count": len(normalized),
        "reference_count": reference_count,
        "source_count": reference_count,
        "new_source_count": new_sources,
        "diff": diff,
    }


def diff_versions(conn: psycopg.Connection, version_a: str, version_b: str) -> dict:
    """Compare source references in two full syllabus versions."""
    query = (
        "SELECT sl.week, sl.title, sr.seq, sr.title, sr.url, sr.description,"
        " sr.resource_code, sr.scope_kind, sr.scope_value, sr.is_hidden"
        " FROM syllabus_source_reference sr"
        " JOIN syllabus_lesson sl ON sl.id = sr.lesson_id"
        " WHERE sr.version_id = %s ORDER BY sl.week, sl.seq, sr.seq, sr.id"
    )
    rows_a = conn.execute(query, (version_a,)).fetchall()
    rows_b = conn.execute(query, (version_b,)).fetchall()
    keys = lambda row: (row[0], row[1], row[3])
    map_a, map_b = {keys(row): row for row in rows_a}, {keys(row): row for row in rows_b}

    def record(row):
        return {
            "week": row[0],
            "lesson": row[1],
            "seq": row[2],
            "title": row[3],
            "url": row[4],
            "description": row[5],
            "resource_code": row[6],
            "scope_kind": row[7],
            "scope_value": row[8],
            "hidden": row[9],
        }

    added = [record(map_b[key]) for key in map_b.keys() - map_a.keys()]
    removed = [record(map_a[key]) for key in map_a.keys() - map_b.keys()]
    changed = []
    for key in map_a.keys() & map_b.keys():
        if map_a[key][4:] != map_b[key][4:]:
            changed.append({"before": record(map_a[key]), "after": record(map_b[key])})
    sort_key = lambda item: (item["week"], item["lesson"], item["seq"], item["title"])
    added.sort(key=sort_key)
    removed.sort(key=sort_key)
    changed.sort(key=lambda item: sort_key(item["after"]))
    return {"added": added, "removed": removed, "changed": changed}


# --- CLI ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.syllabus")
    sub = parser.add_subparsers(dest="command", required=True)
    import_cmd = sub.add_parser("import", help="import a complete workbook version")
    import_cmd.add_argument("path")
    import_cmd.add_argument("--name", required=True, help="human name of the syllabus")
    import_cmd.add_argument("--syllabus-id", help="existing syllabus id for a new version")
    import_cmd.add_argument(
        "--institution-id",
        help="existing Institution id for a new Syllabus",
    )
    import_cmd.add_argument(
        "--display-name",
        help="Institution-facing name of the curricular unit",
    )
    import_cmd.add_argument(
        "--lesson-subject-id",
        action="append",
        dest="lesson_subject_ids",
        help="selected Institution-owned Lesson Subject id; repeat as needed",
    )
    import_cmd.set_defaults(func=cmd_import)
    sub.add_parser("list", help="list syllabi").set_defaults(func=cmd_list)
    return parser


def cmd_import(args: argparse.Namespace) -> None:
    with connect() as conn:
        result = import_workbook(
            conn,
            args.path,
            args.name,
            syllabus_id=args.syllabus_id,
            institution_id=args.institution_id,
            display_name=args.display_name,
            lesson_subject_ids=args.lesson_subject_ids,
            require_syllabus_metadata=True,
        )
    print(json.dumps(result, default=str, ensure_ascii=False, indent=2))


def cmd_list(_args: argparse.Namespace) -> None:
    with connect() as conn:
        result = list_syllabi(conn)
    print(json.dumps(result, default=str, ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
