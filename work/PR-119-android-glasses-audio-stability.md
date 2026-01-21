# PR-119: Android glasses audio stability

## Summary
Fix Android native module recorder/playback stability issues and make WAV handling more robust.

## Changes
- `GlassesRecorder`:
  - Accept output file in `start(outputFile, audioSource)`.
  - Add `RecordingResult` return from `stop()`.
  - Harden AudioRecord init/stop/release and recording thread shutdown.
- `GlassesPlayer`:
  - Make `stop()` resilient to AudioTrack state errors.
  - Parse WAV by scanning chunks (supports extra chunks before `data`).

## Test plan
- Build the Expo dev-client for Android with `expo-glasses-audio` included.
- On-device:
  - Record from phone mic and (if available) Bluetooth SCO.
  - Play back a WAV recorded by the module.
  - Play back a backend-generated WAV that may include metadata chunks.
