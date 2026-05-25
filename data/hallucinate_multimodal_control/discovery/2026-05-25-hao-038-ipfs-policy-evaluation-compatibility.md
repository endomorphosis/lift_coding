# HAO-038 IPFS Policy Evaluation Compatibility

Date: 2026-05-25
Task: HAO-038

## Evidence Used

- `2026-05-25-hao-025-implementation-unknowns.md` records that
  `test_control_surface_policy_ipfs_logic.py` previously used fake logic API
  coverage and did not prove compatibility with the real upstream evaluator.
- `logic-api-inventory.md` records the public dependency surface as
  `ipfs_datasets_py.logic.api` and identifies the sampled upstream evaluator
  mismatch: bridge code passes `at_time` while `PolicyEvaluator.evaluate`
  accepts `now`.

## Result

Hallucinate App keeps the optional IPFS logic lane fail-closed: evaluator
exceptions return a deny-shaped result and do not cache the lane as unusable.
The compatibility shim in
`hallucinate_app/python/hallucinate_app/control_surface_policy.py` is scoped to
one `evaluate_nl_policy` call, temporarily maps upstream `at_time` calls to
`now`, and restores the original `PolicyEvaluator.evaluate` method afterward.

The regression in
`hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
now loads the real `ipfs_datasets_py.logic.api` checkout when available. In
this worktree, `external/ipfs_datasets` is an empty dependency stub, so the
test helper searches ancestor checkouts for a populated
`external/ipfs_datasets/ipfs_datasets_py/logic/api.py` before skipping.

## Validation Evidence

With the listed relative validation command, the test helper found the
populated checkout at `/home/barberb/lift_coding/external/ipfs_datasets`:

```bash
PYTHONPATH=external/ipfs_datasets:hallucinate_app/python \
  python3 hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py
```

Result: 7 tests passed, 0 skipped. The real upstream evaluation returned a deny
decision for an unknown policy CID with no `unexpected keyword argument` reason.

The one-line daemon validation command also passes when only the empty relative
dependency stub is available to runtime code, returning a fail-closed deny
result instead of treating the upstream lane as a soft allow.
