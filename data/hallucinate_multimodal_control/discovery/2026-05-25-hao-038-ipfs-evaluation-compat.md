# HAO-038 IPFS Logic Evaluation Compatibility

Date: 2026-05-25
Task: HAO-038

## Evidence Used

`2026-05-25-hao-025-implementation-unknowns.md` and
`logic-api-inventory.md` record that Hallucinate App already routes freeform
policy compilation through `ipfs_datasets_py.logic.api`, but the sampled real
evaluation path returned a fail-closed deny because the upstream UCAN bridge
called `PolicyEvaluator.evaluate(..., at_time=...)` while the evaluator
signature accepts `now`.

The populated upstream checkout at `/home/barberb/lift_coding/external/ipfs_datasets`
still shows that mismatch:

```text
UCANPolicyBridge.evaluate(..., at_time=None)
PolicyEvaluator.evaluate(..., now=None, ...)
```

Calling the public `api.evaluate_nl_policy("Alice may use display.activate",
tool="display.activate", actor="Alice")` produced a deny result whose reason
included `unexpected keyword argument 'at_time'` before the Hallucinate adapter
shim was applied.

## Regression Added

`test_control_surface_policy_ipfs_logic.py` now includes a non-fake regression
that imports `ipfs_datasets_py.logic.api` when the linked dependency checkout is
available, calls `evaluate_ipfs_nl_policy` with that real API module, and
asserts that the returned decision is fail-closed or permitted by upstream
without leaking the `at_time` keyword error into the result reason.

The same test file also proves evaluator exceptions remain fail-closed and do
not permanently disable later calls through the IPFS logic lane.

## Adapter Behavior

`evaluate_ipfs_nl_policy` still uses the public
`ipfs_datasets_py.logic.api.evaluate_nl_policy` entry point. For the real API
module only, Hallucinate App temporarily adapts `PolicyEvaluator.evaluate` so an
upstream `at_time` keyword is mapped to the evaluator's current `now` keyword.
The shim is scoped to the single public API call and restored immediately.

## Validation Notes

The task validation commands passed against this worktree's declared
`external/ipfs_datasets:hallucinate_app/python` path. Because the local
`external/ipfs_datasets` directory in this worktree is an empty dependency stub,
the real-upstream unittest was skipped there.

The same test and one-shot evaluation were also run with the populated checkout
at `/home/barberb/lift_coding/external/ipfs_datasets`. In that lane the
real-upstream regression executed, all seven tests passed, and the one-shot
evaluation returned:

```text
{'decision': 'deny', 'policy_cid': '', 'reason': 'Unknown policy CID: ', ...}
```

The post-shim reason no longer contains `unexpected keyword argument`.
