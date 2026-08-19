# Proof-Carrying Control Plane: Formal Assurance Program

**Program:** Formal Assurance Control Plane (`FACP-`)
**Date:** 2026-08-19
**Execution branch:** `agent/formal-assurance-control-plane`
**Board namespace:** `formal-assurance-control-plane-v1`
**Primary release:** `formal-claim-algebra-v1`
**Status:** reviewed implementation program; supervisor-controlled execution

## 1. Outcome

Build one small proof-carrying control plane that defines and enforces what the
portfolio may claim, authorize, execute, observe, reuse, certify, and release.
The kernel will make invalid promotion fail closed instead of asking an LLM or
each repository to reinterpret words such as `success`, `available`,
`verified`, `authorized`, `current`, or `production`.

The terminal safety statement is:

> No evidence originating as a fixture, simulation, declaration, unchecked
> hash, browser policy, expired delegation, stale receipt, or unknown external
> outcome can be promoted into a live, authorized, observed, current
> production-success claim.

This is a control-plane program, not a feature-expansion campaign. Until its
day-90 gate passes, the portfolio will not prioritize another MCP++ profile,
backend name, prover adapter, model provider, dashboard, legal jurisdiction,
or autonomous filing path.

## 2. Current-tree starting evidence

The first supervisor wave must reproduce and content-bind these observations;
they are planning inputs, not completion evidence:

- `ipfs_accelerate_py` already contains strong proof, planning, authorization,
  lease, fence, recovery, and repair components, but existing assurance enums
  still tend toward total ladders and legacy paths still contain mock
  capability/inference and pseudo-CID behavior.
- `ipfs_datasets_py` already owns semantic IR, compiler/decompiler, proof, and
  graph facilities, but package import can enable installation behavior and
  fallback operations can return success-shaped values without durable
  effects. Its declared package license and repository license also conflict.
- `ipfs_kit_py` already distinguishes candidate/admitted/current proof roles
  and hermetic/conditional/live backend evidence. Those distinctions are
  reference semantics to adapt, not replace. Its current support matrix must
  remain honest when no live-qualified backend exists.
- SwissKnife already separates several evidence classes in its presentation
  architecture, but browser-side gateway paths can still construct allow-like
  decisions or default consent. Browser state must never originate authority.
- MCP++ already has profiles, IDL, schemas, vectors, and validators in several
  languages, but normative semantics and canonical encodings remain duplicated
  across hand-maintained implementations.

The supervisor executes only against exact committed gitlinks in its clean
controller worktree. It must not consume the dirty legacy checkout as source
authority.

## 3. Target flow and trusted computing base

```text
human, agent, CI job, or remote client
                    |
                    v
          canonical OperationSpec request
                    |
                    v
          verified contract resolution
                    |
                    v
        authority + runtime-policy admission
                    |
                    v
    confirmation / payment / lease obligations
                    |
                    v
          effect reservation and execution
                    |
                    v
       independent effect observation
                    |
                    v
         proof/evidence classification
                    |
                    v
          immutable signed receipt
```

The intended allocation is:

| Concern | Primary mechanism |
| --- | --- |
| Normative claim and promotion semantics | Lean 4 |
| Executable trusted kernel | Rust; Verus only where a pinned toolchain is admitted |
| Stateful and distributed protocols | TLA+/PlusCal; Alloy for relational counterexamples |
| Decidable runtime admission | closed Rust IR, Datalog, bounded temporal monitors |
| Static effects, trust flow, and impact | abstract interpretation and Souffle-compatible Datalog |
| Proof and synthesis | Z3, cvc5, SyGuS/CEGIS, incremental solver scopes |
| Semantic normalization | proved or solver-validated e-graph rewrites |
| Artifact authority | `ipfs_kit_py` immutable artifacts, CAS, WAL, current pointers |
| Orchestration | `ipfs_accelerate_py` admission-token consumption and monitored execution |
| IR/proof semantics | `ipfs_datasets_py` |
| Human presentation | SwissKnife, without authority-creation capability |

Python and TypeScript are not proposed as whole-program proof targets. The
program verifies a small kernel, generates bindings and vectors, and
translation-validates each generated artifact and migration adapter.

## 4. Normative semantic core

Evidence is a product, never a single total ladder:

```text
EvidenceEnvelope {
  origin:     absent | declared | fixture | simulated |
              hermetic_observed | live_observed
  integrity:  unchecked | structurally_valid | digest_valid | signature_valid
  authority:  unchecked | absent | valid | expired | revoked | denied
  policy:     unchecked | allowed | denied |
              allowed_with_obligations | indeterminate
  proof:      none | candidate | verified | refuted |
              unknown | verifier_unavailable
  freshness:  current | stale | superseded | withdrawn
  effect:     not_started | reserved | started | externally_unknown |
              observed | compensated | failed
  environment: hermetic | conditional | live
  review:     unreviewed | machine_reviewed | human_reviewed
}
```

The kernel defines construction and promotion predicates including:

```text
production_supported(e)
effect_successful(e)
proof_reusable(e)
receipt_authoritative(e)
release_admissible(e)
```

A fixture can never become live observation by relabeling. A digest cannot
establish semantic truth. A payment cannot grant authority. A cached proof
candidate cannot become admitted without current verifier evidence. A browser
policy object cannot affect host authorization except through authenticated
request fields independently evaluated by the host.

Every effectful operation uses a closed outcome algebra:

```text
Unavailable | Rejected | Simulated | Attempted | Unknown |
Observed | Verified | Failed | Compensated
```

Generic `success: true` is forbidden on migrated production paths.

## 5. Program dependency graph

```text
source freeze + inventories
          |
          v
FCA Formal Claim Algebra
  |                |
  v                v
CCC contracts      IPA effects/trust/CID analysis
  |                |
  v                |
EAK admission <----+
  |  \             |
  |   \            v
  |    +-------> IFA noninterference
  v
TEP transactional protocols
  | \
  |  +------> SDI semantic invalidation
  |                |
  +------------> AGS assume-guarantee contracts
                   |
         +---------+---------+
         v                   v
TVC translation validation  RSE bounded repair synthesis
         |                   |
         +---------+---------+
                   v
         RPS/PRM verified supervision
                   |
         +---------+---------+
         v                   v
BCS backend certification   PCR release/rights logic
         +---------+---------+
                   v
        one proof-carrying portfolio release
```

## 6. Workstreams and gates

### FCA — Formal Claim Algebra

Deliver the product lattice, legal construction transitions, promotion
predicates, Lean theorems, executable Rust functions, shared transition
vectors, compatibility adapters, and an ambiguous-claim scanner.

Gate: no production API on the four migrated paths exposes unqualified
`success`, `available`, `supported`, `verified`, or `proven`; illegal
promotion fails by type construction or deterministic validation.

### CCC — Canonical Contract Compiler

Define an Assurance IDL `OperationSpec` containing schemas, effects,
idempotency/reversibility class, authority/policy/confirmation/lease and
observation obligations, evidence class, and resource bounds. First normative
artifacts are `EvidenceEnvelope@1`, `OperationSpec@1`, `AdmissionToken@1`, and
`EffectReceipt@1`.

Use deterministic DAG-CBOR for signed persisted artifacts, reject unknown
normative fields and duplicate keys, exclude security-critical floats, and pin
one CID profile per artifact family. Generate Python, TypeScript, Rust, and Go
bindings plus positive, negative, and mutation vectors.

Gate: the same value has byte-identical canonical bytes and CID in all four
languages; one-bit mutations and unknown fields fail.

### EAK — Effect Admission Kernel

Assign every operation a closed effect class and require the typestate path
`Proposed -> ContractResolved -> ActorAuthenticated -> CapabilityVerified ->
PolicyEvaluated -> ObligationsSatisfied -> ConfirmationSatisfied -> LeaseHeld
-> Reserved -> Started -> Observed -> ReceiptSealed`.

Only the kernel constructs an argument-bound, actor/resource/policy/
delegation/confirmation/lease/expiry/nonce-bound `AdmissionToken`. Rich
temporal-deontic source policy is conservatively compiled to a decidable,
default-deny runtime IR. Unknown or untranslatable policy fails closed.

Gate: no effectful handler or transport bypasses the same kernel, and changing
browser `allow`, `consent`, or `dry_run` fields cannot grant authority.

### IPA — Import Purity and Capability Abstract Interpreter

Extract Python and TypeScript facts into a product domain for effects, trust,
outcomes, and identity. Detect import-time installation/network/process/
mutation, mock-to-production flow, success without effect observation,
exception swallowing, and pseudo-CID construction. Use CEGAR for imprecise
dynamic dispatch and attach a source-to-sink trace to every finding.

Gate: core imports are statically pure and dynamically sandboxed; no
mock-origin value or raw hash reaches a live claim; the first deterministic
repairs are admitted for Datasets and Accelerate.

### IFA — Information-Flow Assurance

Introduce labels from `Public` through `CryptographicSecret` and
`WitnessSecret`, explicit declassification, taint propagation, and two-run
tests for browser/host, tenant, prompt/authority, credentials, and proof
witnesses.

Gate: no raw secret or host path reaches browser payloads, public receipts,
logs, or prompts; cross-tenant and browser-nonauthority hyperproperty tests
pass.

### TEP — Transactional Effect Protocols

Model effects, proof sealing, storage/current-pointer changes, leases,
retries, settlement, repository mutation, and irreversible external actions.
Required invariants include `NoDoubleEffect`, `NoStaleFenceCompletion`,
`NoSuccessWithoutObservation`, `NoConfirmationReuse`, and
`NoReplayOfUnknownIrreversibleEffect`. Generate or validate runtime transition
monitors against the same transition vectors.

Gate: bounded models and crash injection cover every persistent boundary;
unknown external outcomes never silently become success or blind retry.

### SDI — Semantic Dependency and Invalidation

Build content-addressed semantic capsules over symbols, contracts, effects,
policies, proofs, tests, environments, and releases. Evaluate impact and reuse
rules in Datalog; use incremental SMT and interpolant-derived boundary
summaries where justified.

Gate: a curated mutation corpus has zero missed required revalidations;
reuse and invalidation both produce minimal dependency-path explanations.

### AGS — Assume-Guarantee Synthesis

Publish versioned contracts for Datasets, Kit, Accelerate, and SwissKnife.
Counterexamples may refine assumptions, but an environmental assumption must
be discharged against its provider before composition.

Gate: a cross-repository failure identifies the violated boundary contract,
and no repository imports another merely to discover its semantics.

### TVC — Translation Validation

Bind every translation among intent, legal, security, policy, solver,
proof, runtime decision, and explanation to a `TranslationReceipt`. Define a
deontic safety-refinement order in which prohibitions remain prohibited,
obligations remain or strengthen, permissions never broaden, and loss is
explicit. Only proved or solver-validated rewrite rules enter proof-producing
e-graph extraction.

Gate: equivalence is never claimed without criteria; adversarial negation,
exceptions, temporal overlap, conflict, and jurisdiction cases are covered.

### RSE — Counterexample-Guided Repair Synthesis

Use fixed repair grammars for false success, mock capability, pseudo-CID,
import effect, browser authority, mutable dependencies, stale proof reuse, and
missing recovery states. LLMs may classify and sketch; they cannot expand the
grammar, waive obligations, promote patches, or create authority.

Gate: every admitted patch has a `PatchCertificate`, removes the original
counterexample, introduces no new abstract counterexample, and passes affected
proofs/tests independently.

### RPS and PRM — Verified Supervisor and Proof Orchestration

Synthesize or mechanically validate bounded control policies for provider
selection, retry/fallback, human gates, leases, proof escalation, compensation,
and safe shutdown. Route obligations through the cheapest sound ladder:
schema, abstract interpretation, Datalog, e-graphs, incremental SMT, Alloy,
TLA+, specialized solver, Lean, then human review.

Gate: hard temporal properties are never weakened; unrealizable specifications
produce cores; `unknown` never becomes `verified`; cache reuse names its
derivation, assumptions, verifier, and exact semantic closure.

### BCS — Backend Certification

Generate model-based, property, crash, concurrency, credential, integrity,
large-object, restart, and interface-parity tests from `BackendContract`.
Certify only local durable filesystem, one pinned IPFS daemon configuration,
and Iroh in the first program.

Gate: backend selection requires a current live signed receipt; configured or
hermetic evidence cannot satisfy a live gate.

### PCR — Proof-Carrying Release and Rights Logic

Define `ReleaseAdmissible` over exact source, immutable dependency closure,
identified build environment, current proofs/tests/capabilities, contract
compatibility, rights resolution, reproducibility, and signed provenance.
Use SPDX Boolean expressions and an explicit `RightsIR`; ambiguous legal
interpretation remains human-blocked rather than machine-cleared.

Gate: two clean environments produce bit-identical artifacts; mutable VCS
dependencies and stale evidence are absent; source, environment, artifacts,
contracts, rights, and qualification evidence are signature-bound.

## 7. Repository ownership

| Repository | Owns | Must not own |
| --- | --- | --- |
| MCP++ | normative contracts, FCA, codecs/vectors, protocol models, generated interface packages | production storage, compute, legal data, UI authority |
| `ipfs_datasets_py` | IR semantics, translation validation, proof obligations, Datalog/impact facts, source policy logic | external-effect success claims |
| `ipfs_kit_py` | immutable artifacts, proof-seal store, WAL/CAS/current pointers, backend receipts | logical proof validity or authorization |
| `ipfs_accelerate_py` | admission consumption, scheduling, provider routes, isolated execution, monitors, repair orchestration, observation | simulation presented as live completion |
| SwissKnife | presentation, intent, confirmation interaction, evidence display, human review | authority, permission, production evidence |

## 8. Phases and exit criteria

| Phase | Target | Exit |
| --- | --- | --- |
| 0, days 1-15 | exact source freeze, inventories, defect corpus, TCB | all ambiguous claims and real defect seeds are content-bound; no prose-only completion |
| 1, days 16-55 | FCA + CCC core and generated bindings | Lean theorem, executable transitions, four contracts, cross-language bytes/CIDs |
| 2, days 45-90 | EAK + IPA and four real migrations | no browser authority, false success, pseudo-CID, import mutation, or mock promotion on migrated paths |
| 3, quarter 2 | TEP + SDI + AGS + IFA | protocol monitors, sound incremental invalidation, repository boundary contracts |
| 4, quarter 3 | TVC + RSE + BCS pilots | translation receipts, proof-carrying patches, filesystem/IPFS/Iroh certification |
| 5, quarter 4 | RPS + PRM + PCR | synthesized/validated supervisor controller and independently reproduced release |

Promotion between phases requires a current gate receipt for the exact source
and dependency closure. A missing optional formal tool yields a typed
capability gap; it never triggers import-time or worker-time installation and
never produces simulated proof.

## 9. Parallel execution contract

The taskboard is a DAG with an initial file-disjoint inventory wave. Four
strict numeric shards execute concurrently. Each task declares one owning
repository, predicted files, validation, resource class, effect ceiling, and
conflict policy. Shared package roots or generated registries are changed only
by explicit fan-in tasks after their producer tasks complete.

Implementation occurs in ephemeral Git worktrees. The merge queue is serial.
The plan, objective heap, taskboard, scheduler config, validator, and launcher
are protected from implementation providers. Objective and codebase refill are
disabled for the initial reviewed program. Model output is proposal-only;
validation, merge, goal completion, release, and authority remain
deterministic or externally reviewed.

Initial ready work is intentionally limited to current-tree inventories and
source/TCB qualification. The supervisor must reconcile existing components
before creating a parallel FCA implementation. It must adapt compatible
components and record incompatibilities rather than creating a second evidence
authority.

## 10. Safety floors and metrics

Hard floors are zero for:

- simulated-to-live promotion;
- effects without an admission token;
- stale proof reuse;
- browser-authored authority;
- pseudo-CID use on supported paths;
- release with mutable dependencies;
- success without observed or verified delegated evidence;
- secret flow to public evidence;
- blind retry of unknown irreversible effects;
- LLM self-certification or policy authority.

Measured outcomes include sound mutation-based impact selection, false-positive
rates for blocking import analysis, context and token reduction from semantic
capsules, incremental proof cost, live capability freshness, repair-patch
minimality, reproducible-build equality, and explicit human-review debt.

## 11. Recovery and rollback

- A task attempt has a bounded retry budget and must checkpoint typed failure.
- Worktree failure never mutates the controller branch.
- Merge failure enters the serial reconciliation queue; it does not mark the
  task complete.
- An ambiguous external effect enters `Unknown` and requires reconciliation.
- Stale leases and fences cannot commit.
- Tool unavailability yields `defer_capability` or a reviewed provisioning
  task, never an ad hoc package install.
- A failed phase gate leaves later tasks dependency-blocked by design; it does
  not weaken the gate.
- Reverting one admitted task commit is the source rollback unit; immutable
  receipts remain as historical, stale evidence.

## 12. Supervisor controls

Companion artifacts:

- objective heap:
  `implementation_plan/docs/49-formal-assurance-control-plane.objectives.md`
- executable taskboard:
  `implementation_plan/docs/49-formal-assurance-control-plane.todo.md`
- sealed scheduler:
  `config/formal_assurance_control_plane_scheduler.json`
- validator:
  `scripts/validate_formal_assurance_control_plane_board.py`
- operator wrapper:
  `scripts/formal_assurance_control_plane_supervisor.sh`

The operator sequence is `doctor -> dry-run -> start -> status`. Start is
admissible only from the exact clean branch and gitlinks in the scheduler.
Healthy startup requires more than a PID: the master and lane processes must
be alive, the heartbeat/log must advance, at least one ready task must become
claimed or produce a typed attempt record, and no lane may report a dependency
deadlock, provider-authentication failure, or stale worktree lease.

## 13. Terminal release theorem

The program terminates only after one bounded portfolio workflow composes:

```text
SwissKnife request
  -> host authentication and admission
  -> Datasets semantic compilation/translation receipt
  -> Accelerate scheduling and observed execution
  -> Kit immutable persistence/current-pointer update
  -> SwissKnife evidence presentation
```

The terminal release receipt must bind the exact source forest, dependency
lock, contracts, controller, policies, proofs, tests, live capability receipts,
rights decision, reproducible artifacts, residual risks, and human-reviewed
exceptions. No historical campaign receipt or unqualified test run can satisfy
that predicate.
