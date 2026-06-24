# VAI-477 Codebase Scan Finding

Date: 2026-06-24
Fingerprint: 95c78eeaccd016f87b7f01055c05c7b27bf0238c
Kind: annotated_followup
Source: swissknife/ipfs_accelerate_js/test/unit/test_hf_cm3.ts:1
Priority: P2
Track: quality

## Evidence

```text
// FIXME: Complex template literal
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

Replaced the failed Python-to-TypeScript conversion in
`swissknife/ipfs_accelerate_js/test/unit/test_hf_cm3.ts` with a focused,
dependency-free Jest fixture for the CM3 registry, hardware selection, prompt
normalization, dependency reporting, and preview truncation behavior. The stale
`// FIXME: Complex template literal` annotation was removed because the file no
longer contains generated template placeholders.
