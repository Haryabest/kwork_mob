# План разработки до полного Production по ТЗ

Источник требований: `ТЗ.txt` (§1–§23).  
Шпаргалка по коду: `.claude/CLAUDE.MD`.  
Цель: **весь продукт в production**, без упрощений «MVP-only» — все пункты ТЗ закрыты.

---

## 0. Текущее состояние (старт плана)

| Компонент | Статус |
|-----------|--------|
| Monorepo, docker-compose, infra-заготовки | ✅ |
| Auth API (register/verify/login/JWT/refresh/logout/reset) | ✅ |
| Миграция `001_initial_schema` | ✅ |
| Staff Panel UI (Mantine, роли admin/support) | 🟡 каркас |
| Web Seller UI (Mantine) | 🟡 каркас |
| Mobile screens | 🟡 Flutter scaffold (auth/onboarding) |
| Worker agent + scripts | 🟡 заглушки |
| Orders / Queue / MinIO / YooKassa / NSFW / B2B | ❌ 501 |
| Production HA (Tailscale, MinIO cluster, backups) | ❌ |

**Правило порядка:** Backend API → Worker pipeline → Web Seller → Mobile → Staff Panel → Infra HA → Soft-features → Docs/QA → Go-live.

---

## Критерии успеха (Definition of Done всего проекта) — §1.4

- [ ] Генерация ≤ 3 мин (домашний ПК) / ≤ 5 мин (облако)
- [ ] Успешные генерации ≥ 95%; отмены ≤ 5%
- [ ] Конверсия оплата→генерация→скачивание→верификация публикации ≥ 60%
- [ ] Оценки 4–5 ≥ 80%
- [ ] Хранение MinIO < 1% выручки
- [ ] Пик 100 задач/час без деградации
- [ ] Алерт ≤ 30 сек
- [ ] Налоговый модуль работает (3 режима)
- [ ] Кампанию можно создать и запустить за ≤ 5 мин
- [ ] Ответ поддержки (раб. часы) ≤ 2 ч
- [ ] NSFW: ложные < 1%; возврат при ложных; запрещённые категории — заказ не создаётся
- [ ] 100% моделей с DWT-DCT только в diffuse, устойчивость JPEG/WebP 80%
- [ ] 50+ фотографов на юрлицо без деградации
- [ ] Shoot-link ≤ 1 сек
- [ ] Grace period ≥ 25 сек; Redlock — нет двойной обработки
- [ ] Unit-тесты ≥ 70% критических модулей
- [ ] Нагрузка: 100 одновременных заказов
- [ ] Документация RU + OpenAPI + deploy + user + B2B

---

# PHASE A — Фундамент Backend (недели 1–3)

> Без этого нельзя ни оплату, ни воркер, ни клиенты.

## A1. Домен пользователей и согласия — §2, §10.9

- [ ] Выбор типа аккаунта после verify: физлицо / юрлицо (`pending_type` → `active_*`)
- [ ] Опциональные ФИО/ИНН; пропуск ФИО при оплате (§2.10)
- [ ] Юрлицо: реквизиты, создание `companies`, роль Owner
- [ ] Юридические документы: оферта, ПДн, пользовательское соглашение
- [ ] Версионирование документов + фиксация согласий при регистрации/обновлении
- [ ] Право на забвение: soft-delete + анонимизация финансов за 5 лет
- [ ] Маркетинговые атрибуты профиля (§2.6, §2.13)
- [ ] 2FA TOTP для Owner компании (§2.4 / §20)
- [ ] Управление сессиями (список / revoke)

**Код:** `api/v1/auth.py`, `user.py`, новые `legal.py`, таблицы `legal_documents`, `user_consents`, `sessions`.

## A2. MinIO и загрузка файлов — §9, §10.2

- [ ] Init buckets: photos, models, backups, logs
- [ ] Presigned upload/download (TTL 30 мин / 1 ч)
- [ ] SHA-256 контроль целостности ZIP
- [ ] UUID-имена объектов (§10.1)
- [ ] Lifecycle: исходники 30 дней
- [ ] CORS + Referer check для скачивания (§10.3)

**Код:** `services/minio.py`, эндпоинты upload, `scripts/init_minio.py`.

## A3. Очередь и оркестрация — §4.2, §4.4

- [ ] Dual-write: Redis List + `task_queue` PostgreSQL
- [ ] Sync каждую минуту (Celery beat)
- [ ] Веса воркеров (−1…+1), выбор idle
- [ ] Heartbeat 5с, offline 20с, grace 25–30с
- [ ] Redlock `SET task:{id} NX EX 60`
- [ ] Эскалация: 30 мин в очереди → priority; 20 мин processing → stop+requeue; 3 эскалации → refund
- [ ] EWT через WebSocket `/ws/queue/{user_id}`
- [ ] Контрактная валидация воркера при `ready` (§4.1.2)
- [ ] Резервный канал wss без Tailscale (§4.3)
- [ ] `task_conflicts` логирование
- [ ] Опциональная приоритезация по тарифу (§4.5)

**Код:** `services/queue.py`, `websocket/routes.py`, `tasks/celery_app.py`.

## A4. Заказы (Orders) — §4.8.1, §3.10

- [ ] `POST /orders/create` с идемпотентностью UUID
- [ ] Чек-лист запрещённых категорий → 400, заказ не создаётся
- [ ] 18+ → birth_date
- [ ] Привязка company_id, проверка лимитов роли
- [ ] Статусы, cancel, list с фильтрами
- [ ] Защита от двойной оплаты

**Код:** `api/v1/orders.py`, `schemas/orders.py`.

## A5. Rate limiting и security basics — §10.4, §4.1.3

- [ ] Redis sliding window: 100/min user, 1000/min IP
- [ ] JWT scopes для staff (`admin` / `support_agent`)
- [ ] API-ключи B2B (создание позже в B2B-фазе) — заложить модель
- [ ] Шифрование чувствительных полей at-rest (реквизиты)

---

# PHASE B — Оплата и финансы (недели 3–5) — §8

## B1. Тарифы и ценообразование

- [ ] Тарифы small 2990 / large 5990 (конфиг в БД + admin)
- [ ] Автоопределение тарифа по AR-данным (§8.3)
- [ ] Апсейл-опции: real_scale, video_360, virtual_tryon, hole_filling (§17)
- [ ] История изменения цен
- [ ] Индивидуальные цены для B2B

## B2. ЮKassa

- [ ] Создание платежа, идемпотентность
- [ ] Webhook `/webhooks/yookassa`
- [ ] Возвраты (полный при ложном NSFW)
- [ ] Фискализация чеков через ЮKassa
- [ ] Только РФ; без Apple/Google Pay
- [ ] СБП QR для пополнения баланса (§8.12)

## B3. Баланс и корпоративные транзакции

- [ ] Личный/корпоративный баланс
- [ ] Списание с баланса при заказе
- [ ] История транзакций, экспорт
- [ ] Промокоды: validate/apply, лимиты, срок, hash кода (§8.5)

## B4. Налоговый модуль владельца сервиса — §8.6, §11.10

- [ ] Переключатель Самозанятый / ИП / ООО
- [ ] Реквизиты, счета PDF, акты PDF
- [ ] Выгрузка Excel/PDF за период
- [ ] **Без** прямой интеграции «Мой Налог»

**Код:** `services/yookassa.py`, `api/v1/tax.py`, `promocodes.py`.

---

# PHASE C — Worker + пайплайн 3D (недели 4–8) — §5, §6

## C1. Инфраструктура воркера

- [ ] Docker CUDA image, TRELLIS + веса
- [ ] `worker_agent.py`: WS connect, ready, heartbeat, metrics (pynvml)
- [ ] Redlock перед start_task
- [ ] Checkpoint каждые 30с / по этапам
- [ ] Graceful shutdown при T≥85°C
- [ ] Overheating → статус + освобождение

## C2. Пайплайн постобработки (строго по порядку)

1. [ ] Download ZIP из MinIO
2. [ ] `remove_background.py` — DeepLabV3+ → SAM fallback (§6.1.1)
3. [ ] NSFW check до генерации (§10.8) — оркестратор или воркер по решению архитектуры; результат в `nsfw_blocks`
4. [ ] `trellis_generate.py` — multi-view 12 фото
5. [ ] `retopology.py`
6. [ ] `bake_pbr.py` — normal/roughness/metallic **без watermark**
7. [ ] `apply_watermark.py` — DWT-DCT **только diffuse** + HMAC в extras
8. [ ] `compress_draco.py` — ≤15 МБ
9. [ ] `validate_glb.py` + опционально USDZ
10. [ ] Upload model + ZIP backup → MinIO
11. [ ] `task_completed` / `task_failed` → оркестратор

## C3. Апсейлы в пайплайне — §17, §6.9

- [ ] real_scale, hole_filling, video_360, virtual_tryon (как отдельные шаги/флаги)

## C4. Жёсткие запреты

- [ ] `compute_fid.py` только в `dev-tools/`, не в Docker, не в панели
- [ ] Не трогать normal/roughness/metallic watermark-ом

## C5. Импорт готовых моделей — §6.10

- [ ] `POST /models/import` только Owner компании

## C6. Валидация водяных знаков в admin — §5.12, §11

- [ ] Инструмент проверки DWT только diffuse

**DoD фазы C:** end-to-end заказ → 12 фото → .glb в MinIO → download URL.

---

# PHASE D — Модерация, поддержка, маркетинг API (недели 6–9)

## D1. NSFW и чёрные списки — §10.8, §13

- [ ] Детектор NSFW перед генерацией
- [ ] Политика: запрещённые категории — нет заказа; иначе refund + temp block + ручная проверка 24ч
- [ ] Постоянный бан при подтверждённом нарушении
- [ ] Чёрный список слов/брендов
- [ ] Age gate для 18+
- [ ] Admin API: reports, verify, block
- [ ] Анти-атака: >3 подтверждённых за 24ч → доп. санкции

## D2. Поддержка + Ollama — §4.8.11, §11.9

- [ ] Тикеты: create/list/reply/status
- [ ] История сообщений (год)
- [ ] «Предложить ответ ИИ» → Ollama
- [ ] FAQ CRUD + версии + publish
- [ ] Вложения (скриншоты ≤5 МБ)

## D3. Маркетинг — §1.2, §11.7–11.8

- [ ] Кампании: шаблоны, сегменты, start/stop, stats/ROI
- [ ] Массовые push + email (с согласием)
- [ ] Сегментация: пол, регион, банк, активность, тариф
- [ ] Отписка от маркетинга
- [ ] Реферальные / «каждая N-я» / таймерные скидки

## D4. Оценка качества моделей — §3.9.3

- [ ] `POST /models/{uuid}/rate` (1–5 + причины)
- [ ] Агрегаты в ClickHouse / admin dashboard

---

# PHASE E — B2B / корпоративный режим (недели 7–10) — §2.5, §4.8

## E1. Команда и роли

- [ ] Invite по email, роли Owner/Manager/Photographer/Viewer
- [ ] Кастомные роли + permissions JSON
- [ ] Лимиты: max_concurrent_orders, monthly_spending, allowed_categories
- [ ] Глобальные политики компании
- [ ] Audit log + CSV export
- [ ] Revoke sessions сотрудника
- [ ] Переключатель Личный / Корпоративный

## E2. Съёмка по ссылке — §2.11, §3.15

- [ ] `POST /company/shoot_link` ≤ 1 сек
- [ ] Публичный `GET/POST /shoot/{token}` — только upload 12 фото, без AR
- [ ] Web page: install app OR gallery upload
- [ ] QR-код в seller UI

## E3. API-ключи и ERP — §8.8, §4.8.8, §14

- [ ] CRUD API keys + scopes
- [ ] `POST /company/orders/bulk` (до 100)
- [ ] Corporate webhooks: model.generated, order.created, shoot_link.uploaded, order.cancelled
- [ ] Документация для 1С / МойСклад

---

# PHASE F — Публикация на маркетплейсах (недели 9–11) — §7

- [ ] Download .glb (Ozon) / .usdz (WB)
- [ ] Инструкции «Как опубликовать»
- [ ] Mark published + URL для автоверификации (парсинг карточки)
- [ ] Бонусы за публикацию
- [ ] Публичный web viewer с watermark (§7.8, §3.12) — `/viewer/[uuid]`
- [ ] ZIP export fallback
- [ ] Аналитика публикаций (admin + corporate)
- [ ] Права Photographer на публикацию (настройка Owner)

---

# PHASE G — Web Seller полный (§20) (недели 8–12)

Параллельно с Mobile после стабильного API auth+orders+models+balance.

## G1. Auth UX

- [ ] Pop-up login на `/` (§20.1)
- [ ] Register / verify / reset — привязка к API
- [ ] noindex: X-Robots-Tag, robots.txt, meta (§21)

## G2. Кабинет

- [ ] Модели (фильтры, download, rate, share, publish link)
- [ ] Заказы (статус WS)
- [ ] Баланс + СБП QR + ЮKassa
- [ ] История транзакций
- [ ] Поддержка / FAQ
- [ ] Профиль, 2FA, сессии, тема, язык
- [ ] Удаление аккаунта

## G3. Owner-разделы

- [ ] Команда, роли, лимиты, invite
- [ ] API keys
- [ ] Политики, аудит, сессии сотрудников
- [ ] Shoot links + QR

## G4. Адаптив и perf — §20.9

- [ ] Desktop/tablet/mobile
- [ ] React Query cache, virtualization, pagination
- [ ] FCP < 1.5s, TTI < 3s

---

# PHASE H — Mobile полный Flutter (§3, §16, §19) (недели 8–14)

> Стек: **Flutter / Dart** (не React Native / Expo).

## H1. База приложения

- [ ] Navigation Tab Bar + FAB
- [ ] Тема цветов WB/Ozon (§19.1)
- [ ] Onboarding 4 экрана
- [ ] Auth / verify / type select
- [ ] Push (FCM/APNs) + fallback SMS/email
- [ ] Offline drafts, local storage manager

## H2. Съёмка

- [ ] Category + Ghost Mesh + forbidden checklist
- [ ] AR Guided Dome 12 views, manual shutter
- [ ] Gyro ±15°, centering crosshair
- [ ] Visual AR markers (не автоспуск)
- [ ] Scale calibration (обязательна для мебели)
- [ ] Device benchmark (только JPEG compression mode)
- [ ] Post-shoot assistant: reshoot angles
- [ ] Upload ZIP resumable + integrity

## H3. Оплата → очередь → результат

- [ ] Payment + promocode + corporate balance
- [ ] Queue UI + cancel + WS status
- [ ] Model viewer 3D + AR preview
- [ ] Quality feedback 1–5
- [ ] Publish flow
- [ ] FAQ (неяркая кнопка)

## H4. Корпоратив в приложении

- [ ] Switch Personal / Company
- [ ] Hide prices for Photographer
- [ ] Team screen (Owner/Manager)
- [ ] Shoot-link / QR

## H5. QA устройств

- [ ] BrowserStack + реальные устройства
- [ ] iOS + Android store builds (без Apple/Google Pay)

---

# PHASE I — Staff Panel полный (§11) (недели 10–14)

Единый `web-admin`: роль из JWT.

## I1. Доступ

- [x] VPN WireGuard/Tailscale CIDR (`ADMIN_VPN_REQUIRED`, `/staff/vpn-status`)
- [x] 2FA TOTP staff (`/staff/login` → setup/verify, web-admin UI)
- [x] JWT session 8ч, idle timeout 30 мин

## I2. Дашборды (ClickHouse)

- [ ] Ops: заказы, EWT, GPU load, success rate
- [ ] Finance: выручка, возвраты, NSFW holds, эквайринг
- [ ] B2B: топ компаний, API usage
- [ ] Quality: ratings distribution
- [ ] Segmentation metrics DeepLab/SAM + alerts >15% fail/device

## I3. Управление

- [ ] Workers: weight, maintenance, grace period, logs, cloud start/stop
- [ ] Prices / upsells / quality thresholds / retention
- [ ] Users + delete (right to be forgotten)
- [ ] B2B companies
- [ ] Promocodes, campaigns, push
- [ ] Moderation NSFW 24h
- [ ] Support tickets + Ollama (support_agent видит только это + FAQ)
- [ ] FAQ editor
- [ ] Tax module UI
- [ ] Legal docs versions
- [ ] Alerts Telegram/email
- [ ] Logs export
- [ ] Storage cluster health (§23)
- [ ] 3D viewer + watermark verify tool
- [ ] TRELLIS version rollout / rollback (§18)

---

# PHASE J — Метрики, логи, ошибки (§12, §13) (недели 11–13)

- [ ] Prometheus raw metrics (2 недели)
- [ ] ClickHouse агрегаты minute/hour/day
- [ ] user_events + corporate events
- [ ] alert_log, пороги настраиваемые
- [ ] Segmentation stats
- [ ] Queue Redis/PG health indicator
- [ ] Error taxonomy + user-facing messages
- [ ] Quality gates перед выдачей модели (§6.12)
- [ ] Export логов/метрик

---

# PHASE K — Инфраструктура Production HA (§5 задачи, §9, §22, §23) (недели 12–16)

## K1. Storage HA

- [ ] MinIO 2 узла, репликация
- [ ] Lifecycle policies
- [ ] SMART / node health в admin
- [ ] Восстановление после сбоя узла (§9.6)

## K2. Data layer

- [ ] PostgreSQL: backup каждые 6ч → MinIO, retention 365 дней
- [ ] Redis AOF + Sentinel / replica
- [ ] ClickHouse prod sizing

## K3. Networking

- [ ] Tailscale: orchestrator ↔ workers ↔ storage
- [ ] Fallback WSS публичный
- [ ] TLS everywhere, Nginx
- [ ] WireGuard только для Staff Panel

## K4. Observability

- [ ] Grafana dashboards
- [ ] Alert → Telegram/email ≤ 30 сек
- [ ] Semi-auto cloud workers: alert queue>20 или busy>5 мин

## K5. Secrets & config

- [ ] Prod secrets (не в git)
- [ ] Env per environment
- [ ] Blue/green или rolling для orchestrator

---

# PHASE L — Интеграции внешние (§14) (недели 13–15)

- [ ] Email SMTP production
- [ ] SMS provider fallback
- [ ] FCM + APNs
- [ ] Ollama (локальный сервер) для support
- [ ] YooKassa prod shop
- [ ] ERP webhooks docs + sandbox
- [ ] (Опционально) WB/Ozon API расширенная публикация (§7.6)

---

# PHASE M — Локализация (§16) (недели 14–15)

- [ ] i18n: RU (default), EN, KK, ZH
- [ ] Все клиенты (mobile, seller, staff) + email/push шаблоны
- [ ] Форматы дат/валют ₽

---

# PHASE N — TRELLIS versioning (§18) (недели 15–16)

- [ ] Версии воркеров в панели
- [ ] Rolling update / canary
- [ ] Rollback
- [ ] Совместимость моделей / миграция

---

# PHASE O — Документация (§15) (недели 15–17)

- [ ] Техдок RU (архитектура, схемы)
- [ ] OpenAPI актуальный
- [ ] Deploy runbook (чек-лист ~50 пунктов)
- [ ] User guide селлера (PDF)
- [ ] B2B guide (роли, API, webhooks)
- [ ] Support playbook
- [ ] Комментарии кода на русском (критичные модули)

---

# PHASE P — Тестирование и приёмка (§1.3 задача 7, §1.4) (недели 16–18)

## P1. Автотесты

- [ ] Unit ≥ 70% критических: auth, queue, redlock, payments, NSFW policy, watermark
- [ ] Integration: order E2E mock worker
- [ ] Contract tests worker↔orchestrator

## P2. Сценарии NSFW

- [ ] Forbidden checklist → no order
- [ ] False positive → refund + unlock
- [ ] Real violation → permanent ban

## P3. Нагрузка

- [ ] 100 одновременных заказов
- [ ] 100 задач/час sustained
- [ ] 50+ photographers на company

## P4. Клиенты

- [ ] Mobile BrowserStack + real devices
- [ ] Seller adaptive + noindex audit
- [ ] Staff VPN+2FA smoke

## P5. Watermark / quality

- [ ] DWT только diffuse; normal/roughness/metallic intact
- [ ] JPEG/WebP 80% robustness
- [ ] GLB ≤ 15 МБ marketplace requirements

## P6. Marketing

- [ ] Promo + campaign + push E2E
- [ ] Campaign create→launch ≤ 5 мин

---

# PHASE Q — Soft launch → Production Go-live (недели 18–20)

## Q1. Pre-prod checklist

- [ ] Все секреты ротированы
- [ ] Backups проверены restore-тестом
- [ ] Monitoring + on-call алерты
- [ ] Legal docs актуальны
- [ ] Rate limits / CORS prod domains
- [ ] MinIO lifecycle ON
- [ ] Grace period default 25
- [ ] FID отсутствует в prod image

## Q2. Soft launch

- [ ] Ограниченный набор селлеров
- [ ] 1–2 домашних воркера + процедура cloud scale
- [ ] Ежедневный разбор NSFW queue (<24ч)
- [ ] Сбор feedback ≥80% оценок 4–5

## Q3. Public production

- [ ] DNS, TLS, seller domain, staff VPN-only
- [ ] App Store / Google Play
- [ ] Support SLA 2ч
- [ ] Post-launch: метрики §1.4 на дашборде

---

# Карта «раздел ТЗ → фаза»

| ТЗ | Фаза |
|----|------|
| §1 Цели / критерии | DoD + Phase P/Q |
| §2 Пользователи / роли | A1, E |
| §3 Mobile функционал | H |
| §4 Сервер / API | A, D, E |
| §5 Worker | C |
| §6 Генерация / post | C |
| §7 Публикация | F |
| §8 Оплата / налоги | B |
| §9 Хранение | A2, K1 |
| §10 Безопасность | A5, D1, K, G1 |
| §11 Staff panel | I |
| §12 Логи / метрики | J |
| §13 Ошибки / качество | C, D1, J |
| §14 Интеграции | L |
| §15 Документация | O |
| §16 Локализация | M |
| §17 Апсейлы | B1, C3 |
| §18 TRELLIS versions | N, I3 |
| §19 Mobile UI | H |
| §20 Seller web | G |
| §21 Web security / noindex | G1 |
| §22 Storage HA | K1 |
| §23 Storage monitoring | K4, I3 |

---

# Рекомендуемый порядок спринтов (кратко)

1. **S1–S2:** A1–A5 (users, minio, queue, orders, security)
2. **S3–S4:** B (YooKassa + balance + promocodes)
3. **S5–S8:** C (worker E2E glb)
4. **S6–S9:** D (NSFW, support, marketing API) ∥ E (B2B)
5. **S8–S12:** G seller + H mobile (после стабильного API)
6. **S9–S11:** F publish
7. **S10–S14:** I staff panel + J metrics
8. **S12–S16:** K HA infra
9. **S13–S17:** L, M, N, O
10. **S16–S18:** P QA
11. **S18–S20:** Q go-live

*Оценка ~18–20 недель для полной команды (backend + worker/ML + mobile + web). Один разработчик — пропорционально дольше; критический путь: **Queue → Worker TRELLIS → Payments → Mobile shoot**.*

---

# Правила исполнения для AI / разработчиков

1. Читать ТЗ точечно (`grep` / offset), не целиком.
2. Не включать FID в production.
3. Watermark только diffuse.
4. Запрещённые категории = заказ не создаётся.
5. Staff = один сайт (`web-admin`), роли JWT.
6. Seller ≠ Staff.
7. Минимальный diff; не коммитить без просьбы.
8. После каждой фазы — чеклист DoD фазы + регрессия auth/orders.
9. Обновлять этот файл: отмечать `[x]` по мере закрытия пунктов.
10. Обновлять `.claude/CLAUDE.MD` при смене структуры/статуса.

---

# Ближайший следующий шаг (сейчас)

**PHASE A2 + A3 + A4:** MinIO upload → dual-write queue → `orders/create` → WS статус (ещё без реального TRELLIS — можно mock-worker, возвращающий fake .glb).

После mock E2E — PHASE C (реальный пайплайн).
