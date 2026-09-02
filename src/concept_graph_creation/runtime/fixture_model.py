"""Deterministic model-call adapter backed only by checked-in fixtures."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FixtureResponseMissing(AssertionError):
    """The fixture manifest has no response for a requested model call."""


@dataclass(frozen=True)
class _FixtureResponse:
    stage_name: str
    input_subset: dict[str, Any]
    response: str
    source: str


class FixtureModelClient:
    """Match deterministic responses by stage and a recursive input subset."""

    def __init__(self, responses: list[_FixtureResponse]):
        self._remaining = list(responses)
        self._lock = threading.Lock()
        self.calls: list[dict[str, Any]] = []

    @classmethod
    def from_file(cls, path: Path) -> "FixtureModelClient":
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if manifest.get("schema_version") != "creation_fixture_model.v1":
            raise ValueError(
                "fixture model manifest schema_version must be creation_fixture_model.v1"
            )
        raw_responses = manifest.get("responses")
        if not isinstance(raw_responses, list):
            raise ValueError("fixture model manifest responses must be a list")
        response_replacements = manifest.get("response_replacements") or {}
        if not isinstance(response_replacements, dict) or not all(
            isinstance(old, str) and isinstance(new, str)
            for old, new in response_replacements.items()
        ):
            raise ValueError("fixture model response_replacements must map strings to strings")
        responses: list[_FixtureResponse] = []
        for index, entry in enumerate(raw_responses):
            if not isinstance(entry, dict):
                raise ValueError(f"fixture response {index} must be an object")
            stage_name = str(entry.get("stage_name") or "")
            if not stage_name:
                raise ValueError(f"fixture response {index} requires stage_name")
            input_subset = entry.get("input_subset") or {}
            if not isinstance(input_subset, dict):
                raise ValueError(f"fixture response {index} input_subset must be an object")
            has_inline = "response" in entry
            has_file = "response_file" in entry
            if has_inline == has_file:
                raise ValueError(
                    f"fixture response {index} requires exactly one of response or response_file"
                )
            if has_file:
                response_path = path.parent / str(entry["response_file"])
                response = response_path.read_text(encoding="utf-8")
                source = str(response_path)
            else:
                inline_response = entry["response"]
                response = (
                    inline_response
                    if isinstance(inline_response, str)
                    else json.dumps(inline_response, ensure_ascii=False)
                )
                source = f"{path}#responses[{index}]"
            for old, new in sorted(
                response_replacements.items(),
                key=lambda item: len(item[0]),
                reverse=True,
            ):
                response = response.replace(old, new)
            responses.append(
                _FixtureResponse(
                    stage_name=stage_name,
                    input_subset=input_subset,
                    response=response,
                    source=source,
                )
            )
        return cls(responses)

    def __call__(
        self,
        *,
        stage_name: str,
        inputs: dict[str, Any],
        **_kwargs: Any,
    ) -> str:
        with self._lock:
            for index, fixture in enumerate(self._remaining):
                if fixture.stage_name != stage_name:
                    continue
                if not _contains_subset(inputs, fixture.input_subset):
                    continue
                selected = self._remaining.pop(index)
                self.calls.append(
                    {
                        "stage_name": stage_name,
                        "source": selected.source,
                    }
                )
                return selected.response
        raise FixtureResponseMissing(
            f"fixture model has no response for stage {stage_name!r} and inputs "
            f"{sorted(inputs)}"
        )

    def assert_exhausted(self) -> None:
        with self._lock:
            if not self._remaining:
                return
            remaining = ", ".join(
                f"{fixture.stage_name} ({fixture.source})"
                for fixture in self._remaining
            )
        raise AssertionError(f"fixture model has unused responses: {remaining}")


def _contains_subset(value: Any, subset: Any) -> bool:
    if isinstance(subset, dict):
        if not isinstance(value, dict):
            return False
        return all(
            key in value and _contains_subset(value[key], item)
            for key, item in subset.items()
        )
    if isinstance(subset, list):
        if not isinstance(value, list) or len(value) < len(subset):
            return False
        return all(
            _contains_subset(actual, expected)
            for actual, expected in zip(value, subset)
        )
    return value == subset
