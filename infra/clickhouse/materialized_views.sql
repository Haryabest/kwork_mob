CREATE MATERIALIZED VIEW IF NOT EXISTS worker_metrics_hourly
ENGINE = SummingMergeTree()
ORDER BY (worker_id, hour)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    worker_id,
    avg(gpu_util) AS gpu_util,
    avg(gpu_temp) AS gpu_temp,
    avg(cpu_percent) AS cpu_percent,
    avg(ram_percent) AS ram_percent
FROM worker_metrics_minute
GROUP BY hour, worker_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS queue_metrics_hourly
ENGINE = SummingMergeTree()
ORDER BY (queue_name, hour)
AS SELECT
    toStartOfHour(timestamp) AS hour,
    queue_name,
    avg(length) AS length,
    avg(avg_wait_seconds) AS avg_wait_seconds
FROM queue_metrics_minute
GROUP BY hour, queue_name;
