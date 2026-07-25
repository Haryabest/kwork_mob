#!/bin/sh
# @gltf-transform/cli требует Node.js >= 18 (Ubuntu apt nodejs = v12 → ERR_MODULE_NOT_FOUND).
set -eu

MIN_NODE=18
NEED=0

if ! command -v node >/dev/null 2>&1; then
  NEED=1
else
  NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]")"
  if [ "${NODE_MAJOR}" -lt "${MIN_NODE}" ] 2>/dev/null; then
    NEED=1
  fi
fi

if [ "${NEED}" = "0" ] && command -v gltf-transform >/dev/null 2>&1; then
  if gltf-transform --help >/dev/null 2>&1; then
    echo "[gltf-transform] OK node=$(node -v) cli=$(gltf-transform --version 2>/dev/null | head -1)"
    exit 0
  fi
  NEED=1
fi

echo "[gltf-transform] установка Node.js 20 + @gltf-transform/cli"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get remove -y -qq nodejs libnode-dev libnode72 2>/dev/null || true
apt-get autoremove -y -qq 2>/dev/null || true
apt-get install -y -qq ca-certificates curl gnupg
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y -qq nodejs
npm uninstall -g @gltf-transform/cli 2>/dev/null || true
npm install -g @gltf-transform/cli
npm install -g --include=optional sharp
pip3 install --no-cache-dir fast-simplification 2>/dev/null || true
gltf-transform --help >/dev/null
echo "[gltf-transform] OK node=$(node -v)"
