# HA Storage (MinIO 2-node, Redis Sentinel, PG Patroni)

Compose: `docker compose -f docker-compose.ha.yml up -d`

| Сервис | Порты / endpoint | Назначение |
|--------|------------------|------------|
| postgres-primary / replica | 5432 inside net | Streaming replica (Patroni config scaffold в `infra/ha/patroni`) |
| redis-master + replica | 6379 | AOF + replicaof |
| redis-sentinel ×3 | 26379 | failover `mymaster` |
| minio-1 / minio-2 | 9010/9012 | 2-node + bucket replication (`infra/ha/minio/setup-replication.sh`) |

## Env оркестратора (prod)

```
POSTGRES_HOST=postgres-primary
REDIS_URL=redis://redis-master:6379/0
# Sentinel (клиенты с поддержкой):
# REDIS_SENTINELS=redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379
# REDIS_SENTINEL_MASTER=mymaster
MINIO_ENDPOINT=http://minio-1:9000
# fallback при падении primary: http://minio-2:9000
```

Dev по-прежнему: `docker compose up` (single-node).

См. также корневой `docs/deployment/README.md`.
