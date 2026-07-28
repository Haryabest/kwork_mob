#!/usr/bin/env bash
# Release APK для LAN-стенда (GPU-сервер клиента).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOST="${CLIENT_HOST:-192.168.0.177}"
API_URL="${API_URL:-http://${HOST}:8000/api/v1}"
cd "$ROOT/apps/mobile"
flutter pub get
flutter build apk --release --dart-define="API_URL=${API_URL}"
echo ""
echo "APK: $ROOT/apps/mobile/build/app/outputs/flutter-apk/app-release.apk"
echo "API_URL=${API_URL}"
