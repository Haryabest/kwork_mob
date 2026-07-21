# Сверка фронтенда с `.claude/ТЗ.txt`

**Дата:** 2026-07-21 (обновлено)  
**Источник:** `ТЗ.txt` §3, §11, §19, §20  
**Приложения:** `apps/mobile`, `apps/web-admin`, `apps/web-seller`

Легенда: **DONE** — реализовано · **PARTIAL** — есть, но не полностью по ТЗ · **MISSING** — нет в коде · **OPS** — не код (ключи, QA, prod) · **N/A** — вне scope приложения

---

## Итог

| App | § ТЗ | Код | Комментарий |
|-----|------|-----|-------------|
| mobile | §3 + §19 | **~99%** | P1+P5 polish закрыт; остаётся OPS |
| web-admin | §11 | **~97%** | P2+P5 polish; мелочи §11.2 zoom, §11.15 RQ |
| web-seller | §20 | **~98%** | P3+P5 polish; forgot-password — страница есть |

**Важно:** «100% по ТЗ» — нет. OPS (скриншоты, device QA, prod keys) вне кода.

---

## apps/mobile — §3 + §19

### DONE (P1 + P5)

| § | Реализация |
|---|------------|
| 3.2 | `AngleDiagramOverlay` в guided dome без AR |
| 3.9 | `angle_error` в quality analyzer + shoot storage |
| 3.11.5 | Ghost mesh green/red/yellow по fit+alignment |
| 19.5 | Сетка иконок категорий |
| 3.11.3 | Ghost hide/shape |
| 3.1 | Live blur gate |
| 3.5.1 | Диалог черновика после reconnect |

### OPS

| § | Требование | Статус |
|---|------------|--------|
| 19.21 | Скриншоты store | OPS |
| 1.4 | Prod QA на устройствах | OPS |
| 3.4.3 | Firebase/APNs prod | OPS |

---

## apps/web-admin — §11

### DONE (P2 + P5)

| § | Реализация |
|---|------------|
| 11.3 | Workers: IP, task, VRAM, temp |
| 11.5 | Segmentation log filter |
| 11.6 | Users: avg_rating, last_activity; Companies: create API key |
| 11.8 | Push marketing opt-outs |
| 11.9 | Support sidebar + escalate |
| 11.11 | Legal: preview версии, author в истории |
| 11.13 | Tax quarterly + instructions |
| 11.16 | Storage cluster nodes (cluster-health) |

### PARTIAL (низкий приоритет)

| § | Пробел |
|---|--------|
| 11.2 | Dashboard: zoom графиков, фильтр worker/company |
| 11.7 | Campaigns: расширенная сегментация |
| 11.15 | React Query не на всех страницах |

---

## apps/web-seller — §20

### DONE (P3 + P5)

| § | Реализация |
|---|------------|
| 20.1 | Forgot password — `/password/forgot` |
| 20.2 | Dashboard: owner-метрики, thumbnails |
| 20.4 | Model regenerate |
| 20.5 | Team audit: IP/date filter; block/reset password |
| 20.6 | Orders pagination |
| 20.8 | Theme system auto/light/dark; ИНН/requisites |
| 20.5 | Invite allowed_categories |

### OPS

Нет критичных code gaps.

---

## План (осталось)

### OPS (не код)
- [ ] Store screenshots §19.21
- [ ] Device QA checklist `front_prod.md`
- [ ] Prod keys, HA cutover

### P6 — optional polish
- [ ] web-admin dashboard zoom/filters §11.2
- [ ] web-admin React Query migration §11.15
