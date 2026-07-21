# Сверка фронтенда с `.claude/ТЗ.txt`

**Дата:** 2026-07-21 (обновлено)  
**Источник:** `ТЗ.txt` §3, §11, §19, §20  

Легенда: **DONE** — реализовано · **OPS** — не код (ключи, QA, prod)

---

## Итог (код)

| App | § ТЗ | Код | Комментарий |
|-----|------|-----|-------------|
| mobile | §3 + §19 | **100%** | Все code gaps закрыты |
| web-admin | §11 | **100%** | Dashboard filters/zoom, campaigns segment preview, RQ |
| web-seller | §20 | **100%** | P3+P5 закрыты ранее |

**OPS** (скриншоты store, device QA, prod Firebase/APNs) — вне кода.

---

## apps/mobile — §3 + §19 — DONE

- §3.2 AngleDiagramOverlay (без AR)
- §3.9 angle_error в quality + storage
- §3.11.5 ghost mesh fit colors
- §19.5 category icon grid
- §3.11.3 ghost hide/shape
- §3.1 live blur gate
- §3.5.1 reconnect draft dialog
- ModelViewerScreen session fix
- category_screen policy filter (`e.value.api`)

---

## apps/web-admin — §11 — DONE

- §11.2 Dashboard: worker filter, company filter (воронка), Brush zoom
- §11.7 Campaigns: segment preview API + UI, React Query
- §11.3–11.16 — см. предыдущие спринты

---

## apps/web-seller — §20 — DONE

- Dashboard thumbnails + owner metrics
- Audit IP/date filters
- Theme auto/light/dark
- Orders pagination, team, models, settings

---

## OPS (не код)

- [ ] Store screenshots §19.21
- [ ] Device QA `front_prod.md`
- [ ] Prod keys, HA cutover, Firebase/APNs
