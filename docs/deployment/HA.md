# HA Storage (MinIO 2-node, Redis Sentinel, PG Patroni)

```bash
docker compose -f docker-compose.ha.yml up -d
# Patroni (profile):
docker compose -f docker-compose.ha.yml --profile patroni up -d --build
```

| Сервис | Порты | Назначение |
|--------|-------|------------|
| postgres-primary / replica | 5432 | Streaming replica (+ Patroni scaffold) |
| patroni-1 (profile) | 5433 / 8008 | Patroni REST + PG |
| redis-master + replica | 6379 | AOF |
| redis-sentinel ×3 | 26379 | failover `mymaster` |
| minio-1 / minio-2 | 9010/9012 | replication |
| grafana | 3002 | dashboards `infra/grafana/dashboards` |

## Env оркестратора

```
REDIS_URL=redis://redis-master:6379/0
REDIS_SENTINELS=redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379
REDIS_SENTINEL_MASTER=mymaster
MINIO_ENDPOINT=http://minio-1:9000
MINIO_DISK_TOTAL_BYTES=2000000000000
```

Клиент Sentinel: `app/core/redis.py`. SMART: `GET /api/v1/storage/smart`.
