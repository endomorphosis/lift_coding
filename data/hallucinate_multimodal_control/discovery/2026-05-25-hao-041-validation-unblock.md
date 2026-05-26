# HAO-041 Validation Unblock

Date: 2026-05-25
Task: HAO-041
Source task: HAO-038

## Finding

The retry-budget evidence for HAO-038 showed the daemon repeatedly executing an
unterminated validation fragment:

```text
PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy
```

The HAO-038 validation command used semicolon-separated Python statements inside
a shell-quoted `python3 -c` command. The daemon split on semicolons before
honoring shell quoting, which produced the unterminated fragment and exhausted
the retry budget before the policy code could be validated.

## Resolution

- The HAO-038 validation command now uses the newline-based `exec(...)` form
  from the supervised backlog entry.
- The HAO-041 and HAO-042 import-only validations are closed shell commands.
- The current `hallucinate_app/main` submodule head contains the policy
  evaluator compatibility patch and regression coverage.
- `/home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_strategy.json`
  has an empty `blocked_tasks` list, so HAO-038 and HAO-041 are not blocked.

## Runtime Compatibility

`evaluate_ipfs_nl_policy` scopes a temporary compatibility shim to the real
`ipfs_datasets_py.logic.api` lane. The shim maps upstream `at_time` evaluator
calls to the current `PolicyEvaluator.evaluate(..., now=...)` signature and
restores the original method immediately after the call. Evaluator exceptions
and residual signature-mismatch payloads still fail closed as `deny`.
