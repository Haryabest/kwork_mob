#!/usr/bin/env bash
# HA cutover preflight (local / staging)
set -euo pipefail
BASE="${API_BASE_URL:-http://localhost:8000}"
TOKEN="${ADMIN_TOKEN:-}"

if [ -z "$TOKEN" ]; then
  echo "Set ADMIN_TOKEN" >&2
  exit 1
fi

curl -sf -H "Authorization: Bearer $TOKEN" \
  "$BASE/api/v1/admin/ha/cutover/preflight" | python -m json.tool
