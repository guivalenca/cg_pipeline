"""Per-source pipeline progress aggregation and attention alerts.

One deep interface: pure SQL reads over the ingestion ledger and model runs.
Computes completion status for each of 16 pipeline stages per source, and
flags coverage gaps and acquisition failures.

Status is computed from the union of every run of a stage, never one run
alone: a unit (artifact, passage, task) counts as done when its newest
usable answer across all runs parses, exactly the rule the dashboard's task
axes use.  A retry chain whose latest run partially failed therefore still
reads done when the union covers everything.  The units in scope for a
stage are the ones the stage would actually call given the pipeline gates:
triage-kept passages for task generation, post-split survivors for revision
onward, triage-supported tasks for substance, substance-kept tasks for the
statement and axis stages, and currently-stated tasks for the judge and the
grouping snapshot.

No writes, no model calls. Every query stays in this module.
"""

import json
from collections import OrderedDict

import psycopg

from universe import curation, defaults
from universe.acquisition.gates import GATE_CODES
from universe.kc_statement import statement_of
from universe.kc_groups import grouping_staleness
from universe.task_granularity import granularity_of
from universe.task_knowledge import knowledge_of
from universe.task_modality import modality_of
from universe.task_revision import revision_of
from universe.task_substance import DROPPED as SUBSTANCE_DROPPED
from universe.task_substance import substance_of
from universe.taskgen import KEEP as PASSAGE_KEEP
from universe.triage import verdict_of as passage_verdict_of


STAGE_ORDER = [
    "snapshot",
    "artifact",
    "blocks",
    "passage-cuts",
    "passage-triage",
    "task-generation",
    "task-granularity",
    "task-revision",
    "task-triage",
    "task-substance",
    "kc-statement",
    "task-modality",
    "task-knowledge",
    "task-embedding",
    "kc-judge",
    "grouped",
]

# Stages before this index carry their own scope semantics; from here on an
# empty scope means "nothing left to do" once the previous stage completed.
_CASCADE_FROM = STAGE_ORDER.index("passage-triage")

_TASK_TRIAGE_VERDICTS = {"supported", "unsupported", "unsure"}

_ACQUISITION_KIND_BY_GATE = {
    "missing_credentials": "missing_credentials",
    "manual_access_required": "manual_access_required",
    "missing_concrete_scope": "missing_concrete_scope",
    "unsupported_media_kind": "unsupported_media_kind",
}


def source_progress(conn: psycopg.Connection) -> dict:
    """Progress of each source through the 16-stage pipeline.

    Returns dict keyed by source_id:
    {
      'source_id': {
        'id': 'source_id',
        'title': 'title',
        'media_type': 'media_type',
        'snapshot_status': 'ok' | 'failed' | 'pending',
        'stages': OrderedDict([
          ('snapshot', {'status': '...', 'run_id': None, 'done': N,
                        'total': M, 'generation': '...' | None}),
          ...
        ])
      }
    }

    Status semantics:
    - 'done': every unit in scope has a usable answer (union of all runs)
    - 'partial': some units covered
    - 'failed': attempts exist but no unit has a usable answer
    - 'pending': nothing attempted yet
    """
    result = {}

    rows = conn.execute(
        "SELECT s.id, s.title, s.media_type,"
        " (SELECT status FROM source_snapshot WHERE source_id = s.id"
        "  ORDER BY created_at DESC LIMIT 1) AS latest_status"
        " FROM source s"
        " ORDER BY s.id"
    ).fetchall()

    for source_id, title, media_type, latest_status in rows:
        snapshot_status = latest_status or "pending"
        if snapshot_status not in ("ok", "failed"):
            snapshot_status = "pending"

        stages = OrderedDict()

        # snapshot: one per source, ok|failed|pending
        if snapshot_status == "ok":
            snapshot_state = "done"
        elif snapshot_status == "failed":
            snapshot_state = "failed"
        else:
            snapshot_state = "pending"
        stages["snapshot"] = {
            "status": snapshot_state,
            "run_id": None,
            "done": 1 if snapshot_state == "done" else 0,
            "total": 1,
            "generation": None,
        }

        # artifact: for ok snapshots
        artifact_count = conn.execute(
            "SELECT count(*) FROM artifact a"
            " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            " WHERE sn.source_id = %s AND sn.status = 'ok'",
            (source_id,),
        ).fetchone()[0]
        ok_snapshot_count = conn.execute(
            "SELECT count(*) FROM source_snapshot WHERE source_id = %s AND status = 'ok'",
            (source_id,),
        ).fetchone()[0]
        stages["artifact"] = {
            "status": "done" if artifact_count > 0 and ok_snapshot_count > 0 else "pending",
            "run_id": None,
            "done": artifact_count,
            "total": ok_snapshot_count,
            "generation": None,
        }

        # blocks: for each artifact
        artifacts_with_blocks = conn.execute(
            "SELECT count(DISTINCT b.artifact_id) FROM block b"
            " JOIN artifact a ON a.id = b.artifact_id"
            " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            " WHERE sn.source_id = %s",
            (source_id,),
        ).fetchone()[0]
        total_artifacts = conn.execute(
            "SELECT count(*) FROM artifact a"
            " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            " WHERE sn.source_id = %s",
            (source_id,),
        ).fetchone()[0]
        stages["blocks"] = {
            "status": "done" if artifacts_with_blocks == total_artifacts and total_artifacts > 0 else ("partial" if artifacts_with_blocks > 0 else "pending"),
            "run_id": None,
            "done": artifacts_with_blocks,
            "total": total_artifacts,
            "generation": None,
        }

        current_passages, all_passages = (
            _current_passages(conn, source_id) if total_artifacts else ([], 0)
        )
        stages["passage-cuts"] = _cuts_facts(
            conn, source_id, current_passages, all_passages
        )

        if total_artifacts == 0:
            # Nothing extracted: every model stage is untouched by definition,
            # and the queries below could only confirm that.
            for stage_name in STAGE_ORDER[_CASCADE_FROM:]:
                stages[stage_name] = _empty_facts()
        else:
            stages.update(_model_stage_facts(conn, source_id, current_passages))

        _cascade_vacuous_done(stages)

        result[source_id] = {
            "id": source_id,
            "title": title,
            "media_type": media_type,
            "snapshot_status": snapshot_status,
            "stages": stages,
        }

    return result


def _empty_facts() -> dict:
    return {"status": "pending", "run_id": None, "done": 0, "total": 0, "generation": None}


def _current_passages(conn: psycopg.Connection, source_id: str) -> tuple[list[str], int]:
    """Passages a current-generation cuts run materialized, plus the overall count.

    The pipeline's scope is the current interpretation of the source: a
    passage only a superseded experiment ever cut is history, not a target
    (the same rule ingest applies when it wires runs together).
    """
    rows = conn.execute(
        "SELECT p.id, r.model, r.prompt_ref FROM passage p"
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " LEFT JOIN passage_origin po ON po.passage_id = p.id"
        " LEFT JOIN run r ON r.id = po.run_id"
        " WHERE sn.source_id = %s",
        (source_id,),
    ).fetchall()
    current: set[str] = set()
    seen: set[str] = set()
    for passage_id, model, prompt_ref in rows:
        seen.add(passage_id)
        if model is not None and (
            defaults.run_generation("passage-cuts", model, prompt_ref) == "current"
        ):
            current.add(passage_id)
    return sorted(current), len(seen)


def _cuts_facts(
    conn: psycopg.Connection, source_id: str, current_passages: list[str], all_passages: int
) -> dict:
    """Passage-cuts progress: current-recipe passages plus the newest run badge."""
    newest = conn.execute(
        "SELECT r.id, r.model, r.prompt_ref FROM run r"
        " WHERE r.stage = 'passage-cuts' AND EXISTS ("
        "   SELECT 1 FROM run_item i"
        "   JOIN artifact a ON a.id = i.artifact_id"
        "   JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        "   WHERE i.run_id = r.id AND sn.source_id = %s)"
        " ORDER BY r.started_at DESC, r.id DESC LIMIT 1",
        (source_id,),
    ).fetchone()
    run_id, model, prompt_ref = newest or (None, None, None)
    covered = len(current_passages)
    return {
        # A source cut only by superseded recipes still needs the current
        # cut; the stage stays open and the badge names the stale run.
        "status": "done" if covered else "pending",
        "run_id": run_id,
        "done": covered,
        "total": covered if covered else all_passages,
        "generation": defaults.run_generation("passage-cuts", model, prompt_ref) if run_id else None,
    }


# --- union-of-runs stage facts ----------------------------------------------


def _usable_dict(parser):
    """A parser that accepts an item when the stage parser returns a dict."""
    def usable(item: dict) -> dict | None:
        parsed = parser(item)
        return parsed if isinstance(parsed, dict) else None
    return usable


def _usable_any(item: dict) -> dict | None:
    """Stages whose mere non-error answer is the fact (generation, embedding)."""
    return {} if item["error"] is None and item["response"] is not None else None


def _usable_passage_triage(item: dict) -> dict | None:
    verdict = passage_verdict_of(item)
    if verdict in ("error", "unparseable"):
        return None
    return {"verdict": verdict}


def _usable_task_triage(item: dict) -> dict | None:
    if item["error"]:
        return None
    try:
        parsed = json.loads(item["response"])
    except (TypeError, json.JSONDecodeError):
        return None
    if isinstance(parsed, dict) and parsed.get("verdict") in _TASK_TRIAGE_VERDICTS:
        return {"verdict": parsed["verdict"]}
    return None


def _stage_rows(
    conn: psycopg.Connection, source_id: str, stage: str, unit: str
) -> list[tuple]:
    """Every run item of a stage touching this source's units, newest first."""
    if unit == "task":
        unit_column = "i.task_id"
        joins = (
            " JOIN task t ON t.id = i.task_id"
            " JOIN passage p ON p.id = t.passage_id"
        )
    else:
        unit_column = "i.passage_id"
        joins = " JOIN passage p ON p.id = i.passage_id"
    return conn.execute(
        f"SELECT {unit_column}, i.id, i.response, i.error,"
        " r.id, r.model, r.prompt_ref"
        " FROM run_item i JOIN run r ON r.id = i.run_id"
        + joins +
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE r.stage = %s AND sn.source_id = %s"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (stage, source_id),
    ).fetchall()


def _fold(rows: list[tuple], usable) -> tuple[dict, set, tuple]:
    """Newest usable answer per unit across every run of a stage.

    Exactly the task-axes rule: walk items newest first, keep the first one
    the stage parser accepts; failed or unparseable attempts fall through to
    older answers instead of erasing them.
    """
    answers: dict[str, dict] = {}
    attempted: set[str] = set()
    newest = (None, None, None)
    for unit_id, item_id, response, error, run_id, model, prompt_ref in rows:
        if newest[0] is None:
            newest = (run_id, model, prompt_ref)
        attempted.add(unit_id)
        if unit_id in answers:
            continue
        parsed = usable({"response": response, "error": error})
        if parsed is not None:
            answers[unit_id] = {"answer": parsed, "item_id": item_id}
    return answers, attempted, newest


def _stage_facts(stage: str, scope, answers: dict, attempted: set, newest: tuple) -> dict:
    done = sum(1 for unit in scope if unit in answers)
    total = len(scope)
    tried_and_failed = sum(
        1 for unit in scope if unit in attempted and unit not in answers
    )
    if total == 0:
        status = "pending"
    elif done == total:
        status = "done"
    elif done:
        status = "partial"
    elif tried_and_failed:
        status = "failed"
    else:
        status = "pending"
    run_id, model, prompt_ref = newest
    return {
        "status": status,
        "run_id": run_id,
        "done": done,
        "total": total,
        "generation": defaults.run_generation(stage, model, prompt_ref) if run_id else None,
    }


def _model_stage_facts(
    conn: psycopg.Connection, source_id: str, passages: list[str]
) -> OrderedDict:
    """Union-of-runs facts for every model stage plus judge and grouping.

    ``passages`` is the current-recipe scope: what a current-generation cuts
    run materialized for this source.
    """
    stages: OrderedDict[str, dict] = OrderedDict()

    tri = _fold(
        _stage_rows(conn, source_id, "passage-triage", "passage"),
        _usable_passage_triage,
    )
    stages["passage-triage"] = _stage_facts("passage-triage", passages, *tri)
    tri_answers = tri[0]
    kept_passages = [
        p for p in passages
        if p in tri_answers and tri_answers[p]["answer"]["verdict"] == PASSAGE_KEEP
    ]

    gen = _fold(
        _stage_rows(conn, source_id, "task-generation", "passage"), _usable_any
    )
    stages["task-generation"] = _stage_facts("task-generation", kept_passages, *gen)

    # This source's tasks: originals from current-generation task-generation
    # run items on kept passages (a superseded experiment's tasks, or tasks
    # of a passage triage now calls filler, are not targets), and parts from
    # task-granularity run items (keyed by the item that split them).
    kept_set = set(kept_passages)
    originals: list[str] = []
    parts_by_item: dict[str, list[str]] = {}
    for task_id, run_stage, run_item_id, model, prompt_ref, passage_id in conn.execute(
        "SELECT t.id, r.stage, t.run_item_id, r.model, r.prompt_ref, t.passage_id"
        " FROM task t JOIN run_item i ON i.id = t.run_item_id"
        " JOIN run r ON r.id = i.run_id"
        " JOIN passage p ON p.id = t.passage_id"
        " JOIN artifact a ON a.id = p.artifact_id"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s ORDER BY t.id",
        (source_id,),
    ).fetchall():
        if run_stage == "task-generation":
            if (
                passage_id in kept_set
                and defaults.run_generation(run_stage, model, prompt_ref) == "current"
            ):
                originals.append(task_id)
        elif run_stage == "task-granularity":
            parts_by_item.setdefault(run_item_id, []).append(task_id)

    gran = _fold(
        _stage_rows(conn, source_id, "task-granularity", "task"),
        _usable_dict(granularity_of),
    )
    stages["task-granularity"] = _stage_facts("task-granularity", originals, *gran)
    gran_answers = gran[0]

    # Post-split survivors: composites are replaced by the parts their newest
    # usable granularity answer materialized.
    survivors: list[str] = []
    for task_id in originals:
        chosen = gran_answers.get(task_id)
        if chosen and chosen["answer"]["verdict"] == "composite":
            survivors.extend(parts_by_item.get(chosen["item_id"], []))
        else:
            survivors.append(task_id)

    rev = _fold(
        _stage_rows(conn, source_id, "task-revision", "task"),
        _usable_dict(revision_of),
    )
    stages["task-revision"] = _stage_facts("task-revision", survivors, *rev)
    rev_answers = rev[0]
    not_dropped = [
        t for t in survivors
        if not (t in rev_answers and rev_answers[t]["answer"]["verdict"] == "unfixable")
    ]

    ttr = _fold(
        _stage_rows(conn, source_id, "task-triage", "task"), _usable_task_triage
    )
    stages["task-triage"] = _stage_facts("task-triage", not_dropped, *ttr)
    ttr_answers = ttr[0]
    supported = [
        t for t in not_dropped
        if t in ttr_answers and ttr_answers[t]["answer"]["verdict"] == "supported"
    ]

    sub = _fold(
        _stage_rows(conn, source_id, "task-substance", "task"),
        _usable_dict(substance_of),
    )
    stages["task-substance"] = _stage_facts("task-substance", supported, *sub)
    sub_answers = sub[0]
    kept_tasks = [
        t for t in supported
        if t in sub_answers
        and sub_answers[t]["answer"]["verdict"] not in SUBSTANCE_DROPPED
    ]

    statement_rows = _stage_rows(conn, source_id, "kc-statement", "task")
    stmt = _fold(statement_rows, _usable_dict(statement_of))
    stages["kc-statement"] = _stage_facts("kc-statement", kept_tasks, *stmt)

    for stage_name, usable in (
        ("task-modality", _usable_dict(modality_of)),
        ("task-knowledge", _usable_dict(knowledge_of)),
        ("task-embedding", _usable_any),
    ):
        folded = _fold(_stage_rows(conn, source_id, stage_name, "task"), usable)
        stages[stage_name] = _stage_facts(stage_name, kept_tasks, *folded)

    stated = _stated_tasks(statement_rows)
    judge_facts, newest_verdict_at, newest_build_key = _judge_facts(conn, stated)
    stages["kc-judge"] = judge_facts
    stages["grouped"] = _grouped_facts(
        conn, stated, newest_verdict_at, newest_build_key
    )
    return stages


def _stated_tasks(statement_rows: list[tuple]) -> list[str]:
    """Tasks whose newest usable current-generation statement is stated."""
    current_rows = [
        row for row in statement_rows
        if defaults.run_generation("kc-statement", row[5], row[6]) == "current"
    ]
    answers, _, _ = _fold(current_rows, _usable_dict(statement_of))
    return sorted(
        task_id
        for task_id, folded in answers.items()
        if folded["answer"]["verdict"] == "stated"
    )


def _judge_facts(
    conn: psycopg.Connection, stated: list[str]
) -> tuple[dict, object, str | None]:
    """Judge coverage over the currently-stated tasks, plus the newest verdict.

    Judge run items are pair-scoped (artifact_id NULL), so coverage is read
    from the verdict ledger itself: a stated task is done when at least one
    current-generation verdict names it.  Returns the facts and the newest
    verdict timestamp touching these tasks (any generation), which is what
    the grouping snapshot must postdate.
    """
    newest_run = conn.execute(
        "SELECT id, model, prompt_ref FROM run WHERE stage = 'kc-judge'"
        " ORDER BY started_at DESC, id DESC LIMIT 1"
    ).fetchone()
    run_id, model, prompt_ref = newest_run or (None, None, None)

    judged: set[str] = set()
    newest_verdict_at = None
    newest_build_key = None
    if stated:
        default = defaults.STAGE_DEFAULTS["kc-judge"]
        default_model = defaults.bare_model(default["model"])
        stated_set = set(stated)
        for task_a, task_b, judge_model, judge_prompt, build_key, created_at in conn.execute(
            "SELECT task_a_id, task_b_id, judge_model, judge_prompt, build_key, created_at"
            " FROM kc_verdict WHERE task_a_id = ANY(%s) OR task_b_id = ANY(%s)",
            (stated, stated),
        ).fetchall():
            if newest_verdict_at is None or created_at > newest_verdict_at:
                newest_verdict_at = created_at
                newest_build_key = build_key
            if (
                defaults.bare_model(judge_model) == default_model
                and judge_prompt == default["prompt_ref"]
            ):
                judged.update({task_a, task_b} & stated_set)

    done, total = len(judged), len(stated)
    if total == 0:
        status = "pending"
    elif done == total:
        status = "done"
    elif done:
        status = "partial"
    else:
        status = "pending"
    facts = {
        "status": status,
        "run_id": run_id,
        "done": done,
        "total": total,
        "generation": defaults.run_generation("kc-judge", model, prompt_ref) if run_id else None,
    }
    return facts, newest_verdict_at, newest_build_key


def _grouped_facts(
    conn: psycopg.Connection,
    stated: list[str],
    newest_verdict_at,
    newest_build_key: str | None,
) -> dict:
    """Grouping snapshot freshness for this source's stated tasks.

    Most stated tasks are legitimately singletons (a task in no group is its
    own KC), so membership is information, not the completion criterion: the
    stage is done when the latest snapshot postdates every verdict touching
    these tasks, pending when a newer verdict exists than the snapshot.
    """
    latest = conn.execute(
        "SELECT id, computed_at, params FROM kc_grouping"
        " ORDER BY computed_at DESC, id DESC LIMIT 1"
    ).fetchone()
    members = 0
    if latest and stated:
        members = conn.execute(
            "SELECT count(DISTINCT task_id) FROM kc_group_member"
            " WHERE grouping_id = %s AND task_id = ANY(%s)",
            (latest[0], stated),
        ).fetchone()[0]
    total = len(stated)
    if total == 0 or latest is None or newest_verdict_at is None:
        status = "pending"
    elif (
        latest[1] >= newest_verdict_at
        and (
            not latest[2].get("build_key")
            or latest[2].get("build_key") == newest_build_key
        )
        and not (
        latest[2].get("build_key")
        and grouping_staleness(
            conn,
            {"id": latest[0], "computed_at": latest[1], "params": latest[2]},
        )[0]
        )
    ):
        status = "done"
    else:
        status = "pending"
    return {
        "status": status,
        "run_id": None,
        "done": members,
        "total": total,
        "generation": None,
    }


def _cascade_vacuous_done(stages: OrderedDict) -> None:
    """An empty scope after a completed predecessor is vacuously complete.

    A source whose passages were all filler has nothing to generate tasks
    from; a source whose tasks were all dropped has nothing to state.  Those
    stages must read done, not eternally pending — but only once the stage
    that defines their scope has itself finished.
    """
    previous_done = False
    for index, name in enumerate(STAGE_ORDER):
        facts = stages[name]
        if (
            index >= _CASCADE_FROM
            and facts["total"] == 0
            and facts["status"] == "pending"
            and previous_done
        ):
            facts["status"] = "done"
        previous_done = facts["status"] == "done"


def attention(conn: psycopg.Connection) -> list:
    """Attention alerts: coverage gaps and acquisition failures.

    Returns list of:
    {
      'kind': 'coverage_gap' | a founder-facing acquisition failure kind,
      'title': 'Source Title',
      'note': 'Context',
      'source_id': 'source_id' or None,
      'item_id': 'syllabus_item_id'
    }

    The book_scope_missing detection (syllabus.book_scope_missing) is a
    stored fact but deliberately NOT surfaced here: the founder wants that
    warning at acquisition time, when the scope is actually needed to cut
    the book (founder decision 2026-08-03).
    """
    # One row per linked source.  A source may appear in several syllabus
    # items, but the acquisition decision is about the source itself; the
    # newest item id is retained only so the dashboard can navigate back.
    rows = conn.execute(
        "WITH latest_snapshot AS ("
        " SELECT DISTINCT ON (source_id) source_id, status, failure_note"
        " FROM source_snapshot"
        " ORDER BY source_id, created_at DESC, id DESC"
        "), latest_skip_event AS ("
        " SELECT DISTINCT ON (subject->>'source_id')"
        "  subject->>'source_id' AS source_id, action"
        " FROM curation_event"
        " WHERE action = ANY(%s)"
        " ORDER BY subject->>'source_id', created_at DESC,"
        "  substring(id from '[0-9]+$')::int DESC NULLS LAST, id DESC"
        ")"
        " SELECT s.id, s.title,"
        "  (array_agg(si.id ORDER BY si.created_at DESC, si.id DESC))[1],"
        "  sn.status, sn.failure_note"
        " FROM source s"
        " JOIN syllabus_item si ON si.source_id = s.id"
        " LEFT JOIN latest_snapshot sn ON sn.source_id = s.id"
        " LEFT JOIN latest_skip_event se ON se.source_id = s.id"
        " WHERE se.action IS DISTINCT FROM %s"
        " GROUP BY s.id, s.title, sn.status, sn.failure_note"
        " HAVING sn.status IS NULL OR sn.status = 'failed'"
        " ORDER BY s.id",
        (list(curation.SOURCE_SKIP_ACTIONS), curation.SOURCE_SKIP_ACTION),
    ).fetchall()
    failed_source_ids = [
        source_id for source_id, _, _, status, _ in rows if status == "failed"
    ]
    gate_reports = _latest_acquisition_gate_reports(conn, failed_source_ids)

    alerts = []
    for source_id, title, item_id, status, failure_note in rows:
        if status is None:
            kind = "coverage_gap"
            note = "This source has not been acquired yet."
        else:
            kind, note = _acquisition_attention_fact(
                gate_reports.get(source_id), failure_note
            )
        alerts.append(
            {
                "kind": kind,
                "title": title,
                "note": note,
                "source_id": source_id,
                "item_id": item_id,
            }
        )
    return alerts


def _latest_acquisition_gate_reports(
    conn: psycopg.Connection, source_ids: list[str]
) -> dict[str, dict]:
    """Newest acquisition gate report for each source in ``source_ids``.

    Failed acquisition items have no artifact to lead back to their source.
    Acquisition records source ids and run items in matching order, so the
    two ordered ledgers are paired here without inventing a mutable link.
    """
    if not source_ids:
        return {}
    rows = conn.execute(
        "SELECT r.id, r.params->'source_ids', i.response,"
        " row_number() OVER (PARTITION BY r.id ORDER BY i.id)"
        " FROM run r JOIN run_item i ON i.run_id = r.id"
        " WHERE r.stage = 'acquisition'"
        "   AND r.params->'source_ids' ?| %s"
        " ORDER BY r.started_at DESC, r.id DESC, i.id",
        (source_ids,),
    ).fetchall()
    wanted = set(source_ids)
    reports: dict[str, dict] = {}
    for _run_id, run_source_ids, response, position in rows:
        if not isinstance(run_source_ids, list) or position > len(run_source_ids):
            continue
        source_id = run_source_ids[position - 1]
        if source_id not in wanted or source_id in reports:
            continue
        try:
            report = json.loads(response)
        except (TypeError, json.JSONDecodeError):
            continue
        if isinstance(report, dict):
            reports[source_id] = report
    return reports


def _acquisition_attention_fact(
    gate_report: dict | None, snapshot_failure_code: str | None
) -> tuple[str, str]:
    """Translate recorded gate facts into a founder-facing kind and note."""
    failures = gate_report.get("failures") if gate_report else None
    code = failures[0] if isinstance(failures, list) and failures else None
    kind = _ACQUISITION_KIND_BY_GATE.get(code, "acquisition_failed")
    description = GATE_CODES.get(code, {}).get("description")
    if description is None and gate_report is None:
        description = GATE_CODES.get(snapshot_failure_code, {}).get("description")
    return kind, description or "The source could not be acquired."
