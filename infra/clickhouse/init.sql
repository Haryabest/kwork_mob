CREATE DATABASE IF NOT EXISTS kwork_metrics;

CREATE TABLE IF NOT EXISTS worker_metrics_minute (
    timestamp DateTime,
    worker_id String,
    gpu_util Float32,
    vram_used_gb Float32,
    gpu_temp Float32,
    cpu_percent Float32,
    ram_percent Float32
) ENGINE = MergeTree()
ORDER BY (worker_id, timestamp);

CREATE TABLE IF NOT EXISTS queue_metrics_minute (
    timestamp DateTime,
    queue_name String,
    length UInt32,
    avg_wait_seconds Float32
) ENGINE = MergeTree()
ORDER BY (queue_name, timestamp);

CREATE TABLE IF NOT EXISTS order_events (
    timestamp DateTime,
    order_id UInt64,
    event_type String,
    user_id UInt64,
    company_id Nullable(UInt64),
    details String
) ENGINE = MergeTree()
ORDER BY (timestamp, order_id);

CREATE TABLE IF NOT EXISTS publication_funnel_events (
    timestamp DateTime,
    model_uuid String,
    event_type String,
    user_id UInt64,
    company_id Nullable(UInt64),
    marketplace Nullable(String)
) ENGINE = MergeTree()
ORDER BY (timestamp, event_type);

-- Materialized Views (§12.2.2)
CREATE MATERIALIZED VIEW IF NOT EXISTS worker_metrics_hourly
ENGINE = AggregatingMergeTree()
ORDER BY (worker_id, hour)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    worker_id,
    avgState(gpu_util) AS gpu_util,
    avgState(gpu_temp) AS gpu_temp,
    avgState(cpu_percent) AS cpu_percent,
    avgState(ram_percent) AS ram_percent
FROM worker_metrics_minute
GROUP BY hour, worker_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS queue_metrics_hourly
ENGINE = AggregatingMergeTree()
ORDER BY (queue_name, hour)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    queue_name,
    avgState(length) AS length,
    avgState(avg_wait_seconds) AS avg_wait_seconds
FROM queue_metrics_minute
GROUP BY hour, queue_name;

CREATE MATERIALIZED VIEW IF NOT EXISTS order_events_daily
ENGINE = SummingMergeTree()
ORDER BY (day, event_type)
AS SELECT
    toDate(timestamp) AS day,
    event_type,
    count() AS events
FROM order_events
GROUP BY day, event_type;

-- Централизованные логи (§11.5 / §9.3)
CREATE TABLE IF NOT EXISTS service_logs (
    timestamp DateTime,
    source String,
    level String,
    message String,
    worker_id String,
    user_id Nullable(UInt64),
    company_id Nullable(UInt64),
    task_id String,
    details String
) ENGINE = MergeTree()
ORDER BY (timestamp, source);

-- Mobile analytics ingest mirror §19.20 (PG source of truth)
CREATE TABLE IF NOT EXISTS mobile_analytics_events (
    user_id UInt64,
    event LowCardinality(String),
    event_ts DateTime,
    props String
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_ts)
ORDER BY (event_ts, event, user_id);

CREATE MATERIALIZED VIEW IF NOT EXISTS mobile_analytics_daily
ENGINE = SummingMergeTree()
ORDER BY (day, event)
AS SELECT
    toDate(event_ts) AS day,
    event,
    count() AS events
FROM mobile_analytics_events
GROUP BY day, event;
