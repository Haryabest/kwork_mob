# KWork Mob — шпаргалка для AI

B2B-платформа 3D-моделей товаров для Wildberries/Ozon. Полное ТЗ: `ТЗ.txt` (6073 строк, читать точечно через grep).
План до production: `.claude/plan.md` (фазы A–Q, чеклисты по всем §1–§23).

## Стек

| Компонент | Путь | Технологии | Порт |
|-----------|------|------------|------|
| Orchestrator | `backend/orchestrator/` | FastAPI, SQLAlchemy, Redis, Celery | 8000 |
| Worker | `worker/` | Python, CUDA, **TRELLIS.2-4B**, Docker | — |
| Mobile | `apps/mobile/` | **Flutter / Dart** | — |
| Staff Panel (admin + support) | `apps/web-admin/` | React, Vite, Mantine · роли admin/support_agent | **3001** |
| Web Seller | `apps/web-seller/` | Next.js, Mantine | **3000** |
| ~~web-support~~ | — | **не использовать** → всё в web-admin :3001 | — |
| Shared types | `packages/shared/` | TypeScript | — |

Infra: `docker-compose.yml`, конфиги в `infra/` (nginx, prometheus, clickhouse).

## Backend (`backend/orchestrator/app/`)

```
main.py              — точка входа FastAPI
core/                — config, database, redis, security, middleware
api/v1/              — роутеры (auth, orders, company, admin, moderation...)
models/__init__.py   — SQLAlchemy-модели (User, Order, TaskQueue, NsfwBlock...)
schemas/             — Pydantic-схемы
services/            — queue, minio, yookassa, nsfw, ollama
tasks/celery_app.py  — фоновые задачи (sync queue, push, backup)
websocket/routes.py  — /ws/queue/{user_id}, /ws/worker
alembic/             — миграции БД (НЕ Python-пакет!)
tests/               — pytest
```

API prefix: `/api/v1`. Docs: `/api/docs`. Health: `/health`.

**Ключевые паттерны из ТЗ:**
- Очередь: Redis List + резерв PostgreSQL (`task_queue`), sync каждую минуту
- Redlock: `SET task:{id} NX EX 60` перед обработкой
- Grace period: 25–30 сек (heartbeat 5 сек, offline 20 сек)
- DWT watermark только в diffuse; FID только в `worker/dev-tools/`
- NSFW: возврат по умолчанию; запрещённые категории — заказ не создаётся

## Worker (`worker/`)

```
worker_agent.py      — WebSocket-агент, Redlock, пайплайн
scripts/             — remove_background, trellis_generate (TRELLIS.2), retopology,
                       bake_pbr (skip при .2), apply_watermark, compress_draco, validate_glb
                       trellis_runtime.py — Trellis2ImageTo3DPipeline + o_voxel export
cloud/               — Intelion/Immers: provision.py «в два клика»
dev-tools/compute_fid.py — только dev, не в Docker
```

Облачные GPU: Intelion (`intelion.cloud/api`), Immers (`immers.cloud/api`) — см. `Адреса Облачных Воркеров.txt`.
Архитектура 4 слоя: оркестратор → Storage HA ×2 → GPU-воркеры → мобилка (`Архитектура 3dvektor.txt`).

## Frontend (3 клиента — разные аудитории)

| App | Кто заходит | UI | ТЗ |
|-----|-------------|----|-----|
| `web-seller` | Селлеры WB/Ozon | Mantine 7 + Tabler Icons | §2.4, §20 |
| `web-admin` | Владелец + поддержка | Mantine 7 + Tabler Icons | §11 |
| `mobile` | Селлеры | **Flutter** (Dart) | §3, §16, §19 |

## Env

`.env.example` → `.env`. Порты (если 5432/6379/9000 заняты другими проектами):
- PostgreSQL: `5435`
- Redis: `6382`
- MinIO: `9010` (console `9011`)

## Статус

- **Auth** — register (+consents §2.8) / verify (+JWT) / login / account-type (individual+legal) / reset confirm
- **Legal** — `/legal/*`, `user_consents`, seed docs; миграция `004_legal_support`
- **Миграции** — `001_initial`, `002_web`, `003_staff_2fa`, `004_legal_support`
- **Staff seed** — `admin@example.com` / `admin1234`, `support@example.com` / `support1234`
- **Staff auth §11** — `/api/v1/staff/*`: VPN CIDR, TOTP 2FA, JWT 8ч, idle 30 мин
- **web-seller** — auth+consents+noindex+support/FAQ live API; UI §20 остальное
- **web-admin** — UI §11 + VPN+2FA login
- **Admin API** — users/companies/workers/support/legal consents/queue stats; storage MinIO health+presign
- **Очередь** — dual-write Redis+PG при создании заказа (если хватает баланса)
- **ЮKassa** — create payment + webhook; без ключей — mock-зачисление
- **Mobile** — Flutter (замена RN/Expo): onboarding, auth→API, home shell, category+forbidden checklist


## Правила для AI

- Минимальный diff, не переписывать рабочий код
- Комментарии на русском в backend
- Не включать `compute_fid.py` в production worker
- Не коммитить без явной просьбы
- ТЗ читать через grep/offset, не целиком
