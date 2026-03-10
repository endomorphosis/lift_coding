# Expo Meta Wearables DAT

Reference Expo module for HandsFree Meta Wearables DAT integration.

Current scope:

- safe JS wrapper when the native module is not linked yet
- diagnostics, capability discovery, and session-state access
- Expo config plugin support for iOS `Info.plist` and Android manifest metadata
- bridge-first baseline for future DAT SDK session and media capture wiring

This module is intentionally not a full DAT feature surface yet. It provides a stable contract for diagnostics and incremental rollout while native SDK linking, packaging, and platform-specific session flows are hardened.