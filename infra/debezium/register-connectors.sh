#!/usr/bin/env bash
# Register Debezium PG connector (§12.1)
set -euo pipefail
CONNECT_URL="${DEBEZIUM_CONNECT_URL:-http://localhost:8083}"
DIR="$(cd "$(dirname "$0")" && pwd)"

echo "Registering pg-user-events-to-ch at $CONNECT_URL"
curl -sf -X POST "$CONNECT_URL/connectors" \
  -H "Content-Type: application/json" \
  -d @"$DIR/user-events-connector.json" | jq . 2>/dev/null || true

echo "Connector status:"
curl -sf "$CONNECT_URL/connectors/pg-user-events-to-ch/status" | jq .
