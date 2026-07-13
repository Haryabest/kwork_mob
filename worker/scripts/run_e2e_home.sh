#!/usr/bin/env bash
# Домашний / Linux GPU E2E TRELLIS (§1 KPI ≤3 мин local)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PHOTOS="${1:?usage: run_e2e_home.sh /path/to/12photos [workdir]}"
WORKDIR="${2:-}"

export WORKER_DEPLOY=local
export WORKER_PIPELINE_MODE=trellis
export TRELLIS_ALLOW_STUB_FALLBACK=0
export WORKER_FORCE_REAL_NOBG=1

ARGS=(--photos "$PHOTOS" --fail-on-budget --preflight)
if [[ -n "$WORKDIR" ]]; then
  ARGS+=(--workdir "$WORKDIR")
  export E2E_KEEP_WORKDIR=1
fi

exec python3 "$ROOT/worker/scripts/e2e_trellis_acceptance.py" "${ARGS[@]}"
