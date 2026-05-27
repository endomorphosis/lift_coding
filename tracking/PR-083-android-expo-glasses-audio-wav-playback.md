# PR-083: Android Expo glasses audio — WAV record + playback

## Goal
Document the landed Android Expo native module (`expo-glasses-audio`) behavior for recording WAV audio and playing WAV audio through the glasses/BT route (SCO), so the end-to-end TTS loop can be tested on Android.

## Context
PR-083 is implemented in the active Expo module. Android `startRecording` now delegates to `GlassesRecorder`, which writes a RIFF/WAVE header, appends PCM 16-bit mono audio data, and updates the header sizes when recording stops. Android `playAudio` now delegates to `GlassesPlayer`, which parses PCM WAV metadata, reads PCM samples, plays them with `AudioTrack`, and lets the bridge clean up SCO routing after playback completion or errors.

iOS already has working implementations under `mobile/modules/expo-glasses-audio/ios/`.

## Scope
- Implement `startRecording(durationSeconds)` on Android to:
  - write a valid WAV file (PCM 16-bit, mono; target 16kHz)
  - return `{ uri, duration, size }` where the file exists and is non-zero
- Implement `playAudio(fileUri)` on Android to:
  - parse WAV header (at minimum support PCM 16-bit mono)
  - stream PCM to `AudioTrack` (or existing `GlassesPlayer.playPcm16Mono` after decoding)
  - stop/cleanup SCO routing on completion
  - emit `onPlaybackStatus` events (started/ended/error)
- Ensure module API is consumable from JS:
  - Export the `ExpoGlassesAudio` module surface in `mobile/modules/expo-glasses-audio/index.ts` (or clearly separate route-monitor vs record/play exports)
  - Update TypeScript types under `mobile/src/types/` as needed
- Update module docs (`mobile/modules/expo-glasses-audio/README.md`) to include recording/playback functions.

## Non-goals
- Perfect WAV compatibility (only what our backend TTS and dev files produce).
- Background audio support.

## Acceptance criteria
- On Android physical device:
  - `startRecording(3)` produces a readable WAV file with non-zero size.
  - `playAudio(uri)` plays audibly and completes without leaving SCO stuck on.
  - Basic playback status events are observable.
- No regressions to iOS module.

## Suggested files
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/ExpoGlassesAudioModule.kt`
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesRecorder.kt`
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesPlayer.kt`
- `mobile/modules/expo-glasses-audio/index.ts`
- `mobile/modules/expo-glasses-audio/README.md`
- `mobile/src/types/expo-glasses-audio.d.ts`

## Validation
- Android build via the existing mobile build instructions.
- Basic lint/typecheck if available in `mobile/`.

## References
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/ExpoGlassesAudioModule.kt` - active Expo bridge for recording, playback, SCO setup/cleanup, and status events.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesRecorder.kt` - active Android recorder that writes PCM data into WAV files and updates WAV sizes on stop.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesPlayer.kt` - active Android WAV parser and PCM playback implementation.
- `mobile/modules/expo-glasses-audio/index.ts` - JS/TS module surface for recording and playback.
- `mobile/modules/expo-glasses-audio/README.md` - module API and Android recording/playback behavior.

## Resolution notes
The prior context line was stale. The current Android implementation records
non-empty WAV files, parses PCM 16-bit mono WAV files for playback, emits
recording/playback events through the Expo bridge, and cleans up SCO routing on
completion, stop, timeout, or playback error paths.
