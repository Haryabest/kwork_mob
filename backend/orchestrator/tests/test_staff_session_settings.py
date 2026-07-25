"""Staff session settings §11.1."""

from __future__ import annotations

import pytest

from app.services import staff_session_settings as sess


@pytest.mark.asyncio
async def test_staff_session_save_and_load(db):
    saved = await sess.save_settings(
        db,
        {
            "staff_jwt_access_expire_minutes": 600,
            "staff_idle_timeout_minutes": 45,
            "staff_jwt_refresh_expire_days": 14,
        },
    )
    await db.commit()
    assert saved["staff_jwt_access_expire_minutes"] == 600
    assert saved["staff_idle_timeout_minutes"] == 45
    assert saved["staff_jwt_refresh_expire_days"] == 14

    loaded = await sess.load_settings(db)
    assert loaded["staff_jwt_access_expire_minutes"] == 600
    assert loaded["staff_idle_timeout_minutes"] == 45


def test_staff_session_settings_routes():
    from app.api.v1 import admin_finance as fin

    paths = {getattr(r, "path", "") for r in fin.router.routes}
    assert "/session/settings" in paths


def test_merge_settings_clamps_invalid():
    merged = sess.merge_settings(
        {
            "staff_jwt_access_expire_minutes": 10,
            "staff_idle_timeout_minutes": 2,
            "staff_jwt_refresh_expire_days": 0,
        }
    )
    defaults = sess.env_defaults()
    assert merged["staff_jwt_access_expire_minutes"] == defaults["staff_jwt_access_expire_minutes"]
    assert merged["staff_idle_timeout_minutes"] == defaults["staff_idle_timeout_minutes"]
