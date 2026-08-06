#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${ROOT_DIR}/dist"

rm -rf "${DIST_DIR}"
mkdir -p "${DIST_DIR}/server" "${DIST_DIR}/assets"
cp "${ROOT_DIR}/infra/sites/worker.js" "${DIST_DIR}/server/index.js"
cp -R "${ROOT_DIR}/site/." "${DIST_DIR}/assets/"

test -f "${DIST_DIR}/server/index.js"
test -f "${DIST_DIR}/assets/index.html"
test -f "${DIST_DIR}/assets/assets/logo.svg"
test -f "${DIST_DIR}/assets/assets/logo-white.svg"
