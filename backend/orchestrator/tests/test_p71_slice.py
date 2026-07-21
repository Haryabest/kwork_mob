"""§12.7 company user_events export."""

from app.api.v1 import company as co


def test_company_user_events_export_route():
    paths = {getattr(r, "path", "") for r in co.router.routes}
    assert "/user-events/export" in paths


def test_ch_mv_ttl_12_8():
    sql = (
        __import__("pathlib").Path(__file__).resolve().parents[3]
        / "infra"
        / "clickhouse"
        / "init.sql"
    ).read_text(encoding="utf-8")
    assert "worker_metrics_daily" in sql
    assert "queue_metrics_daily" in sql
    assert "user_events_hourly" in sql
    assert "TTL timestamp + INTERVAL 7 DAY" in sql
