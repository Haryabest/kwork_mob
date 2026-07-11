# KWork Mob — платформа 3D-моделей для маркетплейсов

B2B-сервис генерации интерактивных 3D-моделей товаров для Wildberries и Ozon.

## Структура проекта

```
kwork_mob/
├── backend/orchestrator/   # FastAPI: API Gateway, оркестратор, очереди
├── worker/                 # GPU-воркер (TRELLIS + постобработка)
├── apps/
│   ├── mobile/             # React Native (iOS / Android)
│   ├── web-seller/         # Next.js — личный кабинет селлера (§20 ТЗ)
│   └── web-admin/          # React — Staff Panel: владелец + поддержка
├── packages/shared/        # Общие типы и схемы
├── infra/                  # Docker, Nginx, мониторинг
├── docs/                   # Документация
└── scripts/                # Утилиты развёртывания
```

## Быстрый старт (dev)

```bash
cp .env.example .env
docker compose up -d postgres redis minio clickhouse
cd backend/orchestrator && pip install -e ".[dev]" && alembic upgrade head
uvicorn app.main:app --reload
```

## Компоненты

| Компонент | Стек | Порт |
|-----------|------|------|
| Orchestrator | FastAPI, Redis, PostgreSQL | 8000 |
| Worker | Python, CUDA, TRELLIS | — |
| Staff Panel | React, Vite | 3001 |
| Web Seller | Next.js, Tailwind | 3000 |
| Mobile | React Native, Expo | — |

## Документация

- [API](docs/api/README.md)
- [Развёртывание](docs/deployment/README.md)
- [Руководство пользователя](docs/user-guide/README.md)
- [B2B API](docs/b2b/README.md)

Полное ТЗ: `ТЗ.txt`
