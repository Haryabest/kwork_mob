# not-ready.md — что ещё осталось по ТЗ

После среза Node timeline / webhooks / storage extend / forecast / trash (2026-07-14).

---

## Критично (железо)

- [ ] RTX 5070 E2E дома
- [ ] Firebase prod + push E2E
- [ ] Alembic `015`–`029` на стенде
- [ ] Заполнить `APPLE_TEAM_ID` + SHA256 fingerprint + Associated Domains на prod host
- [ ] Prod: `YOOKASSA_WEBHOOK_IP_CHECK=true` (без ALLOW_PRIVATE)
- [ ] Настроить agent hooks: MinIO/Patroni/FIO/BACKUP_RESTORE_TEST
- [ ] Prod: `LOKI_URL` или `DOCKER_LOGS_PROXY_URL`
- [ ] Celery beat: `source-expire-daily` + NSFW escalate + `storage-health-sample` + `model-trash-purge-daily`

---

## Сделано в этом срезе

- [x] Node availability timeline §11.16.3
- [x] B2B webhook delivery retries dashboard §14.5.4
- [x] «Продлить хранение» исходников ×3 §9.1.2
- [x] Disk fill forecast / wearout alerts §23.7
- [x] Trash / restore исходников из облака (seller + mobile)

## Сделано ранее

- [x] NSFW SLA dashboard polish §10.8
- [x] Age-gate / date_of_birth UX polish §10.8.3
- [x] Source-expire push scheduler §9.1.2
- [x] Maintenance checklist UI §23.7 (Alembic 028)

---

## Срез: Node timeline / webhooks dashboard / storage extend / forecast / trash (2026-07-14)

### 1. Node availability timeline §11.16.3
- Alembic `029`: таблица `storage_node_events`
- `node_timeline.record_node_heartbeats` — Celery каждые 5 мин из MINIO_HA nodes
- `GET /admin/storage/node-timeline?days=7`
- StoragePage: uptime bar по сегментам online/offline

### 2. B2B webhook delivery retries dashboard §14.5.4
- `company_webhooks.delivery_dashboard`: pending / DLQ / delivered 24h / success rate
- `GET /admin/webhooks/deliveries/dashboard` (+ filter company_id)
- `GET /company/webhooks/deliveries/dashboard`
- Admin `/webhooks` (WebhooksDashboardPage) + seller Team → Webhooks badges

### 3. «Продлить хранение» исходников (×3) §9.1.2
- Поля `models.source_expires_at`, `source_extend_count` (Alembic 029)
- `model_storage.extend_storage` — лимит 3×, +TTL дней, audit log
- `POST /models/{uuid}/extend-storage`; `storage` meta в GET/list
- Seller model card: кнопка + days_left / extends_remaining
- Mobile: «+30 дн.» на экране модели

### 4. Disk fill forecast / wearout alerts §23.7
- Таблица `disk_usage_samples`; Celery sample каждые 5 мин
- `disk_forecast`: линейный days_until_full, SMART wearout snapshot
- `GET /admin/storage/disk-forecast`; интеграция в `storage_alerts.check` (≤30д + wearout)
- StoragePage: forecast card + wearout table

### 5. Trash / restore исходников из облака §3.3 / §9
- `models.trashed_at`; корзина 30 дней, Celery `purge_model_trash` daily
- `GET /models/trash`, `POST trash`, `POST restore-from-trash`
- `POST restore-sources` — presigned ZIP (блок если в корзине)
- Seller: `/models/trash` + кнопки на карточке; Mobile: «В корзину» + restore исходников

### Тесты
- `tests/test_storage_models_ops_slice.py` (4 passed)

---

## Следующие задачи (код)

1. Cloud burn limit hard-stop polish
2. Owner mass extend storage для всех моделей компании §9.1.2
3. Mobile trash list + restore-from-trash экран
4. Webhook delivery detail + retry из admin dashboard
5. Node timeline export CSV
