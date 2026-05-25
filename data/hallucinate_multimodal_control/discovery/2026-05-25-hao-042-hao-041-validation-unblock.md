# HAO-042 HAO-041 Validation Unblock

Date: 2026-05-25
Task: HAO-042
Source task: HAO-041

## Finding

HAO-041 exhausted its retry budget on a shell parse failure before Python could
import `hallucinate_app.control_surface_policy`:

```bash
PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy
```

The command was missing the closing quote because the HAO-038 validation line
embedded semicolon-separated Python statements inside a quoted `python3 -c`
program. The daemon split that validation text into an unterminated fragment,
then carried the fragment forward into HAO-041 and HAO-042.

## Fix

- HAO-038 validation metadata now uses `&&` between shell commands and an
  `exec(...)` Python payload with newline escapes, so the daemon no longer
  splits inside the Python program.
- HAO-041 and HAO-042 validation metadata now use the complete import command
  with the closing shell quote.
- `evaluate_ipfs_nl_policy` scopes a compatibility adapter around the real
  `ipfs_datasets_py.logic.api.evaluate_nl_policy` call so upstream bridge calls
  to `PolicyEvaluator.evaluate(..., at_time=...)` are translated to the
  evaluator's current `now` parameter without leaving a global patch installed.
- The strategy file already has `blocked_tasks: []`; `HAO-041` is absent.

## Verification

The corrected import validation passes in this worktree. With the populated
upstream at `/home/barberb/lift_coding/external/ipfs_datasets`, one-shot
evaluation returns a fail-closed decision without the previous
`unexpected keyword argument 'at_time'` reason.
