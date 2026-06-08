# VAI-266 Codebase Scan Finding

Date: 2026-06-08
Fingerprint: d768e8bb62e512a4ec4059e266aea7bff0bf366a
Kind: swallowed_exception
Source: external/ipfs_kit/archive/applied_patches/ipfs_ipns_operations.py:1501
Priority: P1
Track: runtime

## Evidence

```text
except Exception as resolve_e:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

Removed the redundant inner broad exception swallow from `get_records()`.
`resolve()` already returns structured failures for daemon/request exceptions;
those per-key exceptions are now returned as `resolution_errors`, set the
records result `success` to `False`, and update records metrics as a failed
operation while still returning any records resolved before the error.
