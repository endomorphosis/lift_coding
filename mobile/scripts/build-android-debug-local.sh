#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MOBILE_DIR}/.." && pwd)"
JDK_DIR="${REPO_ROOT}/.tools/jdk17/jdk-17.0.18+8"
SDK_DIR="${REPO_ROOT}/.tools/android-sdk"
EXPO_CLI="${MOBILE_DIR}/node_modules/expo/bin/cli"

if [[ ! -x "${JDK_DIR}/bin/java" ]]; then
  echo "Missing local JDK 17 at ${JDK_DIR}" >&2
  exit 1
fi

if [[ ! -x "${SDK_DIR}/platform-tools/adb" ]]; then
  echo "Missing local Android SDK at ${SDK_DIR}" >&2
  exit 1
fi

if [[ ! -f "${EXPO_CLI}" ]]; then
  echo "Missing Expo CLI at ${EXPO_CLI}. Run npm install in mobile/ first." >&2
  exit 1
fi

export JAVA_HOME="${JDK_DIR}"
export ANDROID_HOME="${SDK_DIR}"
export ANDROID_SDK_ROOT="${SDK_DIR}"
export PATH="${JAVA_HOME}/bin:${ANDROID_HOME}/platform-tools:${PATH}"

printf 'sdk.dir=%s\n' "${SDK_DIR}" > "${MOBILE_DIR}/android/local.properties"

cd "${MOBILE_DIR}"
npx -y node@20 "${EXPO_CLI}" prebuild --platform android --no-install

cd "${MOBILE_DIR}/android"
./gradlew assembleDebug

echo
echo "APK ready at ${MOBILE_DIR}/android/app/build/outputs/apk/debug/app-debug.apk"
