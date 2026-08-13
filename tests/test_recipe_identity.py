"""Provider-free contracts for the exact recipe behind a live Run Witness."""

from copy import deepcopy
import os
from pathlib import Path
import subprocess
import sys

from universe.recipe_identity import (
    launch_recipe,
    matches_recipe,
    recipe_fingerprint,
    recipe_identity,
)


FROZEN_PIPELINE_RECIPES = {
    "passage-cuts": (
        "deepseek/deepseek-v4-flash", "passage-cuts/v001",
        "ab4d1e9871d626b627fb297dcb029d08a6e5fec3cb0f783a1a719086931bb138",
    ),
    "passage-triage": (
        "deepseek/deepseek-v4-flash", "passage-triage/v001",
        "0d7daaac6b29bc383df5e22a72d7cf00c8e6510c006cbc952ebc2a818239b62d",
    ),
    "task-generation": (
        "deepseek/deepseek-v4-pro", "task-generation/v004",
        "65b6103af811d7ca4f3a0949a81858d277644d65149b4f9fd7e061938944bfea",
    ),
    "task-granularity": (
        "deepseek/deepseek-v4-pro", "task-granularity/v004",
        "f7d993dc664108be18dc52c753c78fca7afef4d207481d0ff7e5d383ce4b528a",
    ),
    "task-revision": (
        "deepseek/deepseek-v4-pro", "task-revision/v004",
        "30a6e347c28b4789afab5520637e966700bc1f659af1f1e41bc3fb50dae2f054",
    ),
    "task-triage": (
        "deepseek/deepseek-v4-flash", "task-triage/v001",
        "82095babcce66eef51d68bf897737693f4966334265495b134016f6140c3cd62",
    ),
    "task-substance": (
        "deepseek/deepseek-v4-pro", "task-substance/v004",
        "8824e48d75e10905165abb6c699588158eb8b78c4e899670e0e96b18aa6b712d",
    ),
    "kc-statement": (
        "deepseek/deepseek-v4-pro", "kc-statement/v005",
        "2c1b9f8ac0c10f51c4a35069772cb8f2b0868f035bdf87282a970ae63b51d44f",
    ),
    "task-modality": (
        "deepseek/deepseek-v4-pro", "task-modality/v003",
        "b7aa3ec494d7470ca05523f0c17d0689950878bf39bf22b2c753bd9c0d7717cb",
    ),
    "task-knowledge": (
        "deepseek/deepseek-v4-pro", "task-knowledge/v003",
        "8d4f17769bef42ec07cab545f12c24004d49ce52c548ed956224ee8928f106e5",
    ),
    "task-embedding": (
        "qwen/qwen3-embedding-8b", "task-embedding/v002",
        "835d46325c3de8740c190ebe7743d4756222eba95b93702195c2ab57c8e73674",
    ),
    "kc-judge": (
        "deepseek/deepseek-v4-flash-0731", "kc-judge/v003-surmise-pair",
        "23ce1be180591d15fd262560755b24581654de402aef489ace14226d03e5e350",
    ),
    "kc-canonical-statement": (
        "deepseek/deepseek-v4-pro", "kc-canonical-statement/v001",
        "842d2cc4d2a3b231b4ebb980e4e484222f34ea8f8cf8cffe892fadb1064e6cc1",
    ),
}

FROZEN_RECIPE_FINGERPRINTS = {
    "passage-cuts": "1bce9f2458910dc97e25f1244ef09fb56443e92cd31d92ad029ee1e23adc7d80",
    "passage-triage": "45babf668f14da50eaa82e5bea6ace3cefc2cd83401f5697e46a7331d69be821",
    "task-generation": "9e7fae0e8fe88ec5a278e479963581576e64c100998db11bf7f948745d832efd",
    "task-granularity": "ab1f36c40c624880111127efd0ecd20e5bf2e528c5b262eb02e9d0f29945acf9",
    "task-revision": "e25acfbc224de1adde605d8ecf177480e70f4deded1f84adfc829bc213f01977",
    "task-triage": "9676bb25f06a30beb8ef08de4f8d1fe193571927490f42a91685ab5b8aa0fdd7",
    "task-substance": "343e993b5e0ec57cc18ea25fe8314c9575f6702f0f4620f7fe73a08390e35df0",
    "kc-statement": "2c98644a5a3f0b73e1f57e059e074dfe1130ff0a1dde6e801a8423d257dc877d",
    "task-modality": "1c04fe4f7ad3da077986be1e72975bde44247e107c641021678247579f712f97",
    "task-knowledge": "07d95f44f0d7ac5b9b8491fa4e3e930038d08ded9bdbb8e097e28b7c6ee81f23",
    "task-embedding": "fc6ed61f12d6648e9dae1d38514aa140dcbafc0800a5440e4707a70c06883038",
    "kc-judge": "95efa6238e236cc1926701e10b8c2815b1c6fc7f3fde98a94130e03a41d6f4f5",
    "kc-canonical-statement": "56cd512f234a6f3af49d96c0a1e65c1a4e7cab2ff41d4651c1112314a6ab0fe5",
}


def test_every_pipeline_recipe_is_frozen_as_one_semantic_contract():
    for stage, expected in FROZEN_PIPELINE_RECIPES.items():
        identity = recipe_identity(stage)
        observed = (
            identity["model"], identity["prompt_ref"], identity["prompt_sha"]
        )
        assert observed == expected, stage
        assert recipe_fingerprint(stage) == FROZEN_RECIPE_FINGERPRINTS[stage], stage


def test_every_model_stage_rejects_unknown_semantic_flags():
    for stage in FROZEN_PIPELINE_RECIPES:
        identity = recipe_identity(stage)
        launch = launch_recipe(stage)
        stamped = deepcopy(identity["model_params"])
        stamped.update(identity["input_contract"])
        stamped["workers"] = 37
        stamped["target_manifest"] = {"sha256": "operational-publication-input"}

        assert launch["model"] == identity["model"], stage
        assert launch["prompt_ref"] == identity["prompt_ref"], stage
        assert launch["workers"] >= 1, stage
        assert matches_recipe(stage, **{
            "model": identity["model"],
            "prompt_ref": identity["prompt_ref"],
            "prompt_sha": identity["prompt_sha"],
            "params": stamped,
        }), stage

        stamped["unknown_provider_flag"] = True
        assert not matches_recipe(stage, **{
            "model": identity["model"],
            "prompt_ref": identity["prompt_ref"],
            "prompt_sha": identity["prompt_sha"],
            "params": stamped,
        }), stage


def test_statement_recipe_contains_every_semantic_input_but_not_concurrency():
    identity = recipe_identity("kc-statement")

    assert identity["model"] == "deepseek/deepseek-v4-pro"
    assert identity["prompt_ref"] == "kc-statement/v005"
    assert identity["prompt_sha"] == (
        "2c1b9f8ac0c10f51c4a35069772cb8f2b0868f035bdf87282a970ae63b51d44f"
    )
    assert identity["model_params"]["max_tokens"] == 65536
    assert identity["model_params"]["reasoning_effort"] == "high"
    assert identity["model_params"]["provider"]["ignore"] == ["SiliconFlow"]
    assert identity["model_params"]["tools"][0]["function"]["name"] == (
        "report_statement"
    )
    assert "workers" not in identity
    assert "workers" not in identity["model_params"]
    assert len(recipe_fingerprint("kc-statement")) == 64


def test_live_witness_requires_exact_prompt_and_inference_but_ignores_workers():
    identity = recipe_identity("task-modality")
    params = deepcopy(identity["model_params"])
    params.update({"workers": 999, "revision_run": "r-revision"})

    assert matches_recipe(
        "task-modality",
        model=identity["model"],
        prompt_ref=identity["prompt_ref"],
        prompt_sha=identity["prompt_sha"],
        params=params,
    )

    wrong_prompt = identity["prompt_sha"][:-1] + "0"
    assert not matches_recipe(
        "task-modality",
        model=identity["model"],
        prompt_ref=identity["prompt_ref"],
        prompt_sha=wrong_prompt,
        params=params,
    )

    wrong_reasoning = deepcopy(params)
    wrong_reasoning["reasoning"] = {"enabled": True}
    assert not matches_recipe(
        "task-modality",
        model=identity["model"],
        prompt_ref=identity["prompt_ref"],
        prompt_sha=identity["prompt_sha"],
        params=wrong_reasoning,
    )

    extra_temperature = deepcopy(params)
    extra_temperature["temperature"] = 1
    assert not matches_recipe(
        "task-modality",
        model=identity["model"],
        prompt_ref=identity["prompt_ref"],
        prompt_sha=identity["prompt_sha"],
        params=extra_temperature,
    )


def test_embedding_and_canonical_recipes_are_first_class_identities():
    embedding = recipe_identity("task-embedding")
    canonical = recipe_identity("kc-canonical-statement")

    assert embedding["prompt_sha"] == (
        "835d46325c3de8740c190ebe7743d4756222eba95b93702195c2ab57c8e73674"
    )
    assert embedding["model_params"] == {}
    assert canonical["prompt_sha"] == (
        "842d2cc4d2a3b231b4ebb980e4e484222f34ea8f8cf8cffe892fadb1064e6cc1"
    )
    assert canonical["model_params"]["max_tokens"] == 1000
    assert canonical["model_params"]["tools"][0]["function"]["name"] == (
        "report_statement"
    )
    assert launch_recipe("task-modality")["workers"] == 1
    assert launch_recipe("kc-canonical-statement")["workers"] == 1
    assert launch_recipe("kc-judge")["workers"] == 16


def test_judge_recipe_does_not_follow_the_process_wide_token_override():
    env = dict(os.environ)
    env["CONCEPT_UNIVERSE_MODEL_MAX_TOKENS"] = "8000"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")

    output = subprocess.check_output(
        [
            sys.executable,
            "-c",
            "from universe.recipe_identity import launch_recipe; "
            "print(launch_recipe('kc-judge')['max_tokens'])",
        ],
        env=env,
        text=True,
    )

    assert output.strip() == "65536"


def test_passage_cuts_requires_its_numbered_block_input_contract():
    identity = recipe_identity("passage-cuts")
    common = {
        "model": identity["model"],
        "prompt_ref": identity["prompt_ref"],
        "prompt_sha": identity["prompt_sha"],
    }

    assert identity["input_contract"] == {
        "body_from": "blocks",
        "blocker_version": "3",
    }
    assert not matches_recipe(
        "passage-cuts", **common, params=identity["model_params"]
    )
    assert not matches_recipe(
        "passage-cuts",
        **common,
        params={
            **identity["model_params"],
            "body_from": "artifact",
            "blocker_version": "3",
        },
    )
    assert matches_recipe(
        "passage-cuts",
        **common,
        params={
            **identity["model_params"],
            "body_from": "blocks",
            "blocker_version": "3",
        },
    )
    assert not matches_recipe(
        "passage-cuts",
        **common,
        params={
            **identity["model_params"],
            "body_from": "blocks",
            "blocker_version": "2",
        },
    )
