# HAO-314 Resolution

Date: 2026-06-07
Source: external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:159
Kind: swallowed_exception
Priority: P1
Track: runtime

## Finding

`get_other_instance_pid()` used one broad `except Exception as e:` block around
PID-file existence checks, file reads, and integer parsing. The handler returned
`None` for every failure, which hid whether the problem was an operational read
failure, an invalid PID file, an empty file, or an unsafe non-positive PID.

## Fix

The PID-file path now returns `None` explicitly when the peer PID file is absent,
uses UTF-8 while reading it, and handles `OSError`, `UnicodeDecodeError`, and
`ValueError` separately. Empty and non-positive PID values are rejected with
warnings, so invalid PID files no longer feed unsafe values into later process
checks.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/direct_mcp_server.py
# exit 0
```
