"""User avatar §20.8.1."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.services import user_avatar as av


def test_allowed_ext_validation():
    assert ".jpg" in av.ALLOWED_EXT
    assert av.MAX_BYTES == 2 * 1024 * 1024


@pytest.mark.asyncio
async def test_upload_avatar_rejects_bad_type():
    user = SimpleNamespace(id=1, avatar_key=None)
    file = MagicMock()
    file.filename = "doc.pdf"
    file.content_type = "application/pdf"
    file.read = AsyncMock(return_value=b"x" * 10)
    db = AsyncMock()
    with pytest.raises(HTTPException) as exc:
        await av.upload_avatar(db, user=user, file=file)
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_upload_avatar_ok():
    user = SimpleNamespace(id=7, avatar_key=None)
    file = MagicMock()
    file.filename = "me.png"
    file.content_type = "image/png"
    file.read = AsyncMock(return_value=b"png-bytes")
    db = AsyncMock()
    db.flush = AsyncMock()
    with patch.object(av.minio_service, "ensure_buckets"), patch.object(av.minio_service, "upload_bytes"), patch.object(
        av, "presigned_avatar_url", return_value="https://example/avatar"
    ):
        result = await av.upload_avatar(db, user=user, file=file)
    assert result["avatar_key"].startswith("avatars/7/")
    assert user.avatar_key is not None


@pytest.mark.asyncio
async def test_delete_avatar_clears_key():
    user = SimpleNamespace(id=1, avatar_key="avatars/1/x.jpg")
    db = AsyncMock()
    db.flush = AsyncMock()
    result = await av.delete_avatar(db, user=user)
    assert result["ok"] is True
    assert user.avatar_key is None
