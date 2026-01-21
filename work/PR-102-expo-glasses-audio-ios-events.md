# PR-102: expo-glasses-audio iOS recording/playback events + correct stopRecording result

## Status
- [x] Complete (pending review)

## Checklist
- [x] Fix iOS `stopRecording()` to return real file info
- [x] Add `onRecordingProgress` events on iOS
- [x] Add playback completion callback + `onPlaybackStatus` events on iOS
- [ ] Sanity-check Python tests: `python -m pytest -q`

## Notes / Log
- Implemented iOS recording state tracking and event emission in the Expo module.
- Python tests currently fail to collect in this environment due to missing `google` deps (ModuleNotFoundError). Not related to this PR.
