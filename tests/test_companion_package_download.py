from __future__ import annotations

from dataclasses import replace
from io import BytesIO
import json
from pathlib import Path
import sys
import textwrap
from zipfile import ZipFile

import pytest

from fake_companion import accepting_companion
from test_graph_revision import _seed_finished_build, _seed_subject
from universe import companion_export, graph_revision
from universe.companion_package import (
    CompanionPackage,
    PackageAssemblyError,
    validated_package_archive,
)


GRAPH_ID = "graph-inteli-graduacao-ciencia-da-computacao-com"


def _real_companion_repo() -> Path | None:
    for ancestor in Path(__file__).resolve().parents:
        candidate = ancestor / "companion"
        if (candidate / "app" / "graph_catalog").is_dir():
            return candidate
    return None


def _graph_revision(*, graph_id: str = GRAPH_ID) -> dict:
    concept_id = "concept-lesson-one-build-one"
    return {
        "artifact_type": "runtime_graph",
        "schema_version": "runtime_graph.v0",
        "graph_id": graph_id,
        "subject": {
            "graph_id": graph_id,
            "course_id": "graduacao-ciencia-da-computacao",
            "module_id": "graduacao-ciencia-da-computacao:v0001",
            "pipeline_subject_id": "COM",
            "title": "Computação",
            "language": "pt-BR",
            "professors": [],
        },
        "concepts": [
            {
                "concept_id": concept_id,
                "display_code": "COM-001",
                "label": "Busca em profundidade",
                "knowledge_type": "conceptual",
                "description": "Estratégia de exploração de estados.",
                "coverage_criteria": ["Explicar a ordem de exploração."],
                "common_misconceptions": [],
                "dependencies": {"blocking": [], "hard": [], "soft": []},
            }
        ],
        "lessons": [
            {
                "lesson_id": "lesson-one",
                "title": "Busca em profundidade",
                "segments": [
                    {
                        "segment_id": "segment-one",
                        "label": "Exploração",
                        "instructional_role": "teach",
                        "concept_ids": [concept_id],
                    }
                ],
            }
        ],
        "self_study_resources": [],
    }


def _disagreeing_companion(tmp_path: Path) -> Path:
    companion = tmp_path / "disagreeing-companion"
    scripts = companion / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "validate_graph_package.py").write_text(
        textwrap.dedent(
            """
            import json

            print(json.dumps({
                "schema_version": "companion_graph_package_acceptance.v1",
                "accepted": True,
                "graph_id": "graph-runtime-disagrees",
                "package_sha256": "a" * 64,
                "issues": [],
            }))
            """
        ),
        encoding="utf-8",
    )
    return companion


def _environment_checking_companion(tmp_path: Path) -> Path:
    companion = tmp_path / "environment-companion"
    scripts = companion / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "validate_graph_package.py").write_text(
        textwrap.dedent(
            """
            import json
            import os
            from pathlib import Path
            import sys

            graph = json.loads(
                (next(Path(sys.argv[1]).iterdir()) / "graph.json").read_text()
            )
            accepted = (
                os.environ.get("DATABASE_URL") == "postgresql://companion"
                and os.environ.get("PLATFORM_SCHEMA") == "companion_test"
            )
            print(json.dumps({
                "schema_version": "companion_graph_package_acceptance.v1",
                "accepted": accepted,
                "graph_id": graph["graph_id"] if accepted else None,
                "package_sha256": "a" * 64 if accepted else None,
                "issues": [] if accepted else [{"code": "wrong_database"}],
            }))
            raise SystemExit(0 if accepted else 2)
            """
        ),
        encoding="utf-8",
    )
    return companion


def test_graph_revision_becomes_the_exact_validated_two_file_archive(tmp_path: Path):
    package = CompanionPackage.from_graph_revision(
        _graph_revision(),
        graph_id=GRAPH_ID,
        display_name="Graduação Ciência da Computação · Computação",
        institution_slug="inteli",
    )

    archive = validated_package_archive(
        package,
        companion_repo=accepting_companion(tmp_path, require_replacement=True),
        replace_graph_id=GRAPH_ID,
    )

    assert archive.filename == f"{GRAPH_ID}.zip"
    with ZipFile(BytesIO(archive.body)) as bundle:
        assert set(bundle.namelist()) == {
            f"{GRAPH_ID}/graph.json",
            f"{GRAPH_ID}/intro_notes.json",
        }
        graph = json.loads(bundle.read(f"{GRAPH_ID}/graph.json"))
        intro_notes = json.loads(bundle.read(f"{GRAPH_ID}/intro_notes.json"))
    assert graph["graph_id"] == GRAPH_ID
    assert graph["display_name"] == "Graduação Ciência da Computação · Computação"
    assert graph["institution_slug"] == "inteli"
    assert "subject" not in graph
    assert intro_notes == {
        "artifact_type": "lesson_intro_notes",
        "schema_version": "lesson_intro_notes.v1",
        "source_graph": {"graph_id": GRAPH_ID},
        "lesson_order": [],
        "lessons": {},
    }


def _archived_graph(body: bytes, graph_id: str) -> dict:
    with ZipFile(BytesIO(body)) as archive:
        return json.loads(archive.read(f"{graph_id}/graph.json"))


def test_current_and_explicit_graph_revisions_export_their_own_content(db, tmp_path: Path):
    syllabus_id, version_id, graph_id = _seed_subject(db, "package-history")
    db.execute(
        "INSERT INTO institution (id, name) VALUES ('inteli', 'Inteli')"
        " ON CONFLICT (id) DO NOTHING"
    )
    db.execute(
        "UPDATE syllabus SET institution_id = 'inteli' WHERE id = %s",
        (syllabus_id,),
    )
    db.commit()
    first_build, _ = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="lesson-one",
        build_label="v1",
        lesson_seq=1,
    )
    first = graph_revision.accept(db, first_build, actor="founder")
    second_build, _ = _seed_finished_build(
        db,
        version_id=version_id,
        graph_id=graph_id,
        lesson_id="lesson-two",
        build_label="v1",
        lesson_seq=2,
    )
    graph_revision.accept(db, second_build, actor="founder")
    companion_repo = accepting_companion(tmp_path, require_replacement=True)

    current = companion_export.current_package(
        db,
        graph_id,
        companion_repo=companion_repo,
        occupied_graph_ids={graph_id},
    )
    historical = companion_export.revision_package(
        db,
        first["revision"]["id"],
        companion_repo=companion_repo,
        occupied_graph_ids={graph_id},
    )

    assert [lesson["lesson_id"] for lesson in _archived_graph(current.body, graph_id)["lessons"]] == [
        "lesson-one",
        "lesson-two",
    ]
    assert [lesson["lesson_id"] for lesson in _archived_graph(historical.body, graph_id)["lessons"]] == [
        "lesson-one"
    ]


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda graph: graph["subject"].pop("course_id"),
            "Final Assembly graph is missing graph metadata: subject.course_id.",
        ),
        (
            lambda graph: graph["lessons"][0].update(segments=[]),
            "Lesson 'lesson-one' has no teachable Lesson Segment.",
        ),
        (
            lambda graph: graph["lessons"][0]["segments"][0]["concept_ids"].append(
                "concept-missing"
            ),
            "Lesson Segment 'segment-one' references missing Concept 'concept-missing'.",
        ),
        (
            lambda graph: graph["concepts"][0].update(knowledge_type="theoretical"),
            "Concept 'concept-lesson-one-build-one' has unsupported knowledge_type 'theoretical'.",
        ),
        (
            lambda graph: graph.update(graph_id="graph-build-disagrees"),
            "Graph Revision identity disagrees with its stored Subject graph id.",
        ),
    ],
)
def test_each_graph_blocker_has_a_distinct_operator_message(mutate, message: str):
    graph = _graph_revision()
    mutate(graph)

    with pytest.raises(PackageAssemblyError, match=message.replace(".", r"\.")):
        CompanionPackage.from_graph_revision(
            graph,
            graph_id=GRAPH_ID,
            display_name="Graduação Ciência da Computação · Computação",
            institution_slug="inteli",
        )


def test_invalid_empty_intro_notes_shape_is_a_distinct_blocker(tmp_path: Path):
    package = CompanionPackage.from_graph_revision(
        _graph_revision(),
        graph_id=GRAPH_ID,
        display_name="Graduação Ciência da Computação · Computação",
        institution_slug="inteli",
    )
    package = replace(package, intro_notes={"lessons": []})

    with pytest.raises(
        PackageAssemblyError,
        match=f"Intro-notes artifact is malformed for graph '{GRAPH_ID}'\\.",
    ):
        validated_package_archive(
            package,
            companion_repo=accepting_companion(tmp_path, require_replacement=True),
        )


def test_build_runtime_disagreement_fails_closed(tmp_path: Path):
    package = CompanionPackage.from_graph_revision(
        _graph_revision(),
        graph_id=GRAPH_ID,
        display_name="Graduação Ciência da Computação · Computação",
        institution_slug="inteli",
    )

    with pytest.raises(
        PackageAssemblyError,
        match="Companion validation result disagrees with Graph Revision '",
    ):
        validated_package_archive(
            package,
            companion_repo=_disagreeing_companion(tmp_path),
        )


def test_validation_uses_companion_database_not_authoring_database(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("DATABASE_URL", "postgresql://authoring")
    monkeypatch.setenv("PLATFORM_SCHEMA", "authoring")
    monkeypatch.setenv("COMPANION_DATABASE_URL", "postgresql://companion")
    monkeypatch.setenv("COMPANION_PLATFORM_SCHEMA", "companion_test")
    package = CompanionPackage.from_graph_revision(
        _graph_revision(),
        graph_id=GRAPH_ID,
        display_name="Graduação Ciência da Computação · Computação",
        institution_slug="inteli",
    )

    archive = validated_package_archive(
        package,
        companion_repo=_environment_checking_companion(tmp_path),
    )

    assert archive.filename == f"{GRAPH_ID}.zip"


@pytest.mark.skipif(
    _real_companion_repo() is None,
    reason="requires the sibling Companion checkout",
)
def test_companion_catalog_accepts_empty_then_generated_lesson_previews(tmp_path: Path):
    companion_repo = _real_companion_repo()
    assert companion_repo is not None
    sys.path.insert(0, str(companion_repo))
    try:
        from app.graph_catalog import load_filesystem_graph_catalog
        from scripts.lesson_intro_notes.pipeline import generate_reference_file

        package = CompanionPackage.from_graph_revision(
            _graph_revision(),
            graph_id=GRAPH_ID,
            display_name="Graduação Ciência da Computação · Computação",
            institution_slug="inteli",
        )
        archive = validated_package_archive(
            package,
            companion_repo=accepting_companion(tmp_path, require_replacement=True),
            replace_graph_id=GRAPH_ID,
        )
        package_root = tmp_path / "unpacked"
        with ZipFile(BytesIO(archive.body)) as bundle:
            bundle.extractall(package_root)

        empty = load_filesystem_graph_catalog(package_root).resolve(GRAPH_ID)
        assert dict(empty.intro_notes["lessons"]) == {}

        package_dir = package_root / GRAPH_ID
        generate_reference_file(
            graph_path=package_dir / "graph.json",
            output_path=package_dir / "intro_notes.json",
            note_provider=lambda _lesson: {
                "headline": "Prepare-se para explorar",
                "summary": "Uma visão da aula.",
            },
        )

        completed = load_filesystem_graph_catalog(package_root).resolve(GRAPH_ID)
        assert list(completed.intro_notes["lesson_order"]) == ["lesson-one"]
    finally:
        sys.path.remove(str(companion_repo))
