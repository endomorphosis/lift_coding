# HAO-140 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: 1ea0adf2e36ad8885d5a04559b3dca277c315983
Kind: placeholder_runtime_path
Source: src/handsfree/ipfs_kit_adapters.py:137
Priority: P1
Track: runtime

## Evidence

```text
raise NotImplementedError(
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Remediation

Replaced the `cat` backend-missing placeholder `NotImplementedError` path with a
real backend `get` fallback, matching the upstream `ipfs_kit_py.ipfs_backend`
read surface. When neither `cat` nor `get` is available, the adapter now raises
`IPFSKitUnavailableError` with a concrete missing-surface message. Added focused
coverage for both the `get` fallback and the missing read-helper error.
