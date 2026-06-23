# HAO-041 HAO-038 Validation Unblock

Date: 2026-05-25
Task: HAO-041
Source task: HAO-038

## Finding

HAO-038 exhausted its retry budget after the implementation itself validated
locally, then the daemon split the second validation command at semicolons
inside the Python `-c` payload. The resulting command was syntactically
incomplete:

```bash
PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy
```

That failure happens in the shell before Python imports
`hallucinate_app.control_surface_policy`, so changing only the imported module
cannot make the recorded command execute.

## Fix

The HAO-038 compatibility patch was applied in this worktree:

- `evaluate_ipfs_nl_policy` now scopes an upstream compatibility adapter around
  the real `ipfs_datasets_py.logic.api.evaluate_nl_policy` call.
- The adapter maps bridge-provided `at_time` values to
  `PolicyEvaluator.evaluate(..., now=...)` only when the real upstream module is
  in use and restores the evaluator immediately after the call.
- The IPFS logic tests now cover evaluator exceptions failing closed without
  disabling later calls, plus a real upstream regression when
  `ipfs_datasets_py.logic.api` is available.

The HAO board validation metadata was rewritten so Python `-c` assertions use
`exec(...)` with newline escapes rather than semicolons inside quoted strings.
This keeps the current daemon parser from splitting the Python program into
invalid shell fragments.

## Strategy Unblock

The strategy file at
`/home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_strategy.json`
already has an empty `blocked_tasks` list in this attempt. `HAO-038` is
therefore unblocked for the next daemon pass after the validation metadata fix.
