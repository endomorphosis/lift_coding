# VAI-107 Resolution

Date: 2026-06-09
Finding: swallowed_exception
Source: hallucinate_app/hallucinate_app/js_bridge/pyarrow_content_index_ws_server.py

## Problem

`notify_clients` iterated over `self.clients`, wrapped each `create_task` call in a
`try/except Exception`, logged any error, but never removed the dead client from
`self.clients`. The subsequent `asyncio.gather(..., return_exceptions=True)` then
silently discarded actual send failures, so stale/closed connections accumulated
indefinitely and every future broadcast would fail for those clients.

## Fix

- Replaced the per-client `try/except` + `create_task` loop with a direct list of
  coroutines (one `client.send()` per client snapshot).
- Called `asyncio.gather(*send_tasks, return_exceptions=True)` and zipped the results
  back to the originating clients.
- For any result that is an `Exception`, log a warning and call `self.clients.discard(client)`
  to remove the dead client so future broadcasts are not affected.

## Validation

`python3 -m py_compile hallucinate_app/hallucinate_app/js_bridge/pyarrow_content_index_ws_server.py` → exit 0
