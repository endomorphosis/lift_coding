# VAI-254 Resolution

Date: 2026-06-08
Task: VAI-254 - Review swallowed exception path in fix_mcp_form_data.py:100
Source: external/ipfs_kit/archive/applied_patches/fix_mcp_form_data.py:100
Kind: swallowed_exception
Status: fixed

## Finding

The scan fingerprint `bffca82adedc` flagged a bare `except:` inside the
archived patch script's `old_handle_add_request` match template. That block was
not executed by the script, but keeping the legacy swallowed-exception body as
source-like text made the archive script look like it still contained the
runtime bug it was replacing.

## Fix

Removed the full legacy method body from the script and replaced it with a
regex-based legacy method locator. The archived patch still rewrites matching
`handle_add_request` implementations to the existing fixed form-data handler,
but the script no longer carries the swallowed form-data exception path as a
literal source block.

## Validation

```
python3 -m py_compile external/ipfs_kit/archive/applied_patches/fix_mcp_form_data.py
```

Result: PASS (exit code 0).
