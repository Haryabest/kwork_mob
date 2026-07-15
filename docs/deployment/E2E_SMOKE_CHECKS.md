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
