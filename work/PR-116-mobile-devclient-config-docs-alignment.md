# PR-116: Mobile dev-client config + docs alignment (expo-glasses-audio)

## Summary
Remove legacy glasses-audio configuration and align mobile docs/build instructions around the current `expo-glasses-audio` Expo module.

## Changes
- `mobile/app.json`: remove legacy config plugin reference.
- `mobile/BUILD_INSTRUCTIONS.md`: remove bridging header guidance; point at `modules/expo-glasses-audio`.
- `mobile/README.md`: fix remaining legacy module references.
- `mobile/glasses/README.md`: update architecture tree to reflect `modules/expo-glasses-audio` as source of truth.

## Test plan
- Run `npx expo prebuild --platform ios --clean` (macOS).
- Build dev client with `npx expo run:ios --device` and confirm the Glasses Diagnostics screen reports the native module available.
