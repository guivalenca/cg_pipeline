"""Small local adapter to Companion's graph namespace and package acceptance."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Callable

import psycopg


NAMESPACE_SCHEMA = "companion_graph_namespace.v1"
ACCEPTANCE_SCHEMA = "companion_graph_package_acceptance.v1"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPANION_REPO = PROJECT_ROOT.parent / "companion"


class CompanionSeamError(RuntimeError):
    """Companion could not answer a namespace or package-acceptance request."""


class CompanionRejectedPackage(ValueError):
    """Companion assessed the exact package and rejected its export."""

    def __init__(self, result: dict) -> None:
        self.result = result
        codes = ", ".join(
            str(issue.get("code")) for issue in result.get("issues", [])
        ) or "unknown_rejection"
        super().__init__(f"Companion rejected the graph package: {codes}")


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
    arguments: list[str] | None = None,
    *,
    accepted_return_codes: tuple[int, ...] = (0,),
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict:
    script = companion_repo / "scripts" / script_name
    if not script.is_file():
        raise CompanionSeamError(f"Companion interface not found at {script}")
    environment = _environment()
    python = environment.get("COMPANION_PYTHON", "python3").strip() or "python3"
    try:
        result = run(
            [python, str(script), *(arguments or [])],
            cwd=companion_repo,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise CompanionSeamError(f"Companion interface failed: {exc}") from exc
    if result.returncode not in accepted_return_codes:
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


def graph_namespace(
    companion_repo: Path | None = None,
    *,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict:
    document = _run_json(
        companion_repo or DEFAULT_COMPANION_REPO,
        "export_graph_namespace.py",
        run=run,
    )
    if document.get("schema_version") != NAMESPACE_SCHEMA:
        raise CompanionSeamError("Companion graph namespace version is not supported")
    institutions = document.get("institutions")
    graph_ids = document.get("graph_ids")
    if not isinstance(institutions, list) or not isinstance(graph_ids, list):
        raise CompanionSeamError("Companion graph namespace is incomplete")
    return document


def validate_package(
    candidate_root: Path,
    companion_repo: Path | None = None,
    *,
    replace_graph_id: str | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict:
    arguments = [str(candidate_root.resolve())]
    if replace_graph_id:
        arguments.extend(("--replace-graph-id", replace_graph_id))
    document = _run_json(
        companion_repo or DEFAULT_COMPANION_REPO,
        "validate_graph_package.py",
        arguments,
        accepted_return_codes=(0, 2),
        run=run,
    )
    if document.get("schema_version") != ACCEPTANCE_SCHEMA:
        raise CompanionSeamError("Companion package acceptance version is not supported")
    if not isinstance(document.get("accepted"), bool):
        raise CompanionSeamError("Companion package acceptance result is incomplete")
    package_hash = document.get("package_sha256")
    if document["accepted"] and (
        not isinstance(package_hash, str)
        or len(package_hash) != 64
        or any(character not in "0123456789abcdef" for character in package_hash)
    ):
        raise CompanionSeamError("Companion acceptance receipt has no valid package hash")
    return document


def require_export_acceptance(
    candidate_root: Path,
    companion_repo: Path | None = None,
    *,
    replace_graph_id: str | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> dict:
    """Return a hash-bound acceptance receipt or stop the export."""
    result = validate_package(
        candidate_root,
        companion_repo,
        replace_graph_id=replace_graph_id,
        run=run,
    )
    if not result["accepted"]:
        raise CompanionRejectedPackage(result)
    return result


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
