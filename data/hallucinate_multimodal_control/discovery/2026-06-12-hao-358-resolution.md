# HAO-358 Resolution

Date: 2026-06-12
Task: HAO-358
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/cli_drafts/ipfs_kit_cli_ultra_fast.py:78

## Finding

The scanner reported a bare `except:` in `cmd_status()` while reading
`/tmp/ipfs_kit_daemon.pid`. The handler hid PID-file read and parse failures,
and it also caught unexpected control-flow exceptions.

## Fix

The status command now catches only expected PID-file failures (`OSError` and
`ValueError`). Normal status output remains quiet, while `--verbose` prints why
the PID could not be displayed.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/cli_drafts/ipfs_kit_cli_ultra_fast.py
# exit 0
```
