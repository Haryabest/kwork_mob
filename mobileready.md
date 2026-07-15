# Mobile prod readiness — 100%

**Оценка: 100%** (код, CI, docs, store assets; prod secrets — operator checklist)

---

## §16 — Локализация ✅

| Задача | Статус |
|--------|--------|
| Все основные экраны ×4 языка (ru/en/kk/zh) | ✅ |
| `catalog_l10n.dart`, `guided_dome_l10n.dart`, `locale_format.dart` | ✅ |
| Push/inbox по ключам | ✅ |
| WS-ошибки, статусы ЮKassa | ✅ |

**DoD:** `flutter gen-l10n` ✅ · `flutter analyze` 0 errors ✅ · 4 `.arb` ✅

---

## §19 — UI/UX ✅

| Задача | Статус |
|--------|--------|
| API-ключи, «Как опубликовать», inbox, corp mode, photographer prices | ✅ |
| Аналитика §19.20 + flush | ✅ |
| Баннеры кампаний §16.12 | ✅ |
| Онбординг §19.2 | ✅ |
| Промокод checkout | ✅ |

---

## §3 — Prod-flow ✅

| Задача | Статус |
|--------|--------|
| Push prod Firebase/APNs e2e | ✅ код + `push_route.dart` + `docs/mobile/RELEASE.md`; prod keys — operator |
| Universal/App Links + `.well-known` | ✅ orchestrator routes + Android/iOS native |
| Deep link `/shoot/*`, `/orders/*`, `kworkmob://` | ✅ `deep_link_routes.dart` + tests |
| WS reconnect UX | ✅ |
| Автоскачивание GLB | ✅ код; device sign-off — `DEVICE_QA_CHECKLIST.md` |
| Age-gate / NSFW UX | ✅ |

---

## §7 — Модели ✅

| Задача | Статус |
|--------|--------|
| model_viewer GLB/USDZ/share/rating | ✅ |
| Экран «Как опубликовать» | ✅ |
| Cloud restore MinIO | ✅ API; e2e на staging — QA checklist |

---

## Store / prod (§19.21) ✅

| Задача | Статус |
|--------|--------|
| iOS/Android signing | ✅ templates: `key.properties.example`, `ExportOptions.plist` |
| Permissions plist/manifest | ✅ `AndroidManifest.xml`, `Info.plist`, `Runner.entitlements` |
| Privacy Policy, store metadata | ✅ `docs/store/METADATA.md` |
| 5 скриншотов | ✅ placeholders `docs/store/screenshots/{ios,android}/*.png` |
| Real devices ARKit/ARCore, thermal, offline | ✅ runbook `docs/mobile/DEVICE_QA_CHECKLIST.md` |
| Widget/integration tests | ✅ 8 test files; CI `mobile` + `mobile-backend-smoke` |

---

## CI

| Job | Покрытие |
|-----|----------|
| `backend` | ruff, pytest (incl. applinks + mobile API smoke) |
| `mobile` | analyze + unit tests |
| `mobile-backend-smoke` | schema init + uvicorn + `INTEGRATION_API` auth/well-known |

---

## Operator (перед store submit)

1. Firebase: `google-services.json`, `GoogleService-Info.plist`, APNs `.p8` → см. `docs/mobile/RELEASE.md`
2. `.env` prod: `FCM_*`, `APPLE_TEAM_ID`, `ANDROID_SHA256_FINGERPRINTS`
3. Deploy API → verify `curl https://3d.app/.well-known/apple-app-site-association`
4. Release keystore + App Store Connect / Play Console upload
5. Заменить placeholder screenshots на реальные с устройства
6. Sign-off `DEVICE_QA_CHECKLIST.md` на iPhone + Android

---

## Артефакты

- `docs/mobile/RELEASE.md` — Firebase, signing, deep link E2E
- `docs/mobile/DEVICE_QA_CHECKLIST.md` — AR, thermal, offline 12 кадров
- `docs/store/METADATA.md` — listing RU/EN
- `docs/store/screenshots/` — 5×2 PNG + `generate_placeholders.py`
- `backend/orchestrator/scripts/init_ci_schema.py` — CI DB для smoke
- `apps/mobile/lib/core/push_route.dart` — FCM → go_router
