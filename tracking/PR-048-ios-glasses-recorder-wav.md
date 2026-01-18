# PR-048: iOS glasses Bluetooth recorder (16kHz WAV) + JS bridge

## Goal
Ship the next slice of the native Meta AI glasses Bluetooth audio path.

## Scope
- Implementation work described below
- Add/extend tests where practical (unit-level for JS; native tests optional)
- Keep CI green

## Acceptance criteria
- The feature can be exercised in a development build on a physical device.
- The diagnostics screen exposes enough state to validate routing/recording/playback.

## Notes
- This PR is intentionally scaffold-only initially; implementation lands in follow-up commits on this branch.
