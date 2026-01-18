# MVP1 demo checklist

## Pre-flight
- Glasses paired and connected (Bluetooth).
- iPhone and backend on reachable network.
- Backend is running; verify `GET /v1/status`.

## Backend configuration (choose one)

### Option A: deterministic demo (stub STT/TTS)
- Use stub STT/TTS; audio input will transcribe to a known command.

### Option B: realistic demo (OpenAI STT/TTS)
- Enable STT/TTS providers and ensure `OPENAI_API_KEY` is set.

## Demo script (recommended)
1) Say: “show my inbox”
   - Expected: backend returns `CommandResponse` with `spoken_text` summarizing inbox.
   - Expected: audio playback through glasses.

2) Say: “next”
   - Expected: next item is spoken.

3) Say: “repeat”
   - Expected: last response is spoken again.

4) Say: “summarize PR 123” (or a known fixture PR)
   - Expected: a short summary including checks/review info.

## Fallbacks
- If headset mic input is unreliable, record from phone mic.
- If STT is disabled, use text input for the demo.

## Capture artifacts
- Timestamped backend logs for each command.
- The raw `CommandResponse` JSON for each step.
- Any route diagnostics screenshots from the iOS app.

## References
- MVP1 runbook: tracking/PR-059-ios-rayban-mvp1-demo-runbook.md
- Implementation queue: docs/ios-rayban-implementation-queue.md
