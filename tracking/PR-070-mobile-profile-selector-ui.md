# PR-070: Mobile profile selector UI (workout/commute/kitchen)

## Goal
Expose the backend profile feature in the mobile UI and consistently send the selected profile with requests.

## Why
Profiles exist in the API contract and backend behavior (verbosity/confirmation tuning), but the mobile UI typically runs in `default` profile.

## Scope
Mobile-only.

## Deliverables
- A profile selector UI (simple picker/buttons) for: `default`, `workout`, `commute`, `kitchen`.
- Persist selected profile in AsyncStorage.
- Ensure the profile is sent with:
  - `POST /v1/command`
  - `GET /v1/inbox` (query param `profile`)
- Show current profile in the main status UI.

## Acceptance criteria
- Switching to `workout` noticeably shortens spoken responses.
- The chosen profile persists across app restarts.

## Test plan
- Manual:
  - Toggle profiles and confirm server responses change.
