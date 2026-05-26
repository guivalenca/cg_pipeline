from __future__ import annotations

import concurrent.futures
import hashlib
import json
import re
import shutil
import time
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from concept_graph_creation.runtime.semantic_reduce import (
    build_candidate_registry,
    normalize_decision_output,
    validate_reduce_decision,
)
from concept_graph_creation.runtime.stage_runner import (
    FLASH_ROUTE_ALIAS,
    ModelCall,
    ModelRouter,
    PRO_ROUTE_ALIAS,
    PRO_THINKING_ROUTE_ALIAS,
    StageBlockedError,
    StageContract,
    StageResult,
    StageRunner,
)


@dataclass(frozen=True)
class _SubjectMergePrompt:
    text: str
    path_ref: str


_SUBJECT_MERGE_PROMPT_FILES = {
    "area_partition": "area_partition.md",
    "fine_clustering": "fine_clustering.md",
    "cluster_evaluation": "cluster_evaluation.md",
    "quality_audit": "quality_audit.md",
    "quality_repair": "quality_repair.md",
}


_SUBJECT_MERGE_AUDIT_SCORE_FIELDS = (
    "identity_correctness",
    "granularity_preservation",
    "provenance_preservation",
    "assignment_completeness",
    "overlap_reduction",
    "subject_coherence",
    "net_phase5_benefit",
)
_SUBJECT_MERGE_AUDIT_FLAGS = {
    "assignment_incomplete",
    "granularity_violation",
    "missed_obvious_merge",
    "over_merged_group",
    "provenance_loss",
    "repair_unstable",
    "residual_duplicate",
}
_SUBJECT_MERGE_AUDIT_REPAIR_REASONS = {
    "assignment_incomplete",
    "missed_obvious_merge",
    "over_merged_group",
    "provenance_loss",
    "residual_duplicate",
}


def run_subject_merge_phase(
    *,
    run_dir: Path,
    model_call: ModelCall,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
    model_route: str = PRO_THINKING_ROUTE_ALIAS,
    area_partition_model_route: str | None = None,
    fine_clustering_model_route: str | None = None,
    evaluation_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    repair_model_route: str = FLASH_ROUTE_ALIAS,
    contextual_repair_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase5b_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase5b_enabled: bool = True,
    fine_clustering_concurrency: int = 6,
    evaluation_concurrency: int = 6,
    evaluation_batch_size: int = 1,
    clean_phase_artifacts: bool = False,
    provider_retry_limit: int = 2,
    provider_retry_backoff_seconds: float = 10.0,
) -> dict[str, Any]:
    prompts = _load_subject_merge_prompts(prompt_path)
    evaluation_batch_size = 1
    area_partition_model_route = area_partition_model_route or model_route
    fine_clustering_model_route = fine_clustering_model_route or model_route
    source_ledger = _read_json(run_dir / "source_ledger.json")
    _ensure_lesson_reconciliation_complete(run_dir=run_dir, source_ledger=source_ledger)
    if clean_phase_artifacts:
        _clean_phase_five_artifacts(run_dir=run_dir)

    candidate_sources = _subject_candidate_sources(run_dir=run_dir, source_ledger=source_ledger)
    if not candidate_sources:
        raise StageBlockedError("Subject Merge requires at least one lesson_reconciliation.json artifact")

    scope = _subject_scope(source_ledger)
    registry = build_candidate_registry(
        scope_id=scope["id"],
        source_artifact="source_ledger.json",
        candidate_sources=candidate_sources,
    )
    registry_path = run_dir / "subject_merge_candidate_registry.json"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    input_candidate_ids = list(registry["candidates"])
    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)

    area_clusters_artifact = _run_subject_area_partition(
        run_dir=run_dir,
        registry=registry,
        input_candidate_ids=input_candidate_ids,
        scope=scope,
        prompt=prompts["area_partition"].text,
        prompt_path=prompts["area_partition"].path_ref,
        runner=runner,
        model_route=area_partition_model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    fine_clusters_artifact = _run_subject_fine_clustering(
        run_dir=run_dir,
        registry=registry,
        area_clusters_artifact=area_clusters_artifact,
        prompt=prompts["fine_clustering"].text,
        prompt_path=prompts["fine_clustering"].path_ref,
        runner=runner,
        model_route=fine_clustering_model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        concurrency=fine_clustering_concurrency,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    evaluation_results = _run_subject_cluster_evaluations(
        run_dir=run_dir,
        registry=registry,
        clusters_artifact=fine_clusters_artifact,
        prompt=prompts["cluster_evaluation"].text,
        prompt_path=prompts["cluster_evaluation"].path_ref,
        runner=runner,
        model_route=evaluation_model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        concurrency=evaluation_concurrency,
        evaluation_batch_size=evaluation_batch_size,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    combined_decision = _combine_subject_cluster_evaluation_decisions(
        scope_id=scope["id"],
        input_candidate_ids=input_candidate_ids,
        model_route=evaluation_model_route,
        clusters=fine_clusters_artifact.get("clusters") or [],
        registry=registry,
        evaluation_results=evaluation_results,
    )
    decision_path = run_dir / "subject_merge_decision.json"
    decision_path.write_text(json.dumps(combined_decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifact = assemble_subject_merge(
        source_ledger=source_ledger,
        registry=registry,
        decision=combined_decision,
        decision_artifact_path=str(decision_path.relative_to(run_dir)),
        registry_artifact_path=str(registry_path.relative_to(run_dir)),
        area_clusters_artifact="subject_merge_area_clusters.json",
        candidate_clusters_artifact="subject_merge_candidate_clusters.json",
        cluster_evaluation_decision_artifacts=[
            str(result.decision_path.relative_to(run_dir)) for result in evaluation_results
        ],
    )
    output_path = run_dir / "subject_merge.json"
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    phase5b_result = {
        "enabled": phase5b_enabled,
        "audited_count": 0,
        "repair_count": 0,
        "reliable_count": 0,
        "unrepaired_count": 0,
        "artifacts": [],
    }
    if phase5b_enabled:
        phase5b_run = run_subject_merge_phase5b(
            run_dir=run_dir,
            model_call=model_call,
            router=router,
            prompt_path=prompt_path,
            repair_model_route=repair_model_route,
            contextual_repair_model_route=contextual_repair_model_route,
            phase5b_model_route=phase5b_model_route,
            provider_retry_limit=provider_retry_limit,
            provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        )
        phase5b_result = phase5b_run["phase5b"]
        artifact = _read_json(output_path)

    return {
        "summary": artifact["summary"],
        "artifact_path": output_path,
        "model_route": model_route,
        "area_partition_model_route": area_partition_model_route,
        "fine_clustering_model_route": fine_clustering_model_route,
        "evaluation_model_route": evaluation_model_route,
        "repair_model_route": repair_model_route,
        "contextual_repair_model_route": contextual_repair_model_route,
        "stage_counts": {
            "area_partition_count": 1,
            "fine_clustering_count": len(area_clusters_artifact.get("clusters") or []),
            "cluster_evaluation_count": len(evaluation_results),
            "singleton_passthrough_count": sum(
                1 for cluster in fine_clusters_artifact.get("clusters") or [] if len(cluster.get("candidate_ids") or []) == 1
            ),
        },
        "evaluation_batch_size": evaluation_batch_size,
        "phase5b": phase5b_result,
    }


def run_subject_merge_phase5b(
    *,
    run_dir: Path,
    model_call: ModelCall,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
    repair_model_route: str = FLASH_ROUTE_ALIAS,
    contextual_repair_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase5b_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    provider_retry_limit: int = 2,
    provider_retry_backoff_seconds: float = 10.0,
) -> dict[str, Any]:
    prompts = _load_subject_merge_prompts(prompt_path)
    artifact_path = run_dir / "subject_merge.json"
    if not artifact_path.is_file():
        raise StageBlockedError("Phase 5b requires an existing subject_merge.json from Phase 5")
    artifact = _read_json(artifact_path)
    registry_ref = artifact.get("candidate_registry_artifact") or "subject_merge_candidate_registry.json"
    registry_path = run_dir / str(registry_ref)
    if not registry_path.is_file():
        raise StageBlockedError("Phase 5b requires subject_merge_candidate_registry.json from Phase 5")
    registry = _read_json(registry_path)
    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)
    _clean_phase_five_b_artifacts(run_dir=run_dir)
    artifact.pop("phase5b_quality_audit", None)
    artifact.pop("phase5b_repair_decision_artifacts", None)

    result = {
        "enabled": True,
        "model_route": phase5b_model_route,
        "audited_count": 1,
        "repair_count": 0,
        "reliable_count": 0,
        "unrepaired_count": 0,
        "artifacts": ["subject_merge_quality_audit.json"],
    }

    repaired_artifact = json.loads(json.dumps(artifact, ensure_ascii=False))
    repair_artifacts: list[str] = []
    repaired_any = False

    deterministic_reasons = {"provenance_loss", "assignment_incomplete"}
    hard_guardrails = _build_subject_merge_quality_guardrails(artifact=repaired_artifact, registry=registry)
    deterministic_plans = [
        plan for plan in hard_guardrails.get("repair_plan") or [] if plan.get("repair_reason") in deterministic_reasons
    ]
    if deterministic_plans:
        repaired_artifact = _apply_subject_deterministic_repairs(
            artifact=repaired_artifact,
            registry=registry,
            repair_plans=deterministic_plans,
        )
        repaired_any = True

    audit = _run_subject_phase5b_audit(
        run_dir=run_dir,
        artifact=repaired_artifact,
        registry=registry,
        prompt=prompts["quality_audit"].text,
        prompt_path=prompts["quality_audit"].path_ref,
        runner=runner,
        model_route=phase5b_model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    if audit["reliability"] == "reliable":
        if repaired_any:
            result["repair_count"] = 1
            audit["reliability"] = "repaired"
        else:
            result["reliable_count"] = 1
        repaired_artifact["phase5b_quality_audit"] = audit
        _refresh_subject_merge_summary(repaired_artifact, registry=registry)
        artifact_path.write_text(json.dumps(repaired_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "subject_merge_quality_audit.json").write_text(
            json.dumps(audit, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return {
            "summary": repaired_artifact["summary"],
            "artifact_path": artifact_path,
            "phase5b": result,
        }

    for repair_plan in audit.get("repair_plan") or []:
        repair_reason = str(repair_plan.get("repair_reason") or "quality_repair")
        if repair_reason in deterministic_reasons:
            repaired_artifact = _apply_subject_deterministic_repairs(
                artifact=repaired_artifact,
                registry=registry,
                repair_plans=[repair_plan],
            )
            repaired_any = True
            continue
        target_candidate_ids = [
            candidate_id
            for candidate_id in repair_plan.get("candidate_ids") or []
            if isinstance(candidate_id, str) and candidate_id
        ]
        if not target_candidate_ids:
            continue
        repair_decision_path = _run_subject_phase5b_repair(
            run_dir=run_dir,
            artifact=repaired_artifact,
            registry=registry,
            quality_audit=audit,
            repair_reason=repair_reason,
            target_candidate_ids=target_candidate_ids,
            prompt=prompts["quality_repair"].text,
            prompt_path=prompts["quality_repair"].path_ref,
            runner=runner,
            model_route=phase5b_model_route,
            repair_model_route=repair_model_route,
            contextual_repair_model_route=contextual_repair_model_route,
            provider_retry_limit=provider_retry_limit,
            provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        )
        decision = _read_json(repair_decision_path)
        repaired_artifact = _apply_subject_phase5b_repair_decision(
            artifact=repaired_artifact,
            registry=registry,
            decision=decision,
            target_candidate_ids=target_candidate_ids,
        )
        repair_artifacts.append(str(repair_decision_path.relative_to(run_dir)))
        repaired_any = True

    final_audit = _run_subject_phase5b_audit(
        run_dir=run_dir,
        artifact=repaired_artifact,
        registry=registry,
        prompt=prompts["quality_audit"].text,
        prompt_path=prompts["quality_audit"].path_ref,
        runner=runner,
        model_route=phase5b_model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    result["audited_count"] = 2
    if repaired_any and final_audit["reliability"] == "reliable":
        result["repair_count"] = 1
        final_audit["reliability"] = "repaired"
    elif repaired_any:
        result["unrepaired_count"] = 1
        final_audit.setdefault("flags", []).append("repair_unstable")
        final_audit["reliability"] = "repair_required"
    else:
        result["unrepaired_count"] = 1
    if repair_artifacts:
        final_audit["repair_decision_artifacts"] = repair_artifacts
        repaired_artifact["phase5b_repair_decision_artifacts"] = repair_artifacts
    repaired_artifact["phase5b_quality_audit"] = final_audit
    _refresh_subject_merge_summary(repaired_artifact, registry=registry)
    artifact_path.write_text(json.dumps(repaired_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (run_dir / "subject_merge_quality_audit.json").write_text(
        json.dumps(final_audit, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "summary": repaired_artifact["summary"],
        "artifact_path": artifact_path,
        "phase5b": result,
    }


def _load_subject_merge_prompts(prompt_path: Path | None) -> dict[str, _SubjectMergePrompt]:
    prompts_root = Path(__file__).resolve().parents[3] / "prompts"
    selected = prompt_path or prompts_root / "subject_merge"
    if selected.is_file():
        text = selected.read_text(encoding="utf-8")
        path_ref = _prompt_path_ref(selected, prompts_root)
        return {
            task: _SubjectMergePrompt(text=text, path_ref=path_ref)
            for task in _SUBJECT_MERGE_PROMPT_FILES
        }
    if not selected.is_dir():
        raise StageBlockedError(f"Subject Merge prompt path does not exist: {selected}")
    prompts: dict[str, _SubjectMergePrompt] = {}
    for task, filename in _SUBJECT_MERGE_PROMPT_FILES.items():
        path = selected / filename
        if not path.is_file():
            raise StageBlockedError(f"Subject Merge missing task prompt: {path}")
        prompts[task] = _SubjectMergePrompt(
            text=path.read_text(encoding="utf-8"),
            path_ref=_prompt_path_ref(path, prompts_root),
        )
    return prompts


def _prompt_path_ref(path: Path, prompts_root: Path) -> str:
    try:
        return str(path.relative_to(prompts_root))
    except ValueError:
        return str(path)


def _run_subject_area_partition(
    *,
    run_dir: Path,
    registry: dict[str, Any],
    input_candidate_ids: list[str],
    scope: dict[str, Any],
    prompt: str,
    prompt_path: str,
    runner: StageRunner,
    model_route: str,
    repair_model_route: str,
    contextual_repair_model_route: str,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> dict[str, Any]:
    existing_path = run_dir / "subject_merge_area_clusters.json"
    existing = _existing_valid_subject_clusters_artifact(
        artifact_path=existing_path,
        registry=registry,
        artifact_type="subject_merge_area_clusters",
        schema_version="subject_merge_area_clusters.v0",
        model_route=model_route,
    )
    if existing:
        return existing

    model_input = _build_subject_clustering_input(
        task="subject_merge_area_partition",
        artifact_type="subject_merge_area_partition_input",
        schema_version="subject_merge_area_partition_input.v0",
        scope=scope,
        registry=registry,
        input_candidate_ids=input_candidate_ids,
        prompt=prompt,
        prompt_path=prompt_path,
        model_route=model_route,
        summary_only=True,
    )
    (run_dir / "subject_merge_area_partition_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    contract = StageContract(
        name="subject_merge_area_partition",
        required_inputs=["subject_merge_area_partition_input.json"],
        output_artifact="subject_merge_area_partition_decision.json",
        model_route=model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        validator=lambda artifact: validate_subject_clustering_decision(
            artifact,
            registry=registry,
            artifact_type="subject_merge_area_partition_decision",
            schema_version="subject_merge_area_partition_decision.v0",
        ),
        normalizer=lambda raw, inputs: _normalize_subject_clustering_output(
            raw,
            inputs,
            input_key="subject_merge_area_partition_input.json",
            artifact_type="subject_merge_area_partition_decision",
            schema_version="subject_merge_area_partition_decision.v0",
        ),
    )
    stage_result = _run_stage_with_provider_retry(
        runner=runner,
        contract=contract,
        run_dir=run_dir,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        failure_message="Subject Merge area partition failed without result",
    )
    decision = _read_json(stage_result.artifact_path)
    artifact = _build_subject_clusters_artifact(
        artifact_type="subject_merge_area_clusters",
        schema_version="subject_merge_area_clusters.v0",
        decision=decision,
        decision_artifact_path=str(stage_result.artifact_path.relative_to(run_dir)),
        registry_artifact_path="subject_merge_candidate_registry.json",
    )
    existing_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return artifact


def _run_subject_fine_clustering(
    *,
    run_dir: Path,
    registry: dict[str, Any],
    area_clusters_artifact: dict[str, Any],
    prompt: str,
    prompt_path: str,
    runner: StageRunner,
    model_route: str,
    repair_model_route: str,
    contextual_repair_model_route: str,
    concurrency: int,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> dict[str, Any]:
    existing_path = run_dir / "subject_merge_candidate_clusters.json"
    existing = _existing_valid_subject_clusters_artifact(
        artifact_path=existing_path,
        registry=registry,
        artifact_type="subject_merge_candidate_clusters",
        schema_version="subject_merge_candidate_clusters.v0",
        model_route=model_route,
    )
    if existing:
        return existing

    tasks: list[_SubjectFineClusteringTask] = []
    for index, area in enumerate(area_clusters_artifact.get("clusters") or [], start=1):
        if not isinstance(area, dict):
            continue
        area_id = str(area.get("id") or f"area_{index:03d}")
        candidate_ids = [str(candidate_id) for candidate_id in area.get("candidate_ids") or []]
        area_dir = run_dir / "subject_merge_fine_clustering" / _cluster_dir_name(area_id)
        area_dir.mkdir(parents=True, exist_ok=True)
        model_input = _build_subject_clustering_input(
            task="subject_merge_fine_clustering",
            artifact_type="subject_merge_fine_clustering_input",
            schema_version="subject_merge_fine_clustering_input.v0",
            scope={"id": registry.get("scope_id"), "area_id": area_id, "area": area},
            registry=registry,
            input_candidate_ids=candidate_ids,
            prompt=prompt,
            prompt_path=prompt_path,
            model_route=model_route,
            summary_only=False,
        )
        (area_dir / "subject_merge_fine_clustering_input.json").write_text(
            json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        contract = StageContract(
            name="subject_merge_fine_clustering",
            required_inputs=["subject_merge_fine_clustering_input.json"],
            output_artifact="subject_merge_fine_clustering_decision.json",
            model_route=model_route,
            repair_model_route=repair_model_route,
            contextual_repair_model_route=contextual_repair_model_route,
            validator=lambda artifact, registry=registry: validate_subject_clustering_decision(
                artifact,
                registry=registry,
                artifact_type="subject_merge_fine_clustering_decision",
                schema_version="subject_merge_fine_clustering_decision.v0",
            ),
            normalizer=lambda raw, inputs: _normalize_subject_clustering_output(
                raw,
                inputs,
                input_key="subject_merge_fine_clustering_input.json",
                artifact_type="subject_merge_fine_clustering_decision",
                schema_version="subject_merge_fine_clustering_decision.v0",
            ),
        )
        tasks.append(
            _SubjectFineClusteringTask(
                order=index,
                area_id=area_id,
                area_dir=area_dir,
                registry=registry,
                contract=contract,
            )
        )

    results = _run_subject_fine_clustering_tasks(
        tasks,
        runner=runner,
        concurrency=concurrency,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    scoped_clusters: list[dict[str, Any]] = []
    for result in sorted(results, key=lambda item: item.order):
        for cluster_index, cluster in enumerate(result.decision.get("clusters") or [], start=1):
            if not isinstance(cluster, dict):
                continue
            cluster_id = str(cluster.get("id") or f"cluster_{cluster_index:03d}")
            scoped = dict(cluster)
            scoped["id"] = f"{_cluster_dir_name(result.area_id)}__{_cluster_dir_name(cluster_id)}"
            scoped["area_id"] = result.area_id
            scoped_clusters.append(scoped)
    scoped_clusters, warnings = _canonicalize_cluster_candidate_coverage(
        clusters=scoped_clusters,
        input_candidate_ids=list(registry.get("candidates") or {}),
    )
    artifact = {
        "artifact_type": "subject_merge_candidate_clusters",
        "schema_version": "subject_merge_candidate_clusters.v0",
        "generated_at": _now(),
        "source_artifact": "source_ledger.json",
        "candidate_registry_artifact": "subject_merge_candidate_registry.json",
        "area_clusters_artifact": "subject_merge_area_clusters.json",
        "model_route": model_route,
        "input_candidate_ids": list(registry.get("candidates") or {}),
        "clusters": scoped_clusters,
        "normalization_warnings": warnings,
        "summary": {
            "input_candidate_count": len(registry.get("candidates") or {}),
            "cluster_count": len(scoped_clusters),
            "singleton_cluster_count": sum(1 for cluster in scoped_clusters if len(cluster.get("candidate_ids") or []) == 1),
        },
    }
    existing_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return artifact


def _run_subject_cluster_evaluations(
    *,
    run_dir: Path,
    registry: dict[str, Any],
    clusters_artifact: dict[str, Any],
    prompt: str,
    prompt_path: str,
    runner: StageRunner,
    model_route: str,
    repair_model_route: str,
    contextual_repair_model_route: str,
    concurrency: int,
    evaluation_batch_size: int,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> list[_SubjectClusterEvaluationResult]:
    clusters = [
        cluster
        for cluster in clusters_artifact.get("clusters") or []
        if isinstance(cluster, dict) and len(cluster.get("candidate_ids") or []) >= 2
    ]
    tasks: list[_SubjectClusterEvaluationTask] = []
    for batch_index, cluster_batch in enumerate(_cluster_batches(clusters, evaluation_batch_size), start=1):
        cluster_ids = [
            str(cluster.get("id") or f"cluster_{batch_index:03d}_{offset:03d}")
            for offset, cluster in enumerate(cluster_batch, start=1)
        ]
        cluster_id = cluster_ids[0] if len(cluster_ids) == 1 else f"batch_{batch_index:03d}"
        cluster_dir = run_dir / "subject_cluster_evaluations" / _cluster_dir_name(cluster_id)
        cluster_dir.mkdir(parents=True, exist_ok=True)
        input_candidate_ids = [
            str(candidate_id)
            for cluster in cluster_batch
            for candidate_id in cluster.get("candidate_ids") or []
        ]
        model_input = _build_subject_cluster_evaluation_input(
            clusters=cluster_batch,
            registry=registry,
            input_candidate_ids=input_candidate_ids,
            prompt=prompt,
            prompt_path=prompt_path,
            model_route=model_route,
            subject_candidate_clusters_artifact="subject_merge_candidate_clusters.json",
        )
        (cluster_dir / "subject_cluster_evaluation_input.json").write_text(
            json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        contract = StageContract(
            name="subject_cluster_evaluation",
            required_inputs=["subject_cluster_evaluation_input.json"],
            output_artifact="subject_cluster_evaluation_decision.json",
            model_route=model_route,
            repair_model_route=repair_model_route,
            contextual_repair_model_route=contextual_repair_model_route,
            validator=lambda artifact, registry=registry: validate_subject_merge_decision(artifact, registry),
            normalizer=_normalize_subject_cluster_evaluation_output,
        )
        tasks.append(
            _SubjectClusterEvaluationTask(
                order=batch_index,
                cluster_id=cluster_id,
                cluster_ids=cluster_ids,
                cluster_dir=cluster_dir,
                registry=registry,
                contract=contract,
            )
        )
    return _run_subject_cluster_evaluation_tasks(
        tasks,
        runner=runner,
        concurrency=concurrency,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )


def assemble_subject_merge(
    *,
    source_ledger: dict[str, Any],
    registry: dict[str, Any],
    decision: dict[str, Any],
    decision_artifact_path: str,
    registry_artifact_path: str,
    area_clusters_artifact: str | None = None,
    candidate_clusters_artifact: str | None = None,
    cluster_evaluation_decision_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    entries = registry.get("candidates") or {}
    concept_id_by_reduce_id: dict[str, str] = {}
    concepts: list[dict[str, Any]] = []
    assignment_status_by_candidate_id = {
        str(assignment.get("candidate_id") or ""): str(assignment.get("status") or "")
        for assignment in decision.get("candidate_assignments") or []
        if isinstance(assignment, dict)
    }
    for accepted in decision.get("accepted_concepts") or []:
        if not isinstance(accepted, dict):
            continue
        local_id = str(accepted.get("id") or "")
        concept = _concept_from_accepted(
            accepted=accepted,
            entries=entries,
            assignment_status_by_candidate_id=assignment_status_by_candidate_id,
        )
        concept_id_by_reduce_id[local_id] = concept["concept_id"]
        concepts.append(concept)

    candidate_assignments = []
    pruned_candidates = []
    review_candidates = []
    for assignment in decision.get("candidate_assignments") or []:
        if not isinstance(assignment, dict):
            continue
        item = dict(assignment)
        candidate_id = str(item.get("candidate_id") or "")
        entry = entries.get(candidate_id)
        if item.get("status") == "merged_into":
            item["merged_into_concept_id"] = concept_id_by_reduce_id.get(str(item.get("merged_into") or ""))
        elif item.get("status") == "used_in":
            item["accepted_concept_ids"] = [
                concept_id_by_reduce_id[accepted_id]
                for accepted_id in item.get("accepted_ids") or []
                if accepted_id in concept_id_by_reduce_id
            ]
        elif item.get("status") == "pruned" and entry:
            pruned_candidates.append(
                {
                    "candidate_ref": _candidate_ref(entry),
                    "pruning_reason": item.get("reason"),
                    "explanation": item.get("explanation"),
                }
            )
        elif item.get("status") == "review" and entry:
            review_candidates.append(
                {
                    "candidate_ref": _candidate_ref(entry),
                    "explanation": item.get("explanation"),
                }
            )
        candidate_assignments.append(item)

    artifact = {
        "artifact_type": "subject_merge",
        "schema_version": "subject_merge.v0",
        "generated_at": _now(),
        "source_artifact": "source_ledger.json",
        "candidate_registry_artifact": registry_artifact_path,
        "semantic_reduce_decision_artifact": decision_artifact_path,
        "area_clusters_artifact": area_clusters_artifact,
        "subject_candidate_clusters_artifact": candidate_clusters_artifact,
        "cluster_evaluation_decision_artifacts": cluster_evaluation_decision_artifacts or [],
        "model_route": decision.get("model_route"),
        "course_id": source_ledger.get("course_id"),
        "module_id": source_ledger.get("module_id"),
        "subject_id": source_ledger.get("subject_id"),
        "concepts": concepts,
        "candidate_assignments": candidate_assignments,
        "pruned_candidates": pruned_candidates,
        "review_candidates": review_candidates,
    }
    _refresh_subject_merge_summary(artifact, registry=registry)
    return artifact


def validate_subject_merge_decision(decision: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors = validate_reduce_decision(decision, registry)
    for index, assignment in enumerate(decision.get("candidate_assignments") or []):
        if not isinstance(assignment, dict):
            continue
        status = assignment.get("status")
        if status == "review":
            errors.append(f"candidate_assignments[{index}].status must not use review in subject_merge")
        if status == "pruned":
            errors.append(f"candidate_assignments[{index}].status must not use pruned in subject_merge")
    if decision.get("pruned"):
        errors.append("semantic_reduce_decision.pruned must be empty for subject_merge")
    summary = decision.get("summary") or {}
    if summary.get("review_count") not in (0, None):
        errors.append("semantic_reduce_decision.summary.review_count must be 0 for subject_merge")
    if summary.get("pruned_count") not in (0, None):
        errors.append("semantic_reduce_decision.summary.pruned_count must be 0 for subject_merge")
    return errors


def validate_subject_clustering_decision(
    artifact: dict[str, Any],
    *,
    registry: dict[str, Any],
    artifact_type: str,
    schema_version: str,
) -> list[str]:
    errors = _validate_subject_cluster_shape(
        artifact,
        registry=registry,
        artifact_type=artifact_type,
        schema_version=schema_version,
    )
    summary = artifact.get("summary") or {}
    clusters = artifact.get("clusters") if isinstance(artifact.get("clusters"), list) else []
    input_ids = artifact.get("input_candidate_ids") if isinstance(artifact.get("input_candidate_ids"), list) else []
    if summary.get("input_candidate_count") != len(input_ids):
        errors.append(f"{artifact_type}.summary.input_candidate_count does not match input_candidate_ids length")
    if summary.get("cluster_count") != len(clusters):
        errors.append(f"{artifact_type}.summary.cluster_count does not match clusters length")
    return errors


def _ensure_lesson_reconciliation_complete(*, run_dir: Path, source_ledger: dict[str, Any]) -> None:
    summary_path = run_dir / "lesson_reconciliation_summary.json"
    if not summary_path.is_file():
        raise StageBlockedError("Subject Merge requires a complete lesson_reconciliation_summary.json from Phase 4")
    summary_artifact = _read_json(summary_path)
    summary = summary_artifact.get("summary") or {}
    lesson_count = len(source_ledger.get("lessons") or [])
    reconciled_count = int(summary.get("reconciled_lesson_count") or 0)
    skipped_count = int(summary.get("skipped_count") or 0)
    if summary.get("lesson_count") != lesson_count:
        raise StageBlockedError("Subject Merge blocked: Phase 4 summary lesson_count does not match Source Ledger")
    if reconciled_count + skipped_count != lesson_count:
        raise StageBlockedError("Subject Merge blocked: Phase 4 did not finish every lesson")

    missing_artifacts = []
    for artifact_ref in summary_artifact.get("artifacts") or []:
        artifact_path = run_dir / str(artifact_ref)
        if not artifact_path.is_file():
            missing_artifacts.append(str(artifact_ref))
    if missing_artifacts:
        raise StageBlockedError(
            "Subject Merge blocked: Phase 4 summary references missing artifacts: " + ", ".join(missing_artifacts)
        )


def _subject_candidate_sources(*, run_dir: Path, source_ledger: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for lesson_index, lesson in enumerate(source_ledger.get("lessons") or [], start=1):
        lesson_id = str(lesson.get("lesson_id") or "")
        artifact_path = run_dir / "lessons" / lesson_id / "lesson_reconciliation.json"
        if not artifact_path.is_file():
            continue
        artifact = _read_json(artifact_path)
        if artifact.get("artifact_type") != "lesson_reconciliation":
            raise StageBlockedError(f"Invalid Lesson Reconciliation artifact: {artifact_path}")
        candidates = []
        for candidate in artifact.get("reconciled_candidates") or []:
            if not isinstance(candidate, dict):
                continue
            item = dict(candidate)
            item["candidate_id"] = str(candidate.get("reconciled_candidate_id") or "")
            item["source_anchors"] = _anchors_from_evidence(candidate.get("evidence") or [])
            candidates.append(item)
        sources.append(
            {
                "namespace": f"lr{lesson_index:03d}",
                "artifact_type": "lesson_reconciliation",
                "artifact_path": str(artifact_path.relative_to(run_dir)),
                "lesson_id": lesson_id,
                "evidence_type": "lesson_reconciliation",
                "source_metadata": {
                    "lesson_id": lesson_id,
                    "lesson_title": lesson.get("title"),
                },
                "candidates": candidates,
            }
        )
    return sources


def _subject_scope(source_ledger: dict[str, Any]) -> dict[str, Any]:
    scope_id = "-".join(
        str(source_ledger.get(key) or "")
        for key in ("course_id", "module_id", "subject_id")
        if source_ledger.get(key)
    )
    return {
        "id": scope_id,
        "course_id": source_ledger.get("course_id"),
        "module_id": source_ledger.get("module_id"),
        "subject_id": source_ledger.get("subject_id"),
    }


def _build_subject_clustering_input(
    *,
    task: str,
    artifact_type: str,
    schema_version: str,
    scope: dict[str, Any],
    registry: dict[str, Any],
    input_candidate_ids: list[str],
    prompt: str,
    prompt_path: str,
    model_route: str,
    summary_only: bool,
) -> dict[str, Any]:
    registry_candidates = registry.get("candidates") or {}
    _ensure_known_candidate_ids(input_candidate_ids, registry_candidates)
    return {
        "artifact_type": artifact_type,
        "schema_version": schema_version,
        "source_artifact": registry.get("source_artifact"),
        "candidate_registry_artifact": "subject_merge_candidate_registry.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": task,
        "model_route": model_route,
        "scope": scope,
        "input_candidate_ids": input_candidate_ids,
        "candidates": [
            _compact_subject_candidate_view(registry_candidates[candidate_id], summary_only=summary_only)
            for candidate_id in input_candidate_ids
        ],
        "candidate_assignment_rule": (
            "Cluster only. Every input candidate ID must appear exactly once across clusters. "
            "Prefer tight clusters; topic overlap alone is not a cluster."
        ),
        "web_access_policy": _no_web_policy(),
    }


def _build_subject_cluster_evaluation_input(
    *,
    clusters: list[dict[str, Any]],
    registry: dict[str, Any],
    input_candidate_ids: list[str],
    prompt: str,
    prompt_path: str,
    model_route: str,
    subject_candidate_clusters_artifact: str,
) -> dict[str, Any]:
    registry_candidates = registry.get("candidates") or {}
    _ensure_known_candidate_ids(input_candidate_ids, registry_candidates)
    primary_cluster = clusters[0] if clusters else {}
    return {
        "artifact_type": "subject_cluster_evaluation_input",
        "schema_version": "subject_cluster_evaluation_input.v0",
        "source_artifact": registry.get("source_artifact"),
        "candidate_registry_artifact": "subject_merge_candidate_registry.json",
        "subject_candidate_clusters_artifact": subject_candidate_clusters_artifact,
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "subject_cluster_evaluation",
        "model_route": model_route,
        "scope_id": registry.get("scope_id"),
        "cluster": primary_cluster,
        "clusters": clusters,
        "input_candidate_ids": input_candidate_ids,
        "candidates": [
            _compact_subject_candidate_view(registry_candidates[candidate_id], summary_only=False)
            for candidate_id in input_candidate_ids
        ],
        "output_contract": _subject_decision_output_contract(),
        "web_access_policy": _no_web_policy(),
    }


def _normalize_subject_clustering_output(
    raw: str,
    inputs: dict[str, Any],
    *,
    input_key: str,
    artifact_type: str,
    schema_version: str,
) -> dict[str, Any]:
    model_input = inputs[input_key]
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"{artifact_type} model output must be a JSON object")
    clusters = payload.get("clusters")
    if not isinstance(clusters, list):
        raise ValueError(f"{artifact_type} model output must include clusters")
    normalized_clusters = []
    for index, cluster in enumerate(clusters, start=1):
        if not isinstance(cluster, dict):
            normalized_clusters.append(cluster)
            continue
        candidate_ids = cluster.get("candidate_ids")
        if candidate_ids is None:
            candidate_ids = cluster.get("candidates")
        cluster_id = str(cluster.get("id") or f"cluster_{index:03d}")
        normalized_clusters.append(
            {
                "id": cluster_id,
                "label": cluster.get("label") or cluster.get("name") or cluster_id,
                "rationale": cluster.get("rationale") or cluster.get("reason") or "",
                "candidate_ids": candidate_ids,
            }
        )
    input_candidate_ids = model_input.get("input_candidate_ids") or []
    normalized_clusters, normalization_warnings = _canonicalize_cluster_candidate_coverage(
        clusters=normalized_clusters,
        input_candidate_ids=input_candidate_ids,
    )
    return {
        "artifact_type": artifact_type,
        "schema_version": schema_version,
        "generated_at": _now(),
        "scope_id": str((model_input.get("scope") or {}).get("id") or ""),
        "stage_name": str(model_input.get("task") or ""),
        "model_route": str(model_input.get("model_route") or PRO_ROUTE_ALIAS),
        "input_candidate_ids": input_candidate_ids,
        "clusters": normalized_clusters,
        "normalization_warnings": normalization_warnings,
        "summary": {
            "input_candidate_count": len(input_candidate_ids),
            "cluster_count": len(normalized_clusters),
        },
    }


def _normalize_subject_cluster_evaluation_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    model_input = inputs["subject_cluster_evaluation_input.json"]
    decision = normalize_decision_output(
        raw=raw,
        scope_id=str(model_input.get("scope_id") or ""),
        stage_name="subject_cluster_evaluation",
        model_route=str(model_input.get("model_route") or PRO_THINKING_ROUTE_ALIAS),
        input_candidate_ids=model_input.get("input_candidate_ids") or [],
    )
    return _canonicalize_subject_reduce_decision_assignments(decision, candidate_views=model_input.get("candidates") or [])


def _normalize_subject_phase5b_audit_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    model_input = inputs["subject_merge_quality_audit_input.json"]
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("subject_merge_quality_audit model output must be a JSON object")

    flags = _stable_unique(
        [
            str(flag)
            for flag in payload.get("flags") or []
            if isinstance(flag, str) and flag in _SUBJECT_MERGE_AUDIT_FLAGS and flag != "repair_unstable"
        ]
    )
    repair_plan = _normalize_subject_audit_repair_plan(payload.get("repair_plan") or [])
    missed_merge_candidates = _normalize_missed_merge_candidates(payload.get("missed_merge_candidates") or [])
    if repair_plan and not flags:
        flags = _stable_unique(
            [
                "missed_obvious_merge" if item.get("repair_reason") == "missed_obvious_merge" else str(item.get("repair_reason"))
                for item in repair_plan
                if str(item.get("repair_reason") or "") in _SUBJECT_MERGE_AUDIT_FLAGS
            ]
        )
    if missed_merge_candidates and "missed_obvious_merge" not in flags:
        flags.append("missed_obvious_merge")

    reliability = str(payload.get("reliability") or "").strip()
    if reliability not in {"reliable", "repair_required"}:
        reliability = "repair_required" if flags or repair_plan else "reliable"
    if reliability == "reliable" and (flags or repair_plan):
        reliability = "repair_required"

    scores = payload.get("scores") if isinstance(payload.get("scores"), dict) else {}
    normalized_scores: dict[str, int] = {}
    default_score = 1 if flags else 3
    for field in _SUBJECT_MERGE_AUDIT_SCORE_FIELDS:
        value = scores.get(field)
        if isinstance(value, bool):
            value = int(value)
        if not isinstance(value, int):
            value = default_score
        normalized_scores[field] = max(0, min(3, value))
    if flags:
        normalized_scores["net_phase5_benefit"] = min(normalized_scores.values())

    return {
        "artifact_type": "subject_merge_quality_audit",
        "schema_version": "subject_merge_quality_audit.v0",
        "generated_at": _now(),
        "scope_id": str(model_input.get("scope_id") or ""),
        "stage_name": "subject_merge_quality_audit",
        "model_route": str(model_input.get("model_route") or PRO_THINKING_ROUTE_ALIAS),
        "scores": normalized_scores,
        "reliability": reliability,
        "flags": flags,
        "metrics": (model_input.get("guardrails") or {}).get("metrics") or {},
        "guardrail_findings": (model_input.get("guardrails") or {}).get("findings") or [],
        "repair_plan": repair_plan,
        "missed_merge_candidates": missed_merge_candidates,
    }


def _normalize_subject_audit_repair_plan(raw_items: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    normalized = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        reason = str(item.get("repair_reason") or item.get("reason") or "").strip()
        if reason not in _SUBJECT_MERGE_AUDIT_REPAIR_REASONS:
            continue
        candidate_ids = _stable_unique(
            [
                candidate_id
                for candidate_id in item.get("candidate_ids") or []
                if isinstance(candidate_id, str) and candidate_id
            ]
        )
        normalized.append(
            {
                "repair_reason": reason,
                "candidate_ids": candidate_ids,
                "explanation": str(item.get("explanation") or item.get("rationale") or "").strip(),
            }
        )
    return normalized


def _normalize_missed_merge_candidates(raw_items: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_items, list):
        return []
    normalized = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        candidate_ids = _stable_unique(
            [
                candidate_id
                for candidate_id in item.get("candidate_ids") or []
                if isinstance(candidate_id, str) and candidate_id
            ]
        )
        if len(candidate_ids) < 2:
            continue
        confidence = str(item.get("confidence") or "").strip().lower()
        if confidence not in {"high", "medium", "low"}:
            confidence = "high"
        normalized.append(
            {
                "candidate_ids": candidate_ids,
                "confidence": confidence,
                "explanation": str(item.get("explanation") or item.get("rationale") or "").strip(),
            }
        )
    return normalized


def _normalize_subject_phase5b_repair_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    model_input = inputs["subject_merge_quality_repair_input.json"]
    decision = normalize_decision_output(
        raw=raw,
        scope_id=str(model_input.get("scope_id") or ""),
        stage_name="subject_merge_quality_repair",
        model_route=str(model_input.get("model_route") or PRO_THINKING_ROUTE_ALIAS),
        input_candidate_ids=model_input.get("target_candidate_ids") or [],
    )
    return _canonicalize_subject_reduce_decision_assignments(decision, candidate_views=model_input.get("target_candidates") or [])


def _canonicalize_subject_reduce_decision_assignments(
    decision: dict[str, Any],
    *,
    candidate_views: list[dict[str, Any]],
) -> dict[str, Any]:
    input_candidate_ids = [
        candidate_id
        for candidate_id in decision.get("input_candidate_ids") or []
        if isinstance(candidate_id, str) and candidate_id
    ]
    accepted_concepts = [
        accepted
        for accepted in decision.get("accepted_concepts") or []
        if isinstance(accepted, dict)
    ]
    accepted_ids_by_source_candidate: dict[str, list[str]] = {}
    for accepted in accepted_concepts:
        accepted_id = str(accepted.get("id") or "")
        if not accepted_id:
            continue
        for candidate_id in accepted.get("source_candidate_ids") or []:
            if isinstance(candidate_id, str) and candidate_id:
                accepted_ids_by_source_candidate.setdefault(candidate_id, []).append(accepted_id)

    candidate_by_id = {str(candidate.get("id") or ""): candidate for candidate in candidate_views if isinstance(candidate, dict)}
    accepted_by_id = {
        str(accepted.get("id") or ""): accepted
        for accepted in accepted_concepts
        if isinstance(accepted, dict) and str(accepted.get("id") or "")
    }
    for assignment in decision.get("candidate_assignments") or []:
        if not isinstance(assignment, dict):
            continue
        candidate_id = str(assignment.get("candidate_id") or "")
        if not candidate_id or candidate_id not in candidate_by_id:
            continue
        referenced_ids = _assignment_referenced_accepted_ids(assignment)
        for accepted_id in referenced_ids:
            if accepted_id in accepted_by_id:
                continue
            accepted = _standalone_accepted_from_candidate_view(
                candidate_by_id[candidate_id],
                accepted_id=accepted_id,
            )
            accepted["merge_rationale"] = (
                "Deterministically synthesized because the model assigned this candidate to "
                "a missing accepted concept ID."
            )
            accepted_concepts.append(accepted)
            accepted_by_id[accepted_id] = accepted
            accepted_ids_by_source_candidate.setdefault(candidate_id, []).append(accepted_id)

    canonical_assignments: list[dict[str, Any]] = []
    assigned_candidate_ids: set[str] = set()
    for assignment in decision.get("candidate_assignments") or []:
        if not isinstance(assignment, dict):
            canonical_assignments.append(assignment)
            continue
        candidate_id = str(assignment.get("candidate_id") or "")
        if candidate_id in assigned_candidate_ids:
            continue
        if candidate_id:
            assigned_candidate_ids.add(candidate_id)
        canonical_assignments.append(assignment)

    for candidate_id in input_candidate_ids:
        if candidate_id in assigned_candidate_ids:
            continue
        accepted_ids = accepted_ids_by_source_candidate.get(candidate_id) or []
        if accepted_ids:
            canonical_assignments.append(
                {
                    "candidate_id": candidate_id,
                    "status": "used_in",
                    "accepted_ids": accepted_ids,
                }
            )
        else:
            accepted = _standalone_accepted_from_candidate_view(
                candidate_by_id.get(candidate_id) or {"id": candidate_id},
                accepted_id=f"standalone_{_compact_id_fragment(candidate_id)}",
            )
            accepted_concepts.append(accepted)
            canonical_assignments.append(
                {
                    "candidate_id": candidate_id,
                    "status": "used_in",
                    "accepted_ids": [accepted["id"]],
                    "explanation": "Deterministically accepted as standalone because the model omitted this candidate.",
                }
            )
        assigned_candidate_ids.add(candidate_id)

    decision["accepted"] = accepted_concepts
    decision["accepted_concepts"] = accepted_concepts
    decision["candidate_assignments"] = canonical_assignments
    decision["pruned"] = []
    decision["summary"] = {
        "input_candidate_count": len(input_candidate_ids),
        "accepted_count": len(accepted_concepts),
        "pruned_count": 0,
        "candidate_assignment_count": len(canonical_assignments),
        "review_count": 0,
    }
    return decision


def _assignment_referenced_accepted_ids(assignment: dict[str, Any]) -> list[str]:
    status = assignment.get("status")
    if status == "merged_into":
        accepted_id = str(assignment.get("merged_into") or "")
        return [accepted_id] if accepted_id else []
    accepted_ids = assignment.get("accepted_ids")
    if not isinstance(accepted_ids, list):
        return []
    return [accepted_id for accepted_id in accepted_ids if isinstance(accepted_id, str) and accepted_id]


def _build_subject_clusters_artifact(
    *,
    artifact_type: str,
    schema_version: str,
    decision: dict[str, Any],
    decision_artifact_path: str,
    registry_artifact_path: str,
) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "schema_version": schema_version,
        "generated_at": _now(),
        "source_artifact": "source_ledger.json",
        "candidate_registry_artifact": registry_artifact_path,
        "clustering_decision_artifact": decision_artifact_path,
        "model_route": decision.get("model_route"),
        "input_candidate_ids": decision.get("input_candidate_ids") or [],
        "clusters": decision.get("clusters") or [],
        "normalization_warnings": decision.get("normalization_warnings") or [],
        "summary": {
            "input_candidate_count": len(decision.get("input_candidate_ids") or []),
            "cluster_count": len(decision.get("clusters") or []),
        },
    }


def _combine_subject_cluster_evaluation_decisions(
    *,
    scope_id: str,
    input_candidate_ids: list[str],
    model_route: str,
    clusters: list[dict[str, Any]],
    registry: dict[str, Any],
    evaluation_results: list[_SubjectClusterEvaluationResult],
) -> dict[str, Any]:
    accepted_concepts: list[dict[str, Any]] = []
    candidate_assignments: list[dict[str, Any]] = []
    entries = registry.get("candidates") or {}

    for cluster in clusters:
        if not isinstance(cluster, dict):
            continue
        cluster_id = str(cluster.get("id") or "")
        candidate_ids = [str(candidate_id) for candidate_id in cluster.get("candidate_ids") or []]
        if len(candidate_ids) == 1:
            candidate_id = candidate_ids[0]
            accepted_id = f"{_cluster_dir_name(cluster_id)}__standalone_{_compact_id_fragment(candidate_id)}"
            accepted_concepts.append(
                _standalone_accepted_from_entry(entries[candidate_id], accepted_id=accepted_id)
            )
            candidate_assignments.append(
                {
                    "candidate_id": candidate_id,
                    "status": "used_in",
                    "accepted_ids": [accepted_id],
                    "explanation": "Deterministic singleton passthrough.",
                }
            )
            continue

    for result in sorted(evaluation_results, key=lambda item: item.order):
        prefix = _cluster_dir_name(result.cluster_id)
        local_id_map: dict[str, str] = {}
        for index, accepted in enumerate(result.decision.get("accepted_concepts") or [], start=1):
            if not isinstance(accepted, dict):
                continue
            original_id = str(accepted.get("id") or f"accepted_{index:03d}")
            scoped_id = f"{prefix}__{original_id}"
            local_id_map[original_id] = scoped_id
            scoped = dict(accepted)
            scoped["id"] = scoped_id
            accepted_concepts.append(scoped)
        for assignment in result.decision.get("candidate_assignments") or []:
            if not isinstance(assignment, dict):
                continue
            scoped_assignment = dict(assignment)
            accepted_ids = scoped_assignment.get("accepted_ids")
            if isinstance(accepted_ids, list):
                scoped_assignment["accepted_ids"] = [
                    local_id_map.get(str(accepted_id), str(accepted_id))
                    for accepted_id in accepted_ids
                    if isinstance(accepted_id, str)
                ]
            merged_into = scoped_assignment.get("merged_into")
            if isinstance(merged_into, str):
                scoped_assignment["merged_into"] = local_id_map.get(merged_into, merged_into)
            candidate_assignments.append(scoped_assignment)

    assigned_ids = {
        str(assignment.get("candidate_id") or "")
        for assignment in candidate_assignments
        if isinstance(assignment, dict)
    }
    for candidate_id in input_candidate_ids:
        if candidate_id in assigned_ids or candidate_id not in entries:
            continue
        accepted_id = f"fallback__standalone_{_compact_id_fragment(candidate_id)}"
        accepted_concepts.append(_standalone_accepted_from_entry(entries[candidate_id], accepted_id=accepted_id))
        candidate_assignments.append(
            {
                "candidate_id": candidate_id,
                "status": "used_in",
                "accepted_ids": [accepted_id],
                "explanation": "Deterministically accepted as standalone because no cluster evaluation assigned it.",
            }
        )

    return {
        "artifact_type": "semantic_reduce_decision",
        "schema_version": "semantic_reduce_decision.v0",
        "generated_at": _now(),
        "scope_id": scope_id,
        "stage_name": "subject_merge",
        "model_route": model_route,
        "input_candidate_ids": input_candidate_ids,
        "accepted": accepted_concepts,
        "accepted_concepts": accepted_concepts,
        "candidate_assignments": candidate_assignments,
        "pruned": [],
        "summary": {
            "input_candidate_count": len(input_candidate_ids),
            "accepted_count": len(accepted_concepts),
            "pruned_count": 0,
            "candidate_assignment_count": len(candidate_assignments),
            "review_count": 0,
        },
    }


def _build_subject_merge_quality_audit(*, artifact: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    entries = registry.get("candidates") or {}
    input_ids = list(entries)
    concepts = [concept for concept in artifact.get("concepts") or [] if isinstance(concept, dict)]
    candidate_assignments = [
        assignment for assignment in artifact.get("candidate_assignments") or [] if isinstance(assignment, dict)
    ]
    assigned_ids = {
        str(assignment.get("candidate_id") or "")
        for assignment in candidate_assignments
        if str(assignment.get("candidate_id") or "")
    }
    concept_source_ids = [
        candidate_id
        for concept in concepts
        for candidate_id in concept.get("source_candidate_ids") or []
        if isinstance(candidate_id, str)
    ]
    covered_ids = set(concept_source_ids)
    missing_ids = [candidate_id for candidate_id in input_ids if candidate_id not in assigned_ids or candidate_id not in covered_ids]

    flags: list[str] = []
    repair_plan: list[dict[str, Any]] = []
    if missing_ids:
        flags.append("assignment_incomplete")
        repair_plan.append(
            {
                "repair_reason": "assignment_incomplete",
                "candidate_ids": missing_ids,
                "explanation": "Every lesson-local concept must be assigned; missing candidates become standalone.",
            }
        )

    provenance_loss_ids: list[str] = []
    for concept in concepts:
        source_ids = [candidate_id for candidate_id in concept.get("source_candidate_ids") or [] if candidate_id in entries]
        expected = _occurrences_for_source_candidate_ids(entries, source_ids)
        actual = concept.get("occurrences")
        if not isinstance(actual, list) or len(actual) != len(expected):
            provenance_loss_ids.extend(source_ids)
            continue
        expected_keys = _occurrence_keys(expected)
        actual_keys = _occurrence_keys(actual)
        if expected_keys != actual_keys:
            provenance_loss_ids.extend(source_ids)
    if provenance_loss_ids:
        flags.append("provenance_loss")
        repair_plan.append(
            {
                "repair_reason": "provenance_loss",
                "candidate_ids": sorted(set(provenance_loss_ids), key=provenance_loss_ids.index),
                "explanation": "Concept occurrences do not match lesson-local source provenance.",
            }
        )

    over_merged_target_ids: list[str] = []
    granularity_target_ids: list[str] = []
    for concept in concepts:
        source_ids = [candidate_id for candidate_id in concept.get("source_candidate_ids") or [] if candidate_id in entries]
        if len(source_ids) < 2:
            continue
        depths = [_infer_candidate_depth(entries[candidate_id]) for candidate_id in source_ids]
        depth_bands = {_depth_band(depth) for depth in depths}
        if len(depth_bands) > 1:
            over_merged_target_ids.extend(source_ids)
        if "definition" in depth_bands and any(depth in {"implementation", "limitation", "math", "application"} for depth in depth_bands):
            granularity_target_ids.extend(source_ids)
    if over_merged_target_ids:
        flags.append("over_merged_group")
        repair_plan.append(
            {
                "repair_reason": "over_merged_group",
                "candidate_ids": _stable_unique(over_merged_target_ids),
                "explanation": "A merged concept crosses depth bands or added teachable behavior.",
            }
        )
    if granularity_target_ids:
        flags.append("granularity_violation")

    duplicate_pairs = _find_residual_duplicate_pairs(concepts, entries)
    if duplicate_pairs:
        flags.append("residual_duplicate")
        for duplicate_pair in duplicate_pairs:
            repair_plan.append(
                {
                    "repair_reason": "residual_duplicate",
                    "candidate_ids": duplicate_pair,
                    "explanation": "Two surviving subject concepts look like duplicate definitions.",
                }
            )

    identity_score = 1 if "over_merged_group" in flags else 3
    granularity_score = 1 if "granularity_violation" in flags else 3
    provenance_score = 0 if "provenance_loss" in flags else 3
    assignment_score = 0 if "assignment_incomplete" in flags else 3
    overlap_score = 1 if "residual_duplicate" in flags else 3
    coherence_score = 2 if flags else 3
    net_score = min(
        identity_score,
        granularity_score,
        provenance_score,
        assignment_score,
        overlap_score,
        coherence_score,
    )
    return {
        "artifact_type": "subject_merge_quality_audit",
        "schema_version": "subject_merge_quality_audit.v0",
        "generated_at": _now(),
        "scores": {
            "identity_correctness": identity_score,
            "granularity_preservation": granularity_score,
            "provenance_preservation": provenance_score,
            "assignment_completeness": assignment_score,
            "overlap_reduction": overlap_score,
            "subject_coherence": coherence_score,
            "net_phase5_benefit": net_score,
        },
        "reliability": "repair_required" if flags else "reliable",
        "flags": flags,
        "metrics": {
            "input_candidate_count": len(input_ids),
            "concept_count": len(concepts),
            "assignment_count": len(candidate_assignments),
            "missing_assignment_count": len(missing_ids),
            "provenance_loss_candidate_count": len(set(provenance_loss_ids)),
            "largest_concept_source_count": max((len(concept.get("source_candidate_ids") or []) for concept in concepts), default=0),
        },
        "repair_plan": repair_plan,
    }


def _run_subject_phase5b_audit(
    *,
    run_dir: Path,
    artifact: dict[str, Any],
    registry: dict[str, Any],
    prompt: str,
    prompt_path: str,
    runner: StageRunner,
    model_route: str,
    repair_model_route: str,
    contextual_repair_model_route: str,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> dict[str, Any]:
    model_input = _build_subject_phase5b_audit_input(
        run_dir=run_dir,
        artifact=artifact,
        registry=registry,
        prompt=prompt,
        prompt_path=prompt_path,
        model_route=model_route,
    )
    (run_dir / "subject_merge_quality_audit_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    contract = StageContract(
        name="subject_merge_quality_audit",
        required_inputs=["subject_merge_quality_audit_input.json"],
        output_artifact="subject_merge_quality_audit.json",
        model_route=model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        validator=lambda artifact: _validate_subject_phase5b_audit(artifact, registry=registry),
        normalizer=_normalize_subject_phase5b_audit_output,
    )
    result = _run_stage_with_provider_retry(
        runner=runner,
        contract=contract,
        run_dir=run_dir,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        failure_message="Subject Merge Phase 5b quality audit failed without result",
    )
    return _read_json(result.artifact_path)


def _build_subject_phase5b_audit_input(
    *,
    run_dir: Path,
    artifact: dict[str, Any],
    registry: dict[str, Any],
    prompt: str,
    prompt_path: str,
    model_route: str,
) -> dict[str, Any]:
    entries = registry.get("candidates") or {}
    guardrails = _build_subject_merge_quality_guardrails(artifact=artifact, registry=registry)
    current_subject_concepts = [
        _compact_subject_concept_audit_view(concept, entries=entries)
        for concept in artifact.get("concepts") or []
        if isinstance(concept, dict)
    ]
    merge_attempts = _subject_merge_audit_attempts(run_dir=run_dir)
    return {
        "artifact_type": "subject_merge_quality_audit_input",
        "schema_version": "subject_merge_quality_audit_input.v0",
        "source_artifact": artifact.get("source_artifact") or "source_ledger.json",
        "subject_merge_artifact": "subject_merge.json",
        "candidate_registry_artifact": artifact.get("candidate_registry_artifact") or "subject_merge_candidate_registry.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "subject_merge_quality_audit",
        "model_route": model_route,
        "scope_id": registry.get("scope_id"),
        "guardrails": guardrails,
        "current_subject_concepts": current_subject_concepts,
        "merge_attempts": merge_attempts,
        "review_signals": _subject_merge_review_signals(
            concepts=current_subject_concepts,
            merge_attempts=merge_attempts,
        ),
        "output_contract": _subject_quality_audit_output_contract(),
        "web_access_policy": _no_web_policy(),
    }


def _build_subject_merge_quality_guardrails(*, artifact: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    entries = registry.get("candidates") or {}
    input_ids = list(entries)
    concepts = [concept for concept in artifact.get("concepts") or [] if isinstance(concept, dict)]
    candidate_assignments = [
        assignment for assignment in artifact.get("candidate_assignments") or [] if isinstance(assignment, dict)
    ]
    assigned_ids = {
        str(assignment.get("candidate_id") or "")
        for assignment in candidate_assignments
        if str(assignment.get("candidate_id") or "")
    }
    concept_source_ids = [
        candidate_id
        for concept in concepts
        for candidate_id in concept.get("source_candidate_ids") or []
        if isinstance(candidate_id, str)
    ]
    covered_ids = set(concept_source_ids)
    missing_ids = [candidate_id for candidate_id in input_ids if candidate_id not in assigned_ids or candidate_id not in covered_ids]

    findings: list[dict[str, Any]] = []
    repair_plan: list[dict[str, Any]] = []
    if missing_ids:
        findings.append(
            {
                "flag": "assignment_incomplete",
                "candidate_ids": missing_ids,
                "explanation": "Every lesson-local concept must be assigned to a subject concept.",
            }
        )
        repair_plan.append(
            {
                "repair_reason": "assignment_incomplete",
                "candidate_ids": missing_ids,
                "explanation": "Every lesson-local concept must be assigned; missing candidates become standalone.",
            }
        )

    provenance_loss_ids: list[str] = []
    for concept in concepts:
        source_ids = [candidate_id for candidate_id in concept.get("source_candidate_ids") or [] if candidate_id in entries]
        expected = _occurrences_for_source_candidate_ids(entries, source_ids)
        actual = concept.get("occurrences")
        if not isinstance(actual, list) or len(actual) != len(expected):
            provenance_loss_ids.extend(source_ids)
            continue
        if _occurrence_keys(expected) != _occurrence_keys(actual):
            provenance_loss_ids.extend(source_ids)
    if provenance_loss_ids:
        candidate_ids = sorted(set(provenance_loss_ids), key=provenance_loss_ids.index)
        findings.append(
            {
                "flag": "provenance_loss",
                "candidate_ids": candidate_ids,
                "explanation": "Concept occurrences do not match lesson-local source provenance.",
            }
        )
        repair_plan.append(
            {
                "repair_reason": "provenance_loss",
                "candidate_ids": candidate_ids,
                "explanation": "Concept occurrences do not match lesson-local source provenance.",
            }
        )

    return {
        "metrics": {
            "input_candidate_count": len(input_ids),
            "concept_count": len(concepts),
            "assignment_count": len(candidate_assignments),
            "missing_assignment_count": len(missing_ids),
            "provenance_loss_candidate_count": len(set(provenance_loss_ids)),
            "largest_concept_source_count": max(
                (len(concept.get("source_candidate_ids") or []) for concept in concepts),
                default=0,
            ),
            "merged_concept_count": sum(1 for concept in concepts if len(concept.get("source_candidate_ids") or []) > 1),
        },
        "findings": findings,
        "repair_plan": repair_plan,
    }


def _compact_subject_concept_audit_view(concept: dict[str, Any], *, entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source_candidate_ids = [
        candidate_id
        for candidate_id in concept.get("source_candidate_ids") or []
        if isinstance(candidate_id, str) and candidate_id in entries
    ]
    candidate_summaries = []
    for candidate_id in source_candidate_ids:
        entry = entries[candidate_id]
        candidate = entry.get("original_candidate") or {}
        candidate_summaries.append(
            {
                "id": candidate_id,
                "label": candidate.get("label"),
                "description": candidate.get("description"),
                "coverage_criteria": candidate.get("coverage_criteria") or [],
                "source_roles": candidate.get("source_roles") or [],
                "depth": _infer_candidate_depth(entry),
                "lesson": {
                    "lesson_id": entry.get("lesson_id"),
                    "title": entry.get("lesson_title"),
                },
            }
        )
    return {
        "concept_id": concept.get("concept_id"),
        "label": concept.get("label"),
        "description": concept.get("description"),
        "coverage_criteria": concept.get("coverage_criteria") or [],
        "source_candidate_ids": source_candidate_ids,
        "source_candidates": candidate_summaries,
        "depth": concept.get("depth"),
        "merge_rationale": concept.get("merge_rationale"),
    }


def _subject_merge_audit_attempts(*, run_dir: Path) -> list[dict[str, Any]]:
    attempts: list[dict[str, Any]] = []
    clusters_path = run_dir / "subject_merge_candidate_clusters.json"
    if not clusters_path.is_file():
        return attempts
    clusters = {
        str(cluster.get("id") or ""): cluster
        for cluster in (_read_json(clusters_path).get("clusters") or [])
        if isinstance(cluster, dict) and str(cluster.get("id") or "")
    }
    evaluations_root = run_dir / "subject_cluster_evaluations"
    if not evaluations_root.is_dir():
        return attempts
    for decision_path in sorted(evaluations_root.glob("*/subject_cluster_evaluation_decision.json")):
        decision = _read_json(decision_path)
        input_candidate_ids = [
            candidate_id for candidate_id in decision.get("input_candidate_ids") or [] if isinstance(candidate_id, str)
        ]
        if len(input_candidate_ids) < 2:
            continue
        cluster_id = decision_path.parent.name.replace("_cluster_", "__cluster_")
        cluster = clusters.get(cluster_id) or {}
        accepted = [
            {
                "label": item.get("label"),
                "source_candidate_ids": item.get("source_candidate_ids") or [],
                "merge_rationale": item.get("merge_rationale"),
            }
            for item in decision.get("accepted_concepts") or []
            if isinstance(item, dict)
        ]
        attempts.append(
            {
                "cluster_id": cluster_id,
                "cluster_label": cluster.get("label"),
                "input_candidate_ids": input_candidate_ids,
                "accepted_count": len(accepted),
                "accepted_concepts": accepted,
                "outcome": "merged" if len(accepted) == 1 else "kept_separate",
            }
        )
    return attempts


def _subject_merge_review_signals(
    *,
    concepts: list[dict[str, Any]],
    merge_attempts: list[dict[str, Any]],
) -> dict[str, Any]:
    rejected_same_cluster = [
        {
            "signal": "same_fine_cluster_kept_separate",
            "candidate_ids": attempt.get("input_candidate_ids") or [],
            "cluster_label": attempt.get("cluster_label"),
            "accepted_labels": [
                accepted.get("label")
                for accepted in attempt.get("accepted_concepts") or []
                if isinstance(accepted, dict)
            ],
        }
        for attempt in merge_attempts
        if attempt.get("outcome") == "kept_separate"
    ]
    return {
        "same_fine_cluster_kept_separate": rejected_same_cluster[:24],
        "high_text_overlap_concept_pairs": _high_text_overlap_concept_pairs(concepts)[:24],
    }


def _high_text_overlap_concept_pairs(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pairs = []
    for left_index, left in enumerate(concepts):
        left_tokens = _meaning_tokens(left)
        if not left_tokens:
            continue
        left_sources = left.get("source_candidate_ids") or []
        for right in concepts[left_index + 1 :]:
            right_tokens = _meaning_tokens(right)
            if not right_tokens:
                continue
            overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
            if overlap < 0.35:
                continue
            pairs.append(
                {
                    "candidate_ids": _stable_unique(list(left_sources) + list(right.get("source_candidate_ids") or [])),
                    "left_label": left.get("label"),
                    "right_label": right.get("label"),
                    "token_overlap": round(overlap, 3),
                }
            )
    return sorted(pairs, key=lambda item: item["token_overlap"], reverse=True)


def _subject_quality_audit_output_contract() -> dict[str, Any]:
    return {
        "scores": {field: "integer 0-3" for field in _SUBJECT_MERGE_AUDIT_SCORE_FIELDS},
        "reliability": "reliable or repair_required",
        "flags": sorted(_SUBJECT_MERGE_AUDIT_FLAGS - {"repair_unstable"}),
        "repair_plan": [
            {
                "repair_reason": sorted(_SUBJECT_MERGE_AUDIT_REPAIR_REASONS),
                "candidate_ids": ["lesson-local candidate IDs"],
                "explanation": "Concrete reason this repair is necessary.",
            }
        ],
        "missed_merge_candidates": [
            {
                "candidate_ids": ["lesson-local candidate IDs"],
                "confidence": "high, medium, or low",
                "explanation": "Why this is an obvious missed merge, if any.",
            }
        ],
    }


def _validate_subject_phase5b_audit(artifact: dict[str, Any], *, registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("artifact_type") != "subject_merge_quality_audit":
        errors.append("subject_merge_quality_audit.artifact_type must be 'subject_merge_quality_audit'")
    if artifact.get("schema_version") != "subject_merge_quality_audit.v0":
        errors.append("subject_merge_quality_audit.schema_version must be 'subject_merge_quality_audit.v0'")
    scores = artifact.get("scores")
    if not isinstance(scores, dict):
        errors.append("subject_merge_quality_audit.scores must be an object")
        scores = {}
    for field in _SUBJECT_MERGE_AUDIT_SCORE_FIELDS:
        value = scores.get(field)
        if not isinstance(value, int) or value < 0 or value > 3:
            errors.append(f"subject_merge_quality_audit.scores.{field} must be an integer from 0 to 3")
    reliability = artifact.get("reliability")
    if reliability not in {"reliable", "repair_required"}:
        errors.append("subject_merge_quality_audit.reliability must be reliable or repair_required")
    flags = artifact.get("flags")
    if not isinstance(flags, list) or not all(isinstance(flag, str) for flag in flags):
        errors.append("subject_merge_quality_audit.flags must be a list of strings")
        flags = []
    unknown_flags = sorted(set(flags) - _SUBJECT_MERGE_AUDIT_FLAGS)
    if unknown_flags:
        errors.append("subject_merge_quality_audit.flags contains unknown flags: " + ", ".join(unknown_flags))
    if reliability == "repair_required" and not flags:
        errors.append("subject_merge_quality_audit.repair_required audits must include at least one flag")

    registry_ids = set((registry.get("candidates") or {}).keys())
    repair_plan = artifact.get("repair_plan")
    if not isinstance(repair_plan, list):
        errors.append("subject_merge_quality_audit.repair_plan must be a list")
        repair_plan = []
    for index, item in enumerate(repair_plan):
        location = f"subject_merge_quality_audit.repair_plan[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{location} must be an object")
            continue
        reason = item.get("repair_reason")
        if reason not in _SUBJECT_MERGE_AUDIT_REPAIR_REASONS:
            errors.append(f"{location}.repair_reason is not allowed")
        candidate_ids = item.get("candidate_ids")
        if not isinstance(candidate_ids, list) or not all(isinstance(candidate_id, str) for candidate_id in candidate_ids):
            errors.append(f"{location}.candidate_ids must be a list of candidate IDs")
            continue
        if reason in {"over_merged_group", "residual_duplicate", "missed_obvious_merge"} and len(candidate_ids) < 2:
            errors.append(f"{location}.candidate_ids must contain at least two IDs for {reason}")
        unknown = sorted(set(candidate_ids) - registry_ids)
        if unknown:
            errors.append(f"{location}.candidate_ids references unknown candidates: " + ", ".join(unknown))
        if not str(item.get("explanation") or "").strip():
            errors.append(f"{location}.explanation is required")
    return errors


def _run_subject_phase5b_repair(
    *,
    run_dir: Path,
    artifact: dict[str, Any],
    registry: dict[str, Any],
    quality_audit: dict[str, Any],
    repair_reason: str,
    target_candidate_ids: list[str],
    prompt: str,
    prompt_path: str,
    runner: StageRunner,
    model_route: str,
    repair_model_route: str,
    contextual_repair_model_route: str,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> Path:
    target_digest = hashlib.sha1("\n".join(target_candidate_ids).encode("utf-8")).hexdigest()[:8]
    repair_dir = run_dir / "subject_merge_phase5b_repairs" / f"{_cluster_dir_name(repair_reason)}_{target_digest}"
    repair_dir.mkdir(parents=True, exist_ok=True)
    model_input = _build_subject_phase5b_repair_input(
        artifact=artifact,
        registry=registry,
        quality_audit=quality_audit,
        repair_reason=repair_reason,
        target_candidate_ids=target_candidate_ids,
        prompt=prompt,
        prompt_path=prompt_path,
        model_route=model_route,
    )
    (repair_dir / "subject_merge_quality_repair_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    contract = StageContract(
        name="subject_merge_quality_repair",
        required_inputs=["subject_merge_quality_repair_input.json"],
        output_artifact="subject_merge_quality_repair_decision.json",
        model_route=model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        validator=lambda decision, registry=registry: validate_subject_merge_decision(decision, registry),
        normalizer=_normalize_subject_phase5b_repair_output,
    )
    stage_result = _run_stage_with_provider_retry(
        runner=runner,
        contract=contract,
        run_dir=repair_dir,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        failure_message=f"Subject Merge Phase 5b repair failed without result for {repair_reason}",
    )
    return stage_result.artifact_path


def _build_subject_phase5b_repair_input(
    *,
    artifact: dict[str, Any],
    registry: dict[str, Any],
    quality_audit: dict[str, Any],
    repair_reason: str,
    target_candidate_ids: list[str],
    prompt: str,
    prompt_path: str,
    model_route: str,
) -> dict[str, Any]:
    entries = registry.get("candidates") or {}
    return {
        "artifact_type": "subject_merge_quality_repair_input",
        "schema_version": "subject_merge_quality_repair_input.v0",
        "source_artifact": artifact.get("source_artifact"),
        "candidate_registry_artifact": artifact.get("candidate_registry_artifact"),
        "subject_merge_artifact": "subject_merge.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "subject_merge_quality_repair",
        "model_route": model_route,
        "scope_id": registry.get("scope_id"),
        "quality_audit": quality_audit,
        "repair_reason": repair_reason,
        "target_candidate_ids": target_candidate_ids,
        "target_candidates": [
            _compact_subject_candidate_view(entries[candidate_id], summary_only=False)
            for candidate_id in target_candidate_ids
            if candidate_id in entries
        ],
        "current_subject_concepts": _compact_subject_concepts(artifact.get("concepts") or []),
        "output_contract": _subject_decision_output_contract(),
        "web_access_policy": _no_web_policy(),
    }


def _apply_subject_deterministic_repairs(
    *,
    artifact: dict[str, Any],
    registry: dict[str, Any],
    repair_plans: list[dict[str, Any]],
) -> dict[str, Any]:
    repaired = json.loads(json.dumps(artifact, ensure_ascii=False))
    entries = registry.get("candidates") or {}
    for concept in repaired.get("concepts") or []:
        if not isinstance(concept, dict):
            continue
        source_ids = [candidate_id for candidate_id in concept.get("source_candidate_ids") or [] if candidate_id in entries]
        concept["occurrences"] = _occurrences_for_source_candidate_ids(entries, source_ids)
        concept["lesson_reconciliation_refs"] = [
            _lesson_reconciliation_ref(entries[candidate_id]) for candidate_id in source_ids
        ]

    target_ids = [
        candidate_id
        for plan in repair_plans
        if plan.get("repair_reason") == "assignment_incomplete"
        for candidate_id in plan.get("candidate_ids") or []
        if isinstance(candidate_id, str) and candidate_id in entries
    ]
    assigned_ids = {
        str(assignment.get("candidate_id") or "")
        for assignment in repaired.get("candidate_assignments") or []
        if isinstance(assignment, dict)
    }
    for candidate_id in target_ids:
        if candidate_id in assigned_ids:
            continue
        accepted_id = f"phase5b_standalone_{_compact_id_fragment(candidate_id)}"
        accepted = _standalone_accepted_from_entry(entries[candidate_id], accepted_id=accepted_id)
        concept = _concept_from_accepted(
            accepted=accepted,
            entries=entries,
            assignment_status_by_candidate_id={candidate_id: "used_in"},
        )
        repaired.setdefault("concepts", []).append(concept)
        repaired.setdefault("candidate_assignments", []).append(
            {
                "candidate_id": candidate_id,
                "status": "used_in",
                "accepted_ids": [accepted_id],
                "accepted_concept_ids": [concept["concept_id"]],
                "explanation": "Deterministic Phase 5b standalone passthrough for an unassigned candidate.",
            }
        )
        assigned_ids.add(candidate_id)
    _refresh_subject_merge_summary(repaired, registry=registry)
    return repaired


def _apply_subject_phase5b_repair_decision(
    *,
    artifact: dict[str, Any],
    registry: dict[str, Any],
    decision: dict[str, Any],
    target_candidate_ids: list[str],
) -> dict[str, Any]:
    repaired = json.loads(json.dumps(artifact, ensure_ascii=False))
    entries = registry.get("candidates") or {}
    target_set = set(target_candidate_ids)
    repaired["candidate_assignments"] = [
        assignment
        for assignment in repaired.get("candidate_assignments") or []
        if not isinstance(assignment, dict) or assignment.get("candidate_id") not in target_set
    ]
    kept_concepts = []
    for concept in repaired.get("concepts") or []:
        if not isinstance(concept, dict):
            kept_concepts.append(concept)
            continue
        source_ids = [
            candidate_id
            for candidate_id in concept.get("source_candidate_ids") or []
            if isinstance(candidate_id, str) and candidate_id not in target_set
        ]
        if not source_ids:
            continue
        concept["source_candidate_ids"] = source_ids
        concept["occurrences"] = _occurrences_for_source_candidate_ids(entries, source_ids)
        concept["lesson_reconciliation_refs"] = [
            _lesson_reconciliation_ref(entries[candidate_id]) for candidate_id in source_ids if candidate_id in entries
        ]
        kept_concepts.append(concept)
    repaired["concepts"] = kept_concepts

    concept_id_by_repair_id: dict[str, str] = {}
    assignment_status_by_candidate_id = {
        str(assignment.get("candidate_id") or ""): str(assignment.get("status") or "")
        for assignment in decision.get("candidate_assignments") or []
        if isinstance(assignment, dict)
    }
    for accepted in decision.get("accepted_concepts") or []:
        if not isinstance(accepted, dict):
            continue
        local_id = str(accepted.get("id") or "")
        concept = _concept_from_accepted(
            accepted=accepted,
            entries=entries,
            assignment_status_by_candidate_id=assignment_status_by_candidate_id,
        )
        concept_id_by_repair_id[local_id] = concept["concept_id"]
        repaired.setdefault("concepts", []).append(concept)

    for assignment in decision.get("candidate_assignments") or []:
        if not isinstance(assignment, dict):
            continue
        candidate_id = str(assignment.get("candidate_id") or "")
        if candidate_id not in target_set:
            continue
        item = dict(assignment)
        if item.get("status") == "used_in":
            item["accepted_concept_ids"] = [
                concept_id_by_repair_id[accepted_id]
                for accepted_id in item.get("accepted_ids") or []
                if accepted_id in concept_id_by_repair_id
            ]
        elif item.get("status") == "merged_into":
            item["merged_into_concept_id"] = concept_id_by_repair_id.get(str(item.get("merged_into") or ""))
        repaired.setdefault("candidate_assignments", []).append(item)

    _refresh_subject_merge_summary(repaired, registry=registry)
    return repaired


def _concept_from_accepted(
    *,
    accepted: dict[str, Any],
    entries: dict[str, dict[str, Any]],
    assignment_status_by_candidate_id: dict[str, str],
) -> dict[str, Any]:
    source_candidate_ids = [
        str(item)
        for item in accepted.get("source_candidate_ids") or []
        if str(item) in entries
    ]
    concept = {
        "concept_id": _concept_id(accepted),
        "label": accepted.get("label"),
        "description": accepted.get("description"),
        "coverage_criteria": accepted.get("coverage_criteria") or [],
        "source_candidate_ids": source_candidate_ids,
        "merge_rationale": accepted.get("merge_rationale"),
        "candidate_assignment_status": assignment_status_by_candidate_id.get(source_candidate_ids[0], "used_in")
        if source_candidate_ids
        else "used_in",
        "lesson_reconciliation_refs": [
            _lesson_reconciliation_ref(entries[source_candidate_id])
            for source_candidate_id in source_candidate_ids
        ],
        "occurrences": _occurrences_for_source_candidate_ids(entries, source_candidate_ids),
        "depth": _merged_depth([_infer_candidate_depth(entries[source_candidate_id]) for source_candidate_id in source_candidate_ids]),
    }
    return concept


def _lesson_reconciliation_ref(entry: dict[str, Any]) -> dict[str, Any]:
    candidate = entry.get("original_candidate") or {}
    return {
        "artifact_path": entry.get("artifact_path"),
        "lesson_id": entry.get("lesson_id"),
        "reconciled_candidate_id": entry.get("original_candidate_id"),
        "label": entry.get("label"),
        "source_candidate_ids": candidate.get("source_candidate_ids") or [],
        "evidence": candidate.get("evidence") or [],
    }


def _occurrences_for_source_candidate_ids(
    entries: dict[str, dict[str, Any]],
    source_candidate_ids: list[str],
) -> list[dict[str, Any]]:
    occurrences = []
    for candidate_id in source_candidate_ids:
        entry = entries.get(candidate_id)
        if not entry:
            continue
        candidate = entry.get("original_candidate") or {}
        source_metadata = entry.get("source_metadata") or {}
        occurrences.append(
            {
                "lesson": {
                    "lesson_id": entry.get("lesson_id"),
                    "title": source_metadata.get("lesson_title"),
                },
                "source_candidate_ids": candidate.get("source_candidate_ids") or [],
                "source_roles": candidate.get("source_roles") or entry.get("source_roles") or [],
                "evidence_types": candidate.get("evidence_types") or _as_list(entry.get("evidence_type")),
                "depth": _infer_candidate_depth(entry),
            }
        )
    return occurrences


def _candidate_ref(entry: dict[str, Any]) -> dict[str, Any]:
    return dict(entry.get("candidate_ref") or {})


def _anchors_from_evidence(evidence: list[Any]) -> list[Any]:
    anchors: list[Any] = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        for anchor in item.get("anchors") or []:
            anchors.append(anchor)
    return anchors


def _compact_subject_candidate_view(entry: dict[str, Any], *, summary_only: bool) -> dict[str, Any]:
    description = str(entry.get("description") or "")
    if summary_only:
        description = _one_line(description)
    source_metadata = entry.get("source_metadata") or {}
    return {
        "id": entry.get("compact_id"),
        "label": entry.get("label"),
        "description": description,
        "coverage_criteria": [] if summary_only else entry.get("coverage_criteria") or [],
        "source_roles": [] if summary_only else entry.get("source_roles") or [],
        "evidence_type": entry.get("evidence_type"),
        "lesson_id": entry.get("lesson_id"),
        "lesson_title": source_metadata.get("lesson_title"),
        "depth": _infer_candidate_depth(entry),
    }


def _compact_subject_concepts(concepts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "concept_id": concept.get("concept_id"),
            "label": concept.get("label"),
            "description": concept.get("description"),
            "coverage_criteria": concept.get("coverage_criteria") or [],
            "source_candidate_ids": concept.get("source_candidate_ids") or [],
            "depth": concept.get("depth"),
        }
        for concept in concepts
        if isinstance(concept, dict)
    ]


def _standalone_accepted_from_entry(entry: dict[str, Any], *, accepted_id: str) -> dict[str, Any]:
    return {
        "id": accepted_id,
        "label": entry.get("label") or "Standalone subject concept",
        "description": entry.get("description") or "Standalone subject concept.",
        "coverage_criteria": entry.get("coverage_criteria") or ["Student can explain this subject concept."],
        "source_candidate_ids": [entry.get("compact_id")],
        "merge_rationale": "Doubt or singleton cluster defaults to a standalone subject concept.",
    }


def _standalone_accepted_from_candidate_view(candidate: dict[str, Any], *, accepted_id: str) -> dict[str, Any]:
    candidate_id = str(candidate.get("id") or "")
    return {
        "id": accepted_id,
        "label": candidate.get("label") or "Standalone subject concept",
        "description": candidate.get("description") or "Standalone subject concept.",
        "coverage_criteria": candidate.get("coverage_criteria") or ["Student can explain this subject concept."],
        "source_candidate_ids": [candidate_id],
        "merge_rationale": "Doubt or omitted evaluation defaults to a standalone subject concept.",
    }


def _subject_decision_output_contract() -> dict[str, Any]:
    return {
        "candidate_assignment_rule": (
            "Return accepted subject concepts plus exactly one assignment for every input candidate. "
            "Allowed statuses are only used_in and merged_into. Never use review or pruned. "
            "When uncertain, create a standalone accepted concept."
        ),
        "accepted_concepts": [
            {
                "id": "stage-local-id",
                "label": "Specific teachable idea",
                "description": "What the student needs to understand.",
                "coverage_criteria": ["Observable check in one to three focused questions."],
                "source_candidate_ids": ["compact-candidate-id"],
                "merge_rationale": "Why these candidates belong together or stand alone.",
            }
        ],
        "candidate_assignments": [
            {
                "candidate_id": "compact-candidate-id",
                "status": "used_in",
                "accepted_ids": ["stage-local-id"],
            },
            {
                "candidate_id": "represented-compact-candidate-id",
                "status": "merged_into",
                "merged_into": "stage-local-id",
                "explanation": "Why it is represented by that accepted concept.",
            },
        ],
    }


def _validate_subject_cluster_shape(
    artifact: dict[str, Any],
    *,
    registry: dict[str, Any],
    artifact_type: str,
    schema_version: str,
) -> list[str]:
    errors: list[str] = []
    if artifact.get("artifact_type") != artifact_type:
        errors.append(f"{artifact_type}.artifact_type must be '{artifact_type}'")
    if artifact.get("schema_version") != schema_version:
        errors.append(f"{artifact_type}.schema_version must be '{schema_version}'")
    registry_ids = set((registry.get("candidates") or {}).keys())
    input_ids = artifact.get("input_candidate_ids")
    if not isinstance(input_ids, list) or not all(isinstance(item, str) and item for item in input_ids):
        errors.append(f"{artifact_type}.input_candidate_ids must contain candidate IDs")
        input_ids = []
    input_id_set = set(input_ids)
    unknown_input_ids = sorted(input_id_set - registry_ids)
    if unknown_input_ids:
        errors.append(f"{artifact_type}.input_candidate_ids references unknown candidates: " + ", ".join(unknown_input_ids))
    clusters = artifact.get("clusters")
    if not isinstance(clusters, list) or not clusters:
        errors.append(f"{artifact_type}.clusters must be a non-empty list")
        clusters = []
    cluster_ids: set[str] = set()
    assigned_candidate_ids: list[str] = []
    for index, cluster in enumerate(clusters):
        location = f"{artifact_type}.clusters[{index}]"
        if not isinstance(cluster, dict):
            errors.append(f"{location} must be an object")
            continue
        cluster_id = str(cluster.get("id") or "")
        if not cluster_id:
            errors.append(f"{location}.id is required")
        elif cluster_id in cluster_ids:
            errors.append(f"{location}.id is duplicated")
        if cluster_id:
            cluster_ids.add(cluster_id)
        for field in ("label", "rationale"):
            if not str(cluster.get(field) or "").strip():
                errors.append(f"{location}.{field} is required")
        candidate_ids = cluster.get("candidate_ids")
        if not isinstance(candidate_ids, list) or not all(isinstance(item, str) and item for item in candidate_ids):
            errors.append(f"{location}.candidate_ids must contain candidate IDs")
            continue
        duplicated_in_cluster = _duplicates(candidate_ids)
        if duplicated_in_cluster:
            errors.append(f"{location}.candidate_ids contains duplicates: " + ", ".join(duplicated_in_cluster))
        for candidate_id in candidate_ids:
            if candidate_id not in input_id_set:
                errors.append(f"{location}.candidate_ids references unknown candidate {candidate_id}")
            assigned_candidate_ids.append(candidate_id)
    duplicated_assignments = _duplicates(assigned_candidate_ids)
    if duplicated_assignments:
        errors.append(f"{artifact_type}.clusters assign candidates more than once: " + ", ".join(duplicated_assignments))
    missing = sorted(input_id_set - set(assigned_candidate_ids))
    if missing:
        errors.append(f"{artifact_type} every input candidate must appear in exactly one cluster: " + ", ".join(missing))
    return errors


def _canonicalize_cluster_candidate_coverage(
    *,
    clusters: list[Any],
    input_candidate_ids: list[str],
) -> tuple[list[Any], list[str]]:
    input_id_set = set(input_candidate_ids)
    seen_candidate_ids: set[str] = set()
    canonical_clusters: list[Any] = []
    warnings: list[str] = []
    existing_cluster_ids = {
        str(cluster.get("id") or "")
        for cluster in clusters
        if isinstance(cluster, dict) and str(cluster.get("id") or "")
    }
    for cluster in clusters:
        if not isinstance(cluster, dict):
            canonical_clusters.append(cluster)
            continue
        candidate_ids = cluster.get("candidate_ids")
        if not isinstance(candidate_ids, list):
            canonical_clusters.append(cluster)
            continue
        canonical_candidate_ids: list[str] = []
        for candidate_id in candidate_ids:
            if not isinstance(candidate_id, str) or not candidate_id:
                continue
            if candidate_id not in input_id_set:
                warnings.append(f"dropped unknown candidate {candidate_id} from cluster {cluster.get('id')}")
                continue
            if candidate_id in seen_candidate_ids:
                warnings.append(f"dropped duplicate candidate {candidate_id} from cluster {cluster.get('id')}")
                continue
            canonical_candidate_ids.append(candidate_id)
            seen_candidate_ids.add(candidate_id)
        if not canonical_candidate_ids:
            warnings.append(f"dropped empty cluster {cluster.get('id')}")
            continue
        canonical_cluster = dict(cluster)
        canonical_cluster["candidate_ids"] = canonical_candidate_ids
        canonical_clusters.append(canonical_cluster)

    for candidate_id in input_candidate_ids:
        if candidate_id in seen_candidate_ids:
            continue
        cluster_id = _next_generated_cluster_id(existing_cluster_ids)
        existing_cluster_ids.add(cluster_id)
        canonical_clusters.append(
            {
                "id": cluster_id,
                "label": f"Unclustered candidate {candidate_id}",
                "rationale": "Deterministically added because the clustering output omitted this input candidate.",
                "candidate_ids": [candidate_id],
            }
        )
        seen_candidate_ids.add(candidate_id)
        warnings.append(f"added singleton cluster for omitted candidate {candidate_id}")
    return canonical_clusters, warnings


def _existing_valid_subject_clusters_artifact(
    *,
    artifact_path: Path,
    registry: dict[str, Any],
    artifact_type: str,
    schema_version: str,
    model_route: str | None,
) -> dict[str, Any] | None:
    if not artifact_path.is_file():
        return None
    try:
        artifact = _read_json(artifact_path)
    except json.JSONDecodeError:
        return None
    if model_route is not None and artifact.get("model_route") != model_route:
        return None
    errors = _validate_subject_cluster_shape(
        artifact,
        registry=registry,
        artifact_type=artifact_type,
        schema_version=schema_version,
    )
    return None if errors else artifact


@dataclass(frozen=True)
class _SubjectFineClusteringTask:
    order: int
    area_id: str
    area_dir: Path
    registry: dict[str, Any]
    contract: StageContract


@dataclass(frozen=True)
class _SubjectFineClusteringResult:
    order: int
    area_id: str
    decision_path: Path
    decision: dict[str, Any]
    reused: bool


@dataclass(frozen=True)
class _SubjectClusterEvaluationTask:
    order: int
    cluster_id: str
    cluster_ids: list[str]
    cluster_dir: Path
    registry: dict[str, Any]
    contract: StageContract


@dataclass(frozen=True)
class _SubjectClusterEvaluationResult:
    order: int
    cluster_id: str
    cluster_ids: list[str]
    decision_path: Path
    decision: dict[str, Any]
    reused: bool


def _run_subject_fine_clustering_tasks(
    tasks: list[_SubjectFineClusteringTask],
    *,
    runner: StageRunner,
    concurrency: int,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> list[_SubjectFineClusteringResult]:
    if not tasks:
        return []
    results: list[_SubjectFineClusteringResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        future_to_task = {
            executor.submit(
                _run_subject_fine_clustering_task,
                task,
                runner=runner,
                provider_retry_limit=provider_retry_limit,
                provider_retry_backoff_seconds=provider_retry_backoff_seconds,
            ): task
            for task in tasks
        }
        for future in concurrent.futures.as_completed(future_to_task):
            results.append(future.result())
    return sorted(results, key=lambda item: item.order)


def _run_subject_fine_clustering_task(
    task: _SubjectFineClusteringTask,
    *,
    runner: StageRunner,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> _SubjectFineClusteringResult:
    existing_path = task.area_dir / "subject_merge_fine_clustering_decision.json"
    if existing_path.is_file():
        try:
            existing = _read_json(existing_path)
            if not validate_subject_clustering_decision(
                existing,
                registry=task.registry,
                artifact_type="subject_merge_fine_clustering_decision",
                schema_version="subject_merge_fine_clustering_decision.v0",
            ):
                return _SubjectFineClusteringResult(task.order, task.area_id, existing_path, existing, True)
        except json.JSONDecodeError:
            pass
    stage_result = _run_stage_with_provider_retry(
        runner=runner,
        contract=task.contract,
        run_dir=task.area_dir,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        failure_message=f"Subject Merge fine clustering failed without result for {task.area_id}",
    )
    return _SubjectFineClusteringResult(
        task.order,
        task.area_id,
        stage_result.artifact_path,
        _read_json(stage_result.artifact_path),
        False,
    )


def _run_subject_cluster_evaluation_tasks(
    tasks: list[_SubjectClusterEvaluationTask],
    *,
    runner: StageRunner,
    concurrency: int,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> list[_SubjectClusterEvaluationResult]:
    if not tasks:
        return []
    results: list[_SubjectClusterEvaluationResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, concurrency)) as executor:
        future_to_task = {
            executor.submit(
                _run_subject_cluster_evaluation_task,
                task,
                runner=runner,
                provider_retry_limit=provider_retry_limit,
                provider_retry_backoff_seconds=provider_retry_backoff_seconds,
            ): task
            for task in tasks
        }
        for future in concurrent.futures.as_completed(future_to_task):
            results.append(future.result())
    return sorted(results, key=lambda item: item.order)


def _run_subject_cluster_evaluation_task(
    task: _SubjectClusterEvaluationTask,
    *,
    runner: StageRunner,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> _SubjectClusterEvaluationResult:
    existing_path = task.cluster_dir / "subject_cluster_evaluation_decision.json"
    if existing_path.is_file():
        try:
            existing = _read_json(existing_path)
            if not validate_subject_merge_decision(existing, task.registry):
                return _SubjectClusterEvaluationResult(
                    task.order,
                    task.cluster_id,
                    task.cluster_ids,
                    existing_path,
                    existing,
                    True,
                )
        except json.JSONDecodeError:
            pass
    stage_result = _run_stage_with_provider_retry(
        runner=runner,
        contract=task.contract,
        run_dir=task.cluster_dir,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        failure_message=f"Subject Merge cluster evaluation failed without result for {task.cluster_id}",
    )
    return _SubjectClusterEvaluationResult(
        task.order,
        task.cluster_id,
        task.cluster_ids,
        stage_result.artifact_path,
        _read_json(stage_result.artifact_path),
        False,
    )


def _run_stage_with_provider_retry(
    *,
    runner: StageRunner,
    contract: StageContract,
    run_dir: Path,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
    failure_message: str,
) -> StageResult:
    result: StageResult | None = None
    for attempt in range(provider_retry_limit + 1):
        try:
            result = runner.run(contract, run_dir=run_dir)
            break
        except StageBlockedError as exc:
            if not _is_transient_provider_error(exc) or attempt >= provider_retry_limit:
                raise
            if provider_retry_backoff_seconds:
                time.sleep(provider_retry_backoff_seconds * (attempt + 1))
    if result is None:
        raise StageBlockedError(failure_message)
    return result


def _is_transient_provider_error(exc: StageBlockedError) -> bool:
    message = str(exc)
    transient_markers = (
        "DeepSeek HTTP 429",
        "DeepSeek HTTP 503",
        "DeepSeek request timed out",
        "DeepSeek request failed",
        "DeepSeek returned an empty message",
        "RemoteDisconnected",
        "IncompleteRead",
    )
    return any(marker in message for marker in transient_markers)


def _refresh_subject_merge_summary(artifact: dict[str, Any], *, registry: dict[str, Any]) -> None:
    artifact["pruned_candidates"] = artifact.get("pruned_candidates") or []
    artifact["review_candidates"] = artifact.get("review_candidates") or []
    artifact["summary"] = {
        "input_candidate_count": len(registry.get("candidates") or {}),
        "concept_count": len(artifact.get("concepts") or []),
        "pruned_candidate_count": len(artifact.get("pruned_candidates") or []),
        "review_candidate_count": len(artifact.get("review_candidates") or []),
    }


def _find_residual_duplicate_pairs(
    concepts: list[dict[str, Any]],
    entries: dict[str, dict[str, Any]],
) -> list[list[str]]:
    pairs: list[list[str]] = []
    already_targeted: set[str] = set()
    concepts_by_key: dict[str, list[tuple[dict[str, Any], list[str]]]] = {}
    for concept in concepts:
        sources = [candidate_id for candidate_id in concept.get("source_candidate_ids") or [] if candidate_id in entries]
        if not sources:
            continue
        bands = {_depth_band(_infer_candidate_depth(entries[candidate_id])) for candidate_id in sources}
        if bands - {"definition"}:
            continue
        key = _canonical_identity_key(concept)
        if key:
            concepts_by_key.setdefault(key, []).append((concept, sources))

    for grouped in concepts_by_key.values():
        if len(grouped) <= 1:
            continue
        group_sources = _stable_unique(
            [
                candidate_id
                for _concept, sources in grouped
                for candidate_id in sources
            ]
        )
        if len(group_sources) > 1:
            pairs.append(group_sources)
            already_targeted.update(group_sources)

    for index, left in enumerate(concepts):
        left_sources = [candidate_id for candidate_id in left.get("source_candidate_ids") or [] if candidate_id in entries]
        if not left_sources or any(candidate_id in already_targeted for candidate_id in left_sources):
            continue
        left_bands = {_depth_band(_infer_candidate_depth(entries[candidate_id])) for candidate_id in left_sources}
        if left_bands - {"definition"}:
            continue
        left_tokens = _meaning_tokens(left)
        if not left_tokens:
            continue
        left_key = _canonical_identity_key(left)
        for right in concepts[index + 1 :]:
            right_sources = [candidate_id for candidate_id in right.get("source_candidate_ids") or [] if candidate_id in entries]
            if not right_sources or any(candidate_id in already_targeted for candidate_id in right_sources):
                continue
            right_bands = {_depth_band(_infer_candidate_depth(entries[candidate_id])) for candidate_id in right_sources}
            if right_bands - {"definition"}:
                continue
            right_tokens = _meaning_tokens(right)
            if not right_tokens:
                continue
            right_key = _canonical_identity_key(right)
            overlap = len(left_tokens & right_tokens) / max(len(left_tokens | right_tokens), 1)
            if (left_key and left_key == right_key) or overlap >= 0.5:
                pair = _stable_unique(left_sources + right_sources)
                pairs.append(pair)
                already_targeted.update(pair)
                break
    return pairs


def _canonical_identity_key(concept: dict[str, Any]) -> str | None:
    text = _normalize_concept_text(
        " ".join(
            str(concept.get(field) or "")
            for field in ("label", "description")
        )
    )
    if _contains_any(text, ("challenge", "challenges", "desafio", "desafios", "ferramenta", "tools")):
        return None
    if re.search(r"\bnlp\b", text) or "natural language processing" in text or "processamento de linguagem natural" in text:
        if _contains_any(text, ("application", "applications", "machine learning", "autocorrect", "plagiarism", "segmentacao", "contexto")):
            return None
        if not _contains_any(
            text,
            (
                "definition",
                "define",
                "introduction",
                "intro",
                "field",
                "branch",
                "suitability",
                "criteria",
                "appropriate",
                "processamento de linguagem natural",
            ),
        ):
            return None
        return "nlp_definition"
    if "word2vec" in text and "cbow" in text and "skip gram" in text:
        return "word2vec_cbow_skipgram"
    if "tf idf" in text or "tfidf" in text:
        if _contains_any(
            text,
            (
                "limitation",
                "limitations",
                "limita",
                "implement",
                "implementation",
                "scikit",
                "sklearn",
                "gensim",
                "output",
                "application",
                "applications",
                "comparison",
                "discriminative",
                "less effective",
            ),
        ):
            return None
        return "tfidf_definition"
    if "bag of words" in text or "bag words" in text or re.search(r"\bbow\b", text):
        if _contains_any(
            text,
            (
                "countvectorizer",
                "scikit",
                "sklearn",
                "binary",
                "n gram",
                "ngram",
                "application",
                "applications",
                "strengths",
            ),
        ):
            return None
        return "bow_definition"
    if "sentiment analysis" in text or "analise de sentimento" in text or "analise de sentimentos" in text:
        if _contains_any(text, ("practical", "applications", "advantages", "usage", "dataset", "naive bayes")):
            return None
        return "sentiment_analysis_definition"
    return None


def _meaning_tokens(concept: dict[str, Any]) -> set[str]:
    text = _normalize_concept_text(
        " ".join(
            str(concept.get(field) or "")
            for field in ("label", "description")
        )
    )
    stopwords = {
        "a",
        "an",
        "and",
        "as",
        "by",
        "can",
        "concept",
        "definition",
        "de",
        "do",
        "does",
        "for",
        "in",
        "is",
        "of",
        "or",
        "student",
        "the",
        "to",
        "with",
    }
    return {token for token in text.split() if len(token) > 1 and token not in stopwords}


def _infer_candidate_depth(entry: dict[str, Any]) -> str:
    candidate = entry.get("original_candidate") or {}
    text = _normalize_concept_text(
        " ".join(
            str(value or "")
            for value in (
                entry.get("label"),
                entry.get("description"),
                " ".join(entry.get("coverage_criteria") or []),
                " ".join(entry.get("source_roles") or []),
                candidate.get("merge_rationale"),
            )
        )
    )
    if _contains_any(text, ("limitation", "limitations", "limita", "critique", "drawback", "tradeoff", "less effective")):
        return "limitation"
    if _contains_any(
        text,
        (
            "countvectorizer",
            "scikit",
            "sklearn",
            "nltk",
            "keras",
            "tensorflow",
            "javascript",
            "regex",
            "implement",
            "implementation",
            "building",
            "constructing",
            "stacking",
            "sequential",
            "dense",
            "dropout",
            "softmax",
            "sigmoid",
            "using",
            "method",
            "code",
            "library",
        ),
    ):
        return "implementation"
    if _contains_any(text, ("matrix", "gradient", "derivative", "equation", "formula", "log n df")):
        return "math"
    if _contains_any(text, ("apply", "application", "pipeline", "dataset")):
        return "application"
    return "definition"


def _depth_band(depth: str) -> str:
    return depth if depth in {"implementation", "limitation", "math", "application"} else "definition"


def _merged_depth(depths: list[str]) -> str:
    bands = [_depth_band(depth) for depth in depths if depth]
    if not bands:
        return "definition"
    unique = _stable_unique(bands)
    return unique[0] if len(unique) == 1 else "mixed"


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(marker)}\b", text) for marker in markers)


def _occurrence_keys(occurrences: list[dict[str, Any]]) -> list[tuple[Any, tuple[Any, ...], tuple[Any, ...], str]]:
    keys = []
    for occurrence in occurrences:
        if not isinstance(occurrence, dict):
            continue
        lesson = occurrence.get("lesson") or {}
        keys.append(
            (
                lesson.get("lesson_id"),
                tuple(occurrence.get("source_candidate_ids") or []),
                tuple(occurrence.get("evidence_types") or []),
                str(occurrence.get("depth") or ""),
            )
        )
    return keys


def _clean_phase_five_artifacts(*, run_dir: Path) -> None:
    for relative_path in (
        "subject_merge_candidate_registry.json",
        "subject_merge_area_partition_input.json",
        "subject_merge_area_partition_decision.json",
        "subject_merge_area_clusters.json",
        "subject_merge_candidate_clusters.json",
        "subject_merge_decision.json",
        "subject_merge.json",
        "subject_merge_quality_audit.json",
    ):
        path = run_dir / relative_path
        if path.exists():
            path.unlink()
    for dirname in (
        "subject_merge_fine_clustering",
        "subject_cluster_evaluations",
        "subject_merge_phase5b_repairs",
    ):
        path = run_dir / dirname
        if path.is_dir():
            shutil.rmtree(path)
    raw_output_dir = run_dir / "raw_model_outputs"
    for stage_name in (
        "subject_merge_area_partition",
        "subject_merge_fine_clustering",
        "subject_cluster_evaluation",
        "subject_merge_quality_audit",
        "subject_merge_quality_repair",
    ):
        path = raw_output_dir / stage_name
        if path.is_dir():
            shutil.rmtree(path)


def _clean_phase_five_b_artifacts(*, run_dir: Path) -> None:
    for relative_path in (
        "subject_merge_quality_audit_input.json",
        "subject_merge_quality_audit.json",
    ):
        path = run_dir / relative_path
        if path.exists():
            path.unlink()
    repairs_dir = run_dir / "subject_merge_phase5b_repairs"
    if repairs_dir.is_dir():
        shutil.rmtree(repairs_dir)
    raw_output_dir = run_dir / "raw_model_outputs"
    for stage_name in ("subject_merge_quality_audit", "subject_merge_quality_repair"):
        path = raw_output_dir / stage_name
        if path.is_dir():
            shutil.rmtree(path)


def _ensure_known_candidate_ids(input_candidate_ids: list[str], registry_candidates: dict[str, Any]) -> None:
    unknown_candidate_ids = [
        candidate_id
        for candidate_id in input_candidate_ids
        if candidate_id not in registry_candidates
    ]
    if unknown_candidate_ids:
        raise ValueError("unknown subject merge candidate IDs: " + ", ".join(unknown_candidate_ids))


def _cluster_batches(clusters: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    size = max(1, batch_size)
    return [clusters[index : index + size] for index in range(0, len(clusters), size)]


def _next_generated_cluster_id(existing_cluster_ids: set[str]) -> str:
    index = 1
    while True:
        cluster_id = f"cluster_{index:03d}"
        if cluster_id not in existing_cluster_ids:
            return cluster_id
        index += 1


def _cluster_dir_name(value: str) -> str:
    return _slug(value).replace("-", "_") or "cluster"


def _compact_id_fragment(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_]+", "_", value).strip("_") or "candidate"


def _concept_id(accepted: dict[str, Any]) -> str:
    label = str(accepted.get("label") or "concept")
    description = str(accepted.get("description") or "")
    coverage = json.dumps(accepted.get("coverage_criteria") or [], ensure_ascii=False, sort_keys=True)
    source_ids = json.dumps(accepted.get("source_candidate_ids") or [], ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha1(f"{label}\n{description}\n{coverage}\n{source_ids}".encode("utf-8")).hexdigest()[:8]
    return f"concept-{_slug(label)}-{digest}"


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return slug or "concept"


def _normalize_concept_text(value: Any) -> str:
    ascii_value = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", " ", ascii_value.lower()).strip()
    return re.sub(r"\s+", " ", text)


def _one_line(value: str) -> str:
    line = re.split(r"(?<=[.!?])\s+", value.strip(), maxsplit=1)[0]
    return line[:280]


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicated: list[str] = []
    for value in values:
        if value in seen and value not in duplicated:
            duplicated.append(value)
        seen.add(value)
    return duplicated


def _no_web_policy() -> dict[str, Any]:
    return {
        "web_search_allowed": False,
        "instruction": "Do not use web search or open URLs. Use only the provided candidate cards.",
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
