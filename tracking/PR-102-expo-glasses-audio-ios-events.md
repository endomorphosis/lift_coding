# PR-102: expo-glasses-audio iOS recording/playback events + correct stopRecording result

## Why
Before testing on physical iOS devices + Meta AI Glasses, the iOS `expo-glasses-audio` module needs to support the diagnostics UX:
- Start recording, optionally stop early, and get a real recorded file URI back.
- Emit event-based status updates so the JS UI doesn’t rely on timeouts.

Today, iOS `stopRecording()` returns an empty result, and iOS playback does not emit `onPlaybackStatus` events.

## Scope
- Update `mobile/modules/expo-glasses-audio/ios/ExpoGlassesAudioModule.swift` to:
  - Track active recording state (file URL, start time, scheduled stop).
  - Make `stopRecording()` return a real `{ uri, duration, size }`.
  - Emit `onRecordingProgress` events on start/stop.
  - Emit `onPlaybackStatus` events on start/stop/completion.
- Update `mobile/modules/expo-glasses-audio/ios/GlassesPlayer.swift` to support a completion callback.

## Acceptance Criteria
- On iOS, calling `startRecording()` then `stopRecording()` returns a non-empty `uri` pointing to a real file.
- `onRecordingProgress` emits at least (start, stop) events.
- `onPlaybackStatus` emits `isPlaying=true` when playback starts and `isPlaying=false` on completion or stop.
- No changes to backend behavior.
