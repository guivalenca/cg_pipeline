from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from concept_graph_creation.runtime.model_client import PipelineModelClient
from concept_graph_creation.runtime.stage_runner import (
    FLASH_ROUTE_ALIAS,
    ModelCall,
    ModelRouter,
    PRO_ROUTE_ALIAS,
    PRO_THINKING_ROUTE_ALIAS,
    StageBlockedError,
    StageContract,
    StageRunner,
)
from concept_graph_creation.stages.dependency_deferral import run_dependency_deferral_phase
from concept_graph_creation.stages.final_graph_assembly import run_final_graph_assembly_phase
from concept_graph_creation.stages.source_ledger import (
    build_source_ledger,
    validate_source_ledger,
    write_source_ledger,
)
from concept_graph_creation.stages.metadata_only_extraction import run_metadata_only_extraction_phase
from concept_graph_creation.stages.lesson_reconciliation import run_lesson_reconciliation_phase
from concept_graph_creation.stages.lesson_reconciliation import run_lesson_reconciliation_phase4b
from concept_graph_creation.stages.lesson_segmentation import run_lesson_segmentation_phase
from concept_graph_creation.stages.knowledge_type_classification import run_knowledge_type_classification_phase
from concept_graph_creation.stages.self_study_extraction import run_self_study_extraction_phase
from concept_graph_creation.stages.subject_merge import run_subject_merge_phase
from concept_graph_creation.stages.subject_merge import run_subject_merge_phase5b
from concept_graph_creation.stages.workbook_labels import (
    deterministic_fixture_classifier,
    run_workbook_label_interpretation_stage,
)


def run_pipeline(
    *,
    cg_pipeline_root: Path,
    run_dir: Path,
    workbook_path: Path | None = None,
    index_path: Path | None = None,
    subject_sheet: str,
    course_id: str = "si",
    module_id: str = "mod6",
    subject_id: str | None = None,
    include_validation_failure_demo: bool,
    workbook_label_model_call: ModelCall | None = None,
    self_study_model_call: ModelCall | None = None,
    metadata_only_model_call: ModelCall | None = None,
    lesson_reconciliation_model_call: ModelCall | None = None,
    subject_merge_model_call: ModelCall | None = None,
    lesson_segmentation_model_call: ModelCall | None = None,
    knowledge_type_model_call: ModelCall | None = None,
    deterministic_fixture: bool = False,
    clean_run_dir: bool = True,
    phases: Sequence[str] | None = None,
    phase_three_concurrency: int = 60,
    phase_three_b_concurrency: int = 10,
    phase_four_concurrency: int = 6,
    phase_four_clustering_concurrency: int | None = None,
    phase_four_evaluation_concurrency: int | None = None,
    phase_four_evaluation_batch_size: int = 12,
    phase_four_model_route: str = PRO_ROUTE_ALIAS,
    phase_four_clustering_route: str | None = None,
    phase_four_evaluation_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_four_repair_route: str = FLASH_ROUTE_ALIAS,
    phase_four_contextual_repair_route: str = PRO_ROUTE_ALIAS,
    phase_four_b_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_four_clean: bool = False,
    phase_four_provider_retry_limit: int = 2,
    phase_four_provider_retry_backoff_seconds: float = 10.0,
    phase_five_fine_clustering_concurrency: int = 6,
    phase_five_evaluation_concurrency: int = 6,
    phase_five_evaluation_batch_size: int = 1,
    phase_five_model_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_five_area_partition_route: str | None = None,
    phase_five_fine_clustering_route: str | None = None,
    phase_five_evaluation_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_five_repair_route: str = FLASH_ROUTE_ALIAS,
    phase_five_contextual_repair_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_five_b_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_five_clean: bool = False,
    phase_five_provider_retry_limit: int = 2,
    phase_five_provider_retry_backoff_seconds: float = 10.0,
    phase_seven_planner_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_seven_orderer_route: str = PRO_ROUTE_ALIAS,
    phase_seven_audit_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_seven_quality_repair_route: str = PRO_ROUTE_ALIAS,
    phase_seven_concurrency: int = 6,
    phase_seven_b_classification_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_seven_b_audit_route: str = PRO_THINKING_ROUTE_ALIAS,
    phase_seven_b_quality_repair_route: str = PRO_ROUTE_ALIAS,
    phase_seven_b_concurrency: int = 6,
) -> dict[str, Any]:
    selected_phases = _normalize_phases(phases)
    if clean_run_dir and "phase-2" in selected_phases:
        _reset_run_dir(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    _ensure_run_scaffold(run_dir)

    source_ledger: dict[str, Any] | None = None
    source_ledger_path: Path | None = None
    workbook_label_path: Path | None = None
    workbook_labels: dict[str, Any] | None = None
    self_study_extraction: dict[str, Any] | None = None
    metadata_only_extraction: dict[str, Any] | None = None
    lesson_reconciliation: dict[str, Any] | None = None
    subject_merge: dict[str, Any] | None = None
    dependency_deferral: dict[str, Any] | None = None
    lesson_segmentation: dict[str, Any] | None = None
    knowledge_type_classification: dict[str, Any] | None = None
    final_graph_assembly: dict[str, Any] | None = None

    if "phase-2" in selected_phases:
        source_ledger = build_source_ledger(
            cg_pipeline_root=cg_pipeline_root,
            workbook_path=workbook_path or cg_pipeline_root / "source" / "si_mod6.xlsx",
            index_path=index_path or cg_pipeline_root / "index.json",
            subject_sheet=subject_sheet,
            course_id=course_id,
            module_id=module_id,
            subject_id=subject_id or subject_sheet,
        )
        ledger_errors = validate_source_ledger(source_ledger, cg_pipeline_root=cg_pipeline_root)
        if ledger_errors:
            raise StageBlockedError("Source Ledger validation failed: " + "; ".join(ledger_errors))
        source_ledger_path = write_source_ledger(source_ledger, run_dir / "source_ledger.json")

        workbook_label_result = run_workbook_label_interpretation_stage(
            run_dir=run_dir,
            model_call=workbook_label_model_call
            or (
                _local_workbook_label_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
        )
        workbook_label_path = workbook_label_result.artifact_path
        workbook_labels = json.loads(workbook_label_path.read_text(encoding="utf-8"))
    elif (run_dir / "source_ledger.json").is_file():
        source_ledger_path = run_dir / "source_ledger.json"
        source_ledger = json.loads(source_ledger_path.read_text(encoding="utf-8"))

    if "phase-3" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 3 requires an existing source_ledger.json from Phase 2")
        self_study_extraction = run_self_study_extraction_phase(
            cg_pipeline_root=cg_pipeline_root,
            run_dir=run_dir,
            model_call=self_study_model_call
            or (
                _local_self_study_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
            initial_concurrency=phase_three_concurrency,
        )

    if "phase-3b" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 3b requires an existing source_ledger.json from Phase 2")
        metadata_only_extraction = run_metadata_only_extraction_phase(
            run_dir=run_dir,
            model_call=metadata_only_model_call
            or (
                _local_metadata_only_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
            model_route=PRO_ROUTE_ALIAS,
            concurrency=phase_three_b_concurrency,
        )

    if "phase-4" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 4 requires an existing source_ledger.json from Phase 2")
        lesson_reconciliation = run_lesson_reconciliation_phase(
            run_dir=run_dir,
            model_call=lesson_reconciliation_model_call
            or (
                _local_lesson_reconciliation_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
            concurrency=phase_four_concurrency,
            clustering_concurrency=phase_four_clustering_concurrency,
            evaluation_concurrency=phase_four_evaluation_concurrency,
            evaluation_batch_size=phase_four_evaluation_batch_size,
            model_route=phase_four_clustering_route or phase_four_model_route,
            evaluation_model_route=phase_four_evaluation_route,
            repair_model_route=phase_four_repair_route,
            contextual_repair_model_route=phase_four_contextual_repair_route,
            phase4b_model_route=phase_four_b_route,
            clean_phase_artifacts=phase_four_clean,
            provider_retry_limit=phase_four_provider_retry_limit,
            provider_retry_backoff_seconds=phase_four_provider_retry_backoff_seconds,
        )

    if "phase-4b" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 4b requires an existing source_ledger.json from Phase 2")
        lesson_reconciliation = run_lesson_reconciliation_phase4b(
            run_dir=run_dir,
            model_call=lesson_reconciliation_model_call
            or (
                _local_lesson_reconciliation_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
            repair_model_route=phase_four_repair_route,
            contextual_repair_model_route=phase_four_contextual_repair_route,
            phase4b_model_route=phase_four_b_route,
            provider_retry_limit=phase_four_provider_retry_limit,
            provider_retry_backoff_seconds=phase_four_provider_retry_backoff_seconds,
        )

    if "phase-5" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 5 requires an existing source_ledger.json from Phase 2")
        subject_merge = run_subject_merge_phase(
            run_dir=run_dir,
            model_call=subject_merge_model_call
            or (
                _local_subject_merge_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
            model_route=phase_five_model_route,
            area_partition_model_route=phase_five_area_partition_route,
            fine_clustering_model_route=phase_five_fine_clustering_route,
            evaluation_model_route=phase_five_evaluation_route,
            repair_model_route=phase_five_repair_route,
            contextual_repair_model_route=phase_five_contextual_repair_route,
            phase5b_model_route=phase_five_b_route,
            fine_clustering_concurrency=phase_five_fine_clustering_concurrency,
            evaluation_concurrency=phase_five_evaluation_concurrency,
            evaluation_batch_size=phase_five_evaluation_batch_size,
            clean_phase_artifacts=phase_five_clean,
            provider_retry_limit=phase_five_provider_retry_limit,
            provider_retry_backoff_seconds=phase_five_provider_retry_backoff_seconds,
        )

    if "phase-5b" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 5b requires an existing source_ledger.json from Phase 2")
        subject_merge = run_subject_merge_phase5b(
            run_dir=run_dir,
            model_call=subject_merge_model_call
            or (
                _local_subject_merge_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
            repair_model_route=phase_five_repair_route,
            contextual_repair_model_route=phase_five_contextual_repair_route,
            phase5b_model_route=phase_five_b_route,
            provider_retry_limit=phase_five_provider_retry_limit,
            provider_retry_backoff_seconds=phase_five_provider_retry_backoff_seconds,
        )

    if "phase-6" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 6 requires an existing source_ledger.json from Phase 2")
        dependency_deferral = run_dependency_deferral_phase(run_dir=run_dir)

    if "phase-7" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 7 requires an existing source_ledger.json from Phase 2")
        if not (run_dir / "subject_merge.json").is_file():
            raise StageBlockedError("Phase 7 requires an existing subject_merge.json from Phase 5")
        lesson_segmentation = run_lesson_segmentation_phase(
            run_dir=run_dir,
            model_call=lesson_segmentation_model_call
            or (
                _local_lesson_segmentation_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
            planner_model_route=phase_seven_planner_route,
            orderer_model_route=phase_seven_orderer_route,
            audit_model_route=phase_seven_audit_route,
            quality_repair_model_route=phase_seven_quality_repair_route,
            concurrency=phase_seven_concurrency,
        )

    if "phase-7b" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 7b requires an existing source_ledger.json from Phase 2")
        if not (run_dir / "subject_merge.json").is_file():
            raise StageBlockedError("Phase 7b requires an existing subject_merge.json from Phase 5")
        if not (run_dir / "lesson_segmentation_summary.json").is_file():
            raise StageBlockedError("Phase 7b requires an existing lesson_segmentation_summary.json from Phase 7")
        knowledge_type_classification = run_knowledge_type_classification_phase(
            run_dir=run_dir,
            model_call=knowledge_type_model_call
            or (
                _local_knowledge_type_classification_model_call
                if deterministic_fixture
                else PipelineModelClient.from_env(project_root=Path(__file__).resolve().parents[2]).call
            ),
            classification_model_route=phase_seven_b_classification_route,
            audit_model_route=phase_seven_b_audit_route,
            quality_repair_model_route=phase_seven_b_quality_repair_route,
            concurrency=phase_seven_b_concurrency,
        )

    if "phase-8" in selected_phases:
        if source_ledger is None:
            raise StageBlockedError("Phase 8 requires an existing source_ledger.json from Phase 2")
        final_graph_assembly = run_final_graph_assembly_phase(run_dir=run_dir)

    validation_failure_message = None
    if include_validation_failure_demo:
        validation_failure_message = _write_validation_failure_demo(run_dir)

    manual_output = {
        "ok": True,
        "phases": selected_phases,
        "source_ledger_path": str(source_ledger_path) if source_ledger_path else None,
        "workbook_label_interpretation_path": str(workbook_label_path) if workbook_label_path else None,
        "source_ledger_summary": source_ledger["summary"] if source_ledger else None,
        "workbook_label_interpretation_summary": workbook_labels["summary"] if workbook_labels else None,
        "phase_three_summary": self_study_extraction["summary"] if self_study_extraction else None,
        "phase_three_concurrency": self_study_extraction["concurrency"] if self_study_extraction else None,
        "metadata_only_extraction_summary": metadata_only_extraction["summary"] if metadata_only_extraction else None,
        "metadata_only_extraction_concurrency": metadata_only_extraction["concurrency"]
        if metadata_only_extraction
        else None,
        "lesson_reconciliation_summary": lesson_reconciliation["summary"] if lesson_reconciliation else None,
        "lesson_reconciliation_concurrency": lesson_reconciliation["concurrency"]
        if lesson_reconciliation
        else None,
        "lesson_reconciliation_model_route": lesson_reconciliation["model_route"] if lesson_reconciliation else None,
        "lesson_reconciliation_evaluation_model_route": lesson_reconciliation["evaluation_model_route"]
        if lesson_reconciliation
        else None,
        "lesson_reconciliation_repair_route": lesson_reconciliation["repair_model_route"]
        if lesson_reconciliation
        else None,
        "lesson_reconciliation_contextual_repair_route": lesson_reconciliation["contextual_repair_model_route"]
        if lesson_reconciliation
        else None,
        "lesson_reconciliation_stage_concurrency": lesson_reconciliation["stage_concurrency"]
        if lesson_reconciliation
        else None,
        "lesson_reconciliation_evaluation_batch_size": lesson_reconciliation["evaluation_batch_size"]
        if lesson_reconciliation
        else None,
        "lesson_reconciliation_phase4b": lesson_reconciliation["phase4b"] if lesson_reconciliation else None,
        "subject_merge_summary": subject_merge["summary"] if subject_merge else None,
        "subject_merge_model_route": subject_merge["model_route"] if subject_merge and "model_route" in subject_merge else None,
        "subject_merge_evaluation_model_route": subject_merge["evaluation_model_route"]
        if subject_merge and "evaluation_model_route" in subject_merge
        else None,
        "subject_merge_phase5b": subject_merge["phase5b"] if subject_merge and "phase5b" in subject_merge else None,
        "dependency_deferral_summary": dependency_deferral["summary"] if dependency_deferral else None,
        "lesson_segmentation_summary": lesson_segmentation["summary"] if lesson_segmentation else None,
        "lesson_segmentation_planner_route": lesson_segmentation["planner_model_route"]
        if lesson_segmentation
        else None,
        "lesson_segmentation_orderer_route": lesson_segmentation["orderer_model_route"]
        if lesson_segmentation
        else None,
        "lesson_segmentation_audit_route": lesson_segmentation["audit_model_route"] if lesson_segmentation else None,
        "lesson_segmentation_quality_repair_route": lesson_segmentation["quality_repair_model_route"]
        if lesson_segmentation
        else None,
        "lesson_segmentation_concurrency": lesson_segmentation["concurrency"] if lesson_segmentation else None,
        "knowledge_type_classification_summary": knowledge_type_classification["summary"]
        if knowledge_type_classification
        else None,
        "knowledge_type_classification_route": knowledge_type_classification["classification_model_route"]
        if knowledge_type_classification
        else None,
        "knowledge_type_classification_audit_route": knowledge_type_classification["audit_model_route"]
        if knowledge_type_classification
        else None,
        "knowledge_type_classification_quality_repair_route": knowledge_type_classification[
            "quality_repair_model_route"
        ]
        if knowledge_type_classification
        else None,
        "knowledge_type_classification_concurrency": knowledge_type_classification["concurrency"]
        if knowledge_type_classification
        else None,
        "final_graph_assembly_summary": final_graph_assembly["summary"] if final_graph_assembly else None,
        "final_graph_artifact_paths": final_graph_assembly["artifact_paths"] if final_graph_assembly else None,
        "validation_failure_demo": validation_failure_message,
    }
    (run_dir / "run_summary.json").write_text(
        json.dumps(manual_output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "ok": True,
        "source_ledger": source_ledger,
        "workbook_label_interpretation": workbook_labels,
        "self_study_extraction": self_study_extraction,
        "metadata_only_extraction": metadata_only_extraction,
        "lesson_reconciliation": lesson_reconciliation,
        "subject_merge": subject_merge,
        "dependency_deferral": dependency_deferral,
        "lesson_segmentation": lesson_segmentation,
        "knowledge_type_classification": knowledge_type_classification,
        "final_graph_assembly": final_graph_assembly,
        "manual_output": manual_output,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Concept Graph Creation prototype.")
    parser.add_argument("--cg-pipeline-root", type=Path, default=Path(__file__).resolve().parents[3])
    parser.add_argument("--runs-root", type=Path, help="Directory that contains named pipeline runs.")
    parser.add_argument("--run-id", help="Run directory name under --runs-root. Defaults to a UTC timestamp.")
    parser.add_argument("--run-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--workbook-path", type=Path, help="Workbook to parse. Defaults to source/si_mod6.xlsx.")
    parser.add_argument("--index-path", type=Path, help="Extraction index to parse. Defaults to index.json.")
    parser.add_argument("--subject-sheet", default="COM")
    parser.add_argument("--course-id", default="si")
    parser.add_argument("--module-id", default="mod6")
    parser.add_argument("--subject-id", help="Subject id for the ledger. Defaults to --subject-sheet.")
    parser.add_argument(
        "--no-clean-run-dir",
        action="store_true",
        help="Preserve existing files in the run directory before Phase 2 writes its artifacts.",
    )
    parser.add_argument("--validation-failure-demo", action="store_true")
    parser.add_argument(
        "--phase",
        choices=[
            "phase-2",
            "phase-3",
            "phase-3b",
            "phase-4",
            "phase-4b",
            "phase-5",
            "phase-5b",
            "phase-6",
            "phase-7",
            "phase-7b",
            "phase-8",
            "all",
        ],
        default="phase-2",
        help="Run the whole creation system or one independently invokable phase.",
    )
    parser.add_argument(
        "--phase-3-concurrency",
        type=int,
        default=60,
        help=(
            "Initial Self-study Extraction concurrency. Provider pressure backs this down through "
            "60, 50, 40, 30, 25, 20, 16, 14, 8, 6, 4, 2."
        ),
    )
    parser.add_argument(
        "--phase-3b-concurrency",
        type=int,
        default=10,
        help="Metadata-only Extraction worker count.",
    )
    parser.add_argument(
        "--phase-4-concurrency",
        type=int,
        default=6,
        help="Default Lesson Reconciliation worker count for clustering and cluster evaluation.",
    )
    parser.add_argument(
        "--phase-4-clustering-concurrency",
        type=int,
        help="Lesson candidate clustering worker count. Defaults to --phase-4-concurrency.",
    )
    parser.add_argument(
        "--phase-4-evaluation-concurrency",
        type=int,
        help="Lesson cluster evaluation worker count. Defaults to --phase-4-concurrency.",
    )
    parser.add_argument(
        "--phase-4-evaluation-batch-size",
        type=int,
        default=12,
        help="Maximum number of candidate clusters per Lesson cluster evaluation call.",
    )
    parser.add_argument(
        "--phase-4-model-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_ROUTE_ALIAS,
        help="Legacy alias for --phase-4-clustering-route.",
    )
    parser.add_argument(
        "--phase-4-clustering-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        help="Lesson candidate clustering model route.",
    )
    parser.add_argument(
        "--phase-4-evaluation-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Lesson cluster evaluation model route.",
    )
    parser.add_argument(
        "--phase-4-repair-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=FLASH_ROUTE_ALIAS,
        help="Lesson Reconciliation format repair model route.",
    )
    parser.add_argument(
        "--phase-4-contextual-repair-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_ROUTE_ALIAS,
        help="Lesson Reconciliation contextual repair model route.",
    )
    parser.add_argument(
        "--phase-4b-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Lesson Reconciliation quality repair model route.",
    )
    parser.add_argument(
        "--phase-4-clean",
        action="store_true",
        help="Delete existing Phase 4 artifacts before running Lesson Reconciliation.",
    )
    parser.add_argument(
        "--phase-4-provider-retry-limit",
        type=int,
        default=2,
        help="Retries per lesson for transient provider failures.",
    )
    parser.add_argument(
        "--phase-4-provider-retry-backoff-seconds",
        type=float,
        default=10.0,
        help="Base backoff seconds for transient Phase 4 provider retries.",
    )
    parser.add_argument(
        "--phase-5-fine-clustering-concurrency",
        type=int,
        default=6,
        help="Subject Merge fine clustering worker count.",
    )
    parser.add_argument(
        "--phase-5-evaluation-concurrency",
        type=int,
        default=6,
        help="Subject Merge cluster evaluation worker count.",
    )
    parser.add_argument(
        "--phase-5-evaluation-batch-size",
        type=int,
        default=1,
        help="Compatibility option; Subject Merge evaluates one non-singleton cluster per call.",
    )
    parser.add_argument(
        "--phase-5-model-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Legacy default route for Subject Merge area partition and fine clustering.",
    )
    parser.add_argument(
        "--phase-5-area-partition-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        help="Subject Merge area partition model route. Defaults to --phase-5-model-route.",
    )
    parser.add_argument(
        "--phase-5-fine-clustering-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        help="Subject Merge fine clustering model route. Defaults to --phase-5-model-route.",
    )
    parser.add_argument(
        "--phase-5-evaluation-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Subject Merge cluster evaluation model route.",
    )
    parser.add_argument(
        "--phase-5-repair-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=FLASH_ROUTE_ALIAS,
        help="Subject Merge format repair model route.",
    )
    parser.add_argument(
        "--phase-5-contextual-repair-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Subject Merge contextual repair model route.",
    )
    parser.add_argument(
        "--phase-5b-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Subject Merge quality repair model route.",
    )
    parser.add_argument(
        "--phase-5-clean",
        action="store_true",
        help="Delete existing Phase 5 artifacts before running Subject Merge.",
    )
    parser.add_argument(
        "--phase-5-provider-retry-limit",
        type=int,
        default=2,
        help="Retries per Subject Merge call for transient provider failures.",
    )
    parser.add_argument(
        "--phase-5-provider-retry-backoff-seconds",
        type=float,
        default=10.0,
        help="Base backoff seconds for transient Phase 5 provider retries.",
    )
    parser.add_argument(
        "--phase-7-planner-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Lesson Segment Planner model route.",
    )
    parser.add_argument(
        "--phase-7-orderer-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_ROUTE_ALIAS,
        help="Lesson Segment Concept Orderer model route.",
    )
    parser.add_argument(
        "--phase-7-audit-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Lesson Segmentation quality audit model route.",
    )
    parser.add_argument(
        "--phase-7-quality-repair-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_ROUTE_ALIAS,
        help="Lesson Segmentation targeted quality repair model route.",
    )
    parser.add_argument(
        "--phase-7-concurrency",
        type=int,
        default=6,
        help="Lesson Segmentation worker count for per-Lesson calls.",
    )
    parser.add_argument(
        "--phase-7b-classification-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Knowledge Type Classification model route.",
    )
    parser.add_argument(
        "--phase-7b-audit-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_THINKING_ROUTE_ALIAS,
        help="Knowledge Type Classification quality audit model route.",
    )
    parser.add_argument(
        "--phase-7b-quality-repair-route",
        choices=[FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS],
        default=PRO_ROUTE_ALIAS,
        help="Knowledge Type Classification targeted quality repair model route.",
    )
    parser.add_argument(
        "--phase-7b-concurrency",
        type=int,
        default=6,
        help="Knowledge Type Classification worker count for per-Segment calls.",
    )
    parser.add_argument(
        "--deterministic-fixture",
        action="store_true",
        help="Use the local deterministic workbook-label fixture instead of a live DeepSeek call.",
    )
    args = parser.parse_args(argv)

    try:
        runs_root = args.runs_root or args.cg_pipeline_root / "runs"
        run_dir = args.run_dir or runs_root / (args.run_id or _default_run_id())
        result = run_pipeline(
            cg_pipeline_root=args.cg_pipeline_root,
            run_dir=run_dir,
            workbook_path=args.workbook_path,
            index_path=args.index_path,
            subject_sheet=args.subject_sheet,
            course_id=args.course_id,
            module_id=args.module_id,
            subject_id=args.subject_id,
            include_validation_failure_demo=args.validation_failure_demo,
            deterministic_fixture=args.deterministic_fixture,
            clean_run_dir=(
                args.phase
                not in {
                    "phase-3",
                    "phase-3b",
                    "phase-4",
                    "phase-4b",
                    "phase-5",
                    "phase-5b",
                    "phase-6",
                    "phase-7",
                    "phase-7b",
                    "phase-8",
                }
                and not args.no_clean_run_dir
            ),
            phases=[args.phase],
            phase_three_concurrency=args.phase_3_concurrency,
            phase_three_b_concurrency=args.phase_3b_concurrency,
            phase_four_concurrency=args.phase_4_concurrency,
            phase_four_clustering_concurrency=args.phase_4_clustering_concurrency,
            phase_four_evaluation_concurrency=args.phase_4_evaluation_concurrency,
            phase_four_evaluation_batch_size=args.phase_4_evaluation_batch_size,
            phase_four_model_route=args.phase_4_model_route,
            phase_four_clustering_route=args.phase_4_clustering_route,
            phase_four_evaluation_route=args.phase_4_evaluation_route,
            phase_four_repair_route=args.phase_4_repair_route,
            phase_four_contextual_repair_route=args.phase_4_contextual_repair_route,
            phase_four_b_route=args.phase_4b_route,
            phase_four_clean=args.phase_4_clean,
            phase_four_provider_retry_limit=args.phase_4_provider_retry_limit,
            phase_four_provider_retry_backoff_seconds=args.phase_4_provider_retry_backoff_seconds,
            phase_five_fine_clustering_concurrency=args.phase_5_fine_clustering_concurrency,
            phase_five_evaluation_concurrency=args.phase_5_evaluation_concurrency,
            phase_five_evaluation_batch_size=args.phase_5_evaluation_batch_size,
            phase_five_model_route=args.phase_5_model_route,
            phase_five_area_partition_route=args.phase_5_area_partition_route,
            phase_five_fine_clustering_route=args.phase_5_fine_clustering_route,
            phase_five_evaluation_route=args.phase_5_evaluation_route,
            phase_five_repair_route=args.phase_5_repair_route,
            phase_five_contextual_repair_route=args.phase_5_contextual_repair_route,
            phase_five_b_route=args.phase_5b_route,
            phase_five_clean=args.phase_5_clean,
            phase_five_provider_retry_limit=args.phase_5_provider_retry_limit,
            phase_five_provider_retry_backoff_seconds=args.phase_5_provider_retry_backoff_seconds,
            phase_seven_planner_route=args.phase_7_planner_route,
            phase_seven_orderer_route=args.phase_7_orderer_route,
            phase_seven_audit_route=args.phase_7_audit_route,
            phase_seven_quality_repair_route=args.phase_7_quality_repair_route,
            phase_seven_concurrency=args.phase_7_concurrency,
            phase_seven_b_classification_route=args.phase_7b_classification_route,
            phase_seven_b_audit_route=args.phase_7b_audit_route,
            phase_seven_b_quality_repair_route=args.phase_7b_quality_repair_route,
            phase_seven_b_concurrency=args.phase_7b_concurrency,
        )
    except StageBlockedError as exc:
        print(str(exc))
        return 2

    print(json.dumps(result["manual_output"], ensure_ascii=False, indent=2))
    return 0


def _default_run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _ensure_run_scaffold(run_dir: Path) -> None:
    for relative_path in ("lessons", "critics", "repairs"):
        (run_dir / relative_path).mkdir(parents=True, exist_ok=True)


def _normalize_phases(phases: Sequence[str] | None) -> list[str]:
    if not phases:
        return ["phase-2"]
    normalized: list[str] = []
    for phase in phases:
        if phase == "all":
            for expanded in (
                "phase-2",
                "phase-3",
                "phase-3b",
                "phase-4",
                "phase-5",
                "phase-6",
                "phase-7",
                "phase-7b",
                "phase-8",
            ):
                if expanded not in normalized:
                    normalized.append(expanded)
            continue
        if phase not in {
            "phase-2",
            "phase-3",
            "phase-3b",
            "phase-4",
            "phase-4b",
            "phase-5",
            "phase-5b",
            "phase-6",
            "phase-7",
            "phase-7b",
            "phase-8",
        }:
            raise StageBlockedError(f"Unknown creation phase: {phase}")
        if phase not in normalized:
            normalized.append(phase)
    return normalized


def _reset_run_dir(path: Path) -> None:
    resolved = path.resolve()
    if not path.exists():
        return
    if resolved == resolved.parent:
        raise StageBlockedError(f"Refusing to reset unsafe run directory: {path}")
    if resolved.name in {"", ".", ".."}:
        raise StageBlockedError(f"Refusing to reset unsafe run directory: {path}")
    shutil.rmtree(path)


def _write_validation_failure_demo(run_dir: Path) -> str:
    def bad_model_call(**_kwargs: Any) -> str:
        return '{"artifact_type": "wrong"}'

    contract = StageContract(
        name="validation_failure_demo",
        required_inputs=["source_ledger.json"],
        output_artifact="validation_failure_demo.json",
        model_route=PRO_THINKING_ROUTE_ALIAS,
        validator=lambda artifact: []
        if artifact.get("artifact_type") == "validation_failure_demo"
        else ["artifact_type must be validation_failure_demo"],
    )

    try:
        StageRunner(router=ModelRouter.default(), model_call=bad_model_call).run(contract, run_dir=run_dir)
    except StageBlockedError as exc:
        message = str(exc)
        (run_dir / "validation_failure_demo.txt").write_text(message + "\n", encoding="utf-8")
        return message
    raise AssertionError("validation failure demo unexpectedly passed")


def _local_workbook_label_model_call(**kwargs: Any) -> str:
    route = kwargs["route"]
    inputs = kwargs["inputs"]
    model_input = inputs["workbook_label_interpretation_input.json"]
    classifications = []
    contexts_by_label = model_input.get("label_contexts") or {}
    for item in model_input.get("labels_to_classify") or []:
        label = item["label"]
        classification = deterministic_fixture_classifier(label, contexts_by_label.get(label, []))
        classifications.append({"label": label, **classification})
    return json.dumps({"model_route": route.alias, "classifications": classifications}, ensure_ascii=False)


def _local_self_study_model_call(**kwargs: Any) -> str:
    route = kwargs["route"]
    inputs = kwargs["inputs"]
    model_input = inputs["self_study_extraction_input.json"]
    self_study = model_input["self_study"]
    self_study_id = str(self_study["self_study_id"])
    title = self_study["workbook_metadata"]["title"]
    return json.dumps(
        {
            "model_route": route.alias,
            "candidate_concepts": [
                {
                    "candidate_id": f"candidate-{self_study_id}-001",
                    "label": title,
                    "description": "Deterministic source-local candidate for offline pipeline smoke runs.",
                    "coverage_criteria": ["Student can summarize the main teaching signal from this source."],
                    "source_roles": ["introducing"],
                    "extraction_reason": {
                        "source_grounded_rationale": "Offline fixture preserves the assigned source as a candidate.",
                        "granularity_rationale": "One candidate keeps the fixture small while exercising the stage contract.",
                    },
                    "source_anchors": [{"kind": "source_body", "locator": "assigned markdown"}],
                    "evidence_type": "source_body",
                    "source_name": title,
                    "source_year": None,
                    "name_drops": [],
                }
            ],
            "source_local_connector_candidates": [],
        },
        ensure_ascii=False,
    )


def _local_metadata_only_model_call(**kwargs: Any) -> str:
    route = kwargs["route"]
    inputs = kwargs["inputs"]
    model_input = inputs["metadata_only_extraction_input.json"]
    self_study = model_input["self_study"]
    self_study_id = str(self_study["self_study_id"])
    title = self_study["workbook_metadata"]["title"]
    return json.dumps(
        {
            "model_route": route.alias,
            "candidate_concepts": [
                {
                    "candidate_id": f"metadata-candidate-{self_study_id}-001",
                    "label": title,
                    "description": "Deterministic workbook-metadata candidate for offline pipeline smoke runs.",
                    "coverage_criteria": ["Student can summarize the main teaching signal from the workbook row."],
                    "evidence_type": "workbook_metadata",
                    "metadata_anchors": [{"kind": "workbook_title", "locator": "Title"}],
                    "extraction_reason": {
                        "metadata_grounded_rationale": "Offline fixture preserves the workbook row as a candidate.",
                        "granularity_rationale": "One candidate keeps the fixture small while exercising the stage contract.",
                    },
                }
            ],
        },
        ensure_ascii=False,
    )


def _local_lesson_reconciliation_model_call(**kwargs: Any) -> str:
    route = kwargs["route"]
    inputs = kwargs["inputs"]
    if "lesson_candidate_clustering_input.json" in inputs:
        model_input = inputs["lesson_candidate_clustering_input.json"]
        clusters = []
        for index, candidate in enumerate(model_input.get("candidates") or [], start=1):
            candidate_id = str(candidate["id"])
            clusters.append(
                {
                    "id": f"cluster_{index:03d}",
                    "label": candidate.get("label") or f"Lesson candidate cluster {index}",
                    "rationale": "Deterministic fixture keeps each candidate in its own cluster.",
                    "candidate_ids": [candidate_id],
                }
            )
        return json.dumps({"clusters": clusters}, ensure_ascii=False)

    if "lesson_reconciliation_quality_repair_input.json" in inputs:
        model_input = inputs["lesson_reconciliation_quality_repair_input.json"]
        accepted_concepts = []
        candidate_assignments = []
        for index, candidate in enumerate(model_input.get("target_candidates") or [], start=1):
            accepted_id = f"repair{index:03d}"
            candidate_id = str(candidate["id"])
            accepted_concepts.append(
                {
                    "id": accepted_id,
                    "label": candidate.get("label") or f"Repaired lesson concept {index}",
                    "description": candidate.get("description") or "Deterministic repaired lesson concept.",
                    "coverage_criteria": candidate.get("coverage_criteria")
                    or ["Student can explain the repaired lesson-local concept."],
                    "source_candidate_ids": [candidate_id],
                    "merge_rationale": "Deterministic fixture accepts the targeted repair candidate.",
                }
            )
            candidate_assignments.append(
                {
                    "candidate_id": candidate_id,
                    "status": "used_in",
                    "accepted_ids": [accepted_id],
                    "explanation": "Deterministic fixture resolves Phase 4b repair without review.",
                }
            )
        return json.dumps(
            {
                "new_accepted_concepts": accepted_concepts,
                "existing_concept_candidate_additions": [],
                "candidate_assignments": candidate_assignments,
            },
            ensure_ascii=False,
        )

    model_input = inputs["cluster_evaluation_input.json"]
    accepted_concepts = []
    candidate_assignments = []
    for index, candidate in enumerate(model_input.get("candidates") or [], start=1):
        accepted_id = f"lr{index:03d}"
        candidate_id = str(candidate["id"])
        accepted_concepts.append(
            {
                "id": accepted_id,
                "label": candidate.get("label") or f"Lesson concept {index}",
                "description": candidate.get("description") or "Deterministic lesson reconciliation concept.",
                "coverage_criteria": candidate.get("coverage_criteria")
                or ["Student can explain the lesson-local concept."],
                "source_candidate_ids": [candidate_id],
                "merge_rationale": "Deterministic fixture preserves each input candidate as a lesson-local concept.",
            }
        )
        candidate_assignments.append(
            {
                "candidate_id": candidate_id,
                "status": "used_in",
                "accepted_ids": [accepted_id],
            }
        )
    return json.dumps(
        {
            "model_route": route.alias,
            "accepted_concepts": accepted_concepts,
            "candidate_assignments": candidate_assignments,
        },
        ensure_ascii=False,
    )


def _local_subject_merge_model_call(**kwargs: Any) -> str:
    route = kwargs["route"]
    inputs = kwargs["inputs"]
    if "subject_merge_area_partition_input.json" in inputs:
        model_input = inputs["subject_merge_area_partition_input.json"]
        return json.dumps(
            {
                "clusters": [
                    {
                        "id": f"area_{index:03d}",
                        "label": candidate.get("label") or f"Subject area {index}",
                        "rationale": "Deterministic fixture keeps each candidate in its own area.",
                        "candidate_ids": [candidate["id"]],
                    }
                    for index, candidate in enumerate(model_input.get("candidates") or [], start=1)
                ]
            },
            ensure_ascii=False,
        )

    if "subject_merge_fine_clustering_input.json" in inputs:
        model_input = inputs["subject_merge_fine_clustering_input.json"]
        return json.dumps(
            {
                "clusters": [
                    {
                        "id": f"cluster_{index:03d}",
                        "label": candidate.get("label") or f"Subject cluster {index}",
                        "rationale": "Deterministic fixture keeps each candidate as a tight singleton cluster.",
                        "candidate_ids": [candidate["id"]],
                    }
                    for index, candidate in enumerate(model_input.get("candidates") or [], start=1)
                ]
            },
            ensure_ascii=False,
        )

    if "subject_merge_quality_repair_input.json" in inputs:
        model_input = inputs["subject_merge_quality_repair_input.json"]
        accepted_concepts = []
        candidate_assignments = []
        for index, candidate in enumerate(model_input.get("target_candidates") or [], start=1):
            accepted_id = f"repair{index:03d}"
            candidate_id = str(candidate["id"])
            accepted_concepts.append(
                {
                    "id": accepted_id,
                    "label": candidate.get("label") or f"Repaired subject concept {index}",
                    "description": candidate.get("description") or "Deterministic repaired subject concept.",
                    "coverage_criteria": candidate.get("coverage_criteria")
                    or ["Student can explain the repaired subject concept."],
                    "source_candidate_ids": [candidate_id],
                    "merge_rationale": "Deterministic fixture accepts the targeted Phase 5b repair candidate.",
                }
            )
            candidate_assignments.append(
                {
                    "candidate_id": candidate_id,
                    "status": "used_in",
                    "accepted_ids": [accepted_id],
                    "explanation": "Deterministic fixture resolves Phase 5b repair without review.",
                }
            )
        return json.dumps(
            {
                "accepted_concepts": accepted_concepts,
                "candidate_assignments": candidate_assignments,
            },
            ensure_ascii=False,
        )

    if "subject_merge_quality_audit_input.json" in inputs:
        return json.dumps(
            {
                "scores": {
                    "identity_correctness": 3,
                    "granularity_preservation": 3,
                    "provenance_preservation": 3,
                    "assignment_completeness": 3,
                    "overlap_reduction": 3,
                    "subject_coherence": 3,
                    "net_phase5_benefit": 3,
                },
                "reliability": "reliable",
                "flags": [],
                "repair_plan": [],
                "missed_merge_candidates": [],
            },
            ensure_ascii=False,
        )

    model_input = inputs["subject_cluster_evaluation_input.json"]
    accepted_concepts = []
    candidate_assignments = []
    for index, candidate in enumerate(model_input.get("candidates") or [], start=1):
        accepted_id = f"sm{index:03d}"
        candidate_id = str(candidate["id"])
        accepted_concepts.append(
            {
                "id": accepted_id,
                "label": candidate.get("label") or f"Subject concept {index}",
                "description": candidate.get("description") or "Deterministic subject-level concept.",
                "coverage_criteria": candidate.get("coverage_criteria")
                or ["Student can explain the subject-level concept."],
                "source_candidate_ids": [candidate_id],
                "merge_rationale": "Deterministic fixture preserves each lesson-local candidate as a subject concept.",
            }
        )
        candidate_assignments.append(
            {
                "candidate_id": candidate_id,
                "status": "used_in",
                "accepted_ids": [accepted_id],
            }
        )
    return json.dumps(
        {
            "model_route": route.alias,
            "accepted_concepts": accepted_concepts,
            "candidate_assignments": candidate_assignments,
        },
        ensure_ascii=False,
    )


def _local_lesson_segmentation_model_call(**kwargs: Any) -> str:
    inputs = kwargs["inputs"]
    stage_name = kwargs["stage_name"]
    if stage_name == "lesson_segment_planner":
        model_input = inputs["lesson_segment_planner_input.json"]
        concepts = model_input.get("concepts") or []
        segments = []
        for index in range(0, len(concepts), 4):
            chunk = concepts[index : index + 4]
            first = chunk[0]["label"] if chunk else "Segment"
            segments.append(
                {
                    "label": first if len(chunk) == 1 else f"{first} and related ideas",
                    "concept_ids": [concept["concept_id"] for concept in chunk],
                }
            )
        return json.dumps({"segments": segments}, ensure_ascii=False)

    if stage_name == "lesson_segment_concept_orderer":
        model_input = inputs["lesson_segment_concept_orderer_input.json"]
        return json.dumps({"segments": model_input.get("segments") or []}, ensure_ascii=False)

    if stage_name == "lesson_segmentation_quality_audit":
        return json.dumps(
            {
                "scores": {
                    "segment_coherence": 3,
                    "segment_order": 3,
                    "concept_order": 3,
                    "label_quality": 3,
                    "focus_window_size": 3,
                },
                "reliability": "reliable",
                "findings": [],
                "repair_instructions": [],
            },
            ensure_ascii=False,
        )

    if stage_name == "lesson_segmentation_quality_repair":
        model_input = inputs["lesson_segmentation_quality_repair_input.json"]
        return json.dumps({"segments": model_input.get("current_segments") or []}, ensure_ascii=False)

    raise AssertionError(f"unexpected lesson segmentation stage call: {stage_name}")


def _local_knowledge_type_classification_model_call(**kwargs: Any) -> str:
    inputs = kwargs["inputs"]
    stage_name = kwargs["stage_name"]
    if stage_name == "knowledge_type_classification":
        model_input = inputs["knowledge_type_classification_input.json"]
        return json.dumps(
            {
                "classifications": [
                    {
                        "concept_id": concept["concept_id"],
                        "knowledge_type": _fixture_knowledge_type_for_concept(concept),
                        "rationale": "Deterministic fixture classifies from label, description, and Coverage Criteria.",
                        "confidence": 0.8,
                    }
                    for concept in model_input.get("concepts") or []
                ]
            },
            ensure_ascii=False,
        )

    if stage_name == "knowledge_type_quality_audit":
        return json.dumps(
            {
                "scores": {
                    "taxonomy_fit": 3,
                    "teaching_mode_alignment": 3,
                    "segment_consistency": 3,
                    "factual_boundary": 3,
                    "applied_boundary": 3,
                },
                "reliability": "reliable",
                "flags": [],
                "findings": [],
                "repair_plan": [],
            },
            ensure_ascii=False,
        )

    if stage_name == "knowledge_type_quality_repair":
        model_input = inputs["knowledge_type_quality_repair_input.json"]
        current_by_id = {
            item["concept_id"]: item
            for item in model_input.get("current_classifications") or []
            if isinstance(item, dict) and item.get("concept_id")
        }
        classifications = []
        for concept_id in model_input.get("target_concept_ids") or []:
            current = current_by_id.get(concept_id) or {}
            classifications.append(
                {
                    "concept_id": concept_id,
                    "knowledge_type": current.get("knowledge_type") or "conceptual",
                    "rationale": "Deterministic fixture preserves the targeted classification.",
                    "confidence": current.get("confidence", 0.8),
                }
            )
        return json.dumps({"classifications": classifications}, ensure_ascii=False)

    raise AssertionError(f"unexpected knowledge type classification stage call: {stage_name}")


def _fixture_knowledge_type_for_concept(concept: dict[str, Any]) -> str:
    text = " ".join(
        [
            str(concept.get("label") or ""),
            str(concept.get("teaching_description") or ""),
            " ".join(str(item) for item in concept.get("coverage_criteria") or []),
        ]
    ).lower()
    if any(token in text for token in ("scenario", "trade-off", "tradeoff", "when to use", "choose", "design")):
        return "applied"
    if any(
        token in text
        for token in (
            "step",
            "algorithm",
            "implement",
            "execute",
            "calculate",
            "build",
            "use ",
            "apply",
            "api",
            "function",
            "method",
            "train",
            "fit",
            "extract",
            "count",
        )
    ):
        return "procedural"
    if any(token in text for token in ("definition", "define", "date", "term", "terminology", "name", "list")):
        return "factual"
    return "conceptual"


if __name__ == "__main__":
    raise SystemExit(main())
