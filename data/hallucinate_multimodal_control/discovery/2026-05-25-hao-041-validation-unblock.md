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

The HAO-038 validation command in this worktree still used semicolon-separated
Python statements inside a shell-quoted `python3 -c` command. The daemon split
on semicolons before honoring the shell quoting, which produced the unterminated
fragment and exhausted the retry budget before the policy code could be
validated.

## Resolution

- Replaced the HAO-038 inline validation with the same newline-based
  `exec(...)` form already present in the shared todo file.
- Closed the malformed HAO-041 import-only validation quote in this worktree's
  todo file.
- Added the HAO-038 evaluator compatibility patch to this worktree so the
  original backlog item has the intended code/test changes when unblocked.
- Confirmed `/home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_strategy.json`
  currently has an empty `blocked_tasks` list, so HAO-038 is not blocked there.

## Runtime Compatibility

`evaluate_ipfs_nl_policy` now scopes a temporary compatibility shim to the real
`ipfs_datasets_py.logic.api` lane. The shim maps upstream `at_time` evaluator
calls to the current `PolicyEvaluator.evaluate(..., now=...)` signature and
restores the original method immediately after the call. Evaluator exceptions
and residual signature-mismatch payloads still fail closed as `deny`.
