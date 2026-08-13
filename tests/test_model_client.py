"""Provider response-shape contracts; every transport is local and fake."""

import pytest

from universe import model_client
from universe.model_client import EmbeddingClient, ModelClient, ModelError


TOOL = {
    "type": "function",
    "function": {
        "name": "record_result",
        "parameters": {"type": "object"},
    },
}


@pytest.fixture(autouse=True)
def deterministic_request_duration(monkeypatch):
    ticks = iter((10.0, 10.125))
    monkeypatch.setattr(model_client.time, "monotonic", lambda: next(ticks))


def _chat_client(body):
    def transport(url, headers, payload, timeout):
        return body

    return ModelClient(
        "request/model",
        api_base="https://example.invalid/v1",
        transport=transport,
    )


def _embedding_client(body):
    def transport(url, headers, payload, timeout):
        return body

    return EmbeddingClient(
        "request/embedding-model",
        api_base="https://example.invalid/v1",
        transport=transport,
    )


def test_complete_wraps_non_mapping_message_with_response_telemetry():
    client = _chat_client(
        {
            "choices": [{"message": "not-an-object"}],
            "usage": {"cost": 0.0042, "total_tokens": 31},
            "provider": "example-provider",
            "model": "response/model",
        }
    )

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.complete("hello")

    assert caught.value.usage == {
        "cost": 0.0042,
        "total_tokens": 31,
        "provider": "example-provider",
        "response_model": "response/model",
    }
    assert caught.value.duration_ms == 125


def test_complete_wraps_non_mapping_tool_call_with_response_telemetry():
    client = _chat_client(
        {
            "choices": [{"message": {"tool_calls": ["not-an-object"]}}],
            "usage": {"cost": 0.0051, "total_tokens": 37},
            "provider": "tool-provider",
            "model": "tool-response/model",
        }
    )

    with pytest.raises(ModelError, match="invalid tool call") as caught:
        client.complete("hello")

    assert caught.value.usage == {
        "cost": 0.0051,
        "total_tokens": 37,
        "provider": "tool-provider",
        "response_model": "tool-response/model",
    }
    assert caught.value.duration_ms == 125


def test_call_tool_wraps_non_mapping_message_with_response_telemetry():
    client = _chat_client(
        {
            "choices": [{"message": ["not", "an", "object"]}],
            "usage": {"cost": 0.0063, "total_tokens": 43},
            "provider": "forced-tool-provider",
            "model": "forced-tool-response/model",
        }
    )

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.call_tool([{"role": "user", "content": "hello"}], TOOL)

    assert caught.value.usage == {
        "cost": 0.0063,
        "total_tokens": 43,
        "provider": "forced-tool-provider",
        "response_model": "forced-tool-response/model",
    }
    assert caught.value.duration_ms == 125


def test_embed_wraps_non_mapping_data_item_with_response_telemetry():
    client = _embedding_client(
        {
            "data": ["not-an-object"],
            "usage": {"cost": 0.0009, "total_tokens": 7},
            "provider": "embedding-provider",
            "model": "response/embedding-model",
        }
    )

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.embed(["hello"])

    assert caught.value.usage == {
        "cost": 0.0009,
        "total_tokens": 7,
        "provider": "embedding-provider",
        "response_model": "response/embedding-model",
    }
    assert caught.value.duration_ms == 125


def test_complete_wraps_non_mapping_response_body_with_duration():
    client = _chat_client(["not", "an", "object"])

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.complete("hello")

    assert caught.value.usage == {}
    assert caught.value.duration_ms == 125


def test_call_tool_wraps_non_mapping_response_body_with_duration():
    client = _chat_client(["not", "an", "object"])

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.call_tool([{"role": "user", "content": "hello"}], TOOL)

    assert caught.value.usage == {}
    assert caught.value.duration_ms == 125


def test_embed_wraps_non_mapping_response_body_with_duration():
    client = _embedding_client(["not", "an", "object"])

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.embed(["hello"])

    assert caught.value.usage == {}
    assert caught.value.duration_ms == 125


def test_complete_wraps_non_mapping_tool_function_with_response_telemetry():
    client = _chat_client(
        {
            "choices": [
                {"message": {"tool_calls": [{"function": "not-an-object"}]}}
            ],
            "usage": {"cost": 0.0074, "total_tokens": 47},
            "provider": "function-provider",
            "model": "function-response/model",
        }
    )

    with pytest.raises(ModelError, match="invalid tool call") as caught:
        client.complete("hello")

    assert caught.value.usage == {
        "cost": 0.0074,
        "total_tokens": 47,
        "provider": "function-provider",
        "response_model": "function-response/model",
    }
    assert caught.value.duration_ms == 125


def test_complete_wraps_non_list_tool_calls_with_response_telemetry():
    client = _chat_client(
        {
            "choices": [{"message": {"tool_calls": 17}}],
            "usage": {"cost": 0.0082, "total_tokens": 53},
            "provider": "calls-provider",
            "model": "calls-response/model",
        }
    )

    with pytest.raises(ModelError, match="invalid tool_calls") as caught:
        client.complete("hello")

    assert caught.value.usage == {
        "cost": 0.0082,
        "total_tokens": 53,
        "provider": "calls-provider",
        "response_model": "calls-response/model",
    }
    assert caught.value.duration_ms == 125


def test_call_tool_wraps_non_mapping_tool_call_with_response_telemetry():
    client = _chat_client(
        {
            "choices": [{"message": {"tool_calls": ["not-an-object"]}}],
            "usage": {"cost": 0.0091, "total_tokens": 59},
            "provider": "forced-item-provider",
            "model": "forced-item-response/model",
        }
    )

    with pytest.raises(ModelError, match="expected tool") as caught:
        client.call_tool([{"role": "user", "content": "hello"}], TOOL)

    assert caught.value.usage == {
        "cost": 0.0091,
        "total_tokens": 59,
        "provider": "forced-item-provider",
        "response_model": "forced-item-response/model",
    }
    assert caught.value.duration_ms == 125


def test_complete_wraps_scalar_response_body_with_duration():
    client = _chat_client(23)

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.complete("hello")

    assert caught.value.usage == {}
    assert caught.value.duration_ms == 125


def test_call_tool_wraps_scalar_response_body_with_duration():
    client = _chat_client(29)

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.call_tool([{"role": "user", "content": "hello"}], TOOL)

    assert caught.value.usage == {}
    assert caught.value.duration_ms == 125


def test_embed_wraps_scalar_response_body_with_duration():
    client = _embedding_client(31)

    with pytest.raises(ModelError, match="unexpected response shape") as caught:
        client.embed(["hello"])

    assert caught.value.usage == {}
    assert caught.value.duration_ms == 125


@pytest.mark.parametrize(
    ("arguments", "error"),
    [
        ("{", "tool returned invalid JSON"),
        ("[]", "tool arguments must be a JSON object"),
    ],
)
def test_call_tool_preserves_response_telemetry_when_arguments_are_invalid(
    arguments, error
):
    client = _chat_client(
        {
            "choices": [
                {
                    "message": {
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "record_result",
                                    "arguments": arguments,
                                }
                            }
                        ]
                    }
                }
            ],
            "usage": {"cost": 0.0103, "total_tokens": 67},
            "provider": "argument-provider",
            "model": "argument-response/model",
        }
    )

    with pytest.raises(ModelError, match=error) as caught:
        client.call_tool([{"role": "user", "content": "hello"}], TOOL)

    assert caught.value.usage == {
        "cost": 0.0103,
        "total_tokens": 67,
        "provider": "argument-provider",
        "response_model": "argument-response/model",
    }
    assert caught.value.duration_ms == 125
