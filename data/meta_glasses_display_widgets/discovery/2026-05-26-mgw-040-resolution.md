# MGW-040 Swallowed Exception Resolution

Date: 2026-05-26
Task: MGW-040
Source finding: `src/handsfree/ipfs_kit_adapters.py:347`
Evidence: `/home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-040-codebase-scan-6b0df05ca4a0.md`

## Finding

The adapter treated every exception raised while importing `ipfs_kit_py` as an
absent optional dependency. That kept fallback behavior for missing installs but
also hid import-time failures from broken installed packages or missing
transitive dependencies.

## Resolution

`_import_kit_module()` now only converts a missing root `ipfs_kit_py` package to
the unavailable adapter. Nested `ModuleNotFoundError` failures and all other
import-time exceptions propagate, matching the stricter import handling already
used by the adapter's backend and high-level API resolution paths.

## Validation

```bash
python3 -m py_compile src/handsfree/ipfs_kit_adapters.py
```
