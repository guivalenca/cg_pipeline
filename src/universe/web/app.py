"""Build the local FastAPI administration application.

``create_app`` keeps application construction separate from process startup so
tests and local tooling can create an app without opening a listening socket.
The HTTP layer is deliberately thin: every API request opens one plain
psycopg connection, delegates parsing to the pipeline modules, and closes the
connection before returning.  The same app also serves the static dashboard
pages and generated reports used by this unauthenticated local-only tool.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import psycopg
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from psycopg.types.json import Jsonb

from universe import curation, defaults, ingest, org, spine, syllabus
from universe.db import connect
from universe.kc_canonical_statement import fetch_current_canonicalizations
from universe.kc_groups import fetch_grouping_verdicts, grouping_staleness
from universe.kc_statement import statement_of
from universe.task_knowledge import knowledge_of
from universe.task_modality import modality_of


PROJECT_DIR = Path(__file__).resolve().parents[3]
STATIC_DIR = Path(__file__).resolve().parent / "static"
REPORTS_DIR = PROJECT_DIR / "reports"


def _record_source_event(
    conn: psycopg.Connection,
    source_id: str,
    action: str,
    subject: dict,
    note: str | None,
) -> str:
    """Append one founder source decision to the insert-only curation ledger."""
    exists = conn.execute("SELECT 1 FROM source WHERE id = %s", (source_id,)).fetchone()
    if exists is None:
        raise HTTPException(status_code=404, detail="Source not found")
    event_id = syllabus.next_curation_event_id(conn)
    conn.execute(
        "INSERT INTO curation_event (id, actor, action, subject, note)"
        " VALUES (%s, 'founder', %s, %s, %s) ON CONFLICT (id) DO NOTHING",
        (event_id, action, Jsonb(subject), note),
    )
    conn.commit()
    return event_id


def _source_status(conn: psycopg.Connection, source_id: str) -> str:
    """Derive the current ingestion state from immutable source facts."""
    if curation.source_is_skipped(conn, source_id):
        return "skipped by founder"
    has_snapshot, has_ok, has_failed, has_artifact = conn.execute(
        "SELECT"
        " EXISTS (SELECT 1 FROM source_snapshot WHERE source_id = %s),"
        " EXISTS (SELECT 1 FROM source_snapshot WHERE source_id = %s AND status = 'ok'),"
        " EXISTS (SELECT 1 FROM source_snapshot WHERE source_id = %s AND status = 'failed'),"
        " EXISTS ("
        "   SELECT 1 FROM source_snapshot sn"
        "   JOIN artifact a ON a.snapshot_id = sn.id"
        "   WHERE sn.source_id = %s AND sn.status = 'ok'"
        " )",
        (source_id, source_id, source_id, source_id),
    ).fetchone()
    if has_artifact:
        return "ingested"
    if has_snapshot and has_failed and not has_ok:
        return "failed"
    return "pending"


def _overlay_edits(item: dict, overlay: dict, history: list[dict]) -> None:
    """Lay founder edits over one stored item and expose the edit record."""
    for field in curation.EDITABLE_FIELDS:
        if field in overlay:
            item[field] = overlay[field]
    if "source_id" in overlay:
        item["source_id"] = overlay["source_id"]
    item["edited"] = {
        field: True for field in curation.EDITABLE_FIELDS if field in overlay
    }
    item["edits"] = history


def _media_types(conn: psycopg.Connection, source_ids) -> dict[str, str]:
    source_ids = [source_id for source_id in source_ids if source_id]
    if not source_ids:
        return {}
    return dict(
        conn.execute(
            "SELECT id, media_type FROM source WHERE id = ANY(%s)", (source_ids,)
        ).fetchall()
    )


def _effective_item(conn: psycopg.Connection, item_id: str) -> dict:
    """One syllabus item with founder edits laid over the stored fact."""
    keys = "id week seq kind title description url parent_title source_id".split()
    row = conn.execute(
        "SELECT id, week, seq, kind, title, description, url, parent_title, source_id"
        " FROM syllabus_item WHERE id = %s",
        (item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Syllabus item not found")
    item = dict(zip(keys, row))
    overlay = curation.effective_fields(conn, [item_id]).get(item_id, {})
    history = curation.edit_history(conn, [item_id]).get(item_id, [])
    _overlay_edits(item, overlay, history)
    item["media_type"] = _media_types(conn, [item["source_id"]]).get(item["source_id"])
    item["source_status"] = (
        "unlinked" if item["source_id"] is None else _source_status(conn, item["source_id"])
    )
    return item


def _version_rows(conn: psycopg.Connection, syllabus_id: str | None = None) -> list[dict]:
    where = " WHERE v.syllabus_id = %s" if syllabus_id is not None else ""
    params = (syllabus_id,) if syllabus_id is not None else ()
    rows = conn.execute(
        "SELECT v.id, v.syllabus_id, v.seq, v.origin, v.file_name, v.created_at,"
        " count(i.id), count(DISTINCT i.source_id) FILTER (WHERE i.source_id IS NOT NULL)"
        " FROM syllabus_version v LEFT JOIN syllabus_item i ON i.version_id = v.id"
        + where
        + " GROUP BY v.id ORDER BY v.syllabus_id, v.seq",
        params,
    ).fetchall()
    keys = (
        "id syllabus_id seq origin file_name created_at item_count source_count".split()
    )
    return [dict(zip(keys, row)) for row in rows]


def _syllabi(conn: psycopg.Connection, syllabus_id: str | None = None) -> list[dict]:
    if syllabus_id is None:
        rows = conn.execute("SELECT id, title FROM syllabus ORDER BY created_at, id").fetchall()
    else:
        rows = conn.execute(
            "SELECT id, title FROM syllabus WHERE id = %s", (syllabus_id,)
        ).fetchall()
    versions_by_syllabus: dict[str, list[dict]] = {}
    for version in _version_rows(conn, syllabus_id):
        owner = version.pop("syllabus_id")
        versions_by_syllabus.setdefault(owner, []).append(version)
    return [
        {"id": row[0], "title": row[1], "versions": versions_by_syllabus.get(row[0], [])}
        for row in rows
    ]


def _latest_grouping(conn: psycopg.Connection) -> tuple[dict | None, dict[str, str]]:
    row = conn.execute(
        "SELECT id, computed_at, params FROM kc_grouping"
        " ORDER BY computed_at DESC, id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        return None, {}
    grouping = {"id": row[0], "computed_at": row[1], "params": row[2]}
    stale, reasons = grouping_staleness(conn, grouping)
    grouping["stale"] = stale
    grouping["stale_reasons"] = reasons
    members = conn.execute(
        "SELECT task_id, group_id FROM kc_group_member WHERE grouping_id = %s",
        (row[0],),
    ).fetchall()
    return grouping, {task_id: group_id for task_id, group_id in members}


def _task_axes(
    conn: psycopg.Connection, grouping: dict | None = None
) -> dict[str, dict[str, str | None]]:
    """Read statement and axes from one grouping's pinned dependencies."""
    params = grouping.get("params") or {} if grouping else {}
    pinned = bool(params.get("build_key"))
    run_ids = [
        *(params.get("statements_from") or []),
        *(params.get("modality_runs") or []),
        *(params.get("knowledge_runs") or []),
    ]
    if pinned and not run_ids:
        return {}
    scope = ""
    query_params = []
    if pinned:
        scope = " AND r.id = ANY(%s)"
        query_params.append(run_ids)
    elif grouping is not None:
        # Compatibility for snapshots created before provenance was stored:
        # never let a later run rewrite their visible labels.
        scope = " AND r.started_at <= %s"
        query_params.append(grouping["computed_at"])
    rows = conn.execute(
        "SELECT r.stage, i.task_id, i.response, i.error"
        " FROM run_item i JOIN run r ON r.id = i.run_id"
        " WHERE i.task_id IS NOT NULL"
        "   AND r.stage IN ('kc-statement', 'task-modality', 'task-knowledge')"
        + scope +
        " ORDER BY r.stage, i.task_id, r.started_at DESC, i.created_at DESC, i.id DESC"
        , query_params
    ).fetchall()
    result: dict[str, dict[str, str | None]] = {}
    seen: set[tuple[str, str]] = set()
    for stage, task_id, response, error in rows:
        if (stage, task_id) in seen:
            continue
        item = {"response": response, "error": error}
        if stage == "kc-statement":
            parsed = statement_of(item)
            key = "statement"
            if not isinstance(parsed, dict):
                continue
            value = parsed.get("statement")
        elif stage == "task-modality":
            parsed = modality_of(item)
            key = "modality"
            if not isinstance(parsed, dict):
                continue
            value = parsed["verdict"]
        else:
            parsed = knowledge_of(item)
            key = "knowledge"
            if not isinstance(parsed, dict):
                continue
            value = parsed["verdict"]
        seen.add((stage, task_id))
        result.setdefault(task_id, {})[key] = value
    return result


def _source_stages(conn: psycopg.Connection) -> dict[str, list[dict]]:
    """Per-source stage progress, straight from the spine's union semantics.

    The spine computes each stage from the newest usable answer per unit
    across every run, so a retried stage whose union covers everything reads
    done here and on the Run button alike.
    """
    return {
        source_id: [
            {"stage": name, **facts}
            for name, facts in progress["stages"].items()
        ]
        for source_id, progress in spine.source_progress(conn).items()
    }


def _source_facts(conn: psycopg.Connection) -> dict[str, dict]:
    """One row of acquisition/pipeline facts per source, in three queries."""
    facts = {
        source_id: {
            "extracted": extracted,
            "failed": has_failed and not extracted,
            "tasks": 0,
            "kcs": 0,
        }
        for source_id, extracted, has_failed in conn.execute(
            "SELECT s.id,"
            " EXISTS (SELECT 1 FROM source_snapshot sn"
            "   JOIN artifact a ON a.snapshot_id = sn.id"
            "   WHERE sn.source_id = s.id AND sn.status = 'ok'),"
            " EXISTS (SELECT 1 FROM source_snapshot sn"
            "   WHERE sn.source_id = s.id AND sn.status = 'failed')"
            " FROM source s"
        ).fetchall()
    }
    for source_id, task_count in conn.execute(
        "SELECT sn.source_id, count(*) FROM task t"
        " JOIN passage p ON p.id = t.passage_id"
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " GROUP BY sn.source_id"
    ).fetchall():
        facts[source_id]["tasks"] = task_count
    # A source's KCs: tasks with a usable statement from the current
    # kc-statement generation (what the universe page draws).
    statement_default = defaults.STAGE_DEFAULTS["kc-statement"]
    for source_id, kc_count in conn.execute(
        "SELECT sn.source_id, count(DISTINCT i.task_id)"
        " FROM run_item i JOIN run r ON r.id = i.run_id"
        " JOIN task t ON t.id = i.task_id"
        " JOIN passage p ON p.id = t.passage_id"
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE r.stage = 'kc-statement' AND r.prompt_ref = %s"
        "   AND i.error IS NULL"
        " GROUP BY sn.source_id",
        (statement_default["prompt_ref"],),
    ).fetchall():
        facts[source_id]["kcs"] = kc_count
    return facts


def _corpora(conn: psycopg.Connection) -> list[dict]:
    """Group sources into corpora: one per syllabus, plus unattached test material.

    The founder's rule: real material arrives through a syllabus; sources
    with no syllabus link are the pilot/test corpus and must never be mixed
    into a real course's numbers.
    """
    facts = _source_facts(conn)
    syllabus_sources: dict[str, set[str]] = {}
    titles: dict[str, str] = {}
    for syllabus_id, title, source_id in conn.execute(
        "SELECT DISTINCT sy.id, sy.title, si.source_id"
        " FROM syllabus_item si"
        " JOIN syllabus_version v ON v.id = si.version_id"
        " JOIN syllabus sy ON sy.id = v.syllabus_id"
        " WHERE si.source_id IS NOT NULL"
    ).fetchall():
        titles[syllabus_id] = title
        syllabus_sources.setdefault(syllabus_id, set()).add(source_id)

    groups = org.syllabus_groups(conn)
    attached = set().union(*syllabus_sources.values()) if syllabus_sources else set()
    corpora = []
    for syllabus_id in sorted(syllabus_sources):
        members = syllabus_sources[syllabus_id]
        corpora.append(_corpus_card(
            kind="syllabus",
            corpus_id=syllabus_id,
            title=titles[syllabus_id],
            members=members,
            facts=facts,
            # The founder's manual choice; None means "not assigned to a
            # group yet" — the dashboard never invents an assignment.
            group=groups.get(syllabus_id),
        ))
    unattached = set(facts) - attached
    if unattached:
        corpora.append(_corpus_card(
            kind="test",
            corpus_id=None,
            title="Test corpus (markdown archive, no syllabus)",
            members=unattached,
            facts=facts,
        ))
    return corpora


def _corpus_card(
    *,
    kind: str,
    corpus_id: str | None,
    title: str,
    members: set,
    facts: dict,
    group: dict | None = None,
) -> dict:
    rows = [facts[source_id] for source_id in members]
    extracted = sum(1 for row in rows if row["extracted"])
    failed = sum(1 for row in rows if row["failed"])
    return {
        "kind": kind,
        "id": corpus_id,
        "title": title,
        "group": group,
        "sources": len(rows),
        "extracted": extracted,
        "failed": failed,
        "not_acquired": len(rows) - extracted - failed,
        "tasks": sum(row["tasks"] for row in rows),
        "kcs": sum(row["kcs"] for row in rows),
    }


def _overview(conn: psycopg.Connection) -> dict:
    grouping, group_by_task = _latest_grouping(conn)
    if grouping is None:
        verdicts = []
    else:
        verdicts = fetch_grouping_verdicts(conn, grouping["id"])
    mutual_pairs = sum(
        1 for _, _, ab, ba in verdicts if ab == ba == "clear_yes"
    )
    return {
        "corpora": _corpora(conn),
        "universe": {
            "mutual_pairs": mutual_pairs,
            "composites": len(set(group_by_task.values())),
            "grouping_id": grouping["id"] if grouping else None,
        },
        # Only items needing a founder decision; "not acquired yet" is a
        # corpus number, not an alert.
        "attention": [
            item for item in spine.attention(conn) if item["kind"] != "coverage_gap"
        ],
        "ledger": {
            "runs": conn.execute("SELECT count(*) FROM run").fetchone()[0],
            "verdicts": conn.execute("SELECT count(*) FROM kc_verdict").fetchone()[0],
        },
    }


def _source_list(conn: psycopg.Connection) -> list[dict]:
    sources = conn.execute(
        "SELECT id, title, media_type, identity FROM source ORDER BY created_at, id"
    ).fetchall()
    stage_details = _source_stages(conn)
    corpus_of: dict[str, dict] = {}
    syllabus_rows = conn.execute(
        "SELECT DISTINCT si.source_id, sy.id, sy.title"
        " FROM syllabus_item si"
        " JOIN syllabus_version v ON v.id = si.version_id"
        " JOIN syllabus sy ON sy.id = v.syllabus_id"
        " WHERE si.source_id IS NOT NULL"
    ).fetchall()
    for source_id, syllabus_id, syllabus_title in syllabus_rows:
        corpus_of[source_id] = {"id": syllabus_id, "title": syllabus_title}
    return [
        {
            "id": row[0],
            "title": row[1],
            "media_type": row[2],
            "url": (
                row[3].get("url") or row[3].get("canonical_url")
                if isinstance(row[3], dict)
                else None
            ),
            "source_status": _source_status(conn, row[0]),
            "corpus": corpus_of.get(
                row[0], {"id": None, "title": "Test corpus"}
            ),
            "stages": {
                item["stage"]: {
                    "status": item["status"],
                    "generation": item["generation"],
                }
                for item in stage_details.get(row[0], [])
            },
        }
        for row in sources
    ]


def _source_detail(conn: psycopg.Connection, source_id: str) -> dict:
    source = conn.execute(
        "SELECT id, title, media_type, identity FROM source WHERE id = %s", (source_id,)
    ).fetchone()
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    snapshot_rows = conn.execute(
        "SELECT id, status, captured_at, content_hash, failure_note, created_at"
        " FROM source_snapshot"
        " WHERE source_id = %s ORDER BY created_at, id",
        (source_id,),
    ).fetchall()
    artifact_rows = conn.execute(
        "SELECT a.id, a.snapshot_id, a.kind, a.tool, a.tool_version,"
        " length(a.body), a.created_at"
        " FROM artifact a JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s ORDER BY a.created_at, a.id",
        (source_id,),
    ).fetchall()
    stages = _source_stages(conn).get(source_id, [])

    task_rows = conn.execute(
        "SELECT t.id, t.body, t.answer"
        " FROM task t JOIN passage p ON p.id = t.passage_id"
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s ORDER BY t.created_at, t.id",
        (source_id,),
    ).fetchall()
    grouping, group_by_task = _latest_grouping(conn)
    axes = _task_axes(conn, grouping)
    tasks = [
        {
            "id": task_id,
            "body": body,
            "answer": answer,
            "statement": axes.get(task_id, {}).get("statement"),
            "modality": axes.get(task_id, {}).get("modality"),
            "knowledge": axes.get(task_id, {}).get("knowledge"),
            "group_id": group_by_task.get(task_id),
        }
        for task_id, body, answer in task_rows
    ]
    return {
        "id": source[0],
        "title": source[1],
        "media_type": source[2],
        # Identity is the stable external handle (for example URL or local file).
        "identity": source[3],
        "source_status": _source_status(conn, source_id),
        "snapshots": [
            dict(
                zip(
                    "id status captured_at content_hash failure_note created_at".split(),
                    row,
                )
            )
            for row in snapshot_rows
        ],
        "artifacts": [
            dict(
                zip(
                    "id snapshot_id kind tool tool_version chars created_at".split(),
                    row,
                )
            )
            for row in artifact_rows
        ],
        "stages": stages,
        "tasks": tasks,
    }


def _universe(conn: psycopg.Connection) -> dict:
    grouping, group_by_task = _latest_grouping(conn)
    axes = _task_axes(conn, grouping)
    task_rows = conn.execute(
        "SELECT t.id, s.id, s.title, t.body, t.answer"
        " FROM task t JOIN passage p ON p.id = t.passage_id"
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " JOIN source s ON s.id = sn.source_id ORDER BY t.id"
    ).fetchall()
    nodes = []
    for task_id, source_id, source_title, task_body, task_answer in task_rows:
        annotation = axes.get(task_id, {})
        if not annotation.get("statement"):
            continue
        nodes.append(
            {
                "id": task_id,
                "statement": annotation["statement"],
                "modality": annotation.get("modality"),
                "knowledge": annotation.get("knowledge"),
                "source_id": source_id,
                "source_title": source_title,
                "task": task_body,
                "answer": task_answer,
                "group_id": group_by_task.get(task_id),
            }
        )
    if grouping is None:
        edge_rows = []
    else:
        edge_rows = fetch_grouping_verdicts(conn, grouping["id"])
    edges = [
        {"a": a, "b": b, "ab": ab, "ba": ba, "mutual": ab == ba == "clear_yes"}
        for a, b, ab, ba in edge_rows
    ]
    groups = []
    if grouping is not None:
        canonical = fetch_current_canonicalizations(conn, grouping["id"])
        group_rows = conn.execute(
            "SELECT g.id, array_agg(m.task_id ORDER BY m.task_id)"
            " FILTER (WHERE m.task_id IS NOT NULL)"
            " FROM kc_group g LEFT JOIN kc_group_member m"
            "   ON m.grouping_id = g.grouping_id AND m.group_id = g.id"
            " WHERE g.grouping_id = %s GROUP BY g.id ORDER BY g.id",
            (grouping["id"],),
        ).fetchall()
        groups = []
        for group_id, members in group_rows:
            result = canonical.get(group_id)
            groups.append(
                {
                    "id": group_id,
                    "members": members or [],
                    "canonical_status": result["verdict"] if result else "missing",
                    "canonical_statement": (
                        result.get("statement") if result else None
                    ),
                    "canonical_reason": result.get("reason") if result else None,
                }
            )
    return {"nodes": nodes, "edges": edges, "groups": groups, "grouping": grouping}


def _runs(conn: psycopg.Connection) -> list[dict]:
    rows = conn.execute(
        "SELECT r.id, r.stage, r.model, r.prompt_ref, r.status, r.started_at, r.finished_at,"
        " count(i.id), count(i.id) FILTER (WHERE i.error IS NOT NULL)"
        " FROM run r LEFT JOIN run_item i ON i.run_id = r.id"
        " GROUP BY r.id ORDER BY r.started_at DESC, r.id DESC"
    ).fetchall()
    keys = "id stage model prompt_ref status started_at finished_at items errors".split()
    runs = [dict(zip(keys, row)) for row in rows]
    for run in runs:
        run["generation"] = defaults.run_generation(
            run["stage"], run["model"], run["prompt_ref"]
        )
    return runs


def create_app() -> FastAPI:
    """Create the local dashboard API and static page application."""
    app = FastAPI()

    @app.get("/api/overview")
    def overview() -> dict:
        with connect() as conn:
            return _overview(conn)

    @app.get("/api/syllabi")
    def list_syllabi() -> dict:
        with connect() as conn:
            return {"syllabi": _syllabi(conn)}

    @app.post("/api/syllabi/upload")
    def upload_syllabus(file: UploadFile) -> dict:
        file_name = Path(file.filename or "syllabus.xlsx").name or "syllabus.xlsx"
        temporary_directory: tempfile.TemporaryDirectory | None = None
        temp_path: Path | None = None
        try:
            temporary_directory = tempfile.TemporaryDirectory()
            temp_path = Path(temporary_directory.name) / file_name
            with temp_path.open("wb") as temporary:
                while chunk := file.file.read(1024 * 1024):
                    temporary.write(chunk)
            with connect() as conn:
                imported = syllabus.import_workbook(conn, temp_path, "founder")
                if imported["unchanged"]:
                    item_count = imported.get("item_count", 0)
                    source_count = imported.get("source_count", 0)
                else:
                    # The importer reports newly inserted canonical sources.  The
                    # upload result reports linked workbook rows, including two
                    # activities that intentionally reuse an existing source.
                    item_count, source_count = conn.execute(
                        "SELECT count(*),"
                        " count(*) FILTER (WHERE source_id IS NOT NULL)"
                        " FROM syllabus_item WHERE version_id = %s",
                        (imported["version_id"],),
                    ).fetchone()
            diff = imported.get("diff") or {}
            return {
                "syllabus_id": imported["syllabus_id"],
                "version_id": imported["version_id"],
                "unchanged": bool(imported["unchanged"]),
                "item_count": item_count,
                "source_count": source_count,
                "diff": {
                    name: [
                        {"week": item.get("week"), "title": item.get("title", "")}
                        for item in diff.get(name, [])
                    ]
                    for name in ("added", "removed", "changed")
                },
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        finally:
            file.file.close()
            if temporary_directory is not None:
                temporary_directory.cleanup()

    @app.get("/api/syllabi/{syllabus_id}")
    def syllabus_detail(syllabus_id: str) -> dict:
        with connect() as conn:
            matches = _syllabi(conn, syllabus_id)
            if not matches:
                raise HTTPException(status_code=404, detail="Syllabus not found")
            result = matches[0]
            versions = result["versions"]
            latest = max(versions, key=lambda version: version["seq"], default=None)
            weeks: list[dict[str, Any]] = []
            if latest is not None:
                attention_items = spine.attention(conn)
                attention_by_item: dict[str, list[str]] = {}
                for item in attention_items:
                    if item_id := item.get("item_id"):
                        attention_by_item.setdefault(item_id, []).append(item.get("note") or item["title"])
                item_rows = conn.execute(
                    "SELECT i.id, i.week, i.seq, i.kind, i.title, i.description, i.url,"
                    " i.parent_title, i.source_id, s.media_type"
                    " FROM syllabus_item i LEFT JOIN source s ON s.id = i.source_id"
                    " WHERE i.version_id = %s"
                    " ORDER BY i.week NULLS LAST, i.seq NULLS LAST, i.id",
                    (latest["id"],),
                ).fetchall()
                item_ids = [row[0] for row in item_rows]
                overlays = curation.effective_fields(conn, item_ids)
                histories = curation.edit_history(conn, item_ids)
                relinked_media = _media_types(
                    conn,
                    {o["source_id"] for o in overlays.values() if "source_id" in o},
                )
                by_week: dict[int | None, list[dict]] = {}
                item_keys = (
                    "id week seq kind title description url parent_title source_id media_type".split()
                )
                for row in item_rows:
                    item = dict(zip(item_keys, row))
                    week = item.pop("week")
                    overlay = overlays.get(item["id"], {})
                    _overlay_edits(item, overlay, histories.get(item["id"], []))
                    if "source_id" in overlay:
                        item["media_type"] = relinked_media.get(item["source_id"])
                    item["source_status"] = (
                        "unlinked" if item["source_id"] is None else _source_status(conn, item["source_id"])
                    )
                    item["attention"] = attention_by_item.get(item["id"], [])
                    by_week.setdefault(week, []).append(item)
                weeks = [{"week": week, "items": items} for week, items in by_week.items()]
            result["latest"] = {
                **(latest or {}),
                "version_id": latest["id"] if latest else None,
                "weeks": weeks,
            }
            previous = sorted(versions, key=lambda version: version["seq"], reverse=True)[1:2]
            if latest is not None and previous:
                result["diff"] = {
                    "vs_version_id": previous[0]["id"],
                    **syllabus.diff_versions(conn, previous[0]["id"], latest["id"]),
                }
            else:
                result["diff"] = None
            return result

    @app.post("/api/syllabi/items/{item_id}/edit")
    def edit_syllabus_item(item_id: str, payload: dict) -> dict:
        with connect() as conn:
            try:
                curation.record_edit(
                    conn,
                    item_id,
                    payload.get("field"),
                    payload.get("value"),
                    "founder",
                    payload.get("note"),
                )
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            return _effective_item(conn, item_id)

    @app.get("/api/org")
    def org_tree() -> dict:
        with connect() as conn:
            return {"institutions": org.structure(conn)}

    def _org_write(operation, conn: psycopg.Connection, *args) -> dict:
        try:
            return operation(conn, *args)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    def _required(payload: dict, key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value.strip():
            raise HTTPException(status_code=400, detail=f"{key} is required")
        return value

    @app.post("/api/org/institutions")
    def create_institution(payload: dict) -> dict:
        with connect() as conn:
            return _org_write(
                org.create_institution,
                conn,
                _required(payload, "slug"),
                _required(payload, "name"),
            )

    @app.post("/api/org/courses")
    def create_course(payload: dict) -> dict:
        with connect() as conn:
            return _org_write(
                org.create_course,
                conn,
                _required(payload, "institution_id"),
                _required(payload, "name"),
            )

    @app.post("/api/org/groups")
    def create_group(payload: dict) -> dict:
        with connect() as conn:
            return _org_write(
                org.create_group,
                conn,
                _required(payload, "institution_id"),
                _required(payload, "name"),
                payload.get("course_id") or None,
            )

    @app.post("/api/syllabi/{syllabus_id}/assign-group")
    def assign_syllabus_group(syllabus_id: str, payload: dict) -> dict:
        # group_id must be sent explicitly: a group id assigns, null clears
        # the assignment (back to "not assigned to a group yet").
        if "group_id" not in payload:
            raise HTTPException(status_code=400, detail="group_id is required")
        group_id = payload["group_id"]
        if group_id is not None and (not isinstance(group_id, str) or not group_id.strip()):
            raise HTTPException(
                status_code=400, detail="group_id must be a group id or null"
            )
        with connect() as conn:
            return _org_write(org.assign_syllabus, conn, syllabus_id, group_id)

    @app.get("/api/sources")
    def list_sources() -> dict:
        with connect() as conn:
            return {"sources": _source_list(conn)}

    @app.get("/api/sources/{source_id}")
    def source_detail(source_id: str) -> dict:
        with connect() as conn:
            return _source_detail(conn, source_id)

    @app.post("/api/sources/{source_id}/scope-override")
    def override_source_scope(source_id: str, payload: dict) -> dict:
        if "value" not in payload:
            raise HTTPException(status_code=400, detail="value is required")
        value = payload["value"]
        note = payload.get("note")
        if note is not None and not isinstance(note, str):
            raise HTTPException(status_code=400, detail="note must be text or null")
        if value is None:
            action = curation.SOURCE_SCOPE_OVERRIDE_CLEARED_ACTION
            subject = {"source_id": source_id, "note": note}
        elif isinstance(value, str) and value.strip():
            value = value.strip()
            action = curation.SOURCE_SCOPE_OVERRIDE_ACTION
            subject = {"source_id": source_id, "value": value, "note": note}
        else:
            raise HTTPException(
                status_code=400, detail="value must be a non-empty scope or null"
            )
        with connect() as conn:
            event_id = _record_source_event(
                conn,
                source_id,
                action,
                subject,
                note,
            )
        return {
            "event_id": event_id,
            "source_id": source_id,
            "value": value,
            "note": note,
        }

    @app.post("/api/sources/{source_id}/skip")
    def skip_source(source_id: str, payload: dict) -> dict:
        note = payload.get("note")
        if note is not None and not isinstance(note, str):
            raise HTTPException(status_code=400, detail="note must be text or null")
        with connect() as conn:
            event_id = _record_source_event(
                conn,
                source_id,
                curation.SOURCE_SKIP_ACTION,
                {"source_id": source_id, "note": note},
                note,
            )
        return {"event_id": event_id, "source_id": source_id, "note": note}

    @app.post("/api/sources/{source_id}/unskip")
    def unskip_source(source_id: str, payload: dict | None = None) -> dict:
        note = (payload or {}).get("note")
        if note is not None and not isinstance(note, str):
            raise HTTPException(status_code=400, detail="note must be text or null")
        with connect() as conn:
            event_id = _record_source_event(
                conn,
                source_id,
                curation.SOURCE_UNSKIP_ACTION,
                {"source_id": source_id, "note": note},
                note,
            )
        return {"event_id": event_id, "source_id": source_id, "note": note}

    @app.get("/api/sources/{source_id}/next-step")
    def source_next_step(source_id: str) -> dict:
        with connect() as conn:
            try:
                step = ingest.next_step(conn, source_id)
            except LookupError as exc:
                raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {
            "source_id": source_id,
            "running": ingest.running_step(source_id),
            "next": step,
        }

    @app.post("/api/sources/{source_id}/run-next-step")
    def run_next_step(source_id: str) -> dict:
        try:
            launched = ingest.start_step(source_id)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ingest.StepAlreadyRunning as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ingest.StepNotRunnable as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return launched

    @app.get("/api/universe")
    def universe_graph() -> dict:
        with connect() as conn:
            return _universe(conn)

    @app.get("/api/runs")
    def list_runs() -> dict:
        with connect() as conn:
            return {
                "runs": _runs(conn),
                "stage_defaults": defaults.STAGE_DEFAULTS,
                "retired_stages": sorted(defaults.RETIRED_STAGES),
            }

    page_files = {
        "/": "index.html",
        "/structure": "structure.html",
        "/syllabi": "syllabi.html",
        "/sources": "sources.html",
        "/universe": "universe.html",
        "/runs": "runs.html",
    }

    def page_response(file_name: str) -> FileResponse:
        path = STATIC_DIR / file_name
        if not path.is_file():
            raise HTTPException(status_code=404, detail="Page not found")
        return FileResponse(path, media_type="text/html", headers={"Cache-Control": "no-store"})

    def page_endpoint(file_name: str):
        def endpoint() -> FileResponse:
            return page_response(file_name)

        return endpoint

    for route, file_name in page_files.items():
        app.add_api_route(
            route,
            page_endpoint(file_name),
            methods=["GET"],
            include_in_schema=False,
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR, check_dir=False), name="static")
    app.mount("/reports", StaticFiles(directory=REPORTS_DIR, check_dir=False), name="reports")
    return app
