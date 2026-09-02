"""Semantic identities for Source Publication cleanup model recipes."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

from universe import defaults, harness
from universe.blocks import BLOCKER_VERSION
from universe.model_client import ModelClient


PROJECT_DIR = Path(__file__).resolve().parents[2]
_PROVIDER = {
    "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
    "ignore": ["SiliconFlow"],
}
_THINKING = {
    "thinking": {"type": "enabled"},
    "reasoning_effort": "high",
    "tool_choice": "auto",
    "provider": _PROVIDER,
}


@dataclass(frozen=True, slots=True)
class _RecipeSpec:
    tool: str
    max_tokens: int
    extra: dict
    workers: int


_SPECS = {
    stage: _RecipeSpec(
        f"prompts/{stage}/tool-v001.json",
        65536,
        _THINKING,
        16,
    )
    for stage in ("passage-cuts", "passage-triage")
}
_INPUT_CONTRACTS = {
    "passage-cuts": {
        "body_from": "blocks",
        "blocker_version": BLOCKER_VERSION,
    }
}
_NON_SEMANTIC_RUN_PARAMS = {
    "workers",
    "body_from",
    "blocker_version",
    "pipeline_lease",
    "target_manifest",
    "recipe_fingerprint",
}


def _spec(stage: str) -> _RecipeSpec:
    try:
        return _SPECS[stage]
    except KeyError as exc:
        raise ValueError(f"stage {stage!r} has no model recipe") from exc


def _model_params(stage: str, spec: _RecipeSpec) -> dict:
    tool_payload = harness.load_tool(str(PROJECT_DIR / spec.tool))
    tool_payload.update(deepcopy(spec.extra))
    client = ModelClient(
        defaults.STAGE_DEFAULTS[stage]["model"],
        max_tokens=spec.max_tokens,
        extra=tool_payload,
    )
    return client.params


def recipe_identity(stage: str) -> dict:
    """Return the complete provider-free semantic identity for ``stage``."""
    spec = _spec(stage)
    default = defaults.STAGE_DEFAULTS[stage]
    version = default["prompt_ref"].split("/", 1)[1]
    prompt = harness.load_prompt(stage, version, require_body=False)
    return {
        "model": default["model"],
        "prompt_ref": prompt.ref,
        "prompt_sha": prompt.sha,
        "model_params": _model_params(stage, spec),
        "input_contract": deepcopy(_INPUT_CONTRACTS.get(stage, {})),
    }


def recipe_fingerprint(stage: str) -> str:
    canonical = json.dumps(
        recipe_identity(stage),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def matches_recipe(
    stage: str,
    *,
    model: str | None,
    prompt_ref: str | None,
    prompt_sha: str | None,
    params: dict | None,
) -> bool:
    """Return whether a stamped run matches today's exact recipe."""
    expected = recipe_identity(stage)
    if (
        defaults.bare_model(model) != defaults.bare_model(expected["model"])
        or prompt_ref != expected["prompt_ref"]
        or prompt_sha != expected["prompt_sha"]
        or not isinstance(params, dict)
    ):
        return False
    if any(
        params.get(key) != value
        for key, value in expected["input_contract"].items()
    ):
        return False
    observed_model_params = {
        key: value
        for key, value in params.items()
        if key not in _NON_SEMANTIC_RUN_PARAMS
    }
    return observed_model_params == expected["model_params"]


def launch_recipe(stage: str) -> dict:
    spec = _spec(stage)
    return {
        **recipe_identity(stage),
        "tool": spec.tool,
        "max_tokens": spec.max_tokens,
        "extra": deepcopy(spec.extra),
        "workers": spec.workers,
    }
