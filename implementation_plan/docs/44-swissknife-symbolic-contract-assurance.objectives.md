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
counterexample-to-edit tasks that require minimal model context.

## Goal tree

```text
SCA-G000  Proof-directed SwissKnife contract assurance
|-- SCA-G001  Supervisor-native program sealed
|-- SCA-G010  Exact snapshot, scope, and coverage accounting
|   `-- SCA-G015  Canonical multiformats and CID identity bridge
|-- SCA-G020  Polyglot AST extraction
|   `-- SCA-G021  Whole-tree incremental index
|-- SCA-G030  Typed call/effect/contract graph and bounded GraphRAG
|-- SCA-G040  Reviewed contract authority catalog
|   |-- SCA-G041  SwissKnife expected-contract extraction
|   `-- SCA-G042  Python package actual-surface extraction
|-- SCA-G050  MCP++ invocation reachability
|   `-- SCA-G051  Discovery, execution, transport, and failure parity
|-- SCA-G060  Logic IR and contract obligations
|   `-- SCA-G061  Solver routing and counterexamples
|-- SCA-G070  Trust-aware proof cache and exact invalidation
|-- SCA-G080  ZK threat model and capability policy
|   `-- SCA-G081  Receipt attestation adapter
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
`-- SCA-G160  Promotion, operations, and closeout
```

## SCA-G000 Proof-directed SwissKnife contract assurance

- Status: active
- Parent:
- Priority: P0
- Track: swissknife-contract-assurance
- Bundle: swissknife/contract-assurance/root
- Goal: Deliver a running supervisor program that indexes the complete tracked SwissKnife tree, constructs exact MCP++ call and contract claims, proves or refutes supported claims under explicit authority, and emits minimal targeted accelerator repair tasks.
- Evidence: SCAEV000ROOT
- Outputs: implementation_plan/docs/44-swissknife-symbolic-contract-assurance-plan-2026-07-28.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md, config/swissknife_symbolic_contract_assurance_supervisor.json, config/swissknife_symbolic_contract_assurance_lane_inventory.json, scripts/swissknife_parallel_implementation_supervisor.py
- Validation: test -f implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md && python3 -m json.tool config/swissknife_symbolic_contract_assurance_supervisor.json >/dev/null && python3 -m json.tool config/swissknife_symbolic_contract_assurance_lane_inventory.json >/dev/null && python3 -m py_compile scripts/swissknife_parallel_implementation_supervisor.py
- Acceptance: Every child goal is completed or explicitly blocked with typed evidence; no unaccounted tracked SwissKnife path; generated repair tasks bind current counterexamples and re-proof commands; supervisor refill remains bounded.
- Gap task: Execute child workstreams by task dependency and conflict policy.
- Conflict policy: Own the SCA planning, configuration, and runtime namespaces; do not rewrite SVD/SWR histories or the CBP proof trust model.
- Goal completion schema version: 1
- Completion confidence: 0.0
- Uncovered criteria: ["Every child goal is completed or explicitly blocked with typed evidence","no unaccounted tracked SwissKnife path","generated repair tasks bind current counterexamples and re-proof commands","supervisor refill remains bounded."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G001 Supervisor-native program sealed

- Status: active
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
- Completion confidence: 0.083333
- Uncovered criteria: ["Plan, goals, tasks, identity profiles, proof authority, bounds, and launch command parse under supervisor-native validators","the planning task is complete."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G010 Exact snapshot, scope, and coverage accounting

- Status: active
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

## SCA-G015 Canonical multiformats and CID identity bridge

- Status: active
- Parent: SCA-G010
- Priority: P0
- Track: content-identity
- Bundle: swissknife/contract-assurance/content-identity
- Goal: Normalize accelerator artifacts through explicit canonicalization profiles and bind their exact bytes to validated CIDv1, multicodec, multihash, multibase, and plain digest metadata using the datasets identity modules.
- Evidence: SCAEV015CID
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py -q
- Acceptance: Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256; logic IR uses its separately declared domain-separated raw-codec profile; decoded multihash equals the SHA-256 digest of the exact retained canonical bytes; profile differences among cid_utils, ir_core.identity, ipld_cid, and profile_g remain explicit contradictions; unavailable multiformats support fails closed and no fallback digest is labeled CID.
- Gap task: SCA-015
- Conflict policy: Reuse datasets canonical identity APIs behind a lazy accelerator bridge; never change identity profile or canonicalization implicitly and never create a second proof-cache authority.
- Goal completion schema version: 1
- Completion confidence: 0.083333
- Uncovered criteria: ["Strict DAG-JSON artifacts use lowercase base32 CIDv1/dag-json/sha2-256","logic IR uses its separately declared domain-separated raw-codec profile","decoded multihash equals the SHA-256 digest of the exact retained canonical bytes","profile differences remain explicit contradictions","unavailable multiformats support fails closed and no fallback digest is labeled CID."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

## SCA-G020 Polyglot AST extraction

- Status: active
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

## SCA-G021 Whole-tree incremental index

- Status: active
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

## SCA-G030 Typed call/effect/contract graph and bounded GraphRAG

- Status: active
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

## SCA-G040 Reviewed contract authority catalog

- Status: active
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

## SCA-G041 SwissKnife expected-contract extraction

- Status: active
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

## SCA-G042 Python package actual-surface extraction

- Status: active
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

## SCA-G050 MCP++ invocation reachability

- Status: active
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

## SCA-G051 Discovery, execution, transport, and failure parity

- Status: active
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

## SCA-G060 Logic IR and contract obligations

- Status: active
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

## SCA-G061 Solver routing and counterexamples

- Status: active
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

## SCA-G070 Trust-aware proof cache and exact invalidation

- Status: active
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

## SCA-G080 ZK threat model and capability policy

- Status: active
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

## SCA-G081 Receipt attestation adapter

- Status: active
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

## SCA-G090 Contract mismatch analyzer

- Status: active
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

## SCA-G091 Bug and vulnerability classification

- Status: active
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

## SCA-G100 Minimal CodeEditPacket materialization

- Status: active
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

## SCA-G101 Generated ipfs_accelerate_py repair board

- Status: active
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

## SCA-G110 Supervisor scanner/refill integration

- Status: active
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

## SCA-G111 Grok/Codex bounded provider routing

- Status: active
- Parent: SCA-G100
- Priority: P1
- Track: provider-routing
- Bundle: swissknife/contract-assurance/providers
- Goal: Route implementation proposals to Grok Build and independent bounded review/repair to Codex under one lease and task-specific context limits.
- Evidence: SCAEV111PROVIDERS
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/contract_packet_provider_router.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_packet_provider_router.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_packet_provider_router.py -q
- Acceptance: Providers receive no repository-wide context; review is sequential and read-only until admitted; quotas degrade independently; provider output cannot mark proof or completion.
- Gap task: SCA-111
- Conflict policy: Preserve the single SwissKnife writer lease and existing implementation proposal gate.
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Providers receive no repository-wide context","review is sequential and read-only until admitted","quotas degrade independently","provider output cannot mark proof or completion."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []

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
- Gap task: SCA-120
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

- Status: active
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

## SCA-G160 Promotion, operations, and closeout

- Status: active
- Parent: SCA-G120, SCA-G130, SCA-G140, SCA-G150
- Priority: P1
- Track: rollout
- Bundle: swissknife/contract-assurance/rollout
- Goal: Publish health/status/query/runbook surfaces, shadow-to-assist promotion gates, rollback, lease recovery, artifact retention, and objective exhaustion evidence.
- Evidence: SCAEV160OPS
- Outputs: docs/launch/swissknife-symbolic-contract-supervisor-runbook.md, data/agent_supervisor/swissknife_contract_assurance/completion_gate.json
- Validation: test -f docs/launch/swissknife-symbolic-contract-supervisor-runbook.md && python3 -m json.tool data/agent_supervisor/swissknife_contract_assurance/completion_gate.json >/dev/null
- Acceptance: Operators can verify PID/lease/health/current snapshot/backlog/cache/analyzer state; automatic mutation remains disabled until all promotion gates pass; rollback returns to shadow without losing evidence.
- Gap task: SCA-160
- Conflict policy: Closeout requires current-tree evidence and cannot be inferred from an empty queue.
- Goal completion schema version: 1
- Completion confidence: 0.166667
- Uncovered criteria: ["Operators can verify PID/lease/health/current snapshot/backlog/cache/analyzer state","automatic mutation remains disabled until all promotion gates pass","rollback returns to shadow without losing evidence."]
- Stale evidence: []
- Analyzer health: {"evidence":{},"passed":false,"reason_code":"analyzer_health_missing","status":"missing"}
- Exhaustion quorum: {"evidence":{},"member_count":null,"reason_code":"exhaustion_quorum_missing","required_members":null,"satisfied":false,"stale_members":[]}
- Reopen reasons: []
