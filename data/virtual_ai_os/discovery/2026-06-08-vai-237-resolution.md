# VAI-237 Resolution

Date: 2026-06-08
Task: VAI-237 - Review swallowed exception path in direct_mcp_server.py:255
Source: external/ipfs_kit/archive/applied_patches/direct_mcp_server.py:255
Kind: swallowed_exception
Status: fixed

## Finding

The codebase scan fingerprint `a66dbc016ac0` flagged `start_other_instance()`
because it caught every `Exception`, logged only the string form, and returned
`None`. During blue/green deployment this collapsed subprocess startup failures
into the generic caller response `Failed to start new instance`, hiding the
underlying launch error.

## Fix

Restricted the handler to expected `OSError` failures from `subprocess.Popen`,
logged the full traceback with command and target port context, and re-raised a
`RuntimeError` carrying that context. Unexpected exceptions are no longer
swallowed by this helper; deployment-level error handling can now surface the
specific startup failure.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/direct_mcp_server.py
```

Result: PASS (exit code 0).
