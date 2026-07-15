# Mobile release & prod checklist §19.21

## Firebase + APNs (§3.4.3)

1. Firebase Console → проект `kwork-mob-prod`
2. Android: скачать `google-services.json` → `apps/mobile/android/app/` (gitignored)
3. iOS: `GoogleService-Info.plist` → `apps/mobile/ios/Runner/`
4. APNs: загрузить `.p8` ключ в Firebase → Cloud Messaging → Apple
5. Backend `.env`: `FCM_*`, `APNS_KEY_ID`, `APNS_TEAM_ID`, `APNS_AUTH_KEY_PATH`
6. Сборка:
   ```bash
   flutter build apk --release \
     --dart-define=FIREBASE_API_KEY=... \
     --dart-define=FIREBASE_APP_ID=... \
     --dart-define=FIREBASE_MESSAGING_SENDER_ID=... \
     --dart-define=FIREBASE_PROJECT_ID=...
   ```

## Universal / App Links (§3.15)

1. `.env`: `APPLE_TEAM_ID`, `IOS_BUNDLE_ID`, `ANDROID_PACKAGE_NAME`, `ANDROID_SHA256_FINGERPRINTS`
2. `SELLER_PUBLIC_URL` / API gateway отдаёт `/.well-known/*` (orchestrator `main.py`)
3. Android: `gradle.properties` → `applinks.host=3d.app`
4. iOS: `Runner.entitlements` → `applinks:3d.app`
5. Verify: `curl https://3d.app/.well-known/apple-app-site-association`

## Signing

### Android
```bash
keytool -genkey -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
cp android/key.properties.example android/key.properties
```

### iOS
- Xcode → Signing & Capabilities → Distribution certificate
- `aps-environment: production` in entitlements for App Store

## Deep link E2E (manual + unit tests)

- Unit: `apps/mobile/test/deep_link_routes_test.dart`, `push_route_test.dart`
- CI: `mobile-backend-smoke` → auth + well-known + devices/analytics
- Manual on device:
1. Install release build
2. Send FCM with `data.deeplink=https://3d.app/orders/{id}`
3. Tap notification → opens queue screen
4. Open `https://3d.app/shoot/{token}` in Safari/Chrome → guest shoot

## CI

- `backend` job: integration tests incl. applinks + mobile API smoke
- `mobile-backend-smoke`: flutter test with `INTEGRATION_API`
