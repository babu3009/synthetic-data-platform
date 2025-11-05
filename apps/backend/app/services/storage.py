from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.core.config import settings

try:
    from minio import Minio
except Exception:  # pragma: no cover
    Minio = None  # type: ignore


@dataclass
class StoredObject:
    uri: str
    size: int
    signed_url: Optional[str] = None


class Storage:
    def put_file(self, local_path: Path, object_name: str) -> StoredObject:
        raise NotImplementedError
    def get_signed_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        raise NotImplementedError
    def delete_object(self, object_name: str) -> None:
        raise NotImplementedError


class MinioStorage(Storage):
    def __init__(self):
        if Minio is None:
            raise RuntimeError("minio client not available")
        endpoint = settings.MINIO_ENDPOINT
        access_key = settings.MINIO_ACCESS_KEY
        secret_key = settings.MINIO_SECRET_KEY
        secure = endpoint.startswith("https://")
        endpoint = endpoint.replace("https://", "").replace("http://", "")
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.bucket = settings.MINIO_BUCKET
        # Ensure bucket exists
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def put_file(self, local_path: Path, object_name: str) -> StoredObject:
        self.client.fput_object(self.bucket, object_name, str(local_path))
        uri = f"s3://{self.bucket}/{object_name}"
        # default signed URL
        signed = self.get_signed_url(object_name)
        size = local_path.stat().st_size
        return StoredObject(uri=uri, size=size, signed_url=signed)

    def get_signed_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        from datetime import timedelta
        return self.client.presigned_get_object(
            self.bucket, object_name, expires=timedelta(seconds=expires_seconds)
        )

    def delete_object(self, object_name: str) -> None:
        self.client.remove_object(self.bucket, object_name)


class LocalStorage(Storage):
    def __init__(self, base: Path):
        self.base = base
        self.base.mkdir(parents=True, exist_ok=True)

    def put_file(self, local_path: Path, object_name: str) -> StoredObject:
        dest = self.base / object_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(local_path.read_bytes())
        uri = dest.resolve().as_uri()
        return StoredObject(uri=uri, size=dest.stat().st_size, signed_url=uri)

    def get_signed_url(self, object_name: str, expires_seconds: int = 3600) -> str:
        dest = self.base / object_name
        return dest.resolve().as_uri()

    def delete_object(self, object_name: str) -> None:
        dest = self.base / object_name
        if dest.exists():
            dest.unlink()


def get_storage() -> Storage:
    # Prefer Minio; fall back to local storage under storage/requests
    try:
        if Minio is not None:
            return MinioStorage()
    except Exception:
        pass
    return LocalStorage(Path("storage/requests"))
