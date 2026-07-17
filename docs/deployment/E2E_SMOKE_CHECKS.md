# E2E smoke — import / iOS AR / cloud restore

Ручные и полуавтоматические проверки после деплоя (§3.1.1 / §6.10 / §9.1.3).

## 1. Import GLB → validate → thumbnail

Локально (без orchestrator):

```powershell
cd C:\kwork_mob
python worker\scripts\e2e_import_acceptance.py --glb D:\samples\test.glb --category other
```

Ожидание: exit 0, `e2e_reports/import_acceptance.json` с `thumbnail_bytes > 0`.

Полный E2E через API (нужен Owner + `API_TOKEN`):

```powershell
$env:API_BASE = "http://localhost:8000/api/v1"
$env:API_TOKEN = "<jwt>"
.\worker\scripts\e2e_import_api.ps1 -GlbPath D:\samples\test.glb
```

Сценарий: `POST /models/import/prepare` → PUT GLB → `POST /models/import` → poll `GET /orders/{id}` до `completed` → `GET /models/{uuid}/thumbnail` 200.

## 2. iOS AR Texture smoke (§3.1.1)

На устройстве с ARKit:

1. Сборка `apps/mobile` с `ArPlugin.swift` (associated domains + camera entitlement).
2. Guided Dome → live preview (не placeholder «AR-камера активна»).
3. `startSession` возвращает `textureId`; `NativeArPreview` показывает кадр.
4. `capturePhoto` сохраняет JPEG в `ShootStorage` (view_XX).
5. Перегрев: при thermal warning — пауза съёмки (§3.1.2).

Pass: 3 последовательных capture без crash, texture обновляется ≥10 fps.

## 3. Cloud restore после reinstall (§9.1.3)

1. Авторизоваться, завершить заказ, дождаться GLB в облаке.
2. `POST /models/{uuid}/restore-sources` → скачать ZIP presigned URL.
3. Удалить приложение / очистить данные.
4. Переустановить, войти тем же аккаунтом.
5. Splash → `syncPendingDownloads` подтягивает GLB.
6. Модель открывается офлайн из `LocalModelLibrary`.

Автоматизация (API smoke):

```powershell
$env:API_BASE = "http://localhost:8000/api/v1"
$env:API_TOKEN = "<jwt>"
$env:MODEL_UUID = "<uuid>"
.\worker\scripts\e2e_cloud_restore.ps1
```

Pass: presigned ZIP HTTP 200, `access_log.action=restore_sources`.

## 4. Guest shoot по ссылке (§3.15)

API smoke на staging (Owner JWT, MinIO доступен):

```powershell
$env:API_BASE = "https://staging.3d.app/api/v1"
$env:API_TOKEN = "<owner-jwt>"
.\worker\scripts\e2e_guest_shoot_api.ps1
```

Сценарий: `POST /company/shoot_link` → `GET /shoot/{token}` → presigned PUT ×12 → `POST /shoot/{token}/complete`.

Pass: exit 0, `status=used`, `task_uuid` в ответе.

Webhook + guest shoot (staging):

```powershell
$env:API_BASE = "https://staging.3d.app/api/v1"
$env:API_TOKEN = "<owner-jwt>"
$env:WEBHOOK_URL = "https://webhook.site/<uuid>"
.\worker\scripts\e2e_guest_shoot_webhook.ps1
```

Pass: `shoot_link.uploaded` в deliveries с `ok=true`.

Интеграционный тест (CI): `tests/integration/test_guest_shoot_api_smoke.py` (skip при недоступном MinIO).

## 5. Ops — iOS AR / Firebase prod / real-device QA

См. `docs/mobile/RELEASE.md` и `docs/deployment/OPS_DEVICE_QA.md`.

- **iOS AR**: Guided Dome на iPhone, §2 выше.
- **Firebase prod**: `scripts/push_e2e.py` с prod `API_BASE` + зарегистрированный device token.
- **Real-device QA**: чеклист подписи, deep links, guest shoot в Safari → приложение.
