Итог одной строкой
Оценка
Ядро продукта (съёмка → оплата → очередь → генерация → watermark → кабинет)
~70–80% есть в коде
Production / DoD §1.4 (SLA, нагрузка, 95% генераций, HA)
в основном не подтверждено
Infra §22–23 (Patroni, CH replication, witness, exporters)
~20–40% (есть dev/HA compose, нет prod-пути)
P-loop P37–P44
~5% ТЗ — polish UI/API
§1 — Цели и DoD
Блок	Статус	Комментарий
Бизнес-функции (B2B, 3D, маркетплейсы)
PARTIAL
API и экраны есть, зрелость разная
§1.4 измеримые критерии
UNVERIFIED
Нет prod-бенчмарков: 3/5 мин, 95% успеха, 100 зак/ч, 70% тестов, funnel ≥60%
§2 — Пользователи / auth / B2B
Готово	Частично	Нет
Регистрация, verify, account-type, consents, 2FA Owner, сессии, роли, invite, policies, shoot-link, ЮKassa, право на забвение, forbidden checklist
JWT HS256 (ТЗ RS256), DaData/FNS для юрлиц, авто-revoke сессий при login, PII/Vault
Маркетинговая сегментация профиля (пол, банк карты)
§3–§5 — Mobile / оркестратор / worker
§	Готово	Пробелы
§3 Mobile
Guided Dome, gyro, ghost mesh, quality review, queue WS, push, corp mode, guest shoot, trash, calibration, team (базово)
Resumable multipart upload, offline mode, полная автоверификация WB/Ozon
§4 Orchestrator
Redis+PG queue, Redlock, grace 25s, heartbeat, NSFW, promocodes, company API, shoot links, push fallback
ClickHouse end-to-end, already_processed idempotency worker, RS256 gateway
§5 Worker
TRELLIS, DeepLab+SAM, retopo, PBR, Draco, DWT+HMAC, thermal shutdown, upsells, USDZ
Category-based polycount, per-marketplace 15MB, watermark verify UI
§6–§11 — Pipeline / маркетплейсы / финансы / storage / security / admin
§	Сильные стороны	Главные дыры
§6
Полный pipeline в worker/scripts/
WebP/Ozon-WB ветки сжатия, quality gate по ТЗ
§7
Download, publish/mark, HTML-verify, бонусы, funnel
Напоминания 3/14 дн, seller ZIP export, full API auto-publish
§8
ЮKassa, тарифы, промокоды, corp balance, tax PDF/CSV
AR-автотариф, B2B персональные цены, refund после 3 fails (счётчик)
§9
MinIO, presigned, extend storage, source expire
HA failover, pg_partman, WAL-G, dedicated B2B buckets
§10
Rate limit, NSFW, blacklist, age gate, access_log, E2E photos
reCAPTCHA, WAF, 5 URL/модель/час
§11
web-admin: workers, users, campaigns, push, NSFW, tax, storage
Grafana iframe, watermark UI, CSV import companies
§12–§23 — Analytics / ERP / web §20 / mobile §19 / HA
§	Статус
§12–13 Analytics/CH
PARTIAL — MV в infra/clickhouse/init.sql, app sync; нет TTL, ReplicatedMergeTree, полного user_events, fluentd
§14 ERP/webhooks
DONE в коде — bulk orders, HMAC webhooks, DLQ replay
§15 Docs
PARTIAL — OpenAPI есть; user/B2B guides тонкие; нет templates/{lang}/
§16 i18n
Mobile ru/en/kk/zh DONE; web-seller i18n MISSING
§19 Mobile UX
~85% экранов; offline MISSING
§20 Web seller
Dashboard, balance, models, team, orders, settings есть; grid/virtualization, httpOnly cookies, captcha, avatar, delete account UI — нет
§21 noindex
DONE
§22–23 HA/monitoring
PARTIAL — docker-compose.ha.yml, Patroni, Grafana JSON; default dev = single node; CH не в HA; witness/exporters нет