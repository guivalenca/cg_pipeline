"""One publication-scope predicate for every Markdown-to-KC ledger reader.

A source-stage run is reusable only when its complete item manifest belongs
to the requested Source Publication scope.  The implicit scope resolves each
Source through ``source_publication.current_many``.  Historical reuse is
possible only through an explicit artifact or immutable KC corpus manifest.
"""

from __future__ import annotations

from collections.abc import Iterable

import psycopg

from universe import judge_manifest, kc_corpus_manifest, source_publication
from universe.recipe_identity import matches_recipe, recipe_identity


SOURCE_ITEM_STAGES = {
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
}


def current_publication_artifacts(
    conn: psycopg.Connection,
    source_ids: Iterable[str] | None = None,
) -> dict[str, str]:
    """Canonical artifact id for each requested Source's current Publication."""
    if source_ids is None:
        requested = [
            source_id
            for source_id, in conn.execute(
                "SELECT id FROM source ORDER BY id"
            ).fetchall()
        ]
    else:
        requested = list(dict.fromkeys(source_ids))
    publications = source_publication.current_many(conn, requested)
    return {
        source_id: publications[source_id].artifact_id
        for source_id in requested
        if source_id in publications
    }


def corpus_publication_artifacts(
    conn: psycopg.Connection,
    corpus_manifest_id: str,
) -> dict[str, str]:
    """Exact Source Publication members sealed by one immutable KC corpus."""
    manifest = kc_corpus_manifest.read(conn, corpus_manifest_id)
    if manifest is None:
        raise LookupError(f"no complete KC corpus manifest {corpus_manifest_id}")
    return {
        publication["source_id"]: publication["artifact_id"]
        for publication in manifest["publications"]
    }


def run_artifact_ids(
    conn: psycopg.Connection, run_id: str
) -> tuple[set[str], bool]:
    """Non-null artifacts on a run and whether it also has unscoped items."""
    rows = conn.execute(
        "SELECT artifact_id FROM run_item WHERE run_id = %s",
        (run_id,),
    ).fetchall()
    artifacts = {artifact_id for artifact_id, in rows if artifact_id}
    return artifacts, any(artifact_id is None for artifact_id, in rows)


def eligible_run_ids(
    conn: psycopg.Connection,
    stage: str,
    *,
    artifact_id: str | None = None,
    corpus_manifest_id: str | None = None,
    statuses: Iterable[str] = ("done",),
) -> list[str]:
    """Current-recipe runs whose complete item manifest is in scope.

    With no pin, only current Source Publications are eligible. ``artifact_id``
    requests strict single-publication purity and is the explicit escape hatch
    for a historical Publication. ``corpus_manifest_id`` pins the immutable
    publication set: a run may cover any subset, but never an external Source.
    Runs without items and runs containing null-artifact items are rejected.
    """
    if stage not in SOURCE_ITEM_STAGES:
        return []
    if artifact_id is not None and corpus_manifest_id is not None:
        raise ValueError("artifact_id and corpus_manifest_id are mutually exclusive")
    if artifact_id is not None:
        if not isinstance(artifact_id, str) or not artifact_id.strip():
            raise ValueError("artifact_id must be a non-empty string")
        allowed_artifacts = {artifact_id}
        require_exact_artifact = True
    elif corpus_manifest_id is not None:
        allowed_artifacts = set(
            corpus_publication_artifacts(conn, corpus_manifest_id).values()
        )
        require_exact_artifact = False
    else:
        allowed_artifacts = set(current_publication_artifacts(conn).values())
        require_exact_artifact = False

    rows = conn.execute(
        "SELECT id, model, prompt_ref, prompt_sha, params FROM run"
        " WHERE stage = %s AND status = ANY(%s)"
        " ORDER BY started_at, id",
        (stage, list(statuses)),
    ).fetchall()
    selected = []
    for run_id, model, prompt_ref, prompt_sha, params in rows:
        if not matches_recipe(
            stage,
            model=model,
            prompt_ref=prompt_ref,
            prompt_sha=prompt_sha,
            params=params,
        ):
            continue
        artifacts, has_unscoped = run_artifact_ids(conn, run_id)
        if has_unscoped or not artifacts:
            continue
        if require_exact_artifact:
            if artifacts != allowed_artifacts:
                continue
        elif not artifacts <= allowed_artifacts:
            continue
        selected.append(run_id)
    return selected


def run_unit_ids(
    conn: psycopg.Connection,
    run_id: str,
    *,
    unit: str,
) -> set[str]:
    """The passage or task ids represented by one run's item manifest."""
    if unit not in {"passage", "task"}:
        raise ValueError(f"unsupported run unit {unit!r}")
    column = "passage_id" if unit == "passage" else "task_id"
    return {
        value
        for value, in conn.execute(
            f"SELECT DISTINCT {column} FROM run_item WHERE run_id = %s",
            (run_id,),
        ).fetchall()
        if value is not None
    }


def ordered_unique(groups: Iterable[Iterable[str]]) -> list[str]:
    """Stable first-seen union of already chronological run-id groups."""
    seen: set[str] = set()
    result = []
    for group in groups:
        for run_id in group:
            if run_id not in seen:
                seen.add(run_id)
                result.append(run_id)
    return result


def exact_embedding_run(
    conn: psycopg.Connection,
    *,
    statement_runs: list[str],
    task_ids: set[str],
    corpus_manifest_id: str | None = None,
) -> str | None:
    """Newest one-run embedding witness for the exact statement manifest."""
    if not task_ids:
        return None
    candidates = eligible_run_ids(
        conn,
        "task-embedding",
        corpus_manifest_id=corpus_manifest_id,
        statuses=("done",),
    )
    for run_id in reversed(candidates):
        params = conn.execute(
            "SELECT params FROM run WHERE id = %s", (run_id,)
        ).fetchone()[0] or {}
        if list(params.get("statements_from") or []) != statement_runs:
            continue
        if run_unit_ids(conn, run_id, unit="task") != task_ids:
            continue
        embedded = {
            task_id
            for task_id, in conn.execute(
                "SELECT e.task_id FROM task_embedding e"
                " JOIN run_item i ON i.id = e.run_item_id"
                " WHERE i.run_id = %s",
                (run_id,),
            ).fetchall()
        }
        if embedded == task_ids:
            return run_id
    return None


def completed_judge_build_for_inputs(
    conn: psycopg.Connection, expected: dict
) -> dict | None:
    """Newest current, successful judge run for one exact corpus manifest."""
    expected_build_key, expected_prompt_sha = _expected_judge_identity(expected)
    keys = (
        "statements_from",
        "embedding_run",
        "modality_runs",
        "knowledge_runs",
    )
    rows = conn.execute(
        "SELECT id, model, prompt_ref, prompt_sha, params FROM run"
        " WHERE stage = 'kc-judge' AND status = 'done'"
        " ORDER BY started_at DESC, id DESC"
    ).fetchall()
    for run_id, model, prompt_ref, prompt_sha, params in rows:
        if not matches_recipe(
            "kc-judge",
            model=model,
            prompt_ref=prompt_ref,
            prompt_sha=prompt_sha,
            params=params,
        ):
            continue
        params = params or {}
        manifest = judge_manifest.read(conn, run_id)
        if (
            all(params.get(key) == expected.get(key) for key in keys)
            and params.get("build_key") == expected_build_key
            and manifest is not None
            and prompt_sha == expected_prompt_sha
        ):
            return {
                "run_id": run_id,
                "build_key": expected_build_key,
                "candidate_count": manifest.count,
                "candidate_manifest_sha256": manifest.sha256,
                "manifest": manifest,
                "params": params,
            }
    return None


def expected_judge_build_key(expected: dict) -> str:
    """Fingerprint today's complete judge recipe without calling a provider."""
    return _expected_judge_identity(expected)[0]


def _expected_judge_identity(expected: dict) -> tuple[str, str]:
    """Build key and prompt hash for today's provider-free judge recipe."""
    from universe import kc_judge

    recipe = recipe_identity("kc-judge")
    build_key = kc_judge.universe_build_key(
        model=recipe["model"],
        prompt_ref=recipe["prompt_ref"],
        prompt_sha=recipe["prompt_sha"],
        model_params=recipe["model_params"],
        statement_runs=list(expected["statements_from"]),
        embedding_run=expected["embedding_run"],
        modality_runs=list(expected["modality_runs"]),
        knowledge_runs=list(expected["knowledge_runs"]),
    )
    return build_key, recipe["prompt_sha"]


def grouping_for_judge_manifest(
    conn: psycopg.Connection, judge: dict | None
) -> dict | None:
    """Latest grouping whose verdict rows exactly equal one judge manifest."""
    if not judge:
        return None
    run_id = judge.get("run_id") or judge.get("judge_run_id")
    if not run_id:
        return None
    manifest = judge.get("manifest")
    if not isinstance(manifest, judge_manifest.JudgeManifest):
        manifest = judge_manifest.read(conn, run_id)
    if manifest is None or manifest.judge_run_id != run_id:
        return None
    if (
        judge.get("candidate_count", manifest.count) != manifest.count
        or judge.get("candidate_manifest_sha256", manifest.sha256)
        != manifest.sha256
    ):
        return None
    rows = conn.execute(
        "SELECT id, computed_at, params FROM kc_grouping"
        " WHERE params->>'judge_run_id' = %s"
        " AND params->>'candidate_manifest_sha256' = %s"
        " AND params->>'candidate_count' = %s"
        " ORDER BY computed_at DESC, id DESC",
        (run_id, manifest.sha256, str(manifest.count)),
    ).fetchall()
    expected_ids = set(manifest.run_item_ids)
    for grouping_id, computed_at, params in rows:
        params = params or {}
        if params.get("build_key") != manifest.build_key:
            continue
        actual_ids = {
            run_item_id
            for run_item_id, in conn.execute(
                "SELECT run_item_id FROM kc_grouping_verdict"
                " WHERE grouping_id = %s",
                (grouping_id,),
            ).fetchall()
        }
        if actual_ids == expected_ids:
            return {
                "id": grouping_id,
                "computed_at": computed_at,
                "params": params,
            }
    return None
