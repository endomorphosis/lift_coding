# LogicGovernedSemanticWorkFabric implementation and qualification plan

Status: sealed bootstrap plan, execution in progress through the existing configured-board supervisor. This document is architecture intent; the task board, accepted PlanRevisionStore pointer after Epic A, immutable receipts, and verified datasets artifacts carry execution authority.

## 1. Outcome and present qualification decision

The parent objective is to compose canonical datasets semantic truth with accelerator-owned operational coordination into one continuous, evidence-backed control loop. The implementation order is A through O and every shared contract is frozen before consumers may mutate it.

The present system is **not** the requested fabric and is a **no-go for continuous multi-supervisor operation**. A bounded bootstrap launch is permitted only for the four disjoint read-only inventories. The checked accelerator CLI does not yet wire PlanRevisionStore, LeaseCoordinator, or ResourceScheduler into configured-board daemon execution, and a verified canonical semantic-state root could not be constructed. Those are product gates, not launch assumptions.

Success will be considered only after Epic O independently verifies a content-addressed release. A bounded non-success terminal is an honest board result; it is never rewritten as successful completion.

## 2. Checked-source comparison and implementation authority

The operator checkout was inspected before planning. Its dirty content remains untouched. A clean control worktree was created solely because the sealed launcher requires exact clean gitlinks and a clean root.

| Repository | Checked authority | Material comparison |
|---|---|---|
| lift_coding | `b6f40c05e0884867eb8557f8882cd25cb760ca2f` | locally known origin/main is 175 commits ahead; dirty worktree and historical worktree forest preserved |
| accelerator | `ea11293bb996f052d620eae989f5377a956764b1` | superproject pin `485edc0871c55b0e2ef21d83bece9fa12c2c8d84` is 1,245 commits ahead; PCCE repair head `0837254e910221c17b3c8ac8a2a233658de976f1` is 1,251 ahead |
| datasets | `ac82107e246b30e35a2bbdcf75e01370d22350c6` | accelerator's nested dependency is the deinitialized `a2f5400b…`, 568 commits behind; locally known datasets origin/main is 96 commits ahead |

The exact commit-list and name/status digests, dirty-overlay identities, trees, branch observations, and consequences are in `artifacts/logic_governed_semantic_work_fabric/baseline/revision-comparison.json`. Local remote refs were not refreshed, so their comparisons are informational until a separately authorized fetch.

The control worktree is based on root `b6f40c05…` and bootstrap commit `d99a0204e3936ad40a68c8a457b85dc353ee9eff`, which changes only the accelerator gitlink to the observed checked head `ea11293b…`. This does not discard the dirty overlay: LGSWF-001 inventories every path and LGSWF-005 must explicitly preserve, reject, or selectively port each relevant difference through an admitted task.

### Revision consequences

- Accelerator `ea11293b` has 535 supervisor files and no `agent_supervisor/semantic_state/`. The later `485edc08` tree has 676 files and a 20-file semantic-state package. Later files are review candidates, not current implementation. This plan places new operational contracts in existing `core`, `runtime`, and `planning` layers; it does not scaffold an assumed package or write into the empty root skeleton.
- Datasets `ac82107e` contains the semantic index, semantic state, capsules, freshness, bindings, invalidation, test/proof selection, contracts, verification, formalization, backends, families, verification API, and semantic governor. It does not contain adversarial assurance, incremental proof sealing, `ProofRepository@1`, or later logic-platform canonicalization. The board will not invent replacements. Epic A must either bind a separately admitted exact revision that contains the canonical systems and regenerate all roots, or emit a qualification no-go for the affected requirements.
- Datasets currently imports accelerator semantics upward in the counterexample identity path and optional adapters. That violates the desired package direction and is an explicit Epic A repair.
- The earlier PCCE r5 launch admitted a process and exited zero but completed no product task and wrote no repository change. Its preserved incident (`sha256:28aedd7072735fd539ed4dc4ad9387242a02b0372626a42f36a695c2ce9e9b61`) records empty source context, a review schema that required findings while allowing zero items, and coordination/materialized task CID alias mismatch. Nothing from its claims, leases, fences, worktrees, or task identities is reused.

## 3. Bootstrap semantic-state finding

No canonical semantic root is fabricated for this board.

1. The convenience scan without a namespace failed with `SemanticIndexModelError: namespace must be nonempty trimmed NFC text`.
2. The explicit accelerator scan failed in AST analysis with `ASTIRValidationError: named_argument_names must not contain duplicates`.
3. The explicit datasets scan was boundedly interrupted after more than 22 minutes at approximately 96% CPU and 6.8 GiB resident memory while repeatedly deep-copying AST projections; it emitted no root.

The exact typed record is `artifacts/logic_governed_semantic_work_fabric/baseline/semantic-scan-bootstrap-failures.json`. LGSWF-001 through LGSWF-008 may use exact-tree, raw-source-required bootstrap bindings because their scopes are inventory or explicit bootstrap repair. Every later mutation fails closed until LGSWF-009 verifies non-null datasets roots and activates PlanRevision r1 with exact per-task bindings.

## 4. Authority map and package direction

### Datasets owns semantic truth

The following checked implementations are canonical semantic authorities:

- `logic/software_contracts/semantic_index`: repository capture, AST symbol and symbol-version identity, relationships, deltas, invalidation, explanations, and immutable root publication.
- `logic/software_contracts/semantic_state`: state roots and verified bundles, binding projection, capsule compilation, confidence/freshness, producer-bound raw source, environment-derived invalidation, and graph-based test/proof selection.
- `logic/software_contracts/contracts.py` and `registry.py`: reviewed software contract IR and registry identity.
- `logic/software_verification`: formal program contracts, VC generation, obligation graphs, proof plans, typed proof/counterexample evidence, and verification results.
- `logic/software_contracts/semantic_governor`: context coverage/sufficiency, omission diagnosis, expansion, calibration, trusted decisions, quarantine, and rule proposals.
- `logic/verification_api.py`: high-level semantic proof/receipt consumer API, explicitly not a supervisor-control authority.

Important exact mappings are frozen rather than renamed. `SemanticStateRoot@1` references its own symbol/artifact/link/node/capsule/environment-binding/limitation roots; it does not currently contain global contract or proof-obligation roots. Reviewed contract registries, VC sets, proof graphs, and generic obligation collections retain their artifact-kind-specific roots. Accelerator records reference those roots by type and never add operational fields to datasets state.

### Accelerator owns operational coordination

The checked modules to reuse and extend are:

- objectives: `objective_graph.py`, `objective_tracker.py`, `goal_completion.py`, `backlog_refinery.py`;
- plan and task authority: `planning/plan_revision_contracts.py`, `task_sources/plan_revision_store.py`, task identities and Markdown/DuckDB sources;
- dependency/conflict/change propagation: existing semantic dependency graph, change-propagation pipeline/contracts, and `core/conflict_graph.py`;
- proof orchestration: `proof_scheduler.py` and `formal_verification_cache.py` as consumers of datasets obligations;
- runtime: configured-board scheduler, multi-supervisor runner, resource scheduler, event log, implementation supervisor/daemon/runner;
- merge: lease coordination, queue, train, and checkpoints;
- recovery: watchdog, recovery, rescue orchestration, autonomous unstall, and status projections;
- highest-level `entrypoints` package for the final machine-readable view.

No new semantic index, capsule compiler, context engine, proof cache, plan store, objective tracker, daemon framework, model provider/router, GUI, or MCP++ profile will be created.

### Required package direction

Dependencies remain bottom-up:

```text
core/foundational contracts
  ↑ control, task_sources, context, analysis, proof, semantic references
  ↑ objectives, planning, validation, prompt
  ↑ merge, rescue, runtime, self_improvement
  ↑ todo_daemon, integrations
  ↑ entrypoints
```

Datasets never imports accelerator to define semantic identity. Composition adapters live on the accelerator side or behind datasets-owned leaf protocols. Compatibility facades remain inert. LGSWF-004 produces the complete import graph and implementation classification; LGSWF-005 freezes the accepted map.

## 5. Goal hierarchy and dependency-ordered board

The goal heap contains the parent `LGSWF-G000` and subgoals `LGSWF-G100` through `LGSWF-G1500` for Epics A through O. It is in `docs/architecture/logic_governed_semantic_work_fabric.objectives.md`.

The executable bootstrap projection contains 63 stable tasks in `docs/architecture/logic_governed_semantic_work_fabric.todo.md`. Every task explicitly records the required parent/subgoal, owner, owned paths, base revision, semantic/plan binding, objective, dependencies, read/write/effect scopes, symbols, capsules, contracts/obligations, resource vector, route, permitted/prohibited effects, completion/validation/proof contracts, leases, compensation, evidence, status, and result identity.

The machine projections are `task-board.json` and `task-dependency-graph.json` below `artifacts/logic_governed_semantic_work_fabric/control/`. The accepted PlanRevisionStore projection supersedes this legacy launch projection only after LGSWF-009.

```text
LGSWF-000 board seal
       ↓
001 revision ─┐
002 datasets ─┼─→ 005 interface freeze ─→ 006 scanner repair ─┐
003 accel ────┤                           007 DAG repair ──────┼→ 009 A gate
004 DAG/PCCE ─┘                           008 runtime repair ──┘
       ↓
B world → C bindings → D graphs → E frontier → F resources
       ↓
G supervisors → H daemons → I revisions → J refresh
       ↓
K convergence → L observability → M faults → N benchmark → O release
```

Only LGSWF-001 through LGSWF-004 are initially ready. They read the exact source and write unique evidence files. No initial task owns source code, canonical semantic state, plan authority, provider state, or an external effect.

## 6. Operational world overlay

`SupervisorWorldSnapshot@1` is accelerator-owned and content addressed. It references, without reinterpreting:

- repository identity and tree;
- datasets repository-state CID and semantic-state-root CID;
- typed symbol/capsule/environment/contract/proof roots where the checked datasets contracts actually expose them;
- accepted plan root/revision, objective graph, goal/subgoal/task population, claims, resources, supervisor/daemon capabilities, merge queue, completion evidence, unresolved gaps, active policies, event cursor, coordination epoch, and fencing epoch.

Raw source, prompts, credentials, model replies, mutable local paths, and provider payloads stay in separately managed artifacts. Each component is `current`, `stale`, `unavailable`, `inconsistent`, or `quarantined`, with authority and observation evidence. Scheduling requires exact agreement on repository, tree, plan revision, task population, semantic generation, and policy revision; stale roots and plan pointers fail closed.

`SupervisorWorldView` is a pure query projection for goal/subgoal/task state and bindings, ready/blocking dependencies, conflicts, resources, claims, capsules, contracts, obligations, completion evidence, and refill eligibility. It holds no mutation port.

## 7. Semantic work binding and completion

`SemanticWorkBinding@1` is an accelerator reference record for goals, subgoals, and tasks. It contains accepted plan, tree/root, target symbols/artifacts, capsule/source/environment references, pre/post/exceptional conditions, effects/scopes, tests, proof obligations, assumptions, limitations, counterexamples, invalidation, completion rule, authority, and review requirements. Capsule bodies remain in datasets.

Goal completion is a contract over observable state, semantic properties, current tests/proofs, accepted children, counterexamples, assurance gaps, review, tree, and root. A completed task population does not complete a goal.

Task lifecycle distinguishes execution, patch validation, proof verification, merge, canonical semantic refresh, and supervisor acceptance. A daemon may report worker completion but cannot accept its own task. Worktree changes use an attempt-bound provisional semantic root. Only the accepted merge tree is rescanned and published by datasets authority; predicted and observed deltas are compared and downstream work invalidated.

## 8. Composite graph and conflicts

`SemanticWorkGraph@1` retains separate goal-parent/dependency, task, code/data/interface/schema, contract/proof/validation/policy/merge/lifecycle, read/write/effect, invalidation, conflict, supersession, generation, block, and unlock edges. Each edge records source/target, kind, semantic or operational authority, supporting evidence, fixed-point confidence/certainty, source semantic root, source plan revision, and invalidation conditions.

Dependency and conflict remain separate. Shared reads may run concurrently; disjoint semantic writes may run concurrently when effects/resources/plan relationships agree. Same-symbol, interface, schema, generated authority, fixture, database shard, taskboard, external effect, exclusive provider/hardware, and merge-order conflicts serialize unless an explicit conflict/merge contract proves compatibility. Opaque analysis falls back from symbol to file to repository serialization.

Durable analysis uses integers or scaled integers for topological depth, critical-path length, unlock count, blocking goals, estimated cost, uncertainty, merge risk, resource bottleneck, and cache locality. Binary floating point is excluded from content-addressed decisions.

## 9. Deterministic frontier planner

A task is eligible only if its active plan, legal lifecycle, predecessors, semantic binding, capsule/source fallback, contracts/obligations, scope, conflicts, resources/provider capacity, completion policy, quarantine/supersession/block/review state all pass.

The planner computes the ready set, constructs the dedicated conflict graph, and selects a resource-feasible antichain with a deterministic bounded procedure:

```text
score = completion_value
      + critical_path_gain
      + downstream_unlock_value
      + cache_and_worktree_locality
      + bounded_age_and_fairness
      - resource_and_model_cost
      - provider_pressure
      - conflict_and_merge_risk
      - semantic_uncertainty
      - expected_retry_cost
```

All terms are policy-versioned scaled integers. Stable task identity is the final tie-break. A bounded exact search is used for small frontiers and deterministic greedy-plus-local-improvement for larger ones; every rejection and selection is receipted. LLMs may propose decompositions but never admit work.

Split, coalesce, and rewire use the existing `PlanDelta` operations and apply only to future mutable specifications. Started history is retained; successors carry explicit supersession. Speculation is read-only or isolated, resource bounded, safely cancellable, and candidate-only—never an authoritative merge or publication.

## 10. Resource and multi-supervisor policy

Existing ResourceScheduler contracts are extended across CPU time/concurrency, RAM, GPU memory/compute class, disk capacity/bandwidth, network permission/bandwidth, subprocesses, worktrees, model input/output tokens, provider quota/concurrency, prover class/concurrency, license/key exclusivity, merge slots, and persistence bandwidth.

Hard resources are reserved before dispatch and bound to task, attempt, supervisor, daemon, lease, and fence. Completion, cancellation, timeout, confirmed death, or fenced expiry releases them. GPU memory, provider/prover concurrency, merge authority, exclusive writers, and worktree mutation are never overcommitted.

Observed receipt values remain immutable. Predictions for latency, tokens, memory, retry, tests, proofs, and conflicts are separate records. Single-flight and placement prefer reuse of scans, state blocks, capsules, ContextPacks, provider sessions/prefix caches, test/proof artifacts, environments, dependencies, and worktree objects.

Backpressure is independent for analysis, context, model, proof translation, solver, kernel, validation, merge, and persistence. Provider pressure cannot stop CPU analysis; proof pressure cannot stop unrelated analysis; merge pressure reduces new mutation dispatch but permits read-only work. Only low-priority speculative, stale, superseded, or safely compensated work is preemptible.

Supervisors advertise observed capabilities, not authority. One fenced writer owns each coordination shard; peers read snapshots, propose, claim admitted work, and publish immutable evidence. Failover advances the epoch and prevents the former coordinator from committing. Work partitioning preserves explicit cross-partition edges. Work stealing requires virgin/expired/dead/transferable state, current verified checkpoint, and a later fence. At-least-once processes produce exactly-once logical acceptance over task, plan, base tree, semantic root, and idempotency key.

## 11. Daemon packet, lifecycle, and checkpoints

The existing packet is extended once, not replaced. It binds task/goal/subgoal, plan root/revision, repository/tree/root, symbols, capsules/source, contracts/obligations, ContextPack, scopes/effects, resources, provider/model, validation/proof/completion, lease/fence/attempt/idempotency, checkpoint, timeout/cancellation, and expected artifacts.

Main lifecycle:

```text
offered → admitted → claimed → running → checkpointed → settling
        → worker_completed → supervisor_verified → accepted
```

Side paths are rejected, blocked, cancelled, timed_out, failed, partial_effect, compensation_required, superseded, and quarantined. Checkpoints bind attempt/plan/root/worktree tree, changed files/symbols, completed stage, consumed resources/model calls/tests/proofs, outstanding obligations, effects, resume needs, and CID. They never imply completion.

A daemon returns a typed stale result and stops when plan, supersession, semantic root, lease, fence, scope, cancellation, or prior acceptance changes. It cannot finish after losing authority.

## 12. Immutable refill, semantic refresh, and convergence

Refill proposals use the existing PlanRevisionStore and backlog refinery. Every specified semantic, capsule, source, contract, test, proof, counterexample, governor, assurance, merge, progress, provider, resource, granularity, steering, or out-of-plan repository trigger carries evidence, affected scope, current roots, proposed deltas, predicted parallelism/path/resource impacts, validation, dedupe, uncertainty, fallback, and review.

Successor depth, revision depth, tasks/subgoals per revision, repeated semantic keys, retries, provider calls, tokens, frequency, and no-progress epochs are hard bounded. Cosmetic rewrites cannot bypass dedupe; idle capacity alone cannot generate work; completion contracts cannot be weakened. Claimed/running/settling/completed/accepted records are immutable.

The deterministic plan doctor diagnoses cycles, reachability/orphans, missing completion/binding/verification, hidden or excessive serialization, unsafe parallelism, resource infeasibility, bottlenecks, starvation/retries, stale evidence/root mismatch, and incomplete parent coverage. It proposes but never activates revisions.

Before execution the supervisor verifies the datasets view, blocks, capsule freshness/source fallback, test/proof selection, ContextPack, and attempt binding. During work it obtains datasets-derived provisional symbol delta and invalidation closure, rejects scope drift, and replans verification. Before merge it checks predicted semantic effects, contracts, tests/proofs, governor findings, available assurance, and an incremental seal. After accepted merge it rescans the accepted tree, publishes canonical datasets state, compares deltas, updates the world snapshot, invalidates downstream work, reevaluates goals, and revises/refills.

The convergence loop repeats observe → frontier → reserve → dispatch → execute/checkpoint → verify/merge → refresh → complete → revise. Success requires accepted required goals/children, no mandatory ready/blocked/unresolved task, current completion evidence, no blocking invalidation/proof/critical assurance gap, matching accepted tree/root, current plan, empty mutating claims, settled merge queue, and verified receipts/seals.

Typed non-success terminals are `blocked_external_dependency`, `resource_unavailable`, `provider_unavailable`, `semantic_analysis_inconclusive`, `verification_inconclusive`, `human_review_required`, `bounded_exhaustion`, `no_progress`, `policy_denied`, `quarantined`, and `cancelled`.

## 13. Observability and decision evidence

Every scheduling cycle records world snapshot, plan revision, candidates/rejections, conflict root, selected frontier, resource observations/reservations, supervisor/daemon assignments, priority components, critical path/unlock, cache/fairness/provider adjustments, policy version, and resulting claims.

Metrics cover frontier/DAG/concurrency/utilization/wait/overhead/idle/duplicates/fencing, scan/state/capsule/context/test/proof reuse, model tokens/escalations, provider/prover/merge pressure, conflicts/revisions/refill/no-progress, and cost per accepted task/goal. Machine-readable output is exposed through the existing highest-level entrypoint package. No GUI is added.

## 14. Fault qualification and benchmark

Epic M builds a deterministic fixture with three supervisors and ten daemons. It executes all 26 required behavioral cases and the complete forged/stale/wrong-binding/scope/policy/test/proof/receipt/replay/checkpoint/split-brain/telemetry adversarial matrix. Critical cases fail closed. Restart reconstruction uses durable records, never process dictionaries.

Epic N freezes a workload corpus and compares:

- A: one supervisor/daemon, serial;
- B: one supervisor/multiple daemons, dependency-only;
- C: multiple supervisors/daemons, conflict-aware;
- D: complete logic-governed fabric with reuse, resources, adaptive graph revisions, stealing, incremental verification, and refill.

Raw results report wall time, throughput, efficiency/path delay/wait, utilization/overhead/duplicates/reuse/tokens/throttling/conflicts/failures/refill/revision/recovery, and compute per accepted task. Initial targets are targets only. Process count is never used as a proxy for maximum parallelism.

## 15. Release and final report

Epic O assembles exact source revisions, inventory/authority, all required schemas, integration/fault evidence, corpus/raw results, performance/resource/security reports, limitations, migration, rollback, and qualification decision. The evidence selects no higher than `research_demo`, `internal_alpha`, `internal_pilot`, `supervised_external_pilot`, or `production_candidate`.

The final supervisor report contains the required 24 sections and an explicit continuous-operation go/no-go. The prescribed scoped final claim is permitted only if its factual predicates pass; otherwise the report identifies the precise no-go terminal and unresolved evidence.

## 16. Launch and unstall policy

The checked configured-board launcher is used because it preserves branch, ancestor, protected-file, clean-checkout, exact-gitlink, validator, and lifecycle protections. It is not represented as the completed fabric.

Because the checked root contains no importable accelerator package, detached bootstrap launch must explicitly bind `PYTHONPATH=external/ipfs_accelerate`; the configured subprocess otherwise exits before creating a supervisor. Epic A must replace this bootstrap environment binding with the frozen source resolver rather than hide it in a mutable user profile.

Initial launch uses two supervisors, the runtime-required sealed Grok-primary/Codex-independent-review route with bounded quota fallback, no objective/codebase refill, and the four read-only inventory tasks. Source mutations remain behind Epic A. The runtime has a fresh namespace and does not reuse prior board state.

Monitor lane status for heartbeat/progress, active task and phase, eligible/blocked counts, selection idle reason, implementation/merge return codes, and autonomous-unstall state. Exact critical conditions include stalled worktree/implementation logs, stale heartbeat/no progress, unresolved merge failure, protected-path/worktree reconciliation, missing active plan in fabric mode, provider/resource backoff, and autonomous-unstall quarantine.

The existing inner supervisor performs bounded deterministic autonomous unstall and daemon recycle. The outer runner restarts exited or safely stale supervisors; it does not kill a live mutating task merely because it appears old. Operator intervention is limited to evidence-backed reconciliation, cancellation, or explicit non-success disposition—never deleting history or weakening gates.

## 17. Execution rules

For every task:

1. Resolve exact repository, tree, semantic root or typed bootstrap exception, and accepted plan.
2. Allocate an isolated worktree and declare reads, writes, effects, resources, model route, and completion policy.
3. Acquire claim, mutation permit, resource lease, fencing token, and idempotency key.
4. Run pre-change checks and verify scope authority.
5. Implement the smallest coherent change without touching protected files.
6. Build provisional semantic delta and invalidation through datasets authority.
7. Run focused selected tests/proofs and affected integration validation.
8. Emit checkpoint/result/validation/proof/effect receipts.
9. Merge only through the admitted queue and independent supervisor gate.
10. Refresh canonical semantic state, compare deltas, invalidate, and reevaluate goals.
11. On failure preserve attempts/effects, compensate if required, and revise or enter a typed bounded terminal.

No model or daemon approves its own output. No overlapping independent write lease is admitted without an explicit merge/conflict contract. No worker writes datasets semantic truth or a canonical root. No historical claimed or terminal record is rewritten.
