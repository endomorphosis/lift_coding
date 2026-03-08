#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MOBILE_DIR}/.." && pwd)"
SDK_DIR="${REPO_ROOT}/.tools/android-sdk"
ADB="${SDK_DIR}/platform-tools/adb"
APK_PATH="${MOBILE_DIR}/android/app/build/outputs/apk/debug/app-debug.apk"
PACKAGE_NAME="com.handsfree.mobile"
ACTIVITY_NAME="com.handsfree.mobile.MainActivity"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: ./scripts/install-android-debug-apk.sh [adb-serial]"
  echo
  echo "Installs and launches the local debug APK on a connected Android device."
  exit 0
fi

if [[ ! -x "${ADB}" ]]; then
  echo "Missing adb at ${ADB}" >&2
  exit 1
fi

if [[ ! -f "${APK_PATH}" ]]; then
  echo "Missing APK at ${APK_PATH}. Run npm run android:debug:local first." >&2
  exit 1
fi

serial_arg=()
if [[ $# -ge 1 ]]; then
  serial_arg=(-s "$1")
fi

"${ADB}" "${serial_arg[@]}" devices
"${ADB}" "${serial_arg[@]}" install -r "${APK_PATH}"
"${ADB}" "${serial_arg[@]}" shell am start -n "${PACKAGE_NAME}/${ACTIVITY_NAME}"

echo
echo "Installed and launched ${PACKAGE_NAME} from ${APK_PATH}"
