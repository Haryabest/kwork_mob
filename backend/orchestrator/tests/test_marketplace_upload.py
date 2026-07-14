"""Unit-тесты marketplace upload retry (§14.6.4)."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import settings
from app.services.marketplace_upload import UploadResult, WildberriesUploader


@pytest.mark.asyncio
async def test_wb_uploader_success():
    uploader = WildberriesUploader("test-api-key")
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"media_id": "abc123"}
    mock_resp.text = ""
    mock_resp.reason_phrase = "OK"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.marketplace_upload.httpx.AsyncClient", return_value=mock_client):
        result = await uploader.upload(sku="SKU-1", glb=b"glb-bytes", usdz=None)

    assert result.success is True
    assert result.external_ref == "abc123"
    assert result.http_status == 200


@pytest.mark.asyncio
async def test_wb_uploader_http_error():
    uploader = WildberriesUploader("test-api-key")
    mock_resp = AsyncMock()
    mock_resp.status_code = 502
    mock_resp.text = "bad gateway"
    mock_resp.reason_phrase = "Bad Gateway"

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("app.services.marketplace_upload.httpx.AsyncClient", return_value=mock_client):
        result = await uploader.upload(sku="SKU-1", glb=b"glb", usdz=b"usdz")

    assert result.success is False
    assert result.http_status == 502
    assert "bad gateway" in (result.error or "")


def test_max_retries_config():
    assert settings.MARKETPLACE_UPLOAD_MAX_RETRIES == 3
