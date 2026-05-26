import json
import socket
import urllib.request

import pytest

from concept_graph_creation.runtime.model_client import PipelineModelClient
from concept_graph_creation.runtime.stage_runner import (
    ModelRoute,
    PRO_ROUTE_ALIAS,
    PRO_THINKING_ROUTE_ALIAS,
    StageBlockedError,
)


def test_model_client_from_env_requires_deepseek_key(tmp_path, monkeypatch):
    project_root = tmp_path / "repo" / "cg_pipeline" / "creation"
    project_root.mkdir(parents=True)
    monkeypatch.delenv("DEEPSEEK_API_KEY_ADMIN", raising=False)
    (project_root.parents[1] / ".env").write_text("DEEPSEEK_API_KEY_ADMIN=repo-root-key\n", encoding="utf-8")
    (project_root / ".env").write_text("DEEPSEEK_API_KEY_ADMIN=creation-key\n", encoding="utf-8")

    with pytest.raises(StageBlockedError, match="Set DEEPSEEK_API_KEY_ADMIN in cg_pipeline/.env"):
        PipelineModelClient.from_env(project_root=project_root)


def test_model_client_loads_deepseek_key_from_pipeline_env_file(tmp_path, monkeypatch):
    project_root = tmp_path / "repo" / "cg_pipeline" / "creation"
    project_root.mkdir(parents=True)
    (project_root.parent / ".env").write_text("DEEPSEEK_API_KEY_ADMIN=from-file\n", encoding="utf-8")
    monkeypatch.delenv("DEEPSEEK_API_KEY_ADMIN", raising=False)

    client = PipelineModelClient.from_env(project_root=project_root)

    assert client.api_keys["deepseek"] == "from-file"


def test_model_client_ignores_non_admin_deepseek_key(tmp_path, monkeypatch):
    project_root = tmp_path / "repo" / "cg_pipeline" / "creation"
    project_root.mkdir(parents=True)
    (project_root.parent / ".env").write_text("DEEPSEEK_API_KEY=wrong-key\n", encoding="utf-8")
    monkeypatch.delenv("DEEPSEEK_API_KEY_ADMIN", raising=False)

    with pytest.raises(StageBlockedError, match="Set DEEPSEEK_API_KEY_ADMIN in cg_pipeline/.env"):
        PipelineModelClient.from_env(project_root=project_root)


def test_model_client_posts_openai_compatible_deepseek_request(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": '{"artifact_type":"demo"}'}}]},
                ensure_ascii=False,
            ).encode("utf-8")

    def fake_urlopen(request, timeout, context=None):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["context"] = context
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = PipelineModelClient(
        api_keys={"deepseek": "secret-key"},
        base_urls={"deepseek": "https://deepseek.test"},
        timeout_seconds=7,
        max_tokens=123,
    )

    content = client.call(
        route=ModelRoute(
            alias=PRO_THINKING_ROUTE_ALIAS,
            provider="deepseek",
            model="deepseek-v4-pro",
            reasoning_effort="high",
        ),
        stage_name="demo_stage",
        inputs={"input.json": {"value": 1}},
        repair_context={"repair_type": "format_repair"},
    )

    assert content == '{"artifact_type":"demo"}'
    assert captured["url"] == "https://deepseek.test/chat/completions"
    assert captured["timeout"] == 7
    assert captured["context"] is not None
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["payload"]["model"] == "deepseek-v4-pro"
    assert captured["payload"]["thinking"] == {"type": "enabled"}
    assert captured["payload"]["reasoning_effort"] == "high"
    assert captured["payload"]["max_tokens"] == 123
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    user_payload = json.loads(captured["payload"]["messages"][1]["content"])
    assert user_payload["stage_name"] == "demo_stage"
    assert user_payload["inputs"] == {"input.json": {"value": 1}}
    assert user_payload["repair_context"] == {"repair_type": "format_repair"}


def test_model_client_disables_deepseek_thinking_for_pro_route(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"choices":[{"message":{"content":"{}"}}]}'

    def fake_urlopen(request, timeout, context=None):
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = PipelineModelClient(api_keys={"deepseek": "secret-key"})

    client.call(
        route=ModelRoute(
            alias=PRO_ROUTE_ALIAS,
            provider="deepseek",
            model="deepseek-v4-pro",
            thinking_enabled=False,
            reasoning_effort=None,
        ),
        stage_name="demo_stage",
        inputs={},
    )

    assert captured["payload"]["model"] == "deepseek-v4-pro"
    assert captured["payload"]["thinking"] == {"type": "disabled"}
    assert "reasoning_effort" not in captured["payload"]


def test_model_client_converts_response_read_timeout_to_stage_blocked_error(monkeypatch):
    class TimeoutResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            raise TimeoutError("The read operation timed out")

    def fake_urlopen(_request, timeout, context=None):
        return TimeoutResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = PipelineModelClient(api_keys={"deepseek": "secret-key"})

    with pytest.raises(StageBlockedError, match="DeepSeek request timed out"):
        client.call(
            route=ModelRoute(
                alias=PRO_THINKING_ROUTE_ALIAS,
                provider="deepseek",
                model="deepseek-v4-pro",
                reasoning_effort="high",
            ),
            stage_name="demo_stage",
            inputs={},
        )


def test_model_client_converts_socket_read_timeout_to_stage_blocked_error(monkeypatch):
    class TimeoutResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            raise socket.timeout("timed out")

    def fake_urlopen(_request, timeout, context=None):
        return TimeoutResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    client = PipelineModelClient(api_keys={"deepseek": "secret-key"})

    with pytest.raises(StageBlockedError, match="DeepSeek request timed out"):
        client.call(
            route=ModelRoute(
                alias=PRO_THINKING_ROUTE_ALIAS,
                provider="deepseek",
                model="deepseek-v4-pro",
                reasoning_effort="high",
            ),
            stage_name="demo_stage",
            inputs={},
        )
