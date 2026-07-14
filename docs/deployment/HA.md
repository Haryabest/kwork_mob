# HA Storage (MinIO 2-node, Redis Sentinel, PG Patroni + HAProxy VIP)

```bash
docker compose -f docker-compose.ha.yml up -d
# Patroni + HAProxy VIP:
docker compose -f docker-compose.ha.yml --profile patroni up -d --build
```

| Сервис | Порты | Назначение |
|--------|-------|------------|
| haproxy (profile patroni) | **5432** VIP, 8404 stats | PostgreSQL → Patroni primary |
| postgres-primary / replica | 5432 internal | Streaming replica |
| patroni-1 (profile) | 5433 / 8008 | Patroni REST + PG |
| redis-master + replica | 6379 | AOF |
| redis-sentinel ×3 | 26379 | failover `mymaster` |
| minio-1 / minio-2 | 9010/9012 | replication |
| grafana | 3002 | dashboards + datasources auto-provision |

## Env оркестратора (после cutover)

```
POSTGRES_HOST=haproxy
POSTGRES_PORT=5432
REDIS_URL=redis://redis-master:6379/0
REDIS_SENTINELS=redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379
REDIS_SENTINEL_MASTER=mymaster
MINIO_ENDPOINT=http://minio-1:9000
MINIO_DISK_TOTAL_BYTES=2000000000000
MINIO_SMART_JSON=/var/lib/node_exporter/textfile/minio_smart.json
```

Клиент Sentinel: `app/core/redis.py`. SMART: `GET /api/v1/storage/smart` + `infra/agents/minio_smart_exporter/`.

## Runbook: cutover PostgreSQL на Patroni VIP (§22.3)

### Подготовка

1. Убедиться, что etcd и оба PG-узла healthy: `docker compose -f docker-compose.ha.yml ps`.
2. Поднять Patroni profile: `docker compose -f docker-compose.ha.yml --profile patroni up -d --build`.
3. Проверить Patroni REST: `curl http://localhost:8008/primary` — должен вернуть JSON с `"role":"master"`.
4. Поднять HAProxy: он в том же profile `patroni`.

### Переключение оркестратора

1. **Окно обслуживания** (2–5 мин): остановить Celery worker/beat и uvicorn.
2. В `.env` оркестратора: `POSTGRES_HOST=haproxy`, `POSTGRES_PORT=5432`.
3. `alembic upgrade head` через HAProxy — проверка записи на primary.
4. Запустить оркестратор + Celery; smoke: login, create order stub, `/health`.

### Failover (Узел A пропал)

1. Patroni на Узле B promote replica → primary (автоматически при quorum).
2. HAProxy healthcheck `/primary` переключит backend на новый master (5–10 с).
3. Оркестратор **не меняет** `POSTGRES_HOST` — VIP остаётся `haproxy:5432`.
4. Алерт в Telegram: «Patroni failover» (настроить в §12).

### Возврат Узла A (catch-up)

1. Узел A стартует как replica, догоняет WAL (`pg_rewind` / streaming).
2. Patroni возвращает узел в кластер; HAProxy может снова использовать его как backup.
3. Ручная проверка: `curl http://postgres-primary:8008/replica` и lag < `maximum_lag_on_failover`.

### Откат

1. Вернуть `POSTGRES_HOST=postgres-primary` (или localhost:5435 в dev).
2. Перезапустить оркестратор без HAProxy profile.

## MinIO SMART agent (§21)

На каждом узле хранения (cron 5 min):

```bash
MINIO_SMART_DEVICES=/dev/nvme0n1 \
MINIO_SMART_TEXTFILE_DIR=/var/lib/node_exporter/textfile \
MINIO_SMART_JSON=/var/lib/node_exporter/textfile/minio_smart.json \
python3 infra/agents/minio_smart_exporter/exporter.py
```

Prometheus scrape node_exporter textfile → метрики `minio_node_disk_smart_*`.
Admin UI читает `smart_disks[]` через `MINIO_SMART_JSON` на оркестраторе.

## Grafana datasources

Автопровижининг: `infra/grafana/provisioning/datasources/prometheus.yaml`, `clickhouse.yaml`.
Требуется plugin `grafana-clickhouse-datasource` (уже в compose).
