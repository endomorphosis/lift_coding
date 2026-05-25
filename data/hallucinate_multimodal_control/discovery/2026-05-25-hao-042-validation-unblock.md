# HAO-042 HAO-041 Validation Unblock

Date: 2026-05-25
Task: HAO-042
Source task: HAO-041

## Finding

HAO-041 exhausted its retry budget on a shell parse failure, not a Python import
failure. The recorded validation command was missing its closing single quote:

```bash
PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy
```

That command exits before Python can import
`hallucinate_app.control_surface_policy`, so the retry task needed the task-board
validation metadata corrected in addition to the HAO-038 evaluator regression.

## Fix

The HAO-041 policy patch from the validation-passing attempt was reapplied:

- `evaluate_ipfs_nl_policy` wraps the real
  `ipfs_datasets_py.logic.api.evaluate_nl_policy` call with a temporary
  `at_time` to `now` adapter for `PolicyEvaluator.evaluate`.
- Evaluator exceptions still fail closed as `deny` and do not poison later
  evaluations.
- The IPFS logic tests cover fake evaluator failures, fake signature-mismatch
  payloads, and the real upstream lane when `ipfs_datasets_py.logic.api` is
  available.

The HAO-042 validation command now closes the Python `-c` quote:

```bash
PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy'
```

## Strategy Unblock

The strategy `blocked_tasks` list is empty in this attempt. `HAO-041` was also
removed from the stale `deprioritized_tasks` list so the original retry task can
be selected again after this validation metadata fix.
