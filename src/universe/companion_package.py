"""Assemble legacy Final Assembly output into a Companion graph package."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Sequence


_INSTITUTION_SLUG = "inteli"
_COURSE_SLUGS = {
    "adm": "administracao",
    "cc": "ciencia-computacao",
    "common": "common-core",
    "engcomp": "engenharia-computacao",
    "es": "engenharia-software",
    "si": "sistemas-informacao",
}
_LESSON_SUBJECTS = {
    "COM": ("computacao", "Computação"),
    "LID": ("lideranca", "Liderança"),
    "MTF": ("matematica", "Matemática"),
    "NEG": ("negocios", "Negócios"),
    "UEX": ("design", "User Experience"),
}
_KNOWLEDGE_TYPES = {"conceptual", "procedural", "factual", "applied"}


class PackageAssemblyError(ValueError):
    """A Final Assembly graph cannot be published as a Companion package."""


@dataclass(frozen=True)
class CompanionPackage:
    """The two JSON documents accepted by Companion's Graph Catalog."""

    graph_id: str
    graph: dict[str, Any]
    intro_notes: dict[str, Any]

    @classmethod
    def from_final_assembly(
        cls, final_graph: Mapping[str, Any]
    ) -> "CompanionPackage":
        subject = _validate_final_assembly(final_graph)
        course_id = str(subject["course_id"]).strip().lower()
        if course_id not in _COURSE_SLUGS:
            raise PackageAssemblyError(
                f"Unsupported legacy course_id {subject['course_id']!r}."
            )
        course_slug = _COURSE_SLUGS[course_id]
        module_slug = str(subject["module_id"]).strip().lower()
        if re.fullmatch(r"[a-z][a-z0-9-]*", module_slug) is None:
            raise PackageAssemblyError(
                f"Invalid legacy module_id {subject['module_id']!r}."
            )
        lesson_subject_code = str(subject["pipeline_subject_id"]).strip().upper()
        if lesson_subject_code not in _LESSON_SUBJECTS:
            raise PackageAssemblyError(
                f"Unsupported legacy Lesson Subject code "
                f"{subject['pipeline_subject_id']!r}."
            )
        lesson_subject_slug, display_name = _LESSON_SUBJECTS[lesson_subject_code]
        graph_id = "-".join(
            (
                "graph",
                _INSTITUTION_SLUG,
                course_slug,
                module_slug,
                lesson_subject_slug,
            )
        )
        graph = deepcopy(dict(final_graph))
        graph.pop("subject")
        graph.update(
            {
                "graph_id": graph_id,
                "display_name": display_name,
                "institution_slug": _INSTITUTION_SLUG,
                "professors": deepcopy(subject["professors"]),
            }
        )
        return cls(
            graph_id=graph_id,
            graph=graph,
            intro_notes=_empty_intro_notes(graph_id),
        )


def _validate_final_assembly(
    final_graph: Mapping[str, Any],
) -> Mapping[str, Any]:
    artifact_type = final_graph.get("artifact_type")
    if artifact_type != "runtime_graph":
        raise PackageAssemblyError(
            f"Expected a Phase 10 runtime_graph artifact; got {artifact_type!r}."
        )
    schema_version = final_graph.get("schema_version")
    if schema_version != "runtime_graph.v0":
        raise PackageAssemblyError(
            f"Expected legacy schema runtime_graph.v0; got {schema_version!r}."
        )
    subject = final_graph.get("subject")
    if not isinstance(subject, Mapping):
        raise PackageAssemblyError(
            "Final Assembly graph is missing graph metadata: subject."
        )
    for field in ("course_id", "module_id", "pipeline_subject_id", "title"):
        if not isinstance(subject.get(field), str) or not subject[field].strip():
            raise PackageAssemblyError(
                f"Final Assembly graph is missing graph metadata: subject.{field}."
            )
    professors = subject.get("professors")
    if not isinstance(professors, list) or not all(
        isinstance(professor, str) and bool(professor.strip())
        for professor in professors
    ):
        raise PackageAssemblyError(
            "Final Assembly graph is missing graph metadata: subject.professors."
        )
    concepts = final_graph.get("concepts")
    if not isinstance(concepts, list):
        raise PackageAssemblyError("Final Assembly graph has no Concept list.")
    for concept in concepts:
        if not isinstance(concept, Mapping):
            raise PackageAssemblyError(
                "Final Assembly graph contains a malformed Concept."
            )
        concept_id = str(concept.get("concept_id") or "<missing concept_id>")
        knowledge_type = concept.get("knowledge_type")
        if not isinstance(knowledge_type, str) or not knowledge_type.strip():
            raise PackageAssemblyError(
                f"Concept {concept_id!r} is missing knowledge_type."
            )
        if knowledge_type not in _KNOWLEDGE_TYPES:
            raise PackageAssemblyError(
                f"Concept {concept_id!r} has unsupported knowledge_type "
                f"{knowledge_type!r}."
            )
    concept_ids = {
        str(concept["concept_id"])
        for concept in concepts
        if isinstance(concept, Mapping) and concept.get("concept_id")
    }
    lessons = final_graph.get("lessons")
    if not isinstance(lessons, list):
        raise PackageAssemblyError("Final Assembly graph has no Lesson list.")
    for lesson in lessons:
        if not isinstance(lesson, Mapping):
            raise PackageAssemblyError(
                "Final Assembly graph contains a malformed Lesson."
            )
        lesson_id = str(lesson.get("lesson_id") or "<missing lesson_id>")
        segments = lesson.get("segments")
        has_teachable_segment = isinstance(segments, list) and any(
            isinstance(segment, Mapping)
            and segment.get("instructional_role", "teach") == "teach"
            and isinstance(segment.get("concept_ids"), list)
            and bool(segment["concept_ids"])
            for segment in segments
        )
        if not has_teachable_segment:
            raise PackageAssemblyError(
                f"Lesson {lesson_id!r} has no teachable Lesson Segment."
            )
        for segment in segments:
            if not isinstance(segment, Mapping):
                continue
            segment_id = str(segment.get("segment_id") or "<missing segment_id>")
            references = segment.get("concept_ids")
            if not isinstance(references, list):
                continue
            for reference in references:
                if reference not in concept_ids:
                    raise PackageAssemblyError(
                        f"Lesson Segment {segment_id!r} references missing "
                        f"Concept {reference!r}."
                    )
    return subject


def assemble_companion_package(
    final_graph_path: Path,
    output_root: Path,
    *,
    companion_repo: Path,
    replace_graph_id: str | None = None,
) -> Path:
    """Validate and publish one Final Assembly graph as a two-file package."""
    try:
        final_graph = json.loads(Path(final_graph_path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageAssemblyError(
            f"Final Assembly graph could not be read: {exc}"
        ) from exc
    if not isinstance(final_graph, dict):
        raise PackageAssemblyError("Final Assembly graph must be a JSON object.")

    package = CompanionPackage.from_final_assembly(final_graph)
    return publish_companion_package(
        package,
        output_root,
        companion_repo=companion_repo,
        replace_graph_id=replace_graph_id,
    )


def publish_companion_package(
    package: CompanionPackage,
    output_root: Path,
    *,
    companion_repo: Path,
    replace_graph_id: str | None = None,
) -> Path:
    """Validate and atomically publish already assembled package documents."""
    if package.intro_notes != _empty_intro_notes(package.graph_id):
        raise PackageAssemblyError(
            f"Intro-notes artifact is malformed for graph {package.graph_id!r}."
        )
    destination = Path(output_root) / package.graph_id
    if destination.exists():
        raise PackageAssemblyError(
            f"Companion package destination already exists: {destination}"
        )

    output_root = Path(output_root)
    try:
        output_root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(
            prefix="companion-package-", dir=output_root.parent
        ) as temporary:
            candidate_root = Path(temporary)
            candidate_package = candidate_root / package.graph_id
            candidate_package.mkdir()
            _write_json(candidate_package / "graph.json", package.graph)
            _write_json(candidate_package / "intro_notes.json", package.intro_notes)
            _require_companion_acceptance(
                candidate_root,
                Path(companion_repo),
                replace_graph_id=replace_graph_id,
            )
            output_root.mkdir(parents=True, exist_ok=True)
            candidate_package.replace(destination)
    except PackageAssemblyError:
        raise
    except OSError as exc:
        raise PackageAssemblyError(
            f"Companion package publication failed: {exc}"
        ) from exc
    return destination


def _empty_intro_notes(graph_id: str) -> dict[str, Any]:
    return {
        "artifact_type": "lesson_intro_notes",
        "schema_version": "lesson_intro_notes.v1",
        "source_graph": {"graph_id": graph_id},
        "lesson_order": [],
        "lessons": {},
    }


def _write_json(path: Path, document: Mapping[str, Any]) -> None:
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _require_companion_acceptance(
    candidate_root: Path,
    companion_repo: Path,
    *,
    replace_graph_id: str | None,
) -> None:
    script = companion_repo / "scripts" / "validate_graph_package.py"
    if not script.is_file():
        raise PackageAssemblyError(
            f"Companion package validator was not found at {script}."
        )
    arguments = [
        os.environ.get("COMPANION_PYTHON", sys.executable),
        str(script),
        str(candidate_root),
    ]
    if replace_graph_id is not None:
        arguments.extend(("--replace-graph-id", replace_graph_id))
    try:
        result = subprocess.run(
            arguments,
            cwd=companion_repo,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PackageAssemblyError(
            f"Companion package validation failed: {exc}"
        ) from exc
    if result.returncode not in {0, 2}:
        detail = (result.stderr or "").strip().splitlines()
        reason = detail[-1] if detail else f"process exited {result.returncode}"
        raise PackageAssemblyError(f"Companion package validation failed: {reason}")
    try:
        acceptance = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise PackageAssemblyError(
            "Companion package validator returned invalid JSON."
        ) from exc
    if not isinstance(acceptance, dict) or not isinstance(
        acceptance.get("accepted"), bool
    ):
        raise PackageAssemblyError(
            "Companion package validator returned an incomplete result."
        )
    if not acceptance["accepted"]:
        codes = [
            str(issue.get("code"))
            for issue in acceptance.get("issues", [])
            if isinstance(issue, dict) and issue.get("code")
        ]
        reason = ", ".join(codes) or "unknown rejection"
        raise PackageAssemblyError(f"Companion rejected the package: {reason}.")
    if result.returncode != 0:
        raise PackageAssemblyError(
            "Companion package validation failed: "
            f"process exited {result.returncode}"
        )


def _default_companion_repo() -> Path:
    configured = os.environ.get("COMPANION_REPO", "").strip()
    if configured:
        return Path(configured)
    project_root = Path(__file__).resolve().parents[2]
    for ancestor in project_root.parents:
        candidate = ancestor / "companion"
        if (candidate / "scripts" / "validate_graph_package.py").is_file():
            return candidate
    return project_root.parent / "companion"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("final_graph", type=Path)
    parser.add_argument("output_root", type=Path)
    parser.add_argument(
        "--companion-repo",
        type=Path,
        default=_default_companion_repo(),
        help="Companion checkout containing scripts/validate_graph_package.py.",
    )
    parser.add_argument(
        "--replace-graph-id",
        help="Validate as an explicit replacement of this deployed graph id.",
    )
    arguments = parser.parse_args(argv)
    try:
        destination = assemble_companion_package(
            arguments.final_graph,
            arguments.output_root,
            companion_repo=arguments.companion_repo,
            replace_graph_id=arguments.replace_graph_id,
        )
    except PackageAssemblyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(destination)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
