#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOBILE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${MOBILE_DIR}/.." && pwd)"
TOOLS_DIR="${REPO_ROOT}/.tools"
DOWNLOAD_DIR="${TOOLS_DIR}/downloads"
JDK_ROOT="${TOOLS_DIR}/jdk17"
JDK_CURRENT="${JDK_ROOT}/current"
SDK_DIR="${TOOLS_DIR}/android-sdk"
CMDLINE_TOOLS_URL="${ANDROID_CMDLINE_TOOLS_URL:-https://dl.google.com/android/repository/commandlinetools-linux-13114758_latest.zip}"
JDK_URL="${JDK17_URL:-https://api.adoptium.net/v3/binary/latest/17/ga/linux/aarch64/jdk/hotspot/normal/eclipse?project=jdk}"
ANDROID_PACKAGES=(
  "platform-tools"
  "platforms;android-36"
  "build-tools;36.0.0"
  "ndk;27.1.12297006"
)

mkdir -p "${DOWNLOAD_DIR}" "${JDK_ROOT}" "${SDK_DIR}/cmdline-tools"

if [[ ! -x "${JDK_CURRENT}/bin/java" || ! -x "${JDK_CURRENT}/bin/javac" ]]; then
  echo "Installing repo-local JDK 17 into ${JDK_ROOT}"
  curl -fL "${JDK_URL}" -o "${DOWNLOAD_DIR}/jdk17-linux-aarch64.tar.gz"
  rm -rf "${JDK_ROOT}"/jdk-* "${JDK_ROOT}/current"
  tar -xzf "${DOWNLOAD_DIR}/jdk17-linux-aarch64.tar.gz" -C "${JDK_ROOT}"
  JDK_EXTRACTED="$(find "${JDK_ROOT}" -maxdepth 1 -type d -name 'jdk-*' | sort | tail -1)"
  if [[ -z "${JDK_EXTRACTED}" ]]; then
    echo "Unable to locate extracted JDK under ${JDK_ROOT}" >&2
    exit 1
  fi
  ln -sfn "$(basename "${JDK_EXTRACTED}")" "${JDK_CURRENT}"
fi

if [[ ! -x "${SDK_DIR}/cmdline-tools/latest/bin/sdkmanager" ]]; then
  echo "Installing Android command-line tools into ${SDK_DIR}"
  curl -fL "${CMDLINE_TOOLS_URL}" -o "${DOWNLOAD_DIR}/android-commandlinetools.zip"
  rm -rf "${SDK_DIR}/cmdline-tools/latest" "${SDK_DIR}/cmdline-tools/cmdline-tools"
  unzip -q "${DOWNLOAD_DIR}/android-commandlinetools.zip" -d "${SDK_DIR}/cmdline-tools"
  mv "${SDK_DIR}/cmdline-tools/cmdline-tools" "${SDK_DIR}/cmdline-tools/latest"
fi

export JAVA_HOME="${JDK_CURRENT}"
export ANDROID_HOME="${SDK_DIR}"
export ANDROID_SDK_ROOT="${SDK_DIR}"
export PATH="${JAVA_HOME}/bin:${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${PATH}"

yes | sdkmanager --sdk_root="${SDK_DIR}" --licenses >/dev/null || true
sdkmanager --sdk_root="${SDK_DIR}" --install "${ANDROID_PACKAGES[@]}"

echo
echo "Android local toolchain ready:"
echo "  JAVA_HOME=${JAVA_HOME}"
echo "  ANDROID_SDK_ROOT=${ANDROID_SDK_ROOT}"
