from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Collection, Mapping

from concept_graph_creation.runtime.output_budget import output_budget_identity
from concept_graph_creation.runtime.stage_runner import ModelCall, ModelRouter, StageBlockedError, StageResult


DERIVATION_KEY_VERSION_PREFIX = "drv1-"
REVISION_VERSION_PREFIX = "rev1-"
MODEL_STAGE_DERIVATION_SCHEMA_VERSION = "model_stage_derivation.v1"
VOLATILE_DERIVATION_KEYS = frozenset(
    {
        "completed_at",
        "created_at",
        "finished_at",
        "generated_at",
        "last_modified_at",
        "recorded_at",
        "started_at",
        "updated_at",
    }
)


@dataclass(frozen=True)
class DerivedArtifact:
    artifact: dict[str, Any]
    artifact_path: Path
    derivation_key: str
    derivation_path: Path
    reused: bool
    repaired: bool


def canonical_revision(
    value: Any,
    *,
    ignored_keys: Collection[str] = (),
) -> str:
    """Return a stable revision for semantic JSON content."""

    canonical = _without_ignored_keys(value, ignored_keys=frozenset(ignored_keys))
    serialized = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return REVISION_VERSION_PREFIX + hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def derivation_key(value: Any) -> str:
    """Return a versioned content address for an exact derivation description."""

    revision = canonical_revision(value)
    return DERIVATION_KEY_VERSION_PREFIX + revision.removeprefix(REVISION_VERSION_PREFIX)


def model_execution_identity(
    *,
    router: ModelRouter,
    model_call: ModelCall,
    routes: Mapping[str, str],
    provider_retry_limit: int,
    provider_retry_backoff_seconds: float,
    schema_version: str,
    extra_config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": schema_version,
        "routes": {
            role: _model_route_identity(router, alias)
            for role, alias in sorted(routes.items())
        },
        "generation": _model_generation_identity(model_call),
        "provider_retry_limit": provider_retry_limit,
        "provider_retry_backoff_seconds": provider_retry_backoff_seconds,
        "extra_config": dict(extra_config or {}),
    }


def stage_derivation_identity(
    *,
    stage_name: str,
    model_input: dict[str, Any],
    execution_identity: dict[str, Any],
    input_revisions: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": MODEL_STAGE_DERIVATION_SCHEMA_VERSION,
        "stage_name": stage_name,
        "input_revision": canonical_revision(
            model_input,
            ignored_keys=VOLATILE_DERIVATION_KEYS,
        ),
        "input_schema_version": model_input.get("schema_version"),
        "prompt_revision": canonical_revision(
            {
                "path": model_input.get("prompt_path"),
                "content": model_input.get("prompt"),
            }
        ),
        "output_contract_revision": canonical_revision(model_input.get("output_contract")),
        "output_budget": output_budget_identity(
            stage_name=stage_name,
            inputs=model_input,
        ),
        "input_revisions": dict(input_revisions),
        "execution": execution_identity,
    }


def run_cached_stage(
    *,
    cache_root: Path,
    stage_group: str,
    input_filename: str,
    output_filename: str,
    model_input: dict[str, Any],
    identity: dict[str, Any],
    validator: Callable[[dict[str, Any]], list[str]],
    execute: Callable[[Path], StageResult],
    postprocess: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
) -> DerivedArtifact:
    stage_key = derivation_key(identity)
    stage_dir = cache_root / stage_group / stage_key
    input_path = stage_dir / input_filename
    output_path = stage_dir / output_filename
    derivation_path = stage_dir / "derivation.json"
    cached = _load_cached_stage_artifact(
        input_path=input_path,
        output_path=output_path,
        derivation_path=derivation_path,
        model_input=model_input,
        identity=identity,
        validator=validator,
    )
    if cached is not None:
        metadata = _read_json(derivation_path)
        return DerivedArtifact(
            artifact=cached,
            artifact_path=output_path,
            derivation_key=stage_key,
            derivation_path=derivation_path,
            reused=True,
            repaired=bool(metadata.get("repaired")),
        )

    stage_dir.mkdir(parents=True, exist_ok=True)
    input_path.write_text(
        json.dumps(model_input, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    stage_result = execute(stage_dir)
    artifact = _read_json(stage_result.artifact_path)
    if postprocess is not None:
        artifact = postprocess(artifact)
        errors = validator(artifact)
        if errors:
            raise StageBlockedError(
                "cached stage postprocess produced an invalid artifact: " + "; ".join(errors)
            )
        stage_result.artifact_path.write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    metadata = {
        "schema_version": MODEL_STAGE_DERIVATION_SCHEMA_VERSION,
        "status": "succeeded",
        "key": stage_key,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "input_artifact": input_filename,
        "output_artifact": output_filename,
        "input_revision": canonical_revision(
            model_input,
            ignored_keys=VOLATILE_DERIVATION_KEYS,
        ),
        "output_revision": canonical_revision(
            artifact,
            ignored_keys=VOLATILE_DERIVATION_KEYS,
        ),
        "identity": identity,
        "repaired": stage_result.repaired,
    }
    derivation_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return DerivedArtifact(
        artifact=artifact,
        artifact_path=stage_result.artifact_path,
        derivation_key=stage_key,
        derivation_path=derivation_path,
        reused=False,
        repaired=stage_result.repaired,
    )


def derivation_artifact_succeeded(
    *,
    artifact_path: Path,
    expected_key: str,
    validator: Callable[[dict[str, Any]], list[str]],
) -> bool:
    derivation_path = artifact_path.parent / "derivation.json"
    if not artifact_path.is_file() or not derivation_path.is_file():
        return False
    try:
        artifact = _read_json(artifact_path)
        metadata = _read_json(derivation_path)
    except (OSError, json.JSONDecodeError):
        return False
    identity = metadata.get("identity")
    input_ref = metadata.get("input_artifact")
    if not isinstance(input_ref, str) or not input_ref:
        return False
    input_path = artifact_path.parent / input_ref
    if not input_path.is_file():
        return False
    try:
        saved_input = _read_json(input_path)
    except (OSError, json.JSONDecodeError):
        return False
    return (
        metadata.get("schema_version") == MODEL_STAGE_DERIVATION_SCHEMA_VERSION
        and metadata.get("status") == "succeeded"
        and metadata.get("key") == expected_key
        and metadata.get("output_artifact") == artifact_path.name
        and isinstance(identity, dict)
        and derivation_key(identity) == expected_key
        and metadata.get("input_revision") == identity.get("input_revision")
        and metadata.get("input_revision")
        == canonical_revision(saved_input, ignored_keys=VOLATILE_DERIVATION_KEYS)
        and metadata.get("output_revision")
        == canonical_revision(artifact, ignored_keys=VOLATILE_DERIVATION_KEYS)
        and not validator(artifact)
    )


def _load_cached_stage_artifact(
    *,
    input_path: Path,
    output_path: Path,
    derivation_path: Path,
    model_input: dict[str, Any],
    identity: dict[str, Any],
    validator: Callable[[dict[str, Any]], list[str]],
) -> dict[str, Any] | None:
    if not input_path.is_file() or not output_path.is_file() or not derivation_path.is_file():
        return None
    try:
        saved_input = _read_json(input_path)
        artifact = _read_json(output_path)
        metadata = _read_json(derivation_path)
    except (OSError, json.JSONDecodeError):
        return None
    expected_key = derivation_key(identity)
    input_revision = canonical_revision(
        model_input,
        ignored_keys=VOLATILE_DERIVATION_KEYS,
    )
    if canonical_revision(saved_input, ignored_keys=VOLATILE_DERIVATION_KEYS) != input_revision:
        return None
    if (
        metadata.get("schema_version") != MODEL_STAGE_DERIVATION_SCHEMA_VERSION
        or metadata.get("status") != "succeeded"
        or metadata.get("key") != expected_key
        or metadata.get("input_artifact") != input_path.name
        or metadata.get("output_artifact") != output_path.name
        or metadata.get("input_revision") != input_revision
        or metadata.get("output_revision")
        != canonical_revision(artifact, ignored_keys=VOLATILE_DERIVATION_KEYS)
        or metadata.get("identity") != identity
        or validator(artifact)
    ):
        return None
    return artifact


def _model_route_identity(router: ModelRouter, alias: str) -> dict[str, Any]:
    route = router.resolve(alias)
    return {
        "alias": route.alias,
        "provider": route.provider,
        "model": route.model,
        "thinking_enabled": route.thinking_enabled,
        "reasoning_effort": route.reasoning_effort,
        "provider_sort": route.provider_sort,
        "allow_provider_fallbacks": route.allow_provider_fallbacks,
        "require_provider_parameters": route.require_provider_parameters,
    }


def _model_generation_identity(model_call: ModelCall) -> dict[str, Any]:
    owner = getattr(model_call, "__self__", None)
    identity: dict[str, Any] = {"interface": "injected_model_call"}
    if owner is not None:
        owner_type = type(owner)
        identity["client_type"] = f"{owner_type.__module__}.{owner_type.__qualname__}"
    for field in (
        "max_tokens",
        "stream",
        "timeout_seconds",
        "total_deadline_seconds",
    ):
        value = getattr(owner, field, None)
        if isinstance(value, (bool, int, float, str)):
            identity[field] = value
    base_urls = getattr(owner, "base_urls", None)
    if isinstance(base_urls, dict):
        identity["base_urls"] = {
            str(provider): str(url)
            for provider, url in sorted(base_urls.items())
            if isinstance(provider, str) and isinstance(url, str)
        }
    provider_routing = getattr(owner, "provider_routing", None)
    if isinstance(provider_routing, Mapping):
        identity["provider_routing"] = {
            str(key): value
            for key, value in sorted(provider_routing.items())
            if isinstance(key, str)
        }
    return identity


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _without_ignored_keys(value: Any, *, ignored_keys: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _without_ignored_keys(item, ignored_keys=ignored_keys)
            for key, item in value.items()
            if key not in ignored_keys
        }
    if isinstance(value, list):
        return [_without_ignored_keys(item, ignored_keys=ignored_keys) for item in value]
    return value
