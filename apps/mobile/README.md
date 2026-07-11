# KWork Mob — Flutter (§3, §16, §19)

## Стек
- Flutter 3.x / Dart
- go_router, dio, flutter_secure_storage, shared_preferences
- i18n: `lib/l10n` (ru основной, en вторичный; kk/zh — позже)

## Запуск
```bash
cd apps/mobile
flutter pub get
flutter run
```

API по умолчанию: `http://10.0.2.2:8000/api/v1` (Android emulator → host).
Переопределение: `--dart-define=API_URL=http://...`

## Структура
```
lib/
  main.dart
  core/          — api, theme, router
  features/      — onboarding, auth, home, shoot, placeholder
  l10n/          — ARB локализация
```

Экраны AR-съёмки / оплаты / очереди — заглушки, наполняются по ТЗ.
