# UIR-089 recovery receipt — Grok stream structuredOutput (2026-08-04)

## Failure

UIR-010 attempt 6 (after UIR-088 tool allowlist fix):

1. Packet built (~100KB / 25k tokens).
2. Grok CLI ran with disallowed-tools and returned a streaming-json transcript
   ending in `{"type":"end","structuredOutput":{...proposal...}}`.
3. Supervisor extracted the last JSON object but treated the `end` envelope as
   the proposal, so validation failed closed as `provider_failure` with
   response_bytes=0 at the admission layer.

Failure event `sha256:3657e39e084236c9619f331efd83e02bae3e85f4b96929eb7a76a4e121434241`
sequence **2244**.

## Fix

- Parse `structuredOutput` from terminal Grok stream events.
- Deny remaining default tools (`write`, media, workflow helpers).
- Fall through rejected landed-route preflight (`landed_workspace_invalid`) so
  post-repair tips use ordinary sealed correction.

## Release

Completing this repair mints attempt **7** for UIR-010.
