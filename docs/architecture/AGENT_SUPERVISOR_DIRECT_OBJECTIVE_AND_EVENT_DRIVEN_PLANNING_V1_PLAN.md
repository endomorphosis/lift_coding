# Agent Supervisor Direct Objective and Event-Driven Planning — DOEP-PLAN-V4

Program: `agent-supervisor-direct-objective-and-event-driven-planning-v1`
Plan CID: `sha256:ca087f36486cdfb9137c0b74c19ca4e4ea5f5f17a3a3188404383009638b9743`
Status: sealed bootstrap campaign; execution is owned by the existing supervisor.

## Outcome

A human or delegated external agent submits one bounded high-level idea. The existing supervisor authenticates it, compiles a versioned semantic objective and partial-order plan, persists canonical state, opens a bounded executable frontier, incrementally reacts to authoritative events, and stops on admitted satisfaction or a typed terminal condition. No custom Codex campaign prompt is required after qualification.

## Immutable source forest

| Repository | Commit | Tree |
|---|---|---|
| `lift_coding` | `bb8869ed72eb7002434345d9969efee729c4f7f6` | `99e85bfe584b7688ffbeff86da1e612dd6893a42` |
| `ipfs_accelerate_py` | `e7f17941206a9b0da87f4cc523885e093796ead0` | `52ab7daeab75104a6250544c6b53d1ddb0ea1957` |
| `ipfs_datasets_py` | `6c08977c43d48c2b953eb15fee4b8c671b64f8bc` | `5c84bcbdc70e6efb094908c75050c5dd7b51b2cf` |
| `ipfs_kit_py` | `b6c65ba732733d7e33852713ba18aa3b12235668` | `14da7d92e130b7ba3523d0d6741a3ef7ef1e1bc2` |

Branch names are navigation only. Every task and receipt is bound to exact commits, trees, plan epoch, policy and validation identity.

## Canonical consolidation decision

- Objective path: existing `objectives` heap/refinery plus `entrypoints.intent_service` and `plan_materializer`.
- Planner: existing formal plan compiler/validator/replanner and adaptive planner; no second planner family.
- Operational task authority: `DatabaseTaskSource@1` and its existing DuckDB intent repository, served to concurrent workers only by one authenticated `QuackStateServer@1` owner.
- Event path: existing database event log, runtime CAS and durable Kit storage adapters.
- Refill path: existing refill controller/event adapter/semantic refill/campaign policy.
- Model route: existing route planner and proposal router, extended into the required deterministic-first ladder.
- DuckLake: optional, rebuildable, append-only history/analytics projection; never scheduling, completion, policy or proof authority.
- Datasets owns semantic identity, schemas, ContextPack meaning, formal translation and proof relationships. Kit owns exact durable bytes, CIDs, WAL, recovery and current-root CAS. Accelerate owns operational admission, execution, validation, merge, recovery and terminalization.

The dormant prompt-first facade is not used as false authority at bootstrap: on the sealed base it fails closed without a production intent factory and complete launch plan. DOEP consolidates and qualifies that intended surface. The reviewed bootstrap route is sealed objective/board → canonical JSON materialization → DuckDB → exclusive Quack owner → existing configured multi-lane supervisor.

### Bootstrap revision history

`DOEP-PLAN-V1` failed closed before provider dispatch because task records used GitHub authority names where the existing worktree allocator requires canonical local authorities. `DOEP-PLAN-V2` corrected nested ownership but its four frontier tasks failed closed before provider dispatch because the generated pytest targets were absent from the nested projects' task-bound dependency contracts. `DOEP-PLAN-V3` then moved Accelerate tasks to the bridge's reserved root authority and substituted the portfolio dispatcher for the task's direct validation command. That was rejected as a hidden preflight bypass: it avoided the nested Accelerate V4 task/command/output authority check instead of satisfying it. The complete DuckDB event streams and logs for V1 through V3 remain retained as superseded failed generations. `DOEP-PLAN-V4` restores all three configured gitlink owners, owner-relative outputs and direct pytest commands, and reproducibly installs exact task-bound Accelerate V4 and Datasets V3 contract entries before launch. Kit remains on its existing static project-dependency path.

## Compiler and execution sequence

1. Deterministically validate, normalize scope/budgets/risk, bind repository and policy, and reject authority/path escapes.
2. Inspect manifests, objective/task state, dependency and symbol indexes, schemas, tests, proofs, capabilities, receipts and relevant failures.
3. Apply rule/template decomposition for known objective classes.
4. Send only named unresolved semantic questions and the smallest adequate ContextPack to the smallest adequate specialist; typed output cannot execute tools.
5. Validate contribution, exact outputs/evidence, acyclicity, authority, feasibility, deduplication and explicit assumptions before materialization.
6. Execute the route ladder: exact receipt reuse → AST/symbol/dependency analysis → semantic/interface diff → static/contracts → selected tests → selected proofs → small → medium → frontier → human.
7. On an authoritative event, compute the minimal impact cone, preserve unaffected receipts/tasks, emit PlanDelta and a refill decision, and add only necessary tasks under epoch/wave/convergence limits.

## Truth, safety and stop rules

Simulated is never live; estimates are never measurements; attempt is never effect; stored proof bytes are not admitted proof; and no model claim completes a task. Stale ContextPacks, receipts, proofs, leases, fences, plan epochs, policies and tree identities are rejected. Unknown effects reconcile rather than blind retry. External agents cannot write the databases, terminalize tasks or provide authoritative policy decisions.

An objective stops only when admitted evidence satisfies it, a human/policy decision is required, budget is exhausted, no admissible/convergent plan exists, or it is cancelled. An empty queue is not completion. Promotion is one closed status and retains zero hard-gate violations; absent measurements are missing, not zero.

## Bounded campaign controls

- Initial tasks: 85; initial frontier: `DOEP-000`, `DOEP-001`, `DOEP-002`, `DOEP-003`.
- Bootstrap concurrency: four isolated lanes, strict deterministic sharding, per-task lease/fence and merge serialization.
- Bootstrap objective/codebase refill: disabled because the reviewed board is complete and bounded. DOEP-050..056 implement and qualify the canonical bounded event-driven refill before it is activated elsewhere.
- Campaign generation ceiling: the sealed 85 tasks; no additional feature campaign from the residual-gap report.
- Qualification cohorts: ≥60 hermetic fixtures, ≥20 historical exact-tree replays, held-out set, ≥10 live shadow objectives, then a human-gated low-risk canary.
- Suggested promotion thresholds: ≥35% median input-token reduction, ≥25% weighted provider-cost reduction, ≥50% fewer frontier calls, ≥60% non-large-model eligible routes, ≥50% ContextPack reuse, ≥80% model-free ordinary refill, <5% unnecessary churn, <2% manual recovery, no quality degradation and positive net savings.

## Goals and waves

| Goal | Purpose | Task IDs |
|---|---|---|
| `DOEP-G010` Seal current authority and baseline | Bootstrap facts only; defer unrelated findings. | `DOEP-000`, `DOEP-001`, `DOEP-002`, `DOEP-003` |
| `DOEP-G020` Direct objective contracts and interfaces | One service layer and thin adapters; callers never supply authoritative policy. | `DOEP-010`, `DOEP-011`, `DOEP-012`, `DOEP-013`, `DOEP-014`, `DOEP-015`, `DOEP-016`, `DOEP-017` |
| `DOEP-G030` Consolidated staged objective compiler | Deterministic and semantic stages precede any bounded specialist model. | `DOEP-020`, `DOEP-021`, `DOEP-022`, `DOEP-023`, `DOEP-024`, `DOEP-025`, `DOEP-026`, `DOEP-027` |
| `DOEP-G040` Canonical event path | At-least-once delivery with idempotent, exactly-once logical transitions. | `DOEP-030`, `DOEP-031`, `DOEP-032`, `DOEP-033`, `DOEP-034`, `DOEP-035` |
| `DOEP-G050` Canonical task state machine | No stale lease, fence, policy, tree or plan epoch may complete. | `DOEP-040`, `DOEP-041`, `DOEP-042`, `DOEP-043`, `DOEP-044`, `DOEP-045`, `DOEP-046` |
| `DOEP-G060` Incremental reassessment and bounded refill | Only impacted suffixes change; ordinary frontier refill is model-free and bounded. | `DOEP-050`, `DOEP-051`, `DOEP-052`, `DOEP-053`, `DOEP-054`, `DOEP-055`, `DOEP-056` |
| `DOEP-G070` Cross-repository ContextPacks | Semantic, durable-byte and execution-admission authorities remain separated. | `DOEP-060`, `DOEP-061`, `DOEP-062`, `DOEP-063`, `DOEP-064`, `DOEP-065`, `DOEP-066` |
| `DOEP-G080` Deterministic-first route ladder | Route order is receipt, static, selected tests, proof, small, medium, frontier, human. | `DOEP-070`, `DOEP-071`, `DOEP-072`, `DOEP-073`, `DOEP-074`, `DOEP-075`, `DOEP-076` |
| `DOEP-G090` Logic-constrained incremental planning | Formal methods are qualified by measured benefit and have explicit fallbacks. | `DOEP-080`, `DOEP-081`, `DOEP-082`, `DOEP-083`, `DOEP-084`, `DOEP-085` |
| `DOEP-G100` Typed deterministic-first synthesis | A model assertion is never patch acceptance evidence. | `DOEP-090`, `DOEP-091`, `DOEP-092`, `DOEP-093`, `DOEP-094` |
| `DOEP-G110` Sibling-supervisor interoperability | Sibling supervisors exchange events and receipts, never database writes. | `DOEP-100`, `DOEP-101`, `DOEP-102`, `DOEP-103`, `DOEP-104` |
| `DOEP-G120` Measurement harnesses and populations | Missing measurements remain missing, never zero or estimated-as-measured. | `DOEP-110`, `DOEP-111`, `DOEP-112`, `DOEP-113`, `DOEP-114`, `DOEP-115`, `DOEP-116`, `DOEP-117` |
| `DOEP-G130` Paired qualification and honest release | Promotion thresholds and zero safety gates cannot be weakened. | `DOEP-120`, `DOEP-121`, `DOEP-122`, `DOEP-123`, `DOEP-124`, `DOEP-125`, `DOEP-126` |

Parallel waves are dependency-derived: inventory; contracts/compiler/events/routes; state/direct adapters/ContextPack; reassessment/planning/sibling/synthesis; invariant qualification and corpora; paired hermetic/historical/held-out evaluation; live shadow; conditional canary; closed release receipt.

## Deliverables and completion

The terminal release report must include the ADR; versioned contracts; Python/CLI/MCP/MCP++ direct interfaces; objective compiler; event/outbox/replay/recovery; incremental PlanDelta/refill; deterministic-first routing; cross-repository ContextPacks; sibling delegation; telemetry and paired benchmarks; unit/property/state/crash/race/security tests; operator and integration guides; three held-out demonstrations (one generic MCP); exact commits/trees/CIDs and an honest promotion status.

Functional completion additionally requires direct high-level submission, first task without custom priming, automatic incremental reassessment and refill, sibling-event safety, external-agent non-bypass, package independence from sibling test layouts, repeated-board draining without manual DB repair, current-head tests, paired measurements and all zero safety gates.

## Deferred backlog

Nonessential hazards discovered during inventory—legacy ContextPack candidates, noncanonical in-memory event helpers, duplicate adapters and retention/tombstone gaps—are recorded by DOEP-000/002 for later disposition. They do not expand this campaign.
The exact Accelerate base also contains 13 legacy V4 `present` baseline attestations whose stored target digests are stale; four checked-in contract tests therefore fail closed with `v2_present_target_digest_mismatch`. DOEP uses separate exact task identities with `declared-output-absent` baselines, and all 85 DOEP admissions pass. Repairing that unrelated historical attestation debt is deferred and no current-head-suite success is claimed at bootstrap.
