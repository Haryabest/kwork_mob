#!/usr/bin/env bash
# Сохранить GPU-воркер в образ после install_trellis_runtime (flexgemm, o_voxel…).
# Один раз после первого долгого старта — дальше apply/recreate без переустановки.
#
# Usage:
#   ./scripts/worker_docker_bake.sh
#   ./scripts/worker_docker_bake.sh kwork-worker kwork-worker:trellis2-runtime
#   ./scripts/worker_docker_bake.sh kwork-worker kwork-worker:trellis2-runtime ./kwork-worker-runtime.tar
set -euo pipefail

CONTAINER="${1:-kwork-worker}"
IMAGE_TAG="${2:-kwork-worker:trellis2-runtime}"
SAVE_TAR="${3:-}"

if ! docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Контейнер «${CONTAINER}» не найден. Сначала запустите воркер." >&2
  exit 1
fi

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Запускаю ${CONTAINER}…"
  docker start "$CONTAINER" >/dev/null
fi

echo "[bake] ждём install_trellis_runtime (o_voxel + flex_gemm)…"
deadline=$((SECONDS + 3600))
while (( SECONDS < deadline )); do
  if docker exec "$CONTAINER" python3 -c "
import importlib.util
mods = ('o_voxel', 'flex_gemm')
missing = [m for m in mods if importlib.util.find_spec(m) is None]
raise SystemExit(0 if not missing else 1)
" 2>/dev/null; then
    break
  fi
  if docker logs --tail 5 "$CONTAINER" 2>&1 | grep -q '\[trellis-runtime\] готово'; then
    sleep 2
    break
  fi
  sleep 10
  echo "[bake] … ещё ждём ($(( (deadline - SECONDS) / 60 )) мин осталось)"
done

if ! docker exec "$CONTAINER" python3 -c "import o_voxel, flex_gemm; print('runtime OK')"; then
  echo "Runtime не готов. Логи: docker logs -f ${CONTAINER}" >&2
  exit 1
fi

echo "[bake] docker commit ${CONTAINER} → ${IMAGE_TAG}"
docker commit \
  -m "trellis2 runtime baked $(date -u +%Y-%m-%dT%H:%MZ)" \
  "$CONTAINER" "$IMAGE_TAG"

if [[ -n "$SAVE_TAR" ]]; then
  echo "[bake] docker save → ${SAVE_TAR}"
  docker save -o "$SAVE_TAR" "$IMAGE_TAG"
fi

cat <<EOF

Готово: ${IMAGE_TAG}
В .env или web-admin → Docker → Образ: ${IMAGE_TAG}
Проверка: docker image inspect ${IMAGE_TAG}

Загрузка на другой сервер:
  docker load -i ${SAVE_TAR:-kwork-worker-runtime.tar}
EOF
