# PR-088: Mobile UX — repeat/next quick controls

## Goal
Add a simple, demo-friendly mobile UX for "repeat" and "next" navigation primitives so users can move through inbox and PR summaries without retyping commands.

## Context
The backend supports "repeat/next" navigation primitives server-side (MVP2), but the mobile app lacks dedicated UX affordances.

## Scope
- Add UI controls (buttons) for:
  - Repeat last spoken response
  - Next item (advance in the current inbox/summary context)
- Ensure controls work for both:
  - text command mode
  - audio command mode (where applicable)
- Persist minimal state on-device to support repeat behavior:
  - last `spoken_text`
  - last `command_id` or last command text (whichever the API supports cleanly)
- If the server expects specific commands, implement as sending canonical text commands (e.g., "repeat", "next").

## Non-goals
- Full hands-free voice UX (covered elsewhere).
- Major UI redesign.

## Acceptance criteria
- From the main command screen, a user can tap:
  - **Repeat** → replays the most recent response (TTS) or requests repeat from server.
  - **Next** → advances to the next item in the current inbox/summary sequence.
- Behavior is clearly documented in the screen (small helper text).

## Suggested files
- `mobile/src/screens/CommandScreen.js`
- `mobile/src/api/client.js`

## Validation
- Manual: issue an `inbox` or `pr summarize` command and use Repeat/Next.
