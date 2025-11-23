from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class StoredObject:
    uri: str
    size: int
    signed_url: Optional[str] = None


class Storage:
    def put_file(self, local_path: Path, object_name: str) -> StoredObject:
        raise NotImplementedError
    def get_signed_url(self, object_name: str, expires_seconds: int = 3600, download_filename: Optional[str] = None) -> str:
        raise NotImplementedError
    def delete_object(self, object_name: str) -> None:
        raise NotImplementedError


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

    def get_signed_url(self, object_name: str, expires_seconds: int = 3600, download_filename: Optional[str] = None) -> str:
        dest = self.base / object_name
        # Note: Local file URIs don't support custom filenames natively
        # Browser will use the actual filename from the URI
        return dest.resolve().as_uri()

    def delete_object(self, object_name: str) -> None:
        dest = self.base / object_name
        if dest.exists():
            dest.unlink()


def get_storage() -> Storage:
    # Use local storage under storage/requests
    return LocalStorage(Path("storage/requests"))
