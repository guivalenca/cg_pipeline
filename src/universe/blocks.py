"""Split an artifact into blocks: the units markdown already delimits.

    python -m universe.blocks ARTIFACT_ID
    python -m universe.blocks ARTIFACT_ID --report

No model is involved. `split_blocks` is pure, line-based and deterministic, so
the segmentation is a fact and blocks are the address unit everything
downstream cites. Rows are insert-only: re-running the blocker at the same
BLOCKER_VERSION writes nothing, and a better blocker is a new version whose
rows land beside the old ones.

The precedence of the line rules, highest first:

    front matter  a leading '---' fence is our own metadata, not content:
                  skipped whole, no block emitted for it
    code_block    a ``` line to its closing ``` line, or to end of document
    heading       one ATX line, '#' to '######'
    table         consecutive lines starting with '|'
    blockquote    consecutive lines starting with '>'
    list_item     one marker line plus its indented continuation lines; each
                  item is its own block, never the list as a whole
    image         a paragraph that is nothing but one image reference
    image_summary a paragraph opening with 'Image summary:', the description
                  our own ingestion wrote for an image; the one content that
                  is ours, not the author's, and provenance must see that
    paragraph     any remaining run of non-blank lines

Blank lines between blocks belong to no block. Every non-whitespace character
after the front matter belongs to exactly one block, and each block's text is
its slice of the body, byte for byte; both are asserted before returning.
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import psycopg

from universe.db import connect

BLOCKER_VERSION = "2"
REPORTS_DIR = Path(__file__).resolve().parents[2] / "reports"

KINDS = (
    "paragraph",
    "heading",
    "code_block",
    "list_item",
    "image",
    "image_summary",
    "table",
    "blockquote",
)

FRONT_MATTER_FENCE = "---"
FENCE_OPEN = re.compile(r"^ {0,3}```")
FENCE_CLOSE = re.compile(r"^ {0,3}```\s*$")
HEADING = re.compile(r"^ {0,3}#{1,6}\s")
TABLE = re.compile(r"^ {0,3}\|")
BLOCKQUOTE = re.compile(r"^ {0,3}>")
LIST_ITEM = re.compile(r"^(\s*)([-*+]|\d+[.)])\s")
# A whole paragraph that is one image reference: markdown's own form, and the
# '[Image: caption](url)' form the archive's extractor emits.
IMAGE_ONLY = re.compile(r"(?:!\[[^\]\n]*\]|\[Image:[^\]\n]*\])\([^)\n]*\)")
# The fixed prefix the ingestion pipeline puts on its own image descriptions.
IMAGE_SUMMARY_PREFIX = "Image summary:"


@dataclass(frozen=True)
class Block:
    """One minimal unit of an artifact body. `text` is body[start_char:end_char]."""

    kind: str
    start_char: int
    end_char: int
    text: str


@dataclass(frozen=True)
class Line:
    """One physical line, without its newline, and where it sits in the body."""

    text: str
    start: int
    end: int  # exclusive, before the newline

    @property
    def blank(self) -> bool:
        return not self.text.strip()


def scan_lines(body: str) -> list[Line]:
    """Every line of the body with its character offsets, newline excluded.

    Only '\\n' ends a line, so the offsets stay predictable; a CRLF file keeps
    its '\\r' out of the block text.
    """
    lines, offset = [], 0
    for raw in body.split("\n"):
        text = raw[:-1] if raw.endswith("\r") else raw
        lines.append(Line(text, offset, offset + len(text)))
        offset += len(raw) + 1
    return lines


def front_matter_end(lines: list[Line]) -> int:
    """Index of the first content line: past a leading '---' fence if one closes.

    An opening fence with no closing one is not front matter at all; treating
    it as such would swallow the whole document.
    """
    if not lines or lines[0].text.strip() != FRONT_MATTER_FENCE:
        return 0
    for index in range(1, len(lines)):
        if lines[index].text.strip() == FRONT_MATTER_FENCE:
            return index + 1
    return 0


def starts_block(text: str) -> str | None:
    """The kind a line opens on its own, in precedence order, or None."""
    if FENCE_OPEN.match(text):
        return "code_block"
    if HEADING.match(text):
        return "heading"
    if TABLE.match(text):
        return "table"
    if BLOCKQUOTE.match(text):
        return "blockquote"
    if LIST_ITEM.match(text):
        return "list_item"
    return None


def end_of_code_block(lines: list[Line], start: int) -> int:
    for index in range(start + 1, len(lines)):
        if FENCE_CLOSE.match(lines[index].text):
            return index + 1
    # An unclosed fence runs to the end of the document, minus the blank lines
    # trailing it: no block ends on a blank line.
    stop = len(lines)
    while stop - 1 > start and lines[stop - 1].blank:
        stop -= 1
    return stop


def end_of_run(lines: list[Line], start: int, pattern: re.Pattern) -> int:
    index = start + 1
    while index < len(lines) and pattern.match(lines[index].text):
        index += 1
    return index


def end_of_list_item(lines: list[Line], start: int) -> int:
    """The marker line plus lines indented past the marker: one item, alone."""
    indent = len(LIST_ITEM.match(lines[start].text).group(1))
    index = start + 1
    while index < len(lines):
        text = lines[index].text
        if not text.strip() or LIST_ITEM.match(text):
            break
        if len(text) - len(text.lstrip()) <= indent:
            break
        index += 1
    return index


def end_of_paragraph(lines: list[Line], start: int) -> int:
    index = start + 1
    while index < len(lines):
        text = lines[index].text
        if not text.strip() or starts_block(text):
            break
        index += 1
    return index


def split_blocks(body: str) -> list[Block]:
    """Split a markdown body into blocks. Pure: no database, no I/O."""
    lines = scan_lines(body)
    index = front_matter_end(lines)
    content_start = lines[index].start if index < len(lines) else len(body)

    blocks: list[Block] = []
    while index < len(lines):
        if lines[index].blank:
            index += 1
            continue

        kind = starts_block(lines[index].text)
        if kind == "code_block":
            stop = end_of_code_block(lines, index)
        elif kind == "heading":
            stop = index + 1
        elif kind == "table":
            stop = end_of_run(lines, index, TABLE)
        elif kind == "blockquote":
            stop = end_of_run(lines, index, BLOCKQUOTE)
        elif kind == "list_item":
            stop = end_of_list_item(lines, index)
        else:
            stop = end_of_paragraph(lines, index)
            kind = "paragraph"

        start_char, end_char = lines[index].start, lines[stop - 1].end
        text = body[start_char:end_char]
        if kind == "paragraph" and IMAGE_ONLY.fullmatch(text.strip()):
            kind = "image"
        elif kind == "paragraph" and text.lstrip().startswith(IMAGE_SUMMARY_PREFIX):
            kind = "image_summary"
        blocks.append(Block(kind, start_char, end_char, text))
        index = stop

    check_invariants(body, content_start, blocks)
    return blocks


def check_invariants(body: str, content_start: int, blocks: list[Block]) -> None:
    """Ordered, non-overlapping, exact slices, and nothing dropped on the floor."""
    previous = content_start
    for block in blocks:
        assert block.kind in KINDS, f"unknown kind {block.kind!r}"
        assert block.start_char >= previous, f"block at {block.start_char} overlaps or precedes"
        assert block.end_char > block.start_char, f"empty block at {block.start_char}"
        assert body[block.start_char : block.end_char] == block.text, (
            f"block at {block.start_char} is not its slice of the body"
        )
        # Nothing but whitespace may sit in the gap before this block.
        assert not body[previous : block.start_char].strip(), (
            f"content between {previous} and {block.start_char} is in no block"
        )
        previous = block.end_char

    assert not body[previous:].strip(), f"content after {previous} is in no block"


# --- the ledger -------------------------------------------------------------


def block_id(artifact_id: str, seq: int, version: str = BLOCKER_VERSION) -> str:
    return f"{artifact_id}:b{version}:{seq:04d}"


def fetch_body(conn: psycopg.Connection, artifact_id: str) -> str:
    row = conn.execute("SELECT body FROM artifact WHERE id = %s", (artifact_id,)).fetchone()
    if not row:
        raise SystemExit(f"no artifact {artifact_id}")
    return row[0]


def count_blocks(
    conn: psycopg.Connection, artifact_id: str, version: str = BLOCKER_VERSION
) -> int:
    return conn.execute(
        "SELECT count(*) FROM block WHERE artifact_id = %s AND blocker_version = %s",
        (artifact_id, version),
    ).fetchone()[0]


def store_blocks(
    conn: psycopg.Connection,
    artifact_id: str,
    blocks: list[Block],
    version: str = BLOCKER_VERSION,
) -> int:
    """Write the set, once. Returns 0 if this version already has rows here.

    The table is a fact ledger, so an existing set is never corrected in
    place: re-running is a no-op, and a different split is a new version.
    """
    if count_blocks(conn, artifact_id, version):
        return 0
    with conn.cursor() as cur:
        for seq, block in enumerate(blocks, start=1):
            cur.execute(
                "INSERT INTO block"
                " (id, artifact_id, blocker_version, seq, kind, start_char, end_char, body)"
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (
                    block_id(artifact_id, seq, version),
                    artifact_id,
                    version,
                    seq,
                    block.kind,
                    block.start_char,
                    block.end_char,
                    block.text,
                ),
            )
    conn.commit()
    return len(blocks)


def fetch_blocks(
    conn: psycopg.Connection, artifact_id: str, version: str = BLOCKER_VERSION
) -> list[dict]:
    rows = conn.execute(
        "SELECT id, seq, kind, start_char, end_char, body FROM block"
        " WHERE artifact_id = %s AND blocker_version = %s ORDER BY seq",
        (artifact_id, version),
    ).fetchall()
    keys = "id seq kind start_char end_char body".split()
    return [dict(zip(keys, row)) for row in rows]


# --- reading back -----------------------------------------------------------


def report_path(artifact_id: str, reports_dir: Path | None = None) -> Path:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", artifact_id).strip("-")
    return (reports_dir or REPORTS_DIR) / f"blocks-{slug}.md"


def fence_for(text: str) -> str:
    """A fence longer than the longest backtick run inside, so code survives."""
    longest = max((len(run) for run in re.findall(r"`+", text)), default=0)
    return "`" * max(3, longest + 1)


def render_report(artifact_id: str, version: str, blocks: list[dict]) -> str:
    counts: dict[str, int] = {}
    for block in blocks:
        counts[block["kind"]] = counts.get(block["kind"], 0) + 1

    lines = [
        f"# Blocks of {artifact_id}",
        "",
        f"- blocker version: `{version}`",
        f"- blocks: {len(blocks)}",
    ]
    lines += [f"- {kind}: {counts[kind]}" for kind in sorted(counts)]
    lines += [
        "",
        "Regenerated from the `block` table; the fact lives there, not here.",
        "",
    ]
    for block in blocks:
        fence = fence_for(block["body"])
        lines += [
            f"## {block['seq']:04d} {block['kind']}"
            f" [{block['start_char']}:{block['end_char']}]",
            "",
            fence,
            block["body"],
            fence,
            "",
        ]
    return "\n".join(lines)


def write_report(
    conn: psycopg.Connection,
    artifact_id: str,
    version: str = BLOCKER_VERSION,
    reports_dir: Path | None = None,
) -> Path:
    path = report_path(artifact_id, reports_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(artifact_id, version, fetch_blocks(conn, artifact_id, version)))
    return path


# --- CLI --------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="universe.blocks", description=__doc__)
    parser.add_argument("artifact_id")
    parser.add_argument(
        "--report", action="store_true", help=f"also write {report_path('ARTIFACT_ID').name}"
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    with connect() as conn:
        blocks = split_blocks(fetch_body(conn, args.artifact_id))
        inserted = store_blocks(conn, args.artifact_id, blocks)
        if inserted:
            print(f"{args.artifact_id}: inserted {inserted} block(s) at version {BLOCKER_VERSION}")
        else:
            existing = count_blocks(conn, args.artifact_id)
            print(
                f"{args.artifact_id}: {existing} block(s) already at version"
                f" {BLOCKER_VERSION}, nothing inserted",
                file=sys.stderr,
            )
        if args.report:
            print(write_report(conn, args.artifact_id))


if __name__ == "__main__":
    main()
