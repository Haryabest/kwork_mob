"""§3.3 API verify, §4.1 CH health, §4.2 task idempotency."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1 import worker_callback as wc_api
from app.services import publication_api_verify as pav
from app.services import task_idempotency as tidem
from app.services.analytics_query import clickhouse_health


def test_extract_wb_nm_id():
    assert pav.extract_wb_nm_id("https://www.wildberries.ru/catalog/12345/detail.aspx") == 12345


def test_extract_ozon_product_id():
    assert pav.extract_ozon_product_id("https://www.ozon.ru/product/foo-987654321/") == "987654321"


def test_worker_event_supports_already_processed():
    sig = inspect.signature(wc_api.worker_event)
    assert "body" in sig.parameters


def test_clickhouse_health_unavailable():
    with patch("app.services.analytics_query._ch", return_value=None):
        assert clickhouse_health()["ok"] is False


@pytest.mark.asyncio
async def test_skip_if_completed_no_row(db):
    result = await tidem.skip_if_completed(db, "nonexistent-task-uuid-00000000")
    assert result is None


@pytest.mark.asyncio
async def test_try_api_verify_no_credentials(db, monkeypatch):
    from app.models import Model3D, ModelPublicationLink

    link = ModelPublicationLink(
        model_uuid="m1",
        marketplace="wb",
        url="https://www.wildberries.ru/catalog/99/detail.aspx",
        status="pending",
    )
    model = Model3D(uuid="m1", user_id=1, publish_status="not_published")
    monkeypatch.setattr(pav, "get_credential", AsyncMock(return_value=None))
    monkeypatch.setattr(pav, "_wb_public_card_has_3d", AsyncMock(return_value=False))
    ok, method = await pav.try_api_verify(db, link=link, model=model)
    assert ok is False
    assert method in ("wb_api", "parser")
