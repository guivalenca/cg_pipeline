"""External immutable asset storage; S3 is always exercised with a fake client."""

import hashlib

from universe.assets import LocalAssetStore, S3AssetStore, asset_store_from_env


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


class FakeS3Error(Exception):
    def __init__(self, code):
        self.response = {"Error": {"Code": code}}


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.put_calls = []

    def put_object(self, **kwargs):
        self.put_calls.append(kwargs)
        coordinate = (kwargs["Bucket"], kwargs["Key"])
        if kwargs.get("IfNoneMatch") == "*" and coordinate in self.objects:
            raise FakeS3Error("PreconditionFailed")
        self.objects[coordinate] = bytes(kwargs["Body"])

    def get_object(self, **kwargs):
        body = self.objects[(kwargs["Bucket"], kwargs["Key"])]

        class Stream:
            def read(self):
                return body

        return {"Body": Stream()}

    def delete_object(self, **kwargs):
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)


def test_s3_store_uses_the_same_key_and_conditional_deduplication():
    client = FakeS3()
    store = S3AssetStore(bucket="course-assets", client=client)
    body = b"same bytes on S3"

    first = store.put(body)
    second = store.put(body)

    assert first.created is True
    assert second.created is False
    assert first.key == second.key
    assert all(call["IfNoneMatch"] == "*" for call in client.put_calls)
    assert client.put_calls[0]["Metadata"] == {"sha256": first.sha256}
    assert store.get(first.key) == body


def test_environment_selects_local_or_s3_storage(monkeypatch, tmp_path):
    monkeypatch.delenv("AWS_S3_BUCKET_NAME", raising=False)
    monkeypatch.setenv("CONCEPT_UNIVERSE_ASSET_ROOT", str(tmp_path / "local"))

    local = asset_store_from_env()

    assert isinstance(local, LocalAssetStore)
    assert local.root == (tmp_path / "local").resolve()

    client = FakeS3()
    monkeypatch.setenv("AWS_S3_BUCKET_NAME", "railway-bucket")
    monkeypatch.setenv("AWS_ENDPOINT_URL", "https://storage.example")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-access")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-secret")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "auto")
    monkeypatch.setenv("AWS_S3_URL_STYLE", "path")

    remote = asset_store_from_env(s3_client=client)

    assert isinstance(remote, S3AssetStore)
    assert remote.bucket == "railway-bucket"
    assert remote.endpoint_url == "https://storage.example"
    assert remote.url_style == "path"
