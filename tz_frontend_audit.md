# Сверка фронтенда с `.claude/ТЗ.txt`

**Дата:** 2026-07-21  
**Источник:** `ТЗ.txt` §3, §11, §19, §20  
**Приложения:** `apps/mobile`, `apps/web-admin`, `apps/web-seller`

Легенда: **DONE** — реализовано · **PARTIAL** — есть, но не полностью по ТЗ · **MISSING** — нет в коде · **OPS** — не код (ключи, QA, prod) · **N/A** — вне scope приложения

---

## Итог

| App | § ТЗ | Код | Комментарий |
|-----|------|-----|-------------|
| mobile | §3 + §19 | **~92%** | Ядро закрыто; polish UX (сетка категорий, ghost controls, live blur) |
| web-admin | §11 | **~88%** | Все разделы есть; детализация дашбордов, support, tax, storage §11.16 |
| web-seller | §20 | **~85%** | Основные потоки; owner-gating, пагинация заказов, team polish |

**Важно:** «100% по ТЗ» — нет. Ранее `front_prod.md` завышал оценку. Этот файл — честная сверка.

---

## apps/mobile — §3 + §19

### DONE (ключевое)

| § | Требование |
|---|------------|
| 3.1 | Guided Dome 12 ракурсов, ручной спуск, гироскоп ±15°, AR-метки |
| 3.3 | Локальное хранение, корзина 30д, автозагрузка GLB |
| 3.4 | Очередь WS, multipart upload, cancel, push+email fallback |
| 3.5.1–3.5.2 | Офлайн-съёмка, черновики 7д, перегенерация |
| 3.5.4 | Чек-лист запрещённых категорий, age-gate 18+ |
| 3.6 | Серверное удаление фона (локальное отключено) |
| 3.7 | Калибровка масштаба (мебель обязательна) |
| 3.8 | Бенчмарк устройства, thermal monitor |
| 3.9 | Пост-съёмка QA, оценка 1–5 |
| 3.11 | Ghost mesh по категории |
| 3.12–3.16 | Share link, corp mode, shoot link, team UI |
| 3.17 | Photographer: скрытие цен |
| 3.18 | Owner: импорт GLB |
| 3.19–3.20 | Corp notifications, регистрация без ФИО |
| 19.1–19.20 | Навигация, онбординг, экраны, i18n ru/en/kk/zh, analytics |

### PARTIAL

| § | Требование | Пробел |
|---|------------|--------|
| 3.1 / 19.6 | Live-проверка резкости до спуска | Blur только в post-review |
| 3.2 | Режим без AR с диаграммой ракурсов | Только gyro fallback |
| 3.5.1 | Авто-предложение отправить после reconnect | Нет явного диалога |
| 3.9 | angle_error coverage | Не реализовано |
| 3.11.3 | Смена силуэта / скрыть ghost | Нет UI |
| 3.11.5 | Зелёный/красный по fit mesh | По gyro/crosshair |
| 19.5 | Сетка иконок категорий | Dropdown FSelect |
| 19.18 | Блок оплаты офлайн | **исправлено** в этой сессии |
| 3.5.4 / 3.12 | Corp policies в съёмке/share | **исправлено** — `company_access_policy.dart` |

### MISSING / OPS

| § | Требование | Статус |
|---|------------|--------|
| 19.21 | Скриншоты store | OPS — placeholder в `docs/store/screenshots/` |
| 1.4 | Prod QA на устройствах | OPS — UNVERIFIED |
| 3.4.3 | Firebase/APNs prod | OPS |

---

## apps/web-admin — §11

### DONE

VPN gate, 2FA, ACL admin/support, все маршруты §11, workers, prices, promocodes, campaigns, push, moderation, legal, tax PDF, B2B companies+export, storage health, watermark verify, user events, ops/DoD, react-window (частично), Grafana.

### PARTIAL (по подразделам)

| § | Пробел |
|---|--------|
| 11.2 | Дашборды: нет zoom, фильтров worker/company на всех графиках; finance без split по тарифам/refund reasons |
| 11.3 | Workers: нет IP, task_id, VRAM, temp в таблице; grace только preset 30с |
| 11.5 | Нет фильтра segmentation logs в LogsPage |
| 11.6 | Users: нет avg rating, last activity; Companies: нет create API key в UI |
| 11.7–11.8 | Campaigns/push: упрощённая сегментация; нет unsubscribe UI |
| 11.9 | Support: нет assignee, attachments, user sidebar, escalate |
| 11.11 | Legal: нет preview, author/comment в версиях |
| 11.13 | Tax: нет quarterly report, send email, tax instructions |
| 11.15 | React Query не везде; WS только dashboard |
| 11.16 | Storage: нет CPU/RAM/Tailscale per node, CH replication lag |

### MISSING

| § | Пробел |
|---|--------|
| 11.8 | UI управления отписками marketing |
| 11.13 | Инструкция по уплате налогов |

---

## apps/web-seller — §20

### DONE (38+ пунктов)

Pop-up login, httpOnly cookies, reCAPTCHA, 2FA, dashboard, balance СБП/ЮKassa, models grid+virtualization, filters, team (invite, roles, policies, webhooks, API keys, shoot links), orders WS, support, settings (avatar, delete account), i18n scaffold, noindex.

### PARTIAL

| § | Пробел |
|---|--------|
| 20.1 | Forgot password — страница, не modal |
| 20.2 | Dashboard: нет owner-метрик, thumbnails |
| 20.4 | Нет фильтра статуса генерации |
| 20.5 | Team table упрощена; audit без IP/date filter |
| 20.6 | Заказы без пагинации (API limit 100) |
| 20.8 | i18n только nav/settings; theme binary не system |
| 20.10 | Role UI частичный | **Team nav owner-only исправлено** |

### MISSING

| § | Пробел |
|---|--------|
| 20.4 | Перегенерация модели из ЛК |
| 20.5 | Block employee / reset password |
| 20.5 | Invite: allowed_categories |
| 20.8 | ИНН в settings; корп. реквизиты Owner |

---

## Вне фронта (но в ТЗ)

| § | Тема | Где |
|---|------|-----|
| 1.4 | DoD KPI (18 метрик) | `back_prod.md`, `/admin/dod-metrics` |
| 4–10 | Backend, worker, storage | `back_prod.md` |
| 12 | ClickHouse prod verify | OPS |
| 22–23 | HA cutover, Tailscale | OPS + `back_prod.md` |

---

## План доработки (код)

### P1 — mobile polish
- [ ] Сетка иконок категорий §19.5
- [ ] Ghost mesh: смена силуэта / скрыть §3.11.3
- [ ] Live blur gate §3.1
- [ ] Диалог «отправить черновик» после reconnect §3.5.1

### P2 — web-admin polish
- [ ] Workers table: IP, task, VRAM, temp §11.3
- [ ] Segmentation log filter §11.5
- [ ] Support ticket sidebar + escalate §11.9
- [ ] Tax quarterly export + instructions §11.13
- [ ] Push unsubscribe list §11.8

### P3 — web-seller polish
- [ ] Orders pagination (backend limit/offset + UI) §20.6
- [ ] Team: block/reset password §20.5
- [ ] Models: regenerate §20.4
- [ ] Invite allowed_categories §20.5
- [ ] Settings: ИНН, corp requisites §20.8

### P4 — OPS (не код)
- [ ] Store screenshots §19.21
- [ ] Device QA checklist `front_prod.md`
- [ ] Prod keys, HA cutover

---

## Команды проверки

```bash
cd apps/mobile && flutter analyze && flutter test
cd apps/web-admin && npm test && npm run build
cd apps/web-seller && npm run build
cd backend/orchestrator && py -m pytest tests/ -q
```

---

## Связанные файлы

| Файл | Назначение |
|------|------------|
| `tz_frontend_audit.md` | Этот файл — сверка с ТЗ |
| `front_prod.md` | Prod gate / OPS |
| `webadminprod.md` | §11 спринты (история) |
| `back_prod.md` | Backend vs ТЗ |
| `ЗАДАЧИ_ПО_ТЗ.md` | Общий трекер (частично устарел) |
