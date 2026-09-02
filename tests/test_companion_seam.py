import json
import subprocess

import pytest

from universe import companion_seam


NAMESPACE = {
    "schema_version": "companion_graph_namespace.v1",
    "institutions": [{"slug": "inteli", "name": "Inteli"}],
    "graph_ids": ["graph-inteli-existing"],
}


def _completed(document, returncode=0):
    def run(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], returncode, json.dumps(document), "")
    return run


@pytest.fixture
def companion_repo(tmp_path):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "export_graph_namespace.py").touch()
    (scripts / "validate_graph_package.py").touch()
    return tmp_path


def test_reads_the_narrow_namespace_without_mirroring_courses_or_groups(
    companion_repo,
):
    document = companion_seam.graph_namespace(
        companion_repo,
        run=_completed(NAMESPACE),
    )

    assert document == NAMESPACE
    assert "courses" not in document["institutions"][0]
    assert "groups" not in document["institutions"][0]


def test_reads_a_namespace_snapshot_without_a_companion_checkout(
    tmp_path, monkeypatch
):
    snapshot = tmp_path / "namespace.json"
    snapshot.write_text(json.dumps(NAMESPACE))
    monkeypatch.setenv("COMPANION_GRAPH_NAMESPACE_FILE", str(snapshot))

    document = companion_seam.graph_namespace(tmp_path / "missing-companion")

    assert document == NAMESPACE


@pytest.mark.parametrize(
    "document",
    [
        {},
        [],
        {"schema_version": "wrong", "institutions": [], "graph_ids": []},
        {
            "schema_version": "companion_graph_namespace.v1",
            "institutions": {},
            "graph_ids": [],
        },
    ],
)
def test_rejects_an_invalid_namespace_snapshot(tmp_path, monkeypatch, document):
    snapshot = tmp_path / "namespace.json"
    snapshot.write_text(json.dumps(document))
    monkeypatch.setenv("COMPANION_GRAPH_NAMESPACE_FILE", str(snapshot))

    with pytest.raises(companion_seam.CompanionSeamError):
        companion_seam.graph_namespace(tmp_path / "missing-companion")
