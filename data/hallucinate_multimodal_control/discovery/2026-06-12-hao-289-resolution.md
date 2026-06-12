# HAO-289 Resolution

Reviewed the swallowed exception finding in
`hallucinate_app/python/hallucinate_app/control_surface_policy.py` around the
temporary `PolicyEvaluator.evaluate(..., at_time=...)` adapter.

The adapter is optional and should remain disabled when
`ipfs_datasets_py.mcp_server.temporal_policy` is unavailable, but that skip was
silent. The implementation now logs the caught `ImportError` at debug level with
exception context before returning `None`, preserving fail-closed behavior while
making the skipped compatibility adapter observable.

Focused validation was added to
`hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
to assert that the import-skip path returns no restore callback and emits the
debug diagnostic.
