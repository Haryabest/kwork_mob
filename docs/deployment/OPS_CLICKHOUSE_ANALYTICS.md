# ClickHouse mobile analytics — backfill MV §19.20

После деплоя MV на существующий ClickHouse с данными в `mobile_analytics_events` выполните **оба** backfill (порядок не важен):

## 1. Screen breakdown MV

```powershell
cd infra/clickhouse
.\backfill_screen_mv.ps1
```

SQL: `backfill_mobile_analytics_screen_daily.sql` → `mobile_analytics_screen_daily`.

## 2. Banner CTR MV

```powershell
cd infra/clickhouse
.\backfill_banner_mv.ps1
```

SQL: `backfill_mobile_analytics_banner_daily.sql` → `mobile_analytics_banner_daily`.

## Env

| Переменная | Default |
|------------|---------|
| `CLICKHOUSE_HOST` | localhost |
| `CLICKHOUSE_PORT` | 8123 |
| `CLICKHOUSE_DB` | kwork_metrics |
| `CLICKHOUSE_USER` / `CLICKHOUSE_PASSWORD` | optional |

## Проверка

```sql
SELECT count() FROM mobile_analytics_screen_daily;
SELECT count() FROM mobile_analytics_banner_daily;
```

Admin: `/analytics` — source `clickhouse`, campaign CTR в `/campaigns`.

## PG→CH sync

Celery `sync_analytics_to_clickhouse` каждые 15 мин. Ручной триггер: `POST /admin/analytics/sync`.

Алерт backlog: `pending_ch_sync > analytics_ch_sync_pending_max` (Settings → пороги, default 1000).
