"""Local immutable content-addressed asset storage."""

import hashlib

from universe.assets import LocalAssetStore, asset_store_from_env


def test_local_store_is_content_addressed_and_deduplicates(tmp_path):
    store = LocalAssetStore(tmp_path / "assets")
    body = b"immutable source bytes"
    digest = hashlib.sha256(body).hexdigest()

    first = store.put(body)
    second = store.put(body)

    assert first.key == f"sha256/{digest[:2]}/{digest}"
    assert first.sha256 == digest
    assert first.created is True
    assert second == first.__class__(key=first.key, sha256=digest, created=False)
    assert store.get(first.key) == body


def test_environment_always_selects_local_storage(monkeypatch, tmp_path):
    monkeypatch.setenv("CONCEPT_UNIVERSE_ASSET_ROOT", str(tmp_path / "local"))

    local = asset_store_from_env()

    assert isinstance(local, LocalAssetStore)
    assert local.root == (tmp_path / "local").resolve()
