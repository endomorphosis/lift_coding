# PR-048: iOS glasses Bluetooth recorder (16kHz WAV) + JS bridge — Work Plan

## Context
This repo uses an Expo-managed app under mobile/.
Native glasses work lives under mobile/glasses/ and must be wired into an Expo development build.

## Tasks
- [ ] Implement the native/JS changes for this slice
- [ ] Wire into the Glasses diagnostics screen where relevant
- [ ] Add minimal developer documentation for testing on-device

## References
- mobile/glasses/README.md
- mobile/modules/expo-glasses-audio/ios/GlassesRecorder.swift
- mobile/modules/expo-glasses-audio/ios/ExpoGlassesAudioModule.swift
- mobile/modules/expo-glasses-audio/index.ts
- mobile/modules/expo-glasses-audio/README.md
- mobile/src/screens/GlassesDiagnosticsScreen.js

## Resolution notes
MGW-111 resolved the stale scanner finding at the original line 14 by removing
the broad glasses checklist from this PR-048 reference list. That checklist still
tracks unrelated iOS, Android, validation, and polish follow-up work, while this
work plan is now anchored to the active iOS recorder source, native bridge, JS
API surface, module documentation, and diagnostics screen evidence for the
16kHz WAV recorder slice.
