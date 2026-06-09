# VAI-211 Resolution: Swallowed Exception at advanced_filecoin.py:984

Date: 2026-06-09
Task: VAI-211
Source: external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:984
Kind: swallowed_exception → resolved

## Finding

The codebase scan at fingerprint `f223d9e5d048` flagged a bare `except Exception as e:`
in `AdvancedFilecoinStorage._get_chain_height()` that swallowed all errors without
re-raising or distinguishing expected versus unexpected failures.

## Fix Applied

The `_get_chain_height` method was refactored to:

1. **Cached file read errors** (`OSError`, `json.JSONDecodeError`) — caught narrowly and
   logged as warnings; the method falls through to the live API path.

2. **Invalid cached height values** (`TypeError`, `ValueError`) — caught narrowly at
   line 983 and logged as a warning, consistent with the live-API branch below.

3. **Live API errors** — `_make_api_request` already returns `None` for recoverable
   transport/API failures; unexpected exceptions are left to propagate rather than
   being collapsed into an indistinguishable `None` return.

Before (original swallowed-exception pattern):
```python
except Exception as e:
    pass  # or implicit None return
```

After (narrow, logged exception handling at line 983):
```python
except (TypeError, ValueError) as e:
    logger.warning(f"Invalid cached Filecoin height {chain_height!r}: {e}")
```

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py
# → exit 0 (compile OK)
```

## Notes

Previous three implementation attempts (VAI-211 attempts 1–3) failed due to
Codex/Copilot network connectivity errors rather than code problems. The fix was
incorporated into this branch via the VAI-212 repair worktree and is now committed
as part of attempt 4.
