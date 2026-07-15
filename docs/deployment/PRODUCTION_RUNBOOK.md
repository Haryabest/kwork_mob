# Production Runbook (§15)

Единый пошаговый сценарий вывода платформы 3D-моделей в production.
Разделы: подготовка → инфраструктура → бэкенд → воркеры → клиенты → наблюдаемость → приёмка → эксплуатация.

Связанные документы: [SOFT_LAUNCH](./SOFT_LAUNCH.md), [HA](./HA.md),
[E2E_SMOKE_CHECKS](./E2E_SMOKE_CHECKS.md), [GPU_E2E_RTX5070](./GPU_E2E_RTX5070.md),
[API](../api/README.md), [B2B](../b2b/README.md), [Support Playbook](../support/PLAYBOOK.md).

## A. Подготовка (1–8)

1. Завести домены: `api.*`, `seller.*`, `admin.*`, `grafana.*`; выпустить TLS-сертификаты.
2. Создать production `.env` из [`.env.example`](../../.env.example); заполнить секреты (не коммитить).
3. Сгенерировать сильные секреты: `SECRET_KEY`, `JWT_SECRET`, `WATERMARK_HMAC_SECRET`, `PD_ENCRYPTION_KEY` (base64url, 32 байта).
4. Настроить YooKassa: `YOOKASSA_SHOP_ID`, `YOOKASSA_SECRET_KEY`, включить `YOOKASSA_WEBHOOK_IP_CHECK`.
5. Настроить FCM: `FCM_SERVICE_ACCOUNT_JSON`, `FCM_PROJECT_ID` (см. §3.4.3).
6. Настроить SMTP: `SMTP_HOST/PORT/USER/PASSWORD/FROM` (email-fallback и алерты).
7. Настроить облачный GPU-провайдер: `CLOUD_PROVIDER`, токены, `INTELION_FLAVOR_ID/OS_ID`.
8. Настроить Telegram-алерты: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

## B. Инфраструктура данных (9–18)

9. Развернуть PostgreSQL (Patroni HA — см. [HA](./HA.md)); создать БД и роль.
10. Развернуть Redis (Sentinel: `REDIS_SENTINELS`, `REDIS_SENTINEL_MASTER`).
11. Развернуть MinIO; создать бакеты `photos`, `models`, `backups`; включить SSE (`MINIO_SSE_MODE`).
12. Развернуть ClickHouse; создать БД `kwork_metrics`; задать `CLICKHOUSE_PASSWORD`.
13. Настроить сетевые доступы/файрвол; staff-панель — только через VPN (`ADMIN_VPN_CIDRS`).
14. Прогнать миграции БД: `alembic upgrade head`.
15. Засеять staff-аккаунты: `python scripts/seed_staff.py`.
16. Засеять тарифы/промо/справочники (по §11).
17. Проверить бэкапы PG + MinIO (расписание, тестовое восстановление — §23.7).
18. Экспортировать/проверить API-контракт: `python scripts/export_openapi.py --check`.

## C. Бэкенд-оркестратор (19–26)

19. Собрать образ оркестратора; задеплоить за reverse-proxy (TLS, gzip, CORS из `CORS_ORIGINS`).
20. Запустить API (`uvicorn app.main:app`), health: `GET /api/health` → 200.
21. Запустить Celery worker и Celery beat (расписания §12/§23).
22. Проверить, что beat-задачи зарегистрированы (в т.ч. `push-email-fallback-every-minute`).
23. Настроить `.well-known` для Universal Links / App Links (`APPLE_TEAM_ID`, `ANDROID_SHA256_FINGERPRINTS`).
24. Прописать YooKassa webhook URL в личном кабинете; проверить подпись/IP-allowlist.
25. Проверить rate-limit и лимиты API-ключей (`API_KEY_DEFAULT_*`).
26. Smoke API: register → verify → login → refresh → logout (см. integration-тесты).

## D. Воркеры генерации (27–33)

27. Собрать GPU-образ воркера (CUDA), выложить в реестр (`WORKER_DOCKER_IMAGE`).
28. Прокинуть воркеру секреты, включая `WATERMARK_HMAC_SECRET` (совпадает с бэкендом).
29. Поднять воркер на облачном GPU; проверить CUDA-preflight и heartbeat в очереди.
30. Прогнать e2e-приёмку: `python worker/scripts/e2e_trellis_acceptance.py` (реальные multi-view).
31. Проверить пайплайн: bg-removal → TRELLIS → retopo → PBR → watermark → validate → Draco.
32. Проверить quality-gate: `validate_glb.py` парсит геометрию (faces/vertices), а не только размер.
33. Проверить апсейлы: `real_scale` физически масштабирует меш; `hole_filling`, `video_360`, `virtual_tryon`.

## E. Клиенты (34–39)

34. Web-seller (Next.js): сборка `next build`, задеплоить; проверить live-статусы заказов.
35. Web-admin (Vite): `tsc && vite build`, задеплоить за VPN; проверить дашборды/тёмную тему.
36. Mobile: `flutter gen-l10n`, сборка Android (AAB) и iOS (IPA); проверить 4 языка (ru/en/kk/zh).
37. Проверить push-flow: доставка → deep link на заказ → email-fallback через 5 мин.
38. Проверить shoot-link: QR в web-seller открывает съёмку без регистрации.
39. Проверить оплату из клиента: создание заказа → YooKassa → возврат/квитанция.

## F. Наблюдаемость (40–44)

40. Поднять Grafana (docker-compose): `GF_SECURITY_ADMIN_*`, плагин ClickHouse, mount дашбордов.
41. Проверить datasource ClickHouse (`CLICKHOUSE_PASSWORD` через env).
42. Проверить дашборды: очередь, GPU-температуры, конверсия публикаций, платежи.
43. Проверить алерты: очередь, all-busy, worker-offline, GPU thermal, YooKassa error-streak.
44. Проверить бюджет облака: `CLOUD_MONTHLY_BUDGET_RUB`, burn-alert.

## G. Приёмка и запуск (45–50)

45. Прогнать CI зелёным (backend pytest, web tsc+vitest, flutter analyze).
46. Прогнать [E2E_SMOKE_CHECKS](./E2E_SMOKE_CHECKS.md) на production-стенде.
47. Проверить сценарии возвратов: NSFW block → refund → unblock; эскалация → refund.
48. Включить [SOFT_LAUNCH](./SOFT_LAUNCH.md) (ограниченный трафик), мониторить 24–48 ч.
49. Подготовить дежурство и [Support Playbook](../support/PLAYBOOK.md); проверить SLA первого ответа ≤ 2 ч.
50. Снять soft-launch лимиты, объявить GA; зафиксировать версию API (`openapi.json`) в релизе.

## Откат (rollback)

- Бэкенд/воркер: вернуть предыдущий тег образа; при несовместимой миграции — `alembic downgrade`.
- Клиенты: откат предыдущей сборки; mobile — через поэтапную раскатку в сторах.
- Данные: восстановление из проверенного бэкапа PG/MinIO (см. §23.7).
