"""Pure contracts for resolving chapter scopes through a reader TOC."""

from __future__ import annotations

import pytest

from universe.acquisition.book_toc import (
    BookTocError,
    ChapterSelector,
    TocEntry,
    parse_chapter_selector,
    resolve_chapter_scope_to_page_labels,
    toc_entries_from_text,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("5", ChapterSelector(5, 5)),
        ("5-7", ChapterSelector(5, 7)),
        ("5, 6, 7", ChapterSelector(5, 7)),
        ("5; 6; 7", ChapterSelector(5, 7)),
        ("chapter 5", ChapterSelector(5, 5)),
        ("cap. 5", ChapterSelector(5, 5)),
        ("chapters 5 through 7", ChapterSelector(5, 7)),
        ("capítulos 5 e 6", ChapterSelector(5, 6)),
    ],
)
def test_parse_chapter_selector_accepts_bare_and_prefixed_scopes(
    value: str, expected: ChapterSelector
):
    assert parse_chapter_selector(value) == expected


@pytest.mark.parametrize(
    "value",
    ["", "0", "7-5", "5, 7", "5, 5", "pages 5-7", "chapter five"],
)
def test_parse_chapter_selector_rejects_non_concrete_or_noncontiguous_scopes(
    value: str,
):
    assert parse_chapter_selector(value) is None


def test_parse_chapter_range_preserves_large_endpoints_without_expanding_them():
    assert parse_chapter_selector("1-1000000000") == ChapterSelector(
        1, 1_000_000_000
    )


def test_toc_entries_from_text_reads_named_numeric_and_boundary_entries():
    entries = toc_entries_from_text(
        """
        SUMÁRIO
        Capítulo 5 - Fundamentos
        101
        5.1 Conceitos iniciais 102
        Chapter 6 - Aplicações 110
        Referências
        120
        """
    )

    assert entries == (
        TocEntry(label="5", page=101, level=1),
        TocEntry(label="5.1", page=102, level=2),
        TocEntry(label="6", page=110, level=1),
        TocEntry(label="boundary:referencias", page=120, level=1),
    )


def test_resolve_chapter_scope_uses_the_next_primary_heading_as_its_boundary():
    labels = resolve_chapter_scope_to_page_labels(
        "5",
        """
        Chapter 5 Foundations 101
        5.1 First principles 102
        Chapter 6 Applications 110
        """,
    )

    assert labels == tuple(str(page) for page in range(101, 110))


@pytest.mark.parametrize("value", ["5-7", "chapters 5, 6, 7"])
def test_resolve_chapter_range_includes_every_page_through_the_end_chapter(
    value: str,
):
    labels = resolve_chapter_scope_to_page_labels(
        value,
        """
        5 Foundations 100
        6 Applications 110
        7 Worked examples 120
        8 Review 130
        """,
    )

    assert labels == tuple(str(page) for page in range(100, 130))


def test_resolve_last_chapter_uses_bibliography_as_the_terminal_boundary():
    labels = resolve_chapter_scope_to_page_labels(
        "capítulo 18",
        """
        18 Amplificador Emissor Comum Básico
        271
        Bibliografia
        289
        """,
    )

    assert labels == tuple(str(page) for page in range(271, 289))


def test_resolve_last_chapter_recognizes_an_english_bibliography_boundary():
    labels = resolve_chapter_scope_to_page_labels(
        "18",
        """
        Chapter 18 Closing argument 271
        Bibliography 289
        """,
    )

    assert labels == tuple(str(page) for page in range(271, 289))


def test_resolve_chapter_fails_when_the_toc_has_no_following_boundary():
    with pytest.raises(BookTocError) as exc_info:
        resolve_chapter_scope_to_page_labels(
            "18",
            """
            18 Amplificador Emissor Comum Básico
            271
            """,
        )

    assert exc_info.value.code == "toc_scope_end_boundary_missing"


def test_resolve_chapter_enforces_a_configurable_50_page_default_limit():
    assert resolve_chapter_scope_to_page_labels(
        "5",
        """
        5 Exactly fifty pages 100
        6 Next chapter 150
        """,
    ) == tuple(str(page) for page in range(100, 150))

    toc_text = """
    5 Long chapter 100
    6 Next chapter 151
    """

    with pytest.raises(BookTocError) as exc_info:
        resolve_chapter_scope_to_page_labels("5", toc_text)

    assert exc_info.value.code == "toc_scope_page_range_too_large"
    assert resolve_chapter_scope_to_page_labels(
        "5", toc_text, max_page_count=51
    ) == tuple(str(page) for page in range(100, 151))


def test_resolve_chapter_range_fails_when_an_endpoint_is_absent_from_the_toc():
    with pytest.raises(BookTocError) as exc_info:
        resolve_chapter_scope_to_page_labels(
            "5-7",
            """
            5 Foundations 100
            6 Applications 110
            8 Review 130
            """,
        )

    assert exc_info.value.code == "toc_scope_not_found"


def test_resolve_chapter_range_rejects_a_boundary_before_the_end_chapter_page():
    with pytest.raises(BookTocError) as exc_info:
        resolve_chapter_scope_to_page_labels(
            "5-7",
            """
            5 Foundations 100
            7 Worked examples 130
            8 Malformed boundary 120
            """,
        )

    assert exc_info.value.code == "toc_scope_invalid_page_range"


def test_resolve_chapter_rejects_conflicting_primary_chapter_entries():
    with pytest.raises(BookTocError) as exc_info:
        resolve_chapter_scope_to_page_labels(
            "5",
            """
            5 Foundations 100
            5 Conflicting duplicate 105
            6 Applications 110
            """,
        )

    assert exc_info.value.code == "toc_scope_conflict"
