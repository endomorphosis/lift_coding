# HAO-703 Launch Playwright Validation Gate

Date: 2026-06-26
Task: HAO-703
Goal id: VAIOS-G729
Goal packet: goal_packet/launch/external/ec964340486b
Packet goals: VAIOS-G727, VAIOS-G729
Evidence term: launch Playwright validation gate

HAO-703 closes the Hallucinate-owned VAIOS-G729 objective gap by making the
objective-task janitor expose active steering for launch Playwright validation
repair. The supervisor strategy now records the reopened objective ids, the
launch-gate objective ids, and the exact Swissknife plus Hallucinate App
Playwright command that retry-budget repair tasks must preserve.

## Gate Fixture

```json
{
  "schema": "hao_objective_janitor_launch_playwright_gate_v1",
  "task_id": "HAO-703",
  "goal_id": "VAIOS-G729",
  "goal_packet": "goal_packet/launch/external/ec964340486b",
  "packet_goals": [
    "VAIOS-G727",
    "VAIOS-G729"
  ],
  "evidence_term": "launch Playwright validation gate",
  "missing_evidence_source": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-703-objective-gap-9f377c75e074.md",
  "receipt_path": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-703-launch-playwright-validation-gate.md",
  "shared_packet_receipts": [
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-701-launch-playwright-validation-gate.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-launch-playwright-validation-gate.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-536-launch-playwright-validation-gate.md"
  ],
  "objective_heap": "implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md",
  "supervisor_code": "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objective_task_janitor.py",
  "tests": [
    "tests/test_supervisor_objective_task_janitor.py",
    "tests/test_reconciliation_guardrail_refresh.py"
  ],
  "strategy_fields": [
    "objective_task_janitor_reopen_goal_ids",
    "objective_task_janitor_force_goal_ids",
    "objective_task_janitor_validation_gate_goal_ids",
    "objective_task_janitor_launch_playwright_validation_gate"
  ],
  "launch_packet_command": "PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py tests/test_reconciliation_guardrail_refresh.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)",
  "playwright_gates": [
    {
      "surface": "swissknife",
      "command": "npm --prefix swissknife run test:e2e:meta-glasses"
    },
    {
      "surface": "hallucinate_app",
      "command": "npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
    }
  ],
  "supervisor_alignment": {
    "objective_heap_goal": "VAIOS-G729",
    "packet_sibling_goal": "VAIOS-G727",
    "backlog_task": "HAO-703",
    "keeps_supervisor_fed_backlog_aligned": true,
    "repairs_failed_validation": true
  }
}
```

## Evidence

- `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objective_task_janitor.py`
  records `objective_task_janitor_validation_gate_goal_ids` and
  `objective_task_janitor_launch_playwright_validation_gate` when an idle active
  objective requires the launch Playwright validation gate.
- `tests/test_supervisor_objective_task_janitor.py` asserts that VAIOS-G729 is
  reopened, forced into objective refill, and tagged with the Swissknife and
  Hallucinate App Playwright launch commands.
- `tests/test_reconciliation_guardrail_refresh.py` asserts retry-budget repair
  tasks preserve the launch Playwright validation gate when validation failures
  occur on the shared VAIOS-G727/VAIOS-G729 packet.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  this HAO-703 proof so the supervisor-fed backlog remains aligned with the
  objective heap.
