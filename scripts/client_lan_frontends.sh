#!/usr/bin/env bash
# web-seller :3000 + web-admin :3001 одной командой (фоновые процессы).
# Usage: ./scripts/client_lan_frontends.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "[frontends] нет .env — скопируйте .env.example" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
source .env
set +a

HOST="${CLIENT_HOST:-192.168.0.177}"
API_PROXY="http://127.0.0.1:8000"
LOG_DIR="${ROOT}/.logs"
PID_FILE="${LOG_DIR}/frontends.pid"
mkdir -p "$LOG_DIR"

stop_frontends() {
  if [[ -f "$PID_FILE" ]]; then
    while read -r pid; do
      [[ -n "$pid" ]] && kill "$pid" 2>/dev/null || true
    done <"$PID_FILE"
    rm -f "$PID_FILE"
  fi
}

if [[ "${1:-}" == "stop" ]]; then
  stop_frontends
  echo "[frontends] остановлено"
  exit 0
fi

command -v node >/dev/null || { echo "[frontends] нужен Node.js 20+" >&2; exit 1; }
command -v npm >/dev/null || { echo "[frontends] нужен npm" >&2; exit 1; }

stop_frontends

echo "[frontends] npm install (seller + admin)…"
(cd apps/web-seller && npm install --no-fund --no-audit)
(cd apps/web-admin && npm install --no-fund --no-audit)

echo "[frontends] API proxy → $API_PROXY (browser: /api/v1, WS: ws://${HOST}:8000)"

(
  cd apps/web-seller
  export NEXT_PUBLIC_API_URL="/api/v1"
  export NEXT_PUBLIC_WS_URL="ws://${HOST}:8000"
  export API_PROXY_TARGET="$API_PROXY"
  exec npm run dev -- -H 0.0.0.0 -p 3000
) >"${LOG_DIR}/web-seller.log" 2>&1 &
echo $! >"$PID_FILE"

(
  cd apps/web-admin
  export VITE_API_URL="/api/v1"
  export API_PROXY_TARGET="$API_PROXY"
  exec npm run dev -- --host --port 3001
) >"${LOG_DIR}/web-admin.log" 2>&1 &
echo $! >>"$PID_FILE"

sleep 2
cat <<EOF

=== Фронты запущены (фон) ===
Seller:  http://${HOST}:3000   log: .logs/web-seller.log
Admin:   http://${HOST}:3001   log: .logs/web-admin.log

Остановить: ./scripts/client_lan_frontends.sh stop
Логи:       tail -f .logs/web-seller.log .logs/web-admin.log
EOF
