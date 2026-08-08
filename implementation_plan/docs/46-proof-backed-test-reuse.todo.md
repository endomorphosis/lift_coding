# Proof-Backed Test Reuse Taskboard (PTR)

Consumable by `ipfs_accelerate_py.agent_supervisor` with task prefix
`## PTR-`. Companion goal heap:
`implementation_plan/docs/46-proof-backed-test-reuse.objectives.md`.

## Normative execution contract

- Only an exact trusted prior pass receipt plus a policy-admitted, locally
  verified real certificate may authorize `pytest.skip`.
- CID proves content identity, while AST and runtime traces scope invalidation;
  neither is pass authority alone.
- Any missing, unavailable, corrupt, stale, revoked, incompatible, timed-out, or
  exceptional optional dependency executes the test normally.
- Simulated ZK never authorizes a skip.
- All validations force `IPFS_TEST_PROOF_REUSE_MODE=off` so this implementation
  cannot validate itself from its own cache.
- Three strict numeric shards use isolated worktrees and a shared serial merge
  queue. No concurrency override bypasses a predicted-file or gitlink conflict.
- Planning, objective, board, scheduler profile, validator, and controller files
  are protected from managed implementation agents.

## Historical initial execution wave

`PTR-000` is the operator-authored planning seal. At the original sealed-board
launch, the initial claimable tasks were exactly `PTR-001`, `PTR-002`, and
`PTR-003`, mapping one task to each of the three numeric shards. Waiting tasks
were normal and became selectable only after their declared dependencies
completed. The active claimable wave is defined by the reviewed runtime repair
below.

## Reviewed objective-completion expansion

The original 32-task implementation population is complete, while the
authority projection remains 0 of 12 goals because current bound completion
artifacts do not yet exist. The reviewed 2026-08-03 expansion adds `PTR-108`,
`PTR-109`, `PTR-110`, `PTR-111`, `PTR-112`, `PTR-120`, `PTR-121`,
`PTR-122`, and `PTR-130`. Its first claimable wave is exactly `PTR-108`,
`PTR-109`, and `PTR-110`, one task and one distinct repository resource on
each strict numeric shard. At that projection revision, task completion remained
only implementation progress and the operator-owned closeout command could run
after all 41 tasks closed. The current 53-task closeout condition is defined by
the runtime-activation repair below; the outer controller remains the only path
allowed to project verified goal state.

## Historical runtime-activation repair

The completion expansion is now historical and closed. A 2026-08-03 runtime
audit found that proof-reuse components exist but ordinary direct-node pytest
execution still lacks a complete default composition path: current execution
context cannot be reconstructed safely from a locator alone, the exact
candidate context is not retained as immutable canonical bytes, deferred proof
issuance is not fully typed across the repository boundary, and repository
bootstraps still need a tested zero-configuration path. The bounded repair is
`PTR-131` through `PTR-142`. Its historical first wave was exactly `PTR-131`,
`PTR-132`, and `PTR-133`, one accelerator, datasets, and kit claim on the three
numeric shards. A second repository-parallel bootstrap wave is `PTR-139`,
`PTR-140`, and `PTR-141`. `PTR-142` refreshes current-tree assurance and the
operator handoff after all 53 tasks are closed. Every cache or proof dependency
remains optional: inability to construct, load, rehash, revalidate, prove, or
verify a candidate always produces a typed RUN/DEFERRED result and executes the
test.

## Reviewed production-runtime activation correction

A current-tree audit supersedes the production-activation claims attached to
`PTR-138`, `PTR-140`, and `PTR-142` without rewriting their historical
completion records. Their isolated and injected fixtures did not prove the
ordinary default path: collection still required runtime evidence before it
could create a locator, the configured revalidator used the certificate store
instead of the candidate-context store and had no production current-context
provider, the cold path never started the runtime tracer or published a complete
candidate, the default issuer had no real prover, and the purported e2e built a
deterministic pseudo-certificate or manually injected item/services rather than
running two independent direct-node pytest processes.

The reviewed corrective population now covers `PTR-143` through `PTR-155`, with
the dependency-ordered `PTR-149` operator handoff deliberately last, bringing
the sealed population to 66 tasks. `PTR-143` through `PTR-148` retain their
historical completion identities, but their pre-v4 evidence cannot authorize
closeout. The initial claimable wave is exactly `PTR-150` and `PTR-151` on
numeric shards 0 and 1, owning accelerator and datasets without predicted-file
overlap. `PTR-152` joins both branches on shard 2 and establishes the fail-closed
authority boundary. `PTR-153` and `PTR-154` then preserve proof-bearing issued
material and controller-owned expected context in parallel on shards 0 and 1;
`PTR-155` joins them on shard 2 before `PTR-149` evaluates the exact 66-task
authority gate. Historical `PTR-142`, 53-task, pre-v4 60-task, or pre-material
63-task evidence cannot satisfy this production-activation premise. Missing
trusted setup, reviewed current v4 keys, native compiler, network, endpoint,
cache, or optional package always leaves a typed activation gap and runs tests;
it never blocks the supervisor or manufactures skip/closeout authority.

## Reviewed authenticated-receipt current-tree repair

A 2026-08-08 audit found that the historical 66-task completion projection is
not current execution authority. The datasets and kit gitlink objects recorded
by that projection are no longer fetchable from their configured remotes, 26
unique declared outputs are absent from the reachable repository trees, the
ordinary locator-only warm lookup is filtered out before two-stage
revalidation, and the existing test-pass witness does not bind a verifiable
runner signature. Historical status records remain provenance only.

The bounded corrective population is `PTR-160` through `PTR-170`, bringing the
sealed population to 77 tasks. Its original v6 claimable wave was `PTR-160`,
`PTR-161`, and `PTR-162`, one accelerator, datasets, and kit task on three
distinct numeric shards. A post-merge isolated-import audit proved that the
datasets bridge fails on a namespace-only empty accelerator hierarchy and that
the kit bridge hides an incomplete regular accelerator package. `PTR-160`
remains completed; `PTR-161` and `PTR-162` are therefore reopened. Live v7
retry evidence then exposed a control-plane defect: oversized nested failure
reviews are normalized into a synthetic `implementation_setup` exception while
the real failed validation is relabeled `not_run`, causing exact retries with no
actionable counterexample. The reviewed v8 refill adds `PTR-170`, and makes both
reopened bootstrap tasks wait for it. The current v8 claimable wave is exactly
`PTR-170` on numeric shard 2; after it merges, `PTR-161` and `PTR-162` become the
parallel frontier on shards 2 and 0. `PTR-163` and `PTR-165` remain waiting for
those declared dependencies. The repair authenticates pass
receipts, restores cold-safe package-owned pytest bridges, binds the real proof
statement to the runner attestation, validates completed-task artifacts and
gitlinks, replays only verified historical changes, and proves a genuine
three-repository cold/warm/forced-replay lifecycle. Every new runtime task uses
Grok 4.5 first when ready. The canonical `ipfs_accelerate_py.llm_router` agent
route automatically selects Codex `gpt-5.6-terra` at high reasoning for
confirmed quota exhaustion, authentication failure, or launch unavailability
while the worktree remains unchanged. Generic task/process failure, timeout,
malformed output, transport failure, or any detected side effect remains
terminal and cannot trigger a second provider. The process runner is only a
thin stdin/worktree adapter and sanitizer. This provider transition remains
proposal-only and cannot bypass task validation, merge,
authenticated-receipt, or current-tree gates. Until
`PTR-169` closes, old closeout packets cannot authorize rollout and all
uncertain candidates execute normally.

## PTR-000 Seal the supervisor-native program

- Status: completed
- Completion: manual
- Completion evidence: Operator-authored plan, goal heap, executable board, scheduler profile, fail-closed validator, and isolated controller committed on the target branch before launch.
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: planning
- Depends on:
- Goal id: PTR-G000
- Outputs: implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md, implementation_plan/docs/46-proof-backed-test-reuse.objectives.md, implementation_plan/docs/46-proof-backed-test-reuse.todo.md, config/proof_backed_test_reuse_supervisor.json, scripts/validate_proof_backed_test_reuse_board.py, scripts/proof_backed_test_reuse_supervisor.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 scripts/validate_proof_backed_test_reuse_board.py && python3 -m json.tool config/proof_backed_test_reuse_supervisor.json >/dev/null && python3 -m py_compile scripts/validate_proof_backed_test_reuse_board.py scripts/proof_backed_test_reuse_supervisor.py
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/planning
- Parallel lane: ptr-planning
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md, implementation_plan/docs/46-proof-backed-test-reuse.objectives.md, implementation_plan/docs/46-proof-backed-test-reuse.todo.md, config/proof_backed_test_reuse_supervisor.json, scripts/validate_proof_backed_test_reuse_board.py, scripts/proof_backed_test_reuse_supervisor.py
- Predicted symbols: PTR objective graph, PTR task DAG, PTR runtime profile, PTR controller
- Interfaces: ObjectiveGraph, MarkdownTaskSource, ImplementationSupervisor
- Submodules:
- Generated artifacts: none
- Conflict policy: Own only the PTR planning/control namespace and preserve every prior board and runtime history.
- Symbolic first: true
- LLM context budget bytes: 32768
- Provider role: operator-only
- Context budget tokens: 0
- Preconditions: Current outer accelerator, datasets, and kit gitlinks resolve to clean exact commits.
- Effects: Seals reviewed implementation intent and launch bounds without changing package implementation.
- Evidence subset: PTR planning seal and board validator receipt
- Acceptance: Prefix, namespace, branch, protected paths, three outer worktree submodules, three strict shards, trust doctrine, and optional-capability policy are fixed; validator passes; initial claimable tasks are exactly PTR-001, PTR-002, and PTR-003.

## PTR-001 Define test-execution proof contracts

- Status: completed
- Completion: manual
- Completion evidence: Operator-reviewed accelerator commit 505eb5697; the declared contract suite passed 18/18 with proof reuse forced off, and proposal secret admission was rechecked with an approved scoped synthetic canary while production credential material remained rejected.
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: foundation-contracts
- Depends on: PTR-000
- Goal id: PTR-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_contracts.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_contracts.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/contracts
- Parallel lane: ptr-contracts
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_contracts.py
- Predicted symbols: TestLocatorKey, TestExecutionKey, TestPassReceipt, TestProofCertificate, ReuseDecision, ReuseReasonCode
- Interfaces: TestLocatorKey@1, TestExecutionKey@1, TestPassReceipt@1, TestProofCertificate@1, ReuseDecision@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Add finite typed records under the existing proof authority model; do not create a parallel trust root.
- Symbolic first: true
- LLM context budget bytes: 32768
- Provider role: grok-implement
- Context budget tokens: 8192
- Preconditions: PTR trust invariants and canonical artifact profile are reviewed.
- Effects: Defines the only records allowed to cross collection, cache, proving, and supervisor-validation boundaries.
- Evidence subset: Existing proof dataclasses, canonical serializers, authority enums, and completion-evidence contracts
- Acceptance: Schemas reject nonfinite, unbounded, private, malformed, versionless, and illegal-authority inputs; serialization is deterministic; decision action is explicitly RUN or SKIP; absence and exceptions cannot coerce to SKIP.

## PTR-002 Publish the ZK receipt threat model and authority doctrine

- Status: completed
- Completion: manual
- Completion evidence: Integrated merge d42f4a78a and immutable merge-train receipt 45d96c257af5380dbcfcfe751a524504f0360d2d504b378847e3c8446982051a; the current declared doctrine suite passed 14/14 with proof reuse forced off.
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: threat-policy
- Depends on: PTR-000
- Goal id: PTR-G010
- Outputs: external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_ZK_THREAT_MODEL.md, external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_reuse_doctrine.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_reuse_doctrine.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/threat-model
- Parallel lane: ptr-threat-policy
- Resource class: security-review
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_ZK_THREAT_MODEL.md, external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_reuse_doctrine.py
- Predicted symbols: TestPassStatementV1 threat model, reuse authority lattice
- Interfaces: ProofAuthority, TestPassStatementV1, ZkThreatModel@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Preserve CBP proof doctrine; document test-specific attacks and controls without promoting observations into proof.
- Symbolic first: true
- LLM context budget bytes: 32768
- Provider role: codex-implement
- Context budget tokens: 8192
- Preconditions: Human PTR plan and existing CBP/SCA proof policies are available.
- Effects: Makes replay, substitution, trace incompleteness, key/circuit confusion, witness leakage, and downgrade protections executable doctrine.
- Evidence subset: CBP threat policy, existing ZK adapter tests, proof-attestation authority contracts
- Acceptance: Doctrine states that ZK proves possession of the exact trusted pass receipt, AST similarity never means pass, a CID only identifies bytes, simulated ZK never skips, and every uncertainty executes the test.

## PTR-003 Implement lazy test-reuse capability probes

- Status: completed
- Completion: manual
- Completion evidence: Integrated PTR-003 merge history through 04e9373ac with completed merge-train receipts; the current declared lazy-capability suite passed 24/24 with proof reuse forced off.
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: capability-probe
- Depends on: PTR-000
- Goal id: PTR-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/test_reuse_capabilities.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_capabilities.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_capabilities.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/capabilities
- Parallel lane: ptr-capabilities
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/test_reuse_capabilities.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_capabilities.py
- Predicted symbols: TestReuseCapability, TestReuseCapabilityReport, probe_test_reuse_capabilities
- Interfaces: TestReuseCapabilityReport@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Probe imports/configuration/binaries with strict bounds; never install packages, contact endpoints, start daemons, or create caches.
- Symbolic first: true
- LLM context budget bytes: 32768
- Provider role: codex-implement
- Context budget tokens: 8192
- Preconditions: Optional provider names and environment contracts are documented.
- Effects: Reports multiformats, datasets ZK, Groth16, ProveKit, cache, IPFS, and local verifier availability as typed facts.
- Evidence subset: Import specs, configured paths, backend registries, and cold capability metadata
- Acceptance: Cold probes are lazy, deterministic, bounded, side-effect free, and distinguish available, disabled, missing, incompatible, and unknown; every unavailable optional capability is non-blocking.

## PTR-010 Implement core locator and execution identity

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: identity-core
- Depends on: PTR-001
- Goal id: PTR-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_execution_identity.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/identity-core
- Parallel lane: ptr-identity-core
- Resource class: cpu-small
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_execution_identity.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity.py
- Predicted symbols: TestExecutionIdentityCompiler, compile_test_locator, compile_test_execution_key
- Interfaces: TestExecutionIdentityCompiler@1, ContentIdentity@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Extend the canonical content-identity bridge; never label a fallback digest or kit pseudo-hash as a CID.
- Symbolic first: true
- LLM context budget bytes: 40960
- Provider role: grok-implement
- Context budget tokens: 10240
- Preconditions: PTR-001 contracts exist and datasets/multiformats adapters remain lazy.
- Effects: Produces strict locator and execution artifacts binding node ID, forest, source/AST, context roots, and policy.
- Evidence subset: ContentIdentity bridge, repository snapshots, pytest node IDs, canonical JSON and multiformats vectors
- Acceptance: Exact inputs produce stable CIDv1/base32/dag-json/sha2-256 values; any bound change changes the execution CID; retained canonical bytes decode and rehash; missing CID support returns non-reusable.

## PTR-011 Compile fixtures, hooks, parameters, dependencies, and environment identity

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: identity-components
- Depends on: PTR-001
- Goal id: PTR-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_identity_components.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_identity_components.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_identity_components.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/identity-components
- Parallel lane: ptr-identity-components
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_identity_components.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_identity_components.py
- Predicted symbols: TestIdentityComponents, canonicalize_pytest_parameter, collect_fixture_hook_identity, collect_environment_identity
- Interfaces: TestIdentityComponents@1, TestExecutionKey@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Canonicalize only reviewed finite types; unsupported parameters and uncontrolled inputs become explicit non-reusable reasons.
- Symbolic first: true
- LLM context budget bytes: 40960
- Provider role: codex-implement
- Context budget tokens: 10240
- Preconditions: PTR-001 schemas define bounded component records.
- Effects: Supplies parameter, fixture, conftest, hook, lock/distribution, interpreter, environment, and capability roots to the execution compiler.
- Evidence subset: Pytest fixture manager, conftest hierarchy, installed distributions, lock files, allowlisted environment and platform facts
- Acceptance: Parameters are canonical or rejected; fixture definitions/scopes/values, hooks/plugins, locks/distributions, environment, interpreter, platform, hardware, and capability inputs are bound with privacy-safe allowlists.

## PTR-012 Add independent cross-package CID identity vectors

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: identity-vectors
- Depends on: PTR-010, PTR-011
- Goal id: PTR-G020
- Outputs: external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/identity-vectors
- Parallel lane: ptr-identity-vectors
- Resource class: cpu-small
- Implementation timeout seconds: 5400
- Predicted files: external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py
- Predicted symbols: cross-package execution identity known vectors
- Interfaces: ContentIdentity@1, cid_utils, multiformats.CID, multiformats.multihash
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Independently reproduce the same bytes/digest/CID through datasets and multiformats; do not merely round-trip one implementation.
- Symbolic first: true
- LLM context budget bytes: 32768
- Provider role: codex-implement
- Context budget tokens: 8192
- Preconditions: PTR-010 and PTR-011 expose canonical retained payloads.
- Effects: Prevents cross-package canonicalization drift and fake CID admission.
- Evidence subset: Strict DAG-JSON vectors, decoded multihash digests, invalid legacy kit hash strings
- Acceptance: Known vectors match independently under CIDv1/base32/dag-json/sha2-256; codec/base/version/digest differences are typed contradictions; legacy pseudo-CIDs and malformed multihashes are rejected.

## PTR-020 Implement static AST dependency tracing

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: static-trace
- Depends on: PTR-010, PTR-011
- Goal id: PTR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_static_dependency_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_static_dependency_trace.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_static_dependency_trace.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/static-trace
- Parallel lane: ptr-static-trace
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_static_dependency_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_static_dependency_trace.py
- Predicted symbols: StaticTestDependencyTracer, StaticTestDependencyTrace, UnknownDependencyFrontier
- Interfaces: StaticTestDependencyTrace@1, AnalysisASTIndex
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Extend existing AST records and import closure; unknown dynamic edges remain visible and block narrow eligibility.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: codex-implement
- Context budget tokens: 12288
- Preconditions: Exact identity components and AST content records exist.
- Effects: Computes test/import/fixture/conftest/hook/config/data/effect closure with source spans, tool identity, and analyzer health.
- Evidence subset: AnalysisASTIndex, Python AST, import resolution, fixture graph, configuration and effect references
- Acceptance: Closure is deterministic and content addressed; dynamic imports, reflection, native code, opaque decorators, missing files, and analysis bounds produce an explicit unknown frontier; no source body is persisted in index rows.

## PTR-021 Implement bounded runtime dependency tracing

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime-trace
- Depends on: PTR-001, PTR-010
- Goal id: PTR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_runtime_dependency_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_runtime_dependency_trace.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_runtime_dependency_trace.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/runtime-trace
- Parallel lane: ptr-runtime-trace
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_runtime_dependency_trace.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_runtime_dependency_trace.py
- Predicted symbols: RuntimeTestDependencyTracer, RuntimeTestDependencyTrace, RuntimeTraceCompleteness
- Interfaces: RuntimeTestDependencyTrace@1, TestPassReceipt@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Observe bounded dependency identities only; never retain secrets, arbitrary output bodies, private paths, or unbounded payloads.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: codex-implement
- Context budget tokens: 12288
- Preconditions: Receipt contracts and execution identity are available.
- Effects: Records imported modules/code, file reads, allowlisted environment, subprocess tools, services, randomness/clock policy, hardware/capabilities, and tracer health for a cold execution.
- Evidence subset: Python audit/import hooks, pytest lifecycle, content identity and capability adapters
- Acceptance: Trace limits and instrumentation identity are bound; unsupported/overflow/private events make completeness false; no tracer failure changes the test outcome; results are canonical and safe to include by CID.

## PTR-022 Implement conservative reuse eligibility

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: trace-eligibility
- Depends on: PTR-020, PTR-021
- Goal id: PTR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_reuse_eligibility.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_eligibility.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_eligibility.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/eligibility
- Parallel lane: ptr-eligibility
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_reuse_eligibility.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_eligibility.py
- Predicted symbols: TestReuseEligibilityEvaluator, TestReuseEligibilityDecision
- Interfaces: TestReuseEligibilityDecision@1, StaticTestDependencyTrace@1, RuntimeTestDependencyTrace@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Prefer safe execution over narrow reuse; trace evidence scopes invalidation and cannot establish correctness.
- Symbolic first: true
- LLM context budget bytes: 40960
- Provider role: grok-implement
- Context budget tokens: 10240
- Preconditions: Static and runtime traces expose health, bounds, effects, and unknown frontiers.
- Effects: Classifies pure, snapshot-bound, repository-forest-bound, and non-reusable items with typed reasons.
- Evidence subset: Combined trace roots, effect adapters, environment/capability policy, current repository forest
- Acceptance: Rollout v1 binds the full admitted repository forest; uncontrolled effects, incomplete analysis, unsupported parameters, unaccounted dirty state, and missing adapters always return RUN; no heuristic similarity authorizes reuse.

## PTR-030 Adapt the trust-aware proof cache for test receipts

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: cache-authority
- Depends on: PTR-001, PTR-010, PTR-011
- Goal id: PTR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_cache.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_cache.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/cache-authority
- Parallel lane: ptr-cache-authority
- Resource class: io-artifact
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_cache.py
- Predicted symbols: TestProofCache, TestProofCacheAdmission, TestProofCacheLookup
- Interfaces: TrustAwareProofCache, ProverEvidenceStore, TestProofCache@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Use existing trust-aware cache and evidence-store authority; test adapters cannot create another trust root or trust serialized status flags.
- Symbolic first: true
- LLM context budget bytes: 40960
- Provider role: codex-implement
- Context budget tokens: 10240
- Preconditions: Test proof contracts and exact execution identities exist.
- Effects: Adds test-specific admission and lookup records while re-deriving current authority on every candidate.
- Evidence subset: TrustAwareProofCache, ProverEvidenceStore, proof authority and invalidation contracts
- Acceptance: Stale, poisoned, private, revoked, simulated, policy-mismatched, and CID-invalid candidates miss; lookup absence/errors are typed; mutable metadata cannot override immutable proof and current policy.

## PTR-031 Implement immutable certificate storage and fenced indexes

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: cache-storage
- Depends on: PTR-010, PTR-030
- Goal id: PTR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_certificate_store.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_certificate_store.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/certificate-store
- Parallel lane: ptr-certificate-store
- Resource class: io-artifact
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_certificate_store.py
- Predicted symbols: TestCertificateStore, ImmutableCertificateCAS, TestCertificateIndex, CertificateWriteFence
- Interfaces: TestCertificateStore@1, TrustAwareProofCache
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Immutable CID blobs are authority inputs and locator indexes are bounded hints; all writes are atomic and controller-fenced.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: grok-implement
- Context budget tokens: 12288
- Preconditions: Exact CID compiler and trust-aware cache admission exist.
- Effects: Stores receipts/certificates/traces by CID and maps locators to bounded candidates with TTL, revocation, quarantine, restart recovery, and xdist-safe single flight.
- Evidence subset: Atomic persistence helpers, content-addressed tiers, locking/fencing and revocation patterns
- Acceptance: Writes use temporary file, bounded canonical bytes, atomic replace, readback rehash, then index publication; partial/corrupt/oversized/symlink/path-escape cases miss safely; parallel writers cannot publish mixed authority.

## PTR-040 Define the datasets test-pass ZK statement

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-statement
- Depends on: PTR-001, PTR-002
- Goal id: PTR-G050
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-statement
- Parallel lane: ptr-datasets-statement
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py
- Predicted symbols: TestPassStatementV1, TestPassPublicInputs, TestPassPrivateWitness
- Interfaces: TestPassStatementV1, ZKPStatement
- Submodules: external/ipfs_datasets
- Generated artifacts: none
- Conflict policy: Extend the datasets ZKP statement protocol with the minimum test-specific predicate and no pytest or accelerator dependency.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: grok-implement
- Context budget tokens: 12288
- Preconditions: PTR receipt/certificate schemas and reviewed threat model exist.
- Effects: Defines public/private inputs and constraints for possession of an exact admitted complete-pass receipt.
- Evidence subset: Existing datasets statement/canonicalization/backend protocols and PTR authority doctrine
- Acceptance: Public inputs bind receipt, execution, policy, statement, circuit, verifier-key, issuer, and epoch identities; private witness is minimal; all three pytest phases must pass and disqualifying bits must be clear; malformed/nonfinite/private public data is rejected.

## PTR-041 Implement real test-execution certificate conformance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-certificate
- Depends on: PTR-003, PTR-040
- Goal id: PTR-G050
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_execution_certificate.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/provekit/test_pass_circuit.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-certificate
- Parallel lane: ptr-datasets-certificate
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_execution_certificate.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/provekit/test_pass_circuit.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py
- Predicted symbols: TestExecutionCertificate, TestPassCircuitBinding, verify_test_execution_certificate
- Interfaces: TestProofCertificate@1, Groth16Backend, ProveKitBackend
- Submodules: external/ipfs_datasets
- Generated artifacts: none
- Conflict policy: Bind existing real backend interfaces and pinned artifacts; no fallback or simulated backend can report attested authority.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: TestPassStatementV1 and typed capability results exist.
- Effects: Normalizes real Groth16/ProveKit proof artifacts and locally verifies exact public-input, circuit, key, issuer, and policy bindings.
- Evidence subset: Datasets ZKPProof, Groth16/ProveKit adapters, setup artifacts, verifier-key registry and public-input canonicalization
- Acceptance: Correct real fixtures verify; wrong circuit/key/issuer/policy/public inputs, malformed proof, replay, and simulated artifacts fail with typed reasons; unavailable real backends return non-authoritative unavailable without side effects.

## PTR-042 Implement deferred certificate issuance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-issuance
- Depends on: PTR-031, PTR-041
- Goal id: PTR-G050
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-issuance
- Parallel lane: ptr-datasets-issuance
- Resource class: cpu-proof-solver
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py
- Predicted symbols: TestCertificateIssuer, DeferredCertificateRequest, DeferredCertificateResult
- Interfaces: TestCertificateIssuer@1, TestPassStatementV1, TestCertificateStore@1
- Submodules: external/ipfs_datasets
- Generated artifacts: none
- Conflict policy: Proving runs only after immutable pass receipt storage and cannot change pytest pass status; remote communication is explicit and bounded; negative secret-leak tests use only reviewed synthetic canaries such as should-not-appear or test-only-api-key-value.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: codex-implement
- Context budget tokens: 12288
- Preconditions: Immutable store and real certificate verification contracts are stable.
- Effects: Queues or executes bounded real proving after a complete pass and stores verified results by CID.
- Evidence subset: ProveKit CLI/FFI, Groth16 endpoint adapters, witness manager, timeout/retry and artifact validation
- Acceptance: Endpoint/binary/cache outage records certificate_deferred without affecting the passed test; witness/public secret leakage is absent; retries are bounded/idempotent; only locally verified real outputs publish an index candidate; negative leakage tests use reviewed synthetic canaries such as should-not-appear or test-only-api-key-value.

## PTR-043 Add the lazy datasets certificate provider adapter

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-adapter
- Depends on: PTR-003, PTR-030, PTR-031, PTR-041
- Goal id: PTR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_test_certificate_provider.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_test_certificate_provider.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-adapter
- Parallel lane: ptr-datasets-adapter
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_test_certificate_provider.py
- Predicted symbols: IpfsDatasetsTestCertificateProvider, TestCertificateVerificationResult
- Interfaces: TestCertificateProvider@1, TestExecutionCertificate
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Keep datasets import and proving optional/lazy; verification and issuance are separate capabilities with typed failures.
- Symbolic first: true
- LLM context budget bytes: 40960
- Provider role: grok-implement
- Context budget tokens: 10240
- Preconditions: Capability, cache/store, and real certificate contracts exist.
- Effects: Gives the shared plugin a bounded local verification adapter and an optional deferred issuer handle.
- Evidence subset: Existing ipfs_datasets ZK attestation adapter, optional integration conventions, capability reports
- Acceptance: Cold import loads no datasets ZK backend; verify uses exact retained bytes and pinned inputs; prove is never invoked by lookup; missing/incompatible/timeout/exception states return RUN-compatible typed results; simulated authority is rejected.

## PTR-050 Implement the cold pytest plugin shell

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: pytest-shell
- Depends on: PTR-001
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/config.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/pytest-shell
- Parallel lane: ptr-pytest-shell
- Resource class: cpu-small
- Implementation timeout seconds: 7200
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/config.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py
- Predicted symbols: ProofReuseConfig, pytest_addoption, pytest_configure, pytest_collection_modifyitems
- Interfaces: pytest plugin, ProofReuseConfig@1, ReuseDecision@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Plugin import/configuration is pure and lazy; it cannot create storage, probe network, import a ZK backend, or start a daemon.
- Symbolic first: true
- LLM context budget bytes: 40960
- Provider role: codex-implement
- Context budget tokens: 10240
- Preconditions: Typed contracts define modes, decisions, and reason codes.
- Effects: Adds off/shadow/read/write/readwrite options, markers, collection metadata, and no-op provider seams.
- Evidence subset: Pytest hook specifications, hermetic environment controls, existing accelerator conftest and packaging
- Acceptance: Cold import works with every optional provider absent; off mode is behaviorally inert; invalid configuration degrades to off or an explicit configuration error before tests; required-audit remains separate; markers and collection work for direct nodes without a path registry.

## PTR-051 Implement candidate lookup and verified skip decisions

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: pytest-lookup
- Depends on: PTR-022, PTR-031, PTR-043, PTR-050
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lookup.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_lookup.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_pytest_proof_reuse_lookup.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/pytest-lookup
- Parallel lane: ptr-pytest-lookup
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lookup.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_lookup.py
- Predicted symbols: ProofReuseLookup, batch_lookup_reuse_decisions, apply_verified_skip
- Interfaces: TestCertificateStore@1, TestCertificateProvider@1, TestReuseEligibilityDecision@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Index lookup is a hint; recompute current identity and locally validate every immutable candidate before adding a standard pytest skip marker.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: codex-implement
- Context budget tokens: 12288
- Preconditions: Eligibility, store, datasets verifier adapter, and plugin shell are available.
- Effects: Batches collection lookup and attaches exact typed decisions/user properties to items before fixture setup.
- Evidence subset: Current execution identity, bounded candidate index, immutable certificates, local verification and policy admission
- Acceptance: Only an exact verified candidate yields `pytest.skip("proof-cache-hit:<cid>")`; every miss, timeout, parse error, provider error, stale input, unsupported item, or unexpected exception runs the test; lookup is bounded and performs no proving.

## PTR-052 Implement complete-pass receipt capture

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: pytest-receipt
- Depends on: PTR-021, PTR-030, PTR-042, PTR-050
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/pytest-receipt
- Parallel lane: ptr-pytest-receipt
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py
- Predicted symbols: TestPassReceiptCollector, pytest_runtest_logreport, finalize_test_pass_receipt
- Interfaces: TestPassReceipt@1, RuntimeTestDependencyTrace@1, TestCertificateIssuer@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Receipt capture is post-outcome and cannot override pytest status; proving is deferred beyond immutable receipt admission.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: grok-implement
- Context budget tokens: 12288
- Preconditions: Runtime trace, proof-cache admission, deferred issuer, and plugin shell exist.
- Effects: Aggregates setup/call/teardown reports and eligible trace/context into a canonical pass receipt and optional deferred proving request.
- Evidence subset: Pytest TestReport lifecycle, trace health, outcome policy, immutable receipt store
- Acceptance: Only complete setup+call+teardown pass creates a reusable receipt; skips, xfail/xpass, reruns, interruption, timeout, teardown failure, incomplete trace, and leaked resources do not; store/prover errors never change the test result.

## PTR-053 Complete xdist coordination and reporting

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: pytest-xdist
- Depends on: PTR-051, PTR-052
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/reporting.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/pytest-xdist
- Parallel lane: ptr-pytest-xdist
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/reporting.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py
- Predicted symbols: ProofReuseXdistCoordinator, ProofReuseSessionMetrics, pytest_sessionfinish
- Interfaces: pytest-xdist, TestCertificateStore@1, ProofReuseMetrics@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Workers may read verified immutable candidates; one controller publishes receipt/index state and failures disable writes rather than tests.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: codex-implement
- Context budget tokens: 12288
- Preconditions: Lookup and receipt paths pass independently.
- Effects: Wires final plugin hooks, controller/worker messages, fenced writes, and privacy-safe metrics/reason codes.
- Evidence subset: Pytest-xdist hooks, store fences, session reports, worker crash/restart behavior
- Acceptance: Parallel workers do not duplicate, partially publish, or disagree on authority; controller failure makes workers execute and stops writes; metrics distinguish predicted, verified, skipped, executed, deferred, and degraded outcomes without private test data.

## PTR-060 Add proof-backed supervisor validation authority

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: supervisor-validation
- Depends on: PTR-030, PTR-043, PTR-051, PTR-052
- Goal id: PTR-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_cached_test_validation.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_cached_test_validation.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/supervisor-validation
- Parallel lane: ptr-supervisor-validation
- Resource class: security-review
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_cached_test_validation.py
- Predicted symbols: ProofCachedTestValidation, ProofCachedTestValidationReceipt
- Interfaces: ValidationEvidence, CompletionEvidence, TestProofCertificate@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Extend authoritative validation evidence; ordinary skip text, a cache-hit flag, or historical status never satisfies task/goal/merge completion.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: codex-implement
- Context budget tokens: 12288
- Preconditions: Trust cache, datasets verifier, lookup, and receipt contracts exist.
- Effects: Re-verifies a proof-backed skip against the current tree and emits fresh typed supervisor evidence.
- Evidence subset: Validation runner, completion authority, merge gates, repository snapshot and proof certificate bindings
- Acceptance: Receipt binds validation command, task/goal, current commit/tree/gitlinks/dirty state, execution/receipt/certificate/policy/circuit/key CIDs, verifier authority and freshness; stale/simulated/plain skips remain non-completion evidence.

## PTR-061 Bootstrap proof reuse in ipfs_accelerate_py

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: accelerator-bootstrap
- Depends on: PTR-053, PTR-060
- Goal id: PTR-G070
- Outputs: external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/conftest.py, external/ipfs_accelerate/pytest.ini, external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_bootstrap.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_bootstrap.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/accelerator-bootstrap
- Parallel lane: ptr-accelerator-bootstrap
- Resource class: test-large
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/conftest.py, external/ipfs_accelerate/pytest.ini, external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_bootstrap.py
- Predicted symbols: pytest11 proof-reuse entry point, accelerator proof-reuse bootstrap
- Interfaces: pytest11, pytest root conftest, ProofReuseConfig@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Add one packaging entry point and a minimal optional root loader; preserve existing conftest behavior and hermetic plugin controls.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: grok-implement
- Context budget tokens: 12288
- Preconditions: Shared plugin and supervisor validation authority are complete.
- Effects: Makes suite and directly selected accelerator tests discover the plugin with autoload enabled or disabled.
- Evidence subset: Packaging metadata, pytest plugin manager, root conftest and hermetic subprocess fixtures
- Acceptance: Pytest11 and root loader paths are idempotent; an individual node picks up reuse without a registry; plugin absence executes normally; coverage, mutation, profiling, benchmarking, debugger, and explicit off modes execute; bootstrap import performs no probe/write/network/daemon action.

## PTR-070 Bootstrap proof reuse in ipfs_datasets_py

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-bootstrap
- Depends on: PTR-042, PTR-053
- Goal id: PTR-G080
- Outputs: external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/tests/conftest.py, external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-bootstrap
- Parallel lane: ptr-datasets-bootstrap
- Resource class: test-large
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/tests/conftest.py, external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py
- Predicted symbols: datasets proof-reuse bootstrap, migrated test cache hooks
- Interfaces: pytest root conftest, TestCertificateIssuer@1, shared proof-reuse plugin
- Submodules: external/ipfs_datasets
- Generated artifacts: none
- Conflict policy: Replace the existing commit-only skip cache as authority and repair its nested hook lifecycle without disturbing unrelated datasets fixtures.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: grok-implement
- Context budget tokens: 12288
- Preconditions: Deferred issuer and complete shared plugin exist.
- Effects: Adds optional plugin pickup for suite/direct nodes and migrates old cache behavior to exact post-pass receipts.
- Evidence subset: Datasets tests/conftest commit cache, pyproject, shared plugin and issuer adapter
- Acceptance: Individual tests pick up the plugin with no test list; legacy commit metadata alone cannot skip; hooks are module-scoped and complete-phase aware; plugin/provider/cache absence runs normally; no proof request lies on pass completion.

## PTR-080 Add strict optional certificate transport to ipfs_kit_py

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: kit-store
- Depends on: PTR-003, PTR-031
- Goal id: PTR-G090
- Outputs: external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py, external/ipfs_kit/ipfs_kit_py/test_reuse_capabilities.py, external/ipfs_kit/tests/test_proof_certificate_store.py, external/ipfs_kit/tests/test_reuse_capabilities.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_kit/tests/test_proof_certificate_store.py external/ipfs_kit/tests/test_reuse_capabilities.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/kit-store
- Parallel lane: ptr-kit-store
- Resource class: io-artifact
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py, external/ipfs_kit/ipfs_kit_py/test_reuse_capabilities.py, external/ipfs_kit/tests/test_proof_certificate_store.py, external/ipfs_kit/tests/test_reuse_capabilities.py
- Predicted symbols: IpfsKitProofCertificateStore, KitTestReuseCapabilities
- Interfaces: TestCertificateStoreTransport@1, TestReuseCapabilityReport@1
- Submodules: external/ipfs_kit
- Generated artifacts: none
- Conflict policy: Local/IPFS storage is optional transport only; accelerator policy remains authority and kit testing pseudo-CIDs are never accepted.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: codex-implement
- Context budget tokens: 12288
- Preconditions: Shared immutable store and capability contracts exist.
- Effects: Adds strict CID-verified immutable put/get transport and lazy Kubo/Lotus/Iroh capability fingerprints.
- Evidence subset: Kit storage/backends, multiformats adapter, daemon lifecycle and configuration paths
- Acceptance: External CIDs decode and rehash exact bytes; local transport is atomic and bounded; IPFS errors miss; Kubo/Lotus/Iroh are lazy facts; no operation starts a daemon or touches a user IPFS directory; legacy fake hashes are rejected.

## PTR-081 Bootstrap proof reuse in ipfs_kit_py

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: kit-bootstrap
- Depends on: PTR-053, PTR-080
- Goal id: PTR-G090
- Outputs: external/ipfs_kit/pyproject.toml, external/ipfs_kit/conftest.py, external/ipfs_kit/tests/test_proof_reuse_bootstrap.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_kit/tests/test_proof_reuse_bootstrap.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/kit-bootstrap
- Parallel lane: ptr-kit-bootstrap
- Resource class: test-large
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_kit/pyproject.toml, external/ipfs_kit/conftest.py, external/ipfs_kit/tests/test_proof_reuse_bootstrap.py
- Predicted symbols: kit proof-reuse bootstrap
- Interfaces: pytest root conftest, shared proof-reuse plugin, TestCertificateStoreTransport@1
- Submodules: external/ipfs_kit
- Generated artifacts: none
- Conflict policy: Add a minimal optional loader and preserve all existing kit test fixtures and daemon safety defaults.
- Symbolic first: true
- LLM context budget bytes: 40960
- Provider role: codex-implement
- Context budget tokens: 10240
- Preconditions: Complete plugin and strict optional kit store are available.
- Effects: Makes suite and directly selected kit tests discover proof reuse without daemon startup.
- Evidence subset: Kit pyproject, root/tests conftests, plugin/store unavailable fixtures, temporary configuration roots
- Acceptance: Direct-node pickup works with entry-point autoload enabled/disabled; a verified hit starts no daemon and touches no user IPFS directory; plugin/store/multiformats absence executes normally; explicit off and coverage execute.

## PTR-090 Prove the complete degradation matrix

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: degradation
- Depends on: PTR-061, PTR-070, PTR-081
- Goal id: PTR-G100
- Outputs: external/ipfs_accelerate/test/api/test_proof_reuse_degradation_matrix.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_degradation_matrix.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/degradation
- Parallel lane: ptr-degradation
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/test_proof_reuse_degradation_matrix.py
- Predicted symbols: proof reuse degradation population
- Interfaces: ReuseDecision@1, TestReuseCapabilityReport@1, three repository bootstraps
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Exercise failures through fixtures and subprocess isolation; never require live optional services for the mandatory matrix.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: Accelerator, datasets, and kit bootstrap paths are implemented.
- Effects: Locks every optional-dependency and corrupt-state branch to RUN behavior.
- Evidence subset: Missing/corrupt cache, multiformats/provider/verifier absence, timeouts, wrong circuit/key/issuer/policy/expiry, simulated proof and plugin errors
- Acceptance: Every case executes the test and reports a bounded reason without startup failure; required-audit may explicitly fail its audit only; no ordinary mode turns missing Groth16, ProveKit, cache, IPFS, or local verifier into a skipped or failed test.

## PTR-091 Run the invalidation mutation population

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: invalidation-mutations
- Depends on: PTR-012, PTR-022, PTR-090
- Goal id: PTR-G100
- Outputs: external/ipfs_accelerate/test/fixtures/proof_reuse_mutations.py, external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/invalidation
- Parallel lane: ptr-invalidation
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/fixtures/proof_reuse_mutations.py, external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py
- Predicted symbols: ProofReuseMutationCorpus, assert_no_stale_proof_skip
- Interfaces: TestExecutionKey@1, TestReuseEligibilityDecision@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Use temporary repositories/environments and deterministic fixtures; mutation results cannot be satisfied by proof reuse.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: grok-implement
- Context budget tokens: 14336
- Preconditions: CID vectors, eligibility, and degradation behavior pass.
- Effects: Mutates every identity and dependency class and measures the resulting decision.
- Evidence subset: Test/import/indirect dependency/fixture/conftest/hook/parameter/lock/environment/hardware/data/dynamic import/dirty tree/policy/circuit/key mutations
- Acceptance: Each relevant mutation changes or invalidates the exact execution context and executes the test; unrelated locator-index candidates cannot override current identity; the authoritative stale-skip count is zero.

## PTR-092 Run storage security and concurrency assurance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: security-concurrency
- Depends on: PTR-031, PTR-043, PTR-090
- Goal id: PTR-G100
- Outputs: external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/security-concurrency
- Parallel lane: ptr-security-concurrency
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py
- Predicted symbols: proof reuse security and concurrency population
- Interfaces: TestCertificateStore@1, TestCertificateProvider@1, pytest-xdist
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Use isolated temporary roots, bounded synthetic artifacts, and controlled worker processes; never inspect or modify user cache/IPFS roots.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: Store, provider, and degradation contracts pass.
- Effects: Exercises forgery, privacy, filesystem safety, crash recovery, races, and revocation.
- Evidence subset: Forged receipt/proof/CID, secret leakage, oversized blobs, symlink/path escape, partial writes, restart, parallel writers, stale locks, rollback/replay and revocation races
- Acceptance: No hostile artifact authorizes skip or escapes its root; incomplete writes remain invisible; crash/restart and concurrent publishers preserve immutable authority; revocation wins races; all failures run tests with bounded diagnostics.

## PTR-093 Prove cross-repository direct-node and xdist behavior

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: cross-repo-e2e
- Depends on: PTR-053, PTR-090
- Goal id: PTR-G100
- Outputs: external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/cross-repo-e2e
- Parallel lane: ptr-cross-repo-e2e
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py
- Predicted symbols: cross repository proof reuse subprocess population
- Interfaces: three pytest bootstraps, TestPassReceipt@1, TestProofCertificate@1, pytest-xdist
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Run disposable subprocess repositories/cache roots; real-verifier fixtures are local and network-free.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: Complete plugin and degradation matrix pass; repository bootstrap dependencies are transitively complete.
- Effects: Exercises miss, pass receipt, real certificate, warm skip, mutation, off/coverage, direct-node, autoload-disabled, and xdist flows in all three repos.
- Evidence subset: Subprocess pytest reports, canonical cache artifacts, plugin properties, direct-node exit codes and xdist controller records
- Acceptance: All three repositories execute on miss, create only post-pass receipts, verify one unchanged warm skip, execute after mutation and under off/coverage, pick up individual nodes with both bootstrap paths, and avoid duplicate/partial xdist authority.

## PTR-100 Benchmark shadow and warm reuse

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: benchmark
- Depends on: PTR-091, PTR-092, PTR-093
- Goal id: PTR-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/self_improvement/proof_reuse_benchmark.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_reuse_benchmark.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_BENCHMARK.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_reuse_benchmark.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/benchmark
- Parallel lane: ptr-benchmark
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/self_improvement/proof_reuse_benchmark.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_reuse_benchmark.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_BENCHMARK.md
- Predicted symbols: ProofReuseBenchmark, ProofReuseBenchmarkReceipt
- Interfaces: ProofReuseMetrics@1, BenchmarkReceipt
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Benchmark only controlled eligible populations and report exclusions; performance never relaxes authority.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: grok-implement
- Context budget tokens: 12288
- Preconditions: Invalidation, security/concurrency, and cross-repository populations have zero false skips.
- Effects: Compares off, shadow, cold readwrite, warm read, and forced rerun latency and decisions.
- Evidence subset: Eligible/ineligible fixture populations, collection/lookup/verification/execution timings, bytes and reason-code counts
- Acceptance: False admissions equal zero; at least 80 percent of the explicitly eligible unchanged warm population verifies and skips; verification is cheaper than execution; miss overhead is bounded; saved wall time and exclusions are reproducible.

## PTR-101 Implement staged rollout, sampling, and rollback

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: rollout
- Depends on: PTR-100
- Goal id: PTR-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/rollout.py, external/ipfs_accelerate/test/api/test_proof_reuse_rollout.py, external/ipfs_accelerate/docs/guides/TEST_PROOF_REUSE_RUNBOOK.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_rollout.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/rollout
- Parallel lane: ptr-rollout
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/rollout.py, external/ipfs_accelerate/test/api/test_proof_reuse_rollout.py, external/ipfs_accelerate/docs/guides/TEST_PROOF_REUSE_RUNBOOK.md
- Predicted symbols: ProofReuseRolloutPolicy, ForcedRerunSampler, ProofReuseRollbackDecision
- Interfaces: ProofReuseConfig@1, ProofReuseBenchmarkReceipt, ProofReuseMetrics@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Rollout may narrow or disable reuse but cannot broaden proof authority beyond reviewed eligibility.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: codex-implement
- Context budget tokens: 12288
- Preconditions: Benchmark thresholds and zero-false-admission evidence exist.
- Effects: Encodes off to shadow to read to opt-in readwrite to eligible-default transitions, forced rerun sampling, alerts, and rollback.
- Evidence subset: Benchmark receipts, degradation/mutation mismatch metrics, key/revocation health and operator controls
- Acceptance: Promotion requires explicit fresh gates; forced reruns compare predicted versus actual outcomes; any false skip, authority contradiction, corruption spike, stale key, or unexplained mismatch returns policy to shadow/off; defaults remain off until promoted.

## PTR-102 Publish the final current-tree authority gate

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: final-gate
- Depends on: PTR-091, PTR-092, PTR-093, PTR-101
- Goal id: PTR-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py external/ipfs_kit/tests/test_proof_reuse_bootstrap.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/final-gate
- Parallel lane: ptr-final-gate
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py
- Predicted symbols: ProofTestReuseCurrentTreeGate, ProofTestReuseCompletionEvidence
- Interfaces: CompletionEvidence, ObjectiveGraph, ProofReuseRolloutPolicy
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Aggregate current evidence only; an ordinary skip, stale population, incomplete task, simulated proof, or historical benchmark cannot close the root goal.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: Mutation, security/concurrency, cross-repository e2e, benchmark, and rollout evidence are complete.
- Effects: Evaluates the exact closed PTR task population under current repository forest, policy, providers, and validation receipts.
- Evidence subset: Current commit/tree/recursive gitlinks, task CIDs and merge receipts, child goal evidence, all adversarial populations, benchmark and rollout decision
- Acceptance: Gate fails closed on missing/stale evidence, open tasks, false skips, unhealthy analyzers, mismatched forest/policy/capability/key/circuit identities, ordinary skips, or simulated authority; success emits the only root completion evidence for PTR-G000.

## PTR-108 Emit datasets real-ZK conformance evidence

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-zk-assurance
- Depends on: PTR-040, PTR-041, PTR-042
- Goal id: PTR-G050
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_assurance.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_assurance.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_assurance.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-zk-assurance
- Parallel lane: ptr-datasets-assurance
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_assurance.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_assurance.py
- Predicted symbols: TestCertificateAssuranceReceipt, RealZKConformanceReceipt, TestCertificateAssuranceProvider, TestCertificateAssuranceUnavailable
- Interfaces: TestCertificateAssuranceReceipt@1, RealZKConformanceReceipt@1, TestProofCertificate@1, TestPassStatementV1
- Submodules: external/ipfs_datasets
- Generated artifacts: retained real-certificate verification receipts and typed backend-unavailable results
- Conflict policy: Extend the datasets ZKP authority domain only; never import accelerator or kit, install dependencies during import, treat simulated proof as real, or turn unavailable proving infrastructure into a test failure.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: The test-pass statement, execution-certificate verifier, deferred issuer, Groth16/ProveKit adapters, and lazy capability probes are available.
- Effects: Exposes a repository-native, lazily injectable assurance provider that replays retained certificate bytes and emits exact current verification or typed unavailable evidence for objective closeout.
- Evidence subset: TestPassStatementV1, canonical public inputs, circuit/verifier-key/issuer/policy identities, retained proof bytes, real backend verifier decision, simulated/unavailable authority distinctions
- Acceptance: A receipt binds the exact pass receipt, execution key, statement, circuit, verifier key, issuer, backend and policy plus observed/fresh-until window and canonical retained proof bytes; locally replayed real certificates can emit authoritative conformance while simulated certificates never can; Groth16/ProveKit endpoint or binary absence returns a finite typed unavailable result; cold import performs no network, subprocess, installation, cache write or broad package import; and tampered, stale, mismatched, private-witness, fake-CID and unknown-version inputs fail closed.

## PTR-109 Persist canonical artifact bytes by CID

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: kit-content-addressed-artifacts
- Depends on: PTR-080
- Goal id: PTR-G090
- Outputs: external/ipfs_kit/ipfs_kit_py/content_addressed_artifact_store.py, external/ipfs_kit/tests/test_content_addressed_artifact_store.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_kit/tests/test_content_addressed_artifact_store.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/kit-content-addressed-artifacts
- Parallel lane: ptr-kit-evidence
- Resource class: io-artifact
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_kit/ipfs_kit_py/content_addressed_artifact_store.py, external/ipfs_kit/tests/test_content_addressed_artifact_store.py
- Predicted symbols: CanonicalArtifactStoreTransport, CanonicalDagJsonBlock, CanonicalArtifactStoreResult, CanonicalArtifactCapability
- Interfaces: CanonicalArtifactStoreTransport@1, CanonicalDagJsonBlock@1, TestCertificateStoreTransport@1, CIDv1
- Submodules: external/ipfs_kit
- Generated artifacts: immutable local objective-evidence blobs and bounded optional transport results
- Conflict policy: Provide repository-agnostic byte transport only; never interpret CompletionEvidence, import accelerator or datasets, start Kubo/Lotus/Iroh, trust a mutable index, or accept a legacy pseudo-CID.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: grok-implement
- Context budget tokens: 12288
- Preconditions: Strict certificate storage, canonical external-CID verification, atomic local persistence and lazy kit capability facts are available.
- Effects: Adds an injected immutable canonical-block transport over the existing proof-certificate store with retained bytes, readback rehash, bounded lookup hints and typed local/optional-backend capability results.
- Evidence subset: Strict multiformats CID utilities, proof certificate store atomicity/path safety, local CAS, bounded mutable indexes, Kubo/Lotus/Iroh lazy capability probes
- Acceptance: Canonical DAG-JSON bytes store and load only under their independently rederived CIDv1/base32/dag-json/sha2-256 identity; decoded multihash matches retained bytes; writes are atomic, fenced and readback-rehashed; stale, corrupt, oversized, partial, symlink/path-escaping, index-poisoned and fake-CID artifacts miss safely; missing multiformats/store/IPFS returns a typed result without installing or starting anything; cold import touches no user IPFS directory; and authority semantics remain solely with the injected caller.

## PTR-110 Collect authoritative task and validation provenance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: objective-task-evidence
- Depends on: PTR-102
- Goal id: PTR-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_task_evidence.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_task_evidence.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_task_evidence.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/objective-task-evidence
- Parallel lane: ptr-objective-provenance
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_task_evidence.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_task_evidence.py
- Predicted symbols: ProofTestReuseTaskEvidence, ProofTestReuseTaskEvidenceCollector, TaskValidationProvenance, TaskEvidenceGap
- Interfaces: ProofTestReuseTaskEvidence@1, TaskValidationProvenance@1, ProofCachedTestValidationReceipt, TaskCompletionProvenanceKind
- Submodules: external/ipfs_accelerate
- Generated artifacts: state-root task-evidence packets and typed provenance-gap receipts
- Conflict policy: Read the taskboard and immutable supervisor history generically; never infer authority from Status, Completion, prose, an ordinary skip, or an unverified receipt.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: PTR-102 and the original 32-task implementation population are complete; the exact objective/task sources and current repository checkout are available read-only.
- Effects: Collects exact board/task CIDs, Git ancestry, merge and validation receipts, current reruns, and explicit operator/reviewer provenance into replayable current-tree task evidence without hardcoding test files.
- Evidence subset: Canonical task records, merge queue records, repository ancestry, declared validation commands, proof-cached validation receipts, operator planning seal and reviewed retrospective approvals
- Acceptance: The collector derives the required task population from the validated board; binds repository, Git tree, recursive forest, dirty overlay, task CID, validation command and receipt; accepts retrospective provenance only after verified ancestry plus a current proof-reuse-off rerun and an immutable reviewed approval; requires genuine approval evidence for PTR-000, PTR-001, PTR-011, and PTR-041 when queue records are absent; verifies any proof-backed skip locally; and returns a typed gap rather than authority for every missing, stale, malformed, ordinary-skip, unavailable, or contradictory input.

## PTR-111 Produce independent goal coverage and analyzer receipts

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: objective-goal-assurance
- Depends on: PTR-102, PTR-108
- Goal id: PTR-G100
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_goal_evidence.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_goal_evidence.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_goal_evidence.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/objective-goal-evidence
- Parallel lane: ptr-objective-assurance
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_goal_evidence.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_goal_evidence.py
- Predicted symbols: ProofTestReuseGoalEvidence, GoalAssuranceRunner, AcceptanceCoverageReceipt, ProofReuseAnalyzerReceipt, ProofReusePopulationReceipt
- Interfaces: ProofTestReuseGoalEvidence@1, TestCertificateAssuranceReceipt@1, AcceptanceCoverage@1, AnalyzerHealth, ExhaustionQuorum, ProofReuseBenchmarkReceipt, ProofReuseRollbackDecision
- Submodules: external/ipfs_accelerate
- Generated artifacts: state-root goal, analyzer, adversarial, benchmark, rollout, and quorum receipts
- Conflict policy: Execute the heap-declared validation commands with proof reuse off; never infer a criterion from task status, duplicate one analyzer as two quorum members, or treat an unavailable proof backend as a pass.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: The typed goal heap, declared validations, analyzer implementations, adversarial populations, benchmark contract, and rollout policy are present on the current checkout.
- Effects: Produces exact typed evidence for the 39 machine acceptance IDs, three analyzer channels, three adversarial populations, benchmark and rollout premises, and genuinely independent exhaustive/audit quorum members.
- Evidence subset: Goal Evidence and Acceptance criteria fields, proof-reuse-off validation receipts, static/runtime/eligibility analyzer results, degradation/mutation/security/cross-repository populations, injected datasets real-certificate assurance records, benchmark and rollout records
- Acceptance: Requirement IDs are discovered from the objective heap rather than a per-test registry; every receipt binds its exact producer channel, canonical proof revision, current identities, observed/fresh-until window and retained validation bytes; all three adversarial population receipts explicitly pass with zero false skips; two quorum members are independent, healthy, exhaustive, conclusive, fresh, and uncontradicted; an unavailable Groth16, ProveKit, cache, or IPFS capability is typed and non-blocking but leaves any real-ZK or production-warm criterion unverified unless a reviewed locally verifiable real certificate is present; synthetic `_AlwaysVerify` benchmark data is never deployment authority.

## PTR-112 Define strict objective-completion artifact contracts

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: objective-artifact-contracts
- Depends on: PTR-102, PTR-109
- Goal id: PTR-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_objective_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_objective_contracts.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_objective_contracts.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/objective-contracts
- Parallel lane: ptr-objective-contracts
- Resource class: security-review
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_objective_contracts.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_objective_contracts.py
- Predicted symbols: ProofTestReuseObjectiveBinding, ProofTestReuseCompletionArtifact, ProofTestReuseGateBundle, ObjectiveArtifactStore
- Interfaces: ProofTestReuseObjectiveBinding@1, ProofTestReuseCompletionArtifact@1, ProofTestReuseGateBundle@1, CanonicalArtifactStoreTransport@1, CompletionEvidence
- Submodules: external/ipfs_accelerate
- Generated artifacts: atomic state-root completion evidence and gate envelopes with retained canonical premise bytes
- Conflict policy: Extend the existing generic objective authority boundary; do not create a parallel trust root, alias identity domains, accept pseudo-CIDs, or let artifact paths self-authorize.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: grok-implement
- Context budget tokens: 14336
- Preconditions: Generic goal completion, strict content-identity bridge, objective revision, repository-forest identity, and completion-control-path exclusion contracts are available.
- Effects: Defines finite strict envelopes, per-goal bindings, canonical premise retention/resolution, deserialization and replay verification while injecting the kit canonical artifact transport lazily for atomic persistence.
- Evidence subset: CompletionEvidence, objective goal completion revision, completion tree identity, Git tree/commit/gitlink identities, canonical DAG-JSON bytes, CID/multihash validators, source-channel proofs and freshness policy
- Acceptance: Contracts distinguish git_tree_id, repository_forest_cid, and objective_completion_tree_id; bind repository ID plus exact per-goal objective, analyzer, configuration, policy, capability, circuit and verifier-key revisions; encode authoritative artifacts as CIDv1 lowercase base32 dag-json sha2-256 with retained canonical bytes and decoded-multihash recheck; reject fake or noncanonical CIDs, unknown fields, unsafe paths, partial writes, alias conflicts, stale records and provenance mismatches; exclude only declared state-root control artifacts from completion-tree identity; and fail closed without importing or installing optional packages.

## PTR-120 Assemble bound goal evidence and completion-gate bundles

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: objective-artifact-assembly
- Depends on: PTR-110, PTR-111, PTR-112
- Goal id: PTR-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_objective_evidence.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_objective_evidence.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_objective_evidence.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/objective-evidence
- Parallel lane: ptr-objective-bundles
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_objective_evidence.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_objective_evidence.py
- Predicted symbols: ProofTestReuseObjectiveEvidenceAssembler, ProofTestReuseObjectiveEvidenceBundle, GoalCompletionArtifactGap
- Interfaces: ProofTestReuseTaskEvidence@1, ProofTestReuseGoalEvidence@1, ProofTestReuseCompletionArtifact@1, ObjectiveCompletionEvidenceArtifact
- Submodules: external/ipfs_accelerate
- Generated artifacts: state-root per-goal evidence, coverage, analyzer-health, exhaustion-quorum and gate JSON bundles
- Conflict policy: Aggregate only validated retained premises; no board label, missing record, unverified CID, inferred channel, synthetic benchmark, or optional-capability fallback may be filled with a success placeholder.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-110, PTR-111, and PTR-112 define validated task, goal, analyzer and artifact contracts.
- Effects: Joins exact current task and assurance receipts into atomic, replayable, generic objective-daemon gate and completion-evidence artifacts for all 12 goals.
- Evidence subset: Task and goal evidence packets, per-goal semantic revisions, current repository identities, strict channel proofs, coverage rows, analyzer health, two-member exhaustion quorum, child hierarchy and validation receipts
- Acceptance: The assembler emits exactly one current binding and the exact typed acceptance population for every goal; replays every premise by canonical CID before write; requires fresh verified coverage, a healthy exhaustive analyzer and two independent quorum members; writes atomically with readback rehash; preserves unavailable or incomplete inputs as bounded gap records; generated artifacts round-trip through the existing strict objective-daemon loaders and generic CompletionEvidence validator; and no artifact can verify its own bytes or authorize edits.

## PTR-121 Implement fenced multi-phase objective reconciliation

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: objective-reconciliation
- Depends on: PTR-110, PTR-111, PTR-112
- Goal id: PTR-G110
- Outputs: scripts/proof_backed_test_reuse_objective_reconciliation.py, test/test_proof_backed_test_reuse_objective_reconciliation.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest test/test_proof_backed_test_reuse_objective_reconciliation.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/objective-reconciliation
- Parallel lane: ptr-objective-reconcile
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: scripts/proof_backed_test_reuse_objective_reconciliation.py, test/test_proof_backed_test_reuse_objective_reconciliation.py
- Predicted symbols: ProofTestReuseObjectiveReconciler, ObjectiveCloseoutPhase, ObjectiveCloseoutReceipt, ObjectiveCloseoutFence
- Interfaces: ProofTestReuseObjectiveReconciler@1, ObjectiveCloseoutReceipt@1, GoalLifecycle, ObjectiveCompletionEvidenceArtifact
- Submodules:
- Generated artifacts: state-root lifecycle projection, phase receipts, writer fence and candidate protected objective update
- Conflict policy: Use one outer-controller-owned writer with compare-and-swap fencing; worker lanes remain reconciliation-disabled and no phase may skip a legal lifecycle transition.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: Strict objective artifacts, the current validated board and the generic objective reconciliation API are available.
- Effects: Adds the outer program's bounded non-shell CLI over existing accelerator authority APIs for report-only diagnosis, state-root lifecycle projection, three-stage reconciliation, replay, restart and candidate operator handoff.
- Evidence subset: Objective and task DAGs, strict completion artifacts, current validation reruns, lifecycle decisions, writer lease/fence, repository identity snapshots and contradiction receipts
- Acceptance: The module implements the exact bounded argv consumed by `scripts/proof_backed_test_reuse_supervisor.py closeout`; the report-only path never writes the repository; closeout refuses open tasks, a dirty or changed source checkout, concurrent writers, stale artifacts and unhealthy supervisor state; phase one creates only provisional goals, phase two verifies G010 through G100 after current validation, and phase three admits final-gate evidence before verifying G110 then G000; every refresh recomputes bindings; bounded replay converges; interruption resumes safely; mutation or contradiction reopens affected ancestors/dependents; output is a validated candidate objective update that requires explicit operator commit; and missing optional services yield a nonterminal gap rather than blocking normal tests or supervisors.

## PTR-122 Remove final-gate self-reference and complete current-tree authority

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: final-gate-authority-repair
- Depends on: PTR-102, PTR-110, PTR-111, PTR-112
- Goal id: PTR-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/final-gate-authority-repair
- Parallel lane: ptr-final-gate-repair
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py
- Predicted symbols: ProofTestReuseCurrentTreeGate, ProofTestReuseCompletionEvidence, ProofTestReusePersistedGateBundle, verify_persisted_current_tree_gate_bundle
- Interfaces: ProofTestReuseCurrentTreeGateDecision@1, ProofTestReuseCompletionEvidence@1, CompletionEvidence, ProofTestReuseGateBundle@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: replayable current-tree gate bundle and generic G110/root completion evidence records
- Conflict policy: Preserve all fail-closed gate checks; remove only the G110 self-premise and replace it with direct benchmark/rollout validation, never with a prospective goal label.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: The original PTR-102 gate, authoritative task/goal evidence contracts, and strict artifact bindings are available.
- Effects: Expands the sealed task population to all 41 implementation tasks, validates supervisor health, makes persisted gate decisions replayable, and bridges valid gate output into exact G110 and G000 generic completion records.
- Evidence subset: Full task population, verified G010-G100 children, adversarial/analyzer populations, real benchmark and rollout premises, supervisor launch health, strict objective artifacts and source-channel policy
- Acceptance: The gate no longer requires G110 as its own child premise; it requires verified G010-G100 plus direct fresh G110 benchmark and rollout premises; the producing task is PTR-122 and the required task population includes PTR-108, PTR-109, PTR-110, PTR-111, PTR-112, PTR-120, PTR-121, PTR-122, and PTR-130; it accepts and verifies a fresh current-tree/config-bound three-lane supervisor-health receipt before claiming that root requirement; it distinguishes Git tree, forest and objective-completion identities; validates every retained premise CID; persisted bundles strictly deserialize and replay the gate; the generic adapter uses allowed producer/source semantics, exact per-goal revisions, canonical channel proof and freshness; and a passing gate emits separate exact evidence for `ptr/final-current-tree-gate@1` on G110 and `ptr/cross-repository-current-tree-gate@1` on G000 without claiming the other root requirements by implication.

## PTR-130 Prove objective closeout and publish the operator handoff

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: objective-closeout-e2e
- Depends on: PTR-120, PTR-121, PTR-122
- Goal id: PTR-G000
- Outputs: external/ipfs_accelerate/test/api/test_proof_test_reuse_objective_closeout_e2e.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_OBJECTIVE_CLOSEOUT.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_test_reuse_objective_closeout_e2e.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/objective-closeout
- Parallel lane: ptr-objective-closeout
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/test_proof_test_reuse_objective_closeout_e2e.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_OBJECTIVE_CLOSEOUT.md
- Predicted symbols: proof test reuse objective closeout subprocess population, operator closeout handoff
- Interfaces: ProofTestReuseObjectiveReconciler@1, ProofTestReuseObjectiveEvidenceBundle, ProofTestReuseCurrentTreeGateDecision@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: hermetic closeout receipts, tamper matrix and operator runbook examples
- Conflict policy: Exercise disposable repository and state roots only; this task proves the closeout mechanism but cannot declare the live root complete or edit protected control files.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-120, PTR-121, and PTR-122 provide complete artifact assembly, staged reconciliation, and repaired final-gate authority.
- Effects: Proves end-to-end legal goal convergence and fail-closed degradation, then documents the explicit live current-tree operator closeout and protected commit/restart sequence.
- Evidence subset: A synthetic closed 41-task board with cryptographically valid local fixtures, exact 12-goal heap, retained premise bundles, three-phase lifecycle receipts, supervisor-health records, restart and tamper cases
- Acceptance: A disposable exact population reaches provisional goals, verified G010-G100, then verified G110 and G000 only through three staged reconciliations; missing, stale, forged, noncanonical, mismatched, quorum-short, validation-failed, ordinary-skip, simulated-proof, unavailable-backend-without-real-fixture, tree-mutated and restart-interrupted cases never verify; no test-file registry or network service is required; optional capability absence remains a typed non-blocking gap; the runbook identifies genuine approvals needed for historical provenance and makes clear that task completion precedes, and does not itself constitute, the live operator closeout.

## PTR-131 Seal automatic runtime activation and candidate-context contracts

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime-activation-contracts
- Depends on: PTR-130
- Goal id: PTR-G010
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/activation_contracts.py, external/ipfs_accelerate/test/api/test_proof_reuse_activation_contracts.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_RUNTIME_ACTIVATION.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_activation_contracts.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/runtime-contracts
- Parallel lane: ptr-runtime-contracts
- Resource class: security-review
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/activation_contracts.py, external/ipfs_accelerate/test/api/test_proof_reuse_activation_contracts.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_RUNTIME_ACTIVATION.md
- Predicted symbols: ProofReuseActivationContract, CandidateExecutionContext, CurrentExecutionContext, RuntimeReuseDisposition
- Interfaces: ProofReuseActivationContract@1, CandidateExecutionContext@1, CurrentExecutionContext@1, RuntimeReuseDisposition@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Define one fail-closed runtime composition contract under the existing proof authority model; no item attributes, test registries, environment flags, mutable indexes, or historical traces may become skip authority.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: PTR-130 closed the reviewed objective-completion expansion and the current plugin, identity, trace, receipt, cache, and certificate contracts are available for audit.
- Effects: Fixes the typed boundaries for lazy default activation, exact candidate-context retention, fresh current-context rebuilding, deferred issuance, and fail-open degradation before runtime code is composed.
- Evidence subset: Existing proof reuse contracts, plugin hook ordering, cache authority doctrine, execution-identity inputs, runtime trace lifecycle and repository bootstrap behavior
- Acceptance: The contract distinguishes locator hints, immutable candidate context, freshly rebuilt current context, trusted pass receipt, deferred proof request and authoritative certificate; requires canonical bytes plus CID rehash at every content-addressed boundary; requires current AST/static/runtime/environment/policy comparison before SKIP; records post-pass runtime observations without duplicating the test call; and maps every missing, malformed, incompatible, timed-out or exceptional optional capability to RUN or DEFERRED without collection failure.

## PTR-132 Version the datasets test-pass statement and canonical CID profile

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-statement-binding
- Depends on: PTR-130
- Goal id: PTR-G050
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_execution_certificate.py, external/ipfs_datasets/setup.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_cid_profile.py, external/ipfs_datasets/tests/unit/test_setup_side_effect_defaults.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_cid_profile.py external/ipfs_datasets/tests/unit/test_setup_side_effect_defaults.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-statement-v2
- Parallel lane: ptr-datasets-statement-v2
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_execution_certificate.py, external/ipfs_datasets/setup.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_cid_profile.py, external/ipfs_datasets/tests/unit/test_setup_side_effect_defaults.py
- Predicted symbols: TestPassStatementV2, TestExecutionCertificateV2, TEST_PASS_CID_PROFILE
- Interfaces: TestPassStatementV2, TestExecutionCertificateV2, CanonicalContentIdentity@1
- Submodules: external/ipfs_datasets
- Generated artifacts: deterministic independent statement and certificate CID vectors
- Conflict policy: Version the public-input domain explicitly and preserve V1 verification as a separate compatibility path; never reinterpret legacy bytes, private sha256 labels, or pseudo-CIDs as the new profile.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-108 real-certificate assurance and the current datasets statement, circuit, key and canonicalization implementations are available.
- Effects: Gives accelerator and datasets one byte-exact public statement whose receipt, execution, candidate-context, policy, circuit, verifier-key, issuer and epoch identities reproduce as CIDv1/base32/dag-json/sha2-256, while removing install-time native-build and data-download side effects from the default package path.
- Evidence subset: Retained canonical statement bytes, decoded multihash checks, independent multiformats vectors, Groth16 and ProveKit public-input bindings, circuit and verifier-key pins, isolated setup invocation without native build or NLTK network activity
- Acceptance: The versioned profile accepts only lowercase canonical CIDv1/base32/dag-json/sha2-256 identities whose decoded digest matches retained canonical bytes; binds exact candidate-context and receipt identities plus policy/circuit/key/issuer/epoch; rejects alias encodings, unknown fields, nonfinite values, private inputs, V1/V2 substitution and backend downgrade; remains cold-import safe when multiformats or real proving backends are absent; and makes native Groth16 compilation and NLTK data download disabled/lazy by default during setup/install, available only through explicit opt-in, with missing native artifacts preserved as typed DEFERRED/RUN capability results.

## PTR-133 Harden kit candidate-context artifact transport

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: kit-candidate-context-transport
- Depends on: PTR-130
- Goal id: PTR-G090
- Outputs: external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py, external/ipfs_kit/tests/test_candidate_context_artifact_store.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_kit/tests/test_proof_certificate_store.py external/ipfs_kit/tests/test_candidate_context_artifact_store.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/kit-candidate-context
- Parallel lane: ptr-kit-candidate-context
- Resource class: security-review
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py, external/ipfs_kit/tests/test_candidate_context_artifact_store.py
- Predicted symbols: CanonicalArtifactStore, CandidateContextArtifact, ArtifactStoreResult
- Interfaces: CanonicalArtifactStoreTransport@1, CandidateContextArtifact@1, ArtifactStoreResult@1
- Submodules: external/ipfs_kit
- Generated artifacts: immutable local canonical candidate-context fixtures
- Conflict policy: Keep kit a strict optional byte transport with no proof authority; never import the accelerator, start a daemon, create a user IPFS repository, or trust a path, index value, pseudo-CID, or remote response without rehashing bytes.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: grok-implement
- Context budget tokens: 14336
- Preconditions: PTR-109 canonical artifact transport and the current kit proof certificate store are available.
- Effects: Generalizes the existing strict store contract to bounded candidate-context artifacts while retaining atomic local persistence and optional content-addressed transport.
- Evidence subset: Canonical byte round trips, CID decode and rehash vectors, atomic write/readback, corruption quarantine, path safety, daemon and user-directory isolation
- Acceptance: Arbitrary admitted canonical candidate-context bytes round-trip by strict CID without certificate-specific reinterpretation; reads rehash exact bytes and quarantine corrupt, oversized, partial, symlinked, path-escaping or mismatched artifacts; local-store, multiformats, IPFS and daemon absence return typed misses; remote transport never becomes authority; and cold import plus all miss paths create no network connection, daemon, cache, installer or user IPFS state.

## PTR-134 Build lazy session-scoped default identity services

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime-default-identity
- Depends on: PTR-131
- Goal id: PTR-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/default_identity_services.py, external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/default-identity
- Parallel lane: ptr-default-identity
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/default_identity_services.py, external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py
- Predicted symbols: DefaultIdentityServiceFactory, ProofReuseSessionIdentity, build_default_identity_services
- Interfaces: DefaultIdentityServiceFactory@1, TestExecutionIdentityCompiler@1, AnalysisASTIndexProvider@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: none
- Conflict policy: Compose only from scoped imports after a non-off mode requests the feature; explicit injected services always win, and dependency installers, network services and repository writes are forbidden during collection and identity construction.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: PTR-131 activation contracts and existing identity component collectors, AST index, repository snapshot and capability probes are available.
- Effects: Supplies every collected item a session-scoped default locator/current-context compiler without per-file wiring while amortizing repository-forest, AST-index, distribution-lock and policy snapshots.
- Evidence subset: Direct-node collection, repository-root discovery, AST index construction, identity component collection, session memoization, explicit-injection precedence and cold import traces
- Acceptance: In read, write or readwrite mode a direct pytest node can obtain the full admitted repository-forest identity and exact locator/current static components without conftest service attributes or a test registry; expensive stable inputs are built once per session; dirty overlays and source changes invalidate identities; explicit test injections override defaults; off mode imports no optional provider; and any unavailable, incomplete or exceptional component returns non-reusable rather than aborting pytest.

## PTR-135 Persist immutable candidate execution contexts

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: candidate-context-cache
- Depends on: PTR-131
- Goal id: PTR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_candidate_context_store.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_candidate_context_store.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_candidate_context_store.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/candidate-context-store
- Parallel lane: ptr-candidate-context-store
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_candidate_context_store.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_candidate_context_store.py
- Predicted symbols: TestCandidateContextStore, CandidateContextEnvelope, CandidateContextLookupResult
- Interfaces: TestCandidateContextStore@1, CandidateExecutionContext@1, CanonicalArtifactStoreTransport@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: immutable candidate-context CAS blobs and bounded locator index fixtures
- Conflict policy: The mutable locator index is a bounded lookup hint only; every candidate blob is immutable, canonically encoded and rehashed before use, and store faults never suppress test execution.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-131 fixes candidate-context semantics and the existing certificate store, trust cache, fencing, revocation and optional kit transport protocols are available.
- Effects: Retains exact pass-time execution key, static trace, observed runtime trace, repository forest, environment, policy and receipt canonical bytes so a later run can reconstruct what the certificate actually attests.
- Evidence subset: Candidate canonicalization and CID vectors, locator-index poisoning cases, local CAS atomicity, optional kit transport, revocation/TTL, concurrent publication and corruption quarantine
- Acceptance: A lookup returns bytes plus a non-authoritative candidate descriptor; admission rehashes every retained component, confirms internal/external CID agreement and checks size/version/expiry/revocation/fence; poisoned indexes, missing blobs, stale generations, partial writes, symlinks, remote failures and transport absence become typed misses; publication is atomic and single-flight; and no mutable metadata, cache presence or historical execution key can authorize SKIP.

## PTR-136 Revalidate current context against retained candidates

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime-context-revalidation
- Depends on: PTR-134, PTR-135
- Goal id: PTR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runtime_revalidation.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_revalidation.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_runtime_revalidation.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/runtime-revalidation
- Parallel lane: ptr-runtime-revalidation
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runtime_revalidation.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_revalidation.py
- Predicted symbols: RuntimeContextRevalidator, CandidateComparison, PostPassRuntimeTraceCapture
- Interfaces: RuntimeContextRevalidator@1, CandidateExecutionContext@1, CurrentExecutionContext@1, RuntimeDependencyTrace@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: mutation and current-context comparison vectors
- Conflict policy: Historical runtime traces identify what must be revalidated but never state that current execution would pass; do not pre-execute a test call, execute fixtures twice, or convert an unknown runtime effect into equivalence.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-134 can build fresh session identity services and PTR-135 can return exact immutable candidate context bytes.
- Effects: Implements locator-to-candidate lookup followed by fresh reconstruction and exact comparison of the candidate's admitted dependency frontier, then records the actual runtime frontier after a real pass for future reuse.
- Evidence subset: AST/static closure, candidate runtime file/module/environment/subprocess/service observations, fresh content snapshots, unknown-frontier decisions, mutation vectors and one-call lifecycle counters
- Acceptance: Lookup starts from a stable locator only; every candidate dependency named by the retained trace is freshly resolved and content addressed; current source, AST, fixtures, hooks, parameters, locks, distributions, environment, capabilities, repository forest, policy and external snapshots must match; incomplete, unresolvable, changed or uncontrolled facts return RUN; a verified unchanged context may proceed to certificate verification without executing fixtures or the test body; and a normal miss executes setup/call/teardown exactly once before capturing and publishing its observed runtime trace.

## PTR-137 Add typed deferred certificate requests and lazy issuers

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: deferred-proof-issuance-v2
- Depends on: PTR-132
- Goal id: PTR-G050
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_datasets/tests/unit/logic/zkp/test_deferred_test_certificate_request.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py external/ipfs_datasets/tests/unit/logic/zkp/test_deferred_test_certificate_request.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/deferred-issuer-v2
- Parallel lane: ptr-deferred-issuer-v2
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_datasets/tests/unit/logic/zkp/test_deferred_test_certificate_request.py
- Predicted symbols: DeferredTestCertificateRequest, TestCertificateIssuerFactory, CertificateIssuanceDisposition
- Interfaces: DeferredTestCertificateRequest@1, TestCertificateIssuerFactory@1, TestPassStatementV2
- Submodules: external/ipfs_datasets
- Generated artifacts: deterministic deferred-request and unavailable-backend fixtures
- Conflict policy: Construct a public canonical request only after terminal pass and keep witness material process-local; imports, backend discovery and bounded installation occur only when issuance is requested and package auto-install policy allows it, never during package import or collection.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-132 defines exact versioned public inputs and existing Groth16/ProveKit adapters expose lazy capability results.
- Effects: Lets the accelerator hand datasets a typed public request reconstructed from retained canonical receipt and candidate-context bytes while deferring costly proving outside the pytest worker's pass path.
- Evidence subset: Public request canonicalization, witness redaction, bounded backend selection, lazy import/install traces, timeout/cancellation, real fixture verification and unavailable-capability reason codes
- Acceptance: The request binds exact statement, receipt, execution, candidate-context, policy, circuit, verifier-key, issuer and epoch values; unknown/private/noncanonical fields are rejected; factory selection is bounded and lazy; supported package dependencies are exposed as declared extras and are installed automatically only on first requested issuance when package auto-install policy permits; a disable setting is honored; missing installer, package, key, circuit, endpoint, binary, cache or network returns a typed DEFERRED/RUN result with the pass receipt retained; simulated proofs remain non-authoritative; and no secret or witness is serialized into cache, logs, xdist messages or public artifacts.

## PTR-138 Compose automatic pytest proof-reuse dependency injection

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: pytest-runtime-composition
- Depends on: PTR-136, PTR-137
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_composition.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py external/ipfs_accelerate/test/api/test_proof_reuse_service_injection.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py external/ipfs_accelerate/test/api/test_proof_reuse_runtime_composition.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/runtime-composition
- Parallel lane: ptr-runtime-composition
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_composition.py
- Predicted symbols: DefaultProofReuseServices, ProofReuseRuntimeComposition, DeferredIssuanceEnvelope
- Interfaces: ProofReuseServices@1, RuntimeContextRevalidator@1, DeferredTestCertificateRequest@1, PytestProofReusePlugin@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: hermetic plugin lifecycle, xdist and deferred-issuance fixtures
- Conflict policy: The plugin owns orchestration but not trust; explicit injected services override lazy defaults, workers transmit only admitted public envelopes, and every hook exception degrades to normal pytest execution.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-136 provides fresh context revalidation and PTR-137 provides a typed datasets issuance request and lazy issuer boundary.
- Effects: Makes default services the normal plugin path, connects two-stage lookup and local certificate verification before setup, and connects terminal pass receipts plus runtime traces to controller-owned deferred issuance.
- Evidence subset: Off/shadow/read/write/readwrite hooks, default and explicit DI, local verification, terminal report lifecycle, runtime trace capture, worker/controller serialization and atomic publication
- Acceptance: Every eligible collected item obtains scoped defaults without item monkeypatches or per-test registries; candidate lookup rehashes context and requires fresh current revalidation plus local real-certificate verification before standard SKIP; receipt creation requires passed setup/call/teardown and a complete observed runtime trace; the controller reconstructs and validates deferred requests from public retained bytes instead of trusting workers; workers never serialize witness or private request data; xdist publication is fenced and atomic; and any import, identity, cache, transport, verifier, issuer or controller failure runs the test or retains a deferred receipt without failing pytest.

## PTR-139 Enable accelerator direct-node bootstrap and lazy dependencies

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: accelerator-zero-config-bootstrap
- Depends on: PTR-138
- Goal id: PTR-G070
- Outputs: external/ipfs_accelerate/conftest.py, external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/requirements.txt, external/ipfs_accelerate/ipfs_accelerate_py/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lazy_dependencies.py, external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_zero_config.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_bootstrap.py external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_zero_config.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/accelerator-zero-config
- Parallel lane: ptr-accelerator-zero-config
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/conftest.py, external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/requirements.txt, external/ipfs_accelerate/ipfs_accelerate_py/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lazy_dependencies.py, external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_zero_config.py
- Predicted symbols: AcceleratorProofReuseBootstrap, ProofReuseLazyDependencyInstaller
- Interfaces: PytestProofReusePlugin@1, ProofReuseLazyDependencyInstaller@1, DefaultProofReuseServices
- Submodules: external/ipfs_accelerate
- Generated artifacts: isolated installed/source-tree direct-node and missing-dependency fixtures
- Conflict policy: Register one lightweight plugin loader and scoped imports; dependency declarations are additive and first-use automatic installation is bounded, allowlisted, package-policy-controlled, lock/fence protected and never required for test execution.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-138 composes the full default runtime and the accelerator packaging, conftest and existing bootstrap tests are available.
- Effects: Makes proof reuse discoverable for accelerator suite and direct-node execution and aligns optional content-addressing/ZK dependencies across requirements, setup metadata and modern project metadata.
- Evidence subset: Installed pytest11 discovery, source-tree conftest discovery, autoload-disabled direct node, requirements/setup/pyproject dependency parity, lazy installer lock/retry/failure behavior and scoped import graph
- Acceptance: Off mode and ordinary tests import only the lightweight loader; `ipfs_accelerate_py.__init__` exposes only a narrow lazy proof-reuse bootstrap facade; read/write modes lazily build defaults without manual item attributes or conftest service injection; strict content-addressing and datasets-ZK requirements are declared consistently as core or proof-reuse extras; first-use installation runs automatically only when a requested proof-reuse capability is missing and package auto-install policy permits it, using bounded allowlisted package/version specs and atomic interprocess fencing; disabled installer, offline index, resolver failure, incompatible version, read-only environment or missing dependency emits a typed capability reason and runs tests; and coverage, mutation, profiling, debugger and leak-detection modes remain non-reusing.

## PTR-140 Enable datasets direct-node bootstrap and lazy dependencies

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-zero-config-bootstrap
- Depends on: PTR-137, PTR-138
- Goal id: PTR-G080
- Outputs: external/ipfs_datasets/tests/conftest.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/requirements.txt, external/ipfs_datasets/ipfs_datasets_py/__init__.py, external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py, external/ipfs_datasets/tests/unit/test_proof_reuse_zero_config.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py external/ipfs_datasets/tests/unit/test_proof_reuse_zero_config.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-zero-config
- Parallel lane: ptr-datasets-zero-config
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/tests/conftest.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/requirements.txt, external/ipfs_datasets/ipfs_datasets_py/__init__.py, external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py, external/ipfs_datasets/tests/unit/test_proof_reuse_zero_config.py
- Predicted symbols: DatasetsProofReuseBootstrap, DatasetsProofReuseLazyDependencies
- Interfaces: PytestProofReusePlugin@1, DeferredTestCertificateRequest@1, TestCertificateIssuerFactory@1
- Submodules: external/ipfs_datasets
- Generated artifacts: isolated datasets installed/source-tree direct-node and missing-backend fixtures
- Conflict policy: The datasets shim exposes only lazy protocols and never imports accelerator internals at package import; legacy commit-cache state, installer success and backend availability never authorize a skip.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-137 defines datasets deferred issuance, PTR-138 defines shared runtime composition, and the current datasets shim/bootstrap and packaging files are available.
- Effects: Makes individual datasets tests inherit the shared plugin and local ZK provider while declaring the exact content-addressing, verifier and optional proving dependency surface in every supported packaging manifest.
- Evidence subset: Direct-node and suite discovery, scoped import graph, requirements/setup/pyproject parity, lazy installer/backend probes, legacy commit-cache non-authority and terminal-pass issuance lifecycle
- Acceptance: Installed and source-tree datasets invocations discover the shared plugin without a file list; `ipfs_datasets_py.__init__` and the shim use narrow lazy imports and inject only public provider protocols; proof-reuse extras and backend-specific extras are consistently pinned in requirements, setup and pyproject metadata; first-use installation is bounded and allowlisted and runs automatically only when package auto-install policy permits, while native Groth16 builds and NLTK data downloads always require separate explicit opt-in; missing accelerator plugin, multiformats, Groth16 endpoint, ProveKit binary, key, circuit, cache, network, installer or write permission runs tests and retains typed deferred state; and no nested legacy hook, commit cache or simulated proof can skip.

## PTR-141 Enable kit direct-node bootstrap and lazy dependencies

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: kit-zero-config-bootstrap
- Depends on: PTR-133, PTR-138
- Goal id: PTR-G090
- Outputs: external/ipfs_kit/conftest.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/requirements.txt, external/ipfs_kit/ipfs_kit_py/__init__.py, external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py, external/ipfs_kit/tests/test_proof_reuse_zero_config.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_kit/tests/test_proof_reuse_bootstrap.py external/ipfs_kit/tests/test_pytest_proof_reuse_shim.py external/ipfs_kit/tests/test_proof_reuse_zero_config.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/kit-zero-config
- Parallel lane: ptr-kit-zero-config
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_kit/conftest.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/requirements.txt, external/ipfs_kit/ipfs_kit_py/__init__.py, external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py, external/ipfs_kit/tests/test_proof_reuse_zero_config.py
- Predicted symbols: KitProofReuseBootstrap, KitProofReuseLazyDependencies
- Interfaces: PytestProofReusePlugin@1, CanonicalArtifactStoreTransport@1, TestReuseCapabilityReport@1
- Submodules: external/ipfs_kit
- Generated artifacts: isolated kit installed/source-tree direct-node and no-daemon fixtures
- Conflict policy: Kit injects an optional byte-transport protocol only; narrow lazy imports and installers must never start Kubo, Lotus or Iroh, initialize a repository, or make availability a launch/test gate.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-133 hardens canonical candidate transport, PTR-138 defines shared runtime composition, and current kit shims, bootstrap and packaging files are available.
- Effects: Makes kit tests automatically discover proof reuse and exposes strict candidate/certificate storage only when requested, with content-addressing dependencies represented consistently in packaging and lazy installation metadata.
- Evidence subset: Direct-node and suite discovery, scoped import graph, requirements/setup/pyproject parity, installer failure matrix, canonical transport injection, daemon/user-directory/network isolation and missing-plugin fallback
- Acceptance: Installed and source-tree kit invocations discover the shared plugin without per-test wiring; `ipfs_kit_py.__init__` and the shim import no accelerator or daemon-heavy modules eagerly; exact multiformats/content-addressing requirements are consistently declared; bounded allowlisted installation runs automatically only at first requested transport use when package auto-install policy permits and honors the disable setting; missing plugin, multiformats, store, cache, network, installer or write permission runs tests; all proof-hit and miss paths start no daemon and create no user IPFS state; and kit transport never interprets a certificate or authorizes SKIP.

## PTR-142 Prove runtime activation, refresh the gate, and publish handoff

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: runtime-activation-closeout
- Depends on: PTR-139, PTR-140, PTR-141
- Goal id: PTR-G110
- Outputs: external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py, external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_reuse_benchmark.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_RUNTIME_ACTIVATION_HANDOFF.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_e2e.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py external/ipfs_accelerate/test/api/test_agent_supervisor_proof_reuse_benchmark.py external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/runtime-closeout
- Parallel lane: ptr-runtime-closeout
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py, external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_reuse_benchmark.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_RUNTIME_ACTIVATION_HANDOFF.md
- Predicted symbols: RuntimeActivationE2E, ProofReuseRuntimeActivationGate, runtime activation operator handoff
- Interfaces: ProofReuseActivationContract@1, RuntimeContextRevalidator@1, PytestProofReusePlugin@1, ProofTestReuseCurrentTreeGateDecision@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: cross-repository cold/pass/deferred/warm/mutation receipts, zero-false-skip matrix, warm benchmark, refreshed 53-task gate and operator runbook
- Conflict policy: Exercise disposable repositories, environments, caches and state roots; never use the proof-reuse cache to validate this implementation, treat synthetic proof as deployment authority, mutate live control files, or run the objective closeout before the expanded board is closed.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-139, PTR-140 and PTR-141 provide the complete automatic runtime and repository bootstraps; all prior 50 tasks remain closed with replayable provenance.
- Effects: Proves the default runtime over all three repositories, refreshes adversarial and performance evidence, expands final-tree authority to the exact 53-task population, and documents the final explicit controller closeout.
- Evidence subset: Installed and source direct-node flows, lazy dependency matrix, canonical candidate bytes, current revalidation, real local certificate verification, deferred issuance, xdist fencing, mutation/security populations, benchmark/rollout receipts and supervisor launch health
- Acceptance: Without test-file hardwiring or manual service injection, one direct node in each repository executes on cold miss, records exactly one complete pass and runtime trace, retains exact candidate context, accepts a locally verifiable real certificate, then emits one standard proof-backed skip on an unchanged warm run; every admitted source, AST, indirect dependency, fixture, hook, parameter, environment, lock, capability, policy, circuit, key, issuer, epoch, cache and transport mutation forces RUN; missing or failing installers, packages, Groth16, ProveKit, cache, IPFS, network, key or circuit never blocks pytest or the supervisor; xdist publishes no duplicate/partial/private authority; sequential proof-reuse-off assurance reports zero false skips before the benchmark; warm eligible verification is cheaper than execution and meets the configured target; the gate requires all 53 tasks and fresh repair evidence; and the handoff invokes the existing outer closeout controller only after validation succeeds and an operator reviews the protected lifecycle update.

## PTR-143 Attach stable locator-first collection seeds

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: production-locator-first-identity
- Depends on: PTR-142
- Goal id: PTR-G020
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/collection_seed.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/default_identity_services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/item_identity.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/test/api/test_proof_reuse_locator_first_collection.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_locator_first_collection.py external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_item_identity.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/production-locator-first
- Parallel lane: ptr-production-locator-first
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/collection_seed.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/default_identity_services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/item_identity.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/test/api/test_proof_reuse_locator_first_collection.py
- Predicted symbols: ProofReuseCollectionSeed, LocatorFirstItemIdentityAssembler, ITEM_COLLECTION_SEED_ATTRIBUTE, DefaultIdentityServiceFactory.obtain_static_identity
- Interfaces: ProofReuseCollectionSeed@1, TestLocatorKey@1, DefaultIdentityServiceFactory@1, PytestProofReusePlugin@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: deterministic parameterized and unparameterized collection-seed CID vectors
- Conflict policy: Collection may attach only a stable locator and canonical static seed; it must not fabricate a current runtime trace, final execution key, eligibility decision, cache hit, or skip authority.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-142 is historically closed, and its activation claim has been superseded by the reviewed current-tree audit while existing identity contracts remain available.
- Effects: Splits stable collection identity from post-pass execution identity so every ordinary collected item can perform locator-only candidate discovery without pre-executing fixtures or requiring injected runtime evidence.
- Evidence subset: Default static identity, exact node/parameter facts, repository descriptor and forest, AST/static trace, current identity components, plugin collection hook and fail-open diagnostics
- Acceptance: In read, write, and readwrite modes a direct collected node receives a canonical collection seed and stable locator before any runtime trace exists; parameterized nodes bind the exact canonical parameter-value CID; collection performs no fixture or test call and attaches no final execution key; explicit injected identity remains an override; incomplete or exceptional static facts attach no lookup authority and execute normally; and off mode retains its cold import behavior.

## PTR-144 Provide lazy real Groth16 test-certificate issuance

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-real-groth16-test-pass
- Depends on: PTR-142
- Goal id: PTR-G050
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_pass_groth16_provider.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/provekit/test_pass_circuit.py, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/circuit.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/lib.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/prover.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/verifier.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/setup.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.sh, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_groth16_provider.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.sh --seed 144 && IPFS_TEST_PROOF_REUSE_MODE=off IPFS_DATASETS_ENABLE_GROTH16=1 python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_groth16_provider.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-real-groth16-test-pass
- Parallel lane: ptr-datasets-real-groth16-test-pass
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_pass_groth16_provider.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/provekit/test_pass_circuit.py, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/circuit.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/lib.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/prover.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/verifier.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/setup.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.sh, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_groth16_provider.py
- Predicted symbols: TestPassGroth16CircuitV4, LazyGroth16TestCertificateProvider, IssuedTestCertificateMaterial, build_default_test_certificate_issuer
- Interfaces: DeferredTestCertificateRequest@1, TestCertificateIssuerFactory@1, TestExecutionCertificateV2, Groth16TestPassProvider@1
- Submodules: external/ipfs_datasets
- Generated artifacts: deterministic local test-pass circuit proving and verification keys plus real proof/certificate conformance vectors
- Conflict policy: Add a test-pass-specific real circuit and provider rather than relabeling an unrelated Groth16 proof; no simulated, deterministic-signature, HMAC, metadata-only, or unchecked provider output may become certificate authority.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-132 and PTR-137 provide the canonical V2 statement and deferred request surfaces; native build and NLTK/package dependency work may land independently but remains explicit and lazy.
- Effects: Supplies the default datasets issuance boundary with a bounded, first-use local Groth16 prover/verifier and returns complete public certificate material to the controller without serializing private witness data.
- Evidence subset: Canonical V2 statement and private witness, circuit constraints, Rust setup/prove/verify wire format, pinned key/circuit identities, lazy provider probes, issuer idempotency and outage dispositions
- Acceptance: The native circuit cryptographically binds every V2 public input and enforces the admitted pass witness rather than trusting host metadata; a locally generated proof verifies under the pinned key and fails for any receipt, execution, candidate-context, policy, circuit, key, issuer, epoch, phase, or proof mutation; the factory returns complete canonical certificate material only after local real verification; construction/import performs no build, install, setup, network, or proving work; first requested issuance may use only explicit reviewed local artifacts; and missing binary, key, circuit, cache, package, installer, endpoint, timeout, or write permission returns typed DEFERRED while retaining the pass.

## PTR-145 Wire locator-first candidate revalidation and fresh current context

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: production-two-stage-warm-lookup
- Depends on: PTR-143
- Goal id: PTR-G040
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/current_context_provider.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runtime_revalidation.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lookup.py, external/ipfs_accelerate/test/api/test_proof_reuse_two_stage_warm_lookup.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_two_stage_warm_lookup.py external/ipfs_accelerate/test/api/test_proof_reuse_runtime_revalidation.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_lookup.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/production-two-stage-warm
- Parallel lane: ptr-production-two-stage-warm
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/current_context_provider.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runtime_revalidation.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lookup.py, external/ipfs_accelerate/test/api/test_proof_reuse_two_stage_warm_lookup.py
- Predicted symbols: DefaultCurrentContextProvider, ProofReuseTwoStageLookup, RevalidatedProofReuseLookupRequest, RuntimeContextRevalidator.revalidate
- Interfaces: CurrentContextProvider@1, RuntimeContextRevalidator@1, ProofReuseLookup@1, TestCandidateContextStore@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: locator-only warm lookup and current-context mutation vectors
- Conflict policy: The dedicated candidate-context store is the only locator-stage source; its result remains non-authoritative, and certificate-cache verification is unreachable until fresh exact revalidation succeeds.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-143 supplies a stable collection seed; existing immutable candidate-context and proof-cache contracts remain available.
- Effects: Implements the production two-stage warm path from locator hint to rehashed retained context, live dependency resolution and current identity rebuild, followed only then by authoritative certificate-cache admission.
- Evidence subset: Dedicated candidate store lookup, retained canonical component rehash, live filesystem/module/environment frontier resolution, per-item static identity rebuild, exact current execution-key comparison and proof-cache handoff
- Acceptance: Warm lookup begins with locator plus current collected item only; a dedicated TestCandidateContextStore returns retained bytes; every component is rehashed; the retained runtime frontier is resolved against admitted live roots; the current AST, static trace, fixtures, hooks, parameters, repository forest, locks, distributions, environment, capabilities, snapshots and policy are rebuilt without fixture or test execution; the final current execution key exactly matches the candidate before proof verification; revalidation alone can never skip; and every miss, mismatch, unknown, timeout, corruption, provider absence, or exception returns RUN.

## PTR-146 Capture cold runtime trace and assemble final pass candidate

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: production-cold-pass-publication
- Depends on: PTR-143
- Goal id: PTR-G030
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runtime_trace_lifecycle.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/candidate_publication.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/test/api/test_proof_reuse_cold_pass_publication.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_cold_pass_publication.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_runtime_dependency_trace.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/production-cold-pass
- Parallel lane: ptr-production-cold-pass
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runtime_trace_lifecycle.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/candidate_publication.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/test/api/test_proof_reuse_cold_pass_publication.py
- Predicted symbols: PytestRuntimeTraceLifecycle, CompletedExecutionIdentity, CandidatePublicationEnvelope, build_completed_execution_identity
- Interfaces: RuntimeTestDependencyTracer@1, TestExecutionKey@1, TestPassReceipt@1, CandidateExecutionContext@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: complete one-call setup/call/teardown trace, receipt, final-key and candidate-context vectors
- Conflict policy: Start one real runtime tracer around the single pytest protocol execution and finalize only after teardown; an incomplete observation may preserve the test pass but may not create a receipt, candidate, proof request, or index entry.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-143 attaches the stable locator/static seed and the existing runtime tracer, receipt and candidate contracts are available.
- Effects: Connects the ordinary cold execution lifecycle to an observed runtime trace, compiles the final execution key after that trace exists, finalizes one admitted pass receipt, and constructs the exact canonical candidate publication envelope.
- Evidence subset: Pytest protocol and report hook ordering, CPython audit/profile tracer, complete phase reports, final execution identity compiler, retained forest/static/runtime/environment/policy/receipt bytes and failure cleanup
- Acceptance: The tracer starts immediately before setup and stops only after teardown without invoking the body twice; setup, call and teardown must each pass exactly once; its complete observed trace is canonical and bound into a newly compiled final execution key; the receipt binds that final key and trace; the candidate descriptor and every required canonical component are retained; skipped, xfailed, failed, incomplete, uncontrolled, overflowed, or exceptional traces publish nothing authoritative; and tracing faults never alter pytest's real outcome.

## PTR-147 Compose default two-stage lookup and atomic controller issuance/publication

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: production-runtime-controller-composition
- Depends on: PTR-144, PTR-145, PTR-146
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/default_identity_services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py, external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py, external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py, external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_composition.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py external/ipfs_accelerate/test/api/test_proof_reuse_runtime_composition.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py external/ipfs_accelerate/test/api/test_proof_reuse_service_injection.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/production-controller-composition
- Parallel lane: ptr-production-controller-composition
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/default_identity_services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py, external/ipfs_accelerate/test/api/test_proof_reuse_default_identity_services.py, external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py, external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_composition.py
- Predicted symbols: DATASETS_VERIFIER_REVISION, DATASETS_GROTH16_REVIEWED_FILES_SHA256, DefaultProofReuseServices.candidate_store, DefaultProofReuseServices.issuer, Groth16ArtifactIdentityBindings, build_default_identity_services, ProofReuseLazyDependencyInstaller.ensure_groth16_native_backend, ProofReuseControllerPublicationTransaction, IssuedCertificatePublicationResult, ProofReuseXdistCoordinator.flush_publications, compose_default_proof_reuse_services
- Interfaces: ProofReuseServices@1, ProofReuseTwoStageLookup@1, TestCandidateContextStore@1, TestCertificateIssuerFactory@1, ProofReuseXdistCoordinator@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: default cold/warm composition, deferred issuance retry and atomic controller publication fixtures
- Conflict policy: Explicit injected services still win; defaults use separate candidate-context and certificate stores; workers carry admitted public bytes only; and only the controller may issue, verify, fence and publish certificate index authority.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-144 provides the lazy real datasets issuer, PTR-145 the two-stage warm path, and PTR-146 the complete cold candidate envelope.
- Effects: Makes the repaired paths the normal zero-configuration plugin services, stores complete cold candidates, performs controller-owned lazy issuance, locally re-verifies returned real certificates, and exposes only an atomically indexed certificate to warm proof-cache admission.
- Evidence subset: Default cache-root layout, candidate/certificate store separation, lazy scoped datasets import, explicit first-issuance native/runtime activation, reviewed circuit/proving/verifying-key byte identities, plugin hook composition, xdist public transport, write fences, immediate/deferred issuer timeout/retry, local verifier and crash/restart orderings
- Acceptance: Default composition first advances the accelerator's reviewed datasets revision and source/artifact digest manifests to the exact merged PTR-144 provider commit, then instantiates a persistent dedicated candidate-context store, certificate store, current-context provider, revalidator, two-stage lookup and non-None lazy real issuer without eager optional imports; collection and lookup never build or prove, while the first actual controller issuance calls the bounded Groth16 provisioner and runtime readiness inspection only when the explicit native-build policy permits it; the generic pre-PTR-144 knowledge-of-axioms backend or a native binary alone remains non-authoritative, and `IPFS_DATASETS_ENABLE_GROTH16=1` is published only after the test-pass-specific circuit/key capability and exact provenance are ready; the default policy derives circuit and verifying-key CIDs from the exact reviewed circuit and activated key bytes rather than labels or certificate metadata, and local verification proves that the backend actually used the artifact root matching those pins; missing, synthetic, stale, substituted or mismatched artifact provenance returns RUN/DEFERRED; cold publication writes and rehashes candidate components and receipt before issuance; the controller consumes both immediate and deferred issuer results, locally verifies every success, and atomically publishes the complete candidate context, certificate bytes and index exactly once; `flush_publications()` may not discard a returned certificate or omit `put_candidate`; a crash or failure may leave an immutable non-authoritative candidate/receipt for retry but never a partial skip candidate; workers serialize no witness/private material; cache, issuer, Groth16, transport, lock, permission or controller absence preserves the pass and returns RUN/DEFERRED; and unchanged warm collection can reach a standard proof-cache skip only through the complete authority sequence.

## PTR-148 Prove genuine zero-injection three-repo cold-to-warm reuse and measured subprocess savings

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: production-zero-config-e2e
- Depends on: PTR-147
- Goal id: PTR-G100
- Outputs: external/ipfs_accelerate/test/api/proof_reuse_real_groth16_fixture.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_subprocess_benchmark.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/self_improvement/proof_reuse_benchmark.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off IPFS_DATASETS_ENABLE_GROTH16=1 python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_e2e.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py external/ipfs_accelerate/test/api/test_proof_reuse_subprocess_benchmark.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/production-zero-config-e2e
- Parallel lane: ptr-production-zero-config-e2e
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/proof_reuse_real_groth16_fixture.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_subprocess_benchmark.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/self_improvement/proof_reuse_benchmark.py
- Predicted symbols: ProductionRuntimeActivationE2E, RealGroth16TestPassFixture, SubprocessProofReuseBenchmarkReceipt
- Interfaces: PytestProofReusePlugin@1, TestExecutionCertificateV2, ProofReuseBenchmarkReceipt@1, ProofReuseActivationContract@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: three-repository two-process cold/pass/candidate/certificate/warm-skip receipts and measured wall-time benchmark samples
- Conflict policy: Use disposable repositories, cache roots and subprocesses only; generated conftests may configure test data but may not inject proof-reuse services or item identity attributes, and no deterministic pseudo-proof or in-memory orchestrator counts as activation evidence.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-147 exposes the complete default runtime and PTR-144's real local Groth16 circuit artifacts are available through the reviewed explicit test fixture.
- Effects: Replaces the historical injected/pseudo-certificate claims with direct evidence from two independent pytest processes and records actual subprocess execution and verification timings.
- Evidence subset: Installed/source-tree accelerator, datasets and kit bootstrap, direct node selection, persistent isolated cache, real local Groth16 proof, body side-effect log, pytest terminal outcomes, missing-backend fail-open case and perf-counter samples
- Acceptance: For one unmodified direct node in each repository, with no set_proof_reuse_services call, item monkeypatch, lookup request fixture, fake verifier, pseudo-certificate, or per-test registry, the first independent pytest process reports one pass, executes the body once, captures a complete trace and publishes a locally verified real Groth16 certificate; the second process using the same cache reports exactly one standard proof-cache skip and the body log remains one line; missing Groth16 runs and passes the test on both invocations without blocking; measured subprocess samples derive from actual cold execution and warm verification, retain raw timings, show zero false skips and demonstrate positive saved wall time without synthetic constants; and all three repository bootstraps satisfy the same assertions.

## PTR-149 Refresh live capability reporting, the 66-task gate, and operator handoff

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: production-activation-authority-closeout
- Depends on: PTR-155
- Goal id: PTR-G110
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/reporting.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_report.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_RUNTIME_ACTIVATION_HANDOFF.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_report.py external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_e2e.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py external/ipfs_accelerate/test/api/test_proof_reuse_subprocess_benchmark.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/production-activation-closeout
- Parallel lane: ptr-production-activation-closeout
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/reporting.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_report.py, external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_RUNTIME_ACTIVATION_HANDOFF.md
- Predicted symbols: ProofReuseRuntimeActivationReport, proof_reuse_runtime_activation_report, PRODUCTION_RUNTIME_ACTIVATION_TASK_IDS, production activation operator handoff
- Interfaces: ProofReuseServices@1, ProofReuseRuntimeActivationReport@1, ProofTestReuseCurrentTreeGateDecision@1, ProofReuseBenchmarkReceipt@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: live typed capability report, genuine production-activation evidence packet, exact 66-task gate vectors, truthful activation-gap packet and corrected operator runbook
- Conflict policy: Report only capabilities actually composed and probed in the current process/tree; source-symbol presence, historical PTR-142 fixtures, task labels, simulated proof and optimistic booleans are inadmissible, and only the existing outer controller may write objective lifecycle state.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-155 joined the PTR-153/PTR-154 proof-material and controller-context branches into exact local v4 verification and atomic publication after PTR-152 established the fail-closed authority boundary.
- Effects: Replaces hard-coded activation inventory with live typed service/capability reporting, expands final authority to the exact 66-task population, requires fresh thirteen-task corrective-wave evidence, publishes a truthful activation gap when reviewed authority artifacts are absent, and publishes the explicit operator closeout handoff only when they are present and valid.
- Evidence subset: Live default composition and capability probes, all thirteen reviewed correction task receipts, exact reviewed v4 native source/binary/capability and circuit/key manifests, real Groth16 proof/certificate CIDs, three-repository two-process outcomes, raw benchmark samples, zero-false-skip assurance, supervisor health and current repository/objective identities
- Acceptance: Reporting derives availability from live typed services and bounded non-mutating probes and never imports, installs, builds, downloads NLTK data, runs trusted setup, or generates keys merely to claim readiness; it reports native Groth16 installation/readiness separately from test-certificate authority, and neither the generic pre-PTR-144 knowledge-of-axioms backend nor an unmanifested native binary can satisfy the latter; the current-tree gate requires exactly all 66 tasks plus fresh authoritative production-runtime-activation evidence produced by PTR-149 covering PTR-143 through PTR-155; positive authority must bind the genuine no-injection three-repository two-process results, a locally verified real current-v4 Groth16 certificate, controller-owned receipt/candidate context, retained proof-bearing issuance material, exact reviewed source/binary/capability/circuit/key identities, measured subprocess benchmark, zero false skips, current tree/forest/policy identities and healthy supervisor; absent operator-provided reviewed v4 keys or trusted-setup manifest yields an explicit activation gap, continues running tests, and cannot produce a false warm skip or closeout; any PTR-142, 53-task, pre-v4 60-task, pre-material 63-task, injected, pseudo-certificate, structural-only verification, synthetic-timing, missing, stale, substituted, or mismatched evidence fails closed; all validations run with proof reuse off; and the runbook invokes the existing fenced outer closeout only after the board is closed, the refreshed gate passes, and an operator reviews the protected lifecycle update.

## PTR-150 Add explicit setup-facing lazy proof-reuse provisioning

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: dependency-provisioning
- Depends on: PTR-148
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/setup.py, external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/provisioning_cli.py, external/ipfs_accelerate/test/api/test_proof_reuse_setup_provisioning.py, external/ipfs_accelerate/docs/guides/TEST_PROOF_REUSE_DEPENDENCY_PROVISIONING.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_setup_provisioning.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/setup-provisioning
- Parallel lane: ptr-setup-provisioning
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/setup.py, external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/provisioning_cli.py, external/ipfs_accelerate/test/api/test_proof_reuse_setup_provisioning.py, external/ipfs_accelerate/docs/guides/TEST_PROOF_REUSE_DEPENDENCY_PROVISIONING.md
- Predicted symbols: ProofReuseProvisioningCLI, ProvisionProofReuseDependencies, setup-facing proof-reuse provision command
- Interfaces: LazyDependencyProvisioner@1, ProofReuseDependencySpec@1, ProofReuseProvisioningResult@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: explicit provisioning receipts for Python dependencies, optional NLTK data and the datasets native Groth16 backend
- Conflict policy: Own only accelerator setup-facing provisioning surfaces; normal setup, build, metadata inspection and import remain side-effect free, and generated dependencies or native artifacts are never committed by the task.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-148 established the genuine three-repository activation harness and the existing accelerator manifests, package bootstrap and bounded lazy provisioner are available at their reviewed revisions.
- Effects: Adds one explicit setup-facing command and module CLI that delegate to the existing bounded lazy provisioner, document the consent boundary, and report each selected capability without turning package installation or test collection into an implicit installer.
- Evidence subset: requirements/setup/pyproject parity, allowlisted dependency identifiers, setup command and module CLI argument vectors, environment-policy decisions, bounded subprocess receipts, NLTK package/data cases, datasets native Groth16 build case and unavailable/failure cases
- Acceptance: `requirements.txt`, setup metadata and `pyproject.toml` retain parity for importable proof-reuse dependencies including NLTK and multiformats; ordinary wheel/sdist metadata generation, `pip install`, `setup.py` invocation without the explicit provisioning command, package import, pytest collection and proof-reuse-off validation perform no network access, pip install, NLTK data download, Rust build, trusted setup or key generation; an explicit operator-selected setup-facing command and equivalent module CLI use the same allowlisted lazy installer as runtime first use, can provision the NLTK package and explicitly selected NLTK data and can request the datasets native Groth16 build without pretending that Groth16 is a PyPI distribution; automatic first-use installation occurs only when the existing package auto-install policy explicitly permits it; arguments, timeouts, environment and artifact roots are bounded; missing network, compiler, Cargo, datasets source, permissions or cache returns a typed unavailable result, keeps the supervisor healthy and runs tests; and individual direct-node tests continue to discover the package-level plugin without any per-test registry or file-list hardwiring.

## PTR-151 Publish an auditable v4-capable native Groth16 backend without automatic trusted setup

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-native-groth16-v4
- Depends on: PTR-148
- Goal id: PTR-G050
- Outputs: external/ipfs_datasets/MANIFEST.in, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/ipfs_datasets_py.egg-info/SOURCES.txt, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.toml, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.sh, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/RUST_SETUP.md, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/main.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/groth16, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/release-manifest.json, external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_native_release.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off cargo test --manifest-path external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.toml && IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_native_release.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-native-groth16-v4
- Parallel lane: ptr-datasets-native-groth16-v4
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/MANIFEST.in, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/ipfs_datasets_py.egg-info/SOURCES.txt, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.toml, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.sh, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/RUST_SETUP.md, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/main.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/groth16, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/release-manifest.json, external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_native_release.py
- Predicted symbols: Groth16NativeCapabilitiesV4, locked native source identity, Groth16NativeReleaseManifestV1
- Interfaces: Groth16BackendCLI@1, TestPassStatementV4, Groth16NativeReleaseManifest@1
- Submodules: external/ipfs_datasets
- Generated artifacts: staged linux-aarch64 native Groth16 binary, exact binary/source capability manifest and reproducible build receipts; no production proving or verifying keys
- Conflict policy: Own only the datasets native backend/release and packaging surfaces; do not run or publish an automatic production trusted setup, do not add v4 key artifacts, and do not modify the accelerator branch in parallel.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-148 exposed that the reviewed test-pass statement profile is v4 while the staged native backend and prior release evidence advertise only older profiles; the reviewed locked Rust source is available and trusted-setup/key ceremony remains operator-owned.
- Effects: Makes native capability discovery explicit and artifact-free, publishes a current v4-capable staged binary with a digest-bound source/capability manifest, keeps ordinary source/package builds side-effect free, and documents a separate explicit test-only deterministic setup path.
- Evidence subset: locked Rust dependency/source identity, `capabilities --json` bytes and schema, statement profiles 1 through 4, v4 test-pass circuit identifier, artifact-free probe filesystem diff, default-build side-effect assertions, staged binary SHA-256, release-manifest cross-check and package inclusion
- Acceptance: `groth16 capabilities --json` is bounded, deterministic and artifact-free and reports supported statement profiles 1 through 4 including the current v4 test-pass profile, exact provider/circuit identity and deterministic locked-source identity; the default Cargo/package build performs no trusted setup and generates no proving or verifying keys; deterministic setup is explicitly test-only and cannot be mistaken for production authority; the staged linux-aarch64 binary and packaged release manifest bind the exact binary digest, locked source identity and capability payload and are independently cross-checked by tests; packaging includes the reviewed binary and manifest; no v4 key artifact is added to source control; and missing Cargo, target toolchain, source, compiler or writable output directory remains a typed unavailable build/provisioning result in consumers rather than blocking test execution or permitting an older backend to authorize a skip.

## PTR-152 Fail-closed accelerator Groth16 v4 authority and lazy-runtime hardening

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: production-v4-authority
- Depends on: PTR-150, PTR-151
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/docs/guides/TEST_PROOF_REUSE_DEPENDENCY_PROVISIONING.md, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lazy_dependencies.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/reporting.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py, external/ipfs_accelerate/test/api/test_proof_reuse_lazy_provisioning.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_report.py, external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_zero_config.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py external/ipfs_accelerate/test/api/test_proof_reuse_lazy_provisioning.py external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_report.py external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_zero_config.py
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/production-v4-authority
- Parallel lane: ptr-production-v4-authority
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/docs/guides/TEST_PROOF_REUSE_DEPENDENCY_PROVISIONING.md, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lazy_dependencies.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/reporting.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py, external/ipfs_accelerate/test/api/test_proof_reuse_lazy_provisioning.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_report.py, external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_zero_config.py
- Predicted symbols: Groth16V4AuthorityManifest, current native release verifier, effective proof-reuse runtime capability report, isolated lazy pip invocation
- Interfaces: ProofReuseServices@1, LazyDependencyProvisioner@1, ProofReuseRuntimeActivationReport@1, Groth16NativeReleaseManifest@1, TestExecutionCertificateV2
- Submodules: external/ipfs_accelerate
- Generated artifacts: typed current-v4 native release/key authority decisions, sanitized lazy-install receipts and activation reports; no trusted setup or generated keys
- Conflict policy: Join the reviewed PTR-150 accelerator and PTR-151 datasets contracts only after both merge; never generate trusted setup or keys, trust arbitrary environment paths, promote bundled legacy artifacts, or report source-symbol presence as runtime authority.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-150 exposes explicit setup-facing provisioning through the bounded accelerator lazy installer, and PTR-151 publishes the reviewed artifact-free v4 capability contract plus exact datasets native binary/source release manifest without production keys.
- Effects: Enforces a two-gate native-release-and-key-manifest authority policy at accelerator issuance/publication, rejects structural-only or context-free certificate publication, reports installed/readiness/authority states truthfully, and makes lazy pip execution isolated and sanitized while preserving typed RUN/DEFERRED behavior for every optional-capability failure; PTR-153 through PTR-155 complete the positive proof-material/context/V2-publication path without weakening this denial boundary.
- Evidence subset: manifest schema/version, exact native binary and locked-source digests, artifact-free capability payload, provider/circuit/statement-profile identity, proving/verifying-key byte digests, environment substitution attacks, legacy bundled binary/key cases, installed-wheel source discovery, effective build/install policy, sanitized pip argv/environment and missing-dependency outcomes
- Acceptance: No arbitrary environment key directory, unverifiable source checkout, unmanifested native binary, bundled statement-profile v1-v3 binary/key pair, attached xdist certificate, legacy issuer fallback, missing controller context, or structural-only verifier result can authorize publication or a warm skip; current-v4 readiness requires both a reviewed native release manifest binding the exact executable digest, locked source identity and artifact-free v4 capability payload and a separate hardcoded-review-authorized operator key manifest binding exact proving/verifying-key byte digests, provider, circuit, statement profile and release identity; manifest schema/version and every bound digest are inspected locally, and publication is denied unless a provenance-ready binding and cryptographic verifier can consume controller-owned inputs; absent source discovery, binary, capabilities, key files, either manifest, Cargo/compiler/network/cache, publication transaction, issuer, verifier, complete V2 context, or any stale/substituted/mismatched input returns RUN/DEFERRED or retains a non-authoritative receipt without losing the original pass, blocking the supervisor, generating trusted setup/keys, or writing a candidate; reporting distinguishes package availability, native installation, native v4 readiness and authoritative certificate readiness, includes the effective automatic-build/install policy and precise typed gap, and never claims readiness from source symbols alone; lazy pip uses an isolated interpreter invocation with a sanitized bounded environment and allowlisted requirement rather than inheriting repository import paths or installer-control variables; and the focused zero-configuration tests prove that individual tests still pick up the normal package-level injection while missing capabilities execute normally.

## PTR-153 Preserve proof-bearing issuance material across the lazy real issuer

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: proof-material-retention
- Depends on: PTR-152
- Goal id: PTR-G050
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py, external/ipfs_accelerate/test/api/test_proof_reuse_issued_material_retention.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_test_certificate_provider.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider external/ipfs_accelerate/test/api/test_proof_reuse_issued_material_retention.py external/ipfs_accelerate/test/api/test_proof_reuse_default_runtime_services.py external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_test_certificate_provider.py
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/proof-material-retention
- Parallel lane: ptr-proof-material-retention
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py, external/ipfs_accelerate/test/api/test_proof_reuse_issued_material_retention.py, external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_test_certificate_provider.py
- Predicted symbols: ProofBearingIssuanceMaterial, LazyRealTestCertificateIssuer.issue_material
- Interfaces: IssuedTestCertificateMaterial, LazyRealTestCertificateIssuer@1, TestExecutionCertificateV2
- Submodules: external/ipfs_accelerate
- Generated artifacts: bounded in-memory public proof/certificate material and typed deferred dispositions; no witness, trusted setup or persisted keys
- Conflict policy: Preserve only public proof-bearing issuer output behind a typed interface; never serialize private witness material, log proof bytes, trust certificate self-claims, or change controller publication authority.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: codex-implement
- Context budget tokens: 14336
- Preconditions: PTR-152 rejects every publication lacking provenance-ready bindings and cryptographic verification.
- Effects: Binds actual native prove/verify and key consumption to the exact reviewed bytes at the moment of use, then separates the public proof-bearing material returned by that issuer from its lightweight disposition so controller code can reverify the real proof without importing datasets internals eagerly.
- Evidence subset: Issued/deferred/rejected provider results, prove/verify executable and key substitution races, immutable descriptor or FD-bound execution, proof and certificate byte bounds, witness redaction, exception paths, lazy import/provisioning behavior and material lifetime
- Acceptance: Actual prove and verify never execute a mutable path merely because an earlier capability probe hashed it: the provider uses an immutable private snapshot/FD-bound executable and exact key bytes or revalidates identity atomically at each use, launches with a strict allowlisted child environment that excludes loader/interpreter injection such as LD_PRELOAD and DYLD variables, overwrites rather than inherits the pinned artifacts root, and every post-binding binary/key replacement, alternate ambient artifacts root, or environment injection defers without executing the substituted input; a successful exact v4 issuance returns one typed public material object containing the complete certificate/proof needed for local verification plus its reviewed artifact bindings, while deferred/rejected/unavailable results contain no authority; no private witness or secret key bytes cross the interface or enter logs/receipts; malformed, oversized, provenance-mismatched or structurally incomplete provider output is rejected; cold import and test collection remain installer/network/build free; and all failures retain the original pass and produce typed RUN/DEFERRED behavior.

## PTR-154 Preserve bounded controller-owned candidate context through xdist

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: controller-verification-context
- Depends on: PTR-152
- Goal id: PTR-G060
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/candidate_publication.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_candidate_publication_context.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider external/ipfs_accelerate/test/api/test_proof_reuse_candidate_publication_context.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py external/ipfs_accelerate/test/api/test_proof_reuse_receipt.py
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/controller-verification-context
- Parallel lane: ptr-controller-verification-context
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/candidate_publication.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_candidate_publication_context.py, external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py
- Predicted symbols: ControllerOwnedV2VerificationContext, CandidatePublicationEnvelope retained components, bounded xdist context handoff
- Interfaces: CandidatePublicationEnvelope@1, DeferredTestCertificateRequest, TestPassReceipt@1, TestExecutionKey@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: bounded public receipt/candidate CAS components and CID-bound xdist handoff records; no proof authority or private witness
- Conflict policy: Workers may propose bounded public bytes and CIDs only; the controller reconstructs and rehashes all context, locator/index data remains non-authoritative, and missing/oversized/malformed context is retained only as a receipt or discarded.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: grok-implement
- Context budget tokens: 14336
- Preconditions: PTR-152 routes every serial and xdist publication through one fail-closed controller transaction and forbids direct candidate-store writes.
- Effects: Retains or retrieves the canonical public receipt, candidate context and V2 request pins required for controller-side reconstruction instead of reducing the handoff to receipt IDs or trusting fields copied from an attached certificate.
- Evidence subset: Serial and xdist intent codecs, canonical component CIDs, per-field and aggregate byte bounds, mutation/substitution, duplicate/reordered delivery, worker crash, transaction unavailability and receipt-only fallback
- Acceptance: The controller can reconstruct exact receipt/execution/candidate/policy/statement/circuit/key/issuer/epoch/backend pins from bounded controller-owned or CID-rehashed public bytes; xdist transport never silently truncates a required field, and all transported bytes are size-limited and rehashed before use; certificate fields cannot fill or override missing expected values; direct put_candidate and legacy issuer fallbacks remain unreachable; missing, malformed, oversized, stale or substituted context produces receipt-only RUN/DEFERRED behavior with no candidate publication; and serial/direct-node behavior uses the same context contract without a test-file registry.

## PTR-155 Join exact Groth16 v4 verification and atomic candidate publication

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: exact-v4-controller-publication
- Depends on: PTR-153, PTR-154
- Goal id: PTR-G100
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py, external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py, external/ipfs_accelerate/test/api/test_proof_reuse_v4_publication_integration.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -q -p no:cacheprovider external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py external/ipfs_accelerate/test/api/test_proof_reuse_v4_publication_integration.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/exact-v4-controller-publication
- Parallel lane: ptr-exact-v4-controller-publication
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py, external/ipfs_accelerate/test/api/test_proof_reuse_controller_issuance.py, external/ipfs_accelerate/test/api/test_proof_reuse_v4_publication_integration.py
- Predicted symbols: ControllerV2VerificationContext, verify_test_execution_certificate_v2 publication adapter, atomic verified candidate transaction
- Interfaces: IssuedTestCertificateMaterial, TestPassCircuitBinding, CertificateVerificationStatus.VERIFIED, TestCertificateStore.put_candidate
- Submodules: external/ipfs_accelerate
- Generated artifacts: disposable test-only v4 proof/certificate/key fixtures and atomic candidate receipts under temporary roots; no production key or trusted-setup artifact is committed
- Conflict policy: Build expected public inputs exclusively from controller-owned PTR-154 context, consume PTR-153 public proof material, use only exact provenance-validated datasets modules/backend/artifact roots, and keep deterministic test-only setup explicitly non-production.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: codex-implement
- Context budget tokens: 16384
- Preconditions: PTR-153 preserves complete bounded public issuance material and PTR-154 preserves complete bounded controller-owned expected context without granting either branch publication authority.
- Effects: Reconstructs the exact datasets DeferredTestCertificateRequest and TestPassCircuitBinding, invokes verify_test_execution_certificate_v2 with the pinned backend and expected candidate-context CID, and performs the sole atomic put_candidate only after VERIFIED.
- Evidence subset: Exact PTR-151 source/module provenance, release/key manifests, controller expected inputs, genuine native proof, local V2 verifier status, artifact substitution, proof tampering, context mutation, atomic store ordering and deterministic test-only versus production authority labels
- Acceptance: One disposable explicitly test-only current-v4 fixture proves the complete issue-material to controller-context to local-V2-verify to atomic-publication path and is never counted as reviewed production authority; production publication requires the hardcoded-reviewed key-manifest allowlist, exact PTR-151 source/binary/capability/artifact bindings, immutable/FD-bound actual prove and verify inputs, and CertificateVerificationStatus.VERIFIED from verify_test_execution_certificate_v2 with the expected candidate-context CID; no structural boolean, injected verifier, certificate self-claim, alternate module/provider, stale or swapped binary/key artifact, changed context or missing proof can reach put_candidate; put_candidate occurs exactly once and only after verification, while all failures retain non-authoritative receipts and run future tests; and no trusted setup, key generation, build, download or network call occurs during import, collection, ordinary setup, or verification.

## PTR-160 Authenticate pass receipts with a content-addressed runner attestation

- Status: completed
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: authenticated-pass-receipt
- Depends on: PTR-149
- Goal id: PTR-G120
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runner_pass_attestation.py, external/ipfs_accelerate/test/api/test_proof_reuse_runner_pass_attestation.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_ZK_THREAT_MODEL.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_runner_pass_attestation.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_contracts.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_reuse_doctrine.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/authenticated-receipt
- Parallel lane: ptr-accelerator-authenticated-receipt
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runner_pass_attestation.py, external/ipfs_accelerate/test/api/test_proof_reuse_runner_pass_attestation.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_ZK_THREAT_MODEL.md
- Predicted symbols: RunnerPassAttestation, RunnerTrustPolicy, SignedTestPassReceiptV2
- Interfaces: RunnerPassAttestation@1, RunnerTrustPolicy@1, SignedTestPassReceiptV2
- Submodules: external/ipfs_accelerate
- Generated artifacts: deterministic test signing, rotation and revocation vectors only
- Conflict policy: Extend the existing accelerator trust root; cache and prover code never own signing authority.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: Historical PTR-149 evidence is available as non-authoritative provenance.
- Effects: Binds a complete pass receipt to a canonical runner signature and public-key CID before proof generation.
- Evidence subset: TestPassReceipt, setup/call/teardown phase roots, Ed25519 public-key multicodec bytes, strict DAG-CBOR, nonce, epoch, rotation and revocation
- Acceptance: The sole v1 suite is Ed25519 over `b"ipfs-test-pass-attestation/v1\0" + sha256(unsigned_attestation_dag_cbor_bytes)`; the unsigned envelope has one strict canonical DAG-CBOR encoding and its CID is CIDv1/dag-cbor/sha2-256; signer material is `varint(ed25519-pub) || 32-byte-public-key` and its identifier is the lower-base32 CIDv1/raw/sha2-256 of those exact bytes; trust starts only from an explicitly local-pinned CIDv1/dag-cbor/sha2-256 `RunnerTrustPolicy@1`, never TOFU, cache presence or certificate-selected keys; policy enforces pytest-pass-only key usage, trust domain, key epoch, not-before/not-after, rotation and revocation before proof verification. Canonical signing bytes bind receipt, execution/context, phase, trace and policy CIDs plus a unique issuance nonce and epoch. Re-reading the same immutable certificate is legitimate warm reuse while its exact execution/context/policy/epoch remain current; cross-context, cross-policy, revoked/expired-epoch, substituted-attestation or nonce-reissued certificates are prohibited replay, and the nonce is never consumed merely by a valid cache read. Unsigned, altered, replayed, expired, revoked or wrong-key receipts are non-authoritative and run; proving-key possession alone cannot fabricate pass authority; no witness, private key or secret enters public cache artifacts.

## PTR-161 Install a safe datasets-owned pytest bootstrap

- Status: completed
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: datasets-bootstrap-recovery
- Depends on: PTR-149, PTR-170
- Goal id: PTR-G130
- Outputs: external/ipfs_datasets/conftest.py, external/ipfs_datasets/tests/conftest.py, external/ipfs_datasets/ipfs_datasets_py/__init__.py, external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/requirements.txt, external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py, external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py, external/ipfs_datasets/tests/unit/test_proof_reuse_zero_config.py, external/ipfs_datasets/tests/unit/test_proof_reuse_optional_plugin_startup.py, external/ipfs_datasets/tests/unit/test_proof_reuse_isolated_bootstrap_subprocess.py, external/ipfs_datasets/tests/unit/test_setup_side_effect_defaults.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py external/ipfs_datasets/tests/unit/test_proof_reuse_zero_config.py external/ipfs_datasets/tests/unit/test_proof_reuse_optional_plugin_startup.py external/ipfs_datasets/tests/unit/test_proof_reuse_isolated_bootstrap_subprocess.py external/ipfs_datasets/tests/unit/test_setup_side_effect_defaults.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/datasets-bootstrap-recovery
- Parallel lane: ptr-datasets-safe-bootstrap
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/conftest.py, external/ipfs_datasets/tests/conftest.py, external/ipfs_datasets/ipfs_datasets_py/__init__.py, external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/requirements.txt, external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py, external/ipfs_datasets/tests/unit/test_pytest_proof_reuse_shim.py, external/ipfs_datasets/tests/unit/test_proof_reuse_zero_config.py, external/ipfs_datasets/tests/unit/test_proof_reuse_optional_plugin_startup.py, external/ipfs_datasets/tests/unit/test_proof_reuse_isolated_bootstrap_subprocess.py, external/ipfs_datasets/tests/unit/test_setup_side_effect_defaults.py
- Predicted symbols: DatasetsProofReuseBootstrapV3, datasets-owned cold pytest11 bridge, repaired collection hooks, isolated namespace/gitlink subprocess bootstrap matrix
- Interfaces: PytestProofReusePlugin@1, DatasetsProofReuseBootstrap@3
- Submodules: external/ipfs_datasets
- Generated artifacts: isolated wheel/source-checkout and empty namespace/gitlink subprocess startup fixtures
- Conflict policy: Own datasets bootstrap and packaging only; legacy commit metadata remains display information and never skip authority.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: Reachable datasets base tree is clean; its current default dependency metadata still makes accelerator effectively mandatory, so this task must make proof integration optional rather than assuming it already is.
- Effects: Restores missing datasets bootstrap outputs, repairs the accidentally nested collection hook without eager proof imports, and distinguishes a namespace-only uninitialized accelerator gitlink from a found regular accelerator package.
- Evidence subset: DatasetsProofReuseBootstrap@3 isolated installed pytest11 and source direct-node subprocesses, empty namespace/gitlink import roots, root/tests conftests, packaging parity, absent optional accelerator, transitive import failure visibility, setup/import side effects; no V2 bootstrap receipt satisfies this task
- Acceptance: Isolated installed and source-checkout subprocesses run an ordinary direct node without `-p` or test edits, discover exactly one `ipfs-datasets-proof-reuse = ipfs_datasets_py.pytest_proof_reuse` bridge, execute its body once and pass. The same subprocess matrix places a namespace-only empty `ipfs_accelerate_py/` hierarchy representing an uninitialized or empty nested gitlink ahead of imports; importing the datasets bridge and starting pytest remain a safe inert no-op instead of raising `ModuleNotFoundError(name='ipfs_accelerate_py.testing')`. Source fallback uses conditional module-level `pytest_plugins`, never `pytest_load_initial_conftests`; accelerator is optional in wheel, setup, requirements and pyproject metadata; root conftest never auto-installs pytest dependencies; the collection hook is module-scoped. Absence is suppressed only for the exact optional accelerator module chain when no regular accelerator package/plugin is present; an incomplete regular package or a transitive dependency failure from a found plugin remains visible. Importing the parent package or bridge performs no install, build, download or network action; commit hashes alone never skip.

## PTR-162 Install a safe kit-owned bootstrap and recover canonical artifact transport

- Status: completed
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: kit-bootstrap-transport-recovery
- Depends on: PTR-149, PTR-170
- Goal id: PTR-G130
- Outputs: external/ipfs_kit/conftest.py, external/ipfs_kit/ipfs_kit_py/__init__.py, external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py, external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py, external/ipfs_kit/ipfs_kit_py/test_reuse_capabilities.py, external/ipfs_kit/ipfs_kit_py/content_addressed_artifact_store.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/requirements.txt, external/ipfs_kit/tests/test_proof_reuse_bootstrap.py, external/ipfs_kit/tests/test_pytest_proof_reuse_shim.py, external/ipfs_kit/tests/test_proof_reuse_zero_config.py, external/ipfs_kit/tests/test_proof_reuse_optional_plugin_startup.py, external/ipfs_kit/tests/test_proof_reuse_isolated_bootstrap_subprocess.py, external/ipfs_kit/tests/test_proof_certificate_store.py, external/ipfs_kit/tests/test_reuse_capabilities.py, external/ipfs_kit/tests/test_content_addressed_artifact_store.py, external/ipfs_kit/tests/test_candidate_context_artifact_store.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_kit/tests/test_proof_reuse_bootstrap.py external/ipfs_kit/tests/test_pytest_proof_reuse_shim.py external/ipfs_kit/tests/test_proof_reuse_zero_config.py external/ipfs_kit/tests/test_proof_reuse_optional_plugin_startup.py external/ipfs_kit/tests/test_proof_reuse_isolated_bootstrap_subprocess.py external/ipfs_kit/tests/test_proof_certificate_store.py external/ipfs_kit/tests/test_reuse_capabilities.py external/ipfs_kit/tests/test_content_addressed_artifact_store.py external/ipfs_kit/tests/test_candidate_context_artifact_store.py -q && IPFS_TEST_PROOF_REUSE_MODE=off /usr/bin/python3 -I -c "import functools,sys,tempfile; sys.path.insert(0,'external/ipfs_kit'); from ipfs_kit_py.content_addressed_artifact_store import ContentAddressedArtifactStore,validate_dag_json_cid; from ipfs_kit_py.proof_certificate_store import ProofCertificateStore; bad='b'+'a'*9+chr(0xD800); assert validate_dag_json_cid(bad) is False; root=tempfile.mkdtemp(prefix='ptr162-validation-'); store=ContentAddressedArtifactStore(root+'/cas'); assert store.get_bytes(bad).found is False; assert store.put_bytes(b'{}',claimed_cid=bad).accepted is False; certs=ProofCertificateStore(root+'/certs'); assert certs.put_candidate('bad-cid',certificate_cid=bad).found is False; deep=functools.reduce(lambda value,_:[value],range(1100),0); assert certs.put_candidate('deep-put',context=deep).found is False; import ipfs_kit_py.pytest_proof_reuse as bridge; bridge._accelerator_is_absent_namespace=lambda: True; bridge._accelerator_plugin_is_undiscoverable=lambda: True; bridge.importlib.import_module=lambda _:(_ for _ in ()).throw(ModuleNotFoundError('missing requests',name='requests')); exec('try:\n bridge._optional_accelerator_plugin()\nexcept ModuleNotFoundError as error:\n assert error.name == \'requests\'\nelse:\n raise AssertionError(\'transitive failure was suppressed\')')"
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/kit-bootstrap-transport-recovery
- Parallel lane: ptr-kit-safe-bootstrap
- Resource class: io-artifact
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_kit/conftest.py, external/ipfs_kit/ipfs_kit_py/__init__.py, external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py, external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py, external/ipfs_kit/ipfs_kit_py/test_reuse_capabilities.py, external/ipfs_kit/ipfs_kit_py/content_addressed_artifact_store.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/requirements.txt, external/ipfs_kit/tests/test_proof_reuse_bootstrap.py, external/ipfs_kit/tests/test_pytest_proof_reuse_shim.py, external/ipfs_kit/tests/test_proof_reuse_zero_config.py, external/ipfs_kit/tests/test_proof_reuse_optional_plugin_startup.py, external/ipfs_kit/tests/test_proof_reuse_isolated_bootstrap_subprocess.py, external/ipfs_kit/tests/test_proof_certificate_store.py, external/ipfs_kit/tests/test_reuse_capabilities.py, external/ipfs_kit/tests/test_content_addressed_artifact_store.py, external/ipfs_kit/tests/test_candidate_context_artifact_store.py
- Predicted symbols: KitProofReuseBootstrapV3, KitContentAddressedArtifactStore, KitTestReuseCapabilities, isolated namespace-versus-regular-package subprocess import matrix
- Interfaces: KitProofReuseBootstrap@3, CanonicalArtifactStoreTransport@2, TestReuseCapabilityReport@2
- Submodules: external/ipfs_kit
- Generated artifacts: isolated wheel/source-checkout startup, namespace-versus-regular-package subprocess, local CAS and hostile CID fixtures
- Conflict policy: Kit owns only lazy bootstrap, byte transport and capability facts; accelerator remains sole proof authority.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: Reachable kit base tree is clean and shared plugin/storage are optional.
- Effects: Restores all missing kit proof outputs on a reachable tree, replaces unsafe direct optional plugin loading, and distinguishes namespace-only optional absence from an incomplete regular accelerator installation.
- Evidence subset: KitProofReuseBootstrap@3 missing historical kit outputs, installed/source pytest discovery, isolated namespace-versus-regular-package subprocess imports, multiformats, atomic local storage, daemon/user-directory isolation; no V2 bootstrap receipt satisfies this task
- Missing evidence: Attempt 1 (`b99e98ad2512d06387cdfc35419671a63a272314`, 30 tests) omitted the sealed recursive-input contract and still raised `RecursionError` on an under-limit deep array. Attempt 2 (`750d19df92bbbd099588c70edb7cf2329ee0333e`, 31 tests) added the depth repair but still lets a length-valid lone-surrogate CID raise `UnicodeEncodeError`, omits a checked-in deep `put_candidate` assertion, and suppresses a non-accelerator transitive `ModuleNotFoundError(name='requests')` when validation has no ambient accelerator package. Both completion receipts are contradictory evidence and cannot satisfy this reopened identity.
- Acceptance: Isolated installed and source-checkout subprocesses run an ordinary direct node without `-p` or test edits and load exactly one `ipfs-kit-proof-reuse = ipfs_kit_py.pytest_proof_reuse` bridge. In the first required import case, a namespace-only empty `ipfs_accelerate_py/` hierarchy representing an absent or uninitialized nested gitlink is a safe inert no-op and pytest still executes the real body. In the second case, an installed-style regular `ipfs_accelerate_py/__init__.py` exists but its `testing` or proof-plugin hierarchy is missing; importing the kit bridge must leave `ModuleNotFoundError(name='ipfs_accelerate_py.testing')` visible rather than suppressing it as optional absence. A transitive dependency error from a found accelerator plugin is likewise visible, including an absent-root invocation whose import error names `requests` or any other module outside the exact optional accelerator chain. Namespace absence is suppressible only when the complete accelerator plugin target is undiscoverable and the raised missing name belongs to the optional accelerator chain: a plugin found beneath PEP 420 namespace parents that raises a chain-named `ModuleNotFoundError` remains an actionable visible failure. Root source fallback uses conditional module-level `pytest_plugins`, never `pytest_load_initial_conftests`; setup, requirements and pyproject agree on optional accelerator and strict multiformats bounds; exact canonical bytes round-trip under CIDv1/base32/dag-json/sha2-256. Corrupt, oversized, recursive, malformed or path-escaping blobs and candidate-index records are handled totally and quarantine safely; every blob, quarantine and candidate-index root plus deterministic temporary/index entry is protected against symlink substitution without following or writing outside the trusted root, and candidate reads are byte-, shape-, depth- and CID-bounded. The checked-in validation suite must force the pure-Python JSON encoder and exercise an under-byte-limit array deeper than 1,000 levels; `canonical_dag_json_bytes`, `is_canonical_dag_json`, CID derivation, blob put/get and candidate-index put/get must return bounded typed failure without any `RecursionError`, and a deep corrupt on-disk blob must quarantine inside the anchored trusted root. It must also call deep `put_candidate`, reject a length-valid lone-surrogate CID through direct validation, blob get/claimed put and candidate put without `UnicodeEncodeError`, and exercise the non-accelerator transitive failure with accelerator imports absent. The declared inline isolated counterexample is mandatory validation evidence, not an optional diagnostic. Importing package or bridge never resolves installers, calls `ensure_kubo_binary`, starts a daemon, initializes a repository, touches user state or uses the network even when install environment flags are set; transport never becomes proof authority.

## PTR-163 Bind a real TestPassStatementV5 provider to the runner attestation

- Status: todo
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: authenticated-real-zk
- Depends on: PTR-160, PTR-161
- Goal id: PTR-G120
- Outputs: external/ipfs_datasets/MANIFEST.in, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/ipfs_datasets_py.egg-info/SOURCES.txt, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/provekit/test_pass_circuit.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_execution_certificate.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_assurance.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_pass_groth16_provider.py, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.toml, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.lock, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.sh, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/RUST_SETUP.md, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/WIRE_FORMAT.md, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/circuit.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/domain.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/lib.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/main.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/prover.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/setup.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/verifier.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/schemas/witness_v1.schema.json, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/schemas/proof_v1.schema.json, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/groth16, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/release-manifest.json, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_cid_profile.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_assurance.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py, external/ipfs_datasets/tests/unit/logic/zkp/test_deferred_test_certificate_request.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_groth16_provider.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_v5_authority.py, external/ipfs_datasets/tests/unit_tests/logic/zkp/groth16_wire_vectors.json, external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_wire_schemas.py, external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_wire_vectors.py, external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_native_release.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off cargo test --locked --manifest-path external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.toml && IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_cid_profile.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_assurance.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py external/ipfs_datasets/tests/unit/logic/zkp/test_deferred_test_certificate_request.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_groth16_provider.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_v5_authority.py external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_wire_schemas.py external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_wire_vectors.py external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_native_release.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/authenticated-real-zk
- Parallel lane: ptr-datasets-statement-v5
- Resource class: zk-native
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets/MANIFEST.in, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/ipfs_datasets_py.egg-info/SOURCES.txt, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/provekit/test_pass_circuit.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_execution_certificate.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_assurance.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_pass_groth16_provider.py, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.toml, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/Cargo.lock, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/build.sh, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/RUST_SETUP.md, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/WIRE_FORMAT.md, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/circuit.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/domain.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/lib.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/main.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/prover.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/setup.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/src/verifier.rs, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/schemas/witness_v1.schema.json, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/schemas/proof_v1.schema.json, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/groth16, external/ipfs_datasets/ipfs_datasets_py/processors/groth16_backend/bin/linux-aarch64/release-manifest.json, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_cid_profile.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_assurance.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py, external/ipfs_datasets/tests/unit/logic/zkp/test_deferred_test_certificate_request.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_groth16_provider.py, external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_v5_authority.py, external/ipfs_datasets/tests/unit_tests/logic/zkp/groth16_wire_vectors.json, external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_wire_schemas.py, external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_wire_vectors.py, external/ipfs_datasets/tests/unit_tests/logic/zkp/test_groth16_native_release.py
- Predicted symbols: TestPassStatementV5, AuthenticatedTestCertificateIssuer, signed-attestation Groth16 public inputs
- Interfaces: TestPassStatementV5, TestCertificateIssuerFactory@2, TestCertificateAssurance@2
- Submodules: external/ipfs_datasets
- Generated artifacts: deterministic conformance vectors and reviewed build manifests; no production keys or trusted setup
- Conflict policy: Recover the missing datasets outputs on one reachable commit and reject all legacy authority upgrades.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-160 attestation schema and PTR-161 cold-safe datasets packaging pass.
- Effects: Restores real deferred issuance/local verification and binds proof public inputs to the immutable signed attestation and canonical CID profile.
- Evidence subset: missing historical datasets outputs, Groth16 V5 setup/prove/verify/capability routing, runner key/trust policy CIDs, package-data and native release provenance
- Missing evidence: The preserved pre-revision candidate (`21282cb8779330724e496f88acdf3ed02cccbca1`, datasets `a166f12cd5823416d31a2ebc0f5090ba245b73d5`) is contradictory provenance only. It invents a JSON `RunnerAttestation@2` instead of consuming PTR-160's canonical DAG-CBOR `RunnerPassAttestation@1` and locally pinned `RunnerTrustPolicy@1`; accepts callback booleans and arbitrary verifier objects as authority; leaves V1/hash-only certificates able to skip; proves duplicated caller-supplied commitments rather than an opening of the exact receipt bytes; and does not bind the staged binary, circuit or verifying-key bytes to their claimed CIDs. The interrupted first attempt of the next revision remained contradictory: it required the honest PTR-160 `TestPassReceipt@1` bytes/CID to use DAG-CBOR even though that canonical contract is DAG-JSON; its Rust relation accepted seven arbitrary 32-byte openings and reduced each 256-bit digest to one field element instead of hashing the bounded exact receipt/attestation bytes; its native provider did not compare proof public inputs to the requested statement; the legacy verifier could still authorize a V1 skip; and its release manifest used placeholder source/toolchain claims plus a key path different from the runtime verifier. Neither candidate can satisfy this revised identity or seed authoritative reuse.
- Acceptance: TestPassStatementV5 binds exact attestation, canonical receipt bytes, execution, runner-key, trust-policy, circuit and verifier-key CIDs. PTR-160's honest `TestPassReceipt@1` is decoded and re-encoded as its exact canonical DAG-JSON bytes and identified by CIDv1/dag-json/sha2-256; the sole runner suite and policy remain canonical DAG-CBOR `RunnerPassAttestation@1` and `RunnerTrustPolicy@1` with CIDv1/dag-cbor/sha2-256. The attestation is signed with domain-separated Ed25519 and evaluated against an explicitly local-pinned policy for key usage, domain, epoch, validity, rotation and revocation before ZK verification; no alternate JSON attestation, TOFU key or certificate-selected policy is accepted. The native V5 witness contains the bounded exact receipt and attestation bytes plus explicit lengths/padding, and its constraints hash those bytes in-circuit to the full public SHA-256 multihash digests; each full digest is represented collision-free as constrained bytes or two range-constrained 128-bit limbs, never one field element reduced modulo Fr and never an arbitrary 32-byte label. The typed host boundary canonical-decodes the exact opened bytes, derives the receipt and attestation CIDs, binds their decoded execution/policy/key/pass/nonce/epoch fields to every remaining public input, and compares the complete proof public-input vector to the requested statement before native verification. Only that locally verified composition and the pinned native Groth16 backend may reach VERIFIED; lambdas, booleans, generic callable verifier objects, arbitrary proof bytes and provider self-claims remain non-authoritative. V1-V4 remain readable compatibility formats, but every public verifier entry point sets `can_authorize_skip=false` and RUN for V1-V4/hash-only/simulated openings. Cargo setup, prove, verify and capability paths route V5 through one exact circuit/public-input profile; the runtime uses one immutable reviewed artifact root and rehashes the actual executable, circuit, proving/verifying keys and complete source/build inputs against a truthful release manifest whose architecture, source revision and locked toolchain match the bytes actually used. The mandatory `test_test_pass_v5_authority.py` constructs a real PTR-160 `TestPassReceipt@1`, `RunnerPassAttestation@1` and pinned policy, proves their codec/CID split, and shows the exact typed V5 composition succeeds while receipt/attestation byte mutation, receipt field mismatch, public-input substitution, single-field digest alias/reduction, wrong/revoked/stale policy or key, every public CID mutation, a benign injected `True` backend and the legacy downgrade all fail before candidate authority; Rust tests prove that no arbitrary 32-byte label or statement-A proof verifies as statement B. Missing or mismatched binary/key/circuit/compiler yields DEFERRED/RUN, and no trusted setup, build, download or network action occurs automatically.

## PTR-164 Enforce signed-receipt trust in lookup and controller publication

- Status: todo
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: authenticated-runtime-composition
- Depends on: PTR-160, PTR-163
- Goal id: PTR-G130
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lookup.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_locator_only_warm_path.py, external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_publication.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_locator_only_warm_path.py external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_publication.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/authenticated-runtime
- Parallel lane: ptr-accelerator-authenticated-runtime
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lookup.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py, external/ipfs_accelerate/test/api/test_proof_reuse_locator_only_warm_path.py, external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_publication.py
- Predicted symbols: locator-only warm pipeline, SignedReceiptTrustVerifier, controller-only candidate publication
- Interfaces: TwoStageCandidateLookup@2, SignedTestPassReceiptV2, ControllerCandidatePublisher@2
- Submodules: external/ipfs_accelerate
- Generated artifacts: hermetic locator, signature, key-epoch and xdist fixtures
- Conflict policy: Controller alone signs and publishes; workers send bounded public envelopes and never keys or witnesses.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: Runner attestation contracts and the exact merged TestPassStatementV5 provider, binary capabilities and release manifest from PTR-163 exist; historical injected-item fixtures remain non-authoritative.
- Effects: Makes ordinary locator-seeded items reach two-stage lookup and revalidates signature/trust before local proof verification and atomic publication.
- Evidence subset: collection seed, current context, runtime trace, signature/key epoch/revocation, receipt lifecycle, xdist fencing
- Acceptance: An unmodified item reaches lookup before setup; current AST/fixture/hook/config/dependency/environment/policy context is rebuilt; terminal setup/call/teardown pass is controller-signed; each warm lookup checks immutable bytes, signature, key validity, revocation, epoch and policy before proof verification; any gap runs; workers cannot publish or leak private material; partial/racing writes never authorize reuse.

## PTR-165 Validate completed-task artifacts, exact pins, and replay evidence

- Status: todo
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: task-evidence-integrity
- Depends on: PTR-161, PTR-162
- Goal id: PTR-G140
- Outputs: scripts/proof_backed_test_reuse_task_evidence.py, tests/test_proof_backed_test_reuse_task_evidence.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_proof_backed_test_reuse_task_evidence.py -q && IPFS_TEST_PROOF_REUSE_MODE=off python3 scripts/proof_backed_test_reuse_task_evidence.py --todo implementation_plan/docs/46-proof-backed-test-reuse.todo.md --expect-incomplete
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/task-evidence-integrity
- Parallel lane: ptr-outer-task-evidence
- Resource class: security-review
- Implementation timeout seconds: 7200
- Predicted files: scripts/proof_backed_test_reuse_task_evidence.py, tests/test_proof_backed_test_reuse_task_evidence.py
- Predicted symbols: ProofReuseTaskEvidenceValidator, CompletedTaskArtifactReceipt
- Interfaces: CompletedTaskArtifactReceipt@1, ExactGitlinkEvidence@1
- Submodules:
- Generated artifacts: canonical CID-addressed evidence inventory under configured state roots
- Conflict policy: Add an unprotected evidence validator; do not let workers edit the board, scheduler profile, controller or operator approvals.
- Symbolic first: true
- LLM context budget bytes: 49152
- Provider role: grok-implement
- Context budget tokens: 12288
- Preconditions: Reachable datasets/kit repair tasks define the exact expected recovered surfaces.
- Effects: Builds the independent live-tree audit tool and emits a canonical non-ready gap report for the deliberately incomplete Wave-B tree; it never treats its own successful audit execution as proof that historical work is ready.
- Evidence subset: task outputs, validation targets/command CID, gitlinks, blob digests, merge receipts, commit ancestry, proof-reuse-off receipts
- Missing evidence: Merged attempt 1 (`77aea5348cd6675e628454e9975e0937323961b2`) is contradictory provenance only. Its private task-CID formula disagrees with the supervisor for every current task, blank task CIDs allow arbitrary JSON to pass as completion evidence, validation JSON is trusted without schema/content authentication, JSONL reconciliation evidence is ignored, the configured `IPFS_PROOF_REUSE_STATE_ROOT` base is not honored, and unrelated dependency edges replace explicit later-owner attribution. Its live report therefore accepted zero of 71 completion/validation receipts and emitted 292 synthetic gaps while `--expect-incomplete` still returned success. The subsequently quiesced draft on base `b0da8c875` is also non-authoritative: it scanned only v8, accepted just 3 of 70 completions and 0 of 70 validations while claiming `audit_valid=true`, invented validation schemas and a command-CID formula instead of consuming the retained supervisor contract, and accepted a fabricated one-task board plus self-authored queue/train/validation/event JSON as `ready=true` under `--require-ready`; its deterministic report CID `baguqeerar47kmz4pukq2hsfzjerdc3tkhm44aw7k62swqg6xzd4c3javw44q` records the contradiction but proves no task. Neither attempt can satisfy this revised identity.
- Acceptance: The validator calls the standalone `validate(objective, todo, config, plan)` board gate and requires schema `ipfs_accelerate_py/proof-backed-test-reuse-preflight@1`, `valid=true`, `errors=[]` and `task_count=77`; it then uses supervisor `parse_task_file(..., "## PTR-")` and requires 77 unique records in namespace `proof-backed-test-reuse-v1` with the exact parser-supplied key/CID. A smaller, altered or merely parser-compatible board is an invalid audit. Every observation joins on the exact `(task_id, canonical_task_key, canonical_task_cid)` and the validator never rederives a private task CID. It resolves the current v8 root with the controller's exact semantics—`IPFS_PROOF_REUSE_STATE_ROOT` is the complete override, otherwise XDG state plus the sealed suffix—and from that root's parent derives only the mandatory reviewed sibling `proof-backed-test-reuse-v1` and `proof-backed-test-reuse-v6` roots; missing required roots/manifests are typed audit failures, arbitrary recursive roots are forbidden, and sources are restricted to named completed queue records, matching train receipts, retained validation receipts and manifest/hash-chain-verified JSONL reconciliation events. Raw completed queue rows are authority only by exact allowlisted location and shape: their nested `metadata.schema=ipfs_accelerate_py/agent-supervisor/merge-candidate@3` is validated, but no nonexistent outer schema or content CID is invented. Canonical `project_managed_merge_queue_record` is reused only for its sealed projection, never as authentication. Each raw row must join its train receipt by equal `request_id` and by `dedupe_key` equal to the train filename stem; the queue canonical CID/key and train canonical key must bind the exact task triple. The train status is `merged` or `already_merged`, `integrated=true`, `merge_result.merged=true`, return code zero and `integration_commit_proof.passed=true`, with applicable already-merged proof and an integration commit that is an ancestor of the current target. Recovery-only records without request/dedupe/train binding, including PTR-150/PTR-151/PTR-152, remain typed provenance gaps. Reconciliation authority is restricted to each reviewed root's `state/ptr_lane_{0,1,2}/ptr_lane_*_events.jsonl` and adjacent `ipfs_accelerate_py.agent_supervisor.event-log-manifest@2`, never supervisor/preflight logs or a reader that repairs the evidence while observing it. The validator rederives the manifest digest, validates the named segment population, size/count and digest when sealed, stream/snapshot identity, contiguous sequence, `previous_event_id` chain and every canonical event ID. Only a `merge_reconciled` event with `resolved=true`, reason `implementation_branch_already_merged`, exact completion-task CIDs, passed integration and declared-output proofs, durable completion persistence, ancestor integration commit and nested succeeded `ipfs_accelerate_py.agent_supervisor.member_completion_receipt@1` exact task triple is authority; earlier failed/quarantined events neither authorize nor suppress a later verified success. Historical validation is read only from `projection/completion/validation_receipts/PTR-*.json`, never `failed/` or summary/snapshot files. It accepts only the flat `ipfs_accelerate_py/proof-backed-test-reuse-executed-validation-receipt@1` body, rederives its immutable `validation_receipt_cid` from the body without the claim, and imports canonical `validation_command_identity`; its sole command projection is `{"command": command.strip()}` rather than an invented schema or digest. It requires exact task ID/CID/goal ID, command bytes and CID, proof-reuse-off executed/pass/exit-zero/zero-skip disposition, exact repository ID/state CID/commit/tree/gitlink/forest, clean/dirty-overlay binding and integer freshness; stale, missing or pin-mismatched evidence remains a typed observation gap and is never rerun, refreshed or synthesized. Arbitrary JSON, reports, failed/quarantined rows and self-authored projections are never authority. Output and validation-target facts are checked from mode-160000 gitlinks and exact nested blobs/digests with checkout equality, ancestry and typed remote-reachability gaps. Dependency-ordered later ownership comes from the validated board's sealed historical-missing-artifact quarantine: every unique missing path retains all output/validation roles and its explicit pending later owner (including PTR-163) and keeps `ready=false`; unrelated DAG edges are not ownership. The canonical report body excludes wall-clock time, absolute roots, report paths, mtimes and scan order, is byte-deterministic for identical evidence, and existing CID-named files are rehashed before reuse. CLI output distinguishes `audit_valid` from `ready`: `--expect-incomplete` succeeds only for a valid full-board audit with at least one genuine owner-attributed gap, while a missing/malformed reviewed root, board, receipt chain, manifest or scan fails closed; `--require-ready` additionally requires zero gaps. Completing PTR-165 requires copied real-format fixtures for a v8 raw/train pair, a v6 PTR-160 pair, a v1 flat validation receipt and v1 PTR-011/PTR-041 successful-plus-failed reconciliation chain/manifest. Independent negative mutations cover wrong or missing v1/v6/v8 roots; 76-, two- and one-task boards; recovery-only rows; request/dedupe/filename/task-key/task-CID mismatches; unsuccessful/quarantine coexistence; validation schema/body-CID/command/goal/task/repository-state/dirty/pin/freshness/skip; manifest digest/segment/count/sequence/previous-event/event-ID/nested-receipt tampering; self-authored projections; configured-root selection; PTR-163 later ownership and repeated deterministic report CIDs. Its live canonical report must accurately say `ready=false` with the then-current owned gaps and distinguish retained stale validations from missing ones. Only PTR-167 may require and produce a globally green report after replay. No evidence is synthesized.

## PTR-166 Prove that proving-key possession cannot fabricate a pass

- Status: todo
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: authenticated-proof-adversarial
- Depends on: PTR-163, PTR-164
- Goal id: PTR-G120
- Outputs: external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_real_backend_adversarial.py, external/ipfs_accelerate/test/api/proof_reuse_authenticated_real_backend_fixture.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_real_backend_adversarial.py -q -rsx --strict-markers
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/authenticated-proof-adversarial
- Parallel lane: ptr-authenticated-adversarial
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_real_backend_adversarial.py, external/ipfs_accelerate/test/api/proof_reuse_authenticated_real_backend_fixture.py
- Predicted symbols: authenticated real-backend forgery population
- Interfaces: AuthenticatedRealBackendConformance@1, TestPassStatementV5
- Submodules: external/ipfs_accelerate
- Generated artifacts: deterministic test-only real proof/signature/key fixtures and invalid mutations
- Conflict policy: Exercise production verification without injected acceptors or simulated certificates; never weaken checks for fixtures.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-163 real statement/provider and PTR-164 publication path pass positive conformance.
- Effects: Establishes a concrete denial boundary between valid ZK syntax and trusted pass authority.
- Evidence subset: native provider identity/capabilities, one actual ephemeral test-only setup/prove/verify, fabricated unsigned receipt, wrong signature/key/policy/attestation CID/nonce/epoch/revocation, real positive vector, pytest outcome accounting
- Acceptance: The suite asserts the manifest-pinned native provider identity and performs at least one actual ephemeral test-only setup, prove and verify through the production V5 route; the validation has zero skips, xfails or conditional backend bypasses. A genuine proof over a fabricated unsigned receipt may satisfy raw proof math but fails authority before candidate publication; one correctly signed real-backend vector succeeds; every signature, key, trust-policy, CID, nonce, epoch, revocation and downgrade mutation returns RUN; body-oracle evidence, not a skip counter, determines false admissions.

## PTR-167 Replay verified historical work onto reachable exact gitlinks

- Status: todo
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: verified-history-replay
- Depends on: PTR-165, PTR-166
- Goal id: PTR-G140
- Outputs: external/ipfs_datasets, external/ipfs_kit, scripts/proof_backed_test_reuse_replay_verified_tasks.py, tests/test_proof_backed_test_reuse_replay_verified_tasks.py, implementation_plan/docs/46-proof-backed-test-reuse-replay-map-v5.json
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest tests/test_proof_backed_test_reuse_replay_verified_tasks.py -q && IPFS_TEST_PROOF_REUSE_MODE=off python3 scripts/proof_backed_test_reuse_task_evidence.py --todo implementation_plan/docs/46-proof-backed-test-reuse.todo.md --require-ready
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/verified-history-replay
- Parallel lane: ptr-verified-history-replay
- Resource class: io-artifact
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_datasets, external/ipfs_kit, scripts/proof_backed_test_reuse_replay_verified_tasks.py, tests/test_proof_backed_test_reuse_replay_verified_tasks.py, implementation_plan/docs/46-proof-backed-test-reuse-replay-map-v5.json
- Predicted symbols: VerifiedTaskReplayPlan, ReachableGitlinkReconciler
- Interfaces: VerifiedTaskReplayPlan@1, CompletedTaskArtifactReceipt@1
- Submodules: external/ipfs_datasets, external/ipfs_kit
- Generated artifacts: static old-to-new commit/blob replay mapping without approvals
- Conflict policy: Replay only receipt-named commits/blobs and serialize all gitlink publication; never synthesize history, evidence or completion.
- Symbolic first: true
- LLM context budget bytes: 57344
- Provider role: grok-implement
- Context budget tokens: 14336
- Preconditions: PTR-165 evidence rules and PTR-166 authority tests are green; recovered repository tasks have merged.
- Effects: Reconciles historical implementation provenance with reachable repository commits and exposes every unrecoverable gap.
- Evidence subset: retained supervisor snapshots, merge receipts, expected tree/blob hashes, remote reachability, current submodule ancestry
- Acceptance: Only content matching trusted task/merge receipts is replayed; recreated tree/blob digests are checked before publication; datasets and kit are published as reachable commits and the outer gitlinks are updated to those exact commits; all three pinned commits are fetchable and exact; the live PTR-165 validator now passes across all completed tasks; any unrecoverable output reopens its owning work instead of being waived; dated 66-task artifacts remain immutable historical records.

## PTR-168 Prove genuine three-repository zero-configuration cold and warm runs

- Status: todo
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: genuine-cross-repo-e2e
- Depends on: PTR-161, PTR-162, PTR-166, PTR-167
- Goal id: PTR-G140
- Outputs: external/ipfs_accelerate/test/api/proof_reuse_genuine_e2e_fixture.py, external/ipfs_accelerate/test/api/test_proof_reuse_genuine_three_repo_e2e.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_genuine_three_repo_e2e.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/genuine-e2e-v5
- Parallel lane: ptr-genuine-three-repo-e2e
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/test/api/proof_reuse_genuine_e2e_fixture.py, external/ipfs_accelerate/test/api/test_proof_reuse_genuine_three_repo_e2e.py
- Predicted symbols: genuine installed/source three-repository proof-reuse harness
- Interfaces: PytestProofReuseE2E@2, SignedTestPassReceiptV2, TestPassStatementV5
- Submodules: external/ipfs_accelerate
- Generated artifacts: isolated wheels, state roots, body counters, test signing material and explicit real-backend artifacts
- Conflict policy: Use public package bootstraps only; proof-plugin `-p`, item/service injection, tracer monkeypatch and simulated verification are forbidden.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: Safe datasets/kit bridges, signed real provider, publication authority and verified replay are integrated on reachable pins.
- Effects: Demonstrates the requested no-test-rewrite lifecycle using independent ordinary pytest processes.
- Evidence subset: wheel/source startup, body oracle, immutable candidate bytes, signed real certificate, forced replay and dependency mutation
- Acceptance: In each repository ordinary `python -m pytest node` runs cold exactly once and reports one pass, an independent warm process locally verifies a real signed proof and reports one `proof-cache-hit` skip with body count unchanged, and forced uncached replay passes and increments once; no `-p` or monkeypatch is used; AST/fixture/conftest/dependency/parameter/environment/policy mutations execute the body; zero false skips are measured by the body oracle.

## PTR-169 Seal the exact 77-task authenticated current-tree handoff

- Status: todo
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: current-tree-closeout-v5
- Depends on: PTR-168
- Goal id: PTR-G140
- Outputs: scripts/proof_backed_test_reuse_objective_reconciliation.py, test/test_proof_backed_test_reuse_objective_reconciliation.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_current_tree_gate.py, external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_subprocess_benchmark.py, external/ipfs_accelerate/docs/guides/TEST_PROOF_REUSE_OPERATOR_HANDOFF.md
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest test/test_proof_backed_test_reuse_objective_reconciliation.py external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_current_tree_gate.py external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_subprocess_benchmark.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/current-tree-closeout-v5
- Parallel lane: ptr-current-tree-closeout-v5
- Resource class: test-large
- Implementation timeout seconds: 10800
- Predicted files: scripts/proof_backed_test_reuse_objective_reconciliation.py, test/test_proof_backed_test_reuse_objective_reconciliation.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py, external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_current_tree_gate.py, external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_subprocess_benchmark.py, external/ipfs_accelerate/docs/guides/TEST_PROOF_REUSE_OPERATOR_HANDOFF.md
- Predicted symbols: AuthenticatedProofReuseCurrentTreeGateV5, reachable-tree operator handoff
- Interfaces: AuthenticatedProofReuseCurrentTreeGateV5, ProofReuseBenchmarkReceipt@2
- Submodules: external/ipfs_accelerate
- Generated artifacts: fresh 77-task validation receipts, benchmark summary and non-authoritative operator candidate
- Conflict policy: Final join only; update the outer objective reconciler so G120/G130/G140 remain mandatory, but report gaps without editing this board, approving evidence, generating trust keys or marking goals complete.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-168 genuine e2e passes after authenticated adversarial assurance and exact reachable replay.
- Effects: Replaces the historical 66-task premise with current signed-authority, reachable-tree, ordinary-pytest and performance evidence.
- Evidence subset: exact 77-task inventory, reachable gitlinks, PTR-165 evidence, PTR-166 forgery resistance, PTR-168 cold/warm/replay, PTR-170 actionable retry evidence, zero false skips, measured savings, supervisor health
- Acceptance: All 77 tasks have current evidence and present outputs on fetchable exact pins; the reconciler refuses root completion while G120, G130 or G140 is active and requires the PTR-169 `ptr/authenticated-current-tree-gate-v5@1` artifact; every warm hit uses a trusted signed receipt and locally verified real proof; genuine three-repo e2e and forced replay agree; adversarial/mutation populations have zero false skips; benchmark meets the reviewed threshold; optional capability gaps remain truthful RUN/DEFERRED. PTR-169 may emit only a pre-merge candidate receipt for itself; authoritative completion requires the outer controller to rerun the exact 77-task gate after the PTR-169 merge commit is present and prove that commit/tree. Any 76-task, v7, PTR-149 or 66-task packet is rejected as stale.

## PTR-170 Preserve actionable validation failures in bounded retry evidence

- Status: completed
- Completion: automatic
- Is schedulable: true
- Review only: false
- Priority: P0
- Track: actionable-retry-evidence
- Depends on: PTR-149
- Goal id: PTR-G140
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_failure_review.py, external/ipfs_accelerate/test/api/test_agent_supervisor_context_delta.py, external/ipfs_accelerate/test/api/test_agent_supervisor_todo_daemon_port.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_failure_review.py external/ipfs_accelerate/test/api/test_agent_supervisor_context_delta.py external/ipfs_accelerate/test/api/test_agent_supervisor_todo_daemon_port.py -q
- Board namespace: proof-backed-test-reuse-v1
- Bundle: proof-test-reuse/actionable-retry-evidence
- Parallel lane: ptr-actionable-retry-evidence
- Resource class: security-review
- Implementation timeout seconds: 10800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_failure_review.py, external/ipfs_accelerate/test/api/test_agent_supervisor_context_delta.py, external/ipfs_accelerate/test/api/test_agent_supervisor_todo_daemon_port.py
- Proposal artifact envelope: {"max_file_bytes":2000000,"max_output_bytes":8000000,"max_patch_bytes":6000000,"paths":["external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py","external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_failure_review.py","external/ipfs_accelerate/test/api/test_agent_supervisor_context_delta.py","external/ipfs_accelerate/test/api/test_agent_supervisor_todo_daemon_port.py"],"schema":"ipfs_accelerate_py/agent-supervisor/task-artifact-envelope@1"}
- Predicted symbols: bounded implementation failure normalizer, authoritative validation retry capsule, deduplicated implementation review projection
- Interfaces: ActionableRetryEvidence@1, ImplementationDiagnosticReceipt@1, RetryContextCapsule@1
- Submodules: external/ipfs_accelerate
- Generated artifacts: deterministic oversized nested review, validation counterexample, and retry-capsule fixtures only
- Conflict policy: Own only implementation-daemon diagnostic normalization and its focused tests; do not change proof-cache authority, package bootstraps, task acceptance, provider selection, board mutation or retry budgets.
- Symbolic first: true
- LLM context budget bytes: 65536
- Provider role: grok-implement
- Context budget tokens: 16384
- Preconditions: PTR-149 historical supervisor provenance and the retained v7 PTR-162 failure-event sequence are available; implementation occurs in an isolated task worktree and accelerator gitlink publication remains serialized by the merge queue.
- Effects: Replaces recursive failure-review amplification with one deterministic bounded projection while retaining the validation counterexample that a retrying implementation agent must act on.
- Evidence subset: attempted validation command, passed=false, return code, validation reason, diagnostic receipt id, failed test/command/path, exception type and message, bounded failure head, deduplication counts, truncation hash and original-byte count
- Acceptance: For an implementation whose real subprocess validation was attempted and failed, normalization is deterministic, finite and at most 16 KiB and never raises; it preserves authoritative `attempted=true`, `passed=false`, return code and reason together with the diagnostic receipt id and the failed command, test, path, exception and bounded `failure_head`. Repeated full review/addendum bodies are deduplicated, and every omitted tail is represented by an original-byte count plus a SHA-256 truncation marker. `implementation_finished` and the next retry capsule retain the same actionable counterexample, validation remains attempted/failed rather than `not_run`, and no synthetic `implementation_setup` exception replaces the subprocess failure. Focused regressions cover oversized nested review normalization, context-delta serialization, and the daemon-port retry/event path; no validation output, private material or unbounded review text is copied into the board.
