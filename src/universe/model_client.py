"""A minimal OpenAI-chat-completions client, stdlib only.

Configured by MODEL_API_BASE and MODEL_API_KEY; the model id is passed per
call, because switching models is the point of the harness.

The transport is a plain function (url, headers, payload, timeout) -> parsed
JSON, so tests hand in a fake one and never touch the network.
"""

import json
import os
import time
import urllib.error
import urllib.request

DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("CONCEPT_UNIVERSE_MODEL_TIMEOUT_SECONDS", 300))
DEFAULT_MAX_TOKENS = int(os.environ.get("CONCEPT_UNIVERSE_MODEL_MAX_TOKENS", 8000))


class ModelError(RuntimeError):
    """The call did not come back with a usable completion."""


def http_transport(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise ModelError(f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}") from exc
    except urllib.error.URLError as exc:
        raise ModelError(f"transport failure: {exc.reason}") from exc


class ModelClient:
    """One endpoint and one model; `complete` is the whole surface."""

    def __init__(
        self,
        model: str,
        *,
        api_base: str | None = None,
        api_key: str | None = None,
        temperature: float | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        extra: dict | None = None,
        transport=http_transport,
    ) -> None:
        self.model = model
        self.api_base = (api_base or os.environ.get("MODEL_API_BASE", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("MODEL_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.extra = extra or {}
        self.transport = transport

    @property
    def params(self) -> dict:
        """The model parameters worth stamping on a run."""
        params = {"max_tokens": self.max_tokens}
        if self.temperature is not None:
            params["temperature"] = self.temperature
        params.update(self.extra)
        return params

    def complete(self, prompt: str) -> tuple[str, dict, int]:
        """Send one prompt. Returns (text, usage, duration_ms)."""
        if not self.api_base:
            raise ModelError("MODEL_API_BASE is not set")
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.max_tokens,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        payload.update(self.extra)
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        started = time.monotonic()
        body = self.transport(f"{self.api_base}/chat/completions", headers, payload, self.timeout)
        duration_ms = int((time.monotonic() - started) * 1000)
        text = extract_text(body, require_tool="tools" in payload)
        return text, body.get("usage") or {}, duration_ms


def extract_text(body: dict, require_tool: bool = False) -> str:
    """Pull the completion out, or say plainly what came back instead.

    A response that carries tool calls yields the call's raw arguments string:
    with a declared tool that IS the completion. The prompt asks for one call,
    so more than one is an error, not something to silently pick from. When a
    tool was declared (`require_tool`), prose instead of a call is an error
    too: it happens when the API forbids forcing (thinking mode), and the
    answer must be a recorded failure to rerun, never accepted as if parsed.
    """
    if "error" in body:
        raise ModelError(f"api error: {json.dumps(body['error'])[:500]}")
    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelError(f"unexpected response shape: {json.dumps(body)[:500]}") from exc
    calls = message.get("tool_calls")
    if calls:
        if len(calls) != 1:
            raise ModelError(f"expected one tool call, got {len(calls)}")
        arguments = (calls[0].get("function") or {}).get("arguments")
        if not arguments or not isinstance(arguments, str):
            raise ModelError(f"tool call without arguments: {json.dumps(calls[0])[:500]}")
        return arguments
    if require_tool:
        raise ModelError("prose instead of the declared tool call")
    text = message.get("content")
    if not text:
        raise ModelError(f"empty completion (finish_reason={body['choices'][0].get('finish_reason')})")
    if not isinstance(text, str):
        raise ModelError(f"content is not text: {json.dumps(text)[:500]}")
    return text
