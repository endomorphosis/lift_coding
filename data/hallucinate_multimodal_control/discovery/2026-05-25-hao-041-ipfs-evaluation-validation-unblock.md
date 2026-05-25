# HAO-041 IPFS Evaluation Validation Unblock

Date: 2026-05-25
Task: HAO-041
Source task: HAO-038

## Evidence

- Retry-budget evidence: `data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-hao-038-retry-budget.md`
- HAO-038 validation failed on this command fragment:
  `PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy`
- The fragment came from validation metadata that used semicolons inside a quoted
  `python3 -c` payload. The daemon parser splits validation metadata on every
  semicolon, so it truncated the Python one-liner before the closing quote.
- The underlying compatibility evidence remains the real
  `ipfs_datasets_py.logic.api.evaluate_nl_policy` path returning a deny reason
  containing `PolicyEvaluator.evaluate() got an unexpected keyword argument
  'at_time'` when the bridge passes `at_time` to an evaluator whose parameter is
  `now`.

## Fix

- Added a scoped Hallucinate adapter around the real
  `ipfs_datasets_py.logic.api.evaluate_nl_policy` call. When the resolved
  upstream `PolicyEvaluator.evaluate` has `now` but not `at_time`, the adapter
  temporarily maps `at_time` to `now` for the duration of the one-shot
  evaluation and then restores the original evaluator method.
- Preserved fail-closed behavior for evaluator exceptions and verified that a
  failing evaluation does not poison later calls through a healthy logic API.
- Rewrote the HAO-038 validation one-liner to use newline-based `exec(...)`
  instead of semicolons inside the quoted Python payload.
- Repaired the HAO-041 retry-budget validation command so it is a valid import
  check.
- The strategy `blocked_tasks` list no longer contains `HAO-038`.

## Validation Targets

- `PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
- `PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy'`
- `PYTHONPATH=/home/barberb/lift_coding/external/ipfs_datasets:hallucinate_app/python python3 hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
