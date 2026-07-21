"""§12.4 ReplicatedMergeTree, §12.5 vector logs, §12.6 CH erasure."""

from pathlib import Path


def test_replicated_merge_tree_sql():
    p = Path(__file__).resolve().parents[3] / "infra" / "clickhouse" / "replicated_merge_tree.sql"
    text = p.read_text(encoding="utf-8")
    assert "ReplicatedMergeTree" in text
    assert "user_events_replicated" in text


def test_vector_config():
    p = Path(__file__).resolve().parents[3] / "infra" / "vector" / "vector.toml"
    text = p.read_text(encoding="utf-8")
    assert "clickhouse" in text
    assert "service_logs" in text


def test_service_logs_ttl_3_months():
    sql = (Path(__file__).resolve().parents[3] / "infra" / "clickhouse" / "init.sql").read_text(
        encoding="utf-8"
    )
    assert "TTL timestamp + INTERVAL 3 MONTH" in sql


def test_clickhouse_erasure_tables():
    from app.services.clickhouse_erasure import _CH_USER_TABLES

    assert "user_events" in _CH_USER_TABLES
    assert "mobile_analytics_events" in _CH_USER_TABLES


def test_user_events_sync_task_registered():
    from app.tasks.celery_app import celery_app

    assert "app.tasks.celery_app.sync_user_events_to_clickhouse" in celery_app.tasks
