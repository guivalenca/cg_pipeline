import json

import pytest


def test_fixture_model_matches_stage_inputs_without_provider_calls(tmp_path):
    from concept_graph_creation.runtime.fixture_model import FixtureModelClient

    manifest = tmp_path / "fixture-model.json"
    manifest.write_text(
        json.dumps(
                {
                    "schema_version": "creation_fixture_model.v1",
                    "response_replacements": {"one": "um"},
                "responses": [
                    {
                        "stage_name": "self_study_extraction",
                        "input_subset": {
                            "input.json": {
                                "self_study": {"self_study_id": "source-2"},
                                "candidate_ids": ["candidate-2"],
                            }
                        },
                        "response": {"candidate_concepts": [{"candidate_id": "two"}]},
                    },
                    {
                        "stage_name": "self_study_extraction",
                        "input_subset": {
                            "input.json": {
                                "self_study": {"self_study_id": "source-1"},
                                "candidate_ids": ["candidate-1"],
                            }
                        },
                        "response": {"candidate_concepts": [{"candidate_id": "one"}]},
                    },
                ],
            }
        ),
        encoding="utf-8",
    )
    client = FixtureModelClient.from_file(manifest)

    first = client(
        stage_name="self_study_extraction",
        inputs={
            "input.json": {
                "self_study": {"self_study_id": "source-1"},
                "candidate_ids": ["candidate-1", "candidate-shared"],
            }
        },
    )
    second = client(
        stage_name="self_study_extraction",
        inputs={
            "input.json": {
                "self_study": {"self_study_id": "source-2"},
                "candidate_ids": ["candidate-2", "candidate-shared"],
            }
        },
    )

    assert json.loads(first)["candidate_concepts"][0]["candidate_id"] == "um"
    assert json.loads(second)["candidate_concepts"][0]["candidate_id"] == "two"
    client.assert_exhausted()


def test_fixture_model_fails_explicitly_when_no_response_matches(tmp_path):
    from concept_graph_creation.runtime.fixture_model import (
        FixtureModelClient,
        FixtureResponseMissing,
    )

    manifest = tmp_path / "fixture-model.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": "creation_fixture_model.v1",
                "responses": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(FixtureResponseMissing, match="no response for stage"):
        FixtureModelClient.from_file(manifest)(stage_name="unexpected", inputs={})
