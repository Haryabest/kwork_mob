#!/bin/sh
# @gltf-transform/cli требует Node.js >= 18 (Ubuntu apt nodejs = v12 → ERR_MODULE_NOT_FOUND).
set -eu

MIN_NODE=18
NEED=0

_sharp_ok() {
  CLI_DIR="$(npm root -g 2>/dev/null)/@gltf-transform/cli"
  if [ ! -d "${CLI_DIR}/node_modules/sharp" ]; then
    return 1
  fi
  node -e "require('${CLI_DIR}/node_modules/sharp')" >/dev/null 2>&1
}

if ! command -v node >/dev/null 2>&1; then
  NEED=1
else
  NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]")"
  if [ "${NODE_MAJOR}" -lt "${MIN_NODE}" ] 2>/dev/null; then
    NEED=1
  fi
fi

if [ "${NEED}" = "0" ] && command -v gltf-transform >/dev/null 2>&1; then
  if gltf-transform --help >/dev/null 2>&1 && _sharp_ok; then
    echo "[gltf-transform] OK node=$(node -v) cli=$(gltf-transform --version 2>/dev/null | head -1)"
    NEED=0
  else
    NEED=1
  fi
fi

if [ "${NEED}" = "1" ]; then
  echo "[gltf-transform] установка Node.js 20 + @gltf-transform/cli + sharp"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get remove -y -qq nodejs libnode-dev libnode72 2>/dev/null || true
  apt-get autoremove -y -qq 2>/dev/null || true
  apt-get install -y -qq ca-certificates curl gnupg libvips42 libvips-dev 2>/dev/null || \
    apt-get install -y -qq ca-certificates curl gnupg
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
  npm uninstall -g @gltf-transform/cli 2>/dev/null || true
  npm install -g @gltf-transform/cli
  CLI_DIR="$(npm root -g)/@gltf-transform/cli"
  (cd "${CLI_DIR}" && npm install sharp --include=optional && npm rebuild sharp)
  node -e "require('${CLI_DIR}/node_modules/sharp')" >/dev/null
  gltf-transform --help >/dev/null
  echo "[gltf-transform] OK node=$(node -v)"
fi

if ! command -v gltfpack >/dev/null 2>&1; then
  echo "[gltfpack] установка meshoptimizer gltfpack"
  GLTFPACK_VER="${GLTFPACK_VERSION:-0.22}"
  curl -fsSL \
    "https://github.com/zeux/meshoptimizer/releases/download/v${GLTFPACK_VER}/gltfpack" \
    -o /usr/local/bin/gltfpack
  chmod +x /usr/local/bin/gltfpack
fi
gltfpack --version 2>/dev/null | head -1 || true
pip3 install --no-cache-dir fast-simplification 2>/dev/null || true
