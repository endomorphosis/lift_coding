# PR-095: expo-glasses-audio README update (iOS support)

## Goal
Update the `mobile/modules/expo-glasses-audio/README.md` to accurately reflect current iOS support and any required permissions/limitations.

## Context
The module README currently states:
- “⚠️ iOS (not yet implemented)”

…but there is an iOS implementation present in `mobile/modules/expo-glasses-audio/ios/` (route monitor, recorder, player, diagnostics module).

For demo setup, the README should clearly indicate what works on iOS and what remains, plus any iOS permissions / config expectations.

## Scope
- Update `mobile/modules/expo-glasses-audio/README.md`:
  - Mark iOS as supported (with any caveats if needed)
  - Document iOS requirements (e.g., microphone permission, Bluetooth usage notes, audio session behavior)
  - Briefly note any known limitations / WIP items if present

## Non-goals
- Implementing new iOS functionality.
- Changing native code.

## Acceptance criteria
- README no longer claims iOS is unimplemented.
- README provides enough info to run the diagnostics on iOS without guessing.

## Suggested files
- `mobile/modules/expo-glasses-audio/README.md`

## Validation
- Doc review: verify statements match files under `mobile/modules/expo-glasses-audio/ios/`.
