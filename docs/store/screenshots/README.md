# Store screenshots §19.21

## Требования

| # | Экран | iOS (1290×2796) | Android (1080×1920) |
|---|--------|-----------------|---------------------|
| 1 | Главная / съёмка | home_shoot.png | home_shoot.png |
| 2 | Guided Dome / AR | guided_dome.png | guided_dome.png |
| 3 | Очередь заказов | queue.png | queue.png |
| 4 | Просмотр 3D модели | model_viewer.png | model_viewer.png |
| 5 | Профиль / публикация WB-Ozon | publish.png | publish.png |

## Как снять

```bash
cd apps/mobile
flutter run --dart-define=API_URL=https://api.3d.app/api/v1
# На симуляторе/устройстве: Cmd+S (iOS) / adb exec-out screencap
```

Или Fastlane `snapshot` / `screengrab` (см. `docs/mobile/RELEASE.md`).

## Placeholder

Сгенерированы брендированные placeholder PNG (заменить перед загрузкой в store):

```bash
py docs/store/screenshots/generate_placeholders.py
```

Файлы: `android/*.png` (1080×1920), `ios/*.png` (1290×2796).
