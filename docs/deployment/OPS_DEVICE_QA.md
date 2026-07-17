# Ops: real-device QA checklist §19.21

Ручные проверки перед релизом (не автоматизируются в CI).

## iOS AR Texture (§3.1.1)

1. Release-сборка на iPhone с ARKit (`apps/mobile`, `ArPlugin.swift`).
2. Guided Dome → live AR preview (не статичный placeholder).
3. 3 capture подряд без crash; texture ≥10 fps.
4. Thermal warning → пауза съёмки (§3.1.2).

**Pass:** все 4 пункта OK.

## Firebase prod push (§3.4.3)

1. Prod `google-services.json` / `GoogleService-Info.plist` в сборке.
2. Backend: `FCM_*`, APNs `.p8` в `.env`.
3. Устройство: login → `POST /user/devices` с FCM token.
4. Запуск:
   ```bash
   python scripts/push_e2e.py --base https://api.3d.app/api/v1 \
     --email <admin> --password '...' --user-id <uid>
   ```
5. Push получен на устройстве; tap → deep link открывает экран.

**Pass:** push доставлен, deeplink работает.

## Real-device QA (Android + iOS)

| # | Сценарий | Pass |
|---|----------|------|
| 1 | Login / logout / session revoke | |
| 2 | Shoot wizard: category → dome → quality → upload → checkout | |
| 3 | Guest shoot: `https://3d.app/shoot/{token}` → 12 фото | |
| 4 | Universal Link `/orders/{id}` из push | |
| 5 | Offline: checkout показывает «Нет интернета» | |
| 6 | Corp mode switch → balance filters сброс | |
| 7 | Store build: signing, icons, permissions | |

## Staging E2E scripts

```powershell
# Import
$env:API_BASE = "https://staging.3d.app/api/v1"
$env:API_TOKEN = "<jwt>"
.\worker\scripts\e2e_import_api.ps1 -GlbPath D:\samples\test.glb

# Guest shoot
.\worker\scripts\e2e_guest_shoot_api.ps1
```
