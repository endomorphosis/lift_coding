# UIR-091 recovery receipt — attempt-8 provider_failure diagnostics (2026-08-04)

## Failure

UIR-010 attempt 8 (after UIR-090 timeout + X-tool deny):

1. Repair grant projected and dispatch started on pin `8af0ca4a1`.
2. Packet built (~100KB / 25k tokens); fallthrough on `landed_workspace_invalid`.
3. Grok implement failed in ~9s wall clock with `provider_failure` and
   `response_bytes=0`. Tiny tool-free structured Grok invokes succeed with the
   same deny list, so the large packet path still fails closed without a
   preserved native exception message in the provider receipt.

Failure event `sha256:8ffd2d460fc0eca38426a87ac0bfadff768ef1ef113272c84719373746d40df2` sequence **2335**.

## Fix

- Preserve a short, secret-free exception class+message on provider routing
  failures so the next attempt's receipt distinguishes timeout / tool-call /
  parse / CLI errors.
- Keep 600s timeout and X-tool deny from UIR-090.

## Release

Completing this repair mints attempt **9** for UIR-010.
