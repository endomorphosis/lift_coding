# UIR-092 recovery receipt — Grok oneOf dual-mode proposals (2026-08-04)

## Failure

UIR-010 attempts 8–9 built the exact ~100KB production packet and invoked
tool-free Grok, but the native structured-output enforcer rejected the model
response because the CLI schema used `oneOf` requiring either non-empty
`files` with empty `patch` **or** empty `files` with non-empty `patch`.
Grok commonly emits file bodies plus a dummy non-empty patch string, so
structuredOutput never materializes and the route fails closed with
`provider_failure` / `response_bytes=0` in ~9s.

Offline reproduction with a production-sized prompt captured the stream tail:
`is not valid under any of the schemas listed in the 'oneOf' keyword`.

Failure event `sha256:8f8b90a33f4deaae8d736c2c3287d00a27326f390a2185b9db6d58aed6c521e6` sequence **2378**.

## Fix

- Drop CLI-level `oneOf`; keep exclusive mode in supervisor validation after
  normalizing dual-mode emissions (prefer files when present).
- Surface short Grok stream failure detail on provider attempts.
- Prefer grant-matching board repair revisions when duplicate repair IDs exist.

## Release

Completing this repair mints attempt **10** for UIR-010.
