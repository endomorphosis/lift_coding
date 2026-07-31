# Proof-Backed Test Reuse Objective Heap (PTR)

Machine-ingestible objective state for `ipfs_accelerate_py.agent_supervisor`.
The executable board is
`implementation_plan/docs/46-proof-backed-test-reuse.todo.md` with task prefix
`## PTR-`. The reviewed architecture is
`implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md`.

## North star

Make exact, previously passing pytest executions safely reusable across
`ipfs_accelerate_py`, `ipfs_datasets_py`, and `ipfs_kit_py` through canonical
AST/runtime dependency identities, strict multiformats CIDs, trusted pass
receipts, optional real-ZK certificates, and revalidated caches. Every missing
or invalid optional capability executes the real test.

## Goal tree

```text
PTR-G000  Proof-backed cross-repository test reuse
|-- PTR-G010  Contracts, authority, and threat model
|-- PTR-G020  Canonical execution identity
|-- PTR-G030  Static/runtime traces and eligibility
|-- PTR-G040  Trust-aware cache and certificate storage
|-- PTR-G050  Datasets real-ZK pass certificates
|-- PTR-G060  Automatically discovered pytest plugin
|-- PTR-G070  Agent-supervisor completion authority
|-- PTR-G080  Datasets repository integration
|-- PTR-G090  Kit storage and repository integration
|-- PTR-G100  Degradation, mutation, security, and e2e assurance
`-- PTR-G110  Benchmark, rollout, and current-tree closeout
```

## PTR-G000 Proof-backed cross-repository test reuse

- Status: active
- Parent:
- Depends on:
- Fib priority: 1
- Priority: P0
- Track: proof-test-reuse
- Bundle: proof-test-reuse/root
- Goal: Deliver exact proof-backed pytest reuse across the three outer IPFS Python repositories without per-test hardwiring and without turning unavailable proof infrastructure into a test failure or false skip.
- Evidence: ptr/cross-repository-current-tree-gate@1, ptr/zero-false-authoritative-skip@1, ptr/warm-reuse-benchmark@1, ptr/supervisor-launch-health@1
- Outputs: implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md, implementation_plan/docs/46-proof-backed-test-reuse.objectives.md, implementation_plan/docs/46-proof-backed-test-reuse.todo.md, config/proof_backed_test_reuse_supervisor.json, scripts/validate_proof_backed_test_reuse_board.py, scripts/proof_backed_test_reuse_supervisor.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py -q
- Acceptance: Every child goal has current typed evidence; every authoritative skip binds an exact trusted pass receipt and locally verified real certificate; zero stale or false skips occur; optional dependency loss always runs tests; the warm eligible population demonstrates useful savings.
- Gap task: Execute PTR-001 through PTR-102 under the reviewed dependency graph and current-tree gate.
- Refinement: Preserve one shared policy/plugin and split identity, trace, storage, proving, repository bootstrap, adversarial, and rollout evidence into independently reviewable child goals.
- Embedding query: exact proof-backed pytest reuse AST trace CID multihash pass receipt ZK cache graceful degradation all three IPFS Python repositories
- AST query: Find pytest collection and report hooks, proof-cache authority, content-identity bridges, ZKP adapters, repository conftests, and supervisor validation gates affected by reusable pass evidence.

## PTR-G010 Contracts, authority, and threat model

- Status: active
- Parent: PTR-G000
- Depends on:
- Fib priority: 2
- Priority: P0
- Track: foundation-contracts
- Bundle: proof-test-reuse/foundation
- Goal: Define finite typed records, authority precedence, capability results, and a reviewed ZK threat model before implementation can authorize any skip.
- Evidence: ptr/test-execution-contracts@1, ptr/reuse-authority-policy@1, ptr/zk-test-receipt-threat-model@1, ptr/capability-probe@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_ZK_THREAT_MODEL.md, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/test_reuse_capabilities.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_contracts.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_reuse_doctrine.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_capabilities.py -q
- Acceptance: Contracts reject nonfinite, unbounded, private, malformed, and illegal-authority inputs; CID and AST evidence are not pass evidence; only a trusted exact receipt and admitted real certificate may skip; simulated ZK is non-authoritative; capability absence is typed and non-blocking.
- Gap task: PTR-001, PTR-002, PTR-003
- Refinement: Separate executable schemas, security doctrine, and cold lazy capability probing so the initial wave is conflict-free.
- Embedding query: TestLocatorKey TestExecutionKey TestPassReceipt TestProofCertificate authority policy real ZK simulated ZK capability unavailable
- AST query: Locate accelerator proof dataclasses, ZK authority enums, lazy integrations, finite canonicalization checks, and existing capability probe conventions.

## PTR-G020 Canonical execution identity

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G010
- Fib priority: 2
- Priority: P0
- Track: execution-identity
- Bundle: proof-test-reuse/identity
- Goal: Produce strict locator and execution CIDs that change for every admitted behavior-affecting test, source, fixture, configuration, dependency, environment, capability, and policy input.
- Evidence: ptr/test-locator-key@1, ptr/test-execution-key@1, ptr/cross-package-cid-vectors@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_execution_identity.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_identity_components.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_identity_components.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py -q
- Acceptance: CIDv1/base32/dag-json/sha2-256 identities independently reproduce across datasets and multiformats; parameters and context are canonical or non-reusable; forest, node, AST, fixtures, hooks, locks, environment, capabilities, and policy are bound; pseudo-CIDs are rejected.
- Gap task: PTR-010, PTR-011, PTR-012
- Refinement: Separate core keys, component collectors, and independent known-vector conformance.
- Embedding query: canonical pytest node identity parameter fixture conftest hook environment lock capability CIDv1 dag-json sha2-256
- AST query: Find nodeid normalization, parameter serialization, repository snapshot, content identity, installed distribution, fixture, conftest, and pytest hook sources.

## PTR-G030 Static/runtime traces and eligibility

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G010, PTR-G020
- Fib priority: 3
- Priority: P0
- Track: dependency-tracing
- Bundle: proof-test-reuse/tracing
- Goal: Combine bounded AST closure and observed runtime dependencies into explicit completeness and eligibility decisions, initially binding the full admitted repository forest.
- Evidence: ptr/static-test-dependency-trace@1, ptr/runtime-test-dependency-trace@1, ptr/reuse-eligibility-decision@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_static_dependency_trace.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_runtime_dependency_trace.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_reuse_eligibility.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_static_dependency_trace.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_runtime_dependency_trace.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_eligibility.py -q
- Acceptance: AST/import/fixture/config/effect closure and runtime module/file/environment/subprocess/service facts are bounded and content addressed; unknown frontiers remain explicit; incomplete or uncontrolled effects return RUN; v1 reuse includes the current repository-forest CID.
- Gap task: PTR-020, PTR-021, PTR-022
- Refinement: Implement static and dynamic evidence independently, then admit eligibility only through their typed composition.
- Embedding query: pytest static AST import fixture dependency trace runtime audit hook completeness unknown frontier effect eligibility repository forest
- AST query: Locate AnalysisASTIndex providers, import graph closure, pytest fixture definitions, Python audit hooks, subprocess/file/environment effects, and analyzer-health receipts.

## PTR-G040 Trust-aware cache and certificate storage

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G010, PTR-G020
- Fib priority: 3
- Priority: P0
- Track: proof-cache
- Bundle: proof-test-reuse/cache
- Goal: Reuse existing trust-aware proof authority while adding immutable test receipt/certificate blobs, bounded locator indexes, atomic writes, revocation, and xdist-safe single flight.
- Evidence: ptr/test-proof-cache-admission@1, ptr/immutable-certificate-index@1, ptr/distributed-singleflight@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_cache.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_certificate_store.py -q
- Acceptance: Every hit re-derives authority from immutable bytes; mutable indexes are hints; stale, poisoned, oversized, private, partial, revoked, or path-escaping artifacts miss safely; writes are atomic and fenced; missing stores return RUN.
- Gap task: PTR-030, PTR-031
- Refinement: Keep trust admission separate from physical storage/index/concurrency mechanics.
- Embedding query: TrustAwareProofCache ProverEvidenceStore immutable CID CAS locator candidate index atomic write quarantine TTL revocation singleflight xdist
- AST query: Locate proof cache admission, evidence store, CAS tiers, atomic JSON persistence, merge fencing, revocation, and cache invalidation implementations.

## PTR-G050 Datasets real-ZK pass certificates

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G010, PTR-G040
- Fib priority: 3
- Priority: P0
- Track: datasets-zk
- Bundle: proof-test-reuse/datasets-zk
- Goal: Extend `ipfs_datasets_py.logic.zkp` with a minimal test-pass statement, real backend binding, deferred issuance, and a lazy accelerator verification adapter.
- Evidence: ptr/test-pass-statement@1, ptr/real-zk-certificate-conformance@1, ptr/deferred-certificate-issuance@1, ptr/datasets-certificate-adapter@1
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_execution_certificate.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_test_certificate_provider.py -q
- Acceptance: Real Groth16/ProveKit certificates bind exact receipt/execution/policy/circuit/key/issuer public inputs; verification and proving are split; issuance is deferred and leaks no witness data; an unavailable backend is a typed non-blocking result; simulated ZK never authorizes skip.
- Gap task: PTR-040, PTR-041, PTR-042, PTR-043
- Refinement: Build the statement, real certificate conformance, deferred issuer, and lazy cross-package adapter as dependency-ordered units.
- Embedding query: ipfs_datasets logic zkp test pass statement Groth16 ProveKit public inputs receipt certificate deferred issuance verifier
- AST query: Locate ZKP statement protocols, ZKPProof, ProveKit circuits/backends, Groth16 adapters, public input validation, capability registries, and lazy imports.

## PTR-G060 Automatically discovered pytest plugin

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G020, PTR-G030, PTR-G040, PTR-G050
- Fib priority: 5
- Priority: P0
- Track: pytest-plugin
- Bundle: proof-test-reuse/pytest
- Goal: Provide one cold-import-safe pytest plugin that evaluates every collected item, verifies reusable candidates before fixture setup, records complete passes, and coordinates xdist without a test-file registry.
- Evidence: ptr/pytest-proof-reuse-plugin@1, ptr/pass-receipt-lifecycle@1, ptr/xdist-reuse-coordination@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lookup.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_lookup.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py -q
- Acceptance: off/shadow/read/write/readwrite modes work; lookup is batched and any fault runs; only setup+call+teardown pass creates a receipt; verified hits use standard `proof-cache-hit:<cid>` skips; xdist writes are controller-coordinated; cold import touches no optional service.
- Gap task: PTR-050, PTR-051, PTR-052, PTR-053
- Refinement: Land option/collection shell independently, then lookup and receipt paths, then xdist/reporting composition.
- Embedding query: pytest plugin collection modify items runtest logreport setup call teardown standard skip pytest11 direct node xdist cache proof
- AST query: Locate pytest options/hooks, root conftests, plugin entry points, report serialization, xdist worker/controller hooks, and hermetic autoload controls.

## PTR-G070 Agent-supervisor completion authority

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G060
- Fib priority: 5
- Priority: P0
- Track: supervisor-authority
- Bundle: proof-test-reuse/supervisor
- Goal: Integrate proof-backed pytest results with hermetic validation and authoritative completion without allowing ordinary skips or cache flags to count as evidence.
- Evidence: ptr/proof-reuse-validation-receipt@1, ptr/supervisor-authority-conformance@1, ptr/accelerator-pytest-bootstrap@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py, external/ipfs_accelerate/conftest.py, external/ipfs_accelerate/pyproject.toml
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_cached_test_validation.py external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_bootstrap.py -q
- Acceptance: A cached hit emits fresh current-tree typed validation proof; plain skip, simulated proof, or stale receipt cannot satisfy goal/task/merge authority; installed and autoload-disabled direct-node invocations discover the plugin; coverage/mutation/profile modes execute.
- Gap task: PTR-060, PTR-061
- Refinement: Establish the supervisor authority adapter before enabling repository bootstrap and packaging registration.
- Embedding query: agent supervisor validation cached pytest skip completion evidence merge gate hermetic plugin autoload direct node
- AST query: Locate validation command result parsing, completion evidence, merge gates, pytest subprocess environment, pyproject pytest11 entries, and accelerator conftest.

## PTR-G080 Datasets repository integration

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G050, PTR-G060
- Fib priority: 5
- Priority: P0
- Track: datasets-integration
- Bundle: proof-test-reuse/datasets-bootstrap
- Goal: Make datasets suite and directly selected tests automatically use the shared plugin while replacing its commit-only test cache with the exact proof-backed lifecycle.
- Evidence: ptr/datasets-test-certificate-provider@1, ptr/datasets-pytest-bootstrap@1
- Outputs: external/ipfs_datasets/tests/conftest.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py -q
- Acceptance: Individual and suite tests pick up the plugin without file lists; the existing commit cache cannot skip and its nested hook defect is removed; plugin/provider/cache absence runs normally; proof creation remains after terminal pass.
- Gap task: PTR-070
- Refinement: Keep datasets bootstrap and legacy-hook migration in one repository-owned task after shared plugin and issuer contracts stabilize.
- Embedding query: ipfs_datasets pytest conftest commit cache nested hook plugin bootstrap individual node proof certificate
- AST query: Locate datasets conftest pytest hooks, commit cache state, pyproject entry points, ZKP imports, and direct-node test startup paths.

## PTR-G090 Kit storage and repository integration

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G040, PTR-G060
- Fib priority: 5
- Priority: P0
- Track: kit-integration
- Bundle: proof-test-reuse/kit
- Goal: Add strict optional certificate storage/capability facts in kit and bootstrap the shared plugin without starting daemons or trusting legacy pseudo-CIDs.
- Evidence: ptr/kit-certificate-store@1, ptr/kit-capability-fingerprint@1, ptr/kit-pytest-bootstrap@1
- Outputs: external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py, external/ipfs_kit/ipfs_kit_py/test_reuse_capabilities.py, external/ipfs_kit/conftest.py, external/ipfs_kit/tests/test_proof_reuse_bootstrap.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_kit/tests/test_proof_certificate_store.py external/ipfs_kit/tests/test_reuse_capabilities.py external/ipfs_kit/tests/test_proof_reuse_bootstrap.py -q
- Acceptance: Immutable local/IPFS transport verifies strict external CIDs; Kubo/Lotus/Iroh capabilities are lazy facts; a proof hit starts no daemon and touches no user IPFS directory; legacy fake CIDs are rejected; plugin/store absence runs normally.
- Gap task: PTR-080, PTR-081
- Refinement: Implement optional storage/capability contracts before enabling the kit repository bootstrap.
- Embedding query: ipfs_kit immutable certificate store strict multiformats CID Kubo Lotus Iroh capability lazy pytest bootstrap
- AST query: Locate kit multiformat adapters, storage APIs, daemon lifecycle, configuration directories, root/test conftests, and pyproject plugin registration.

## PTR-G100 Degradation, mutation, security, and e2e assurance

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G070, PTR-G080, PTR-G090
- Fib priority: 8
- Priority: P0
- Track: adversarial-assurance
- Bundle: proof-test-reuse/adversarial
- Goal: Demonstrate zero stale admissions across dependency mutations, unavailable/corrupt infrastructure, hostile storage, concurrency, restarts, and cross-repository direct-node execution.
- Evidence: ptr/degradation-matrix@1, ptr/invalidation-mutation-population@1, ptr/cross-repo-direct-node-conformance@1, ptr/security-concurrency-population@1
- Outputs: external/ipfs_accelerate/test/api/test_proof_reuse_degradation_matrix.py, external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py, external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py, external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_degradation_matrix.py external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py -q
- Acceptance: Every missing, corrupt, stale, forged, revoked, incompatible, timed-out, racy, restarted, or mutated case runs normally; all three repositories complete miss-pass-certificate-warm-skip-direct-node flows; off and coverage execute; false authoritative skips equal zero.
- Gap task: PTR-090, PTR-091, PTR-092, PTR-093
- Refinement: Establish the degradation baseline, then run disjoint mutation, security/concurrency, and cross-repository populations in parallel.
- Embedding query: proof cache degradation mutation invalidation forged certificate concurrency xdist restart cross repository direct node zero false skip
- AST query: Find all proof reuse decision branches and construct tests for provider errors, cache parsing, file safety, revocation, concurrent publication, plugin discovery, and test identity mutations.

## PTR-G110 Benchmark, rollout, and current-tree closeout

- Status: active
- Parent: PTR-G000
- Depends on: PTR-G100
- Fib priority: 13
- Priority: P1
- Track: rollout-closeout
- Bundle: proof-test-reuse/rollout
- Goal: Quantify safe savings, implement shadow-to-readwrite controls with forced rerun and rollback, and publish an exact current-tree completion gate.
- Evidence: ptr/shadow-benchmark@1, ptr/rollout-decision@1, ptr/final-current-tree-gate@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/self_improvement/proof_reuse_benchmark.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/rollout.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_reuse_benchmark.py external/ipfs_accelerate/test/api/test_proof_reuse_rollout.py external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py -q
- Acceptance: Shadow and warm benchmarks report zero false admissions, at least 80 percent reuse on the eligible warm fixture population, and verification cheaper than execution; rollout has sampling and automatic rollback; the final gate binds the current forest, closed task population, policy, capabilities, and fresh evidence.
- Gap task: PTR-100, PTR-101, PTR-102
- Refinement: Measure first, encode staged policy second, and let an independent final gate aggregate only current authoritative evidence.
- Embedding query: proof reuse benchmark saved time shadow warm hit rate forced rerun rollback rollout current tree completion evidence
- AST query: Locate supervisor metrics, rollout policy, validation populations, objective completion gates, repository snapshot identities, and proof-cache performance harnesses.
