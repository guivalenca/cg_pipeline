"""Pure source-level image prompt, tool and reconciliation contracts."""

import json

from universe.acquisition.source_images import (
    SourceImageInput,
    analyze_source_images,
    prompt_stamp,
    reconcile_source_image_results,
)
from universe.model_client import ModelClient


def _image(image_id: str) -> SourceImageInput:
    return SourceImageInput(
        image_id=image_id,
        alt_text=f"Alt {image_id}",
        source_url=f"https://cdn.test/{image_id}.png",
        model_image_url=f"data:image/png;base64,{image_id}",
        asset_sha256=("a" if image_id == "image-1" else "b") * 64,
        model_input_sha256=("c" if image_id == "image-1" else "d") * 64,
    )


def test_one_forced_tool_call_analyzes_every_source_image():
    payloads = []

    def transport(_url, _headers, payload, _timeout):
        payloads.append(payload)
        return {
            "model": "google/gemini-resolved",
            "provider": "Google",
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "report_source_images",
                                    "arguments": json.dumps(
                                        {
                                            "images": [
                                                {
                                                    "image_id": "image-2",
                                                    "retain": False,
                                                    "reason_code": "decoration",
                                                    "ocr": None,
                                                    "description": None,
                                                    "limitations": None,
                                                },
                                                {
                                                    "image_id": "image-1",
                                                    "retain": True,
                                                    "reason_code": "information",
                                                    "ocr": "Accuracy 92%",
                                                    "description": "A result chart.",
                                                    "limitations": None,
                                                },
                                            ]
                                        }
                                    ),
                                }
                            }
                        ]
                    }
                }
            ],
            "usage": {"total_tokens": 42},
        }

    client = ModelClient(
        "google/gemini-requested",
        api_base="https://openrouter.test/v1",
        transport=transport,
    )
    result = analyze_source_images(
        "# Source\n\nThe chart reports model accuracy.",
        [_image("image-1"), _image("image-2")],
        client=client,
    )

    assert len(payloads) == 1
    content = payloads[0]["messages"][0]["content"]
    assert len(content) == 5
    assert content[0]["text"].count("# Source") == 1
    assert [item["type"] for item in content] == [
        "text",
        "text",
        "image_url",
        "text",
        "image_url",
    ]
    assert "image_id: image-1" in content[1]["text"]
    assert "image_id: image-2" in content[3]["text"]
    assert payloads[0]["tool_choice"]["function"]["name"] == "report_source_images"
    assert set(result.analyses) == {"image-1", "image-2"}
    assert result.analyses["image-1"].ocr == "Accuracy 92%"
    assert result.analyses["image-2"].retain is False
    assert result.unresolved == {}
    assert result.usage == {"total_tokens": 42}
    assert len(result.input_manifest_hash) == 64


def test_active_prompt_requires_teachable_content_not_represented_by_source_text():
    prompt_ref, _prompt_sha, template = prompt_stamp()

    assert prompt_ref == "source-image-analysis/v002"
    assert (
        "Retain an image only when it adds teachable content that is not "
        "adequately represented by the source text."
    ) in template


def test_reconciliation_is_fail_open_per_missing_duplicate_or_invalid_image():
    arguments = {
        "images": [
            {
                "image_id": "image-1",
                "retain": False,
                "reason_code": "decoration",
                "ocr": None,
                "description": None,
                "limitations": None,
            },
            {
                "image_id": "image-1",
                "retain": True,
                "reason_code": "information",
                "ocr": None,
                "description": "Duplicate answer",
                "limitations": None,
            },
            {
                "image_id": "image-2",
                "retain": False,
                "reason_code": "insufficient_evidence",
                "ocr": None,
                "description": None,
                "limitations": None,
            },
            {
                "image_id": "unknown",
                "retain": False,
                "reason_code": "decoration",
                "ocr": None,
                "description": None,
                "limitations": None,
            },
        ]
    }

    analyses, unresolved = reconcile_source_image_results(
        arguments, ["image-1", "image-2", "image-3"]
    )

    assert analyses == {}
    assert unresolved == {
        "image-1": "duplicate_result",
        "image-2": "invalid_result",
        "image-3": "missing_result",
    }
