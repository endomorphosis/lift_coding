# HAO-327 Resolution

Date: 2026-06-08
Task: HAO-327
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/fix_all_storacha.py:292

## Finding

The scanner reported a swallowed `except Exception:` in the MCP restart path
around the `pkill -f enhanced_mcp_server.py` cleanup call. The previous behavior
ignored all failures from that process-control cleanup, which hid missing
executables, subprocess failures, and unexpected runtime errors.

## Fix

Verified that the current `external/ipfs_kit` gitlink,
`53e70ce078cc4461da7e2b20cefcd15ec67b8820`, includes the focused source fix
from `eb599252fa5d530ed5cf9b2ada266de435630e93`. The `pkill` path now captures
stdout and stderr, logs nonzero return codes, treats return code 1 as "no
matching process", and catches only `OSError` and
`subprocess.SubprocessError`. Unexpected exceptions are no longer swallowed by
that cleanup block.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_all_storacha.py
# exit 0
```

The compile emitted the existing `SyntaxWarning: invalid escape sequence '\.'`
for the unrelated `find` glob string on line 243, but did not fail.
