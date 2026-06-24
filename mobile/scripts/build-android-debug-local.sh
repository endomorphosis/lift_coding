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
HOST_ARCH="$(uname -m)"
ARM64_NDK_VERSION="${LIFT_CODING_ANDROID_ARM64_NDK_VERSION:-29.0.14206865}"
ARM64_CMAKE_DIR="${LIFT_CODING_ANDROID_ARM64_CMAKE_DIR:-${REPO_ROOT}/.tools/cmake-arm64}"
ARM64_SDK_TOOLS_VERSION="${LIFT_CODING_ANDROID_ARM64_SDK_TOOLS_VERSION:-35.0.2}"
ARM64_AAPT2="${LIFT_CODING_ANDROID_ARM64_AAPT2:-${REPO_ROOT}/.tools/android-arm64/sdk-tools/${ARM64_SDK_TOOLS_VERSION}/build-tools/aapt2}"
ARM64_COMPAT_LIB="${LIFT_CODING_ANDROID_ARM64_COMPAT_LIB:-${REPO_ROOT}/.tools/android-arm64/compat-lib}"
ARM64_ARCHITECTURES="${LIFT_CODING_ANDROID_ARM64_ARCHITECTURES:-arm64-v8a}"

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

if [[ ! -d "${SDK_DIR}/platforms" || ! -d "${SDK_DIR}/build-tools" ]]; then
  echo "Missing local Android SDK packages at ${SDK_DIR}. Run npm run android:bootstrap:local from mobile/ first." >&2
  exit 1
fi

if [[ ! -f "${EXPO_CLI}" ]]; then
  echo "Missing Expo CLI at ${EXPO_CLI}. Run npm install in mobile/ first." >&2
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
GRADLE_ARGS=("assembleDebug")
LOCAL_PROPERTIES=("sdk.dir=${SDK_DIR}")

if [[ "${HOST_ARCH}" =~ ^(aarch64|arm64)$ ]]; then
  if [[ -d "${SDK_DIR}/ndk/${ARM64_NDK_VERSION}" &&
        -x "${ARM64_CMAKE_DIR}/bin/cmake" &&
        -x "${ARM64_CMAKE_DIR}/bin/ninja" &&
        -x "${ARM64_AAPT2}" &&
        -e "${ARM64_COMPAT_LIB}/libxml2.so.16" ]]; then
    LOCAL_PROPERTIES+=("cmake.dir=${ARM64_CMAKE_DIR}")
    export LD_LIBRARY_PATH="${ARM64_COMPAT_LIB}:${LD_LIBRARY_PATH:-}"
    GRADLE_ARGS+=(
      "-PndkVersion=${ARM64_NDK_VERSION}"
      "-Pandroid.aapt2FromMavenOverride=${ARM64_AAPT2}"
    )
    if [[ -n "${ARM64_ARCHITECTURES}" ]]; then
      GRADLE_ARGS+=("-PreactNativeArchitectures=${ARM64_ARCHITECTURES}")
    fi
    echo "Using unofficial Linux ARM64 Android APK toolchain (${ARM64_NDK_VERSION}, ${ARM64_SDK_TOOLS_VERSION})."
  elif [[ "${LIFT_CODING_ANDROID_ALLOW_ARM_FULL_APK:-}" != "1" ]]; then
    echo "Full APK assembly on Linux ARM requires the optional unofficial ARM64 Android toolchain." >&2
    echo "Run npm run android:bootstrap:arm64:local, then retry npm run android:debug:local." >&2
    echo "For the official Google toolchain validation gate, run npm run android:validate:local." >&2
    exit 2
  fi
fi

{
  for property in "${LOCAL_PROPERTIES[@]}"; do
    printf '%s\n' "${property}"
  done
} > "${MOBILE_DIR}/android/local.properties"

if [[ "${LIFT_CODING_ANDROID_NEW_ARCH:-auto}" == "auto" ]]; then
  case "${HOST_ARCH}" in
    aarch64|arm64)
      GRADLE_ARGS+=("-PnewArchEnabled=false")
      ;;
  esac
elif [[ -n "${LIFT_CODING_ANDROID_NEW_ARCH}" ]]; then
  GRADLE_ARGS+=("-PnewArchEnabled=${LIFT_CODING_ANDROID_NEW_ARCH}")
fi

cd "${MOBILE_DIR}/android"
./gradlew "${GRADLE_ARGS[@]}"

echo
echo "APK ready at ${MOBILE_DIR}/android/app/build/outputs/apk/debug/app-debug.apk"
