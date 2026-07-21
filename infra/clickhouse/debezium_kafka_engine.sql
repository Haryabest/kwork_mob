-- §12.1 Kafka engine for Debezium topics → user_events (run on CH after Redpanda+Debezium)
-- Topic: kwork.public.user_events (see infra/debezium/user-events-connector.json)

CREATE TABLE IF NOT EXISTS user_events_kafka (
    raw String
) ENGINE = Kafka
SETTINGS
    kafka_broker_list = 'redpanda:9092',
    kafka_topic_list = 'kwork.public.user_events',
    kafka_group_name = 'ch_user_events_consumer',
    kafka_format = 'JSONAsString',
    kafka_num_consumers = 1;

CREATE TABLE IF NOT EXISTS user_events_debezium_staging (
    event_id String,
    user_id UInt64,
    company_id Nullable(UInt64),
    member_role String,
    event_type String,
    event_ts DateTime64(3, 'UTC'),
    payload String
) ENGINE = MergeTree()
ORDER BY (event_ts, event_id);

-- Materialized view: parse Debezium envelope (after row)
CREATE MATERIALIZED VIEW IF NOT EXISTS user_events_debezium_mv TO user_events_debezium_staging AS
SELECT
    JSONExtractString(JSONExtractRaw(raw, 'after'), 'event_id') AS event_id,
    toUInt64OrZero(JSONExtractString(JSONExtractRaw(raw, 'after'), 'user_id')) AS user_id,
    toUInt64OrNull(JSONExtractString(JSONExtractRaw(raw, 'after'), 'company_id')) AS company_id,
    JSONExtractString(JSONExtractRaw(raw, 'after'), 'member_role') AS member_role,
    JSONExtractString(JSONExtractRaw(raw, 'after'), 'event_type') AS event_type,
    parseDateTime64BestEffortOrNull(JSONExtractString(JSONExtractRaw(raw, 'after'), 'created_at')) AS event_ts,
    JSONExtractRaw(JSONExtractRaw(raw, 'after'), 'payload') AS payload
FROM user_events_kafka
WHERE JSONExtractString(raw, 'op') IN ('c', 'r', 'u');
