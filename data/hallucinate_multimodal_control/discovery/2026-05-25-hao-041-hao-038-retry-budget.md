# HAO-041 Retry-Budget Finding: HAO-038

Date: 2026-05-25
Source task: HAO-038
Follow-up task: HAO-041
Retry budget: 3
Observed consecutive validation failures: 3

## Evidence

- Failed command: `PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy`
- Attempts: 1, 2, 3
- Logs: /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-038-attempt-1.log, /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-038-attempt-2.log, /home/barberb/lift_coding/data/hallucinate_multimodal_control/state/implementation_logs/hao-038-attempt-3.log

## Guardrail Result

The Hallucinate multimodal-control daemon classified this as backlog work instead of
allowing another implementation attempt to loop on the same validation failure. The
source task is added to the strategy `blocked_tasks` list and the follow-up task below
is appended to the HAO board for normal daemon parsing.

## HAO-041 Diagnosis

All three HAO-038 implementation attempts reached the same post-implementation
validation failure. The policy adapter and regression test were present, but the
daemon parsed the HAO-038 validation metadata by splitting on every semicolon.
That split included semicolons inside the Python `-c` snippet, so the second
validation command became an unterminated shell quote:

```bash
PYTHONPATH=external/ipfs_datasets:hallucinate_app/python python3 -c 'from hallucinate_app.control_surface_policy import evaluate_ipfs_nl_policy
```

The failure was therefore a validation-command metadata issue, not another
policy-evaluator implementation failure.

## HAO-041 Fix

The HAO-038 validation one-liner now uses a newline-based `exec(...)` Python
snippet with no internal semicolons, so the daemon parser keeps it as one shell
command. The HAO-041 validation line was also closed and extended with the
required strategy assertion for the retry-budget unblock.

The HAO-038 implementation evidence from the failed attempts was also carried
forward into the active worktree: `evaluate_ipfs_nl_policy` now scopes a
temporary compatibility shim around the real `ipfs_datasets_py.logic.api`
evaluator call, mapping upstream `at_time` calls to
`PolicyEvaluator.evaluate(..., now=...)` when the installed upstream signature
requires `now`. The shim is restored after each call. Evaluator exceptions and
residual signature-mismatch payloads still fail closed with `decision="deny"`
without disabling later healthy evaluations.

The current strategy state has an empty `blocked_tasks` list, so `HAO-038` is no
longer blocked and can be retried by the normal backlog flow.
