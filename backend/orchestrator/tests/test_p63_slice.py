"""§9.8 company deletion grace, §9.9 backup verify, §10.3 download rate."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from app.services.company_deletion import GRACE_DAYS, cancel_deletion, request_deletion


@pytest.mark.asyncio
async def test_company_deletion_request_and_cancel(db):
    from app.models import Company, User

    user = User(email="del@test.local", password_hash="x", status="active_legal", email_verified=True)
    db.add(user)
    await db.flush()
    company = Company(name="Del Co", inn="7701234567", owner_id=user.id, status="active", balance=0)
    db.add(company)
    await db.flush()

    out = await request_deletion(db, company, user_id=user.id)
    assert out["pending_deletion"] is True
    assert company.status == "pending_deletion"

    cancelled = await cancel_deletion(db, company, user_id=user.id)
    assert cancelled["cancelled"] is True
    assert company.status == "active"


def test_grace_days_constant():
    assert GRACE_DAYS == 30


@pytest.mark.asyncio
async def test_download_rate_limit_blocks(db, monkeypatch):
    from app.models import AccessLog
    from app.services.download_guard import assert_model_download_rate

    for i in range(5):
        db.add(
            AccessLog(
                user_id=1,
                model_uuid="rate-model",
                action="download",
                created_at=datetime.now(timezone.utc),
            )
        )
    await db.flush()

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        await assert_model_download_rate(db, user_id=1, model_uuid="rate-model")
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_backup_status_counts(db, monkeypatch):
    from app.models import Company, Model3D, Order, User
    from app.services.backup_insurance import company_backup_status

    user = User(email="bk@test.local", password_hash="x", status="active_legal", email_verified=True)
    db.add(user)
    await db.flush()
    company = Company(name="Bk", inn="7701234568", owner_id=user.id)
    db.add(company)
    await db.flush()
    order = Order(
        user_id=user.id,
        company_id=company.id,
        task_uuid="bk-task-uuid",
        category="other",
        tier="small",
        status="completed",
        amount=100,
    )
    db.add(order)
    await db.flush()
    model = Model3D(uuid="bk-model", order_id=order.id, user_id=user.id, company_id=company.id)
    db.add(model)
    await db.flush()

    with patch("app.services.backup_insurance.minio_service") as m:
        m.object_exists = lambda _b, k: "company_" in k
        out = await company_backup_status(db, company.id)
    assert out["backups_found"] == 1
    assert out["coverage_ratio"] == 1.0
