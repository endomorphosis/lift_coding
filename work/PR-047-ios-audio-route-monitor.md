# PR-047: iOS audio route monitor (AVAudioSession) + JS bridge — Work Plan

## Context
This repo uses an Expo-managed app under mobile/.
Native glasses work lives under mobile/glasses/ and must be wired into an Expo development build.

## Tasks
- [ ] Implement the native/JS changes for this slice
- [ ] Wire into the Glasses diagnostics screen where relevant
- [ ] Add minimal developer documentation for testing on-device

## References
- mobile/modules/expo-glasses-audio/ios/AudioRouteMonitor.swift
- mobile/modules/expo-glasses-audio/ios/ExpoGlassesAudioModule.swift
- mobile/modules/expo-glasses-audio/index.ts
- mobile/modules/expo-glasses-audio/README.md
- mobile/src/screens/GlassesDiagnosticsScreen.js

## Resolution Notes
VAI-093 resolved the stale scanner finding at the original line 14 by replacing
the broad glasses checklist with the active Expo module route-monitor source, JS
API surface, module documentation, and diagnostics screen evidence for this
iOS audio route slice.
