"""Blocker tests. The split is pure, so most of this needs no database."""

import pytest

from universe import blocks
from universe.blocks import BLOCKER_VERSION, split_blocks

SYNTHETIC = """---
id: "1"
title: "Every kind"
---

# A heading

An opening paragraph that runs
across two lines.

## Second heading

![alt text](https://example.invalid/a.png)

[Image: A captioned figure](https://example.invalid/b.png)

Image summary: our ingestion's description of a figure, not the author's prose.

- first item
- second item
  continued under the marker
* third item

1. numbered one
2) numbered two

> quoted line one
> quoted line two

| a | b |
| - | - |
| 1 | 2 |

```python
print("hello")
# not a heading, it is inside the fence

- not a list item either
```

A closing paragraph.
"""


def kinds(body: str) -> list[str]:
    return [block.kind for block in split_blocks(body)]


def texts(body: str, kind: str) -> list[str]:
    return [block.text for block in split_blocks(body) if block.kind == kind]


def test_every_kind_appears_in_the_order_it_is_written():
    assert kinds(SYNTHETIC) == [
        "heading",
        "paragraph",
        "heading",
        "image",
        "image",
        "list_item",
        "list_item",
        "list_item",
        "list_item",
        "list_item",
        "blockquote",
        "table",
        "code_block",
        "paragraph",
    ]


def test_front_matter_is_skipped_entirely():
    first = split_blocks(SYNTHETIC)[0]
    assert first.text == "# A heading"
    assert SYNTHETIC[: first.start_char].strip().endswith("---")
    assert all('title: "Every kind"' not in block.text for block in split_blocks(SYNTHETIC))


def test_front_matter_that_never_closes_is_not_front_matter():
    body = "---\nid: 1\n\nA paragraph.\n"
    assert [block.text for block in split_blocks(body)] == ["---\nid: 1", "A paragraph."]


def test_a_document_with_no_front_matter_starts_at_the_first_line():
    assert kinds("# Title\n\nText.\n") == ["heading", "paragraph"]


def test_each_list_item_is_its_own_block_with_its_continuation():
    items = texts(SYNTHETIC, "list_item")
    assert items[0] == "- first item"
    assert items[1] == "- second item\n  continued under the marker"
    assert items[2] == "* third item"
    assert items[3] == "1. numbered one"
    assert items[4] == "2) numbered two"


def test_a_nested_list_item_is_a_block_of_its_own():
    body = "- outer\n  - inner\n"
    assert [(b.kind, b.text) for b in split_blocks(body)] == [
        ("list_item", "- outer"),
        ("list_item", "  - inner"),
    ]


def test_a_code_block_swallows_markers_and_blank_lines():
    code = texts(SYNTHETIC, "code_block")[0]
    assert code.startswith("```python") and code.endswith("```")
    assert "# not a heading" in code and "- not a list item either" in code
    assert "\n\n" in code


def test_an_unclosed_code_block_runs_to_the_end_of_the_document():
    body = "Intro.\n\n```\nstill code\n\n# still code\n"
    result = split_blocks(body)
    assert [block.kind for block in result] == ["paragraph", "code_block"]
    assert result[1].text == "```\nstill code\n\n# still code"


def test_a_table_and_a_blockquote_are_each_one_block():
    assert texts(SYNTHETIC, "table") == ["| a | b |\n| - | - |\n| 1 | 2 |"]
    assert texts(SYNTHETIC, "blockquote") == ["> quoted line one\n> quoted line two"]


def test_image_only_paragraphs_are_images_and_prose_about_images_is_not():
    assert texts(SYNTHETIC, "image") == [
        "![alt text](https://example.invalid/a.png)",
        "[Image: A captioned figure](https://example.invalid/b.png)\n\n"
        "Image summary: our ingestion's description of a figure, not the author's prose.",
    ]
    images = [block for block in split_blocks(SYNTHETIC) if block.kind == "image"]
    assert [block.image_state for block in images] == ["unresolved", "enriched"]


def test_an_ingestion_image_summary_is_part_of_the_image_atom():
    assert texts(SYNTHETIC, "image_summary") == []
    assert "Image summary:" in texts(SYNTHETIC, "image")[1]

    # A summary without an image is still addressable instead of being lost.
    orphan = "Image summary: an orphaned legacy description.\n"
    assert kinds(orphan) == ["image_summary"]
    assert texts(orphan, "image_summary") == [orphan.rstrip()]
    # Prose that merely mentions the prefix mid-sentence stays a paragraph.
    body = "The words Image summary: appear here mid-thought.\n"
    assert kinds(body) == ["paragraph"]


def test_visual_fields_and_wrapped_descriptions_stay_in_one_enriched_atom():
    body = (
        "![Chart](https://example.invalid/chart.png)\n\n"
        "Image summary: A chart compares two systems across\n"
        "three dimensions.\n\n"
        "Visible text: System A; System B\n\n"
        "Following prose.\n"
    )

    result = split_blocks(body)

    assert [block.kind for block in result] == ["image", "paragraph"]
    assert result[0].image_state == "enriched"
    assert "three dimensions." in result[0].text
    assert "Visible text:" in result[0].text
    assert result[1].text == "Following prose."


def test_linked_and_explicitly_unresolved_images_are_protected_atoms():
    linked = "[![Diagram](https://example.invalid/a.png)](https://example.invalid/full)\n"
    explicit = (
        "![Unavailable](https://example.invalid/b.png)\n\n"
        "Image analysis: unresolved because the source asset was unavailable.\n"
    )

    assert split_blocks(linked)[0].image_state == "unresolved"
    unresolved = split_blocks(explicit)
    assert len(unresolved) == 1
    assert unresolved[0].kind == "image"
    assert unresolved[0].image_state == "unresolved"


def test_a_paragraph_stops_at_the_next_block_start():
    body = "Some prose\n# heading right after\n"
    assert [(b.kind, b.text) for b in split_blocks(body)] == [
        ("paragraph", "Some prose"),
        ("heading", "# heading right after"),
    ]


def test_an_empty_or_blank_body_yields_nothing():
    assert split_blocks("") == []
    assert split_blocks("\n\n   \n") == []
    assert split_blocks("---\ntitle: x\n---\n") == []


@pytest.mark.parametrize(
    "body",
    [SYNTHETIC, "", "\n\n", "# only\n", "```\nunclosed", "- a\n- b\n", "text without newline"],
)
def test_every_block_is_its_own_slice_and_nothing_is_lost(body):
    result = split_blocks(body)  # split_blocks asserts the invariants itself
    assert all(body[b.start_char : b.end_char] == b.text for b in result)

    # Ordered and non-overlapping.
    offsets = [(block.start_char, block.end_char) for block in result]
    assert offsets == sorted(offsets)
    assert all(a[1] <= b[0] for a, b in zip(offsets, offsets[1:]))

    # Nothing but whitespace outside the blocks, once the front matter is past.
    previous = result[0].start_char if result else 0
    for block in result:
        assert not body[previous : block.start_char].strip()
        previous = block.end_char
    assert not body[previous:].strip()


# --- the ledger -------------------------------------------------------------


@pytest.fixture(scope="module")
def blocked_artifact(db) -> str:
    """A source of the blocker's own, independent of the fixture backfill."""
    source_id = "blocks-src-1"
    snapshot_id = f"{source_id}:snap:test"
    artifact_id = f"{snapshot_id}:markdown"
    db.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, '{\"kind\": \"test\"}', 'Blocker lesson', 'article')"
        " ON CONFLICT DO NOTHING",
        (source_id,),
    )
    db.execute(
        "INSERT INTO source_snapshot (id, source_id, content_hash, status)"
        " VALUES (%s, %s, 'deadbeef', 'ok') ON CONFLICT DO NOTHING",
        (snapshot_id, source_id),
    )
    db.execute(
        "INSERT INTO artifact (id, snapshot_id, kind, tool, body)"
        " VALUES (%s, %s, 'markdown', 'test', %s) ON CONFLICT DO NOTHING",
        (artifact_id, snapshot_id, SYNTHETIC),
    )
    db.commit()
    return artifact_id


def test_storing_writes_every_block_once_and_never_again(db, blocked_artifact):
    body = blocks.fetch_body(db, blocked_artifact)
    assert body == SYNTHETIC
    expected = split_blocks(body)

    assert blocks.store_blocks(db, blocked_artifact, expected) == len(expected)
    assert blocks.store_blocks(db, blocked_artifact, expected) == 0  # insert-only ledger
    assert blocks.count_blocks(db, blocked_artifact) == len(expected)

    stored = blocks.fetch_blocks(db, blocked_artifact)
    assert [row["seq"] for row in stored] == list(range(1, len(expected) + 1))
    assert [row["kind"] for row in stored] == [block.kind for block in expected]
    assert [row["image_state"] for row in stored] == [
        block.image_state for block in expected
    ]
    assert stored[0]["id"] == f"{blocked_artifact}:b{BLOCKER_VERSION}:0001"
    assert all(body[r["start_char"] : r["end_char"]] == r["body"] for r in stored)


def test_a_new_blocker_version_lands_beside_the_old_one(db, blocked_artifact):
    body = blocks.fetch_body(db, blocked_artifact)
    first = split_blocks(body)[:1]
    assert blocks.store_blocks(db, blocked_artifact, first, version="test2") == 1
    assert blocks.count_blocks(db, blocked_artifact, "test2") == 1
    assert blocks.count_blocks(db, blocked_artifact) > 1


def test_a_missing_artifact_is_a_clear_error(db):
    with pytest.raises(SystemExit, match="no artifact"):
        blocks.fetch_body(db, "does-not-exist")


def test_the_report_is_rendered_from_the_database(db, blocked_artifact, tmp_path):
    blocks.store_blocks(db, blocked_artifact, split_blocks(SYNTHETIC))
    path = blocks.write_report(db, blocked_artifact, reports_dir=tmp_path)
    text = path.read_text()

    assert path.parent == tmp_path and path.name.startswith("blocks-") and path.suffix == ".md"
    assert ":" not in path.name
    assert blocked_artifact in text
    assert f"blocker version: `{BLOCKER_VERSION}`" in text
    assert "- code_block: 1" in text and "- list_item: 5" in text
    assert "0001 heading [" in text
    assert 'print("hello")' in text
    # A block containing a fence is wrapped in a longer one.
    assert "````" in text
