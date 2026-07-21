# Web-admin prod readiness (по `.claude/ТЗ.txt` §11)

**Область:** `apps/web-admin/`  
**Обновлено:** 2026-07-21

## Итог

| Метрика | Было | Цель |
|---------|------|------|
| UI vs ТЗ §11 | ~85% | 100% |
| Prod-ready | ~78% | 100% |

---

## MISSING / PARTIAL

| ID | ТЗ | Статус |
|----|-----|--------|
| W8 | §11.2.1 Success rate QS≥0.7 | **DONE** — quality tab |
| W9 | §11.3 Логи воркера 24ч | **DONE** — Workers «Логи 24ч» |
| W10 | §11.8 Push schedule + журнал | **DONE** |
| W11 | §11.10 forbidden_category log | **DONE** — Moderation tab |
| W12 | §11.11 Legal version history | **DONE** |
| W13 | §11.13 PDF счёт/акт из UI | **DONE** |

---

## План

### Спринт 1 — ops + gaps
- [x] OpsPage, UserEvents, queue health, marketplace upload, ACL

### Спринт 2 — polish
- [x] Quality score QS≥0.7 на дашборде
- [x] Worker logs UI (24ч)
- [x] Push schedule + журнал
- [x] Legal history
- [x] Tax PDF actions
- [x] Forbidden category log

### Спринт 3 — остаток
- [ ] §11.3 per-worker docker logs (Storage уже есть)
- [ ] §11.8 push open-rate stats
- [ ] §11.14 company export UI polish
- [ ] Техдолг: AdminPages stubs

---

## Команды

```bash
cd apps/web-admin && npm run build && npm test
cd backend/orchestrator && py -m ruff check app tests
```
