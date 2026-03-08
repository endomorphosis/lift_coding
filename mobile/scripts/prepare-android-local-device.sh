#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: ./scripts/prepare-android-local-device.sh [adb-serial]"
  echo
  echo "Builds the local debug APK, installs it, grants runtime permissions,"
  echo "and prints install/app-state diagnostics for one connected Android device."
  exit 0
fi

serial="${1:-}"
serial_arg=()
if [[ -n "${serial}" ]]; then
  serial_arg=("${serial}")
fi

"${MOBILE_DIR}/scripts/build-android-debug-local.sh"
"${MOBILE_DIR}/scripts/install-android-debug-apk.sh" "${serial_arg[@]}"
"${MOBILE_DIR}/scripts/grant-android-local-permissions.sh" "${serial_arg[@]}"
"${MOBILE_DIR}/scripts/check-android-local-app.sh" "${serial_arg[@]}"

echo
echo "Android handset is prepared for local BLE diagnostics."
echo "Next: open the Glasses tab and use advertise / scan / connect / ping."
