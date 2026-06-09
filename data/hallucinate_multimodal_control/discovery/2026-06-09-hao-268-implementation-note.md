# HAO-268 Implementation Note

Reviewed the swallowed exception finding for
`hallucinate_app/hallucinate_app/python/hallucinate_app/js_bridge/pyarrow_content_index_bridge.py`.

The worker loop intended to ignore only idle queue timeouts while waiting for
queued work. The broad `except Exception:` also hid unexpected queue failures, so
the handler now catches `queue.Empty` specifically. Unexpected exceptions continue
to the surrounding worker-loop error path for logging instead of being treated as
normal idle time.
