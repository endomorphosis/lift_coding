# HAO-347 Resolution

Date: 2026-06-08
Task: HAO-347
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_fix_resource_handlers.py:249

## Finding

The scan fingerprint `84c70ed539d3` flagged the generated wrapper's broad
`except Exception as e:` handler in `patch_module()`. That handler could hide
unexpected import/runtime failures while returning `None` as if logger patching
was merely unavailable.

## Fix

The current submodule source had already narrowed the generated wrapper handler
to `AttributeError` and `TypeError`. This resolution keeps that narrow runtime
path and includes the caught exception value in the `logger.exception()` message,
so expected logger-attachment failures retain traceback context without
swallowing unrelated exceptions.

## Validation

Result: passed in this worktree.

```text
python3 -m py_compile external/ipfs_kit/archive/archive_clutter/fix_scripts/direct_fix_resource_handlers.py
```
