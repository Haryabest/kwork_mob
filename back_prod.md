# Backend prod readiness (по `.claude/ТЗ.txt`)

**Область:** `backend/orchestrator/`, `worker/`, `infra/`  
**Обновлено:** 2026-07-21

## Итог

| Метрика | Было | Цель |
|---------|------|------|
| Код vs ТЗ | ~85% | 100% |
| Prod-ready | ~62% | 100% |

**Вердикт:** бизнес-API зрелый; блокеры — storage/backup, HA ops, prod GPU pipeline, KPI §1.4.

---

## Статус по разделам ТЗ

| § | Тема | Статус | % |
|---|------|--------|---|
| 1 | KPI §1.4 | UNVERIFIED | 55 |
| 2 | Auth, B2B, legal | DONE | 85 |
| 3 | Server mobile API | PARTIAL | 78 |
| 4 | Orchestrator | PARTIAL | 88 |
| 5 | Worker Docker | PARTIAL | 68 |
| 6 | Постобработка | PARTIAL | 72 |
| 7 | Публикация | PARTIAL | 65 |
| 8 | Оплата | DONE | 88 |
| 9 | Хранение | PARTIAL | 78 |
| 10 | Безопасность | PARTIAL | 80 |
| 11 | Admin API | DONE | 85 |
| 12 | ClickHouse / events | PARTIAL | 68 |
| 13 | Quality / errors | DONE | 82 |
| 14 | Интеграции | DONE | 82 |
| 15 | Документация | PARTIAL | 40 |
| 16 | Server i18n | PARTIAL | 60 |
| 17 | Апсейлы | DONE | 90 |
| 18 | TRELLIS rollout | DONE | 85 |
| 19 | Mobile UI | N/A | — |
| 20 | ЛК селлера API | PARTIAL | 75 |
| 21 | Веб-безопасность | PARTIAL | 70 |
| 22 | Storage HA | PARTIAL | 72 |
| 23 | Мониторинг кластера | PARTIAL | 75 |

---

## DONE (есть в коде)

### §2 Auth / B2B
- JWT RS256, email+пароль, verify, refresh
- DaData ИНН (`dadata.py`)
- B2B: invite, роли, custom roles, policies, limits, audit
- Legal consents, marketing profile, shoot links
- Forbidden categories block, company deletion grace 30д, Owner 2FA

### §3 Server mobile
- Multipart/ZIP upload, cancel+refund, push→email fallback, public share

### §4 Orchestrator
- Redis+PG dual-write, Redlock, grace 25s, WS, idempotency
- Escalation, cloud autoscaling, ERP webhooks, bulk orders

### §5–6 Worker
- `worker_agent.py`, DWT watermark, Draco, FID excluded from prod Docker
- Pipeline scripts: remove_background, trellis, retopo, PBR

### §7–8
- WB/Ozon link verify, ЮKassa, промокоды, corp balance, PDF счета/акты

### §9 базовое
- MinIO presigned, lifecycle, source insurance, pg_dump→MinIO 6ч

### §10–11
- PII AES-256, NSFW+модерация, 5 скачиваний/модель/час
- Admin ~80 endpoints, watermark verify, storage health

### §12–14
- user_events, Celery→CH sync, GDPR erasure, API keys, Ollama support

### §17–18
- Upsells, TRELLIS rollout/rollback

### §22–23 в репо
- `docker-compose.ha.yml`, Patroni, Grafana, SMART exporter

---

## MISSING (нет в коде / не развёрнуто)

| ID | ТЗ | Статус |
|----|-----|--------|
| P1 | §9.3.2 `pg_partman` + `pg_cron` | **DONE** — `partman.py`, Celery 03:00, `infra/postgres/pg_partman_init.sql` |
| P2 | §9.4 WAL-G incremental + GPG + PITR | **DONE** — `backup.py` GPG+WAL-G, Celery 6h, `infra/backup/walg-backup.sh` |
| P3 | §9.5.2 Async export всех данных компании | **DONE** — `company_data_export.py` |
| P4 | §4.2.2 PG dequeue `SKIP LOCKED` при падении Redis | **DONE** — `queue.py` |
| P5 | §10.10 reCAPTCHA register/pay (подозрительные) | **DONE** — `captcha_guard.py` |
| P6 | §10.10 Лимит 10 заказов/час | **DONE** — `order_rate_limit.py` |
| P7 | §12.1 Debezium PG→CH | MISSING — только Celery app-sync |
| P8 | §22.5 Witness/quorum split-brain | **DONE** — `infra/ha/witness/`, admin `/ha/witness` |
| P9 | §10.7.6 / §21 WAF Cloudflare | **DONE** — `cloudflare_waf.py`, `infra/cloudflare/waf-rules.example.json` |
| P10 | §9.5.1 Dedicated B2B buckets (опция) | **DONE** — `company_buckets.py`, admin API |
| P11 | §10 CSE premium KMS | MISSING (опция) |
| P12 | §23.1 VictoriaMetrics + полный exporter stack | **DONE** — compose + `prometheus.ha.yml`, admin `/monitoring/victoria` |
| P13 | §1.4 Все KPI prod | UNVERIFIED |
| P14 | §5 TRELLIS prod (`WORKER_PIPELINE_MODE=stub` default) | UNVERIFIED |
| P15 | §7.6 Marketplace API upload | PARTIAL — scaffold |

---

## PARTIAL (доработать)

- §4.2.2 — PG fallback только при ошибке Redis (не при пустой очереди)
- §6.1.1 — rembg первым, ТЗ: DeepLab primary
- §9.6 — MinIO VIP: `MINIO_VIP` + `infra/ha/keepalived/` (prod deploy на узлах)
- §4.3 — Tailscale mesh + WS fallback в prod agent
- §12 — CH sync через Celery (лаг при сбоях)
- §22 — HA compose есть, cutover нет

---

## UNVERIFIED (§1.4 DoD)

- Генерация ≤3/5 мин
- Success rate ≥95%
- Воронка ≥60%
- Оценки 4–5 ≥80%
- NSFW false rate <1%
- DWT 100%
- 100 задач/час
- Redlock e2e без дублей
- SLA поддержки ≤2ч

---

## План доработки (приоритет)

### Спринт 1 — код (текущий)
- [x] `back_prod.md` — этот файл
- [x] §4.2.2 PG `SKIP LOCKED` dequeue (`queue.py`, `dispatcher.py`)
- [x] §9.5.2 Company data export async job (`company_data_export.py`, migration 045)
- [x] §10.10 reCAPTCHA register/pay (`captcha_guard.py`)
- [x] §10.10 Order rate limit 10/h (`order_rate_limit.py`)
- [x] Заготовки §9.3.2 pg_partman, §9.4 WAL-G (`infra/`)

### Спринт 2 — storage
- [x] §9.3.2 pg_partman deploy (`partman.py`, Celery, `infra/postgres/pg_partman_init.sql`)
- [x] §9.4 WAL-G + GPG (`backup.py`, Celery, `infra/backup/walg-backup.sh`)
- [x] §9.5.1 Dedicated buckets (`company_buckets.py`, admin API)

### Спринт 3 — HA / ops
- [x] §22.5 Witness node (`infra/ha/witness/`, docker-compose.ha.yml)
- [x] §9.6 MinIO VIP / Keepalived (`infra/ha/keepalived/`, `MINIO_VIP`)
- [x] §10.7.6 WAF Cloudflare (`cloudflare_waf.py`, rules template)
- [x] §23.1 Exporters + VictoriaMetrics (`prometheus.ha.yml`, compose)

### Спринт 4 — prod validation
- [x] `WORKER_PIPELINE_MODE=trellis` prod template (`worker/.env.prod.example`)
- [x] Load test 100 orders (`load_test.py`, `scripts/load_test_orders.py`, `POST /admin/load-test/queue`)
- [x] KPI §1.4 DoD dashboard (`dod_metrics.py`, `GET /admin/dod-metrics`)
- [x] §6.1.1 DeepLab primary в `remove_background.py`
- [x] Debezium connector template (`infra/debezium/user-events-connector.json`)

---

## Файлы

| Компонент | Путь |
|-----------|------|
| API router | `backend/orchestrator/app/api/v1/router.py` |
| Queue | `backend/orchestrator/app/services/queue.py` |
| Dispatcher | `backend/orchestrator/app/services/dispatcher.py` |
| Worker | `worker/worker_agent.py` |
| HA compose | `docker-compose.ha.yml` |
| CH DDL | `infra/clickhouse/` |

---

## Команды проверки

```bash
cd backend/orchestrator
pytest tests/ -q --tb=no
```

```bash
cd worker
python -m pytest tests/test_dwt_jpeg_webp.py -q
```
