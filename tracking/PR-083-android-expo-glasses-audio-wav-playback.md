# PR-083: Android Expo glasses audio — WAV record + playback

## Goal
Make the Android Expo native module (`expo-glasses-audio`) actually record to WAV and play WAV audio through the glasses/BT route (SCO) so the end-to-end TTS loop can be tested on Android.

## Context
PR-083 is implemented in the Android Expo native module. `ExpoGlassesAudioModule.kt`
now routes `startRecording` through `GlassesRecorder` and `playAudio` through
`GlassesPlayer`: the recorder writes RIFF/WAV headers plus PCM data and updates
file sizes on stop, while the player parses PCM WAV metadata and plays mono
16-bit audio through `AudioTrack` using the voice-communication route.

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

## Implementation status
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/ExpoGlassesAudioModule.kt` exposes `startRecording`, `stopRecording`, `playAudio`, and `stopPlayback`, emits recording/playback status events, and restores SCO/audio mode after completion or errors.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesRecorder.kt` records 16 kHz mono PCM through `AudioRecord`, writes samples to the WAV file, and updates the RIFF/data chunk sizes when recording stops.
- `mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/GlassesPlayer.kt` validates RIFF/WAVE headers, supports PCM 16-bit mono WAV files, converts data to samples, and plays them with `AudioTrack`.
- `mobile/modules/expo-glasses-audio/index.ts`, `mobile/src/types/expo-glasses-audio.d.ts`, and `mobile/modules/expo-glasses-audio/README.md` document and export the record/play module surface.
- Remaining validation is hardware-facing Android device verification of audible playback and SCO cleanup.

## Resolution notes
HAO-163 resolved the stale scanner finding at line 7. The earlier context
described missing Android WAV playback and recording work, but the current code
implements both paths through `GlassesPlayer` and `GlassesRecorder`. This
tracker now records the shipped implementation state so stale follow-up wording
is not re-ingested as open work.

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
