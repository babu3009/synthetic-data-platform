from __future__ import annotations

import base64
import os
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.crud.users import create_user, set_status
from app.db.models import UserRole, UserStatus, User
from sqlalchemy import update
from app.security.passwords import hash_password
from app.security.jwt import create_access_token

PNG_SIG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 10  # minimal header + padding

@pytest.mark.asyncio
async def test_users_me_profile(async_client: AsyncClient, db_session: AsyncSession):
    # Create approved user
    user = await create_user(
        db_session,
        email="me@example.com",
        password_hash=hash_password("StrongPass#123"),
        organization="Org",
    )
    # set status and role explicitly
    await set_status(db_session, user.id, UserStatus.APPROVED)
    await db_session.execute(update(User).where(User.id == user.id).values(role=UserRole.USER))
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(str(user.id), user.role.value, expires_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}

    r = await async_client.get("/api/v1/users/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == str(user.id)
    assert data["email"] == "me@example.com"
    assert data["role"] == "USER"
    assert data["status"] == "APPROVED"


@pytest.mark.asyncio
async def test_avatar_upload_success(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    user = await create_user(
        db_session,
        email="avatar@example.com",
        password_hash=hash_password("AvatarPass#123"),
        organization="Org",
    )
    await set_status(db_session, user.id, UserStatus.APPROVED)
    await db_session.execute(update(User).where(User.id == user.id).values(role=UserRole.USER))
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(str(user.id), user.role.value, expires_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}

    file_content = PNG_SIG + b"moredata"  # small valid PNG-like content
    # FastAPI test client expects tuple (filename, bytes, content_type)
    files = {"file": ("avatar.png", file_content, "image/png")}
    r = await async_client.patch("/api/v1/users/me/avatar", headers=headers, files=files)
    assert r.status_code == 200
    data = r.json()
    assert "profile_image_url" in data
    assert data["profile_image_url"].startswith("/storage/uploads/avatars/")


@pytest.mark.asyncio
async def test_avatar_upload_too_large(async_client: AsyncClient, db_session: AsyncSession, monkeypatch):
    user = await create_user(
        db_session,
        email="toolarge@example.com",
        password_hash=hash_password("LargePass#123"),
        organization="Org",
    )
    await set_status(db_session, user.id, UserStatus.APPROVED)
    await db_session.execute(update(User).where(User.id == user.id).values(role=UserRole.USER))
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(str(user.id), user.role.value, expires_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}

    # Construct content exceeding AVATAR_MAX_MB (2MB default) -> use 2MB + 1 byte
    oversized = PNG_SIG + b"A" * (2 * 1024 * 1024 + 1)
    files = {"file": ("big.png", oversized, "image/png")}
    r = await async_client.patch("/api/v1/users/me/avatar", headers=headers, files=files)
    assert r.status_code == 400
    assert r.json()["detail"] == "File too large"


@pytest.mark.asyncio
async def test_avatar_upload_unsupported_type(async_client: AsyncClient, db_session: AsyncSession):
    user = await create_user(
        db_session,
        email="badtype@example.com",
        password_hash=hash_password("BadTypePass#123"),
        organization="Org",
    )
    await set_status(db_session, user.id, UserStatus.APPROVED)
    await db_session.execute(update(User).where(User.id == user.id).values(role=UserRole.USER))
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(str(user.id), user.role.value, expires_minutes=5)
    headers = {"Authorization": f"Bearer {token}"}

    junk = b"notanimageformatcontent" * 10
    files = {"file": ("avatar.bin", junk, "application/octet-stream")}
    r = await async_client.patch("/api/v1/users/me/avatar", headers=headers, files=files)
    assert r.status_code == 400
    assert r.json()["detail"] == "Unsupported image type"
