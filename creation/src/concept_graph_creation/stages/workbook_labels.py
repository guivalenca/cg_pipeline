from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from concept_graph_creation.runtime.stage_runner import (
    ModelCall,
    ModelRouter,
    PRO_ROUTE_ALIAS,
    StageBlockedError,
    StageContract,
    StageResult,
    StageRunner,
)


ALLOWED_PATTERNS = {
    "prerequisite_hint",
    "lesson_cluster",
    "application_adjacent_signal",
    "ignored_ambiguous",
}

Classifier = Callable[[str, list[dict[str, Any]]], dict[str, str]]


def run_workbook_label_interpretation_stage(
    *,
    run_dir: Path,
    model_call: ModelCall,
    model_route: str = PRO_ROUTE_ALIAS,
    router: ModelRouter | None = None,
    prompt_path: Path | None = None,
) -> StageResult:
    prompt_path = prompt_path or Path(__file__).resolve().parents[3] / "prompts" / "workbook_label_interpretation.md"
    prompt = prompt_path.read_text(encoding="utf-8")
    source_ledger_path = run_dir / "source_ledger.json"
    source_ledger = json.loads(source_ledger_path.read_text(encoding="utf-8"))
    contexts_by_label = _collect_label_contexts(source_ledger)
    existing_interpretations = _load_existing_interpretations(run_dir / "workbook_label_interpretation.json")
    labels_to_classify = [{"label": label} for label in sorted(contexts_by_label) if label not in existing_interpretations]
    model_input = {
        "artifact_type": "workbook_label_interpretation_input",
        "schema_version": "workbook_label_interpretation_input.v0",
        "source_artifact": "source_ledger.json",
        "prompt_path": str(prompt_path),
        "prompt": prompt,
        "existing_interpretations": existing_interpretations,
        "label_contexts": contexts_by_label,
        "labels_to_classify": labels_to_classify,
    }
    (run_dir / "workbook_label_interpretation_input.json").write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if not labels_to_classify:
        artifact = build_workbook_label_interpretation(
            source_ledger=source_ledger,
            classifier=_unexpected_classifier,
            existing_interpretations=existing_interpretations,
        )
        artifact["model_route"] = "reused_existing"
        errors = validate_workbook_label_interpretation(artifact)
        if errors:
            raise StageBlockedError("Workbook Label Interpretation validation failed: " + "; ".join(errors))
        artifact_path = write_workbook_label_interpretation(artifact, run_dir / "workbook_label_interpretation.json")
        return StageResult(
            stage_name="workbook_label_interpretation",
            artifact_path=artifact_path,
            raw_output_paths=[],
            repaired=False,
        )

    contract = StageContract(
        name="workbook_label_interpretation",
        required_inputs=["workbook_label_interpretation_input.json"],
        output_artifact="workbook_label_interpretation.json",
        model_route=model_route,
        validator=validate_workbook_label_interpretation,
        normalizer=_normalize_model_label_output,
    )
    return StageRunner(router=router or ModelRouter.default(), model_call=model_call).run(contract, run_dir=run_dir)


def _unexpected_classifier(label: str, _contexts: list[dict[str, Any]]) -> dict[str, str]:
    raise StageBlockedError(f"Workbook label '{label}' unexpectedly required model classification")


def build_workbook_label_interpretation(
    *,
    source_ledger: dict[str, Any],
    classifier: Classifier,
    existing_interpretations: dict[str, dict[str, str]] | None = None,
) -> dict[str, Any]:
    existing_interpretations = existing_interpretations or {}
    contexts_by_label = _collect_label_contexts(source_ledger)
    return _build_workbook_label_interpretation_from_contexts(
        contexts_by_label=contexts_by_label,
        classifier=classifier,
        existing_interpretations=existing_interpretations,
    )


def _build_workbook_label_interpretation_from_contexts(
    *,
    contexts_by_label: dict[str, list[dict[str, Any]]],
    classifier: Classifier,
    existing_interpretations: dict[str, dict[str, str]],
) -> dict[str, Any]:

    interpretations: list[dict[str, Any]] = []
    reused_count = 0
    classified_count = 0
    for label in sorted(contexts_by_label):
        contexts = contexts_by_label[label]
        if label in existing_interpretations:
            result = existing_interpretations[label]
            reused = True
            reused_count += 1
        else:
            result = classifier(label, contexts)
            reused = False
            classified_count += 1

        interpretations.append(
            {
                "label": label,
                "pattern": result.get("pattern", "ignored_ambiguous"),
                "confidence": result.get("confidence", "stubbed"),
                "rationale": result.get("rationale", ""),
                "reused": reused,
                "context_count": len(contexts),
                "contexts": contexts,
            }
        )

    prerequisite_hints = _labels_for_pattern(interpretations, "prerequisite_hint")
    lesson_clusters = _labels_for_pattern(interpretations, "lesson_cluster")
    application_adjacent = _labels_for_pattern(interpretations, "application_adjacent_signal")
    ignored = [
        {
            "label": item["label"],
            "rationale": item["rationale"],
            "context_count": item["context_count"],
        }
        for item in interpretations
        if item["pattern"] == "ignored_ambiguous"
    ]

    return {
        "artifact_type": "workbook_label_interpretation",
        "schema_version": "workbook_label_interpretation.v0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_artifact": "source_ledger.json",
        "model_route": "deterministic_fixture",
        "summary": {
            "unique_label_count": len(interpretations),
            "reused_count": reused_count,
            "classified_count": classified_count,
            "prerequisite_hint_count": len(prerequisite_hints),
            "lesson_cluster_count": len(lesson_clusters),
            "application_adjacent_signal_count": len(application_adjacent),
            "ignored_ambiguous_count": len(ignored),
        },
        "active_outputs": {
            "prerequisite_hints": prerequisite_hints,
            "lesson_clusters": lesson_clusters,
        },
        "audit_only": {
            "application_adjacent_signals": application_adjacent,
        },
        "ignored_ambiguous": ignored,
        "interpretations": interpretations,
    }


def validate_workbook_label_interpretation(artifact: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if artifact.get("artifact_type") != "workbook_label_interpretation":
        errors.append("workbook_label_interpretation.artifact_type must be 'workbook_label_interpretation'")

    interpretations = artifact.get("interpretations")
    if not isinstance(interpretations, list) or not interpretations:
        errors.append("workbook_label_interpretation.interpretations must not be empty")
        return errors

    labels = [item.get("label") for item in interpretations]
    if len(labels) != len(set(labels)):
        errors.append("workbook_label_interpretation.interpretations contains duplicate labels")

    pattern_by_label: dict[str, str] = {}
    for item in interpretations:
        label = item.get("label")
        pattern = item.get("pattern")
        if not label:
            errors.append("workbook_label_interpretation.interpretations[].label is required")
        if pattern not in ALLOWED_PATTERNS:
            errors.append(f"workbook_label_interpretation label '{label}' has invalid pattern: {pattern}")
        if not item.get("rationale"):
            errors.append(f"workbook_label_interpretation label '{label}' requires rationale")
        if not item.get("contexts"):
            errors.append(f"workbook_label_interpretation label '{label}' requires workbook context")
        if label:
            pattern_by_label[label] = pattern

    active_outputs = artifact.get("active_outputs") or {}
    for label in active_outputs.get("prerequisite_hints", []):
        if pattern_by_label.get(label) != "prerequisite_hint":
            errors.append(f"active prerequisite hint '{label}' is not classified as prerequisite_hint")
    for label in active_outputs.get("lesson_clusters", []):
        if pattern_by_label.get(label) != "lesson_cluster":
            errors.append(f"active lesson cluster '{label}' is not classified as lesson_cluster")

    audit_only = artifact.get("audit_only") or {}
    for label in audit_only.get("application_adjacent_signals", []):
        if pattern_by_label.get(label) != "application_adjacent_signal":
            errors.append(
                f"audit-only application/adjacent label '{label}' is not classified as application_adjacent_signal"
            )

    ignored_labels = {item.get("label") for item in artifact.get("ignored_ambiguous", [])}
    for label in ignored_labels:
        if pattern_by_label.get(label) != "ignored_ambiguous":
            errors.append(f"ignored label '{label}' is not classified as ignored_ambiguous")

    summary = artifact.get("summary") or {}
    if summary.get("unique_label_count") != len(interpretations):
        errors.append("workbook_label_interpretation.summary.unique_label_count does not match interpretations")
    return errors


def _normalize_model_label_output(raw: str, inputs: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError("workbook label model output must be a JSON object")
    if isinstance(payload.get("interpretations"), list):
        return payload

    model_input = inputs["workbook_label_interpretation_input.json"]
    expected_labels = [item["label"] for item in model_input.get("labels_to_classify", [])]
    classified = _extract_model_classifications(payload)
    missing = sorted(label for label in expected_labels if label not in classified)
    if missing:
        preview = ", ".join(missing[:10])
        if len(missing) > 10:
            preview += f", ... ({len(missing)} total)"
        raise ValueError(f"model output missing classifications for labels: {preview}")

    def classifier(label: str, _contexts: list[dict[str, Any]]) -> dict[str, str]:
        return classified[label]

    artifact = _build_workbook_label_interpretation_from_contexts(
        contexts_by_label=model_input.get("label_contexts", {}),
        classifier=classifier,
        existing_interpretations=model_input.get("existing_interpretations", {}),
    )
    artifact["model_route"] = payload.get("model_route", PRO_ROUTE_ALIAS)
    return artifact


def _extract_model_classifications(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    rows: list[dict[str, Any]] = []
    if isinstance(payload.get("classifications"), list):
        rows.extend(payload["classifications"])
    interpretations = payload.get("interpretations")
    if isinstance(interpretations, dict):
        for pattern, values in interpretations.items():
            rows.extend(_classification_rows(pattern, values))
    for pattern in ALLOWED_PATTERNS:
        rows.extend(_classification_rows(pattern, payload.get(pattern)))
    rows.extend(_classification_rows("prerequisite_hint", payload.get("prerequisite_hints")))
    rows.extend(_classification_rows("lesson_cluster", payload.get("lesson_clusters")))
    audit_only = payload.get("audit_only")
    if isinstance(audit_only, dict):
        rows.extend(_classification_rows("application_adjacent_signal", audit_only.get("application_adjacent_signals")))
    rows.extend(_classification_rows("ignored_ambiguous", payload.get("ignored_ambiguous")))

    classified: dict[str, dict[str, str]] = {}
    for row in rows:
        label = str(row.get("label") or "").strip()
        pattern = str(row.get("pattern") or row.get("category") or "").strip()
        if pattern == "prerequisite_hints":
            pattern = "prerequisite_hint"
        elif pattern == "lesson_clusters":
            pattern = "lesson_cluster"
        if pattern == "application_adjacent_signals":
            pattern = "application_adjacent_signal"
        if not label or pattern not in ALLOWED_PATTERNS:
            continue
        classified[label] = {
            "pattern": pattern,
            "confidence": str(row.get("confidence") or "model"),
            "rationale": str(row.get("rationale") or row.get("reason") or "Model classified this label."),
        }
    return classified


def _classification_rows(pattern: str, values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    rows: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, str):
            rows.append({"label": value, "pattern": pattern})
        elif isinstance(value, dict):
            rows.append({"pattern": pattern, **value})
    return rows


def write_workbook_label_interpretation(artifact: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def _load_existing_interpretations(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    existing: dict[str, dict[str, str]] = {}
    for item in artifact.get("interpretations", []):
        label = item.get("label")
        pattern = item.get("pattern")
        rationale = item.get("rationale")
        if label and pattern in ALLOWED_PATTERNS and rationale:
            existing[label] = {
                "pattern": pattern,
                "confidence": item.get("confidence", "existing"),
                "rationale": rationale,
            }
    return existing


def deterministic_fixture_classifier(label: str, _contexts: list[dict[str, Any]]) -> dict[str, str]:
    if label in {
        "Programação lógica",
        "Estruturas de dados",
        "Lógica algorítmica",
        "Recursão e indução",
        "Projeto de algoritmos",
        "Sistemas de numeração de base",
        "Aritmética binária",
    }:
        return {
            "pattern": "prerequisite_hint",
            "confidence": "deterministic_fixture",
            "rationale": "Programming or computing foundation likely needed before later NLP synthesis.",
        }
    if label in {
        "Introdução ao Processamento de Linguagem Natural",
        "Processamento de texto, métricas e técnicas",
        "Processamento do discurso",
        "Representação vetorial de textos",
        "Determinação do conteúdo em PLN",
        "Processamento de Linguagem Natural",
    }:
        return {
            "pattern": "lesson_cluster",
            "confidence": "deterministic_fixture",
            "rationale": "Label names an NLP lesson cluster or direct curricular theme.",
        }
    if label in {
        "Gestão da configuração",
        "Licenças de software",
        "API",
        "Deployment",
        "Qualidade de software",
        "ISO/IEC 25010",
        "Teste de software",
    }:
        return {
            "pattern": "application_adjacent_signal",
            "confidence": "deterministic_fixture",
            "rationale": "Recorded for audit as adjacent software-engineering or application context, not active v0 synthesis.",
        }
    return {
        "pattern": "ignored_ambiguous",
        "confidence": "deterministic_fixture",
        "rationale": "No deterministic v0-active interpretation in this prototype.",
    }


def _collect_label_contexts(source_ledger: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    contexts_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for lesson in source_ledger.get("lessons", []):
        for label in lesson.get("related_labels", []):
            contexts_by_label[label].append(
                {
                    "context_type": "lesson",
                    "lesson_id": lesson.get("lesson_id"),
                    "lesson_title": lesson.get("title"),
                    "self_study_id": None,
                    "self_study_title": None,
                }
            )
    for self_study in source_ledger.get("self_studies", []):
        metadata = self_study.get("workbook_metadata") or {}
        for label in metadata.get("related_labels", []):
            contexts_by_label[label].append(
                {
                    "context_type": "self_study",
                    "lesson_id": self_study.get("lesson_id"),
                    "lesson_title": metadata.get("parent_class"),
                    "self_study_id": self_study.get("self_study_id"),
                    "self_study_title": metadata.get("title"),
                }
            )
    return contexts_by_label


def _labels_for_pattern(interpretations: list[dict[str, Any]], pattern: str) -> list[str]:
    return [item["label"] for item in interpretations if item["pattern"] == pattern]
