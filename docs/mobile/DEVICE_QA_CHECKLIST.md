# Device QA matrix §1.4 / §19.21

Sign-off перед релизом. Отметить ✅ на реальном устройстве.

## Матрица

| Сценарий | iPhone (ARKit) | Android (ARCore) | Offline |
|----------|----------------|------------------|---------|
| Auth login/register | ☐ | ☐ | ☐ |
| Onboarding 4 экрана | ☐ | ☐ | — |
| Category + age gate 18+ | ☐ | ☐ | — |
| Guided Dome 12 кадров | ☐ | ☐ | ☐ |
| Thermal throttle FPS 15 | ☐ | ☐ | — |
| Upload 12 photos + checkout | ☐ | ☐ | ☐ |
| Push → open order | ☐ | ☐ | — |
| Universal Link `/orders/{id}` | ☐ | ☐ | — |
| Universal Link `/shoot/{token}` | ☐ | ☐ | — |
| GLB auto-download completed | ☐ | ☐ | ☐ |
| Model viewer GLB/USDZ share | ☐ | ☐ | — |
| Corp mode + shoot link QR | ☐ | ☐ | — |
| Photographer hide prices | ☐ | ☐ | — |

## Offline shoot (12 кадров)

1. Airplane mode ON после выбора категории
2. Снять 12 кадров локально
3. Airplane mode OFF → upload resume §3.4.1

## Thermal

1. Нагрев >40°C (или dev simulate в `thermal_monitor`)
2. FPS снижается, сообщение `gdFpsWait` показывается

## Подпись QA

| Роль | Имя | Дата | Build |
|------|-----|------|-------|
| QA | | | |
| Owner | | | |
