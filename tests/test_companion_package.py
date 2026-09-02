from __future__ import annotations

from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import textwrap

import pytest

from universe.companion_package import (
    CompanionPackage,
    PackageAssemblyError,
    assemble_companion_package,
    publish_companion_package,
)


FIXTURE = Path(__file__).parent / "fixtures" / "cc-mod6-com.runtime-graph.json"
GRAPH_ID = "graph-inteli-ciencia-computacao-mod6-computacao"


def _golden_graph() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _companion_with_validator(tmp_path: Path, source: str) -> Path:
    companion = tmp_path / "companion"
    scripts = companion / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "validate_graph_package.py").write_text(
        textwrap.dedent(source),
        encoding="utf-8",
    )
    return companion


def _accepting_companion(tmp_path: Path) -> Path:
    return _companion_with_validator(
        tmp_path,
        textwrap.dedent(
            """
            import json
            from pathlib import Path
            import sys

            root = Path(sys.argv[1])
            package = next(root.iterdir())
            graph = json.loads((package / "graph.json").read_text())
            intro = json.loads((package / "intro_notes.json").read_text())
            accepted = (
                {path.name for path in package.iterdir()}
                == {"graph.json", "intro_notes.json"}
                and package.name == graph["graph_id"]
                and intro["source_graph"]["graph_id"] == graph["graph_id"]
            )
            print(json.dumps({
                "schema_version": "companion_graph_package_acceptance.v1",
                "accepted": accepted,
                "graph_id": graph["graph_id"],
                "package_sha256": "a" * 64 if accepted else None,
                "issues": [] if accepted else [{"code": "fixture_rejection"}],
            }))
            raise SystemExit(0 if accepted else 2)
            """
        ),
    )


def _rejecting_companion(tmp_path: Path, code: str) -> Path:
    return _companion_with_validator(
        tmp_path,
        textwrap.dedent(
            f"""
            import json

            print(json.dumps({{
                "schema_version": "companion_graph_package_acceptance.v1",
                "accepted": False,
                "graph_id": None,
                "package_sha256": None,
                "issues": [{{"code": {code!r}}}],
            }}))
            raise SystemExit(2)
            """
        ),
    )


def _inconsistent_companion(tmp_path: Path) -> Path:
    return _companion_with_validator(
        tmp_path,
        textwrap.dedent(
            """
            import json

            print(json.dumps({
                "schema_version": "companion_graph_package_acceptance.v1",
                "accepted": True,
                "graph_id": "graph-wrong",
                "package_sha256": "a" * 64,
                "issues": [],
            }))
            raise SystemExit(2)
            """
        ),
    )


def _real_companion_repo() -> Path | None:
    for ancestor in Path(__file__).resolve().parents:
        candidate = ancestor / "companion"
        if (candidate / "scripts" / "validate_graph_package.py").is_file():
            return candidate
    return None


def _write_graph(tmp_path: Path, graph: dict) -> Path:
    path = tmp_path / "runtime-graph.json"
    path.write_text(json.dumps(graph), encoding="utf-8")
    return path


def test_golden_graph_maps_to_companion_package_documents() -> None:
    source = _golden_graph()

    package = CompanionPackage.from_final_assembly(source)

    assert package.graph_id == GRAPH_ID
    assert package.graph["graph_id"] == GRAPH_ID
    assert package.graph["display_name"] == "Computação"
    assert package.graph["institution_slug"] == "inteli"
    assert package.graph["professors"] == [
        "Fillipe Manoel Xavier Resina",
        "Rodolfo Riyoei Goya",
    ]
    assert "subject" not in package.graph
    assert package.intro_notes == {
        "artifact_type": "lesson_intro_notes",
        "schema_version": "lesson_intro_notes.v1",
        "source_graph": {"graph_id": GRAPH_ID},
        "lesson_order": [],
        "lessons": {},
    }
    assert source == _golden_graph()


@pytest.mark.parametrize(
    ("lesson_subject_code", "lesson_subject_slug", "display_name"),
    [
        ("COM", "computacao", "Computação"),
        ("LID", "lideranca", "Liderança"),
        ("MTF", "matematica", "Matemática"),
        ("NEG", "negocios", "Negócios"),
        ("UEX", "design", "User Experience"),
    ],
)
def test_legacy_lesson_subject_identity_maps_to_catalog_identity(
    lesson_subject_code: str,
    lesson_subject_slug: str,
    display_name: str,
) -> None:
    source = _golden_graph()
    source["subject"]["pipeline_subject_id"] = lesson_subject_code
    source["subject"]["title"] = lesson_subject_code

    package = CompanionPackage.from_final_assembly(source)

    assert package.graph_id == (
        f"graph-inteli-ciencia-computacao-mod6-{lesson_subject_slug}"
    )
    assert package.graph["display_name"] == display_name


@pytest.mark.parametrize(
    ("course_id", "course_slug"),
    [
        ("adm", "administracao"),
        ("cc", "ciencia-computacao"),
        ("common", "common-core"),
        ("engcomp", "engenharia-computacao"),
        ("es", "engenharia-software"),
        ("si", "sistemas-informacao"),
    ],
)
def test_legacy_course_identity_maps_to_catalog_identity(
    course_id: str,
    course_slug: str,
) -> None:
    source = _golden_graph()
    source["subject"]["course_id"] = course_id

    package = CompanionPackage.from_final_assembly(source)

    assert package.graph_id == (
        f"graph-inteli-{course_slug}-mod6-computacao"
    )


def test_accepted_package_is_published_with_exactly_two_files(tmp_path: Path) -> None:
    output_root = tmp_path / "output"

    package_dir = assemble_companion_package(
        FIXTURE,
        output_root,
        companion_repo=_accepting_companion(tmp_path),
    )

    assert package_dir == output_root / GRAPH_ID
    assert {path.name for path in package_dir.iterdir()} == {
        "graph.json",
        "intro_notes.json",
    }
    assert json.loads((package_dir / "graph.json").read_text())["graph_id"] == GRAPH_ID


def test_companion_rejection_leaves_no_package(tmp_path: Path) -> None:
    output_root = tmp_path / "output"

    with pytest.raises(
        PackageAssemblyError,
        match=r"Companion rejected the package: malformed_runtime_graph\.",
    ):
        assemble_companion_package(
            FIXTURE,
            output_root,
            companion_repo=_rejecting_companion(tmp_path, "malformed_runtime_graph"),
        )

    assert not output_root.exists()


def test_nonzero_validator_exit_fails_closed(tmp_path: Path) -> None:
    output_root = tmp_path / "output"

    with pytest.raises(
        PackageAssemblyError,
        match=r"Companion package validation failed: process exited 2",
    ):
        assemble_companion_package(
            FIXTURE,
            output_root,
            companion_repo=_inconsistent_companion(tmp_path),
        )

    assert not output_root.exists()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        (
            "artifact_type",
            "final_assembly",
            "Expected a Phase 10 runtime_graph artifact; got 'final_assembly'",
        ),
        (
            "schema_version",
            "runtime_graph.v1",
            "Expected legacy schema runtime_graph.v0; got 'runtime_graph.v1'",
        ),
    ],
)
def test_unsupported_final_assembly_contract_blocks_package(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
) -> None:
    graph = _golden_graph()
    graph[field] = value
    output_root = tmp_path / "output"

    with pytest.raises(PackageAssemblyError, match=rf"{message}\."):
        assemble_companion_package(
            _write_graph(tmp_path, graph),
            output_root,
            companion_repo=_accepting_companion(tmp_path),
        )

    assert not output_root.exists()


def test_lesson_without_teachable_segment_blocks_package(tmp_path: Path) -> None:
    graph = _golden_graph()
    graph["lessons"][0]["segments"] = []
    output_root = tmp_path / "output"

    with pytest.raises(
        PackageAssemblyError,
        match=r"Lesson 'lesson-2026-04-23-vis-o-geral-de-otimiza-o-combinat-ria' "
        r"has no teachable Lesson Segment\.",
    ):
        assemble_companion_package(
            _write_graph(tmp_path, graph),
            output_root,
            companion_repo=_accepting_companion(tmp_path),
        )

    assert not output_root.exists()


def test_segment_pointing_to_missing_concept_blocks_package(tmp_path: Path) -> None:
    graph = _golden_graph()
    graph["lessons"][0]["segments"][0]["concept_ids"].append("concept-missing")
    output_root = tmp_path / "output"

    with pytest.raises(
        PackageAssemblyError,
        match=r"Lesson Segment 'segment_001' references missing Concept "
        r"'concept-missing'\.",
    ):
        assemble_companion_package(
            _write_graph(tmp_path, graph),
            output_root,
            companion_repo=_accepting_companion(tmp_path),
        )

    assert not output_root.exists()


@pytest.mark.parametrize(
    ("knowledge_type", "message"),
    [
        (None, "is missing knowledge_type"),
        ("theoretical", "has unsupported knowledge_type 'theoretical'"),
    ],
)
def test_invalid_knowledge_type_blocks_package(
    tmp_path: Path,
    knowledge_type: str | None,
    message: str,
) -> None:
    graph = _golden_graph()
    concept = graph["concepts"][0]
    if knowledge_type is None:
        concept.pop("knowledge_type")
    else:
        concept["knowledge_type"] = knowledge_type
    output_root = tmp_path / "output"

    with pytest.raises(
        PackageAssemblyError,
        match=rf"Concept '{concept['concept_id']}' {message}\.",
    ):
        assemble_companion_package(
            _write_graph(tmp_path, graph),
            output_root,
            companion_repo=_accepting_companion(tmp_path),
        )

    assert not output_root.exists()


def test_missing_graph_metadata_blocks_package(tmp_path: Path) -> None:
    graph = _golden_graph()
    graph.pop("subject")
    output_root = tmp_path / "output"

    with pytest.raises(
        PackageAssemblyError,
        match=r"Final Assembly graph is missing graph metadata: subject\.",
    ):
        assemble_companion_package(
            _write_graph(tmp_path, graph),
            output_root,
            companion_repo=_accepting_companion(tmp_path),
        )

    assert not output_root.exists()


@pytest.mark.parametrize(
    "field",
    ["course_id", "module_id", "pipeline_subject_id", "title", "professors"],
)
def test_missing_subject_metadata_names_the_field(
    tmp_path: Path,
    field: str,
) -> None:
    graph = _golden_graph()
    graph["subject"].pop(field)

    with pytest.raises(
        PackageAssemblyError,
        match=rf"Final Assembly graph is missing graph metadata: subject\.{field}\.",
    ):
        assemble_companion_package(
            _write_graph(tmp_path, graph),
            tmp_path / "output",
            companion_repo=_accepting_companion(tmp_path),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("course_id", "unknown", "Unsupported legacy course_id 'unknown'"),
        (
            "pipeline_subject_id",
            "XYZ",
            "Unsupported legacy Lesson Subject code 'XYZ'",
        ),
        ("module_id", "module 6", "Invalid legacy module_id 'module 6'"),
    ],
)
def test_unsupported_graph_metadata_is_operator_readable(
    field: str,
    value: str,
    message: str,
) -> None:
    graph = _golden_graph()
    graph["subject"][field] = value

    with pytest.raises(PackageAssemblyError, match=rf"{message}\."):
        CompanionPackage.from_final_assembly(graph)


def test_malformed_intro_notes_block_package(tmp_path: Path) -> None:
    package = CompanionPackage.from_final_assembly(_golden_graph())
    package = replace(package, intro_notes={"lessons": []})
    output_root = tmp_path / "output"

    with pytest.raises(
        PackageAssemblyError,
        match=rf"Intro-notes artifact is malformed for graph '{GRAPH_ID}'\.",
    ):
        publish_companion_package(
            package,
            output_root,
            companion_repo=_accepting_companion(tmp_path),
        )

    assert not output_root.exists()


def test_publication_io_failure_is_operator_readable(tmp_path: Path) -> None:
    package = CompanionPackage.from_final_assembly(_golden_graph())
    output_root = tmp_path / "output"
    output_root.write_text("not a directory", encoding="utf-8")

    with pytest.raises(
        PackageAssemblyError,
        match=r"Companion package publication failed: .+",
    ):
        publish_companion_package(
            package,
            output_root,
            companion_repo=_accepting_companion(tmp_path),
        )

    assert output_root.is_file()


def test_module_cli_publishes_validated_package(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    companion_repo = _accepting_companion(tmp_path)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = "src"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "universe.companion_package",
            str(FIXTURE),
            str(output_root),
            "--companion-repo",
            str(companion_repo),
        ],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == str(output_root / GRAPH_ID)
    assert (output_root / GRAPH_ID / "graph.json").is_file()


@pytest.mark.skipif(
    os.environ.get("RUN_COMPANION_CONTRACT") != "1",
    reason="set RUN_COMPANION_CONTRACT=1 with a sibling Companion checkout",
)
def test_golden_package_passes_real_companion_validator(tmp_path: Path) -> None:
    companion_repo = _real_companion_repo()
    assert companion_repo is not None

    package_dir = assemble_companion_package(
        FIXTURE,
        tmp_path / "output",
        companion_repo=companion_repo,
        replace_graph_id=GRAPH_ID,
    )

    assert {path.name for path in package_dir.iterdir()} == {
        "graph.json",
        "intro_notes.json",
    }
