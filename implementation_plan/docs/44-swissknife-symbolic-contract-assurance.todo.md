# SwissKnife Symbolic Contract Assurance Taskboard (SCA)

Consumable by `ipfs_accelerate_py.agent_supervisor` with task prefix
`## SCA-`.

Companion objectives:
`implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md`.

Human plan:
`implementation_plan/docs/44-swissknife-symbolic-contract-assurance-plan-2026-07-28.md`.

Runtime profile:
`config/swissknife_symbolic_contract_assurance_supervisor.json`.

## Objective

Build a whole-tree, content-addressed SwissKnife AST and MCP++ contract graph;
prove or refute reviewed structural contracts against the real
`ipfs_accelerate_py`, `ipfs_kit_py`, and `ipfs_datasets_py` MCP surfaces; cache
exact proof receipts; optionally attest approved predicates with a real ZK
backend; and convert current counterexamples into small accelerator repair
tasks with minimal model context.

Normative:

- Every tracked SwissKnife file gets a typed coverage disposition.
- Every authoritative artifact declares a canonicalization and multiformat
  identity profile; decoded CID multihashes must match the exact retained
  canonical bytes.
- GraphRAG, model output, tests, runtime traces, and static analysis are not
  silently promoted into mathematical proof.
- `TrustAwareProofCache` is the only authoritative proof-receipt cache.
- Simulated ZK never emits `ATTESTED`.
- No LLM sees repository-wide source. Providers receive a bounded
  counterexample-first packet only after symbolic analysis creates it.
- Mutation and completion require current-snapshot validation and re-proof.

## Parallel execution contract

- Four deterministic task shards may implement ready tasks concurrently.
- Every active task declares a unique `Parallel lane`, exact `Predicted files`,
  dependencies, validation, and a bounded implementation timeout.
- A task becomes selectable only when all `Depends on` tasks are completed.
- Unordered tasks with overlapping predicted path scopes make launcher
  validation fail closed.
- Each implementation runs in an isolated Git worktree. Canonical task-claim
  locks prevent duplicate execution and one shared merge queue serializes
  integration into `agent/swissknife-sca-parallel`.
- Only shard zero runs objective/codebase refill and taskboard maintenance.
  Other shards are execution-only.
- The outer SwissKnife lease remains singular and covers the parallel
  coordinator and all descendant lanes.

## Execution waves

| Wave | Tasks | Parallelism |
| --- | --- | --- |
| 0 | 000, 010 | Sealed and completed |
| 1 | 015 and 040; then 020 | Identity/catalog in parallel, then AST |
| 2 | 021, 041, 042; then 030 | Index and extractors overlap; graph joins |
| 3 | 050, 051, 060; then 061 and 080 | Invocation chain, then prover/policy in parallel |
| 4 | 070, 090; then 081 and 091 | Cache/mismatch and attestation/security pairs |
| 5 | 100, 101, 111 | Packets, refinery, and provider routing overlap where ready |
| 6 | 110, 120 | Runtime integration and baseline |
| 7 | 121, 130, 140, 150, 166, 167, 168 | Operational fan-out plus parser/provider and snapshot-authority recovery |
| 8 | 170; then 171, 172, 173, 174 | Runtime catalog then four component extractors |
| 9 | 175, 176, 177 | Runtime obligations, exact MCP++ traces, and vulnerability rules |
| 10 | 178, 179, 180, 181; then 160 | Runtime repair/refill, healthy baseline/evaluation, then closeout |

## SCA-000 Seal the supervisor-native program

- Status: completed
- Completion: manual
- Priority: P0
- Track: planning
- Depends on:
- Goal id: SCA-G001
- Outputs: implementation_plan/docs/44-swissknife-symbolic-contract-assurance-plan-2026-07-28.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md, config/swissknife_symbolic_contract_assurance_supervisor.json, config/swissknife_symbolic_contract_assurance_lane_inventory.json, scripts/swissknife_parallel_implementation_supervisor.py
- Validation: test -f implementation_plan/docs/44-swissknife-symbolic-contract-assurance-plan-2026-07-28.md && test -f implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md && test -f implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md && python3 -m json.tool config/swissknife_symbolic_contract_assurance_supervisor.json >/dev/null && python3 -m json.tool config/swissknife_symbolic_contract_assurance_lane_inventory.json >/dev/null && python3 -m py_compile scripts/swissknife_parallel_implementation_supervisor.py
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/planning
- Parallel lane: sca-planning
- Resource class: cpu-small
- Resource stage: planning
- Implementation timeout seconds: 1800
- Predicted files: implementation_plan/docs/44-swissknife-symbolic-contract-assurance-plan-2026-07-28.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md, config/swissknife_symbolic_contract_assurance_supervisor.json, config/swissknife_symbolic_contract_assurance_lane_inventory.json, scripts/swissknife_parallel_implementation_supervisor.py
- Interfaces: ObjectiveGraph, MarkdownTaskSource
- Conflict policy: Own SCA planning/configuration only; preserve all prior boards.
- Preconditions: Current accelerator, datasets, and kit origins are available.
- Effects: Creates reviewed intent and an executable dependency graph; no source implementation mutation.
- Evidence subset: SCA planning seal
- Acceptance: Files parse, goal/task IDs are unique, dependencies are acyclic, trust boundaries and full-scan scope are explicit, and launch configuration is bounded.

## SCA-010 Implement exact repository snapshot and coverage contracts

- Status: completed
- Completion: automated
- Completion evidence: 17 focused tests passed on 2026-07-28
- Priority: P0
- Track: snapshot
- Depends on: SCA-000
- Goal id: SCA-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_snapshot.py, config/swissknife_symbolic_contract_scope.json, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_snapshot.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_snapshot.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/snapshot
- Parallel lane: sca-snapshot
- Allow concurrent with: SCA-040
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_snapshot.py, config/swissknife_symbolic_contract_scope.json, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_snapshot.py
- Interfaces: RepositorySnapshot@1, CoverageDisposition@1, AnalyzerHealth
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Extend existing content-identity and analyzer-health patterns; do not relax clean-tree or proof bindings.
- Preconditions: SCA scope policy in the human plan is reviewed.
- Effects: Produces one canonical identity for the tracked tree plus in-scope overlay and an exhaustive path disposition ledger.
- Evidence subset: Git tree, status overlay, gitlinks, scope policy
- Acceptance: Snapshot binds tracked/staged/modified/deleted and allowlisted untracked inputs; every tracked SwissKnife path has exactly one disposition; exclusion is explicit; dependency directories are represented by lock/tool identities; tests cover dirty, deleted, untracked, rename, submodule, symlink, path escape, and canonical ordering cases.

## SCA-015 Implement the canonical multiformats and CID identity bridge

- Status: completed
- Completion: automated
- Completion evidence: 29 focused tests passed and the implementation was merged into agent/swissknife-sca-parallel on 2026-07-29
- Priority: P0
- Track: content-identity
- Depends on: SCA-010
- Goal id: SCA-G015
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/content-identity
- Parallel lane: sca-content-identity
- Allow concurrent with: SCA-040
- Resource class: cpu-small
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py
- Interfaces: ContentIdentity@1, ipfs_datasets.utils.cid_utils, ipfs_datasets.logic.ir_core.identity, multiformats.CID, multiformats.multihash
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Add one lazy accelerator adapter over datasets identity APIs; do not fork canonicalizers, silently recanonicalize bytes, equate different codecs, or create another proof-cache trust root.
- Preconditions: RepositorySnapshot canonical payload contract exists.
- Effects: Emits profile-tagged canonical bytes, SHA-256 digest, CID text/version/base/codec/multihash metadata, and validation reason codes for every authoritative artifact class.
- Evidence subset: datasets cid_utils, logic.ir_core.identity, logic.ipld_cid, logic.profile_g, multiformats conformance vectors
- Acceptance: Strict artifact profile is lowercase base32 CIDv1/dag-json/sha2-256; domain-separated logic IR profile remains raw-codec ir-canonical-identity-v1; every CID decodes and its raw multihash digest equals SHA-256 of the retained canonical bytes; cross-module canonical-byte or codec differences become typed profile contradictions; provider import remains lazy; missing multiformats fails closed for CID-required operations; no fallback or digest-shaped string is labeled CID.

## SCA-020 Add deterministic TypeScript and JavaScript AST extraction

- Status: completed
- Priority: P0
- Track: ast
- Depends on: SCA-015
- Goal id: SCA-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/polyglot_ast_provider.py, external/ipfs_accelerate/scripts/extract_typescript_ast.mjs, external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_provider.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_provider.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/ast
- Parallel lane: sca-ast
- Allow concurrent with: SCA-040
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/polyglot_ast_provider.py, external/ipfs_accelerate/scripts/extract_typescript_ast.mjs, external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_provider.py
- Interfaces: ASTBlobRecord, PolyglotASTProvider@1
- Context budget tokens: 6144
- Provider role: grok-implement, codex-review
- Conflict policy: Emit existing canonical ASTBlobRecord facts; do not fork AnalysisASTIndex or persist source bodies in rows.
- Preconditions: RepositorySnapshot and exact source/blob identities exist.
- Effects: Adds bounded TS/JS/TSX/JSX extraction through the local TypeScript compiler API while preserving Python extraction and structured-schema adapters.
- Evidence subset: ASTBlobRecord schema, TypeScript compiler API, representative SwissKnife fixtures
- Acceptance: Stable symbols, imports, calls, interfaces, state/effect facts, semantic symbol hashes, and line spans; compiler/tool version bound; parse errors typed; process timeout and byte/file limits enforced; cold Python import starts no Node process; no LLM use.

## SCA-021 Build the complete incremental SwissKnife index

- Status: completed
- Priority: P0
- Track: ast-index
- Depends on: SCA-020
- Goal id: SCA-G021
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_indexer.py, external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_indexer.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_indexer.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/index
- Parallel lane: sca-index
- Allow concurrent with: SCA-040, SCA-041, SCA-042
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_indexer.py, external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_indexer.py
- Interfaces: RepositoryIndexer@1, AnalysisASTIndex, AnalysisCache, RuntimeCAS
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Reuse content-addressed cache and AST invalidations; one current snapshot per index root.
- Preconditions: Snapshot and polyglot AST producer pass fixtures.
- Effects: Indexes all supported source and schema facts while recording explicit dispositions for every other tracked path.
- Evidence subset: Exact snapshot, path ledger, AST records, cache outcomes
- Acceptance: No silent skip; source bodies remain in CAS; compact rows bounded; unchanged blob reuse, rename reuse, deletion/change invalidation, corruption recovery, concurrent readers, deterministic serialization, parser-health thresholds, and 5,771-path seed accounting tested.

## SCA-030 Project the typed contract graph and bounded GraphRAG view

- Status: completed
- Priority: P0
- Track: graph
- Depends on: SCA-021
- Goal id: SCA-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/symbolic_contract_graph.py, external/ipfs_accelerate/test/api/test_agent_supervisor_symbolic_contract_graph.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_symbolic_contract_graph.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/graph
- Parallel lane: sca-graph
- Allow concurrent with: SCA-041, SCA-042
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/symbolic_contract_graph.py, external/ipfs_accelerate/test/api/test_agent_supervisor_symbolic_contract_graph.py
- Interfaces: SymbolicContractGraph@1, CodeEvidenceGraph, BoundedGraphRAGRetriever, ContentIdentity@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: GraphRAG nominates context-only edges; deterministic typed closure supplies mandatory proof dependencies.
- Preconditions: Current repository index and analyzer-health receipt exist.
- Effects: Creates content-addressed nodes and edges for files, modules, symbols, calls, imports, effects, schemas, tools, handlers, tests, policy, transport, and provenance.
- Evidence subset: AST index, schema index, CodeEvidenceGraph
- Acceptance: Identity/provenance/authority/version on every node and edge; stable graph root; exact forward/reverse closure; bounded candidate retrieval with receipt; truncation and missing mandatory edges fail closed; optional datasets provider remains lazy.

## SCA-040 Define the reviewed MCP contract catalog

- Status: completed
- Completion: automated
- Completion evidence: 29 focused tests passed and the implementation was merged into agent/swissknife-sca-parallel on 2026-07-29
- Priority: P0
- Track: contracts
- Depends on: SCA-010
- Goal id: SCA-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_catalog.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_catalog.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/catalog
- Parallel lane: sca-catalog
- Allow concurrent with: SCA-010, SCA-015, SCA-020, SCA-021
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_catalog.py
- Interfaces: McpContractCatalog@1, CodePropertyCatalog
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Adapt existing property catalog and interface contracts; retain one assurance lattice.
- Preconditions: Authority precedence in human plan is reviewed.
- Effects: Publishes closed claim families and versioned contract source records.
- Evidence subset: MCP-IDL, JSON Schema, typed interfaces, conformance tests, registrations, manifests, docs
- Acceptance: Canonical IDs; explicit authority and review state; contradictory sources remain contradictory; unknown/unreviewed prose fails closed; source and schema version invalidators are complete.

## SCA-041 Extract SwissKnife expected MCP++ contracts

- Status: completed
- Priority: P0
- Track: expected-contracts
- Depends on: SCA-020, SCA-040
- Goal id: SCA-G041
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/swissknife_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_contract_extractor.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/expected
- Parallel lane: sca-expected
- Allow concurrent with: SCA-021, SCA-030, SCA-042
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/swissknife_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_swissknife_contract_extractor.py
- Interfaces: SwissKnifeContractExtractor@1, McpContractCatalog@1
- Context budget tokens: 6144
- Provider role: grok-implement, codex-review
- Conflict policy: SwissKnife is read-only evidence in this task; no inferred declaration becomes authoritative.
- Preconditions: Typed graph and catalog APIs exist.
- Effects: Normalizes descriptors, capability registries, connectors, policy mediators, app bindings, schemas, direct fetches, compatibility routes, and contract tests.
- Evidence subset: swissknife/src/services/mcp, swissknife/src/services/apps, swissknife/contracts, focused tests/scripts
- Acceptance: All canonical package descriptors represented; direct/compatibility invocation edges retained; dynamic values unresolved with source span; versions/defaults/errors/streaming/policy/transport expectations preserved; fixtures cover conflicting descriptor and test sources.

## SCA-042 Extract actual MCP surfaces from all Python packages

- Status: completed
- Priority: P0
- Track: actual-contracts
- Depends on: SCA-020, SCA-040
- Goal id: SCA-G042
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/python_mcp_surface_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_python_mcp_surface_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_python_mcp_surface_extractor.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/actual
- Parallel lane: sca-actual
- Allow concurrent with: SCA-021, SCA-030, SCA-041
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/python_mcp_surface_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_python_mcp_surface_extractor.py
- Interfaces: PythonMcpSurfaceExtractor@1, McpContractCatalog@1
- Context budget tokens: 6144
- Provider role: grok-implement, codex-review
- Conflict policy: Static extraction is default; live import/discovery is optional typed evidence and cannot change static authority.
- Preconditions: Catalog and graph APIs exist.
- Effects: Normalizes registration, schemas, hierarchical facade dispatch, aliases, handlers, policy checks, transports, and implementation symbols in accelerate, kit, and datasets.
- Evidence subset: Exact scoped paths and Git identities for three provider repositories
- Acceptance: Cold extraction imports no provider package; facade meta-tools and domain tools remain distinguishable; handler reachability and source spans retained; live tools/list fixtures are capability-bound; dynamic registration is unresolved, not absent.

## SCA-050 Compute exact MCP++ invocation reachability

- Status: completed
- Priority: P0
- Track: invocation
- Depends on: SCA-030, SCA-041, SCA-042
- Goal id: SCA-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_invocation_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_invocation_trace.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_invocation_trace.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/invocation
- Parallel lane: sca-invocation
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_invocation_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_invocation_trace.py
- Interfaces: McpInvocationTrace@1, SymbolicContractGraph@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Reachability proves graph structure only; it does not prove handler semantics.
- Preconditions: Expected and actual normalized catalogs share stable join keys.
- Effects: Joins each SwissKnife operation through descriptor, registry, connector, transport, tools/call or facade dispatch, package handler, and implementation.
- Evidence subset: Catalog joins and typed mandatory closure
- Acceptance: Exactly one terminal state of reachable/refuted/ambiguous/unsupported/not_measured; path contains edge IDs and source spans; direct and compatibility paths visible; unresolved dynamic segment prevents proved reachability.

## SCA-051 Analyze schema, argument, result, policy, transport, and failure parity

- Status: completed
- Priority: P0
- Track: parity
- Depends on: SCA-050
- Goal id: SCA-G051
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_analysis.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_analysis.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_analysis.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/parity
- Parallel lane: sca-parity
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_analysis.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_analysis.py
- Interfaces: McpContractAnalysis@1, McpInvocationTrace@1
- Context budget tokens: 6144
- Provider role: grok-implement, codex-review
- Conflict policy: Preserve typed unknown and partial states; no best-effort coercion at authority boundaries.
- Preconditions: Exact invocation traces exist.
- Effects: Emits reviewed contract claims and premises for every parity dimension.
- Evidence subset: Expected/actual schema and traces, policy dominance, transport variants, error envelopes
- Acceptance: Detect argument rename/default/type loss, schema variance violations, envelope/error collapse, tools/list versus tools/call drift, policy-after-effect, transport-only bypass, and compatibility bypass; aliases require reviewed mapping; seeded fixtures pass/refute deterministically.

## SCA-060 Compile contract claims into canonical logic obligations

- Status: completed
- Priority: P0
- Track: logic-ir
- Depends on: SCA-040, SCA-051
- Goal id: SCA-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_obligations.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_obligations.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_obligations.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/logic
- Parallel lane: sca-logic
- Resource class: cpu-proof-solver
- Resource stage: proof
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_obligations.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_obligations.py
- Interfaces: CodeProofObligation, CodeClaimRecord@1, ipfs_datasets logic IR
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Reuse formal_verification_contracts and shared logic IR; do not create a second claim or assurance model.
- Preconditions: Reviewed catalog and claim premises available.
- Effects: Produces compact graph/relation/schema/deontic/temporal obligations with explicit supported fragments.
- Evidence subset: Contract IDs, exact premise IDs, assumptions, invalidators
- Acceptance: Snapshot/scope/catalog/toolchain/policy/required-assurance bound; unsupported fragment explicit; no source dumps or natural-language theorem invention; canonical round trip and premise-order invariance tested.

## SCA-061 Route proofs and produce compact counterexamples

- Status: completed
- Priority: P0
- Track: proving
- Depends on: SCA-060
- Goal id: SCA-G061
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_prover.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_prover.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_prover.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/proving
- Parallel lane: sca-proving
- Resource class: cpu-proof-solver
- Resource stage: proof
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_prover.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_prover.py
- Interfaces: MultiProverRouter, ProofReceipt, FormalCounterexample
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Capability probe before dispatch; candidate solvers cannot grant kernel assurance.
- Preconditions: Typed obligations and local deterministic graph/schema checkers exist.
- Effects: Routes graph and schema checks locally, then supported TDFOL/CEC/SMT/kernel operations through lazy datasets providers.
- Evidence subset: Obligation, prover matrix, exact capability/policy/toolchain
- Acceptance: Proved/refuted/unsupported/inconclusive/timed_out distinct; failed edge/premise counterexamples compact; deterministic fallback without datasets/prover; no LLM call; forged provider assurance rejected.

## SCA-070 Integrate trust-aware proof caching and invalidation

- Status: completed
- Priority: P0
- Track: proof-cache
- Depends on: SCA-015, SCA-061
- Goal id: SCA-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_proof_cache.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_proof_cache.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_proof_cache.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/cache
- Parallel lane: sca-cache
- Allow concurrent with: SCA-080, SCA-090
- Resource class: cpu-medium
- Resource stage: proof
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_proof_cache.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_proof_cache.py
- Interfaces: TrustAwareProofCache, ProofCacheKey, ProofReceipt
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Existing formal_verification_cache is the sole trust root; adapter owns no second cache.
- Preconditions: Prover emits typed receipts and counterexamples.
- Effects: Lookup-before-prove, put-after-validated-proof, single-flight, exact semantic invalidation, and bounded negative TTL.
- Evidence subset: Snapshot, obligation, premises, assumptions, catalog, provider, toolchain, policy, assurance
- Acceptance: Warm exact hit avoids provider and re-derives assurance; keys bind declared identity profiles and CIDs; retained canonical bytes revalidate against decoded multihash; every semantic dimension invalidates; poisoned/wrong-tree/private/candidate/stale/cross-profile entries reject with reason; concurrent identical requests one flight; retention bounds tested.

## SCA-080 Seal the ZK threat model and attestation policy

- Status: completed
- Priority: P1
- Track: zk-policy
- Depends on: SCA-060
- Goal id: SCA-G080
- Outputs: external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_THREAT_MODEL.md, external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_POLICY.md
- Validation: test -f external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_THREAT_MODEL.md && test -f external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_POLICY.md
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/zk-policy
- Parallel lane: sca-zk-policy
- Allow concurrent with: SCA-061, SCA-070, SCA-090
- Resource class: cpu-small
- Resource stage: proof
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_THREAT_MODEL.md, external/ipfs_accelerate/docs/architecture/SWISSKNIFE_CONTRACT_ZK_POLICY.md
- Interfaces: ProofAttestationPolicy, ipfs_datasets zkp_attestation
- Context budget tokens: 4096
- Provider role: grok-draft, codex-review
- Conflict policy: Extend CBP ZK policy; no backend implementation before approved use case.
- Preconditions: Property proof and cache semantics are stable.
- Effects: Defines qualifying private witness, public inputs, setup trust, replay, leakage, backend capability, and assurance rules.
- Evidence subset: Existing proof_attestation and datasets ZK capability behavior
- Acceptance: Clearly separates property proof, receipt integrity, and ZK; approved predicates limited to receipt possession/membership/private reviewed predicate; simulation below ATTESTED; no secret/witness in receipt/context/log; unsupported use case terminates not applicable.

## SCA-081 Implement capability-checked proof receipt attestation

- Status: completed
- Priority: P1
- Track: zk-attestation
- Depends on: SCA-070, SCA-080
- Goal id: SCA-G081
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_attestation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_attestation.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_attestation.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/zk-attestation
- Parallel lane: sca-zk
- Allow concurrent with: SCA-091, SCA-100
- Resource class: cpu-proof-solver
- Resource stage: proof
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_attestation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_attestation.py
- Interfaces: ProofAttestation, ZkpAttestationAdapter
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Lazy adapter over existing proof_attestation and datasets bridge; no witness persistence.
- Preconditions: Approved policy identifies at least one qualifying predicate, otherwise implement explicit not-applicable path only.
- Effects: Attests current validated receipts with real backend when available and emits typed simulated/unavailable state otherwise.
- Evidence subset: Receipt/cache/snapshot/property roots and capability report
- Acceptance: Public inputs bind receipt/property/snapshot/policy/backend/setup/result-set-root CIDs and identity-profile IDs; witness zeroized/not serialized; forged root, replay, changed policy, changed backend/setup, simulation promotion, malformed proof, cross-profile identity, and capability drift fail closed.

## SCA-090 Build the deterministic contract mismatch analyzer

- Status: completed
- Priority: P0
- Track: mismatches
- Depends on: SCA-051, SCA-061
- Goal id: SCA-G090
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_mismatch_analyzer.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_analyzer.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_analyzer.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/mismatches
- Parallel lane: sca-mismatches
- Allow concurrent with: SCA-070, SCA-080
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_mismatch_analyzer.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_analyzer.py
- Interfaces: ContractFinding@1, CodeProofQuery@1, FormalCounterexample
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Finding lifecycle mirrors claim lifecycle; cache miss and unknown are not refutation.
- Preconditions: Parity claims and current proof/cache results exist.
- Effects: Produces deterministic finding identities, bounded impact closure, source ownership, and stale/reopen transitions.
- Evidence subset: Refuted/stale/contradictory/ambiguous/unsupported/not_measured claims
- Acceptance: Dedupe identity binds snapshot/contract/family/symbols/counterexample; exact reproduction handles; changed evidence updates one finding; source ownership routes accelerator, kit, datasets, SwissKnife, or MCP++ without guessing.

## SCA-091 Add bug and vulnerability classification rules

- Status: completed
- Priority: P0
- Track: security-findings
- Depends on: SCA-090
- Goal id: SCA-G091
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_vulnerability_rules.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_vulnerability_rules.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_vulnerability_rules.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/security
- Parallel lane: sca-security
- Allow concurrent with: SCA-081
- Resource class: cpu-medium
- Resource stage: security
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_vulnerability_rules.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_vulnerability_rules.py
- Interfaces: ContractVulnerabilityFinding@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Separate proof status, confidence, severity, exploitability, and taxonomy.
- Preconditions: Deterministic finding and counterexample exist.
- Effects: Classifies policy bypass, auth-after-effect, schema confusion, argument loss, capability escalation, compatibility bypass, stale replay, failure collapse, and transport drift.
- Evidence subset: Matched structural premises and reviewed security rule IDs
- Acceptance: CWE/OWASP/CAPEC tags only with complete premises; unknown/dynamic behavior not automatically vulnerable; severity deterministic and override-reviewable; seeded positive/negative fixtures have no false authoritative admission.

## SCA-100 Materialize minimal contract-directed edit packets

- Status: completed
- Priority: P0
- Track: packets
- Depends on: SCA-090, SCA-091
- Goal id: SCA-G100
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_edit_packet.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_edit_packet.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_edit_packet.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/packets
- Parallel lane: sca-packets
- Allow concurrent with: SCA-081
- Resource class: cpu-medium
- Resource stage: planning
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/mcp_contract_edit_packet.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_edit_packet.py
- Interfaces: CodeEditPacket, ContextCapsule, ContractFinding@1
- Context budget tokens: 6144
- Provider role: grok-implement, codex-review
- Conflict policy: Extend existing packet/context APIs and preserve required-core non-truncation.
- Preconditions: Current admitted finding, counterexample, impact closure, and ownership.
- Effects: Emits task/contract/obligation IDs, affected symbols, compact slice, counterexample, postcondition, validations, re-proof, handles, and exact read/write paths.
- Evidence subset: Minimal mandatory closure and content-addressed expansion manifest
- Acceptance: Packet stale check; no repository/AST/proof body; prompt-injection text labeled data; max 8,192 tokens with fixture median target <=2,048; omitted mandatory dependency rejected; unchanged retry uses proof_delta only.

## SCA-101 Emit the generated ipfs_accelerate_py bug and vulnerability board

- Status: completed
- Priority: P0
- Track: task-refinery
- Depends on: SCA-100
- Goal id: SCA-G101
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/contract_mismatch_refinery.py, data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_refinery.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_refinery.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/refinery
- Parallel lane: sca-refinery
- Allow concurrent with: SCA-111
- Resource class: cpu-medium
- Resource stage: planning
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/contract_mismatch_refinery.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_mismatch_refinery.py
- Interfaces: BacklogRefinery, MarkdownTaskSource, CodeEditPacket
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Generated board is a bounded projection; only accelerator-owned paths admitted.
- Preconditions: Valid non-stale packet and goal lineage.
- Effects: Creates deduplicated repair tasks with priority, dependencies, exact files, reproduction, validation, re-proof, and acceptance.
- Evidence subset: Accelerator-owned admitted findings
- Acceptance: No broad source-review task; stale finding updates/blocks existing task; open-work/finding/cooldown bounds; deterministic IDs; malformed paths/dependencies rejected; generated task cannot self-certify completion.

## SCA-110 Integrate contract analysis into supervisor refill

- Status: completed
- Priority: P0
- Track: supervisor-runtime
- Depends on: SCA-021, SCA-090, SCA-101
- Goal id: SCA-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/contract_assurance_refill.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_refill.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_refill.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime
- Parallel lane: sca-runtime
- Allow concurrent with: SCA-111
- Resource class: cpu-medium
- Resource stage: runtime
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/contract_assurance_refill.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_refill.py
- Interfaces: ObjectiveDaemon, BacklogRefinery, AnalyzerHealth, ContractMismatchRefinery
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Direct Python handler and typed records only; no shell-string control route.
- Preconditions: Index, analyzer, and generated-board refinery are deterministic.
- Effects: Low backlog triggers bounded current-snapshot index/analyze/prove/refine and persists health/findings/cache/refill receipts.
- Evidence subset: Objective gaps, snapshot delta, analyzer health, current findings, retry/dependency guardrails
- Acceptance: Goal lineage required; current capability and health required; task storms prevented; state corruption recovered; restart idempotent; no finding means exhaustion only with full coverage/canaries/quorum.

## SCA-111 Add bounded Grok implementation and Codex review routing

- Status: completed
- Priority: P1
- Track: provider-routing
- Depends on: SCA-100
- Goal id: SCA-G111
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/contract_packet_provider_router.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_packet_provider_router.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_packet_provider_router.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/providers
- Parallel lane: sca-providers
- Allow concurrent with: SCA-101, SCA-110
- Resource class: llm-bounded
- Resource stage: implementation
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/contract_packet_provider_router.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_packet_provider_router.py
- Interfaces: ImplementationProviderRouter@1, CodeEditPacket
- Context budget tokens: 4096
- Provider role: grok-implement, codex-independent-review
- Conflict policy: One SwissKnife writer lease; Codex review is sequential and proposal-only.
- Preconditions: Packet read/write scope and current-snapshot check pass.
- Effects: Selects Grok for implementation and Codex for bounded review/repair, with independent quota latches and deterministic local no-model path.
- Evidence subset: Packet, provider capability/quota, validation/re-proof results
- Acceptance: No provider receives broad repository context; provider output cannot change proof/completion; Codex review cannot write before admitted; quota failure falls back or defers with typed reason; exact prompt/response size limits and redaction tested.

## SCA-120 Run the no-mutation baseline scan

- Status: completed
- Completion: manual
- Priority: P0
- Track: baseline
- Depends on: SCA-021, SCA-051, SCA-061, SCA-070, SCA-090, SCA-167, SCA-168
- Goal id: SCA-G120
- Outputs: data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md
- Validation: python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline --shadow
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/baseline
- Parallel lane: sca-baseline
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 21600
- Predicted files: data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md
- Interfaces: RepositoryIndexer@1, ContractMismatchAnalyzer@1
- Context budget tokens: 2048
- Provider role: deterministic-only
- Proposal artifact envelope: {"schema":"ipfs_accelerate_py/agent-supervisor/task-artifact-envelope@1","paths":["data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json","data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json","data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md"],"max_file_bytes":4000000,"max_patch_bytes":8000000,"max_output_bytes":16000000}
- Conflict policy: Shadow task writes evidence only; no source, board status, or implementation mutation.
- Preconditions: Full pipeline unit/conformance tests pass.
- Effects: Captures exact baseline coverage, capabilities, graph root, claims, proofs, counterexamples, cache outcomes, and analyzer health.
- Evidence subset: Current parent and recursive submodule snapshot
- Acceptance: All tracked paths disposed; exact snapshot/capability/policy roots; every contract terminal status typed; generated findings reproducible; partial health prevents exhaustive/no-drift claim; zero LLM calls.

## SCA-121 Triage baseline counterexamples into initial accelerator packets

- Status: active
- Priority: P0
- Track: baseline-triage
- Depends on: SCA-100, SCA-101, SCA-200
- Goal id: SCA-G120
- Outputs: data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md, data/agent_supervisor/swissknife_contract_assurance/baseline/triage.json
- Validation: python3 -m ipfs_accelerate_py.agent_supervisor.objectives.contract_mismatch_refinery --findings data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json --owner external/ipfs_accelerate --output data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/baseline-triage
- Parallel lane: sca-triage
- Allow concurrent with: SCA-130, SCA-140, SCA-150
- Resource class: cpu-medium
- Resource stage: planning
- Implementation timeout seconds: 7200
- Predicted files: data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md, data/agent_supervisor/swissknife_contract_assurance/baseline/triage.json
- Interfaces: ContractMismatchRefinery, CodeEditPacket
- Context budget tokens: 2048
- Provider role: deterministic-only
- Conflict policy: Route only accelerator-owned findings; preserve other owner queues as evidence.
- Preconditions: Baseline health allows finding admission.
- Effects: Seeds the first minimal bug/vulnerability backlog without broad model review.
- Evidence subset: Current admitted accelerator findings and packets
- Acceptance: Every task maps one current counterexample family/impact cluster; no duplicate identity; severity and proof state separate; exact validation/re-proof and path allowlists; stale or unsupported findings not implementation-ready.

## SCA-130 Implement continuous exact invalidation and refill

- Status: active
- Priority: P1
- Track: continuous
- Depends on: SCA-110, SCA-200
- Goal id: SCA-G130
- Outputs: data/agent_supervisor/swissknife_contract_assurance/state/invalidation.jsonl, data/agent_supervisor/swissknife_contract_assurance/state/refill_metrics.json, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_incremental.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_incremental.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/continuous
- Parallel lane: sca-continuous
- Allow concurrent with: SCA-121, SCA-140, SCA-150
- Resource class: cpu-large
- Resource stage: runtime
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_incremental.py
- Interfaces: ProofScopeIndex, AnalysisASTIndex, ContractAssuranceRefill
- Context budget tokens: 2048
- Provider role: deterministic-only
- Conflict policy: Preserve historical receipts and mark stale; never delete evidence to manufacture clean state.
- Preconditions: Baseline and durable state roots valid.
- Effects: Updates changed blobs and reverse dependency closure, re-proves affected claims, updates finding/task lifecycle, and records metrics.
- Evidence subset: Parent/child snapshot delta and reverse proof scope
- Acceptance: Controlled symbol/schema/policy/toolchain changes invalidate all and only dependents; rename/deletion handled; cooldown/dedupe/open bounds hold; no-op scan has no provider/model work; crash recovery idempotent.

## SCA-140 Benchmark scale, cache reuse, and context size

- Status: active
- Priority: P1
- Track: benchmark
- Depends on: SCA-070, SCA-100, SCA-200
- Goal id: SCA-G140
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py, data/agent_supervisor/swissknife_contract_assurance/benchmarks/report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/benchmark
- Parallel lane: sca-benchmark
- Allow concurrent with: SCA-121, SCA-130, SCA-150
- Resource class: cpu-large
- Resource stage: benchmark
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py, data/agent_supervisor/swissknife_contract_assurance/benchmarks/report.json
- Interfaces: ContractAssuranceBenchmark@1
- Context budget tokens: 2048
- Provider role: deterministic-only
- Conflict policy: Report observed resource envelope; do not promote concurrency from synthetic counts.
- Preconditions: Baseline artifacts and packet fixtures available.
- Effects: Measures cold/warm/incremental parse, graph, proof, cache, bytes, RSS, process count, and packet tokens.
- Evidence subset: Current SwissKnife baseline plus controlled 10x irrelevant corpus fixture
- Acceptance: >=95 percent unchanged blob/obligation reuse target; packets <=8192 and median target <=2048 tokens; irrelevant corpus growth does not materially change mandatory context; storage/latency/high-watermarks and failures reported.

## SCA-150 Run adversarial and mutation evaluation

- Status: completed
- Priority: P0
- Track: evaluation
- Depends on: SCA-051, SCA-061, SCA-070, SCA-081, SCA-100
- Goal id: SCA-G150
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_adversarial.py, data/agent_supervisor/swissknife_contract_assurance/evaluation/report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_adversarial.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/evaluation
- Parallel lane: sca-evaluation
- Allow concurrent with: SCA-121, SCA-130, SCA-140
- Resource class: cpu-proof-solver
- Resource stage: evaluation
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_adversarial.py, data/agent_supervisor/swissknife_contract_assurance/evaluation/report.json
- Interfaces: ContractAssuranceEvaluation@1
- Context budget tokens: 2048
- Provider role: deterministic-only
- Conflict policy: Held-out mutations remain outside provider context and premise-selection training.
- Preconditions: Claim/proof/cache/attestation/packet paths pass conformance.
- Effects: Seeds missing handler, wrong schema/default, alias confusion, direct bypass, auth-after-effect, transport drift, error collapse, forged/stale cache, poisoned graph, simulated ZK, witness leak, prompt injection, and closure truncation.
- Evidence subset: Preregistered positive/negative/held-out fixtures
- Acceptance: Zero false authoritative admissions; all seeded mandatory safety failures detected or explicitly unsupported; mutation score, precision/recall by claim family, repair precision, and regression rate published; no hidden fixture reaches LLM.

## SCA-160 Publish promotion gates and operations runbook

- Status: active
- Priority: P1
- Track: rollout
- Depends on: SCA-111, SCA-130, SCA-140, SCA-150, SCA-166, SCA-167, SCA-181
- Goal id: SCA-G160
- Outputs: docs/launch/swissknife-symbolic-contract-supervisor-runbook.md, data/agent_supervisor/swissknife_contract_assurance/completion_gate.json
- Validation: test -f docs/launch/swissknife-symbolic-contract-supervisor-runbook.md && python3 -m json.tool data/agent_supervisor/swissknife_contract_assurance/completion_gate.json >/dev/null
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/rollout
- Parallel lane: sca-rollout
- Resource class: cpu-small
- Resource stage: rollout
- Implementation timeout seconds: 7200
- Predicted files: docs/launch/swissknife-symbolic-contract-supervisor-runbook.md, data/agent_supervisor/swissknife_contract_assurance/completion_gate.json
- Interfaces: SupervisorHealth, CompletionEvidence, RolloutDecision
- Context budget tokens: 4096
- Provider role: grok-draft, codex-review
- Conflict policy: Empty queue is not completion; current-tree coverage/proof/evaluation evidence required.
- Preconditions: Continuous, benchmark, and adversarial evidence current.
- Effects: Documents start/status/stop/reclaim/recovery/query/retention/rollback and defines shadow, assist, and automatic gates.
- Evidence subset: Current PID/lease/health/snapshot/backlog/cache/analyzer/evaluation state
- Acceptance: Operator can verify live supervisor and exact bindings; shadow is default; promotion requires zero false authority and complete health gates; rollback disables model mutation but retains evidence; goal exhaustion requires current healthy scan and child completion proofs.

## SCA-161 Resolve validation retry-budget failure for SCA-040

- Status: completed
- Completion: manual
- Completion evidence: Catalog outputs were validated and merged through the isolated integration worktree on 2026-07-29
- Priority: P1
- Track: ops
- Depends on: SCA-010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/mcp_contract_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_mcp_contract_catalog.py, data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-01/discovery
- Validation: test -f /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-01/discovery/2026-07-28-sca-161-sca-040-retry-budget.md
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in SCA-040. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-01/discovery/2026-07-28-sca-161-sca-040-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release SCA-040 from strategy blocked_tasks.

## SCA-162 Resolve validation retry-budget failure for SCA-015

- Status: completed
- Completion: manual
- Completion evidence: Content-identity outputs were validated and merged through the isolated integration worktree on 2026-07-29
- Priority: P1
- Track: ops
- Depends on: SCA-010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py, external/ipfs_accelerate/test/api/test_agent_supervisor_content_identity_bridge.py, data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery
- Validation: test -f /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery/2026-07-28-sca-162-sca-015-retry-budget.md
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in SCA-015. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery/2026-07-28-sca-162-sca-015-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release SCA-015 from strategy blocked_tasks.

## SCA-163 Resolve dirty main checkout blocking 1 worktree merges

- Status: completed
- Completion: manual
- Completion evidence: Reconciliation now targets agent/swissknife-sca-parallel in an ephemeral worktree; unrelated dirty main content was preserved
- Priority: P1
- Track: ops
- Fingerprint: 9d07bd096ca9fcd86ac68453c056b8b53bbb1942
- Dedupe key: reconciliation_guardrail:main_checkout_dirty
- Depends on:
- Outputs: data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery, implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md
- Validation: test -f /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery/2026-07-28-sca-163-reconciliation-9d07bd096ca9.md
- Acceptance: Reconciliation guardrail filed this because 1 branch or worktree cleanup candidates are blocked by main_checkout_dirty. This task is intentionally operator-gated because unknown dirty checkout content must not be committed, stashed, or discarded automatically. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery/2026-07-28-sca-163-reconciliation-9d07bd096ca9.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## SCA-164 Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py:241

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py
- Validation: python3 -m py_compile external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py
- Graph parents: SCA-G010, SCA-G000
- Graph depth: 2
- Goal id: SCA-G015
- Goal lineage: SCA-G015, SCA-G010, SCA-G000
- Goal registration: existing
- Canonical task key: task/v1/d3c8c2794726bece22e9be3b090d3adb11816d0669a72d204ae7053579cd16e0
- Canonical task CID: baguqeera2peme6khe27m4ixjxy5qsdj23miyc3igngts2ick44ctk6onc3qa
- Semantic identity: d3c8c2794726bece22e9be3b090d3adb11816d0669a72d204ae7053579cd16e0
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py:241
- Preconditions: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py:241, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-164-codebase-scan-ff65e1bdaf7e.md
- Resource class: cpu-small
- Token class: small
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py:241
- Candidate kind: codebase_scan
- Todo vector key: ff65e1bdaf7e3033
- Bundle: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-content_identity_bridge
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-content_identity_bridge.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-content_identity_bridge
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py
- AST symbols: __future__, __future__.annotations, __init__, _assert_not_digest_as_cid, _build_identity, _cache_module, _is_multiformats_failure, _provider_snapshot, _require_module, _sha256_digest_bytes, assert not digest as cid, build identity, cache module, cidvalidationerror, cidvalidationerror init, cidvalidationerror.__init__, collections abc, collections abc mapping, collections abc sequence, collections.abc, collections.abc.mapping, collections.abc.sequence, compare provider identities, compare_provider_identities, content identity probe, content_identity_probe, contentidentity, contentidentity hexdigest, contentidentity to dict, contentidentity.hexdigest, contentidentity.to_dict, contentidentityerror, contentidentityerror init, contentidentityerror.__init__, dataclasses, dataclasses dataclass, dataclasses field, dataclasses.dataclass, dataclasses.field, decode and verify cid, decode and verify identity, decode_and_verify_cid, decode_and_verify_identity, enum, enum enum, enum.enum, future, future annotations, hashlib, hexdigest, identify for profile, identify logic ir, identify strict artifact, identify strict artifact bytes, identify_for_profile, identify_logic_ir, identify_strict_artifact, identify_strict_artifact_bytes, importlib, init, is digest shaped, is multiformats failure, is_digest_shaped, multiformats, multiformats available, multiformats cid, multiformats multihash, multiformats.cid, multiformats.multihash, multiformats_available, multiformatsunavailableerror, multiformatsunavailableerror init, multiformatsunavailableerror.__init__, profilecontradiction, profilecontradiction to dict, profilecontradiction.to_dict, profilecontradictionkind, profiles are interchangeable, profiles_are_interchangeable, provider available
- AST symbol scope: file
- Merge key: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-content_identity_bridge
- Merge family: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/content_identity_bridge.py:241 for SCA-G015. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-164-codebase-scan-ff65e1bdaf7e.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.

## SCA-165 Resolve validation retry-budget failure for SCA-120

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: SCA-021, SCA-051, SCA-061, SCA-070, SCA-090
- Outputs: data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md, data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery
- Validation: test -f /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery/2026-07-29-sca-165-sca-120-retry-budget.md
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in SCA-120. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery/2026-07-29-sca-165-sca-120-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release SCA-120 from strategy blocked_tasks.

## SCA-166 Recover healthy whole-tree semantic coverage

- Status: completed
- Priority: P0
- Track: analyzer-health
- Depends on: SCA-020, SCA-021, SCA-120
- Goal id: SCA-G166
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/polyglot_ast_health.py, external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_health.py, data/agent_supervisor/swissknife_contract_assurance/analyzer_health/report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_health.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/analyzer-health
- Parallel lane: sca-analyzer-health
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/polyglot_ast_health.py, external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_health.py, data/agent_supervisor/swissknife_contract_assurance/analyzer_health/report.json
- Interfaces: PolyglotASTProvider@1, AnalyzerHealth@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Preserve protected-source, symlink, byte, file-count, memory, and timeout bounds; never convert a parse failure into fabricated success.
- Preconditions: Current whole-tree baseline exposes path-level parser outcomes.
- Effects: Clusters failures by language/reason/parser identity, repairs real parser adapters, reruns canaries, and emits a content-addressed health report.
- Evidence subset: Parser-eligible disposition IDs, bounded failure samples, parser/toolchain CIDs
- Acceptance: Every eligible path has success or a typed bounded failure; JS/TS/JSX/TSX/CJS/MJS authority comes from a real parser; parse health is within reviewed per-language thresholds or remains a completion blocker; no model sees source bodies.

## SCA-167 Enforce symbolic-only tasks and bounded Grok/Codex routing

- Status: completed
- Priority: P0
- Track: provider-policy
- Depends on: SCA-100, SCA-110, SCA-111
- Goal id: SCA-G167
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/task_execution_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_task_execution_policy.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_task_execution_policy.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/provider-policy
- Parallel lane: sca-provider-policy
- Resource class: cpu-medium
- Resource stage: runtime
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/task_execution_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_task_execution_policy.py
- Interfaces: TaskExecutionPolicy@1, ImplementationProviderRouter@1, CodeEditPacket
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Extend the existing daemon/router boundary; do not create a second implementation loop or let a provider set proof/task/goal status.
- Preconditions: Existing CodeEditPacket and provider router conformance tests pass.
- Effects: Compiles task metadata into deterministic-local or bounded-provider permits and records executable identity, call count, prompt bounds, fallback/review, and admission receipts.
- Evidence subset: Task CID, execution mode, packet CID, provider capability/quota and context policy
- Acceptance: Deterministic-only tasks can run only typed allowlisted local operations and record zero model calls; task context metadata is a hard limit; Grok implements before independent Codex review; labels cannot silently select another executable; quota/failure defers safely.

## SCA-168 Bind canonical SwissKnife snapshot authority

- Status: completed
- Priority: P0
- Track: snapshot-authority
- Depends on: SCA-010, SCA-167
- Goal id: SCA-G168
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_authority.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py, data/agent_supervisor/swissknife_contract_assurance/state/snapshot_authority.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/snapshot-authority
- Parallel lane: sca-snapshot-authority
- Resource class: cpu-medium
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_authority.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py, data/agent_supervisor/swissknife_contract_assurance/state/snapshot_authority.json
- Interfaces: RepositoryAuthority@1, RepositorySnapshot@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Report and queue freshness work only; do not fetch, reset, merge, update a gitlink, or rewrite either checkout under this task.
- Preconditions: Exact integration gitlink snapshot and host checkout, when present, are readable.
- Effects: Records origin/commit/tree/ancestry/dirty overlay/gitlink/path-population identities and selects one reviewed authority for analysis.
- Evidence subset: Git object IDs, canonical path manifests, scope policy and content-identity profile
- Acceptance: Each checkout is independently CID-bound; the integration gitlink is the default program authority unless reviewed evidence changes it; divergence creates typed freshness work; cache/proof/artifact joins across authority roots fail closed.

## SCA-170 Build the versioned runtime-component catalog

- Status: completed
- Priority: P0
- Track: runtime-catalog
- Depends on: SCA-040, SCA-042, SCA-167, SCA-168
- Goal id: SCA-G170
- Outputs: config/swissknife_runtime_contract_scope.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_component_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-catalog
- Parallel lane: sca-runtime-catalog
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: config/swissknife_runtime_contract_scope.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_component_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py
- Interfaces: RuntimeComponentCatalog@1, McpContractCatalog@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Extend the existing catalog and identity bridge; docs, mocks, generated aliases, and narrow fixtures remain non-authoritative evidence.
- Preconditions: Expected and actual MCP catalogs and content identity profiles exist.
- Effects: Names canonical/adapter/legacy/contradictory entrypoints, schemas, routes, state roots, policy boundaries, and package ownership for four components.
- Evidence subset: SwissKnife and provider manifests, descriptor/route/registration AST facts, exact Git identities
- Acceptance: Model server, orchestrator, scheduler, and supervisor roots are complete and CID-bound; alternate implementations have typed authority; connector/launcher/health/list/call routes normalize without name-only joins; missing/duplicate routes fail closed.

## SCA-171 Extract model-server route and inference contracts

- Status: completed
- Priority: P0
- Track: model-server
- Depends on: SCA-170
- Goal id: SCA-G171
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/model_server_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_model_server_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_model_server_contract_extractor.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-model-server
- Parallel lane: sca-model-server
- Allow concurrent with: SCA-172, SCA-173, SCA-174
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/model_server_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_model_server_contract_extractor.py
- Interfaces: ModelServerContractCatalog@1, RuntimeComponentCatalog@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Do not select Flask, integrated dashboard, MCP++ trio, compatibility adapter, or legacy AI server by availability alone.
- Preconditions: Runtime catalog fixes exact component and snapshot identities.
- Effects: Extracts launcher/route/schema/auth/queue/batch/cache/model/backend/stream/error/health/provenance premises from consumer through handlers.
- Evidence subset: SwissKnife connector/capability registry/compat adapter and accelerator HF/MCP/native-model-tool surfaces
- Acceptance: Launcher and connector route tables agree or refute with exact counterexamples; invocation uses canonical JSON-RPC or reviewed adapter; model ID/revision/parameters and result/error/provenance are preserved; synthesized aliases and mock/degraded transports cannot prove success.

## SCA-172 Extract orchestrator lifecycle contracts

- Status: completed
- Priority: P0
- Track: orchestrator
- Depends on: SCA-170
- Goal id: SCA-G172
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-orchestrator
- Parallel lane: sca-orchestrator
- Allow concurrent with: SCA-171, SCA-173, SCA-174
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Interfaces: OrchestratorContractCatalog@1, RuntimeComponentCatalog@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Runtime traces are observations; broad exception/silent-pass paths stay explicit and cannot be interpreted as success.
- Preconditions: Runtime catalog fixes exact component and snapshot identities.
- Effects: Extracts admission, ownership, dispatch, retry, cancellation, timeout, result, receipt, datasets-adapter, and failure state machines.
- Evidence subset: TaskOrchestrator, P2P service/client, datasets integration, MCP tools, SwissKnife bindings
- Acceptance: All lifecycle transitions carry pre/post/error states and spans; retries/cancellation/results are idempotent or refuted; swallowed failures are visible; direct package calls are distinguished from mandatory MCP++ paths.

## SCA-173 Resolve scheduler authority and concurrency contracts

- Status: completed
- Priority: P0
- Track: scheduler
- Depends on: SCA-170
- Goal id: SCA-G173
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/scheduler_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_scheduler_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_scheduler_contract_extractor.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-scheduler
- Parallel lane: sca-scheduler
- Allow concurrent with: SCA-171, SCA-172, SCA-174
- Resource class: cpu-proof-solver
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/scheduler_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_scheduler_contract_extractor.py
- Interfaces: SchedulerContractCatalog@1, RuntimeComponentCatalog@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Shared names do not prove scheduler equivalence; every concurrency claim binds the implementation/version and modeled bound.
- Preconditions: Runtime catalog fixes exact component and snapshot identities.
- Effects: Relates deterministic, legacy workflow, MCP++ workflow/risk, resource, provider, and validation/proof schedulers and emits ownership/clock/queue/lease/fence invariants.
- Evidence subset: Scheduler AST/control facts, lease DB/event receipts, bounded interleaving fixtures
- Acceptance: Each scheduler is canonical, a proved adapter, legacy-only, or contradictory; lease and fence checks dominate effects; bounded interleavings conserve admitted work and terminal outcomes; retry/cancel/crash paths cannot duplicate or lose tasks.

## SCA-174 Extract native agent-supervisor control and goal/task contracts

- Status: completed
- Priority: P0
- Track: agent-supervisor
- Depends on: SCA-170
- Goal id: SCA-G174
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/supervisor_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_contract_extractor.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-agent-supervisor
- Parallel lane: sca-agent-supervisor
- Allow concurrent with: SCA-171, SCA-172, SCA-173
- Resource class: cpu-large
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/supervisor_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_contract_extractor.py
- Interfaces: SupervisorContractCatalog@1, SupervisorControlService, ObjectiveGraph
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Generic workflow/data/storage tools are not substitutes for native supervisor operation identities; governed effects require preview/permit/receipt.
- Preconditions: Runtime catalog and native supervisor operation manifest are available.
- Effects: Maps goal/subgoal/task, status/health, lane, bundle, event, receipt, cache, lifecycle, rescue, refinement, and refill contracts from SwissKnife to native handlers.
- Evidence subset: SwissKnife console gateway/schema/backend selector and native agent_supervisor tool/control manifests
- Acceptance: Every SwissKnife capability maps to one exact native `agent_supervisor_*` request/result/dispatcher/function identity or refutes; generic proxy selection is rejected; completion requires current child/evidence/health/exhaustion closure; mutation paths are policy dominated.

## SCA-175 Compile runtime state-machine obligations

- Status: completed
- Priority: P0
- Track: runtime-proof
- Depends on: SCA-060, SCA-061, SCA-171, SCA-172, SCA-173, SCA-174
- Goal id: SCA-G175
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/runtime_contract_obligations.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_obligations.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_obligations.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-obligations
- Parallel lane: sca-runtime-obligations
- Resource class: cpu-proof-solver
- Resource stage: proof
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/runtime_contract_obligations.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_obligations.py
- Interfaces: RuntimeContractObligation@1, CodeProofObligation, ipfs_datasets logic IR
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Use trusted deterministic graph/schema decisions or hammer/kernel reconstruction; solver SAT, legacy success enums, strings, traces, and LLM claims are never theorem authority.
- Preconditions: Four component catalogs have stable source and behavior IDs.
- Effects: Compiles lifecycle, schema, reachability, dominance, temporal, conservation, idempotence, and bounded concurrency claims into canonical obligations.
- Evidence subset: Exact component catalogs, mandatory edge closure, state machines, policy/toolchain/capability roots
- Acceptance: Claims bind snapshot/catalog/policy/toolchain/bounds and all premises; proved/refuted/unknown/unsupported/timed-out remain distinct; unsupported program semantics stay unknown; compact counterexamples identify the failed edge/transition/invariant.

## SCA-176 Prove exact cross-component MCP++ mediation

- Status: completed
- Priority: P0
- Track: runtime-invocation
- Depends on: SCA-050, SCA-051, SCA-175
- Goal id: SCA-G175
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_mcp_invocation_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_mcp_invocation_trace.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_mcp_invocation_trace.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-invocation
- Parallel lane: sca-runtime-invocation
- Resource class: cpu-proof-solver
- Resource stage: proof
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_mcp_invocation_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_mcp_invocation_trace.py
- Interfaces: RuntimeMcpInvocationTrace@1, DispatchPipeline, InterfaceDescriptor
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Post-hoc trace and descriptor name matches cannot prove the dispatch pipeline mediated a call; mandatory unknown/dynamic segments block proof.
- Preconditions: Runtime obligations and normalized connector/provider routes exist.
- Effects: Closes health/discovery/call/policy/transport/handler/implementation paths and records descriptor, behavior, event, and receipt identities.
- Evidence subset: Mandatory typed closure from SwissKnife capability through MCP++ to real package function
- Acceptance: Primary `tools_dispatch` and HTTP paths use the reviewed pipeline or refute; route/schema/function identities match; direct fetch/import/compatibility bypasses are visible; native supervisor operations and all three packages receive exact terminal states.

## SCA-177 Add runtime drift and vulnerability rules

- Status: completed
- Priority: P0
- Track: runtime-security
- Depends on: SCA-091, SCA-175, SCA-176
- Goal id: SCA-G176
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_contract_vulnerability_rules.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_vulnerability_rules.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_vulnerability_rules.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-security
- Parallel lane: sca-runtime-security
- Resource class: cpu-proof-solver
- Resource stage: analysis
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_contract_vulnerability_rules.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_vulnerability_rules.py
- Interfaces: RuntimeContractVulnerabilityRules@1, ContractMismatchAnalyzer@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Proof state, severity, exploitability, CWE/OWASP/CAPEC mapping, and remediation priority remain separate; heuristics only nominate candidates.
- Preconditions: Runtime proofs emit typed counterexamples and unknowns.
- Effects: Classifies route/launcher mismatch, direct dispatch, policy/auth/lease bypass, schema confusion, stale replay, duplicate/lost work, swallowed failure, mock/degraded evidence, false release GO, and provider-policy bypass.
- Evidence subset: Deterministic rule premises and exact runtime counterexamples
- Acceptance: Every classification is reproducible with required premises; unknown behavior is not mislabeled vulnerable; positive/negative/near-miss fixtures pass; seeded mandatory safety failures are detected with zero false authoritative admissions.

## SCA-178 Project runtime findings into the accelerator repair board

- Status: active
- Priority: P0
- Track: runtime-triage
- Depends on: SCA-100, SCA-101, SCA-121, SCA-177
- Goal id: SCA-G176
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_mismatch_refinery.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_mismatch_refinery.py, data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md, data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_triage.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_mismatch_refinery.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-triage
- Parallel lane: sca-runtime-triage
- Resource class: cpu-medium
- Resource stage: planning
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_mismatch_refinery.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_mismatch_refinery.py, data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md, data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_triage.json
- Interfaces: RuntimeContractMismatchRefinery@1, CodeEditPacket
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Append to the existing accelerator board after baseline triage; preserve non-accelerator owners and historical/stale evidence.
- Preconditions: Current runtime counterexamples pass analyzer-health and admission policy.
- Effects: Clusters exact affected symbols/contracts, deduplicates identities, and emits minimal read/write/validate/re-proof packets.
- Evidence subset: Runtime finding/obligation/receipt CIDs and bounded mandatory graph slice
- Acceptance: One current counterexample impact cluster yields one task; packets include no repository corpus, exact paths/spans/symbols, expected postcondition, deterministic validation and re-proof; unsupported/stale/unknown-only findings are not implementation-ready.

## SCA-179 Integrate runtime contract discovery into continuous refill

- Status: active
- Priority: P0
- Track: runtime-refill
- Depends on: SCA-110, SCA-167, SCA-178
- Goal id: SCA-G176
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_assurance_refill.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_assurance_refill.py, data/agent_supervisor/swissknife_contract_assurance/state/runtime_refill_metrics.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_assurance_refill.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-refill
- Parallel lane: sca-runtime-refill
- Resource class: cpu-large
- Resource stage: runtime
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_assurance_refill.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_assurance_refill.py, data/agent_supervisor/swissknife_contract_assurance/state/runtime_refill_metrics.json
- Interfaces: RuntimeContractAssuranceRefill@1, ObjectiveGraph, ProofScopeIndex
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Refill only from admitted current evidence; preserve stale receipts, enforce cooldown/open-work/depth/breadth bounds, and never certify exhaustion from unhealthy analyzers.
- Preconditions: Runtime refinery and task execution policy pass conformance.
- Effects: Invalidates changed component dependencies, re-extracts/re-proves affected contracts, and appends/reopens/deduplicates bounded goal-backed tasks.
- Evidence subset: Snapshot delta, reverse proof scope, runtime component/goal lineage and analyzer health
- Acceptance: No-op scans make zero provider calls; one-symbol/route/schema/policy changes update all and only dependents; crashes are idempotent; task storms and cross-component duplicate repairs are bounded; new findings refill the correct subgoal.

## SCA-180 Run the initialized four-component symbolic baseline

- Status: active
- Priority: P0
- Track: runtime-baseline
- Depends on: SCA-166, SCA-176, SCA-177, SCA-179
- Goal id: SCA-G176
- Outputs: data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/contracts.json, data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/summary.md
- Validation: python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components --shadow
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-baseline
- Parallel lane: sca-runtime-baseline
- Resource class: cpu-proof-solver
- Resource stage: analysis
- Implementation timeout seconds: 21600
- Predicted files: data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/contracts.json, data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/summary.md
- Interfaces: RepositoryIndexer@1, RuntimeContractAssuranceRefill@1
- Context budget tokens: 2048
- Provider role: deterministic-only
- Proposal artifact envelope: {"schema":"ipfs_accelerate_py/agent-supervisor/task-artifact-envelope@1","paths":["data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/coverage.json","data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/contracts.json","data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/findings.json","data/agent_supervisor/swissknife_contract_assurance/baseline/runtime_components/summary.md"],"max_file_bytes":4000000,"max_patch_bytes":12000000,"max_output_bytes":24000000}
- Conflict policy: No source/task mutation; baseline health and unknowns cannot be rewritten to manufacture a clean result.
- Preconditions: Initialized pinned SwissKnife and provider checkouts, healthy parser policy, runtime proof/refill pipeline.
- Effects: Runs exact inventory/index/catalog/trace/proof/cache/classification and seeds current accelerator repair evidence with zero model calls.
- Evidence subset: Current recursive Git/submodule/overlay, scope, parser, catalog, policy, toolchain and capability roots
- Acceptance: All 5,771-or-current tracked paths have dispositions and healthy supported AST coverage; every runtime operation has proved/refuted/unknown/unsupported/stale status; real MCP++ binding gaps generate findings; proof/cache roots reproduce; model call count is zero.

## SCA-181 Evaluate runtime mutations, ZK receipt attestation, and release aggregation

- Status: active
- Priority: P0
- Track: runtime-evaluation
- Depends on: SCA-081, SCA-150, SCA-180
- Goal id: SCA-G176
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_evaluation.py, data/agent_supervisor/swissknife_contract_assurance/evaluation/runtime_report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_evaluation.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/runtime-evaluation
- Parallel lane: sca-runtime-evaluation
- Resource class: cpu-proof-solver
- Resource stage: evaluation
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_evaluation.py, data/agent_supervisor/swissknife_contract_assurance/evaluation/runtime_report.json
- Interfaces: RuntimeContractEvaluation@1, ProofAttestation
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Conflict policy: Held-out mutations and private witnesses stay outside provider context; mock/narrow/stale child evidence cannot produce a release GO.
- Preconditions: Current four-component baseline and real/simulated ZK capability report exist.
- Effects: Seeds route/launcher, native-supervisor binding, scheduler split, state/lease, policy, cache, mock evidence, stale release root, forged receipt, and ZK replay mutations.
- Evidence subset: Preregistered held-out fixtures, current release ledgers, exact proof/attestation public inputs
- Acceptance: All mandatory held-out failures are detected or explicitly unsupported; zero false authoritative admissions; release aggregation fails closed on no-go/stale/mock/degraded children; simulated ZK never attests; real ZK, when available, proves only the approved verified-receipt predicate and exact roots.

## SCA-182 Close objective gap: Runtime drift refinery and continuous refill

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: runtime-refill
- Depends on: SCA-177, SCA-178, SCA-179
- Blocked reason: Superseded by the existing canonical runtime drift, repair-board, and refill tasks SCA-177 through SCA-179.
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_contract_vulnerability_rules.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_mismatch_refinery.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_assurance_refill.py, data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_refill.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-182-objective-gap-fef8acf47c25.md
- Bundle: swissknife/contract-assurance/runtime-refill
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-runtime-refill.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G090, SCA-G091, SCA-G101, SCA-G110, SCA-G175
- Graph depth: 20
- Objective heap index: 2
- Parallel lane: swissknife/contract-assurance/runtime-refill
- Conflict policy: Security severity and exploitability remain separate from proof state; heuristics can nominate work but cannot label a vulnerability proved.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_contract_vulnerability_rules.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_mismatch_refinery.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/objectives/runtime_contract_assurance_refill.py, data/agent_supervisor/swissknife_contract_assurance/generated/ipfs_accelerate_contract_repairs.todo.md
- Changed paths:
- AST symbols: SCAEV176REFILL
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G176
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/443a4fdece623f4d049f5b46c31a4fbe7ba28d6e0406232b4cb6a5d14c87b96c
- Canonical task CID: baguqeeraiq5e7xwomi7u2be7lndmggspxz52fdloaqdcgk2mw2s5ctehxfwa
- Semantic identity: objective-evidence-obligation/v1/1104c36ae34e113e1df4f0a59a24185a0ea1890628e3477d19733d85715995ef
- Acceptance subset: Route mismatch, policy bypass, direct dispatch, schema confusion, stale replay, lease/fence violation, duplicate/lost work, mock/degraded evidence, false release GO, and provider-context bypass have typed rules, one current counterexample cluster yields one bounded task, fixes close only after current-tree reindex and re-proof.
- Preconditions: objective goal SCA-G176 is schedulable
- Effects: satisfy evidence requirement: SCAEV176REFILL
- Evidence subset: SCAEV176REFILL
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G176
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/1104c36ae34e113e1df4f0a59a24185a0ea1890628e3477d19733d85715995ef
- Missing evidence: SCAEV176REFILL
- Embedding query: Classify current runtime counterexamples, append deduplicated accelerator bug/vulnerability tasks with minimal edit packets, and continuously reopen or refill them from exact changed dependency closures.
- AST query: SCAEV176REFILL
- Surplus group: objective/SCA-G176
- Merge key: ecaf8ea8784894e2
- Merge family: objective/SCA-G176
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 01ce91069a53b38a
- Acceptance: Objective scan filed this gap for SCA-G176. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-182-objective-gap-fef8acf47c25.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV176REFILL), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-183 Close objective gap: Shadow baseline scan and triage

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: baseline
- Depends on: SCA-120
- Blocked reason: Superseded by the existing canonical baseline task SCA-120.
- Outputs: data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md
- Validation: python3 external/ipfs_accelerate/scripts/index_repository_contracts.py --repo-root . --scope-config config/swissknife_symbolic_contract_scope.json --output-root data/agent_supervisor/swissknife_contract_assurance/baseline --shadow
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-183-objective-gap-eccaa5cd8157.md
- Bundle: swissknife/contract-assurance/baseline
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-baseline.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G021, SCA-G051, SCA-G061, SCA-G070, SCA-G090
- Graph depth: 11
- Objective heap index: 6
- Parallel lane: swissknife/contract-assurance/baseline
- Conflict policy: Baseline artifacts are generated evidence and cannot rewrite source or task status directly.
- Predicted files: data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md
- Changed paths:
- AST symbols: SCAEV120BASE
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G120
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/66d80fc4f1162031c08ea32626effee3338b9b210079677b189800dd058cbf01
- Canonical task CID: baguqeeram3ma7rhrcyqddqeoumtcn3764mzyxgzbab4wo6yytaan2bmmx4aq
- Semantic identity: objective-evidence-obligation/v1/1e716599f49059c193b5ab20e5500db0727f47c7fed0ced57730e71e924e7a94
- Acceptance subset: Exact snapshot and capability report recorded, all tracked paths disposed, no mutation, findings distinguish proved/refuted/unknown/unsupported/stale, no authority promotion from optional providers.
- Preconditions: objective goal SCA-G120 is schedulable
- Effects: satisfy evidence requirement: SCAEV120BASE
- Evidence subset: SCAEV120BASE
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G120
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/1e716599f49059c193b5ab20e5500db0727f47c7fed0ced57730e71e924e7a94
- Missing evidence: SCAEV120BASE
- Embedding query: Run a no-mutation baseline over the current SwissKnife snapshot, publish coverage/analyzer health, contract status, proof/cache outcomes, and prioritized accelerator findings.
- AST query: SCAEV120BASE
- Surplus group: objective/SCA-G120
- Merge key: ee8ebd8a95d0a0a3
- Merge family: objective/SCA-G120
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: ccb58e560df563aa
- Acceptance: Objective scan filed this gap for SCA-G120. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-183-objective-gap-eccaa5cd8157.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV120BASE), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-184 Close objective gap: Whole-tree analyzer health recovery

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: analyzer-health
- Depends on: SCA-166
- Blocked reason: Superseded by the existing canonical analyzer-health task SCA-166.
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/polyglot_ast_health.py, external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_health.py, data/agent_supervisor/swissknife_contract_assurance/analyzer_health/report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_health.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-184-objective-gap-c5c8046c1e56.md
- Bundle: swissknife/contract-assurance/analyzer-health
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-analyzer-health.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G020, SCA-G021, SCA-G120
- Graph depth: 12
- Objective heap index: 7
- Parallel lane: swissknife/contract-assurance/analyzer-health
- Conflict policy: Preserve hard bounds and protected-source policy; a typed unsupported artifact is safer than an unbounded parser or fabricated AST.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/polyglot_ast_health.py, external/ipfs_accelerate/test/api/test_agent_supervisor_polyglot_ast_health.py, data/agent_supervisor/swissknife_contract_assurance/analyzer_health/report.json
- Changed paths:
- AST symbols: SCAEV166HEALTH
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G166
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/43617db0dbf5168f6446e8a7c27578d60f5594c17bcaf8cf77b30f724d502823
- Canonical task CID: baguqeerainqx3mg36uli6zcg5ct4e5ly2yhvlfgbppfprt3xwmhxetkqfarq
- Semantic identity: objective-evidence-obligation/v1/2145f157338394d083fe2cf3732af7c55a7d8bccafa7e0147914bce6dc878022
- Acceptance subset: Every parser-eligible path has a successful AST record or typed bounded failure, JS/TS/JSX/TSX/CJS/MJS use a real parser rather than regex authority, per-language health thresholds and canaries pass or block completion, no source body enters model context.
- Preconditions: objective goal SCA-G166 is schedulable
- Effects: satisfy evidence requirement: SCAEV166HEALTH
- Evidence subset: SCAEV166HEALTH
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G166
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/2145f157338394d083fe2cf3732af7c55a7d8bccafa7e0147914bce6dc878022
- Missing evidence: SCAEV166HEALTH
- Embedding query: Turn the complete SwissKnife path inventory into healthy semantic coverage by classifying and repairing the current parser failures without weakening file, byte, timeout, symlink, or protected-source bounds.
- AST query: SCAEV166HEALTH
- Surplus group: objective/SCA-G166
- Merge key: f7f2a45618fc3da3
- Merge family: objective/SCA-G166
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 2d0ff0cfe424c09f
- Acceptance: Objective scan filed this gap for SCA-G166. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-184-objective-gap-c5c8046c1e56.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV166HEALTH), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-185 Close objective gap: Canonical SwissKnife snapshot authority

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: snapshot-authority
- Depends on: SCA-168
- Blocked reason: Superseded by the existing canonical snapshot-authority task SCA-168.
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_authority.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py, data/agent_supervisor/swissknife_contract_assurance/state/snapshot_authority.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-185-objective-gap-afdb51353fa4.md
- Bundle: swissknife/contract-assurance/snapshot-authority
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-snapshot-authority.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G010, SCA-G167
- Graph depth: 16
- Objective heap index: 9
- Parallel lane: swissknife/contract-assurance/snapshot-authority
- Conflict policy: This goal may report or queue a gitlink update but cannot fetch, reset, merge, or rewrite a checkout without separately authorized work.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/repository_authority.py, external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py, data/agent_supervisor/swissknife_contract_assurance/state/snapshot_authority.json
- Changed paths:
- AST symbols: SCAEV168AUTH
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G168
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/ff3ccce9c24588dd3df4cbc356473744430588f885c88861fd98109a096c25fd
- Canonical task CID: baguqeera746mz2ociwen2ppuzpbvmrzxirbqlchyqxeiqyp5taijuclmex6q
- Semantic identity: objective-evidence-obligation/v1/4c192cbf4243bde1b06273f0913400b72ed1157300c7135d565d0978567bc521
- Acceptance subset: Origin, commit, tree, ancestry, dirty overlay, gitlink, and tracked-path population are CID-bound for each checkout, exactly one authority is selected by reviewed policy, newer/divergent trees create typed freshness work, artifacts from different authorities never share cache or proof identity.
- Preconditions: objective goal SCA-G168 is schedulable
- Effects: satisfy evidence requirement: SCAEV168AUTH
- Evidence subset: SCAEV168AUTH
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G168
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/4c192cbf4243bde1b06273f0913400b72ed1157300c7135d565d0978567bc521
- Missing evidence: SCAEV168AUTH
- Embedding query: Bind the integration gitlink and any standalone SwissKnife checkout as distinct repository identities, select the reviewed analysis authority, and prevent mixed-tree coverage, contract, proof, or completion claims.
- AST query: SCAEV168AUTH
- Surplus group: objective/SCA-G168
- Merge key: 096604543cc93105
- Merge family: objective/SCA-G168
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 6fee934bd7638ef9
- Acceptance: Objective scan filed this gap for SCA-G168. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-185-objective-gap-afdb51353fa4.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV168AUTH), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-186 Close objective gap: Versioned runtime-component contract catalog

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: runtime-catalog
- Depends on: SCA-170
- Blocked reason: Superseded by the existing canonical runtime-catalog task SCA-170.
- Outputs: config/swissknife_runtime_contract_scope.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_component_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-186-objective-gap-982d6a71edca.md
- Bundle: swissknife/contract-assurance/runtime-catalog
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-runtime-catalog.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G040, SCA-G042, SCA-G168
- Graph depth: 17
- Objective heap index: 10
- Parallel lane: swissknife/contract-assurance/runtime-catalog
- Conflict policy: Extend McpContractCatalog with a typed runtime view; documentation and fixture aliases are candidate evidence only.
- Predicted files: config/swissknife_runtime_contract_scope.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_component_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py
- Changed paths:
- AST symbols: SCAEV170CAT
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G170
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/4e41ff670fb8ffaf669e727e496856b304fce469ee8020cac5de37718daefee0
- Canonical task CID: baguqeerajza76zypxd726zu6oj7es2cwwmcpzzdj52acbswf3y3xddno73qa
- Semantic identity: objective-evidence-obligation/v1/d09b9d281dbea9501ddc6fe66e54b9c1e4a9b1aa3d2c7b14505e9f410c487521
- Acceptance subset: Four component roots are complete and CID-bound, alternate servers/schedulers/registries are canonical, versioned-adapter, legacy, or contradiction, SwissKnife launch/health/list/call routes and actual package routes are normalized without name-only joins.
- Preconditions: objective goal SCA-G170 is schedulable
- Effects: satisfy evidence requirement: SCAEV170CAT
- Evidence subset: SCAEV170CAT
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G170
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/d09b9d281dbea9501ddc6fe66e54b9c1e4a9b1aa3d2c7b14505e9f410c487521
- Missing evidence: SCAEV170CAT
- Embedding query: Publish one content-addressed manifest for canonical and compatibility entrypoints, schemas, transports, state stores, policies, and package ownership of the model server, orchestrator, scheduler, and agent supervisor.
- AST query: SCAEV170CAT
- Surplus group: objective/SCA-G170
- Merge key: 0e1535faa8464b05
- Merge family: objective/SCA-G170
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 47855a2441f34a9f
- Acceptance: Objective scan filed this gap for SCA-G170. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-186-objective-gap-982d6a71edca.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV170CAT), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-187 Close objective gap: Cross-component state-machine and MCP++ proofs

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: runtime-proof
- Depends on: SCA-175, SCA-176
- Blocked reason: Superseded by the existing canonical obligation and MCP++ mediation tasks SCA-175 and SCA-176.
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/runtime_contract_obligations.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_mcp_invocation_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_proofs.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_proofs.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-187-objective-gap-16493c8193a9.md
- Bundle: swissknife/contract-assurance/runtime-proof
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-runtime-proof.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G171, SCA-G172, SCA-G173, SCA-G174, SCA-G060, SCA-G061
- Graph depth: 19
- Objective heap index: 11
- Parallel lane: swissknife/contract-assurance/runtime-proof
- Conflict policy: ZK membership or event-root possession is not function-call correctness; solver SAT is not proof; mandatory unknown edges block authority.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/runtime_contract_obligations.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_mcp_invocation_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_contract_proofs.py
- Changed paths:
- AST symbols: SCAEV175PROOF
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G175
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/e74d4f0e5ccd0cc6adc7e9d0620207602b48ee6e3c9372ffa79be51cb005f641
- Canonical task CID: baguqeera45gu6ds4zugmnloh5higeaqhmavur3tohsjxf75htpsrzmaf6zaq
- Semantic identity: objective-evidence-obligation/v1/caca9832c7e4be9fe20453a9beeb2fadf2e9274a081b34e983a0ffedd1e3be0b
- Acceptance subset: Mandatory dispatch closes through the configured MCP++ pipeline rather than direct handler invocation, interface and behavior IDs bind every path, unsupported semantics remain unknown, solver candidates require trusted deterministic classification or kernel reconstruction, optional ZK attests only verified receipt predicates.
- Preconditions: objective goal SCA-G175 is schedulable
- Effects: satisfy evidence requirement: SCAEV175PROOF
- Evidence subset: SCAEV175PROOF
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G175
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/caca9832c7e4be9fe20453a9beeb2fadf2e9274a081b34e983a0ffedd1e3be0b
- Missing evidence: SCAEV175PROOF
- Embedding query: Compile runtime state machines and cross-component call paths into typed graph, schema, deontic, temporal, and bounded concurrency obligations and prove or refute the supported fragments.
- AST query: SCAEV175PROOF
- Surplus group: objective/SCA-G175
- Merge key: 464ed4e8ccd10ca1
- Merge family: objective/SCA-G175
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: e7e2a7d8ca075fdd
- Acceptance: Objective scan filed this gap for SCA-G175. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-187-objective-gap-16493c8193a9.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV175PROOF), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-188 Close objective gap: Symbolic-only execution and bounded provider enforcement

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: provider-policy
- Depends on:
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/task_execution_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_task_execution_policy.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_task_execution_policy.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-188-objective-gap-f76f9b398d94.md
- Bundle: swissknife/contract-assurance/provider-policy
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-provider-policy.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G100, SCA-G110, SCA-G111
- Graph depth: 15
- Objective heap index: 27
- Parallel lane: swissknife/contract-assurance/provider-policy
- Conflict policy: Integrate with the existing implementation daemon and CodeEditPacket router; do not add a second task runner or grant model output completion authority.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/task_execution_policy.py, external/ipfs_accelerate/test/api/test_agent_supervisor_task_execution_policy.py
- Changed paths:
- AST symbols: SCAEV167ROUTE
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G167
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/d7132a6d9431c86559773f116fef83b1ea10f22be762026b00c7c1ff2b120920
- Canonical task CID: baguqeera24jsu3mughegkwlxh4iw734dwhvbb4rl45rae2yay7a76kysbeqa
- Semantic identity: objective-evidence-obligation/v1/c07536cb9461db13f148f6a4e5365f0c52c95a89fd6cc79913bbd895ba3bda61
- Acceptance subset: Deterministic-only tasks run typed allowlisted local operations with zero provider calls, task context budgets are hard limits, Grok/Codex executable identity, quota, fallback, review order, prompt bytes/tokens, and admission are receipted, labels alone cannot select or upgrade a provider result.
- Preconditions: objective goal SCA-G167 is schedulable
- Effects: satisfy evidence requirement: SCAEV167ROUTE
- Evidence subset: SCAEV167ROUTE
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G167
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/c07536cb9461db13f148f6a4e5365f0c52c95a89fd6cc79913bbd895ba3bda61
- Missing evidence: SCAEV167ROUTE
- Embedding query: Make task execution mode and context limits executable supervisor policy so deterministic-only tasks cannot invoke a model and edit packets route through bounded Grok implementation followed by independent Codex review.
- AST query: SCAEV167ROUTE
- Surplus group: objective/SCA-G167
- Merge key: 936318b53ed9dd80
- Merge family: objective/SCA-G167
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 20df32ef74f92e18
- Acceptance: Objective scan filed this gap for SCA-G167. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-188-objective-gap-f76f9b398d94.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV167ROUTE), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-189 Close objective gap: Model-server route and inference contracts

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: model-server
- Depends on: SCA-171
- Blocked reason: Superseded by the existing canonical model-server contract task SCA-171.
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/model_server_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_model_server_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_model_server_contract_extractor.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-189-objective-gap-93ef74c93aa3.md
- Bundle: swissknife/contract-assurance/runtime-model-server
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-runtime-model-server.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G170
- Graph depth: 18
- Objective heap index: 28
- Parallel lane: swissknife/contract-assurance/runtime-model-server
- Conflict policy: Do not choose a server by availability; contradictions remain open until one reviewed canonical route or versioned adapter is proved.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/model_server_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_model_server_contract_extractor.py
- Changed paths:
- AST symbols: SCAEV171MODEL
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G171
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/4c41cf5f7f9e5155974f611818cca3f675c43f4c3dc154e34781b7b9c5ab25b7
- Canonical task CID: baguqeerajra46x37tzivlf2pmembrtfd6z24ip2mhxavjy2hqg33trnlew3q
- Semantic identity: objective-evidence-obligation/v1/223f932bdb7430fe2f6a1d9ed58428f12c8549ae88058bc20d4f39865bfc0864
- Acceptance subset: Connector, capability registry, CLI launcher, Flask/integrated/MCP++ servers, compatibility adapter, and native model tools have exact route/schema/function identities, model revision and generation arguments are preserved, synthetic aliases and mock/degraded transports cannot prove reachability.
- Preconditions: objective goal SCA-G171 is schedulable
- Effects: satisfy evidence requirement: SCAEV171MODEL
- Evidence subset: SCAEV171MODEL
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G171
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/223f932bdb7430fe2f6a1d9ed58428f12c8549ae88058bc20d4f39865bfc0864
- Missing evidence: SCAEV171MODEL
- Embedding query: Extract expected and actual model-server route, schema, auth, queue, batching, cache, model-selection, backend, streaming, error, health, and provenance contracts from SwissKnife through MCP++ to accelerator handlers.
- AST query: SCAEV171MODEL
- Surplus group: objective/SCA-G171
- Merge key: c1579b2259e431eb
- Merge family: objective/SCA-G171
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 5e668de7414cf5f3
- Acceptance: Objective scan filed this gap for SCA-G171. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-189-objective-gap-93ef74c93aa3.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV171MODEL), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-190 Resolve implementation retry-budget failure for SCA-170

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: SCA-040, SCA-042, SCA-167, SCA-168
- Outputs: config/swissknife_runtime_contract_scope.json, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/runtime_component_catalog.py, external/ipfs_accelerate/test/api/test_agent_supervisor_runtime_component_catalog.py, data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery
- Validation: test -f /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery/2026-07-29-sca-190-sca-170-implementation-retry-budget.md
- Provider role: grok-implement, codex-review
- Context budget tokens: 4096
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in SCA-170. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery/2026-07-29-sca-190-sca-170-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release SCA-170 from strategy blocked_tasks.

## SCA-191 Close objective gap: Orchestrator lifecycle contracts

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Blocked reason: Superseded by the existing canonical orchestrator task SCA-172.
- Priority: P0
- Track: orchestrator
- Depends on:
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-191-objective-gap-5e23aeb52447.md
- Bundle: swissknife/contract-assurance/runtime-orchestrator
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-runtime-orchestrator.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G170
- Graph depth: 18
- Objective heap index: 29
- Parallel lane: swissknife/contract-assurance/runtime-orchestrator
- Conflict policy: Observed runtime traces are bounded observations; they do not close unmodeled transitions.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Changed paths:
- AST symbols: SCAEV172ORCH
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G172
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/0c32af1fedbc14e41e373a867a7a8cc8a24e3fe2b04ab11f4c797b521de42547
- Canonical task CID: baguqeerabqzk6h7nxqkoihrxhkdhu6umzcre4p7cwbflch2mpf5vehpeevdq
- Semantic identity: objective-evidence-obligation/v1/c1198d75c921af127ff8edc64cd35386a4650f22c7ef3eccee2e5cdc616cbf7e
- Acceptance subset: Every lifecycle edge has pre/post/error states and evidence spans, broad exception/silent-pass paths are visible, retry/cancel/result idempotence and receipt publication are proved, refuted, or unknown, direct package calls are distinguished from MCP++ mediation.
- Preconditions: objective goal SCA-G172 is schedulable
- Effects: satisfy evidence requirement: SCAEV172ORCH
- Evidence subset: SCAEV172ORCH
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G172
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/c1198d75c921af127ff8edc64cd35386a4650f22c7ef3eccee2e5cdc616cbf7e
- Missing evidence: SCAEV172ORCH
- Embedding query: Extract task-orchestrator admission, ownership, dispatch, state transition, retry, cancellation, timeout, result, receipt, and failure contracts across P2P services, datasets adapters, MCP tools, and SwissKnife.
- AST query: SCAEV172ORCH
- Surplus group: objective/SCA-G172
- Merge key: 5db57018c60265e4
- Merge family: objective/SCA-G172
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 14b71f12926db728
- Acceptance: Objective scan filed this gap for SCA-G172. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-191-objective-gap-5e23aeb52447.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV172ORCH), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-192 Close objective gap: Scheduler authority and concurrency contracts

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Blocked reason: Superseded by the existing canonical scheduler task SCA-173.
- Priority: P0
- Track: scheduler
- Depends on:
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/scheduler_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_scheduler_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_scheduler_contract_extractor.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-192-objective-gap-dce4088f2698.md
- Bundle: swissknife/contract-assurance/runtime-scheduler
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-runtime-scheduler.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G170
- Graph depth: 18
- Objective heap index: 30
- Parallel lane: swissknife/contract-assurance/runtime-scheduler
- Conflict policy: Do not infer equivalence from shared class or method names; concurrency claims bind the modeled bounds and scheduler version.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/scheduler_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_scheduler_contract_extractor.py
- Changed paths:
- AST symbols: SCAEV173SCHED
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G173
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/6ff8d5968d88f3a0afacf8fd319354b0336a389bb7b3bc402f74d361bcf28d6a
- Canonical task CID: baguqeeran74nlfunrdz2bl5m7d6tde2uwazwuoe3w6z3yqbpotjwdphsrvva
- Semantic identity: objective-evidence-obligation/v1/d2611f6900beb36fcf1624926cd9db769e8cc92e4cb9aa3709a9a8529f1c09d5
- Acceptance subset: Deterministic, legacy workflow, MCP++ workflow/risk, and supervisor resource/provider schedulers are related by proved equivalence, explicit adapter, or contradiction, lease/fence dominates effects, bounded interleavings conserve tasks and terminal outcomes.
- Preconditions: objective goal SCA-G173 is schedulable
- Effects: satisfy evidence requirement: SCAEV173SCHED
- Evidence subset: SCAEV173SCHED
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G173
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/d2611f6900beb36fcf1624926cd9db769e8cc92e4cb9aa3709a9a8529f1c09d5
- Missing evidence: SCAEV173SCHED
- Embedding query: Resolve scheduler authority and model deterministic ownership, clocks, queues, capacity, fairness, leases, fencing, backpressure, retry, cancellation, and crash recovery across every accelerator scheduler surface.
- AST query: SCAEV173SCHED
- Surplus group: objective/SCA-G173
- Merge key: de2b5aeb03c3fcac
- Merge family: objective/SCA-G173
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 8e0e852db03c20e6
- Acceptance: Objective scan filed this gap for SCA-G173. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-192-objective-gap-dce4088f2698.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV173SCHED), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-193 Close objective gap: Agent-supervisor control and goal/task contracts

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Blocked reason: Superseded by the existing canonical supervisor-contract task SCA-174.
- Priority: P0
- Track: agent-supervisor
- Depends on:
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/supervisor_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_contract_extractor.py
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_contract_extractor.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-193-objective-gap-15f69b5c871a.md
- Bundle: swissknife/contract-assurance/runtime-agent-supervisor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-runtime-agent-supervisor.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G170
- Graph depth: 18
- Objective heap index: 31
- Parallel lane: swissknife/contract-assurance/runtime-agent-supervisor
- Conflict policy: UI labels and generic backend ownership are not native-operation reachability; governed mutations require preview/permit/receipt paths.
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/supervisor_contract_extractor.py, external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_contract_extractor.py
- Changed paths:
- AST symbols: SCAEV174SUP
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G174
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/1433c79e413bbfea719984bd507eb5bd417380cccbedc9378bf5a3d750575cba
- Canonical task CID: baguqeeracqz4phsbho76u4mzqs6va7vvxvaxhagmzpw4sn4l6wr5oucxls5a
- Semantic identity: objective-evidence-obligation/v1/f24f9bb6475be830d73d9e7437f69789cac4a61534cbd2242250f2396ed9c7f4
- Acceptance subset: Each SwissKnife console capability maps to an exact native `agent_supervisor_*` operation, request/result schema, dispatcher/function identity, policy, and effect, generic workflow/data/storage proxy tools are refuted, goal completion requires child/evidence/health/exhaustion closure.
- Preconditions: objective goal SCA-G174 is schedulable
- Effects: satisfy evidence requirement: SCAEV174SUP
- Evidence subset: SCAEV174SUP
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G174
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/f24f9bb6475be830d73d9e7437f69789cac4a61534cbd2242250f2396ed9c7f4
- Missing evidence: SCAEV174SUP
- Embedding query: Extract goal/subgoal/task, control-plane, lane, validation, proof, refill, implementation, merge, recovery, status, and completion contracts and map every SwissKnife supervisor capability to a native accelerator operation.
- AST query: SCAEV174SUP
- Surplus group: objective/SCA-G174
- Merge key: cf1b311eb0adc5ce
- Merge family: objective/SCA-G174
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: b2b985b636a32c68
- Acceptance: Objective scan filed this gap for SCA-G174. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-193-objective-gap-15f69b5c871a.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV174SUP), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-194 Close objective gap: Scale and context-budget benchmark

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Blocked reason: Superseded by the existing canonical benchmark task SCA-140.
- Priority: P1
- Track: benchmark
- Depends on:
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py, data/agent_supervisor/swissknife_contract_assurance/benchmarks/report.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-194-objective-gap-197624eff234.md
- Bundle: swissknife/contract-assurance/benchmark
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-benchmark.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G021, SCA-G070, SCA-G100, SCA-G120
- Graph depth: 13
- Objective heap index: 35
- Parallel lane: swissknife/contract-assurance/benchmark
- Conflict policy: Benchmarks report measured capacity and never infer production concurrency from worker count.
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py, data/agent_supervisor/swissknife_contract_assurance/benchmarks/report.json
- Changed paths:
- AST symbols: SCAEV140BENCH
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G140
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/b461611ce6c7e94814f8f01f5256ea1d852fef2fb4a1819a4dff8afc0365c399
- Canonical task CID: baguqeerawrqwchhgy7uuqfhy6apvevxkdwcs73zpwsqydgsn76fpya3fyomq
- Semantic identity: objective-evidence-obligation/v1/3452288c3061ee223131bb9d3b636f5854da686f0564cf3cb088061afd2bf66f
- Acceptance subset: Warm unchanged reuse >=95 percent, packet max <=8192 tokens and median target <=2048, 10x irrelevant corpus growth does not materially grow mandatory context, bounds and high-watermarks are recorded.
- Preconditions: objective goal SCA-G140 is schedulable
- Effects: satisfy evidence requirement: SCAEV140BENCH
- Evidence subset: SCAEV140BENCH
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G140
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/3452288c3061ee223131bb9d3b636f5854da686f0564cf3cb088061afd2bf66f
- Missing evidence: SCAEV140BENCH
- Embedding query: Measure cold/warm/incremental scan, graph, proof, cache, storage, and prompt costs at SwissKnife scale and under irrelevant-corpus growth.
- AST query: SCAEV140BENCH
- Surplus group: objective/SCA-G140
- Merge key: 54b1ead460268296
- Merge family: objective/SCA-G140
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 403a863ae64ae446
- Acceptance: Objective scan filed this gap for SCA-G140. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-194-objective-gap-197624eff234.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV140BENCH), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-195 Close objective gap: Continuous incremental refill

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Blocked reason: Superseded by the existing canonical continuous-refill task SCA-130.
- Priority: P1
- Track: continuous
- Depends on:
- Outputs: data/agent_supervisor/swissknife_contract_assurance/state/invalidation.jsonl, data/agent_supervisor/swissknife_contract_assurance/state/refill_metrics.json
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_refill.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-195-objective-gap-d2d7972e4d78.md
- Bundle: swissknife/contract-assurance/continuous
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-continuous.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G110, SCA-G120
- Graph depth: 15
- Objective heap index: 36
- Parallel lane: swissknife/contract-assurance/continuous
- Conflict policy: Preserve prior receipts as historical evidence while marking stale bindings explicitly.
- Predicted files: data/agent_supervisor/swissknife_contract_assurance/state/invalidation.jsonl, data/agent_supervisor/swissknife_contract_assurance/state/refill_metrics.json
- Changed paths:
- AST symbols: SCAEV130REFILL
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G130
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/945b3e2881d22aefe2ea34fe901b4858aa9960568b8cd0c6db1623ab2d7588ef
- Canonical task CID: baguqeerasrnt4keb2ivo7yxkgt7jag2ilcvjsycwrognbrw3cyr2wllvrdxq
- Semantic identity: objective-evidence-obligation/v1/488f5ba0c64507e7b7b014d945616ac659ee701b691eca0a778064ccb77c933c
- Acceptance subset: Controlled one-symbol edits invalidate all and only dependents, cooldown/dedupe/open-work bounds hold, unhealthy scans cannot certify exhaustion.
- Preconditions: objective goal SCA-G130 is schedulable
- Effects: satisfy evidence requirement: SCAEV130REFILL
- Evidence subset: SCAEV130REFILL
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G130
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/488f5ba0c64507e7b7b014d945616ac659ee701b691eca0a778064ccb77c933c
- Missing evidence: SCAEV130REFILL
- Embedding query: Detect snapshot changes, update only changed index/proof closures, and refill bounded goal-backed tasks until no healthy current finding remains.
- AST query: SCAEV130REFILL
- Surplus group: objective/SCA-G130
- Merge key: 8fe9305298cd3592
- Merge family: objective/SCA-G130
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 7cca2df82b4fbe00
- Acceptance: Objective scan filed this gap for SCA-G130. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-195-objective-gap-d2d7972e4d78.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV130REFILL), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-196 Close objective gap: Promotion, operations, and closeout

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Blocked reason: Superseded by the existing canonical rollout task SCA-160.
- Priority: P1
- Track: rollout
- Depends on:
- Outputs: docs/launch/swissknife-symbolic-contract-supervisor-runbook.md, data/agent_supervisor/swissknife_contract_assurance/completion_gate.json
- Validation: test -f docs/launch/swissknife-symbolic-contract-supervisor-runbook.md && python3 -m json.tool data/agent_supervisor/swissknife_contract_assurance/completion_gate.json >/dev/null
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-196-objective-gap-a19b50a10098.md
- Bundle: swissknife/contract-assurance/rollout
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-rollout.todo.md
- Bundle strategy: explicit
- Graph parents: SCA-G120, SCA-G130, SCA-G140, SCA-G150, SCA-G166, SCA-G167, SCA-G176
- Graph depth: 21
- Objective heap index: 37
- Parallel lane: swissknife/contract-assurance/rollout
- Conflict policy: Closeout requires current-tree evidence and cannot be inferred from an empty queue.
- Predicted files: docs/launch/swissknife-symbolic-contract-supervisor-runbook.md, data/agent_supervisor/swissknife_contract_assurance/completion_gate.json
- Changed paths:
- AST symbols: SCAEV160OPS
- Interfaces:
- Submodules:
- Generated artifacts:
- Allow concurrent with:
- Goal id: SCA-G160
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/bd27305e27c47f8af6ffab498aa1dbbcfd5d528b003a4bd74f0e821e3fd0ec6d
- Canonical task CID: baguqeeraxuttaxrhyr7yv5x7vneyvio3xt6v2uulaa5exv2pb2bb4p6q5rwq
- Semantic identity: objective-evidence-obligation/v1/0667f777b00c4ebe6342b5282e81bc696ecbf87d9516485aa99666181ee3a005
- Acceptance subset: Operators can verify PID/lease/health/current snapshot/backlog/cache/analyzer and four-component runtime-contract state, automatic mutation remains disabled until all promotion gates pass, rollback returns to shadow without losing evidence.
- Preconditions: objective goal SCA-G160 is schedulable
- Effects: satisfy evidence requirement: SCAEV160OPS
- Evidence subset: SCAEV160OPS
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: objective/SCA-G160
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-evidence-obligation/v1/0667f777b00c4ebe6342b5282e81bc696ecbf87d9516485aa99666181ee3a005
- Missing evidence: SCAEV160OPS
- Embedding query: Publish health/status/query/runbook surfaces, shadow-to-assist promotion gates, rollback, lease recovery, artifact retention, and objective exhaustion evidence.
- AST query: SCAEV160OPS
- Surplus group: objective/SCA-G160
- Merge key: f266220232116771
- Merge family: objective/SCA-G160
- Merge role: aggregate
- Work item count: 1
- Work scope: goal_subgoal_multi_evidence_batch
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: aggregate
- Todo vector key: 271f909a069babfc
- Acceptance: Objective scan filed this gap for SCA-G160. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-196-objective-gap-a19b50a10098.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (SCAEV160OPS), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## SCA-197 Review completion-evidence alignment for Proof-directed SwissKnife contract assurance

- Status: blocked
- Blocked reason: manual review required because no precise edit targets were authorized
- Completion: manual
- Is schedulable: false
- Review only: true
- Priority: P0
- Track: swissknife-contract-assurance
- Depends on:
- Outputs:
- Validation: git diff --check; test -f implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md && python3 -m json.tool config/swissknife_symbolic_contract_assurance_supervisor.json >/dev/null && python3 -m json.tool config/swissknife_symbolic_contract_assurance_lane_inventory.json >/dev/null && python3 -m py_compile scripts/swissknife_parallel_implementation_supervisor.py
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-197-objective-gap-235654021c85.md
- Bundle: swissknife/contract-assurance/root
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-root.todo.md
- Bundle strategy: bounded_objective_generation
- Graph parents: none
- Graph depth: 1
- Objective heap index: 0
- Parallel lane: swissknife/contract-assurance/root
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Predicted files:
- Changed paths:
- AST symbols: completion-reconciliation, SCAEV000ROOT
- Interfaces:
- Submodules:
- Generated artifacts: data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-00/objective_generation.json
- Allow concurrent with:
- Goal id: SCA-G000
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/5a4c489cf44ef81ed6ed58f21a62af469b5825404a5bdd342581febb4c42cadc
- Canonical task CID: baguqeeraljgerhhuj34b5vxnldzbuyvpi2nvqjkajjn52nbfqh7lwtcczloa
- Semantic identity: objective-family/v1/f2798f83d0ede4b6956be3cb97e9b788a011922768c2f27f24c17298934b3d22
- Acceptance subset: Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied., Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one., Manual review required: no precise implementation, affected-document, or validator-source file was authorized as an edit target., Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree., Produce completion evidence for: Every child goal is completed or explicitly blocked with typed evidence, Reconcile the unverified completion decision with current evidence for: Proof-directed SwissKnife contract assurance, Require an explicitly healthy analyzer that is safe for completion reasoning., Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree., Task completion is provisional until every criterion has valid evidence.
- Preconditions: objective goal SCA-G000 is schedulable
- Effects: satisfy evidence requirement: Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied., satisfy evidence requirement: Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one., satisfy evidence requirement: Manual review required: no precise implementation, affected-document, or validator-source file was authorized as an edit target., satisfy evidence requirement: Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree., satisfy evidence requirement: Produce completion evidence for: Every child goal is completed or explicitly blocked with typed evidence, satisfy evidence requirement: Reconcile the unverified completion decision with current evidence for: Proof-directed SwissKnife contract assurance, satisfy evidence requirement: Require an explicitly healthy analyzer that is safe for completion reasoning., satisfy evidence requirement: Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree., satisfy evidence requirement: Task completion is provisional until every criterion has valid evidence.
- Evidence subset: Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied., Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one., Manual review required: no precise implementation, affected-document, or validator-source file was authorized as an edit target., Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree., Produce completion evidence for: Every child goal is completed or explicitly blocked with typed evidence, Reconcile the unverified completion decision with current evidence for: Proof-directed SwissKnife contract assurance, Require an explicitly healthy analyzer that is safe for completion reasoning., Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree., Task completion is provisional until every criterion has valid evidence.
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: SCA-G000
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-family/v1/f2798f83d0ede4b6956be3cb97e9b788a011922768c2f27f24c17298934b3d22
- Missing evidence: Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied., Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one., Manual review required: no precise implementation, affected-document, or validator-source file was authorized as an edit target., Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree., Produce completion evidence for: Every child goal is completed or explicitly blocked with typed evidence, Reconcile the unverified completion decision with current evidence for: Proof-directed SwissKnife contract assurance, Require an explicitly healthy analyzer that is safe for completion reasoning., Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree., Task completion is provisional until every criterion has valid evidence.
- Embedding query: completion reconciliation completion-evidence alignment SCAEV000ROOT
- AST query: completion-reconciliation, SCAEV000ROOT
- Surplus group: SCA-G000
- Merge key: objective-family/v1/f2798f83d0ede4b6956be3cb97e9b788a011922768c2f27f24c17298934b3d22
- Merge family: SCA-G000
- Merge role: completion_gate_gap_manual_review
- Work item count: 9
- Work scope: bounded_objective_generation
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: generated_task
- Todo vector key: f2798f83d0ede4b6
- Acceptance: Objective scan filed this review gap for SCA-G000. Inspect the evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-197-objective-gap-235654021c85.md; either resolve the diagnostic without an implementation change or authorize precise repository-relative edit targets before changing the task status.

## SCA-198 Review completion-evidence alignment for Canonical SwissKnife snapshot authority

- Status: blocked
- Blocked reason: manual review required because no precise edit targets were authorized
- Completion: manual
- Is schedulable: false
- Review only: true
- Priority: P0
- Track: snapshot-authority
- Depends on:
- Outputs:
- Validation: git diff --check; python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_repository_authority.py -q
- Evidence inputs: data/agent_supervisor/swissknife_contract_assurance/discovery
- Discovery evidence: /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-198-objective-gap-ba60f80546e2.md
- Bundle: swissknife/contract-assurance/snapshot-authority
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/swissknife-contract-assurance-snapshot-authority.todo.md
- Bundle strategy: bounded_objective_generation
- Graph parents: SCA-G010, SCA-G167
- Graph depth: 1
- Objective heap index: 0
- Parallel lane: swissknife/contract-assurance/snapshot-authority
- Conflict policy: prefer bundle-local changes; invoke the LLM merge resolver for semantic conflicts
- Predicted files:
- Changed paths:
- AST symbols: completion-reconciliation, SCAEV168AUTH
- Interfaces:
- Submodules:
- Generated artifacts: data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-00/objective_generation.json
- Allow concurrent with:
- Goal id: SCA-G168
- Completion authority: local
- External authority blockers:
- Canonical task key: task/v1/95c40719d7baf7666416e0db713830abb518e7aae5ab7ef4ae15e0cfa1b6f459
- Canonical task CID: baguqeerasxcaogoxxl3wmzaw4dnxcobqvo2rrz5k4wvx55focxqm7inw6rmq
- Semantic identity: objective-family/v1/b48b96ffb51d6ec69f56232298683c2fd29e0477308c6e6f267efc084dc64a51
- Acceptance subset: Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied., Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one., Manual review required: no precise implementation, affected-document, or validator-source file was authorized as an edit target., Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree., Produce completion evidence for: Origin, commit, tree, ancestry, dirty overlay, gitlink, and tracked-path population are CID-bound for each checkout, Reconcile the unverified completion decision with current evidence for: Canonical SwissKnife snapshot authority, Require an explicitly healthy analyzer that is safe for completion reasoning., Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree., Task completion is provisional until every criterion has valid evidence.
- Preconditions: objective goal SCA-G168 is schedulable
- Effects: satisfy evidence requirement: Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied., satisfy evidence requirement: Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one., satisfy evidence requirement: Manual review required: no precise implementation, affected-document, or validator-source file was authorized as an edit target., satisfy evidence requirement: Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree., satisfy evidence requirement: Produce completion evidence for: Origin, commit, tree, ancestry, dirty overlay, gitlink, and tracked-path population are CID-bound for each checkout, satisfy evidence requirement: Reconcile the unverified completion decision with current evidence for: Canonical SwissKnife snapshot authority, satisfy evidence requirement: Require an explicitly healthy analyzer that is safe for completion reasoning., satisfy evidence requirement: Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree., satisfy evidence requirement: Task completion is provisional until every criterion has valid evidence.
- Evidence subset: Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied., Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one., Manual review required: no precise implementation, affected-document, or validator-source file was authorized as an edit target., Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree., Produce completion evidence for: Origin, commit, tree, ancestry, dirty overlay, gitlink, and tracked-path population are CID-bound for each checkout, Reconcile the unverified completion decision with current evidence for: Canonical SwissKnife snapshot authority, Require an explicitly healthy analyzer that is safe for completion reasoning., Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree., Task completion is provisional until every criterion has valid evidence.
- Resource class: cpu-medium
- Token class: medium
- Estimated tokens: 0
- Resources: cpu-medium
- Merge fate: SCA-G168
- Rejection reasons: none (accepted)
- Evidence obligation key: objective-family/v1/b48b96ffb51d6ec69f56232298683c2fd29e0477308c6e6f267efc084dc64a51
- Missing evidence: Every descendant must remain verified with all proof requirements fresh, conclusive, uncontradicted, and satisfied., Every submitted validation proof must be fresh and passing, and every mandatory criterion must have one., Manual review required: no precise implementation, affected-document, or validator-source file was authorized as an edit target., Map every mandatory acceptance criterion to fresh, verified implementation and validation proof bound to the current tree., Produce completion evidence for: Origin, commit, tree, ancestry, dirty overlay, gitlink, and tracked-path population are CID-bound for each checkout, Reconcile the unverified completion decision with current evidence for: Canonical SwissKnife snapshot authority, Require an explicitly healthy analyzer that is safe for completion reasoning., Require the configured number of independent, fresh, healthy exhaustive receipts bound to the current repository tree., Task completion is provisional until every criterion has valid evidence.
- Embedding query: completion reconciliation completion-evidence alignment SCAEV168AUTH
- AST query: completion-reconciliation, SCAEV168AUTH
- Surplus group: SCA-G168
- Merge key: objective-family/v1/b48b96ffb51d6ec69f56232298683c2fd29e0477308c6e6f267efc084dc64a51
- Merge family: SCA-G168
- Merge role: completion_gate_gap_manual_review
- Work item count: 9
- Work scope: bounded_objective_generation
- Goal packet:
- Goal packet role:
- Goal packet goals:
- Goal packet task count: 0
- Goal packet work item count: 0
- Completion goal bindings: {}
- Completion task bindings:
- Candidate kind: generated_task
- Todo vector key: b48b96ffb51d6ec6
- Acceptance: Objective scan filed this review gap for SCA-G168. Inspect the evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-198-objective-gap-ba60f80546e2.md; either resolve the diagnostic without an implementation change or authorize precise repository-relative edit targets before changing the task status.

## SCA-199 Resolve implementation retry-budget failure for SCA-194

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: false
- Blocked reason: Source task SCA-194 is a terminal alias superseded by canonical task SCA-140.
- Priority: P1
- Track: ops
- Depends on:
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_benchmark.py, data/agent_supervisor/swissknife_contract_assurance/benchmarks/report.json, data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery
- Validation: test -f /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery/2026-07-29-sca-199-sca-194-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in SCA-194. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-02/discovery/2026-07-29-sca-199-sca-194-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release SCA-194 from strategy blocked_tasks.

## SCA-200 Materialize the complete symbolic contract baseline

- Status: completed
- Priority: P0
- Track: baseline-pipeline
- Depends on: SCA-120, SCA-166, SCA-177
- Goal id: SCA-G120
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_assurance_baseline.py, external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_baseline.py, data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md
- Validation: python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_baseline.py -q
- Board namespace: swissknife-symbolic-contract-assurance-v1
- Bundle: swissknife/contract-assurance/baseline-pipeline
- Parallel lane: sca-baseline-pipeline
- Resource class: cpu-proof-solver
- Resource stage: analysis
- Implementation timeout seconds: 21600
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_assurance_baseline.py, external/ipfs_accelerate/scripts/index_repository_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_baseline.py, data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json, data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json, data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md
- Interfaces: RepositoryIndexer@1, RuntimeComponentCatalog@1, SymbolicContractGraph@1, McpInvocationTrace@1, ContractMismatchAnalyzer@1, ContractVulnerabilityRuleEngine@1
- Context budget tokens: 4096
- Provider role: grok-implement, codex-review
- Proposal artifact envelope: {"schema":"ipfs_accelerate_py/agent-supervisor/task-artifact-envelope@1","paths":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/contract_assurance_baseline.py","external/ipfs_accelerate/scripts/index_repository_contracts.py","external/ipfs_accelerate/test/api/test_agent_supervisor_contract_assurance_baseline.py","data/agent_supervisor/swissknife_contract_assurance/baseline/coverage.json","data/agent_supervisor/swissknife_contract_assurance/baseline/contract_findings.json","data/agent_supervisor/swissknife_contract_assurance/baseline/summary.md"],"max_file_bytes":4000000,"max_patch_bytes":8000000,"max_output_bytes":16000000}
- Conflict policy: Consume the healthy repository index and reviewed runtime extractors; never turn missing graph, proof, or health evidence into an empty-success finding set.
- Preconditions: Whole-tree analyzer health is within reviewed thresholds and cross-component proof surfaces are implemented.
- Effects: Runs extraction, catalog normalization, mandatory graph closure, expected-versus-actual MCP++ tracing, proof/cache verification, mismatch classification, vulnerability rules, and bounded artifact publication over one exact snapshot.
- Evidence subset: Current snapshot/index/AST roots, capability and policy roots, contract graph, claims, obligations, proof/cache/attestation receipts, counterexamples, and analyzer health
- Acceptance: Every in-scope contract has proved, refuted, unknown, unsupported, or stale status; graph/proof/finding identities are CID-bound to one snapshot; unhealthy or incomplete stages withhold no-drift claims; coverage remains within the artifact envelope; runtime performs zero LLM calls.

## SCA-201 Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:295

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Validation: python3 -m py_compile external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Graph parents: SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Graph depth: 22
- Goal id: SCA-G172
- Goal lineage: SCA-G172, SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Goal registration: existing
- Canonical task key: task/v1/a1c9751c6e9d69edca1a4fc2393f5322ef9b2b331723ac0ff13180b3e05417c2
- Canonical task CID: baguqeerauhexkhdotvu63sq2j7bdsp2telxzwkztc4r2yd7rggalhycuc7ba
- Semantic identity: a1c9751c6e9d69edca1a4fc2393f5322ef9b2b331723ac0ff13180b3e05417c2
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:295
- Preconditions: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:295, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-201-codebase-scan-127ed75eb2de.md
- Resource class: cpu-small
- Token class: small
- Context budget tokens: 2048
- Provider role: grok-implement, codex-review
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:295
- Candidate kind: codebase_scan
- Todo vector key: 127ed75eb2de779a
- Bundle: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- AST symbols: __future__, __future__.annotations, __init__, __post_init__, _bool, _cid, _clean_path, _enum, _extract_swallowed_regex, _line_span_for_offset, _mapping, _nonneg_int, _optional_text, _parse_idempotence, _parse_invocation, _parse_receipt, _parse_source_span, _parse_surface, _parse_swallowed, _parse_transition, _positive_int, _sequence, _source_path, _source_sha256, _span, _state_for_kind, _text, _validate_catalog_consistency, _verified_cid, apply lifecycle transition, apply_lifecycle_transition, assert idempotence closed, assert lifecycle edges complete, assert mediation distinguished, assert swallowed failures visible, assert_idempotence_closed, assert_lifecycle_edges_complete, assert_mediation_distinguished, assert_swallowed_failures_visible, ast, bool, build orchestrator contract catalog, build_orchestrator_contract_catalog, cid, claimfamily, classify invocation path, classify_invocation_path, clean path, collections abc, collections abc iterable, collections abc mapping, collections abc sequence, collections.abc, collections.abc.iterable, collections.abc.mapping, collections.abc.sequence, content identity bridge, content identity bridge identify strict artifact, content_identity_bridge, content_identity_bridge.identify_strict_artifact, dataclasses, dataclasses dataclass, dataclasses field, dataclasses.dataclass, dataclasses.field, default orchestrator inventory, default_orchestrator_inventory, direct package paths, direct_package_paths, duplicateorchestratorerror, enum, enum enum, enum.enum, evaluate cancel idempotence, evaluate idempotence from source, evaluate result idempotence, evaluate retry idempotence, evaluate_cancel_idempotence, evaluate_idempotence_from_source, evaluate_result_idempotence
- AST symbol scope: file
- Merge key: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Merge family: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:295 for SCA-G172. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-201-codebase-scan-127ed75eb2de.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.

## SCA-202 Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:296

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Validation: python3 -m py_compile external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Graph parents: SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Graph depth: 22
- Goal id: SCA-G172
- Goal lineage: SCA-G172, SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Goal registration: existing
- Canonical task key: task/v1/66a69eb9195bf28301a9f5a993f9ec6faa0867d61fd5b0d055271ab7d0c6e206
- Canonical task CID: baguqeeram2tj5oizlpziganj6wuzh6pmn6vaqz6wd7k3bucve4nlpugg4ida
- Semantic identity: 66a69eb9195bf28301a9f5a993f9ec6faa0867d61fd5b0d055271ab7d0c6e206
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:296
- Preconditions: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:296, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-202-codebase-scan-dc5339180262.md
- Resource class: cpu-small
- Token class: small
- Context budget tokens: 2048
- Provider role: grok-implement, codex-review
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:296
- Candidate kind: codebase_scan
- Todo vector key: dc5339180262e3dc
- Bundle: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- AST symbols: __future__, __future__.annotations, __init__, __post_init__, _bool, _cid, _clean_path, _enum, _extract_swallowed_regex, _line_span_for_offset, _mapping, _nonneg_int, _optional_text, _parse_idempotence, _parse_invocation, _parse_receipt, _parse_source_span, _parse_surface, _parse_swallowed, _parse_transition, _positive_int, _sequence, _source_path, _source_sha256, _span, _state_for_kind, _text, _validate_catalog_consistency, _verified_cid, apply lifecycle transition, apply_lifecycle_transition, assert idempotence closed, assert lifecycle edges complete, assert mediation distinguished, assert swallowed failures visible, assert_idempotence_closed, assert_lifecycle_edges_complete, assert_mediation_distinguished, assert_swallowed_failures_visible, ast, bool, build orchestrator contract catalog, build_orchestrator_contract_catalog, cid, claimfamily, classify invocation path, classify_invocation_path, clean path, collections abc, collections abc iterable, collections abc mapping, collections abc sequence, collections.abc, collections.abc.iterable, collections.abc.mapping, collections.abc.sequence, content identity bridge, content identity bridge identify strict artifact, content_identity_bridge, content_identity_bridge.identify_strict_artifact, dataclasses, dataclasses dataclass, dataclasses field, dataclasses.dataclass, dataclasses.field, default orchestrator inventory, default_orchestrator_inventory, direct package paths, direct_package_paths, duplicateorchestratorerror, enum, enum enum, enum.enum, evaluate cancel idempotence, evaluate idempotence from source, evaluate result idempotence, evaluate retry idempotence, evaluate_cancel_idempotence, evaluate_idempotence_from_source, evaluate_result_idempotence
- AST symbol scope: file
- Merge key: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Merge family: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:296 for SCA-G172. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-202-codebase-scan-dc5339180262.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.

## SCA-203 Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2529

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Validation: python3 -m py_compile external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Graph parents: SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Graph depth: 22
- Goal id: SCA-G172
- Goal lineage: SCA-G172, SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Goal registration: existing
- Canonical task key: task/v1/ca77c09e8029f8f243254a82a501d8dda36d4145d7cb812eb34c7df00f7cdcd9
- Canonical task CID: baguqeerazj34bhuafh4peqzfjkbkkaoy3wrw2qkf27fyclvtjr67ad343tmq
- Semantic identity: ca77c09e8029f8f243254a82a501d8dda36d4145d7cb812eb34c7df00f7cdcd9
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2529
- Preconditions: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2529, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-203-codebase-scan-f1650d37e707.md
- Resource class: cpu-small
- Token class: small
- Context budget tokens: 2048
- Provider role: grok-implement, codex-review
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2529
- Candidate kind: codebase_scan
- Todo vector key: f1650d37e7079592
- Bundle: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- AST symbols: __future__, __future__.annotations, __init__, __post_init__, _bool, _cid, _clean_path, _enum, _extract_swallowed_regex, _line_span_for_offset, _mapping, _nonneg_int, _optional_text, _parse_idempotence, _parse_invocation, _parse_receipt, _parse_source_span, _parse_surface, _parse_swallowed, _parse_transition, _positive_int, _sequence, _source_path, _source_sha256, _span, _state_for_kind, _text, _validate_catalog_consistency, _verified_cid, apply lifecycle transition, apply_lifecycle_transition, assert idempotence closed, assert lifecycle edges complete, assert mediation distinguished, assert swallowed failures visible, assert_idempotence_closed, assert_lifecycle_edges_complete, assert_mediation_distinguished, assert_swallowed_failures_visible, ast, bool, build orchestrator contract catalog, build_orchestrator_contract_catalog, cid, claimfamily, classify invocation path, classify_invocation_path, clean path, collections abc, collections abc iterable, collections abc mapping, collections abc sequence, collections.abc, collections.abc.iterable, collections.abc.mapping, collections.abc.sequence, content identity bridge, content identity bridge identify strict artifact, content_identity_bridge, content_identity_bridge.identify_strict_artifact, dataclasses, dataclasses dataclass, dataclasses field, dataclasses.dataclass, dataclasses.field, default orchestrator inventory, default_orchestrator_inventory, direct package paths, direct_package_paths, duplicateorchestratorerror, enum, enum enum, enum.enum, evaluate cancel idempotence, evaluate idempotence from source, evaluate result idempotence, evaluate retry idempotence, evaluate_cancel_idempotence, evaluate_idempotence_from_source, evaluate_result_idempotence
- AST symbol scope: file
- Merge key: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Merge family: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2529 for SCA-G172. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-203-codebase-scan-f1650d37e707.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.

## SCA-204 Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2545

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Validation: python3 -m py_compile external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Graph parents: SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Graph depth: 22
- Goal id: SCA-G172
- Goal lineage: SCA-G172, SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Goal registration: existing
- Canonical task key: task/v1/1b917baffdea41340524af66b3a1fc30d4e85420d02136fbcb20396aae53268d
- Canonical task CID: baguqeeradoixxl755jatibjev5tlhip4gdkoqvba2aqtn66lea4wvlste2gq
- Semantic identity: 1b917baffdea41340524af66b3a1fc30d4e85420d02136fbcb20396aae53268d
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2545
- Preconditions: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2545, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-204-codebase-scan-839c8b06c016.md
- Resource class: cpu-small
- Token class: small
- Context budget tokens: 2048
- Provider role: grok-implement, codex-review
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2545
- Candidate kind: codebase_scan
- Todo vector key: 839c8b06c0162bc6
- Bundle: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- AST symbols: __future__, __future__.annotations, __init__, __post_init__, _bool, _cid, _clean_path, _enum, _extract_swallowed_regex, _line_span_for_offset, _mapping, _nonneg_int, _optional_text, _parse_idempotence, _parse_invocation, _parse_receipt, _parse_source_span, _parse_surface, _parse_swallowed, _parse_transition, _positive_int, _sequence, _source_path, _source_sha256, _span, _state_for_kind, _text, _validate_catalog_consistency, _verified_cid, apply lifecycle transition, apply_lifecycle_transition, assert idempotence closed, assert lifecycle edges complete, assert mediation distinguished, assert swallowed failures visible, assert_idempotence_closed, assert_lifecycle_edges_complete, assert_mediation_distinguished, assert_swallowed_failures_visible, ast, bool, build orchestrator contract catalog, build_orchestrator_contract_catalog, cid, claimfamily, classify invocation path, classify_invocation_path, clean path, collections abc, collections abc iterable, collections abc mapping, collections abc sequence, collections.abc, collections.abc.iterable, collections.abc.mapping, collections.abc.sequence, content identity bridge, content identity bridge identify strict artifact, content_identity_bridge, content_identity_bridge.identify_strict_artifact, dataclasses, dataclasses dataclass, dataclasses field, dataclasses.dataclass, dataclasses.field, default orchestrator inventory, default_orchestrator_inventory, direct package paths, direct_package_paths, duplicateorchestratorerror, enum, enum enum, enum.enum, evaluate cancel idempotence, evaluate idempotence from source, evaluate result idempotence, evaluate retry idempotence, evaluate_cancel_idempotence, evaluate_idempotence_from_source, evaluate_result_idempotence
- AST symbol scope: file
- Merge key: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Merge family: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2545 for SCA-G172. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-204-codebase-scan-839c8b06c016.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.

## SCA-205 Review swallowed exception path in external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py:443

- Status: completed
- Completion: manual
- Priority: P1
- Track: quality
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Validation: python3 -m py_compile external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Graph parents: SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Graph depth: 22
- Goal id: SCA-G172
- Goal lineage: SCA-G172, SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Goal registration: existing
- Canonical task key: task/v1/729821e2e6f34ceeaf68c52c1867e72e8499a835b198c17ee57fc47b5e2413b0
- Canonical task CID: baguqeeraokmcdyxg6ngo5l3iyuwbqz7hf2cjtkbvwgmmc7xfp7chwxrecoya
- Semantic identity: 729821e2e6f34ceeaf68c52c1867e72e8499a835b198c17ee57fc47b5e2413b0
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py:443
- Preconditions: external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py:443, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-205-codebase-scan-5d7f78247d82.md
- Resource class: cpu-small
- Token class: small
- Context budget tokens: 2048
- Provider role: grok-implement, codex-review
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py:443
- Candidate kind: codebase_scan
- Todo vector key: 5d7f78247d820096
- Bundle: codebase/quality/external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-quality-external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/quality/external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- AST symbols: __future__, __future__.annotations, _unmaterialized, copy, future, future annotations, ipfs accelerate py agent supervisor analysis orchestrator contract extractor, ipfs accelerate py agent supervisor analysis orchestrator contract extractor apply lifecycle transition, ipfs accelerate py agent supervisor analysis orchestrator contract extractor assert idempotence closed, ipfs accelerate py agent supervisor analysis orchestrator contract extractor assert lifecycle edges complete, ipfs accelerate py agent supervisor analysis orchestrator contract extractor assert mediation distinguished, ipfs accelerate py agent supervisor analysis orchestrator contract extractor assert swallowed failures visible, ipfs accelerate py agent supervisor analysis orchestrator contract extractor build orchestrator contract catalog, ipfs accelerate py agent supervisor analysis orchestrator contract extractor catalog version, ipfs accelerate py agent supervisor analysis orchestrator contract extractor classify invocation path, ipfs accelerate py agent supervisor analysis orchestrator contract extractor default orchestrator inventory, ipfs accelerate py agent supervisor analysis orchestrator contract extractor duplicateorchestratorerror, ipfs accelerate py agent supervisor analysis orchestrator contract extractor evaluate cancel idempotence, ipfs accelerate py agent supervisor analysis orchestrator contract extractor evaluate idempotence from source, ipfs accelerate py agent supervisor analysis orchestrator contract extractor evaluate result idempotence, ipfs accelerate py agent supervisor analysis orchestrator contract extractor evaluate retry idempotence, ipfs accelerate py agent supervisor analysis orchestrator contract extractor extract orchestrator contracts, ipfs accelerate py agent supervisor analysis orchestrator contract extractor extract orchestrator source contracts, ipfs accelerate py agent supervisor analysis orchestrator contract extractor extract swallowed failures from source, ipfs accelerate py agent supervisor analysis orchestrator contract extractor extract transitions from source, ipfs accelerate py agent supervisor analysis orchestrator contract extractor idempotencedisposition, ipfs accelerate py agent supervisor analysis orchestrator contract extractor idempotencesubject, ipfs accelerate py agent supervisor analysis orchestrator contract extractor invocationpathkind, ipfs accelerate py agent supervisor analysis orchestrator contract extractor lifecyclestate, ipfs accelerate py agent supervisor analysis orchestrator contract extractor materialize orchestrator contract catalog, ipfs accelerate py agent supervisor analysis orchestrator contract extractor missingorchestratorerror, ipfs accelerate py agent supervisor analysis orchestrator contract extractor orchestrator contract catalog interface, ipfs accelerate py agent supervisor analysis orchestrator contract extractor orchestrator contract extractor interface, ipfs accelerate py agent supervisor analysis orchestrator contract extractor orchestratorciderror, ipfs accelerate py agent supervisor analysis orchestrator contract extractor orchestratorcontracterror, ipfs accelerate py agent supervisor analysis orchestrator contract extractor orchestratorcontractextractor, ipfs accelerate py agent supervisor analysis orchestrator contract extractor orchestratorinvarianterror, ipfs accelerate py agent supervisor analysis orchestrator contract extractor orchestratorsourceerror, ipfs accelerate py agent supervisor analysis orchestrator contract extractor orchestratorsurfacerole, ipfs accelerate py agent supervisor analysis orchestrator contract extractor runtime component id, ipfs accelerate py agent supervisor analysis orchestrator contract extractor scaev172orch, ipfs accelerate py agent supervisor analysis orchestrator contract extractor swallowedfailurekind, ipfs accelerate py agent supervisor analysis orchestrator contract extractor terminal states, ipfs accelerate py agent supervisor analysis orchestrator contract extractor transitionkind, ipfs accelerate py agent supervisor analysis orchestrator contract extractor validate orchestrator sources, ipfs accelerate py agent supervisor analysis runtime component catalog, ipfs accelerate py agent supervisor analysis runtime component catalog runtimecomponentkind, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.apply_lifecycle_transition, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.assert_idempotence_closed, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.assert_lifecycle_edges_complete, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.assert_mediation_distinguished, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.assert_swallowed_failures_visible, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.build_orchestrator_contract_catalog, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.catalog_version, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.classify_invocation_path, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.default_orchestrator_inventory, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.duplicateorchestratorerror, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.evaluate_cancel_idempotence, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.evaluate_idempotence_from_source, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.evaluate_result_idempotence, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.evaluate_retry_idempotence, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.extract_orchestrator_contracts, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.extract_orchestrator_source_contracts, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.extract_swallowed_failures_from_source, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.extract_transitions_from_source, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.idempotencedisposition, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.idempotencesubject, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.invocationpathkind, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.lifecyclestate, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.materialize_orchestrator_contract_catalog, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.missingorchestratorerror, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.orchestrator_contract_catalog_interface, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.orchestrator_contract_extractor_interface, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.orchestratorciderror, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.orchestratorcontracterror, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.orchestratorcontractextractor, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.orchestratorinvarianterror, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.orchestratorsourceerror, ipfs_accelerate_py.agent_supervisor.analysis.orchestrator_contract_extractor.orchestratorsurfacerole
- AST symbol scope: file
- Merge key: codebase/quality/external-ipfs_accelerate-test-api-test_agent_supervisor_orchestrator_contract_extractor
- Merge family: external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/test/api/test_agent_supervisor_orchestrator_contract_extractor.py:443 for SCA-G172. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-205-codebase-scan-5d7f78247d82.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.

## SCA-206 Resolve validation retry-budget failure for SCA-203

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py, data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery
- Validation: test -f /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery/2026-07-29-sca-206-sca-203-retry-budget.md
- Provider role: grok-implement, codex-review
- Context budget tokens: 2048
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in SCA-203. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-03/discovery/2026-07-29-sca-206-sca-203-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release SCA-203 from strategy blocked_tasks.

## SCA-207 Resolve validation retry-budget failure for SCA-204

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py, data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-00/discovery
- Validation: test -f /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-00/discovery/2026-07-29-sca-207-sca-204-retry-budget.md
- Provider role: grok-implement, codex-review
- Context budget tokens: 2048
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in SCA-204. Use evidence in /home/barberb/lift_coding/data/agent_supervisor/swissknife_contract_assurance/parallel/lanes/lane-00/discovery/2026-07-29-sca-207-sca-204-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release SCA-204 from strategy blocked_tasks.

## SCA-208 Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2535

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Validation: python3 -m py_compile external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Graph parents: SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Graph depth: 22
- Goal id: SCA-G172
- Goal lineage: SCA-G172, SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Goal registration: existing
- Canonical task key: task/v1/1a82327bcb9b3b8462b7a7e360bad18e3cf637b196c62a64431b847984465e25
- Canonical task CID: baguqeeradkbde66ltm5yiyvxu7rwbowrry6pmn5rs3dcuzcddochtbcglysq
- Semantic identity: 1a82327bcb9b3b8462b7a7e360bad18e3cf637b196c62a64431b847984465e25
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2535
- Preconditions: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2535, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-208-codebase-scan-a3f7fcc511b7.md
- Resource class: cpu-small
- Token class: small
- Context budget tokens: 2048
- Provider role: grok-implement, codex-review
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2535
- Candidate kind: codebase_scan
- Todo vector key: a3f7fcc511b7434c
- Bundle: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- AST symbols: __future__, __future__.annotations, __init__, __post_init__, _bool, _cid, _clean_path, _enum, _extract_swallowed_regex, _line_span_for_offset, _mapping, _nonneg_int, _optional_text, _parse_idempotence, _parse_invocation, _parse_receipt, _parse_source_span, _parse_surface, _parse_swallowed, _parse_transition, _positive_int, _sequence, _source_path, _source_sha256, _span, _state_for_kind, _text, _validate_catalog_consistency, _verified_cid, apply lifecycle transition, apply_lifecycle_transition, assert idempotence closed, assert lifecycle edges complete, assert mediation distinguished, assert swallowed failures visible, assert_idempotence_closed, assert_lifecycle_edges_complete, assert_mediation_distinguished, assert_swallowed_failures_visible, ast, bool, build orchestrator contract catalog, build_orchestrator_contract_catalog, cid, claimfamily, classify invocation path, classify_invocation_path, clean path, collections abc, collections abc iterable, collections abc mapping, collections abc sequence, collections.abc, collections.abc.iterable, collections.abc.mapping, collections.abc.sequence, content identity bridge, content identity bridge identify strict artifact, content_identity_bridge, content_identity_bridge.identify_strict_artifact, dataclasses, dataclasses dataclass, dataclasses field, dataclasses.dataclass, dataclasses.field, default orchestrator inventory, default_orchestrator_inventory, direct package paths, direct_package_paths, duplicateorchestratorerror, enum, enum enum, enum.enum, evaluate cancel idempotence, evaluate idempotence from source, evaluate result idempotence, evaluate retry idempotence, evaluate_cancel_idempotence, evaluate_idempotence_from_source, evaluate_result_idempotence
- AST symbol scope: file
- Merge key: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Merge family: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2535 for SCA-G172. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-208-codebase-scan-a3f7fcc511b7.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.

## SCA-209 Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2551

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Validation: python3 -m py_compile external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Graph parents: SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Graph depth: 22
- Goal id: SCA-G172
- Goal lineage: SCA-G172, SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Goal registration: existing
- Canonical task key: task/v1/8c5533ed8057038a83ab968bc5acd01414e2f37565db46931e48ad8aa70b632c
- Canonical task CID: baguqeerarrkth3mak4byva5ls2f4llgqcqkof43vmxnuney6jcwyvjylmmwa
- Semantic identity: 8c5533ed8057038a83ab968bc5acd01414e2f37565db46931e48ad8aa70b632c
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2551
- Preconditions: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2551, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-209-codebase-scan-81554eb648a8.md
- Resource class: cpu-small
- Token class: small
- Context budget tokens: 2048
- Provider role: grok-implement, codex-review
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2551
- Candidate kind: codebase_scan
- Todo vector key: 81554eb648a83a93
- Bundle: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- AST symbols: __future__, __future__.annotations, __init__, __post_init__, _bool, _cid, _clean_path, _enum, _extract_swallowed_regex, _line_span_for_offset, _mapping, _nonneg_int, _optional_text, _parse_idempotence, _parse_invocation, _parse_receipt, _parse_source_span, _parse_surface, _parse_swallowed, _parse_transition, _positive_int, _sequence, _source_path, _source_sha256, _span, _state_for_kind, _text, _validate_catalog_consistency, _verified_cid, apply lifecycle transition, apply_lifecycle_transition, assert idempotence closed, assert lifecycle edges complete, assert mediation distinguished, assert swallowed failures visible, assert_idempotence_closed, assert_lifecycle_edges_complete, assert_mediation_distinguished, assert_swallowed_failures_visible, ast, bool, build orchestrator contract catalog, build_orchestrator_contract_catalog, cid, claimfamily, classify invocation path, classify_invocation_path, clean path, collections abc, collections abc iterable, collections abc mapping, collections abc sequence, collections.abc, collections.abc.iterable, collections.abc.mapping, collections.abc.sequence, content identity bridge, content identity bridge identify strict artifact, content_identity_bridge, content_identity_bridge.identify_strict_artifact, dataclasses, dataclasses dataclass, dataclasses field, dataclasses.dataclass, dataclasses.field, default orchestrator inventory, default_orchestrator_inventory, direct package paths, direct_package_paths, duplicateorchestratorerror, enum, enum enum, enum.enum, evaluate cancel idempotence, evaluate idempotence from source, evaluate result idempotence, evaluate retry idempotence, evaluate_cancel_idempotence, evaluate_idempotence_from_source, evaluate_result_idempotence
- AST symbol scope: file
- Merge key: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Merge family: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2551 for SCA-G172. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-209-codebase-scan-81554eb648a8.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.

## SCA-210 Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2554

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/agent_supervisor/swissknife_contract_assurance/discovery, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Validation: python3 -m py_compile external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Graph parents: SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Graph depth: 22
- Goal id: SCA-G172
- Goal lineage: SCA-G172, SCA-G170, SCA-G040, SCA-G042, SCA-G168, SCA-G000, SCA-G010, SCA-G020, SCA-G167, SCA-G015, SCA-G100, SCA-G110, SCA-G111, SCA-G090, SCA-G091, SCA-G021, SCA-G101, SCA-G051, SCA-G061, SCA-G050, SCA-G060, SCA-G030, SCA-G041
- Goal registration: existing
- Canonical task key: task/v1/c3be67ab2f0354af896e7ac65635d4e9b7d12f4133d244fdba6a3f38f78ede3b
- Canonical task CID: baguqeerayo7gpkzpankk7clopldfmnou5g35cl2bgpjej7n2ni7tr54o3y5q
- Semantic identity: c3be67ab2f0354af896e7ac65635d4e9b7d12f4133d244fdba6a3f38f78ede3b
- Acceptance subset: Resolve swallowed_exception at external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2554
- Preconditions: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py exists and the scan evidence remains applicable
- Effects: resolve swallowed_exception in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py and pass focused validation
- Evidence subset: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2554, data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-210-codebase-scan-b078ee596ea9.md
- Resource class: cpu-small
- Token class: small
- Context budget tokens: 2048
- Provider role: grok-implement, codex-review
- Resources: python, focused validation runner
- Merge fate: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Rejection reasons: none
- Missing evidence: Review swallowed exception path in external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2554
- Candidate kind: codebase_scan
- Todo vector key: b078ee596ea99bfa
- Bundle: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Bundle shard: data/agent_supervisor/swissknife_contract_assurance/bundles/codebase-runtime-external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor.todo.md
- Bundle strategy: codebase_file_ast
- Parallel lane: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Conflict policy: serialize findings for the same file; allow independent file bundles to run concurrently
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- AST symbols: __future__, __future__.annotations, __init__, __post_init__, _bool, _cid, _clean_path, _enum, _extract_swallowed_regex, _line_span_for_offset, _mapping, _nonneg_int, _optional_text, _parse_idempotence, _parse_invocation, _parse_receipt, _parse_source_span, _parse_surface, _parse_swallowed, _parse_transition, _positive_int, _sequence, _source_path, _source_sha256, _span, _state_for_kind, _text, _validate_catalog_consistency, _verified_cid, apply lifecycle transition, apply_lifecycle_transition, assert idempotence closed, assert lifecycle edges complete, assert mediation distinguished, assert swallowed failures visible, assert_idempotence_closed, assert_lifecycle_edges_complete, assert_mediation_distinguished, assert_swallowed_failures_visible, ast, bool, build orchestrator contract catalog, build_orchestrator_contract_catalog, cid, claimfamily, classify invocation path, classify_invocation_path, clean path, collections abc, collections abc iterable, collections abc mapping, collections abc sequence, collections.abc, collections.abc.iterable, collections.abc.mapping, collections.abc.sequence, content identity bridge, content identity bridge identify strict artifact, content_identity_bridge, content_identity_bridge.identify_strict_artifact, dataclasses, dataclasses dataclass, dataclasses field, dataclasses.dataclass, dataclasses.field, default orchestrator inventory, default_orchestrator_inventory, direct package paths, direct_package_paths, duplicateorchestratorerror, enum, enum enum, enum.enum, evaluate cancel idempotence, evaluate idempotence from source, evaluate result idempotence, evaluate retry idempotence, evaluate_cancel_idempotence, evaluate_idempotence_from_source, evaluate_result_idempotence
- AST symbol scope: file
- Merge key: codebase/runtime/external-ipfs_accelerate-ipfs_accelerate_py-agent_supervisor-analysis-orchestrator_contract_extractor
- Merge family: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py
- Merge role: codebase_scan
- Work item count: 1
- Work scope: codebase_file_ast
- Acceptance: Goal-scoped refill admitted this finding from external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/orchestrator_contract_extractor.py:2554 for SCA-G172. Use evidence in data/agent_supervisor/swissknife_contract_assurance/discovery/2026-07-29-sca-210-codebase-scan-b078ee596ea9.md, make only the smallest change required by that goal lineage, add or update focused validation when appropriate, and do not expand into adjacent cleanup.
