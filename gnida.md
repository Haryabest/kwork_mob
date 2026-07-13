# gnida.md — план кодинга (без тестов на GPU)

**Дата:** 2026-07-14  
**Контекст:** на домашнем ПК остановились на smoke TRELLIS.2 (воркер качает фото, `remove_background` идёт). На другом ПК — **только писать код**, не гонять docker/GPU/push.

**Перед стартом:** `git pull`, открыть `.claude/CLAUDE.MD` + `not-ready.md`.

---

## Что НЕ делаем завтра

- Docker build / `e2e_trellis_acceptance` / `nvidia-smi`
- Firebase push на устройстве
- `alembic upgrade` на стенде, k6/locust прогоны
- Soft launch burn ₽/ч

---

## День 1 — порядок работ

| # | Блок | Часы | Итог |
|---|------|------|------|
| 1 | Worker / TRELLIS.2 hardening | 3–4 | образ и агент готовы к прогону дома |
| 2 | Admin Logs (backend + UI) | 2–3 | `/logs` не placeholder |
| 3 | Celery `auto_block_inactive` | 1–2 | политика §2.5.4 работает в коде |
| 4 | Grafana + HAProxy scaffold | 2 | конфиги в репо, без поднятия кластера |
| 5 | ТЗ / docs sync TRELLIS.2 | 1 | ТЗ не противоречит коду |

---

## Блок 1 — Worker / TRELLIS.2 (код)

### 1.1 `setup.sh` в Docker-образе

**Файлы:** `worker/Dockerfile`, опционально `worker/scripts/install_trellis2.sh`

**Сделать:**
- После `git clone TRELLIS.2` вызывать `setup.sh` (или эквивалент deps: `o-voxel`, `xformers`, flash-attn с `|| true` где не собирается в CI)
- `pip install -e /app/trellis` без silent fail на критичных пакетах
- `DOWNLOAD_WEIGHTS=1` — веса `microsoft/TRELLIS.2-4B` в `/app/trellis/weights` (или HF cache в образе)
- Закрепить `torch` **cu128** (уже в Dockerfile — не откатывать на cu124)

**DoD:** Dockerfile собирается логически полным; в README одна команда build.

### 1.2 Живые логи пайплайна

**Файлы:** `worker/worker_agent.py`

**Сделать:**
- `run_script()` — стрим stdout/stderr в logger построчно (не ждать конца шага)
- Лог `Starting step X` / `Finished step X in Ys` до и после subprocess
- Env `WORKER_SUBPROCESS_STREAM=1` (default on)

**DoD:** при прогоне дома видно, на каком шаге зависло, без `docker exec ps`.

### 1.3 Таймауты и дубли задач

**Файлы:** `worker/worker_agent.py`, `.env.example`

**Сделать (если ещё не в main):**
- `WORKER_TASK_DRAIN_TIMEOUT_SEC=3600` — в env example + `ЗАВТРА_ЛОКАЛЬНЫЙ_ЗАПУСК.md`
- Skip duplicate `task` assign если та же `task_id` уже в `_task_coro`
- Документировать: WS `closed` при обработке — норма

### 1.4 TRELLIS.2 runtime

**Файлы:** `worker/scripts/trellis_runtime.py`, `trellis_generate.py`, `pipeline_env.py`

**Сделать:**
- Явная ошибка если `sm_120` + torch без cu128 (preflight в runtime)
- Один вход: `view_00` после nobg (не 12-view legacy)
- Stub fallback только при `TRELLIS_ALLOW_STUB_FALLBACK=1`

### 1.5 E2E harness (код без прогона)

**Файлы:** `worker/scripts/e2e_trellis_acceptance.py`

**Сделать:**
- `--photos` опционально: режим `--from-minio` с env bucket/prefix (для будущего)
- Отчёт JSON в `e2e_reports/` с полями `step_timings`, `trellis_version`, `cuda`

---

## Блок 2 — Admin Logs

**Файлы:**
- `backend/orchestrator/app/api/v1/admin_logs.py` (новый)
- `backend/orchestrator/app/services/log_query.py` (новый)
- `apps/web-admin/src/pages/LogsPage.tsx` (вынести из placeholder в `AdminPages.tsx`)
- `infra/prometheus/` или `infra/loki/` — заготовка

**Сделать:**
- API `GET /admin/logs?source=&level=&q=&from=&to=&limit=`
- Источник v1: **ClickHouse** таблица `service_logs` (если нет — migration + writer в middleware) **или** чтение из PG `audit_events` + orchestrator structlog
- Fallback: mock paginated для dev без ClickHouse
- UI: фильтры, таблица, auto-refresh 10s, export CSV

**DoD:** `LogsPage` показывает реальные записи при локальном API (хотя бы audit + worker events из HTTP callback).

---

## Блок 3 — Celery auto_block_inactive

**Файлы:**
- `backend/orchestrator/app/tasks/celery_app.py`
- `backend/orchestrator/app/tasks/company_maintenance.py` (новый)
- `backend/orchestrator/app/services/company_policies.py`

**Сделать:**
- Beat task раз в сутки: для каждой company с `auto_block_inactive_days` найти members с `last_login_at` старше N дней → `status=blocked`, audit log
- Уважать Owner (не блокировать), исключения в политике
- Unit-тест на логику (mock DB)

**DoD:** задача зарегистрирована в beat; ручной `celery call` не обязателен завтра.

---

## Блок 4 — Infra scaffold (только файлы)

### 4.1 Grafana datasources

**Файлы:** `infra/grafana/provisioning/datasources/*.yaml`

**Сделать:** auto-provision Prometheus `:9090`, ClickHouse `:8123`.

### 4.2 HAProxy + Patroni

**Файлы:** `infra/ha/haproxy.cfg`, `docker-compose.ha.yml`, `docs/deployment/HA.md`

**Сделать:** VIP frontend :5432 → Patroni primary; healthcheck; runbook cutover (текст).

### 4.3 MinIO SMART agent

**Файлы:** `infra/agents/minio_smart_exporter/` (Python или shell + node_exporter textfile)

**Сделать:** скрипт SMART/disk% → Prometheus metric `minio_node_disk_smart_*`; admin `/storage/smart` уже есть — подключить поле `smart_disks[]` если пусто.

---

## Блок 5 — ТЗ и docs

**Файлы:** `Техническое задание 3DVektor.txt`, `ТЗ.txt` (точечно grep §5 §6)

**Сделать:**
- TRELLIS **v2**: single image input, native PBR, `512`+`low_vram` для 12GB
- Убрать/пометить legacy 12-view multi-view gen
- `ready.md` / `not-ready.md` — перенести GPU-приёмку в «дома»

---

## Блок 6 — если останется время (P2)

| # | Задача | Файлы |
|---|--------|-------|
| 6.1 | Vault/AES ПД §2.7 | `app/core/crypto.py`, encrypt ФИО/реквизиты |
| 6.2 | Воронка публикации в dashboard | `web-admin` Dashboard + API агрегат |
| 6.3 | Seller support UI §20.7 | `web-seller` `/support` довести до create ticket |
| 6.4 | WB/Ozon API upload scaffold | `app/services/marketplace_upload.py` + interface |
| 6.5 | Mobile thermal §3.8.2 | `apps/mobile` battery thermal → FPS cap |

---

## Чеклист перед коммитом (без GPU)

```bash
cd backend/orchestrator && ruff check . && pytest tests/ -q --ignore=tests/integration
cd apps/web-admin && npm run build
cd apps/web-seller && npm run build
```

---

## Дома (другой ПК) — один прогон

1. `docker build` worker с cu128
2. `docker compose up` + uvicorn + seller
3. `docker run` воркер → заказ → `completed` + превью GLB
4. `e2e_trellis_acceptance --preflight --fail-on-budget` (опционально)

---

## Ссылки

- Шпаргалка: `.claude/CLAUDE.MD`
- Полный план: `.claude/plan.md`
- Готово: `ready.md`
- Пробелы: `not-ready.md`
- Локальный запуск: `ЗАВТРА_ЛОКАЛЬНЫЙ_ЗАПУСК.md`
