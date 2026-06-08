# VAI-215 Resolution

Date: 2026-06-07
Task: VAI-215
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:159

## Finding

`get_other_instance_pid()` caught every exception while reading the inactive
blue/green instance PID file and returned `None`. A malformed or unreadable PID
file was therefore indistinguishable from the normal "other instance is absent"
case.

## Fix

The peer PID reader now handles each expected condition explicitly:

- a missing PID file returns `None`;
- file read failures log the path and traceback before returning `None`;
- invalid UTF-8 PID file contents log a warning;
- empty PID files log a warning;
- non-integer and non-positive PID values log warnings and return `None`;
- valid positive integer PID values are returned.

This preserves tolerant startup/deployment behavior while removing the catch-all
exception path that hid why a peer PID could not be used.

## Validation

`python3 -m py_compile external/ipfs_kit/archive/applied_patches/direct_mcp_server.py` -> exit 0

An additional AST validation checked that `get_other_instance_pid()` no longer
catches `Exception` and still has an explicit `OSError` path for PID-file read
failures -> exit 0.
