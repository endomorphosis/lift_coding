# PR-062: MVP1 demo checklist + script (docs-only)

## Goal
Provide a minimal checklist and spoken script that can be run the same way every time to validate MVP1.

## Scope
- Create a demo checklist doc that includes:
  - pre-demo setup steps (pairing, backend env, network)
  - a short script of voice commands to run in order
  - expected backend responses / success criteria
  - fallback behaviors (phone mic, text mode)
  - a post-demo "artifacts to capture" list (logs, timestamps)

## Deliverables
- `docs/mvp1-demo-checklist.md`

## Acceptance criteria
- A new team member can run MVP1 with this doc alone.
- The checklist is compatible with both stubbed and real STT/TTS.
- References the runbook and queue doc.
