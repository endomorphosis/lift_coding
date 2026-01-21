# PR-105: expo-glasses-audio import + typing alignment

## Goal
Make the app’s JS usage of `expo-glasses-audio` consistent and safe for device testing by:
- Importing the module via its package name (`expo-glasses-audio`) instead of deep/relative paths.
- Aligning local TypeScript declarations with the runtime API.

## Why
We have native support for optional `audioSource` selection and native event-driven status, but JS callsites and typings were inconsistent. This creates “works in dev, breaks on device” risk and makes it easier to accidentally call the wrong module entrypoint.

## Acceptance criteria
- `useGlassesRecorder` imports `expo-glasses-audio` via package name.
- Local TS declaration module name matches the package import.
- Type signatures match runtime shapes (route + playback status).

## Non-goals
- Refactor diagnostics screen flows (covered by other PRs).
- Change native iOS/Android audio behavior.
