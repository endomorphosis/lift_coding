# PR-046: Expo dev client + native module plumbing (glasses) — Work Plan

## Context
This repo uses an Expo-managed app under mobile/.
Native glasses work lives under mobile/glasses/ and must be wired into an Expo development build.

## Tasks
- [ ] Implement the native/JS changes for this slice
- [ ] Wire into the Glasses diagnostics screen where relevant
- [ ] Add minimal developer documentation for testing on-device

## References
- mobile/glasses/README.md
- mobile/BUILD.md
- mobile/IMPLEMENTATION_SUMMARY.md
- mobile/modules/expo-glasses-audio/README.md
- mobile/modules/expo-glasses-audio/expo-module.config.json
- mobile/src/screens/GlassesDiagnosticsScreen.js

## Resolution notes
VAI-092 removed the broad glasses implementation checklist from this PR-046
reference list because it still tracks unrelated iOS, Android, testing, and
polish follow-up work. PR-046 is now anchored to the concrete Expo
development-client docs, implementation summary, module config/API docs, and the
diagnostics screen that exercise the native glasses plumbing.

HAO-166 resolved the stale scanner finding at the original line 14 by verifying
that the broad checklist is no longer a PR-046 reference. This work plan remains
scoped to the Expo dev-client build docs, active native module docs/config,
implementation summary, and diagnostics screen evidence for this slice.
