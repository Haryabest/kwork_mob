# Развёртывание (по `Архитектура 3dvektor.txt` + ТЗ §4 / §22)

## 4 слоя

| Слой | Что | Где в репо |
|------|-----|------------|
| 1. Оркестратор + фронт | FastAPI, Celery, Nginx, web-seller, web-admin | `backend/`, `apps/web-*`, `infra/nginx` |
| 2. Storage HA | PG Patroni, Redis Sentinel, ClickHouse, MinIO ×2 | `docker-compose.ha.yml` + `docs/deployment/HA.md` (dev — single-node) |
| 3. Воркеры GPU | TRELLIS + agent, Tailscale или WSS | `worker/`; облако: Intelion / Immers |
| 4. Мобилка | Flutter | `apps/mobile/` |

Сеть: **Tailscale** между оркестратором, storage и воркерами. Admin — VPN + 2FA.

## Требования

- Docker 24+, Docker Compose v2
- NVIDIA GPU + CUDA 12.x (для воркеров)
- Node.js 20+ (web), Python 3.11+ (orchestrator), Flutter 3.x (mobile)

## Dev-окружение

```bash
cp .env.example .env
docker compose up -d postgres redis minio clickhouse
cd backend/orchestrator && pip install -e ".[dev]" && alembic upgrade head
uvicorn app.main:app --reload
```

Облачный воркер (чеклист):

```bash
python worker/cloud/provision.py --action status
python worker/cloud/provision.py --action env
# затем GPU-инстанс у Intelion/Immers + docker run worker
```

См. `worker/cloud/README.md`, `Адреса Облачных Воркеров.txt`.

## Production (целевое)

1. Tailscale VPN: оркестратор ↔ Server1/Server2 ↔ воркеры
2. Storage HA: `docker compose -f docker-compose.ha.yml up -d` — см. [HA.md](./HA.md)
   - MinIO ×2 + bucket replication
   - Redis master/replica + Sentinel ×3
   - PG primary + streaming replica (Patroni scaffold)
3. VIP / fallback: оркестратор → Primary, при падении → Replica
4. Воркеры: дома или облако (Intelion/Immers API create/start/stop + autoscaling Celery 30с)
5. Nginx + TLS; Staff Panel только VPN+2FA
6. Бэкап PG каждые 6ч → MinIO
7. GPU приёмка TRELLIS: `python worker/scripts/e2e_trellis_acceptance.py --photos ./samples --fail-on-budget`

Облачный воркер:

```bash
export CLOUD_API_TOKEN=... CLOUD_API_MOCK=0
python worker/cloud/provision.py --action create --provider intelion --gpu rtx4090
# или из admin: POST /api/v1/admin/cloud/instances
```

## Grace period / Redlock

Grace: 25–30 сек (admin). Redlock: `SET task:{id} processing NX EX 60` перед обработкой.

