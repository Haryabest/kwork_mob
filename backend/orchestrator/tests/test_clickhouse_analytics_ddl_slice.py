"""ClickHouse DDL for mobile analytics §19.20."""

from pathlib import Path


def test_init_sql_has_mobile_analytics_events():
    sql = (Path(__file__).resolve().parents[3] / "infra" / "clickhouse" / "init.sql").read_text(
        encoding="utf-8"
    )
    assert "CREATE TABLE IF NOT EXISTS mobile_analytics_events" in sql
    assert "mobile_analytics_daily" in sql
