# Dockerized Android Emulator Runner (Linux/KVM)

This document describes an **optional** approach: running an Android emulator inside Docker.

This can be useful for:
- onboarding (a single, containerized toolchain)
- a reproducible “emulator runner” for smoke workflows

It is **not** a replacement for:
- physical device testing
- Bluetooth accessory pairing/routing

## Constraints

- Works best on **Linux** with KVM.
- Requires passing `/dev/kvm` into the container.
- Many CI providers do not allow KVM → software emulation is usually too slow.

## Recommended baseline approach

Prefer:
- backend in Docker
- emulator on host (Android Studio)

Only use “emulator in Docker” if you have a strong reason.

## Proposed compose profile (future)

A follow-up PR may add:
- a `docker-compose.emulator.yml` or compose `profiles` entry
- a container image that runs the Android emulator headless
- a way to connect ADB (`adb connect`) from the host

## Networking

From emulator → host:
- `10.0.2.2` is the emulator’s view of the host, but in containerized setups this may differ.

A follow-up PR should document the exact networking model selected.

