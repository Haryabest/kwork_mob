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
