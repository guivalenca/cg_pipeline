"""Internal progress projection for the Markdown-to-KC Module.

Pure SQL reads over the content ledger and model runs compute completion for
the current Markdown artifact of each source. Historical artifacts remain
immutable facts but never leak back into today's processing scope.

Multi-reference consumers use the smallest union of runs whose newest usable
answers cover their scope. Singular-reference consumers require one coherent
run covering that exact scope; disjoint retry fragments remain partial rather
than becoming an unreproducible downstream input. The units in scope for a
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

from universe import kc_corpus_manifest, pipeline_lease
from universe.blocks import BLOCKER_VERSION
from universe.effective_evidence import effective_task_manifest_sha, resolve_chain
from universe.kc_canonical_statement import canonicalization_of
from universe.kc_statement import statement_of
from universe.pipeline_scope import (
    completed_judge_build_for_inputs,
    current_publication_artifacts,
    eligible_run_ids,
    exact_embedding_run,
    grouping_for_judge_manifest,
    ordered_unique,
)
from universe.run_overlay import fold_newest_usable
from universe.recipe_identity import matches_recipe
from universe.task_granularity import granularity_of
from universe.task_knowledge import knowledge_of
from universe.task_modality import modality_of
from universe.task_revision import revision_of
from universe.task_substance import DROPPED as SUBSTANCE_DROPPED
from universe.task_substance import substance_of
from universe.taskgen import KEEP as PASSAGE_KEEP
from universe.taskgen import tasks_of
from universe.triage import verdict_of as passage_verdict_of


LOCAL_STAGE_ORDER = [
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
]

SHARED_STAGE_ORDER = [
    "task-embedding",
    "kc-judge",
    "grouped",
    "kc-canonical-statement",
]

# Retained as the stable semantic ordering; projections expose one side of the
# target boundary at a time instead of grafting shared state onto every Source.
STAGE_ORDER = [*LOCAL_STAGE_ORDER, *SHARED_STAGE_ORDER]

# Stages before this index carry their own scope semantics; from here on an
# empty scope means "nothing left to do" once the previous stage completed.
_CASCADE_FROM = STAGE_ORDER.index("passage-triage")

_TASK_TRIAGE_VERDICTS = {"supported", "unsupported", "unsure"}

# These outputs are consumed through singular CLI references. A retry union
# may preserve useful work for diagnostics, but it is not a coherent input to
# the next stage: one completed run must cover the exact current scope.
_COHERENT_RUN_STAGES = {
    "task-granularity",
    "task-revision",
    "task-triage",
    "task-substance",
    "task-embedding",
}

_NO_EFFECTIVE_MANIFEST = object()

def source_progress(
    conn: psycopg.Connection,
    *,
    ignore_lease_token: str | None = None,
) -> dict:
    """Progress of each current Source Publication through 11 local stages.

    Returns dict keyed by source_id:
    {
      'source_id': {
        'id': 'source_id',
        'title': 'title',
        'media_type': 'media_type',
        'stages': OrderedDict([
          ('blocks', {'status': '...', 'run_id': None, 'done': N,
                        'total': M, 'generation': '...' | None}),
          ...
        ])
      }
    }

    Status semantics:
    - 'done': every unit has a reproducible witness for its consumer shape
    - 'partial': some units covered
    - 'failed': attempts exist but no unit has a usable answer
    - 'pending': nothing attempted yet
    """
    current = current_publication_artifacts(conn)
    result = {}
    for source_id, artifact_id in current.items():
        source, _ = _publication_progress(
            conn,
            source_id=source_id,
            artifact_id=artifact_id,
            include_lease=True,
            ignore_lease_token=ignore_lease_token,
        )
        result[source_id] = source
    return result


def publication_progress(
    conn: psycopg.Connection,
    *,
    source_id: str,
    artifact_id: str,
    ignore_lease_token: str | None = None,
) -> dict:
    """Project one exact Source Publication, including an explicit history pin."""
    source, _ = _publication_progress(
        conn,
        source_id=source_id,
        artifact_id=artifact_id,
        include_lease=(
            current_publication_artifacts(conn, [source_id]).get(source_id)
            == artifact_id
        ),
        ignore_lease_token=ignore_lease_token,
    )
    return source


def _publication_progress(
    conn: psycopg.Connection,
    *,
    source_id: str,
    artifact_id: str,
    include_lease: bool,
    ignore_lease_token: str | None = None,
) -> tuple[dict, list[str]]:
    """Project the exact artifact named by one Publication or corpus member."""
    row = conn.execute(
        "SELECT s.title, s.media_type FROM artifact a"
        " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " JOIN source s ON s.id = sn.source_id"
        " WHERE s.id = %s AND a.id = %s AND sn.status = 'ok'"
        " AND a.kind = 'markdown'",
        (source_id, artifact_id),
    ).fetchone()
    if row is None:
        raise LookupError(
            f"artifact {artifact_id} is not a Source Publication for {source_id}"
        )
    title, media_type = row
    stages = OrderedDict()
    artifacts_with_blocks = int(
        conn.execute(
            "SELECT EXISTS (SELECT 1 FROM block"
            " WHERE artifact_id = %s AND blocker_version = %s)",
            (artifact_id, BLOCKER_VERSION),
        ).fetchone()[0]
    )
    stages["blocks"] = {
        "status": "done" if artifacts_with_blocks else "pending",
        "run_id": None,
        "done": artifacts_with_blocks,
        "total": 1,
        "generation": None,
        "input_runs": [],
        "coherent_run_id": None,
    }
    current_passages, all_passages = _current_passages(conn, artifact_id)
    stages["passage-cuts"] = _cuts_facts(
        conn, artifact_id, current_passages, all_passages
    )
    local_stages, stated = _model_stage_facts(
        conn, artifact_id, current_passages
    )
    stages.update(local_stages)

    if include_lease:
        _mark_running(
            conn,
            scope_key=f"source:{source_id}",
            stages=stages,
            ignore_lease_token=ignore_lease_token,
        )
    _cascade_vacuous_done(stages)
    return {
        "id": source_id,
        "title": title,
        "media_type": media_type,
        "artifact_id": artifact_id,
        "stages": stages,
    }, stated


def corpus_progress(
    conn: psycopg.Connection,
    manifest_id: str,
    *,
    ignore_lease_token: str | None = None,
) -> dict:
    """Project exactly four shared stages for one immutable corpus manifest."""
    manifest = kc_corpus_manifest.read(conn, manifest_id)
    if manifest is None:
        raise LookupError(f"no complete KC corpus manifest {manifest_id}")
    members = list(manifest["publications"])
    source_ids = [member["source_id"] for member in members]
    current = current_publication_artifacts(conn, source_ids)
    progress = {}
    stated_by_source = {}
    publications = []
    for member in members:
        source_id = member["source_id"]
        artifact_id = member["artifact_id"]
        source, stated = _publication_progress(
            conn,
            source_id=source_id,
            artifact_id=artifact_id,
            include_lease=current.get(source_id) == artifact_id,
            ignore_lease_token=ignore_lease_token,
        )
        progress[source_id] = source
        stated_by_source[source_id] = stated
        next_stage = next(
            (
                name
                for name in LOCAL_STAGE_ORDER
                if source["stages"][name]["status"] != "done"
            ),
            None,
        )
        publications.append(
            {
                "source_id": source_id,
                "artifact_id": artifact_id,
                "local_complete": next_stage is None,
                "next_local_stage": next_stage,
            }
        )
    ready = bool(publications) and all(
        publication["local_complete"] for publication in publications
    )
    inputs, stages = _corpus_stage_facts(
        conn,
        manifest_id=manifest_id,
        progress=progress,
        stated_by_source=stated_by_source,
        ready=ready,
    )
    grouping_id = stages["grouped"].get("grouping_id")
    stages["kc-canonical-statement"] = _canonical_facts(
        conn,
        inputs["task_ids"],
        grouping_id if stages["grouped"]["status"] == "done" else None,
    )
    _cascade_shared_vacuous_done(stages, local_complete=ready)
    _mark_running(
        conn,
        scope_key=f"corpus:{manifest_id}",
        stages=stages,
        ignore_lease_token=ignore_lease_token,
    )
    return {
        "id": manifest_id,
        "manifest_sha256": manifest["manifest_sha256"],
        "origin": manifest["origin"],
        "created_at": manifest["created_at"],
        "publications": publications,
        "ready": ready,
        **inputs,
        "stages": stages,
    }


def _empty_facts() -> dict:
    return {
        "status": "pending",
        "run_id": None,
        "done": 0,
        "total": 0,
        "generation": None,
        "input_runs": [],
        "coherent_run_id": None,
    }


def _mark_running(
    conn: psycopg.Connection,
    *,
    scope_key: str,
    stages: OrderedDict,
    ignore_lease_token: str | None = None,
) -> None:
    """Only a live, token-fenced lease makes a stage in flight.

    A historical ``run.status = running`` without a live lease is an orphan,
    not a permanent pipeline lock.  The lease expiry is the recovery seam.
    """
    for stage, facts in stages.items():
        lease = pipeline_lease.active(
            conn, scope_key=scope_key, stage=stage
        )
        if lease is None or lease.token == ignore_lease_token:
            continue
        facts["status"] = "running"
        facts["lease_token"] = lease.token
        facts["lease_owner"] = lease.owner_id
        facts["lease_expires_at"] = lease.expires_at
        row = conn.execute(
            "SELECT id FROM run WHERE stage = %s"
            " AND params#>>'{pipeline_lease,token}' = %s"
            " ORDER BY started_at DESC, id DESC LIMIT 1",
            (stage, lease.token),
        ).fetchone()
        facts["run_id"] = row[0] if row else None


def _current_passages(conn: psycopg.Connection, artifact_id: str) -> tuple[list[str], int]:
    """Passages a current-generation cuts run materialized, plus the overall count.

    The pipeline's scope is the current interpretation of the source: a
    passage only a superseded experiment ever cut is history, not a target
    (the same rule orchestration applies when it wires runs together).
    """
    runs = eligible_run_ids(
        conn, "passage-cuts", artifact_id=artifact_id, statuses=("done",)
    )
    if not runs:
        all_passages = conn.execute(
            "SELECT count(*) FROM passage WHERE artifact_id = %s",
            (artifact_id,),
        ).fetchone()[0]
        return [], all_passages
    rows = conn.execute(
        "SELECT p.id FROM passage p"
        " JOIN passage_origin po ON po.passage_id = p.id"
        " JOIN run r ON r.id = po.run_id"
        " WHERE p.artifact_id = %s AND r.id = ANY(%s)",
        (artifact_id, runs),
    ).fetchall()
    current: set[str] = set()
    seen: set[str] = set()
    for passage_id, in rows:
        seen.add(passage_id)
        # ``eligible_run_ids`` already applied the complete semantic recipe.
        current.add(passage_id)
    return sorted(current), len(seen)


def _cuts_facts(
    conn: psycopg.Connection,
    artifact_id: str,
    current_passages: list[str],
    all_passages: int,
) -> dict:
    """Passage-cuts progress: current-recipe passages plus the newest run badge."""
    runs = eligible_run_ids(
        conn, "passage-cuts", artifact_id=artifact_id, statuses=("done",)
    )
    run_id = runs[-1] if runs else None
    covered = len(current_passages)
    return {
        # A source cut only by superseded recipes still needs the current
        # cut; the stage stays open and the badge names the stale run.
        "status": "done" if covered else "pending",
        "run_id": run_id,
        "done": covered,
        "total": covered if covered else all_passages,
        "generation": "current" if run_id else None,
        # Passage interpretations are additive: all pure current cuts remain
        # part of the exact downstream passage scope.
        "input_runs": runs,
        "coherent_run_id": None,
    }


# --- union-of-runs stage facts ----------------------------------------------


def _usable_dict(parser):
    """A parser that accepts an item when the stage parser returns a dict."""
    def usable(item: dict) -> dict | None:
        parsed = parser(item)
        return parsed if isinstance(parsed, dict) else None
    return usable


def _usable_any(item: dict) -> dict | None:
    """Stages whose mere non-error answer is the fact (embedding)."""
    return {} if item["error"] is None and item["response"] is not None else None


def _usable_task_generation(item: dict) -> dict | None:
    """Only the same task list the publisher can materialize is coverage."""
    parsed = tasks_of(item)
    return {"tasks": parsed} if isinstance(parsed, list) else None


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
    conn: psycopg.Connection,
    artifact_id: str,
    stage: str,
    unit: str,
    *,
    effective_manifest_sha: str | None | object = _NO_EFFECTIVE_MANIFEST,
) -> list[tuple]:
    """Items from pure, current, completed runs for this exact artifact."""
    runs = eligible_run_ids(
        conn,
        stage,
        artifact_id=None if stage == "task-embedding" else artifact_id,
        statuses=("done",),
    )
    if effective_manifest_sha is not _NO_EFFECTIVE_MANIFEST:
        if effective_manifest_sha is None:
            return []
        runs = [
            run_id
            for run_id, in conn.execute(
                "SELECT id FROM run WHERE id = ANY(%s)"
                " AND params->>'effective_task_manifest_sha' = %s",
                (runs, effective_manifest_sha),
            ).fetchall()
        ]
    if not runs:
        return []
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
        " WHERE r.id = ANY(%s) AND p.artifact_id = %s"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (runs, artifact_id),
    ).fetchall()


def _basic_stage_facts(
    stage: str,
    scope,
    answers: dict,
    attempted: set,
    newest: tuple,
) -> dict:
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
        # Every row reached this projection through ``eligible_run_ids``.
        "generation": "current" if run_id else None,
        "input_runs": [],
        "coherent_run_id": None,
    }


def _project_stage(
    stage: str,
    scope: list[str],
    rows: list[tuple],
    usable,
    *,
    additive: bool = False,
) -> tuple[dict, dict]:
    """Project coverage and the exact run witness safe for downstream use.

    A run with an item outside ``scope`` is rejected wholesale. For stages
    consumed through a singular reference, union coverage remains visible but
    cannot close the stage until one completed run covers the whole scope.
    """
    scope_set = set(scope)
    rows_by_run: dict[str, list[tuple]] = {}
    run_order_newest: list[str] = []
    for row in rows:
        run_id = row[4]
        if run_id not in rows_by_run:
            rows_by_run[run_id] = []
            run_order_newest.append(run_id)
        rows_by_run[run_id].append(row)

    safe_runs = [
        run_id
        for run_id in run_order_newest
        if rows_by_run[run_id]
        and {row[0] for row in rows_by_run[run_id]} <= scope_set
    ]
    safe_run_set = set(safe_runs)
    safe_rows = [row for row in rows if row[4] in safe_run_set]
    answers, attempted, newest = fold_newest_usable(safe_rows, usable)

    per_run_answers = {
        run_id: fold_newest_usable(rows_by_run[run_id], usable)[0]
        for run_id in safe_runs
    }
    coherent_run = next(
        (
            run_id
            for run_id in safe_runs
            if scope_set <= set(per_run_answers[run_id])
        ),
        None,
    )
    requires_coherent = stage in _COHERENT_RUN_STAGES
    chosen_answers = (
        per_run_answers[coherent_run]
        if requires_coherent and coherent_run is not None
        else answers
    )
    facts = _basic_stage_facts(stage, scope, answers, attempted, newest)
    if requires_coherent and scope_set:
        if coherent_run is not None:
            facts["status"] = "done"
            facts["run_id"] = coherent_run
            facts["done"] = len(scope_set)
        elif facts["status"] == "done":
            # Useful retry fragments exist, but no singular downstream input
            # can reproduce their union.
            facts["status"] = "partial"
    if additive:
        input_runs = list(reversed(safe_runs))
    elif requires_coherent:
        input_runs = [coherent_run] if coherent_run else []
    else:
        witness = {answer["run_id"] for answer in chosen_answers.values()}
        input_runs = [
            run_id for run_id in reversed(safe_runs) if run_id in witness
        ]
    facts["input_runs"] = input_runs
    facts["coherent_run_id"] = coherent_run
    return facts, chosen_answers


def _effective_manifest_for_scope(
    conn: psycopg.Connection,
    *,
    generation_runs: list[str],
    granularity_runs: list[str],
    revision_runs: list[str],
    task_ids: list[str],
) -> str | None:
    """Hash today's resolved task evidence, or fail closed if incoherent."""
    if task_ids and (
        not generation_runs or not granularity_runs or not revision_runs
    ):
        return None
    try:
        tasks = resolve_chain(
            conn,
            generation_runs=generation_runs,
            granularity_runs=granularity_runs,
            revision_runs=revision_runs,
            task_ids=task_ids,
        )
    except RuntimeError:
        return None
    return effective_task_manifest_sha(tasks)


def _model_stage_facts(
    conn: psycopg.Connection, artifact_id: str, passages: list[str]
) -> tuple[OrderedDict, list[str]]:
    """Source-local witness facts through the statement/axis stages.

    ``passages`` is the current-recipe scope: what a current-generation cuts
    run materialized for this source.
    """
    stages: OrderedDict[str, dict] = OrderedDict()

    tri_facts, tri_answers = _project_stage(
        "passage-triage",
        passages,
        _stage_rows(conn, artifact_id, "passage-triage", "passage"),
        _usable_passage_triage,
    )
    stages["passage-triage"] = tri_facts
    kept_passages = [
        p for p in passages
        if p in tri_answers and tri_answers[p]["answer"]["verdict"] == PASSAGE_KEEP
    ]

    gen_facts, _ = _project_stage(
        "task-generation",
        kept_passages,
        _stage_rows(conn, artifact_id, "task-generation", "passage"),
        _usable_task_generation,
    )
    stages["task-generation"] = gen_facts

    # This source's tasks: originals from current-generation task-generation
    # run items on kept passages (a superseded experiment's tasks, or tasks
    # of a passage triage now calls filler, are not targets), and parts from
    # task-granularity run items (keyed by the item that split them).
    kept_set = set(kept_passages)
    originals: list[str] = []
    parts_by_item: dict[str, list[str]] = {}
    generation_runs = stages["task-generation"]["input_runs"]
    for (
        task_id,
        run_id,
        run_stage,
        run_item_id,
        passage_id,
    ) in conn.execute(
        "SELECT t.id, r.id, r.stage, t.run_item_id, t.passage_id"
        " FROM task t JOIN run_item i ON i.id = t.run_item_id"
        " JOIN run r ON r.id = i.run_id"
        " JOIN passage p ON p.id = t.passage_id"
        " WHERE p.artifact_id = %s ORDER BY t.id",
        (artifact_id,),
    ).fetchall():
        if run_stage == "task-generation":
            if (
                run_id in generation_runs
                and passage_id in kept_set
            ):
                originals.append(task_id)
        elif run_stage == "task-granularity":
            parts_by_item.setdefault(run_item_id, []).append(task_id)

    gran_facts, gran_answers = _project_stage(
        "task-granularity",
        originals,
        _stage_rows(conn, artifact_id, "task-granularity", "task"),
        _usable_dict(granularity_of),
    )
    stages["task-granularity"] = gran_facts

    # Post-split survivors: composites are replaced by the parts their newest
    # usable granularity answer materialized.
    survivors: list[str] = []
    for task_id in originals:
        chosen = gran_answers.get(task_id)
        if chosen and chosen["answer"]["verdict"] == "composite":
            survivors.extend(parts_by_item.get(chosen["item_id"], []))
        else:
            survivors.append(task_id)

    rev_facts, rev_answers = _project_stage(
        "task-revision",
        survivors,
        _stage_rows(conn, artifact_id, "task-revision", "task"),
        _usable_dict(revision_of),
    )
    stages["task-revision"] = rev_facts
    not_dropped = [
        t for t in survivors
        if not (t in rev_answers and rev_answers[t]["answer"]["verdict"] == "unfixable")
    ]
    chain = {
        "generation_runs": generation_runs,
        "granularity_runs": stages["task-granularity"]["input_runs"],
        "revision_runs": stages["task-revision"]["input_runs"],
    }
    triage_manifest = (
        _effective_manifest_for_scope(conn, **chain, task_ids=not_dropped)
        if rev_facts["status"] == "done"
        else None
    )

    triage_facts, ttr_answers = _project_stage(
        "task-triage",
        not_dropped,
        _stage_rows(
            conn,
            artifact_id,
            "task-triage",
            "task",
            effective_manifest_sha=triage_manifest,
        ),
        _usable_task_triage,
    )
    stages["task-triage"] = triage_facts
    supported = [
        t for t in not_dropped
        if t in ttr_answers and ttr_answers[t]["answer"]["verdict"] == "supported"
    ]
    substance_manifest = (
        _effective_manifest_for_scope(conn, **chain, task_ids=supported)
        if triage_facts["status"] == "done"
        else None
    )

    substance_facts, sub_answers = _project_stage(
        "task-substance",
        supported,
        _stage_rows(
            conn,
            artifact_id,
            "task-substance",
            "task",
            effective_manifest_sha=substance_manifest,
        ),
        _usable_dict(substance_of),
    )
    stages["task-substance"] = substance_facts
    kept_tasks = [
        t for t in supported
        if t in sub_answers
        and sub_answers[t]["answer"]["verdict"] not in SUBSTANCE_DROPPED
    ]
    downstream_manifest = (
        _effective_manifest_for_scope(conn, **chain, task_ids=kept_tasks)
        if substance_facts["status"] == "done"
        else None
    )

    statement_rows = _stage_rows(
        conn,
        artifact_id,
        "kc-statement",
        "task",
        effective_manifest_sha=downstream_manifest,
    )
    statement_facts, statement_answers = _project_stage(
        "kc-statement",
        kept_tasks,
        statement_rows,
        _usable_dict(statement_of),
    )
    stages["kc-statement"] = statement_facts

    stated = sorted(
        task_id
        for task_id, folded in statement_answers.items()
        if folded["answer"]["verdict"] == "stated"
    )

    # The axis CLIs classify every task left by substance. A statement may
    # deliberately answer ``unsure`` and stay out of grouping, but it remains
    # part of the exact source-local axis manifest.
    for stage_name, usable in (
        ("task-modality", _usable_dict(modality_of)),
        ("task-knowledge", _usable_dict(knowledge_of)),
    ):
        facts, _ = _project_stage(
            stage_name,
            kept_tasks,
            _stage_rows(
                conn,
                artifact_id,
                stage_name,
                "task",
                effective_manifest_sha=downstream_manifest,
            ),
            usable,
        )
        stages[stage_name] = facts
    return stages, stated


def _corpus_stage_facts(
    conn: psycopg.Connection,
    *,
    manifest_id: str,
    progress: dict,
    stated_by_source: dict[str, list[str]],
    ready: bool,
) -> tuple[dict, dict[str, dict]]:
    """Select shared witnesses only from the manifest's complete members."""
    participants = list(progress.values()) if ready else []
    task_ids = sorted({
        task_id
        for source in participants
        for task_id in stated_by_source[source["id"]]
    })
    if ready:
        statement_runs = ordered_unique(
            source["stages"]["kc-statement"]["input_runs"]
            for source in participants
        )
        modality_runs = ordered_unique(
            source["stages"]["task-modality"]["input_runs"]
            for source in participants
        )
        knowledge_runs = ordered_unique(
            source["stages"]["task-knowledge"]["input_runs"]
            for source in participants
        )
    else:
        statement_runs = []
        modality_runs = []
        knowledge_runs = []

    embedding_run = None
    if ready and task_ids:
        embedding_run = exact_embedding_run(
            conn,
            statement_runs=statement_runs,
            task_ids=set(task_ids),
            corpus_manifest_id=manifest_id,
        )
    expected = None
    if embedding_run is not None:
        expected = {
            "statements_from": statement_runs,
            "embedding_run": embedding_run,
            "modality_runs": modality_runs,
            "knowledge_runs": knowledge_runs,
        }
    judge = (
        completed_judge_build_for_inputs(conn, expected)
        if expected is not None
        else None
    )
    grouping = grouping_for_judge_manifest(conn, judge)

    total = len(task_ids)
    embedding_facts = {
        "status": "done" if embedding_run else "pending",
        "run_id": embedding_run,
        "done": total if embedding_run else 0,
        "total": total,
        "generation": "manifest" if embedding_run else None,
        "input_runs": [embedding_run] if embedding_run else [],
        "coherent_run_id": embedding_run,
        "manifest_ready": ready,
    }
    judge_facts = {
        "status": "done" if judge else "pending",
        "run_id": judge["run_id"] if judge else None,
        "done": total if judge else 0,
        "total": total,
        "generation": "manifest" if judge else None,
        "input_runs": [judge["run_id"]] if judge else [],
        "coherent_run_id": judge["run_id"] if judge else None,
        "build_key": judge["build_key"] if judge else None,
        "candidate_count": judge["candidate_count"] if judge else None,
        "candidate_manifest_sha256": (
            judge["candidate_manifest_sha256"] if judge else None
        ),
    }
    grouped_facts = {
        "status": "done" if grouping else "pending",
        "run_id": None,
        "done": total if grouping else 0,
        "total": total,
        "generation": None,
        "input_runs": [],
        "coherent_run_id": None,
        "build_key": judge["build_key"] if judge else None,
        "judge_run_id": judge["run_id"] if judge else None,
        "candidate_count": judge["candidate_count"] if judge else None,
        "candidate_manifest_sha256": (
            judge["candidate_manifest_sha256"] if judge else None
        ),
        "grouping_id": grouping["id"] if grouping else None,
    }
    inputs = {
        "corpus_manifest_id": manifest_id,
        "task_ids": task_ids,
        "statements_from": statement_runs,
        "embedding_run": embedding_run,
        "modality_runs": modality_runs,
        "knowledge_runs": knowledge_runs,
        "judge_run": judge["run_id"] if judge else None,
        "build_key": judge["build_key"] if judge else None,
        "candidate_count": judge["candidate_count"] if judge else None,
        "candidate_manifest_sha256": (
            judge["candidate_manifest_sha256"] if judge else None
        ),
        "grouping_id": grouping["id"] if grouping else None,
    }
    return inputs, {
        "task-embedding": embedding_facts,
        "kc-judge": judge_facts,
        "grouped": grouped_facts,
    }


def _canonical_facts(
    conn: psycopg.Connection,
    stated: list[str],
    grouping_id: str | None,
) -> dict:
    """Current canonical coverage for composites touching this source.

    The grouping id is explicit so a result can never drift onto a later
    membership snapshot.  Both ``stated`` and ``unsure`` responses parse to a
    dict; the latter is therefore a valid, intentionally unnamed component.
    """
    if grouping_id is None or not stated:
        return _empty_facts()
    scope = [
        row[0]
        for row in conn.execute(
            "SELECT DISTINCT group_id FROM kc_group_member"
            " WHERE grouping_id = %s AND task_id = ANY(%s) ORDER BY group_id",
            (grouping_id, stated),
        ).fetchall()
    ]
    if not scope:
        return _empty_facts()
    rows = conn.execute(
        "SELECT c.group_id, i.id, i.response, i.error,"
        " r.id, r.model, r.prompt_ref, r.prompt_sha, r.params"
        " FROM kc_canonicalization c"
        " JOIN run_item i ON i.id = c.run_item_id"
        " JOIN run r ON r.id = i.run_id"
        " WHERE c.grouping_id = %s AND c.group_id = ANY(%s)"
        " ORDER BY r.started_at DESC, i.created_at DESC, i.id DESC",
        (grouping_id, scope),
    ).fetchall()
    current_rows = [
        row[:7]
        for row in rows
        if matches_recipe(
            "kc-canonical-statement",
            model=row[5],
            prompt_ref=row[6],
            prompt_sha=row[7],
            params=row[8],
        )
    ]
    folded = fold_newest_usable(
        current_rows, _usable_dict(canonicalization_of)
    )
    facts = _basic_stage_facts("kc-canonical-statement", scope, *folded)
    facts["input_runs"] = ordered_unique(
        [[answer["run_id"]] for answer in folded[0].values()]
    )
    return facts


def _cascade_vacuous_done(stages: OrderedDict) -> None:
    """An empty scope after a completed predecessor is vacuously complete.

    A source whose passages were all filler has nothing to generate tasks
    from; a source whose tasks were all dropped has nothing to state.  Those
    stages must read done, not eternally pending — but only once the stage
    that defines their scope has itself finished.
    """
    previous_done = False
    for index, name in enumerate(STAGE_ORDER):
        if name not in stages:
            break
        facts = stages[name]
        if (
            index >= _CASCADE_FROM
            and facts["total"] == 0
            and facts["status"] == "pending"
            and previous_done
        ):
            facts["status"] = "done"
        previous_done = facts["status"] == "done"


def _cascade_shared_vacuous_done(
    stages: OrderedDict,
    *,
    local_complete: bool,
) -> None:
    """An empty shared suffix closes only after every pinned local chain."""
    previous_done = local_complete
    for name in SHARED_STAGE_ORDER:
        facts = stages[name]
        if (
            facts["total"] == 0
            and facts["status"] == "pending"
            and previous_done
        ):
            facts["status"] = "done"
        previous_done = facts["status"] == "done"
