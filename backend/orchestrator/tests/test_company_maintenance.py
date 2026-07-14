"""Unit-тесты auto_block_inactive (§2.5.4)."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.tasks.company_maintenance import (
    effective_last_login,
    is_auto_block_exempt,
    should_block_member,
)


def _user(**kwargs):
    defaults = {
        "id": 10,
        "status": "active_individual",
        "last_login_at": None,
        "created_at": datetime(2025, 1, 1, tzinfo=timezone.utc),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _company(**kwargs):
    defaults = {"id": 1, "owner_id": 1}
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _member(**kwargs):
    defaults = {"user_id": 10, "role": "photographer"}
    defaults.update(kwargs)
    return SimpleNamespace(**kwargs)


def test_effective_last_login_prefers_last_login():
    user = _user(
        last_login_at=datetime(2026, 6, 1, tzinfo=timezone.utc),
        created_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    assert effective_last_login(user) == user.last_login_at


def test_owner_is_exempt():
    company = _company(owner_id=5)
    member = _member(user_id=5, role="owner")
    assert is_auto_block_exempt(
        company=company,
        member=member,
        user_id=5,
        policies={"auto_block_exempt_user_ids": []},
    )


def test_exempt_list_in_policy():
    company = _company(owner_id=1)
    member = _member(user_id=42, role="photographer")
    assert is_auto_block_exempt(
        company=company,
        member=member,
        user_id=42,
        policies={"auto_block_exempt_user_ids": [42]},
    )


def test_should_block_inactive_member():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=90)
    old = now - timedelta(days=120)
    assert should_block_member(last_active=old, cutoff=cutoff, user_status="active_individual")


def test_should_not_block_owner_status_already_blocked():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=90)
    old = now - timedelta(days=120)
    assert not should_block_member(last_active=old, cutoff=cutoff, user_status="blocked")


def test_should_not_block_recent_login():
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=90)
    recent = now - timedelta(days=10)
    assert not should_block_member(last_active=recent, cutoff=cutoff, user_status="active_individual")
