from __future__ import annotations

import concurrent.futures
import json
import re
import shutil
import time
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
from concept_graph_creation.stages.metadata_only_extraction import validate_metadata_only_extraction
from concept_graph_creation.stages.self_study_extraction import validate_self_study_extraction


def run_lesson_reconciliation_phase(
    *,
    run_dir: Path,
    model_call: ModelCall,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
    model_route: str = PRO_ROUTE_ALIAS,
    evaluation_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    repair_model_route: str = FLASH_ROUTE_ALIAS,
    contextual_repair_model_route: str = PRO_ROUTE_ALIAS,
    concurrency: int = 6,
    clustering_concurrency: int | None = None,
    evaluation_concurrency: int | None = None,
    evaluation_batch_size: int = 12,
    clean_phase_artifacts: bool = False,
    provider_retry_limit: int = 2,
    provider_retry_backoff_seconds: float = 10.0,
    phase4b_enabled: bool = True,
    phase4b_model_route: str = PRO_THINKING_ROUTE_ALIAS,
) -> dict[str, Any]:
    prompt_path = prompt_path or Path(__file__).resolve().parents[3] / "prompts" / "lesson_reconciliation.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    source_ledger = _read_json(run_dir / "source_ledger.json")
    self_studies_by_lesson = _self_studies_by_lesson(source_ledger.get("self_studies") or [])
    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)
    tasks: list[_LessonReconciliationTask] = []
    artifact_paths: list[Path] = []
    reused_count = 0
    reused_clustering_count = 0
    reused_evaluation_count = 0
    skipped: list[dict[str, str]] = []
    clustering_worker_count = max(1, clustering_concurrency if clustering_concurrency is not None else concurrency)
    evaluation_worker_count = max(1, evaluation_concurrency if evaluation_concurrency is not None else concurrency)

    if clean_phase_artifacts:
        _clean_phase_four_artifacts(run_dir=run_dir, source_ledger=source_ledger)

    for order, lesson in enumerate(source_ledger.get("lessons") or []):
        lesson_id = str(lesson.get("lesson_id") or "")
        lesson_dir = run_dir / "lessons" / lesson_id
        lesson_dir.mkdir(parents=True, exist_ok=True)
        candidate_sources = _lesson_candidate_sources(
            run_dir=run_dir,
            lesson_id=lesson_id,
            self_studies=self_studies_by_lesson.get(lesson_id, []),
        )
        if not candidate_sources:
            skipped.append({"lesson_id": lesson_id, "reason": "no_candidate_artifacts"})
            continue

        existing_artifact_path = lesson_dir / "lesson_reconciliation.json"
        if _existing_valid_artifact(
            artifact_path=existing_artifact_path,
            lesson_id=lesson_id,
            model_route=evaluation_model_route,
        ):
            artifact_paths.append(existing_artifact_path)
            reused_count += 1
            continue

        registry = build_candidate_registry(
            scope_id=lesson_id,
            source_artifact="source_ledger.json",
            candidate_sources=candidate_sources,
        )
        registry_path = lesson_dir / "semantic_reduce_candidate_registry.json"
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        input_candidate_ids = list(registry["candidates"])
        model_input = _build_lesson_candidate_clustering_input(
            lesson=_compact_lesson(lesson),
            registry=registry,
            input_candidate_ids=input_candidate_ids,
            prompt=prompt,
            prompt_path=str(prompt_path),
            model_route=model_route,
        )
        (lesson_dir / "lesson_candidate_clustering_input.json").write_text(
            json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        contract = StageContract(
            name="lesson_candidate_clustering",
            required_inputs=["lesson_candidate_clustering_input.json"],
            output_artifact="lesson_candidate_clustering_decision.json",
            model_route=model_route,
            repair_model_route=repair_model_route,
            contextual_repair_model_route=contextual_repair_model_route,
            validator=lambda artifact, registry=registry: validate_lesson_candidate_clustering_decision(
                artifact,
                registry,
            ),
            normalizer=_normalize_lesson_candidate_clustering_output,
        )
        tasks.append(
            _LessonReconciliationTask(
                order=order,
                lesson_id=lesson_id,
                lesson_dir=lesson_dir,
                registry=registry,
                registry_artifact_path=str(registry_path.relative_to(run_dir)),
                clustering_contract=contract,
                evaluation_model_route=evaluation_model_route,
                repair_model_route=repair_model_route,
                contextual_repair_model_route=contextual_repair_model_route,
            )
        )

    clustering_result_by_order = _run_clustering_tasks_with_queue(
        tasks,
        runner=runner,
        run_dir=run_dir,
        concurrency=clustering_worker_count,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    reused_clustering_count += sum(1 for result in clustering_result_by_order.values() if result.reused)

    evaluation_tasks: list[_ClusterEvaluationTask] = []
    for task in tasks:
        clustering_result = clustering_result_by_order.get(task.order)
        if clustering_result is None:
            continue
        evaluation_tasks.extend(
            _prepare_cluster_evaluation_tasks(
                task=task,
                clusters_artifact=clustering_result.clusters_artifact,
                prompt=prompt,
                prompt_path=prompt_path,
                run_dir=run_dir,
                evaluation_batch_size=evaluation_batch_size,
            )
        )

    evaluation_results = _run_cluster_evaluation_tasks_with_queue(
        evaluation_tasks,
        runner=runner,
        run_dir=run_dir,
        concurrency=evaluation_worker_count,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    reused_evaluation_count += sum(1 for result in evaluation_results if result.reused)

    evaluations_by_lesson: dict[str, list[_ClusterEvaluationResult]] = {}
    for result in evaluation_results:
        evaluations_by_lesson.setdefault(result.lesson_id, []).append(result)

    for task in tasks:
        lesson_evaluations = sorted(
            evaluations_by_lesson.get(task.lesson_id, []),
            key=lambda item: item.cluster_index,
        )
        if not lesson_evaluations:
            continue
        combined_decision = _combine_cluster_evaluation_decisions(
            lesson_id=task.lesson_id,
            input_candidate_ids=list(task.registry.get("candidates") or {}),
            model_route=task.evaluation_model_route,
            cluster_results=lesson_evaluations,
        )
        decision_path = task.lesson_dir / "lesson_reconciliation_decision.json"
        decision_path.write_text(
            json.dumps(combined_decision, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        final_artifact = assemble_lesson_reconciliation(
            lesson_id=task.lesson_id,
            registry=task.registry,
            decision=combined_decision,
            decision_artifact_path=str(decision_path.relative_to(run_dir)),
            registry_artifact_path=task.registry_artifact_path,
            lesson_candidate_clusters_artifact=str(
                (task.lesson_dir / "lesson_candidate_clusters.json").relative_to(run_dir)
            ),
            cluster_evaluation_decision_artifacts=[
                str(result.decision_path.relative_to(run_dir))
                for result in lesson_evaluations
            ],
        )
        output_path = task.lesson_dir / "lesson_reconciliation.json"
        output_path.write_text(json.dumps(final_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        artifact_paths.append(output_path)

    phase4b_result = {
        "enabled": phase4b_enabled,
        "audited_count": 0,
        "repair_count": 0,
        "confirmed_count": 0,
        "reliable_count": 0,
        "unrepaired_count": 0,
        "artifacts": [],
    }
    if phase4b_enabled:
        phase4b_result = _run_lesson_reconciliation_quality_gate(
            run_dir=run_dir,
            artifact_paths=artifact_paths,
            source_ledger=source_ledger,
            prompt=prompt,
            prompt_path=prompt_path,
            runner=runner,
            model_route=phase4b_model_route,
            repair_model_route=repair_model_route,
            contextual_repair_model_route=contextual_repair_model_route,
            provider_retry_limit=provider_retry_limit,
            provider_retry_backoff_seconds=provider_retry_backoff_seconds,
        )

    summary = {
        "lesson_count": len(source_ledger.get("lessons") or []),
        "reconciled_lesson_count": len(artifact_paths),
        "reused_lesson_count": reused_count,
        "skipped_count": len(skipped),
    }
    summary_artifact = {
        "artifact_type": "lesson_reconciliation_summary",
        "schema_version": "lesson_reconciliation_summary.v0",
        "generated_at": _now(),
        "summary": summary,
        "artifacts": [str(path.relative_to(run_dir)) for path in artifact_paths],
        "skipped": skipped,
        "model_route": model_route,
        "evaluation_model_route": evaluation_model_route,
        "repair_model_route": repair_model_route,
        "contextual_repair_model_route": contextual_repair_model_route,
        "concurrency": {"initial": concurrency, "final": concurrency},
        "stage_concurrency": {
            "clustering": {"initial": clustering_worker_count, "final": clustering_worker_count},
            "evaluation": {"initial": evaluation_worker_count, "final": evaluation_worker_count},
        },
        "stage_counts": {
            "clustering_count": len(clustering_result_by_order),
            "cluster_evaluation_count": len(evaluation_results),
            "reused_clustering_count": reused_clustering_count,
            "reused_evaluation_count": reused_evaluation_count,
        },
        "evaluation_batch_size": evaluation_batch_size,
        "provider_retries": {
            "limit": provider_retry_limit,
            "backoff_seconds": provider_retry_backoff_seconds,
        },
        "phase4b": phase4b_result,
    }
    (run_dir / "lesson_reconciliation_summary.json").write_text(
        json.dumps(summary_artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "summary": summary,
        "artifact_paths": artifact_paths,
        "skipped": skipped,
        "model_route": model_route,
        "evaluation_model_route": evaluation_model_route,
        "repair_model_route": repair_model_route,
        "contextual_repair_model_route": contextual_repair_model_route,
        "concurrency": {"initial": concurrency, "final": concurrency},
        "stage_concurrency": summary_artifact["stage_concurrency"],
        "stage_counts": summary_artifact["stage_counts"],
        "evaluation_batch_size": evaluation_batch_size,
        "reused_lesson_count": reused_count,
        "phase4b": phase4b_result,
    }


def run_lesson_reconciliation_phase4b(
    *,
    run_dir: Path,
    model_call: ModelCall,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
    repair_model_route: str = FLASH_ROUTE_ALIAS,
    contextual_repair_model_route: str = PRO_ROUTE_ALIAS,
    provider_retry_limit: int = 2,
    provider_retry_backoff_seconds: float = 10.0,
    phase4b_model_route: str = PRO_THINKING_ROUTE_ALIAS,
) -> dict[str, Any]:
    prompt_path = prompt_path or Path(__file__).resolve().parents[3] / "prompts" / "lesson_reconciliation.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    source_ledger = _read_json(run_dir / "source_ledger.json")
    runner = StageRunner(router=router or ModelRouter.default(), model_call=model_call)
    artifact_paths: list[Path] = []
    skipped: list[dict[str, str]] = []

    for lesson in source_ledger.get("lessons") or []:
        lesson_id = str(lesson.get("lesson_id") or "")
        lesson_dir = run_dir / "lessons" / lesson_id
        registry_path = lesson_dir / "semantic_reduce_candidate_registry.json"
        decision_path = lesson_dir / "lesson_reconciliation_decision.json"
        clusters_path = lesson_dir / "lesson_candidate_clusters.json"
        if not registry_path.is_file() or not decision_path.is_file():
            skipped.append({"lesson_id": lesson_id, "reason": "missing_phase4a_artifacts"})
            continue

        _clean_phase_four_b_artifacts(lesson_dir=lesson_dir)
        registry = _read_json(registry_path)
        decision = _read_json(decision_path)
        cluster_evaluation_decision_artifacts = [
            str(path.relative_to(run_dir))
            for path in sorted((lesson_dir / "cluster_evaluations").glob("*/cluster_evaluation_decision.json"))
        ]
        rebuilt_artifact = assemble_lesson_reconciliation(
            lesson_id=lesson_id,
            registry=registry,
            decision=decision,
            decision_artifact_path=str(decision_path.relative_to(run_dir)),
            registry_artifact_path=str(registry_path.relative_to(run_dir)),
            lesson_candidate_clusters_artifact=str(clusters_path.relative_to(run_dir))
            if clusters_path.is_file()
            else None,
            cluster_evaluation_decision_artifacts=cluster_evaluation_decision_artifacts,
        )
        output_path = lesson_dir / "lesson_reconciliation.json"
        output_path.write_text(json.dumps(rebuilt_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        artifact_paths.append(output_path)

    phase4b_result = _run_lesson_reconciliation_quality_gate(
        run_dir=run_dir,
        artifact_paths=artifact_paths,
        source_ledger=source_ledger,
        prompt=prompt,
        prompt_path=prompt_path,
        runner=runner,
        model_route=phase4b_model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        provider_retry_limit=provider_retry_limit,
        provider_retry_backoff_seconds=provider_retry_backoff_seconds,
    )
    summary = {
        "lesson_count": len(source_ledger.get("lessons") or []),
        "reconciled_lesson_count": len(artifact_paths),
        "reused_lesson_count": 0,
        "skipped_count": len(skipped),
    }
    summary_path = run_dir / "lesson_reconciliation_summary.json"
    if summary_path.is_file():
        summary_artifact = _read_json(summary_path)
    else:
        summary_artifact = {
            "artifact_type": "lesson_reconciliation_summary",
            "schema_version": "lesson_reconciliation_summary.v0",
        }
    summary_artifact.update(
        {
            "generated_at": _now(),
            "summary": summary,
            "artifacts": [str(path.relative_to(run_dir)) for path in artifact_paths],
            "skipped": skipped,
            "phase4b": phase4b_result,
            "phase4b_rebuilt_from_phase4a_count": len(artifact_paths),
        }
    )
    summary_path.write_text(json.dumps(summary_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "summary": summary,
        "artifact_paths": artifact_paths,
        "skipped": skipped,
        "model_route": summary_artifact.get("model_route"),
        "evaluation_model_route": summary_artifact.get("evaluation_model_route"),
        "repair_model_route": repair_model_route,
        "contextual_repair_model_route": contextual_repair_model_route,
        "concurrency": summary_artifact.get("concurrency"),
        "stage_concurrency": summary_artifact.get("stage_concurrency"),
        "stage_counts": summary_artifact.get("stage_counts"),
        "evaluation_batch_size": summary_artifact.get("evaluation_batch_size"),
        "reused_lesson_count": 0,
        "rebuilt_from_phase4a_count": len(artifact_paths),
        "phase4b": phase4b_result,
    }


@dataclass(frozen=True)
class _LessonReconciliationTask:
    order: int
    lesson_id: str
    lesson_dir: Path
    registry: dict[str, Any]
    registry_artifact_path: str
    clustering_contract: StageContract
    evaluation_model_route: str
    repair_model_route: str
    contextual_repair_model_route: str


@dataclass(frozen=True)
class _LessonClusteringResult:
    order: int
    lesson_id: str
    clusters_path: Path
    clusters_artifact: dict[str, Any]
    reused: bool


@dataclass(frozen=True)
class _ClusterEvaluationTask:
    order: int
    lesson_id: str
    cluster_index: int
    cluster_id: str
    cluster_ids: list[str]
    cluster_dir: Path
    registry: dict[str, Any]
    contract: StageContract


@dataclass(frozen=True)
class _ClusterEvaluationResult:
    order: int
    lesson_id: str
    cluster_index: int
    cluster_id: str
    cluster_ids: list[str]
    decision_path: Path
    decision: dict[str, Any]
    reused: bool


def _run_clustering_tasks_with_queue(
    tasks: list[_LessonReconciliationTask],
    *,
    runner: StageRunner,
    run_dir: Path,
    concurrency: int,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> dict[int, _LessonClusteringResult]:
    if not tasks:
        return {}
    worker_count = max(1, concurrency)
    result_by_order: dict[int, _LessonClusteringResult] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_task = {
            executor.submit(
                _run_lesson_clustering_task,
                task,
                runner=runner,
                run_dir=run_dir,
                provider_retry_limit=provider_retry_limit,
                provider_retry_backoff_seconds=provider_retry_backoff_seconds,
            ): task
            for task in tasks
        }
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            result_by_order[task.order] = future.result()
    return result_by_order


def _run_lesson_clustering_task(
    task: _LessonReconciliationTask,
    *,
    runner: StageRunner,
    run_dir: Path,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> _LessonClusteringResult:
    existing = _existing_valid_lesson_candidate_clusters(
        artifact_path=task.lesson_dir / "lesson_candidate_clusters.json",
        registry=task.registry,
        model_route=task.clustering_contract.model_route,
    )
    if existing:
        return _LessonClusteringResult(
            order=task.order,
            lesson_id=task.lesson_id,
            clusters_path=task.lesson_dir / "lesson_candidate_clusters.json",
            clusters_artifact=existing,
            reused=True,
        )

    result: StageResult | None = None
    for attempt in range(provider_retry_limit + 1):
        try:
            result = runner.run(task.clustering_contract, run_dir=task.lesson_dir)
            break
        except StageBlockedError as exc:
            if not _is_transient_provider_error(exc) or attempt >= provider_retry_limit:
                raise
            if provider_retry_backoff_seconds:
                time.sleep(provider_retry_backoff_seconds * (attempt + 1))
    if result is None:
        raise StageBlockedError(f"Lesson candidate clustering failed without result for lesson {task.lesson_id}")
    decision = _read_json(result.artifact_path)
    clusters_artifact = _build_lesson_candidate_clusters_artifact(
        decision=decision,
        decision_artifact_path=str(result.artifact_path.relative_to(run_dir)),
        registry_artifact_path=task.registry_artifact_path,
    )
    output_path = task.lesson_dir / "lesson_candidate_clusters.json"
    output_path.write_text(json.dumps(clusters_artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return _LessonClusteringResult(
        order=task.order,
        lesson_id=task.lesson_id,
        clusters_path=output_path,
        clusters_artifact=clusters_artifact,
        reused=False,
    )


def _prepare_cluster_evaluation_tasks(
    *,
    task: _LessonReconciliationTask,
    clusters_artifact: dict[str, Any],
    prompt: str,
    prompt_path: Path,
    run_dir: Path,
    evaluation_batch_size: int,
) -> list[_ClusterEvaluationTask]:
    tasks: list[_ClusterEvaluationTask] = []
    clusters = [cluster for cluster in clusters_artifact.get("clusters") or [] if isinstance(cluster, dict)]
    for cluster_index, cluster_batch in enumerate(_cluster_batches(clusters, evaluation_batch_size), start=1):
        cluster_ids = [
            str(cluster.get("id") or f"cluster_{cluster_index:03d}_{offset:03d}")
            for offset, cluster in enumerate(cluster_batch, start=1)
        ]
        cluster_id = cluster_ids[0] if len(cluster_ids) == 1 else f"batch_{cluster_index:03d}"
        cluster_dir = task.lesson_dir / "cluster_evaluations" / _cluster_dir_name(cluster_id)
        cluster_dir.mkdir(parents=True, exist_ok=True)
        input_candidate_ids = [
            str(candidate_id)
            for cluster in cluster_batch
            for candidate_id in cluster.get("candidate_ids") or []
        ]
        model_input = _build_cluster_evaluation_input(
            lesson_id=task.lesson_id,
            clusters=cluster_batch,
            registry=task.registry,
            input_candidate_ids=input_candidate_ids,
            prompt=prompt,
            prompt_path=str(prompt_path),
            model_route=task.evaluation_model_route,
            lesson_candidate_clusters_artifact=str((task.lesson_dir / "lesson_candidate_clusters.json").relative_to(run_dir)),
        )
        (cluster_dir / "cluster_evaluation_input.json").write_text(
            json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        contract = StageContract(
            name="lesson_cluster_evaluation",
            required_inputs=["cluster_evaluation_input.json"],
            output_artifact="cluster_evaluation_decision.json",
            model_route=task.evaluation_model_route,
            repair_model_route=task.repair_model_route,
            contextual_repair_model_route=task.contextual_repair_model_route,
            validator=lambda artifact, registry=task.registry: validate_reduce_decision(artifact, registry),
            normalizer=_normalize_cluster_evaluation_output,
        )
        tasks.append(
            _ClusterEvaluationTask(
                order=task.order,
                lesson_id=task.lesson_id,
                cluster_index=cluster_index,
                cluster_id=cluster_id,
                cluster_ids=cluster_ids,
                cluster_dir=cluster_dir,
                registry=task.registry,
                contract=contract,
            )
        )
    return tasks


def _run_cluster_evaluation_tasks_with_queue(
    tasks: list[_ClusterEvaluationTask],
    *,
    runner: StageRunner,
    run_dir: Path,
    concurrency: int,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> list[_ClusterEvaluationResult]:
    if not tasks:
        return []
    worker_count = max(1, concurrency)
    results: list[_ClusterEvaluationResult] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        future_to_task = {
            executor.submit(
                _run_cluster_evaluation_task,
                task,
                runner=runner,
                run_dir=run_dir,
                provider_retry_limit=provider_retry_limit,
                provider_retry_backoff_seconds=provider_retry_backoff_seconds,
            ): task
            for task in tasks
        }
        for future in concurrent.futures.as_completed(future_to_task):
            results.append(future.result())
    return sorted(results, key=lambda item: (item.order, item.cluster_index))


def _run_cluster_evaluation_task(
    task: _ClusterEvaluationTask,
    *,
    runner: StageRunner,
    run_dir: Path,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> _ClusterEvaluationResult:
    existing = _existing_valid_cluster_evaluation_decision(
        artifact_path=task.cluster_dir / "cluster_evaluation_decision.json",
        registry=task.registry,
        model_route=task.contract.model_route,
    )
    if existing:
        return _ClusterEvaluationResult(
            order=task.order,
            lesson_id=task.lesson_id,
            cluster_index=task.cluster_index,
            cluster_id=task.cluster_id,
            cluster_ids=task.cluster_ids,
            decision_path=task.cluster_dir / "cluster_evaluation_decision.json",
            decision=existing,
            reused=True,
        )

    result: StageResult | None = None
    for attempt in range(provider_retry_limit + 1):
        try:
            result = runner.run(task.contract, run_dir=task.cluster_dir)
            break
        except StageBlockedError as exc:
            if not _is_transient_provider_error(exc) or attempt >= provider_retry_limit:
                raise
            if provider_retry_backoff_seconds:
                time.sleep(provider_retry_backoff_seconds * (attempt + 1))
    if result is None:
        raise StageBlockedError(f"Lesson cluster evaluation failed without result for cluster {task.cluster_id}")
    return _ClusterEvaluationResult(
        order=task.order,
        lesson_id=task.lesson_id,
        cluster_index=task.cluster_index,
        cluster_id=task.cluster_id,
        cluster_ids=task.cluster_ids,
        decision_path=result.artifact_path,
        decision=_read_json(result.artifact_path),
        reused=False,
    )


def _run_lesson_reconciliation_quality_gate(
    *,
    run_dir: Path,
    artifact_paths: list[Path],
    source_ledger: dict[str, Any],
    prompt: str,
    prompt_path: Path,
    runner: StageRunner,
    model_route: str,
    repair_model_route: str,
    contextual_repair_model_route: str,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> dict[str, Any]:
    lesson_by_id = {
        str(lesson.get("lesson_id") or ""): _compact_lesson(lesson)
        for lesson in source_ledger.get("lessons") or []
    }
    result = {
        "enabled": True,
        "model_route": model_route,
        "audited_count": 0,
        "repair_count": 0,
        "confirmed_count": 0,
        "reliable_count": 0,
        "unrepaired_count": 0,
        "artifacts": [],
    }
    for artifact_path in artifact_paths:
        artifact = _read_json(artifact_path)
        lesson_id = str(artifact.get("lesson_id") or "")
        lesson_dir = artifact_path.parent
        registry_path = run_dir / str(artifact.get("candidate_registry_artifact") or "")
        registry = _read_json(registry_path)
        audit = _build_lesson_reconciliation_quality_audit(
            lesson=lesson_by_id.get(lesson_id, {"id": lesson_id}),
            artifact=artifact,
            registry=registry,
        )
        audit_path = lesson_dir / "lesson_reconciliation_quality_audit.json"
        audit_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result["audited_count"] += 1
        result["artifacts"].append(str(audit_path.relative_to(run_dir)))
        if audit["reliability"] == "reliable":
            result["reliable_count"] += 1
            artifact["phase4b_quality_audit"] = audit
            artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            continue

        repaired_artifact = artifact
        repair_artifacts: list[str] = []
        repair_decisions: list[dict[str, Any]] = []
        repaired_any = False
        for repair_plan in audit.get("repair_plan") or []:
            repair_reason = str(repair_plan.get("repair_reason") or "quality_repair")
            target_candidate_ids = [
                candidate_id
                for candidate_id in repair_plan.get("candidate_ids") or []
                if isinstance(candidate_id, str) and candidate_id
            ]
            if not target_candidate_ids:
                continue
            repair_decision_path = _run_phase4b_repair(
                run_dir=run_dir,
                lesson_dir=lesson_dir,
                lesson=lesson_by_id.get(lesson_id, {"id": lesson_id}),
                artifact=repaired_artifact,
                registry=registry,
                quality_audit=audit,
                repair_reason=repair_reason,
                target_candidate_ids=target_candidate_ids,
                prompt=prompt,
                prompt_path=prompt_path,
                runner=runner,
                model_route=model_route,
                repair_model_route=repair_model_route,
                contextual_repair_model_route=contextual_repair_model_route,
                provider_retry_limit=provider_retry_limit,
                provider_retry_backoff_seconds=provider_retry_backoff_seconds,
            )
            decision = _read_json(repair_decision_path)
            repair_decisions.append(decision)
            repaired_artifact = _apply_phase4b_repair_decision(
                artifact=repaired_artifact,
                registry=registry,
                decision=decision,
                target_candidate_ids=target_candidate_ids,
            )
            repair_artifacts.append(str(repair_decision_path.relative_to(run_dir)))
            repaired_any = True

        if repaired_any:
            repaired_audit = _build_lesson_reconciliation_quality_audit(
                lesson=lesson_by_id.get(lesson_id, {"id": lesson_id}),
                artifact=repaired_artifact,
                registry=registry,
            )
            if repaired_audit.get("reliability") == "reliable":
                result["repair_count"] += 1
                repaired_audit["reliability"] = "repaired"
            elif _is_confirmed_over_pruned_repair(
                initial_audit=audit,
                repaired_audit=repaired_audit,
                repair_decisions=repair_decisions,
            ):
                result["confirmed_count"] += 1
                repaired_audit["reliability"] = "confirmed"
                repaired_audit["flags"] = ["over_pruned_confirmed"]
            else:
                result["unrepaired_count"] += 1
                repaired_audit.setdefault("flags", []).append("repair_still_unreliable")
            repaired_audit["repair_decision_artifacts"] = repair_artifacts
            repaired_artifact["phase4b_quality_audit"] = repaired_audit
            repaired_artifact["phase4b_repair_decision_artifacts"] = repair_artifacts
            artifact_path.write_text(
                json.dumps(repaired_artifact, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            result["unrepaired_count"] += 1
            artifact["phase4b_quality_audit"] = audit
            artifact_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def _run_phase4b_repair(
    *,
    run_dir: Path,
    lesson_dir: Path,
    lesson: dict[str, Any],
    artifact: dict[str, Any],
    registry: dict[str, Any],
    quality_audit: dict[str, Any],
    repair_reason: str,
    target_candidate_ids: list[str],
    prompt: str,
    prompt_path: Path,
    runner: StageRunner,
    model_route: str,
    repair_model_route: str,
    contextual_repair_model_route: str,
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
) -> Path:
    repair_dir = lesson_dir / "phase4b_repairs" / _cluster_dir_name(repair_reason)
    repair_dir.mkdir(parents=True, exist_ok=True)
    decision_path = repair_dir / "lesson_reconciliation_quality_repair_decision.json"
    existing = _existing_valid_phase4b_repair_decision(
        artifact_path=decision_path,
        target_candidate_ids=target_candidate_ids,
        artifact=artifact,
    )
    if existing:
        return decision_path

    model_input = _build_phase4b_repair_input(
        lesson=lesson,
        artifact=artifact,
        registry=registry,
        quality_audit=quality_audit,
        repair_reason=repair_reason,
        target_candidate_ids=target_candidate_ids,
        prompt=prompt,
        prompt_path=str(prompt_path),
        model_route=model_route,
    )
    (repair_dir / "lesson_reconciliation_quality_repair_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    contract = StageContract(
        name="lesson_reconciliation_quality_repair",
        required_inputs=["lesson_reconciliation_quality_repair_input.json"],
        output_artifact="lesson_reconciliation_quality_repair_decision.json",
        model_route=model_route,
        repair_model_route=repair_model_route,
        contextual_repair_model_route=contextual_repair_model_route,
        validator=lambda decision, target_candidate_ids=target_candidate_ids, artifact=artifact: (
            validate_phase4b_repair_decision(
                decision,
                target_candidate_ids=target_candidate_ids,
                artifact=artifact,
            )
        ),
        normalizer=_normalize_phase4b_repair_output,
    )
    stage_result: StageResult | None = None
    for attempt in range(provider_retry_limit + 1):
        try:
            stage_result = runner.run(contract, run_dir=repair_dir)
            break
        except StageBlockedError as exc:
            if not _is_transient_provider_error(exc) or attempt >= provider_retry_limit:
                raise
            if provider_retry_backoff_seconds:
                time.sleep(provider_retry_backoff_seconds * (attempt + 1))
    if stage_result is None:
        raise StageBlockedError(f"Lesson reconciliation Phase 4b repair failed without result for {repair_reason}")
    return stage_result.artifact_path


def _is_confirmed_over_pruned_repair(
    *,
    initial_audit: dict[str, Any],
    repaired_audit: dict[str, Any],
    repair_decisions: list[dict[str, Any]],
) -> bool:
    initial_flags = set(initial_audit.get("flags") or [])
    repaired_flags = set(repaired_audit.get("flags") or [])
    if initial_flags != {"over_pruned"}:
        return False
    if repaired_flags != {"over_pruned"}:
        return False
    if len(repair_decisions) != 1:
        return False
    decision = repair_decisions[0]
    if decision.get("repair_reason") != "over_pruned":
        return False
    target_ids = {
        candidate_id
        for candidate_id in decision.get("target_candidate_ids") or []
        if isinstance(candidate_id, str) and candidate_id
    }
    assignments = [
        assignment
        for assignment in decision.get("candidate_assignments") or []
        if isinstance(assignment, dict)
    ]
    assigned_ids = {
        str(assignment.get("candidate_id") or "")
        for assignment in assignments
        if str(assignment.get("candidate_id") or "")
    }
    if not target_ids or assigned_ids != target_ids:
        return False
    confirmation_reasons = {"unrelated", "low_teaching_value", "unsupported_lesson_intent", "incidental"}
    return all(
        assignment.get("status") == "pruned" and assignment.get("reason") in confirmation_reasons
        for assignment in assignments
    )


def _existing_valid_artifact(*, artifact_path: Path, lesson_id: str, model_route: str) -> bool:
    if not artifact_path.is_file():
        return False
    try:
        artifact = _read_json(artifact_path)
    except json.JSONDecodeError:
        return False
    return not validate_lesson_reconciliation_artifact(
        artifact,
        lesson_id=lesson_id,
        model_route=model_route,
    )


def _build_lesson_candidate_clustering_input(
    *,
    lesson: dict[str, Any],
    registry: dict[str, Any],
    input_candidate_ids: list[str],
    prompt: str,
    prompt_path: str,
    model_route: str,
) -> dict[str, Any]:
    registry_candidates = registry.get("candidates") or {}
    unknown_candidate_ids = [
        candidate_id
        for candidate_id in input_candidate_ids
        if candidate_id not in registry_candidates
    ]
    if unknown_candidate_ids:
        raise ValueError("unknown lesson candidate IDs: " + ", ".join(unknown_candidate_ids))
    return {
        "artifact_type": "lesson_candidate_clustering_input",
        "schema_version": "lesson_candidate_clustering_input.v0",
        "source_artifact": registry.get("source_artifact"),
        "candidate_registry_artifact": "semantic_reduce_candidate_registry.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "lesson_candidate_clustering",
        "model_route": model_route,
        "lesson": lesson,
        "input_candidate_ids": input_candidate_ids,
        "candidates": [_compact_candidate_view(registry_candidates[candidate_id]) for candidate_id in input_candidate_ids],
        "output_contract": {
            "clusters": [
                {
                    "id": "cluster_001",
                    "label": "Short cluster label",
                    "rationale": "Why these candidates may describe the same teachable idea.",
                    "candidate_ids": ["compact-candidate-id"],
                }
            ],
            "candidate_assignment_rule": (
                "Cluster only. Every input candidate ID must appear exactly once across clusters. "
                "Do not create accepted concepts, final labels, provenance, or evidence."
            ),
        },
        "web_access_policy": _no_web_policy(),
    }


def _build_cluster_evaluation_input(
    *,
    lesson_id: str,
    clusters: list[dict[str, Any]],
    registry: dict[str, Any],
    input_candidate_ids: list[str],
    prompt: str,
    prompt_path: str,
    model_route: str,
    lesson_candidate_clusters_artifact: str,
) -> dict[str, Any]:
    registry_candidates = registry.get("candidates") or {}
    unknown_candidate_ids = [
        candidate_id
        for candidate_id in input_candidate_ids
        if candidate_id not in registry_candidates
    ]
    if unknown_candidate_ids:
        raise ValueError("unknown lesson cluster candidate IDs: " + ", ".join(unknown_candidate_ids))
    primary_cluster = clusters[0] if clusters else {}
    return {
        "artifact_type": "cluster_evaluation_input",
        "schema_version": "cluster_evaluation_input.v0",
        "source_artifact": registry.get("source_artifact"),
        "candidate_registry_artifact": "semantic_reduce_candidate_registry.json",
        "lesson_candidate_clusters_artifact": lesson_candidate_clusters_artifact,
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "lesson_cluster_evaluation",
        "model_route": model_route,
        "lesson_id": lesson_id,
        "cluster": primary_cluster,
        "clusters": clusters,
        "input_candidate_ids": input_candidate_ids,
        "candidates": [_compact_candidate_view(registry_candidates[candidate_id]) for candidate_id in input_candidate_ids],
        "controlled_pruning_reasons": sorted(_controlled_pruning_reasons()),
        "output_contract": _cluster_evaluation_output_contract(),
        "web_access_policy": _no_web_policy(),
    }


def _normalize_lesson_candidate_clustering_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    model_input = inputs["lesson_candidate_clustering_input.json"]
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("lesson candidate clustering model output must be a JSON object")
    clusters = payload.get("clusters")
    if not isinstance(clusters, list):
        raise ValueError("lesson candidate clustering model output must include clusters")
    normalized_clusters = []
    normalization_warnings: list[str] = []
    for index, cluster in enumerate(clusters, start=1):
        if not isinstance(cluster, dict):
            normalized_clusters.append(cluster)
            continue
        cluster_id = str(cluster.get("id") or f"cluster_{index:03d}")
        candidate_ids = cluster.get("candidate_ids")
        if candidate_ids is None:
            candidate_ids = cluster.get("candidates")
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
        "artifact_type": "lesson_candidate_clustering_decision",
        "schema_version": "lesson_candidate_clustering_decision.v0",
        "generated_at": _now(),
        "lesson_id": str((model_input.get("lesson") or {}).get("id") or ""),
        "stage_name": "lesson_candidate_clustering",
        "model_route": str(model_input.get("model_route") or PRO_ROUTE_ALIAS),
        "input_candidate_ids": input_candidate_ids,
        "clusters": normalized_clusters,
        "normalization_warnings": normalization_warnings,
        "summary": {
            "input_candidate_count": len(input_candidate_ids),
            "cluster_count": len(normalized_clusters),
        },
    }


def _normalize_cluster_evaluation_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    model_input = inputs["cluster_evaluation_input.json"]
    decision = normalize_decision_output(
        raw=raw,
        scope_id=str(model_input.get("lesson_id") or ""),
        stage_name="lesson_cluster_evaluation",
        model_route=str(model_input.get("model_route") or PRO_THINKING_ROUTE_ALIAS),
        input_candidate_ids=model_input.get("input_candidate_ids") or [],
    )
    return _canonicalize_reduce_decision_assignments(decision)


def _normalize_phase4b_repair_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("Phase 4b repair output must be a JSON object")
    new_accepted = payload.get("new_accepted_concepts") or payload.get("accepted_concepts") or []
    existing_additions = payload.get("existing_concept_candidate_additions") or []
    candidate_assignments = payload.get("candidate_assignments") or []
    return {
        "artifact_type": "lesson_reconciliation_quality_repair_decision",
        "schema_version": "lesson_reconciliation_quality_repair_decision.v0",
        "generated_at": _now(),
        "lesson_id": str(model_input.get("lesson_id") or ""),
        "stage_name": "lesson_reconciliation_quality_repair",
        "model_route": str(model_input.get("model_route") or PRO_THINKING_ROUTE_ALIAS),
        "repair_reason": str(model_input.get("repair_reason") or ""),
        "target_candidate_ids": model_input.get("target_candidate_ids") or [],
        "new_accepted_concepts": new_accepted,
        "existing_concept_candidate_additions": existing_additions,
        "candidate_assignments": candidate_assignments,
        "summary": {
            "target_candidate_count": len(model_input.get("target_candidate_ids") or []),
            "new_accepted_concept_count": len(new_accepted) if isinstance(new_accepted, list) else 0,
            "existing_concept_addition_count": len(existing_additions)
            if isinstance(existing_additions, list)
            else 0,
            "candidate_assignment_count": len(candidate_assignments)
            if isinstance(candidate_assignments, list)
            else 0,
        },
    }


def _build_phase4b_repair_input(
    *,
    lesson: dict[str, Any],
    artifact: dict[str, Any],
    registry: dict[str, Any],
    quality_audit: dict[str, Any],
    repair_reason: str,
    target_candidate_ids: list[str],
    prompt: str,
    prompt_path: str,
    model_route: str,
) -> dict[str, Any]:
    registry_candidates = registry.get("candidates") or {}
    return {
        "artifact_type": "lesson_reconciliation_quality_repair_input",
        "schema_version": "lesson_reconciliation_quality_repair_input.v0",
        "source_artifact": artifact.get("source_artifact"),
        "candidate_registry_artifact": artifact.get("candidate_registry_artifact"),
        "lesson_reconciliation_artifact": "lesson_reconciliation.json",
        "prompt_path": prompt_path,
        "prompt": prompt,
        "task": "lesson_reconciliation_quality_repair",
        "model_route": model_route,
        "lesson_id": artifact.get("lesson_id"),
        "lesson": lesson,
        "quality_audit": quality_audit,
        "repair_reason": repair_reason,
        "target_candidate_ids": target_candidate_ids,
        "target_candidates": [
            _compact_candidate_view(registry_candidates[candidate_id])
            for candidate_id in target_candidate_ids
            if candidate_id in registry_candidates
        ],
        "current_reconciled_candidates": _compact_reconciled_candidates(
            artifact.get("reconciled_candidates") or []
        ),
        "current_pruned_candidates": _compact_candidate_refs_with_reason(
            artifact.get("pruned_candidates") or [],
            registry=registry,
        ),
        "current_review_candidates": _compact_candidate_refs_with_reason(
            artifact.get("review_candidates") or [],
            registry=registry,
        ),
        "controlled_pruning_reasons": sorted(_controlled_pruning_reasons()),
        "output_contract": _phase4b_repair_output_contract(),
        "web_access_policy": _no_web_policy(),
    }


def _compact_reconciled_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    compact = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        compact.append(
            {
                "reconciled_candidate_id": candidate.get("reconciled_candidate_id"),
                "label": candidate.get("label"),
                "description": candidate.get("description"),
                "coverage_criteria": candidate.get("coverage_criteria") or [],
                "source_candidate_ids": candidate.get("source_candidate_ids") or [],
                "merge_rationale": candidate.get("merge_rationale"),
            }
        )
    return compact


def _compact_candidate_refs_with_reason(
    candidates: list[dict[str, Any]],
    *,
    registry: dict[str, Any],
) -> list[dict[str, Any]]:
    compact = []
    entries = registry.get("candidates") or {}
    for item in candidates:
        if not isinstance(item, dict):
            continue
        candidate_id = _candidate_ref_to_compact_id(entries, item.get("candidate_ref") or {})
        compact.append(
            {
                "candidate_id": candidate_id,
                "pruning_reason": item.get("pruning_reason"),
                "explanation": item.get("explanation"),
            }
        )
    return compact


def _build_lesson_candidate_clusters_artifact(
    *,
    decision: dict[str, Any],
    decision_artifact_path: str,
    registry_artifact_path: str,
) -> dict[str, Any]:
    return {
        "artifact_type": "lesson_candidate_clusters",
        "schema_version": "lesson_candidate_clusters.v0",
        "generated_at": _now(),
        "source_artifact": "source_ledger.json",
        "candidate_registry_artifact": registry_artifact_path,
        "clustering_decision_artifact": decision_artifact_path,
        "lesson_id": decision.get("lesson_id"),
        "model_route": decision.get("model_route"),
        "input_candidate_ids": decision.get("input_candidate_ids") or [],
        "clusters": decision.get("clusters") or [],
        "summary": {
            "input_candidate_count": len(decision.get("input_candidate_ids") or []),
            "cluster_count": len(decision.get("clusters") or []),
        },
    }


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


def _next_generated_cluster_id(existing_cluster_ids: set[str]) -> str:
    index = 1
    while True:
        cluster_id = f"cluster_{index:03d}"
        if cluster_id not in existing_cluster_ids:
            return cluster_id
        index += 1


def _combine_cluster_evaluation_decisions(
    *,
    lesson_id: str,
    input_candidate_ids: list[str],
    model_route: str,
    cluster_results: list[_ClusterEvaluationResult],
) -> dict[str, Any]:
    accepted_concepts: list[dict[str, Any]] = []
    candidate_assignments: list[dict[str, Any]] = []
    pruned: list[dict[str, Any]] = []
    review_count = 0

    for result in cluster_results:
        local_id_map: dict[str, str] = {}
        prefix = _cluster_dir_name(result.cluster_id)
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
            if scoped_assignment.get("status") == "pruned":
                pruned.append(
                    {
                        "candidate_id": scoped_assignment.get("candidate_id"),
                        "reason": scoped_assignment.get("reason"),
                        "explanation": scoped_assignment.get("explanation"),
                    }
                )
            elif scoped_assignment.get("status") == "review":
                review_count += 1

    return {
        "artifact_type": "semantic_reduce_decision",
        "schema_version": "semantic_reduce_decision.v0",
        "generated_at": _now(),
        "scope_id": lesson_id,
        "stage_name": "lesson_reconciliation",
        "model_route": model_route,
        "input_candidate_ids": input_candidate_ids,
        "accepted": accepted_concepts,
        "accepted_concepts": accepted_concepts,
        "candidate_assignments": candidate_assignments,
        "pruned": pruned,
        "summary": {
            "input_candidate_count": len(input_candidate_ids),
            "accepted_count": len(accepted_concepts),
            "pruned_count": len(pruned),
            "candidate_assignment_count": len(candidate_assignments),
            "review_count": review_count,
        },
    }


def _canonicalize_reduce_decision_assignments(decision: dict[str, Any]) -> dict[str, Any]:
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
            canonical_assignments.append(
                {
                    "candidate_id": candidate_id,
                    "status": "review",
                    "explanation": "Deterministically added because cluster evaluation omitted this input candidate.",
                }
            )
        assigned_candidate_ids.add(candidate_id)

    pruned = [
        {
            "candidate_id": assignment.get("candidate_id"),
            "reason": assignment.get("reason"),
            "explanation": assignment.get("explanation"),
        }
        for assignment in canonical_assignments
        if isinstance(assignment, dict) and assignment.get("status") == "pruned"
    ]
    review_count = sum(
        1
        for assignment in canonical_assignments
        if isinstance(assignment, dict) and assignment.get("status") == "review"
    )
    decision["candidate_assignments"] = canonical_assignments
    decision["pruned"] = pruned
    decision["summary"] = {
        "input_candidate_count": len(input_candidate_ids),
        "accepted_count": len(accepted_concepts),
        "pruned_count": len(pruned),
        "candidate_assignment_count": len(canonical_assignments),
        "review_count": review_count,
    }
    return decision


def _build_lesson_reconciliation_quality_audit(
    *,
    lesson: dict[str, Any],
    artifact: dict[str, Any],
    registry: dict[str, Any],
) -> dict[str, Any]:
    entries = registry.get("candidates") or {}
    input_count = len(entries)
    reconciled_count = len(artifact.get("reconciled_candidates") or [])
    pruned_candidates = artifact.get("pruned_candidates") or []
    review_candidates = artifact.get("review_candidates") or []
    pruned_count = len(pruned_candidates)
    review_count = len(review_candidates)
    candidate_assignments = artifact.get("candidate_assignments") or []
    reconciled_candidates = artifact.get("reconciled_candidates") or []
    assignment_count = len(candidate_assignments)
    merged_assignment_count = sum(
        1 for assignment in candidate_assignments if isinstance(assignment, dict) and assignment.get("status") == "merged_into"
    )
    largest_reconciled_source_ids = max(
        (
            [
                candidate_id
                for candidate_id in candidate.get("source_candidate_ids") or []
                if isinstance(candidate_id, str) and candidate_id
            ]
            for candidate in reconciled_candidates
            if isinstance(candidate, dict)
        ),
        key=len,
        default=[],
    )
    duplicate_accepted_candidate_ids: list[str] = []
    duplicate_label_groups = 0
    metadata_only_accepted_candidate_ids: list[str] = []
    metadata_only_accepted_count = 0
    off_lesson_accepted_candidate_ids: list[str] = []
    accepted_candidate_ids: list[str] = []
    source_body_candidate_count = sum(
        1 for entry in entries.values() if entry.get("evidence_type") == "source_body"
    )
    reconciled_by_normalized_label: dict[str, list[dict[str, Any]]] = {}
    for candidate in reconciled_candidates:
        if not isinstance(candidate, dict):
            continue
        source_candidate_ids = [
            candidate_id
            for candidate_id in candidate.get("source_candidate_ids") or []
            if isinstance(candidate_id, str) and candidate_id
        ]
        accepted_candidate_ids.extend(source_candidate_ids)
        if source_candidate_ids and all(
            (entries.get(candidate_id) or {}).get("evidence_type") == "workbook_metadata"
            for candidate_id in source_candidate_ids
        ):
            metadata_only_accepted_count += 1
            metadata_only_accepted_candidate_ids.extend(source_candidate_ids)
        if _looks_like_off_lesson_accepted_concept(candidate):
            off_lesson_accepted_candidate_ids.extend(source_candidate_ids)
        normalized_label = _normalize_concept_text(candidate.get("label"))
        if normalized_label:
            reconciled_by_normalized_label.setdefault(normalized_label, []).append(candidate)
    for duplicate_group in reconciled_by_normalized_label.values():
        if len(duplicate_group) <= 1:
            continue
        duplicate_label_groups += 1
        for duplicate_candidate in duplicate_group[1:]:
            duplicate_accepted_candidate_ids.extend(
                candidate_id
                for candidate_id in duplicate_candidate.get("source_candidate_ids") or []
                if isinstance(candidate_id, str) and candidate_id
            )
    deterministic_review_count = sum(
        1
        for item in review_candidates
        if "deterministically added" in str(item.get("explanation") or "").lower()
    )
    near_duplicate_pruned_ids = [
        candidate_id
        for item in pruned_candidates
        for candidate_id in [_candidate_ref_to_compact_id(entries, item.get("candidate_ref") or {})]
        if candidate_id and item.get("pruning_reason") == "near_duplicate"
    ]
    pruned_candidate_ids = [
        candidate_id
        for item in pruned_candidates
        for candidate_id in [_candidate_ref_to_compact_id(entries, item.get("candidate_ref") or {})]
        if candidate_id
    ]
    review_candidate_ids = [
        candidate_id
        for item in review_candidates
        for candidate_id in [_candidate_ref_to_compact_id(entries, item.get("candidate_ref") or {})]
        if candidate_id
    ]
    review_ratio = review_count / input_count if input_count else 0.0
    pruned_ratio = pruned_count / input_count if input_count else 0.0
    accepted_ratio = reconciled_count / input_count if input_count else 0.0
    merged_ratio = merged_assignment_count / input_count if input_count else 0.0
    assignment_complete = assignment_count >= input_count
    flags: list[str] = []
    repair_plan: list[dict[str, Any]] = []

    evidence_score = 3 if assignment_complete else 1
    assignment_score = 3 if assignment_complete and review_count == 0 else 1 if assignment_complete else 0
    pruning_review_score = 3
    granularity_score = 3
    concept_score = 3
    coherence_score = 3
    criteria_score = 3 if _all_reconciled_candidates_have_criteria(artifact) else 1

    if review_count:
        flags.append("review_needed")
        assignment_score = min(assignment_score, 1)
        pruning_review_score = min(pruning_review_score, 1)
        granularity_score = min(granularity_score, 2)
        repair_plan.append(
            {
                "repair_reason": "review_fallback",
                "candidate_ids": review_candidate_ids,
                "explanation": "Review is not allowed as a final Phase 4 state.",
            }
        )
    if deterministic_review_count:
        flags.append("deterministic_review_fallback")
        pruning_review_score = 0
    if near_duplicate_pruned_ids and pruned_ratio >= 0.25:
        flags.append("questionable_prune")
        flags.append("granularity_loss")
        granularity_score = min(granularity_score, 1)
        pruning_review_score = min(pruning_review_score, 1)
        repair_plan.append(
            {
                "repair_reason": "questionable_prune",
                "candidate_ids": near_duplicate_pruned_ids,
                "explanation": "Many candidates were pruned as near-duplicates and need targeted re-evaluation.",
            }
        )
    if input_count and accepted_ratio < 0.15 and pruned_ratio > 0.5:
        flags.append("over_pruned")
        concept_score = min(concept_score, 2)
        coherence_score = min(coherence_score, 1)
        already_targeted_ids = {
            candidate_id
            for plan in repair_plan
            for candidate_id in plan.get("candidate_ids") or []
            if isinstance(candidate_id, str)
        }
        over_pruned_candidate_ids = [
            candidate_id for candidate_id in pruned_candidate_ids if candidate_id not in already_targeted_ids
        ]
        if over_pruned_candidate_ids:
            repair_plan.append(
                {
                    "repair_reason": "over_pruned",
                    "candidate_ids": over_pruned_candidate_ids,
                    "explanation": (
                        "The accepted/pruned balance suggests useful lesson-local concepts may have been "
                        "discarded and need targeted re-evaluation."
                    ),
                }
            )
    if input_count >= 5 and accepted_ratio < 0.25 and pruned_ratio < 0.25 and (
        len(largest_reconciled_source_ids) >= 5 or merged_ratio >= 0.5
    ):
        flags.append("over_merged")
        granularity_score = min(granularity_score, 1)
        coherence_score = min(coherence_score, 1)
        over_merged_candidate_ids = largest_reconciled_source_ids[1:]
        if over_merged_candidate_ids:
            repair_plan.append(
                {
                    "repair_reason": "over_merged",
                    "candidate_ids": over_merged_candidate_ids,
                    "explanation": (
                        "Many distinct candidates are represented by one broad accepted concept and need "
                        "targeted split/recheck."
                    ),
                }
            )
    if duplicate_accepted_candidate_ids:
        flags.append("fragmented_duplicates")
        concept_score = min(concept_score, 2)
        granularity_score = min(granularity_score, 1)
        repair_plan.append(
            {
                "repair_reason": "fragmented_duplicates",
                "candidate_ids": duplicate_accepted_candidate_ids,
                "explanation": "Accepted concepts with duplicate labels need targeted merge/recheck.",
            }
        )
    metadata_only_accepted_ratio = metadata_only_accepted_count / reconciled_count if reconciled_count else 0.0
    if (
        source_body_candidate_count > 0
        and metadata_only_accepted_count >= 2
        and metadata_only_accepted_ratio >= 0.5
        and metadata_only_accepted_candidate_ids
    ):
        flags.append("metadata_overreach")
        concept_score = min(concept_score, 1)
        coherence_score = min(coherence_score, 1)
        repair_plan.append(
            {
                "repair_reason": "metadata_overreach",
                "candidate_ids": metadata_only_accepted_candidate_ids,
                "explanation": (
                    "Metadata-only candidates dominate accepted concepts despite source-body evidence and need "
                    "targeted lesson-gap recheck."
                ),
            }
        )
    if off_lesson_accepted_candidate_ids:
        flags.append("off_lesson_accepted")
        concept_score = min(concept_score, 1)
        coherence_score = min(coherence_score, 1)
        repair_plan.append(
            {
                "repair_reason": "off_lesson_accepted",
                "candidate_ids": off_lesson_accepted_candidate_ids,
                "explanation": (
                    "Accepted setup, repository, administration, download, or career material needs targeted "
                    "lesson-local recheck."
                ),
            }
        )
    if input_count >= 6 and accepted_ratio >= 0.85 and pruned_ratio <= 0.05 and len(accepted_candidate_ids) > 1:
        flags.append("over_accepted")
        concept_score = min(concept_score, 2)
        coherence_score = min(coherence_score, 1)
        already_targeted_ids = {
            candidate_id
            for plan in repair_plan
            for candidate_id in plan.get("candidate_ids") or []
            if isinstance(candidate_id, str)
        }
        over_accepted_candidate_ids = [
            candidate_id for candidate_id in accepted_candidate_ids[1:] if candidate_id not in already_targeted_ids
        ]
        if over_accepted_candidate_ids:
            repair_plan.append(
                {
                    "repair_reason": "over_accepted",
                    "candidate_ids": over_accepted_candidate_ids,
                    "explanation": (
                        "Nearly every candidate became an accepted concept and needs targeted pruning/merge recheck."
                    ),
                }
            )

    net_score = min(
        concept_score,
        granularity_score,
        evidence_score,
        assignment_score,
        pruning_review_score,
        criteria_score,
        coherence_score,
    )
    if review_ratio >= 0.2:
        net_score = min(net_score, 1)
    if pruned_ratio >= 0.5 and near_duplicate_pruned_ids:
        net_score = min(net_score, 1)

    scores = {
        "concept_validity": concept_score,
        "granularity": granularity_score,
        "evidence_preservation": evidence_score,
        "assignment_quality": assignment_score,
        "pruning_review_quality": pruning_review_score,
        "coverage_criteria": criteria_score,
        "lesson_coherence": coherence_score,
        "net_phase4_benefit": net_score,
    }
    return {
        "artifact_type": "lesson_reconciliation_quality_audit",
        "schema_version": "lesson_reconciliation_quality_audit.v0",
        "generated_at": _now(),
        "lesson_id": artifact.get("lesson_id"),
        "lesson": lesson,
        "scores": scores,
        "reliability": "repair_required" if net_score <= 1 else "reliable",
        "flags": flags,
        "metrics": {
            "input_candidate_count": input_count,
            "reconciled_candidate_count": reconciled_count,
            "pruned_candidate_count": pruned_count,
            "review_count": review_count,
            "deterministic_review_count": deterministic_review_count,
            "near_duplicate_pruned_count": len(near_duplicate_pruned_ids),
            "merged_assignment_count": merged_assignment_count,
            "largest_reconciled_source_count": len(largest_reconciled_source_ids),
            "duplicate_accepted_label_group_count": duplicate_label_groups,
            "metadata_only_accepted_count": metadata_only_accepted_count,
            "off_lesson_accepted_count": len(off_lesson_accepted_candidate_ids),
            "accepted_candidate_assignment_count": len(accepted_candidate_ids),
            "source_body_candidate_count": source_body_candidate_count,
            "assignment_count": assignment_count,
            "accepted_ratio": round(accepted_ratio, 4),
            "pruned_ratio": round(pruned_ratio, 4),
            "merged_ratio": round(merged_ratio, 4),
            "metadata_only_accepted_ratio": round(metadata_only_accepted_ratio, 4),
            "review_ratio": round(review_ratio, 4),
        },
        "repair_plan": repair_plan,
    }


def _all_reconciled_candidates_have_criteria(artifact: dict[str, Any]) -> bool:
    return all(
        _non_empty_string_list(candidate.get("coverage_criteria"))
        for candidate in artifact.get("reconciled_candidates") or []
        if isinstance(candidate, dict)
    )


def _candidate_ref_to_compact_id(entries: dict[str, dict[str, Any]], candidate_ref: dict[str, Any]) -> str | None:
    original_candidate_id = candidate_ref.get("candidate_id")
    self_study_id = candidate_ref.get("self_study_id")
    artifact_path = candidate_ref.get("artifact_path")
    for candidate_id, entry in entries.items():
        ref = entry.get("candidate_ref") or {}
        if (
            ref.get("candidate_id") == original_candidate_id
            and ref.get("self_study_id") == self_study_id
            and ref.get("artifact_path") == artifact_path
        ):
            return candidate_id
    return None


def _normalize_concept_text(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
    return re.sub(r"\s+", " ", text)


def _looks_like_off_lesson_accepted_concept(candidate: dict[str, Any]) -> bool:
    text = _normalize_concept_text(
        " ".join(
            str(candidate.get(field) or "")
            for field in ("label", "description", "merge_rationale")
        )
    )
    off_lesson_markers = (
        "pip",
        "install",
        "installation",
        "setup",
        "environment",
        "github",
        "git",
        "repository",
        "repo",
        "license",
        "licensing",
        "career",
        "certificate",
        "certification",
        "download",
        "dataset download",
        "file io",
        "instalacao",
        "instalar",
        "ambiente",
        "repositorio",
        "licenca",
        "carreira",
        "certificado",
        "baixar",
    )
    return any(re.search(rf"\b{re.escape(marker)}\b", text) for marker in off_lesson_markers)


def _existing_valid_phase4b_repair_decision(
    *,
    artifact_path: Path,
    target_candidate_ids: list[str],
    artifact: dict[str, Any],
) -> dict[str, Any] | None:
    if not artifact_path.is_file():
        return None
    try:
        decision = _read_json(artifact_path)
    except json.JSONDecodeError:
        return None
    errors = validate_phase4b_repair_decision(
        decision,
        target_candidate_ids=target_candidate_ids,
        artifact=artifact,
    )
    return None if errors else decision


def _existing_valid_lesson_candidate_clusters(
    *,
    artifact_path: Path,
    registry: dict[str, Any],
    model_route: str,
) -> dict[str, Any] | None:
    if not artifact_path.is_file():
        return None
    try:
        artifact = _read_json(artifact_path)
    except json.JSONDecodeError:
        return None
    errors = validate_lesson_candidate_clusters_artifact(
        artifact,
        registry=registry,
        model_route=model_route,
    )
    return None if errors else artifact


def _existing_valid_cluster_evaluation_decision(
    *,
    artifact_path: Path,
    registry: dict[str, Any],
    model_route: str,
) -> dict[str, Any] | None:
    if not artifact_path.is_file():
        return None
    try:
        artifact = _read_json(artifact_path)
    except json.JSONDecodeError:
        return None
    if artifact.get("model_route") != model_route:
        return None
    errors = validate_reduce_decision(artifact, registry)
    return None if errors else artifact


def validate_lesson_candidate_clustering_decision(
    artifact: dict[str, Any],
    registry: dict[str, Any],
) -> list[str]:
    errors = _validate_lesson_candidate_cluster_shape(
        artifact,
        artifact_type="lesson_candidate_clustering_decision",
        schema_version="lesson_candidate_clustering_decision.v0",
        registry=registry,
    )
    summary = artifact.get("summary") or {}
    clusters = artifact.get("clusters") if isinstance(artifact.get("clusters"), list) else []
    input_ids = artifact.get("input_candidate_ids") if isinstance(artifact.get("input_candidate_ids"), list) else []
    if summary.get("input_candidate_count") != len(input_ids):
        errors.append(
            "lesson_candidate_clustering_decision.summary.input_candidate_count does not match input_candidate_ids length"
        )
    if summary.get("cluster_count") != len(clusters):
        errors.append("lesson_candidate_clustering_decision.summary.cluster_count does not match clusters length")
    return errors


def validate_lesson_candidate_clusters_artifact(
    artifact: dict[str, Any],
    *,
    registry: dict[str, Any],
    model_route: str | None = None,
) -> list[str]:
    errors = _validate_lesson_candidate_cluster_shape(
        artifact,
        artifact_type="lesson_candidate_clusters",
        schema_version="lesson_candidate_clusters.v0",
        registry=registry,
    )
    if model_route is not None and artifact.get("model_route") != model_route:
        errors.append("lesson_candidate_clusters.model_route must match expected route")
    return errors


def _validate_lesson_candidate_cluster_shape(
    artifact: dict[str, Any],
    *,
    artifact_type: str,
    schema_version: str,
    registry: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if artifact.get("artifact_type") != artifact_type:
        errors.append(f"{artifact_type}.artifact_type must be '{artifact_type}'")
    if artifact.get("schema_version") != schema_version:
        errors.append(f"{artifact_type}.schema_version must be '{schema_version}'")
    if artifact.get("lesson_id") != registry.get("scope_id"):
        errors.append(f"{artifact_type}.lesson_id must match registry.scope_id")

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


def validate_lesson_reconciliation_artifact(
    artifact: dict[str, Any],
    *,
    lesson_id: str | None = None,
    model_route: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if artifact.get("artifact_type") != "lesson_reconciliation":
        errors.append("lesson_reconciliation.artifact_type must be 'lesson_reconciliation'")
    if artifact.get("schema_version") != "lesson_reconciliation.v0":
        errors.append("lesson_reconciliation.schema_version must be 'lesson_reconciliation.v0'")
    if lesson_id is not None and artifact.get("lesson_id") != lesson_id:
        errors.append("lesson_reconciliation.lesson_id must match expected lesson")
    if model_route is not None and artifact.get("model_route") != model_route:
        errors.append("lesson_reconciliation.model_route must match expected route")
    candidates = artifact.get("reconciled_candidates")
    if not isinstance(candidates, list):
        errors.append("lesson_reconciliation.reconciled_candidates must be a list")
        candidates = []
    candidate_ids = set()
    for index, candidate in enumerate(candidates):
        location = f"reconciled_candidates[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{location} must be an object")
            continue
        candidate_id = str(candidate.get("reconciled_candidate_id") or "")
        if not candidate_id:
            errors.append(f"{location}.reconciled_candidate_id is required")
        elif candidate_id in candidate_ids:
            errors.append(f"{location}.reconciled_candidate_id is duplicated")
        candidate_ids.add(candidate_id)
        for field in ("label", "description", "merge_rationale"):
            if not str(candidate.get(field) or "").strip():
                errors.append(f"{location}.{field} is required")
        if not _non_empty_string_list(candidate.get("coverage_criteria")):
            errors.append(f"{location}.coverage_criteria must contain at least one string")
        if not isinstance(candidate.get("source_candidate_ids"), list) or not candidate.get("source_candidate_ids"):
            errors.append(f"{location}.source_candidate_ids must contain at least one candidate ID")
        if not isinstance(candidate.get("evidence"), list) or not candidate.get("evidence"):
            errors.append(f"{location}.evidence must contain at least one evidence reference")
    summary = artifact.get("summary") or {}
    if summary.get("reconciled_candidate_count") != len(candidates):
        errors.append("lesson_reconciliation.summary.reconciled_candidate_count does not match candidates length")
    return errors


def validate_phase4b_repair_decision(
    decision: dict[str, Any],
    *,
    target_candidate_ids: list[str],
    artifact: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if decision.get("artifact_type") != "lesson_reconciliation_quality_repair_decision":
        errors.append(
            "lesson_reconciliation_quality_repair_decision.artifact_type must be "
            "'lesson_reconciliation_quality_repair_decision'"
        )
    if decision.get("schema_version") != "lesson_reconciliation_quality_repair_decision.v0":
        errors.append(
            "lesson_reconciliation_quality_repair_decision.schema_version must be "
            "'lesson_reconciliation_quality_repair_decision.v0'"
        )
    target_set = set(target_candidate_ids)
    assignments = decision.get("candidate_assignments")
    if not isinstance(assignments, list):
        errors.append("lesson_reconciliation_quality_repair_decision.candidate_assignments must be a list")
        assignments = []
    assigned_ids: list[str] = []
    new_ids = {
        str(accepted.get("id") or "")
        for accepted in decision.get("new_accepted_concepts") or []
        if isinstance(accepted, dict)
    }
    existing_ids = {
        str(candidate.get("reconciled_candidate_id") or "")
        for candidate in artifact.get("reconciled_candidates") or []
        if isinstance(candidate, dict)
    }
    for index, assignment in enumerate(assignments):
        location = f"candidate_assignments[{index}]"
        if not isinstance(assignment, dict):
            errors.append(f"{location} must be an object")
            continue
        candidate_id = str(assignment.get("candidate_id") or "")
        if candidate_id not in target_set:
            errors.append(f"{location}.candidate_id must be one of the target candidates")
        assigned_ids.append(candidate_id)
        status = assignment.get("status")
        if status == "review":
            errors.append(f"{location}.status must not be review")
        elif status in {"used_in", "merged_into"}:
            accepted_ids = assignment.get("accepted_ids")
            if status == "merged_into":
                accepted_ids = [assignment.get("merged_into")]
            if not isinstance(accepted_ids, list) or not accepted_ids:
                errors.append(f"{location} must reference an accepted concept")
            else:
                for accepted_id in accepted_ids:
                    if str(accepted_id) not in new_ids and str(accepted_id) not in existing_ids:
                        errors.append(f"{location} references unknown accepted concept {accepted_id}")
        elif status == "pruned":
            if assignment.get("reason") not in _controlled_pruning_reasons():
                errors.append(f"{location}.reason must be a controlled pruning reason")
        else:
            errors.append(f"{location}.status must be used_in, merged_into, or pruned")
    missing = sorted(target_set - set(assigned_ids))
    if missing:
        errors.append("lesson_reconciliation_quality_repair_decision must assign every target candidate: " + ", ".join(missing))
    duplicated = _duplicates(assigned_ids)
    if duplicated:
        errors.append("lesson_reconciliation_quality_repair_decision assigns candidates more than once: " + ", ".join(duplicated))
    for index, accepted in enumerate(decision.get("new_accepted_concepts") or []):
        location = f"new_accepted_concepts[{index}]"
        if not isinstance(accepted, dict):
            errors.append(f"{location} must be an object")
            continue
        for field in ("id", "label", "description", "merge_rationale"):
            if not str(accepted.get(field) or "").strip():
                errors.append(f"{location}.{field} is required")
        if not _non_empty_string_list(accepted.get("coverage_criteria")):
            errors.append(f"{location}.coverage_criteria must contain at least one string")
        source_candidate_ids = accepted.get("source_candidate_ids")
        if not isinstance(source_candidate_ids, list) or not source_candidate_ids:
            errors.append(f"{location}.source_candidate_ids must contain target candidate IDs")
        elif any(candidate_id not in target_set for candidate_id in source_candidate_ids):
            errors.append(f"{location}.source_candidate_ids must only contain target candidate IDs")
    return errors


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


def _clean_phase_four_artifacts(*, run_dir: Path, source_ledger: dict[str, Any]) -> None:
    for relative_path in ("lesson_reconciliation_summary.json",):
        path = run_dir / relative_path
        if path.exists():
            path.unlink()
    for lesson in source_ledger.get("lessons") or []:
        lesson_id = str(lesson.get("lesson_id") or "")
        lesson_dir = run_dir / "lessons" / lesson_id
        for relative_path in (
            "semantic_reduce_candidate_registry.json",
            "lesson_reconciliation_input.json",
            "lesson_reconciliation_decision.json",
            "lesson_reconciliation.json",
            "lesson_candidate_clustering_input.json",
            "lesson_candidate_clustering_decision.json",
            "lesson_candidate_clusters.json",
            "lesson_reconciliation_quality_audit.json",
            "stage_progress.jsonl",
        ):
            path = lesson_dir / relative_path
            if path.exists():
                path.unlink()
        cluster_evaluation_dir = lesson_dir / "cluster_evaluations"
        if cluster_evaluation_dir.is_dir():
            shutil.rmtree(cluster_evaluation_dir)
        raw_output_dir = lesson_dir / "raw_model_outputs" / "lesson_reconciliation"
        if raw_output_dir.is_dir():
            shutil.rmtree(raw_output_dir)
        clustering_raw_output_dir = lesson_dir / "raw_model_outputs" / "lesson_candidate_clustering"
        if clustering_raw_output_dir.is_dir():
            shutil.rmtree(clustering_raw_output_dir)
        phase4b_repair_dir = lesson_dir / "phase4b_repairs"
        if phase4b_repair_dir.is_dir():
            shutil.rmtree(phase4b_repair_dir)
        phase4b_raw_output_dir = lesson_dir / "raw_model_outputs" / "lesson_reconciliation_quality_repair"
        if phase4b_raw_output_dir.is_dir():
            shutil.rmtree(phase4b_raw_output_dir)


def _clean_phase_four_b_artifacts(*, lesson_dir: Path) -> None:
    for relative_path in ("lesson_reconciliation_quality_audit.json",):
        path = lesson_dir / relative_path
        if path.exists():
            path.unlink()
    phase4b_repair_dir = lesson_dir / "phase4b_repairs"
    if phase4b_repair_dir.is_dir():
        shutil.rmtree(phase4b_repair_dir)
    phase4b_raw_output_dir = lesson_dir / "raw_model_outputs" / "lesson_reconciliation_quality_repair"
    if phase4b_raw_output_dir.is_dir():
        shutil.rmtree(phase4b_raw_output_dir)


def _non_empty_string_list(value: Any) -> bool:
    return isinstance(value, list) and any(isinstance(item, str) and item.strip() for item in value)


def assemble_lesson_reconciliation(
    *,
    lesson_id: str,
    registry: dict[str, Any],
    decision: dict[str, Any],
    decision_artifact_path: str,
    registry_artifact_path: str,
    lesson_candidate_clusters_artifact: str | None = None,
    cluster_evaluation_decision_artifacts: list[str] | None = None,
) -> dict[str, Any]:
    entries = registry.get("candidates") or {}
    reconciled_candidates = []
    final_id_by_reduce_id: dict[str, str] = {}
    final_id_by_source_candidate_id: dict[str, str] = {}

    for index, accepted in enumerate(decision.get("accepted_concepts") or [], start=1):
        local_id = str(accepted.get("id") or "")
        final_id = f"reconciled-candidate-{lesson_id}-{index:03d}"
        final_id_by_reduce_id[local_id] = final_id
        source_candidate_ids = [str(item) for item in accepted.get("source_candidate_ids") or []]
        for source_candidate_id in source_candidate_ids:
            final_id_by_source_candidate_id[source_candidate_id] = final_id
        reconciled_candidates.append(
            {
                "reconciled_candidate_id": final_id,
                "label": accepted.get("label"),
                "description": accepted.get("description"),
                "coverage_criteria": accepted.get("coverage_criteria") or [],
                "source_candidate_ids": source_candidate_ids,
                "merge_rationale": accepted.get("merge_rationale"),
                "source_roles": _union_from_entries(entries, source_candidate_ids, "source_roles"),
                "evidence_types": _union_from_entries(entries, source_candidate_ids, "evidence_type"),
                "evidence": [_evidence_ref(entries[source_candidate_id]) for source_candidate_id in source_candidate_ids],
            }
        )

    pruned_candidates = []
    review_candidates = []
    for assignment in decision.get("candidate_assignments") or []:
        candidate_id = str(assignment.get("candidate_id") or "")
        entry = entries.get(candidate_id)
        if not entry:
            continue
        status = assignment.get("status")
        if status == "pruned":
            pruned_candidates.append(
                {
                    "candidate_ref": _candidate_ref(entry),
                    "pruning_reason": assignment.get("reason"),
                    "explanation": assignment.get("explanation"),
                }
            )
        elif status == "review":
            review_candidates.append(
                {
                    "candidate_ref": _candidate_ref(entry),
                    "explanation": assignment.get("explanation"),
                }
            )
        elif status == "merged_into":
            target = str(assignment.get("merged_into") or "")
            final_target = final_id_by_reduce_id.get(target)
            if not final_target:
                final_target = final_id_by_source_candidate_id.get(candidate_id)
            if final_target:
                assignment["merged_into_reconciled_candidate_id"] = final_target

    return {
        "artifact_type": "lesson_reconciliation",
        "schema_version": "lesson_reconciliation.v0",
        "generated_at": _now(),
        "source_artifact": "source_ledger.json",
        "candidate_registry_artifact": registry_artifact_path,
        "semantic_reduce_decision_artifact": decision_artifact_path,
        "lesson_candidate_clusters_artifact": lesson_candidate_clusters_artifact,
        "cluster_evaluation_decision_artifacts": cluster_evaluation_decision_artifacts or [],
        "model_route": decision.get("model_route"),
        "lesson_id": lesson_id,
        "input_candidate_refs": [_candidate_ref(entry) for entry in entries.values()],
        "reconciled_candidates": reconciled_candidates,
        "candidate_assignments": decision.get("candidate_assignments") or [],
        "pruned_candidates": pruned_candidates,
        "review_candidates": review_candidates,
        "summary": {
            "input_candidate_count": len(entries),
            "reconciled_candidate_count": len(reconciled_candidates),
            "pruned_candidate_count": len(pruned_candidates),
            "review_candidate_count": len(review_candidates),
        },
    }


def _apply_phase4b_repair_decision(
    *,
    artifact: dict[str, Any],
    registry: dict[str, Any],
    decision: dict[str, Any],
    target_candidate_ids: list[str],
) -> dict[str, Any]:
    repaired = json.loads(json.dumps(artifact, ensure_ascii=False))
    entries = registry.get("candidates") or {}
    target_set = set(target_candidate_ids)
    next_index = len(repaired.get("reconciled_candidates") or []) + 1
    repair_id_to_final_id: dict[str, str] = {}

    repaired["review_candidates"] = [
        item
        for item in repaired.get("review_candidates") or []
        if _candidate_ref_to_compact_id(entries, item.get("candidate_ref") or {}) not in target_set
    ]
    repaired["pruned_candidates"] = [
        item
        for item in repaired.get("pruned_candidates") or []
        if _candidate_ref_to_compact_id(entries, item.get("candidate_ref") or {}) not in target_set
    ]
    repaired["candidate_assignments"] = [
        assignment
        for assignment in repaired.get("candidate_assignments") or []
        if not isinstance(assignment, dict) or assignment.get("candidate_id") not in target_set
    ]
    _remove_candidates_from_reconciled_candidates(
        repaired,
        entries=entries,
        candidate_ids=target_set,
    )

    for accepted in decision.get("new_accepted_concepts") or []:
        if not isinstance(accepted, dict):
            continue
        local_id = str(accepted.get("id") or f"repair{next_index:03d}")
        final_id = f"reconciled-candidate-{artifact.get('lesson_id')}-{next_index:03d}"
        repair_id_to_final_id[local_id] = final_id
        source_candidate_ids = [
            candidate_id
            for candidate_id in accepted.get("source_candidate_ids") or []
            if isinstance(candidate_id, str) and candidate_id in entries
        ]
        repaired.setdefault("reconciled_candidates", []).append(
            {
                "reconciled_candidate_id": final_id,
                "label": accepted.get("label"),
                "description": accepted.get("description"),
                "coverage_criteria": accepted.get("coverage_criteria") or [],
                "source_candidate_ids": source_candidate_ids,
                "merge_rationale": accepted.get("merge_rationale"),
                "source_roles": _union_from_entries(entries, source_candidate_ids, "source_roles"),
                "evidence_types": _union_from_entries(entries, source_candidate_ids, "evidence_type"),
                "evidence": [_evidence_ref(entries[candidate_id]) for candidate_id in source_candidate_ids],
            }
        )
        next_index += 1

    for addition in decision.get("existing_concept_candidate_additions") or []:
        if not isinstance(addition, dict):
            continue
        final_id = str(addition.get("reconciled_candidate_id") or "")
        candidate_ids = [
            candidate_id
            for candidate_id in addition.get("candidate_ids") or []
            if isinstance(candidate_id, str) and candidate_id in entries
        ]
        _add_candidates_to_reconciled_candidate(repaired, entries=entries, final_id=final_id, candidate_ids=candidate_ids)

    for assignment in decision.get("candidate_assignments") or []:
        if not isinstance(assignment, dict):
            continue
        candidate_id = str(assignment.get("candidate_id") or "")
        if candidate_id not in entries:
            continue
        status = assignment.get("status")
        if status == "pruned":
            repaired.setdefault("candidate_assignments", []).append(
                {
                    "candidate_id": candidate_id,
                    "status": "pruned",
                    "reason": assignment.get("reason"),
                    "explanation": assignment.get("explanation"),
                }
            )
            repaired.setdefault("pruned_candidates", []).append(
                {
                    "candidate_ref": _candidate_ref(entries[candidate_id]),
                    "pruning_reason": assignment.get("reason"),
                    "explanation": assignment.get("explanation"),
                }
            )
            continue
        if status in {"used_in", "merged_into"}:
            accepted_ids = assignment.get("accepted_ids")
            if status == "merged_into":
                accepted_ids = [assignment.get("merged_into")]
            final_ids = [
                repair_id_to_final_id.get(str(accepted_id), str(accepted_id))
                for accepted_id in accepted_ids or []
                if accepted_id
            ]
            for final_id in final_ids:
                _add_candidates_to_reconciled_candidate(
                    repaired,
                    entries=entries,
                    final_id=final_id,
                    candidate_ids=[candidate_id],
                )
            repaired.setdefault("candidate_assignments", []).append(
                {
                    "candidate_id": candidate_id,
                    "status": "used_in" if status == "used_in" else "merged_into",
                    "accepted_ids": final_ids if status == "used_in" else None,
                    "merged_into": final_ids[0] if status == "merged_into" and final_ids else None,
                    "explanation": assignment.get("explanation"),
                }
            )
    for assignment in repaired.get("candidate_assignments") or []:
        if isinstance(assignment, dict):
            if assignment.get("accepted_ids") is None:
                assignment.pop("accepted_ids", None)
            if assignment.get("merged_into") is None:
                assignment.pop("merged_into", None)
            if assignment.get("explanation") is None:
                assignment.pop("explanation", None)

    repaired["summary"] = {
        "input_candidate_count": len(entries),
        "reconciled_candidate_count": len(repaired.get("reconciled_candidates") or []),
        "pruned_candidate_count": len(repaired.get("pruned_candidates") or []),
        "review_candidate_count": len(repaired.get("review_candidates") or []),
    }
    return repaired


def _remove_candidates_from_reconciled_candidates(
    artifact: dict[str, Any],
    *,
    entries: dict[str, dict[str, Any]],
    candidate_ids: set[str],
) -> None:
    kept_candidates = []
    for candidate in artifact.get("reconciled_candidates") or []:
        if not isinstance(candidate, dict):
            kept_candidates.append(candidate)
            continue
        source_candidate_ids = [
            candidate_id
            for candidate_id in candidate.get("source_candidate_ids") or []
            if isinstance(candidate_id, str) and candidate_id not in candidate_ids
        ]
        if not source_candidate_ids:
            continue
        candidate["source_candidate_ids"] = source_candidate_ids
        candidate["evidence"] = [
            evidence
            for evidence in candidate.get("evidence") or []
            if _candidate_ref_to_compact_id(entries, evidence.get("candidate_ref") or {}) not in candidate_ids
        ]
        candidate["source_roles"] = _union_from_entries(entries, source_candidate_ids, "source_roles")
        candidate["evidence_types"] = _union_from_entries(entries, source_candidate_ids, "evidence_type")
        kept_candidates.append(candidate)
    artifact["reconciled_candidates"] = kept_candidates


def _add_candidates_to_reconciled_candidate(
    artifact: dict[str, Any],
    *,
    entries: dict[str, dict[str, Any]],
    final_id: str,
    candidate_ids: list[str],
) -> None:
    for candidate in artifact.get("reconciled_candidates") or []:
        if not isinstance(candidate, dict) or candidate.get("reconciled_candidate_id") != final_id:
            continue
        existing_source_ids = candidate.setdefault("source_candidate_ids", [])
        existing_evidence_refs = {
            ((item.get("candidate_ref") or {}).get("artifact_path"), (item.get("candidate_ref") or {}).get("candidate_id"))
            for item in candidate.setdefault("evidence", [])
            if isinstance(item, dict)
        }
        for candidate_id in candidate_ids:
            if candidate_id not in existing_source_ids:
                existing_source_ids.append(candidate_id)
            evidence = _evidence_ref(entries[candidate_id])
            evidence_key = (
                (evidence.get("candidate_ref") or {}).get("artifact_path"),
                (evidence.get("candidate_ref") or {}).get("candidate_id"),
            )
            if evidence_key not in existing_evidence_refs:
                candidate.setdefault("evidence", []).append(evidence)
                existing_evidence_refs.add(evidence_key)
        candidate["source_roles"] = _union_from_entries(entries, existing_source_ids, "source_roles")
        candidate["evidence_types"] = _union_from_entries(entries, existing_source_ids, "evidence_type")
        return


def _normalize_lesson_decision_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    model_input = inputs["lesson_reconciliation_input.json"]
    return normalize_decision_output(
        raw=raw,
        scope_id=str((model_input.get("scope") or {}).get("id") or ""),
        stage_name="lesson_reconciliation",
        model_route=str(model_input.get("model_route") or PRO_THINKING_ROUTE_ALIAS),
        input_candidate_ids=model_input.get("input_candidate_ids") or [],
    )


def _lesson_candidate_sources(
    *,
    run_dir: Path,
    lesson_id: str,
    self_studies: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    for self_study in self_studies:
        self_study_id = str(self_study.get("self_study_id") or "")
        self_study_dir = run_dir / "lessons" / lesson_id / "self_studies" / self_study_id
        extraction_set_path = self_study_dir / "self_study_extraction_set.json"
        if extraction_set_path.is_file():
            extraction_set = _read_json(extraction_set_path)
            for extraction_pass in extraction_set.get("extraction_passes") or []:
                artifact_path = run_dir / str(extraction_pass.get("artifact_path") or "")
                artifact = _read_json(artifact_path)
                errors = validate_self_study_extraction(artifact)
                if errors:
                    raise StageBlockedError(
                        f"Invalid self-study extraction artifact {artifact_path}: " + "; ".join(errors)
                    )
                route = str(artifact.get("model_route") or extraction_pass.get("route_alias") or "")
                sources.append(
                    {
                        "namespace": f"c{self_study_id}_{_slug(route)}",
                        "artifact_type": "self_study_extraction",
                        "artifact_path": str(artifact_path.relative_to(run_dir)),
                        "lesson_id": lesson_id,
                        "self_study_id": self_study_id,
                        "model_route": route,
                        "pass_id": extraction_pass.get("pass_id"),
                        "evidence_type": "source_body",
                        "source_metadata": {
                            key: value
                            for key, value in {
                                "source_name": artifact.get("source_name")
                                or (self_study.get("workbook_metadata") or {}).get("title"),
                                "source_year": artifact.get("source_year"),
                            }.items()
                            if value is not None
                        },
                        "candidates": artifact.get("candidate_concepts") or [],
                    }
                )

        metadata_path = self_study_dir / "metadata_only_extraction.json"
        if metadata_path.is_file():
            artifact = _read_json(metadata_path)
            errors = validate_metadata_only_extraction(artifact)
            if errors:
                raise StageBlockedError(
                    f"Invalid metadata-only extraction artifact {metadata_path}: " + "; ".join(errors)
                )
            if artifact.get("excluded") is True:
                continue
            sources.append(
                {
                    "namespace": f"m{self_study_id}",
                    "artifact_type": "metadata_only_extraction",
                    "artifact_path": str(metadata_path.relative_to(run_dir)),
                    "lesson_id": lesson_id,
                    "self_study_id": self_study_id,
                    "model_route": artifact.get("model_route"),
                    "evidence_type": "workbook_metadata",
                    "source_metadata": {
                        "source_name": artifact.get("source_name")
                        or (self_study.get("workbook_metadata") or {}).get("title"),
                    },
                    "candidates": artifact.get("candidate_concepts") or [],
                }
            )
    return sources


def _compact_lesson(lesson: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": lesson.get("lesson_id"),
        "title": lesson.get("title"),
        "description": lesson.get("description"),
        "date": lesson.get("date"),
        "display_code": lesson.get("display_code"),
    }


def _self_studies_by_lesson(self_studies: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for self_study in self_studies:
        grouped.setdefault(str(self_study.get("lesson_id") or ""), []).append(self_study)
    return grouped


def _evidence_ref(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_ref": _candidate_ref(entry),
        "evidence_type": entry.get("evidence_type"),
        "anchors": entry.get("anchors") or [],
        "extraction_reason": entry.get("extraction_reason") or {},
        "source_metadata": entry.get("source_metadata") or {},
    }


def _candidate_ref(entry: dict[str, Any]) -> dict[str, Any]:
    return dict(entry.get("candidate_ref") or {})


def _union_from_entries(entries: dict[str, dict[str, Any]], candidate_ids: list[str], field: str) -> list[str]:
    values: list[str] = []
    for candidate_id in candidate_ids:
        entry = entries.get(candidate_id) or {}
        value = entry.get(field)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item and item not in values:
                    values.append(item)
        elif isinstance(value, str) and value and value not in values:
                values.append(value)
    return values


def _compact_candidate_view(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": entry.get("compact_id"),
        "label": entry.get("label"),
        "description": entry.get("description"),
        "coverage_criteria": entry.get("coverage_criteria") or [],
        "source_roles": entry.get("source_roles") or [],
        "evidence_type": entry.get("evidence_type"),
        "rationale": {
            str(key): str(value)
            for key, value in (entry.get("extraction_reason") or {}).items()
            if isinstance(value, (str, int, float)) and str(value).strip()
        },
        "anchors": _compact_anchors(entry.get("anchors") or []),
    }


def _compact_anchors(anchors: list[Any]) -> list[str]:
    compact: list[str] = []
    for anchor in anchors[:5]:
        if isinstance(anchor, dict):
            locator = str(anchor.get("locator") or "").strip()
            if locator:
                compact.append(locator)
        elif isinstance(anchor, str) and anchor.strip():
            compact.append(anchor.strip())
    return compact


def _cluster_evaluation_output_contract() -> dict[str, Any]:
    return {
        "accepted_concepts": [
            {
                "id": "cluster-local-id",
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
                "accepted_ids": ["cluster-local-id"],
            },
            {
                "candidate_id": "represented-compact-candidate-id",
                "status": "merged_into",
                "merged_into": "cluster-local-id",
                "explanation": "Why it should not stand alone but is represented by the accepted concept.",
            },
            {
                "candidate_id": "discarded-compact-candidate-id",
                "status": "pruned",
                "reason": "low_teaching_value",
                "explanation": "Why this candidate should not influence the graph.",
            },
            {
                "candidate_id": "discarded-compact-candidate-id",
                "status": "pruned",
                "reason": "unrelated",
                "explanation": "Why this candidate should not influence the graph.",
            },
        ],
        "review_policy": "Do not use review except for structurally impossible inputs; Phase 4b repairs review outputs.",
    }


def _phase4b_repair_output_contract() -> dict[str, Any]:
    return {
        "new_accepted_concepts": [
            {
                "id": "repair-local-id",
                "label": "Specific lesson-local teachable idea",
                "description": "What the student needs to understand.",
                "coverage_criteria": ["Observable check in one to three focused questions."],
                "source_candidate_ids": ["target-compact-candidate-id"],
                "merge_rationale": "Why these target candidates form a concept.",
            }
        ],
        "existing_concept_candidate_additions": [
            {
                "reconciled_candidate_id": "existing-final-reconciled-candidate-id",
                "candidate_ids": ["target-compact-candidate-id"],
                "explanation": "Why the target candidate is represented by this existing concept.",
            }
        ],
        "candidate_assignments": [
            {
                "candidate_id": "target-compact-candidate-id",
                "status": "used_in",
                "accepted_ids": ["repair-local-id"],
                "explanation": "Why this candidate is accepted.",
            },
            {
                "candidate_id": "target-compact-candidate-id",
                "status": "merged_into",
                "merged_into": "existing-final-reconciled-candidate-id",
                "explanation": "Why this candidate is represented by an existing concept.",
            },
            {
                "candidate_id": "target-compact-candidate-id",
                "status": "pruned",
                "reason": "low_teaching_value",
                "explanation": "Why this candidate should not influence the graph.",
            },
        ],
        "forbidden_statuses": ["review"],
    }


def _controlled_pruning_reasons() -> set[str]:
    return {
        "duplicate",
        "near_duplicate",
        "low_teaching_value",
        "incidental",
        "too_narrow",
        "too_broad",
        "unrelated",
        "unsupported_metadata_only",
        "unsupported_lesson_intent",
    }


def _no_web_policy() -> dict[str, Any]:
    return {
        "web_search_allowed": False,
        "instruction": "Do not use web search or open URLs. Use only the provided candidate cards.",
    }


def _cluster_dir_name(cluster_id: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", cluster_id).strip("._")
    return safe or "cluster"


def _cluster_batches(clusters: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    effective_batch_size = max(1, batch_size)
    return [
        clusters[index : index + effective_batch_size]
        for index in range(0, len(clusters), effective_batch_size)
    ]


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicated: list[str] = []
    for value in values:
        if value in seen and value not in duplicated:
            duplicated.append(value)
        seen.add(value)
    return duplicated


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "unknown"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
