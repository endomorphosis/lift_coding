# HAO-146 Resolution

Date: 2026-05-26
Source finding: 2026-05-26-hao-146-codebase-scan-87a17f74176c.md

## Finding

The codebase scan flagged the peer chat recent-conversation read path because a
broad `except Exception` around persisted conversation listing could swallow
unexpected runtime defects while returning the in-memory fallback.

## Resolution

`PeerChatSessionService.list_recent_conversations` is covered by the peer chat
persistence error set for its database fallback path. The recent-conversation
read path only falls back for DuckDB or filesystem persistence failures, logs
traceback context, and allows unrelated exceptions to propagate. This task adds
focused regression tests for the intended fallback behavior and the propagation
behavior that would have failed with the old broad catch.

## Validation

Passed from the HAO-146 worktree:

```bash
python3 -m py_compile src/handsfree/peer_chat.py
pytest tests/test_peer_chat_persistence.py
```
