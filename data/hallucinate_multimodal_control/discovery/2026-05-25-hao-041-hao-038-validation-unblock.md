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
`hallucinate_app.control_surface_policy`, so it cannot be fixed by changing only
the imported module.

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

The HAO board validation metadata was also rewritten so the Python `-c`
assertion uses `exec(...)` with newline escapes rather than semicolons inside a
quoted string. This keeps the existing daemon parser from splitting the Python
program into invalid shell fragments.

## Strategy Unblock

`HAO-038` was removed from the strategy `blocked_tasks` list after the code and
validation metadata were corrected, allowing the original logic backlog item to
be retried without looping on the malformed validation command.
