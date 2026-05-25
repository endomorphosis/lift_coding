# HAO-038 IPFS Logic Evaluation Compatibility

Date: 2026-05-25
Task: HAO-038

## Evidence Used

- `2026-05-25-hao-025-implementation-unknowns.md` records that the previous
  `test_control_surface_policy_ipfs_logic.py` lane used a fake logic API and
  did not prove compatibility with the real upstream evaluator.
- `logic-api-inventory.md` records the real public surface as
  `ipfs_datasets_py.logic.api` and notes that sampled `evaluate_nl_policy` and
  `evaluate_with_manager` calls failed closed because the bridge passed
  `at_time` to `PolicyEvaluator.evaluate`, whose observed parameter was `now`.

## Implementation Note

Hallucinate App now calls `ipfs_datasets_py.logic.api.evaluate_nl_policy`
through a scoped compatibility wrapper. When the upstream
`PolicyEvaluator.evaluate` signature accepts `now` but not `at_time`, the
wrapper temporarily adapts `at_time` to `now` for the duration of the upstream
call and restores the original evaluator immediately afterward. If an upstream
result still reports a signature mismatch as data, Hallucinate App normalizes
that reason to a fail-closed compatibility message rather than leaking
`unexpected keyword argument` as the runtime authorization rationale.

The regression keeps evaluator errors fail-closed by returning a deny-shaped
payload when the evaluator raises. A follow-up healthy evaluator call is still
attempted normally, so one evaluator error does not permanently disable the
real upstream lane.

## Validation Target

The real-upstream regression in
`hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
imports `ipfs_datasets_py.logic.api` when available, runs
`evaluate_ipfs_nl_policy("Alice may use display.activate", ...)`, and asserts
that the resulting reason no longer exposes the
`unexpected keyword argument` compatibility failure.
