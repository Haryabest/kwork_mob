# not-ready.md — что ещё осталось по ТЗ

После среза cloud/pub/HA/E2E harness (2026-07-12).

---

## Критично для «полного 3D прода»

- [ ] **Прогнать** `e2e_trellis_acceptance.py --fail-on-budget` на реальном GPU с весами TRELLIS (код готов, нужна приёмка на железе)
- [ ] Instant Meshes / quadriflow как отдельный бинарь (сейчас Open3D/trimesh decimation)
- [ ] Полноценный PBR bake из текстур фото (сейчас procedural maps + factors)
- [ ] `usd_from_gltf` / Blender в образе гарантированно (есть fallback zip-USDZ)
- [ ] video_360: гарантированный Blender в образе
- [ ] Устойчивость DWT к JPEG/WebP 80% — формальные тесты приёмки

---

## B2B / продукт

- [ ] Кастомные роли (не только owner/manager/photographer/viewer)
- [ ] ЮKassa topup напрямую на `Company.balance` (сейчас manual topup + charge)
- [ ] Corporate webhooks retry/DLQ UI
- [ ] 50+ фотографов нагрузочный DoD
- [ ] Авто-логика кампаний referral / nth_free / timed_discount

---

## Mobile / платежи / compliance

- [ ] Полный Flutter-клиент (съёмка 12 ракурсов, AR, очередь, push FCM)
- [ ] СБП QR пополнение (ЮKassa)
- [ ] Фискализация чеков ЮKassa (НПД/УСН/ОСНО настройки)
- [ ] Право на забвение (анонимизация финансов 5 лет)
- [ ] 2FA TOTP для Owner компании
- [ ] SHA-256 целостность ZIP исходников
- [ ] CORS + Referer на скачивание (§10.3)
- [ ] Admin Dashboard UI на `/admin/metrics/dashboard` (API есть, страница — частично)

---

## Ops polish

- [ ] Полный Patroni (сейчас streaming replica + scaffold YAML; bitnami/patroni образ в prod)
- [ ] Redis Sentinel client в оркестраторе (`REDIS_SENTINELS`) — сейчас URL на master
- [ ] MinIO SMART / health dashboard в admin Storage
- [ ] Grafana dashboards JSON
- [ ] ClickHouse MV подключить в init контейнера
- [ ] PG backup retention scrubber
- [ ] Tailscale пакет в worker image (entrypoint готов)
