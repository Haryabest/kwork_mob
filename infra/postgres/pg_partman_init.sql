-- §9.3.2 pg_partman + pg_cron — партиционирование PostgreSQL
-- Выполнить от superuser на prod PostgreSQL (после CREATE EXTENSION).

CREATE EXTENSION IF NOT EXISTS pg_partman;
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- user_events: партиции по месяцу (§12.1)
SELECT partman.create_parent(
    p_parent_table := 'public.user_events',
    p_control := 'created_at',
    p_type := 'native',
    p_interval := 'monthly',
    p_premake := 3
);

-- orders: партиции по месяцу (опционально, для крупных объёмов)
-- SELECT partman.create_parent(
--     p_parent_table := 'public.orders',
--     p_control := 'created_at',
--     p_type := 'native',
--     p_interval := 'monthly',
--     p_premake := 3
-- );

-- Ежедневное обслуживание 03:00 UTC (дублирует Celery task)
SELECT cron.schedule(
    'partman-maintenance',
    '0 3 * * *',
    $$SELECT partman.run_maintenance()$$
);
