"""Where saved files (cleaned CSVs and reports) live.

Two interchangeable stores with the same three methods:
  LocalStore  a folder on disk, used for development
  S3Store     an S3 bucket, used in the cloud
"""
from pathlib import Path

from checker import config


class LocalStore:
    def __init__(self, root):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        root = self.root.resolve()
        path = (root / key).resolve()
        if root not in path.parents:  # blocks keys like ../../something
            raise ValueError(f"Invalid artifact key: {key!r}")
        return path

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Store:
    def __init__(self, bucket: str, client=None):
        if client is None:
            import boto3  # imported here so local use never needs AWS

            client = boto3.client("s3")
        self.bucket = bucket
        self.client = client

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data,
            ContentType=content_type, ServerSideEncryption="AES256",
        )
        return key

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def make_store():
    """S3 if S3_BUCKET is set, otherwise a local folder."""
    bucket = config.s3_bucket()
    if bucket:
        return S3Store(bucket)
    return LocalStore(config.artifact_dir())


def run_key(run_id: int, name: str) -> str:
    return f"runs/{run_id}/{name}"