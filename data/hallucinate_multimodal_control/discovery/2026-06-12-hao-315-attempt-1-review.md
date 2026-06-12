# HAO-315 Attempt 1 Review

Date: 2026-06-12
Source: external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:217
Kind: swallowed_exception
Priority: P1
Track: runtime

## Review

The originally scanned `run_pytest()` broad exception path has already been
replaced in the current `external/ipfs_kit` gitlink. The active implementation
builds the pytest command before `subprocess.run()`, handles
`subprocess.TimeoutExpired` and `OSError` explicitly, logs those failures, and
returns captured subprocess output for normal pytest failures.

## Follow-up Hardening

`run_pytest()` now normalizes `test_paths` before the subprocess call. A single
path string is treated as one pytest argument instead of being expanded into
characters, and path-like arguments are converted with `os.fspath()`. Invalid
caller input now fails during command construction instead of being hidden
behind subprocess error handling.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/direct_mcp_server.py
# exit 0
```
