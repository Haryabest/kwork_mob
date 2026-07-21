"""§11.15 WebSocket live admin dashboard."""

from app.services.events import admin_dashboard_channel, publish_admin_dashboard


def test_admin_dashboard_channel():
    assert admin_dashboard_channel() == "events:admin:dashboard"


def test_admin_dashboard_ws_route():
    from app.websocket.routes import ws_router

    paths = {getattr(r, "path", "") for r in ws_router.routes}
    assert "/ws/admin/dashboard" in paths


async def _noop_publish(event):
    return event


def test_publish_admin_dashboard_import():
    from app.services import events as ev

    assert callable(ev.publish_admin_dashboard)
