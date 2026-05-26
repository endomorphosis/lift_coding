# HAO-130 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: 5fce1886e75a4a2dbf45fa4af04d73c097bac18a
Kind: placeholder_runtime_path
Source: src/handsfree/ipfs_accelerate_adapters.py:59
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

Replaced the unsupported direct-import surface placeholder with
`IPFSAccelerateUnavailableError`, the adapter's concrete runtime error for a
missing or unusable `ipfs_accelerate_py` integration surface. Added focused
coverage for the installed-package-without-supported-callables path.
