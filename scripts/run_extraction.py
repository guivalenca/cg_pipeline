#!/usr/bin/env python3
"""PROTOTYPE: compare four DeepSeek Source Fragment extractions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from number_source import prepare_source


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "data/si-mod6-com/source-bodies/0023-an-introduction-to-bag-of-words-and-how-to-code-it-in-python-for-nlp.md"
DEFAULT_PROMPT = ROOT / "prompts/source-fragment-extraction.txt"
DEFAULT_OUTPUT = ROOT / "results/0023-bag-of-words"
SOURCE_TITLE = "An Introduction to Bag of Words and How to Code It in Python for NLP"


@dataclass(frozen=True)
class Run:
    filename: str
    label: str
    model_env: str
    thinking: bool


RUNS = (
    Run("flash.md", "DeepSeek V4 Flash", "DEEPSEEK_FLASH_MODEL", False),
    Run("flash-thinking.md", "DeepSeek V4 Flash", "DEEPSEEK_FLASH_MODEL", True),
    Run("pro.md", "DeepSeek V4 Pro", "DEEPSEEK_PRO_MODEL", False),
    Run("pro-thinking.md", "DeepSeek V4 Pro", "DEEPSEEK_PRO_THINKING_MODEL", True),
)


TOOL = {
    "type": "function",
    "function": {
        "name": "submit_source_fragments",
        "description": "Submit the complete ordered list of Source Fragments.",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "fragments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "idea": {"type": "string"},
                            "start_line": {"type": "integer"},
                            "end_line": {"type": "integer"},
                        },
                        "required": ["idea", "start_line", "end_line"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["fragments"],
            "additionalProperties": False,
        },
    },
}


class ApiError(RuntimeError):
    def __init__(self, status: int, body: str) -> None:
        super().__init__(f"DeepSeek HTTP {status}: {body}")
        self.retryable = status in {408, 409, 429} or status >= 500


def load_env(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"").strip("'"))


def required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def render_prompt(template: str, numbered_source: str) -> str:
    replacements = {
        "{{SOURCE_TITLE}}": SOURCE_TITLE,
        "{{SOURCE_KIND}}": "Web article",
        "{{SOURCE_LANGUAGE}}": "English",
        "{{NUMBERED_SOURCE_BODY}}": numbered_source,
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    remaining = [key for key in replacements if key in rendered]
    if remaining:
        raise RuntimeError(f"Unresolved prompt placeholders: {remaining}")
    return rendered


def api_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if not base.endswith("/beta"):
        base += "/beta"
    return base + "/chat/completions"


def call_api(url: str, api_key: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        raise ApiError(error.code, body) from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"DeepSeek request failed: {error.reason}") from error


def parse_fragments(response: dict[str, Any], line_count: int) -> list[dict[str, Any]]:
    try:
        choice = response["choices"][0]
        calls = choice["message"]["tool_calls"]
    except (KeyError, IndexError, TypeError) as error:
        raise ValueError("Response did not contain a tool call") from error
    if len(calls) != 1 or calls[0]["function"]["name"] != "submit_source_fragments":
        raise ValueError("Response must contain exactly one submit_source_fragments call")
    try:
        arguments = json.loads(calls[0]["function"]["arguments"])
    except json.JSONDecodeError as error:
        raise ValueError("Tool arguments were not valid JSON") from error
    if set(arguments) != {"fragments"} or not isinstance(arguments["fragments"], list):
        raise ValueError("Tool arguments did not match the expected root schema")

    fragments = arguments["fragments"]
    for position, fragment in enumerate(fragments, 1):
        if not isinstance(fragment, dict) or set(fragment) != {"idea", "start_line", "end_line"}:
            raise ValueError(f"Fragment {position} did not match the expected schema")
        idea, start, end = fragment["idea"], fragment["start_line"], fragment["end_line"]
        if not isinstance(idea, str) or not idea.strip():
            raise ValueError(f"Fragment {position} has an empty idea")
        if type(start) is not int or type(end) is not int or not (1 <= start <= end <= line_count):
            raise ValueError(f"Fragment {position} has invalid evidence lines {start}-{end}")
    return fragments


def usage_line(usage: dict[str, Any]) -> str:
    prompt = usage.get("prompt_tokens", "?")
    completion = usage.get("completion_tokens", "?")
    total = usage.get("total_tokens", "?")
    return f"Prompt: {prompt}; completion: {completion}; total: {total}"


def markdown_result(
    run: Run,
    model: str,
    response: dict[str, Any],
    fragments: list[dict[str, Any]],
    source_lines: list[str],
    elapsed: float,
) -> str:
    mode = "on (high)" if run.thinking else "off"
    lines = [
        f"# Source Fragment Extraction — {run.label}",
        "",
        f"- **Source:** `{DEFAULT_SOURCE.name}`",
        f"- **Model:** `{model}`",
        f"- **Thinking:** {mode}",
        f"- **Generated:** {datetime.now(timezone.utc).isoformat()}",
        f"- **Latency:** {elapsed:.1f} seconds",
        f"- **Usage:** {usage_line(response.get('usage') or {})}",
        f"- **Fragments:** {len(fragments)}",
        "",
    ]
    for index, fragment in enumerate(fragments, 1):
        start, end = fragment["start_line"], fragment["end_line"]
        evidence = [f"[L{line_number:03d}] {source_lines[line_number - 1]}" for line_number in range(start, end + 1)]
        lines.extend(
            [
                f"## Fragment {index}",
                "",
                fragment["idea"].strip(),
                "",
                f"**Evidence:** L{start:03d}–L{end:03d}",
                "",
                "```text",
                *evidence,
                "```",
                "",
            ]
        )
    return "\n".join(lines)


def run_once(
    run: Run,
    prompt: str,
    source_lines: list[str],
    url: str,
    api_key: str,
    timeout: int,
    max_tokens: int,
) -> tuple[str, dict[str, Any], list[dict[str, Any]], float]:
    model = required_env(run.model_env)
    payload: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "tools": [TOOL],
        "thinking": {"type": "enabled" if run.thinking else "disabled"},
        "max_tokens": max_tokens,
        "stream": False,
    }
    if run.thinking:
        payload["reasoning_effort"] = "high"
    else:
        payload["tool_choice"] = {
            "type": "function",
            "function": {"name": "submit_source_fragments"},
        }

    started = time.monotonic()
    response = call_api(url, api_key, payload, timeout)
    elapsed = time.monotonic() - started
    fragments = parse_fragments(response, len(source_lines))
    return model, response, fragments, elapsed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--only", nargs="*", choices=[run.filename for run in RUNS])
    args = parser.parse_args()

    load_env(ROOT / ".env")
    api_key = required_env("DEEPSEEK_API_KEY")
    url = api_url(required_env("DEEPSEEK_BASE_URL"))
    timeout = int(os.environ.get("CONCEPT_UNIVERSE_MODEL_TIMEOUT_SECONDS", "600"))
    max_tokens = int(os.environ.get("CONCEPT_UNIVERSE_MODEL_MAX_TOKENS", "65536"))
    source_lines, numbered = prepare_source(args.source)
    prompt = render_prompt(args.prompt.read_text(encoding="utf-8"), "\n".join(numbered))
    args.output.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    selected_runs = [run for run in RUNS if not args.only or run.filename in args.only]
    for run in selected_runs:
        print(f"Running {run.filename}...", flush=True)
        for attempt in range(1, args.attempts + 1):
            try:
                model, response, fragments, elapsed = run_once(
                    run, prompt, source_lines, url, api_key, timeout, max_tokens
                )
                output = markdown_result(run, model, response, fragments, source_lines, elapsed)
                (args.output / run.filename).write_text(output, encoding="utf-8")
                print(f"  wrote {len(fragments)} fragments in {elapsed:.1f}s", flush=True)
                break
            except (RuntimeError, ValueError, json.JSONDecodeError) as error:
                print(f"  attempt {attempt}/{args.attempts} failed: {error}", file=sys.stderr, flush=True)
                retryable = not isinstance(error, ApiError) or error.retryable
                if attempt == args.attempts or not retryable:
                    failures.append(f"{run.filename}: {error}")
                    break
                else:
                    time.sleep(min(2 ** attempt, 8))

    if failures:
        raise SystemExit("Failed runs:\n- " + "\n- ".join(failures))


if __name__ == "__main__":
    main()
