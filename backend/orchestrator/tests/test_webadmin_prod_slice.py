"""Web-admin prod: push stats, exports, events, metrics, routes (sprints 1–3)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException


def _campaign_paths() -> set[str]:
    from app.api.v1 import campaigns as camp_api

    return {getattr(r, "path", "") for r in camp_api.router.routes}


def _legal_paths() -> set[str]:
    from app.api.v1 import legal as legal_api

    return {getattr(r, "path", "") for r in legal_api.router.routes}


def _tax_admin_paths() -> set[str]:
    from app.api.v1.tax import admin_router

    return {getattr(r, "path", "") for r in admin_router.routes}


def _marketplace_paths() -> set[str]:
    from app.api.v1 import marketplace_admin as mp_api

    return {getattr(r, "path", "") for r in mp_api.router.routes}


def test_campaign_push_routes_exist():
    paths = _campaign_paths()
    assert "/push" in paths
    assert "/push/stats" in paths
    assert "/push/test" in paths


def test_legal_version_history_route():
    assert "/legal/admin/{slug}/versions" in _legal_paths()


def test_admin_tax_pdf_routes():
    paths = _tax_admin_paths()
    assert "/admin/tax/invoice/{order_id}" in paths
    assert "/admin/tax/act/{order_id}" in paths


def test_marketplace_admin_upload_route():
    assert "/admin/marketplace/upload" in _marketplace_paths()


def test_admin_company_export_routes():
    from app.api.v1.admin import (
        admin_get_company_data_export,
        admin_list_company_data_exports,
        admin_request_company_data_export,
    )

    assert admin_request_company_data_export.__name__ == "admin_request_company_data_export"
    assert admin_list_company_data_exports.__name__ == "admin_list_company_data_exports"
    assert admin_get_company_data_export.__name__ == "admin_get_company_data_export"


def test_admin_sprint1_routes():
    from app.api.v1.admin import (
        admin_user_events,
        admin_user_events_taxonomy,
        dod_metrics,
        dod_metrics_export,
        ha_cutover_preflight,
        ha_mesh_status,
        ha_minio_vip_status,
        queue_stats,
    )

    for fn in (
        queue_stats,
        admin_user_events,
        admin_user_events_taxonomy,
        dod_metrics,
        dod_metrics_export,
        ha_cutover_preflight,
        ha_mesh_status,
        ha_minio_vip_status,
    ):
        assert callable(fn)


def test_forbidden_category_in_taxonomy():
    from app.services.user_events import USER_EVENT_TYPES

    assert "forbidden_category_attempt" in USER_EVENT_TYPES


@pytest.mark.asyncio
async def test_record_forbidden_category_event(db):
    from app.models import User
    from app.services.user_events import list_events, record_event

    user = User(email="forbidden@example.com", password_hash="x", status="active")
    db.add(user)
    await db.flush()
    await record_event(
        db,
        event_type="forbidden_category_attempt",
        user_id=user.id,
        payload={"categories": ["weapons"], "category": "electronics"},
    )
    await db.commit()

    data = await list_events(db, event_type="forbidden_category_attempt", user_id=user.id)
    assert data["total"] >= 1
    assert data["items"][0]["event_type"] == "forbidden_category_attempt"
    assert data["items"][0]["payload"]["categories"] == ["weapons"]


@pytest.mark.asyncio
async def test_unknown_user_event_raises(db):
    from app.services.user_events import record_event

    with pytest.raises(ValueError, match="unknown user event"):
        await record_event(db, event_type="not_a_real_event")


@pytest.mark.asyncio
async def test_push_open_stats_empty(db):
    from app.services.campaigns import push_open_stats

    out = await push_open_stats(db, days=30)
    assert out["total_delivered"] == 0
    assert out["total_opened"] == 0
    assert out["open_rate"] == 0.0
    assert isinstance(out["items"], list)


@pytest.mark.asyncio
async def test_push_open_stats_with_inbox(db):
    from app.models import PushBroadcast, User, UserNotification
    from app.services.campaigns import push_open_stats

    user = User(email="push-open@example.com", password_hash="x", status="active")
    db.add(user)
    await db.flush()
    broadcast = PushBroadcast(
        title="Promo",
        body="Hello",
        segment={},
        status="sent",
        stats={"reach": 1, "pushed": 1},
        sent_at=datetime.now(timezone.utc),
    )
    db.add(broadcast)
    await db.flush()

    db.add(
        UserNotification(
            user_id=user.id,
            title="Promo",
            body="Hello",
            dedup_key=f"push:broadcast:{broadcast.id}:{user.id}",
            read_at=datetime.now(timezone.utc),
        )
    )
    db.add(
        UserNotification(
            user_id=user.id,
            title="Promo 2",
            body="Unread",
            dedup_key=f"push:broadcast:{broadcast.id}:{user.id}:alt",
        )
    )
    await db.commit()

    out = await push_open_stats(db, days=30)
    assert out["total_delivered"] >= 2
    assert out["total_opened"] >= 1
    assert 0 < out["open_rate"] <= 1.0
    row = next((i for i in out["items"] if i["id"] == broadcast.id), None)
    assert row is not None
    assert row["opened"] >= 1


@pytest.mark.asyncio
async def test_send_push_broadcast_scheduled_skips_delivery(db, monkeypatch):
    from app.models import User
    from app.services import campaigns as camp_svc

    user = User(email="sched@example.com", password_hash="x", status="active", staff_role="admin")
    db.add(user)
    await db.flush()

    called = False

    async def _fake_deliver(db_sess, row):
        nonlocal called
        called = True
        return row

    monkeypatch.setattr(camp_svc, "_deliver_push_broadcast", _fake_deliver)

    future = datetime.now(timezone.utc) + timedelta(hours=2)
    row = await camp_svc.send_push_broadcast(
        db,
        title="Later",
        body="Body",
        segment={},
        created_by=user.id,
        send_at=future,
    )
    await db.commit()

    assert row.status == "scheduled"
    assert row.stats.get("scheduled_at")
    assert called is False


@pytest.mark.asyncio
async def test_dispatch_scheduled_push_broadcasts(db, monkeypatch):
    from app.models import PushBroadcast
    from app.services import campaigns as camp_svc

    past = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    row = PushBroadcast(
        title="Due",
        body="Now",
        segment={},
        status="scheduled",
        stats={"scheduled_at": past},
    )
    db.add(row)
    await db.commit()

    delivered: list[int] = []

    async def _fake_deliver(db_sess, broadcast_row):
        delivered.append(broadcast_row.id)
        broadcast_row.status = "sent"
        return broadcast_row

    monkeypatch.setattr(camp_svc, "_deliver_push_broadcast", _fake_deliver)
    out = await camp_svc.dispatch_scheduled_push_broadcasts(db)
    assert out["processed"] == 1
    assert delivered == [row.id]


@pytest.mark.asyncio
async def test_deliver_push_broadcast_sets_dedup_keys(db, monkeypatch):
    from app.models import User
    from app.services import campaigns as camp_svc

    user = User(
        email="dedup@example.com",
        password_hash="x",
        status="active",
        marketing_opt_in=True,
    )
    db.add(user)
    await db.flush()

    captured: list[dict] = []

    async def _fake_send(db_sess, uid, title, body, *, data=None, email_fallback=True):
        captured.append({"user_id": uid, "data": data or {}})
        return {
            "user_id": uid,
            "delivered_push": True,
            "email_fallback": False,
            "fcm_configured": False,
            "devices": 0,
        }

    monkeypatch.setattr("app.services.push.send_to_user", _fake_send)

    from app.models import PushBroadcast as PB

    broadcast = PB(title="T", body="B", segment={}, status="sending", stats={})
    db.add(broadcast)
    await db.flush()

    result = await camp_svc._deliver_push_broadcast(db, broadcast)
    assert result.status == "sent"
    assert len(captured) == 1
    assert captured[0]["data"]["dedup_key"] == f"push:broadcast:{broadcast.id}:{user.id}"


@pytest.mark.asyncio
async def test_company_data_export_list(db):
    from app.models import Company, CompanyDataExport, User
    from app.services import company_data_export as cde_svc

    company = Company(name="Export Co", inn="7700000000", status="active")
    user = User(email="owner@export.co", password_hash="x", status="active")
    db.add_all([company, user])
    await db.flush()

    row = CompanyDataExport(
        company_id=company.id,
        requested_by_user_id=user.id,
        status="completed",
        notify_email=user.email,
    )
    db.add(row)
    await db.commit()

    items = await cde_svc.list_exports(db, company_id=company.id)
    assert len(items) >= 1
    assert items[0]["status"] == "completed"
    assert items[0]["company_id"] == company.id


@pytest.mark.asyncio
async def test_company_data_export_pending_dedup(db):
    from app.models import Company, User
    from app.services import company_data_export as cde_svc

    company = Company(name="Pending Co", inn="7700000001", status="active")
    user = User(email="pending@export.co", password_hash="x", status="active")
    db.add_all([company, user])
    await db.flush()

    first = await cde_svc.request_export(db, company=company, user=user)
    second = await cde_svc.request_export(db, company=company, user=user)
    assert first.id == second.id


@pytest.mark.asyncio
async def test_pg_dashboard_qs_pass_rate(db, monkeypatch):
    from app.models import ServiceLogEvent
    from app.services.metrics import _pg_dashboard

    now = datetime.now(timezone.utc)
    db.add(
        ServiceLogEvent(
            source="worker",
            level="INFO",
            message="task_completed",
            details={"quality_score": 0.85},
            created_at=now,
        )
    )
    db.add(
        ServiceLogEvent(
            source="worker",
            level="INFO",
            message="task_completed",
            details={"quality_score": 0.5},
            created_at=now,
        )
    )
    await db.commit()

    data = await _pg_dashboard()
    assert "qs_pass_rate_7d" in data
    assert data["qs_sample_total"] >= 2
    assert 0 <= data["qs_pass_rate_7d"] <= 1.0


@pytest.mark.asyncio
async def test_list_document_versions(db):
    from app.models import LegalDocument
    from app.api.v1.legal import list_document_versions

    db.add(
        LegalDocument(
            slug="terms",
            title="Terms v1",
            body="body1",
            version=1,
            is_published=True,
        )
    )
    db.add(
        LegalDocument(
            slug="terms",
            title="Terms v2",
            body="body2",
            version=2,
            is_published=True,
        )
    )
    await db.commit()

    out = await list_document_versions("terms", _={"sub": 1}, db=db)
    assert len(out["items"]) == 2
    assert out["items"][0]["version"] == 2


@pytest.mark.asyncio
async def test_admin_generate_invoice_requires_staff(db, monkeypatch):
    from app.api.v1.tax import admin_generate_invoice
    from app.models import Order, User

    user = User(email="nostaff@example.com", password_hash="x", status="active")
    db.add(user)
    await db.flush()
    order = Order(
        user_id=user.id,
        task_uuid="tax-order-1",
        category="electronics",
        tier="small",
        status="completed",
        amount=100,
    )
    db.add(order)
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await admin_generate_invoice(order.id, staff=user, db=db)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_push_broadcast_stats_route_delegates(db, monkeypatch):
    from app.api.v1.campaigns import push_broadcast_stats

    async def _fake_stats(db_sess, *, days=30):
        return {"days": days, "open_rate": 0.5, "items": []}

    monkeypatch.setattr("app.api.v1.campaigns.camp_svc.push_open_stats", _fake_stats)
    out = await push_broadcast_stats(days=14, db=db)
    assert out["days"] == 14
    assert out["open_rate"] == 0.5


@pytest.mark.asyncio
async def test_list_push_broadcasts_returns_items(db):
    from app.api.v1.campaigns import list_push_broadcasts
    from app.models import PushBroadcast

    db.add(PushBroadcast(title="A", body="a", segment={}, status="sent", stats={"reach": 3}))
    await db.commit()

    out = await list_push_broadcasts(db=db)
    assert len(out["items"]) >= 1
    assert out["items"][0]["title"] == "A"


def test_export_to_dict_minimal():
    from app.models import CompanyDataExport
    from app.services.company_data_export import export_to_dict

    row = CompanyDataExport(
        id=10,
        company_id=5,
        status="processing",
        requested_by_user_id=1,
        notify_email="a@b.c",
    )
    d = export_to_dict(row)
    assert d["id"] == 10
    assert d["company_id"] == 5
    assert d["status"] == "processing"
    assert d["download_url"] is None


def test_push_create_schema_send_at():
    from datetime import datetime, timezone

    from app.api.v1.campaigns import PushCreate

    when = datetime.now(timezone.utc)
    body = PushCreate(title="Hi", body="Text", segment={"has_orders": True}, send_at=when)
    assert body.send_at == when
    assert body.segment["has_orders"] is True


def test_user_events_taxonomy_count():
    from app.services.user_events import USER_EVENT_TYPES

    assert len(USER_EVENT_TYPES) >= 30
    assert "order_created" in USER_EVENT_TYPES
    assert "forbidden_category_attempt" in USER_EVENT_TYPES


def test_metrics_dashboard_quality_keys():
    import inspect

    from app.services import metrics

    src = inspect.getsource(metrics.dashboard_aggregates)
    assert "qs_pass_rate_7d" in src


def test_celery_scheduled_push_task_registered():
    from app.tasks.celery_app import celery_app

    assert "app.tasks.celery_app.run_scheduled_push_broadcasts" in celery_app.tasks
