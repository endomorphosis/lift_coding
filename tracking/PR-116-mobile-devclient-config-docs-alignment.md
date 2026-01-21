# PR-116: Mobile dev-client config + docs alignment (expo-glasses-audio)

## Goal
Make on-device builds reliable by ensuring the mobile app config and documentation consistently reference the active native module (`expo-glasses-audio`) and do not require legacy/manual Xcode bridging-header steps.

## Why
The repo currently mixes two generations of the glasses audio module:
- Legacy `modules/glasses-audio` (bridging header, custom config plugin)
- Current `modules/expo-glasses-audio` (Expo Modules API, auto-linked)

This drift causes confusing build instructions and can break `expo prebuild`/dev-client builds.

## Acceptance criteria
- `mobile/app.json` does not reference the legacy `modules/glasses-audio` plugin.
- `mobile/BUILD_INSTRUCTIONS.md`, `mobile/README.md`, and `mobile/glasses/README.md` point to `modules/expo-glasses-audio`.
- No mention of bridging header setup remains in the iOS build instructions.
