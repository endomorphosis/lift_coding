# SwissKnife Symbolic Contract Assurance Plan

Date: 2026-07-28

Status: active supervisor program

Objective heap:
`implementation_plan/docs/44-swissknife-symbolic-contract-assurance.objectives.md`

Taskboard:
`implementation_plan/docs/44-swissknife-symbolic-contract-assurance.todo.md`

Task prefix: `## SCA-`

Board namespace: `swissknife-symbolic-contract-assurance-v1`

Runtime root: `data/agent_supervisor/swissknife_contract_assurance`

## Outcome

Build a content-addressed, proof-directed analysis loop that can:

1. Account for every Git-tracked SwissKnife file and every in-scope working-tree
   overlay without loading the repository into a model context.
2. Parse supported source languages into path-independent AST facts and retain
   explicit coverage records for binaries, generated files, unsupported
   languages, parse failures, exclusions, and dependency-only artifacts.
3. Construct a typed graph of modules, symbols, imports, calls, effects,
   interfaces, schemas, tests, MCP tools, MCP++ descriptors, transports, and
   package implementations.
4. Compare reviewed expected contracts with actual reachable implementation
   paths in `ipfs_accelerate_py`, `ipfs_kit_py`, and `ipfs_datasets_py`.
5. Compile structural and protocol claims into typed proof obligations, route
   supported claims to deterministic solvers or kernels, cache exact receipts,
   and preserve unsupported or inconclusive results without promotion.
6. Attest selected proof receipts and private witness predicates through a
   capability-checked zero-knowledge backend when a real backend and approved
   threat model exist. Simulated ZK never grants authority.
7. Turn each current contract counterexample into a small, reproducible
   `CodeEditPacket` and a generated `ipfs_accelerate_py` bug or vulnerability
   task, with only the affected AST slice, contract IDs, counterexample,
   validation commands, and content-addressed expansion handles.
8. Refill goals and tasks from new static-analysis evidence while preserving
   bounded work, deduplication, leases, dependency guardrails, and exact
   invalidation.
9. Treat the drifted model server, orchestrator, scheduler, and agent
   supervisor as explicit versioned runtime components, prove their lifecycle
   and cross-component MCP++ contracts, and project their current
   counterexamples into the accelerator repair board.

## Current-state findings

- SwissKnife currently contains 5,771 tracked files and is TypeScript-heavy:
  2,079 `.ts`, 106 `.tsx`, 649 `.js`, 263 `.cjs`, and 46 `.mjs` files at the
  planning baseline.
- `AnalysisASTIndex` already supports deterministic incremental indexing,
  compact evidence references, and invalidation, but its canonical producer is
  currently `build_python_ast_blob_record()`. A polyglot producer is required
  before a whole SwissKnife semantic scan can be claimed.
- The accelerator already has reusable analysis, proof, cache, context,
  objective-refill, and code-edit packet modules. This program composes and
  extends those modules rather than creating a second control plane.
- `ipfs_datasets_py` provides knowledge-graph/Cypher AST machinery,
  bounded graph traversal, shared logic IR, TDFOL/CEC/SMT routing, proof
  caches, ZK adapters, and canonical multiformat identity helpers. In
  particular, `utils.cid_utils` supplies strict DAG-JSON/CIDv1 helpers while
  `logic.ir_core.identity` supplies the distinct domain-separated
  `ir-canonical-identity-v1` raw-codec profile. `logic.ipld_cid` and
  `logic.profile_g` are conformance inputs, not silently interchangeable
  canonicalizers. Those providers remain optional and proposal-tier until a
  supervisor-owned policy validates their exact capability and receipt.
- SwissKnife has explicit MCP++ connectors, descriptors, JSON schemas,
  capability registries, policy mediation, and package-specific adapter
  evidence. The scan must prove that declared tools reach real package
  registrations through the expected MCP++ path; a matching name or document
  is not sufficient.
- The current whole-tree shadow evidence disposes all 6,395 tracked paths but
  remains unsafe for completion reasoning: 3,109 of 3,369 parser-eligible
  paths retain typed parse failures. The warm repeat reused all 3,369 parser
  records. Coverage accounting and content-addressed reuse are present, but
  semantic coverage is not healthy enough to assert no drift.
- A separate host checkout of SwissKnife is newer than the integration
  superproject's pinned `swissknife` gitlink and has a different tracked-file
  population. `SCA-168` records their origins/commits/ancestry and makes one
  reviewed snapshot authority explicit; evidence from the two trees is never
  silently mixed.
- The datasets package has strong CID/IR identity, bounded GraphRAG, hammer
  receipt/cache, SMT/ATP, and availability-gated ZK building blocks, but it
  does not provide a ready-made repository-wide interprocedural contract
  analyzer. Its legacy proof and CID variants are not interchangeable trust
  roots. The accelerator must own the policy bridge and conformance tests.
- MCP++ descriptors, event receipts, and an optional dispatch pipeline exist,
  but the primary hierarchical `tools_dispatch` path can invoke handlers
  directly. A trace or descriptor match is not proof that the mandatory
  policy/schema pipeline mediated the call.
- The launch profile names Grok Build and Codex roles, while the recovered
  runtime selected one provider for broad implementation prompts and even
  invoked a model for `deterministic-only` work. Provider labels and per-task
  context budgets must become enforced runtime policy, not documentation.
- Existing SVD and SWR boards are historical implementation/release programs.
  This program uses a separate `SCA` namespace and state root so their evidence
  and retry histories are not rewritten.

## Scope contract

### Authoritative repository scope

The primary repository snapshot is the complete Git-tracked tree under
`swissknife/`, plus tracked modifications, staged changes, deletions, and
allowlisted untracked source/config overlays when dirty-tree analysis is
enabled.

Every tracked path must produce exactly one coverage disposition:

- semantic AST indexed;
- structured data/schema indexed;
- text/reference indexed;
- binary or generated artifact content-addressed and metadata-indexed;
- dependency/toolchain artifact represented by a lockfile or build identity;
- unsupported with a typed reason;
- parse failure with a typed reason; or
- excluded by an explicit reviewed policy rule.

No missing disposition is treated as clean coverage.

Every authoritative manifest, AST blob, graph root, contract, obligation,
receipt, and edit packet has a declared content-identity profile. The primary
artifact profile encodes strict deterministic DAG-JSON and uses lowercase
base32 CIDv1, the `dag-json` multicodec, and `sha2-256` multihash. Its plain
SHA-256 digest and CID multihash digest must be verified over the same exact
canonical bytes. Logic IR may use the separately named, domain-separated
`ir-canonical-identity-v1` raw-codec profile. Cross-profile equality is never
inferred from matching payloads or digests; profile, canonicalization,
multibase, CID version, multicodec, and multihash are all identity metadata.

`node_modules`, `.git`, caches, Playwright output, transient test output, and
supervisor runtime directories are not source authority. Their content is not
recursively indexed; package locks, tool versions, selected generated
manifests, and reviewed runtime receipts bind the relevant dependency and
execution identity.

### Provider comparison scope

The provider scan covers the public MCP/MCP++ registration, schema,
dispatch, policy, transport, and implementation surfaces in:

- `external/ipfs_accelerate`;
- `external/ipfs_kit`;
- `external/ipfs_datasets`; and
- the interoperability schemas and conformance vectors in `Mcp-Plus-Plus`.

The provider repositories do not need an unrelated whole-tree semantic index
to prove a SwissKnife invocation contract. Their exact in-scope path manifest
and Git identities are part of each receipt.

### Runtime-component scope

The runtime drift catalog has four named component roots:

- `model-server`: the Hugging Face server, MCP AI-model facades, native model
  tools, model loading/cache, batching/queueing, auth, health, and transport
  schemas;
- `orchestrator`: P2P task orchestration, lifecycle orchestration, dispatch,
  cancellation, retry, ownership, and result publication;
- `scheduler`: deterministic/P2P workflow scheduling, MCP++ workflow and risk
  schedulers, supervisor resource/provider schedulers, leases, fencing,
  capacity, fairness, and backpressure; and
- `agent-supervisor`: objective/goal/subgoal/task materialization, task
  sources, control plane, lane lifecycle, durable state, refill, validation,
  proof admission, implementation, and merge reconciliation.

Each component records canonical and compatibility entrypoints separately.
Duplicate servers, schedulers, registries, or control paths are contradictions
unless a reviewed adapter contract proves their version and semantics. The
catalog also binds the corresponding SwissKnife descriptors/connectors and the
actual package registrations in `ipfs_accelerate_py`, `ipfs_kit_py`, and
`ipfs_datasets_py`.

## Authority model

The analysis keeps these classes distinct:

| Evidence | Use | Authority |
| --- | --- | --- |
| File inventory, AST, schema, and call facts | Exact structural premises | Observation bound to one snapshot |
| BM25/vector/GraphRAG result | Candidate discovery and ranking | Context only |
| Test or runtime trace | Bounded behavior observation | Observation only |
| SMT/ATP/model-check result | Refutation or proof candidate | Candidate unless independently checked |
| Kernel-checked proof | Discharge a reviewed supported obligation | Authoritative under exact bindings |
| Cryptographic/ZK attestation | Prove possession or a reviewed predicate without revealing its witness | Attested only with a real backend and approved policy |
| LLM output | Proposed code or plan | Never proof or completion authority |

Expected behavior is resolved in this order:

1. Versioned MCP-IDL, JSON Schema, typed public interface, or reviewed policy
   contract.
2. Canonical conformance vector or executable contract test bound to that
   interface version.
3. Package tool registration and schema publication.
4. Reviewed manifest or release gate.
5. Documentation or inferred behavior, which may nominate a contract but
   cannot become authoritative until reviewed and assigned a contract ID.

Conflicting authorities produce an explicit contradiction; the analyzer must
not silently pick one.

## Target graph

```text
RepositorySnapshot
  -> ContentIdentity(profile, canonical bytes, digest, CID)
  -> File -> Module -> Symbol -> Call/Import/Effect
  -> Schema/IDL -> Interface -> Method/Tool
  -> SwissKnife registry/descriptor/adapter
  -> MCP++ connector -> tools/list or tools/call
  -> package MCP registration -> handler -> implementation
  -> policy/authorization/transport/failure envelope
  -> ContractClaim -> ProofObligation -> ProofReceipt
  -> Counterexample -> CodeEditPacket -> generated repair task
```

GraphRAG is used to find candidate neighborhoods. Mandatory proof dependencies
are completed by deterministic typed-edge closure over the pinned graph.

## Contract claim families

The reviewed property catalog must support at least:

- `DeclaredToolExists`: a SwissKnife-declared tool exists in the selected
  package's canonical MCP tool registry.
- `DescriptorSchemaMatches`: MCP++ descriptor inputs and outputs are compatible
  with the package-published schema under the selected version.
- `InvocationReachable`: the declared SwissKnife call path reaches a concrete
  package handler through an allowlisted MCP++ dispatch edge.
- `ArgumentsPreserved`: required arguments, defaults, names, and types survive
  registry, envelope, transport, facade, and handler translation.
- `ResultEnvelopePreserved`: success, error, streaming, provenance, and
  content-envelope semantics are compatible at each boundary.
- `PolicyBeforeEffect`: authentication, UCAN/deontic policy, lease/fence, and
  authorization checks dominate every mutation-capable effect.
- `NoCompatibilityBypass`: a compatibility endpoint cannot silently bypass
  MCP++ policy, schema, provenance, or receipt requirements.
- `TransportParity`: HTTP, stdio, WebSocket, and libp2p routes expose only
  reviewed differences and preserve common method semantics.
- `DiscoveryExecutionParity`: `tools/list` or hierarchical facade discovery
  agrees with `tools/call` reachability.
- `FailureParity`: unsupported, unavailable, denied, timed-out, malformed, and
  partial states remain distinguishable end to end.
- `SnapshotFreshness`: every claim, graph edge, cache hit, and attestation binds
  the exact repository, submodule, schema, policy, toolchain, and capability
  roots that affect it.
- `NoDynamicAuthority`: unresolved dynamic dispatch, unknown schema, truncated
  mandatory closure, or provider degradation cannot be reported as proved.
- `CanonicalImplementationSelected`: every public runtime operation resolves
  to one reviewed canonical implementation or an explicit versioned adapter;
  shadow copies and unreviewed fallbacks are refuted.
- `LifecycleStateMachineConforms`: model, job, task, lease, lane, goal,
  subgoal, and scheduler transitions respect versioned preconditions,
  terminal states, cancellation, timeout, retry, and recovery semantics.
- `LeaseFenceBeforeEffect`: current lease ownership and fencing-token
  validation dominate every distributed or repository-mutating effect.
- `QueueAccountingConserved`: admission, reservation, running, retry,
  completion, cancellation, and failure transitions neither lose nor
  duplicate work under the modeled concurrency bounds.
- `ModelSelectionPreserved`: model identity, revision, hardware/backend,
  capability, generation parameters, cache identity, and result provenance
  survive SwissKnife, MCP++, model-server, and package boundaries.
- `GoalTaskClosure`: every active supervisor goal/subgoal has bounded
  satisfiable work or typed blocked evidence; task completion cannot imply
  goal completion without current acceptance, analyzer-health, and exhaustion
  receipts.
- `DeterministicOnlyMeansNoModel`: a task marked deterministic-only executes
  only an allowlisted typed local operation and records a zero-model receipt.
- `ProviderContextBounded`: Grok and Codex receive only a current
  counterexample/edit packet within the task hard limit; provider choice,
  fallback, review order, quota, and redaction are recorded.

Semantic product behavior that is not represented by a reviewed formal model
remains `unsupported` or `not_measured`; structural proof does not imply full
functional correctness.

## Pipeline

### 1. Snapshot and coverage

Create a canonical manifest from Git trees and the in-scope working-tree
overlay. Hash every path, assign a coverage disposition, and record recursive
submodule identities. Dirty and untracked inputs that can affect analysis must
change the snapshot identity.

### 2. Canonical multiformat identity

Add one accelerator-owned bridge over the datasets CID, multihash, and logic
identity modules. It emits a typed identity record containing canonicalization
profile, byte length, SHA-256 digest, CID text, CID version, multibase,
multicodec, and multihash. It decodes and validates every CID and checks that
the multihash digest is the digest of the retained canonical bytes.

Use strict DAG-JSON/CIDv1 for protocol artifacts and the domain-separated raw
IR profile only where its domain and schema-version envelope is required.
Conformance tests compare `utils.cid_utils`, `logic.ir_core.identity`,
`logic.ipld_cid`, and `logic.profile_g`; any canonical-byte or codec difference
is a typed profile contradiction, never an alias. Missing optional
`multiformats` support fails closed for CID-required operations and must not
produce a digest-shaped value labeled as a CID.

### 3. Polyglot AST extraction

Keep `ASTBlobRecord` as the compact path-independent interchange record.
Add deterministic TypeScript/JavaScript/TSX/JSX extraction through the local
TypeScript compiler API, with bounded parsing and no model calls. Add adapters
for Python and structured schemas. Store source bodies in CAS, not in index
rows or prompts.

### 4. Graph and retrieval

Project AST and schema facts into `CodeEvidenceGraph` and the datasets
knowledge-graph representation. Store content IDs and provenance on every node
and edge. Use BM25/vector/GraphRAG only for candidate seeds; complete required
call, contract, policy, and implementation dependencies with deterministic
closure.

### 5. MCP++ contract extraction

Extract SwissKnife descriptors, registries, generated app bindings, connector
methods, direct fetches, compatibility routes, and tests. Extract the actual
MCP registrations and schemas from the three Python packages. Normalize both
sides into one versioned `McpContractCatalog` and retain source precedence.

Build a separate `RuntimeComponentCatalog` over the model server,
orchestrator, scheduler, and supervisor. It inventories canonical and legacy
entrypoints, schemas, state machines, persistence roots, policy checks,
transports, dispatch adapters, duplicate implementations, and the exact
SwissKnife/MCP++ route expected to reach each operation.

### 6. Symbolic obligations

Compile catalog entries and call paths into a small logic IR. Prefer
deterministic graph reachability and schema-subtyping checks; use
`ipfs_datasets_py` TDFOL/CEC/SMT backends only for claim families they
explicitly support. Require proof-capability probing and preserve
unsupported/inconclusive states.

### 7. Cache and attestation

Use the accelerator `TrustAwareProofCache` as the only authoritative proof
receipt cache. Keys bind snapshot, scope, property/catalog version, premises,
assumptions, solver/toolchain, policy, capability report, and required
assurance. Every component is referenced by its declared content-identity
profile and CID; the cache also verifies retained canonical bytes against the
bound multihash. Cache hits re-derive assurance and never upgrade it.

ZK is a later attestation layer. It may prove possession of a valid receipt,
membership of a receipt in a committed result set, or satisfaction of a
reviewed predicate over a private witness. It does not discover code
correctness and cannot conceal a missing proof. Public inputs bind the receipt,
property, snapshot, policy, backend/setup, and result-set root CIDs, including
their identity-profile IDs. Simulation stays below `ATTESTED`.

### 8. Mismatch and vulnerability refinement

Each refuted or stale claim emits a typed counterexample. Security-sensitive
families are classified with CWE/OWASP/CAPEC references only when the
deterministic rule's premises are present. Severity and exploitability remain
separate. Unknown dynamic behavior is not automatically labeled vulnerable.

The refinery deduplicates by:

```text
snapshot + contract_id + claim_family + affected_symbol_set + counterexample
```

It writes an `ipfs_accelerate_py` repair board whose tasks include only:

- contract and obligation IDs;
- exact affected symbols and paths;
- bounded call/contract slice;
- counterexample and failed premise;
- expected postcondition;
- validation and re-proof commands;
- receipt/CAS expansion handles; and
- read/write path allowlists.

### 9. Autonomous implementation

One lease-protected coordinator runs four deterministic implementation shards.
Each task executes in an isolated Git worktree. Canonical task claims prevent
duplicate execution, declared path scopes prevent unordered write overlap, and
one shared merge queue serializes integration into the reviewed parallel
branch. Only the primary shard performs objective/codebase refill and
taskboard maintenance.

During bootstrap, shards have explicit Grok or Codex provider identities so
the declared provider does not silently resolve to another executable.
`SCA-167` then makes task metadata authoritative: deterministic-only work uses
a typed local runner with zero model calls; implementable
`CodeEditPacket` work routes first to Grok Build and then to an independent,
bounded Codex review/repair step. No provider receives the repository corpus.
Model invocation begins only after a deterministic mismatch packet exists and
uses obligation-first context.

Generated patches remain proposals. Validation, re-proof, protected-path
checks, task dependencies, retry budgets, and current-snapshot completion
evidence decide admission.

## Refill policy

Objective refill runs when open work falls below the configured threshold.
Static refill consumes only typed analyzer findings with a goal lineage,
content identity, current snapshot, severity/confidence fields, and a
reproduction or proof obligation.

New work is bounded by depth, breadth, open-task count, finding count, and
cooldown. Duplicate or stale findings update existing evidence rather than
creating tasks. Analyzer health gates block "no findings" conclusions when
coverage, parser health, canaries, or provider capability is insufficient.

## Delivery waves

| Wave | Tasks | Exit condition |
| --- | --- | --- |
| 0 | SCA-000, 010 | Plan and exact snapshot implementation complete |
| 1 | SCA-015, 020, 040 | Identity/AST and catalog branches overlap |
| 2 | SCA-021, 030, 041, 042 | Index/graph and expected/actual extraction overlap |
| 3 | SCA-050, 051, 060, 061, 080 | Invocation/logic chain fans out to prover and ZK policy |
| 4 | SCA-070, 081, 090, 091 | Cache/attestation and mismatch/security branches overlap |
| 5 | SCA-100, 101, 110, 111 | Packets, refinery, runtime, and providers converge |
| 6 | SCA-120 | Exhaustive health-gated repository baseline |
| 7 | SCA-150, 166, 167, 168 | Parser/provider recovery, evaluation, and snapshot-authority reconciliation |
| 8 | SCA-170, 171, 172, 173, 174 | Runtime manifest followed by four parallel component extractors |
| 9 | SCA-175, 176, 177 | Runtime state-machine obligations, MCP++ reachability, and vulnerability rules |
| 10 | SCA-200 | Complete graph/proof/cache/mismatch baseline after health recovery |
| 11 | SCA-121, 130, 140, 178, 179, 180, 181 | Repair/refill projection, benchmark, healthy runtime baseline, and held-out evaluation |
| 12 | SCA-160 | Promotion and rollout closeout after runtime evidence |

## Success gates

- 100 percent of tracked SwissKnife paths have a coverage disposition.
- Every authoritative artifact carries a validated identity profile and CID;
  its decoded multihash equals the digest of the exact retained canonical
  bytes, and cross-profile identities are never conflated.
- 100 percent of supported source files are indexed or carry a typed parse
  failure; no silent parser drop. Promotion additionally requires parser
  health within the reviewed per-language threshold or explicit unsupported
  coverage that cannot hide an in-scope contract surface.
- All canonical SwissKnife MCP tool declarations join to exactly one of
  `reachable`, `refuted`, `ambiguous`, `unsupported`, or `not_measured`.
- Zero GraphRAG, model, test, static observation, or simulated-ZK result is
  promoted to kernel or attested authority.
- Warm unchanged scans avoid reparsing and re-proving at least 95 percent of
  unchanged blobs/obligations.
- A one-symbol change invalidates all and only the transitive dependent
  contracts on controlled fixtures.
- Generated LLM packets remain under 8,192 input tokens, with a target median
  below 2,048; repository size does not directly determine prompt size.
- Seeded descriptor/schema/dispatch/policy/failure vulnerabilities are found
  with zero false authoritative admissions.
- Every generated repair task reproduces on its source snapshot and closes
  only after current-tree validation and re-proof.
- Every model-server, orchestrator, scheduler, and supervisor operation has a
  versioned terminal contract state, including duplicate/legacy paths and the
  exact MCP++ mediation result.
- Every deterministic-only task has a receipt proving zero provider calls;
  every provider task records its selected provider, bounded packet size,
  fallback/review chain, and admission result.
- The four-shard coordinator remains healthy, lease-protected, refill-bounded,
  conflict-checked, and restartable from per-lane durable state.

## Non-goals

- Proving arbitrary product semantics from source text.
- Treating documentation, embeddings, GraphRAG, tests, or LLM output as a
  theorem.
- Recursively indexing `node_modules` or runtime caches as source authority.
- A second proof-cache trust root.
- ZK as a substitute for program proof or as a way to hide missing evidence.
- Parallel workers outside the one lease-owning coordinator or without
  isolated worktrees and serialized merge admission.
- Broad model-driven repository review before a symbolic mismatch exists.
