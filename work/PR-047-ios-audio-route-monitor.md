# PR-047: iOS audio route monitor (AVAudioSession) + JS bridge — Work Plan

## Context
This repo uses an Expo-managed app under mobile/.
Native glasses work lives under mobile/glasses/ and must be wired into an Expo development build.

## Tasks
- [ ] Implement the native/JS changes for this slice
- [ ] Wire into the Glasses diagnostics screen where relevant
- [ ] Add minimal developer documentation for testing on-device

## References
- mobile/glasses/README.md
- mobile/modules/expo-glasses-audio/ios/AudioRouteMonitor.swift
- mobile/modules/expo-glasses-audio/index.ts
- mobile/modules/expo-glasses-audio/README.md
- mobile/src/screens/GlassesDiagnosticsScreen.js
