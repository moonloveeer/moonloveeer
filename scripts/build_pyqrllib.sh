#!/usr/bin/env bash
set -euo pipefail

# Optional overrides:
#   PYQRLLIB_VERSION   - version string for the wheel (default: 1.2.4.post1)
#   PYTHON_BIN         - python executable to run setup.py (default: venv/bin/python if present, otherwise python)
#   PYQRLLIB_INSTALL   - if set to 1, install the freshly built wheel via pip

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT}/vendor/qrllib"
DEFAULT_VERSION="1.2.4.post1"
VERSION="${PYQRLLIB_VERSION:-$DEFAULT_VERSION}"

if [[ ! -d "${BUILD_DIR}" ]]; then
  echo "error: expected vendor/qrllib/ directory at ${BUILD_DIR}" >&2
  exit 1
fi

if [[ -d "${ROOT}/venv/bin" ]]; then
  PYTHON_BIN="${PYTHON_BIN:-${ROOT}/venv/bin/python}"
  PIP_BIN="${PIP_BIN:-${ROOT}/venv/bin/pip}"
else
  PYTHON_BIN="${PYTHON_BIN:-python}"
  PIP_BIN="${PIP_BIN:-pip}"
fi

pushd "${BUILD_DIR}" >/dev/null

echo "[pyqrllib] cleaning previous build artifacts"
rm -rf build/ dist/ pyqrllib.egg-info/

echo "[pyqrllib] building wheel with PYQRLLIB_VERSION_OVERRIDE=${VERSION}"
PYQRLLIB_VERSION_OVERRIDE="${VERSION}" "${PYTHON_BIN}" setup.py bdist_wheel -v

WHEEL_PATH="${BUILD_DIR}/dist/pyqrllib-${VERSION}-"*
if ls ${WHEEL_PATH} >/dev/null 2>&1; then
  echo "[pyqrllib] built wheel(s):"
  ls -1 ${WHEEL_PATH}
else
  echo "[pyqrllib] warning: no wheel found in dist/" >&2
fi

if [[ "${PYQRLLIB_INSTALL:-0}" == "1" ]]; then
  echo "[pyqrllib] installing wheel via ${PIP_BIN}"
  "${PIP_BIN}" install --force-reinstall ${WHEEL_PATH}
fi

popd >/dev/null
