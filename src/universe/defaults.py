"""The current generation of every pipeline stage.

One place that answers "is this run still how we do things?".  The ledger
keeps every run forever; this module is the interpretation that separates
the current reference chain from superseded experiments.  It mirrors the
decisions in ``docs/pipeline-defaults.md`` — when a stage default changes
there, it changes here, and everything downstream (dashboard badges,
re-run suggestions) follows.

Model names are compared by their bare id: runs before 2026-07-26 went to
the native DeepSeek API (``deepseek-v4-pro``), later ones to OpenRouter
(``deepseek/deepseek-v4-pro``).  Same model, same generation.
"""

STAGE_DEFAULTS: dict[str, dict[str, str]] = {
    "passage-cuts": {"model": "deepseek/deepseek-v4-flash", "prompt_ref": "passage-cuts/v001"},
    "passage-triage": {"model": "deepseek/deepseek-v4-flash", "prompt_ref": "passage-triage/v001"},
    "task-generation": {"model": "deepseek/deepseek-v4-pro", "prompt_ref": "task-generation/v004"},
    "task-granularity": {"model": "deepseek/deepseek-v4-pro", "prompt_ref": "task-granularity/v004"},
    "task-revision": {"model": "deepseek/deepseek-v4-pro", "prompt_ref": "task-revision/v004"},
    "task-triage": {"model": "deepseek/deepseek-v4-flash", "prompt_ref": "task-triage/v001"},
    "task-substance": {"model": "deepseek/deepseek-v4-pro", "prompt_ref": "task-substance/v004"},
    "kc-statement": {"model": "deepseek/deepseek-v4-pro", "prompt_ref": "kc-statement/v005"},
    "task-modality": {"model": "deepseek/deepseek-v4-pro", "prompt_ref": "task-modality/v003"},
    "task-knowledge": {"model": "deepseek/deepseek-v4-pro", "prompt_ref": "task-knowledge/v003"},
    # Statement-input template (docs/pipeline-defaults.md, 2026-08-03, r0153):
    # v002 renders the selected kc-statement and is the judge's vector space.
    "task-embedding": {"model": "qwen/qwen3-embedding-8b", "prompt_ref": "task-embedding/v002"},
    "kc-judge": {
        "model": "deepseek/deepseek-v4-flash-0731",
        "prompt_ref": "kc-judge/v003-surmise-pair",
    },
    "kc-canonical-statement": {
        "model": "deepseek/deepseek-v4-pro",
        "prompt_ref": "kc-canonical-statement/v001",
    },
}

# Inference policy owned by the KC suffix. Keeping this beside the stage
# recipes lets canonicalization reuse one authoritative routing contract
# without depending on the web adapter or the orchestrator implementation.
KC_INFERENCE_DEFAULTS: dict[str, dict] = {
    "kc-canonical-statement": {
        "thinking": {"type": "enabled"},
        "reasoning_effort": "high",
        "tool_choice": "auto",
        "provider": {
            "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
            "ignore": ["SiliconFlow"],
        },
    },
}

# Stages that no longer exist in the pipeline at all; their runs are
# history, not candidates for re-running.
RETIRED_STAGES = {"passage-segmentation", "task-fact"}


def bare_model(model: str | None) -> str:
    """Strip the provider prefix: ``deepseek/deepseek-v4-pro`` -> ``deepseek-v4-pro``."""
    return (model or "").rsplit("/", 1)[-1]


def run_generation(stage: str, model: str | None, prompt_ref: str | None) -> str:
    """Classify a run against the current defaults.

    ``current``    — this is how the stage runs today.
    ``superseded`` — an older model or prompt; re-running the stage with the
                     current default would replace what this produced.
    ``retired``    — the stage itself no longer exists in the pipeline.
    """
    if stage in RETIRED_STAGES:
        return "retired"
    default = STAGE_DEFAULTS.get(stage)
    if default is None:
        return "current"
    if (
        bare_model(model) == bare_model(default["model"])
        and prompt_ref == default["prompt_ref"]
    ):
        return "current"
    return "superseded"
