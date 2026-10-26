import io

import pytest

from checker.artifacts import LocalStore, S3Store, make_store, run_key


class FakeS3:
    """Stands in for boto3's S3 client so no AWS account is needed."""

    def __init__(self):
        self.objects = {}
        self.put_calls = []

    def put_object(self, **kwargs):
        self.objects[kwargs["Key"]] = kwargs["Body"]
        self.put_calls.append(kwargs)

    def get_object(self, Bucket, Key):
        return {"Body": io.BytesIO(self.objects[Key])}

    def delete_object(self, Bucket, Key):
        self.objects.pop(Key, None)


def test_run_key_layout():
    assert run_key(7, "report.md") == "runs/7/report.md"


def test_local_store_round_trip(tmp_path):
    store = LocalStore(tmp_path)
    key = store.put("runs/1/report.md", b"hello", "text/markdown")
    assert key == "runs/1/report.md"
    assert store.get(key) == b"hello"


def test_local_store_overwrites_same_key(tmp_path):
    store = LocalStore(tmp_path)
    store.put("a/b.txt", b"one")
    store.put("a/b.txt", b"two")
    assert store.get("a/b.txt") == b"two"


def test_local_store_delete_is_safe_when_missing(tmp_path):
    store = LocalStore(tmp_path)
    store.put("a.txt", b"x")
    store.delete("a.txt")
    store.delete("a.txt")  # deleting twice must not raise
    with pytest.raises(FileNotFoundError):
        store.get("a.txt")


def test_local_store_rejects_keys_that_escape_the_folder(tmp_path):
    store = LocalStore(tmp_path / "artifacts")
    with pytest.raises(ValueError):
        store.put("../evil.txt", b"x")
    with pytest.raises(ValueError):
        store.get("../../secret.txt")


def test_s3_store_puts_encrypted_object_in_the_right_bucket():
    fake = FakeS3()
    store = S3Store("my-bucket", client=fake)
    store.put("runs/1/report.md", b"hello", "text/markdown")
    call = fake.put_calls[0]
    assert call["Bucket"] == "my-bucket"
    assert call["Key"] == "runs/1/report.md"
    assert call["ContentType"] == "text/markdown"
    assert call["ServerSideEncryption"] == "AES256"


def test_s3_store_get_and_delete():
    fake = FakeS3()
    store = S3Store("my-bucket", client=fake)
    store.put("k", b"data")
    assert store.get("k") == b"data"
    store.delete("k")
    assert "k" not in fake.objects


def test_make_store_defaults_to_a_local_folder(tmp_path, monkeypatch):
    monkeypatch.delenv("S3_BUCKET", raising=False)
    monkeypatch.setenv("ARTIFACT_DIR", str(tmp_path))
    store = make_store()
    assert isinstance(store, LocalStore)
    store.put("x.txt", b"1")
    assert (tmp_path / "x.txt").read_bytes() == b"1"