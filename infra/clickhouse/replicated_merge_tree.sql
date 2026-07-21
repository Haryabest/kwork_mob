-- HA overlay §12.4 / §22.2.3 — применять на кластере ClickHouse с Keeper (ZooKeeper).
-- Dev single-node использует MergeTree из init.sql.

CREATE TABLE IF NOT EXISTS user_events_replicated ON CLUSTER '{cluster}' (
    event_id UUID,
    user_id UInt64,
    company_id Nullable(UInt64),
    member_role LowCardinality(String),
    event_type LowCardinality(String),
    event_ts DateTime,
    payload String
) ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/user_events', '{replica}')
PARTITION BY toYYYYMM(event_ts)
ORDER BY (event_ts, event_type, user_id)
TTL event_ts + INTERVAL 1 YEAR;

CREATE TABLE IF NOT EXISTS service_logs_replicated ON CLUSTER '{cluster}' (
    timestamp DateTime,
    source String,
    level String,
    message String,
    worker_id String,
    user_id Nullable(UInt64),
    company_id Nullable(UInt64),
    task_id String,
    details String
) ENGINE = ReplicatedMergeTree('/clickhouse/tables/{shard}/service_logs', '{replica}')
PARTITION BY toYYYYMM(timestamp)
ORDER BY (timestamp, source)
TTL timestamp + INTERVAL 3 MONTH;
