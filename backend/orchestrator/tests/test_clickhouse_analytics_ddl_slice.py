"""ClickHouse DDL for mobile analytics §19.20."""

from pathlib import Path


def test_init_sql_has_mobile_analytics_events():
    sql = (Path(__file__).resolve().parents[3] / "infra" / "clickhouse" / "init.sql").read_text(
        encoding="utf-8"
    )
    assert "CREATE TABLE IF NOT EXISTS mobile_analytics_events" in sql
    assert "mobile_analytics_daily" in sql
    assert "mobile_analytics_screen_daily" in sql
    assert "mobile_analytics_banner_daily" in sql
    backfill = Path(__file__).resolve().parents[3] / "infra" / "clickhouse" / "backfill_mobile_analytics_screen_daily.sql"
    assert backfill.is_file()
    backfill_banner = Path(__file__).resolve().parents[3] / "infra" / "clickhouse" / "backfill_mobile_analytics_banner_daily.sql"
    assert backfill_banner.is_file()
