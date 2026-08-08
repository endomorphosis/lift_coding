# Proof-Backed Test Reuse Across IPFS Python Repositories

Date: 2026-07-31

Current reviewed revision: 2026-08-08 (`authenticated-receipt-current-tree-repair-v8`)

Program: `proof-backed-test-reuse-v1`

Task prefix: `PTR-`
Integration branch: `agent/proof-backed-test-reuse`

## 1. Outcome

Upgrade the test infrastructure shared by `ipfs_accelerate_py`,
`ipfs_datasets_py`, and `ipfs_kit_py` so a test whose exact prior successful
execution is still valid can be represented by a verified proof certificate
and reported by pytest as skipped. The implementation must work for an entire
collected test suite and for a directly selected node such as
`pytest tests/test_x.py::test_y`; it must not require a maintained list of test
files.

The optimization is deliberately conservative:

1. A CID proves the identity of bytes, not that a test passed.
2. An AST or runtime dependency trace scopes invalidation; similarity is never
   pass evidence.
3. A skip is authorized only by an exact trusted pass receipt, a current
   execution identity, an admitted policy, and a locally verified certificate.
4. A missing, slow, incompatible, corrupt, expired, or unreachable optional
   dependency produces `RUN`, never an error and never `SKIP`.
5. Simulated ZK is test evidence for adapters only and can never authorize a
   production skip.
6. Proof creation is deferred until after a complete pass and is never on the
   critical path that decides whether the test itself passed.

This is proof of a prior execution under an identical admitted context, not a
proof that arbitrary changed code remains correct. The first production
release intentionally binds the complete admitted repository forest. Narrower
dependency-based reuse becomes eligible only after trace-completeness tests and
mutation evidence establish that it is safe.

## 2. Scope and non-goals

### In scope

- Python tests collected through pytest in all three repositories.
- Stable identities for test nodes, parameters, code, fixtures, hooks,
  configuration, dependencies, environment, capabilities, and observed effects.
- Strict multiformats/multihash CID creation and verification.
- Static Python AST dependency closure plus bounded runtime dependency traces.
- Immutable pass receipts, optional real-ZK certificates, local/remote CAS, and
  mutable lookup indexes with revalidation on every hit.
- One reusable pytest plugin with package-specific bootstrap only.
- pytest-xdist coordination, concurrency, corruption, revocation, and downgrade
  behavior.
- Fresh supervisor validation evidence for a proof-backed skip.
- Shadow measurement, forced re-execution sampling, gradual rollout, and rapid
  rollback.

### Non-goals

- Replacing pytest outcomes with solver scores or model judgments.
- Treating ordinary pytest skips, xfail, xpass, flaky reruns, coverage runs, or
  benchmark results as reusable passes.
- Creating a second proof-cache trust root alongside the accelerator's
  `TrustAwareProofCache` and `ProverEvidenceStore` contracts.
- Allowing the legacy test-only hash strings in `ipfs_kit_py.ipfs_multiformats`
  to cross an authority boundary as CIDs.
- Starting Kubo, Lotus, Iroh, Groth16, or ProveKit automatically.
- Reusing tests with uncontrolled network, clock, randomness, mutable external
  data, subprocess, hardware, or secret-dependent effects unless an explicit
  snapshot adapter closes and binds that dependency.
- Claiming a zero-knowledge property when the configured backend is simulated.

### Supervisor provider execution policy

The reviewed proof-reuse supervisor profile always starts implementation work
with Grok model `grok-4.5` when that primary is ready. Preflight probes Grok
binary and headless-auth readiness, but an unavailable, unlaunchable, or
unauthenticated Grok primary activates the configured Codex fallback instead of
blocking launch, provided that Codex itself is installed and authenticated.

Codex is the automatic fallback with model `gpt-5.6-terra` and
`model_reasoning_effort="high"`. The canonical
`ipfs_accelerate_py.llm_router` owns provider readiness, failure
classification, fallback selection, and route records. Its explicit agent
route is separate from `generate_text`: it preserves the router invariant that
side-effecting work is never replayed through a second provider. Codex is
selected automatically only for confirmed Grok quota exhaustion,
authentication failure, or launch unavailability while the worktree remains
unchanged. Timeout, transport, malformed output, generic nonzero exit, task
failure, or detected worktree mutation is terminal for that attempt.

Preflight records primary readiness, the effective provider, and fallback
reason; status records the exact static router policy; and every transition
emits typed, bounded, task/attempt/stage-bound route telemetry in the private
runtime state and event stream. That telemetry explicitly has no completion
authority: proposal, validation, merge, and authenticated closeout receipts
remain the only acceptance authorities. The stdin/worktree runner is only a
process adapter and sanitizer; it does not own provider selection. Semantic
merge invocations repeat the typed readiness probe so a recovered Grok primary
is selected without restarting the supervisor.

This behavior is profile-scoped and selects
`IPFS_ACCELERATE_AGENT_PROVIDER_FALLBACK_POLICY=grok_quota_auth_or_unavailable`
for both implementation and semantic merge resolution. Provider output remains
a proposal only: automatic routing never bypasses isolated-worktree
containment, protected-path and proposal checks, declared validation, the
serial merge queue, authenticated test receipts, or current-tree closeout
gates. Provider stderr is sanitized before replay or persistence, known
credential assignments and bearer values are redacted, and spawned lane
processes use a private file-creation mask.

## 3. Existing assets and gaps

| Repository | Reuse | Required upgrade |
| --- | --- | --- |
| `ipfs_accelerate_py` | `AnalysisASTIndex`, `content_identity_bridge`, proof-cache/evidence contracts, ZK attestation adapter, supervisor validation and objective machinery | Add test identity/trace/certificate domains, the shared pytest plugin, proof-reuse validation, and rollout controls |
| `ipfs_datasets_py` | Strict `cid_utils`, logic canonical identity, `logic.common.proof_cache`, ZKP statements/backends including ProveKit | Add the test-pass statement, real certificate/issuer adapters, and a lazy pytest bootstrap; repair the existing commit-only cache hook rather than making it another authority |
| `ipfs_kit_py` | Local/IPFS storage and multiformat integrations | Add an optional immutable certificate transport and capability fingerprint; reject legacy pseudo-CIDs and never start a daemon during collection or verification |

The authoritative orchestration root is the outer superproject. Its current
submodules are `external/ipfs_accelerate`, `external/ipfs_datasets`, and
`external/ipfs_kit`. The similarly named nested gitlinks inside the accelerator
checkout are not substituted for these repositories.

## 4. Trust and safety invariants

The following invariants are release blockers.

- `SKIP` is an allow decision. Unknown, unavailable, timeout, unsupported,
  malformed, stale, revoked, ambiguous, over-budget, or exception states map to
  `RUN`.
- Lookup and proof verification are local, bounded, deterministic operations.
  A proving service may be remote, but a remote service is never consulted to
  decide an existing hit when the local verifier can operate.
- Certificate and receipt CIDs are recomputed from retained canonical bytes.
  Parsed fields cannot be trusted until the CID multihash matches those bytes.
- The verifier key CID, circuit CID, proof-system identifier, statement schema,
  issuer/trust policy, and policy version are public inputs.
- A real proof establishes possession of an exact trusted pass receipt and the
  declared statement only. It does not turn an incomplete dependency trace into
  a complete one.
- Receipt creation requires passing setup, call, and teardown phases. Skipped,
  xfailed, xpassed, rerun-only, interrupted, timed-out, leaked-resource, or
  incomplete-trace executions are not admitted.
- Test-reuse implementation tests always run with
  `IPFS_TEST_PROOF_REUSE_MODE=off`, preventing the feature from validating
  itself through its own cache.
- Coverage, mutation testing, profiling, leak detection, debugger, and
  benchmark modes disable proof-backed skips unless a future reviewed policy
  explicitly defines equivalent semantics.
- No witness, test secret, environment secret, stdout/stderr body, private path,
  or source body is placed in a public input or shared lookup index.
- Mutable indexes are hints. Immutable content plus local verification remains
  the authority.

## 5. Architecture

```text
pytest collection
      |
      v
TestLocatorKey ---- static AST/fixture/hook/import/config closure
      |                              |
      +---------- current snapshot -+
                     |
                     v
             TestExecutionKey CID
                     |
              batched index lookup
                     |
       +-------------+--------------+
       |                            |
 no candidate / any fault     immutable candidate bytes
       |                            |
       v                            v
     RUN TEST              CID + policy + ZK verification
       |                            |
 setup/call/teardown pass      exact current binding?
       |                       /                 \
 runtime trace + receipt     no                   yes
       |                     |                     |
 immutable CAS write        RUN            pytest standard skip
       |                                    proof-cache-hit:<cid>
 deferred real proving
       |
 certificate CAS + locator index publication
```

### 5.1 Shared component placement

The shared plugin and authority decisions live in `ipfs_accelerate_py`:

- `agent_supervisor/proof/test_execution_contracts.py`
- `agent_supervisor/analysis/test_execution_identity.py`
- `agent_supervisor/analysis/test_static_dependency_trace.py`
- `agent_supervisor/analysis/test_runtime_dependency_trace.py`
- `agent_supervisor/analysis/test_reuse_eligibility.py`
- `agent_supervisor/proof/test_proof_cache.py`
- `agent_supervisor/proof/test_certificate_store.py`
- `agent_supervisor/integrations/ipfs_datasets_test_certificate_provider.py`
- `agent_supervisor/validation/proof_cached_test_validation.py`
- `testing/proof_reuse/`

The ZK statement, circuit/backend binding, and deferred issuer live in
`ipfs_datasets_py.logic.zkp`. Optional IPFS-backed certificate transport and
storage capability fingerprints live in `ipfs_kit_py`. Neither package owns a
separate decision policy.

### 5.2 Typed decision boundary

All lookups return a `ReuseDecision` with one of two actions:

- `RUN(reason_code, diagnostics)`
- `SKIP(certificate_cid, receipt_cid, validation_receipt, diagnostics)`

There is no third implicit truthy state. Plugin boundaries catch ordinary
provider/cache exceptions, normalize them to bounded reason codes, and choose
`RUN`. A strict `required-audit` mode may fail an explicitly configured audit
job after collection, but it does not silently change normal developer test
semantics.

## 6. Canonical identities

### 6.1 CID profile

Authoritative JSON artifacts use:

- canonicalization: strict DAG-JSON profile v1 with sorted keys, UTF-8, finite
  values only, and no implicit string coercion;
- CID: CIDv1, lowercase base32;
- multicodec: `dag-json`;
- multihash: `sha2-256`;
- verification: decode through `multiformats.CID`, decode the multihash, and
  compare its digest to SHA-256 of the retained canonical bytes.

The implementation uses `ipfs_datasets_py.utils.cid_utils` through the
accelerator's lazy content-identity bridge. Cross-package known vectors must be
independently reproduced. Missing `multiformats` makes CID-required reuse
unavailable and runs the test.

### 6.2 `TestLocatorKey@1`

The locator narrows candidate retrieval but cannot authorize reuse. It binds:

- repository/package identity and normalized root;
- normalized pytest node ID;
- collection/plugin schema version;
- canonical parameter ID and values, or an explicit non-reusable reason;
- selection semantics relevant to the node.

The index maps the locator CID to a bounded set of immutable certificate CIDs.

### 6.3 `TestExecutionKey@1`

The execution key is the exact reusable context and includes:

- locator CID;
- Git commit/tree/gitlink state and dirty overlay identity;
- test module, class, function, decorator, and parameter source/AST CIDs;
- fixture definitions, scopes, values or value adapters, `conftest.py` closure,
  and pytest hook/plugin code CIDs;
- static import/call dependency closure and explicit unknown frontier;
- admitted prior runtime trace root and completeness policy;
- pytest/Python/plugin versions, command semantics, configuration, and markers;
- dependency-lock and installed-distribution fingerprints;
- allowlisted environment, platform, interpreter ABI, hardware/capability, and
  external snapshot identities;
- reuse-policy, canonicalization, tracer, and certificate schema CIDs.

For rollout v1, the admitted repository-forest CID is also bound. This avoids a
false hit caused by an initially incomplete dependency analysis. A later policy
may replace the forest with a narrower closed dependency root only after the
mutation population proves completeness for that eligibility class.

### 6.4 Dirty and generated state

Tracked modifications, staged changes, deletions, renames, recursive gitlink
changes, and allowlisted generated inputs are canonical overlay records. An
unaccounted untracked source or generated dependency makes the item ineligible.
Paths are repository-relative; symlinks and path escapes are rejected.

## 7. Static and runtime traces

### 7.1 Static trace

The static tracer extends existing AST index contracts and records:

- test symbol and decorator spans;
- imports and resolved source/module identities;
- fixture references and definitions;
- relevant `conftest.py`, pytest hooks, and registered plugins;
- configuration and data-file references that can be resolved statically;
- subprocess/network/filesystem/time/random/hardware effects;
- an explicit unresolved/dynamic frontier;
- tracer/parser/tool version and bounded-analysis receipts.

Dynamic import, reflection, native extension, opaque decorator, and unresolved
fixture cases remain typed unknowns. They do not disappear from the trace.

### 7.2 Runtime trace

The successful cold execution observes, with strict bounds:

- loaded Python modules and code objects;
- opened/read files and content identities where policy permits;
- allowlisted environment reads;
- subprocess executable/arguments/tool identity;
- service/capability identities supplied by adapters;
- random seed, clock policy, hardware selection, and accelerator capabilities;
- trace overflow, unsupported event, and instrumentation health.

Instrumentation must avoid recording secrets or large payloads. A trace is
complete only for a declared eligibility profile. Incomplete or over-budget
traces can still be diagnostic and cached, but cannot authorize reuse.

### 7.3 Eligibility classes

- `pure`: deterministic code and immutable fixture/data closure.
- `snapshot_bound`: controlled external state with an authoritative snapshot
  adapter and current identity.
- `repository_forest_bound`: v1 safe default; any admitted repository change
  invalidates the candidate.
- `non_reusable`: uncontrolled effects, unsupported parameter serialization,
  incomplete trace, secrets, or policy exclusion.

## 8. Pass receipt and zero-knowledge certificate

### 8.1 `SignedTestPassReceipt@2`

Created only after terminal teardown, the receipt binds:

- execution-key CID and locator CID;
- setup/call/teardown outcomes and timings;
- pytest outcome policy and absence of disqualifying states;
- static/runtime trace roots and completeness receipt;
- runner identity, trust-domain/issuer key ID, nonce, and time/epoch policy;
- captured dependency forest and capability roots;
- schema and policy CIDs.

The receipt is not pass authority until a trusted runner has emitted a canonical
`RunnerPassAttestation@1`. That attestation signs the receipt CID, execution-key
and candidate-context CIDs, setup/call/teardown and trace-completeness roots,
fresh issuance nonce, trust domain, key epoch and policy CID. The only v1
signature suite is Ed25519 over
`b"ipfs-test-pass-attestation/v1\0" + sha256(unsigned_attestation_dag_cbor_bytes)`.
The unsigned envelope has one strict canonical DAG-CBOR representation and a
CIDv1/dag-cbor/sha2-256 identity. Public-key material is exactly
`varint(ed25519-pub) || raw_32_byte_key`; its identifier is the lower-base32
CIDv1/raw/sha2-256 of those bytes. The verifier recomputes every CID, verifies
the signature locally, and starts trust only from an explicitly locally pinned
CIDv1/dag-cbor/sha2-256 `RunnerTrustPolicy@1`, never TOFU, cache presence, or a
certificate-selected key. That policy restricts key usage to pytest-pass
attestation and checks trust domain, key epoch, not-before/not-after, rotation,
and revocation before proof verification. An unknown, expired, revoked,
unsigned, ambiguously encoded, or legacy hash-only receipt runs normally. The
attestation's immutable canonical bytes are stored before proving.

A unique nonce prevents issuance substitution; it is not a consume-on-read
token. Repeated verification of the same immutable certificate is legitimate
warm reuse while the exact execution context, policy CID, trust domain, and key
epoch remain current. Cross-context or cross-policy use, an expired/revoked
epoch, substituted attestation, or nonce reuse for a different issuance is a
replay and must run the test.

### 8.2 `TestPassStatementV5`

The real-ZK statement proves possession of the exact receipt committed by a
separately verified runner attestation and satisfying:

1. the private receipt hashes to the public receipt CID;
2. its execution-key CID equals the public current key;
3. setup, call, and teardown are all pass;
4. no disqualifying outcome bit is set;
5. the trace-completeness and policy identifiers match public admitted values;
6. its signed-attestation, candidate-context and phase-root commitments equal
   the public values; and
7. the proof-system/circuit/key/issuer binding satisfies the approved policy.

Public inputs include statement/circuit/verifying-key CIDs, receipt and
execution-key CIDs, signed-attestation CID, runner public-key CID, policy CID,
outcome and phase-root commitments, issuer commitment, nonce domain and allowed
epoch data. Private inputs contain only the minimum receipt witness. Signature
verification is either circuit-native or a mandatory locally verified
co-condition whose exact attestation CID is a public input; a prover-controlled
boolean that merely claims a signature was checked is never accepted. The
threat model covers replay, substitution, wrong circuit/key, runner or issuer
confusion, proving-key-only forgery, malformed proof, public-input mismatch,
witness leakage, downgrade, rotation/revocation races, and simulated-backend
mislabeling.

### 8.3 Proving and verification

- Verification is local through a pinned real backend and bounded by byte/time
  limits.
- The authenticated-current-tree correction uses the reviewed local Groth16 backend
  for issuance. `IPFS_TEST_PROOF_REUSE_GROTH16_ENDPOINT` is currently a bounded
  diagnostic/configuration capability only, not an implemented remote issuer;
  its absence never blocks launch or test execution. A future authenticated
  endpoint client requires a separately reviewed trust/transport task and is
  not completion evidence for this 77-task board.
- Groth16 or ProveKit issuance is asynchronous/deferred. Any unavailable local
  provider or diagnostic endpoint state records `certificate_deferred` and
  does not change the passed test.
- A locally retained pass receipt can be proved later by an explicit maintenance
  command.
- Simulated proofs have authority `non_attested`; their artifacts may exercise
  serialization and reporting only.
- Existing real certificates remain usable when the proving endpoint is down if
  their local verifier, keys, policy, and current inputs validate.

## 9. Cache and storage model

### 9.1 Layers

1. Process/session memoization for repeated verification within one pytest run.
2. Local immutable CAS for canonical receipts, certificates, traces, and keys.
3. Mutable local locator-to-candidate index, treated only as an optimization.
4. Optional shared/IPFS transport for immutable blobs and index hints.

All authority re-derivation follows the accelerator's trust-aware proof-cache
contract. Shared cache presence, IPFS connectivity, and pinning are optional.

### 9.2 Admission and lookup

On write, canonical bytes are written atomically, fsynced where supported,
renamed into a CID path, read back, and rehashed before index publication. On
read, candidate counts and sizes are bounded; the blob is rehashed, decoded,
schema checked, trust/policy/revocation checked, and proof verified. Corrupt or
hostile entries are quarantined where safe and treated as misses.

The mutable index supports TTL, schema migration, issuer/key revocation,
negative/corruption diagnostics, and fenced single-flight publication. pytest
workers read; one xdist controller coordinates receipt/index writes to prevent
partial or competing updates.

### 9.3 Cache keys and invalidation

Lookup begins with `TestLocatorKey`; authorization requires exact
`TestExecutionKey`. Changes to any bound component invalidate the hit,
including test, import, fixture, hook, parameter, config, dependency lock,
environment, hardware/capability, data, repository forest, policy, tracer,
circuit, verifier key, issuer, or revocation epoch.

## 10. Pytest integration without per-file hardwiring

### 10.1 Shared plugin

`ipfs_accelerate_py.testing.proof_reuse.plugin` owns collection, lookup,
reporting, and pass-receipt lifecycle through pytest hooks:

- `pytest_addoption` and `pytest_configure` define modes, paths, markers, and
  policy without importing optional providers.
- `pytest_collection_modifyitems` computes locators, batches candidate lookup,
  and attaches typed decisions to collected items.
- A verified hit adds the standard skip marker with reason
  `proof-cache-hit:<certificate-cid>` before fixture setup.
- report hooks collect all setup/call/teardown phases and write a receipt only
  when the complete outcome is eligible.
- session/xdist hooks consolidate deferred writes, metrics, diagnostics, and
  optional proving work.

No test path registry is maintained. Every collected item is evaluated from its
node ID, source, fixtures, hooks, parameters, and policy. Markers allow local
opt-out (`proof_reuse_disabled`) and explicit effect adapters, not file lists.

### 10.2 Automatic pickup

The plugin has two complementary registration paths:

1. a `pytest11` packaging entry point for installed/development environments;
2. a tiny root `conftest.py` bootstrap in each repository that conditionally
   imports the plugin, catches only the defined unavailable case, and otherwise
   leaves pytest unchanged.

The bootstrap covers repository-local direct-node invocation even when pytest
entry-point autoload is disabled by the hermetic supervisor. An explicit
`-p ipfs_accelerate_py.testing.proof_reuse.plugin` remains supported. Importing
the plugin performs no network access, daemon startup, cache creation, or ZK
probe.

Each package `__init__.py` exposes only a narrow, lazy proof-reuse bootstrap
facade used by these registration paths; it does not eagerly import pytest,
proof systems, cache clients, or daemon code. Package `__init__.py` cannot be
the sole registration mechanism because pytest is not required to import the
package before collecting an arbitrary test module. The `pytest11` plus root
`conftest.py` composition therefore provides the requested no-test-rewrite
injection while the `__init__.py` facade keeps package-specific wiring lazy and
side-effect free.

### 10.3 Modes

| Mode | Read candidates | Skip | Write receipt | Prove |
| --- | --- | --- | --- | --- |
| `off` | no | no | no | no |
| `shadow` | yes, diagnostic | no | optional local | deferred/off |
| `read` | yes | verified hits | no | no |
| `write` | no | no | yes | deferred per policy |
| `readwrite` | yes | verified hits | yes on executed misses | deferred per policy |

Default rollout is `off`, then `shadow`. `required-audit` is a separate,
explicit CI policy that may make missing mandatory audit capabilities visible;
normal modes always degrade to executing tests.

## 11. Graceful degradation matrix

| Condition | Test action | Diagnostic |
| --- | --- | --- |
| Plugin absent or disabled | Run | `plugin_unavailable` or no PTR output |
| Cache absent/unreachable/read-only | Run | `cache_unavailable` |
| Locator miss | Run | `candidate_missing` |
| Corrupt/oversized/path-escaping entry | Run, quarantine if safe | `candidate_integrity_failed` |
| `multiformats` or CID provider missing | Run | `cid_provider_unavailable` |
| Datasets ZK provider missing/incompatible | Run | `certificate_provider_unavailable` |
| Groth16/ProveKit issuer missing | Run or retain passed receipt for later proving | `certificate_deferred` |
| Local verifier/key/circuit missing | Run | typed verifier/key/circuit reason |
| Simulated proof | Run | `certificate_non_attested` |
| Expired/revoked/wrong issuer/policy | Run | typed trust reason |
| Incomplete or changed trace | Run | typed invalidation reason |
| xdist controller failure | Workers run tests; stop writes | `coordination_unavailable` |
| Unexpected plugin exception | Run and count bounded diagnostic | `internal_error_fail_open_to_run` |

“Fail open” here means open to executing the real test, never open to accepting a
pass. Required audit jobs can separately assert that degradation rates remain
within policy.

## 12. Supervisor validation authority

A proof-backed pytest skip is not an ordinary skip for agent-supervisor
completion. `ProofCachedTestValidation` re-verifies the exact certificate under
the current tree and emits a fresh validation receipt containing:

- task/goal and validation-command identity;
- current commit/tree/recursive gitlinks and dirty-state identity;
- execution-key, receipt, certificate, policy, circuit, and verifier-key CIDs;
- verifier result, authority class, timestamp/epoch, and reason codes.

Only this fresh typed receipt may satisfy a supervisor validation requirement.
Plain pytest skip text, a cache flag, simulated ZK, or a historical status cannot
satisfy completion. This preserves the existing authoritative completion and
merge gates.

## 13. Alignment with agent-supervisor goals

| PTR goal | Supervisor alignment | Conformance |
| --- | --- | --- |
| `PTR-G010` contracts/threat model | `CBP-G025`, `CBP-G200`, `ASI-G300`, `ASI-G310` | Typed evidence, exact statement authority, pinned identities |
| `PTR-G020` execution identity | `ASI-G310`, `VFS-G030` | Canonical content identity and recursive snapshot binding |
| `PTR-G030` traces/eligibility | `ASI-G220`, `ASI-G320` | Software-first AST evidence and bounded semantic context |
| `PTR-G040` cache/store | `ASI-G250`, `CBP-G015`, `CBP-G050` | Tiered CAS, re-derived trust, exact invalidation |
| `PTR-G050` datasets ZK | `CBP-G200`, `ASI-G300` | Real proof-carrying evidence; simulated never authoritative |
| `PTR-G060` pytest plugin | `ASI-G240`, `ASI-G350` | Hermetic validation and exact enforcement |
| `PTR-G070` supervisor authority | `ASI-G240`, `ASI-G300`, `ASI-G350` | Fresh proof-backed validation receipts |
| `PTR-G080` datasets integration | `ASI-G220` | Lazy provider integration without import side effects |
| `PTR-G090` kit integration | `ASI-G250` | Optional immutable transport and capability facts |
| `PTR-G100` adversarial/e2e | `ASI-G240`, `ASI-G280`, `ASI-G360` | Hermetic tests, recovery, rollout safety |
| `PTR-G110` rollout/closeout | `ASI-G260`, `ASI-G290`, `ASI-G360` | Parallel operation, measurable efficiency, staged promotion |
| `PTR-G120` authenticated authority | `CBP-G025`, `CBP-G200`, `ASI-G300` | Signed runner pass attestation, key lifecycle, V5 real-proof binding |
| `PTR-G130` zero-configuration runtime | `ASI-G220`, `ASI-G240`, `ASI-G350` | Safe package bridges and ordinary pytest discovery without test rewrites |
| `PTR-G140` current-tree assurance | `ASI-G240`, `ASI-G280`, `ASI-G360` | Reachable exact pins, replayable evidence, adversarial and subprocess gates |

The PTR heap is a separate program. It does not silently add children to closed
ASI or CBP populations. Cross-references describe conformance; PTR completion
still requires its own current-tree evidence.

## 13.1 Reviewed objective-completion projection (2026-08-03)

The original implementation population is complete (`PTR-000` through
`PTR-102`, 32 of 32), but that is implementation progress rather than goal
authority. The current objective projection correctly reports 12 active goals
and zero authority-verified goals because it has no current bound completion
artifacts and reconciliation is deliberately disabled. Historical task status,
pytest exit status, merge prose, ordinary skips, and synthetic gate fixtures
must not be promoted into goal evidence.

The reviewed audit found the following bounded completion gaps:

- Goal reconciliation selected 54 prose `Acceptance` clauses while the heap
  declares 39 stable typed `Evidence` requirements. Every goal now declares an
  explicit `Acceptance criteria` field equal to those typed requirement IDs;
  the human-readable `Acceptance` field remains explanatory.
- The current-tree gate required `PTR-G110` to be verified even though
  `PTR-G110` itself requires the final-tree gate. The production gate must
  instead verify `PTR-G010` through `PTR-G100`, validate G110 benchmark and
  rollout premises directly, then emit evidence for G110 and the root.
- The final-gate adapter is not yet admissible by the generic objective
  completion contract. It must use an allowed task/scan producer kind, exact
  per-goal objective revisions, explicit freshness, canonical channel proofs,
  strict source policy, and retained replayable provenance.
- The gate claims a supervisor-launch-health requirement without currently
  accepting or checking a current-tree/config-bound launch-health receipt.
- Git tree identity, recursive repository-forest identity, and the
  objective-completion scan identity are distinct domains and must be carried
  and checked independently.
- Production completion artifacts require strict CIDv1/base32/dag-json/
  sha2-256 identity over retained canonical bytes. A nonempty string or a
  private `sha256:` label is not authoritative artifact identity.
- The merge queue contains historical records for 28 tasks. `PTR-000`,
  `PTR-001`, `PTR-011`, and `PTR-041` require genuine operator/review or
  retrospective ancestry plus fresh-validation provenance; `Status:
  completed` alone cannot fill the gap.
- Current host absence of Groth16, ProveKit, snarkjs, IPFS, or a shared cache
  remains non-blocking. It produces typed unavailable evidence and runs tests;
  it never manufactures real-ZK or warm-production authority. A locally
  verifiable reviewed real-certificate fixture or explicitly invoked real
  backend is required for the corresponding closeout criterion.

The reviewed bounded expansion is `PTR-108`, `PTR-109`, `PTR-110`,
`PTR-111`, `PTR-112`, `PTR-120`, `PTR-121`, `PTR-122`, and `PTR-130`.
Autonomous objective and codebase refill remain disabled. Failed completion
gates may describe gaps, but may generate work only after the bounded
producer/reconciliation path is verified and only with stable deduplication and
a reviewed finding limit.

Completion has one writer. At this historical projection revision, the three
implementation lanes continued with goal reconciliation disabled and, after
all 41 then-declared implementation tasks closed, an operator could invoke a
distinct closeout command which:

1. verifies the exact clean integration checkout and complete task population;
2. collects retained current-tree task, validation, analyzer, adversarial,
   benchmark, rollout, capability, policy, and supervisor-health premises;
3. emits atomic state-root evidence and gate artifacts and replays every
   premise by canonical CID;
4. transitions drained goals to provisional without claiming verification;
5. reruns declared validation with proof reuse off and verifies G010-G100;
6. evaluates the final gate without a G110 self-reference, then verifies G110
   and G000 in a third bounded phase;
7. fails closed on any missing, stale, corrupt, contradictory, unavailable, or
   mismatched authority input and retains actionable reason codes; and
8. presents the protected objective lifecycle update for an explicit
   operator-owned commit before normal lane restart.

## 13.2 Reviewed runtime-activation repair (2026-08-03)

The 41-task objective-completion expansion above is implemented, but a runtime
audit found a separate bounded integration gap: the components are present and
their isolated contracts pass, while an ordinary direct-node pytest invocation
cannot yet compose the full authoritative path without test-owned service
injection. The active reviewed projection is therefore `PTR-131` through
`PTR-142`; it does not reopen or rewrite the completed task contracts.

The repair closes these concrete gaps:

- The plugin's safe default is intentionally inert. A non-off mode needs a
  session-scoped factory for repository discovery, forest identity, AST index,
  identity components, cache, local verifier and deferred issuer, while any
  explicitly injected test/service implementation must continue to override
  the default.
- A locator can find candidates but cannot reconstruct what a certificate
  attests. Each successful execution must retain immutable canonical candidate
  context: exact execution key, source/static closure, observed runtime trace,
  forest/environment/policy facts and pass receipt. A mutable locator index
  points to those bytes and remains a hint only.
- The runtime trace is observed during a real setup/call/teardown lifecycle. A
  warm admission must not run the test once to predict whether it can skip.
  Instead, the retained trace specifies the dependency frontier to resolve and
  content-address freshly; unknown or changed facts execute the test. A cold
  pass executes once and records its observed frontier afterward.
- Datasets and accelerator need one versioned byte-exact statement profile.
  CID strings alone are insufficient: retained canonical DAG-JSON bytes must
  decode and rehash as CIDv1/lowercase-base32/dag-json/sha2-256, and the public
  statement must pin receipt, execution/candidate context, policy, circuit,
  verifier key, issuer and epoch.
- Deferred issuance needs a finite public request reconstructed by the
  controller. A worker may send admitted public envelope bytes but never
  witness material or a private request object. Missing packages, native
  artifacts, keys, circuits, endpoints, binaries, caches and transports retain
  the receipt and produce typed `DEFERRED`/`RUN` results.
- Each package needs a narrow lazy bootstrap usable by installed, source-tree
  and direct-node invocations. Package `__init__` modules may expose/inject a
  lightweight public protocol shim, but must not eagerly import the accelerator
  supervisor, datasets ZK stack, kit daemons or installer machinery.
- Content-addressing, verification and optional proving requirements must agree
  across `requirements.txt`, `setup.py` and `pyproject.toml`. First-use lazy
  installation is bounded, allowlisted, fenced, automatic only when package
  auto-install policy permits, and disabled throughout implementation
  validation; it is never necessary for pytest to continue. In datasets, native Groth16
  compilation and NLTK data download are off/lazy by default during setup and
  installation and require explicit opt-in.

The runtime authority sequence is fixed:

1. Compute a stable locator from the collected item and session identity.
2. Resolve a bounded candidate descriptor from the mutable index.
3. Load retained canonical candidate bytes and rehash every CID.
4. Rebuild the current admitted dependency frontier from live source, AST,
   fixtures, hooks, locks, environment, capabilities, policy and external
   snapshots named by the candidate.
5. Require exact comparison plus local verification of a real, exactly bound
   certificate before emitting `proof-cache-hit:<cid>`.
6. Otherwise execute setup/call/teardown exactly once. On terminal pass, retain
   the observed runtime trace and receipt, then request proof issuance lazily.
7. Publish candidate/certificate state atomically from the controller; every
   failure preserves normal pytest behavior.

This ordering prevents both circular runtime-key prediction and duplicate test
execution. Historical AST/runtime traces narrow revalidation work but never
assert that the current test passes. Simulated proof, cache presence, installer
success and repository bootstrap are likewise never authority.

The first repair wave is deliberately repository-parallel: `PTR-131` owns only
accelerator, `PTR-132` only datasets, and `PTR-133` only kit, covering numeric
shards 2, 0 and 1 respectively. The second repository-parallel wave is
`PTR-139`, `PTR-140` and `PTR-141` after the shared composition stabilizes.
`PTR-142` runs sequential zero-false-skip assurance before benchmarking,
refreshes the exact final-tree population from 41 to 53 tasks, and hands the
existing fenced outer closeout controller to the operator. Autonomous gap or
codebase refill remains disabled.

## 13.3 Reviewed production-runtime activation correction (2026-08-03)

A current-tree implementation audit found that the completed repair did not
actually satisfy its production-activation acceptance. This finding preserves
the historical completion provenance of `PTR-138`, `PTR-140`, and `PTR-142`
but supersedes their activation evidence. In particular:

- collection calls the full identity assembler, which requires unavailable
  current runtime evidence before it creates the locator needed to retrieve a
  retained runtime candidate;
- the default revalidator is constructed over the certificate store, not the
  dedicated candidate-context store, has no production current-context
  provider, and is not in the plugin lookup authority sequence;
- ordinary cold execution attaches lifecycle counters but never starts the
  existing runtime dependency tracer, cannot compile the final execution key
  after observation, and does not publish the canonical candidate components;
- the default datasets issuer factory has no real provider, while its public
  request path does not turn a returned proof-bearing certificate into
  controller-publishable issued material;
- the claimed activation e2e manually creates identity/proof artifacts or
  injects services/item attributes, uses a deterministic pseudo-certificate,
  and does not run independent cold and warm pytest subprocesses; and
- dependency reporting is hard-coded source inventory rather than a live typed
  composition/capability result.

The first bounded correction, `PTR-143` through `PTR-149`, would have expanded
the sealed population from 53 to 60. `PTR-143` through `PTR-148` are now
historically complete, but a final review correctly withheld `PTR-149`: the
staged native binary does not advertise statement-profile v4, there is no
reviewed current binary/source/key manifest, and ordinary package setup does not
offer a single explicit setup-facing route through the same lazy provisioner.
Those findings do not rewrite the six completed task records or their canonical
identities. A further controller-path audit found that the lazy issuer could
drop proof-bearing issued material and the deferred/xdist handoff could drop
controller-owned candidate context required by the v4 verifier. The reviewed
correction therefore covers `PTR-143` through `PTR-155`, with the
dependency-ordered `PTR-149` handoff last, and expands the exact sealed
population from 53 to 66:

1. `PTR-143` attaches a stable locator/static collection seed without requiring
   runtime evidence or inventing a final execution key.
2. `PTR-144` supplies a test-pass-specific real Groth16 circuit and lazy local
   provider; it may defer when explicit native artifacts are absent but never
   substitutes an unrelated or simulated proof.
3. `PTR-145` performs locator-only candidate-context lookup, retained-byte
   rehash, live frontier resolution and fresh current identity reconstruction
   before certificate-cache verification.
4. `PTR-146` runs the production tracer around exactly one cold pytest
   setup/call/teardown lifecycle, then builds the final key, receipt and
   canonical candidate publication envelope.
5. `PTR-147` composes those paths as defaults and makes the controller the sole
   issuer/verifier/index publisher; deferred or interrupted issuance leaves no
   skip authority.
6. `PTR-148` uses two independent direct-node pytest subprocesses and one
   persistent disposable cache for accelerator, datasets and kit, with a real
   local Groth16 certificate, body-once evidence, missing-backend fail-open
   behavior and raw measured cold/warm wall time.
7. `PTR-150` exposes explicit setup-facing accelerator provisioning through the
   same bounded lazy installer, while ordinary build/install/import remains
   side-effect free and every provisioning failure remains typed and fail-open.
8. `PTR-151` publishes an auditable v4-capable datasets native backend and
   release manifest binding locked source, binary digest and capability output,
   without generating or shipping a production trusted setup or v4 keys.
9. `PTR-152` makes accelerator issuance and reporting fail closed unless the
   exact reviewed v4 source, binary, capability payload, circuit and key
   identities match, hardens lazy pip execution isolation, and denies every
   structural-only or context-free publication.
10. `PTR-153` preserves complete bounded public proof-bearing issuance material
    across the lazy real issuer without exposing private witness material.
11. `PTR-154` preserves/reconstructs bounded controller-owned receipt,
    candidate and V2 request context through serial and xdist handoffs.
12. `PTR-155` joins both branches, reconstructs the exact datasets V2 binding,
    requires local `VERIFIED`, and performs the sole atomic candidate write.
13. `PTR-149` derives activation reporting from live typed services and
    refreshes the current-tree gate/handoff for the exact 66-task population.

The historical first wave was `PTR-143` and `PTR-144` on shards 2 and 0,
followed by the disjoint `PTR-144`/`PTR-145`/`PTR-146` wave, `PTR-147`, and
`PTR-148`. The current corrective wave is exactly `PTR-150` and `PTR-151` on
numeric shards 0 and 1, owning accelerator and datasets respectively. Their
predicted files and repository claims are disjoint. `PTR-152` on shard 2 joins
both branches and establishes the denial boundary. `PTR-153` and `PTR-154` then
run on shards 0 and 1 with disjoint accelerator files to preserve proof material
and expected context; `PTR-155` on shard 2 joins them into exact local V2
verification. Only then may `PTR-149` run and evaluate the exact 66-task gate.
Historical 53-task, `PTR-142`, pre-v4 60-task, or pre-material 63-task activation
packets are explicitly inadmissible. Absence of operator-provided reviewed v4
keys or a trusted-setup manifest is a truthful activation gap: tests continue to
run and the supervisor continues, but no warm skip or closeout authority is
invented.

## 13.4 Authenticated-receipt and reachable-current-tree repair (2026-08-08)

A final launch audit rejected the 66-task completion packet. Its labels are
retained as historical facts, but they do not establish a runnable or secure
current tree:

- the datasets and kit commits named by the historical outer gitlinks are not
  available from the configured remotes, while the nearest reachable commits
  predate required proof-reuse outputs;
- the completion validator accepted a completed Markdown label without proving
  that every declared output and validation target exists at the exact pinned
  commit or that a task receipt names an ancestor commit;
- the V4 statement proves knowledge of internally consistent receipt bytes but
  does not establish that a trusted pytest runner observed the asserted pass;
  possession of proving material can therefore create a mathematically valid
  proof around a self-asserted pass;
- the warm plugin path filters candidates before the locator-only lookup can
  recover retained current-context material;
- datasets has no package-owned cold-safe proof plugin loader and kit's source
  fallback relies on a pytest hook location that is not guaranteed to load;
  package `__init__.py` injection alone cannot solve either case because pytest
  need not import the package before collection; and
- the prior cross-repository e2e explicitly loaded the plugin or injected
  services, and its skip counts did not independently prove that a forged hit
  avoided or executed the actual test body.

The first v6 repair wave subsequently merged, but an isolated post-merge import
audit found two acceptance failures that in-process tests had not modeled. The
datasets pytest11 bridge raises
`ModuleNotFoundError(name='ipfs_accelerate_py.testing')` when an uninitialized
gitlink leaves a namespace-only empty `ipfs_accelerate_py/` hierarchy. The kit
bridge over-corrects that case by suppressing the same nested error even when an
installed-style regular `ipfs_accelerate_py/__init__.py` exists, hiding a broken
accelerator installation. Revision v7 therefore reopened the existing
repository owners `PTR-161` and `PTR-162`.

The stopped v7 lanes then exposed a separate supervisor failure. Real
subprocess validation failures were present in implementation logs, but nested
full reviews and addenda recursively exceeded the diagnostic-size limit. The
normalizer raised, the outer catcher mislabeled the attempt as
`implementation_setup`, and the retry capsule reported validation `not_run`.
That destroyed the actionable counterexample and caused an exact repeat.
Revision v8 adds one reviewed control-plane owner, `PTR-170`, and makes both
reopened bootstrap tasks depend on it; it does not broaden proof or skip
authority.

The bounded repair is `PTR-160` through `PTR-170`, taking the reviewed
population to 77 tasks. It does not pretend that the old unreachable commits
are valid launch pins. The clean integration branch instead starts from the
nearest fetchable datasets and kit baselines, preserves the compatible
accelerator supervisor commit, and makes reconstruction of every missing
historical output explicit work with current evidence:

1. `PTR-160` defines signed runner pass-attestation, trust-policy, public-key
   multicodec CID, nonce, epoch, rotation and revocation contracts.
2. `PTR-170` makes failed-validation retry evidence deterministic and at most
   16 KiB without raising. It preserves attempted/failed state, return code,
   reason, receipt, failed command/test/path/exception and a bounded failure
   head, deduplicates repeated review bodies, and records hash-marked
   truncation instead of replacing the failure with a synthetic setup error.
3. `PTR-161` restores the datasets-owned missing outputs and supplies a
   `pytest11`/source bootstrap that is inert when accelerator or ZK extras are
   absent. Isolated installed and source direct-node subprocesses must also
   prove that a namespace-only empty accelerator/gitlink hierarchy is optional
   absence and still executes the ordinary test body. This is the versioned
   `DatasetsProofReuseBootstrap@3` boundary; historical V2 evidence is stale.
4. `PTR-162` restores the kit-owned immutable stores and supplies the same
   cold-safe bootstrap and strict-CID transport boundary. Its isolated
   subprocess matrix must distinguish a namespace-only empty hierarchy, which
   is a safe no-op, from a regular accelerator package with a missing nested
   testing/plugin hierarchy, whose `ModuleNotFoundError` remains visible. This
   is `KitProofReuseBootstrap@3`; historical V2 evidence is stale.

   A post-merge contradiction on 2026-08-08 invalidated PTR-162 attempt 1:
   its 30-test receipt omitted the explicit recursive-input counterexample, and
   a roughly 4 KiB, 2,000-level canonical JSON array still raised
   `RecursionError` through the pure-Python encoder path. PTR-162 is therefore
   reopened under a new canonical task identity. The merged attempt remains
   provenance only; downstream joins must wait for a checked-in deep-input
   regression and a fresh authoritative completion receipt.

   A second completion was also contradicted before any downstream join ran.
   It repaired deep JSON but left lone-surrogate CIDs non-total, omitted the
   required deep candidate-put regression, and allowed an ambient accelerator
   import to mask suppression of a non-accelerator transitive error. The third
   identity therefore places those three counterexamples directly in the
   declared validation command as an isolated, mandatory gate.
5. `PTR-163` implements `TestPassStatementV5`, binds the real Groth16 proof to
   the signed attestation CID and requires local signature/trust verification.
6. `PTR-164` fixes locator-only warm lookup and makes the controller the sole
   signed-receipt/candidate publication authority.
7. `PTR-165` validates completed-task outputs, validation targets, exact
   gitlinks, commit ancestry and merge receipts instead of trusting board text.
8. `PTR-166` uses the real backend to prove that unsigned, wrongly signed,
   stale, revoked and proving-key-only forged receipts cannot authorize a skip.
9. `PTR-167` replays only receipt-identified historical blobs/commits, checks
   retained tree and blob digests, publishes reachable commits, and reopens any
   material that cannot be reconstructed rather than waiving it.
10. `PTR-168` installs or source-loads all three packages and runs independent
   ordinary cold, warm and forced-replay pytest processes without `-p`, service
   injection, tracer monkeypatches or simulated proof authority. A persistent
   body oracle establishes zero false skips under AST, fixture, conftest,
   parameter, dependency, environment and policy mutations.
11. `PTR-169` joins the exact reachable 77-task inventory, authenticated
    adversarial evidence, genuine three-repository e2e and measured subprocess
    benchmark into a fresh operator handoff. The old 66-task packet is stale.

The original v6 first wave was `PTR-160`, `PTR-161` and `PTR-162`, on three
numeric shards and three distinct repository claims. `PTR-160` remains
completed. The fresh v8 claimable set is exactly `PTR-170` on numeric shard 2.
After its bounded retry-evidence repair merges, reopened `PTR-161` and
`PTR-162` become the parallel frontier on numeric shards 2 and 0 with disjoint
datasets and kit ownership.
`PTR-163` and `PTR-165` remain waiting until their exact bootstrap dependencies
merge, after which datasets V5 work and the outer audit-tool work run in
parallel on distinct resources. `PTR-164` then consumes the exact merged V5
provider and release manifest to implement accelerator runtime composition. The
authority join `PTR-166`, verified replay/gitlink publication `PTR-167`, genuine
e2e `PTR-168`, and handoff `PTR-169` are deliberately ordered because each
consumes the preceding trust boundary. Completing `PTR-165` means its live audit
accurately reports the expected Wave-B gaps; `PTR-167` is the first task allowed
to require that audit to be globally green. All implementation validation
forces proof reuse off so this feature cannot certify itself. Missing optional
proof/cache/IPFS capabilities remain typed `RUN` or `DEFERRED`, never startup
failures or synthetic authority.

## 14. Parallel implementation program

The machine board is
`implementation_plan/docs/46-proof-backed-test-reuse.todo.md`. Three strict
numeric task shards run in isolated ephemeral worktrees with one serialized
merge queue. Every task declares exact files, dependencies, resource class,
submodule scope, validation, and acceptance. Planning/control files are
protected from implementation agents.

### Execution waves

| Wave | Tasks | Parallel intent |
| --- | --- | --- |
| 0 | `PTR-000` | Plan/control seal, completed before launch |
| 1 | `PTR-001`, `PTR-002`, `PTR-003` | Contracts, threat model, capability probes on all three shards |
| 2 | `PTR-010`, `PTR-011`, `PTR-040`, `PTR-050` | Identity, datasets statement, plugin shell where dependencies permit |
| 3 | `PTR-012`, `PTR-020`, `PTR-021`, `PTR-030`, `PTR-041` | CID vectors, traces, cache, real certificate binding |
| 4 | `PTR-022`, `PTR-031`, `PTR-042`, `PTR-043` | Eligibility, storage/single-flight, deferred issuance, lazy adapter |
| 5 | `PTR-051`, `PTR-052` then `PTR-053` | Lookup/receipt paths then xdist/reporting integration |
| 6 | `PTR-060`, `PTR-080` then `PTR-061`, `PTR-070`, `PTR-081` | Supervisor authority and three repository bootstraps |
| 7 | `PTR-090`, then `PTR-091`, `PTR-092`, `PTR-093` | Degradation, invalidation, security/concurrency, cross-repo e2e |
| 8 | `PTR-100`, `PTR-101`, `PTR-102` | Benchmark, staged rollout, current-tree gate |
| 9 | `PTR-108`, `PTR-109`, `PTR-110` | Datasets real-ZK assurance, kit canonical-byte transport, and accelerator task provenance own three distinct repository claims and run concurrently |
| 10 | `PTR-111`, `PTR-112` | Accelerator goal/analyzer evidence and semantic artifact contracts adapt the repository-native protocols; the conservative shared accelerator claim serializes them safely |
| 11 | `PTR-120`, `PTR-121`, `PTR-122` | Outer single-writer reconciliation runs beside one accelerator artifact/gate task while the shared accelerator claim serializes the other |
| 12 | `PTR-130` | Hermetic closeout proof and operator handoff; the real current-tree closeout is invoked only after this task is completed |
| 13 | `PTR-131`, `PTR-132`, `PTR-133` | Runtime contracts, datasets statement/setup safety, and kit candidate transport claim accelerator, datasets, and kit independently on all three shards |
| 14 | `PTR-134`, `PTR-135`, `PTR-137` | Lazy identity, immutable candidate context, and typed deferred issuance proceed when repository claims permit; shared accelerator changes serialize |
| 15 | `PTR-136` | Fresh current-context reconstruction joins the identity and candidate-store contracts |
| 16 | `PTR-138` | The plugin composes lookup, revalidation, local verification, terminal pass capture, controller issuance, and xdist fencing |
| 17 | `PTR-139`, `PTR-140`, `PTR-141` | Accelerator, datasets, and kit add direct-node bootstrap, manifest parity, scoped imports, and bounded lazy installers concurrently |
| 18 | `PTR-142` | Cross-repository activation assurance, benchmark, exact 53-task gate refresh, and operator handoff |
| 19 | `PTR-143`, `PTR-144` | Accelerator locator-first collection and datasets real Groth16 test-pass issuance start independently on two numeric shards |
| 20 | `PTR-145`, `PTR-146` (while `PTR-144` may continue) | Disjoint accelerator warm revalidation and cold trace/candidate publication branches can fill the remaining two shards |
| 21 | `PTR-147` | Default service/plugin/controller composition joins real issuance, warm revalidation and cold publication |
| 22 | `PTR-148` | Genuine no-injection two-process activation and measured subprocess savings across all three repositories |
| 23 | `PTR-150`, `PTR-151` | Explicit accelerator setup-facing lazy provisioning and an auditable datasets v4 native release start in parallel on distinct resources |
| 24 | `PTR-152` | Join both branches with fail-closed current-v4 source, binary, capability, circuit and key provenance plus truthful runtime reporting |
| 25 | `PTR-153`, `PTR-154` | Preserve proof-bearing issued material and controller-owned V2 context in parallel on disjoint accelerator files and numeric shards |
| 26 | `PTR-155` | Join exact datasets V2 local verification with the sole atomic candidate publication path |
| 27 | `PTR-149` | Live reporting, exact 66-task authority gate, corrected handoff and explicit operator closeout premise |
| 28 | `PTR-170` | V8 first repairs bounded actionable retry evidence on shard 2 so subsequent failed validations cannot be normalized into synthetic setup failures |
| 29 | `PTR-161`, `PTR-162` | Reopened datasets and kit isolated-bootstrap contracts run concurrently on shards 2 and 0 only after PTR-170 merges; PTR-160 signed-runner work remains complete |
| 30 | `PTR-163`, `PTR-165` | V5 native real-proof binding and the outer evidence-audit tool run independently on datasets and the outer tree |
| 31 | `PTR-164` | Accelerator runtime composition pins and consumes the exact merged V5 provider/capability/release identities |
| 32 | `PTR-166` | Real-backend authenticity join rejects proving-key-only, signature, key-lifecycle and downgrade forgeries with zero skipped/xfail assurance cases |
| 33 | `PTR-167` | Receipt-verified history replay publishes reachable exact commits/gitlinks and requires green current output ancestry |
| 34 | `PTR-168` | Genuine installed/source three-repository cold, warm, forced-replay and mutation-oracle e2e |
| 35 | `PTR-169` | Exact 77-task authenticated current-tree candidate, benchmark and reconciler update; authority requires a post-merge outer rerun and rejects v7/76-task packets |

Tasks that change the same git submodule remain subject to canonical claims and
the shared serial merge queue. No concurrency override bypasses a gitlink or
predicted-file conflict.

The first completion wave is repository-parallel by construction rather than by
override: `PTR-108` claims only datasets, `PTR-109` only kit, and `PTR-110`
only accelerator. Datasets and kit expose lazy injected protocols and never
import the accelerator supervisor; accelerator remains the sole interpreter of
goal evidence and completion authority.

The active runtime-repair waves preserve the same rule. `PTR-131`, `PTR-132`
and `PTR-133`, then `PTR-139`, `PTR-140` and `PTR-141`, own one distinct
repository each. Numeric shards determine canonical provider roles and the
shared merge queue serializes gitlink publication; predicted-file conflicts
remain dependency ordered and cannot be overridden.

The historical production-activation wave began with `PTR-143` on accelerator
and `PTR-144` on datasets, then used the dependency-ordered
`PTR-144`/`PTR-145`/`PTR-146` parallel set before `PTR-147` and `PTR-148`.
The current corrective wave again uses two independent repositories rather than
inventing unrelated kit work: `PTR-150` owns accelerator on shard 0 and
`PTR-151` owns datasets on shard 1. `PTR-152` joins them on accelerator only
after both merge. `PTR-153` and `PTR-154` then occupy shards 0 and 1 with
disjoint predicted files; the shared merge queue serializes their accelerator
gitlink publication before shard-2 `PTR-155` joins them. `PTR-149` remains last.
That order is retained as historical provenance. The v6 correction started
with `PTR-160`, `PTR-161` and `PTR-162`; v8 first runs `PTR-170`, then resumes
reopened `PTR-161` and `PTR-162` in parallel. Their merge admits the disjoint
`PTR-163`/`PTR-165` wave, followed by
the dependency-ordered `PTR-164` runtime join. Authenticity, replay, genuine e2e
and closeout form the ordered `PTR-166` through `PTR-169` joins. Numeric shards
preserve canonical provider identities; runtime execution remains Grok 4.5
first when ready, with automatic Codex `gpt-5.6-terra` high fallback when Grok
is unavailable, unauthenticated, or quota-exhausted before any worktree side
effect.

## 15. Validation strategy

### Unit and contract tests

- Canonical JSON/CID known vectors, finite-value rejection, and cross-module
  digest reproduction.
- Locator/execution-key stability and change sensitivity.
- Fixture/hook/config/parameter/lock/environment/capability identity.
- Static and runtime trace completeness, overflow, and unknown frontiers.
- Pass outcome lifecycle and disqualifying pytest states.
- Real/simulated/unavailable proof authority distinctions.
- Immutable CAS, mutable index, atomic write, corruption, revocation, and TTL.
- Plugin cold import and every degradation reason mapping to `RUN`.

### Mutation and adversarial population

Mutate test bodies, imports, indirect dependencies, fixtures, conftests, hooks,
parameters, locks, installed versions, environment, hardware facts, data files,
dynamic imports, dirty overlays, policies, circuits, verifier keys, and issuers.
The required invariant is zero stale authoritative skips.

Security cases cover forged proof/receipt/CID, oversized blobs, private-data
leakage, symlink/path escape, partial writes, index poisoning, worker crashes,
restart recovery, parallel publishers, rollback/replay, and revocation races.

### Cross-repository e2e

For a direct node in each repository:

1. empty cache causes execution;
2. complete pass creates an immutable receipt;
3. an available real backend creates a certificate, or a deterministic real
   verifier fixture supplies one without network;
4. the unchanged warm run verifies and reports one proof-backed skip;
5. a relevant mutation forces execution;
6. `off`, coverage, and missing-provider modes execute;
7. autoload enabled and disabled repository bootstraps behave consistently;
8. xdist produces no duplicate or partial authority records; and
9. isolated installed and source direct-node subprocesses treat an empty
   namespace/gitlink accelerator hierarchy as optional absence but expose a
   missing nested hierarchy or transitive dependency from a regular accelerator
   package.

### Performance gates

- Warm verification is materially cheaper than the eligible test execution.
- Target at least 80% reuse for the explicitly eligible warm fixture population.
- Collection/lookup overhead is bounded when no candidate exists.
- The false-admission count is exactly zero; any observed false skip rolls the
  feature back to shadow/off.

## 16. Rollout

1. Land contracts, identity, traces, stores, provider adapters, and tests with
   mode `off`.
2. Enable `shadow` in selected CI jobs; compare predicted hits with actual
   executions and collect reason-code/latency metrics.
3. Require a zero-false-admission mutation population and healthy degradation
   matrix.
4. Enable `read` for explicit pure, repository-forest-bound tests with forced
   random re-execution sampling.
5. Enable opt-in `readwrite` for controlled CI issuers and local cache roots.
6. Consider eligible-default reuse only after the benchmark and current-tree
   gate pass across all three repositories.
7. Automatically revert to shadow/off on any false admission, verifier-policy
   contradiction, corruption spike, stale-key event, or unexplained mismatch.

Metrics include collected/eligible/lookup/hit/verified/skip/run counts, reason
codes, verify and execution latency, bytes read/written, deferred proofs,
quarantine/revocation events, forced rerun mismatches, and saved wall time. No
test names, paths, parameters, or output bodies are exported as telemetry unless
explicitly permitted.

## 17. Operational launch contract

- Launch only from the clean isolated worktree on
  `agent/proof-backed-test-reuse`.
- Keep state, worktrees, logs, projection artifacts, and merge queue outside the
  repository under the XDG state root.
- Initialize exactly the three outer submodules in worker worktrees.
- Use three strict deterministic shards and a shared serial merge queue.
- Disable objective/codebase refill initially because the reviewed board is
  comprehensive. The historical nine-task completion expansion and historical
  twelve-task runtime-activation repair, plus the active thirteen-task
  production-activation correction, are immutable 2026-08-03 projections. The
  active eleven-task authenticated-current-tree repair is the bounded 2026-08-08
  projection; none enables autonomous refill.
- Use the fresh `proof-backed-test-reuse-v8` state directory so the stopped v7
  launch, its repeated non-actionable PTR-162 retry state, superseded
  PTR-161/PTR-162 completion state, stale earlier lane
  state, old health failures and historical generated-output checks cannot be
  mistaken for this run.
- Run the native board validator, objective projection, a non-implementing
  daemon readiness pass, and reconciliation-only lane preflights before start.
- Require live supervisor and managed-daemon PIDs, fresh status/task state, no
  structural blocked tasks, and at least one globally selectable or active task.
- Groth16, ProveKit, cache, and IPFS are optional capability facts and never
  startup gates.
- Keep all worker-lane goal reconciliation disabled. Only the outer controller's
  explicit, fenced closeout operation may write lifecycle state.
- Keep ordinary `project`, `preflight`, and `start` report-only with respect to
  the protected objective heap.

The committed controller is `scripts/proof_backed_test_reuse_supervisor.py` and
the profile is `config/proof_backed_test_reuse_supervisor.json`.

## 18. Definition of done

- All PTR tasks and child goals have current authoritative completion evidence.
- The objective closeout replays canonical premise bytes, distinguishes Git,
  forest, and objective-completion identities, checks a fresh supervisor-health
  receipt, and reaches verified state through staged legal transitions rather
  than task labels.
- Direct-node and suite invocation automatically discover the plugin in all
  three repositories without a test-file registry.
- Package roots expose only narrow lazy bootstrap/provider protocols; scoped
  imports avoid pulling accelerator, datasets-ZK, kit-daemon or installer
  dependency trees until a non-off mode requests them.
- Content-addressing/ZK dependencies agree across requirements, setup and
  project metadata; bounded opt-in lazy installers degrade to typed
  unavailable results, and datasets setup performs no native Groth16 build or
  NLTK download by default.
- A warm decision reloads and rehashes immutable candidate-context bytes,
  rebuilds current dependency facts, and never duplicates the test call merely
  to predict its runtime trace.
- Every authoritative skip is backed by an exact current execution key, trusted
  signed runner pass attestation, locally verified real certificate, current
  signer trust/rotation/revocation state, and fresh supervisor receipt.
- Every completed task has present declared outputs and validation targets at
  fetchable exact gitlinks, plus replayable task/merge evidence whose commit is
  an ancestor of the current pin; historical labels alone have no authority.
- The certificate policy and verifier bind content identities computed from the
  exact reviewed circuit and activated verifying-key bytes; label-derived,
  certificate-selected, stale, or provenance-mismatched artifact identities
  remain non-authoritative and execute/defer.
- Every missing or faulty optional dependency executes the test normally.
- Simulated proofs, legacy pseudo-CIDs, ordinary skips, xfails, and incomplete
  traces never satisfy skip or supervisor completion authority.
- Mutation, degradation, security, concurrency, and cross-repository e2e
  populations pass with proof reuse forced off for their own validation.
- Shadow and warm benchmarks meet the admitted threshold with zero false skips.
- The authoritative activation benchmark contains raw timings from genuine
  cold and warm pytest subprocesses; injected in-memory orchestration,
  deterministic pseudo-certificates, and synthetic timing constants are not
  closeout evidence.
- Ordinary installed and source-tree pytest invocations in accelerator,
  datasets and kit discover the package-owned bridge without `-p` or test
  rewrites; cold, warm and forced replay agree with an independent body oracle.
- A real-backend proof around an unsigned, self-signed, wrongly keyed, stale or
  revoked receipt never skips, even when the prover possesses valid proving
  material and the raw proof equations verify.
- Operations can inspect, start, and stop isolated lanes without modifying the
  original dirty workspace or colliding with other supervisor programs.
