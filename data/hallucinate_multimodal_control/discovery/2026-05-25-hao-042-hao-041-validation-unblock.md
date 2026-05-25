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

The command is the first fragment produced after the daemon parser split the
HAO-038 validation line on semicolons inside a Python `-c` payload. The fragment
has an unterminated single quote, so Bash exits before application code can run.

## Fix

- The IPFS logic policy evaluator now wraps real
  `ipfs_datasets_py.logic.api.evaluate_nl_policy` calls with a scoped
  `at_time` to `now` compatibility adapter for the upstream
  `PolicyEvaluator.evaluate` signature.
- Evaluator errors continue to fail closed as `deny` responses and do not cache
  or disable later IPFS logic evaluations.
- The HAO-038, HAO-041, and HAO-042 validation metadata now use `exec(...)`
  payloads without semicolons inside quoted Python programs, so the existing
  daemon parser keeps each shell command intact.

## Strategy Unblock

`HAO-041` was removed from
`/home/barberb/lift_coding/data/hallucinate_multimodal_control/state/hallucinate_multimodal_control_strategy.json`
after the validation metadata was made parseable.
