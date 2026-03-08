#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MOBILE_DIR}/.." && pwd)"
SDK_DIR="${REPO_ROOT}/.tools/android-sdk"
ADB="${SDK_DIR}/platform-tools/adb"

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  echo "Usage: ./scripts/logcat-android-local.sh [adb-serial]"
  echo
  echo "Streams logcat lines relevant to the HandsFree Android app and Bluetooth peer bridge."
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

"${ADB}" "${serial_arg[@]}" logcat -v color \
  BluetoothPeerBridge:D \
  GlassesRecorder:D \
  GlassesPlayer:D \
  ExpoGlassesAudio:D \
  ReactNativeJS:I \
  AndroidRuntime:E \
  '*:S'
