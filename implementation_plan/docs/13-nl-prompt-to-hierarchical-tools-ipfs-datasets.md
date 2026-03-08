# Natural Language Prompt → Hierarchical Tools (IPFS Datasets + Logic + Theorem Prover)

## Objective
Define a production-ready pipeline that transforms a natural language prompt into safe, deterministic hierarchical tool execution, using:
- `ipfs_datasets_py` for dataset/tool capability grounding and dataset-aware parsing
- existing command-routing/policy logic in this codebase
- new logic + theorem-prover modules for constraint validation and proof-backed execution plans

This plan is designed to work in both:
1. **Prototype mode**: direct CLI/package import execution
2. **Production mode**: MCP server remote execution

## Problem framing
Natural language requests are ambiguous, underspecified, and can violate policy or operational constraints.
For Meta glasses usage, we need:
- concise interaction,
- high confidence mapping from prompt to tool intent,
- explainable safety checks,
- and hierarchical decomposition when one prompt requires multiple tool calls.

## End-to-end architecture
1. **NL ingestion + normalization**
   - Input: ASR transcript or text prompt
   - Output: normalized prompt + confidence + context (profile/session/repo/task)

2. **Intent candidate generation (`ipfs_datasets_py`-assisted)**
   - Use `ipfs_datasets_py` to load dataset-indexed intent exemplars, schema hints, and tool metadata.
   - Generate candidate intents with slot/entity proposals.

3. **Logic normalization layer**
   - Convert candidate intents into canonical logical forms:
     - action predicate
     - entities (repo, issue, CID, dataset, filters)
     - constraints (must-confirm, policy preconditions, required parameters)

4. **Theorem-prover validation**
   - Evaluate logical form against:
     - policy axioms (allowed actions, confirmation requirements)
     - type/shape constraints for tool inputs
     - state constraints (task status, branch/check state)
   - Accept only plans with satisfiable constraints.
   - If unsat: return minimal clarification question.

5. **Hierarchical planner**
   - Build a task tree:
     - root intent
     - intermediate subtasks
     - leaf tool actions
   - Each node carries preconditions, postconditions, retry policy, and observability IDs.

6. **Execution adapter**
   - Prototype: direct CLI/import adapters.
   - Production: MCP remote adapters.
   - Maintain a shared internal action schema to keep planner/output stable across modes.

7. **Result synthesis**
   - Collect leaf outputs → reduce to user-facing summary.
   - Produce concise spoken response + optional detailed trace link.

## Hierarchical tool model
### L0: User intent
- Example: “Find the latest legal dataset, publish it to IPFS, and summarize provenance.”

### L1: Intent family
- `dataset_discovery`
- `dataset_prepare`
- `ipfs_publish`
- `provenance_report`

### L2: Tool chain
- `ipfs_datasets_py.search_catalog`
- `ipfs_datasets_py.select_candidate`
- `ipfs_datasets_py.prepare_manifest`
- `ipfs_kit` (pin/publish/metadata operations)
- `ipfs_accelerate` (optional acceleration/execution optimization)

### L3: Primitive tool actions
- validated function/CLI invocations with exact parameters and typed outputs

## `ipfs_datasets_py` integration design
Use `ipfs_datasets_py` as a semantic and operational grounding layer:
- intent example corpus for few-shot retrieval
- dataset schema/type hints for slot filling
- domain taxonomy (dataset categories, provenance attributes, publication modes)
- capability map that binds intent families to tool actions

Planned adapter contract:
- `resolve_intent_candidates(prompt, context) -> [IntentCandidate]`
- `resolve_entity_schema(intent_name) -> EntitySchema`
- `resolve_tool_capabilities(intent_name) -> [ToolCapability]`

## Logic + theorem-prover modules
### Module boundaries
- `logic_form_builder`: prompt/intents -> formal predicates
- `constraint_library`: reusable predicates for policy/safety/type constraints
- `plan_prover`: satisfiability + proof artifact generation
- `clarification_generator`: unsat-core -> user question

### Suggested rule classes
- **Safety rules**: destructive actions require confirmation token.
- **Completeness rules**: required entities must be present before execution.
- **Type rules**: entity types must match tool contracts.
- **Policy rules**: profile/repo policy can deny or gate actions.
- **Execution rules**: remote-only actions in production mode.

### Proof artifacts
Store per-plan proof metadata:
- theorem set version
- satisfied/unsatisfied constraints
- minimal unsat core (if rejected)
- proof hash in task trace for auditability

## Data contracts
### `IntentCandidate`
- `name`
- `confidence`
- `entities`
- `supporting_examples`
- `tool_capability_refs`

### `LogicalPlanNode`
- `node_id`
- `goal`
- `preconditions`
- `postconditions`
- `children`
- `executor` (`direct_cli|direct_import|mcp_remote`)
- `timeout_s`

### `ProofDecision`
- `status` (`sat|unsat|unknown`)
- `violations`
- `required_clarifications`

## Prototype path (direct execution)
1. Parse NL prompt using current parser + `ipfs_datasets_py` candidate resolver.
2. Build logical plan and run theorem checks locally.
3. Execute leaf nodes via direct package imports (preferred) or CLI fallback.
4. Return spoken summary + debug trace for rapid iteration.

## Production path (MCP remote)
1. Same parse/plan/prove pipeline.
2. Route leaf tool nodes through MCP adapters.
3. Enforce production policy:
   - no direct execution,
   - strict authn/authz,
   - correlation IDs + structured audit logs.
4. Support retries/idempotency for long-running remote operations.

## Rollout phases
### Phase 1 — planning and contracts
- Finalize data contracts (`IntentCandidate`, `LogicalPlanNode`, `ProofDecision`).
- Add abstraction interfaces and configuration toggles.

### Phase 2 — parser augmentation
- Integrate `ipfs_datasets_py` candidate/entity resolution.
- Add confidence thresholds and fallback clarifications.

### Phase 3 — theorem-prover MVP
- Implement core safety/completeness/type rules.
- Add satisfiability checks before execution.

### Phase 4 — hierarchical execution
- Implement planner tree + deterministic execution runtime.
- Add direct adapters for prototype mode.

### Phase 5 — MCP production cutover
- Bind planner leaves to MCP adapters.
- Enable production profile guardrails and remote-only enforcement.

## Testing strategy
- Unit:
  - prompt -> intent candidates
  - logical-form generation
  - theorem rule evaluation
  - planner decomposition correctness
- Integration:
  - direct mode end-to-end with mocked `ipfs_datasets_py` + local adapters
  - MCP mode end-to-end with mocked MCP responses
- Safety regression:
  - adversarial/ambiguous prompts
  - missing required entities
  - denied actions and confirmation-required actions

## Success criteria
- >=90% intent routing accuracy on curated glasses prompts for targeted workflows.
- 100% execution plans pass theorem-prover checks before tool execution.
- <1 clarification question on median for supported intent families.
- Equivalent user-facing behavior between direct prototype and MCP production modes.

## Suggested PR decomposition
- PR-A: Contracts + parser integration points + feature flags
- PR-B: Logic-form + theorem-prover MVP + tests
- PR-C: Hierarchical planner + direct adapters
- PR-D: MCP adapter binding + production policy gates + observability
