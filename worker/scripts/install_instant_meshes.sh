#!/usr/bin/env bash
# Установка Instant Meshes → /usr/local/bin/instant_meshes (§5 / §6.3)
set -euo pipefail

TARGET="${1:-/usr/local/bin/instant_meshes}"
WORKDIR="${INSTANT_MESHES_BUILD_DIR:-/tmp/instant-meshes-build}"

if [ -x "$TARGET" ]; then
  echo "[instant_meshes] already at $TARGET"
  exit 0
fi

apt-get update -qq
apt-get install -y -qq cmake g++ libx11-dev libxi-dev libxrandr-dev libxinerama-dev \
  libxcursor-dev libgl1-mesa-dev || true

rm -rf "$WORKDIR"
git clone --depth 1 https://github.com/wjakob/instant-meshes.git "$WORKDIR"
mkdir -p "$WORKDIR/build"
cd "$WORKDIR/build"
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release -j"$(nproc)"

BIN=""
for c in InstantMeshes InstantMeshes_gui InstantMeshes_bin InstantMeshes_cli; do
  if [ -x "./$c" ]; then BIN="./$c"; break; fi
  if [ -x "./Release/$c" ]; then BIN="./Release/$c"; break; fi
done
# иногда бинарь называется InstantMeshes без суффикса
if [ -z "$BIN" ]; then
  BIN="$(find . -maxdepth 2 -type f -executable -iname '*instant*' | head -n1 || true)"
fi
if [ -z "$BIN" ] || [ ! -x "$BIN" ]; then
  echo "[instant_meshes] build produced no binary" >&2
  exit 1
fi

install -m 0755 "$BIN" "$TARGET"
echo "[instant_meshes] installed → $TARGET"
"$TARGET" --help >/dev/null 2>&1 || true
