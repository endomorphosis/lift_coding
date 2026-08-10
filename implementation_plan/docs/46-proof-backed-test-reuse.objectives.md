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
|-- PTR-G110  Benchmark, rollout, and current-tree closeout
|-- PTR-G120  Authenticated pass-receipt and real-ZK authority repair
|-- PTR-G130  Reachable zero-configuration runtime integration
`-- PTR-G140  Current-tree evidence, adversarial assurance, and closeout
```

## PTR-G000 Proof-backed cross-repository test reuse

- Status: verified_complete
- Parent:
- Depends on:
- Fib priority: 1
- Priority: P0
- Track: proof-test-reuse
- Bundle: proof-test-reuse/root
- Goal: Deliver exact proof-backed pytest reuse across the three outer IPFS Python repositories without per-test hardwiring and without turning unavailable proof infrastructure into a test failure or false skip.
- Evidence: ptr/cross-repository-current-tree-gate@1, ptr/zero-false-authoritative-skip@1, ptr/warm-reuse-benchmark@1, ptr/supervisor-launch-health@1
- Acceptance criteria: ptr/cross-repository-current-tree-gate@1; ptr/zero-false-authoritative-skip@1; ptr/warm-reuse-benchmark@1; ptr/supervisor-launch-health@1
- Outputs: implementation_plan/docs/46-proof-backed-test-reuse-plan-2026-07-31.md, implementation_plan/docs/46-proof-backed-test-reuse.objectives.md, implementation_plan/docs/46-proof-backed-test-reuse.todo.md, config/proof_backed_test_reuse_supervisor.json, scripts/validate_proof_backed_test_reuse_board.py, scripts/proof_backed_test_reuse_supervisor.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py -q
- Acceptance: Every child goal has current typed evidence, including the G130 datasets and kit V3 bootstrap contracts for the current tree and the G140 bounded actionable-retry contract; V2 bootstrap receipts and v7/v8 gate packets cannot satisfy the v9 runtime goal; every authoritative skip binds an exact trusted pass receipt and locally verified real certificate; zero stale or false skips occur; optional dependency loss always runs tests; the warm eligible population demonstrates useful savings.
- Gap task: Complete authenticated current-tree repair PTR-160 through PTR-171 and invoke operator closeout only after all 78 tasks have current artifact, ancestry, validation, signed-receipt, actionable-retry, real-proof and genuine cold/warm/replay evidence; historical PTR-149/66-task, v7/76-task and v8/77-task packets are provenance only.
- Refinement: Preserve one shared policy/plugin and split stable locator seeding, real Groth16 issuance, retained proof-bearing material, controller-owned candidate context, fresh two-stage revalidation, cold trace publication, controller composition, explicit setup-facing lazy provisioning, an auditable v4 native backend, fail-closed key/source/binary provenance, exact V2 local verification, genuine cross-repository e2e, and refreshed authority into independently reviewable child goals.
- Embedding query: exact proof-backed pytest reuse AST trace CID multihash pass receipt ZK cache graceful degradation all three IPFS Python repositories
- AST query: Find pytest collection and report hooks, proof-cache authority, content-identity bridges, ZKP adapters, repository conftests, and supervisor validation gates affected by reusable pass evidence.

## PTR-G010 Contracts, authority, and threat model

- Status: verified_complete
- Parent: PTR-G000
- Depends on:
- Fib priority: 2
- Priority: P0
- Track: foundation-contracts
- Bundle: proof-test-reuse/foundation
- Goal: Define finite typed records, authority precedence, capability results, and a reviewed ZK threat model before implementation can authorize any skip.
- Evidence: ptr/test-execution-contracts@1, ptr/reuse-authority-policy@1, ptr/zk-test-receipt-threat-model@1, ptr/capability-probe@1
- Acceptance criteria: ptr/test-execution-contracts@1; ptr/reuse-authority-policy@1; ptr/zk-test-receipt-threat-model@1; ptr/capability-probe@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_execution_contracts.py, external/ipfs_accelerate/docs/architecture/TEST_PROOF_REUSE_ZK_THREAT_MODEL.md, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/test_reuse_capabilities.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/activation_contracts.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_contracts.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_reuse_doctrine.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_capabilities.py -q
- Acceptance: Contracts reject nonfinite, unbounded, private, malformed, and illegal-authority inputs; CID and AST evidence are not pass evidence; only a trusted exact receipt and admitted real certificate may skip; simulated ZK is non-authoritative; capability absence is typed and non-blocking.
- Gap task: PTR-001, PTR-002, PTR-003, PTR-111, PTR-120, PTR-131
- Refinement: Separate executable schemas, security doctrine, cold lazy capability probing, and the automatic runtime activation boundary so every later composition step has one reviewed fail-closed contract.
- Embedding query: TestLocatorKey TestExecutionKey TestPassReceipt TestProofCertificate authority policy real ZK simulated ZK capability unavailable
- AST query: Locate accelerator proof dataclasses, ZK authority enums, lazy integrations, finite canonicalization checks, and existing capability probe conventions.

## PTR-G020 Canonical execution identity

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G010
- Fib priority: 2
- Priority: P0
- Track: execution-identity
- Bundle: proof-test-reuse/identity
- Goal: Produce strict locator and execution CIDs that change for every admitted behavior-affecting test, source, fixture, configuration, dependency, environment, capability, and policy input.
- Evidence: ptr/test-locator-key@1, ptr/test-execution-key@1, ptr/cross-package-cid-vectors@1
- Acceptance criteria: ptr/test-locator-key@1; ptr/test-execution-key@1; ptr/cross-package-cid-vectors@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_execution_identity.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_identity_components.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/default_identity_services.py, external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_identity_components.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_execution_identity_vectors.py -q
- Acceptance: CIDv1/base32/dag-json/sha2-256 identities independently reproduce across datasets and multiformats; parameters and context are canonical or non-reusable; forest, node, AST, fixtures, hooks, locks, environment, capabilities, and policy are bound; pseudo-CIDs are rejected.
- Gap task: PTR-010, PTR-011, PTR-012, PTR-110, PTR-111, PTR-120, PTR-134, PTR-143
- Refinement: Separate core keys, component collectors, independent known-vector conformance, and a lazy session-scoped factory; PTR-143 must attach a stable locator/static collection seed before runtime evidence exists and defer the final execution key until a complete cold trace or fresh warm revalidation exists.
- Embedding query: canonical pytest node identity parameter fixture conftest hook environment lock capability CIDv1 dag-json sha2-256
- AST query: Find nodeid normalization, parameter serialization, repository snapshot, content identity, installed distribution, fixture, conftest, and pytest hook sources.

## PTR-G030 Static/runtime traces and eligibility

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G010, PTR-G020
- Fib priority: 3
- Priority: P0
- Track: dependency-tracing
- Bundle: proof-test-reuse/tracing
- Goal: Combine bounded AST closure and observed runtime dependencies into explicit completeness and eligibility decisions, initially binding the full admitted repository forest.
- Evidence: ptr/static-test-dependency-trace@1, ptr/runtime-test-dependency-trace@1, ptr/reuse-eligibility-decision@1
- Acceptance criteria: ptr/static-test-dependency-trace@1; ptr/runtime-test-dependency-trace@1; ptr/reuse-eligibility-decision@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_static_dependency_trace.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_runtime_dependency_trace.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/analysis/test_reuse_eligibility.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runtime_revalidation.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_static_dependency_trace.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_runtime_dependency_trace.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_reuse_eligibility.py -q
- Acceptance: AST/import/fixture/config/effect closure and runtime module/file/environment/subprocess/service facts are bounded and content addressed; unknown frontiers remain explicit; incomplete or uncontrolled effects return RUN; v1 reuse includes the current repository-forest CID.
- Gap task: PTR-020, PTR-021, PTR-022, PTR-111, PTR-120, PTR-136, PTR-145, PTR-146
- Refinement: Implement static and dynamic evidence independently, start the production tracer around exactly one cold pytest lifecycle, then use a retained historical frontier only to rebuild and compare fresh current context before certificate verification.
- Embedding query: pytest static AST import fixture dependency trace runtime audit hook completeness unknown frontier effect eligibility repository forest
- AST query: Locate AnalysisASTIndex providers, import graph closure, pytest fixture definitions, Python audit hooks, subprocess/file/environment effects, and analyzer-health receipts.

## PTR-G040 Trust-aware cache and certificate storage

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G010, PTR-G020
- Fib priority: 3
- Priority: P0
- Track: proof-cache
- Bundle: proof-test-reuse/cache
- Goal: Reuse existing trust-aware proof authority while adding immutable test receipt/certificate blobs, bounded locator indexes, atomic writes, revocation, and xdist-safe single flight.
- Evidence: ptr/test-proof-cache-admission@1, ptr/immutable-certificate-index@1, ptr/distributed-singleflight@1
- Acceptance criteria: ptr/test-proof-cache-admission@1; ptr/immutable-certificate-index@1; ptr/distributed-singleflight@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_proof_cache.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_certificate_store.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/test_candidate_context_store.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_test_proof_cache.py external/ipfs_accelerate/test/api/test_agent_supervisor_test_certificate_store.py -q
- Acceptance: Every hit re-derives authority from immutable bytes; mutable indexes are hints; stale, poisoned, oversized, private, partial, revoked, or path-escaping artifacts miss safely; writes are atomic and fenced; missing stores return RUN.
- Gap task: PTR-030, PTR-031, PTR-111, PTR-120, PTR-135, PTR-145, PTR-147, PTR-154, PTR-155
- Refinement: Keep trust admission separate from physical storage/index/concurrency mechanics, use a dedicated locator-keyed candidate-context store before certificate lookup, preserve bounded controller-owned context through xdist, and make controller publication safe under partial/deferred issuance with exactly one post-verification candidate write.
- Embedding query: TrustAwareProofCache ProverEvidenceStore immutable CID CAS locator candidate index atomic write quarantine TTL revocation singleflight xdist
- AST query: Locate proof cache admission, evidence store, CAS tiers, atomic JSON persistence, merge fencing, revocation, and cache invalidation implementations.

## PTR-G050 Datasets real-ZK pass certificates

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G010, PTR-G040
- Fib priority: 3
- Priority: P0
- Track: datasets-zk
- Bundle: proof-test-reuse/datasets-zk
- Goal: Extend `ipfs_datasets_py.logic.zkp` with a minimal test-pass statement, real backend binding, deferred issuance, and a lazy accelerator verification adapter.
- Evidence: ptr/test-pass-statement@1, ptr/real-zk-certificate-conformance@1, ptr/deferred-certificate-issuance@1, ptr/datasets-certificate-adapter@1
- Acceptance criteria: ptr/test-pass-statement@1; ptr/real-zk-certificate-conformance@1; ptr/deferred-certificate-issuance@1; ptr/datasets-certificate-adapter@1
- Outputs: external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_execution_certificate.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/logic/zkp/test_test_pass_statement.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_execution_certificate.py external/ipfs_datasets/tests/unit/logic/zkp/test_test_certificate_issuer.py external/ipfs_accelerate/test/api/test_agent_supervisor_ipfs_datasets_test_certificate_provider.py -q
- Acceptance: Real Groth16/ProveKit certificates bind exact receipt/execution/policy/circuit/key/issuer public inputs; verification and proving are split; issuance is deferred and leaks no witness data; an unavailable backend is a typed non-blocking result; simulated ZK never authorizes skip.
- Gap task: PTR-040, PTR-041, PTR-042, PTR-043, PTR-108, PTR-110, PTR-111, PTR-120, PTR-132, PTR-137, PTR-144, PTR-147, PTR-151, PTR-152, PTR-153, PTR-155
- Refinement: Version the exact canonical statement profile and side-effect-free setup contract first, then implement a test-pass-specific real Groth16 circuit/provider and auditable v4-capable native release whose complete proof-bearing certificate material is preserved and locally V2-verified by the controller; only manifest-pinned current source, binary and key identities are authoritative, while missing artifacts remain typed deferred state.
- Embedding query: ipfs_datasets logic zkp test pass statement Groth16 ProveKit public inputs receipt certificate deferred issuance verifier
- AST query: Locate ZKP statement protocols, ZKPProof, ProveKit circuits/backends, Groth16 adapters, public input validation, capability registries, and lazy imports.

## PTR-G060 Automatically discovered pytest plugin

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G020, PTR-G030, PTR-G040, PTR-G050
- Fib priority: 5
- Priority: P0
- Track: pytest-plugin
- Bundle: proof-test-reuse/pytest
- Goal: Provide one cold-import-safe pytest plugin that evaluates every collected item, verifies reusable candidates before fixture setup, records complete passes, and coordinates xdist without a test-file registry.
- Evidence: ptr/pytest-proof-reuse-plugin@1, ptr/pass-receipt-lifecycle@1, ptr/xdist-reuse-coordination@1
- Acceptance criteria: ptr/pytest-proof-reuse-plugin@1; ptr/pass-receipt-lifecycle@1; ptr/xdist-reuse-coordination@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/default_identity_services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lookup.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/services.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/receipt.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/xdist.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_pytest_proof_reuse_plugin.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_lookup.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_receipt.py external/ipfs_accelerate/test/api/test_pytest_proof_reuse_xdist.py -q
- Acceptance: off/shadow/read/write/readwrite modes work; lookup is batched and any fault runs; only setup+call+teardown pass creates a receipt; default real-ZK policy inputs bind CIDs of the exact reviewed circuit and activated verifying-key bytes, never synthetic labels or certificate-selected artifacts; verified hits use standard `proof-cache-hit:<cid>` skips; xdist writes are controller-coordinated; cold import touches no optional service.
- Gap task: PTR-050, PTR-051, PTR-052, PTR-053, PTR-111, PTR-120, PTR-138, PTR-143, PTR-145, PTR-146, PTR-147, PTR-150, PTR-152, PTR-153, PTR-154, PTR-155
- Refinement: Compose scoped default dependency injection only after locator-first collection, candidate-context revalidation, one-call cold trace publication, explicit side-effect-free setup-facing provisioning, proof-bearing issuance and exact controller V2 verification are independently complete; explicit injections remain test overrides but cannot stand in for zero-configuration production evidence.
- Embedding query: pytest plugin collection modify items runtest logreport setup call teardown standard skip pytest11 direct node xdist cache proof
- AST query: Locate pytest options/hooks, root conftests, plugin entry points, report serialization, xdist worker/controller hooks, and hermetic autoload controls.

## PTR-G070 Agent-supervisor completion authority

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G060
- Fib priority: 5
- Priority: P0
- Track: supervisor-authority
- Bundle: proof-test-reuse/supervisor
- Goal: Integrate proof-backed pytest results with hermetic validation and authoritative completion without allowing ordinary skips or cache flags to count as evidence.
- Evidence: ptr/proof-reuse-validation-receipt@1, ptr/supervisor-authority-conformance@1, ptr/accelerator-pytest-bootstrap@1
- Acceptance criteria: ptr/proof-reuse-validation-receipt@1; ptr/supervisor-authority-conformance@1; ptr/accelerator-pytest-bootstrap@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_cached_test_validation.py, external/ipfs_accelerate/conftest.py, external/ipfs_accelerate/pyproject.toml, external/ipfs_accelerate/setup.py, external/ipfs_accelerate/requirements.txt, external/ipfs_accelerate/ipfs_accelerate_py/__init__.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/lazy_dependencies.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_cached_test_validation.py external/ipfs_accelerate/test/api/test_proof_reuse_accelerator_bootstrap.py -q
- Acceptance: A cached hit emits fresh current-tree typed validation proof; plain skip, simulated proof, or stale receipt cannot satisfy goal/task/merge authority; installed and autoload-disabled direct-node invocations discover the plugin; coverage/mutation/profile modes execute.
- Gap task: PTR-060, PTR-061, PTR-110, PTR-112, PTR-120, PTR-121, PTR-122, PTR-139, PTR-142, PTR-143, PTR-147, PTR-149, PTR-150, PTR-152, PTR-153, PTR-154, PTR-155
- Refinement: Establish the supervisor authority adapter and a genuinely composed locator-first/cold-publication/warm-revalidation runtime, retain manifest parity and bounded lazy installation, then admit only live capability and exact 66-task corrective-wave evidence with pinned current v4 source, binary, key, proof-material and controller-context provenance.
- Embedding query: agent supervisor validation cached pytest skip completion evidence merge gate hermetic plugin autoload direct node
- AST query: Locate validation command result parsing, completion evidence, merge gates, pytest subprocess environment, pyproject pytest11 entries, and accelerator conftest.

## PTR-G080 Datasets repository integration

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G050, PTR-G060
- Fib priority: 5
- Priority: P0
- Track: datasets-integration
- Bundle: proof-test-reuse/datasets-bootstrap
- Goal: Make datasets suite and directly selected tests automatically use the shared plugin while replacing its commit-only test cache with the exact proof-backed lifecycle.
- Evidence: ptr/datasets-test-certificate-provider@1, ptr/datasets-pytest-bootstrap@1
- Acceptance criteria: ptr/datasets-test-certificate-provider@1; ptr/datasets-pytest-bootstrap@1
- Outputs: external/ipfs_datasets/tests/conftest.py, external/ipfs_datasets/pyproject.toml, external/ipfs_datasets/setup.py, external/ipfs_datasets/requirements.txt, external/ipfs_datasets/ipfs_datasets_py/__init__.py, external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py, external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_datasets/tests/unit/test_proof_reuse_bootstrap.py -q
- Acceptance: Individual and suite tests pick up the plugin without file lists; the existing commit cache cannot skip and its nested hook defect is removed; plugin/provider/cache absence runs normally; proof creation remains after terminal pass.
- Gap task: PTR-070, PTR-110, PTR-111, PTR-120, PTR-140, PTR-144, PTR-148, PTR-151
- Refinement: Make the datasets shim and package root inject only narrow public protocols, keep native Groth16 build and NLTK download opt-in, supply a real test-pass-specific prover lazily, publish an auditable current v4-capable native release without automatic trusted setup, and prove the repository bootstrap with an uninjected two-process direct-node lifecycle.
- Embedding query: ipfs_datasets pytest conftest commit cache nested hook plugin bootstrap individual node proof certificate
- AST query: Locate datasets conftest pytest hooks, commit cache state, pyproject entry points, ZKP imports, and direct-node test startup paths.

## PTR-G090 Kit storage and repository integration

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G040, PTR-G060
- Fib priority: 5
- Priority: P0
- Track: kit-integration
- Bundle: proof-test-reuse/kit
- Goal: Add strict optional certificate storage/capability facts in kit and bootstrap the shared plugin without starting daemons or trusting legacy pseudo-CIDs.
- Evidence: ptr/kit-certificate-store@1, ptr/kit-capability-fingerprint@1, ptr/kit-pytest-bootstrap@1
- Acceptance criteria: ptr/kit-certificate-store@1; ptr/kit-capability-fingerprint@1; ptr/kit-pytest-bootstrap@1
- Outputs: external/ipfs_kit/ipfs_kit_py/proof_certificate_store.py, external/ipfs_kit/ipfs_kit_py/test_reuse_capabilities.py, external/ipfs_kit/ipfs_kit_py/__init__.py, external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py, external/ipfs_kit/conftest.py, external/ipfs_kit/pyproject.toml, external/ipfs_kit/setup.py, external/ipfs_kit/requirements.txt, external/ipfs_kit/tests/test_proof_reuse_bootstrap.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_kit/tests/test_proof_certificate_store.py external/ipfs_kit/tests/test_reuse_capabilities.py external/ipfs_kit/tests/test_proof_reuse_bootstrap.py -q
- Acceptance: Immutable local/IPFS transport verifies strict external CIDs; Kubo/Lotus/Iroh capabilities are lazy facts; a proof hit starts no daemon and touches no user IPFS directory; legacy fake CIDs are rejected; plugin/store absence runs normally.
- Gap task: PTR-080, PTR-081, PTR-109, PTR-111, PTR-112, PTR-120, PTR-133, PTR-141, PTR-148
- Refinement: Harden strict arbitrary canonical artifact transport before enabling the kit shim, packaging parity, and opt-in lazy dependency bootstrap; then prove kit's ordinary direct-node cold-to-warm path without service injection or daemon startup.
- Embedding query: ipfs_kit immutable certificate store strict multiformats CID Kubo Lotus Iroh capability lazy pytest bootstrap
- AST query: Locate kit multiformat adapters, storage APIs, daemon lifecycle, configuration directories, root/test conftests, and pyproject plugin registration.

## PTR-G100 Degradation, mutation, security, and e2e assurance

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G070, PTR-G080, PTR-G090
- Fib priority: 8
- Priority: P0
- Track: adversarial-assurance
- Bundle: proof-test-reuse/adversarial
- Goal: Demonstrate zero stale admissions across dependency mutations, unavailable/corrupt infrastructure, hostile storage, concurrency, restarts, and cross-repository direct-node execution.
- Evidence: ptr/degradation-matrix@1, ptr/invalidation-mutation-population@1, ptr/cross-repo-direct-node-conformance@1, ptr/security-concurrency-population@1
- Acceptance criteria: ptr/degradation-matrix@1; ptr/invalidation-mutation-population@1; ptr/cross-repo-direct-node-conformance@1; ptr/security-concurrency-population@1
- Outputs: external/ipfs_accelerate/test/api/test_proof_reuse_degradation_matrix.py, external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py, external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py, external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py, external/ipfs_accelerate/test/api/test_proof_reuse_runtime_activation_e2e.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_degradation_matrix.py external/ipfs_accelerate/test/api/test_proof_reuse_invalidation_mutations.py external/ipfs_accelerate/test/api/test_proof_reuse_security_concurrency.py external/ipfs_accelerate/test/api/test_proof_reuse_cross_repository_e2e.py -q
- Acceptance: Every missing, corrupt, stale, forged, revoked, incompatible, timed-out, racy, restarted, or mutated case runs normally; all three repositories complete miss-pass-certificate-warm-skip-direct-node flows; off and coverage execute; false authoritative skips equal zero.
- Gap task: PTR-090, PTR-091, PTR-092, PTR-093, PTR-111, PTR-120, PTR-142, PTR-148, PTR-151, PTR-152, PTR-153, PTR-154, PTR-155
- Refinement: Supersede the injected and pseudo-certificate PTR-142 activation fixture and pre-v4 PTR-148 artifact assumptions with two independent direct-node pytest processes in every repository, retained real proof material, controller-reconstructed expected context, a locally V2-verified manifest-pinned current-v4 Groth16 certificate, missing-backend fail-open evidence, body-once proof, and raw subprocess timings.
- Embedding query: proof cache degradation mutation invalidation forged certificate concurrency xdist restart cross repository direct node zero false skip
- AST query: Find all proof reuse decision branches and construct tests for provider errors, cache parsing, file safety, revocation, concurrent publication, plugin discovery, and test identity mutations.

## PTR-G110 Benchmark, rollout, and current-tree closeout

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G100
- Fib priority: 13
- Priority: P1
- Track: rollout-closeout
- Bundle: proof-test-reuse/rollout
- Goal: Quantify safe savings, implement shadow-to-readwrite controls with forced rerun and rollback, and publish an exact current-tree completion gate.
- Evidence: ptr/shadow-benchmark@1, ptr/rollout-decision@1, ptr/final-current-tree-gate@1
- Acceptance criteria: ptr/shadow-benchmark@1; ptr/rollout-decision@1; ptr/final-current-tree-gate@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/self_improvement/proof_reuse_benchmark.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/rollout.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_proof_reuse_benchmark.py external/ipfs_accelerate/test/api/test_proof_reuse_rollout.py external/ipfs_accelerate/test/api/test_agent_supervisor_proof_test_reuse_current_tree_gate.py -q
- Acceptance: Shadow and warm benchmarks report zero false admissions, at least 80 percent reuse on the eligible warm fixture population, and verification cheaper than execution; rollout has sampling and automatic rollback; the final gate distinguishes native Groth16 availability from test-certificate authority and binds the current forest, closed task population, policy, exact circuit/key capabilities, and fresh evidence.
- Gap task: PTR-100, PTR-101, PTR-102, PTR-108, PTR-109, PTR-110, PTR-111, PTR-112, PTR-120, PTR-121, PTR-122, PTR-130, PTR-142, PTR-148, PTR-149, PTR-150, PTR-151, PTR-152, PTR-153, PTR-154, PTR-155
- Refinement: Measure actual cold and warm subprocesses only after genuine zero-false-skip assurance, expand the final gate to all 66 tasks with a fresh PTR-143 through PTR-155 production-activation premise, reject historical PTR-142, pre-v4 PTR-148 and pre-material 63-task evidence, surface an activation gap instead of false closeout when reviewed current keys are absent, and retain the existing single-writer closeout as an explicit operator action.
- Embedding query: proof reuse benchmark saved time shadow warm hit rate forced rerun rollback rollout current tree completion evidence
- AST query: Locate supervisor metrics, rollout policy, validation populations, objective completion gates, repository snapshot identities, and proof-cache performance harnesses.

## PTR-G120 Authenticated pass-receipt and real-ZK authority repair

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G010, PTR-G040, PTR-G050
- Fib priority: 1
- Priority: P0
- Track: authenticated-proof-authority
- Bundle: proof-test-reuse/authenticated-authority-v7
- Goal: Ensure that a proof-carrying cache hit derives pass authority from a cryptographically authenticated complete runner receipt, not from self-asserted fields or proving-key possession.
- Evidence: ptr/runner-pass-attestation@1, ptr/test-pass-statement-v5@1, ptr/authenticated-real-backend-adversarial@1
- Acceptance criteria: ptr/runner-pass-attestation@1; ptr/test-pass-statement-v5@1; ptr/authenticated-real-backend-adversarial@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/runner_pass_attestation.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/statements/test_pass.py, external/ipfs_datasets/ipfs_datasets_py/logic/zkp/test_certificate_issuer.py, external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_real_backend_adversarial.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_runner_pass_attestation.py external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_real_backend_adversarial.py -q
- Acceptance: Ed25519 signs the domain-separated digest of one canonical DAG-CBOR unsigned envelope; the envelope, multicodec-prefixed public key and locally pinned trust policy have strict CIDv1 identities; receipt signatures bind exact execution/context and complete phase/trace roots; pytest-pass key usage, validity, epochs, rotation and revocation are enforced without TOFU; TestPassStatementV5 binds the signed attestation; a manifest-pinned native setup/prove/verify vector runs without skips; legacy, simulated, unsigned and forged receipts always run; no secret enters public artifacts.
- Gap task: PTR-160, PTR-163, PTR-166
- Refinement: Separate runner trust contracts, datasets real-proof binding and adversarial forgery assurance so no component can approve its own evidence.
- Embedding query: signed pytest pass receipt runner attestation public key multicodec CID Groth16 proof forgery revocation
- AST query: Locate receipt creation, trust policy, datasets test-pass statement/circuit, certificate issuance and publication authority checks.

## PTR-G130 Reachable zero-configuration runtime integration

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G020, PTR-G030, PTR-G060, PTR-G080, PTR-G090, PTR-G120
- Fib priority: 2
- Priority: P0
- Track: reachable-zero-config-runtime
- Bundle: proof-test-reuse/reachable-runtime-v7
- Goal: Make ordinary installed and source-checkout pytest invocations in all three repositories discover a cold-safe bridge and reach exact locator/current-context lookup without test rewrites.
- Evidence: ptr/datasets-bootstrap-v3@1, ptr/kit-bootstrap-v3@1, ptr/authenticated-runtime-composition@1
- Acceptance criteria: ptr/datasets-bootstrap-v3@1; ptr/kit-bootstrap-v3@1; ptr/authenticated-runtime-composition@1
- Outputs: external/ipfs_datasets/ipfs_datasets_py/pytest_proof_reuse.py, external/ipfs_datasets/tests/unit/test_proof_reuse_isolated_bootstrap_subprocess.py, external/ipfs_kit/ipfs_kit_py/pytest_proof_reuse.py, external/ipfs_kit/tests/test_proof_reuse_isolated_bootstrap_subprocess.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/plugin.py, external/ipfs_accelerate/ipfs_accelerate_py/testing/proof_reuse/publication.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_proof_reuse_locator_only_warm_path.py external/ipfs_datasets/tests/unit/test_proof_reuse_optional_plugin_startup.py external/ipfs_datasets/tests/unit/test_proof_reuse_isolated_bootstrap_subprocess.py external/ipfs_kit/tests/test_proof_reuse_optional_plugin_startup.py external/ipfs_kit/tests/test_proof_reuse_isolated_bootstrap_subprocess.py -q
- Acceptance: Only current `ptr/datasets-bootstrap-v3@1` and `ptr/kit-bootstrap-v3@1` evidence satisfies the repository bootstrap boundary; V2 receipts are stale for this goal. Unique `pytest11` bridges plus conditional module-level root `pytest_plugins` load without `-p` or test edits in isolated installed and source direct-node subprocesses; a namespace-only empty accelerator hierarchy left by an uninitialized gitlink is treated as optional absence and remains an inert no-op, while a regular installed-style `ipfs_accelerate_py/__init__.py` whose testing/plugin hierarchy is missing exposes `ModuleNotFoundError` rather than being mistaken for optional absence; package-owned bridges never suppress a transitive failure from an accelerator plugin that was actually found; package `__init__` files expose lazy facades only and never install, build, download, start daemons or touch user state; ordinary items reach two-stage lookup; current context and signed authority are revalidated; no genuinely absent optional plugin/cache/prover/transport prevents real test execution.
- Gap task: PTR-161, PTR-162, PTR-164
- Refinement: Recover reachable package surfaces independently, then join them with the accelerator's locator-first and controller-only runtime.
- Embedding query: pytest11 lazy bridge no test rewrite locator only warm lookup current context xdist controller publication
- AST query: Locate package entry points/conftests/facades, collection filtering, locator lookup, current context, receipt and xdist publication paths.

## PTR-G140 Current-tree evidence, adversarial assurance, and closeout

- Status: verified_complete
- Parent: PTR-G000
- Depends on: PTR-G070, PTR-G100, PTR-G110, PTR-G120, PTR-G130
- Fib priority: 3
- Priority: P0
- Track: authenticated-current-tree-assurance
- Bundle: proof-test-reuse/current-tree-assurance-v9
- Goal: Preserve actionable retry counterexamples, reconcile historical implementation onto reachable exact gitlinks, and publish fresh 78-task evidence from genuine ordinary pytest cold/warm/replay and adversarial runs.
- Evidence: ptr/actionable-retry-evidence@1, ptr/completed-task-artifact-evidence@1, ptr/verified-history-replay@1, ptr/genuine-three-repository-e2e-v2@1, ptr/authenticated-current-tree-gate-v5@1
- Acceptance criteria: ptr/actionable-retry-evidence@1; ptr/completed-task-artifact-evidence@1; ptr/verified-history-replay@1; ptr/genuine-three-repository-e2e-v2@1; ptr/authenticated-current-tree-gate-v5@1
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py, external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_failure_review.py, external/ipfs_accelerate/test/api/test_agent_supervisor_context_delta.py, external/ipfs_accelerate/test/api/test_agent_supervisor_todo_daemon_port.py, scripts/proof_backed_test_reuse_task_evidence.py, scripts/proof_backed_test_reuse_replay_verified_tasks.py, scripts/proof_backed_test_reuse_objective_reconciliation.py, external/ipfs_accelerate/test/api/test_proof_reuse_genuine_three_repo_e2e.py, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/validation/proof_test_reuse_current_tree_gate.py
- Validation: IPFS_TEST_PROOF_REUSE_MODE=off python3 -m pytest external/ipfs_accelerate/test/api/test_agent_supervisor_implementation_failure_review.py external/ipfs_accelerate/test/api/test_agent_supervisor_context_delta.py external/ipfs_accelerate/test/api/test_agent_supervisor_todo_daemon_port.py tests/test_proof_backed_test_reuse_task_evidence.py tests/test_proof_backed_test_reuse_replay_verified_tasks.py test/test_proof_backed_test_reuse_objective_reconciliation.py external/ipfs_accelerate/test/api/test_proof_reuse_genuine_three_repo_e2e.py external/ipfs_accelerate/test/api/test_proof_reuse_authenticated_current_tree_gate.py -q
- Acceptance: Failed subprocess validation remains attempted/failed and produces deterministic, deduplicated retry evidence of at most 16 KiB with its receipt, command/test/path/exception/failure head and hash-marked truncation intact; no normalizer exception relabels it as setup/not-run. Completed labels are backed by present outputs and validation targets with exact path owners, task/merge receipts and ancestor commits on fetchable exact gitlinks; cold/warm/replay uses no `-p`, service or tracer injection; body-oracle false skips are zero; performance threshold passes; optional gaps remain RUN/DEFERRED; G120/G130/G140 remain mandatory; PTR-169's self-receipt is only a candidate until the outer controller reruns the 78-task gate on its merged commit and then projects completion. Any 77-task, 76-task, v8 or v7 packet is stale.
- Gap task: PTR-163, PTR-171, PTR-165, PTR-167, PTR-168, PTR-169
- Refinement: Preserve bounded actionable failures before retrying repository repairs, validate evidence rules, replay only verified material, prove the public three-repository lifecycle, then perform one final current-tree join.
- Embedding query: task artifact evidence gitlink reachability replay merge receipt cold warm forced rerun zero false skip benchmark closeout
- AST query: Locate task/merge receipts, submodule pins, current-tree gates, subprocess fixtures, body counters, mutation oracles and rollout metrics.

## Closeout candidate metadata

- Operator commit required: true
- Fence token: 1
- Fence revision: 3
- Binding count: 15
- Optional gaps: 5
- Artifact: ObjectiveCompletionEvidenceArtifact
