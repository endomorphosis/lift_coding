# VAI-107 Resolution

The swallowed exception path in
`hallucinate_app/hallucinate_app/js_bridge/pyarrow_content_index_ws_server.py`
was narrowed so malformed websocket messages are handled as protocol errors
rather than by a broad `except Exception` block.

The message handler now sends structured `invalid_json` or `invalid_message`
responses for bad client input and allows unexpected response send or stats
handling failures to surface through the websocket server instead of being
logged and silently ignored.

Validation:
- `python3 -m py_compile hallucinate_app/hallucinate_app/js_bridge/pyarrow_content_index_ws_server.py`
