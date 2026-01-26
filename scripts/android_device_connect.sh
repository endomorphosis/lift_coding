#!/usr/bin/env bash
set -euo pipefail

# Android Device Connect Helper
#
# Applies adb reverse for the backend port so the phone can use http://localhost:8080.

BACKEND_PORT="${BACKEND_PORT:-8080}"

have() { command -v "$1" >/dev/null 2>&1; }

die() {
  echo "ERROR: $*" >&2
  exit 1
}

if ! have adb; then
  die "adb not found. Install Android platform-tools and ensure adb is on PATH."
fi

if ! adb get-state >/dev/null 2>&1; then
  die "No device detected. Plug in an Android phone with USB debugging enabled."
fi

echo "Device detected. Applying adb reverse for port ${BACKEND_PORT}..."
adb reverse "tcp:${BACKEND_PORT}" "tcp:${BACKEND_PORT}"

echo "Done. In the mobile app, set Backend URL to http://localhost:${BACKEND_PORT}"
