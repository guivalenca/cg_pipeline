"""A minimal OpenAI-chat-completions client, stdlib only, configured by
MODEL_API_BASE and MODEL_API_KEY, defaulting to OpenRouter with
OPEN_ROUTER_API_KEY.

The transport is a plain function (url, headers, payload, timeout) -> parsed
JSON, so tests hand in a fake one and never touch the network.
"""

import copy
import json
import os
import socket
import time
import urllib.error
import urllib.request

DEFAULT_TIMEOUT_SECONDS = float(os.environ.get("CONCEPT_UNIVERSE_MODEL_TIMEOUT_SECONDS", 300))
DEFAULT_MAX_TOKENS = int(os.environ.get("CONCEPT_UNIVERSE_MODEL_MAX_TOKENS", 8000))
DEFAULT_API_BASE = "https://openrouter.ai/api/v1"
DEFAULT_ROUTING = {
    "provider": {
        "quantizations": ["int8", "fp8", "fp16", "bf16", "fp32", "unknown"],
        "ignore": ["SiliconFlow"],
    }
}


class ModelError(RuntimeError):
    """The call did not come back with a usable completion."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def is_transient_failure(exc: BaseException) -> bool:
    """Classify the failures for which retrying the same request may help.

    Transport wrappers retain their original exception as ``__cause__``, so
    this single classifier works for both ModelClient calls and test/client
    transports that raise the underlying stdlib exception directly.
    """
    seen: set[int] = set()
    current: BaseException | object | None = exc
    while isinstance(current, BaseException) and id(current) not in seen:
        seen.add(id(current))

        status_code = getattr(current, "status_code", None)
        if status_code is None and isinstance(current, urllib.error.HTTPError):
            status_code = current.code
        if status_code is None and isinstance(current, ModelError):
            prefix = str(current).partition(":")[0]
            if prefix.startswith("HTTP "):
                try:
                    status_code = int(prefix.removeprefix("HTTP "))
                except ValueError:
                    pass
        if isinstance(status_code, int):
            return status_code == 429 or 500 <= status_code <= 599

        if isinstance(current, (TimeoutError, socket.timeout, ConnectionError)):
            return True

        if isinstance(current, urllib.error.URLError):
            reason = current.reason
            if isinstance(reason, BaseException):
                current = reason
                continue
            normalized_reason = str(reason).lower()
            return (
                "timed out" in normalized_reason
                or "connection reset" in normalized_reason
            )

        current = current.__cause__ or current.__context__
    return False


def _merged_extra(extra: dict | None) -> dict:
    """Put caller-supplied request fields over shared routing defaults."""
    merged = copy.deepcopy(DEFAULT_ROUTING)
    for key, value in (extra or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _api_error(body: dict) -> ModelError:
    detail = body["error"]
    raw_code = detail.get("code") if isinstance(detail, dict) else None
    try:
        status_code = int(raw_code) if raw_code is not None else None
    except (TypeError, ValueError):
        status_code = None
    return ModelError(
        f"api error: {json.dumps(detail)[:500]}", status_code=status_code
    )


def http_transport(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise ModelError(
            f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:500]}",
            status_code=exc.code,
        ) from exc
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
            or os.environ.get("OPEN_ROUTER_API_KEY")
            or ""
        )
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.extra = _merged_extra(extra)
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
        usage = dict(body.get("usage") or {})
        if body.get("provider"):
            usage["provider"] = body["provider"]
        return text, usage, duration_ms


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
            raise _api_error(body)

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
        raise _api_error(body)
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
