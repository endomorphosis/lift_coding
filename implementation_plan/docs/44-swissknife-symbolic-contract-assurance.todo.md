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
| 7 | 121, 130, 140, 150; then 160 | Four-way operational fan-out, then closeout |

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

- Status: active
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

- Status: active
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

- Status: active
- Priority: P0
- Track: baseline
- Depends on: SCA-021, SCA-051, SCA-061, SCA-070, SCA-090
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
- Conflict policy: Shadow task writes evidence only; no source, board status, or implementation mutation.
- Preconditions: Full pipeline unit/conformance tests pass.
- Effects: Captures exact baseline coverage, capabilities, graph root, claims, proofs, counterexamples, cache outcomes, and analyzer health.
- Evidence subset: Current parent and recursive submodule snapshot
- Acceptance: All tracked paths disposed; exact snapshot/capability/policy roots; every contract terminal status typed; generated findings reproducible; partial health prevents exhaustive/no-drift claim; zero LLM calls.

## SCA-121 Triage baseline counterexamples into initial accelerator packets

- Status: active
- Priority: P0
- Track: baseline-triage
- Depends on: SCA-100, SCA-101, SCA-120
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
- Depends on: SCA-110, SCA-120
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
- Depends on: SCA-070, SCA-100, SCA-120
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
- Depends on: SCA-111, SCA-130, SCA-140, SCA-150
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
