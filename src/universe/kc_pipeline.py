"""The deep Source Publication -> Knowledge Components Module.

``SourcePublicationTarget`` advances exactly eleven local stages.
``CorpusManifestTarget`` advances exactly four shared stages over an immutable
publication set. ``next_step``, ``advance``, and ``read_snapshot`` dispatch on
that explicit target boundary; local work can never fall through into corpus
work and no shared participant is inferred from global/latest state.

The scoping rule mirrors the reference chain: passage cutting is scoped with
``--artifacts <id>``; every later per-source stage is scoped through the run ids
the chain itself produced for this source (always the current-generation runs,
so a superseded experiment never leaks back in).  The corpus-wide stages
(task-embedding, kc-judge, and canonicalization) preserve their exact ledger
or grouping scope across the whole corpus.
A stage whose scope cannot be derived safely is reported as not runnable,
with the reason — never guessed. Acquisition, syllabus interpretation, and
web presentation are intentionally outside this seam.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread

import psycopg
from universe import (
    defaults,
    kc_corpus_manifest,
    kc_progress as spine,
    pipeline_lease,
)
from universe.blocks import BLOCKER_VERSION
from universe.effective_evidence import resolve_statement_tasks
from universe.kc_canonical_statement import fetch_current_canonicalizations
from universe.kc_statement import fetch_usable_statements
from universe.pipeline_scope import completed_judge_build_for_inputs
from universe.recipe_identity import launch_recipe
from universe.source_publication import current as current_publication
from universe.source_publication import read as read_publication

PROJECT_DIR = Path(__file__).resolve().parents[2]

# Founder-plain wording; no table names.
DESCRIPTIONS = {
    "blocks": "Split the extracted text into numbered blocks",
    "passage-cuts": "Cut this source into passages",
    "passage-triage": "Sort the passages — keep substance, drop filler",
    "task-generation": "Write learner tasks from the kept passages",
    "task-granularity": "Split any task that asks several things at once",
    "task-revision": "Reword tasks that lean on text the learner cannot see",
    "task-triage": "Check each task against its source, dropping the unsupported",
    "task-substance": "Check each task could show real learning",
    "kc-statement": "State the one thing each task shows a learner knows",
    "task-modality": "Label each task: doing or explaining",
    "task-knowledge": "Label each task's knowledge: concept or procedure",
    "task-embedding": "Compute similarity vectors for the pinned corpus statements",
    "kc-judge": "Judge which pinned-corpus statements carry each other",
    "grouped": "Fold mutually-carrying statements into knowledge components",
    "kc-canonical-statement": "Name or deliberately leave unnamed each composite",
}

class StepNotRunnable(Exception):
    """The next step exists but cannot be launched by this Module."""


class StepAlreadyRunning(StepNotRunnable):
    """The selected source/corpus stage already has an in-flight launch."""


@dataclass(frozen=True, slots=True)
class SourcePublicationTarget:
    """One exact Canonical Source Markdown publication for local KC work."""

    source_id: str
    artifact_id: str


@dataclass(frozen=True, slots=True)
class CorpusManifestTarget:
    """One immutable set of Source Publications for shared KC work."""

    manifest_id: str


PipelineTarget = SourcePublicationTarget | CorpusManifestTarget


@dataclass(frozen=True, slots=True)
class _LocalPlan:
    """One source-scoped progress projection reused while planning a stage.

    ``kc_progress`` owns witness selection: additive stages expose their
    oldest-first retry union, while singular consumers expose at most one
    coherent run. Builders consume that projected answer without querying a
    broader corpus or reconstructing its semantics.
    """

    target: SourcePublicationTarget
    stages: Mapping[str, Mapping[str, object]]

    def runs(self, stage: str) -> list[str]:
        return list(self.stages.get(stage, {}).get("input_runs") or [])


def current_target(
    conn: psycopg.Connection, source_id: str
) -> SourcePublicationTarget:
    """Resolve new work at the Source Publication seam without ledger writes."""
    publication = current_publication(conn, source_id)
    if publication is None or publication.is_previous_attempt:
        raise LookupError(f"no current Source Publication for {source_id}")
    return SourcePublicationTarget(source_id, publication.artifact_id)


def _local_target(
    conn: psycopg.Connection,
    target: SourcePublicationTarget | str,
) -> SourcePublicationTarget:
    if isinstance(target, str):
        return current_target(conn, target)
    publication = current_publication(conn, target.source_id)
    if (
        publication is None
        or publication.is_previous_attempt
        or publication.artifact_id != target.artifact_id
    ):
        raise StepNotRunnable(
            "the pinned Source Publication is no longer current"
        )
    return target


def corpus_target(
    conn: psycopg.Connection,
    manifest_id: str,
) -> CorpusManifestTarget:
    """Resolve one explicit immutable corpus without deriving participants."""
    if not isinstance(manifest_id, str) or not manifest_id.strip():
        raise ValueError("manifest_id must be a non-empty string")
    if kc_corpus_manifest.read(conn, manifest_id) is None:
        raise LookupError(f"no complete KC corpus manifest {manifest_id}")
    return CorpusManifestTarget(manifest_id)


def _corpus_target(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
) -> CorpusManifestTarget:
    if not isinstance(target, CorpusManifestTarget):
        raise TypeError("shared KC work requires a CorpusManifestTarget")
    return corpus_target(conn, target.manifest_id)


# --- deciding the next step -------------------------------------------------


def _require(runs: list[str], stage: str) -> list[str]:
    if not runs:
        raise StepNotRunnable(
            f"its input — {DESCRIPTIONS[stage].lower()} — has no completed run"
            " with the current recipe; run that step first"
        )
    return runs


def _latest(plan: _LocalPlan, stage: str) -> str:
    return _require(plan.runs(stage), stage)[-1]


def _model_argv(
    module: str,
    stage: str,
    refs: list[str],
) -> tuple[list[str], str]:
    """The exact invocation of one model stage, and the model it spends on."""
    recipe = launch_recipe(stage)
    prompt = recipe["prompt_ref"].split("/", 1)[1]
    argv = [
        sys.executable,
        "-m",
        module,
        "run",
        "--prompt",
        prompt,
        "--model",
        recipe["model"],
        *refs,
        "--tool",
        recipe["tool"],
        "--workers",
        str(recipe["workers"]),
        "--max-tokens",
        str(recipe["max_tokens"]),
        "--extra",
        json.dumps(recipe["extra"]),
    ]
    return argv, recipe["model"]


def _task_refs(plan: _LocalPlan, *stages: str) -> list[str]:
    """CLI references to this source's own chain, the way the reference chain
    wired them: every current-generation task-generation run, and the latest
    current-generation run of each judging stage."""
    refs: list[str] = []
    for stage in stages:
        if stage == "task-generation":
            refs += [
                "--gen-runs",
                ",".join(_require(plan.runs(stage), stage)),
            ]
        elif stage == "task-granularity":
            refs += ["--granularity-run", _latest(plan, stage)]
        elif stage == "task-granularity-list":
            refs += ["--granularity-runs", _latest(plan, "task-granularity")]
        elif stage == "task-revision":
            refs += ["--revision-run", _latest(plan, stage)]
        elif stage == "parts-revision":
            # The reference chain revised originals and parts in one run.
            refs += ["--parts-revision-run", _latest(plan, "task-revision")]
        elif stage == "task-triage":
            refs += ["--triage-run", _latest(plan, stage)]
        elif stage == "task-substance":
            refs += ["--substance-run", _latest(plan, stage)]
        else:  # pragma: no cover - a typo in the builder table
            raise ValueError(f"unknown reference stage {stage}")
    return refs


def _build_blocks(
    conn: psycopg.Connection, plan: _LocalPlan
) -> dict:
    target = plan.target
    exists = conn.execute(
        "SELECT EXISTS (SELECT 1 FROM block"
        " WHERE artifact_id = %s AND blocker_version = %s)",
        (target.artifact_id, BLOCKER_VERSION),
    ).fetchone()[0]
    if exists:
        raise StepNotRunnable(
            "the pinned Source Publication already has current blocks"
        )
    return {
        "argv": [sys.executable, "-m", "universe.blocks", target.artifact_id],
        "model": None,
        "spends_model_calls": False,
    }


def _build_passage_cuts(
    conn: psycopg.Connection, plan: _LocalPlan
) -> dict:
    target = plan.target
    recipe = launch_recipe("passage-cuts")
    argv = [
        sys.executable, "-m", "universe.harness", "run",
        "--stage", "passage-cuts",
        "--prompt", recipe["prompt_ref"].split("/", 1)[1],
        "--model", recipe["model"],
        "--artifacts", target.artifact_id,
        "--body-from", recipe["input_contract"]["body_from"],
        "--tool", recipe["tool"],
        "--workers", str(recipe["workers"]),
        "--max-tokens", str(recipe["max_tokens"]),
        "--extra", json.dumps(recipe["extra"]),
    ]
    return {"argv": argv, "model": recipe["model"], "spends_model_calls": True}


def _build_passage_triage(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    cuts = _require(plan.runs("passage-cuts"), "passage-cuts")
    argv, model = _model_argv(
        "universe.triage", "passage-triage",
        ["--cuts-runs", ",".join(cuts)],
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_generation(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    cuts = _require(plan.runs("passage-cuts"), "passage-cuts")
    triage = _require(
        plan.runs("passage-triage"),
        "passage-triage",
    )
    previous = plan.runs("task-generation")
    refs = ["--cuts-runs", ",".join(cuts), "--triage-runs", ",".join(triage)]
    if previous:
        refs += ["--skip-runs", ",".join(previous)]
    argv, model = _model_argv(
        "universe.taskgen", "task-generation",
        refs,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_granularity(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    refs = _task_refs(plan, "task-generation")
    argv, model = _model_argv(
        "universe.task_granularity", "task-granularity", refs,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_revision(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    refs = _task_refs(plan, "task-generation", "task-granularity-list")
    argv, model = _model_argv(
        "universe.task_revision", "task-revision", refs,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_triage(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    refs = _task_refs(plan, "task-generation", "task-revision", "task-granularity")
    argv, model = _model_argv(
        "universe.task_triage", "task-triage", refs,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_substance(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    refs = _task_refs(
        plan,
        "task-generation",
        "task-revision",
        "task-granularity",
        "parts-revision",
        "task-triage",
    )
    argv, model = _model_argv(
        "universe.task_substance", "task-substance", refs,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _statement_shaped_refs(plan: _LocalPlan) -> list[str]:
    return _task_refs(
        plan,
        "task-generation", "task-revision", "task-granularity", "parts-revision",
        "task-triage", "task-substance",
    )


def _build_kc_statement(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    argv, model = _model_argv(
        "universe.kc_statement", "kc-statement",
        _statement_shaped_refs(plan),
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_modality(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    argv, model = _model_argv(
        "universe.task_modality", "task-modality",
        _statement_shaped_refs(plan),
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_knowledge(conn: psycopg.Connection, plan: _LocalPlan) -> dict:
    argv, model = _model_argv(
        "universe.task_knowledge", "task-knowledge",
        _statement_shaped_refs(plan),
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _corpus_projection(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
) -> dict:
    projection = spine.corpus_progress(conn, target.manifest_id)
    if not projection["ready"]:
        incomplete = [
            publication["source_id"]
            for publication in projection["publications"]
            if not publication["local_complete"]
        ]
        raise StepNotRunnable(
            "every Source Publication in the corpus must complete its 11 local"
            f" stages first; incomplete: {', '.join(incomplete)}"
        )
    return projection


def _build_task_embedding(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
) -> dict:
    manifest = _corpus_projection(conn, target)
    statements = _require(manifest["statements_from"], "kc-statement")
    recipe = launch_recipe("task-embedding")
    argv = [
        sys.executable, "-m", "universe.task_embedding", "run",
        "--prompt", recipe["prompt_ref"].split("/", 1)[1],
        "--model", recipe["model"],
        "--statements-from", ",".join(statements),
        "--workers", str(recipe["workers"]),
    ]
    return {"argv": argv, "model": recipe["model"], "spends_model_calls": True}


def _current_judge_inputs(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
) -> dict:
    """The coherent inputs selected by one immutable corpus manifest."""
    manifest = _corpus_projection(conn, target)
    statements = _require(manifest["statements_from"], "kc-statement")
    embedding = manifest["embedding_run"]
    if embedding is None:
        raise StepNotRunnable(
            "no single embedding run covers the exact pinned statement corpus"
        )
    modality = _require(manifest["modality_runs"], "task-modality")
    knowledge = _require(manifest["knowledge_runs"], "task-knowledge")
    return {
        "statements_from": statements,
        "embedding_run": embedding,
        "modality_runs": modality,
        "knowledge_runs": knowledge,
    }


def _completed_judge_build_for_inputs(
    conn: psycopg.Connection, expected: Mapping
) -> dict | None:
    """Newest successful current judge run for this exact input manifest."""
    return completed_judge_build_for_inputs(conn, dict(expected))


def _build_kc_judge(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
) -> dict:
    inputs = _current_judge_inputs(conn, target)
    recipe = launch_recipe("kc-judge")
    argv = [
        sys.executable, "-m", "universe.kc_judge", "run",
        "--statements-from", ",".join(inputs["statements_from"]),
        "--embedding-run", inputs["embedding_run"],
        "--modality-run", ",".join(inputs["modality_runs"]),
        "--knowledge-run", ",".join(inputs["knowledge_runs"]),
        "--workers", str(recipe["workers"]),
    ]
    return {"argv": argv, "model": recipe["model"], "spends_model_calls": True}


def _build_kc_canonical_statement(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
) -> dict:
    """Canonicalize the exact grouping selected by this corpus manifest."""
    grouping_id = _corpus_projection(conn, target)["grouping_id"]
    if grouping_id is None:
        raise StepNotRunnable(
            "no grouping snapshot matches the exact pinned corpus manifest"
        )
    recipe = launch_recipe("kc-canonical-statement")
    return {
        "argv": [
            sys.executable,
            "-m",
            "universe.kc_canonical_statement",
            "run",
            "--grouping",
            grouping_id,
            "--model",
            recipe["model"],
            "--workers",
            str(recipe["workers"]),
            "--max-tokens",
            str(recipe["max_tokens"]),
        ],
        "model": recipe["model"],
        "spends_model_calls": True,
    }


def _build_grouped(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
) -> dict:
    """Materialize one immutable clique snapshot for the pinned judge build."""
    expected = _current_judge_inputs(conn, target)
    completed = _completed_judge_build_for_inputs(conn, expected)
    if completed is None:
        raise StepNotRunnable(
            "no completed KC judge run matches the exact pinned corpus manifest"
        )
    return {
        "argv": [
            sys.executable,
            "-m",
            "universe.kc_groups",
            "compute",
            "--judge-run",
            completed["run_id"],
        ],
        "model": None,
        "spends_model_calls": False,
    }


LOCAL_BUILDERS = {
    "blocks": _build_blocks,
    "passage-cuts": _build_passage_cuts,
    "passage-triage": _build_passage_triage,
    "task-generation": _build_task_generation,
    "task-granularity": _build_task_granularity,
    "task-revision": _build_task_revision,
    "task-triage": _build_task_triage,
    "task-substance": _build_task_substance,
    "kc-statement": _build_kc_statement,
    "task-modality": _build_task_modality,
    "task-knowledge": _build_task_knowledge,
}

SHARED_BUILDERS = {
    "task-embedding": _build_task_embedding,
    "kc-judge": _build_kc_judge,
    "grouped": _build_grouped,
    "kc-canonical-statement": _build_kc_canonical_statement,
}

LOCAL_STAGES = tuple(spine.LOCAL_STAGE_ORDER)
SHARED_STAGES = tuple(spine.SHARED_STAGE_ORDER)
LEASE_TTL_SECONDS = pipeline_lease.DEFAULT_TTL_SECONDS


def _scope_key(target: PipelineTarget, stage: str) -> str:
    if isinstance(target, CorpusManifestTarget):
        return f"corpus:{target.manifest_id}"
    return f"source:{target.source_id}"


def _acquire_lease(
    conn: psycopg.Connection,
    *,
    scope_key: str,
    stage: str,
    owner_id: str,
    ttl_seconds: float = LEASE_TTL_SECONDS,
) -> pipeline_lease.Lease | None:
    """Atomic lease Adapter retained as a narrow test/operations seam."""
    return pipeline_lease.acquire(
        conn,
        scope_key=scope_key,
        stage=stage,
        owner_id=owner_id,
        ttl_seconds=ttl_seconds,
    )


def _heartbeat_lease(
    conn: psycopg.Connection,
    lease: pipeline_lease.Lease,
    *,
    ttl_seconds: float = LEASE_TTL_SECONDS,
) -> bool:
    return (
        pipeline_lease.heartbeat(conn, lease, ttl_seconds=ttl_seconds)
        is not None
    )


def _release_lease(
    conn: psycopg.Connection,
    lease: pipeline_lease.Lease,
) -> bool:
    return pipeline_lease.release(conn, lease)


def next_step(
    conn: psycopg.Connection,
    target: PipelineTarget | str,
) -> dict:
    """Plan one stage inside the boundary named by the explicit target.

    Strings resolve only as Source ids. Shared planning therefore always
    requires ``CorpusManifestTarget`` and cannot happen as a local fallthrough.
    """
    if isinstance(target, CorpusManifestTarget):
        return _plan_corpus_step(conn, _corpus_target(conn, target))
    return _plan_step(conn, _local_target(conn, target))


def _plan_step(
    conn: psycopg.Connection,
    target: SourcePublicationTarget,
    *,
    ignore_lease_token: str | None = None,
) -> dict:
    """Private planner that can revalidate the lease it just acquired."""
    target = _local_target(conn, target)
    progress = spine.publication_progress(
        conn,
        source_id=target.source_id,
        artifact_id=target.artifact_id,
        ignore_lease_token=ignore_lease_token,
    )
    plan = _LocalPlan(target, progress["stages"])
    stages = plan.stages
    stage = next(
        (name for name in LOCAL_STAGES if stages[name]["status"] != "done"),
        None,
    )
    if stage is None:
        return {
            "stage": None,
            "stage_status": "complete",
            "runnable": False,
            "description": "Every local stage is complete for this Source Publication.",
            "model": None,
            "spends_model_calls": False,
            "argv": None,
            "reason": None,
        }
    step = {
        "stage": stage,
        "stage_status": stages[stage]["status"],
        "runnable": False,
        "description": DESCRIPTIONS.get(stage, stage),
        "model": None,
        "spends_model_calls": False,
        "argv": None,
        "reason": None,
    }
    if stages[stage]["status"] == "running":
        running_run = stages[stage].get("run_id")
        step["reason"] = (
            f"{DESCRIPTIONS.get(stage, stage)} is already running"
            + (f" ({running_run})" if running_run else "")
        )
        return step
    try:
        built = LOCAL_BUILDERS[stage](conn, plan)
    except StepNotRunnable as exc:
        step["reason"] = str(exc)
        return step
    step.update(built)
    step["runnable"] = True
    step["model"] = defaults.bare_model(step["model"]) if step["model"] else None
    return step


def _plan_corpus_step(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
    *,
    ignore_lease_token: str | None = None,
) -> dict:
    """Plan one of exactly four stages against the pinned corpus members."""
    target = _corpus_target(conn, target)
    progress = spine.corpus_progress(
        conn,
        target.manifest_id,
        ignore_lease_token=ignore_lease_token,
    )
    stages = progress["stages"]
    stage = next(
        (name for name in SHARED_STAGES if stages[name]["status"] != "done"),
        None,
    )
    if stage is None:
        return {
            "stage": None,
            "stage_status": "complete",
            "runnable": False,
            "description": "Every shared stage is complete for this corpus manifest.",
            "model": None,
            "spends_model_calls": False,
            "argv": None,
            "reason": None,
        }
    step = {
        "stage": stage,
        "stage_status": stages[stage]["status"],
        "runnable": False,
        "description": DESCRIPTIONS.get(stage, stage),
        "model": None,
        "spends_model_calls": False,
        "argv": None,
        "reason": None,
    }
    if stages[stage]["status"] == "running":
        running_run = stages[stage].get("run_id")
        step["reason"] = (
            f"{DESCRIPTIONS.get(stage, stage)} is already running"
            + (f" ({running_run})" if running_run else "")
        )
        return step
    try:
        built = SHARED_BUILDERS[stage](conn, target)
    except StepNotRunnable as exc:
        step["reason"] = str(exc)
        return step
    step.update(built)
    step["runnable"] = True
    step["model"] = defaults.bare_model(step["model"]) if step["model"] else None
    return step


def _plan_target(
    conn: psycopg.Connection,
    target: PipelineTarget,
    *,
    ignore_lease_token: str | None = None,
) -> dict:
    if isinstance(target, CorpusManifestTarget):
        return _plan_corpus_step(
            conn,
            target,
            ignore_lease_token=ignore_lease_token,
        )
    return _plan_step(
        conn,
        target,
        ignore_lease_token=ignore_lease_token,
    )


def _task_evidence(
    conn: psycopg.Connection,
    task_ids: set[str],
    statement_runs: list[str],
) -> dict[str, dict]:
    if not task_ids:
        return {}
    tasks = resolve_statement_tasks(
        conn,
        statement_runs,
        task_ids=sorted(task_ids),
    )
    source_by_artifact = {
        artifact_id: source_id
        for artifact_id, source_id in conn.execute(
            "SELECT a.id, s.id FROM artifact a"
            " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            " JOIN source s ON s.id = sn.source_id"
            " WHERE a.id = ANY(%s)",
            (sorted({task["artifact_id"] for task in tasks}),),
        ).fetchall()
    }
    return {
        task["id"]: {
            "task_id": task["id"],
            "source_id": source_by_artifact[task["artifact_id"]],
            "task": task["body"],
            "answer": task["answer"],
        }
        for task in tasks
    }


def read_publication_snapshot(
    conn: psycopg.Connection,
    target: SourcePublicationTarget | str | None = None,
    *,
    source_id: str | None = None,
    require_current: bool = True,
) -> dict:
    """Read local progress and stated unitary KCs without inferring a corpus.

    New work is current-only.  Durable callers may set ``require_current`` to
    false to keep an already pinned, formerly canonical Source Publication
    inspectable after a refresh; the Source Publication module still rejects
    arbitrary Markdown intermediates.
    """
    if target is None:
        if source_id is None:
            raise TypeError("read_snapshot requires a Source Publication target")
        target = source_id
    elif source_id is not None:
        raise TypeError("pass target or source_id, not both")
    if isinstance(target, str):
        local = current_target(conn, target)
    elif require_current:
        local = _local_target(conn, target)
    else:
        local = target
    source_id = local.source_id
    publication = (
        current_publication(conn, source_id)
        if require_current
        else read_publication(conn, source_id, local.artifact_id)
    )
    if publication is None or publication.artifact_id != local.artifact_id:
        qualifier = "current " if require_current else ""
        raise LookupError(f"no {qualifier}Source Publication for {source_id}")
    current = current_publication(conn, source_id)
    title_row = conn.execute(
        "SELECT title FROM source WHERE id = %s", (source_id,)
    ).fetchone()

    progress = spine.publication_progress(
        conn,
        source_id=local.source_id,
        artifact_id=local.artifact_id,
    )
    stages = progress["stages"]
    next_stage = next(
        (name for name, facts in stages.items() if facts["status"] != "done"),
        None,
    )
    source = {
        "id": source_id,
        "title": title_row[0] if title_row else None,
        "artifact_id": publication.artifact_id,
        "content_sha256": publication.content_hash,
        "provenance": publication.metadata,
        "current": bool(
            current is not None
            and not current.is_previous_attempt
            and current.artifact_id == publication.artifact_id
        ),
        "previous_attempt": publication.is_previous_attempt,
    }
    base = {
        "source": source,
        "status": "complete" if next_stage is None else "pending",
        "next_stage": next_stage,
        "stages": stages,
        "grouping_id": None,
        "components": [],
        "relationships": [],
    }
    statement_runs = list(stages["kc-statement"].get("input_runs") or [])
    if not statement_runs:
        return base
    statements = fetch_usable_statements(conn, statement_runs)
    if not statements:
        return base
    scoped_tasks = {
        row[0]
        for row in conn.execute(
            "SELECT t.id FROM task t"
            " JOIN passage p ON p.id = t.passage_id"
            " JOIN artifact a ON a.id = p.artifact_id"
            " JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            " WHERE sn.source_id = %s AND p.artifact_id = %s"
            " AND t.id = ANY(%s)",
            (source_id, publication.artifact_id, sorted(statements)),
        ).fetchall()
    }
    if not scoped_tasks:
        return base
    evidence = _task_evidence(conn, scoped_tasks, statement_runs)
    for task_id, item in evidence.items():
        item["statement"] = statements.get(task_id)
    components = []
    for task_id in sorted(scoped_tasks):
        if task_id not in evidence:
            continue
        statement = statements.get(task_id)
        components.append(
            {
                "id": task_id,
                "kind": "singleton",
                "canonical": (
                    {"verdict": "stated", "statement": statement}
                    if statement is not None
                    else {"verdict": "pending"}
                ),
                "members": [evidence[task_id]],
            }
        )
    base["components"] = sorted(components, key=lambda item: item["id"])
    return base


def read_corpus_snapshot(
    conn: psycopg.Connection,
    target: CorpusManifestTarget,
) -> dict:
    """Read shared progress and results for exactly one pinned corpus."""
    corpus = _corpus_target(conn, target)
    progress = spine.corpus_progress(conn, corpus.manifest_id)
    stages = progress["stages"]
    next_stage = next(
        (name for name in SHARED_STAGES if stages[name]["status"] != "done"),
        None,
    )
    base = {
        "corpus": {
            "id": progress["id"],
            "manifest_sha256": progress["manifest_sha256"],
            "origin": progress["origin"],
            "created_at": progress["created_at"],
            "publications": progress["publications"],
        },
        "status": "complete" if next_stage is None else "pending",
        "next_stage": next_stage,
        "stages": stages,
        "grouping_id": progress["grouping_id"],
        "components": [],
        "relationships": [],
    }
    statement_runs = list(progress["statements_from"])
    task_ids = set(progress["task_ids"])
    if not statement_runs or not task_ids:
        return base
    statements = fetch_usable_statements(conn, statement_runs)
    evidence = _task_evidence(conn, task_ids, statement_runs)
    for task_id, item in evidence.items():
        item["statement"] = statements.get(task_id)

    grouping_id = progress["grouping_id"]
    members_by_group: dict[str, list[str]] = {}
    group_by_task: dict[str, str] = {}
    if grouping_id is not None:
        for group_id, task_id in conn.execute(
            "SELECT group_id, task_id FROM kc_group_member"
            " WHERE grouping_id = %s ORDER BY group_id, task_id",
            (grouping_id,),
        ).fetchall():
            if task_id not in task_ids:
                continue
            members_by_group.setdefault(group_id, []).append(task_id)
            group_by_task[task_id] = group_id

    canonical = (
        fetch_current_canonicalizations(conn, grouping_id)
        if grouping_id is not None
        else {}
    )
    components = []
    for group_id, members in sorted(members_by_group.items()):
        components.append(
            {
                "id": group_id,
                "kind": "composite",
                "canonical": canonical.get(group_id, {"verdict": "pending"}),
                "members": [
                    evidence[task_id]
                    for task_id in members
                    if task_id in evidence
                ],
            }
        )
    for task_id in sorted(task_ids - set(group_by_task)):
        if task_id not in evidence:
            continue
        statement = statements.get(task_id)
        components.append(
            {
                "id": task_id,
                "kind": "singleton",
                "canonical": (
                    {"verdict": "stated", "statement": statement}
                    if statement is not None
                    else {"verdict": "pending"}
                ),
                "members": [evidence[task_id]],
            }
        )
    base["components"] = sorted(components, key=lambda item: item["id"])

    if grouping_id is None:
        return base
    component_by_task = {
        member["task_id"]: component["id"]
        for component in components
        for member in component["members"]
    }
    relationships = []
    for task_a, task_b, a_to_b, b_to_a in conn.execute(
        "SELECT v.task_a_id, v.task_b_id, v.a_implies_b, v.b_implies_a"
        " FROM kc_grouping_verdict gv"
        " JOIN kc_verdict v ON v.run_item_id = gv.run_item_id"
        " WHERE gv.grouping_id = %s ORDER BY v.task_a_id, v.task_b_id",
        (grouping_id,),
    ).fetchall():
        component_a = component_by_task.get(task_a)
        component_b = component_by_task.get(task_b)
        if component_a is None or component_b is None or component_a == component_b:
            continue
        relationships.extend(
            [
                {
                    "from": component_a,
                    "to": component_b,
                    "strength": a_to_b,
                    "from_task": task_a,
                    "to_task": task_b,
                },
                {
                    "from": component_b,
                    "to": component_a,
                    "strength": b_to_a,
                    "from_task": task_b,
                    "to_task": task_a,
                },
            ]
        )
    base["relationships"] = relationships
    return base


def read_snapshot(
    conn: psycopg.Connection,
    target: PipelineTarget | str | None = None,
    *,
    source_id: str | None = None,
) -> dict:
    """Read the local or shared projection named by the explicit target."""
    if isinstance(target, CorpusManifestTarget):
        if source_id is not None:
            raise TypeError("pass target or source_id, not both")
        return read_corpus_snapshot(conn, target)
    return read_publication_snapshot(conn, target, source_id=source_id)


def _dotenv() -> dict[str, str]:
    """KEY=VALUE pairs from the project .env; nothing auto-loads it."""
    values: dict[str, str] = {}
    path = PROJECT_DIR / ".env"
    if not path.exists():
        return values
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        values[key.strip()] = value.strip().strip("'\"")
    return values


def _spawn(
    argv: list[str],
    lease: pipeline_lease.Lease,
    *,
    database_url: str | None = None,
):
    """Production Adapter: one same-process worker owns the child lease."""
    if len(argv) < 3 or argv[1] != "-m" or not argv[2].startswith("universe."):
        raise ValueError("planned commands must be Python universe modules")
    env = os.environ.copy()
    for key, value in _dotenv().items():
        env.setdefault(key, value)
    env["PYTHONPATH"] = str(PROJECT_DIR / "src")
    if database_url is not None:
        # The caller connection is authoritative. Never put this credential in
        # argv, logs, or the public advance result.
        env["DATABASE_URL"] = database_url
    env.update(
        {
            "UNIVERSE_KC_LEASE_SCOPE": lease.scope_key,
            "UNIVERSE_KC_LEASE_STAGE": lease.stage,
            "UNIVERSE_KC_LEASE_TOKEN": lease.token,
            "UNIVERSE_KC_LEASE_OWNER": lease.owner_id,
        }
    )
    wrapped = [
        sys.executable,
        "-m",
        "universe.pipeline_worker",
        lease.stage,
        argv[2],
        "--",
        *argv[3:],
    ]
    return subprocess.Popen(wrapped, cwd=str(PROJECT_DIR), env=env)


def _release_persisted(dsn: str, lease: pipeline_lease.Lease) -> bool:
    with psycopg.connect(dsn) as lease_conn:
        return _release_lease(lease_conn, lease)


def _connection_dsn(conn: psycopg.Connection) -> str:
    """Clone the caller's database target, including its non-exported secret."""
    return pipeline_lease.connection_dsn(conn)


def _terminate_process(process: object, *, timeout: float = 5.0) -> None:
    """Bounded terminate -> wait -> kill escalation for a fenced generation."""
    poll = getattr(process, "poll", None)
    if not callable(poll) or poll() is not None:
        return
    terminate = getattr(process, "terminate", None)
    if callable(terminate):
        terminate()
    wait = getattr(process, "wait", None)
    if callable(wait):
        try:
            wait(timeout=timeout)
        except (subprocess.TimeoutExpired, TimeoutError):
            pass
    if poll() is not None:
        return
    kill = getattr(process, "kill", None)
    if callable(kill):
        kill()
    if callable(wait):
        try:
            wait(timeout=timeout)
        except (subprocess.TimeoutExpired, TimeoutError):
            pass


def _monitor_process(
    dsn: str,
    process: object,
    lease: pipeline_lease.Lease,
) -> None:
    """Watch, but never renew, the authoritative child-owned generation."""
    poll = getattr(process, "poll", None)
    if not callable(poll):
        return
    interval = max(1.0, min(60.0, LEASE_TTL_SECONDS / 3.0))
    pause = Event()
    while poll() is None:
        pause.wait(interval)
        if poll() is not None:
            break
        try:
            with psycopg.connect(dsn) as lease_conn:
                held = pipeline_lease.active(
                    lease_conn,
                    scope_key=lease.scope_key,
                    stage=lease.stage,
                )
        except psycopg.Error:
            # A transient database outage is not proof that the generation
            # lost ownership. Expiry will fence it if connectivity stays down.
            continue
        if held is None or held.token != lease.token:
            _terminate_process(process)
            return
    try:
        _release_persisted(dsn, lease)
    except psycopg.Error:
        # The row is self-healing: expiry permits a later atomic takeover.
        return


def advance(
    conn: psycopg.Connection,
    target: PipelineTarget | str,
    *,
    spawn: Callable[[list[str], pipeline_lease.Lease], object] = _spawn,
) -> dict:
    """Launch exactly one next stage and return its launch status.

    This is intentionally not a loop: callers may schedule many independent
    sources, inspect durable progress, and invoke ``advance`` again. ``spawn``
    is the process Adapter; tests and other runtimes can replace it without
    changing orchestration decisions.
    """
    resolved: PipelineTarget
    if isinstance(target, CorpusManifestTarget):
        resolved = _corpus_target(conn, target)
    else:
        resolved = _local_target(conn, target)
    step = next_step(conn, resolved)
    if step["stage"] is None:
        raise StepNotRunnable(step["description"])
    if not step["runnable"]:
        reason = step["reason"] or f"{step['stage']} is not runnable"
        if "already running" in reason:
            raise StepAlreadyRunning(reason)
        raise StepNotRunnable(reason)
    stage = step["stage"]
    scope_key = _scope_key(resolved, stage)
    owner_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"
    dsn = _connection_dsn(conn)
    # A dedicated transaction makes the claim visible before any subprocess
    # starts, without committing unrelated work on the caller's connection.
    with psycopg.connect(dsn) as lease_conn:
        lease = _acquire_lease(
            lease_conn,
            scope_key=scope_key,
            stage=stage,
            owner_id=owner_id,
        )
    if lease is None:
        raise StepAlreadyRunning(
            f"{DESCRIPTIONS.get(stage, stage)} is already running"
        )

    # Close the plan/claim race: once this generation owns the stage, verify
    # that it is still exactly the next work item. Ignore only our own token.
    confirmed = _plan_target(
        conn, resolved, ignore_lease_token=lease.token
    )
    if confirmed["stage"] != stage or not confirmed["runnable"]:
        _release_persisted(dsn, lease)
        if confirmed["stage"] is None:
            raise StepNotRunnable(confirmed["description"])
        reason = confirmed["reason"] or (
            f"pipeline moved to {confirmed['stage']} while claiming {stage}"
        )
        raise StepNotRunnable(reason)
    try:
        if spawn is _spawn:
            process = _spawn(
                confirmed["argv"],
                lease,
                database_url=dsn,
            )
        else:
            process = spawn(confirmed["argv"], lease)
    except Exception:
        _release_persisted(dsn, lease)
        raise
    if callable(getattr(process, "poll", None)):
        Thread(
            target=_monitor_process,
            args=(dsn, process, lease),
            daemon=True,
            name=f"kc-lease-{stage}",
        ).start()
    return {
        "status": "launched",
        "stage": stage,
        "pid": getattr(process, "pid", None),
        "argv": confirmed["argv"],
        "lease_token": lease.token,
        "lease_expires_at": lease.expires_at,
    }
