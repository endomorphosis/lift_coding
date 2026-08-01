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

## Initial execution wave

`PTR-000` is the operator-authored planning seal. The initial claimable tasks
are exactly `PTR-001`, `PTR-002`, and `PTR-003`, mapping one task to each of the
three numeric shards. Waiting tasks are normal and become selectable only after
their declared dependencies complete.

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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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
