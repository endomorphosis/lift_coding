# VAI-263 Codebase Scan Finding

Date: 2026-06-08
Fingerprint: 070deff5a913c290e1d8102368115b892bf5303a
Kind: swallowed_exception
Source: external/ipfs_kit/archive/applied_patches/fix_storacha_backend.py:1549
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

Reviewed `StorachaBackend.get_status`. The backend status endpoint version parse
is optional, but the previous broad handler silently hid malformed JSON and
unexpected response shapes. The path now only attempts version parsing for
successful status responses, logs JSON decode failures, and logs unexpected
non-object JSON while preserving the best-effort `api_version = None` behavior.
