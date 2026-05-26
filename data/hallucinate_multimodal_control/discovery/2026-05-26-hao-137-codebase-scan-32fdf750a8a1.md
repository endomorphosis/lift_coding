# HAO-137 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: 32fdf750a8a1da4172fa2c1f66d82c7c109a84fe
Kind: placeholder_runtime_path
Source: src/handsfree/ipfs_kit_adapters.py:96
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

Replaced the canonical backend factory placeholder `NotImplementedError` with
`IPFSKitUnavailableError`, matching the adapter's concrete runtime error for an
installed-but-unusable `ipfs_kit_py` integration. Added focused coverage for a
present `ipfs_kit_py.ipfs_backend` module that lacks `get_instance`.
