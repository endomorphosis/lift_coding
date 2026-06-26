# VAI-520 Launch Playwright Validation Gate

Date: 2026-06-26
Task: VAI-520
Goal id: VAIOS-G729
Goal packet: goal_packet/launch/external/ec964340486b
Packet goals: VAIOS-G727, VAIOS-G729
Evidence term: launch Playwright validation gate

## Evidence

- `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objective_task_janitor.py` keeps `objective_task_janitor_validation_gate_goal_ids` and `objective_task_janitor_launch_playwright_validation_gate` active for scheduled launch-gate goals even when the goal already has open todo work.
- `tests/test_supervisor_objective_task_janitor.py` covers the active-work path for `VAIOS-G729` so the supervisor-fed backlog keeps the launch Playwright validation gate visible without forcing a duplicate reopened goal.
- `tests/test_reconciliation_guardrail_refresh.py` covers validation retry-budget repair tasks appending the Swissknife and Hallucinate App Playwright launch commands.

## Launch Gate Command

`PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py tests/test_reconciliation_guardrail_refresh.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)`

## Result

This receipt closes the VAIOS-G729 objective gap by proving that active objective heap steering and failed validation repair both preserve the launch Playwright validation gate for the shared VAIOS-G727/VAIOS-G729 packet.
