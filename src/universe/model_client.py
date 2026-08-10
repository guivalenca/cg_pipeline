"""A minimal OpenAI-chat-completions client, stdlib only, configured by
MODEL_API_BASE and MODEL_API_KEY, defaulting to OpenRouter with either
OPENROUTER_API_KEY or the legacy OPEN_ROUTER_API_KEY spelling.

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
DEFAULT_API_BASE = "https://openrouter.ai/api/v1"


class ModelError(RuntimeError):
    """The call did not come back with a usable completion."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.usage: dict = {}
        self.duration_ms: int = 0


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
        resolved_api_base = (
            api_base
            if api_base is not None
            else os.environ.get("MODEL_API_BASE") or DEFAULT_API_BASE
        )
        self.api_base = resolved_api_base.rstrip("/")
        self.api_key = (
            api_key
            if api_key is not None
            else os.environ.get("MODEL_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("OPEN_ROUTER_API_KEY")
            or ""
        )
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
        usage = dict(body.get("usage") or {})
        if body.get("provider"):
            usage["provider"] = body["provider"]
        if body.get("model"):
            usage["response_model"] = body["model"]
        try:
            text = extract_text(body, require_tool="tools" in payload)
        except ModelError as exc:
            # A syntactically valid provider response can still violate the
            # forced-tool contract. Preserve its billed usage for a controlled
            # application-level failover instead of making that attempt vanish.
            exc.usage = usage
            exc.duration_ms = duration_ms
            raise
        return text, usage, duration_ms

    def call_tool(
        self, messages: list[dict], tool: dict
    ) -> tuple[dict, dict, int]:
        """Force exactly one named tool call over arbitrary chat content.

        ``messages`` may contain OpenAI-compatible multimodal content blocks.
        The payload surface stays generic while the declared schema and the
        parsed arguments remain caller-owned.  Provider response bodies and
        request media are never returned as telemetry.
        """
        if not self.api_base:
            raise ModelError("MODEL_API_BASE is not set")
        try:
            tool_name = tool["function"]["name"]
        except (KeyError, TypeError) as exc:
            raise ModelError("tool must declare function.name") from exc
        if not isinstance(tool_name, str) or not tool_name:
            raise ModelError("tool must declare function.name")

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
        }
        if self.temperature is not None:
            payload["temperature"] = self.temperature
        payload.update(self.extra)
        # These fields are intentionally written after ``extra``: callers may
        # configure routing there, but cannot accidentally weaken the forced
        # one-tool output contract.
        payload.update(
            {
                "tools": [tool],
                "tool_choice": {
                    "type": "function",
                    "function": {"name": tool_name},
                },
                "parallel_tool_calls": False,
            }
        )
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        started = time.monotonic()
        body = self.transport(
            f"{self.api_base}/chat/completions", headers, payload, self.timeout
        )
        duration_ms = int((time.monotonic() - started) * 1000)
        raw_arguments = extract_tool_arguments(body, expected_tool=tool_name)
        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError as exc:
            raise ModelError(f"tool returned invalid JSON: {exc.msg}") from exc
        if not isinstance(arguments, dict):
            raise ModelError("tool arguments must be a JSON object")

        usage = dict(body.get("usage") or {})
        if body.get("provider"):
            usage["provider"] = body["provider"]
        if body.get("model"):
            usage["response_model"] = body["model"]
        return arguments, usage, duration_ms


class EmbeddingClient:
    """Embed texts to vectors via the model endpoint."""

    def __init__(
        self,
        model: str,
        *,
        api_base: str | None = None,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        transport=http_transport,
    ) -> None:
        self.model = model
        resolved_api_base = (
            api_base
            if api_base is not None
            else os.environ.get("MODEL_API_BASE") or DEFAULT_API_BASE
        )
        self.api_base = resolved_api_base.rstrip("/")
        self.api_key = (
            api_key
            if api_key is not None
            else os.environ.get("MODEL_API_KEY")
            or os.environ.get("OPENROUTER_API_KEY")
            or os.environ.get("OPEN_ROUTER_API_KEY")
            or ""
        )
        self.timeout = timeout
        self.transport = transport

    def embed(self, texts: list[str]) -> tuple[list[list[float]], dict, int]:
        """Send texts for embedding and return vectors, usage, and duration."""
        if not self.api_base:
            raise ModelError("api_base is not set")
        payload = {
            "model": self.model,
            "input": texts,
        }
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        started = time.monotonic()
        body = self.transport(f"{self.api_base}/embeddings", headers, payload, self.timeout)
        duration_ms = int((time.monotonic() - started) * 1000)

        if "error" in body:
            raise ModelError(f"api error: {json.dumps(body['error'])[:500]}")

        try:
            data = body["data"]
            if not isinstance(data, list):
                raise ModelError(f"unexpected response shape: {json.dumps(body)[:500]}")
            if len(data) != len(texts):
                raise ModelError(f"expected {len(texts)} embeddings, got {len(data)}")

            sorted_data = sorted(data, key=lambda item: item.get("index", 0))

            vectors = []
            for item in sorted_data:
                if "embedding" not in item or not isinstance(item["embedding"], list):
                    raise ModelError(f"item without embedding: {json.dumps(item)[:500]}")
                if not item["embedding"]:
                    raise ModelError(f"empty embedding vector: {json.dumps(item)[:500]}")
                vectors.append(item["embedding"])

            return vectors, body.get("usage") or {}, duration_ms
        except (KeyError, IndexError, TypeError) as exc:
            raise ModelError(f"unexpected response shape: {json.dumps(body)[:500]}") from exc


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


def extract_tool_arguments(body: dict, *, expected_tool: str) -> str:
    """Return arguments only when exactly the forced named tool was called."""
    if "error" in body:
        raise ModelError(f"api error: {json.dumps(body['error'])[:500]}")
    try:
        message = body["choices"][0]["message"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ModelError(f"unexpected response shape: {json.dumps(body)[:500]}") from exc
    calls = message.get("tool_calls")
    if not isinstance(calls, list) or len(calls) != 1:
        count = len(calls) if isinstance(calls, list) else 0
        raise ModelError(f"expected one tool call, got {count}")
    function = calls[0].get("function") if isinstance(calls[0], dict) else None
    if not isinstance(function, dict) or function.get("name") != expected_tool:
        raise ModelError(f"expected tool {expected_tool!r}")
    arguments = function.get("arguments")
    if not isinstance(arguments, str) or not arguments:
        raise ModelError("tool call without arguments")
    return arguments
