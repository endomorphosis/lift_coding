# VAI-276 Codebase Scan Finding

Date: 2026-06-08
Fingerprint: ec600ae38de45bd1c2ef2343190feb132e896500
Kind: swallowed_exception
Source: external/ipfs_kit/archive/archive_clutter/fix_scripts/fixed_runner.py:58
Priority: P1
Track: runtime

## Evidence

```text
except:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution

Fixed both bare `except:` clauses in the file (lines 58 and 240):

1. **Line 58** (`kill_existing_servers`): Changed `except:` → `except Exception as e:` with a `logger.warning(...)` so failures reading/removing PID files are surfaced instead of silently swallowed.
2. **Line 240** (`main` finally block): Same change for the server-termination cleanup path.

Validation: `python3 -m py_compile` passes.
