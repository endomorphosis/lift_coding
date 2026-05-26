# VAI-041 Codebase Scan Finding

Date: 2026-05-26
Fingerprint: fa5c9b97278c8678de523c06f7714ca6ab7005f4
Kind: swallowed_exception
Source: src/handsfree/ipfs_kit_adapters.py:194
Priority: P1
Track: runtime

## Evidence

```text
except Exception as exc:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

The `add_bytes` direct-call fallback at `src/handsfree/ipfs_kit_adapters.py:194`
now only catches `NotImplementedError`, which is the intentional sentinel for an
installed shim that declines the operation before backend fallback. Unexpected
direct-call exceptions continue to propagate instead of being swallowed.

The remaining broad optional import catch in this adapter was narrowed to
`ModuleNotFoundError` for the root `ipfs_kit_py` package only. Missing optional
dependency installs still return the unavailable adapter, while broken installed
packages and transitive import failures now surface to callers.

Validation:
- `python3 -m py_compile src/handsfree/ipfs_kit_adapters.py`
