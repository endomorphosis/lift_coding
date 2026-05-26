# VAI-038 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: b7a1b442e24bd4919f1e43d056cfb38ecc64fedc
Kind: placeholder_runtime_path
Source: src/handsfree/ipfs_kit_adapters.py:147
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

Replaced the `cat` backend-missing placeholder `NotImplementedError` path with
the adapter's concrete `IPFSKitUnavailableError`. The adapter now also falls
back to a backend `get` callable after `cat`, matching the upstream
`ipfs_kit_py.ipfs_backend.IPFSBackend` retrieval surface and the README's
documented `api.get(cid)` content-read path.
