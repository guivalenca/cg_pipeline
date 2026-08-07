import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_pipeline_flash_benchmark.py"
SPEC = importlib.util.spec_from_file_location("pipeline_flash_benchmark", SCRIPT)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(benchmark)


def row(identifier: str, verdict: str, length: int) -> dict:
    return {"run_item_id": identifier, "verdict": verdict, "length": length}


def test_choose_two_stratifies_classifier_cases() -> None:
    rows = [
        row("single-short", "single", 10),
        row("single-long", "single", 20),
        row("composite", "composite", 15),
    ]

    chosen = benchmark.choose_two("task-granularity", rows)

    assert [item["verdict"] for item in chosen] == ["composite", "single"]
    assert chosen[1]["run_item_id"] == "single-long"


def test_choose_two_falls_back_to_longest_and_shortest() -> None:
    rows = [row("short", "supported", 10), row("middle", "supported", 20), row("long", "supported", 30)]

    chosen = benchmark.choose_two("task-triage", rows)

    assert [item["run_item_id"] for item in chosen] == ["long", "short"]


def test_choose_two_refuses_a_one_case_sample() -> None:
    with pytest.raises(ValueError, match="fewer than two"):
        benchmark.choose_two("task-triage", [row("only", "supported", 10)])
