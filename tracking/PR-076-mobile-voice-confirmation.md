# PR-076: Mobile voice confirmation (hands-free) (MVP3)

## Goal
Enable hands-free confirmations by letting the user speak “yes” / “no” (and a few safe synonyms) on the confirmation screen, in addition to tapping buttons.

## Context
The backend confirmation endpoint exists and the mobile confirmation UI exists, but the confirmation flow isn’t fully hands-free. For the Ray-Ban Meta demo, the user should be able to keep the phone in-pocket and confirm via voice.

## Scope
- Mobile-only implementation.
- On the confirmation screen, add a “Voice confirm” option:
  - Capture a short audio snippet (phone mic or glasses mic depending on settings).
  - Send audio to backend for transcription (reuse existing command/audio upload flow if available).
  - Interpret transcript as confirm/cancel.
  - If confirm: call `POST /v1/commands/confirm` with the pending action id.
  - If cancel: dismiss and do not confirm.
- Add clear UX states:
  - listening, processing, understood(confirm/cancel), did-not-understand
- Add a fallback for noisy environments:
  - keep existing Confirm/Cancel buttons

## Non-goals
- Training a custom wake word.
- Full natural-language confirmation parsing beyond yes/no.

## Acceptance criteria
- When a confirmation is shown, user can speak “yes” to confirm and “no” to cancel.
- Works with app in foreground; does not regress existing button-based confirmation.
- If transcript is not understood, app prompts the user to try again and still offers buttons.
- Adds at least one minimal test (unit or integration) for transcript → decision mapping.

## Suggested files
- `mobile/src/screens/ConfirmationScreen.js`
- `mobile/src/api/*` (confirmation call)
- `mobile/src/audio/*` (audio capture helper) or reuse existing recorder code

## Validation
- Mobile: run the app and manually test confirm/cancel by voice.
- If backend is touched: `python -m pytest -q`.
