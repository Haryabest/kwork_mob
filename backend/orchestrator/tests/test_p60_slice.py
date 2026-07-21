"""§7.6 download meta, §7.7 verify max 5."""

from __future__ import annotations

import pytest

from app.services import marketplace_download as mp_dl
from app.services import publication as pub_svc


def test_download_meta_wb_glb():
    meta = mp_dl.download_meta("wildberries", "glb")
    assert meta["marketplace"] == "wb"
    assert "Wildberries" in meta["button_label"]
    assert meta["limit_bytes"] == mp_dl.WB_BYTES


def test_download_meta_ozon_usdz():
    meta = mp_dl.download_meta("ozon", "usdz")
    assert meta["marketplace"] == "ozon"
    assert meta["limit_bytes"] == mp_dl.OZON_BYTES


@pytest.mark.asyncio
async def test_verify_link_blocks_after_max_attempts(db):
    from app.models import Model3D, ModelPublicationLink, Order, User

    user = User(email="pub-max@test.local", password_hash="x", status="active_individual", email_verified=True)
    db.add(user)
    await db.flush()
    order = Order(
        user_id=user.id,
        task_uuid="pub-max-task",
        category="other",
        tier="small",
        status="completed",
        amount=100,
    )
    db.add(order)
    await db.flush()
    model = Model3D(uuid="pub-max-model", order_id=order.id, user_id=user.id, glb_url="s3://b/k")
    link = ModelPublicationLink(
        model_uuid=model.uuid,
        marketplace="ozon",
        url="https://www.ozon.ru/product/1",
        status="failed",
        check_attempts=pub_svc.MAX_VERIFY_ATTEMPTS,
        created_by_user_id=user.id,
    )
    db.add(model)
    db.add(link)
    await db.flush()
    out = await pub_svc.verify_link(db, link)
    assert out.status == "failed"
    assert out.check_attempts == pub_svc.MAX_VERIFY_ATTEMPTS
    assert "лимит" in (out.error_message or "").lower()
