# PR-120: iOS autolinking and WAV correctness

## Goal
Ensure the iOS `expo-glasses-audio` module autolinks correctly in React Native projects and that WAV files are recorded and played back with correct headers and parsing behavior on iOS.

## Why
- iOS autolinking for `expo-glasses-audio` can fail or require manual configuration, leading to integration friction and build issues.
- Incorrect or incomplete WAV headers can cause duration/size mismatches and playback problems in iOS audio APIs.
- WAV parsing on iOS must handle files with additional metadata chunks, not just minimal 44-byte headers, to avoid intermittent playback failures.

## Acceptance criteria
- The iOS `expo-glasses-audio` module autolinks without manual changes to Xcode projects for supported React Native configurations.
- WAV files produced or consumed by the iOS implementation have correct headers, with size and duration fields updated consistently.
- The iOS audio pipeline can successfully parse and play WAV files that include non-trivial chunk layouts (e.g., additional metadata) without crashes or silent failures.
