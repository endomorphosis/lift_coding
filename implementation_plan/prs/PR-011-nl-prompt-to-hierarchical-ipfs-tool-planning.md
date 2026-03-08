# PR-011: NL prompt → hierarchical IPFS tool planning with logic/prover validation

## Goal
Implement the core orchestration layer that converts natural-language prompts into theorem-checked hierarchical tool plans, grounded by `ipfs_datasets_py`.

## Scope
- Add intent-candidate grounding interface backed by `ipfs_datasets_py`.
- Add canonical logic-form representation for parsed intents.
- Add theorem-prover gate before execution planning.
- Add hierarchical planner tree and execution-mode bindings.
- Add direct (prototype) and MCP (production) execution compatibility at the planner leaf level.

## Out of scope
- Full intent support for all command families in one PR.
- Replacement of existing command router internals in one step.
- Non-IPFS tool families.

## Acceptance criteria
- Supported prompts produce a deterministic `LogicalPlanNode` tree.
- Unsatisfied constraints produce clarification prompts, not unsafe execution.
- Plans can execute in direct mode and MCP mode without changing intent surface behavior.
- Audit traces include proof decision metadata and correlation IDs.

## Dependencies
- `implementation_plan/docs/13-nl-prompt-to-hierarchical-tools-ipfs-datasets.md`
- `implementation_plan/docs/12-meta-glasses-ipfs-tool-integration.md`
- `implementation_plan/prs/PR-010-meta-glasses-ipfs-tooling-prototype-and-mcp-production.md`
