# Web-admin prod readiness (по `.claude/ТЗ.txt` §11)

**Область:** `apps/web-admin/`  
**Обновлено:** 2026-07-21

## Итог

| Метрика | Было | Цель |
|---------|------|------|
| UI vs ТЗ §11 | ~78% | 100% |
| Prod-ready | ~65% | 100% |

**Вердикт:** каркас панели зрелый (30+ маршрутов); пробелы — user_events, DoD/HA ops, queue health, доработки push/legal/tax.

---

## Статус по §11

| § | Раздел | % | Статус |
|---|--------|---|--------|
| 11.1 | Auth VPN+2FA | 95 | DONE |
| 11.2 | Дашборды / Grafana | 75 | PARTIAL |
| 11.3 | Воркеры | 80 | PARTIAL |
| 11.4 | Цены / тарифы | 90 | DONE |
| 11.5 | Логи / user_events | 65 | PARTIAL |
| 11.6 | Users / B2B | 85 | PARTIAL |
| 11.7 | Промо / кампании | 90 | DONE |
| 11.8 | Push | 70 | PARTIAL |
| 11.9 | Поддержка | 85 | PARTIAL |
| 11.10 | Модерация | 80 | PARTIAL |
| 11.11 | Legal | 75 | PARTIAL |
| 11.12 | GDPR delete | 90 | DONE |
| 11.13 | Налоги | 70 | PARTIAL |
| 11.14 | Экспорт | 70 | PARTIAL |
| 11.15 | UI / perf | 85 | DONE |
| 11.16 | Storage HA | 80 | PARTIAL |

---

## DONE (есть в UI)

- VPN badge + staff 2FA login (`AuthContext`, `LoginPage`)
- Дашборд §11.2: заказы, EWT, воркеры, финансы, B2B, воронка, quality, WS live
- Grafana embed + native charts fallback
- Воркеры: вес, grace, maintenance, cloud, TRELLIS rollout
- Settings: тарифы, апсейлы, алерты, escalations
- Users / B2B / invitations / promocodes / campaigns / push / moderation / tax / legal
- Support tickets + FAQ + stats + AI suggest
- Storage §11.16: SMART, cluster-health, write-activity, FIO, docker logs
- Watermark verify, audit export, access log, webhooks, marketplace credentials

---

## MISSING / PARTIAL

| ID | ТЗ | Статус |
|----|-----|--------|
| W1 | §4.2.2 Индикатор Redis OK / PG актуальна | **DONE** — dashboard badges |
| W2 | §1.4 DoD metrics UI | **DONE** — `/ops` |
| W3 | §12.1 user_events browser | **DONE** — `/user-events` |
| W4 | §22 HA ops (mesh, cutover, VIP, debezium) | **DONE** — `/ops` |
| W5 | §5 TRELLIS status | **DONE** — `/ops` |
| W6 | §7.6 Marketplace manual upload | **DONE** |
| W7 | `roles.ts` ACL для nav routes | **DONE** |
| W8 | §11.2.1 Success rate QS≥0.7 на дашборде | SPRINT 2 |
| W9 | §11.3 Логи воркера 24ч | SPRINT 2 |
| W10 | §11.8 Push schedule + журнал | SPRINT 2 |
| W11 | §11.10 forbidden_category log | SPRINT 2 |
| W12 | §11.11 Legal version history | SPRINT 2 |
| W13 | §11.13 PDF счёт/акт из UI | SPRINT 2 |

---

## Техдолг

- `AdminPages.tsx` — мёртвые stub-экспорты (Promocodes, Campaigns, …)
- `PageStub.tsx` — не используется

---

## План

### Спринт 1 — ops + gaps (текущий)
- [x] `webadminprod.md`
- [x] `roles.ts` — все nav routes
- [x] `OpsPage` — DoD, HA, trellis, debezium, load test
- [x] `UserEventsPage` — §12.1
- [x] Dashboard — queue Redis/PG badge
- [x] Marketplace — manual upload

### Спринт 2 — polish
- [ ] Quality score на дашборде
- [ ] Worker logs UI
- [ ] Push schedule
- [ ] Legal history
- [ ] Tax PDF actions

---

## Команды

```bash
cd apps/web-admin
npm run build
npm test
```
