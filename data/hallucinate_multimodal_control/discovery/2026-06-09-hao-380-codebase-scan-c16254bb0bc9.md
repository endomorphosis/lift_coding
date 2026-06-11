# HAO-380 Codebase Scan Finding

Date: 2026-06-09
Fingerprint: c16254bb0bc90435bca0d01e55275adbc50f2d25
Kind: swallowed_exception
Source: external/ipfs_kit/archive/mcp_final_20250414_082801/controllers/peer_websocket_controller_anyio.py:568
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
