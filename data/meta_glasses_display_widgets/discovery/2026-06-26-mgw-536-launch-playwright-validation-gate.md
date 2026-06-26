# MGW-536 Launch Playwright Validation Gate

Date: 2026-06-26
Task: MGW-536
Goal id: VAIOS-G729
Goal packet: goal_packet/launch/external/ec964340486b
Packet goals: VAIOS-G727, VAIOS-G729
Evidence term: launch Playwright validation gate
Missing evidence source: data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-536-objective-gap-9f377c75e074.md

MGW-536 closes the VAIOS-G729 objective gap by making supervisor-generated
validation repair tasks preserve the launch Playwright validation gate. When a
launch task repeatedly fails validation, the retry-budget guardrail now appends
the Swissknife Meta glasses Playwright command and the Hallucinate App
multimodal-control-surface Playwright command to the repair task validation.

## Receipt

```json
{
  "schema": "mgw_objective_heap_validation_repair_gate_v1",
  "task_id": "MGW-536",
  "goal_id": "VAIOS-G729",
  "goal_packet": "goal_packet/launch/external/ec964340486b",
  "packet_goals": [
    "VAIOS-G727",
    "VAIOS-G729"
  ],
  "evidence_term": "launch Playwright validation gate",
  "supervisor_paths": [
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/backlog_refinery.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objective_task_janitor.py",
    "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objective_tracker.py"
  ],
  "validation_tests": [
    "tests/test_supervisor_objective_task_janitor.py::test_objective_task_janitor_keeps_launch_playwright_gate_repairs_on_mission",
    "tests/test_reconciliation_guardrail_refresh.py::test_launch_validation_retry_repair_preserves_playwright_gate"
  ],
  "repair_gate": {
    "python_command": "PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py tests/test_reconciliation_guardrail_refresh.py -q",
    "playwright_commands": [
      "npm --prefix swissknife run test:e2e:meta-glasses",
      "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
    ]
  },
  "assertions": [
    "Launch retry-budget repairs append the launch Playwright validation gate when the failed task is on the launch track or names the launch Playwright gate.",
    "The objective-task janitor keeps launch Playwright validation gate repairs mission-aligned instead of deprioritizing them as generic scan churn.",
    "The VAIOS-G729 heap seed contains the launch Playwright validation gate evidence term so regenerated heaps keep the supervisor-fed backlog aligned."
  ]
}
```

## Evidence

- `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/backlog_refinery.py`
  adds launch-aware retry repair validation that appends the Swissknife and
  Hallucinate App Playwright gates when a launch task exhausts validation
  retries.
- `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objective_task_janitor.py`
  treats `launch Playwright validation gate` as a mission term so supervisor
  steering does not defer those repair tasks as off-mission generated work.
- `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objective_tracker.py`
  keeps the VAIOS-G729 seed evidence aligned with the active objective heap.
- `tests/test_reconciliation_guardrail_refresh.py` proves a repeated MGW-536
  validation failure generates a repair task whose validation includes both
  launch Playwright commands.
- `tests/test_supervisor_objective_task_janitor.py` proves VAIOS-G729 is forced
  back into objective refill while launch-gate repair tasks remain on mission.

## Validation

- 2026-06-26: `PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py tests/test_reconciliation_guardrail_refresh.py -q` passed with 17 tests.
- 2026-06-26: `npm --prefix swissknife run test:e2e:meta-glasses` passed with 2 Playwright tests.
- 2026-06-26: `npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts` passed with 4 Playwright tests.
