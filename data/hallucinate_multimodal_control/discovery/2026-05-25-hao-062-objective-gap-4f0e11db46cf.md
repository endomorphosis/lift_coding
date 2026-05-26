# HAO-062 Objective Goal Gap

Date: 2026-05-25
Fingerprint: 4f0e11db46cf54a88c41d159d0402f73dabc3591
Kind: objective_goal_gap
Goal id: VAIOS-G020
Goal title: Capability routing kernel
Objective heap: implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
Priority: P1
Track: runtime

## Goal

Stable capability ids route work across local Python, daemon tasks, MCP/MCP++, SwissKnife ORB, Hallucinate App, and mobile/glasses surfaces.

## Missing Evidence

- src/handsfree/capability_registry.py

## Present Evidence

- capability registry: implementation_plan/docs/12-github-cli-copilot-integration.md, implementation_plan/docs/14-mcp-plus-plus-ipfs-server-integration.md, implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md
- runtime router: implementation_plan/docs/16-phase-1-capability-registry-execution-matrix.md, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, src/handsfree/ai/models.py
- tests/test_virtual_ai_os_capability_registry.py: implementation_plan/docs/16-phase-1-capability-registry-execution-matrix.md, src/handsfree/ai/capability_registry.py, tests/test_virtual_ai_os_capability_registry.py
- tests/test_virtual_ai_os_runtime_router.py: tests/test_virtual_ai_os_runtime_router.py

## Suggested Handling

Add or tighten routing evidence for any execution mode that is named in the architecture but not exercised by tests.

If the gap is too broad for one task, refine `VAIOS-G020` in the objective
heap by adding child goals with concrete evidence terms, then keep the generated
backlog record narrow enough for the supervisor to validate.
