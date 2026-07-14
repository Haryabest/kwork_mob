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
    mock_resp.json = lambda: {"media_id": "abc123"}
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


def test_get_credential_prefers_company():
    from types import SimpleNamespace

    from app.services.marketplace_upload import get_credential

    company_row = SimpleNamespace(
        company_id=7,
        marketplace="wb",
        enabled=True,
        api_key_encrypted="enc",
    )
    global_row = SimpleNamespace(
        company_id=None,
        marketplace="wb",
        enabled=True,
        api_key_encrypted="enc2",
    )

    class FakeResult:
        def __init__(self, row):
            self._row = row

        def scalar_one_or_none(self):
            return self._row

    class FakeDb:
        def __init__(self, rows):
            self._rows = list(rows)
            self._i = 0

        async def scalar(self, _stmt):
            row = self._rows[self._i]
            self._i += 1
            return row

    async def run():
        db = FakeDb([company_row, global_row])
        cred = await get_credential(db, marketplace="wb", company_id=7)  # type: ignore[arg-type]
        assert cred is company_row

    import asyncio

    asyncio.run(run())
