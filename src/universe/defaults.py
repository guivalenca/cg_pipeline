"""The current generation of each Source Publication cleanup stage.

One place that answers "is this run still how we do things?".  The ledger
keeps every run forever; this module is the interpretation that separates
the current reference chain from superseded experiments.  It mirrors the
accepted source-cleanup recipe.

Model names are compared by their bare id: runs before 2026-07-26 went to
the native DeepSeek API (``deepseek-v4-pro``), later ones to OpenRouter
(``deepseek/deepseek-v4-pro``).  Same model, same generation.
"""

STAGE_DEFAULTS: dict[str, dict[str, str]] = {
    "passage-cuts": {"model": "deepseek/deepseek-v4-flash", "prompt_ref": "passage-cuts/v001"},
    "passage-triage": {"model": "deepseek/deepseek-v4-flash", "prompt_ref": "passage-triage/v001"},
}

# Stages that no longer exist in the pipeline at all; their runs are
# history, not candidates for re-running.
RETIRED_STAGES = {"passage-segmentation"}


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
