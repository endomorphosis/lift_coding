# PR-083: Android Expo glasses audio — WAV record + playback

## Goal
Document the landed Android Expo native module (`expo-glasses-audio`) behavior for recording WAV audio and playing WAV audio through the glasses/BT route (SCO), so the end-to-end TTS loop can be tested on Android.

## Context
The Android Expo native module now ships the PR-083 WAV path. The active
bridge at
`mobile/modules/expo-glasses-audio/android/src/main/java/expo/modules/glassesaudio/ExpoGlassesAudioModule.kt`
routes `startRecording` through `GlassesRecorder` and `playAudio` through
`GlassesPlayer`: the recorder writes RIFF/WAV headers plus PCM data and
updates file sizes on stop, while the player parses PCM WAV metadata and plays
mono 16-bit audio through `AudioTrack` using the voice-communication route. The
bridge cleans up SCO routing after playback completion, stop, timeout, or error
paths.

iOS already has working implementations under `mobile/modules/expo-glasses-audio/ios/`.

## Delivered scope
- `startRecording(durationSeconds)` on Android writes valid WAV files
  (PCM 16-bit, mono, 16 kHz) and returns `{ uri, duration, size }` for the
  generated file.
- `playAudio(fileUri)` on Android parses PCM WAV metadata, streams mono
  16-bit samples to `AudioTrack`, emits `onPlaybackStatus` events, and cleans
  up SCO routing on completion, stop, timeout, or error paths.
- The JS/TS module surface exports record/play functions through
  `mobile/modules/expo-glasses-audio/index.ts` and
  `mobile/src/types/expo-glasses-audio.d.ts`.
- `mobile/modules/expo-glasses-audio/README.md` documents the recording and
  playback functions.

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
MGW-109 and VAI-089 both matched stale PR-083 tracking text that treated
Android WAV playback and recording as future work. The current Android
implementation records non-empty WAV files, parses PCM 16-bit mono WAV files
for playback, emits recording/playback events through the Expo bridge, and
cleans up SCO routing on completion, stop, timeout, or playback error paths.
This tracker now records the shipped implementation state so obsolete
follow-up wording is not re-ingested as open work.
