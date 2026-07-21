# Frontend prod readiness (mobile + web-admin + web-seller)

**Источник:** `.claude/ТЗ.txt` §3, §11, §19, §20  
**Сверка с кодом:** 2026-07-21  
**Связанные файлы:** `webadminprod.md` (§11 детально), `back_prod.md` (backend), `67.md` → этот файл

---

## Итог

| Приложение | Код vs ТЗ | Prod-ready | Комментарий |
|------------|-----------|------------|-------------|
| `apps/web-admin` | **100%** §11 | **~90%** | UI/API-клиент закрыт; gate — VPN, Grafana prod, DoD KPI |
| `apps/mobile` | **~98%** §3+§19 | **~75%** | Фичи в коде; gate — store assets, real-device QA, Firebase prod |
| `apps/web-seller` | **100%** §20 | **~95%** | Код закрыт; gate — prod keys, WAF |
| `apps/web-support` | — | **100%** | Deprecated → web-admin |

**Вердикт:** новые экраны и API-клиенты писать почти нечего. Блокеры — **release/QA/ops** и **backend prod-verify** (§1.4).

---

## apps/mobile (`§3`, `§19`)

### DONE (код)

| ID | Тема |
|----|------|
| 3.1 | Resumable multipart upload ZIP (12 фото) |
| 3.2 | Offline mode (очередь действий) |
| 3.3 | WB/Ozon автоверификация |
| 3.4 | Team UI parity |
| 3.5 | Cancel order UX |
| 3.6 | Push → email fallback (клиент + backend) |
| 3.7 | Public share: rate-limit + watermark |
| 19.1 | Offline mode |
| 19.2 | Analytics events → CH |
| 19.1 | WB `#6D3B6B` / Ozon `#005B9F`, tab bar 4 вкладки |
| 19.19 | Анимации / haptic / spinners |
| 3.8 | Adaptive benchmark UI |
| 3.19 | Routing корп. уведомлений → policies |
| 3.4.3 | Push open tracking (`notification_id` → `markNotificationRead`) |

*Экраны: onboarding, auth, shoot, queue, viewer, publish, FAQ, profile, guest shoot, corp mode, calibration, trash.*

### Остаток — код

| ID | Задача | Статус | Действие |
|----|--------|--------|----------|
| M1 | §19.21 Store screenshots | **PLACEHOLDER** | Заменить PNG в `docs/store/screenshots/{ios,android}/` реальными с устройства |
| M2 | Мёртвый код / TODO в Dart | **DONE** | `TODO`/`FIXME` в `lib/` нет |

### Остаток — ops / QA (не код)

| ID | Задача | Статус | Действие |
|----|--------|--------|----------|
| M3 | Prod QA iOS/Android | **UNVERIFIED** | Чеклист ниже § «Mobile prod QA» |
| M4 | Firebase + APNs prod keys | **OPS** | `docs/mobile/RELEASE.md` |
| M5 | Signing (keystore / Distribution) | **OPS** | `docs/mobile/RELEASE.md` |
| M6 | Universal / App Links E2E на device | **UNVERIFIED** | `test/deep_link_routes_test.dart` + manual |
| M7 | RuStore / App Store submit | **OPS** | `docs/mobile/RELEASE.md`, `docs/store/METADATA.md` |
| M8 | Thermal graceful shutdown на реальном GPU-phone | **UNVERIFIED** | Soft launch item `mobile` |

### Mobile prod QA (ручной чеклист)

```text
[ ] Release build: flutter build apk --release / ios archive
[ ] Login → email verify → consents
[ ] Guided Dome: 12 фото → upload → queue WS progress
[ ] Push: FCM data.deeplink → экран заказа
[ ] Push open: tap → read_at в inbox (admin push stats)
[ ] Guest shoot link → съёмка без аккаунта
[ ] Corp: invite accept, policies, shoot-link
[ ] WB/Ozon verify + download GLB/USDZ
[ ] Offline: действие в очереди → sync при сети
[ ] Deep link https://3d.app/orders/{id} (Safari + Chrome)
[ ] Thermal: длительная съёмка без краша (Android/iOS)
[ ] Локали: ru / en / kk / zh переключение
```

### Команды

```bash
cd apps/mobile
flutter analyze
flutter test
flutter build apk --release
py ../docs/store/screenshots/generate_placeholders.py   # placeholder PNG
```

---

## apps/web-admin (`§11`)

### DONE

Все пункты §11 закрыты — см. `webadminprod.md` (спринты 1–4).

Ключевое: Ops, user events, QS dashboard, push schedule+stats, legal versions, tax PDF, forbidden log, company export + presign, ACL, react-window, VPN badge, native charts.

### Остаток — код

| ID | Задача | Статус | Действие |
|----|--------|--------|----------|
| A1 | Stub-страницы | **DONE** | Удалён `PageStub.tsx` |
| A2 | Новые экраны §11 | **DONE** | — |

### Остаток — ops / QA

| ID | Задача | Статус | Действие |
|----|--------|--------|----------|
| A3 | Admin VPN gate в prod | **OPS** | `require_vpn` + Tailscale mesh |
| A4 | Grafana iframe prod URL | **OPS** | `GrafanaPage`, env `GRAFANA_URL` |
| A5 | Soft launch checklist | **UNVERIFIED** | `/soft-launch` — GPU E2E, funnel, alerts |
| A6 | DoD KPI §1.4 | **UNVERIFIED** | `/ops` → `GET /admin/dod-metrics` |
| A7 | 2FA Owner в prod | **OPS** | Settings + реальный TOTP |

### Команды

```bash
cd apps/web-admin
npm test
npm run build
cd ../../backend/orchestrator && py scripts/export_openapi.py --check
```

---

## apps/web-seller (`§20`, `§16`)

Все пункты закрыты (`ЗАДАЧИ_ПО_ТЗ.md` P46–P53, §20.9).

**Ops:** prod JWT cookies, reCAPTCHA keys, `SELLER_PUBLIC_URL`, WAF.

---

## Зависимости фронта от backend (не блокируют UI, блокируют prod)

| § | Тема | Влияет на | Статус |
|---|------|-----------|--------|
| 1.4 | DoD KPI (18 метрик) | admin SoftLaunch, mobile funnel | UNVERIFIED |
| 9.1 | MinIO HA failover | download/presign mobile+admin | PARTIAL |
| 9.7 | Async company export job | admin CompanyDetail | DONE (код) |
| 10.1 | reCAPTCHA | web-seller register/pay | DONE (код), keys OPS |
| 22.6–22.8 | HA cutover, witness, Tailscale storage | admin Storage, workers | PARTIAL / OPS |
| 5 | TRELLIS prod GPU pipeline | mobile queue completion | TOOLING + prod verify |

Детали: `back_prod.md`.

---

## Ops (все приложения)

| ID | Задача | Документ |
|----|--------|----------|
| OPS.1 | CH backfill staging | `OPS_CLICKHOUSE_ANALYTICS.md` |
| OPS.2 | OAuth prod keys | `OPS_OAUTH.md` |
| OPS.3 | Firebase prod + real-device QA | `docs/mobile/RELEASE.md` |
| OPS.4 | RuStore / App Store submit | `docs/store/METADATA.md` |
| OPS.5 | ЮKassa / SMTP prod | `.env` prod |
| OPS.6 | WAF Cloudflare | `infra/cloudflare/` |
| OPS.7 | Tailscale mesh storage nodes | `back_prod.md` §22 |
| OPS.8 | Prod HA cutover | `scripts/ha_cutover_preflight.sh` |

---

## План (приоритет)

### Спринт F1 — release mobile (ручное)
- [ ] M3 Prod QA чеклист (10 пунктов выше)
- [ ] M1 Реальные screenshots → `docs/store/screenshots/`
- [ ] M4–M7 Firebase, signing, store submit

### Спринт F2 — admin/seller prod gate
- [ ] A3 VPN + A7 2FA в prod
- [ ] A5 Soft launch: все галочки зелёные
- [ ] A6 DoD export CSV + review KPI

### Спринт F3 — e2e prod
- [ ] OPS.8 HA cutover
- [ ] §1.4 все UNVERIFIED → measured в prod
- [ ] M8 thermal + GPU E2E на реальном железе

---

## Файлы

| Компонент | Путь |
|-----------|------|
| Mobile app | `apps/mobile/lib/` |
| Web-admin routes | `apps/web-admin/src/main.tsx` |
| Store screenshots | `docs/store/screenshots/` |
| Store metadata | `docs/store/METADATA.md` |
| Mobile release | `docs/mobile/RELEASE.md` |
| Admin §11 audit | `webadminprod.md` |
| Backend audit | `back_prod.md` |
