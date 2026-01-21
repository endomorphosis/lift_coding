# PR-113: Align mobile config/docs to expo-glasses-audio

## Goal
Remove drift between the mobile app’s build configuration/docs and the current native module used for glasses routing (`expo-glasses-audio`).

## Why
`mobile/app.json` and several docs still referenced the legacy `modules/glasses-audio` config plugin and paths, which can lead to building the wrong native setup (or failing builds) when moving onto real devices.

## Acceptance criteria
- `mobile/app.json` no longer references the legacy `modules/glasses-audio` config plugin.
- Primary docs point to `modules/expo-glasses-audio` and `BUILD.md` for dev-client build instructions.
