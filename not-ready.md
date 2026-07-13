# not-ready.md — что ещё осталось по ТЗ



После среза B2B roles / webhooks DLQ / campaigns / HA (2026-07-13).



---



## Критично (железо)



- [ ] Домашний GPU: `e2e_trellis_acceptance.py --fail-on-budget --preflight`

- [ ] Firebase prod keys + push E2E на устройстве

- [ ] Alembic `015` + `016_b2b_ops` на стенде



---



## Сделано в этом срезе



- [x] Кастомные роли B2B (`company_roles`, `/company/roles`, seller UI)

- [x] Webhooks retry×10 + DLQ + UI `/team/webhooks` + Celery

- [x] Авто-кампании referral / nth_free / timed_discount

- [x] Redis Sentinel client (`REDIS_SENTINELS`)

- [x] Patroni Dockerfile + compose profile `patroni`

- [x] Grafana dashboards JSON + ClickHouse MV в `init.sql`

- [x] MinIO SMART/usage `/storage/smart` + admin UI



---



## Осталось

- [ ] Admin Logs (не placeholder)
- [ ] HAProxy/VIP Patroni cutover
- [ ] Grafana datasources provisioning
- [ ] MinIO SMART node agent
- [x] Политики компании §2.5.4 API+UI
- [x] Load harness `scripts/load/`
- [x] Авто-refund в mark_failed
- [x] Mobile FAQ/support + Ollama suggest
- [x] Device benchmark + AR→тариф
- [ ] Soft launch checklist + burn ₽/ч

---

## Следующие задачи

1. Admin Logs  
2. HAProxy + Patroni runbook  
3. Grafana datasources  
4. MinIO SMART agent  
5. Celery auto_block_inactive  
6. Vault/AES ПД, E2E crypto, WB/Ozon API, воронка публикации  
