#!/bin/sh
# @gltf-transform/cli требует Node.js >= 18 + sharp linux-x64 (@img/sharp-linux-x64).
set -u

MIN_NODE=18
CLI_DIR=""

_cli_dir() {
  if [ -z "${CLI_DIR}" ]; then
    CLI_DIR="$(npm root -g 2>/dev/null)/@gltf-transform/cli"
  fi
  printf '%s' "${CLI_DIR}"
}

_sharp_ok() {
  local cli
  cli="$(_cli_dir)"
  if [ ! -d "${cli}/node_modules/sharp" ]; then
    return 1
  fi
  node -e "require('${cli}/node_modules/sharp')" >/dev/null 2>&1
}

_gltf_transform_ok() {
  command -v gltf-transform >/dev/null 2>&1 && gltf-transform --version >/dev/null 2>&1
}

_install_vips() {
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get install -y -qq \
    libvips42 libglib2.0-0 libjpeg-turbo8 libpng16-16 libwebp7 libtiff5 libexif12 \
    2>/dev/null || apt-get install -y -qq libvips42 libglib2.0-0 2>/dev/null || true
}

_repair_sharp() {
  local cli sharp_ver
  cli="$(_cli_dir)"
  if [ ! -d "${cli}" ]; then
    echo "[gltf-transform] skip sharp repair — нет ${cli}"
    return 1
  fi
  echo "[gltf-transform] repair sharp in ${cli}"
  _install_vips
  (
    cd "${cli}"
    rm -rf node_modules/sharp node_modules/@img
    npm install sharp --no-save --include=optional --os=linux --cpu=x64 --force
    sharp_ver="$(node -e "try{console.log(require('./node_modules/sharp/package.json').version)}catch(e){console.log('')}" 2>/dev/null || true)"
    if [ -n "${sharp_ver}" ]; then
      npm install \
        "@img/sharp-linux-x64@${sharp_ver}" \
        "@img/sharp-libvips-linux-x64@${sharp_ver}" \
        --no-save --include=optional --force 2>/dev/null || true
    else
      npm install @img/sharp-linux-x64 @img/sharp-libvips-linux-x64 \
        --no-save --include=optional --force 2>/dev/null || true
    fi
    npm rebuild sharp --force 2>/dev/null || true
  )
  if _sharp_ok; then
    echo "[gltf-transform] sharp OK"
    return 0
  fi
  echo "[gltf-transform] sharp repair: build-from-source"
  apt-get install -y -qq libvips-dev g++ make python3 2>/dev/null || true
  (
    cd "${cli}"
    rm -rf node_modules/sharp node_modules/@img
    npm install sharp --no-save --build-from-source --include=optional 2>/dev/null || \
      npm install sharp --no-save --include=optional --os=linux --cpu=x64 --force
  )
  if _sharp_ok; then
    echo "[gltf-transform] sharp OK (build-from-source)"
    return 0
  fi
  echo "[gltf-transform] sharp still broken after repair"
  return 1
}

_install_node_cli() {
  echo "[gltf-transform] установка Node.js 20 + @gltf-transform/cli"
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -qq
  apt-get remove -y -qq nodejs libnode-dev libnode72 2>/dev/null || true
  apt-get autoremove -y -qq 2>/dev/null || true
  apt-get install -y -qq ca-certificates curl gnupg
  _install_vips
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y -qq nodejs
  export npm_config_platform=linux
  export npm_config_arch=x64
  export npm_config_include_optional=true
  npm uninstall -g @gltf-transform/cli 2>/dev/null || true
  npm install -g @gltf-transform/cli
  CLI_DIR=""
  _repair_sharp || true
}

_install_gltfpack() {
  if command -v gltfpack >/dev/null 2>&1; then
    if gltfpack -v >/dev/null 2>&1 || gltfpack --version >/dev/null 2>&1; then
      return 0
    fi
  fi
  echo "[gltfpack] установка meshoptimizer gltfpack (ubuntu zip)"
  GLTFPACK_VER="${GLTFPACK_VERSION:-1.2}"
  TMPDIR="$(mktemp -d)"
  ZIP_URL="https://github.com/zeux/meshoptimizer/releases/download/v${GLTFPACK_VER}/gltfpack-ubuntu.zip"
  if ! curl -fsSL "${ZIP_URL}" -o "${TMPDIR}/gltfpack.zip"; then
    echo "[gltfpack] FAIL download ${ZIP_URL}"
    rm -rf "${TMPDIR}"
    return 1
  fi
  apt-get install -y -qq unzip 2>/dev/null || true
  if command -v unzip >/dev/null 2>&1; then
    unzip -q -o "${TMPDIR}/gltfpack.zip" -d "${TMPDIR}/extract"
  else
    python3 -c "import zipfile; zipfile.ZipFile('${TMPDIR}/gltfpack.zip').extractall('${TMPDIR}/extract')"
  fi
  GLTF_BIN="$(find "${TMPDIR}/extract" -type f -name gltfpack 2>/dev/null | head -1)"
  if [ -z "${GLTF_BIN}" ] || [ ! -f "${GLTF_BIN}" ]; then
    echo "[gltfpack] FAIL binary not found in zip"
    rm -rf "${TMPDIR}"
    return 1
  fi
  install -m 0755 "${GLTF_BIN}" /usr/local/bin/gltfpack
  rm -rf "${TMPDIR}"
  gltfpack -v 2>/dev/null | head -1 || gltfpack --version 2>/dev/null | head -1 || true
  return 0
}

NEED=0
if ! command -v node >/dev/null 2>&1; then
  NEED=1
else
  NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]")"
  if [ "${NODE_MAJOR}" -lt "${MIN_NODE}" ] 2>/dev/null; then
    NEED=1
  fi
fi

if [ "${NEED}" = "0" ] && ! command -v gltf-transform >/dev/null 2>&1; then
  NEED=1
fi

if [ "${NEED}" = "1" ]; then
  _install_node_cli
else
  if ! _sharp_ok || ! _gltf_transform_ok; then
    _repair_sharp || _install_node_cli
  fi
fi

_install_gltfpack || true

if _gltf_transform_ok; then
  echo "[gltf-transform] OK node=$(node -v) $(gltf-transform --version 2>/dev/null | head -1)"
else
  echo "[gltf-transform] WARN gltf-transform/sharp не работает — compress_draco использует gltfpack/pygltf"
fi
gltfpack --version 2>/dev/null | head -1 || true
pip3 install --no-cache-dir fast-simplification 2>/dev/null || true
