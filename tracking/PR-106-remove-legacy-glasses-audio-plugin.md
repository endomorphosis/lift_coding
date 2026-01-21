# PR-106: Remove legacy glasses-audio config plugin

## Goal
Make the iOS build configuration match the app’s runtime module strategy by removing the legacy `modules/glasses-audio` config plugin from `mobile/app.json`.

## Why
The app runtime is now standardized around `expo-glasses-audio` (Expo Module). Keeping the legacy `glasses-audio` Podfile injection plugin increases build complexity and raises the risk of “it builds but the wrong native module is present”.

## Acceptance criteria
- `mobile/app.json` no longer includes `./modules/glasses-audio/app.plugin.js`.
- Developer docs point to `modules/expo-glasses-audio` as the canonical module.

## Notes
- Removing the plugin does not remove the `modules/glasses-audio` folder; it only stops injecting it into iOS builds.
