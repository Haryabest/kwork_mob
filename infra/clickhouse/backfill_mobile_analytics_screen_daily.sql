-- Backfill mobile_analytics_screen_daily for existing ClickHouse instances §19.20.
-- Run once after deploying MV on a DB that already has mobile_analytics_events rows.
-- Safe to re-run: SummingMergeTree merges duplicate (day, screen) keys.

INSERT INTO mobile_analytics_screen_daily (day, screen, events)
SELECT
    toDate(event_ts) AS day,
    JSONExtractString(props, 'screen') AS screen,
    count() AS events
FROM mobile_analytics_events
WHERE event = 'screen_view'
  AND JSONExtractString(props, 'screen') != ''
GROUP BY day, screen;
