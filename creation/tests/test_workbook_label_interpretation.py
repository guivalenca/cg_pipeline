import json
from pathlib import Path

from concept_graph_creation.stages.source_ledger import build_source_ledger
from concept_graph_creation.stages.workbook_labels import (
    build_workbook_label_interpretation,
    run_workbook_label_interpretation_stage,
    validate_workbook_label_interpretation,
    write_workbook_label_interpretation,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
CG_PIPELINE_ROOT = REPO_ROOT / "cg_pipeline"


def test_workbook_label_interpretation_classifies_real_labels_once_and_writes_valid_artifact():
    ledger = build_source_ledger(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        workbook_path=CG_PIPELINE_ROOT / "source" / "si_mod6.xlsx",
        index_path=CG_PIPELINE_ROOT / "index.json",
        subject_sheet="COM",
        course_id="si",
        module_id="mod6",
        subject_id="COM",
    )

    calls = []

    def classifier(label, contexts):
        calls.append(label)
        if label == "Programação lógica":
            return {
                "pattern": "prerequisite_hint",
                "confidence": "fixture",
                "rationale": "Repeated programming foundation label used as a prerequisite signal.",
            }
        if label == "Introdução ao Processamento de Linguagem Natural":
            return {
                "pattern": "lesson_cluster",
                "confidence": "fixture",
                "rationale": "Matches lesson framing for introductory NLP content.",
            }
        if label == "Gestão da configuração":
            return {
                "pattern": "application_adjacent_signal",
                "confidence": "fixture",
                "rationale": "Useful audit context but not an active v0 synthesis input.",
            }
        return {
            "pattern": "ignored_ambiguous",
            "confidence": "fixture",
            "rationale": "No deterministic fixture classification for this prototype.",
        }

    artifact = build_workbook_label_interpretation(
        source_ledger=ledger,
        classifier=classifier,
        existing_interpretations={
            "Programação lógica": {
                "pattern": "prerequisite_hint",
                "confidence": "existing",
                "rationale": "Existing interpretation reused within the run.",
            }
        },
    )

    errors = validate_workbook_label_interpretation(artifact)
    assert errors == []

    output_path = write_workbook_label_interpretation(
        artifact,
        Path(__file__).resolve().parents[1] / "tmp" / "pytest" / "workbook_label_interpretation.json",
    )

    assert output_path.is_file()
    assert artifact["artifact_type"] == "workbook_label_interpretation"
    assert "Programação lógica" not in calls
    assert artifact["summary"]["unique_label_count"] > 40
    assert artifact["summary"]["reused_count"] == 1
    assert artifact["active_outputs"]["prerequisite_hints"] == ["Programação lógica"]
    assert "Introdução ao Processamento de Linguagem Natural" in artifact["active_outputs"]["lesson_clusters"]
    assert "Gestão da configuração" in artifact["audit_only"]["application_adjacent_signals"]
    assert artifact["ignored_ambiguous"]


def test_workbook_label_interpretation_stage_uses_model_call_instead_of_deterministic_fixture(tmp_path):
    ledger = build_source_ledger(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        workbook_path=CG_PIPELINE_ROOT / "source" / "si_mod6.xlsx",
        index_path=CG_PIPELINE_ROOT / "index.json",
        subject_sheet="COM",
        course_id="si",
        module_id="mod6",
        subject_id="COM",
    )
    write_path = tmp_path / "source_ledger.json"
    write_path.write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        assert set(inputs) == {"workbook_label_interpretation_input.json"}
        model_input = inputs["workbook_label_interpretation_input.json"]
        assert "source_ledger.json" not in inputs
        assert "Introdução ao Processamento de Linguagem Natural" in model_input["label_contexts"]
        calls.append({"route": route.alias, "stage_name": stage_name, "repair_context": repair_context})
        labels = [item["label"] for item in model_input["labels_to_classify"]]
        return json.dumps(
            {
                "classifications": [
                    {
                        "label": label,
                        "pattern": "lesson_cluster"
                        if label == "Introdução ao Processamento de Linguagem Natural"
                        else "ignored_ambiguous",
                        "confidence": "fake_model",
                        "rationale": "Fake model classification for normalization.",
                    }
                    for label in labels
                ],
                "model_route": route.alias,
            },
            ensure_ascii=False,
        )

    result = run_workbook_label_interpretation_stage(run_dir=tmp_path, model_call=model_call)

    artifact = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    pattern_by_label = {item["label"]: item["pattern"] for item in artifact["interpretations"]}
    assert calls == [{"route": "Pro", "stage_name": "workbook_label_interpretation", "repair_context": None}]
    assert result.raw_output_paths[0].name == "attempt_1.txt"
    assert pattern_by_label["Programação lógica"] == "ignored_ambiguous"
    assert artifact["active_outputs"]["prerequisite_hints"] == []
    assert artifact["active_outputs"]["lesson_clusters"] == ["Introdução ao Processamento de Linguagem Natural"]


def test_workbook_label_interpretation_stage_normalizes_model_classification_table(tmp_path):
    ledger = build_source_ledger(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        workbook_path=CG_PIPELINE_ROOT / "source" / "si_mod6.xlsx",
        index_path=CG_PIPELINE_ROOT / "index.json",
        subject_sheet="COM",
        course_id="si",
        module_id="mod6",
        subject_id="COM",
    )
    (tmp_path / "source_ledger.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")

    def model_call(*, route, stage_name, inputs, repair_context=None):
        labels = [item["label"] for item in inputs["workbook_label_interpretation_input.json"]["labels_to_classify"]]
        return json.dumps(
            {
                "classifications": [
                    {
                        "label": label,
                        "pattern": "lesson_cluster"
                        if label == "Introdução ao Processamento de Linguagem Natural"
                        else "ignored_ambiguous",
                        "confidence": "fake_model",
                        "rationale": "Fake model classification for normalization.",
                    }
                    for label in labels
                ],
                "model_route": route.alias,
            },
            ensure_ascii=False,
        )

    result = run_workbook_label_interpretation_stage(run_dir=tmp_path, model_call=model_call)

    artifact = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert artifact["summary"]["unique_label_count"] == 58
    assert artifact["active_outputs"]["lesson_clusters"] == ["Introdução ao Processamento de Linguagem Natural"]
    assert artifact["interpretations"][0]["contexts"]


def test_workbook_label_interpretation_stage_reuses_existing_interpretations_without_model_input(tmp_path):
    ledger = build_source_ledger(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        workbook_path=CG_PIPELINE_ROOT / "source" / "si_mod6.xlsx",
        index_path=CG_PIPELINE_ROOT / "index.json",
        subject_sheet="COM",
        course_id="si",
        module_id="mod6",
        subject_id="COM",
    )
    (tmp_path / "source_ledger.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    (tmp_path / "workbook_label_interpretation.json").write_text(
        json.dumps(
            {
                "artifact_type": "workbook_label_interpretation",
                "interpretations": [
                    {
                        "label": "Programação lógica",
                        "pattern": "prerequisite_hint",
                        "confidence": "previous_model",
                        "rationale": "Previously classified prerequisite.",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    def model_call(*, route, stage_name, inputs, repair_context=None):
        model_input = inputs["workbook_label_interpretation_input.json"]
        labels_to_classify = [item["label"] for item in model_input["labels_to_classify"]]
        assert "Programação lógica" not in labels_to_classify

        return json.dumps(
            {
                "classifications": [
                    {
                        "label": label,
                        "pattern": "ignored_ambiguous",
                        "confidence": "fake_model",
                        "rationale": "Fake model ignored the new label.",
                    }
                    for label in labels_to_classify
                ],
                "model_route": route.alias,
            },
            ensure_ascii=False,
        )

    result = run_workbook_label_interpretation_stage(run_dir=tmp_path, model_call=model_call)

    artifact = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    reused = [item for item in artifact["interpretations"] if item["label"] == "Programação lógica"]
    assert reused == [
        {
            "label": "Programação lógica",
            "pattern": "prerequisite_hint",
            "confidence": "previous_model",
            "rationale": "Previously classified prerequisite.",
            "reused": True,
            "context_count": len(reused[0]["contexts"]),
            "contexts": reused[0]["contexts"],
        }
    ]
    assert artifact["summary"]["reused_count"] == 1


def test_workbook_label_interpretation_stage_skips_model_call_when_all_labels_are_reused(tmp_path):
    ledger = build_source_ledger(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        workbook_path=CG_PIPELINE_ROOT / "source" / "si_mod6.xlsx",
        index_path=CG_PIPELINE_ROOT / "index.json",
        subject_sheet="COM",
        course_id="si",
        module_id="mod6",
        subject_id="COM",
    )
    (tmp_path / "source_ledger.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    previous_artifact = build_workbook_label_interpretation(
        source_ledger=ledger,
        classifier=lambda _label, _contexts: {
            "pattern": "ignored_ambiguous",
            "confidence": "previous_model",
            "rationale": "Previously classified label.",
        },
    )
    write_workbook_label_interpretation(previous_artifact, tmp_path / "workbook_label_interpretation.json")

    def model_call(**_kwargs):
        raise AssertionError("model should not be called when every label has an existing interpretation")

    result = run_workbook_label_interpretation_stage(run_dir=tmp_path, model_call=model_call)

    artifact = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert result.raw_output_paths == []
    assert artifact["summary"]["reused_count"] == artifact["summary"]["unique_label_count"]


def test_workbook_label_interpretation_stage_loads_prompt_from_prompt_file(tmp_path):
    ledger = build_source_ledger(
        cg_pipeline_root=CG_PIPELINE_ROOT,
        workbook_path=CG_PIPELINE_ROOT / "source" / "si_mod6.xlsx",
        index_path=CG_PIPELINE_ROOT / "index.json",
        subject_sheet="COM",
        course_id="si",
        module_id="mod6",
        subject_id="COM",
    )
    (tmp_path / "source_ledger.json").write_text(json.dumps(ledger, ensure_ascii=False), encoding="utf-8")
    prompt_path = tmp_path / "prompts" / "workbook_label_interpretation.md"
    prompt_path.parent.mkdir(parents=True)
    prompt_path.write_text("Classify workbook labels from this prompt file.\n", encoding="utf-8")

    def model_call(*, route, stage_name, inputs, repair_context=None):
        model_input = inputs["workbook_label_interpretation_input.json"]
        assert model_input["prompt_path"] == str(prompt_path)
        assert model_input["prompt"] == "Classify workbook labels from this prompt file.\n"

        return json.dumps(
            {
                "classifications": [
                    {
                        "label": item["label"],
                        "pattern": "ignored_ambiguous",
                        "confidence": "fake_model",
                        "rationale": "Fake model ignored this label.",
                    }
                    for item in model_input["labels_to_classify"]
                ],
                "model_route": route.alias,
            },
            ensure_ascii=False,
        )

    run_workbook_label_interpretation_stage(
        run_dir=tmp_path,
        model_call=model_call,
        prompt_path=prompt_path,
    )
