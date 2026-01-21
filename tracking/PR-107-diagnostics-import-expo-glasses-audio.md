# PR-107: Diagnostics import uses expo-glasses-audio package

## Goal
Reduce on-device brittleness by ensuring the Glasses Diagnostics screen imports the native module via the package name (`expo-glasses-audio`) rather than a deep relative path into the module source.

## Why
Deep imports are fragile across bundling/prebuild/dev-client workflows and make it easier to accidentally couple to internal module structure.

## Acceptance criteria
- `mobile/src/screens/GlassesDiagnosticsScreen.js` imports `expo-glasses-audio` via `import ... from 'expo-glasses-audio'`.
- No functional behavior changes beyond the import path.
