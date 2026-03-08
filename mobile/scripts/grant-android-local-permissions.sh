#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MOBILE_DIR}/.." && pwd)"
SDK_DIR="${REPO_ROOT}/.tools/android-sdk"
ADB="${SDK_DIR}/platform-tools/adb"
PACKAGE_NAME="com.handsfree.mobile"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: ./scripts/grant-android-local-permissions.sh [adb-serial]"
  echo
  echo "Grants the Bluetooth, microphone, notification, and storage permissions"
  echo "used by the local Android debug build."
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

permissions=(
  android.permission.BLUETOOTH_ADVERTISE
  android.permission.BLUETOOTH_CONNECT
  android.permission.BLUETOOTH_SCAN
  android.permission.RECORD_AUDIO
  android.permission.POST_NOTIFICATIONS
  android.permission.READ_EXTERNAL_STORAGE
  android.permission.WRITE_EXTERNAL_STORAGE
)

for permission in "${permissions[@]}"; do
  "${ADB}" "${serial_arg[@]}" shell pm grant "${PACKAGE_NAME}" "${permission}" || true
done

echo
echo "Requested runtime permission grants for ${PACKAGE_NAME}"
