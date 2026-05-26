# HAO-139 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: 7cdc6c25a5e11fa670650d259c05436b7c715aa6
Kind: placeholder_runtime_path
Source: src/handsfree/ipfs_kit_adapters.py:122
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

Replaced the `add_bytes` backend-missing placeholder `NotImplementedError` path
with `IPFSKitUnavailableError`, matching the adapter's concrete runtime error
for an installed but unusable `ipfs_kit_py` content-add integration. Added
focused coverage for a backend that exposes neither `add_bytes` nor `add_str`.
