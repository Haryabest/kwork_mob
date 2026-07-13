# Mobile (Flutter) — KWork Mob

Стек: Flutter 3.41+ · **Forui** · Dio · Camera · FCM · model_viewer_plus · AR.

## Запуск

```bash
cd apps/mobile
flutter pub get
flutter run --dart-define=API_URL=http://10.0.2.2:8000/api/v1
```

## FCM (§3.4.3)

1. `android/app/google-services.json.example` → `google-services.json`
2. iOS: `GoogleService-Info.plist.example` → `GoogleService-Info.plist`
3. Оркестратор `.env`: `FCM_SERVER_KEY` или `FCM_SERVICE_ACCOUNT_JSON` + `FCM_PROJECT_ID`
4. E2E: `python scripts/push_e2e.py --email ... --password ... --user-id N`

Без ключей приложение стартует, push отключён; токен → `POST /user/devices`.

## AR (§3.1.1)

- Native: `ArSessionPlugin` (ARCore) / `ArPlugin` (ARKit) — каналы `com.kwork.mob/ar`
- Fallback: `GyroArSession` (±15°)
- Guided Dome показывает бэкенд: ARKit / ARCore / Gyro

## Поток съёмки (§3)

1. Категория + запрещённые + тариф  
2. Guided Dome 12 ракурсов  
3. Проверка качества + пересъёмка  
4. Presigned upload + заказ  
5. Очередь WS  
6. Viewer + оценка 1–5  

## Корпоратив

Личный / Компания · shoot-link + QR.
