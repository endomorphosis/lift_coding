# HAO-308 Resolution

Date: 2026-06-07
Task: HAO-308
Kind: swallowed_exception fix
Source: external/ipfs_kit/archive/applied_patches/advanced_filecoin.py:984

## Finding

The `_get_chain_height` helper wrapped mock stats loading and the real
`Filecoin.ChainHead` lookup in a broad `except Exception` block. Any unexpected
internal error was logged as a warning and converted to `None`, which made real
defects indistinguishable from a normal "height unavailable" response.

## Fix

Removed the method-wide broad exception handler. Expected runtime fallback paths
are now handled explicitly:

1. Unreadable or invalid mock stats files catch only `OSError` and
   `json.JSONDecodeError`, log the file path, and continue to the API fallback.
2. Mock stats with the wrong JSON shape are logged and ignored.
3. Non-dictionary chain head responses are logged and treated as unavailable.

Unexpected programming errors now propagate to existing callers, which already
wrap their user-facing workflows and return structured errors.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/advanced_filecoin.py
```

Exit code: 0 (pass)
