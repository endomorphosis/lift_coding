#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MOBILE_DIR}/.." && pwd)"
TOOLS_DIR="${REPO_ROOT}/.tools"
DOWNLOAD_DIR="${TOOLS_DIR}/downloads"
SDK_DIR="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-${TOOLS_DIR}/android-sdk}}"
JDK_CURRENT="${TOOLS_DIR}/jdk17/current"
ARM_ROOT="${TOOLS_DIR}/android-arm64"
ARM_NDK_ROOT="${ARM_ROOT}/ndk"
ARM_NDK_CURRENT="${ARM_NDK_ROOT}/current"
ARM_NDK_VERSION="${LIFT_CODING_ANDROID_ARM64_NDK_VERSION:-29.0.14206865}"
ARM_NDK_URL="${LIFT_CODING_ANDROID_ARM64_NDK_URL:-https://github.com/SnowNF/ndk-aarch64-linux/releases/download/0.0.2/android-ndk-r29-linux-aarch64.tar.gz}"
ARM_NDK_ARCHIVE="${DOWNLOAD_DIR}/android-ndk-r29-linux-aarch64.tar.gz"
ARM_SDK_TOOLS_VERSION="${LIFT_CODING_ANDROID_ARM64_SDK_TOOLS_VERSION:-35.0.2}"
ARM_SDK_TOOLS_URL="${LIFT_CODING_ANDROID_ARM64_SDK_TOOLS_URL:-https://github.com/lzhiyong/android-sdk-tools/releases/download/35.0.2/android-sdk-tools-static-aarch64.zip}"
ARM_SDK_TOOLS_ARCHIVE="${DOWNLOAD_DIR}/android-sdk-tools-static-aarch64-${ARM_SDK_TOOLS_VERSION}.zip"
ARM_SDK_TOOLS_DIR="${ARM_ROOT}/sdk-tools/${ARM_SDK_TOOLS_VERSION}"
ARM_CMAKE_DIR="${TOOLS_DIR}/cmake-arm64"
NINJA_VENV="${TOOLS_DIR}/ninja-venv"
COMPAT_LIB_DIR="${ARM_ROOT}/compat-lib"

case "$(uname -m)" in
  aarch64|arm64) ;;
  *)
    echo "This optional toolchain is only needed on Linux ARM64 hosts." >&2
    exit 2
    ;;
esac

if [[ ! -x "${JDK_CURRENT}/bin/java" || ! -d "${SDK_DIR}/platforms/android-36" || ! -d "${SDK_DIR}/build-tools/36.0.0" ]]; then
  "${SCRIPT_DIR}/bootstrap-android-local-toolchain.sh"
fi

mkdir -p "${DOWNLOAD_DIR}" "${ARM_NDK_ROOT}" "${ARM_SDK_TOOLS_DIR}" "${ARM_CMAKE_DIR}/bin" "${COMPAT_LIB_DIR}"

if [[ ! -x "${ARM_NDK_CURRENT}/toolchains/llvm/prebuilt/linux-x86_64/bin/clang" ]]; then
  echo "Installing unofficial Linux ARM64 Android NDK into ${ARM_NDK_ROOT}"
  curl -fL "${ARM_NDK_URL}" -o "${ARM_NDK_ARCHIVE}"
  rm -rf "${ARM_NDK_ROOT}/r29" "${ARM_NDK_CURRENT}"
  tar -xzf "${ARM_NDK_ARCHIVE}" -C "${ARM_NDK_ROOT}"
  ln -sfn r29 "${ARM_NDK_CURRENT}"
fi

mkdir -p "${SDK_DIR}/ndk"
ln -sfn "${ARM_NDK_CURRENT}" "${SDK_DIR}/ndk/${ARM_NDK_VERSION}"

if [[ ! -x "${ARM_SDK_TOOLS_DIR}/build-tools/aapt2" ]]; then
  echo "Installing unofficial Linux ARM64 Android SDK build tools into ${ARM_SDK_TOOLS_DIR}"
  curl -fL "${ARM_SDK_TOOLS_URL}" -o "${ARM_SDK_TOOLS_ARCHIVE}"
  rm -rf "${ARM_SDK_TOOLS_DIR}"
  mkdir -p "${ARM_SDK_TOOLS_DIR}"
  unzip -q "${ARM_SDK_TOOLS_ARCHIVE}" -d "${ARM_SDK_TOOLS_DIR}"
fi

CMAKE_BIN="${LIFT_CODING_CMAKE:-$(command -v cmake || true)}"
if [[ -z "${CMAKE_BIN}" || ! -x "${CMAKE_BIN}" ]]; then
  echo "Missing ARM64 CMake on PATH. Install cmake or set LIFT_CODING_CMAKE." >&2
  exit 1
fi
ln -sfn "${CMAKE_BIN}" "${ARM_CMAKE_DIR}/bin/cmake"

if [[ ! -x "${NINJA_VENV}/bin/ninja" ]]; then
  echo "Installing repo-local ARM64 Ninja into ${NINJA_VENV}"
  python3 -m venv "${NINJA_VENV}"
  "${NINJA_VENV}/bin/python" -m pip install --upgrade pip
  "${NINJA_VENV}/bin/python" -m pip install ninja
fi
ln -sfn "${NINJA_VENV}/bin/ninja" "${ARM_CMAKE_DIR}/bin/ninja"

LIBXML_TARGET="$(
  ldconfig -p 2>/dev/null | awk '/libxml2\.so\.16 .*AArch64/ { print $NF; exit }' || true
)"
if [[ -z "${LIBXML_TARGET}" ]]; then
  LIBXML_TARGET="$(
    ldconfig -p 2>/dev/null | awk '/libxml2\.so\.2 .*AArch64/ { print $NF; exit }' || true
  )"
fi
if [[ -z "${LIBXML_TARGET}" || ! -r "${LIBXML_TARGET}" ]]; then
  echo "Missing host ARM64 libxml2 runtime for the unofficial ARM NDK linker." >&2
  exit 1
fi
ln -sfn "${LIBXML_TARGET}" "${COMPAT_LIB_DIR}/libxml2.so.16"

export LD_LIBRARY_PATH="${COMPAT_LIB_DIR}:${LD_LIBRARY_PATH:-}"
"${ARM_NDK_CURRENT}/toolchains/llvm/prebuilt/linux-x86_64/bin/ld.lld" --version >/dev/null 2>&1
"${ARM_SDK_TOOLS_DIR}/build-tools/aapt2" version >/dev/null 2>&1
"${ARM_CMAKE_DIR}/bin/cmake" --version >/dev/null 2>&1
"${ARM_CMAKE_DIR}/bin/ninja" --version >/dev/null 2>&1

echo
echo "Unofficial Linux ARM64 Android APK toolchain ready:"
echo "  NDK: ${SDK_DIR}/ndk/${ARM_NDK_VERSION}"
echo "  CMake dir: ${ARM_CMAKE_DIR}"
echo "  AAPT2: ${ARM_SDK_TOOLS_DIR}/build-tools/aapt2"
echo "  Runtime shim: ${COMPAT_LIB_DIR}/libxml2.so.16 -> ${LIBXML_TARGET}"
echo
echo "Build with:"
echo "  npm run android:debug:local"
