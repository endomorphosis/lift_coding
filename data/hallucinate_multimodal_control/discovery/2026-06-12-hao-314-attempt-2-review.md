# HAO-314 Attempt 2 Review

Date: 2026-06-12
Source: external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:159
Kind: swallowed_exception
Priority: P1
Track: runtime

## Review

The scanned `get_other_instance_pid()` path no longer uses the original broad
`except Exception as e:` handler. It now handles missing peer PID files, read
errors, decode errors, empty files, invalid integer content, and non-positive
PIDs explicitly.

## Follow-up Hardening

The PID-file read is capped at 65 characters and rejects content longer than
64 characters before stripping and parsing. PID files should contain only a
small process ID, so oversized content is now reported as malformed instead of
being passed through the normal integer parse path.

## Validation

```text
python3 -m py_compile external/ipfs_kit/archive/applied_patches/direct_mcp_server.py
# exit 0
```
