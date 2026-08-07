"""Import the institution's syllabus workbook as immutable, versioned facts.

The public surface is deliberately small: pure workbook parsing and URL
classification functions sit beside one database import operation and one
version diff.  Parsing preserves every received cell in ``fields`` while
lifting only the columns needed for navigation into typed item attributes.
Imports derive stable syllabus, version, item, and source identities, so a
re-upload never rewrites an earlier fact and identical files are idempotent.

    python -m universe.syllabus import path/to/syllabus.xlsx
    python -m universe.syllabus list
    python -m universe.syllabus diff SYLLABUS:v0001 SYLLABUS:v0002
"""

import argparse
import hashlib
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote_plus, urlparse

import psycopg
from openpyxl import load_workbook
from psycopg.types.json import Jsonb

from universe.db import connect

COLUMNS = (
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
WEEK = re.compile(r"^Semana\s+(\d+)$", re.IGNORECASE)
BOOK_SCOPE = re.compile(
    r"(?:capítulos?|cap\.|chapters?|páginas?|págs?\.|p\.|pages?|unidades?|units?)"
    r"\s*\d+(?:\s*[-–—]\s*\d+)?",
    re.IGNORECASE,
)


def slugify(text: str) -> str:
    """Return a lowercase ASCII slug suitable for a stable syllabus id."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_text.lower())).strip("-")


def canonical_url(url: str) -> str:
    """Remove tracking parameters and fragments without rewriting the URL."""
    base, _, _fragment = url.strip().partition("#")
    path, separator, query = base.partition("?")
    if not separator:
        return path
    kept = []
    for parameter in query.split("&"):
        key = unquote_plus(parameter.partition("=")[0])
        if not key.lower().startswith("utm_"):
            kept.append(parameter)
    return f"{path}?{'&'.join(kept)}" if kept else path


def media_type(url: str) -> str:
    """Classify the few media families that affect syllabus ingestion."""
    host = (urlparse((url or "").strip()).hostname or "").lower()
    video_hosts = ("youtube.com", "youtu.be", "vimeo.com", "ted.com")
    if any(host == candidate or host.endswith(f".{candidate}") for candidate in video_hosts):
        return "video"
    book_host = "integrada.minhabiblioteca.com.br"
    if host == book_host or host.endswith(f".{book_host}") or "sophia" in (url or "").lower():
        return "book"
    return "article"


def book_scope_missing(item: dict) -> bool:
    """Say whether a linked book lacks an explicit chapter, page, or unit."""
    if media_type(item.get("url") or "") != "book":
        return False
    text = f"{item.get('title') or ''}\n{item.get('description') or ''}"
    return BOOK_SCOPE.search(text) is None


def _cell(value) -> str | None:
    if value is None or not str(value).strip():
        return None
    return str(value)


def _sheet(workbook):
    if "Projetos" in workbook.sheetnames:
        return workbook["Projetos"]
    for sheet in workbook.worksheets:
        header = tuple(_cell(cell.value) for cell in next(sheet.iter_rows(max_row=1), ()))
        if header == COLUMNS:
            return sheet
    for sheet in workbook.worksheets:
        header = tuple(_cell(cell.value) for cell in next(sheet.iter_rows(max_row=1), ()))
        if "Projeto" in header or "Atividade" in header:
            return sheet
    raise ValueError("no 'Projetos' sheet or sheet with a syllabus header")


def _validate_header(header: tuple[str | None, ...]) -> None:
    missing = [column for column in COLUMNS if column not in header]
    unknown = [
        column if column is not None else "<blank>"
        for column in header
        if column not in COLUMNS
    ]
    if len(header) != len(COLUMNS) or missing or unknown:
        details = []
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        if unknown:
            details.append(f"unknown columns: {', '.join(unknown)}")
        if len(header) != len(COLUMNS):
            details.append(f"expected 21 columns, found {len(header)}")
        raise ValueError("invalid syllabus header; " + "; ".join(details))


def parse_workbook(path: str | Path) -> dict:
    """Parse a syllabus workbook without touching the database."""
    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        sheet = _sheet(workbook)
        rows = sheet.iter_rows(values_only=True)
        header = tuple(_cell(value) for value in next(rows, ()))
        _validate_header(header)

        items = []
        for row_number, raw_row in enumerate(rows, start=2):
            values = tuple(_cell(value) for value in raw_row)
            if not any(value is not None for value in values):
                continue
            fields = dict(zip(COLUMNS, values, strict=True))
            week_match = WEEK.fullmatch((fields["Semana"] or "").strip())
            if not week_match:
                raise ValueError(
                    f"row {row_number}: invalid Semana value {fields['Semana']!r};"
                    " expected 'Semana XX'"
                )
            try:
                seq = int((fields["Ordem"] or "").strip())
            except ValueError as exc:
                raise ValueError(
                    f"row {row_number}: invalid Ordem value {fields['Ordem']!r}"
                ) from exc
            items.append(
                {
                    "week": int(week_match.group(1)),
                    "seq": seq,
                    "kind": (fields["Tipo da atividade"] or "").strip(),
                    "title": (fields["Atividade"] or "").strip(),
                    "description": (fields["Descrição da atividade"] or "").strip(),
                    "parent_title": (fields["Encontro pai"] or "").strip(),
                    "url": (fields["URL"] or "").strip(),
                    "fields": fields,
                }
            )
    finally:
        workbook.close()

    if not items:
        raise ValueError("syllabus workbook has no items")
    title = (items[0]["fields"]["Projeto"] or "").strip()
    if not title:
        raise ValueError("first syllabus item has no Projeto value")
    return {"syllabus_id": slugify(title), "title": title, "items": items}


# --- Database import ----


def next_curation_event_id(conn: psycopg.Connection) -> str:
    """Allocate the next curation event id."""
    conn.execute("LOCK TABLE curation_event IN SHARE ROW EXCLUSIVE MODE")
    number = conn.execute(
        "SELECT coalesce(max(substring(id from '[0-9]+$')::int), 0) + 1"
        " FROM curation_event"
    ).fetchone()[0]
    return f"ce{number:04d}"


def resolve_source(conn: psycopg.Connection, url: str, title: str) -> tuple[str, bool]:
    """Resolve-or-mint the canonical source for a URL.

    This is the one place a URL becomes a source identity: the id derives
    from the canonical URL, so the same address always resolves to the same
    row.  Workbook import and founder edits both link items through here.
    Returns the source id and whether a new row was minted.
    """
    canonical = canonical_url(url)
    source_id = "src-" + hashlib.sha256(canonical.encode()).hexdigest()[:12]
    cursor = conn.execute(
        "INSERT INTO source (id, identity, title, media_type)"
        " VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (source_id, Jsonb({"canonical_url": canonical}), title, media_type(url)),
    )
    return source_id, bool(cursor.rowcount)


def _get_or_create_syllabus(conn: psycopg.Connection, syllabus_id: str, title: str) -> None:
    """Ensure the syllabus exists; do not update if it does."""
    conn.execute(
        "INSERT INTO syllabus (id, title) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (syllabus_id, title),
    )


def _get_previous_version(conn: psycopg.Connection, syllabus_id: str) -> dict | None:
    """Fetch the latest version of a syllabus."""
    row = conn.execute(
        "SELECT id, seq, file_sha FROM syllabus_version"
        " WHERE syllabus_id = %s ORDER BY seq DESC LIMIT 1",
        (syllabus_id,),
    ).fetchone()
    if row:
        return {"id": row[0], "seq": row[1], "file_sha": row[2]}
    return None


def _next_version_id(syllabus_id: str, seq: int) -> str:
    """Derive a version id from syllabus id and sequence."""
    return f"{syllabus_id}:v{seq:04d}"


def _next_item_id(version_id: str, index: int) -> str:
    """Derive an item id from version id and index."""
    return f"{version_id}:{index:04d}"


def diff_versions(conn: psycopg.Connection, version_a: str, version_b: str) -> dict:
    """Compare two syllabus versions by (week, title) key."""
    items_a = conn.execute(
        "SELECT week, seq, title, url, description FROM syllabus_item"
        " WHERE version_id = %s ORDER BY week, seq, title",
        (version_a,),
    ).fetchall()
    items_b = conn.execute(
        "SELECT week, seq, title, url, description FROM syllabus_item"
        " WHERE version_id = %s ORDER BY week, seq, title",
        (version_b,),
    ).fetchall()
    map_a = {(row[0], row[2]): row for row in items_a}
    map_b = {(row[0], row[2]): row for row in items_b}

    added = []
    removed = []
    changed = []

    for key, row_b in map_b.items():
        if key not in map_a:
            added.append(
                {
                    "week": row_b[0],
                    "seq": row_b[1],
                    "title": row_b[2],
                    "url": row_b[3],
                    "description": row_b[4],
                }
            )

    for key, row_a in map_a.items():
        if key not in map_b:
            removed.append(
                {
                    "week": row_a[0],
                    "seq": row_a[1],
                    "title": row_a[2],
                    "url": row_a[3],
                    "description": row_a[4],
                }
            )
        else:
            row_b = map_b[key]
            if row_a[3] != row_b[3] or row_a[4] != row_b[4]:
                changed.append(
                    {
                        "week": row_a[0],
                        "title": row_a[2],
                        "url_a": row_a[3],
                        "url_b": row_b[3],
                        "description_a": row_a[4],
                        "description_b": row_b[4],
                    }
                )

    added.sort(key=lambda item: (item["week"], item["seq"], item["title"]))
    removed.sort(key=lambda item: (item["week"], item["seq"], item["title"]))
    changed.sort(key=lambda item: (item["week"], item["title"]))
    return {"added": added, "removed": removed, "changed": changed}


def import_workbook(
    conn: psycopg.Connection, path: str | Path, actor: str = "founder"
) -> dict:
    """Import a syllabus workbook and record all facts immutably."""
    path = Path(path)
    file_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    parsed = parse_workbook(path)
    syllabus_id = parsed["syllabus_id"]
    items = parsed["items"]

    _get_or_create_syllabus(conn, syllabus_id, parsed["title"])
    previous = _get_previous_version(conn, syllabus_id)
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

    next_seq = (previous["seq"] if previous else 0) + 1
    version_id = _next_version_id(syllabus_id, next_seq)
    conn.execute(
        "INSERT INTO syllabus_version"
        " (id, syllabus_id, seq, origin, file_name, file_sha)"
        " VALUES (%s, %s, %s, 'upload', %s, %s)",
        (version_id, syllabus_id, next_seq, path.name, file_sha),
    )

    source_count = 0
    source_lookup = {}
    for item in items:
        if item["kind"] == "Autoestudo" and item["url"]:
            source_id, created = resolve_source(conn, item["url"], item["title"])
            source_lookup[item["url"]] = source_id
            source_count += created

    sorted_items = sorted(items, key=lambda x: (x["week"], x["seq"], x["title"]))
    for index, item in enumerate(sorted_items, start=1):
        item_id = _next_item_id(version_id, index)
        source_id = (
            source_lookup.get(item["url"])
            if item["kind"] == "Autoestudo" and item["url"]
            else None
        )
        conn.execute(
            "INSERT INTO syllabus_item"
            " (id, version_id, week, seq, kind, title, description, parent_title, url,"
            "  source_id, fields)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                item_id,
                version_id,
                item["week"],
                item["seq"],
                item["kind"],
                item["title"],
                item["description"],
                item["parent_title"],
                item["url"],
                source_id,
                Jsonb(item["fields"]),
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
                    "syllabus_id": syllabus_id,
                    "version_id": version_id,
                    "file_sha": file_sha,
                }
            ),
        ),
    )
    diff = diff_versions(conn, previous["id"], version_id) if previous else {}
    conn.commit()
    return {
        "syllabus_id": syllabus_id,
        "version_id": version_id,
        "seq": next_seq,
        "unchanged": False,
        "item_count": len(sorted_items),
        "source_count": source_count,
        "diff": diff,
    }


# --- CLI ---


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="universe.syllabus",
        description="Import and manage syllabus versions.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    import_cmd = sub.add_parser("import", help="import a workbook")
    import_cmd.add_argument("path", help="path to workbook file")
    import_cmd.set_defaults(func=cmd_import)

    sub.add_parser("list", help="list syllabus versions").set_defaults(func=cmd_list)

    diff_cmd = sub.add_parser("diff", help="compare two versions")
    diff_cmd.add_argument("version_a", help="first version id")
    diff_cmd.add_argument("version_b", help="second version id")
    diff_cmd.set_defaults(func=cmd_diff)

    return parser


def cmd_import(args: argparse.Namespace) -> None:
    """Import a workbook."""
    with connect() as conn:
        result = import_workbook(conn, args.path)

    if result["unchanged"]:
        print(f"File unchanged (version {result['version_id']}, seq {result['seq']})")
    else:
        print(f"Imported {result['syllabus_id']} version {result['seq']}")
        print(f"  Items: {result['item_count']}")
        print(f"  New sources: {result['source_count']}")
        if result["diff"]:
            print(f"  Added: {len(result['diff'].get('added', []))}")
            print(f"  Removed: {len(result['diff'].get('removed', []))}")
            print(f"  Changed: {len(result['diff'].get('changed', []))}")


def cmd_list(args: argparse.Namespace) -> None:
    """List all syllabus versions."""
    with connect() as conn:
        rows = conn.execute(
            "SELECT s.id, sv.id, sv.seq, sv.created_at"
            " FROM syllabus s"
            " JOIN syllabus_version sv ON sv.syllabus_id = s.id"
            " ORDER BY s.id, sv.seq",
        ).fetchall()

    if not rows:
        print("No syllabus versions")
        return

    for s_id, sv_id, seq, created in rows:
        print(f"{sv_id} (seq {seq}, {created.strftime('%Y-%m-%d %H:%M')})")


def cmd_diff(args: argparse.Namespace) -> None:
    """Show diff between two versions."""
    with connect() as conn:
        result = diff_versions(conn, args.version_a, args.version_b)

    if result["added"]:
        print(f"Added ({len(result['added'])}):")
        for item in result["added"]:
            print(f"  Week {item['week']}: {item['title']}")

    if result["removed"]:
        print(f"Removed ({len(result['removed'])}):")
        for item in result["removed"]:
            print(f"  Week {item['week']}: {item['title']}")

    if result["changed"]:
        print(f"Changed ({len(result['changed'])}):")
        for item in result["changed"]:
            print(f"  Week {item['week']}: {item['title']}")
            if item["url_a"] != item["url_b"]:
                print(f"    URL: {item['url_a']} -> {item['url_b']}")
            if item["description_a"] != item["description_b"]:
                print(f"    Description changed")


def main(argv: list[str] | None = None) -> None:
    """Entry point."""
    args = build_parser().parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
