#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MOBILE_DIR}/.." && pwd)"
SDK_DIR="${REPO_ROOT}/.tools/android-sdk"
ADB="${SDK_DIR}/platform-tools/adb"
PACKAGE_NAME="com.handsfree.mobile"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: ./scripts/check-android-local-app.sh [adb-serial]"
  echo
  echo "Prints install path, granted permissions, and the foreground activity for the app."
  exit 0
fi

if [[ ! -x "${ADB}" ]]; then
  echo "Missing adb at ${ADB}" >&2
  exit 1
fi

serial_arg=()
if [[ $# -ge 1 ]]; then
  serial_arg=(-s "$1")
fi

echo "== Devices =="
"${ADB}" "${serial_arg[@]}" devices

echo
echo "== Package Path =="
"${ADB}" "${serial_arg[@]}" shell pm path "${PACKAGE_NAME}" || true

echo
echo "== Granted Permissions =="
"${ADB}" "${serial_arg[@]}" shell dumpsys package "${PACKAGE_NAME}" | sed -n '/grantedPermissions:/,/runtime permissions:/p' || true

echo
echo "== Top Activity =="
"${ADB}" "${serial_arg[@]}" shell dumpsys activity activities | rg -n "${PACKAGE_NAME}|mResumedActivity|topResumedActivity" || true
