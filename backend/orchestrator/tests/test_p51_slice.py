"""§3.1 ZIP upload, §3.5 cancel processing, §3.7 share rate-limit."""

from __future__ import annotations

import inspect
import io
import zipfile
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.api.v1 import models as models_api
from app.api.v1 import orders as orders_api
from app.services import photos_zip_upload as zip_up
from app.services import share_rate_limit as share_rl
from app.services import task_lifecycle as tl


def test_zip_upload_routes_exist():
    assert "zip_upload_init" in dir(orders_api)
    assert "zip_upload_status" in dir(orders_api)
    assert "zip_upload_chunk" in dir(orders_api)
    assert "zip_upload_complete" in dir(orders_api)


def test_cancel_order_body_ack_no_refund():
    body = orders_api.CancelOrderBody(ack_no_refund=True)
    assert body.ack_no_refund is True


def test_public_share_has_request_param():
    sig = inspect.signature(models_api.public_share)
    assert "request" in sig.parameters


@pytest.mark.asyncio
async def test_share_rate_limit_blocks(monkeypatch):
  calls = {"n": 0}

  class FakeRedis:
    async def incr(self, _key):
      calls["n"] += 1
      return calls["n"]

    async def expire(self, _key, _ttl):
      return True

  async def fake_get_redis():
    return FakeRedis()

  monkeypatch.setattr(share_rl, "DEFAULT_LIMIT", 2)
  monkeypatch.setattr("app.core.redis.get_redis", fake_get_redis)

  req = MagicMock()
  req.client = MagicMock(host="1.2.3.4")
  req.headers = {}

  await share_rl.assert_share_allowed(req, "abc123")
  await share_rl.assert_share_allowed(req, "abc123")
  with pytest.raises(HTTPException) as exc:
    await share_rl.assert_share_allowed(req, "abc123")
  assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_init_upload_validates_sha256():
  with pytest.raises(HTTPException) as exc:
    await zip_up.init_upload(
      task_uuid="t1",
      user_id=1,
      total_size=1024,
      sha256="bad",
    )
  assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_complete_upload_requires_all_parts(monkeypatch):
  meta = {
    "upload_id": "u1",
    "task_uuid": "t1",
    "user_id": 1,
    "total_size": 10,
    "sha256": "a" * 64,
    "chunk_size": 10,
    "parts": [],
    "completed": False,
  }

  async def fake_load(_upload_id, _user_id):
    return meta

  monkeypatch.setattr(zip_up, "_load_meta", fake_load)
  with pytest.raises(HTTPException) as exc:
    await zip_up.complete_upload("u1", 1)
  assert exc.value.status_code == 400


def _make_zip() -> bytes:
  buf = io.BytesIO()
  with zipfile.ZipFile(buf, "w") as zf:
    for i in range(12):
      zf.writestr(f"view_{i:02d}.jpg", b"jpeg")
  return buf.getvalue()


@pytest.mark.asyncio
async def test_complete_upload_happy_path(monkeypatch):
  data = _make_zip()
  from app.services.integrity import sha256_bytes

  digest = sha256_bytes(data)
  meta = {
    "upload_id": "u1",
    "task_uuid": "task-uuid",
    "user_id": 1,
    "total_size": len(data),
    "sha256": digest,
    "chunk_size": len(data),
    "parts": [0],
    "completed": False,
  }

  async def fake_load(_upload_id, _user_id):
    return meta

  monkeypatch.setattr(zip_up, "_load_meta", fake_load)
  monkeypatch.setattr(
    zip_up.minio_service,
    "download_bytes",
    lambda _b, _k: data,
  )
  monkeypatch.setattr(zip_up.minio_service, "upload_bytes", lambda *a, **k: None)
  monkeypatch.setattr(zip_up.minio_service, "delete_prefix", lambda *a, **k: None)
  monkeypatch.setattr(zip_up.photos_service, "require_all_photos", lambda _t: None)

  class FakeRedis:
    async def set(self, *_a, **_k):
      return True

  monkeypatch.setattr(zip_up, "_redis", AsyncMock(return_value=FakeRedis()))

  out = await zip_up.complete_upload("u1", 1)
  assert out["ok"] is True
  assert out["task_uuid"] == "task-uuid"


@pytest.mark.asyncio
async def test_cancel_processing_order_sets_cancelled(db, monkeypatch):
  from app.models import Order, TaskQueue

  order = Order(
    id=9001,
    user_id=1,
    task_uuid="cancel-task",
    status="processing",
    amount=100,
    category="other",
    tier="small",
  )
  row = TaskQueue(task_id="cancel-task", status="processing", worker_id="w1")
  db.add(order)
  db.add(row)
  await db.flush()

  conn = MagicMock()
  conn.websocket = MagicMock()
  conn.websocket.send_json = AsyncMock()

  class FakeHub:
    async def get(self, worker_id):
      assert worker_id == "w1"
      return conn

  monkeypatch.setattr("app.services.worker_hub.worker_hub", FakeHub())

  await tl.cancel_processing_order(db, order)
  assert order.status == "cancelled"
  assert row.status == "cancelled"
  conn.websocket.send_json.assert_awaited_once()
