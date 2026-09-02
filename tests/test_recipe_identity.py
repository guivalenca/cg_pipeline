import pytest

from universe import harness
from universe.blocks import BLOCKER_VERSION
from universe.recipe_identity import (
    launch_recipe,
    matches_recipe,
    recipe_fingerprint,
    recipe_identity,
)


@pytest.mark.parametrize("stage", ["passage-cuts", "passage-triage"])
def test_source_cleanup_recipe_stamps_prompt_and_model_request(stage):
    identity = recipe_identity(stage)
    prompt = harness.load_prompt(stage, "v001", require_body=False)

    assert identity["prompt_ref"] == prompt.ref
    assert identity["prompt_sha"] == prompt.sha
    assert identity["model"]
    assert identity["model_params"]["tools"]
    assert len(recipe_fingerprint(stage)) == 64


def test_passage_cuts_recipe_includes_the_block_input_contract():
    identity = recipe_identity("passage-cuts")

    assert identity["input_contract"] == {
        "body_from": "blocks",
        "blocker_version": BLOCKER_VERSION,
    }


def test_recipe_match_ignores_only_operational_run_fields():
    identity = recipe_identity("passage-cuts")
    params = {
        **identity["model_params"],
        **identity["input_contract"],
        "workers": 4,
        "target_manifest": {"sha256": "test"},
    }

    assert matches_recipe(
        "passage-cuts",
        model=identity["model"],
        prompt_ref=identity["prompt_ref"],
        prompt_sha=identity["prompt_sha"],
        params=params,
    )
    assert not matches_recipe(
        "passage-cuts",
        model=identity["model"],
        prompt_ref=identity["prompt_ref"],
        prompt_sha=identity["prompt_sha"],
        params={**params, "unknown_request_flag": True},
    )


def test_launch_recipe_exposes_operational_fields_without_changing_identity():
    launch = launch_recipe("passage-cuts")

    assert launch["workers"] == 16
    assert launch["tool"] == "prompts/passage-cuts/tool-v001.json"
    assert launch["input_contract"] == recipe_identity("passage-cuts")["input_contract"]


def test_removed_stage_has_no_recipe():
    with pytest.raises(ValueError, match="has no model recipe"):
        recipe_identity("generation")
