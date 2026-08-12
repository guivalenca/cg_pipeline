"""Frozen contracts promoted by the August 2026 KC judge research."""

import hashlib
import os
from pathlib import Path
import subprocess
import sys

from universe import defaults
from universe import kc_canonical_statement
from universe.kc_judge import DEFAULT_EXTRA as JUDGE_INFERENCE
from universe.kc_judge import DEFAULT_WORKERS as JUDGE_WORKERS


ROOT = Path(__file__).resolve().parents[1]


def test_judged_prompt_files_match_the_empirical_baseline():
    expected = {
        "prompts/kc-statement/v005.md":
            "2c1b9f8ac0c10f51c4a35069772cb8f2b0868f035bdf87282a970ae63b51d44f",
        "prompts/kc-statement/tool-v007.json":
            "0e3801c2104ac11f8184baebe45e0aef3a71cdf83eff13fec1afceac271461c5",
        "prompts/task-modality/v003.md":
            "b7aa3ec494d7470ca05523f0c17d0689950878bf39bf22b2c753bd9c0d7717cb",
        "prompts/task-modality/tool-v001.json":
            "f3cd760ff47e7261636548b1d630d4892f2df5be259b166ec08a32e41a022edd",
        "prompts/task-knowledge/v003.md":
            "8d4f17769bef42ec07cab545f12c24004d49ce52c548ed956224ee8928f106e5",
        "prompts/task-knowledge/tool-v002.json":
            "b882e67f7d7e5fe8f173c8fd2ffc610abaa7a921f3ef93ceb5667c24adfcbd55",
        "prompts/task-embedding/v002.md":
            "835d46325c3de8740c190ebe7743d4756222eba95b93702195c2ab57c8e73674",
        "prompts/kc-judge/v003-surmise-pair.md":
            "23ce1be180591d15fd262560755b24581654de402aef489ace14226d03e5e350",
        "prompts/kc-judge/tool-v002.json":
            "844966d2ecdb306607f3d9fc8085a2783b0e998ebbfeef2e61406f0e413d4412",
        "prompts/kc-canonical-statement/v001.md":
            "842d2cc4d2a3b231b4ebb980e4e484222f34ea8f8cf8cffe892fadb1064e6cc1",
        "prompts/kc-canonical-statement/tool-v001.json":
            "086ea244102cf4ec202198431c84750ecdc6518b8d74d3be2d121336f5bc2812",
    }

    observed = {
        path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        for path in expected
    }

    assert observed == expected


def test_judged_stage_defaults_match_the_empirical_baseline():
    expected = {
        "kc-statement": {
            "model": "deepseek/deepseek-v4-pro",
            "prompt_ref": "kc-statement/v005",
        },
        "task-modality": {
            "model": "deepseek/deepseek-v4-pro",
            "prompt_ref": "task-modality/v003",
        },
        "task-knowledge": {
            "model": "deepseek/deepseek-v4-pro",
            "prompt_ref": "task-knowledge/v003",
        },
        "task-embedding": {
            "model": "qwen/qwen3-embedding-8b",
            "prompt_ref": "task-embedding/v002",
        },
        "kc-judge": {
            "model": "deepseek/deepseek-v4-flash-0731",
            "prompt_ref": "kc-judge/v003-surmise-pair",
        },
        "kc-canonical-statement": {
            "model": "deepseek/deepseek-v4-pro",
            "prompt_ref": "kc-canonical-statement/v001",
        },
    }

    assert {stage: defaults.STAGE_DEFAULTS[stage] for stage in expected} == expected
    assert JUDGE_WORKERS == 16
    assert JUDGE_INFERENCE == {
        "tool_choice": "auto",
        "reasoning_effort": "low",
        "provider": {
            "sort": "throughput",
            "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
        },
    }


def test_canonical_inference_policy_is_owned_by_kc_defaults():
    expected = {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "tool_choice": "auto",
        "provider": {
            "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
            "ignore": ["SiliconFlow"],
        },
    }

    assert defaults.KC_INFERENCE_DEFAULTS["kc-canonical-statement"] == expected
    assert kc_canonical_statement.DEFAULT_EXTRA == expected


def test_canonical_stage_imports_without_the_source_orchestrator():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; "
                "sys.modules['universe.kc_pipeline'] = None; "
                "import universe.kc_canonical_statement"
            ),
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
