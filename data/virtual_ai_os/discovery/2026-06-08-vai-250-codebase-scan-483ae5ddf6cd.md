# VAI-250 Codebase Scan Finding

Date: 2026-06-08
Fingerprint: 483ae5ddf6cd189190f33b4f6c4b07aa13d2d3a7
Kind: swallowed_exception
Source: external/ipfs_kit/archive/applied_patches/fix_huggingface_integration.py:318
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

The flagged path was a real observability gap in a best-effort server stop. The
restart helper now captures `pkill` output, logs the expected no-match exit code
at debug level, warns on unexpected nonzero exits, and records process-launch
exceptions instead of silently swallowing them.
