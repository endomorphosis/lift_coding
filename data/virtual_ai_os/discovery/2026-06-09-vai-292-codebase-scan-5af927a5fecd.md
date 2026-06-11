# VAI-292 Codebase Scan Finding

Date: 2026-06-09
Fingerprint: 5af927a5fecde4e54305e839f025bd4853bd7a37
Kind: swallowed_exception
Source: external/ipfs_kit/archive/mcp_development/mcp_test_suite.py:265
Priority: P1
Track: quality

## Evidence

```text
except Exception as e:
```

## Suggested Handling

Review the finding in context, decide whether it represents a bug, missing test,
maintenance risk, or false positive, and land a small fix with validation. If the
finding is a false positive, document why in the changed code or discovery notes
so the supervisor does not keep re-adding the same work.

## Resolution (VAI-292)

**Status:** Fixed  
**Fix date:** 2026-06-09

The `except Exception as e` at line 265 in `get_server_info()` was a broad catch-all that
swallowed unexpected exceptions after already handling `requests.RequestException`. The only
realistic non-network exception in that try block is `json.JSONDecodeError` (from
`response.json()` at line 256). Replaced the broad handler with `except json.JSONDecodeError`
so truly unexpected exceptions (e.g., `MemoryError`, `KeyboardInterrupt`) propagate naturally
rather than being silently swallowed and replaced with a `None` return.
