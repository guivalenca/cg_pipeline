from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


CREATION_OUTPUT_BUDGET_POLICY_VERSION = "creation-output-budget.v1"
OUTPUT_TOKEN_EMERGENCY_CEILING = 65_536
SUBJECT_REPAIR_LARGE_TARGET_GROUP_SIZE = 32


@dataclass(frozen=True)
class OutputBudgetPolicy:
    operation: str
    initial_max_tokens: int
    length_retry_max_tokens: int | None = None
    version: str = CREATION_OUTPUT_BUDGET_POLICY_VERSION

    def __post_init__(self) -> None:
        if not self.operation.strip():
            raise ValueError("Output budget operation must not be blank")
        if not 0 < self.initial_max_tokens <= OUTPUT_TOKEN_EMERGENCY_CEILING:
            raise ValueError(
                "Initial output budget must be positive and no greater than the emergency ceiling"
            )
        if self.length_retry_max_tokens is None:
            return
        if not self.initial_max_tokens < self.length_retry_max_tokens <= OUTPUT_TOKEN_EMERGENCY_CEILING:
            raise ValueError(
                "Length retry output budget must exceed the initial budget without exceeding the emergency ceiling"
            )

    def identity(self) -> dict[str, Any]:
        return {
            "operation": self.operation,
            "initial_max_tokens": self.initial_max_tokens,
            "length_retry_max_tokens": self.length_retry_max_tokens,
            "emergency_ceiling": OUTPUT_TOKEN_EMERGENCY_CEILING,
            "version": self.version,
        }

    def attempt_caps(self) -> tuple[int, ...]:
        if self.length_retry_max_tokens is None:
            return (self.initial_max_tokens,)
        return (self.initial_max_tokens, self.length_retry_max_tokens)


_INITIAL_CAP_BY_OPERATION = {
    "workbook_label_interpretation": 8_192,
    "metadata_only_extraction": 8_192,
    "lesson_candidate_clustering": 16_384,
    "lesson_segment_concept_orderer": 8_192,
    "lesson_segmentation_quality_repair": 8_192,
    "knowledge_type_quality_repair": 4_096,
    "knowledge_type_classification": 16_384,
    "lesson_segment_planner": 16_384,
    "lesson_segmentation_quality_audit": 16_384,
    "knowledge_type_quality_audit": 16_384,
    "subject_cluster_evaluation": 16_384,
    "lesson_cluster_evaluation": 32_768,
    "lesson_reconciliation_quality_repair": 32_768,
    "subject_merge_area_partition": 32_768,
    "subject_merge_quality_audit": 32_768,
    "subject_merge_quality_repair": 32_768,
    "self_study_extraction": OUTPUT_TOKEN_EMERGENCY_CEILING,
    "subject_merge_fine_clustering": OUTPUT_TOKEN_EMERGENCY_CEILING,
}


def resolve_output_budget(
    *,
    stage_name: str,
    inputs: Mapping[str, Any],
    configured: OutputBudgetPolicy | None = None,
) -> OutputBudgetPolicy:
    """Resolve the audited cap for one Creation model operation.

    Unknown operations stay at the global ceiling. A stage already at the ceiling has no
    same-cap retry because repeating the identical request cannot recover a length stop.
    """

    if configured is not None:
        return configured
    operation = str(stage_name or "").strip()
    initial_cap = _INITIAL_CAP_BY_OPERATION.get(
        operation,
        OUTPUT_TOKEN_EMERGENCY_CEILING,
    )
    if (
        operation == "subject_merge_quality_repair"
        and _subject_repair_target_count(inputs) >= SUBJECT_REPAIR_LARGE_TARGET_GROUP_SIZE
    ):
        initial_cap = OUTPUT_TOKEN_EMERGENCY_CEILING
    retry_cap = (
        OUTPUT_TOKEN_EMERGENCY_CEILING
        if initial_cap < OUTPUT_TOKEN_EMERGENCY_CEILING
        else None
    )
    return OutputBudgetPolicy(
        operation=operation or "unnamed_creation_stage",
        initial_max_tokens=initial_cap,
        length_retry_max_tokens=retry_cap,
    )


def output_budget_identity(
    *,
    stage_name: str,
    inputs: Mapping[str, Any],
) -> dict[str, Any]:
    return resolve_output_budget(stage_name=stage_name, inputs=inputs).identity()


def _subject_repair_target_count(inputs: Mapping[str, Any]) -> int:
    model_input = inputs.get("subject_merge_quality_repair_input.json")
    if not isinstance(model_input, Mapping):
        # Derivation helpers receive the model input itself rather than StageRunner's filename map.
        model_input = inputs
    candidate_ids = model_input.get("target_candidate_ids")
    if not isinstance(candidate_ids, list):
        return 0
    return sum(1 for candidate_id in candidate_ids if isinstance(candidate_id, str) and candidate_id)
