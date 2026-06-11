# HAO-315 Resolution

Date: 2026-06-07
Task: HAO-315
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:217

## Finding

The scan reported the broad exception handler in `run_pytest()`. That handler
previously caught every exception from command construction and subprocess
execution, returned only `str(e)`, and lost context about whether pytest timed
out, could not be launched, or failed normally.

## Fix

Verified that the current `external/ipfs_kit` gitlink,
`3dbb75d35ddc8005b388a6fcc30e5c447311c9f9`, already includes the focused
source fix from commit `12b7ead4423a468d5b1a74511b6bdf9c092c8ae7`. The
`run_pytest()` path now builds the command before the risky subprocess call,
handles `subprocess.TimeoutExpired` and `OSError` explicitly, logs diagnostic
messages, and preserves captured stdout/stderr in the returned failure details.
Unexpected programming errors are no longer swallowed by the pytest runner.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/direct_mcp_server.py
# exit 0
```
