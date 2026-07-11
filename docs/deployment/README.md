# Развёртывание

## Требования

- Docker 24+, Docker Compose v2
- NVIDIA GPU + CUDA 12.x (для воркеров)
- Node.js 20+ (для фронтенда)
- Python 3.11+ (для оркестратора)

## Dev-окружение

```bash
cp .env.example .env
docker compose up -d postgres redis minio clickhouse
cd backend/orchestrator && pip install -e ".[dev]" && alembic upgrade head
uvicorn app.main:app --reload
```

## Production

1. Tailscale VPN для связи оркестратор ↔ воркеры
2. MinIO-кластер (2 узла, репликация)
3. PostgreSQL бэкап каждые 6 часов → MinIO
4. Redis AOF + Sentinel
5. Nginx + TLS
6. WireGuard VPN для admin-панели + 2FA

## Grace period

По умолчанию 25 сек (настраивается 25–30 сек в admin-панели).

## Redlock

Воркер выполняет `SET task:{task_id} processing NX EX 60` перед обработкой.
