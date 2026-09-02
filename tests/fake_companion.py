"""Shared fake implementations of Companion's package-validator protocol."""

from pathlib import Path
import textwrap


def accepting_companion(
    tmp_path: Path, *, require_replacement: bool
) -> Path:
    companion = tmp_path / "companion"
    scripts = companion / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "validate_graph_package.py").write_text(
        textwrap.dedent(
            f"""
            import json
            from pathlib import Path
            import sys

            root = Path(sys.argv[1])
            package = next(root.iterdir())
            graph = json.loads((package / "graph.json").read_text())
            intro = json.loads((package / "intro_notes.json").read_text())
            replacement_matches = (
                sys.argv[2:] == ["--replace-graph-id", graph["graph_id"]]
            )
            accepted = (
                {{path.name for path in package.iterdir()}}
                == {{"graph.json", "intro_notes.json"}}
                and package.name == graph["graph_id"]
                and intro["source_graph"]["graph_id"] == graph["graph_id"]
                and (not {require_replacement!r} or replacement_matches)
            )
            print(json.dumps({{
                "schema_version": "companion_graph_package_acceptance.v1",
                "accepted": accepted,
                "graph_id": graph["graph_id"],
                "package_sha256": "a" * 64 if accepted else None,
                "issues": [] if accepted else [{{"code": "fixture_rejection"}}],
            }}))
            raise SystemExit(0 if accepted else 2)
            """
        ),
        encoding="utf-8",
    )
    return companion
