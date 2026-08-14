# Proof-Carrying Context Engine v0.1 Improvement and Execution Plan

**Status:** active execution plan
**Parent objective:** `PCCE-G000`
**Board namespace:** `proof-carrying-context-engine-v0.1`
**Human-readable board:** `docs/architecture/proof_carrying_context_engine_v0_1.todo.md`
**Objective heap:** `docs/architecture/proof_carrying_context_engine_v0_1.objectives.md`
**Machine projections:** `artifacts/proof_carrying_context_engine/control/`
**Control base:** `lift_coding@b6f40c05e0884867eb8557f8882cd25cb760ca2f`

## Outcome

Deliver and qualify version `0.1` of an installable, provider-neutral
`ProofCarryingContextEngine`. The product is a governed sidecar for an existing
coding agent, not a new coding agent. It must scan an ordinary Python Git
repository, construct minimal proof-aware context, route or accept a patch,
apply it in an isolated worktree, incrementally verify and assure it, seal the
result, and return stable human and machine reports. Production and supervised
paths fail closed on stale, simulated, unavailable, forged, or insufficient
evidence.

The initial qualification target is `internal_alpha`. No higher level is
assigned without current-tree installation, benchmark, security, and
longitudinal evidence.

## Exact starting identities

The visible shared checkouts are intentionally not used for mutation: the
datasets and accelerator checkouts contain unrelated dirty work and are older
than the superproject gitlinks. The supervisor starts from a dedicated clean
control worktree and these exact recorded pins:

| Repository | Root-relative path | Initial commit |
| --- | --- | --- |
| `endomorphosis/ipfs_datasets_py` | `external/ipfs_datasets` | `ac82107e246b30e35a2bbdcf75e01370d22350c6` |
| `endomorphosis/ipfs_kit_py` | `external/ipfs_kit` | `6196017ca3df016c7159dce43af60f2a0d96a9ae` |
| `endomorphosis/ipfs_accelerate_py` | `external/ipfs_accelerate` | `485edc0871c55b0e2ef21d83bece9fa12c2c8d84` |
| `endomorphosis/Mcp-Plus-Plus` | `Mcp-Plus-Plus` | `6965f89f066769f3b3ac7b5f753b1a0044562570` |

Each task receipt must bind the then-current superproject commit/tree, recursive
gitlinks, dirty overlay, objective and canonical task identities, policy,
lease, fencing epoch, worktree, validations, and final artifact identity.

### Supervisor bootstrap compatibility gate

Pinned-import preflight found that the accelerator pin reintroduced
supervisor-only `canonical_task_key` and `canonical_task_cid` fields inside a
strict datasets-owned Profile-G v1 TaskSpec. It also overwrote the canonical
unlimited-attempt translation and failed to propagate a finite lane attempt
ceiling into immutable task specs. These faults made lease admission invalid
at the exact repository pins even though ambient editable-package tests passed.

Before product-task admission, the isolated control repair
`ipfs_accelerate_py@c8e953be8696d47376442c73739eea14fad83113` removed the two
extension fields, restored `0 -> 100` only at the Profile-G boundary, preserved
finite limits, and propagated the configured three-attempt ceiling. The change
is limited to lease coordination, bundle planning, and focused tests. Exact-pin
verification passed 127 lease, worktree, resource, and attempt-boundary tests.
The initial inventory identity remains `485edc087...`; the launch gitlink is the
descendant bootstrap commit and is recorded separately in the control receipt.

## Evidence-backed preliminary inventory

This inventory is a launch input, not the contract freeze. `PCCE-001` through
`PCCE-005` must reproduce it from code, imports, tests, board state, and exact
Git objects before any candidate is adopted.

| Reported subsystem | Current evidence | Preliminary disposition |
| --- | --- | --- |
| Incremental Semantic Index | `external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/semantic_index/index.py::IncrementalSemanticIndex` with package tests | Present at the exact datasets pin; candidate datasets authority. |
| Semantic Capsule Compiler | `external/ipfs_datasets/ipfs_datasets_py/logic/software_contracts/semantic_state/capsules.py::compile_semantic_capsule(s)` | Present at the exact datasets pin; function API rather than the reported class name. |
| ContextPack Builder | `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_state/context_pack.py::ContextPacker` and datasets `ContextPackView` | Functional candidate exists, but production construction is accelerator-owned and violates the requested boundary. Migration/adapter work is mandatory. |
| Verification Receipt Cache | `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/receipt_cache.py::VerificationReceiptCache` | Present; persistent authority must be delegated to a kit-backed adapter. |
| Incremental Verification Planner | `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/planner.py::IncrementalVerificationPlanner` | Present at the exact accelerator pin. |
| Model Route Planner | `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/verification/model_route.py::ModelRoutePlanner` | Present; selects capability tier, not provider credentials or mutation authority. |
| Semantic Compression Governor | `external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/semantic_governor/governor.py::SemanticCompressionGovernor` | Present at the exact accelerator pin; depends on datasets/kit adapters. |
| Verified GUI Optimizer | candidate code under a separate `feature/verified-gui-optimizer` superproject worktree | Not in the pinned baseline; unpublished/dirty candidate state is non-authoritative. It is inventory input only and is not a v0.1 product requirement unless a narrow reusable contract is proven necessary. |
| Incremental Proof Sealer | local candidate branch `agent/incremental-proof-sealer-v1@e73e6fa44c7936b07ca526a879afcd45322835e8` with IPS-044 and IPS-047 through IPS-056 still open | WIP, not canonical. Its referenced datasets/kit objects require exact acquisition; convergence and current-tree tests are required before use. |
| Adversarial Assurance Engine | local candidate branch `agent/adversarial-assurance-engine-v1@3c2a0b0036329a3e4bb0144e8ca1442458ec74f8` with open runtime/release work | WIP, not canonical. Reuse only after bounded migration and acceptance evidence. |
| Self-Hosting Qualification Harness | candidate line `agent/self-hosting-qualification-v1@17e19a8e5db327a18dc9437a8de2be299599ecf2` plus dirty plan history | Prerequisite observers and plans exist; no completed canonical harness facade is assumed. |

The inventory must also identify duplicate schemas, pseudo-CIDs, simulated
success paths, recursive submodules, editable sibling dependencies, mutable
branch dependencies, circular imports, and package metadata gaps. Path presence,
historical green boards, branch names, and documentation claims are not
completion evidence.

The preliminary WIP audit found that the sealer and assurance branches bind
four nested candidate commits not present in the clean pinned object stores:
datasets `1480ea2b...` and kit `da3947f6...` for sealing, plus datasets
`2334135a...` and kit `523fc9b3...` for assurance. PCCE-017 through
PCCE-019 and PCCE-013 must acquire exact immutable objects before adopting
code. If an object is unpublished or unreachable, the owning task records a
typed external-prerequisite block; agents may not reconstruct proof or
assurance implementations from plans.

## Canonical ownership target

| Repository | v0.1 authority |
| --- | --- |
| `ipfs_datasets_py` | semantic repository state, capsules, ContextPacks and sufficiency views, invalidation, task/benchmark specifications, semantic outcome comparison |
| `ipfs_kit_py` | immutable artifacts, state/receipt/proof-forest persistence, CAS roots, WAL transitions, local hermetic storage and optional IPFS transport |
| `ipfs_accelerate_py` | engine facade, lifecycle orchestration, adapters, worktrees, routing, verification/proof scheduling, cancellation/timeouts/admission/retry, shadow and assurance campaigns |
| `Mcp-Plus-Plus` | shared invocation/receipt schemas, canonical vectors, and narrow interoperability contracts only |

Compatibility adapters may remain in a consumer package, but semantic or
persistence authority may not be silently duplicated there. MCP++ never owns
production runtime state or execution authority.

## Frozen lifecycle

Every accepted patch follows this sequence:

```text
identify operator and bind policy
  -> resolve exact repository/task state
  -> scan semantic state
  -> create invalidation plan and ContextPack
  -> evaluate context sufficiency
  -> select permitted model tier
  -> invoke a bounded adapter or accept an external patch
  -> validate declared scope
  -> apply in an isolated disposable worktree
  -> rescan changed state
  -> incrementally verify static checks, tests, and proofs
  -> expand context/escalate when required
  -> run assurance policy
  -> create an incremental seal
  -> accept, reject, or require human review
```

No adapter may approve its own patch or bypass a stage. Simulation and replay
records remain permanently labelled and cannot be promoted into production
evidence.

## Execution graph

```text
PCCE-000 board seal
  -> PCCE-001..004 repository inventories (parallel)
  -> PCCE-005 ownership/canonical reconciliation
  -> PCCE-006 shared contract freeze
  -> PCCE-007..010 parity and blocker repairs
  -> {PCCE-012 datasets ContextPack ownership ||
      PCCE-017 datasets proof contracts ||
      PCCE-018 datasets assurance contracts}
  -> {PCCE-013 kit proof/receipt store || PCCE-019 kit assurance store}
  -> {PCCE-014 public proof-sealer convergence ||
      PCCE-016 selected-test soundness repair}
  -> PCCE-015 assurance-runtime convergence
  -> PCCE-011 Epic A acceptance gate
  -> PCCE-020 runtime contracts
  -> PCCE-021..023 semantic, persistence, lifecycle slices (parallel)
  -> PCCE-024 facade composition
  -> PCCE-025 governed-runtime gate
  -> {PCCE-030..035 adapters || PCCE-040..044 CLI}
  -> {PCCE-045 self-hosting harness || PCCE-050/PCCE-051 providers ||
      PCCE-055 example || PCCE-057 MCP++ contract artifact}
  -> PCCE-052 runtime profiles
  -> PCCE-053 locks, hashes, SBOM, and environment
  -> PCCE-054 clean-install/container verification
  -> PCCE-056 clean-install gate
  -> {PCCE-060..066 benchmark setup || PCCE-070..075 security}
  -> PCCE-079 bounded self-hosting qualification
  -> PCCE-067..068 benchmark execution and gate
  -> PCCE-076 security gate
  -> PCCE-080 CI
  -> PCCE-081 release candidate
  -> PCCE-082 qualification
  -> PCCE-083 go/no-go report
```

Concurrency is admitted only when declared paths do not overlap and frozen
contracts are ready. Shared package exports, metadata, lock files, root schemas,
and release manifests have serialized integration tasks.

## Contract freeze

`PCCE-006` freezes versioned definitions for repository state, semantic
capsule, ContextPack, TaskSpecification, coding-agent invocation, patch
proposal, invalidation plan, verification plan, model-route decision,
execution receipt, proof unit, incremental seal, qualification result,
error/status taxonomies, canonicalization, and CID behavior. Any later
incompatible change requires a new schema version,
migration, vectors, compatibility-matrix update, and invalidation of every
dependent task receipt.

## Modes and failure semantics

The closed modes are `production`, `supervised`, `evaluation`, and
`simulation`. Production and supervised runs reject mocks, simulated proof
success, unavailable-as-passed checks, stale capsules/receipts, pseudo-CIDs,
missing authority, and accepted unsealed patches.

The minimum terminal/status vocabulary is `succeeded`, `rejected`,
`verification_failed`, `proof_failed`, `assurance_failed`,
`context_insufficient`, `model_escalation_required`, `human_review_required`,
`unavailable`, `timeout`, `cancelled`, `invalid`, `stale`, `simulated`,
`infrastructure_failure`, `partial_effect`, and `repair_required`.

## Installation and benchmark gates

Core installation must not pull every model, browser, prover, or storage
backend. Immutable datasets, kit, accelerator, and data-only MCP++ contract
artifacts and hashes are required for core, verification, Codex adapter, an
already-supported local adapter, and full evaluation profiles. The MCP++
artifact carries schemas/vectors through package resources and has no runtime
authority. Editable paths, specially placed siblings, recursive submodule
requirements, source-path injection, and mutable branch dependencies are
release blockers.

Benchmark thresholds are frozen before eligible evaluation begins:

- median context reduction at least 50%; target 60%;
- total cost reduction per accepted patch at least 30%; target 50%;
- accepted-patch quality within the declared noninferiority margin;
- zero accepted critical regressions;
- zero stale capsule, stale proof, or simulated-success acceptance;
- zero selected-test false negatives in controlled fixtures;
- frontier escalation at most 25% on routine localized tasks; target 20%.

Missing live-provider, hidden-test, cost, or longitudinal evidence is reported
as unavailable, never inferred from a smoke run. A failed threshold produces a
documented no-go or a lower qualification level.

## Supervisor policy

The control files in this program are protected operator inputs. Workers use
isolated worktrees, exact gitlinks, shared lease/fence and merge-queue
namespaces, bounded attempts, and task-specific mutation scopes. Model output
is a proposal. Validation and merge authority remain independent.

Initial execution uses two lanes because other supervisor programs already
consume provider and repository resources. Admission may rise to three only
after fresh CPU, memory, disk, model-capacity, and conflict evidence. Missing
telemetry grants no extra capacity.

Monitoring classifies each lane from heartbeat, process identity, current
task, phase, log progress, lease/fence state, merge queue, retry counters, and
task receipts. Recovery is bounded:

1. Reconcile stale projections and already-merged worktrees.
2. Restart a dead or stale owned process with the same identity binding.
3. Reclaim only expired leases whose owner is proven dead.
4. Expand task context or minimize a failing counterexample after repeat failure.
5. Escalate the model route only when policy permits.
6. Mark an external prerequisite blocked or require human review after the
   configured retry bound; never spin indefinitely or conceal attempts.

No automatic protected-branch merge, credential propagation, broad cleanup,
or deletion of evidence state is authorized.

## Final qualification report

`PCCE-083` must publish the parent objective identity, final board and DAG,
all terminal task dispositions, changed repositories/files, ownership and
public APIs, CLI/install examples, test and CI evidence, benchmark context and
cost reductions, route distribution, verification reuse, assurance/security
results, release artifacts, qualification level, blockers, rollback, and an
explicit `proceed`, `proceed with restrictions`, or `no-go` recommendation.

The evidence-bounded claim is:

> The completed semantic-compression, incremental verification, model-routing,
> assurance, and proof-sealing subsystems were integrated into one installable
> Proof-Carrying Context Engine. The engine was evaluated against the frozen
> task corpus and qualified only to the level supported by the current
> installation, quality, security, context-reduction, cost, and verification
> evidence.
