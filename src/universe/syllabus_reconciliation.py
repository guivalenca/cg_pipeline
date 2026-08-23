"""Durable three-way review for an incoming Syllabus workbook.

The institution's last accepted workbook is the baseline, the latest
SyllabusVersion is the founder's current projection, and the newly uploaded
workbook is the incoming projection.  Only baseline -> incoming changes need a
decision; current manual edits and operational review markers remain in place
unless the founder explicitly transitions that item.
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path

import psycopg
from psycopg.types.json import Jsonb

from universe.syllabus import (
    XLSX_MIME,
    SyllabusVersionConflict,
    curate_syllabus,
    get_syllabus_version,
    parse_workbook,
    parse_subjects,
)


DECISIONS = {"keep", "transition", "custom"}
PLAN_VERSION = 3
LESSON_AUTHORED_FIELDS = (
    "week", "kind", "title", "subject", "subjects", "date", "description",
)
SOURCE_AUTHORED_FIELDS = (
    "title", "description", "url", "media_type", "resource_code",
    "scope_kind", "scope_value",
)


def _text(value: object) -> str:
    return str(value or "").strip()


def _norm(value: object) -> str:
    plain = unicodedata.normalize("NFKD", _text(value)).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", plain.casefold()).strip()


def _date(value: object) -> str | None:
    if isinstance(value, (date, datetime)):
        return value.date().isoformat() if isinstance(value, datetime) else value.isoformat()
    return _text(value) or None


def _json_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return _date(value)
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _source_projection(source: dict, order: int) -> dict:
    return {
        "reference_id": source.get("reference_id"),
        "source_id": source.get("source_id"),
        "seq": order,
        "title": source.get("title") or "",
        "description": source.get("description"),
        "url": source.get("url"),
        "media_type": source.get("media_type") or "article",
        "resource_code": source.get("resource_code"),
        "scope_kind": source.get("scope_kind"),
        "scope_value": source.get("scope_value"),
        "hidden": bool(source.get("hidden", source.get("is_hidden", False))),
        "fields": _json_value(dict(source.get("fields") or {})),
        "review": _json_value(dict(source.get("review") or {})),
    }


def _lesson_projection(lesson: dict, order: int, source_key: str) -> dict:
    sources = lesson.get(source_key, [])
    return {
        "id": lesson.get("id"),
        "week": lesson.get("week"),
        "seq": order,
        "kind": lesson.get("kind") or "Class",
        "title": lesson.get("title") or "",
        "subject": lesson.get("subject"),
        "subjects": parse_subjects(lesson.get("subjects")),
        "date": _date(lesson.get("date", lesson.get("lesson_date"))),
        "description": lesson.get("description"),
        "hidden": bool(lesson.get("hidden", lesson.get("is_hidden", False))),
        "fields": _json_value(dict(lesson.get("fields") or {})),
        "sources": [_source_projection(source, index) for index, source in enumerate(sources, 1)],
    }


def _version_projection(detail: dict) -> dict:
    return {
        "lessons": [
            _lesson_projection(lesson, index, "sources")
            for index, lesson in enumerate(detail.get("lessons", []), 1)
        ]
    }


def _parsed_projection(parsed: dict) -> dict:
    return {
        "lessons": [
            _lesson_projection(lesson, index, "source_references")
            for index, lesson in enumerate(parsed.get("lessons", []), 1)
        ]
    }


def _lesson_signature(item: dict | None) -> tuple:
    if not item:
        return ()
    return (
        item.get("week"),
        _norm(item.get("kind")),
        _norm(item.get("title")),
        _norm(item.get("subject")),
        tuple(_norm(subject) for subject in parse_subjects(item.get("subjects"))),
        _date(item.get("date")),
        _norm(item.get("description")),
    )


def _source_signature(item: dict | None) -> tuple:
    if not item:
        return ()
    return (
        _norm(item.get("title")),
        _norm(item.get("description")),
        _norm(item.get("url")),
        item.get("media_type"),
        _norm(item.get("resource_code")),
        item.get("scope_kind"),
        _norm(item.get("scope_value")),
    )


def _ratio(left: object, right: object) -> float:
    a, b = _norm(left), _norm(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _lesson_score(left: dict, right: dict) -> float:
    score = 0.0
    if _norm(left.get("title")) == _norm(right.get("title")):
        score += 100
    else:
        similarity = _ratio(left.get("title"), right.get("title"))
        if similarity >= 0.72:
            score += similarity * 55
    if left.get("week") == right.get("week"):
        score += 15
    if _norm(left.get("subject")) == _norm(right.get("subject")) and _norm(left.get("subject")):
        score += 12
    left_subjects = tuple(_norm(value) for value in parse_subjects(left.get("subjects")))
    right_subjects = tuple(_norm(value) for value in parse_subjects(right.get("subjects")))
    if left_subjects and left_subjects == right_subjects:
        score += 12
    if left.get("date") and left.get("date") == right.get("date"):
        score += 8
    if left.get("seq") == right.get("seq"):
        score += 5
    return score


def _source_score(left: dict, right: dict) -> float:
    score = 0.0
    if _norm(left.get("title")) == _norm(right.get("title")):
        score += 100
    else:
        similarity = _ratio(left.get("title"), right.get("title"))
        if similarity >= 0.68:
            score += similarity * 55
    if _norm(left.get("url")) and _norm(left.get("url")) == _norm(right.get("url")):
        score += 85
    if _norm(left.get("resource_code")) and _norm(left.get("resource_code")) == _norm(right.get("resource_code")):
        score += 85
    if left.get("media_type") == right.get("media_type"):
        score += 8
    if left.get("seq") == right.get("seq"):
        score += 8
    description_similarity = _ratio(left.get("description"), right.get("description"))
    if description_similarity >= 0.82:
        score += description_similarity * 18
    return score


def _match(
    left: list[dict], right: list[dict], score, threshold: float, *, positional: bool = False
) -> dict[int, int]:
    candidates = sorted(
        (
            (score(left_item, right_item), left_index, right_index)
            for left_index, left_item in enumerate(left)
            for right_index, right_item in enumerate(right)
        ),
        reverse=True,
    )
    result: dict[int, int] = {}
    used_right: set[int] = set()
    for value, left_index, right_index in candidates:
        if value < threshold or left_index in result or right_index in used_right:
            continue
        result[left_index] = right_index
        used_right.add(right_index)

    if positional:
        remaining_left = [index for index in range(len(left)) if index not in result]
        remaining_right = [index for index in range(len(right)) if index not in used_right]
        for left_index in remaining_left:
            compatible = [
                right_index
                for right_index in remaining_right
                if left[left_index].get("seq") == right[right_index].get("seq")
                and left[left_index].get("media_type") == right[right_index].get("media_type")
            ]
            if len(compatible) != 1:
                continue
            right_index = compatible[0]
            reverse = [
                candidate
                for candidate in remaining_left
                if left[candidate].get("seq") == right[right_index].get("seq")
                and left[candidate].get("media_type") == right[right_index].get("media_type")
            ]
            if len(reverse) != 1:
                continue
            result[left_index] = right_index
            used_right.add(right_index)
            remaining_right.remove(right_index)
    return result


def _status(
    baseline: dict | None,
    current: dict | None,
    incoming: dict | None,
    signature,
    effective: dict | None = None,
) -> str:
    if baseline is not None and incoming is not None:
        if signature(baseline) == signature(incoming):
            return "unchanged"
        if current is not None and signature(current) == signature(effective or incoming):
            return "unchanged"
        return "changed"
    if baseline is not None:
        return "removed" if current is not None else "unchanged"
    if incoming is not None:
        if current is not None and signature(current) == signature(incoming):
            return "unchanged"
        return "added"
    return "unchanged"


def _three_way_incoming(
    baseline: dict | None,
    current: dict | None,
    incoming: dict | None,
    fields: tuple[str, ...],
) -> dict | None:
    """Apply only institutional field deltas over the founder's current item."""
    if incoming is None:
        return None
    if baseline is None or current is None:
        return copy.deepcopy(incoming)
    merged = copy.deepcopy(current)
    for field in fields:
        if baseline.get(field) != incoming.get(field):
            merged[field] = copy.deepcopy(incoming.get(field))
    return merged


def _effective_incoming(
    status: str,
    current: dict | None,
    incoming: dict | None,
    merged: dict | None = None,
) -> dict | None:
    return copy.deepcopy(current if status == "unchanged" else (merged or incoming))


def _build_source_plans(
    baseline: list[dict], current: list[dict], incoming: list[dict]
) -> list[dict]:
    base_current = _match(baseline, current, _source_score, 35, positional=True)
    base_incoming = _match(baseline, incoming, _source_score, 35, positional=True)
    used_current = set(base_current.values())
    used_incoming = set(base_incoming.values())
    plans: list[dict] = []

    for baseline_index, base_item in enumerate(baseline):
        current_item = current[base_current[baseline_index]] if baseline_index in base_current else None
        incoming_item = incoming[base_incoming[baseline_index]] if baseline_index in base_incoming else None
        merged = _three_way_incoming(
            base_item, current_item, incoming_item, SOURCE_AUTHORED_FIELDS
        )
        status = _status(
            base_item, current_item, incoming_item, _source_signature, merged
        )
        if status == "unchanged" and current_item is None:
            continue
        plans.append(
            {
                "kind": "source",
                "status": status,
                "order": (incoming_item or current_item or base_item).get("seq"),
                "current": copy.deepcopy(current_item),
                "incoming": _effective_incoming(status, current_item, incoming_item, merged),
            }
        )

    unmatched_current = [item for index, item in enumerate(current) if index not in used_current]
    unmatched_incoming = [item for index, item in enumerate(incoming) if index not in used_incoming]
    local_matches = _match(unmatched_current, unmatched_incoming, _source_score, 35, positional=True)
    matched_incoming = set(local_matches.values())
    for current_index, current_item in enumerate(unmatched_current):
        incoming_item = unmatched_incoming[local_matches[current_index]] if current_index in local_matches else None
        exact = incoming_item is not None and _source_signature(current_item) == _source_signature(incoming_item)
        plans.append(
            {
                "kind": "source",
                "status": "unchanged" if exact or incoming_item is None else "added",
                "order": (incoming_item or current_item).get("seq"),
                "current": copy.deepcopy(current_item),
                "incoming": copy.deepcopy(current_item if exact or incoming_item is None else incoming_item),
            }
        )
    for incoming_index, incoming_item in enumerate(unmatched_incoming):
        if incoming_index in matched_incoming:
            continue
        plans.append(
            {
                "kind": "source",
                "status": "added",
                "order": incoming_item.get("seq"),
                "current": None,
                "incoming": copy.deepcopy(incoming_item),
            }
        )
    plans.sort(
        key=lambda item: (
            item.get("order") or 10**9,
            _norm((item.get("incoming") or item.get("current") or {}).get("title")),
        )
    )
    return plans


def build_plan(baseline: dict, current: dict, incoming: dict) -> dict:
    """Build one deterministic lesson/source reconciliation tree."""
    base_lessons = list(baseline.get("lessons") or [])
    current_lessons = list(current.get("lessons") or [])
    incoming_lessons = list(incoming.get("lessons") or [])
    base_current = _match(base_lessons, current_lessons, _lesson_score, 45)
    base_incoming = _match(base_lessons, incoming_lessons, _lesson_score, 45)
    used_current = set(base_current.values())
    used_incoming = set(base_incoming.values())
    lesson_plans: list[dict] = []

    for baseline_index, base_lesson in enumerate(base_lessons):
        current_lesson = current_lessons[base_current[baseline_index]] if baseline_index in base_current else None
        incoming_lesson = incoming_lessons[base_incoming[baseline_index]] if baseline_index in base_incoming else None
        merged_lesson = _three_way_incoming(
            base_lesson, current_lesson, incoming_lesson, LESSON_AUTHORED_FIELDS
        )
        lesson_status = _status(
            base_lesson, current_lesson, incoming_lesson, _lesson_signature, merged_lesson
        )
        if lesson_status == "unchanged" and current_lesson is None:
            continue
        source_plans = _build_source_plans(
            base_lesson.get("sources") or [],
            (current_lesson or {}).get("sources") or [],
            (incoming_lesson or {}).get("sources") or [],
        )
        lesson_plans.append(
            {
                "kind": "lesson",
                "status": lesson_status,
                "order": (incoming_lesson or current_lesson or base_lesson).get("seq"),
                "current": copy.deepcopy(current_lesson),
                "incoming": _effective_incoming(
                    lesson_status, current_lesson, incoming_lesson, merged_lesson
                ),
                "sources": source_plans,
            }
        )

    unmatched_current = [item for index, item in enumerate(current_lessons) if index not in used_current]
    unmatched_incoming = [item for index, item in enumerate(incoming_lessons) if index not in used_incoming]
    local_matches = _match(unmatched_current, unmatched_incoming, _lesson_score, 45)
    matched_incoming = set(local_matches.values())
    for current_index, current_lesson in enumerate(unmatched_current):
        incoming_lesson = unmatched_incoming[local_matches[current_index]] if current_index in local_matches else None
        exact = incoming_lesson is not None and _lesson_signature(current_lesson) == _lesson_signature(incoming_lesson)
        lesson_status = "unchanged" if exact or incoming_lesson is None else "added"
        source_plans = _build_source_plans(
            [], current_lesson.get("sources") or [], (incoming_lesson or {}).get("sources") or []
        )
        lesson_plans.append(
            {
                "kind": "lesson",
                "status": lesson_status,
                "order": (incoming_lesson or current_lesson).get("seq"),
                "current": copy.deepcopy(current_lesson),
                "incoming": copy.deepcopy(current_lesson if lesson_status == "unchanged" else incoming_lesson),
                "sources": source_plans,
            }
        )
    for incoming_index, incoming_lesson in enumerate(unmatched_incoming):
        if incoming_index in matched_incoming:
            continue
        lesson_plans.append(
            {
                "kind": "lesson",
                "status": "added",
                "order": incoming_lesson.get("seq"),
                "current": None,
                "incoming": copy.deepcopy(incoming_lesson),
                "sources": _build_source_plans([], [], incoming_lesson.get("sources") or []),
            }
        )

    lesson_plans.sort(
        key=lambda item: (
            (item.get("incoming") or item.get("current") or {}).get("week") or 10**9,
            item.get("order") or 10**9,
        )
    )
    action_count = 0
    unchanged_source_count = 0
    unchanged_lesson_count = 0
    inherited_settings = 0
    for lesson_index, lesson in enumerate(lesson_plans, 1):
        lesson["item_id"] = f"lesson-{lesson_index:04d}"
        if lesson["status"] == "unchanged":
            unchanged_lesson_count += 1
        else:
            action_count += 1
        for source_index, source in enumerate(lesson["sources"], 1):
            source["item_id"] = f"source-{lesson_index:04d}-{source_index:04d}"
            if source["status"] == "unchanged":
                unchanged_source_count += 1
            else:
                action_count += 1
            current_source = source.get("current") or {}
            review = current_source.get("review") or {}
            if current_source.get("hidden") or review.get("validated") or review.get("complexity"):
                inherited_settings += 1

    changed_lessons = sum(
        1
        for lesson in lesson_plans
        if lesson["status"] != "unchanged"
        or any(source["status"] != "unchanged" for source in lesson["sources"])
    )
    return {
        "version": PLAN_VERSION,
        "lessons": lesson_plans,
        "summary": {
            "lesson_count": len(incoming_lessons),
            "source_count": sum(len(lesson.get("sources") or []) for lesson in incoming_lessons),
            "unchanged_lesson_count": unchanged_lesson_count,
            "unchanged_source_count": unchanged_source_count,
            "changed_lesson_count": changed_lessons,
            "action_count": action_count,
            "inherited_settings": inherited_settings,
        },
    }


def _baseline_projection(conn: psycopg.Connection, syllabus_id: str) -> dict:
    applied = conn.execute(
        "SELECT incoming FROM syllabus_reconciliation"
        " WHERE syllabus_id = %s AND status = 'applied'"
        " ORDER BY applied_at DESC, id DESC LIMIT 1",
        (syllabus_id,),
    ).fetchone()
    if applied is not None:
        return dict(applied[0])
    uploaded = conn.execute(
        "SELECT id FROM syllabus_version"
        " WHERE syllabus_id = %s AND origin = 'upload' ORDER BY seq DESC LIMIT 1",
        (syllabus_id,),
    ).fetchone()
    if uploaded is None:
        raise LookupError(f"syllabus {syllabus_id!r} has no uploaded baseline")
    return _version_projection(get_syllabus_version(conn, syllabus_id, uploaded[0]))


def _row_payload(row: tuple) -> dict:
    keys = (
        "id", "syllabus_id", "base_version_id", "status", "input_format",
        "file_name", "file_sha", "incoming", "plan", "decisions",
        "created_version_id", "created_at", "applied_at",
    )
    payload = dict(zip(keys, row))
    payload["incoming"] = dict(payload.get("incoming") or {})
    payload["plan"] = dict(payload.get("plan") or {})
    payload["decisions"] = dict(payload.get("decisions") or {})
    payload.update(payload["plan"])
    return payload


RECONCILIATION_SELECT = (
    "SELECT id, syllabus_id, base_version_id, status, input_format, file_name,"
    " file_sha, incoming, plan, decisions, created_version_id, created_at, applied_at"
    " FROM syllabus_reconciliation"
)


def get_reconciliation(
    conn: psycopg.Connection, syllabus_id: str, reconciliation_id: str
) -> dict:
    row = conn.execute(
        RECONCILIATION_SELECT + " WHERE id = %s AND syllabus_id = %s",
        (reconciliation_id, syllabus_id),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown reconciliation {reconciliation_id!r}")
    payload = _row_payload(row)
    if payload["status"] == "pending" and payload["plan"].get("version") != PLAN_VERSION:
        baseline = _baseline_projection(conn, syllabus_id)
        current = _version_projection(
            get_syllabus_version(conn, syllabus_id, payload["base_version_id"])
        )
        plan = build_plan(baseline, current, payload["incoming"])
        conn.execute(
            "UPDATE syllabus_reconciliation SET plan = %s WHERE id = %s",
            (Jsonb(plan), reconciliation_id),
        )
        conn.commit()
        payload["plan"] = plan
        payload.update(plan)
    return payload


def create_reconciliation(
    conn: psycopg.Connection,
    syllabus_id: str,
    path: str | Path,
) -> dict:
    """Persist an incoming workbook and return its three-way review plan."""
    latest = conn.execute(
        "SELECT id, seq FROM syllabus_version WHERE syllabus_id = %s ORDER BY seq DESC LIMIT 1",
        (syllabus_id,),
    ).fetchone()
    if latest is None:
        raise LookupError(f"unknown syllabus {syllabus_id!r}")
    path = Path(path)
    body = path.read_bytes()
    sha = hashlib.sha256(body).hexdigest()
    reconciliation_id = "recon-" + hashlib.sha256(
        f"{syllabus_id}\0{latest[0]}\0{sha}".encode()
    ).hexdigest()[:20]
    existing = conn.execute(
        RECONCILIATION_SELECT + " WHERE id = %s", (reconciliation_id,)
    ).fetchone()
    if existing is not None:
        conn.commit()
        return get_reconciliation(conn, syllabus_id, reconciliation_id)

    parsed = parse_workbook(path)
    incoming = _parsed_projection(parsed)
    current = _version_projection(get_syllabus_version(conn, syllabus_id, latest[0]))
    baseline = _baseline_projection(conn, syllabus_id)
    plan = build_plan(baseline, current, incoming)
    conn.execute(
        "INSERT INTO syllabus_reconciliation"
        " (id, syllabus_id, base_version_id, input_format, file_name, file_mime,"
        "  file_sha, file_body, incoming, plan)"
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (
            reconciliation_id, syllabus_id, latest[0], parsed["format"], path.name,
            XLSX_MIME, sha, body, Jsonb(incoming), Jsonb(plan),
        ),
    )
    conn.commit()
    return get_reconciliation(conn, syllabus_id, reconciliation_id)


def _action_items(plan: dict) -> list[dict]:
    return [
        item
        for lesson in plan.get("lessons", [])
        for item in (lesson, *lesson.get("sources", []))
        if item.get("status") != "unchanged"
    ]


def _selected_projection(item: dict, choice: str, draft: dict | None) -> dict | None:
    current = copy.deepcopy(item.get("current"))
    incoming = copy.deepcopy(item.get("incoming"))
    if choice == "keep":
        return current
    if choice == "transition":
        selected = incoming
        if selected is not None and current is not None:
            selected["hidden"] = bool(current.get("hidden"))
            if item.get("kind") == "lesson":
                selected["id"] = current.get("id")
            else:
                selected["reference_id"] = current.get("reference_id")
                selected["review"] = copy.deepcopy(current.get("review") or {})
        return selected
    if choice != "custom":
        raise ValueError("invalid reconciliation decision")

    if not isinstance(draft, dict):
        raise ValueError("A versão manual deste item está vazia.")
    title = _text(draft.get("title"))
    if not title:
        raise ValueError("Toda versão manual precisa de um título.")
    anchor = current or incoming or {}
    if item.get("kind") == "lesson":
        return {
            "id": (current or {}).get("id"),
            "week": draft.get("week") if draft.get("week") not in {None, ""} else None,
            "kind": _text(draft.get("kind")) or anchor.get("kind") or "Class",
            "title": title,
            "subject": _text(draft.get("subject")) or None,
            "subjects": parse_subjects(draft.get("subjects")),
            "date": _text(draft.get("date")) or None,
            "description": _text(draft.get("description")) or None,
            "hidden": bool((current or anchor).get("hidden")),
            "fields": copy.deepcopy((current or anchor).get("fields") or {}),
            "sources": [],
        }
    scope_kind = _text(draft.get("scope_kind")) or None
    scope_value = _text(draft.get("scope_value")) or None
    if bool(scope_kind) != bool(scope_value):
        raise ValueError("Escopo manual exige tipo e valor juntos.")
    return {
        "reference_id": (current or {}).get("reference_id"),
        "source_id": (current or {}).get("source_id"),
        "title": title,
        "description": _text(draft.get("description")) or None,
        "url": _text(draft.get("url")) or None,
        "media_type": _text(draft.get("media_type")) or anchor.get("media_type") or "article",
        "resource_code": _text(draft.get("resource_code")) or None,
        "scope_kind": scope_kind,
        "scope_value": scope_value,
        "hidden": bool((current or anchor).get("hidden")),
        "fields": copy.deepcopy((current or anchor).get("fields") or {}),
        "review": copy.deepcopy((current or {}).get("review") or {}),
    }


def _projection_from_decisions(plan: dict, decisions: dict, drafts: dict) -> list[dict]:
    actions = {item["item_id"]: item for item in _action_items(plan)}
    missing = sorted(set(actions) - set(decisions))
    unknown = sorted(set(decisions) - set(actions))
    if missing:
        raise ValueError(f"Ainda existem {len(missing)} itens sem decisão.")
    if unknown:
        raise ValueError("A reconciliação contém decisões para itens desconhecidos.")
    invalid = [item_id for item_id, value in decisions.items() if value not in DECISIONS]
    if invalid:
        raise ValueError("A reconciliação contém uma decisão inválida.")

    output: list[dict] = []
    for lesson in plan.get("lessons", []):
        lesson_choice = decisions.get(lesson["item_id"], "keep")
        selected_lesson = _selected_projection(
            lesson, lesson_choice, drafts.get(lesson["item_id"])
        ) if lesson["status"] != "unchanged" else copy.deepcopy(lesson.get("current"))
        if selected_lesson is None:
            continue
        selected_sources: list[dict] = []
        for source in lesson.get("sources", []):
            source_choice = decisions.get(source["item_id"], "keep")
            selected_source = _selected_projection(
                source, source_choice, drafts.get(source["item_id"])
            ) if source["status"] != "unchanged" else copy.deepcopy(source.get("current"))
            if selected_source is not None:
                selected_sources.append(selected_source)
        selected_lesson["sources"] = selected_sources
        output.append(selected_lesson)
    return output


def apply_reconciliation(
    conn: psycopg.Connection,
    syllabus_id: str,
    reconciliation_id: str,
    decisions: object,
    drafts: object = None,
    *,
    actor: str = "founder",
) -> dict:
    """Compile all reviewed choices into the next immutable version."""
    row = conn.execute(
        RECONCILIATION_SELECT + " WHERE id = %s AND syllabus_id = %s FOR UPDATE",
        (reconciliation_id, syllabus_id),
    ).fetchone()
    if row is None:
        raise LookupError(f"unknown reconciliation {reconciliation_id!r}")
    record = _row_payload(row)
    if record["status"] == "applied":
        conn.commit()
        return {
            "syllabus_id": syllabus_id,
            "version_id": record["created_version_id"],
            "reconciliation_id": reconciliation_id,
            "unchanged": record["created_version_id"] == record["base_version_id"],
            "already_applied": True,
        }
    latest = conn.execute(
        "SELECT id FROM syllabus_version WHERE syllabus_id = %s ORDER BY seq DESC LIMIT 1",
        (syllabus_id,),
    ).fetchone()
    if latest is None or latest[0] != record["base_version_id"]:
        conn.rollback()
        raise SyllabusVersionConflict(
            "Este syllabus recebeu uma versão mais nova. Refaça a comparação antes de aplicar."
        )
    if record["plan"].get("version") != PLAN_VERSION:
        baseline = _baseline_projection(conn, syllabus_id)
        current = _version_projection(
            get_syllabus_version(conn, syllabus_id, record["base_version_id"])
        )
        record["plan"] = build_plan(baseline, current, record["incoming"])
        conn.execute(
            "UPDATE syllabus_reconciliation SET plan = %s WHERE id = %s",
            (Jsonb(record["plan"]), reconciliation_id),
        )
    if not isinstance(decisions, dict):
        raise ValueError("As decisões da reconciliação são obrigatórias.")
    if drafts is None:
        drafts = {}
    if not isinstance(drafts, dict):
        raise ValueError("As versões manuais da reconciliação são inválidas.")
    projection = _projection_from_decisions(record["plan"], decisions, drafts)
    result = curate_syllabus(
        conn,
        syllabus_id,
        record["base_version_id"],
        projection,
        actor=actor,
        note=f"Reconciliação da planilha {record['file_name']} ({reconciliation_id})",
    )
    conn.execute(
        "UPDATE syllabus_reconciliation SET status = 'applied', decisions = %s,"
        " created_version_id = %s, applied_at = now() WHERE id = %s",
        (
            Jsonb({"choices": decisions, "drafts": drafts}),
            result["version_id"],
            reconciliation_id,
        ),
    )
    conn.commit()
    return {**result, "reconciliation_id": reconciliation_id, "already_applied": False}
