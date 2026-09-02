import hashlib
import json
import importlib
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


@pytest.mark.parametrize(
    "relative_path",
    [
        "self_study_extraction.md",
        "lesson_reconciliation.md",
        "lesson_segmentation/segment_planner.md",
        "lesson_segmentation/concept_orderer.md",
        "lesson_segmentation/quality_audit.md",
        "lesson_segmentation/quality_repair.md",
    ],
)
def test_prose_prompts_require_brazilian_portuguese_without_rewriting_literals(
    relative_path,
):
    prompt = (ROOT / "prompts" / relative_path).read_text(encoding="utf-8").lower()

    assert "português brasileiro" in prompt
    assert "código" in prompt
    assert "notação" in prompt
    assert "nomes próprios" in prompt
    assert "identificadores exatos" in prompt


@pytest.mark.parametrize(
    ("module_name", "entry_point"),
    [
        ("self_study_extraction", "run_self_study_extraction_phase"),
        ("lesson_reconciliation", "run_lesson_reconciliation_phase"),
        ("dependency_deferral", "run_dependency_deferral_phase"),
        ("lesson_segmentation", "run_lesson_segmentation_phase"),
        ("knowledge_type_classification", "run_knowledge_type_classification_phase"),
        ("final_graph_assembly", "run_final_graph_assembly_phase"),
    ],
)
def test_retained_creation_stage_entry_points_are_vendored(module_name, entry_point):
    module = importlib.import_module(f"concept_graph_creation.stages.{module_name}")

    assert callable(getattr(module, entry_point))


def test_metadata_only_creation_and_subject_merge_are_omitted():
    metadata_compatibility = importlib.import_module(
        "concept_graph_creation.stages.metadata_only_extraction"
    )

    assert not hasattr(metadata_compatibility, "run_metadata_only_extraction_phase")
    assert importlib.util.find_spec(
        "concept_graph_creation.stages.subject_merge"
    ) is None


def test_stage_runner_rejects_a_malformed_model_response(tmp_path):
    from concept_graph_creation.runtime.stage_runner import (
        ModelRouter,
        StageBlockedError,
        StageContract,
        StageRunner,
    )

    (tmp_path / "input.json").write_text(json.dumps({"lesson_id": "lesson-1"}))
    contract = StageContract(
        name="contract_probe",
        required_inputs=["input.json"],
        output_artifact="output.json",
        model_route="Pro",
        validator=lambda artifact: [] if artifact.get("ok") is True else ["ok is required"],
    )
    runner = StageRunner(
        router=ModelRouter.default(),
        model_call=lambda **_kwargs: "not-json",
    )

    with pytest.raises(StageBlockedError, match="failed Stage Contract.*JSON parse error"):
        runner.run(contract, run_dir=tmp_path)


def test_editing_self_study_prompt_invalidates_the_completed_stage(tmp_path):
    from concept_graph_creation.stages.self_study_extraction import (
        run_self_study_extraction_phase,
    )

    source_body = tmp_path / "source.md"
    source_body.write_text("# Introdução\n\nUma ideia ensinável.\n", encoding="utf-8")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "source_ledger.json").write_text(
        json.dumps(
            {
                "artifact_type": "source_ledger",
                "schema_version": "source_ledger.v0",
                "course_id": "cc",
                "module_id": "mod6",
                "subject_id": "COM",
                "lessons": [{"lesson_id": "stable-lesson-id", "title": "Introdução"}],
                "self_studies": [
                    {
                        "self_study_id": "source-1",
                        "lesson_id": "stable-lesson-id",
                        "source_body_status": "usable_source_body",
                        "workbook_metadata": {"title": "Fonte"},
                        "source_body": {
                            "path": str(source_body),
                            "sha256": hashlib.sha256(
                                source_body.read_bytes()
                            ).hexdigest(),
                            "word_count": 3,
                        },
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Primeira revisão.", encoding="utf-8")
    calls = []

    def model_call(**_kwargs):
        calls.append(1)
        return json.dumps(
            {
                "candidate_concepts": [
                    {
                        "candidate_id": "candidate-source-1-001",
                        "label": "Ideia ensinável",
                        "description": "Descrição da ideia.",
                        "coverage_criteria": ["Explicar a ideia."],
                        "source_roles": ["introducing"],
                        "extraction_reason": {
                            "source_grounded_rationale": "A fonte apresenta a ideia.",
                            "granularity_rationale": "Cabe em uma pergunta.",
                        },
                        "source_anchors": [
                            {"kind": "markdown_heading", "locator": "Introdução"}
                        ],
                        "evidence_type": "source_body",
                    }
                ],
                "source_local_connector_candidates": [],
            },
            ensure_ascii=False,
        )

    run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path,
        run_dir=run_dir,
        model_call=model_call,
        prompt_path=prompt_path,
        initial_concurrency=1,
    )
    prompt_path.write_text("Segunda revisão.", encoding="utf-8")
    run_self_study_extraction_phase(
        cg_pipeline_root=tmp_path,
        run_dir=run_dir,
        model_call=model_call,
        prompt_path=prompt_path,
        initial_concurrency=1,
    )

    assert len(calls) == 2


def test_lesson_build_stage_accepts_the_vendored_creation_namespace(monkeypatch):
    from universe import lesson_build_stage

    calls = []

    class Module:
        @staticmethod
        def main(argv):
            calls.append(argv)

    monkeypatch.setattr(lesson_build_stage.importlib, "import_module", lambda _name: Module)

    lesson_build_stage.execute_module(
        "concept_graph_creation.stages.fixture",
        ["source", "artifact", "hash"],
    )

    assert calls == [["source", "artifact", "hash"]]
