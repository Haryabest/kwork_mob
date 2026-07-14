# Soft Launch Checklist — 3DVektor / KWork Mob

Чеклист перед ограниченным запуском (soft launch). Источник: ТЗ §1 KPI, §11–§14, §17.

## 0. Инфра и секреты

- [ ] `ENVIRONMENT=production`, смена всех `change-me*` ключей
- [ ] `PD_ENCRYPTION_KEY` или Vault (`VAULT_ADDR` + `VAULT_TOKEN`)
- [ ] ЮKassa shopId/secret + webhook `/api/v1/webhooks/yookassa`
- [ ] SMTP / FCM prod credentials
- [ ] TLS 1.3 на API + seller + admin
- [ ] `ADMIN_VPN_REQUIRED=true`, 2FA staff включён
- [ ] Alembic `upgrade head` (включая `021_support_attachments`)

## 1. Хранилище и БД

- [ ] MinIO buckets: `photos`, `models`, `backups` + lifecycle
- [ ] PostgreSQL backup → MinIO
- [ ] Redis AOF / Sentinel (если HA)
- [ ] ClickHouse `service_logs` + Grafana datasources

## 2. GPU / воркер

- [ ] Worker image cu128 + TRELLIS.2 веса
- [ ] `TRELLIS_ALLOW_STUB_FALLBACK=0`
- [ ] E2E на целевом GPU: `run_e2e_home.ps1` exit 0 (бюджет ≤180 local / ≤300 cloud)
- [ ] Burn ₽/ч облака: лимиты autoscaling в admin `/workers`

## 3. Платежи и налоги

- [ ] Режим владельца (НПД / ИП / ООО) в `/admin/tax`
- [ ] Тестовый платёж + фискальный чек ЮKassa
- [ ] Возврат (refund) на failed / NSFW

## 4. Продукт B2C / B2B

- [ ] Регистрация → email verify → заказ → генерация → download
- [ ] Публикация: ссылка WB/Ozon + verify Celery
- [ ] Company: invite, roles, policies, webhooks DLQ
- [ ] E2E photo encryption (опционально) на тестовой компании

## 5. Поддержка и compliance

- [ ] FAQ опубликован, support ticket create/reply
- [ ] NSFW moderation queue
- [ ] Право на забвение: заявка + SLA 30 дней
- [ ] Юр. документы версии + consent

## 6. Мобильное приложение

- [ ] Onboarding + auth + Guided Dome (12 ракурсов)
- [ ] Thermal: ≥40°C FPS 15, >45°C warning
- [ ] Push FCM register + deep link на заказ
- [ ] Публикация / «Я опубликовал» / ссылка

## 7. Soft launch gate

- [ ] KPI мониторинг: queue EWT, gen→verify funnel ≥ цель
- [ ] Алерты Telegram (воркер down, disk, NSFW spike)
- [ ] Burn cloud ≤ дневной бюджет
- [ ] Rollback plan: stub worker / feature flags

**Ответственный:** ________  **Дата soft launch:** ________
