from __future__ import annotations

import json
import os
import queue
import re
import socket
import ssl
import http.client
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from concept_graph_creation.runtime.output_budget import (
    OUTPUT_TOKEN_EMERGENCY_CEILING,
    OutputBudgetPolicy,
)
from concept_graph_creation.runtime.provider_errors import is_transient_provider_error
from concept_graph_creation.runtime.stage_runner import (
    ModelOutputTruncatedError,
    ModelRoute,
    StageBlockedError,
)


OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_TOTAL_DEADLINE_SECONDS = 1800
DEFAULT_OPENROUTER_DATA_COLLECTION = "deny"
DEFAULT_OPENROUTER_PREFERRED_MIN_THROUGHPUT_P50 = 25.0
DEFAULT_OPENROUTER_PREFERRED_MAX_LATENCY_P90 = 8.0
DEFAULT_OPENROUTER_MAX_PROMPT_PRICE = 1.75
DEFAULT_OPENROUTER_MAX_COMPLETION_PRICE = 3.5
# Thinking routes (reasoning_effort=high) can spend >11k tokens on reasoning alone for a dense
# Source Body before emitting any answer. The budget must leave room for the JSON answer *after*
# reasoning, otherwise the response is truncated (finish_reason=length). 12k starved dense docs;
# 32k still starved Subject Merge fine clustering on a mid-sized area (reasoning alone consumed
# the whole budget). 64k leaves headroom for both reasoning and the stage result. Override via env.
DEFAULT_MAX_TOKENS = 65536
_USAGE_WRITE_LOCK = threading.Lock()
_STAGE_RESULT_TOOL_NAME = "submit_stage_result"
_SUCCESSFUL_FINISH_REASONS = frozenset({"stop", "tool_calls"})
_DISABLED_ROUTING_VALUES = frozenset({"off", "none", "disable", "disabled"})
# A provider that streams a structurally broken forced tool call is a provider glitch, not a
# stage contract failure. Ignore the offending provider and re-route: 1 initial attempt plus up
# to 3 retries, each one ignoring every provider that already failed in this call.
MAX_FORCED_TOOL_ATTEMPTS = 4

# Marker attribute stamped on exceptions raised for provider-transient conditions (invalid tool
# envelopes, HTTP/streaming pressure, timeouts, wall-clock deadline). The CLI reads it through
# ``is_transient_provider_failure`` to map the run onto a retryable exit code instead of the
# semantic "stage refused" code, without string-matching messages at the exit boundary.
TRANSIENT_PROVIDER_ATTRIBUTE = "transient_provider"


def mark_transient_provider(exc: BaseException) -> BaseException:
    """Flag ``exc`` as caused by provider pressure rather than by a contract violation."""
    setattr(exc, TRANSIENT_PROVIDER_ATTRIBUTE, True)
    return exc


def is_transient_provider_failure(exc: BaseException | None) -> bool:
    """True when ``exc`` (or anything that caused it) is a provider-transient failure."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        if getattr(current, TRANSIENT_PROVIDER_ATTRIBUTE, False):
            return True
        if isinstance(current, TimeoutError):
            return True
        # Stages re-raise provider failures as fresh StageBlockedErrors built from the original
        # message, which drops the marker attribute; the shared matcher recovers those.
        if is_transient_provider_error(current):
            return True
        current = current.__cause__ or current.__context__
    return False


def _stage_blocked(message: str, *, transient: bool | None = None) -> StageBlockedError:
    """Build a StageBlockedError, marking provider-transient causes at the raise site."""
    exc = StageBlockedError(message)
    if transient is None:
        transient = is_transient_provider_error(exc)
    if transient:
        mark_transient_provider(exc)
    return exc


class _TotalDeadlineExceeded(TimeoutError):
    """The response did not finish within the call's wall-clock budget."""


class _InvalidToolCallError(StageBlockedError):
    """A forced tool response violated the structural envelope contract."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code
        self.response_provider: str | None = None
        # A broken tool envelope is always a provider glitch: every retry ladder rung already
        # re-routed away from the providers that produced it.
        mark_transient_provider(self)


class PipelineModelClient:
    def __init__(
        self,
        *,
        api_keys: Mapping[str, str],
        base_urls: Mapping[str, str] | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        total_deadline_seconds: float = DEFAULT_TOTAL_DEADLINE_SECONDS,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        usage_path: Path | None = None,
        stream: bool = True,
        provider_routing: Mapping[str, Any] | None = None,
    ) -> None:
        # Keep the mapping-shaped constructor for dependency injection compatibility, but only
        # retain the OpenRouter credential. Direct provider keys must never be used by creation.
        self.api_keys = {"openrouter": str(api_keys.get("openrouter", ""))}
        configured_base_urls = dict(base_urls or {})
        self.base_urls = {
            "openrouter": configured_base_urls.get("openrouter", OPENROUTER_BASE_URL)
        }
        self.timeout_seconds = timeout_seconds
        self.total_deadline_seconds = total_deadline_seconds
        self.max_tokens = max_tokens
        self.usage_path = usage_path
        self.stream = stream
        self.provider_routing = _safe_provider_routing(
            _default_provider_routing()
            if provider_routing is None
            else provider_routing
        )

    @classmethod
    def from_env(cls, *, project_root: Path) -> "PipelineModelClient":
        _load_dotenv(
            project_root.parent / ".env",
            allowed_keys={
                "OPENROUTER_API_KEY",
                "CG_PIPELINE_MODEL_TIMEOUT_SECONDS",
                "CG_PIPELINE_MODEL_TOTAL_DEADLINE_SECONDS",
                "CG_PIPELINE_MODEL_MAX_TOKENS",
                "CG_PIPELINE_MODEL_USAGE_PATH",
                "CG_PIPELINE_OPENROUTER_DATA_COLLECTION",
                "CG_PIPELINE_OPENROUTER_PREFERRED_MIN_THROUGHPUT_P50",
                "CG_PIPELINE_OPENROUTER_PREFERRED_MAX_LATENCY_P90",
                "CG_PIPELINE_OPENROUTER_MAX_PROMPT_PRICE",
                "CG_PIPELINE_OPENROUTER_MAX_COMPLETION_PRICE",
            },
        )

        openrouter_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
        if not openrouter_key:
            raise StageBlockedError(
                "OpenRouter model call is not configured. Set OPENROUTER_API_KEY in cg_pipeline/.env, "
                "or rerun with --deterministic-fixture for an offline fixture run."
            )

        usage_path = _optional_path_from_env(
            "CG_PIPELINE_MODEL_USAGE_PATH",
            relative_to=project_root.parent,
        )
        return cls(
            api_keys={"openrouter": openrouter_key},
            base_urls={"openrouter": OPENROUTER_BASE_URL},
            timeout_seconds=int(os.environ.get("CG_PIPELINE_MODEL_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)),
            total_deadline_seconds=float(
                os.environ.get(
                    "CG_PIPELINE_MODEL_TOTAL_DEADLINE_SECONDS",
                    DEFAULT_TOTAL_DEADLINE_SECONDS,
                )
            ),
            max_tokens=int(os.environ.get("CG_PIPELINE_MODEL_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
            usage_path=usage_path,
            provider_routing=_provider_routing_from_env(),
        )

    def call(
        self,
        *,
        route: ModelRoute,
        stage_name: str,
        inputs: dict[str, Any],
        repair_context: dict[str, Any] | None = None,
        max_tokens: int | None = None,
        output_budget: OutputBudgetPolicy | None = None,
        output_budget_attempt: int = 1,
    ) -> str:
        if route.provider != "openrouter":
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
                        "Call submit_stage_result exactly once with the complete stage result. "
                        "Do not return markdown, commentary, prose, or message content."
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
            "tools": [_stage_result_tool()],
            "tool_choice": {
                "type": "function",
                "function": {"name": _STAGE_RESULT_TOOL_NAME},
            },
            "max_tokens": min(
                self.max_tokens if max_tokens is None else max_tokens,
                OUTPUT_TOKEN_EMERGENCY_CEILING,
            ),
            # Stream the response. A non-streaming read sends zero bytes while the model reasons,
            # so an idle-connection timeout in front of the provider (~60s) kills long reasoning
            # requests with IncompleteRead(0 bytes) before any answer arrives. Streaming keeps the
            # connection alive because reasoning/answer deltas flow continuously.
            "stream": self.stream,
            "provider": {
                **self.provider_routing,
                "allow_fallbacks": route.allow_provider_fallbacks,
                # Tool choice and reasoning settings must not be silently discarded by a fallback.
                "require_parameters": route.require_provider_parameters,
            },
        }
        payload["reasoning"] = {
            "effort": route.reasoning_effort or ("medium" if route.thinking_enabled else "none")
        }
        # Retry ladder: each invalid forced tool call adds the offending provider to the routing
        # ignore list and retries, so attempt N is routed away from every provider that already
        # returned a broken envelope during this call.
        attempt_payload = payload
        ignored_providers: list[str] = []
        trigger_code: str | None = None
        for attempt in range(1, MAX_FORCED_TOOL_ATTEMPTS + 1):
            try:
                return self._post_chat_completion(
                    route.provider,
                    attempt_payload,
                    route=route,
                    stage_name=stage_name,
                    output_budget=output_budget,
                    output_budget_attempt=output_budget_attempt,
                    forced_tool_retry_attempt=attempt,
                    forced_tool_retry_ignored_provider=(
                        ignored_providers[-1] if ignored_providers else None
                    ),
                    forced_tool_retry_ignored_providers=list(ignored_providers),
                    forced_tool_retry_trigger_code=trigger_code,
                )
            except _InvalidToolCallError as exc:
                if attempt >= MAX_FORCED_TOOL_ATTEMPTS:
                    raise
                ignored_provider = _openrouter_provider_slug(exc.response_provider)
                if not route.allow_provider_fallbacks or ignored_provider is None:
                    raise

                provider_routing = dict(attempt_payload["provider"])
                configured_ignore = provider_routing.get("ignore")
                ignored = (
                    [value for value in configured_ignore if isinstance(value, str)]
                    if isinstance(configured_ignore, list)
                    else []
                )
                if any(
                    _openrouter_provider_slug(value) == ignored_provider
                    for value in ignored
                ):
                    # The router handed back a provider we already excluded: another rung would
                    # re-route to the same broken provider, so stop paying for it.
                    raise
                provider_routing["ignore"] = [*ignored, ignored_provider]
                attempt_payload = {**attempt_payload, "provider": provider_routing}
                ignored_providers.append(ignored_provider)
                trigger_code = exc.code
        raise AssertionError("forced tool retry ladder terminated without a result")

    def _post_chat_completion(
        self,
        provider: str,
        payload: dict[str, Any],
        *,
        route: ModelRoute,
        stage_name: str,
        output_budget: OutputBudgetPolicy | None = None,
        output_budget_attempt: int = 1,
        forced_tool_retry_attempt: int = 1,
        forced_tool_retry_ignored_provider: str | None = None,
        forced_tool_retry_ignored_providers: list[str] | None = None,
        forced_tool_retry_trigger_code: str | None = None,
    ) -> str:
        base_url = self.base_urls[provider].rstrip("/")
        ssl_context = _ssl_context()
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_keys[provider]}",
                "Content-Type": "application/json",
                "X-OpenRouter-Metadata": "enabled",
            },
            method="POST",
        )
        # Consume the Server-Sent Events stream, accumulating answer deltas and tracking the
        # terminal finish_reason. A truncated response (finish_reason=length) is treated as a hard
        # block rather than silently returning partial JSON that would parse-fail downstream.
        content_parts: list[str] = []
        tool_call_names: dict[int, str] = {}
        tool_call_arguments: dict[int, list[str]] = {}
        finish_reason: str | None = None
        saw_event = False
        usage: dict[str, Any] = {}
        response_model: str | None = None
        response_provider: str | None = None
        generation_id: str | None = None
        started_at = time.monotonic()
        deadline = started_at + self.total_deadline_seconds

        def telemetry_fields(current_usage: Mapping[str, Any]) -> dict[str, Any]:
            return {
                **_model_call_telemetry_fields(
                    payload=payload,
                    route=route,
                    output_budget=output_budget,
                    output_budget_attempt=output_budget_attempt,
                    usage=current_usage,
                ),
                "forced_tool_retry_attempt": forced_tool_retry_attempt,
                "forced_tool_retry": forced_tool_retry_attempt > 1,
                # The provider excluded to produce THIS attempt, plus every provider excluded so
                # far in the ladder, so the accumulation is auditable per attempt.
                "forced_tool_retry_ignored_provider": forced_tool_retry_ignored_provider,
                "forced_tool_retry_ignored_providers": list(
                    forced_tool_retry_ignored_providers or []
                ),
                "forced_tool_retry_trigger_code": forced_tool_retry_trigger_code,
            }

        try:
            remaining_before_open = deadline - time.monotonic()
            if remaining_before_open <= 0:
                raise _TotalDeadlineExceeded
            # ``urlopen`` may block before the SSE response object exists. Cap that initial
            # socket wait as well, otherwise a configured total deadline shorter than the idle
            # timeout is not actually a wall-clock bound until after response headers arrive.
            open_timeout = min(float(self.timeout_seconds), remaining_before_open)
            with urllib.request.urlopen(request, timeout=open_timeout, context=ssl_context) as response:
                get_header = getattr(response, "getheader", None)
                if callable(get_header):
                    header_generation_id = get_header("X-Generation-Id")
                    if header_generation_id:
                        generation_id = str(header_generation_id)
                response_chunks = _response_chunks_before_deadline(
                    response,
                    stream=bool(payload.get("stream")),
                    deadline=deadline,
                )
                for raw_line in response_chunks:
                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    data = line[len("data:") :].strip() if line.startswith("data:") else line
                    if data == "[DONE]":
                        break
                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    saw_event = True
                    if isinstance(event.get("usage"), dict):
                        usage = event["usage"]
                    if event.get("model"):
                        response_model = str(event["model"])
                    if event.get("provider"):
                        response_provider = str(event["provider"])
                    if event.get("id"):
                        generation_id = str(event["id"])
                    if isinstance(event.get("error"), dict):
                        error = event["error"]
                        code = error.get("code", "unknown")
                        metadata = error.get("metadata") if isinstance(error.get("metadata"), dict) else {}
                        self._append_usage_event(
                            {
                                "recorded_at": datetime.now(timezone.utc).isoformat(),
                                "stage_name": stage_name,
                                "route_alias": route.alias,
                                "requested_model": route.model,
                                "response_model": response_model or route.model,
                                "response_provider": response_provider,
                                "generation_id": generation_id,
                                "finish_reason": "error",
                                "outcome": "stream_error",
                                "error_code": code,
                                "error_type": metadata.get("error_type"),
                                "elapsed_seconds": round(time.monotonic() - started_at, 3),
                                "usage": usage,
                                **telemetry_fields(usage),
                            }
                        )
                        message = str(error.get("message") or "streaming provider error")
                        # Transience follows the shared matcher: pressure codes are retryable,
                        # a rejected request (e.g. 400/401) is not.
                        raise _stage_blocked(f"OpenRouter streaming error {code}: {message}")
                    choice = (event.get("choices") or [{}])[0]
                    message_part = choice.get("delta") or choice.get("message") or {}
                    piece = message_part.get("content")
                    if isinstance(piece, str):
                        content_parts.append(piece)
                    _accumulate_streamed_tool_calls(
                        message_part.get("tool_calls"),
                        names=tool_call_names,
                        arguments=tool_call_arguments,
                    )
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
        except _TotalDeadlineExceeded as exc:
            partial_tool_call = bool(tool_call_names or tool_call_arguments)
            self._append_usage_event(
                {
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "stage_name": stage_name,
                    "route_alias": route.alias,
                    "requested_model": route.model,
                    "response_model": response_model or route.model,
                    "response_provider": response_provider,
                    "generation_id": generation_id,
                    "finish_reason": finish_reason,
                    "outcome": "total_timeout",
                    "total_deadline_seconds": self.total_deadline_seconds,
                    "elapsed_seconds": round(time.monotonic() - started_at, 3),
                    "saw_stream_event": saw_event,
                    "partial_tool_call": partial_tool_call,
                    "usage": usage,
                    **telemetry_fields(usage),
                }
            )
            discarded = "Partial tool response" if partial_tool_call else "Partial response"
            raise _stage_blocked(
                f"OpenRouter request exceeded total wall-clock deadline of {self.total_deadline_seconds:g} seconds. "
                f"{discarded} was discarded; submit_stage_result must complete within "
                "CG_PIPELINE_MODEL_TOTAL_DEADLINE_SECONDS.",
                transient=True,
            ) from exc
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            try:
                error_response = json.loads(detail)
            except json.JSONDecodeError:
                error_response = {}
            if not isinstance(error_response, dict):
                error_response = {}
            error_usage = (
                error_response.get("usage")
                if isinstance(error_response.get("usage"), dict)
                else {}
            )
            error = (
                error_response.get("error")
                if isinstance(error_response.get("error"), dict)
                else {}
            )
            metadata = error.get("metadata") if isinstance(error.get("metadata"), dict) else {}
            get_header = getattr(exc, "headers", None)
            header_generation_id = (
                get_header.get("X-Generation-Id")
                if hasattr(get_header, "get")
                else None
            )
            self._append_usage_event(
                {
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "stage_name": stage_name,
                    "route_alias": route.alias,
                    "requested_model": route.model,
                    "response_model": error_response.get("model") or route.model,
                    "response_provider": error_response.get("provider"),
                    "generation_id": error_response.get("id") or header_generation_id,
                    "finish_reason": "error",
                    "outcome": "http_error",
                    "status_code": exc.code,
                    "error_type": metadata.get("error_type"),
                    "elapsed_seconds": round(time.monotonic() - started_at, 3),
                    "usage": error_usage,
                    **telemetry_fields(error_usage),
                }
            )
            raise _stage_blocked(
                f"OpenRouter HTTP {exc.code}: {_http_error_detail(exc.code, detail)}"
            ) from exc
        except (TimeoutError, socket.timeout) as exc:
            raise _stage_blocked(
                f"OpenRouter request timed out while reading response: {exc}",
                transient=True,
            ) from exc
        except urllib.error.URLError as exc:
            raise _stage_blocked(
                f"OpenRouter request failed: {exc.reason}", transient=True
            ) from exc
        except (ConnectionError, http.client.IncompleteRead, http.client.RemoteDisconnected) as exc:
            raise _stage_blocked(
                f"OpenRouter request failed while reading response: {exc}", transient=True
            ) from exc

        content = "".join(content_parts)
        has_tool_call = bool(tool_call_names or tool_call_arguments)

        def record_usage(outcome: str, **extra: Any) -> None:
            if not saw_event:
                return
            self._append_usage_event(
                {
                    "recorded_at": datetime.now(timezone.utc).isoformat(),
                    "stage_name": stage_name,
                    "route_alias": route.alias,
                    "requested_model": route.model,
                    "response_model": response_model or route.model,
                    "response_provider": response_provider,
                    "generation_id": generation_id,
                    "finish_reason": finish_reason,
                    "outcome": outcome,
                    "elapsed_seconds": round(time.monotonic() - started_at, 3),
                    "usage": usage,
                    **telemetry_fields(usage),
                    **extra,
                }
            )

        if finish_reason == "length":
            record_usage("truncated")
            raise ModelOutputTruncatedError(
                "OpenRouter response was truncated before completion (finish_reason=length): reasoning plus "
                f"output exceeded max_tokens={payload.get('max_tokens')}. The partial response was discarded."
            )
        if not saw_event:
            raise _stage_blocked("OpenRouter returned no streaming events in the response")
        if finish_reason not in _SUCCESSFUL_FINISH_REASONS:
            record_usage("incomplete" if finish_reason is None else "unsuccessful_finish")
            received = "no finish_reason" if finish_reason is None else f"finish_reason={finish_reason}"
            raise StageBlockedError(
                "OpenRouter response ended without a terminal successful finish_reason "
                f"('stop' or 'tool_calls'); received {received}. Partial response was discarded."
            )
        if has_tool_call:
            try:
                result, tool_result_recovery = _unwrap_stage_result_tool_call(
                    tool_call_names,
                    tool_call_arguments,
                )
            except _InvalidToolCallError as exc:
                diagnostic = _tool_call_diagnostics(
                    tool_call_names,
                    tool_call_arguments,
                )
                diagnostic["code"] = exc.code
                exc.response_provider = response_provider
                record_usage(
                    "invalid_tool",
                    tool_diagnostic=diagnostic,
                )
                raise
            if tool_result_recovery == "missing_result_envelope":
                record_usage(
                    "success_recovered_tool_envelope",
                    tool_envelope_recovered=True,
                )
            elif tool_result_recovery == "json_encoded_object":
                record_usage(
                    "success_recovered_serialized_tool_result",
                    tool_result_recovery=tool_result_recovery,
                )
            else:
                record_usage("success")
            return result
        if content.strip():
            record_usage(
                "invalid_tool",
                tool_diagnostic={
                    "code": "message_instead_of_tool",
                    "tool_call_count": 0,
                    "expected_tool_matched": None,
                    "arguments_parse_state": "missing",
                    "arguments_type": "unknown",
                    "has_result": False,
                    "unexpected_key_count": 0,
                    "result_type": "missing",
                },
            )
            raise StageBlockedError(
                "OpenRouter returned message content instead of the required submit_stage_result tool call"
            )
        record_usage("empty")
        raise _stage_blocked("OpenRouter returned an empty message")

    def _append_usage_event(self, event: dict[str, Any]) -> None:
        if self.usage_path is None:
            return
        try:
            self.usage_path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
            with _USAGE_WRITE_LOCK, self.usage_path.open("a", encoding="utf-8") as handle:
                handle.write(line)
        except OSError:
            # Telemetry is deliberately best effort: a diagnostics path must not discard a valid
            # model response or cause a completed paid request to be repeated.
            return


def _response_chunks_before_deadline(
    response: Any,
    *,
    stream: bool,
    deadline: float,
):
    """Yield response bytes without allowing one blocking read to outlive the total deadline."""

    messages: queue.Queue[tuple[str, Any]] = queue.Queue()

    def read_response() -> None:
        try:
            if stream:
                for chunk in response:
                    messages.put(("chunk", chunk))
            else:
                messages.put(("chunk", response.read()))
        except Exception as exc:  # Transport errors must be re-raised in the caller thread.
            messages.put(("error", exc))
        finally:
            messages.put(("done", None))

    threading.Thread(
        target=read_response,
        name="openrouter-response-reader",
        daemon=True,
    ).start()

    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _TotalDeadlineExceeded
        try:
            kind, value = messages.get(timeout=remaining)
        except queue.Empty as exc:
            raise _TotalDeadlineExceeded from exc
        if time.monotonic() >= deadline:
            raise _TotalDeadlineExceeded
        if kind == "chunk":
            yield value
        elif kind == "error":
            raise value
        else:
            return


def _default_provider_routing() -> dict[str, Any]:
    return {
        "data_collection": DEFAULT_OPENROUTER_DATA_COLLECTION,
        "preferred_min_throughput": {
            "p50": DEFAULT_OPENROUTER_PREFERRED_MIN_THROUGHPUT_P50
        },
        "preferred_max_latency": {"p90": DEFAULT_OPENROUTER_PREFERRED_MAX_LATENCY_P90},
        "max_price": {
            "prompt": DEFAULT_OPENROUTER_MAX_PROMPT_PRICE,
            "completion": DEFAULT_OPENROUTER_MAX_COMPLETION_PRICE,
        },
    }


def _provider_routing_from_env() -> dict[str, Any]:
    routing: dict[str, Any] = {}
    data_collection = _optional_routing_choice_from_env(
        "CG_PIPELINE_OPENROUTER_DATA_COLLECTION",
        default=DEFAULT_OPENROUTER_DATA_COLLECTION,
        allowed={"allow", "deny"},
    )
    if data_collection is not None:
        routing["data_collection"] = data_collection

    min_throughput = _optional_routing_float_from_env(
        "CG_PIPELINE_OPENROUTER_PREFERRED_MIN_THROUGHPUT_P50",
        default=DEFAULT_OPENROUTER_PREFERRED_MIN_THROUGHPUT_P50,
    )
    if min_throughput is not None:
        routing["preferred_min_throughput"] = {"p50": min_throughput}

    max_latency = _optional_routing_float_from_env(
        "CG_PIPELINE_OPENROUTER_PREFERRED_MAX_LATENCY_P90",
        default=DEFAULT_OPENROUTER_PREFERRED_MAX_LATENCY_P90,
    )
    if max_latency is not None:
        routing["preferred_max_latency"] = {"p90": max_latency}

    price = {
        "prompt": _optional_routing_float_from_env(
            "CG_PIPELINE_OPENROUTER_MAX_PROMPT_PRICE",
            default=DEFAULT_OPENROUTER_MAX_PROMPT_PRICE,
        ),
        "completion": _optional_routing_float_from_env(
            "CG_PIPELINE_OPENROUTER_MAX_COMPLETION_PRICE",
            default=DEFAULT_OPENROUTER_MAX_COMPLETION_PRICE,
        ),
    }
    enabled_price = {name: value for name, value in price.items() if value is not None}
    if enabled_price:
        routing["max_price"] = enabled_price
    return _safe_provider_routing(routing)


def _safe_provider_routing(value: Mapping[str, Any]) -> dict[str, Any]:
    routing = dict(value)
    # Explicit ordering bypasses OpenRouter Auto Exacto. parallel_tool_calls is not advertised by
    # the current DeepSeek V4 endpoints and would eliminate every endpoint with strict parameters.
    for unsupported in ("sort", "order", "parallel_tool_calls"):
        routing.pop(unsupported, None)
    return routing


def _openrouter_provider_slug(value: str | None) -> str | None:
    """Convert OpenRouter's response provider label to its request routing slug."""

    if not isinstance(value, str) or not value.strip():
        return None
    parts = []
    for part in value.casefold().split("/"):
        normalized = re.sub(r"[^a-z0-9]+", "-", part).strip("-")
        if not normalized:
            return None
        parts.append(normalized)
    return "/".join(parts)


def _optional_routing_choice_from_env(
    name: str,
    *,
    default: str,
    allowed: set[str],
) -> str | None:
    raw = os.environ.get(name)
    normalized = default if raw is None or not raw.strip() else raw.strip().lower()
    if normalized in _DISABLED_ROUTING_VALUES:
        return None
    if normalized not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of {choices}, or 'off'")
    return normalized


def _optional_routing_float_from_env(name: str, *, default: float) -> float | None:
    raw = os.environ.get(name)
    normalized = str(default) if raw is None or not raw.strip() else raw.strip().lower()
    if normalized in _DISABLED_ROUTING_VALUES:
        return None
    try:
        value = float(normalized)
    except ValueError as exc:
        raise ValueError(f"{name} must be a non-negative number, or 'off'") from exc
    if value < 0:
        raise ValueError(f"{name} must be a non-negative number, or 'off'")
    return value


def _model_call_telemetry_fields(
    *,
    payload: Mapping[str, Any],
    route: ModelRoute,
    output_budget: OutputBudgetPolicy | None,
    output_budget_attempt: int,
    usage: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "requested_provider": route.provider,
        "requested_max_tokens": _integer_or_none(payload.get("max_tokens")),
        "output_budget_policy": output_budget.operation if output_budget is not None else None,
        "output_budget_policy_version": output_budget.version if output_budget is not None else None,
        "output_budget_attempt": output_budget_attempt,
        "output_budget_retry": output_budget_attempt > 1,
        "length_retry_from": (
            output_budget.initial_max_tokens
            if output_budget is not None and output_budget.length_retry_max_tokens is not None
            else None
        ),
        "length_retry_to": (
            output_budget.length_retry_max_tokens if output_budget is not None else None
        ),
        "reasoning_effort": route.reasoning_effort
        or ("medium" if route.thinking_enabled else "none"),
        "reasoning_tokens": _reasoning_tokens(usage),
        "cost_usd": _usage_cost(usage),
    }


def _reasoning_tokens(usage: Mapping[str, Any]) -> int | None:
    for key in ("reasoning_tokens", "thoughts_token_count"):
        value = _integer_or_none(usage.get(key))
        if value is not None:
            return value
    details = usage.get("completion_tokens_details")
    if isinstance(details, Mapping):
        return _integer_or_none(details.get("reasoning_tokens"))
    return None


def _usage_cost(usage: Mapping[str, Any]) -> float | None:
    for key in ("cost", "total_cost", "cost_usd"):
        value = _float_or_none(usage.get(key))
        if value is not None:
            return value
    return None


def _integer_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _http_error_detail(status_code: int, detail: str) -> str:
    try:
        payload = json.loads(detail)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
    message = str(error.get("message") or detail or "unknown OpenRouter error")[:1000]
    metadata = _router_metadata(payload)
    no_endpoint_message = "no endpoint" in message.lower() or "no provider" in message.lower()
    if status_code != 404 or (metadata is None and not no_endpoint_message):
        return message
    result = f"No eligible provider matched the OpenRouter routing constraints. {message}"
    if metadata is not None:
        serialized = json.dumps(metadata, ensure_ascii=False, sort_keys=True)[:1000]
        result += f" Router metadata: {serialized}"
    return result


def _router_metadata(payload: Mapping[str, Any]) -> Mapping[str, Any] | None:
    metadata = payload.get("openrouter_metadata")
    if isinstance(metadata, Mapping):
        return metadata
    error = payload.get("error")
    error_metadata = error.get("metadata") if isinstance(error, Mapping) else None
    if not isinstance(error_metadata, Mapping):
        return None
    nested = error_metadata.get("openrouter_metadata")
    if isinstance(nested, Mapping):
        return nested
    if any(key in error_metadata for key in ("attempts", "ignored_providers", "provider_selection")):
        return error_metadata
    return None


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


def _optional_path_from_env(name: str, *, relative_to: Path) -> Path | None:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    path = Path(raw).expanduser()
    return path if path.is_absolute() else relative_to / path


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
    except ImportError:
        return ssl.create_default_context()
    return ssl.create_default_context(cafile=certifi.where())


def _stage_result_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": _STAGE_RESULT_TOOL_NAME,
            "description": "Submit the complete JSON object produced by this Concept Graph Pipeline stage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "result": {
                        "type": "object",
                        "description": "The complete stage output object, with no prose wrapper.",
                    }
                },
                "required": ["result"],
                "additionalProperties": False,
            },
        },
    }


def _accumulate_streamed_tool_calls(
    value: Any,
    *,
    names: dict[int, str],
    arguments: dict[int, list[str]],
) -> None:
    if not isinstance(value, list):
        return
    for position, item in enumerate(value):
        if not isinstance(item, dict):
            continue
        raw_index = item.get("index", position)
        if not isinstance(raw_index, int):
            continue
        function = item.get("function")
        if not isinstance(function, dict):
            continue
        name = function.get("name")
        if isinstance(name, str) and name:
            names[raw_index] = names.get(raw_index, "") + name
        fragment = function.get("arguments")
        if isinstance(fragment, str):
            arguments.setdefault(raw_index, []).append(fragment)


def _unwrap_stage_result_tool_call(
    names: Mapping[int, str],
    argument_fragments: Mapping[int, list[str]],
) -> tuple[str, str | None]:
    indexes = set(names) | set(argument_fragments)
    if indexes != {0}:
        raise _InvalidToolCallError(
            "OpenRouter must return exactly one submit_stage_result tool call",
            code="tool_call_count_mismatch",
        )
    if names.get(0) != _STAGE_RESULT_TOOL_NAME:
        raise _InvalidToolCallError(
            "OpenRouter returned an unexpected tool instead of submit_stage_result",
            code="unexpected_tool",
        )
    raw_arguments = "".join(argument_fragments.get(0, []))
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError as exc:
        raise _InvalidToolCallError(
            f"OpenRouter returned invalid submit_stage_result arguments: {exc.msg}",
            code="invalid_arguments_json",
        ) from exc
    if not isinstance(arguments, dict):
        raise _InvalidToolCallError(
            "OpenRouter submit_stage_result arguments must contain one JSON object in 'result'",
            code="arguments_not_object",
        )
    if "result" in arguments:
        result = arguments["result"]
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False), None
        if isinstance(result, str):
            try:
                decoded_result = json.loads(result)
            except json.JSONDecodeError as exc:
                raise _InvalidToolCallError(
                    "OpenRouter submit_stage_result arguments must contain one JSON object in 'result'",
                    code="result_not_object",
                ) from exc
            if isinstance(decoded_result, dict):
                return json.dumps(decoded_result, ensure_ascii=False), "json_encoded_object"
        if not isinstance(result, dict):
            raise _InvalidToolCallError(
                "OpenRouter submit_stage_result arguments must contain one JSON object in 'result'",
                code="result_not_object",
            )
        raise AssertionError("unreachable result shape")

    # Some otherwise tool-compliant OpenRouter endpoints occasionally omit only the
    # schema's outer ``result`` property and place the stage object directly in the
    # forced tool arguments. Preserve the forced exactly-one tool boundary, but let
    # StageRunner apply the real stage-specific normalizer and contract to this object.
    # This is safer and cheaper than repeating a long reasoning call merely to add an
    # envelope; invalid direct objects still fail (or receive the normal one repair)
    # at the Stage Contract boundary.
    return json.dumps(arguments, ensure_ascii=False), "missing_result_envelope"


def _tool_call_diagnostics(
    names: Mapping[int, str],
    argument_fragments: Mapping[int, list[str]],
) -> dict[str, Any]:
    """Describe a rejected tool envelope without persisting model-produced content."""

    indexes = sorted(set(names) | set(argument_fragments))
    raw_arguments = "".join(argument_fragments.get(0, [])) if indexes == [0] else ""
    diagnostics: dict[str, Any] = {
        "tool_call_count": len(indexes),
        "expected_tool_matched": (
            names.get(0) == _STAGE_RESULT_TOOL_NAME if indexes == [0] else None
        ),
        "arguments_parse_state": "missing" if not raw_arguments else "invalid_json",
        "arguments_type": "unknown",
        "has_result": False,
        "unexpected_key_count": 0,
        "result_type": "missing",
    }
    if indexes != [0]:
        return diagnostics

    if not raw_arguments:
        return diagnostics
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return diagnostics

    diagnostics["arguments_parse_state"] = "parsed"
    diagnostics["arguments_type"] = _json_type_name(arguments)
    if not isinstance(arguments, dict):
        return diagnostics

    diagnostics["has_result"] = "result" in arguments
    diagnostics["unexpected_key_count"] = len(set(arguments) - {"result"})
    if "result" not in arguments:
        return diagnostics
    result = arguments["result"]
    diagnostics["result_type"] = _json_type_name(result)
    if isinstance(result, str):
        try:
            decoded_result = json.loads(result)
        except json.JSONDecodeError:
            diagnostics["decoded_result_type"] = "invalid_json"
        else:
            diagnostics["decoded_result_type"] = _json_type_name(decoded_result)
    return diagnostics


def _json_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (int, float)):
        return "number"
    return type(value).__name__
