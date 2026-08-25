import json
from pathlib import Path
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


def test_reads_the_narrow_namespace_without_mirroring_courses_or_groups():
    document = companion_seam.graph_namespace(
        Path(__file__).resolve().parents[2] / "companion",
        run=_completed(NAMESPACE),
    )

    assert document == NAMESPACE
    assert "courses" not in document["institutions"][0]
    assert "groups" not in document["institutions"][0]


def test_preserves_a_companion_rejection_document():
    rejected = {
        "schema_version": "companion_graph_package_acceptance.v1",
        "accepted": False,
        "graph_id": "graph-inteli-existing",
        "package_sha256": None,
        "issues": [{"code": "graph_id_conflict"}],
    }
    result = companion_seam.validate_package(
        Path("candidate"),
        Path(__file__).resolve().parents[2] / "companion",
        run=_completed(rejected, returncode=2),
    )

    assert result == rejected


def test_export_gate_cannot_return_a_rejected_package():
    rejected = {
        "schema_version": "companion_graph_package_acceptance.v1",
        "accepted": False,
        "graph_id": "graph-inteli-existing",
        "package_sha256": None,
        "issues": [{"code": "graph_id_conflict"}],
    }

    with pytest.raises(
        companion_seam.CompanionRejectedPackage,
        match="graph_id_conflict",
    ):
        companion_seam.require_export_acceptance(
            Path("candidate"),
            Path(__file__).resolve().parents[2] / "companion",
            run=_completed(rejected, returncode=2),
        )


def test_export_gate_rejects_an_unbound_acceptance_receipt():
    accepted_without_hash = {
        "schema_version": "companion_graph_package_acceptance.v1",
        "accepted": True,
        "graph_id": "graph-inteli-new",
        "package_sha256": None,
        "issues": [],
    }

    with pytest.raises(
        companion_seam.CompanionSeamError,
        match="package hash",
    ):
        companion_seam.require_export_acceptance(
            Path("candidate"),
            Path(__file__).resolve().parents[2] / "companion",
            run=_completed(accepted_without_hash),
        )
