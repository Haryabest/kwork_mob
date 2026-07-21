#!/usr/bin/env bash
# §9.4 WAL-G backup — полный push + retention (cron на узле PostgreSQL)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "${SCRIPT_DIR}/walg.env" ]]; then
  set -a
  # shellcheck source=/dev/null
  source "${SCRIPT_DIR}/walg.env"
  set +a
fi

: "${PGDATA:?PGDATA required}"
: "${WALG_S3_PREFIX:?WALG_S3_PREFIX required}"

wal-g backup-push "${PGDATA}"
wal-g delete retain FULL 4 --confirm
wal-g delete retain FIND_FULL 14 --confirm

echo "WAL-G backup completed at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
