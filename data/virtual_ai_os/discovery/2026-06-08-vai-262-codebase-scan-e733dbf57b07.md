# VAI-262 Codebase Scan Finding

Date: 2026-06-08
Fingerprint: e733dbf57b0753be209b708f333797de261f2fd4
Kind: swallowed_exception
Source: external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py:1070
Priority: P1
Track: runtime

## Evidence

```text
except Exception:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

Reviewed `StorachaBackend.get_metadata`. Falling back to the Storacha API after a
local metadata cache read failure is intentional, but the previous broad handler
hid cache corruption and filesystem failures. The handler now catches expected
cache read/decode errors explicitly and logs a warning before falling back.
