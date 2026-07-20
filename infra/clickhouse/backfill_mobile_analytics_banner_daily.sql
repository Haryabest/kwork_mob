-- Backfill mobile_analytics_banner_daily for existing ClickHouse instances §19.20.

INSERT INTO mobile_analytics_banner_daily (day, banner_id, screen, events)
SELECT
    toDate(event_ts) AS day,
    toInt64OrZero(JSONExtractString(props, 'banner_id')) AS banner_id,
    JSONExtractString(props, 'screen') AS screen,
    count() AS events
FROM mobile_analytics_events
WHERE event = 'screen_view'
  AND JSONExtractString(props, 'screen') IN ('campaign_banner', 'campaign_banner_click')
  AND toInt64OrZero(JSONExtractString(props, 'banner_id')) > 0
GROUP BY day, banner_id, screen;
