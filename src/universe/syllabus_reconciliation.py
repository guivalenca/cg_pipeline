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
IDENTITY_DECISIONS = {"same", "new", "keep"}
IDENTITY_STATES = {"carried", "review", "new", "removed"}
IDENTITY_REASONS = {
    "exact_text",
    "small_text_edit",
    "subject_changed",
    "kind_changed",
    "ambiguous_match",
    "large_title_edit",
    "large_description_edit",
    "no_confident_match",
    "no_predecessor",
    "removed",
}
IDENTITY_REASONS_BY_STATE = {
    "carried": {"exact_text", "small_text_edit"},
    "review": {
        "subject_changed",
        "kind_changed",
        "ambiguous_match",
        "large_title_edit",
        "large_description_edit",
        "no_confident_match",
    },
    "new": {"no_predecessor"},
    "removed": {"removed"},
}
PLAN_VERSION = 6
AUTO_TITLE_SIMILARITY = 0.86
AUTO_DESCRIPTION_SIMILARITY = 0.80
AUTO_MATCH_MARGIN = 8.0
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
        "incoming_key": lesson.get("incoming_key"),
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
    lessons = []
    for index, lesson in enumerate(parsed.get("lessons", []), 1):
        projected = _lesson_projection(lesson, index, "source_references")
        projected["incoming_key"] = f"incoming-{index:04d}"
        lessons.append(projected)
    return {"lessons": lessons}


def _ensure_incoming_keys(projection: dict) -> dict:
    keyed = copy.deepcopy(projection)
    for index, lesson in enumerate(keyed.get("lessons") or [], 1):
        lesson["incoming_key"] = lesson.get("incoming_key") or f"incoming-{index:04d}"
    return keyed


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


def _normalized_similarity(
    a: str,
    b: str,
    *,
    empty_values_match: bool,
) -> float:
    if a == b:
        return 1.0 if a or empty_values_match else 0.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _similarity(
    left: object,
    right: object,
    *,
    empty_values_match: bool = True,
) -> float:
    return _normalized_similarity(
        _norm(left),
        _norm(right),
        empty_values_match=empty_values_match,
    )


def _plan_similarity():
    """Reuse normalized text comparisons within one reconciliation plan."""
    cache: dict[tuple[str, str, bool], float] = {}

    def compare(
        left: object,
        right: object,
        *,
        empty_values_match: bool = True,
    ) -> float:
        a, b = _norm(left), _norm(right)
        key = (a, b, empty_values_match)
        if key not in cache:
            cache[key] = _normalized_similarity(
                a,
                b,
                empty_values_match=empty_values_match,
            )
        return cache[key]

    return compare


def _lesson_score(left: dict, right: dict, *, similarity=_similarity) -> float:
    left_id, right_id = _text(left.get("id")), _text(right.get("id"))
    if left_id and left_id == right_id:
        return 1000.0
    subject_same = _norm(left.get("subject")) == _norm(right.get("subject"))
    kind_same = _norm(left.get("kind")) == _norm(right.get("kind"))
    score = similarity(left.get("title"), right.get("title")) * 55
    score += similarity(left.get("description"), right.get("description")) * 25
    score += 30 if subject_same else -30
    score += 12 if kind_same else -12
    if left.get("week") is not None and left.get("week") == right.get("week"):
        score += 12
    if left.get("seq") is not None and left.get("seq") == right.get("seq"):
        score += 8
    return score


def _lesson_pair_is_plausible(
    left: dict,
    right: dict,
    score: float,
    *,
    similarity=_similarity,
) -> bool:
    left_id, right_id = _text(left.get("id")), _text(right.get("id"))
    if left_id and left_id == right_id:
        return True
    title_similarity = similarity(left.get("title"), right.get("title"))
    description_similarity = similarity(
        left.get("description"), right.get("description")
    )
    same_position = (
        left.get("week") is not None
        and left.get("week") == right.get("week")
        and left.get("seq") is not None
        and left.get("seq") == right.get("seq")
    )
    return (
        title_similarity >= 0.45
        or (title_similarity >= 0.30 and description_similarity >= 0.45)
        or same_position
        or score >= 70
    )


def _identity_reason(
    left: dict,
    right: dict,
    *,
    automatic: bool,
    unambiguous: bool,
    similarity=_similarity,
) -> str:
    if _norm(left.get("subject")) != _norm(right.get("subject")):
        return "subject_changed"
    if _norm(left.get("kind")) != _norm(right.get("kind")):
        return "kind_changed"
    if not unambiguous:
        return "ambiguous_match"
    if automatic:
        exact = (
            _norm(left.get("title")) == _norm(right.get("title"))
            and _norm(left.get("description")) == _norm(right.get("description"))
        )
        return "exact_text" if exact else "small_text_edit"
    if similarity(left.get("title"), right.get("title")) < AUTO_TITLE_SIMILARITY:
        return "large_title_edit"
    return "large_description_edit"


def _match_lessons(
    left: list[dict], right: list[dict], *, similarity=_similarity
) -> dict[int, dict]:
    """Pair plausible Lessons and classify whether identity can carry silently."""
    candidates: list[tuple[float, int, int]] = []
    by_left: dict[int, list[tuple[float, int]]] = {}
    by_right: dict[int, list[tuple[float, int]]] = {}
    for left_index, left_item in enumerate(left):
        for right_index, right_item in enumerate(right):
            value = _lesson_score(left_item, right_item, similarity=similarity)
            if not _lesson_pair_is_plausible(
                left_item, right_item, value, similarity=similarity
            ):
                continue
            candidates.append((value, left_index, right_index))
            by_left.setdefault(left_index, []).append((value, right_index))
            by_right.setdefault(right_index, []).append((value, left_index))

    for values in (*by_left.values(), *by_right.values()):
        values.sort(reverse=True)

    result: dict[int, dict] = {}
    used_right: set[int] = set()
    for value, left_index, right_index in sorted(candidates, reverse=True):
        if left_index in result or right_index in used_right:
            continue
        left_rank = by_left[left_index]
        right_rank = by_right[right_index]
        mutual_best = (
            left_rank[0][1] == right_index and right_rank[0][1] == left_index
        )
        left_margin = value - left_rank[1][0] if len(left_rank) > 1 else float("inf")
        right_margin = value - right_rank[1][0] if len(right_rank) > 1 else float("inf")
        unambiguous = (
            mutual_best
            and left_margin >= AUTO_MATCH_MARGIN
            and right_margin >= AUTO_MATCH_MARGIN
        )
        left_item, right_item = left[left_index], right[right_index]
        same_id = (
            bool(_text(left_item.get("id")))
            and _text(left_item.get("id")) == _text(right_item.get("id"))
        )
        automatic = same_id or (
            unambiguous
            and _norm(left_item.get("subject")) == _norm(right_item.get("subject"))
            and _norm(left_item.get("kind")) == _norm(right_item.get("kind"))
            and similarity(left_item.get("title"), right_item.get("title"))
            >= AUTO_TITLE_SIMILARITY
            and similarity(
                left_item.get("description"), right_item.get("description")
            )
            >= AUTO_DESCRIPTION_SIMILARITY
        )
        result[left_index] = {
            "right_index": right_index,
            "automatic": automatic,
            "reason": _identity_reason(
                left_item,
                right_item,
                automatic=automatic,
                unambiguous=unambiguous,
                similarity=similarity,
            ),
        }
        used_right.add(right_index)
    return result


def _source_score(left: dict, right: dict) -> float:
    score = 0.0
    if _norm(left.get("title")) == _norm(right.get("title")):
        score += 100
    else:
        similarity = _similarity(
            left.get("title"), right.get("title"), empty_values_match=False
        )
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
    description_similarity = _similarity(
        left.get("description"),
        right.get("description"),
        empty_values_match=False,
    )
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


def _identity_plan(anchor: dict | None, incoming: dict | None, match: dict | None) -> dict:
    lesson_id = _text((anchor or {}).get("id")) or None
    if incoming is None:
        return {"state": "removed", "lesson_id": lesson_id, "reason": "removed"}
    if anchor is None or lesson_id is None:
        return {"state": "new", "lesson_id": None, "reason": "no_predecessor"}
    if match and match.get("automatic"):
        return {
            "state": "carried",
            "lesson_id": lesson_id,
            "reason": match["reason"],
        }
    return {
        "state": "review",
        "lesson_id": None,
        "reason": (match or {}).get("reason") or "ambiguous_match",
        "candidates": [_identity_candidate(anchor)],
    }


def _identity_candidate(lesson: dict) -> dict:
    return {
        "lesson_id": lesson.get("id"),
        "title": lesson.get("title"),
        "description": lesson.get("description"),
        "subject": lesson.get("subject"),
        "kind": lesson.get("kind"),
        "week": lesson.get("week"),
        "seq": lesson.get("seq"),
        "date": _date(lesson.get("date", lesson.get("lesson_date"))),
    }


def _validate_identity(identity: dict) -> None:
    """Validate the closed identity result sent across the HTTP seam."""
    state = identity.get("state")
    reason = identity.get("reason")
    if (
        state not in IDENTITY_STATES
        or reason not in IDENTITY_REASONS
        or reason not in IDENTITY_REASONS_BY_STATE.get(state, set())
    ):
        raise ValueError("invalid lesson identity plan")
    lesson_id = _text(identity.get("lesson_id"))
    candidates = identity.get("candidates")
    allowed_keys = {"state", "lesson_id", "reason"}
    if state == "review":
        allowed_keys.add("candidates")
    if set(identity) != allowed_keys:
        raise ValueError("lesson identity plan has invalid fields")
    if state in {"carried", "removed"} and not lesson_id:
        raise ValueError("resolved lesson identity is missing its id")
    if state == "review":
        if lesson_id or not isinstance(candidates, list) or not candidates:
            raise ValueError("reviewable lesson identity needs candidates")
        candidate_keys = {
            "lesson_id",
            "title",
            "description",
            "subject",
            "kind",
            "week",
            "seq",
            "date",
        }
        if any(
            not isinstance(candidate, dict) or set(candidate) != candidate_keys
            for candidate in candidates
        ):
            raise ValueError("reviewable lesson identity candidate shape is invalid")
        candidate_ids = [_text(candidate.get("lesson_id")) for candidate in candidates]
        if not all(candidate_ids) or len(candidate_ids) != len(set(candidate_ids)):
            raise ValueError("reviewable lesson identity candidates are invalid")
    elif state == "new" and lesson_id:
        raise ValueError("new lesson identity cannot have an existing id")
    elif candidates is not None:
        raise ValueError("resolved lesson identity cannot include candidates")


def _enrich_identity_reviews(
    lesson_plans: list[dict], current_lessons: list[dict], *, similarity=_similarity
) -> None:
    """Offer every unreserved stable Lesson when automation is not safe.

    The matcher chooses a primary pair for the content comparison. Identity is
    more conservative: a founder can select any previous Lesson that was not
    already carried automatically, or explicitly create a new identity.
    """
    reserved_ids = {
        _text((lesson.get("identity") or {}).get("lesson_id"))
        for lesson in lesson_plans
        if (lesson.get("identity") or {}).get("state") == "carried"
    }
    available = {
        _text(lesson.get("id")): lesson
        for lesson in current_lessons
        if _text(lesson.get("id")) and _text(lesson.get("id")) not in reserved_ids
    }
    for lesson in lesson_plans:
        identity = lesson.get("identity") or {}
        if identity.get("state") not in {"review", "new"}:
            _validate_identity(identity)
            continue
        incoming = lesson.get("incoming") or {}
        primary_ids = [
            _text(candidate.get("lesson_id"))
            for candidate in identity.get("candidates") or []
        ]
        ranked = sorted(
            available.values(),
            key=lambda candidate: (
                _text(candidate.get("id")) not in primary_ids,
                -_lesson_score(candidate, incoming, similarity=similarity),
                candidate.get("seq") or 10**9,
                _norm(candidate.get("title")),
            ),
        )
        if identity.get("state") == "new" and ranked:
            identity = {
                "state": "review",
                "lesson_id": None,
                "reason": "no_confident_match",
            }
            lesson["identity"] = identity
        if identity.get("state") == "review":
            identity["candidates"] = [_identity_candidate(candidate) for candidate in ranked]
        _validate_identity(identity)


def build_plan(baseline: dict, current: dict, incoming: dict) -> dict:
    """Build one deterministic lesson/source reconciliation tree."""
    base_lessons = list(baseline.get("lessons") or [])
    current_lessons = list(current.get("lessons") or [])
    incoming_lessons = list(incoming.get("lessons") or [])
    lesson_similarity = _plan_similarity()
    base_current = _match_lessons(
        base_lessons, current_lessons, similarity=lesson_similarity
    )
    base_incoming = _match_lessons(
        base_lessons, incoming_lessons, similarity=lesson_similarity
    )
    used_current = {match["right_index"] for match in base_current.values()}
    used_incoming = {match["right_index"] for match in base_incoming.values()}
    lesson_plans: list[dict] = []

    for baseline_index, base_lesson in enumerate(base_lessons):
        current_match = base_current.get(baseline_index)
        incoming_match = base_incoming.get(baseline_index)
        current_lesson = (
            current_lessons[current_match["right_index"]] if current_match else None
        )
        incoming_lesson = (
            incoming_lessons[incoming_match["right_index"]]
            if incoming_match
            else None
        )
        merged_lesson = _three_way_incoming(
            base_lesson, current_lesson, incoming_lesson, LESSON_AUTHORED_FIELDS
        )
        lesson_status = _status(
            base_lesson, current_lesson, incoming_lesson, _lesson_signature, merged_lesson
        )
        if lesson_status == "unchanged" and current_lesson is None:
            continue
        lesson_plans.append(
            {
                "kind": "lesson",
                "status": lesson_status,
                "order": (incoming_lesson or current_lesson or base_lesson).get("seq"),
                "incoming_key": (incoming_lesson or {}).get("incoming_key"),
                "identity": _identity_plan(
                    current_lesson or base_lesson, incoming_lesson, incoming_match
                ),
                "current": copy.deepcopy(current_lesson),
                "incoming": _effective_incoming(
                    lesson_status, current_lesson, incoming_lesson, merged_lesson
                ),
                "sources": _build_source_plans(
                    base_lesson.get("sources") or [],
                    (current_lesson or {}).get("sources") or [],
                    (incoming_lesson or {}).get("sources") or [],
                ),
            }
        )

    unmatched_current = [
        item for index, item in enumerate(current_lessons) if index not in used_current
    ]
    unmatched_incoming = [
        item for index, item in enumerate(incoming_lessons) if index not in used_incoming
    ]
    local_matches = _match_lessons(
        unmatched_current, unmatched_incoming, similarity=lesson_similarity
    )
    matched_incoming = {match["right_index"] for match in local_matches.values()}
    for current_index, current_lesson in enumerate(unmatched_current):
        local_match = local_matches.get(current_index)
        incoming_lesson = (
            unmatched_incoming[local_match["right_index"]] if local_match else None
        )
        exact = (
            incoming_lesson is not None
            and _lesson_signature(current_lesson) == _lesson_signature(incoming_lesson)
        )
        lesson_status = "unchanged" if exact or incoming_lesson is None else "added"
        lesson_plans.append(
            {
                "kind": "lesson",
                "status": lesson_status,
                "order": (incoming_lesson or current_lesson).get("seq"),
                "incoming_key": (incoming_lesson or {}).get("incoming_key"),
                "identity": _identity_plan(
                    current_lesson, incoming_lesson, local_match
                ),
                "current": copy.deepcopy(current_lesson),
                "incoming": copy.deepcopy(
                    current_lesson if lesson_status == "unchanged" else incoming_lesson
                ),
                "sources": _build_source_plans(
                    [],
                    current_lesson.get("sources") or [],
                    (incoming_lesson or {}).get("sources") or [],
                ),
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
                "incoming_key": incoming_lesson.get("incoming_key"),
                "identity": _identity_plan(None, incoming_lesson, None),
                "current": None,
                "incoming": copy.deepcopy(incoming_lesson),
                "sources": _build_source_plans(
                    [], [], incoming_lesson.get("sources") or []
                ),
            }
        )

    _enrich_identity_reviews(
        lesson_plans, current_lessons, similarity=lesson_similarity
    )
    lesson_plans.sort(
        key=lambda item: (
            (item.get("incoming") or item.get("current") or {}).get("week") or 10**9,
            item.get("order") or 10**9,
        )
    )
    action_count = 0
    identity_action_count = 0
    automatic_identity_count = 0
    unchanged_source_count = 0
    unchanged_lesson_count = 0
    inherited_settings = 0
    for lesson_index, lesson in enumerate(lesson_plans, 1):
        lesson["item_id"] = f"lesson-{lesson_index:04d}"
        if lesson["status"] == "unchanged":
            unchanged_lesson_count += 1
        else:
            action_count += 1
        if lesson["identity"]["state"] == "review":
            identity_action_count += 1
        elif lesson["identity"]["state"] == "carried":
            automatic_identity_count += 1
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
        or lesson["identity"]["state"] == "review"
        or any(source["status"] != "unchanged" for source in lesson["sources"])
    )
    return {
        "version": PLAN_VERSION,
        "lessons": lesson_plans,
        "summary": {
            "lesson_count": len(incoming_lessons),
            "source_count": sum(
                len(lesson.get("sources") or []) for lesson in incoming_lessons
            ),
            "unchanged_lesson_count": unchanged_lesson_count,
            "unchanged_source_count": unchanged_source_count,
            "changed_lesson_count": changed_lessons,
            "action_count": action_count,
            "identity_action_count": identity_action_count,
            "automatic_identity_count": automatic_identity_count,
            "inherited_settings": inherited_settings,
        },
    }


def _baseline_projection(conn: psycopg.Connection, syllabus_id: str) -> dict:
    applied = conn.execute(
        "SELECT incoming, decisions FROM syllabus_reconciliation"
        " WHERE syllabus_id = %s AND status = 'applied'"
        " ORDER BY applied_at DESC, id DESC LIMIT 1",
        (syllabus_id,),
    ).fetchone()
    if applied is not None:
        decisions = dict(applied[1] or {})
        accepted = decisions.get("accepted_incoming") or applied[0]
        return _ensure_incoming_keys(dict(accepted))
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
        payload["incoming"] = _ensure_incoming_keys(payload["incoming"])
        baseline = _baseline_projection(conn, syllabus_id)
        current = _version_projection(
            get_syllabus_version(conn, syllabus_id, payload["base_version_id"])
        )
        plan = build_plan(baseline, current, payload["incoming"])
        conn.execute(
            "UPDATE syllabus_reconciliation SET incoming = %s, plan = %s WHERE id = %s",
            (Jsonb(payload["incoming"]), Jsonb(plan), reconciliation_id),
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


def _identity_action_items(plan: dict) -> list[dict]:
    return [
        lesson
        for lesson in plan.get("lessons", [])
        if (lesson.get("identity") or {}).get("state") == "review"
    ]


_LESSON_ID_UNSET = object()


def _selected_projection(
    item: dict,
    choice: str,
    draft: dict | None,
    *,
    lesson_id: object = _LESSON_ID_UNSET,
) -> dict | None:
    current = copy.deepcopy(item.get("current"))
    incoming = copy.deepcopy(item.get("incoming"))
    if choice == "keep":
        if (
            current is not None
            and item.get("kind") == "lesson"
            and lesson_id is not _LESSON_ID_UNSET
        ):
            current["id"] = lesson_id
        return current
    if choice == "transition":
        selected = incoming
        if selected is not None:
            if current is not None:
                selected["hidden"] = bool(current.get("hidden"))
            if item.get("kind") == "lesson":
                if lesson_id is not _LESSON_ID_UNSET:
                    selected["id"] = lesson_id
                elif current is not None:
                    selected["id"] = current.get("id")
            elif current is not None:
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
            "id": (
                (current or {}).get("id")
                if lesson_id is _LESSON_ID_UNSET
                else lesson_id
            ),
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


def _validated_identity_decisions(
    plan: dict,
    decisions: object,
    content_decisions: object = None,
) -> dict:
    if decisions is None:
        decisions = {}
    if not isinstance(decisions, dict):
        raise ValueError("As decisões de identidade das aulas são inválidas.")
    if content_decisions is None:
        content_decisions = {}
    if not isinstance(content_decisions, dict):
        raise ValueError("As decisões da reconciliação são inválidas.")
    lessons = {
        lesson["item_id"]: lesson for lesson in plan.get("lessons", [])
    }
    actions = {
        item["item_id"]: item for item in _identity_action_items(plan)
    }
    actions.update(
        {
            item_id: lessons[item_id]
            for item_id, choice in content_decisions.items()
            if choice == "custom" and item_id in lessons
        }
    )
    missing = sorted(set(actions) - set(decisions))
    unknown = sorted(set(decisions) - set(actions))
    if missing:
        raise ValueError(
            f"Ainda existem {len(missing)} identidades de aula sem decisão."
        )
    if unknown:
        raise ValueError("A reconciliação contém identidades de aula desconhecidas.")
    normalized = {}
    selected_ids = [
        _text((lessons[item_id].get("current") or {}).get("id"))
        for item_id, choice in content_decisions.items()
        if choice == "keep"
        and item_id in lessons
        and _text((lessons[item_id].get("current") or {}).get("id"))
    ]
    for item_id, value in decisions.items():
        if not isinstance(value, dict) or value.get("choice") not in IDENTITY_DECISIONS:
            raise ValueError("A reconciliação contém uma decisão de identidade inválida.")
        choice = value["choice"]
        item = actions[item_id]
        identity = item.get("identity") or {}
        content_choice = content_decisions.get(item_id)
        if choice == "keep":
            if (
                set(value) != {"choice"}
                or identity.get("state") != "review"
                or (
                    item.get("status") != "unchanged"
                    and content_choice != "keep"
                )
            ):
                raise ValueError(
                    "Manter uma aula exige manter também seu conteúdo atual."
                )
            normalized[item_id] = {"choice": "keep"}
            current_id = _text((item.get("current") or {}).get("id"))
            if current_id and content_choice != "keep":
                selected_ids.append(current_id)
            continue
        if item.get("status") != "unchanged" and content_choice == "keep":
            raise ValueError(
                "Uma aula mantida não pode receber outra decisão de identidade."
            )
        if choice == "new":
            if set(value) != {"choice"}:
                raise ValueError("A decisão de nova aula contém dados inválidos.")
            normalized[item_id] = {"choice": "new"}
            continue
        lesson_id = _text(value.get("lesson_id"))
        candidate_ids = {
            _text(candidate.get("lesson_id"))
            for candidate in identity.get("candidates", [])
        }
        if identity.get("state") == "carried":
            candidate_ids.add(_text(identity.get("lesson_id")))
        if identity.get("state") == "removed":
            candidate_ids.add(_text((item.get("current") or {}).get("id")))
        candidate_ids.discard("")
        if set(value) != {"choice", "lesson_id"} or lesson_id not in candidate_ids:
            raise ValueError("A aula anterior escolhida não é uma candidata válida.")
        normalized[item_id] = {"choice": "same", "lesson_id": lesson_id}
        selected_ids.append(lesson_id)
    if len(selected_ids) != len(set(selected_ids)):
        raise ValueError("Uma aula anterior não pode continuar como duas aulas diferentes.")
    return normalized


def _resolved_identity(lesson: dict, identity_decisions: dict) -> tuple[str | None, str]:
    identity = lesson.get("identity") or {}
    state = identity.get("state")
    decision = identity_decisions.get(lesson["item_id"])
    if decision is not None:
        if decision["choice"] == "keep":
            return _text((lesson.get("current") or {}).get("id")) or None, "founder_kept_current"
        if decision["choice"] == "same":
            return decision["lesson_id"], "founder_same"
        return None, "founder_new"
    if state == "carried":
        return identity.get("lesson_id"), "automatic_same"
    if state == "review":
        raise ValueError("A identidade desta aula ainda não foi decidida.")
    if state == "new":
        return None, "automatic_new"
    return identity.get("lesson_id"), "removed"


def _projection_from_decisions(
    plan: dict,
    decisions: dict,
    drafts: dict,
    identity_decisions: dict,
) -> list[dict]:
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

    claimed_ids = {
        value["lesson_id"]: item_id
        for item_id, value in identity_decisions.items()
        if value["choice"] == "same"
    }
    output: list[dict] = []
    for lesson in plan.get("lessons", []):
        resolved_id, identity_outcome = _resolved_identity(
            lesson, identity_decisions
        )
        lesson_choice = decisions.get(lesson["item_id"], "keep")
        current = lesson.get("current") or {}
        current_id = _text(current.get("id")) or None
        displaced = bool(
            current_id
            and current_id in claimed_ids
            and claimed_ids[current_id] != lesson["item_id"]
        )
        if (
            identity_outcome == "founder_same"
            and current_id
            and current_id != resolved_id
            and not displaced
        ):
            preserved = copy.deepcopy(current)
            preserved["_incoming_key"] = None
            preserved["_maps_incoming_identity"] = False
            preserved["_identity_outcome"] = "preserved_after_reassignment"
            output.append(preserved)
        if lesson["status"] != "unchanged":
            keep_identity = (
                resolved_id
                if identity_outcome == "founder_same"
                else _LESSON_ID_UNSET
            )
            selected_lesson = _selected_projection(
                lesson,
                lesson_choice,
                drafts.get(lesson["item_id"]),
                lesson_id=(keep_identity if lesson_choice == "keep" else resolved_id),
            )
        elif identity_outcome == "founder_new":
            selected_lesson = _selected_projection(
                lesson, "transition", None, lesson_id=None
            )
        else:
            selected_lesson = copy.deepcopy(lesson.get("current"))
            if selected_lesson is not None and identity_outcome == "founder_same":
                selected_lesson["id"] = resolved_id
        if displaced and lesson_choice == "keep":
            selected_lesson = None
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
        incoming_key = lesson.get("incoming_key")
        maps_incoming = bool(incoming_key) and (
            identity_outcome
            in {"automatic_same", "founder_same", "founder_kept_current"}
            or lesson_choice in {"transition", "custom"}
            or lesson["status"] == "unchanged"
        )
        selected_lesson["_incoming_key"] = incoming_key
        selected_lesson["_maps_incoming_identity"] = maps_incoming
        selected_lesson["_identity_outcome"] = identity_outcome
        output.append(selected_lesson)
    stable_ids = [_text(lesson.get("id")) for lesson in output if lesson.get("id")]
    if len(stable_ids) != len(set(stable_ids)):
        raise ValueError("A reconciliação tentou reutilizar o mesmo ID de aula duas vezes.")
    return output


def _accepted_incoming(
    incoming: dict,
    plan: dict,
    projection: list[dict],
    created: dict,
) -> tuple[dict, dict]:
    ids_by_key: dict[str, str] = {}
    for selected, stored in zip(projection, created.get("lessons", []), strict=True):
        incoming_key = selected.get("_incoming_key")
        if incoming_key and selected.get("_maps_incoming_identity"):
            ids_by_key[incoming_key] = stored["id"]

    accepted = _ensure_incoming_keys(incoming)
    for lesson in accepted.get("lessons", []):
        lesson["id"] = ids_by_key.get(lesson.get("incoming_key"))

    outcomes = {}
    for lesson in plan.get("lessons", []):
        incoming_key = lesson.get("incoming_key")
        if not incoming_key:
            continue
        outcomes[incoming_key] = {
            "outcome": next(
                (
                    selected.get("_identity_outcome")
                    for selected in projection
                    if selected.get("_incoming_key") == incoming_key
                ),
                (
                    "automatic_new"
                    if (lesson.get("identity") or {}).get("state") == "new"
                    else "not_applied"
                ),
            ),
            "lesson_id": ids_by_key.get(incoming_key),
            "reason": (lesson.get("identity") or {}).get("reason"),
        }
    return accepted, outcomes


def apply_reconciliation(
    conn: psycopg.Connection,
    syllabus_id: str,
    reconciliation_id: str,
    decisions: object,
    drafts: object = None,
    identity_decisions: object = None,
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
        record["incoming"] = _ensure_incoming_keys(record["incoming"])
        baseline = _baseline_projection(conn, syllabus_id)
        current = _version_projection(
            get_syllabus_version(conn, syllabus_id, record["base_version_id"])
        )
        record["plan"] = build_plan(baseline, current, record["incoming"])
        conn.execute(
            "UPDATE syllabus_reconciliation SET incoming = %s, plan = %s WHERE id = %s",
            (Jsonb(record["incoming"]), Jsonb(record["plan"]), reconciliation_id),
        )
    if not isinstance(decisions, dict):
        raise ValueError("As decisões da reconciliação são obrigatórias.")
    if drafts is None:
        drafts = {}
    if not isinstance(drafts, dict):
        raise ValueError("As versões manuais da reconciliação são inválidas.")
    identity_decisions = _validated_identity_decisions(
        record["plan"], identity_decisions, decisions
    )
    projection = _projection_from_decisions(
        record["plan"], decisions, drafts, identity_decisions
    )
    result = curate_syllabus(
        conn,
        syllabus_id,
        record["base_version_id"],
        projection,
        actor=actor,
        note=f"Reconciliação da planilha {record['file_name']} ({reconciliation_id})",
    )
    created = get_syllabus_version(conn, syllabus_id, result["version_id"])
    accepted_incoming, identity_outcomes = _accepted_incoming(
        record["incoming"], record["plan"], projection, created
    )
    conn.execute(
        "UPDATE syllabus_reconciliation SET status = 'applied', decisions = %s,"
        " created_version_id = %s, applied_at = now() WHERE id = %s",
        (
            Jsonb(
                {
                    "choices": decisions,
                    "drafts": drafts,
                    "identities": identity_decisions,
                    "identity_outcomes": identity_outcomes,
                    "accepted_incoming": accepted_incoming,
                }
            ),
            result["version_id"],
            reconciliation_id,
        ),
    )
    conn.commit()
    return {**result, "reconciliation_id": reconciliation_id, "already_applied": False}
