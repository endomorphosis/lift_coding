# HAO-063 Objective Goal Gap

Date: 2026-05-25
Fingerprint: 5eadd5fc2d80c1850f510af99aaf4c1dffe2dd71
Kind: objective_goal_gap
Goal id: VAIOS-G030
Goal title: IDL, ORB, and MCP++ bridge
Objective heap: implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
Priority: P1
Track: runtime

## Goal

Interface descriptor language records voice, gesture, mouse, and agent controls, then dispatches them through ORB/MCP++ with policy mediation.

## Missing Evidence

- interface descriptor language

## Present Evidence

- object request broker: implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, implementation_plan/docs/21-swissknife-mobile-orb-bridge.md, Mcp-Plus-Plus/docs/architecture/glossary.md
- mcp_plus_plus: dev/meta-rayban-display-simulator/webapp/app.js, docs/GETTING_STARTED.md, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- control surface: implementation_plan/docs/19-virtual-ai-os-submodule-integration.md, implementation_plan/docs/22-multimodal-control-surface-logic-idl.md, tracking/PR-089-mobile-push-subscription-settings.md
- deontic logic: implementation_plan/docs/22-multimodal-control-surface-logic-idl.md, hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/tools/dataset_tools/native_dataset_tools.py
- event calculus: implementation_plan/docs/22-multimodal-control-surface-logic-idl.md, hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, external/ipfs_datasets/README.md
- frame logic: implementation_plan/docs/22-multimodal-control-surface-logic-idl.md, hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md, hallucinate_app/python/hallucinate_app/control_surface_logic_ir.py

## Suggested Handling

Close the weakest modality-to-policy-to-dispatch proof in the IDL/ORB/MCP++ bridge.

If the gap is too broad for one task, refine `VAIOS-G030` in the objective
heap by adding child goals with concrete evidence terms, then keep the generated
todo task small enough for the supervisor to validate.
