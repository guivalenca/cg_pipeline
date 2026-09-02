"""Small local adapter to Companion's graph-authoring namespace."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Callable

import psycopg


NAMESPACE_SCHEMA = "companion_graph_namespace.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPANION_REPO = PROJECT_ROOT.parent / "companion"


class CompanionSeamError(RuntimeError):
    """Companion's graph namespace could not be read."""


def _environment() -> dict[str, str]:
    environment = os.environ.copy()
    configured_url = environment.get("COMPANION_DATABASE_URL", "").strip()
    if configured_url:
        environment["DATABASE_URL"] = configured_url
    else:
        environment.pop("DATABASE_URL", None)
    configured_schema = environment.get("COMPANION_PLATFORM_SCHEMA", "").strip()
    if configured_schema:
        environment["PLATFORM_SCHEMA"] = configured_schema
    else:
        environment.pop("PLATFORM_SCHEMA", None)
    return environment


def _run_json(
    companion_repo: Path,
    script_name: str,
    *,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict:
    script = companion_repo / "scripts" / script_name
    if not script.is_file():
        raise CompanionSeamError(f"Companion interface not found at {script}")
    environment = _environment()
    python = environment.get("COMPANION_PYTHON", "python3").strip() or "python3"
    try:
        result = run(
            [python, str(script)],
            cwd=companion_repo,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CompanionSeamError(f"Companion interface failed: {exc}") from exc
    if result.returncode != 0:
        detail = (result.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else f"process exited {result.returncode}"
        raise CompanionSeamError(f"Companion interface failed: {reason}")
    try:
        document = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CompanionSeamError("Companion returned invalid JSON") from exc
    if not isinstance(document, dict):
        raise CompanionSeamError("Companion returned an invalid document")
    return document


def _validated_namespace(document: object) -> dict:
    if not isinstance(document, dict):
        raise CompanionSeamError("Companion returned an invalid document")
    if document.get("schema_version") != NAMESPACE_SCHEMA:
        raise CompanionSeamError("Companion graph namespace version is not supported")
    institutions = document.get("institutions")
    graph_ids = document.get("graph_ids")
    if not isinstance(institutions, list) or not isinstance(graph_ids, list):
        raise CompanionSeamError("Companion graph namespace is incomplete")
    return document


def graph_namespace(
    companion_repo: Path | None = None,
    *,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict:
    configured_snapshot = os.environ.get("COMPANION_GRAPH_NAMESPACE_FILE", "").strip()
    if configured_snapshot:
        try:
            document = json.loads(Path(configured_snapshot).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CompanionSeamError(
                f"Companion graph namespace snapshot could not be read: {exc}"
            ) from exc
    else:
        document = _run_json(
            companion_repo or DEFAULT_COMPANION_REPO,
            "export_graph_namespace.py",
            run=run,
        )
    return _validated_namespace(document)


def select_institution(document: dict, slug: str) -> dict:
    matches = [
        institution
        for institution in document.get("institutions", [])
        if institution.get("slug") == slug
    ]
    if len(matches) != 1:
        raise ValueError("Selecione uma instituição existente no Companion.")
    institution = matches[0]
    if not isinstance(institution.get("name"), str) or not institution["name"].strip():
        raise CompanionSeamError("Companion returned an invalid Institution name")
    return institution


def remember_institution(
    conn: psycopg.Connection,
    namespace: dict,
    slug: str,
) -> dict:
    """Persist the exact Institution label used by a durable Syllabus."""
    institution = select_institution(namespace, slug)
    conn.execute(
        "INSERT INTO institution (id, name) VALUES (%s, %s)"
        " ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name",
        (institution["slug"], institution["name"].strip()),
    )
    return {"id": institution["slug"], "name": institution["name"].strip()}
