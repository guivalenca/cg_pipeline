"""One semantic identity for every model recipe the KC pipeline can launch.

The ledger may carry operational and provenance parameters beside a model
request.  A reusable Run Witness is stricter: its model, prompt bytes, tool
payload, and inference/routing request must match today's recipe exactly.
Concurrency is deliberately absent because it cannot change one call's
meaning.
"""

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
_MODALITY = {
    "reasoning": {"enabled": False},
    "provider": _PROVIDER,
}
_JUDGE = {
    "tool_choice": "auto",
    "reasoning_effort": "low",
    "provider": {
        "sort": "throughput",
        "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
    },
}


@dataclass(frozen=True, slots=True)
class _RecipeSpec:
    tool: str | None
    max_tokens: int | None
    extra: dict | None
    workers: int


_TOOLS = {
    "passage-cuts": "prompts/passage-cuts/tool-v001.json",
    "passage-triage": "prompts/passage-triage/tool-v001.json",
    "task-generation": "prompts/task-generation/tool-v001.json",
    "task-granularity": "prompts/task-granularity/tool-v001.json",
    "task-revision": "prompts/task-revision/tool-v003.json",
    "task-triage": "prompts/task-triage/tool-v001.json",
    "task-substance": "prompts/task-substance/tool-v004.json",
    "kc-statement": "prompts/kc-statement/tool-v007.json",
    "task-modality": "prompts/task-modality/tool-v001.json",
    "task-knowledge": "prompts/task-knowledge/tool-v002.json",
    "kc-judge": "prompts/kc-judge/tool-v002.json",
    "kc-canonical-statement": "prompts/kc-canonical-statement/tool-v001.json",
}

_SPECS = {
    **{
        stage: _RecipeSpec(_TOOLS[stage], 65536, _THINKING, 16)
        for stage in (
            "passage-cuts",
            "passage-triage",
            "task-generation",
            "task-granularity",
            "task-revision",
            "task-triage",
            "task-substance",
            "kc-statement",
            "task-knowledge",
        )
    },
    "task-modality": _RecipeSpec(
        _TOOLS["task-modality"], 65536, _MODALITY, 1
    ),
    "task-embedding": _RecipeSpec(None, None, None, 8),
    "kc-judge": _RecipeSpec(
        # The corpus witness must not depend on the process-wide client
        # override.  Both the launcher and every later reader compare this
        # exact value when deciding whether the grouping is current.
        _TOOLS["kc-judge"], 65536, _JUDGE, 16
    ),
    "kc-canonical-statement": _RecipeSpec(
        _TOOLS["kc-canonical-statement"],
        1000,
        defaults.KC_INFERENCE_DEFAULTS["kc-canonical-statement"],
        1,
    ),
}

_INPUT_CONTRACTS = {
    # The accepted cut prompt sees stable numbered blocks, never the raw
    # artifact body. Same prompt/model/tool over a different rendering is a
    # different recipe even though the provider request flags are identical.
    "passage-cuts": {
        "body_from": "blocks",
        "blocker_version": BLOCKER_VERSION,
    },
    "kc-judge": {
        "semantic_floor": 0.70,
        "semantic_cap": 6,
        "lexical_k": 5,
    },
}

# Parameters that are either verified through ``input_contract`` or describe
# what was selected, where it came from, or how the process was scheduled.
# None belong to ``ModelClient.params``. The allowlist is intentionally
# closed: an unknown top-level request flag must invalidate reuse instead of
# being silently treated as provenance.
_NON_SEMANTIC_RUN_PARAMS = {
    "workers",
    "body_from",
    "blocker_version",
    "pipeline_lease",
    "target_manifest",
    "recipe_fingerprint",
    "effective_task_manifest_sha",
    "cuts_runs",
    "triage_runs",
    "skip_runs",
    "gen_runs",
    "passages_from",
    "revision_run",
    "granularity_run",
    "granularity_runs",
    "parts_revision_run",
    "triage_run",
    "substance_run",
    "statements_from",
    "embedding_run",
    "modality_runs",
    "knowledge_runs",
    "grouping_id",
    "build_key",
    "candidate_count",
    "candidate_manifest_complete",
    "candidate_manifest_sha256",
    "semantic_floor",
    "semantic_cap",
    "lexical_k",
}


def _spec(stage: str) -> _RecipeSpec:
    try:
        return _SPECS[stage]
    except KeyError as exc:
        raise ValueError(f"stage {stage!r} has no model recipe") from exc


def _model_params(stage: str, spec: _RecipeSpec) -> dict:
    if stage == "task-embedding":
        return {}
    extra = deepcopy(spec.extra or {})
    if spec.tool is not None:
        tool_payload = harness.load_tool(str(PROJECT_DIR / spec.tool))
        # This is the same precedence every runner uses: the explicit tool
        # payload is loaded, then the accepted inference preset is applied.
        if stage not in {"kc-judge", "kc-canonical-statement"}:
            tool_payload.update(extra)
            extra = tool_payload
        else:
            extra.update(tool_payload)
    client = ModelClient(
        defaults.STAGE_DEFAULTS[stage]["model"],
        max_tokens=spec.max_tokens,
        extra=extra,
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
    """Stable SHA-256 of one stage's semantic recipe."""
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
    """Whether a stamped run is a live witness for today's exact recipe.

    Provenance, input-run ids, lease stamps, and even a historical ``workers``
    field may coexist in ``params``.  Only fields that enter a provider
    request are compared here, and every one of those fields must be present.
    """
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
    """Operational fields used to build the subprocess for ``stage``.

    ``workers`` is returned beside, but intentionally excluded from,
    :func:`recipe_identity` and its fingerprint.
    """
    spec = _spec(stage)
    return {
        **recipe_identity(stage),
        "tool": spec.tool,
        "max_tokens": spec.max_tokens,
        "extra": deepcopy(spec.extra),
        "workers": spec.workers,
    }
