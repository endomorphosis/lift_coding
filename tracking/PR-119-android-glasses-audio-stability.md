# PR-119: Android glasses audio stability

## Goal
Reduce on-device flakiness in the Android `expo-glasses-audio` module by making recording/playback lifecycle handling correct and resilient.

## Why
- The Android recorder implementation had API mismatches vs the module wrapper (output file + stop result), which can lead to build/runtime breakage.
- AudioTrack stop/release can throw depending on state; unhandled exceptions here can cause intermittent failures.
- WAV parsing assumed a fixed 44-byte header; real-world WAV files may include extra chunks (metadata), causing playback failures.

## Acceptance criteria
- `GlassesRecorder.start(...)` accepts an output `File` and records to a valid WAV.
- `GlassesRecorder.stop()` returns `{ file, sizeBytes, durationSeconds }` and updates the WAV header.
- `GlassesPlayer` can parse WAVs with non-trivial chunk layouts and cleans up AudioTrack safely.
