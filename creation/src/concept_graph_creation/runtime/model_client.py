from __future__ import annotations

import json
import os
import socket
import ssl
import http.client
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from concept_graph_creation.runtime.stage_runner import ModelRoute, StageBlockedError


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_MAX_TOKENS = 12000


class PipelineModelClient:
    def __init__(
        self,
        *,
        api_keys: Mapping[str, str],
        base_urls: Mapping[str, str] | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ) -> None:
        self.api_keys = dict(api_keys)
        self.base_urls = dict(base_urls or {"deepseek": DEEPSEEK_BASE_URL})
        self.timeout_seconds = timeout_seconds
        self.max_tokens = max_tokens

    @classmethod
    def from_env(cls, *, project_root: Path) -> "PipelineModelClient":
        _load_dotenv(project_root.parent / ".env", allowed_keys={"DEEPSEEK_API_KEY_ADMIN"})

        deepseek_key = os.environ.get("DEEPSEEK_API_KEY_ADMIN", "").strip()
        if not deepseek_key:
            raise StageBlockedError(
                "DeepSeek model call is not configured. Set DEEPSEEK_API_KEY_ADMIN in cg_pipeline/.env, "
                "or rerun with --deterministic-fixture for an offline fixture run."
            )

        return cls(
            api_keys={"deepseek": deepseek_key},
            base_urls={"deepseek": os.environ.get("DEEPSEEK_BASE_URL", "").strip() or DEEPSEEK_BASE_URL},
            timeout_seconds=int(os.environ.get("CG_PIPELINE_MODEL_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
            max_tokens=int(os.environ.get("CG_PIPELINE_MODEL_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        )

    def call(
        self,
        *,
        route: ModelRoute,
        stage_name: str,
        inputs: dict[str, Any],
        repair_context: dict[str, Any] | None = None,
    ) -> str:
        if route.provider != "deepseek":
            raise StageBlockedError(
                f"Provider '{route.provider}' for route '{route.alias}' is not wired for live pipeline model calls"
            )

        api_key = self.api_keys.get(route.provider, "")
        if not api_key:
            raise StageBlockedError(f"API key for provider '{route.provider}' is not configured")

        payload = {
            "model": route.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are executing a Concept Graph Pipeline stage. "
                        "Return one valid JSON object only. Do not include markdown fences, commentary, or prose."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "stage_name": stage_name,
                            "route_alias": route.alias,
                            "inputs": inputs,
                            "repair_context": repair_context,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "response_format": {"type": "json_object"},
            "max_tokens": self.max_tokens,
        }
        payload["thinking"] = {"type": "enabled" if route.thinking_enabled else "disabled"}
        if route.reasoning_effort:
            payload["reasoning_effort"] = route.reasoning_effort
        return self._post_chat_completion(route.provider, payload)

    def _post_chat_completion(self, provider: str, payload: dict[str, Any]) -> str:
        base_url = self.base_urls[provider].rstrip("/")
        ssl_context = _ssl_context()
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_keys[provider]}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds, context=ssl_context) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:1000]
            raise StageBlockedError(f"DeepSeek HTTP {exc.code}: {detail}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise StageBlockedError(f"DeepSeek request timed out while reading response: {exc}") from exc
        except urllib.error.URLError as exc:
            raise StageBlockedError(f"DeepSeek request failed: {exc.reason}") from exc
        except (ConnectionError, http.client.IncompleteRead, http.client.RemoteDisconnected) as exc:
            raise StageBlockedError(f"DeepSeek request failed while reading response: {exc}") from exc

        try:
            response_payload = json.loads(body)
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise StageBlockedError(f"DeepSeek returned an unexpected response shape: {body[:1000]}") from exc
        if not isinstance(content, str) or not content.strip():
            raise StageBlockedError("DeepSeek returned an empty message")
        return content


def _load_dotenv(path: Path, *, allowed_keys: set[str]) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in allowed_keys or key in os.environ:
            continue
        os.environ[key] = _unquote_env_value(value.strip())


def _unquote_env_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())
