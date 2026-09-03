"""Pure chapter-scope resolution against reader table-of-contents text."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


_DASHES = str.maketrans({dash: "-" for dash in "‐‑‒–—−"})
_PREFIX = re.compile(
    r"^(?:chapters?|chap\.?|cap\.?|capitulos?)\s+", re.IGNORECASE
)
DEFAULT_MAX_PAGE_COUNT = 50


class BookTocError(ValueError):
    """A chapter scope cannot be resolved safely from the supplied TOC."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class ChapterSelector:
    """Inclusive, contiguous chapter selection."""

    start: int
    end: int


@dataclass(frozen=True)
class TocEntry:
    """One numbered heading or terminal boundary exposed by a reader TOC."""

    label: str
    page: int
    level: int


def parse_chapter_selector(value: str) -> ChapterSelector | None:
    """Parse a bare or chapter-prefixed selector into inclusive endpoints."""
    text = _ascii_fold(str(value or "")).lower().translate(_DASHES).strip()
    text = _PREFIX.sub("", text).strip()
    if not text:
        return None

    if re.fullmatch(r"[0-9]+", text):
        chapters = [int(text)]
    else:
        range_match = re.fullmatch(
            r"([0-9]+)\s*(?:-|to|through|ate|a)\s*([0-9]+)", text
        )
        if range_match:
            start, end = map(int, range_match.groups())
            if start <= 0 or end < start:
                return None
            return ChapterSelector(start, end)
        elif re.fullmatch(r"[0-9]+(?:\s*(?:,|;|e|and)\s*[0-9]+)+", text):
            chapters = [
                int(part)
                for part in re.split(r"\s*(?:,|;|e|and)\s*", text)
            ]
        else:
            return None

    if not chapters or chapters[0] <= 0:
        return None
    if any(right != left + 1 for left, right in zip(chapters, chapters[1:])):
        return None
    return ChapterSelector(chapters[0], chapters[-1])


def toc_entries_from_text(text: str) -> tuple[TocEntry, ...]:
    """Extract ordered chapter, section, and terminal-boundary entries."""
    lines = [_collapse_spaces(line) for line in str(text or "").splitlines()]
    lines = [line for line in lines if line]
    entries: list[TocEntry] = []
    seen: set[tuple[str, int]] = set()
    for index, line in enumerate(lines):
        label = _toc_label_from_line(line) or _toc_boundary_label_from_line(line)
        if not label:
            continue
        page = _toc_page_on_line(line)
        if page is None:
            page = _toc_page_after_line(lines, index)
        if page is None or (label, page) in seen:
            continue
        seen.add((label, page))
        entries.append(TocEntry(label, page, label.count(".") + 1))
    return tuple(entries)


def resolve_chapter_scope_to_page_labels(
    value: str,
    toc_text: str,
    *,
    max_page_count: int = DEFAULT_MAX_PAGE_COUNT,
) -> tuple[str, ...]:
    """Resolve an inclusive chapter selector to bounded printed-page labels."""
    selector = parse_chapter_selector(value)
    if selector is None:
        raise BookTocError(
            "toc_scope_not_parseable",
            f"Chapter scope is not a concrete contiguous selector: {value}",
        )
    if (
        not isinstance(max_page_count, int)
        or isinstance(max_page_count, bool)
        or max_page_count <= 0
    ):
        raise ValueError("max_page_count must be a positive integer")

    entries = toc_entries_from_text(toc_text)
    conflicting_label = _conflicting_primary_label(entries)
    if conflicting_label is not None:
        raise BookTocError(
            "toc_scope_conflict",
            f"Reader table of contents maps chapter {conflicting_label} to multiple pages",
        )
    start_index = _primary_entry_index(entries, selector.start)
    end_index = _primary_entry_index(entries, selector.end)
    if start_index is None or end_index is None:
        missing = selector.start if start_index is None else selector.end
        raise BookTocError(
            "toc_scope_not_found",
            f"Reader table of contents does not contain chapter {missing}",
        )
    if end_index < start_index:
        raise BookTocError(
            "toc_scope_invalid_order",
            "Reader table of contents lists the selected chapter end before its start",
        )

    boundary = next(
        (entry for entry in entries[end_index + 1 :] if entry.level == 1),
        None,
    )
    if boundary is None:
        raise BookTocError(
            "toc_scope_end_boundary_missing",
            f"Reader table of contents has no end boundary after chapter {selector.end}",
        )

    start_page = entries[start_index].page
    end_chapter_page = entries[end_index].page
    end_page = boundary.page - 1
    if (
        start_page <= 0
        or end_chapter_page < start_page
        or boundary.page <= end_chapter_page
    ):
        raise BookTocError(
            "toc_scope_invalid_page_range",
            f"Reader table of contents resolves to invalid pages {start_page}-{end_page}",
        )
    page_count = end_page - start_page + 1
    if page_count > max_page_count:
        raise BookTocError(
            "toc_scope_page_range_too_large",
            f"Reader table of contents resolves to {page_count} pages; maximum is {max_page_count}",
        )
    return tuple(str(page) for page in range(start_page, end_page + 1))


def _primary_entry_index(entries: tuple[TocEntry, ...], chapter: int) -> int | None:
    label = str(chapter)
    return next(
        (
            index
            for index, entry in enumerate(entries)
            if entry.level == 1 and entry.label == label
        ),
        None,
    )


def _conflicting_primary_label(entries: tuple[TocEntry, ...]) -> str | None:
    pages_by_label: dict[str, int] = {}
    for entry in entries:
        if entry.level != 1 or not entry.label.isdigit():
            continue
        previous_page = pages_by_label.setdefault(entry.label, entry.page)
        if previous_page != entry.page:
            return entry.label
    return None


def _collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _normalize_toc_label(value: str) -> str:
    parts = [part for part in value.strip().strip(".").split(".") if part]
    if not parts or any(not part.isdigit() for part in parts):
        return ""
    return ".".join(str(int(part)) for part in parts)


def _toc_label_from_line(line: str) -> str:
    folded = _ascii_fold(line)
    chapter_match = re.match(
        r"^(?:capitulo|chapter|chap\.?)\s+(?P<label>[0-9]+)\b",
        folded,
        flags=re.IGNORECASE,
    )
    if chapter_match:
        return _normalize_toc_label(chapter_match.group("label"))
    numbered_match = re.match(
        r"^(?P<label>[0-9]+(?:\.[0-9]+)*)(?:\.)?\s+[^0-9\s]",
        folded,
    )
    if not numbered_match:
        return ""
    return _normalize_toc_label(numbered_match.group("label"))


def _toc_boundary_label_from_line(line: str) -> str:
    folded = _ascii_fold(line).lower()
    match = re.match(
        r"^(bibliografia|bibliography|referencias|references)\b", folded
    )
    if not match:
        return ""
    return f"boundary:{match.group(1)}"


def _toc_page_on_line(line: str) -> int | None:
    folded = _ascii_fold(line)
    if _toc_boundary_label_from_line(line):
        boundary_page = re.search(r"\s([0-9]{1,4})$", folded)
        return int(boundary_page.group(1)) if boundary_page else None
    match = re.match(
        r"^(?:[0-9]+(?:\.[0-9]+)*(?:\.)?"
        r"|(?:capitulo|chapter|chap\.?)\s+[0-9]+"
        r")\s+\S.*\s(?P<page>[0-9]{1,4})$",
        folded,
        flags=re.IGNORECASE,
    )
    return int(match.group("page")) if match else None


def _toc_page_after_line(lines: list[str], index: int) -> int | None:
    for candidate in lines[index + 1 : index + 5]:
        if _toc_label_from_line(candidate) or _toc_boundary_label_from_line(candidate):
            return None
        if re.fullmatch(r"[0-9]{1,4}", candidate):
            return int(candidate)
    return None


def _ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")
