"""Article-image acquisition and pure canonicalization contracts."""

import hashlib
import json
from dataclasses import dataclass

import pytest

from universe.acquisition import articles
from universe.acquisition.article_images import (
    ARTICLE_IMAGE_TOOL,
    ArticleImageAnalysis,
    ArticleImageModelResult,
    analyze_article_image,
    associate_article_images,
    deterministic_image_analysis,
    extract_markdown_images,
)
from universe.acquisition.articles import fetch_article_detailed
from universe.blocks import split_blocks
from universe.model_client import ModelClient, ModelError


@dataclass
class _Response:
    status_code: int
    payload: dict
    headers: dict[str, str] | None = None

    def json(self):
        return self.payload


def test_firecrawl_preserves_raw_markdown_and_ordered_unique_image_urls(monkeypatch):
    requests = []

    def post(url, *, headers, json, timeout):
        requests.append((url, headers, json, timeout))
        return _Response(
            200,
            {
                "data": {
                    "markdown": "# Lesson\n\n![Chart](https://cdn.test/chart.png)\n",
                    "images": [
                        "https://cdn.test/chart.png",
                        None,
                        "  ",
                        "https://cdn.test/chart.png",
                        " https://cdn.test/photo.jpg ",
                        {"url": "https://cdn.test/ignored-shape.png"},
                    ],
                }
            },
            {},
        )

    monkeypatch.setenv("FIRECRAWL_API_KEY", "test-key")
    monkeypatch.setattr(articles.httpx, "post", post)

    result = fetch_article_detailed(
        {"identity": {"canonical_url": "https://example.test/lesson"}}
    )

    assert requests[0][2] == {
        "url": "https://example.test/lesson",
        "formats": ["markdown", "images"],
        "timeout": 60_000,
    }
    assert result.markdown == "# Lesson\n\n![Chart](https://cdn.test/chart.png)\n"
    assert result.raw_markdown == result.markdown
    assert result.image_urls == (
        "https://cdn.test/chart.png",
        "https://cdn.test/photo.jpg",
    )


def test_markdown_image_references_preserve_order_and_exact_source_slices():
    markdown = """Before

[![Chart](https://cdn.test/chart.png)](https://example.test/data)

![Photo](https://cdn.test/photo.jpg "Source photo")

After
"""

    references = extract_markdown_images(markdown)

    assert [reference.source_url for reference in references] == [
        "https://cdn.test/chart.png",
        "https://cdn.test/photo.jpg",
    ]
    assert [reference.alt_text for reference in references] == ["Chart", "Photo"]
    assert references[0].link_url == "https://example.test/data"
    assert references[1].link_url is None
    assert all(
        markdown[reference.start_char : reference.end_char]
        == reference.original_markdown
        for reference in references
    )


def test_deterministic_filter_removes_only_strong_web_chrome_signals():
    references = extract_markdown_images(
        """![Share on LinkedIn](https://cdn.test/icons/linkedin-logo.png)

![Experiment results](https://cdn.test/figures/results-chart.png)
"""
    )

    chrome = deterministic_image_analysis(references[0])
    chart = deterministic_image_analysis(references[1])

    assert chrome is not None
    assert chrome.pedagogical_importance == "not_important"
    assert chrome.description == ""
    assert chrome.visible_text == ""
    assert chrome.confidence == "high"
    assert chart is None


def test_deterministic_filter_does_not_remove_pedagogical_logo_or_avatar_topics():
    references = extract_markdown_images(
        """![Logo design exercise](https://cdn.test/logo-design-exercise.png)

![Customer avatar model](https://cdn.test/customer-avatar-framework.png)
"""
    )

    assert [deterministic_image_analysis(reference) for reference in references] == [
        None,
        None,
    ]


def test_article_image_analysis_uses_one_forced_strict_tool_call():
    payloads = []

    def transport(_url, _headers, payload, _timeout):
        payloads.append(payload)
        return {
            "model": "provider/resolved-vision",
            "provider": "Example Provider",
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "report_article_image",
                                    "arguments": (
                                        '{"pedagogical_importance":"important",'
                                        '"description":"A line chart rises over time.",'
                                        '"visible_text":"2024  2025",'
                                        '"reason":"The trend is evidence for the lesson.",'
                                        '"confidence":"high"}'
                                    ),
                                }
                            }
                        ]
                    }
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 12},
        }

    reference = extract_markdown_images(
        "![Results](https://cdn.test/results.png)"
    )[0]
    client = ModelClient(
        "requested/vision",
        api_base="https://openrouter.test/v1",
        api_key="test-key",
        transport=transport,
    )

    result = analyze_article_image(
        reference,
        client=client,
        image_url="https://assets.test/local/results.png",
        context="The surrounding paragraph discusses yearly growth.",
        asset_sha256="b" * 64,
    )

    payload = payloads[0]
    assert payload["tools"] == [ARTICLE_IMAGE_TOOL]
    assert payload["tool_choice"] == {
        "type": "function",
        "function": {"name": "report_article_image"},
    }
    assert payload["parallel_tool_calls"] is False
    assert payload["messages"][0]["content"][1] == {
        "type": "image_url",
        "image_url": {
            "url": "https://assets.test/local/results.png",
            "detail": "high",
        },
    }
    assert result.analysis.pedagogical_importance == "important"
    assert result.analysis.description == "A line chart rises over time."
    assert result.analysis.visible_text == "2024  2025"
    assert result.requested_model == "requested/vision"
    assert result.response_model == "provider/resolved-vision"
    assert result.provider == "Example Provider"
    assert result.reference_id.startswith("article-image-ref:0001:")
    assert result.source_url == "https://cdn.test/results.png"
    assert result.model_image_url == "https://assets.test/local/results.png"
    assert len(result.input_sha256) == 64
    assert result.asset_sha256 == "b" * 64


def test_article_image_analysis_preserves_contradictory_non_decorative_content():
    def transport(_url, _headers, _payload, _timeout):
        return {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "report_article_image",
                                    "arguments": (
                                        '{"pedagogical_importance":"not_important",'
                                        '"description":"",'
                                        '"visible_text":"Revenue increased 20%",'
                                        '"reason":"It looks decorative.",'
                                        '"confidence":"low"}'
                                    ),
                                }
                            }
                        ]
                    }
                }
            ]
        }

    reference = extract_markdown_images("![Chart](https://cdn.test/chart.png)")[0]
    client = ModelClient(
        "requested/vision",
        api_base="https://openrouter.test/v1",
        transport=transport,
    )

    result = analyze_article_image(reference, client=client)

    assert result.analysis.pedagogical_importance == "important"
    assert result.analysis.visible_text == "Revenue increased 20%"
    assert result.analysis.description == "The image contains meaningful legible text."
    assert result.analysis.confidence == "low"
    assert "Preserved because" in result.analysis.reason


def test_optional_association_preserves_local_and_unanalyzed_images():
    raw_markdown = """# Lesson

![Results](https://cdn.test/results.png)

![LinkedIn logo](https://cdn.test/linkedin-logo.png)

![Uncertain photo](https://cdn.test/photo.jpg)
"""
    first_reference = extract_markdown_images(raw_markdown)[0]
    analyses = {
        1: ArticleImageModelResult(
            analysis=ArticleImageAnalysis(
                pedagogical_importance="important",
                description="A line chart rises from 2024 to 2025.",
                visible_text="2024  2025",
                reason="The trend supports the article's claim.",
                confidence="high",
            ),
            requested_model="requested/vision",
            response_model="provider/resolved-vision",
            provider="Example Provider",
            usage={"prompt_tokens": 20, "completion_tokens": 12},
            duration_ms=35,
            reference_id=first_reference.reference_id,
            source_url=first_reference.source_url,
            model_image_url="https://assets.test/results.png",
            input_sha256="a" * 64,
            asset_sha256="b" * 64,
        ),
    }

    result = associate_article_images(
        raw_markdown,
        analyses=analyses,
        local_url_for=lambda reference: (
            None
            if reference.ordinal == 3
            else f"/article-assets/{reference.ordinal}"
        ),
    )

    assert result.raw_markdown == raw_markdown
    assert "![Results](/article-assets/1)" in result.canonical_markdown
    assert (
        "Image description: A line chart rises from 2024 to 2025.\n"
        "OCR: 2024  2025"
    ) in result.canonical_markdown
    assert "![LinkedIn logo](/article-assets/2)" in result.canonical_markdown
    assert "![Uncertain photo](https://cdn.test/photo.jpg)" in result.canonical_markdown
    assert result.canonical_markdown.count("Image description:") == 1
    assert "image" in {
        block.kind for block in split_blocks(result.canonical_markdown)
    }
    assert result.manifest["raw_sha256"] == hashlib.sha256(
        raw_markdown.encode("utf-8")
    ).hexdigest()
    assert result.manifest["canonical_sha256"] == hashlib.sha256(
        result.canonical_markdown.encode("utf-8")
    ).hexdigest()
    assert [item["action"] for item in result.manifest["images"]] == [
        "summarized",
        "preserved_unanalyzed",
        "preserved_original_missing_local",
    ]
    assert result.manifest["images"][0]["reference_id"] == first_reference.reference_id
    assert result.manifest["images"][0]["replacement_sha256"] == hashlib.sha256(
        (
            "![Results](/article-assets/1)\n"
            "Image description: A line chart rises from 2024 to 2025.\n"
            "OCR: 2024  2025"
        ).encode("utf-8")
    ).hexdigest()
    assert result.manifest["images"][1]["replacement_sha256"] == hashlib.sha256(
        (
            "![LinkedIn logo](/article-assets/2)\n"
            "Image analysis: unresolved"
        ).encode("utf-8")
    ).hexdigest()
    assert result.manifest["images"][0]["model"] == {
        "requested": "requested/vision",
        "response": "provider/resolved-vision",
        "provider": "Example Provider",
            "prompt_version": "article-image-analysis.v2",
        "usage": {"prompt_tokens": 20, "completion_tokens": 12},
        "duration_ms": 35,
        "reference_id": first_reference.reference_id,
        "source_url": "https://cdn.test/results.png",
        "model_image_transport": "remote_url",
        "input_sha256": "a" * 64,
        "asset_sha256": "b" * 64,
    }


def test_association_manifest_never_persists_an_inline_image_data_url():
    raw_markdown = "![Diagram](https://cdn.test/diagram.png)\n"
    reference = extract_markdown_images(raw_markdown)[0]
    result = associate_article_images(
        raw_markdown,
        analyses={
            1: ArticleImageModelResult(
                analysis=ArticleImageAnalysis(
                    pedagogical_importance="important",
                    description="A useful diagram.",
                    visible_text="",
                    reason="It explains the source.",
                    confidence="high",
                ),
                requested_model="requested/vision",
                response_model="resolved/vision",
                provider="Provider",
                usage={},
                duration_ms=1,
                reference_id=reference.reference_id,
                source_url=reference.source_url,
                model_image_url="data:image/png;base64,very-large-payload",
                input_sha256="a" * 64,
                asset_sha256="b" * 64,
            )
        },
        local_url_for=lambda _reference: "/api/source-assets/diagram",
    )

    serialized = json.dumps(result.manifest)
    assert "data:image" not in serialized
    assert result.manifest["images"][0]["model"]["model_image_transport"] == "data_url"


def test_association_rejects_model_result_bound_to_another_image_occurrence():
    raw_markdown = """![First](https://cdn.test/shared.png)

![Second](https://cdn.test/shared.png)
"""
    first, _second = extract_markdown_images(raw_markdown)
    result_for_first = ArticleImageModelResult(
        analysis=ArticleImageAnalysis(
            pedagogical_importance="important",
            description="A reusable diagram.",
            visible_text="",
            reason="The relationships support the lesson.",
            confidence="high",
        ),
        requested_model="requested/vision",
        response_model="provider/resolved-vision",
        provider="Example Provider",
        usage={},
        duration_ms=10,
        reference_id=first.reference_id,
        source_url=first.source_url,
        model_image_url="https://assets.test/shared.png",
        input_sha256="a" * 64,
    )

    with pytest.raises(ValueError, match="does not match the Markdown reference"):
        associate_article_images(
            raw_markdown,
            analyses={2: result_for_first},
            local_url_for=lambda reference: f"/article-assets/{reference.ordinal}",
        )


def test_low_confidence_not_important_decision_never_removes_an_image():
    raw_markdown = "![Possible diagram](https://cdn.test/possible.png)\n"
    result = associate_article_images(
        raw_markdown,
        analyses={
            1: ArticleImageAnalysis(
                pedagogical_importance="not_important",
                description="",
                visible_text="",
                reason="The visual may be decorative.",
                confidence="low",
            )
        },
        local_url_for=lambda _reference: "/article-assets/possible",
    )

    assert "![Possible diagram](/article-assets/possible)" in result.canonical_markdown
    assert result.manifest["images"][0]["action"] == "preserved_low_confidence"
