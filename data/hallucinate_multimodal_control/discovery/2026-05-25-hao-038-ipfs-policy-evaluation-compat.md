# HAO-038 IPFS Policy Evaluation Compatibility

Date: 2026-05-25
Task: HAO-038

## Evidence Used

- `2026-05-25-hao-025-implementation-unknowns.md` records that the existing
  policy test used a fake logic API and did not prove compatibility with the
  real `ipfs_datasets_py.logic.api.evaluate_nl_policy` path.
- `logic-api-inventory.md` records the sampled upstream mismatch where
  `UCANPolicyBridge.evaluate` passes `at_time` into
  `PolicyEvaluator.evaluate`, whose audited signature accepts `now`.

## Implementation Notes

Hallucinate App now wraps real `ipfs_datasets_py.logic.api` evaluation in a
scoped compatibility context. The context restores upstream objects after each
call and only applies to the real public API module, not fake test adapters.

The compatibility layer covers the observed `at_time` to `now` evaluator drift.
It also adapts adjacent one-shot bridge shape drift that prevented the real
evaluation lane from reaching a successful permission decision in this checkout:
string policy text is converted to the list form expected by the compiler, an
unsupported `audience_did` keyword is ignored when necessary, and
`BridgeResult.denials` is exposed under the bridge's expected
`deny_capabilities` alias for the duration of the call.

## Regression Coverage

`hallucinate_app/python/hallucinate_app/test/test_control_surface_policy_ipfs_logic.py`
now includes:

- A fail-closed evaluator-error regression that returns `deny` and then proves
  a later healthy evaluator call still runs.
- A non-fake regression against `ipfs_datasets_py.logic.api` when the real
  dependency is importable. It evaluates `Alice may read files` with the real
  public API and asserts an allow/permit decision without the
  `unexpected keyword argument 'at_time'` reason.

When the external dependency checkout is absent, the real-upstream regression is
skipped by `unittest` instead of replacing it with a fake.
