# PR-113: Align mobile config/docs to expo-glasses-audio

## Summary
Align the mobile app’s config and key docs to the current local Expo module (`expo-glasses-audio`) used for Meta AI Glasses audio routing.

## Changes
- Remove the legacy `modules/glasses-audio` config plugin reference from `mobile/app.json`.
- Update `mobile/README.md`, `mobile/BUILD_INSTRUCTIONS.md`, and `mobile/glasses/README.md` to reference `modules/expo-glasses-audio` and modern dev-client build steps.

## Test plan
- `cd mobile && npx expo prebuild --platform ios --clean` and verify the native projects generate.
- Build and run dev client on iOS/Android device; confirm Glasses diagnostics no longer mentions legacy module paths.
