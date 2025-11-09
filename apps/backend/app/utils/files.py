from pathlib import Path
from typing import Tuple

ALLOWED_EXT = {"jpg", "jpeg", "png", "webp"}
MAGIC = {
    b"\xFF\xD8\xFF": "jpg",
    b"\x89PNG\r\n\x1a\n": "png",
    b"RIFF": "webp",
}


def sniff_extension(content: bytes) -> str:
    for sig, ext in MAGIC.items():
        if content.startswith(sig):
            return ext
    raise ValueError("Unsupported image type")


def save_avatar(base_dir: Path, user_id: str, content: bytes) -> Tuple[str, Path]:
    ext = sniff_extension(content)
    if ext not in ALLOWED_EXT:
        raise ValueError("Unsupported image type")
    user_dir = base_dir / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    rel = f"uploads/avatars/{user_id}/avatar.{ext}"
    out_path = base_dir / user_id / f"avatar.{ext}"
    with open(out_path, "wb") as f:
        f.write(content)
    return rel.replace("\\", "/"), out_path
