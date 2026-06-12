# HAO-301 Resolution

The codebase scan flagged a shutdown TODO for missing `ipfs_kit_instance`
cleanup in `hallucinate_app/python/hallucinate_app/ipfs_kit_bridge.py`.

The shutdown path now performs explicit cleanup for both bridge-owned IPFS
resources:

- saves and closes the metadata index when supported;
- calls the first available high-level API cleanup method on `ipfs_simple_api`;
- calls the first available runtime cleanup method on `ipfs_kit_instance`,
  preferring daemon shutdown methods before generic close/stop hooks;
- records cleanup failures independently so one resource cleanup failure does not
  skip the next cleanup attempt;
- clears bridge references after cleanup so stale resources cannot be reused.

Validation: `python3 -m py_compile hallucinate_app/python/hallucinate_app/ipfs_kit_bridge.py`.
