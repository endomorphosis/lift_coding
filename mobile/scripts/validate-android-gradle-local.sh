#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MOBILE_DIR}/.." && pwd)"
DEFAULT_NODE_BIN="${REPO_ROOT}/.tools/node/current/bin/node"
JDK_DIR="${LIFT_CODING_JDK_DIR:-${REPO_ROOT}/.tools/jdk17/current}"
SDK_DIR="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-${REPO_ROOT}/.tools/android-sdk}}"
EXPO_CLI="${MOBILE_DIR}/node_modules/expo/bin/cli"
NODE_BIN="${LIFT_CODING_NODE:-${DEFAULT_NODE_BIN}}"

if [[ ! -x "${NODE_BIN}" ]]; then
  NODE_BIN="$(command -v node || true)"
fi

if [[ -z "${NODE_BIN}" || ! -x "${NODE_BIN}" ]]; then
  echo "Missing Node. Run npm run android:bootstrap:local from mobile/ or install Node >=20.19.4." >&2
  exit 1
fi

if ! "${NODE_BIN}" -e "const [major, minor, patch] = process.versions.node.split('.').map(Number); process.exit(major > 20 || (major === 20 && (minor > 19 || (minor === 19 && patch >= 4))) ? 0 : 1)"; then
  echo "Node >=20.19.4 is required; ${NODE_BIN} reports $("${NODE_BIN}" -v)." >&2
  exit 1
fi

if [[ ! -x "${JDK_DIR}/bin/java" || ! -x "${JDK_DIR}/bin/javac" ]]; then
  echo "Missing local JDK 17 at ${JDK_DIR}. Run npm run android:bootstrap:local from mobile/ first." >&2
  exit 1
fi

if [[ ! -d "${SDK_DIR}/platforms/android-36" || ! -d "${SDK_DIR}/build-tools/36.0.0" ]]; then
  echo "Missing local Android SDK 36 packages at ${SDK_DIR}. Run npm run android:bootstrap:local from mobile/ first." >&2
  exit 1
fi

if [[ ! -f "${EXPO_CLI}" ]]; then
  echo "Missing Expo CLI at ${EXPO_CLI}. Run npm ci in mobile/ first." >&2
  exit 1
fi

export JAVA_HOME="${JDK_DIR}"
export ANDROID_HOME="${SDK_DIR}"
export ANDROID_SDK_ROOT="${SDK_DIR}"
export NODE_ENV="${NODE_ENV:-development}"
export PATH="$(dirname "${NODE_BIN}"):${JAVA_HOME}/bin:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${PATH}"

cd "${MOBILE_DIR}"
"${NODE_BIN}" "${EXPO_CLI}" prebuild --platform android --no-install

mkdir -p "${MOBILE_DIR}/android"
printf 'sdk.dir=%s\n' "${SDK_DIR}" > "${MOBILE_DIR}/android/local.properties"

cd "${MOBILE_DIR}/android"
./gradlew \
  :expo-meta-wearables-dat:compileDebugKotlin \
  :expo-glasses-audio:compileDebugKotlin \
  -PnewArchEnabled=false
