# PR-065: Demo env template + smoke script

## Goal
Make it easy to run a stable MVP1 demo by providing:
- a `.env.example.demo` template with the minimum required variables
- a smoke script that validates the server and common endpoints

## Scope
Docs + lightweight scripts.

## Deliverables
- `.env.example.demo` with clearly grouped env vars
- `scripts/smoke_demo.py` (or similar) that:
  - checks `/v1/status`
  - checks `/v1/tts`
  - checks `/v1/command` with a short text prompt
  - optionally checks `/v1/notifications` (non-fatal if no subs)
- Update README or docs with how to use it.

## Acceptance criteria
- Running the script exits 0 on success, non-zero on failure.
- Script prints actionable errors.
- Script does not require external services by default (fixture-first).

## Notes
- Keep dependencies minimal; prefer stdlib + existing deps.
