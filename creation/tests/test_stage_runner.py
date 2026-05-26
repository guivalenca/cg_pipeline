import json
from pathlib import Path

import pytest

from concept_graph_creation.runtime.stage_runner import (
    FLASH_ROUTE_ALIAS,
    ModelRouter,
    PRO_ROUTE_ALIAS,
    PRO_THINKING_ROUTE_ALIAS,
    StageBlockedError,
    StageContract,
    StageRunner,
)


def test_model_router_exposes_pro_and_pro_thinking_routes():
    router = ModelRouter.default()

    assert set(router.routes) == {FLASH_ROUTE_ALIAS, PRO_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS}
    assert router.resolve(FLASH_ROUTE_ALIAS).model == "deepseek-v4-flash"
    assert router.resolve(FLASH_ROUTE_ALIAS).thinking_enabled is False
    assert router.resolve(FLASH_ROUTE_ALIAS).reasoning_effort is None
    assert router.resolve(PRO_ROUTE_ALIAS).model == "deepseek-v4-pro"
    assert router.resolve(PRO_ROUTE_ALIAS).thinking_enabled is False
    assert router.resolve(PRO_ROUTE_ALIAS).reasoning_effort is None
    assert router.resolve(PRO_THINKING_ROUTE_ALIAS).model == "deepseek-v4-pro"
    assert router.resolve(PRO_THINKING_ROUTE_ALIAS).thinking_enabled is True
    assert router.resolve(PRO_THINKING_ROUTE_ALIAS).reasoning_effort == "high"


def test_stage_runner_routes_model_and_repairs_malformed_json_once(tmp_path):
    run_dir = tmp_path / "stage_runner_format_repair"
    input_path = run_dir / "source_ledger.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text('{"artifact_type": "source_ledger"}\n', encoding="utf-8")

    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        calls.append((route.alias, stage_name, repair_context))
        if repair_context is None:
            return '{"artifact_type": "demo_stage", "value": 1'
        return '{"artifact_type": "demo_stage", "value": 1}'

    contract = StageContract(
        name="demo_stage",
        required_inputs=["source_ledger.json"],
        output_artifact="demo_stage.json",
        model_route=PRO_THINKING_ROUTE_ALIAS,
        validator=lambda artifact: [] if artifact.get("artifact_type") == "demo_stage" else ["wrong artifact_type"],
    )

    runner = StageRunner(router=ModelRouter.default(), model_call=model_call)
    result = runner.run(contract, run_dir=run_dir)

    assert result.artifact_path == run_dir / "demo_stage.json"
    assert json.loads(result.artifact_path.read_text(encoding="utf-8")) == {
        "artifact_type": "demo_stage",
        "value": 1,
    }
    assert result.repaired is True
    assert [call[0] for call in calls] == [PRO_THINKING_ROUTE_ALIAS, PRO_THINKING_ROUTE_ALIAS]
    assert calls[1][2]["repair_type"] == "format_repair"
    assert (run_dir / "raw_model_outputs" / "demo_stage" / "attempt_1.txt").is_file()
    assert (run_dir / "raw_model_outputs" / "demo_stage" / "attempt_2_format_repair.txt").is_file()
    progress_events = [
        json.loads(line)
        for line in (run_dir / "stage_progress.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event"] for event in progress_events] == [
        "model_call_start",
        "model_call_returned",
        "model_call_start",
        "model_call_returned",
        "artifact_written",
    ]
    assert progress_events[0]["route"] == PRO_THINKING_ROUTE_ALIAS


def test_stage_runner_can_route_format_repair_to_flash(tmp_path):
    run_dir = tmp_path / "stage_runner_flash_repair"
    input_path = run_dir / "source_ledger.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text('{"artifact_type": "source_ledger"}\n', encoding="utf-8")
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        calls.append((route.alias, repair_context["repair_type"] if repair_context else None))
        if repair_context is None:
            return '{"artifact_type": "demo_stage"'
        return '{"artifact_type": "demo_stage"}'

    contract = StageContract(
        name="demo_stage",
        required_inputs=["source_ledger.json"],
        output_artifact="demo_stage.json",
        model_route=PRO_ROUTE_ALIAS,
        repair_model_route=FLASH_ROUTE_ALIAS,
        validator=lambda artifact: [] if artifact.get("artifact_type") == "demo_stage" else ["wrong artifact_type"],
    )

    StageRunner(router=ModelRouter.default(), model_call=model_call).run(contract, run_dir=run_dir)

    assert calls == [(PRO_ROUTE_ALIAS, None), (FLASH_ROUTE_ALIAS, "format_repair")]


def test_stage_runner_can_route_contextual_repair_to_pro(tmp_path):
    run_dir = tmp_path / "stage_runner_contextual_repair"
    input_path = run_dir / "source_ledger.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text('{"artifact_type": "source_ledger"}\n', encoding="utf-8")
    calls = []

    def model_call(*, route, stage_name, inputs, repair_context=None):
        calls.append((route.alias, repair_context["repair_type"] if repair_context else None))
        if repair_context is None:
            return '{"artifact_type": "wrong"}'
        return '{"artifact_type": "demo_stage"}'

    contract = StageContract(
        name="demo_stage",
        required_inputs=["source_ledger.json"],
        output_artifact="demo_stage.json",
        model_route=FLASH_ROUTE_ALIAS,
        repair_model_route=FLASH_ROUTE_ALIAS,
        contextual_repair_model_route=PRO_ROUTE_ALIAS,
        validator=lambda artifact: [] if artifact.get("artifact_type") == "demo_stage" else ["wrong artifact_type"],
    )

    StageRunner(router=ModelRouter.default(), model_call=model_call).run(contract, run_dir=run_dir)

    assert calls == [(FLASH_ROUTE_ALIAS, None), (PRO_ROUTE_ALIAS, "contextual_repair")]


def test_stage_runner_blocks_when_required_input_is_missing_before_model_call(tmp_path):
    run_dir = tmp_path / "stage_runner_missing_input"
    called = False

    def model_call(**_kwargs):
        nonlocal called
        called = True
        return "{}"

    contract = StageContract(
        name="missing_input_stage",
        required_inputs=["source_ledger.json"],
        output_artifact="missing_input_stage.json",
        model_route=PRO_THINKING_ROUTE_ALIAS,
        validator=lambda _artifact: [],
    )

    runner = StageRunner(router=ModelRouter.default(), model_call=model_call)
    with pytest.raises(StageBlockedError, match="missing required input artifact: source_ledger.json"):
        runner.run(contract, run_dir=run_dir)

    assert called is False
    assert not (run_dir / "missing_input_stage.json").exists()


def test_stage_runner_blocks_after_one_failed_contextual_repair_without_partial_artifact(tmp_path):
    run_dir = tmp_path / "stage_runner_failed_repair"
    input_path = run_dir / "source_ledger.json"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text('{"artifact_type": "source_ledger"}\n', encoding="utf-8")

    def model_call(**_kwargs):
        return '{"artifact_type": "wrong"}'

    contract = StageContract(
        name="bad_stage",
        required_inputs=["source_ledger.json"],
        output_artifact="bad_stage.json",
        model_route=PRO_THINKING_ROUTE_ALIAS,
        validator=lambda artifact: [] if artifact.get("artifact_type") == "expected" else ["wrong artifact_type"],
    )

    runner = StageRunner(router=ModelRouter.default(), model_call=model_call)
    with pytest.raises(StageBlockedError, match="Stage 'bad_stage' failed Stage Contract: wrong artifact_type"):
        runner.run(contract, run_dir=run_dir)

    assert not (run_dir / "bad_stage.json").exists()
    assert (run_dir / "raw_model_outputs" / "bad_stage" / "attempt_1.txt").is_file()
    assert (run_dir / "raw_model_outputs" / "bad_stage" / "attempt_2_contextual_repair.txt").is_file()
