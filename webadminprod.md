# Web-admin prod readiness (по `.claude/ТЗ.txt` §11)

**Область:** `apps/web-admin/`  
**Обновлено:** 2026-07-21

## Итог

| Метрика | Было | Цель |
|---------|------|------|
| UI vs ТЗ §11 | ~92% | 100% |
| Prod-ready | ~85% | 100% |

**Статус:** все пункты §11 закрыты.

---

## План

### Спринт 1–2 — DONE
Ops, user events, QS dashboard, push schedule, legal/tax/forbidden, ACL

### Спринт 3 — DONE
- [x] OpenAPI regen (`docs/api/openapi.json`)
- [x] Workers → Storage docker logs (deep link)
- [x] Push open-rate stats (`GET /admin/campaigns/push/stats`)
- [x] Company data export UI §11.14 (`/admin/companies/{id}/data-export`)
- [x] Удалены stub-страницы в `AdminPages.tsx`, `PageStub.tsx`

### Спринт 4 — DONE
- [x] Push open tracking в mobile (`notification_id` → `markNotificationRead`)
- [x] §11.14 presign download refresh (`GET .../data-export/{id}/presign`, poll pending)

---

## Команды

```bash
cd backend/orchestrator && py scripts/export_openapi.py --check
cd apps/web-admin && npm run build
```
