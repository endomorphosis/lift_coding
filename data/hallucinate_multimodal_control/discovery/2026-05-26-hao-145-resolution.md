# HAO-145 Resolution

Date: 2026-05-26
Source finding: 2026-05-26-hao-145-codebase-scan-ab48ea3fcc0c.md

## Finding

The codebase scan flagged the peer chat history read path because a broad
`except Exception` around persisted message listing could swallow unexpected
runtime defects while returning the in-memory fallback.

## Resolution

`PeerChatSessionService.list_messages` now uses the shared peer chat persistence
error set introduced for the peer chat fallback paths. The history read path
only falls back for DuckDB or filesystem persistence failures, logs traceback
context, and allows unrelated exceptions to propagate. A focused regression test
covers both the intended persistence fallback and the propagation behavior that
would have failed with the old broad catch.

## Validation

Passed from the HAO-145 worktree:

```bash
python3 -m py_compile src/handsfree/peer_chat.py
pytest tests/test_peer_chat_persistence.py
```
