# PR-105: expo-glasses-audio import + typing alignment

## Checklist
- [ ] Verify `useGlassesRecorder` still records on iOS
- [ ] Verify glasses/BT mic preference is respected on Android
- [ ] Sanity check playback status listener types

## Notes
- This PR is intentionally small: it focuses on consistency and typing so the on-device debug loop is less fragile.
