"""Per-source pipeline run targeting: what runs next, and launching it.

One deep interface over the ledger.  ``next_step(conn, source_id)`` reads the
same facts the spine reads and answers, for one source, "what would run next
and exactly how" — the full CLI argv, rebuilt from the current stage defaults
plus the operational recipe of the reference ingestion chain (r0135–r0158).
``start_step(source_id)`` launches that argv as a detached subprocess so the
dashboard can fire a step and keep serving.

The scoping rule mirrors the reference chain: passage cutting is scoped with
``--sources <id>``; every later per-source stage is scoped through the run ids
the chain itself produced for this source (always the current-generation runs,
so a superseded experiment never leaks back in).  The two corpus-wide stages
(task-embedding, kc-judge) are scoped the same way the reference scoped them:
every current-generation run of their input stages across the whole ledger.
A stage whose scope cannot be derived safely is reported as not runnable from
the dashboard, with the reason — never guessed.

Acquisition does not call a model, but its article fetcher does call the
Firecrawl API.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import psycopg

from universe import defaults, spine
from universe.acquisition.book_scope import is_missing_scope
from universe.blocks import BLOCKER_VERSION
from universe.db import connect

PROJECT_DIR = Path(__file__).resolve().parents[2]
LOGS_DIR = PROJECT_DIR / "logs"

# Operational rules of the reference chain, baked in.
PROVIDER = {
    # Routing decision 2026-08-01 (docs/pipeline-defaults.md): no low-bit
    # quantization; SiliconFlow excluded everywhere.
    "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
    "ignore": ["SiliconFlow"],
}
THINKING_EXTRA = {
    "thinking": {"type": "enabled"},
    "reasoning_effort": "high",
    "tool_choice": "auto",
    "provider": PROVIDER,
}
MODALITY_EXTRA = {"reasoning": {"enabled": False}, "provider": PROVIDER}
MAX_TOKENS = "65536"
THINKING_WORKERS = "16"
# Tool-routing concentrates on few providers; serialize this fragile axis.
MODALITY_WORKERS = "1"
JUDGE_WORKERS = "12"
EMBEDDING_WORKERS = "8"

TOOLS = {
    "passage-cuts": "prompts/passage-cuts/tool-v001.json",
    "passage-triage": "prompts/passage-triage/tool-v001.json",
    "task-generation": "prompts/task-generation/tool-v001.json",
    "task-granularity": "prompts/task-granularity/tool-v001.json",
    "task-revision": "prompts/task-revision/tool-v003.json",
    "task-triage": "prompts/task-triage/tool-v001.json",
    "task-substance": "prompts/task-substance/tool-v004.json",
    "kc-statement": "prompts/kc-statement/tool-v007.json",
    "task-modality": "prompts/task-modality/tool-v001.json",
    "task-knowledge": "prompts/task-knowledge/tool-v002.json",
}

# Founder-plain wording; no table names.
DESCRIPTIONS = {
    "acquisition": "Acquire this source's content using Firecrawl",
    "snapshot": "Capture this source's material",
    "artifact": "Extract readable text from the captured material",
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
    "task-embedding": "Compute similarity vectors for the knowledge statements (whole corpus)",
    "kc-judge": "Judge which knowledge statements carry each other (whole corpus)",
    "grouped": "Fold mutually-carrying statements into knowledge components",
}

# Stages whose scope is the whole corpus, not one source: a running run of
# these blocks every source's button, and their inputs span every source.
CORPUS_STAGES = {"task-embedding", "kc-judge"}


class StepNotRunnable(Exception):
    """The next step exists but cannot be launched from the dashboard."""


class StepAlreadyRunning(Exception):
    """A run for this source and stage is already in flight."""


# --- deciding the next step -------------------------------------------------


def _current_runs(
    conn: psycopg.Connection, stage: str, source_id: str | None = None
) -> list[str]:
    """Completed runs of a stage at the current generation, oldest first.

    With a source, only runs whose items touch that source's artifacts; without
    one, the whole ledger (how the corpus-wide stages scope their inputs).
    """
    scope, params = "", [stage]
    if source_id is not None:
        scope = (
            " AND EXISTS (SELECT 1 FROM run_item i"
            "   JOIN artifact a ON a.id = i.artifact_id"
            "   JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            "   WHERE i.run_id = r.id AND sn.source_id = %s)"
        )
        params.append(source_id)
    rows = conn.execute(
        "SELECT r.id, r.model, r.prompt_ref FROM run r"
        " WHERE r.stage = %s AND r.status = 'done'" + scope + " ORDER BY r.started_at, r.id",
        params,
    ).fetchall()
    return [
        run_id
        for run_id, model, prompt_ref in rows
        if defaults.run_generation(stage, model, prompt_ref) == "current"
    ]


def _require(runs: list[str], stage: str) -> list[str]:
    if not runs:
        raise StepNotRunnable(
            f"its input — {DESCRIPTIONS[stage].lower()} — has no completed run"
            " with the current recipe; run that step first"
        )
    return runs


def _latest(conn: psycopg.Connection, stage: str, source_id: str | None = None) -> str:
    return _require(_current_runs(conn, stage, source_id), stage)[-1]


def _model_argv(
    module: str,
    stage: str,
    refs: list[str],
    workers: str,
    extra: dict,
) -> tuple[list[str], str]:
    """The exact invocation of one model stage, and the model it spends on."""
    default = defaults.STAGE_DEFAULTS[stage]
    prompt = default["prompt_ref"].split("/", 1)[1]
    argv = [
        sys.executable, "-m", module, "run",
        "--prompt", prompt,
        "--model", default["model"],
        *refs,
        "--tool", TOOLS[stage],
        "--workers", workers,
        "--max-tokens", MAX_TOKENS,
        "--extra", json.dumps(extra),
    ]
    return argv, default["model"]


def _task_refs(conn: psycopg.Connection, source_id: str, *stages: str) -> list[str]:
    """CLI references to this source's own chain, the way the reference chain
    wired them: every current-generation task-generation run, and the latest
    current-generation run of each judging stage."""
    refs: list[str] = []
    for stage in stages:
        if stage == "task-generation":
            refs += ["--gen-runs", ",".join(_require(_current_runs(conn, stage, source_id), stage))]
        elif stage == "task-granularity":
            refs += ["--granularity-run", _latest(conn, stage, source_id)]
        elif stage == "task-granularity-list":
            refs += ["--granularity-runs", _latest(conn, "task-granularity", source_id)]
        elif stage == "task-revision":
            refs += ["--revision-run", _latest(conn, stage, source_id)]
        elif stage == "parts-revision":
            # The reference chain revised originals and parts in one run.
            refs += ["--parts-revision-run", _latest(conn, "task-revision", source_id)]
        elif stage == "task-triage":
            refs += ["--triage-run", _latest(conn, stage, source_id)]
        elif stage == "task-substance":
            refs += ["--substance-run", _latest(conn, stage, source_id)]
        else:  # pragma: no cover - a typo in the builder table
            raise ValueError(f"unknown reference stage {stage}")
    return refs


def _build_blocks(conn: psycopg.Connection, source_id: str) -> dict:
    row = conn.execute(
        "SELECT a.id FROM artifact a JOIN source_snapshot sn ON sn.id = a.snapshot_id"
        " WHERE sn.source_id = %s AND NOT EXISTS ("
        "   SELECT 1 FROM block b WHERE b.artifact_id = a.id AND b.blocker_version = %s)"
        " ORDER BY a.created_at DESC, a.id DESC LIMIT 1",
        (source_id, BLOCKER_VERSION),
    ).fetchone()
    if row is None:
        raise StepNotRunnable(
            "every extracted text already has blocks at the current version;"
            " if the spine still shows this step open, the remaining blocks are"
            " from an older splitter"
        )
    return {
        "argv": [sys.executable, "-m", "universe.blocks", row[0]],
        "model": None,
        "spends_model_calls": False,
    }


def _build_acquisition(conn: psycopg.Connection, source_id: str) -> dict:
    """Acquisition for a source without an ok snapshot.

    Acquisition does not call model endpoints but does call the Firecrawl API.
    """
    source = conn.execute(
        "SELECT media_type FROM source WHERE id = %s", (source_id,)
    ).fetchone()
    if source is None:
        raise StepNotRunnable(f"source {source_id} not found")
    media_type = source[0]
    if media_type != "article":
        raise StepNotRunnable(
            f"media type '{media_type}' is not supported for automatic acquisition"
        )
    return {
        "argv": [
            sys.executable,
            "-m",
            "universe.acquisition",
            "run",
            "--sources",
            source_id,
            "--only-missing",
        ],
        "model": None,
        "spends_model_calls": False,
    }


def _build_passage_cuts(conn: psycopg.Connection, source_id: str) -> dict:
    default = defaults.STAGE_DEFAULTS["passage-cuts"]
    argv = [
        sys.executable, "-m", "universe.harness", "run",
        "--stage", "passage-cuts",
        "--prompt", default["prompt_ref"].split("/", 1)[1],
        "--model", default["model"],
        "--sources", source_id,
        "--body-from", "blocks",
        "--tool", TOOLS["passage-cuts"],
        "--workers", THINKING_WORKERS,
        "--max-tokens", MAX_TOKENS,
        "--extra", json.dumps(THINKING_EXTRA),
    ]
    return {"argv": argv, "model": default["model"], "spends_model_calls": True}


def _build_passage_triage(conn: psycopg.Connection, source_id: str) -> dict:
    cuts = _require(_current_runs(conn, "passage-cuts", source_id), "passage-cuts")
    argv, model = _model_argv(
        "universe.triage", "passage-triage",
        ["--cuts-runs", ",".join(cuts)],
        THINKING_WORKERS, THINKING_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_generation(conn: psycopg.Connection, source_id: str) -> dict:
    cuts = _require(_current_runs(conn, "passage-cuts", source_id), "passage-cuts")
    triage = _latest(conn, "passage-triage", source_id)
    argv, model = _model_argv(
        "universe.taskgen", "task-generation",
        ["--cuts-runs", ",".join(cuts), "--triage-runs", triage],
        THINKING_WORKERS, THINKING_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_granularity(conn: psycopg.Connection, source_id: str) -> dict:
    refs = _task_refs(conn, source_id, "task-generation")
    argv, model = _model_argv(
        "universe.task_granularity", "task-granularity", refs,
        THINKING_WORKERS, THINKING_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_revision(conn: psycopg.Connection, source_id: str) -> dict:
    refs = _task_refs(conn, source_id, "task-generation", "task-granularity-list")
    argv, model = _model_argv(
        "universe.task_revision", "task-revision", refs,
        THINKING_WORKERS, THINKING_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_triage(conn: psycopg.Connection, source_id: str) -> dict:
    refs = _task_refs(conn, source_id, "task-generation", "task-revision", "task-granularity")
    argv, model = _model_argv(
        "universe.task_triage", "task-triage", refs,
        THINKING_WORKERS, THINKING_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_substance(conn: psycopg.Connection, source_id: str) -> dict:
    refs = _task_refs(
        conn, source_id,
        "task-generation", "task-revision", "task-granularity", "parts-revision",
        "task-triage",
    )
    argv, model = _model_argv(
        "universe.task_substance", "task-substance", refs,
        THINKING_WORKERS, THINKING_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _statement_shaped_refs(conn: psycopg.Connection, source_id: str) -> list[str]:
    return _task_refs(
        conn, source_id,
        "task-generation", "task-revision", "task-granularity", "parts-revision",
        "task-triage", "task-substance",
    )


def _build_kc_statement(conn: psycopg.Connection, source_id: str) -> dict:
    argv, model = _model_argv(
        "universe.kc_statement", "kc-statement",
        _statement_shaped_refs(conn, source_id),
        THINKING_WORKERS, THINKING_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_modality(conn: psycopg.Connection, source_id: str) -> dict:
    argv, model = _model_argv(
        "universe.task_modality", "task-modality",
        _statement_shaped_refs(conn, source_id),
        MODALITY_WORKERS, MODALITY_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_knowledge(conn: psycopg.Connection, source_id: str) -> dict:
    argv, model = _model_argv(
        "universe.task_knowledge", "task-knowledge",
        _statement_shaped_refs(conn, source_id),
        THINKING_WORKERS, THINKING_EXTRA,
    )
    return {"argv": argv, "model": model, "spends_model_calls": True}


def _build_task_embedding(conn: psycopg.Connection, source_id: str) -> dict:
    # Corpus-wide by design: the statement runs define the exact grouping
    # scope, so every current-generation statement run goes in — exactly how
    # the reference chain scoped r0153.
    statements = _require(_current_runs(conn, "kc-statement"), "kc-statement")
    default = defaults.STAGE_DEFAULTS["task-embedding"]
    argv = [
        sys.executable, "-m", "universe.task_embedding", "run",
        "--prompt", default["prompt_ref"].split("/", 1)[1],
        "--model", default["model"],
        "--statements-from", ",".join(statements),
        "--workers", EMBEDDING_WORKERS,
    ]
    return {"argv": argv, "model": default["model"], "spends_model_calls": True}


def _build_kc_judge(conn: psycopg.Connection, source_id: str) -> dict:
    # Corpus-wide by design; model, prompt, tool and routing are the judge's
    # own defaults.  Only pairs with no recorded verdict get calls.
    statements = _require(_current_runs(conn, "kc-statement"), "kc-statement")
    embedding = _latest(conn, "task-embedding")
    modality = _require(_current_runs(conn, "task-modality"), "task-modality")
    knowledge = _require(_current_runs(conn, "task-knowledge"), "task-knowledge")
    argv = [
        sys.executable, "-m", "universe.kc_judge", "run",
        "--statements-from", ",".join(statements),
        "--embedding-run", embedding,
        "--modality-run", ",".join(modality),
        "--knowledge-run", ",".join(knowledge),
        "--workers", JUDGE_WORKERS,
    ]
    default = defaults.STAGE_DEFAULTS["kc-judge"]
    return {"argv": argv, "model": default["model"], "spends_model_calls": True}


NOT_FROM_DASHBOARD = {
    "artifact": "text extraction is part of acquisition and is not started"
    " from here yet",
    "grouped": "grouping is a recompute over the recorded judgments, not a"
    " model run; it is not started from here yet",
}

BUILDERS = {
    "acquisition": _build_acquisition,
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
    "task-embedding": _build_task_embedding,
    "kc-judge": _build_kc_judge,
}


def _acquisition_blocker(
    conn: psycopg.Connection, source: dict
) -> str | None:
    """Explain why this source has no built acquisition path, if it has none."""
    media_type = source.get("media_type")
    if media_type == "article":
        return None
    if media_type == "book":
        descriptions = conn.execute(
            "SELECT string_agg(coalesce(description, ''), E'\\n' ORDER BY created_at, id)"
            " FROM syllabus_item WHERE source_id = %s",
            (source["id"],),
        ).fetchone()[0]
        if is_missing_scope(
            {
                "source": source,
                "item": {"description": descriptions or ""},
            },
            conn,
        ):
            return "This book needs a chapter, page range, or unit before it can be fetched."
    label = media_type or "unknown"
    return f"{label.capitalize()} sources do not have a fetcher yet."


def next_step(conn: psycopg.Connection, source_id: str) -> dict:
    """The next runnable stage for one source, with the exact argv it would run.

    Mirrors the spine's stage semantics: the next step is the first stage of
    the pipeline that is not done.  Raises ``LookupError`` for an unknown
    source.
    """
    progress = spine.source_progress(conn)
    if source_id not in progress:
        raise LookupError(f"no source {source_id}")
    source = progress[source_id]
    stages = source["stages"]
    has_ok_snapshot = conn.execute(
        "SELECT EXISTS ("
        " SELECT 1 FROM source_snapshot WHERE source_id = %s AND status = 'ok'"
        ")",
        (source_id,),
    ).fetchone()[0]
    if not has_ok_snapshot:
        step = {
            "stage": "acquisition",
            "stage_status": stages["snapshot"]["status"],
            "runnable": False,
            "description": DESCRIPTIONS["acquisition"],
            "model": None,
            "spends_model_calls": False,
            "argv": None,
            "reason": _acquisition_blocker(conn, source),
        }
        if step["reason"] is not None:
            return step
        step.update(BUILDERS["acquisition"](conn, source_id))
        step["runnable"] = True
        return step
    stage = next(
        (
            name
            for name, facts in stages.items()
            if name != "snapshot" and facts["status"] != "done"
        ),
        None,
    )
    if stage is None:
        return {
            "stage": None,
            "stage_status": "complete",
            "runnable": False,
            "description": "Every stage is complete for this source.",
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
    if stage in NOT_FROM_DASHBOARD:
        step["reason"] = NOT_FROM_DASHBOARD[stage]
        return step
    try:
        built = BUILDERS[stage](conn, source_id)
    except StepNotRunnable as exc:
        step["reason"] = str(exc)
        return step
    step.update(built)
    step["runnable"] = True
    step["model"] = defaults.bare_model(step["model"]) if step["model"] else None
    return step


# --- launching --------------------------------------------------------------

# One dashboard process launches steps; what it launched and has not seen
# finish.  Keyed by source so a source fires one step at a time.
_RUNNING: dict[str, dict] = {}


def running_step(source_id: str) -> dict | None:
    """The step this process launched for the source, while it is still alive."""
    entry = _RUNNING.get(source_id)
    if entry is None:
        return None
    if entry["process"].poll() is not None:
        del _RUNNING[source_id]
        return None
    return {"stage": entry["stage"], "pid": entry["process"].pid, "log": entry["log"]}


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


def _db_running(conn: psycopg.Connection, source_id: str, stage: str) -> str | None:
    """A ledger run of this stage still marked running, for this scope."""
    if stage == "acquisition":
        row = conn.execute(
            "SELECT id FROM run WHERE stage = 'acquisition' AND status = 'running'"
            " AND params->'source_ids' ? %s"
            " ORDER BY started_at DESC LIMIT 1",
            (source_id,),
        ).fetchone()
    elif stage in CORPUS_STAGES:
        row = conn.execute(
            "SELECT id FROM run WHERE stage = %s AND status = 'running'"
            " ORDER BY started_at DESC LIMIT 1",
            (stage,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT r.id FROM run r WHERE r.stage = %s AND r.status = 'running'"
            " AND EXISTS (SELECT 1 FROM run_item i"
            "   JOIN artifact a ON a.id = i.artifact_id"
            "   JOIN source_snapshot sn ON sn.id = a.snapshot_id"
            "   WHERE i.run_id = r.id AND sn.source_id = %s)"
            " ORDER BY r.started_at DESC LIMIT 1",
            (stage, source_id),
        ).fetchone()
    return row[0] if row else None


def start_step(source_id: str) -> dict:
    """Launch the source's next step as a detached subprocess.

    Raises ``StepAlreadyRunning`` when this source already has a step in
    flight, ``StepNotRunnable`` when the next step cannot be launched here.
    """
    live = running_step(source_id)
    if live is not None:
        raise StepAlreadyRunning(
            f"{DESCRIPTIONS.get(live['stage'], live['stage'])} is already running"
            " for this source"
        )
    with connect() as conn:
        step = next_step(conn, source_id)
        if step["stage"] is None:
            raise StepNotRunnable(step["description"])
        if not step["runnable"]:
            raise StepNotRunnable(step["reason"])
        ledger_run = _db_running(conn, source_id, step["stage"])
    if ledger_run is not None:
        raise StepAlreadyRunning(
            f"{DESCRIPTIONS[step['stage']]} is already running ({ledger_run})"
        )

    env = os.environ.copy()
    for key, value in _dotenv().items():
        env.setdefault(key, value)
    if step["spends_model_calls"] and not env.get("OPEN_ROUTER_API_KEY"):
        raise StepNotRunnable(
            "no OPEN_ROUTER_API_KEY in the project's .env — add the key before"
            " launching model runs"
        )
    env["PYTHONPATH"] = str(PROJECT_DIR / "src")

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOGS_DIR / f"{source_id}-{step['stage']}-{time.strftime('%Y%m%d-%H%M%S')}.log"
    with open(log_path, "ab") as log:
        process = subprocess.Popen(
            step["argv"],
            cwd=str(PROJECT_DIR),
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    _RUNNING[source_id] = {
        "stage": step["stage"],
        "process": process,
        "log": str(log_path),
    }
    return {"stage": step["stage"], "run_argv": step["argv"], "pid": process.pid, "log": str(log_path)}
