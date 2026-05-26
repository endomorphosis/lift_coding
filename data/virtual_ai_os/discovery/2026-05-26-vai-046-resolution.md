# VAI-046 Resolution

Date: 2026-05-26
Source finding: `src/handsfree/transport/libp2p_bluetooth.py:1244`
Evidence: `data/virtual_ai_os/discovery/2026-05-26-vai-046-codebase-scan-74ff113b87c6.md`

The scan evidence pointed at a swallowed exception in the py-libp2p Bluetooth
runtime cleanup path. Synchronous close and reset failures were already logged,
but async cleanup failures that raised `RuntimeError` were hidden by
`_resolve_runtime_value()`: it treated every `RuntimeError` from `trio.run()` as
a nested-run signal and returned the awaitable without letting
`_close_runtime_stream()` log the failure or try the reset fallback.

## Resolution

- Runtime awaitable resolution now checks for an already-running Trio context
  before calling `trio.run()`, instead of catching runtime cleanup failures from
  the awaited coroutine.
- The Trio token probe is isolated in `_is_running_inside_trio()` so the
  intentional `RuntimeError` handling is documented by control flow rather than
  an opaque `pass`.
- Existing focused coverage verifies that async `close()` failures are logged
  and followed by `reset()`.
- Left the parseable VAI backlog metadata unchanged; the supervisor owns task
  completion state.

## Validation

- `python3 -m py_compile src/handsfree/transport/libp2p_bluetooth.py`
- `PYTHONPATH=$(pwd)/src python3 -m pytest -q tests/test_transport_providers.py::test_protocol_routing_adapter_logs_runtime_stream_cleanup_failures tests/test_transport_providers.py::test_protocol_routing_adapter_logs_async_runtime_stream_cleanup_failures`
