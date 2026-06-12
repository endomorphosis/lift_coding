# HAO-376 Codebase Scan Finding

Date: 2026-06-09
Fingerprint: 00f9e978ed6aea6d8388eab29f150fc0eba8d7da
Kind: swallowed_exception
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller_anyio.py:2187
Priority: P1
Track: runtime

## Evidence

```text
except Exception:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (HAO-376)

Status: Fixed

The `except Exception` at line 2193 (originally flagged via the comment at 2187)
was narrowed to `except (ValueError, UnicodeDecodeError)`. `json.JSONDecodeError`
is a subclass of `ValueError`, so this captures all real JSON parse failures
without silently hiding unrelated exceptions (e.g., MemoryError, KeyboardInterrupt).

Additionally, the `import json` statement was moved from inside the `try` block
to the module top-level imports, ensuring `ImportError` cannot be accidentally
swallowed by this handler.

Fix validated with: `python3 -m py_compile external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/ipfs_controller_anyio.py`
