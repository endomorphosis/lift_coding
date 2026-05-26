# HAO-134 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: ce17f5d67a65174befbb41fe0c7e307b239febe3
Kind: placeholder_runtime_path
Source: src/handsfree/ipfs_kit_adapters.py:50
Priority: P1
Track: runtime

## Evidence

```text
raise NotImplementedError(f"ipfs_kit_py.{method} is unavailable: install ipfs_kit_py")
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Remediation

Replaced the missing optional-dependency placeholder `NotImplementedError` path
with `IPFSKitUnavailableError`, a concrete runtime error for unavailable
`ipfs_kit_py` integration. Updated focused adapter coverage to assert the
concrete unavailable error when the optional dependency is absent.
