"""Ordered creation stages available to the per-Lesson build worker."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StagePlan:
    name: str
    module: str
    label: str = ""
    result_path: str = ""
    prompt_path: str | None = None


_STAGES: tuple[StagePlan, ...] = (
    StagePlan(
        "candidate-concepts",
        "universe.lesson_creation_stage",
        "Conceitos candidatos",
        "self_study_extraction_summary.json",
        "prompts/self_study_extraction.md",
    ),
    StagePlan(
        "lesson-reconciliation",
        "universe.lesson_creation_stage",
        "Conceitos reconciliados",
        "lesson_reconciliation_summary.json",
        "prompts/lesson_reconciliation.md",
    ),
    StagePlan(
        "dependency-deferral",
        "universe.lesson_creation_stage",
        "Dependências adiadas",
        "dependency_inference.json",
        None,
    ),
    StagePlan(
        "lesson-segmentation",
        "universe.lesson_creation_stage",
        "Segmentos e ordem",
        "lesson_segmentation_summary.json",
        "prompts/lesson_segmentation",
    ),
    StagePlan(
        "knowledge-types",
        "universe.lesson_creation_stage",
        "Tipos de conhecimento",
        "knowledge_type_classification_summary.json",
        "prompts/knowledge_type_classification",
    ),
    StagePlan(
        "lesson-fragment",
        "universe.lesson_creation_stage",
        "Fragmento final",
        "final_graph/runtime_graph.json",
        None,
    ),
)


def registered_stages() -> tuple[StagePlan, ...]:
    """Return the immutable ordered registry used by Lesson workers."""
    return _STAGES


def next_stage(*, completed: tuple[str, ...]) -> StagePlan | None:
    """Return the first registered stage not present in ``completed``."""
    done = set(completed)
    return next((stage for stage in _STAGES if stage.name not in done), None)
