#!/usr/bin/env bash
set -euo pipefail

# Android Emulator Smoke Script (host-run)
#
# Purpose:
# - Sanity-check that an emulator is online
# - Print the correct backend base URL for emulator networking
# - Optionally open the backend status endpoint in the emulator browser
#
# This script intentionally avoids installing/building the mobile app.
# It is meant to be a quick pre-flight before deeper manual testing.

BACKEND_PORT="${BACKEND_PORT:-8080}"
BASE_URL="http://10.0.2.2:${BACKEND_PORT}"
STATUS_PATH="/v1/status"

have() { command -v "$1" >/dev/null 2>&1; }

die() {
  echo "ERROR: $*" >&2
  exit 1
}

if ! have adb; then
  die "adb not found. Install Android platform-tools and ensure adb is on PATH."
fi

# Ensure at least one device is connected.
if ! adb get-state >/dev/null 2>&1; then
  die "No device/emulator detected. Start an Android emulator first."
fi

echo "Emulator/device detected via adb."

echo ""
echo "Backend base URL for emulator: ${BASE_URL}"
echo "Status endpoint: ${BASE_URL}${STATUS_PATH}"

echo ""
echo "Tip: configure the mobile app Backend URL to ${BASE_URL}"

echo ""
if [[ "${OPEN_BROWSER:-0}" == "1" ]]; then
  echo "Opening ${BASE_URL}${STATUS_PATH} in emulator browser..."
  adb shell am start -a android.intent.action.VIEW -d "${BASE_URL}${STATUS_PATH}" >/dev/null || true
  echo "Done."
else
  echo "Set OPEN_BROWSER=1 to open the status URL in the emulator browser."
fi
