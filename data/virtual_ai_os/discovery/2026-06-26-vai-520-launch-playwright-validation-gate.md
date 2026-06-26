# VAI-520 Launch Playwright Validation Gate

Date: 2026-06-26
Task: VAI-520
Goal id: VAIOS-G729
Goal packet: goal_packet/launch/external/ec964340486b
Packet goals: VAIOS-G727, VAIOS-G729
Evidence term: launch Playwright validation gate
Missing evidence source: data/virtual_ai_os/discovery/2026-06-26-vai-520-objective-gap-9f377c75e074.md

VAI-520 closes the VAIOS-G729 objective gap on the VAI task board by making
supervisor retry-budget findings carry the exact shared launch Playwright
validation gate command. The supervisor can now distinguish a launch validation
repair from generic retry churn and keep the VAIOS-G727/VAIOS-G729 goal packet
attached to Swissknife and Hallucinate App Playwright replay evidence.

## Receipt

```json
{
  "schema": "vai_objective_heap_validation_repair_gate_v1",
  "task_id": "VAI-520",
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
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py tests/test_reconciliation_guardrail_refresh.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)",
  "repair_gate": {
    "python_command": "PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py tests/test_reconciliation_guardrail_refresh.py -q",
    "playwright_commands": [
      "npm --prefix swissknife run test:e2e:meta-glasses",
      "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
    ]
  },
  "assertions": [
    "Launch retry-budget findings expose the exact shared Playwright gate command when a launch task exhausts validation retries.",
    "The objective-task janitor keeps launch Playwright validation gate repair work mission-aligned and forces idle VAIOS-G729 objective refill.",
    "The VAIOS-G729 heap record points at this VAI receipt and the packet sibling VAIOS-G727 so supervisor-fed backlog repair remains aligned with the objective heap."
  ]
}
```

## Evidence

- `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/backlog_refinery.py`
  appends and reports the guarded Swissknife and Hallucinate App Playwright
  launch command for launch validation retry repairs.
- `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objective_task_janitor.py`
  treats `launch Playwright validation gate` as a mission term, so VAIOS-G729
  launch repair work is not deprioritized as generic scan churn.
- `tests/test_reconciliation_guardrail_refresh.py` asserts the retry-budget
  finding payload, generated board text, and strategy block for a launch gate
  failure.
- `tests/test_supervisor_objective_task_janitor.py` asserts the janitor keeps
  launch-gate repair work on mission and forces VAIOS-G729 back into objective
  refill when the heap has no open task for that active goal.

## Validation

- Command: `PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py tests/test_reconciliation_guardrail_refresh.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)`
