# UIR-093 recovery receipt — Grok JSON capture + Codex review degradation (2026-08-04)

## Failure

UIR-010 attempt 10 (after UIR-092 oneOf normalize):

1. Primary `grok-4.5` implement **succeeded** and was admitted
   (`response_bytes=5722`, `reason_code=bounded_provider_route`).
2. Independent `codex-independent-review` failed closed with
   `provider_failure` / `response_bytes=0` and empty execution provenance,
   so the route disposition was `pending_degraded` /
   `provider_receipt_degraded` with `review_presence=review_degraded`.
3. No write or merge occurred. Attempt 10 is durably consumed by event
   `sha256:870c9b2ef6894c6cdc272a697bc692a637dd131a36e3b8b66f75fb176e19a41f`,
   sequence **2418**.

Separately, offline reproduction of a full three-file UIR-010 proposal under
`--output-format streaming-json` produced ~1.7 MiB of NDJSON text deltas and
exceeded the previous 1 MiB native capture bound. That path cannot land a
complete multi-file schema even when Grok succeeds.

## Fix

- Production Grok proposals use `--output-format json` (already implied by
  `--json-schema`) so capture holds only the terminal structured object.
- Raise the native CLI capture backstop from 1 MiB to 4 MiB.
- Keep Grok as implementer primary; Terra medium remains implementation
  fallback only on verified Grok 402 balance exhaustion.
- Independent review remains `gpt-5.6-sol`; when Codex is usage-limited the
  route must fail closed as review-degraded (not silently self-review).

Accelerator pin: `b88582d7b564e518c2cdc0b14cf049beb755624f`.

## Release

Completing this repair mints attempt **11** for UIR-010.
