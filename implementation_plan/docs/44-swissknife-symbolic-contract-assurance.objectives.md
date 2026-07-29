# SwissKnife Symbolic Contract Assurance Objective Heap (SCA)

This objective heap is machine-ingestible planning state for the
`ipfs_accelerate_py.agent_supervisor` objective daemon. The executable
projection is
`implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md`
with task prefix `## SCA-`.

Human plan:
`implementation_plan/docs/44-swissknife-symbolic-contract-assurance-plan-2026-07-28.md`.

## North star

Make SwissKnife drift mechanically observable and repairable through a
whole-tree, content-addressed AST/contract graph; proof-directed MCP++ contract
checks against `ipfs_accelerate_py`, `ipfs_kit_py`, and `ipfs_datasets_py`;
trust-aware proof caching and optional real-ZK attestation; and bounded
counterexample-to-edit tasks that require minimal model context. Make the
model server, orchestrator, scheduler, and agent supervisor explicit contract
domains rather than assuming generic MCP discovery covers their runtime
semantics.

## Goal tree

```text
SCA-G000  Proof-directed SwissKnife contract assurance
|-- SCA-G001  Supervisor-native program sealed
|-- SCA-G010  Exact snapshot, scope, and coverage accounting
|   `-- SCA-G015  Canonical multiformats and CID identity bridge
|-- SCA-G020  Polyglot AST extraction
|   |-- SCA-G021  Whole-tree incremental index
|   `-- SCA-G022  Current authoritative index publication
|-- SCA-G030  Typed call/effect/contract graph and bounded GraphRAG
|   `-- SCA-G031  Exact datasets GraphRAG and Cypher-AST binding
|-- SCA-G040  Reviewed contract authority catalog
|   |-- SCA-G041  SwissKnife expected-contract extraction
|   |-- SCA-G042  Python package actual-surface extraction
|   `-- SCA-G043  Multi-root provider source index
|-- SCA-G050  MCP++ invocation reachability
|   |-- SCA-G051  Discovery, execution, transport, and failure parity
|   `-- SCA-G052  Endpoint-anchor and observed-contract compilation
|-- SCA-G060  Logic IR and contract obligations
|   |-- SCA-G061  Solver routing and counterexamples
|   `-- SCA-G062  Exact datasets logic and prover binding
|-- SCA-G070  Trust-aware proof cache and exact invalidation
|   `-- SCA-G071  End-to-end proof/cache orchestration
|-- SCA-G080  ZK threat model and capability policy
|   |-- SCA-G081  Receipt attestation adapter
|   `-- SCA-G082  Real datasets ZK receipt backend
|-- SCA-G090  Contract mismatch analyzer
|   `-- SCA-G091  Bug and vulnerability classification
|-- SCA-G100  Minimal CodeEditPacket materialization
|   `-- SCA-G101  Generated ipfs_accelerate_py repair board
|-- SCA-G110  Supervisor scanner/refill integration
|   `-- SCA-G111  Grok/Codex bounded provider routing
|-- SCA-G120  Shadow baseline scan and triage
|-- SCA-G130  Continuous incremental refill
|-- SCA-G140  Scale and context-budget benchmark
|-- SCA-G150  Adversarial and mutation evaluation
|-- SCA-G166  Whole-tree analyzer health recovery
|-- SCA-G167  Symbolic-only execution and bounded provider enforcement
|-- SCA-G168  Canonical SwissKnife snapshot authority
|-- SCA-G170  Versioned runtime-component contract catalog
|   |-- SCA-G171  Model-server route and inference contracts
|   |-- SCA-G172  Orchestrator lifecycle contracts
|   |-- SCA-G173  Scheduler authority and concurrency contracts
|   |-- SCA-G174  Agent-supervisor control and goal/task contracts
|   |-- SCA-G175  Cross-component state-machine and MCP++ proofs
|   `-- SCA-G176  Runtime drift refinery and continuous refill
`-- SCA-G160  Promotion, operations, and closeout
```

## SCA-G000 Proof-directed SwissKnife contract assurance

- Status: reopened
- Parent:
- Priority: P0
- Track: swissknife-contract-assurance
- Bundle: swissknife/contract-assurance/root
- Goal: Deliver a running supervisor program that indexes the complete tracked SwissKnife tree, constructs exact MCP++ call and contract claims, proves or refutes supported claims under explicit authority, and emits minimal targeted accelerator repair tasks.
- Evidence: SCAEV000ROOT
- Outputs: implementation_plan/docs/44-swissknife-symbolic-contract-assurance-plan-2026-07-28.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md, config/swissknife_symbolic_contract_assurance_supervisor.json, config/swissknife_symbolic_contract_assurance_lane_inventory.json, scripts/swissknife_parallel_implementation_supervisor.py
- Validation: test -f implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md && python3 -m json.tool config/swissknife_symbolic_contract_assurance_supervisor.json >/dev/null && python3 -m json.tool config/swissknife_symbolic_contract_assurance_lane_inventory.json >/dev/null && python3 -m py_compile scripts/swissknife_parallel_implementation_supervisor.py
- Acceptance: Every child goal is completed or explicitly blocked with typed evidence; no unaccounted tracked SwissKnife path; model-server/orchestrator/scheduler/supervisor contracts have current terminal states; generated repair tasks bind current counterexamples and re-proof commands; supervisor refill remains bounded.
- Gap task: Execute child workstreams by task dependency and conflict policy.
- Conflict policy: Own the SCA planning, configuration, and runtime namespaces; do not rewrite SVD/SWR histories or the CBP proof trust model.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Every child goal is completed or explicitly blocked with typed evidence","no unaccounted tracked SwissKnife path","model-server/orchestrator/scheduler/supervisor contracts have current terminal states","generated repair tasks bind current counterexamples and re-proof commands","supervisor refill remains bounded."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-32fac5c4e31362c4657aff99fb5f8416","contradiction-630c545ac131055a9a80802f721bc746","contradiction-da8554f3386660917f5076229b93f0db","contradiction-dac854015f9564d6fd9f67b7a2a72443","contradiction-ebb4702cfe77261814db9b9989ff0354"],"contradictions":[{"contradiction_id":"contradiction-32fac5c4e31362c4657aff99fb5f8416","detected_at":null,"fingerprint":"contradiction-32fac5c4e31362c4657aff99fb5f8416","goal_id":"SCA-G000","impacted_criteria":["Every child goal is completed or explicitly blocked with typed evidence","generated repair tasks bind current counterexamples and re-proof commands","model-server/orchestrator/scheduler/supervisor contracts have current terminal states","no unaccounted tracked SwissKnife path","supervisor refill remains bounded."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5."},{"contradiction_id":"contradiction-630c545ac131055a9a80802f721bc746","detected_at":null,"fingerprint":"contradiction-630c545ac131055a9a80802f721bc746","goal_id":"SCA-G000","impacted_criteria":["Every child goal is completed or explicitly blocked with typed evidence","generated repair tasks bind current counterexamples and re-proof commands","model-server/orchestrator/scheduler/supervisor contracts have current terminal states","no unaccounted tracked SwissKnife path","supervisor refill remains bounded."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226."},{"contradiction_id":"contradiction-da8554f3386660917f5076229b93f0db","detected_at":null,"fingerprint":"contradiction-da8554f3386660917f5076229b93f0db","goal_id":"SCA-G000","impacted_criteria":["Every child goal is completed or explicitly blocked with typed evidence","generated repair tasks bind current counterexamples and re-proof commands","model-server/orchestrator/scheduler/supervisor contracts have current terminal states","no unaccounted tracked SwissKnife path","supervisor refill remains bounded."],"invalidated_evidence":["goal:SCA-G040"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G040"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G040"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G040 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."},{"contradiction_id":"contradiction-dac854015f9564d6fd9f67b7a2a72443","detected_at":null,"fingerprint":"contradiction-dac854015f9564d6fd9f67b7a2a72443","goal_id":"SCA-G000","impacted_criteria":["Every child goal is completed or explicitly blocked with typed evidence","generated repair tasks bind current counterexamples and re-proof commands","model-server/orchestrator/scheduler/supervisor contracts have current terminal states","no unaccounted tracked SwissKnife path","supervisor refill remains bounded."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c."},{"contradiction_id":"contradiction-ebb4702cfe77261814db9b9989ff0354","detected_at":null,"fingerprint":"contradiction-ebb4702cfe77261814db9b9989ff0354","goal_id":"SCA-G000","impacted_criteria":["Every child goal is completed or explicitly blocked with typed evidence","generated repair tasks bind current counterexamples and re-proof commands","model-server/orchestrator/scheduler/supervisor contracts have current terminal states","no unaccounted tracked SwissKnife path","supervisor refill remains bounded."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-6d1f278ceae9d809439ed624878828ff9a59f511."}],"goal_id":"SCA-G000","historical_completion_receipt_ids":[],"impacted_criteria":["Every child goal is completed or explicitly blocked with typed evidence","generated repair tasks bind current counterexamples and re-proof commands","model-server/orchestrator/scheduler/supervisor contracts have current terminal states","no unaccounted tracked SwissKnife path","supervisor refill remains bounded."],"invalidated_evidence":["goal:SCA-G020","goal:SCA-G040"],"newly_scheduled_work":[{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G020"},{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G040"}],"previous_state":"provisionally_complete","receipt_id":"reopen-40ed87503f532e8dfe2f6ca689e78d1e","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G040"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-32fac5c4e31362c4657aff99fb5f8416","contradiction-630c545ac131055a9a80802f721bc746","contradiction-da8554f3386660917f5076229b93f0db","contradiction-dac854015f9564d6fd9f67b7a2a72443","contradiction-ebb4702cfe77261814db9b9989ff0354"]
- Contradiction impacted criteria: ["Every child goal is completed or explicitly blocked with typed evidence","generated repair tasks bind current counterexamples and re-proof commands","model-server/orchestrator/scheduler/supervisor contracts have current terminal states","no unaccounted tracked SwissKnife path","supervisor refill remains bounded."]
- Contradiction invalidated evidence: ["goal:SCA-G020","goal:SCA-G040"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G040"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"}]
- Newly scheduled work: [{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G020"},{"goal_id":"SCA-G000","reason":"child_reopened","source_goal_id":"SCA-G040"}]

## SCA-G001 Supervisor-native program sealed

- Status: provisionally_complete
- Parent: SCA-G000
- Priority: P0
- Track: planning
- Bundle: swissknife/contract-assurance/planning
- Goal: Seal the reviewed SCA plan, objective heap, executable taskboard, supervisor profile, and lease inventory before implementation work begins.
- Evidence: SCAEV001PLAN
- Outputs: implementation_plan/docs/44-swissknife-symbolic-contract-assurance-plan-2026-07-28.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md, config/swissknife_symbolic_contract_assurance_supervisor.json, config/swissknife_symbolic_contract_assurance_lane_inventory.json, scripts/swissknife_parallel_implementation_supervisor.py
- Validation: test -f implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md && python3 -m json.tool config/swissknife_symbolic_contract_assurance_supervisor.json >/dev/null && python3 -m json.tool config/swissknife_symbolic_contract_assurance_lane_inventory.json >/dev/null && python3 -m py_compile scripts/swissknife_parallel_implementation_supervisor.py
- Acceptance: Plan, goals, tasks, identity profiles, proof authority, bounds, and launch command parse under supervisor-native validators and the planning task is complete.
- Gap task: SCA-000
- Conflict policy: Own SCA planning/configuration only; preserve prior boards and runtime histories.
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Plan, goals, tasks, identity profiles, proof authority, bounds, and launch command parse under supervisor-native validators and the planning task is complete."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Plan, goals, tasks, identity profiles, proof authority, bounds, and launch command parse under supervisor-native validators and the planning task is complete.; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G010 Exact snapshot, scope, and coverage accounting

- Status: reopened
- Parent: SCA-G000
- Priority: P0
- Track: snapshot
- Bundle: swissknife/contract-assurance/snapshot
- Goal: Bind Git trees, submodule identities, tracked/staged/modified/deleted paths, and allowlisted untracked overlays into one canonical snapshot and issue exactly one coverage disposition for every tracked SwissKnife path.
- Evidence: SCAEV010SNAP
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_snapshot.py, config/swissknife_symbolic_contract_scope.json, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_snapshot.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_snapshot.py -q
- Acceptance: Snapshot identity changes for every behavior-affecting overlay; all 5,771 baseline tracked paths are accounted for on the seed fixture; recursive gitlinks and exclusions are explicit; node_modules and caches are dependency metadata, not source authority.
- Gap task: SCA-010
- Conflict policy: Extend analysis identity contracts; do not weaken existing clean-tree or proof-cache bindings.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Snapshot identity changes for every behavior-affecting overlay","all 5,771 baseline tracked paths are accounted for on the seed fixture","recursive gitlinks and exclusions are explicit","node_modules and caches are dependency metadata, not source authority."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-1f31507c51f21b105afbd4d2ca086d7f","contradiction-4ec588553f5a5a2437d5cfa9a4322257","contradiction-96ed8dfe154577c690a9be85fec4cffb","contradiction-c5fe5b2f953497f491c103b4428d9377","contradiction-f22e5af53d80572254ff18545441fa43"],"contradictions":[{"contradiction_id":"contradiction-1f31507c51f21b105afbd4d2ca086d7f","detected_at":null,"fingerprint":"contradiction-1f31507c51f21b105afbd4d2ca086d7f","goal_id":"SCA-G010","impacted_criteria":["771 baseline tracked paths are accounted for on the seed fixture","all 5","node_modules and caches are dependency metadata","not source authority.","recursive gitlinks and exclusions are explicit","Snapshot identity changes for every behavior-affecting overlay"],"invalidated_evidence":["goal:SCA-G040"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G040"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G040"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G040 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."},{"contradiction_id":"contradiction-4ec588553f5a5a2437d5cfa9a4322257","detected_at":null,"fingerprint":"contradiction-4ec588553f5a5a2437d5cfa9a4322257","goal_id":"SCA-G010","impacted_criteria":["771 baseline tracked paths are accounted for on the seed fixture","all 5","node_modules and caches are dependency metadata","not source authority.","recursive gitlinks and exclusions are explicit","Snapshot identity changes for every behavior-affecting overlay"],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-6d1f278ceae9d809439ed624878828ff9a59f511."},{"contradiction_id":"contradiction-96ed8dfe154577c690a9be85fec4cffb","detected_at":null,"fingerprint":"contradiction-96ed8dfe154577c690a9be85fec4cffb","goal_id":"SCA-G010","impacted_criteria":["771 baseline tracked paths are accounted for on the seed fixture","all 5","node_modules and caches are dependency metadata","not source authority.","recursive gitlinks and exclusions are explicit","Snapshot identity changes for every behavior-affecting overlay"],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c."},{"contradiction_id":"contradiction-c5fe5b2f953497f491c103b4428d9377","detected_at":null,"fingerprint":"contradiction-c5fe5b2f953497f491c103b4428d9377","goal_id":"SCA-G010","impacted_criteria":["771 baseline tracked paths are accounted for on the seed fixture","all 5","node_modules and caches are dependency metadata","not source authority.","recursive gitlinks and exclusions are explicit","Snapshot identity changes for every behavior-affecting overlay"],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5."},{"contradiction_id":"contradiction-f22e5af53d80572254ff18545441fa43","detected_at":null,"fingerprint":"contradiction-f22e5af53d80572254ff18545441fa43","goal_id":"SCA-G010","impacted_criteria":["771 baseline tracked paths are accounted for on the seed fixture","all 5","node_modules and caches are dependency metadata","not source authority.","recursive gitlinks and exclusions are explicit","Snapshot identity changes for every behavior-affecting overlay"],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226."}],"goal_id":"SCA-G010","historical_completion_receipt_ids":[],"impacted_criteria":["771 baseline tracked paths are accounted for on the seed fixture","all 5","node_modules and caches are dependency metadata","not source authority.","recursive gitlinks and exclusions are explicit","Snapshot identity changes for every behavior-affecting overlay"],"invalidated_evidence":["goal:SCA-G020","goal:SCA-G040"],"newly_scheduled_work":[{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G020"},{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G040"}],"previous_state":"provisionally_complete","receipt_id":"reopen-a42874c8a5ba786a4862c6864229d17e","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G040"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-1f31507c51f21b105afbd4d2ca086d7f","contradiction-4ec588553f5a5a2437d5cfa9a4322257","contradiction-96ed8dfe154577c690a9be85fec4cffb","contradiction-c5fe5b2f953497f491c103b4428d9377","contradiction-f22e5af53d80572254ff18545441fa43"]
- Contradiction impacted criteria: ["771 baseline tracked paths are accounted for on the seed fixture","Snapshot identity changes for every behavior-affecting overlay","all 5","node_modules and caches are dependency metadata","not source authority.","recursive gitlinks and exclusions are explicit"]
- Contradiction invalidated evidence: ["goal:SCA-G020","goal:SCA-G040"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G040"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"}]
- Newly scheduled work: [{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G020"},{"goal_id":"SCA-G010","reason":"child_reopened","source_goal_id":"SCA-G040"}]

## SCA-G015 Canonical multiformats and CID identity bridge

- Status: reopened
- Parent: SCA-G010
- Priority: P0
- Track: content-identity
- Bundle: swissknife/contract-assurance/content-identity
- Goal: Normalize accelerator artifacts through explicit canonicalization profiles and bind their exact bytes to validated CIDv1, multicodec, multihash, multibase, and plain digest metadata using the datasets identity modules.
- Evidence: SCAEV015CID
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py -q
- Acceptance: Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256; logic IR uses its separately declared domain-separated raw-codec profile; decoded multihash equals the SHA-256 digest of the exact retained canonical bytes; profile differences among cid_utils, ir_core.identity, ipld_cid, and profile_g remain explicit contradictions; unavailable multiformats support fails closed and no fallback digest is labeled CID.
- Gap task: SCA-015, SCA-220
- Conflict policy: Reuse datasets canonical identity APIs behind a lazy accelerator bridge; never change identity profile or canonicalization implicitly and never create a second proof-cache authority.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","logic IR uses its separately declared domain-separated raw-codec profile","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","profile differences among cid_utils, ir_core.identity, ipld_cid, and profile_g remain explicit contradictions","unavailable multiformats support fails closed and no fallback digest is labeled CID."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-01b373891bba5cb227b1afa222e97e71","contradiction-2585ec991fdaf2291708a977dce1be02","contradiction-66bb13ee95568467cf5d5be5fbc07763","contradiction-ab8e87e8e2b902bd86d704c4e8851804","contradiction-d33e57dc502775f5cb1885451ff2a4a4"],"contradictions":[{"contradiction_id":"contradiction-01b373891bba5cb227b1afa222e97e71","detected_at":null,"fingerprint":"contradiction-01b373891bba5cb227b1afa222e97e71","goal_id":"SCA-G015","impacted_criteria":["and profile_g remain explicit contradictions","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","ipld_cid","ir_core.identity","logic IR uses its separately declared domain-separated raw-codec profile","profile differences among cid_utils","Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","unavailable multiformats support fails closed and no fallback digest is labeled CID."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G015","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5."},{"contradiction_id":"contradiction-2585ec991fdaf2291708a977dce1be02","detected_at":null,"fingerprint":"contradiction-2585ec991fdaf2291708a977dce1be02","goal_id":"SCA-G015","impacted_criteria":["and profile_g remain explicit contradictions","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","ipld_cid","ir_core.identity","logic IR uses its separately declared domain-separated raw-codec profile","profile differences among cid_utils","Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","unavailable multiformats support fails closed and no fallback digest is labeled CID."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G015","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226."},{"contradiction_id":"contradiction-66bb13ee95568467cf5d5be5fbc07763","detected_at":null,"fingerprint":"contradiction-66bb13ee95568467cf5d5be5fbc07763","goal_id":"SCA-G015","impacted_criteria":["and profile_g remain explicit contradictions","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","ipld_cid","ir_core.identity","logic IR uses its separately declared domain-separated raw-codec profile","profile differences among cid_utils","Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","unavailable multiformats support fails closed and no fallback digest is labeled CID."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G015","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c."},{"contradiction_id":"contradiction-ab8e87e8e2b902bd86d704c4e8851804","detected_at":null,"fingerprint":"contradiction-ab8e87e8e2b902bd86d704c4e8851804","goal_id":"SCA-G015","impacted_criteria":["and profile_g remain explicit contradictions","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","ipld_cid","ir_core.identity","logic IR uses its separately declared domain-separated raw-codec profile","profile differences among cid_utils","Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","unavailable multiformats support fails closed and no fallback digest is labeled CID."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G015","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."},{"contradiction_id":"contradiction-d33e57dc502775f5cb1885451ff2a4a4","detected_at":null,"fingerprint":"contradiction-d33e57dc502775f5cb1885451ff2a4a4","goal_id":"SCA-G015","impacted_criteria":["and profile_g remain explicit contradictions","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","ipld_cid","ir_core.identity","logic IR uses its separately declared domain-separated raw-codec profile","profile differences among cid_utils","Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","unavailable multiformats support fails closed and no fallback digest is labeled CID."],"invalidated_evidence":["goal:SCA-G020"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G015","reason":"child_reopened","source_goal_id":"SCA-G020"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},"source_receipt_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","summary":"Child goal SCA-G020 was reopened by contradiction contradiction-6d1f278ceae9d809439ed624878828ff9a59f511."}],"goal_id":"SCA-G015","historical_completion_receipt_ids":[],"impacted_criteria":["and profile_g remain explicit contradictions","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","ipld_cid","ir_core.identity","logic IR uses its separately declared domain-separated raw-codec profile","profile differences among cid_utils","Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","unavailable multiformats support fails closed and no fallback digest is labeled CID."],"invalidated_evidence":["goal:SCA-G020"],"newly_scheduled_work":[{"goal_id":"SCA-G015","reason":"child_reopened","source_goal_id":"SCA-G020"}],"previous_state":"provisionally_complete","receipt_id":"reopen-2e5ea2784fb5a487f519b6b1c7ad17ca","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-01b373891bba5cb227b1afa222e97e71","contradiction-2585ec991fdaf2291708a977dce1be02","contradiction-66bb13ee95568467cf5d5be5fbc07763","contradiction-ab8e87e8e2b902bd86d704c4e8851804","contradiction-d33e57dc502775f5cb1885451ff2a4a4"]
- Contradiction impacted criteria: ["Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","and profile_g remain explicit contradictions","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","ipld_cid","ir_core.identity","logic IR uses its separately declared domain-separated raw-codec profile","profile differences among cid_utils","unavailable multiformats support fails closed and no fallback digest is labeled CID."]
- Contradiction invalidated evidence: ["goal:SCA-G020"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G020"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G020"}]
- Newly scheduled work: [{"goal_id":"SCA-G015","reason":"child_reopened","source_goal_id":"SCA-G020"}]

## SCA-G020 Polyglot AST extraction

- Status: reopened
- Parent: SCA-G000, SCA-G010, SCA-G015
- Priority: P0
- Track: ast
- Bundle: swissknife/contract-assurance/ast
- Goal: Add deterministic TypeScript, JavaScript, TSX, JSX, Python, and structured-schema producers that emit canonical path-independent AST facts without model calls.
- Evidence: SCAEV020AST
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/polyglot_ast_provider.py, external/ipfs_accelerate/scripts/extract_typescript_ast.mjs, external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_provider.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_provider.py -q
- Acceptance: Stable symbols/imports/calls/interfaces/effects and source ranges; TypeScript compiler version is bound; bodies remain in CAS; unsupported syntax and parser failure are typed; cold import starts no Node process.
- Gap task: SCA-020
- Conflict policy: Reuse ASTBlobRecord interchange and AnalysisASTIndex; add a producer, not a second AST index.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Stable symbols/imports/calls/interfaces/effects and source ranges","TypeScript compiler version is bound","bodies remain in CAS","unsupported syntax and parser failure are typed","cold import starts no Node process."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-308e60a1ccf6d7b47a55975e66aac131","contradiction-5b16d6ca33124094b704e0f57254a132","contradiction-66b67eba9f3ef24c85e331fcdfcbe604","contradiction-94dd8c3cb5be2280d0224a90a0566af8","contradiction-bf4afaea548966f5a7feebf678c9b3d0"],"contradictions":[{"contradiction_id":"contradiction-308e60a1ccf6d7b47a55975e66aac131","detected_at":null,"fingerprint":"contradiction-308e60a1ccf6d7b47a55975e66aac131","goal_id":"SCA-G020","impacted_criteria":["bodies remain in CAS","cold import starts no Node process.","Stable symbols/imports/calls/interfaces/effects and source ranges","TypeScript compiler version is bound","unsupported syntax and parser failure are typed"],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G020","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5."},{"contradiction_id":"contradiction-5b16d6ca33124094b704e0f57254a132","detected_at":null,"fingerprint":"contradiction-5b16d6ca33124094b704e0f57254a132","goal_id":"SCA-G020","impacted_criteria":["bodies remain in CAS","cold import starts no Node process.","Stable symbols/imports/calls/interfaces/effects and source ranges","TypeScript compiler version is bound","unsupported syntax and parser failure are typed"],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G020","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226."},{"contradiction_id":"contradiction-66b67eba9f3ef24c85e331fcdfcbe604","detected_at":null,"fingerprint":"contradiction-66b67eba9f3ef24c85e331fcdfcbe604","goal_id":"SCA-G020","impacted_criteria":["bodies remain in CAS","cold import starts no Node process.","Stable symbols/imports/calls/interfaces/effects and source ranges","TypeScript compiler version is bound","unsupported syntax and parser failure are typed"],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G020","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-6d1f278ceae9d809439ed624878828ff9a59f511."},{"contradiction_id":"contradiction-94dd8c3cb5be2280d0224a90a0566af8","detected_at":null,"fingerprint":"contradiction-94dd8c3cb5be2280d0224a90a0566af8","goal_id":"SCA-G020","impacted_criteria":["bodies remain in CAS","cold import starts no Node process.","Stable symbols/imports/calls/interfaces/effects and source ranges","TypeScript compiler version is bound","unsupported syntax and parser failure are typed"],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G020","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c."},{"contradiction_id":"contradiction-bf4afaea548966f5a7feebf678c9b3d0","detected_at":null,"fingerprint":"contradiction-bf4afaea548966f5a7feebf678c9b3d0","goal_id":"SCA-G020","impacted_criteria":["bodies remain in CAS","cold import starts no Node process.","Stable symbols/imports/calls/interfaces/effects and source ranges","TypeScript compiler version is bound","unsupported syntax and parser failure are typed"],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G020","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."}],"goal_id":"SCA-G020","historical_completion_receipt_ids":[],"impacted_criteria":["bodies remain in CAS","cold import starts no Node process.","Stable symbols/imports/calls/interfaces/effects and source ranges","TypeScript compiler version is bound","unsupported syntax and parser failure are typed"],"invalidated_evidence":["goal:SCA-G041"],"newly_scheduled_work":[{"goal_id":"SCA-G020","reason":"child_reopened","source_goal_id":"SCA-G041"}],"previous_state":"provisionally_complete","receipt_id":"reopen-f276967d104a073e750e72b035003526","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G041"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-308e60a1ccf6d7b47a55975e66aac131","contradiction-5b16d6ca33124094b704e0f57254a132","contradiction-66b67eba9f3ef24c85e331fcdfcbe604","contradiction-94dd8c3cb5be2280d0224a90a0566af8","contradiction-bf4afaea548966f5a7feebf678c9b3d0"]
- Contradiction impacted criteria: ["Stable symbols/imports/calls/interfaces/effects and source ranges","TypeScript compiler version is bound","bodies remain in CAS","cold import starts no Node process.","unsupported syntax and parser failure are typed"]
- Contradiction invalidated evidence: ["goal:SCA-G041"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G041"}]
- Newly scheduled work: [{"goal_id":"SCA-G020","reason":"child_reopened","source_goal_id":"SCA-G041"}]

## SCA-G021 Whole-tree incremental index

- Status: reopened
- Parent: SCA-G020
- Priority: P0
- Track: ast-index
- Bundle: swissknife/contract-assurance/index
- Goal: Scan the exact SwissKnife snapshot, reuse unchanged blob records, persist compact index/CAS artifacts, and prove coverage and invalidation accounting.
- Evidence: SCAEV021INDEX
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_indexer.py, external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_indexer.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_indexer.py -q
- Acceptance: Every tracked path has one disposition; no source body in compact rows; unchanged blobs are cache hits; rename/delete/change invalidations are exact; partial analyzer health cannot claim exhaustive coverage.
- Gap task: SCA-021
- Conflict policy: Compose repository_snapshot, AnalysisASTIndex, analysis_cache, runtime CAS, and analyzer_health.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Every tracked path has one disposition","no source body in compact rows","unchanged blobs are cache hits","rename/delete/change invalidations are exact","partial analyzer health cannot claim exhaustive coverage."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-cc356700e56eabb57c18a8be2a4ffd28"],"contradictions":[{"contradiction_id":"contradiction-cc356700e56eabb57c18a8be2a4ffd28","detected_at":null,"fingerprint":"contradiction-cc356700e56eabb57c18a8be2a4ffd28","goal_id":"SCA-G021","impacted_criteria":["Every tracked path has one disposition","no source body in compact rows","partial analyzer health cannot claim exhaustive coverage.","rename/delete/change invalidations are exact","unchanged blobs are cache hits"],"invalidated_evidence":["goal:SCA-G030"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G021","reason":"child_reopened","source_goal_id":"SCA-G030"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G030"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G030 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."}],"goal_id":"SCA-G021","historical_completion_receipt_ids":[],"impacted_criteria":["Every tracked path has one disposition","no source body in compact rows","partial analyzer health cannot claim exhaustive coverage.","rename/delete/change invalidations are exact","unchanged blobs are cache hits"],"invalidated_evidence":["goal:SCA-G030"],"newly_scheduled_work":[{"goal_id":"SCA-G021","reason":"child_reopened","source_goal_id":"SCA-G030"}],"previous_state":"provisionally_complete","receipt_id":"reopen-7c5adc9d0f77aa92c10a3f5e05a726db","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G030"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-cc356700e56eabb57c18a8be2a4ffd28"]
- Contradiction impacted criteria: ["Every tracked path has one disposition","no source body in compact rows","partial analyzer health cannot claim exhaustive coverage.","rename/delete/change invalidations are exact","unchanged blobs are cache hits"]
- Contradiction invalidated evidence: ["goal:SCA-G030"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G030"}]
- Newly scheduled work: [{"goal_id":"SCA-G021","reason":"child_reopened","source_goal_id":"SCA-G030"}]

## SCA-G030 Typed call/effect/contract graph and bounded GraphRAG

- Status: reopened
- Parent: SCA-G021
- Priority: P0
- Track: graph
- Bundle: swissknife/contract-assurance/graph
- Goal: Project indexed facts into typed module/symbol/call/effect/schema/tool/handler edges and expose bounded GraphRAG candidate retrieval followed by deterministic mandatory closure.
- Evidence: SCAEV030GRAPH
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/symbolic_contract_graph.py, external/ipfs_accelerate/test/api/test_agent_supervisor_symbolic_contract_graph.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_symbolic_contract_graph.py -q
- Acceptance: Every node/edge carries identity, provenance, authority, snapshot, and version; GraphRAG edges are context-only; mandatory closure is deterministic and reports truncation or missing edges.
- Gap task: SCA-030
- Conflict policy: Extend CodeEvidenceGraph/semantic_dependency_graph and use the lazy ipfs_datasets analysis provider; no proof authority from graph rank.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Every node/edge carries identity, provenance, authority, snapshot, and version","GraphRAG edges are context-only","mandatory closure is deterministic and reports truncation or missing edges."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-0b7f4af3971df7e0fdd45308a81b90e4"],"contradictions":[{"contradiction_id":"contradiction-0b7f4af3971df7e0fdd45308a81b90e4","detected_at":null,"fingerprint":"contradiction-0b7f4af3971df7e0fdd45308a81b90e4","goal_id":"SCA-G030","impacted_criteria":["and version","authority","Every node/edge carries identity","GraphRAG edges are context-only","mandatory closure is deterministic and reports truncation or missing edges.","provenance","snapshot"],"invalidated_evidence":["goal:SCA-G050"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G030","reason":"child_reopened","source_goal_id":"SCA-G050"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G050 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."}],"goal_id":"SCA-G030","historical_completion_receipt_ids":[],"impacted_criteria":["and version","authority","Every node/edge carries identity","GraphRAG edges are context-only","mandatory closure is deterministic and reports truncation or missing edges.","provenance","snapshot"],"invalidated_evidence":["goal:SCA-G050"],"newly_scheduled_work":[{"goal_id":"SCA-G030","reason":"child_reopened","source_goal_id":"SCA-G050"}],"previous_state":"provisionally_complete","receipt_id":"reopen-71ffecc882b10d5f9b4ea05079e192df","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-0b7f4af3971df7e0fdd45308a81b90e4"]
- Contradiction impacted criteria: ["Every node/edge carries identity","GraphRAG edges are context-only","and version","authority","mandatory closure is deterministic and reports truncation or missing edges.","provenance","snapshot"]
- Contradiction invalidated evidence: ["goal:SCA-G050"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"}]
- Newly scheduled work: [{"goal_id":"SCA-G030","reason":"child_reopened","source_goal_id":"SCA-G050"}]

## SCA-G040 Reviewed contract authority catalog

- Status: reopened
- Parent: SCA-G000, SCA-G010
- Priority: P0
- Track: contracts
- Bundle: swissknife/contract-assurance/catalog
- Goal: Define versioned contract records, source precedence, contradiction handling, and reviewed property families for MCP++ declarations and implementations.
- Evidence: SCAEV040CAT
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_catalog.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_catalog.py -q
- Acceptance: IDL/schema/type/test/registration/manifest/doc sources retain authority class; conflicts remain explicit; inferred natural language cannot silently become a reviewed contract.
- Gap task: SCA-040
- Conflict policy: Adapt code_property_catalog and interface_contract_codegen; do not introduce a parallel assurance lattice.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["IDL/schema/type/test/registration/manifest/doc sources retain authority class","conflicts remain explicit","inferred natural language cannot silently become a reviewed contract."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-2aa77006106bd72774747f7df7eba2e6","contradiction-38b72764dcc92ace8da7e0f69d21d9ab","contradiction-5792647076c7ae464a6290de169330ae","contradiction-a757441329c8855cf299aa216829531b","contradiction-ee468407e062884da15991aeabc16ddc"],"contradictions":[{"contradiction_id":"contradiction-2aa77006106bd72774747f7df7eba2e6","detected_at":null,"fingerprint":"contradiction-2aa77006106bd72774747f7df7eba2e6","goal_id":"SCA-G040","impacted_criteria":["conflicts remain explicit","IDL/schema/type/test/registration/manifest/doc sources retain authority class","inferred natural language cannot silently become a reviewed contract."],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226."},{"contradiction_id":"contradiction-38b72764dcc92ace8da7e0f69d21d9ab","detected_at":null,"fingerprint":"contradiction-38b72764dcc92ace8da7e0f69d21d9ab","goal_id":"SCA-G040","impacted_criteria":["conflicts remain explicit","IDL/schema/type/test/registration/manifest/doc sources retain authority class","inferred natural language cannot silently become a reviewed contract."],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-6d1f278ceae9d809439ed624878828ff9a59f511."},{"contradiction_id":"contradiction-5792647076c7ae464a6290de169330ae","detected_at":null,"fingerprint":"contradiction-5792647076c7ae464a6290de169330ae","goal_id":"SCA-G040","impacted_criteria":["conflicts remain explicit","IDL/schema/type/test/registration/manifest/doc sources retain authority class","inferred natural language cannot silently become a reviewed contract."],"invalidated_evidence":["goal:SCA-G060"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G060"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G060"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G060 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."},{"contradiction_id":"contradiction-a757441329c8855cf299aa216829531b","detected_at":null,"fingerprint":"contradiction-a757441329c8855cf299aa216829531b","goal_id":"SCA-G040","impacted_criteria":["conflicts remain explicit","IDL/schema/type/test/registration/manifest/doc sources retain authority class","inferred natural language cannot silently become a reviewed contract."],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c."},{"contradiction_id":"contradiction-ee468407e062884da15991aeabc16ddc","detected_at":null,"fingerprint":"contradiction-ee468407e062884da15991aeabc16ddc","goal_id":"SCA-G040","impacted_criteria":["conflicts remain explicit","IDL/schema/type/test/registration/manifest/doc sources retain authority class","inferred natural language cannot silently become a reviewed contract."],"invalidated_evidence":["goal:SCA-G041"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G041"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G041"},"source_receipt_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","summary":"Child goal SCA-G041 was reopened by contradiction contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5."}],"goal_id":"SCA-G040","historical_completion_receipt_ids":[],"impacted_criteria":["conflicts remain explicit","IDL/schema/type/test/registration/manifest/doc sources retain authority class","inferred natural language cannot silently become a reviewed contract."],"invalidated_evidence":["goal:SCA-G041","goal:SCA-G060"],"newly_scheduled_work":[{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G041"},{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G060"}],"previous_state":"provisionally_complete","receipt_id":"reopen-63cb01ac8ae359484078322763c90e92","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G060"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G041"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-2aa77006106bd72774747f7df7eba2e6","contradiction-38b72764dcc92ace8da7e0f69d21d9ab","contradiction-5792647076c7ae464a6290de169330ae","contradiction-a757441329c8855cf299aa216829531b","contradiction-ee468407e062884da15991aeabc16ddc"]
- Contradiction impacted criteria: ["IDL/schema/type/test/registration/manifest/doc sources retain authority class","conflicts remain explicit","inferred natural language cannot silently become a reviewed contract."]
- Contradiction invalidated evidence: ["goal:SCA-G041","goal:SCA-G060"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G060"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","source_goal_id":"SCA-G041"},{"kind":"child_reopened","root_contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","source_goal_id":"SCA-G041"}]
- Newly scheduled work: [{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G041"},{"goal_id":"SCA-G040","reason":"child_reopened","source_goal_id":"SCA-G060"}]

## SCA-G041 SwissKnife expected-contract extraction

- Status: reopened
- Parent: SCA-G020, SCA-G040
- Priority: P0
- Track: expected-contracts
- Bundle: swissknife/contract-assurance/expected
- Goal: Deterministically extract SwissKnife MCP++ descriptors, schemas, registries, connectors, policy mediators, compatibility endpoints, generated app bindings, and contract tests into the reviewed catalog.
- Evidence: SCAEV041EXPECTED
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/swissknife_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_contract_extractor.py -q
- Acceptance: Source precedence and version are explicit; dynamic declarations are unresolved, not guessed; direct REST/fetch paths and compatibility routes are represented for bypass checks.
- Gap task: SCA-041
- Conflict policy: Read SwissKnife as evidence; implementation changes remain separate counterexample-driven tasks.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Source precedence and version are explicit","dynamic declarations are unresolved, not guessed","direct REST/fetch paths and compatibility routes are represented for bypass checks."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-4c07cc98fb66e29f98d51629eb51fedc","contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226"],"contradictions":[{"contradiction_id":"contradiction-4c07cc98fb66e29f98d51629eb51fedc","detected_at":null,"fingerprint":"contradiction-4c07cc98fb66e29f98d51629eb51fedc","goal_id":"SCA-G041","impacted_criteria":["direct REST/fetch paths and compatibility routes are represented for bypass checks.","dynamic declarations are unresolved","not guessed","Source precedence and version are explicit"],"invalidated_evidence":["goal:SCA-G050"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G041","reason":"child_reopened","source_goal_id":"SCA-G050"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G050 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."},{"contradiction_id":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","detected_at":null,"fingerprint":"contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","goal_id":"SCA-G041","impacted_criteria":["direct REST/fetch paths and compatibility routes are represented for bypass checks.","dynamic declarations are unresolved, not guessed","Source precedence and version are explicit"],"invalidated_evidence":[],"kind":"mapped_finding","scheduled_work":[{"task_id":"SCA-202"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeram2tj5oizlpziganj6wuzh6pmn6vaqz6wd7k3bucve4nlpugg4ida","canonical_task_key":"task/v1/66a69eb9195bf28301a9f5a993f9ec6faa0867d61fd5b0d055271ab7d0c6e206","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-202-codebase-scan-dc5339180262.md","fingerprint":"dc5339180262e3dc3ca1d8ef5b981431a4234ac6","follow_up_task_id":"SCA-202","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"66a69eb9195bf28301a9f5a993f9ec6faa0867d61fd5b0d055271ab7d0c6e206","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:296"},"finding_id":"dc5339180262e3dc3ca1d8ef5b981431a4234ac6","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},"source_receipt_id":"dc5339180262e3dc3ca1d8ef5b981431a4234ac6","summary":"swallowed_exception"},{"contradiction_id":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","detected_at":null,"fingerprint":"contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","goal_id":"SCA-G041","impacted_criteria":["direct REST/fetch paths and compatibility routes are represented for bypass checks.","dynamic declarations are unresolved, not guessed","Source precedence and version are explicit"],"invalidated_evidence":[],"kind":"mapped_finding","scheduled_work":[{"task_id":"SCA-203"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeerazj34bhuafh4peqzfjkbkkaoy3wrw2qkf27fyclvtjr67ad343tmq","canonical_task_key":"task/v1/ca77c09e8029f8f243254a82a501d8dda36d4145d7cb812eb34c7df00f7cdcd9","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-203-codebase-scan-f1650d37e707.md","fingerprint":"f1650d37e707959222e15790aeef30ddc7f8809e","follow_up_task_id":"SCA-203","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"ca77c09e8029f8f243254a82a501d8dda36d4145d7cb812eb34c7df00f7cdcd9","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2529"},"finding_id":"f1650d37e707959222e15790aeef30ddc7f8809e","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},"source_receipt_id":"f1650d37e707959222e15790aeef30ddc7f8809e","summary":"swallowed_exception"},{"contradiction_id":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","detected_at":null,"fingerprint":"contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","goal_id":"SCA-G041","impacted_criteria":["direct REST/fetch paths and compatibility routes are represented for bypass checks.","dynamic declarations are unresolved, not guessed","Source precedence and version are explicit"],"invalidated_evidence":[],"kind":"mapped_finding","scheduled_work":[{"task_id":"SCA-204"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeradoixxl755jatibjev5tlhip4gdkoqvba2aqtn66lea4wvlste2gq","canonical_task_key":"task/v1/1b917baffdea41340524af66b3a1fc30d4e85420d02136fbcb20396aae53268d","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-204-codebase-scan-839c8b06c016.md","fingerprint":"839c8b06c0162bc60be36486f9780a3569ffd728","follow_up_task_id":"SCA-204","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"1b917baffdea41340524af66b3a1fc30d4e85420d02136fbcb20396aae53268d","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2545"},"finding_id":"839c8b06c0162bc60be36486f9780a3569ffd728","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},"source_receipt_id":"839c8b06c0162bc60be36486f9780a3569ffd728","summary":"swallowed_exception"},{"contradiction_id":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","detected_at":null,"fingerprint":"contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226","goal_id":"SCA-G041","impacted_criteria":["direct REST/fetch paths and compatibility routes are represented for bypass checks.","dynamic declarations are unresolved, not guessed","Source precedence and version are explicit"],"invalidated_evidence":[],"kind":"mapped_finding","scheduled_work":[{"task_id":"SCA-201"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeerauhexkhdotvu63sq2j7bdsp2telxzwkztc4r2yd7rggalhycuc7ba","canonical_task_key":"task/v1/a1c9751c6e9d69edca1a4fc2393f5322ef9b2b331723ac0ff13180b3e05417c2","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-201-codebase-scan-127ed75eb2de.md","fingerprint":"127ed75eb2de779af430970b9874a3ef6f709dbb","follow_up_task_id":"SCA-201","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"a1c9751c6e9d69edca1a4fc2393f5322ef9b2b331723ac0ff13180b3e05417c2","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:295"},"finding_id":"127ed75eb2de779af430970b9874a3ef6f709dbb","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},"source_receipt_id":"127ed75eb2de779af430970b9874a3ef6f709dbb","summary":"swallowed_exception"}],"goal_id":"SCA-G041","historical_completion_receipt_ids":[],"impacted_criteria":["direct REST/fetch paths and compatibility routes are represented for bypass checks.","dynamic declarations are unresolved","dynamic declarations are unresolved, not guessed","not guessed","Source precedence and version are explicit"],"invalidated_evidence":["goal:SCA-G050"],"newly_scheduled_work":[{"goal_id":"SCA-G041","reason":"child_reopened","source_goal_id":"SCA-G050"},{"task_id":"SCA-201"},{"task_id":"SCA-202"},{"task_id":"SCA-203"},{"task_id":"SCA-204"}],"previous_state":"provisionally_complete","receipt_id":"reopen-ffa40e2edb2adb0d1cd0cd361ddb4047","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeradoixxl755jatibjev5tlhip4gdkoqvba2aqtn66lea4wvlste2gq","canonical_task_key":"task/v1/1b917baffdea41340524af66b3a1fc30d4e85420d02136fbcb20396aae53268d","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-204-codebase-scan-839c8b06c016.md","fingerprint":"839c8b06c0162bc60be36486f9780a3569ffd728","follow_up_task_id":"SCA-204","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"1b917baffdea41340524af66b3a1fc30d4e85420d02136fbcb20396aae53268d","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2545"},"finding_id":"839c8b06c0162bc60be36486f9780a3569ffd728","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeram2tj5oizlpziganj6wuzh6pmn6vaqz6wd7k3bucve4nlpugg4ida","canonical_task_key":"task/v1/66a69eb9195bf28301a9f5a993f9ec6faa0867d61fd5b0d055271ab7d0c6e206","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-202-codebase-scan-dc5339180262.md","fingerprint":"dc5339180262e3dc3ca1d8ef5b981431a4234ac6","follow_up_task_id":"SCA-202","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"66a69eb9195bf28301a9f5a993f9ec6faa0867d61fd5b0d055271ab7d0c6e206","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:296"},"finding_id":"dc5339180262e3dc3ca1d8ef5b981431a4234ac6","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeerauhexkhdotvu63sq2j7bdsp2telxzwkztc4r2yd7rggalhycuc7ba","canonical_task_key":"task/v1/a1c9751c6e9d69edca1a4fc2393f5322ef9b2b331723ac0ff13180b3e05417c2","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-201-codebase-scan-127ed75eb2de.md","fingerprint":"127ed75eb2de779af430970b9874a3ef6f709dbb","follow_up_task_id":"SCA-201","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"a1c9751c6e9d69edca1a4fc2393f5322ef9b2b331723ac0ff13180b3e05417c2","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:295"},"finding_id":"127ed75eb2de779af430970b9874a3ef6f709dbb","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeerazj34bhuafh4peqzfjkbkkaoy3wrw2qkf27fyclvtjr67ad343tmq","canonical_task_key":"task/v1/ca77c09e8029f8f243254a82a501d8dda36d4145d7cb812eb34c7df00f7cdcd9","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-203-codebase-scan-f1650d37e707.md","fingerprint":"f1650d37e707959222e15790aeef30ddc7f8809e","follow_up_task_id":"SCA-203","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"ca77c09e8029f8f243254a82a501d8dda36d4145d7cb812eb34c7df00f7cdcd9","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2529"},"finding_id":"f1650d37e707959222e15790aeef30ddc7f8809e","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-4c07cc98fb66e29f98d51629eb51fedc","contradiction-6d1f278ceae9d809439ed624878828ff9a59f511","contradiction-7ff69a55d2cae567e5331d5a7b71877fedb6005c","contradiction-8290c643ade4d3023def6d10aa7fd3bbc54995d5","contradiction-e95a17578e8e34225afacfd0f821bb5abdb97226"]
- Contradiction impacted criteria: ["Source precedence and version are explicit","direct REST/fetch paths and compatibility routes are represented for bypass checks.","dynamic declarations are unresolved","dynamic declarations are unresolved, not guessed","not guessed"]
- Contradiction invalidated evidence: ["goal:SCA-G050"]
- Contradiction source receipts: [{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeradoixxl755jatibjev5tlhip4gdkoqvba2aqtn66lea4wvlste2gq","canonical_task_key":"task/v1/1b917baffdea41340524af66b3a1fc30d4e85420d02136fbcb20396aae53268d","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-204-codebase-scan-839c8b06c016.md","fingerprint":"839c8b06c0162bc60be36486f9780a3569ffd728","follow_up_task_id":"SCA-204","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"1b917baffdea41340524af66b3a1fc30d4e85420d02136fbcb20396aae53268d","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2545"},"finding_id":"839c8b06c0162bc60be36486f9780a3569ffd728","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeram2tj5oizlpziganj6wuzh6pmn6vaqz6wd7k3bucve4nlpugg4ida","canonical_task_key":"task/v1/66a69eb9195bf28301a9f5a993f9ec6faa0867d61fd5b0d055271ab7d0c6e206","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-202-codebase-scan-dc5339180262.md","fingerprint":"dc5339180262e3dc3ca1d8ef5b981431a4234ac6","follow_up_task_id":"SCA-202","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"66a69eb9195bf28301a9f5a993f9ec6faa0867d61fd5b0d055271ab7d0c6e206","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:296"},"finding_id":"dc5339180262e3dc3ca1d8ef5b981431a4234ac6","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeerauhexkhdotvu63sq2j7bdsp2telxzwkztc4r2yd7rggalhycuc7ba","canonical_task_key":"task/v1/a1c9751c6e9d69edca1a4fc2393f5322ef9b2b331723ac0ff13180b3e05417c2","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-201-codebase-scan-127ed75eb2de.md","fingerprint":"127ed75eb2de779af430970b9874a3ef6f709dbb","follow_up_task_id":"SCA-201","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"a1c9751c6e9d69edca1a4fc2393f5322ef9b2b331723ac0ff13180b3e05417c2","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:295"},"finding_id":"127ed75eb2de779af430970b9874a3ef6f709dbb","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.230769,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.230769","finding":{"bundle_key":"codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeerazj34bhuafh4peqzfjkbkkaoy3wrw2qkf27fyclvtjr67ad343tmq","canonical_task_key":"task/v1/ca77c09e8029f8f243254a82a501d8dda36d4145d7cb812eb34c7df00f7cdcd9","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-203-codebase-scan-f1650d37e707.md","fingerprint":"f1650d37e707959222e15790aeef30ddc7f8809e","follow_up_task_id":"SCA-203","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py"],"semantic_identity":"ca77c09e8029f8f243254a82a501d8dda36d4145d7cb812eb34c7df00f7cdcd9","source":"external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2529"},"finding_id":"f1650d37e707959222e15790aeef30ddc7f8809e","goal_id":"SCA-G041","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"}]
- Newly scheduled work: [{"goal_id":"SCA-G041","reason":"child_reopened","source_goal_id":"SCA-G050"},{"task_id":"SCA-201"},{"task_id":"SCA-202"},{"task_id":"SCA-203"},{"task_id":"SCA-204"}]

## SCA-G042 Python package actual-surface extraction

- Status: reopened
- Parent: SCA-G020, SCA-G040
- Priority: P0
- Track: actual-contracts
- Bundle: swissknife/contract-assurance/actual
- Goal: Extract canonical MCP/MCP++ tool registration, schemas, facade dispatch, handlers, policy gates, transports, and implementation symbols from all three Python packages.
- Evidence: SCAEV042ACTUAL
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/python_mcp_surface_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_python_mcp_surface_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_python_mcp_surface_extractor.py -q
- Acceptance: Package import is not required for static extraction; optional live discovery is separate evidence; aliases and hierarchical facade tools normalize without hiding domain tools; unknown dynamic registration remains unresolved.
- Gap task: SCA-042
- Conflict policy: Provider paths are exact scoped evidence; no eager optional package import during supervisor discovery.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Package import is not required for static extraction","optional live discovery is separate evidence","aliases and hierarchical facade tools normalize without hiding domain tools","unknown dynamic registration remains unresolved."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-0b5c2fea050bbe910b433ded0e3476dc"],"contradictions":[{"contradiction_id":"contradiction-0b5c2fea050bbe910b433ded0e3476dc","detected_at":null,"fingerprint":"contradiction-0b5c2fea050bbe910b433ded0e3476dc","goal_id":"SCA-G042","impacted_criteria":["aliases and hierarchical facade tools normalize without hiding domain tools","optional live discovery is separate evidence","Package import is not required for static extraction","unknown dynamic registration remains unresolved."],"invalidated_evidence":["goal:SCA-G050"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G042","reason":"child_reopened","source_goal_id":"SCA-G050"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G050 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."}],"goal_id":"SCA-G042","historical_completion_receipt_ids":[],"impacted_criteria":["aliases and hierarchical facade tools normalize without hiding domain tools","optional live discovery is separate evidence","Package import is not required for static extraction","unknown dynamic registration remains unresolved."],"invalidated_evidence":["goal:SCA-G050"],"newly_scheduled_work":[{"goal_id":"SCA-G042","reason":"child_reopened","source_goal_id":"SCA-G050"}],"previous_state":"provisionally_complete","receipt_id":"reopen-9bd6b648bbeb3695ff254df15ac00ef8","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-0b5c2fea050bbe910b433ded0e3476dc"]
- Contradiction impacted criteria: ["Package import is not required for static extraction","aliases and hierarchical facade tools normalize without hiding domain tools","optional live discovery is separate evidence","unknown dynamic registration remains unresolved."]
- Contradiction invalidated evidence: ["goal:SCA-G050"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G050"}]
- Newly scheduled work: [{"goal_id":"SCA-G042","reason":"child_reopened","source_goal_id":"SCA-G050"}]

## SCA-G050 MCP++ invocation reachability

- Status: reopened
- Parent: SCA-G030, SCA-G041, SCA-G042
- Priority: P0
- Track: invocation
- Bundle: swissknife/contract-assurance/invocation
- Goal: Join expected and actual contracts and compute the exact SwissKnife descriptor/registry/connector/transport/tool/handler/implementation path for each declared package operation.
- Evidence: SCAEV050CALL
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_invocation_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_invocation_trace.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_invocation_trace.py -q
- Acceptance: Each operation is reachable, refuted, ambiguous, unsupported, or not measured; unresolved dynamic calls never count as reachable; trace carries exact edge and source IDs.
- Gap task: SCA-050
- Conflict policy: Graph reachability is structural evidence; behavioral claims require their own obligation.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Each operation is reachable, refuted, ambiguous, unsupported, or not measured","unresolved dynamic calls never count as reachable","trace carries exact edge and source IDs."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-a6e4ceb72d72d3a4bfcb2c60993fda4d"],"contradictions":[{"contradiction_id":"contradiction-a6e4ceb72d72d3a4bfcb2c60993fda4d","detected_at":null,"fingerprint":"contradiction-a6e4ceb72d72d3a4bfcb2c60993fda4d","goal_id":"SCA-G050","impacted_criteria":["ambiguous","Each operation is reachable","or not measured","refuted","trace carries exact edge and source IDs.","unresolved dynamic calls never count as reachable","unsupported"],"invalidated_evidence":["goal:SCA-G051"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G050","reason":"child_reopened","source_goal_id":"SCA-G051"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G051"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G051 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."}],"goal_id":"SCA-G050","historical_completion_receipt_ids":[],"impacted_criteria":["ambiguous","Each operation is reachable","or not measured","refuted","trace carries exact edge and source IDs.","unresolved dynamic calls never count as reachable","unsupported"],"invalidated_evidence":["goal:SCA-G051"],"newly_scheduled_work":[{"goal_id":"SCA-G050","reason":"child_reopened","source_goal_id":"SCA-G051"}],"previous_state":"provisionally_complete","receipt_id":"reopen-02457450373c29659c7a5cac8ec10d1a","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G051"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-a6e4ceb72d72d3a4bfcb2c60993fda4d"]
- Contradiction impacted criteria: ["Each operation is reachable","ambiguous","or not measured","refuted","trace carries exact edge and source IDs.","unresolved dynamic calls never count as reachable","unsupported"]
- Contradiction invalidated evidence: ["goal:SCA-G051"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G051"}]
- Newly scheduled work: [{"goal_id":"SCA-G050","reason":"child_reopened","source_goal_id":"SCA-G051"}]

## SCA-G051 Discovery, execution, transport, and failure parity

- Status: reopened
- Parent: SCA-G050
- Priority: P0
- Track: parity
- Bundle: swissknife/contract-assurance/parity
- Goal: Check schema, argument, result, policy, transport, discovery/execution, compatibility, and failure-state parity across SwissKnife and each provider package.
- Evidence: SCAEV051PARITY
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_analysis.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_analysis.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_analysis.py -q
- Acceptance: Required arguments/defaults and result/error envelopes are preserved; tools/list agrees with tools/call reachability; policy dominates effects; compatibility paths cannot bypass required MCP++ semantics.
- Gap task: SCA-051
- Conflict policy: Preserve unsupported/unavailable/denied/timed_out/malformed/partial distinctions.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Required arguments/defaults and result/error envelopes are preserved","tools/list agrees with tools/call reachability","policy dominates effects","compatibility paths cannot bypass required MCP++ semantics."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-e3e57931a17d7217ce1c834381b6d866"],"contradictions":[{"contradiction_id":"contradiction-e3e57931a17d7217ce1c834381b6d866","detected_at":null,"fingerprint":"contradiction-e3e57931a17d7217ce1c834381b6d866","goal_id":"SCA-G051","impacted_criteria":["compatibility paths cannot bypass required MCP++ semantics.","policy dominates effects","Required arguments/defaults and result/error envelopes are preserved","tools/list agrees with tools/call reachability"],"invalidated_evidence":["goal:SCA-G090"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G051","reason":"child_reopened","source_goal_id":"SCA-G090"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G090"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G090 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."}],"goal_id":"SCA-G051","historical_completion_receipt_ids":[],"impacted_criteria":["compatibility paths cannot bypass required MCP++ semantics.","policy dominates effects","Required arguments/defaults and result/error envelopes are preserved","tools/list agrees with tools/call reachability"],"invalidated_evidence":["goal:SCA-G090"],"newly_scheduled_work":[{"goal_id":"SCA-G051","reason":"child_reopened","source_goal_id":"SCA-G090"}],"previous_state":"provisionally_complete","receipt_id":"reopen-86025208b8b568aa9acdbfc188f294b6","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G090"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-e3e57931a17d7217ce1c834381b6d866"]
- Contradiction impacted criteria: ["Required arguments/defaults and result/error envelopes are preserved","compatibility paths cannot bypass required MCP++ semantics.","policy dominates effects","tools/list agrees with tools/call reachability"]
- Contradiction invalidated evidence: ["goal:SCA-G090"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G090"}]
- Newly scheduled work: [{"goal_id":"SCA-G051","reason":"child_reopened","source_goal_id":"SCA-G090"}]

## SCA-G060 Logic IR and contract obligations

- Status: reopened
- Parent: SCA-G040, SCA-G050, SCA-G051
- Priority: P0
- Track: logic-ir
- Bundle: swissknife/contract-assurance/logic
- Goal: Compile reviewed contract families and exact graph premises into canonical shared logic views and CodeProofObligation records.
- Evidence: SCAEV060LOGIC
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_obligations.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_obligations.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_obligations.py -q
- Acceptance: Every obligation binds property, premises, assumptions, snapshot, scope, invalidators, required assurance, and supported logic fragment; source or graph dumps are rejected as premises.
- Gap task: SCA-060
- Conflict policy: Reuse code_claim_contracts, code_proof_obligations, and ipfs_datasets shared logic IR adapters.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Every obligation binds property, premises, assumptions, snapshot, scope, invalidators, required assurance, and supported logic fragment","source or graph dumps are rejected as premises."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-60491f019c93db59ed602f09f7602f89"],"contradictions":[{"contradiction_id":"contradiction-60491f019c93db59ed602f09f7602f89","detected_at":null,"fingerprint":"contradiction-60491f019c93db59ed602f09f7602f89","goal_id":"SCA-G060","impacted_criteria":["and supported logic fragment","assumptions","Every obligation binds property","invalidators","premises","required assurance","scope","snapshot","source or graph dumps are rejected as premises."],"invalidated_evidence":["goal:SCA-G061"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G060","reason":"child_reopened","source_goal_id":"SCA-G061"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G061"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G061 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."}],"goal_id":"SCA-G060","historical_completion_receipt_ids":[],"impacted_criteria":["and supported logic fragment","assumptions","Every obligation binds property","invalidators","premises","required assurance","scope","snapshot","source or graph dumps are rejected as premises."],"invalidated_evidence":["goal:SCA-G061"],"newly_scheduled_work":[{"goal_id":"SCA-G060","reason":"child_reopened","source_goal_id":"SCA-G061"}],"previous_state":"provisionally_complete","receipt_id":"reopen-5b0500ed8ea680d0a9be11afcb1a8e2e","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G061"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-60491f019c93db59ed602f09f7602f89"]
- Contradiction impacted criteria: ["Every obligation binds property","and supported logic fragment","assumptions","invalidators","premises","required assurance","scope","snapshot","source or graph dumps are rejected as premises."]
- Contradiction invalidated evidence: ["goal:SCA-G061"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G061"}]
- Newly scheduled work: [{"goal_id":"SCA-G060","reason":"child_reopened","source_goal_id":"SCA-G061"}]

## SCA-G061 Solver routing and counterexamples

- Status: reopened
- Parent: SCA-G060
- Priority: P0
- Track: proving
- Bundle: swissknife/contract-assurance/proving
- Goal: Route graph, schema, SMT, TDFOL, CEC, and kernel-supported obligations through explicit capability probes and return compact proofs, counterexamples, or typed inconclusive states.
- Evidence: SCAEV061PROVE
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_prover.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_prover.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_prover.py -q
- Acceptance: Candidate solver output cannot mint kernel assurance; counterexamples identify failed premises/edges; unavailable providers fail closed; no LLM is required for the proof path.
- Gap task: SCA-061
- Conflict policy: Use multi_prover_router and formal_verification_provider; provider capability is operation-specific.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Candidate solver output cannot mint kernel assurance","counterexamples identify failed premises/edges","unavailable providers fail closed","no LLM is required for the proof path."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-d2f7e46a3a5d9913e5f9882071ca8e9a"],"contradictions":[{"contradiction_id":"contradiction-d2f7e46a3a5d9913e5f9882071ca8e9a","detected_at":null,"fingerprint":"contradiction-d2f7e46a3a5d9913e5f9882071ca8e9a","goal_id":"SCA-G061","impacted_criteria":["Candidate solver output cannot mint kernel assurance","counterexamples identify failed premises/edges","no LLM is required for the proof path.","unavailable providers fail closed"],"invalidated_evidence":["goal:SCA-G090"],"kind":"child_reopened","scheduled_work":[{"goal_id":"SCA-G061","reason":"child_reopened","source_goal_id":"SCA-G090"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G090"},"source_receipt_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","summary":"Child goal SCA-G090 was reopened by contradiction contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675."}],"goal_id":"SCA-G061","historical_completion_receipt_ids":[],"impacted_criteria":["Candidate solver output cannot mint kernel assurance","counterexamples identify failed premises/edges","no LLM is required for the proof path.","unavailable providers fail closed"],"invalidated_evidence":["goal:SCA-G090"],"newly_scheduled_work":[{"goal_id":"SCA-G061","reason":"child_reopened","source_goal_id":"SCA-G090"}],"previous_state":"provisionally_complete","receipt_id":"reopen-08f9486d0199954e061a769cf3300313","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G090"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-d2f7e46a3a5d9913e5f9882071ca8e9a"]
- Contradiction impacted criteria: ["Candidate solver output cannot mint kernel assurance","counterexamples identify failed premises/edges","no LLM is required for the proof path.","unavailable providers fail closed"]
- Contradiction invalidated evidence: ["goal:SCA-G090"]
- Contradiction source receipts: [{"kind":"child_reopened","root_contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","source_goal_id":"SCA-G090"}]
- Newly scheduled work: [{"goal_id":"SCA-G061","reason":"child_reopened","source_goal_id":"SCA-G090"}]

## SCA-G070 Trust-aware proof cache and exact invalidation

- Status: provisionally_complete
- Parent: SCA-G015, SCA-G060, SCA-G061
- Priority: P0
- Track: proof-cache
- Bundle: swissknife/contract-assurance/cache
- Goal: Put every contract proof attempt through the existing trust-aware cache and invalidate exactly on semantic input drift.
- Evidence: SCAEV070CACHE
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_proof_cache.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_proof_cache.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_proof_cache.py -q
- Acceptance: Keys bind all semantic dimensions and declared CID identity profiles; retained canonical bytes revalidate against the decoded multihash; hits re-derive assurance; negative/inconclusive TTLs are bounded; stale, poisoned, wrong-snapshot, toolchain-drift, private-material, cross-profile, and candidate-only hits are rejected with reason codes.
- Gap task: SCA-070
- Conflict policy: TrustAwareProofCache remains the sole proof-receipt memoization authority.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Keys bind all semantic dimensions and declared CID identity profiles","retained canonical bytes revalidate against the decoded multihash","hits re-derive assurance","negative/inconclusive TTLs are bounded","stale, poisoned, wrong-snapshot, toolchain-drift, private-material, cross-profile, and candidate-only hits are rejected with reason codes."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Keys bind all semantic dimensions and declared CID identity profiles; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G080 ZK threat model and capability policy

- Status: provisionally_complete
- Parent: SCA-G060
- Priority: P1
- Track: zk-policy
- Bundle: swissknife/contract-assurance/zk-policy
- Goal: Approve or reject concrete private-witness attestation use cases and define the real-backend, public-input, witness, leakage, replay, setup, and assurance policy.
- Evidence: SCAEV080ZKPOL
- Outputs: external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_THREAT_MODEL.md, external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_POLICY.md
- Validation: test -f external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_POLICY.md
- Acceptance: ZK proves only reviewed attestation predicates after property proof; simulation cannot emit ATTESTED; no backend is selected without a qualifying threat boundary and capability report.
- Gap task: SCA-080
- Conflict policy: Extend existing codebase-proof ZK policy and proof_attestation; do not claim ZK proves arbitrary code correctness.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["ZK proves only reviewed attestation predicates after property proof","simulation cannot emit ATTESTED","no backend is selected without a qualifying threat boundary and capability report."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: ZK proves only reviewed attestation predicates after property proof; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G081 Receipt attestation adapter

- Status: provisionally_complete
- Parent: SCA-G070, SCA-G080
- Priority: P1
- Track: zk-attestation
- Bundle: swissknife/contract-assurance/zk-attestation
- Goal: Bind approved proof receipts to real ZK or signature/commitment backends with explicit degradation when only simulation is available.
- Evidence: SCAEV081ZK
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_attestation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_attestation.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_attestation.py -q
- Acceptance: Public inputs bind receipt/cache/snapshot/property roots; private witnesses never enter public receipts or prompts; replay/canonicalization/backend substitution tests fail closed.
- Gap task: SCA-081
- Conflict policy: Use proof_attestation and ipfs_datasets zkp_attestation through lazy adapters.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Public inputs bind receipt/cache/snapshot/property roots","private witnesses never enter public receipts or prompts","replay/canonicalization/backend substitution tests fail closed."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Public inputs bind receipt/cache/snapshot/property roots; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G090 Contract mismatch analyzer

- Status: reopened
- Parent: SCA-G051, SCA-G061
- Priority: P0
- Track: mismatches
- Bundle: swissknife/contract-assurance/mismatches
- Goal: Convert refuted, stale, contradictory, ambiguous, unsupported, and not-measured contract claims into deterministic findings with compact counterexamples and impact closure.
- Evidence: SCAEV090MISMATCH
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_mismatch_analyzer.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_analyzer.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_analyzer.py -q
- Acceptance: Finding identity is deterministic; cache miss is not mismatch; dynamic unknown is not refuted; impact paths and invalidation reasons are bounded and reproducible.
- Gap task: SCA-090
- Conflict policy: Findings are evidence, not task completion or mutation authority.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Finding identity is deterministic","cache miss is not mismatch","dynamic unknown is not refuted","impact paths and invalidation reasons are bounded and reproducible."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T10:45:23.821373+00:00
- State transition reason: completion evidence contradicted; scheduled repair work and recalculate parent/dependent goal proof
- Provisional at: 2026-07-29T08:44:29.727168+00:00
- Goal reopening receipts: [{"contradiction_ids":["contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675"],"contradictions":[{"contradiction_id":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","detected_at":null,"fingerprint":"contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675","goal_id":"SCA-G090","impacted_criteria":["cache miss is not mismatch","dynamic unknown is not refuted","Finding identity is deterministic","impact paths and invalidation reasons are bounded and reproducible."],"invalidated_evidence":[],"kind":"mapped_finding","scheduled_work":[{"task_id":"SCA-205"}],"schema":"ipfs_accelerate_py.agent_supervisor.contradiction.v1","schema_version":1,"source_receipt":{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.257143,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.257143","finding":{"bundle_key":"codebase/quality/external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-quality-external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeraokmcdyxg6ngo5l3iyuwbqz7hf2cjtkbvwgmmc7xfp7chwxrecoya","canonical_task_key":"task/v1/729821e2e6f34ceeaf68c52c1867e72e8499a835b198c17ee57fc47b5e2413b0","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-205-codebase-scan-5d7f78247d82.md","fingerprint":"5d7f78247d820096875dca52b1a9bf0ef56ace6e","follow_up_task_id":"SCA-205","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py"],"semantic_identity":"729821e2e6f34ceeaf68c52c1867e72e8499a835b198c17ee57fc47b5e2413b0","source":"external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py:443"},"finding_id":"5d7f78247d820096875dca52b1a9bf0ef56ace6e","goal_id":"SCA-G090","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"},"source_receipt_id":"5d7f78247d820096875dca52b1a9bf0ef56ace6e","summary":"swallowed_exception"}],"goal_id":"SCA-G090","historical_completion_receipt_ids":[],"impacted_criteria":["cache miss is not mismatch","dynamic unknown is not refuted","Finding identity is deterministic","impact paths and invalidation reasons are bounded and reproducible."],"invalidated_evidence":[],"newly_scheduled_work":[{"task_id":"SCA-205"}],"previous_state":"provisionally_complete","receipt_id":"reopen-db2979352284da21bdc8e8fdc4c50844","reopened_at":"2026-07-29T10:45:23.821373+00:00","schema":"ipfs_accelerate_py.agent_supervisor.goal_reopening_receipt.v1","schema_version":1,"source_receipts":[{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.257143,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.257143","finding":{"bundle_key":"codebase/quality/external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-quality-external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeraokmcdyxg6ngo5l3iyuwbqz7hf2cjtkbvwgmmc7xfp7chwxrecoya","canonical_task_key":"task/v1/729821e2e6f34ceeaf68c52c1867e72e8499a835b198c17ee57fc47b5e2413b0","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-205-codebase-scan-5d7f78247d82.md","fingerprint":"5d7f78247d820096875dca52b1a9bf0ef56ace6e","follow_up_task_id":"SCA-205","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py"],"semantic_identity":"729821e2e6f34ceeaf68c52c1867e72e8499a835b198c17ee57fc47b5e2413b0","source":"external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py:443"},"finding_id":"5d7f78247d820096875dca52b1a9bf0ef56ace6e","goal_id":"SCA-G090","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"}],"state":"reopened"}]
- Contradiction ids: ["contradiction-6b220aaf6bfb7453c314e9281959e28dc5902675"]
- Contradiction impacted criteria: ["Finding identity is deterministic","cache miss is not mismatch","dynamic unknown is not refuted","impact paths and invalidation reasons are bounded and reproducible."]
- Contradiction invalidated evidence: []
- Contradiction source receipts: [{"analyzer_version":"codebase-annotation-analyzer/v1","artifact_path":"swissknife_contract_assurance_00_scan_receipts/baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra.json","candidate_funnel":{"appended_task_count":5,"cache_hit_count":0,"deduplicated_candidate_count":0,"eligible_file_count":57640,"excluded_file_count":21678,"git_root_count":17,"parsed_file_count":57640,"parser_failure_count":0,"raw_candidate_count":13007,"seen_candidate_count":0,"tracked_file_count":79318},"duration_seconds":98.258655,"finding_mapping":{"confidence":0.257143,"explanation":"most relevant registered goal by deterministic token Jaccard score 0.257143","finding":{"bundle_key":"codebase/quality/external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor","bundle_shard":"data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-quality-external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor.todo.md","canonical_task_cid":"baguqeeraokmcdyxg6ngo5l3iyuwbqz7hf2cjtkbvwgmmc7xfp7chwxrecoya","canonical_task_key":"task/v1/729821e2e6f34ceeaf68c52c1867e72e8499a835b198c17ee57fc47b5e2413b0","discovery_path":"data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-205-codebase-scan-5d7f78247d82.md","fingerprint":"5d7f78247d820096875dca52b1a9bf0ef56ace6e","follow_up_task_id":"SCA-205","kind":"swallowed_exception","objective_goal_ids":["SCA-G172","SCA-G170","SCA-G040","SCA-G042","SCA-G168","SCA-G000","SCA-G010","SCA-G020","SCA-G167","SCA-G015","SCA-G100","SCA-G110","SCA-G111","SCA-G090","SCA-G091","SCA-G021","SCA-G101","SCA-G051","SCA-G061","SCA-G050","SCA-G060","SCA-G030","SCA-G041"],"predicted_files":["external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py"],"semantic_identity":"729821e2e6f34ceeaf68c52c1867e72e8499a835b198c17ee57fc47b5e2413b0","source":"external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py:443"},"finding_id":"5d7f78247d820096875dca52b1a9bf0ef56ace6e","goal_id":"SCA-G090","inferred":true,"source_goal_id":""},"finished_at":"2026-07-29T10:45:22.410515+00:00","freshness":{"age_seconds":1.301,"as_of":"2026-07-29T10:45:23.711903+00:00","fresh":true,"fresh_for_seconds":3600.0,"status":"fresh"},"generated_count":5,"health":"healthy","receipt_cid":"baguqeeraplc3du4wv7ejuj5pv5flysx2l6lcdssrcaafeotukmzq33fizrra","repository_id":"/home/barberb/lift_coding/.git","repository_identity":"/home/barberb/lift_coding/.git","safe_for_completion_reasoning":false,"scan_kind":"codebase","scan_mode":"runnable_drained_exhaustive","schema":"ipfs_accelerate_py/agent-supervisor/refill-scan-receipt-projection@1","schema_version":1,"started_at":"2026-07-29T10:43:44.151860+00:00","terminal_reason":"generated","tree_id":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1","tree_identity":"sha256:6a97ed53148cde190ce5055275efba8d4ddf13b0fa2e49db5490bcf57d6e80c1"}]
- Newly scheduled work: [{"task_id":"SCA-205"}]

## SCA-G091 Bug and vulnerability classification

- Status: provisionally_complete
- Parent: SCA-G090
- Priority: P0
- Track: security-findings
- Bundle: swissknife/contract-assurance/security
- Goal: Classify deterministic contract counterexamples as correctness bugs or security findings without conflating severity, exploitability, confidence, and proof status.
- Evidence: SCAEV091SEC
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_vulnerability_rules.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_vulnerability_rules.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_vulnerability_rules.py -q
- Acceptance: Rules cover policy bypass, schema confusion, argument loss, unauthorized effect, stale receipt, discovery/execution drift, failure collapse, and compatibility bypass; CWE/OWASP/CAPEC tags require matched premises; unknowns are not auto-labeled vulnerabilities.
- Gap task: SCA-091
- Conflict policy: Static classification remains revision-bound and does not assert exploitability without evidence.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Rules cover policy bypass, schema confusion, argument loss, unauthorized effect, stale receipt, discovery/execution drift, failure collapse, and compatibility bypass","CWE/OWASP/CAPEC tags require matched premises","unknowns are not auto-labeled vulnerabilities."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Rules cover policy bypass, schema confusion, argument loss, unauthorized effect, stale receipt, discovery/execution drift, failure collapse, and compatibility bypass; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G100 Minimal CodeEditPacket materialization

- Status: provisionally_complete
- Parent: SCA-G090, SCA-G091
- Priority: P0
- Track: packets
- Bundle: swissknife/contract-assurance/packets
- Goal: Materialize obligation-first repair packets containing only affected symbols, contracts, counterexamples, postconditions, validation, re-proof, and expansion handles.
- Evidence: SCAEV100PACKET
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_edit_packet.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_edit_packet.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_edit_packet.py -q
- Acceptance: Required core cannot be truncated; full source/AST/proof bodies remain behind handles; read/write allowlists are exact; packet is rejected if the counterexample is stale.
- Gap task: SCA-100
- Conflict policy: Extend CodeEditPacket/context compiler, preserving existing authority and prompt-injection boundaries.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Required core cannot be truncated","full source/AST/proof bodies remain behind handles","read/write allowlists are exact","packet is rejected if the counterexample is stale."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Required core cannot be truncated; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G101 Generated ipfs_accelerate_py repair board

- Status: provisionally_complete
- Parent: SCA-G100
- Priority: P0
- Track: task-refinery
- Bundle: swissknife/contract-assurance/refinery
- Goal: Deduplicate and append current accelerator-owned bug/vulnerability tasks from admitted contract packets in agent-supervisor Markdown format.
- Evidence: SCAEV101BOARD
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/contract_mismatch_refinery.py, data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_refinery.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_refinery.py -q
- Acceptance: Only accelerator-owned affected paths enter this board; identity deduplicates snapshot/contract/family/symbols/counterexample; stale findings update evidence; each task has targeted validation and re-proof.
- Gap task: SCA-101
- Conflict policy: Generated board is a projection; objective heap and proof evidence remain sources of intent and truth.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Only accelerator-owned affected paths enter this board","identity deduplicates snapshot/contract/family/symbols/counterexample","stale findings update evidence","each task has targeted validation and re-proof."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Only accelerator-owned affected paths enter this board; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G110 Supervisor scanner/refill integration

- Status: provisionally_complete
- Parent: SCA-G021, SCA-G090, SCA-G101
- Priority: P0
- Track: supervisor-runtime
- Bundle: swissknife/contract-assurance/runtime
- Goal: Register the repository index, contract analyzer, proof workflow, task refinery, analyzer health, and incremental invalidation in the live objective/backlog supervisor loop.
- Evidence: SCAEV110RUN
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/contract_assurance_refill.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_refill.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_refill.py -q
- Acceptance: Low backlog triggers bounded current-snapshot analysis; findings require goal lineage and health; duplicate/stale evidence does not create task storms; restart resumes durable exact state.
- Gap task: SCA-110
- Conflict policy: Integrate through existing objective_daemon/backlog_refinery handlers; no shell-string control API.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Low backlog triggers bounded current-snapshot analysis","findings require goal lineage and health","duplicate/stale evidence does not create task storms","restart resumes durable exact state."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Low backlog triggers bounded current-snapshot analysis; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G111 Grok/Codex bounded provider routing

- Status: provisionally_complete
- Parent: SCA-G100
- Priority: P1
- Track: provider-routing
- Bundle: swissknife/contract-assurance/providers
- Goal: Route implementation proposals to Grok Build and independent bounded review/repair to Codex under one lease and task-specific context limits.
- Evidence: SCAEV111PROVIDERS
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/contract_packet_provider_router.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_packet_provider_router.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_packet_provider_router.py -q
- Acceptance: Providers receive no repository-wide context; review is sequential and read-only until admitted; quotas degrade independently; provider output cannot mark proof or completion.
- Gap task: SCA-111, SCA-228
- Conflict policy: Preserve the single SwissKnife writer lease and existing implementation proposal gate.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Providers receive no repository-wide context","review is sequential and read-only until admitted","quotas degrade independently","provider output cannot mark proof or completion."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Providers receive no repository-wide context; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G120 Shadow baseline scan and triage

- Status: active
- Parent: SCA-G021, SCA-G051, SCA-G061, SCA-G070, SCA-G090
- Priority: P0
- Track: baseline
- Bundle: swissknife/contract-assurance/baseline
- Goal: Run a no-mutation baseline over the current SwissKnife snapshot, publish coverage/analyzer health, contract status, proof/cache outcomes, and prioritized accelerator findings.
- Evidence: SCAEV120BASE
- Outputs: data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md
- Validation: python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline --shadow
- Acceptance: Exact snapshot and capability report recorded; all tracked paths disposed; no mutation; findings distinguish proved/refuted/unknown/unsupported/stale; no authority promotion from optional providers.
- Gap task: SCA-200
- Refinement: SCA-120 records the exhaustive health-gated repository baseline; SCA-200 runs the complete contract graph, proof, cache, mismatch, vulnerability, and artifact pipeline after analyzer health and runtime proof surfaces are ready.
- Conflict policy: Baseline artifacts are generated evidence and cannot rewrite source or task status directly.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Exact snapshot and capability report recorded","all tracked paths disposed","no mutation","findings distinguish proved/refuted/unknown/unsupported/stale","no authority promotion from optional providers."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G130 Continuous incremental refill

- Status: active
- Parent: SCA-G110, SCA-G120
- Priority: P1
- Track: continuous
- Bundle: swissknife/contract-assurance/continuous
- Goal: Detect snapshot changes, update only changed index/proof closures, and refill bounded goal-backed tasks until no healthy current finding remains.
- Evidence: SCAEV130REFILL
- Outputs: data/agent_supervisor/swissknife_contract_assurance/state/invalidation.jsonl, data/agent_supervisor/swissknife_contract_assurance/state/refill_metrics.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_refill.py -q
- Acceptance: Controlled one-symbol edits invalidate all and only dependents; cooldown/dedupe/open-work bounds hold; unhealthy scans cannot certify exhaustion.
- Gap task: SCA-130
- Conflict policy: Preserve prior receipts as historical evidence while marking stale bindings explicitly.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Controlled one-symbol edits invalidate all and only dependents","cooldown/dedupe/open-work bounds hold","unhealthy scans cannot certify exhaustion."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G140 Scale and context-budget benchmark

- Status: active
- Parent: SCA-G021, SCA-G070, SCA-G100, SCA-G120
- Priority: P1
- Track: benchmark
- Bundle: swissknife/contract-assurance/benchmark
- Goal: Measure cold/warm/incremental scan, graph, proof, cache, storage, and prompt costs at SwissKnife scale and under irrelevant-corpus growth.
- Evidence: SCAEV140BENCH
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py, data/agent_supervisor/swissknife_contract_assurance/benchmarks/report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py -q
- Acceptance: Warm unchanged reuse >=95 percent; packet max <=8192 tokens and median target <=2048; 10x irrelevant corpus growth does not materially grow mandatory context; bounds and high-watermarks are recorded.
- Gap task: SCA-140
- Conflict policy: Benchmarks report measured capacity and never infer production concurrency from worker count.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Warm unchanged reuse >=95 percent","packet max <=8192 tokens and median target <=2048","10x irrelevant corpus growth does not materially grow mandatory context","bounds and high-watermarks are recorded."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G150 Adversarial and mutation evaluation

- Status: provisionally_complete
- Parent: SCA-G051, SCA-G061, SCA-G070, SCA-G081, SCA-G090, SCA-G100
- Priority: P0
- Track: evaluation
- Bundle: swissknife/contract-assurance/evaluation
- Goal: Seed descriptor, schema, dispatch, policy, transport, failure, cache, ZK, and context attacks and measure detection, false authority, repair precision, and regression rate.
- Evidence: SCAEV150EVAL
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_adversarial.py, data/agent_supervisor/swissknife_contract_assurance/evaluation/report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_adversarial.py -q
- Acceptance: Zero false authoritative admissions; all seeded mandatory-edge, stale-root, policy-bypass, forged-receipt, simulated-ZK, and prompt-injection cases fail closed; unsupported cases remain explicit.
- Gap task: SCA-150
- Conflict policy: Held-out mutations are never included in model context or training fixtures for the same evaluation.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Zero false authoritative admissions","all seeded mandatory-edge, stale-root, policy-bypass, forged-receipt, simulated-ZK, and prompt-injection cases fail closed","unsupported cases remain explicit."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T08:44:29.727168+00:00
- State transition reason: Produce completion evidence for: Zero false authoritative admissions; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T08:44:29.727168+00:00

## SCA-G166 Whole-tree analyzer health recovery

- Status: active
- Parent: SCA-G020, SCA-G021, SCA-G120
- Priority: P0
- Track: analyzer-health
- Bundle: swissknife/contract-assurance/analyzer-health
- Goal: Turn the complete SwissKnife path inventory into healthy semantic coverage by classifying and repairing the current parser failures without weakening file, byte, timeout, symlink, or protected-source bounds.
- Evidence: SCAEV166HEALTH
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/polyglot_ast_health.py, external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_health.py, data/agent_supervisor/swissknife_contract_assurance/analyzer_health/report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_health.py -q
- Acceptance: Every parser-eligible path has a successful AST record or typed bounded failure; JS/TS/JSX/TSX/CJS/MJS use a real parser rather than regex authority; per-language health thresholds and canaries pass or block completion; no source body enters model context.
- Gap task: SCA-166
- Conflict policy: Preserve hard bounds and protected-source policy; a typed unsupported artifact is safer than an unbounded parser or fabricated AST.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Every parser-eligible path has a successful AST record or typed bounded failure","JS/TS/JSX/TSX/CJS/MJS use a real parser rather than regex authority","per-language health thresholds and canaries pass or block completion","no source body enters model context."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G167 Symbolic-only execution and bounded provider enforcement

- Status: provisionally_complete
- Parent: SCA-G100, SCA-G110, SCA-G111
- Priority: P0
- Track: provider-policy
- Bundle: swissknife/contract-assurance/provider-policy
- Goal: Make task execution mode and context limits executable supervisor policy so deterministic-only tasks cannot invoke a model and edit packets route through bounded Grok implementation followed by independent Codex review.
- Evidence: SCAEV167ROUTE
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/task_execution_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_task_execution_policy.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_task_execution_policy.py -q
- Acceptance: Deterministic-only tasks run typed allowlisted local operations with zero provider calls; task context budgets are hard limits; Grok/Codex executable identity, quota, fallback, review order, prompt bytes/tokens, and admission are receipted; labels alone cannot select or upgrade a provider result.
- Gap task: SCA-167, SCA-224, SCA-226, SCA-227, SCA-229
- Conflict policy: Integrate with the existing implementation daemon and CodeEditPacket router; do not add a second task runner or grant model output completion authority.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Deterministic-only tasks run typed allowlisted local operations with zero provider calls","task context budgets are hard limits","Grok/Codex executable identity, quota, fallback, review order, prompt bytes/tokens, and admission are receipted","labels alone cannot select or upgrade a provider result."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T09:33:34.172214+00:00
- State transition reason: Produce completion evidence for: Deterministic-only tasks run typed allowlisted local operations with zero provider calls; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T09:33:34.172214+00:00

## SCA-G168 Canonical SwissKnife snapshot authority

- Status: provisionally_complete
- Parent: SCA-G010, SCA-G167
- Priority: P0
- Track: snapshot-authority
- Bundle: swissknife/contract-assurance/snapshot-authority
- Goal: Bind the integration gitlink and any standalone SwissKnife checkout as distinct repository identities, select the reviewed analysis authority, and prevent mixed-tree coverage, contract, proof, or completion claims.
- Evidence: SCAEV168AUTH
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_authority.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py, data/agent_supervisor/swissknife_contract_assurance/state/snapshot_authority.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py -q
- Acceptance: Origin, commit, tree, ancestry, dirty overlay, gitlink, and tracked-path population are CID-bound for each checkout; exactly one authority is selected by reviewed policy; newer/divergent trees create typed freshness work; artifacts from different authorities never share cache or proof identity.
- Gap task: SCA-168
- Conflict policy: This goal may report or queue a gitlink update but cannot fetch, reset, merge, or rewrite a checkout without separately authorized work.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Origin, commit, tree, ancestry, dirty overlay, gitlink, and tracked-path population are CID-bound for each checkout","exactly one authority is selected by reviewed policy","newer/divergent trees create typed freshness work","artifacts from different authorities never share cache or proof identity."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
- State transitioned at: 2026-07-29T09:33:34.172214+00:00
- State transition reason: Produce completion evidence for: Origin, commit, tree, ancestry, dirty overlay, gitlink, and tracked-path population are CID-bound for each checkout; Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree.; Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one.; Require an explicitly healthy analyzer that is safe for completion reasoning.; Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree.; Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied.; Task completion is provisional until every criterion has valid evidence.
- Provisional at: 2026-07-29T09:33:34.172214+00:00

## SCA-G170 Versioned runtime-component contract catalog

- Status: active
- Parent: SCA-G040, SCA-G042, SCA-G168
- Priority: P0
- Track: runtime-catalog
- Bundle: swissknife/contract-assurance/runtime-catalog
- Goal: Publish one content-addressed manifest for canonical and compatibility entrypoints, schemas, transports, state stores, policies, and package ownership of the model server, orchestrator, scheduler, and agent supervisor.
- Evidence: SCAEV170CAT
- Outputs: config/swissknife_runtime_contract_scope.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_component_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py -q
- Acceptance: Four component roots are complete and CID-bound; alternate servers/schedulers/registries are canonical, versioned-adapter, legacy, or contradiction; SwissKnife launch/health/list/call routes and actual package routes are normalized without name-only joins.
- Gap task: SCA-170
- Conflict policy: Extend McpContractCatalog with a typed runtime view; documentation and fixture aliases are candidate evidence only.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Four component roots are complete and CID-bound","alternate servers/schedulers/registries are canonical, versioned-adapter, legacy, or contradiction","SwissKnife launch/health/list/call routes and actual package routes are normalized without name-only joins."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G171 Model-server route and inference contracts

- Status: active
- Parent: SCA-G170
- Priority: P0
- Track: model-server
- Bundle: swissknife/contract-assurance/runtime-model-server
- Goal: Extract expected and actual model-server route, schema, auth, queue, batching, cache, model-selection, backend, streaming, error, health, and provenance contracts from SwissKnife through MCP++ to accelerator handlers.
- Evidence: SCAEV171MODEL
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/model_server_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_model_server_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_model_server_contract_extractor.py -q
- Acceptance: Connector, capability registry, CLI launcher, Flask/integrated/MCP++ servers, compatibility adapter, and native model tools have exact route/schema/function identities; model revision and generation arguments are preserved; synthetic aliases and mock/degraded transports cannot prove reachability.
- Gap task: SCA-171
- Conflict policy: Do not choose a server by availability; contradictions remain open until one reviewed canonical route or versioned adapter is proved.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Connector, capability registry, CLI launcher, Flask/integrated/MCP++ servers, compatibility adapter, and native model tools have exact route/schema/function identities","model revision and generation arguments are preserved","synthetic aliases and mock/degraded transports cannot prove reachability."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G172 Orchestrator lifecycle contracts

- Status: active
- Parent: SCA-G170
- Priority: P0
- Track: orchestrator
- Bundle: swissknife/contract-assurance/runtime-orchestrator
- Goal: Extract task-orchestrator admission, ownership, dispatch, state transition, retry, cancellation, timeout, result, receipt, and failure contracts across P2P services, datasets adapters, MCP tools, and SwissKnife.
- Evidence: SCAEV172ORCH
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py -q
- Acceptance: Every lifecycle edge has pre/post/error states and evidence spans; broad exception/silent-pass paths are visible; retry/cancel/result idempotence and receipt publication are proved, refuted, or unknown; direct package calls are distinguished from MCP++ mediation.
- Gap task: SCA-172
- Conflict policy: Observed runtime traces are bounded observations; they do not close unmodeled transitions.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Every lifecycle edge has pre/post/error states and evidence spans","broad exception/silent-pass paths are visible","retry/cancel/result idempotence and receipt publication are proved, refuted, or unknown","direct package calls are distinguished from MCP++ mediation."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G173 Scheduler authority and concurrency contracts

- Status: active
- Parent: SCA-G170
- Priority: P0
- Track: scheduler
- Bundle: swissknife/contract-assurance/runtime-scheduler
- Goal: Resolve scheduler authority and model deterministic ownership, clocks, queues, capacity, fairness, leases, fencing, backpressure, retry, cancellation, and crash recovery across every accelerator scheduler surface.
- Evidence: SCAEV173SCHED
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/scheduler_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_scheduler_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_scheduler_contract_extractor.py -q
- Acceptance: Deterministic, legacy workflow, MCP++ workflow/risk, and supervisor resource/provider schedulers are related by proved equivalence, explicit adapter, or contradiction; lease/fence dominates effects; bounded interleavings conserve tasks and terminal outcomes.
- Gap task: SCA-173
- Conflict policy: Do not infer equivalence from shared class or method names; concurrency claims bind the modeled bounds and scheduler version.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Deterministic, legacy workflow, MCP++ workflow/risk, and supervisor resource/provider schedulers are related by proved equivalence, explicit adapter, or contradiction","lease/fence dominates effects","bounded interleavings conserve tasks and terminal outcomes."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G174 Agent-supervisor control and goal/task contracts

- Status: active
- Parent: SCA-G170
- Priority: P0
- Track: agent-supervisor
- Bundle: swissknife/contract-assurance/runtime-agent-supervisor
- Goal: Extract goal/subgoal/task, control-plane, lane, validation, proof, refill, implementation, merge, recovery, status, and completion contracts and map every SwissKnife supervisor capability to a native accelerator operation.
- Evidence: SCAEV174SUP
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/supervisor_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_contract_extractor.py -q
- Acceptance: Each SwissKnife console capability maps to an exact native `agent_supervisor_*` operation, request/result schema, dispatcher/function identity, policy, and effect; generic workflow/data/storage proxy tools are refuted; goal completion requires child/evidence/health/exhaustion closure.
- Gap task: SCA-174
- Conflict policy: UI labels and generic backend ownership are not native-operation reachability; governed mutations require preview/permit/receipt paths.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Each SwissKnife console capability maps to an exact native `agent_supervisor_*` operation, request/result schema, dispatcher/function identity, policy, and effect","generic workflow/data/storage proxy tools are refuted","goal completion requires child/evidence/health/exhaustion closure."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G175 Cross-component state-machine and MCP++ proofs

- Status: active
- Parent: SCA-G171, SCA-G172, SCA-G173, SCA-G174, SCA-G060, SCA-G061
- Priority: P0
- Track: runtime-proof
- Bundle: swissknife/contract-assurance/runtime-proof
- Goal: Compile runtime state machines and cross-component call paths into typed graph, schema, deontic, temporal, and bounded concurrency obligations and prove or refute the supported fragments.
- Evidence: SCAEV175PROOF
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/runtime_contract_obligations.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_mcp_invocation_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_proofs.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_proofs.py -q
- Acceptance: Mandatory dispatch closes through the configured MCP++ pipeline rather than direct handler invocation; interface and behavior IDs bind every path; unsupported semantics remain unknown; solver candidates require trusted deterministic classification or kernel reconstruction; optional ZK attests only verified receipt predicates.
- Gap task: SCA-175, SCA-176
- Conflict policy: ZK membership or event-root possession is not function-call correctness; solver SAT is not proof; mandatory unknown edges block authority.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Mandatory dispatch closes through the configured MCP++ pipeline rather than direct handler invocation","interface and behavior IDs bind every path","unsupported semantics remain unknown","solver candidates require trusted deterministic classification or kernel reconstruction","optional ZK attests only verified receipt predicates."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G176 Runtime drift refinery and continuous refill

- Status: active
- Parent: SCA-G090, SCA-G091, SCA-G101, SCA-G110, SCA-G175
- Priority: P0
- Track: runtime-refill
- Bundle: swissknife/contract-assurance/runtime-refill
- Goal: Classify current runtime counterexamples, append deduplicated accelerator bug/vulnerability tasks with minimal edit packets, and continuously reopen or refill them from exact changed dependency closures.
- Evidence: SCAEV176REFILL
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_contract_vulnerability_rules.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_mismatch_refinery.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_assurance_refill.py, data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_refill.py -q
- Acceptance: Route mismatch, policy bypass, direct dispatch, schema confusion, stale replay, lease/fence violation, duplicate/lost work, mock/degraded evidence, false release GO, and provider-context bypass have typed rules; one current counterexample cluster yields one bounded task; fixes close only after current-tree reindex and re-proof.
- Gap task: SCA-177, SCA-178, SCA-179, SCA-180, SCA-181, SCA-221
- Conflict policy: Security severity and exploitability remain separate from proof state; heuristics can nominate work but cannot label a vulnerability proved.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Route mismatch, policy bypass, direct dispatch, schema confusion, stale replay, lease/fence violation, duplicate/lost work, mock/degraded evidence, false release GO, and provider-context bypass have typed rules","one current counterexample cluster yields one bounded task","fixes close only after current-tree reindex and re-proof."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G022 Current authoritative index publication

- Status: active
- Parent: SCA-G021, SCA-G166, SCA-G168
- Priority: P0
- Track: authoritative-index
- Bundle: swissknife/contract-assurance/authoritative-index
- Goal: Replace stale compiler-unavailable evidence with one current snapshot-bound repository index and analyzer-health receipt produced by the real TypeScript 5.9.3 parser, while retaining every bounded parse failure as typed evidence.
- Evidence: SCAEV022INDEX
- Outputs: external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_index_handoff.py, implementation_plan/conformance/swissknife-parser-failure-backlog-v1.json, data/agent_supervisor/swissknife_contract_assurance/analyzer_health/report.json, data/agent_supervisor/swissknife_contract_assurance/baseline/repository-index.json, data/agent_supervisor/swissknife_contract_assurance/baseline/current.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_index_handoff.py -q
- Acceptance: Snapshot authority, coverage, AST index, repository index, parser/toolchain identity, and current manifest bind the same roots; every eligible path is success or a typed bounded failure; compiler-unavailable rows are not reused after the compiler identity changes; no provider or model call occurs.
- Gap task: SCA-215, SCA-225, SCA-231, SCA-232, SCA-233, SCA-234, SCA-235, SCA-236, SCA-237, SCA-512
- Conflict policy: Do not lower health thresholds or relabel parse failures; stale index roots remain historical and cannot satisfy current completion.

## SCA-G031 Exact datasets GraphRAG and Cypher-AST binding

- Status: active
- Parent: SCA-G015, SCA-G030
- Priority: P0
- Track: datasets-graph
- Bundle: swissknife/contract-assurance/datasets-graph
- Goal: Bind bounded candidate retrieval and graph-query syntax to the exact `ipfs_datasets_py.logic.intent_ir.graphrag.retrieval` and `ipfs_datasets_py.knowledge_graphs.cypher.ast`/`parser` APIs instead of assuming the package root implements the adapter protocol.
- Evidence: SCAEV031DATASETSGRAPH
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_analysis_provider.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/symbolic_contract_graph.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_symbolic_bridge.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_symbolic_bridge.py -q
- Acceptance: Real modules, signatures, versions, package tree, graph roots, bounds, and result identities are capability-receipted; a real-module canary returns context-only candidates; Cypher AST is syntax-only; package-root fallback, fixture-only backends, and local lexical fallback cannot claim exact datasets use or proof authority.
- Gap task: SCA-213
- Conflict policy: Retain lazy imports and deterministic local availability, but fail the exact-provider gate on missing or incompatible datasets modules.

## SCA-G043 Multi-root provider source index

- Status: active
- Parent: SCA-G010, SCA-G042, SCA-G168
- Priority: P0
- Track: provider-index
- Bundle: swissknife/contract-assurance/provider-index
- Goal: Scan and index the configured source trees for `ipfs_accelerate_py`, `ipfs_kit_py`, and `ipfs_datasets_py` as content-addressed provider roots instead of treating their Gitlinks as opaque identities.
- Evidence: SCAEV043MULTIROOT
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_snapshot.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_indexer.py, external/ipfs_accelerate/test/api/test_agent_supervisor_multi_root_repository_index.py, data/agent_supervisor/swissknife_contract_assurance/baseline/provider-index.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_multi_root_repository_index.py -q
- Acceptance: Each provider root has an origin/commit/tree/dirty-overlay/path ledger and independent analyzer health; cross-root symbols join only through exact package/module/function identities; missing, dirty, moved, or version-divergent roots remain contradictions; provider source bodies stay in CAS.
- Gap task: SCA-216, SCA-225
- Conflict policy: Keep the SwissKnife primary snapshot distinct; never flatten multiple repositories into one ambiguous path namespace or infer source contents from a Gitlink alone.

## SCA-G052 Endpoint-anchor and observed-contract compilation

- Status: active
- Parent: SCA-G041, SCA-G042, SCA-G051, SCA-G170, SCA-G175
- Priority: P0
- Track: invocation-evidence
- Bundle: swissknife/contract-assurance/invocation-evidence
- Goal: Compile reviewed SwissKnife endpoints, MCP++ discovery/call transports, package registrations, schemas, and observed actual contracts into exact tracer anchors and analyzer inputs for the baseline.
- Evidence: SCAEV052ANCHORS
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_contract_evidence_compiler.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_assurance_baseline.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_evidence_compiler.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_evidence_compiler.py -q
- Acceptance: Healthy indexed catalogs deterministically emit nonempty endpoint anchors and observed contracts for every reviewed runtime operation; traces distinguish direct package calls from the mandatory MCP++ route; missing or ambiguous anchors yield typed unknowns rather than a withheld empty-success stage.
- Gap task: SCA-217
- Conflict policy: Only reviewed catalog and indexed source facts become anchors; runtime observations and matching names cannot synthesize registrations or mediation.

## SCA-G062 Exact datasets logic and prover binding

- Status: active
- Parent: SCA-G015, SCA-G060, SCA-G061
- Priority: P0
- Track: datasets-logic
- Bundle: swissknife/contract-assurance/datasets-logic
- Goal: Adapt the real datasets IR, TDFOL, CEC, SMT, and Hammer signatures into the accelerator obligation/prover interfaces and register only capability-probed, reconstruction-compatible backends.
- Evidence: SCAEV062DATASETSLOGIC
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_logic_provider.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_prover.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_logic_conformance.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_logic_conformance.py -q
- Acceptance: Real-module conformance exercises actual signatures rather than injected fixtures; IR and premise selection retain canonical identities; SMT/TDFOL/CEC outputs are candidates until trusted reconstruction; unregistered or unavailable backends are unsupported, never silently local-success.
- Gap task: SCA-214
- Conflict policy: Do not fork datasets logic IR or treat SAT/model output as a proof; capability labels alone cannot register a backend.

## SCA-G071 End-to-end proof/cache orchestration

- Status: active
- Parent: SCA-G052, SCA-G060, SCA-G061, SCA-G062, SCA-G070, SCA-G090
- Priority: P0
- Track: proof-orchestration
- Bundle: swissknife/contract-assurance/proof-orchestration
- Goal: Wire current obligations through `McpContractProver`, kernel verification, `TrustAwareProofCache`, mismatch analysis, and vulnerability refinement in the baseline instead of stopping after object construction.
- Evidence: SCAEV071PROOFCACHE
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_assurance_baseline.py, external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_proof_pipeline.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_proof_pipeline.py -q
- Acceptance: Every supported reviewed operation reaches a terminal proved/refuted/unknown/unsupported/stale state; proof receipts and cache hits revalidate exact snapshot, graph, policy, solver, kernel, and toolchain roots; counterexamples flow into mismatch/vulnerability records; missing evidence withholds downstream authority.
- Gap task: SCA-218
- Conflict policy: `TrustAwareProofCache` remains the sole proof-receipt cache and no analyzer, test, trace, provider, or solver candidate bypasses kernel policy.

## SCA-G082 Real datasets ZK receipt backend

- Status: active
- Parent: SCA-G071, SCA-G080, SCA-G081
- Priority: P1
- Track: zk-backend
- Bundle: swissknife/contract-assurance/zk-backend
- Goal: Bind an available datasets Groth16/ProveKit backend to the approved verified-receipt predicate with setup identity, self-tests, verifier callback, and explicit threat-model gating.
- Evidence: SCAEV082REALZK
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/ipfs_datasets_zk_attestation.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/proof_attestation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_zk_attestation.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_zk_attestation.py -q
- Acceptance: Real setup/prover/verifier identities and current proof/cache roots are bound; positive and negative self-tests pass; only the approved already-verified receipt predicate can attest; unavailable or simulated backends emit non-attested typed status and block real-ZK claims.
- Gap task: SCA-219
- Conflict policy: ZK attests receipt possession/membership or approved private predicates, not source-code correctness or unverified function-call behavior.

## SCA-G160 Promotion, operations, and closeout

- Status: active
- Parent: SCA-G120, SCA-G130, SCA-G140, SCA-G150, SCA-G166, SCA-G167, SCA-G176
- Priority: P1
- Track: rollout
- Bundle: swissknife/contract-assurance/rollout
- Goal: Publish health/status/query/runbook surfaces, shadow-to-assist promotion gates, rollback, lease recovery, artifact retention, and objective exhaustion evidence.
- Evidence: SCAEV160OPS
- Outputs: docs/launch/swissknife-symbolic-contract-supervisor-runbook.md, data/agent_supervisor/swissknife_contract_assurance/completion_gate.json
- Validation: test -f docs/launch/swissknife-symbolic-contract-supervisor-runbook.md && python3 -m json.tool data/agent_supervisor/swissknife_contract_assurance/completion_gate.json >/dev/null
- Acceptance: Operators can verify PID/lease/health/current snapshot/backlog/cache/analyzer and four-component runtime-contract state; automatic mutation remains disabled until all promotion gates pass; rollback returns to shadow without losing evidence.
- Gap task: SCA-160, SCA-230
- Conflict policy: Closeout requires current-tree evidence and cannot be inferred from an empty queue.
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Operators can verify PID/lease/health/current snapshot/backlog/cache/analyzer and four-component runtime-contract state","automatic mutation remains disabled until all promotion gates pass","rollback returns to shadow without losing evidence."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
