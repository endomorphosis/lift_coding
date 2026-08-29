# Proof-Carrying Platform Qualification and Release v1

Program identifier: proof-carrying-platform-qualification-and-release-v1

Short identifier: PCPR

Execution mode: execute_with_confirmations

Risk class: high_assurance_platform_release

Status: bootstrap handoff prepared; the qualification campaign is not yet admitted and no release claim has been made.

## Outcome and bounded claim

Make ipfs_datasets_py, ipfs_kit_py, and ipfs_accelerate_py production-qualifiable as one proof-carrying platform by eliminating legacy false-authority paths, qualifying real storage, compute, model, and prover backends, replacing source-tree coupling with immutable package contracts, publishing exact signed releases, and validating one end-to-end objective, ContextPack, execution, proof, recovery, event, and receipt workflow.

The intended outcome is one exact, bounded, signed, reproducible release candidate with an explicit capability matrix and explicit limitations. This campaign never implies an unlimited or global production-ready claim.

The campaign has one authority-preserving bootstrap exception. The current public prompt facade exists, but a high-level prompt cannot yet create its own admitted CompleteLaunchPlan and live runtime binding. The immutable bootstrap board therefore contains only PCPR-004. That task repairs the existing direct path. After its independently validated receipt is admitted, the exact high-level objective above and the constraints in this plan must be submitted through the repaired interface. The supervisor, not the bootstrap agent, must elaborate and materialize the 66 required blueprint packages below.

## Scope and non-goals

The only source repositories in scope are:

- endomorphosis/ipfs_datasets_py;
- endomorphosis/ipfs_kit_py;
- endomorphosis/ipfs_accelerate_py;
- this portfolio repository solely for the sealed handoff, cross-repository receipts, compatibility manifest, audit package, and release decision.

The following are prohibited scope expansions:

- no new supervisor family;
- no new planner family;
- no new meta-controller;
- no new task database;
- no new event database;
- no new MCP++ profile;
- no new dashboard;
- no new model-provider family;
- no new backend category;
- no new legal jurisdiction;
- no new public dataset family;
- no global production claim;
- no automatically generated successor architecture campaign.

Current-head qualification and live evidence are mandatory for every capability represented as live. Missing evidence produces typed unavailability or honest non-promotion. Existing event-driven reassessment and bounded task-frontier refill must be used, and all generated work must remain inside PCPR.

## Canonical handoff and authority

The current product surfaces are Supervisor.run(prompt), the product CLI supervisor run command, and the MCP agent_supervisor_run tool. They share the production facade, but current code fails closed unless a pre-built CompleteLaunchPlan and a StandardSupervisorRuntimeFactory have already been injected. PromptSupervisorService.bootstrap is the lower canonical preview, materialize, and start saga. PlanSupervisorService and PlanRevisionStore are the canonical plan-create and revision authorities.

PCPR-004 must connect these existing components. It may not create a parallel submission service. The repaired path must perform:

1. body-safe prompt capture and objective identity;
2. authenticated caller and repository-scope resolution;
3. current repository, tree, policy, capability, and task-source observation;
4. bounded PromptWorkflowRequest and PlanCreateRequest construction;
5. deterministic scan and evidence collection;
6. goal, subgoal, task, assumption, guarantee, non-goal, proof-obligation, test, budget, and unresolved-question proposal;
7. independent admission with an admitted verdict;
8. authorized PlanRevisionStore application to the existing DuckDB task source;
9. Quack-fenced task-source publication;
10. a separately authorized START operation;
11. linked objective, preview, admission, materialization, lifecycle, and run receipts;
12. the same identities and semantics through Python, CLI, and MCP.

The high-level prompt remains intent, never authority. Apply and start require exact current roots, authorization, expected effects, idempotency, lease, fencing, and event-cursor bindings. A stale or incomplete binding fails closed. No task or adapter may directly edit DuckDB tables.

## Cross-repository authority boundaries

### ipfs_datasets_py

Datasets owns semantic identity, canonical IR, source and derivative lineage, legal, security, intent, UI, and software-contract semantics, proof obligations, formal relationships, semantic ContextPack construction, theorem and solver result validation, source-rights and temporal metadata, and semantic release manifests.

### ipfs_kit_py

Kit owns exact bytes, CID verification, immutable blocks, durable roots, current-root compare-and-swap, WAL, crash recovery, proof-object and receipt storage, ContextPack storage, retention, tombstones, invalidation records, and optional replication.

Kit must not decide whether a proof is valid, whether a task is complete, whether a result may be reused, whether an execution is permitted, or what semantic bytes mean.

### ipfs_accelerate_py

Accelerate owns objective and task operational state, task admission, provider and model selection, resource admission, claims, leases, fencing, execution, validation execution, proof and test reuse admission, repair, retry, rescue, merge, reconciliation, terminalization, policy promotion, and rollback.

No repository may silently remint another repository's authoritative identity. No external agent, UI, CLI adapter, MCP client, or sibling supervisor may write directly to DuckDB task tables, Quack owner state, root-pointer tables, policy pointers, current-seal pointers, task terminal state, or release qualification state.

## Source seal

Before materialization, record the exact commit and tree of the portfolio and each of the three source repositories. Each source repository must be clean, its current HEAD must equal the portfolio gitlink or explicit isolated-source binding, and current fetched origin/main must be an ancestor of that HEAD. Recursive sibling submodules are not source authority. A changed source seal requires a fresh inventory and qualification baseline.

The Markdown plan, objective heap, bootstrap board, scheduler configuration, generator, validator, and operator are immutable bootstrap inputs after the seal is committed. Markdown is bootstrap-only. DuckDB becomes authoritative after successful materialization. Quack is the exclusive authenticated state-owner transport. DuckLake is an optional, rebuildable, non-authoritative analytics projection and can never grant scheduling, completion, release, policy, or mutation authority.

## Goal hierarchy and parallel execution

The objective heap defines a root, phase goals, and leaf subgoals:

- PCPR-G000: bounded proof-carrying platform qualification and release;
  - PCPR-G100: supervisor bootstrap, qualification, freeze, and legacy inventory;
  - PCPR-G200: Datasets canonical cutover and solver qualification;
  - PCPR-G300: Kit live storage and durability qualification;
  - PCPR-G400: Accelerate legacy quarantine and live compute qualification;
  - PCPR-G500: shared normative contracts and compatibility vectors;
  - PCPR-G600: clean package and signed release train;
  - PCPR-G700: reference proof-carrying workflow and recovery;
  - PCPR-G800: external Python and MCP interoperability;
  - PCPR-G900: audit package, release gates, closed decision, and residual report.

Each phase contains explicit leaf subgoals in the objective heap. Datasets, Kit, and Accelerate work may proceed in parallel only after the supervisor gate emits either supervisor promotion or an explicit bounded operator override. Shared contracts join the three component paths. Packaging, reference workflow, interoperability, and final release gates consume the exact admitted outputs of their prerequisites. Overlapping files are serialized through the existing merge queue.

## Phase 0: qualify and freeze the supervisor

Before the supervisor acts as release authority, qualify its direct-objective, event-driven planning, and automatic-refill machinery using at least:

- 10 consecutive bounded objectives without manual database edits;
- 20 historical task replays;
- held-out high-level objective decomposition tests;
- owner-loss and restart tests;
- stale-task recovery;
- provider-outcome-unknown reconciliation;
- lease and fencing races;
- event replay and duplicate delivery;
- automatic task-frontier refill;
- incremental plan reassessment;
- ContextPack reuse and invalidation;
- cross-supervisor event handling;
- external Python and MCP submission.

Measure end-to-end input and output tokens, model calls by class, provider cost, CPU and GPU time, wall time, tests, proof obligations, retries, rescues, merge conflicts, human interventions, manual recovery, task churn, plan churn, automatic refill rate, deterministic route share, ContextPack reuse, and final outcome.

Minimum qualification targets are:

- at least 30 percent median end-to-end input-token reduction against the prior Codex-primed route;
- at least 40 percent frontier-model call reduction;
- positive net cost reduction after audit and verification overhead;
- at least 60 percent of eligible decisions resolved without a frontier model;
- at least 80 percent of ordinary task refills performed without an LLM;
- at least 50 percent ContextPack reuse on eligible tasks;
- less than 5 percent unnecessary task churn;
- less than 2 percent manual recovery;
- zero manual task-table edits;
- zero hard safety failures.

If the targets fail, preserve useful telemetry, safety, and interoperability improvements, issue supervisor_non_promoted, and continue only with bounded operator approval. The supervisor must not act as its own release authority. If the targets pass, freeze its public objective, task, event, ContextPack, state-machine, and receipt contracts for PCPR and prohibit competing authorities.

## Phase 1: Datasets canonical cutover

Make the modern typed semantic and proof architecture canonical.

- Import must not set auto-install flags, invoke installers, repair environments, start services, or access networks. Optional dependencies produce typed unavailable results, and installation is an explicit CLI or operator action.
- Remove or quarantine every fallback that returns success without a real effect. Closed statuses include unavailable, unsupported, denied, rejected, simulated, attempted, observed, verified, failed, and compensated. Simulation requires explicit caller selection.
- Make LogicProviderProtocol version 2 or its current successor canonical. Free-form payloads cannot mint executable BackendRequest values. A version 1 adapter is explicit and fail-closed. Advisory data remains non-authoritative and executable work has explicit bounds.
- Publish stable versioned APIs for canonical IR identity, source lineage, ContextPack construction, proof obligations, proof-result validation, translation receipts, interpolation, CEGAR, incremental SMT, and source and rights manifests.
- Put cross-repository schemas and fixtures in package data, immutable vectors, a normative schema location, or a separately versioned contract package. Installed packages cannot depend on an adjacent Datasets tests directory.
- Make LICENSE, pyproject metadata, classifiers, README, wheels, and source distributions agree. AGPL and any intended dual-license authority must be explicit.
- Replace broad None fallbacks with typed errors or outcomes and document stable, beta, experimental, simulation-only, compatibility-only, and unavailable surfaces.
- Run bounded real qualification for Z3, cvc5, one Lean or Coq path, canonical IR round-trip, source-lineage validation, ContextPack identity, one translation receipt, and one proof or counterexample workflow. Missing solvers remain typed unavailable.

## Phase 2: Kit live qualification

Preserve the semantic versus byte authority boundary and qualify:

- the current-head local durable backend for write, read-back, digest, delete, replay, timeout, concurrency, restart, corruption, large objects, credentials, and Python, CLI, MCP, and MCP++ parity;
- a pinned exact IPFS daemon for clean provisioning, add, read-back, digest equality, pin persistence, unpin and deletion, restart, daemon loss, timeout, concurrency, large objects, unexpected content, configuration, interface parity, upgrade, and rollback;
- Iroh with the same bounded suite, or classify it experimental, unavailable, or unsupported and remove live-support claims;
- hermetic VFS plus Linux FUSE, Windows WinFsp, and container FUSE only where real environments exist; WAL recovery, current-root CAS, ARC coherence, crash recovery, stale-root rejection, corruption, and mount lifecycle remain mandatory;
- the proof-seal store for exact bytes, candidate versus current separation, fresh verification before reuse, no public proving-key or witness leakage, WAL, restart, stale-parent rejection, concurrent writers, tombstones, invalidations, and legacy-certificate staging without admission.

Replace sibling test-tree fixtures with immutable normative vectors. Generate one authoritative support matrix using hermetic_qualified, live_qualified, conditional, configuration_only, experimental, unavailable, and unsupported. README claims must be generated from or checked against that matrix.

## Phase 3: Accelerate legacy quarantine

- Move the mock-oriented coordinator behind an explicit compatibility or simulation namespace. The ordinary runtime cannot silently instantiate it.
- Replace fabricated hardware availability with a ladder of declared, installed, detected, canary_passed, model_compatible, resource_sufficient, qualified, and production_authorized. Device visibility, adapter presence, package import, configuration, or testing defaults never imply qualification.
- Remove or quarantine hexadecimal pseudo-CIDs derived from stringified data. Use canonical bytes and real CID generation.
- A registered endpoint is live only when the backend and exact model exist, model load or availability is verified, a real canary and output validation pass, timeout and cancellation are defined, and resource admission succeeds. Explicit simulation receipts say simulation.
- All production actions use the canonical objective service, event state, task state machine, claims, leases, fencing, reconciliation, current validation, and exact receipts.
- Replace mutable VCS branches with immutable commits, exact versions, or signed artifacts.
- Align code, metadata, and CI on the real Python floor.
- Consolidate commands under one stable hierarchy while retaining documented compatibility migration.
- Qualify CPU execution, one real NVIDIA CUDA environment when GPU support is claimed, one real model task, and one real provider or local model-server route. Cover load, inference, output validation, cancellation, timeout, cleanup, insufficient resources or OOM, repeated execution, and exact model, runtime, driver, and hardware identity. If CUDA is unavailable, issue a blocker or a CPU-only candidate with no GPU claim.

## Phase 4: shared contracts

Stabilize one normative source for:

- SupervisorObjectiveIntent;
- ObjectiveMaterializationReceipt;
- SupervisorContextPack;
- SemanticArtifactIdentity;
- DurableArtifactReceipt;
- ProofObligation;
- ProofResult;
- ProofAdmissionDecision;
- ExecutionInvocation;
- ExecutionReceipt;
- SupervisorEvent;
- TaskStateTransition;
- ReleaseComponentManifest;
- PortfolioCompatibilityManifest.

Each contract requires an exact schema version, canonicalization, unknown-field policy, integer and numeric limits, Unicode and ordering rules, CID rules, positive and negative vectors, exact canonical-byte and CID vectors, and cross-language tests where applicable. Repositories cannot redefine these contracts independently; bindings should be generated from one normative source where practical.

## Phase 5: clean installation and release train

Produce one exact release candidate per repository with a signed Git tag, source distribution, wheel, checksums, SBOM, build provenance, dependency lock, supported Python and platform matrices, capability matrix, schema and interface versions, migration and rollback notes, current-head qualification receipt, and known limitations.

Every clean install must work without sibling source trees, recursive submodules, editable local dependencies, implicit sys.path injection, network installation during import, or mutable Git dependencies. Record source commit and tree, build command, Python and build-tool versions, native dependencies, wheel and source-archive digests, and relevant container digests.

Create one signed proof-carrying-platform-0.1.0 compatibility manifest binding every repository version, commit, tree, and artifact; all contract versions and schema roots; supported capability combinations; exact test-suite, SBOM, and qualification-receipt identities.

Where permissions allow, protect default branches and release tags and require current-head and release checks. Otherwise emit an explicit operator-blocking task and never represent the governance gate as complete. A partial required-build failure prohibits release publication.

## Phase 6: reference end-to-end workflow

The reference objective is:

    Modify a typed formal-logic API while reusing unaffected proofs,
    selecting only impacted tests, rejecting stale-tree evidence, and
    producing a complete proof-carrying execution receipt.

The sequence must start from only that high-level idea through the repaired direct interface:

1. authenticate the caller, validate authority, and materialize the objective, goals, tasks, assumptions, guarantees, acceptance conditions, and budgets;
2. have Datasets inspect semantic impact, files, symbols, interfaces, schemas, proof obligations, tests, contracts, and receipts, then construct and identify the minimal ContextPack;
3. have Kit verify and store exact ContextPack bytes, publish the current root through CAS, record storage and transition receipts, restart, and re-open with verification;
4. have Accelerate route through exact valid receipts, AST and dependency analysis, schema, type, and static checks, selected tests, incremental prover, then a named small specialist and finally a larger model only when necessary;
5. create a bounded PatchPlan, modify only authorized paths, run selected tests and proofs, fall back to full validation when selection is incomplete, and record exact outputs;
6. introduce an unrelated documentation change and demonstrate eligible ContextPack, proof, and test reuse without whole-plan regeneration;
7. introduce a relevant interface change and demonstrate stale receipt and ContextPack rejection, minimal impacted cone, plan-epoch increment, PlanDelta, preserved unaffected completion, and automatic frontier refill;
8. restart the authoritative state owner and prove exact reconstruction, duplicate-effect rejection, safe lease and fence retention or expiry, and continuation without database edits;
9. have Datasets independently validate the proof or counterexample, Kit durably store final artifacts, and Accelerate terminalize only after current admitted validation;
10. emit the objective CID, ContextPack CID, plan-epoch history, task, proof, storage and execution receipts, event DAG, release compatibility identity, and final result CID.

## Phase 7: external interoperability

Use a Python client and a generic MCP client. A third existing CLI, MCP++, or agent client is optional. Each required client submits the same canonical objective, receives the same objective identity and equivalent plan semantics, subscribes to events, inspects task state, submits candidate evidence, and retrieves final receipts. At least one generic MCP client must execute the complete high-level objective path.

Negative tests prove that external clients cannot directly update or terminalize tasks, forge policy, bypass confirmation, leases, or fencing, broaden scope, write current roots or policy pointers, or promote themselves.

## Phase 8: audit-ready package and release decision

Prepare a reproducible external-review package for:

    objective submission
    -> authentication and authority
    -> planning and ContextPack
    -> task state machine
    -> execution admission
    -> proof and test admission
    -> receipt
    -> release decision

Include architecture diagrams, threat model, trusted computing base, state machine, authority model, canonicalization and CID vectors, event, lease, fencing, unknown-outcome, confirmation, and proof-admission models, build provenance, negative tests, known limitations, and exact reproduction commands.

The only permitted status is external_audit_ready. Never claim externally_audited without an independently identified reviewer.

## Truth invariants

1. No simulated observation may be represented as live.
2. No estimated metric may be represented as measured.
3. No attempted operation may be represented as observed.
4. No observed operation may be represented as verified without admitted verifier evidence.
5. No present CID may be represented as proof authority.
6. No stored proof may be represented as an admitted proof.
7. No cache hit may be reused against a different tree, policy, objective, schema, interface, toolchain, or relevant environment.
8. No missing capability may silently fall back to a mock.
9. No unavailable backend may be advertised as available.
10. No mock endpoint may be advertised as a real endpoint.
11. No SHA-256 hexadecimal string may be advertised as an IPFS CID.
12. No absent dependency may be automatically installed during package import.
13. No unavailable operation may return `status: success`.
14. No test or validation failure may be converted into a warning for release.
15. No task may complete solely from an LLM assertion.
16. No provider-outcome-unknown may enter blind retry.
17. No stale lease or fence may complete.
18. No client-supplied policy `allow` or confirmation is authoritative.
19. No package may depend on a mutable Git branch in a qualified release.
20. No package test may require an uninstalled sibling source-tree `tests/` directory.
21. No release may be published after partial required-build failure.
22. No production claim may be inferred from hermetic fixtures alone.
23. No legal, security, model, provider, or data capability may be described more broadly than its current qualification receipt.
24. No policy promotion may be self-authorized.
25. An empty task queue does not prove objective satisfaction.

The following counters must remain zero:

- false completions;
- unauthorized mutations;
- simulated-as-live outcomes;
- stale cache admissions;
- stale ContextPack admissions;
- stale lease completions;
- stale fence completions;
- double execution;
- double terminalization;
- confirmation replays;
- path or scope escapes;
- hidden validation reductions;
- accepted critical controlled omissions;
- selected-test false negatives in release qualification;
- self-authorized promotions;
- release creation after failed required gates.

## Token and compute policy

Record objective-materialization, planning, implementation, validation, replan, and explanation tokens; calls by model class; provider costs; CPU and GPU seconds; test and prover time; ContextPack build and retrieval; proof and test reuse; retries; rescues; merges; human interventions; and final outcome.

Use this escalation order:

    exact receipt
    -> AST and dependency analysis
    -> schema, type, and static checks
    -> selected tests
    -> incremental prover
    -> local small specialist
    -> medium model
    -> frontier model
    -> human decision

Every escalation carries a typed unresolved question. A model call is prohibited when its answer cannot alter an admissible decision. Efficiency never weakens validation, proof obligations, selected-test recall, safety, or release evidence.

Budget ceilings:

- maximum initial tasks: 80;
- maximum total tasks without operator scope expansion: 140;
- maximum replan epochs: 20;
- maximum automatically generated tasks per refill: 12;
- frontier-model calls: explicitly budgeted and minimized by the admitted plan;
- final validation reserve: at least 30 percent of token and compute budgets.

The 66 blueprint packages may be materialized as the initial admitted direct-objective plan after PCPR-004; the 12-task limit applies to later automatic refills. Every refill is append-only, content-addressed, deduplicated, evidence-bound, and scope checked. Seed tasks are immutable. Empty-queue scans cannot grant completion.

## Bootstrap package

PCPR-004 Repair and qualify the canonical direct-objective submission path is not one of the supplied blueprint packages. It is the sole executable bootstrap task and exists only because the current direct prompt facade cannot yet derive and launch a real admitted plan from a high-level idea. Its only purpose is to repair that existing canonical handoff. Its detailed contract is in the immutable bootstrap board.

After PCPR-004 passes, the bootstrap agent must submit the exact root idea and constraints through the repaired public interface. The resulting objective materialization receipt becomes the PCPR campaign submission event. Any omitted critical requirement must be added through the canonical objective-revision interface.

## Required 66-package blueprint

| ID | Exact required title |
| --- | --- |
| PCPR-000 | Seal repositories, contracts, policies, and supervisor baseline |
| PCPR-001 | Qualify direct objective and event-driven supervisor |
| PCPR-002 | Freeze canonical supervisor contracts or issue non-promotion |
| PCPR-003 | Inventory every legacy bypass and false-authority path |
| PCPR-010 | Remove Datasets import-time auto-install |
| PCPR-011 | Remove Datasets false-success fallbacks |
| PCPR-012 | Make typed outcomes canonical |
| PCPR-013 | Canonicalize LogicProviderProtocol |
| PCPR-014 | Stabilize semantic APIs and ContextPack contract |
| PCPR-015 | Package schemas and shared vectors |
| PCPR-016 | Resolve Datasets license metadata |
| PCPR-017 | Qualify real Datasets solver paths |
| PCPR-020 | Requalify local Kit backend |
| PCPR-021 | Qualify pinned IPFS backend |
| PCPR-022 | Qualify or de-scope Iroh |
| PCPR-023 | Qualify VFS/WAL/current-root recovery |
| PCPR-024 | Qualify proof-seal store |
| PCPR-025 | Remove sibling test-tree coupling |
| PCPR-026 | Qualify Python/CLI/MCP/MCP++ parity |
| PCPR-027 | Generate authoritative support matrix |
| PCPR-030 | Quarantine Accelerate legacy mock coordinator |
| PCPR-031 | Remove fabricated hardware capability |
| PCPR-032 | Remove pseudo-CID identity |
| PCPR-033 | Remove fabricated endpoint success |
| PCPR-034 | Consolidate capability ladder |
| PCPR-035 | Pin mutable dependencies |
| PCPR-036 | Correct Python compatibility metadata |
| PCPR-037 | Qualify CPU execution |
| PCPR-038 | Qualify real CUDA execution |
| PCPR-039 | Qualify one real model/provider path |
| PCPR-040 | Stabilize shared contracts |
| PCPR-041 | Add canonical-byte and CID vectors |
| PCPR-042 | Add negative and cross-language vectors |
| PCPR-043 | Add cross-repository compatibility checks |
| PCPR-050 | Build clean Datasets package |
| PCPR-051 | Build clean Kit package |
| PCPR-052 | Build clean Accelerate package |
| PCPR-053 | Produce dependency locks |
| PCPR-054 | Produce SBOMs and provenance |
| PCPR-055 | Produce signed tags and artifacts |
| PCPR-056 | Produce portfolio compatibility lock |
| PCPR-057 | Add branch and release gates |
| PCPR-060 | Submit reference high-level objective |
| PCPR-061 | Build semantic ContextPack |
| PCPR-062 | Persist and publish current ContextPack root |
| PCPR-063 | Execute deterministic-first route |
| PCPR-064 | Produce bounded patch |
| PCPR-065 | Run selected tests and proofs |
| PCPR-066 | Introduce unrelated state change |
| PCPR-067 | Demonstrate safe reuse |
| PCPR-068 | Introduce relevant interface change |
| PCPR-069 | Demonstrate stale rejection and PlanDelta |
| PCPR-070 | Restart authoritative state owner |
| PCPR-071 | Demonstrate recovery and idempotency |
| PCPR-072 | Produce final proof-carrying receipt chain |
| PCPR-080 | Add Python external-client demonstration |
| PCPR-081 | Add generic MCP-client demonstration |
| PCPR-082 | Prove cross-client objective identity parity |
| PCPR-083 | Prove external clients cannot bypass authority |
| PCPR-090 | Prepare threat model |
| PCPR-091 | Prepare trusted-computing-base inventory |
| PCPR-092 | Prepare security and correctness audit package |
| PCPR-093 | Run release-candidate gate |
| PCPR-094 | Produce promotion or honest non-promotion receipt |
| PCPR-095 | Publish residual-gap report |
| PCPR-096 | Recommend the next customer or synthetic pilot |

## Release-candidate gates

Supervisor gates require working direct submission, automatic reassessment and refill, zero manual database repair, promotion or explicit bounded operator override, and exact current-head evidence.

Datasets gates require inert import, no default auto-install or false success, canonical typed provider protocol, consistent licensing, packaged schemas, recorded real solver qualification, and typed unavailability for missing solvers.

Kit gates require current-head local durability; live evidence for every live backend; qualified IPFS if claimed; Iroh qualified or removed from live claims; VFS, WAL, root, and proof-store qualification; and no adjacent test-tree dependency.

Accelerate gates require no default mock hardware, pseudo-CID, or fabricated endpoint authority; the real capability ladder; qualified CPU; CUDA evidence if GPU support is claimed; a qualified model/provider path; immutable release dependencies; and accurate Python metadata.

Packaging gates require clean installs, exact locks, SBOMs, provenance, signed artifacts, the exact compatibility manifest, no partial publication, and current-head release checks.

Reference-workflow gates require direct high-level submission, ContextPack and storage root, deterministic-first execution, selected tests and proofs, unrelated-change reuse, relevant-change invalidation, PlanDelta and refill, restart recovery, and the complete receipt chain.

Interoperability gates require Python and generic MCP clients, identical objective identity, equivalent semantics, and no authority bypass.

Every hard-zero counter is a release blocker.

## Closed release outcomes

The final decision must use exactly one of:

- release_candidate_qualified;
- non_promoted_supervisor_unqualified;
- non_promoted_import_or_false_success;
- non_promoted_live_storage_gap;
- non_promoted_live_compute_gap;
- non_promoted_solver_gap;
- non_promoted_packaging_gap;
- non_promoted_dependency_reproducibility;
- non_promoted_security_failure;
- non_promoted_interoperability_gap;
- non_promoted_reference_workflow_failure;
- non_promoted_unmeasured;
- non_promoted_operator_gate_required.

Board complete, mostly complete, and nearly production are not release outcomes. Release qualification requires admitted current-tree evidence.

## Required deliverables

1. Exact repository commits and trees.
2. Supervisor qualification receipt.
3. Legacy-path inventory and dispositions.
4. Canonical architecture decision records.
5. Stable shared schemas and vectors.
6. Datasets qualification report.
7. Kit support matrix and backend receipts.
8. Accelerate capability and execution matrix.
9. Clean package artifacts.
10. Dependency locks.
11. SBOMs.
12. Build provenance.
13. Signed tags or explicit operator-blocked status.
14. Portfolio compatibility manifest.
15. Reference workflow event and receipt DAG.
16. Python interoperability report.
17. MCP interoperability report.
18. Negative authority-bypass report.
19. Audit-ready package.
20. Final release decision.
21. Residual-gap report.
22. Recommended next pilot.

## Completion criteria

The campaign completes only when:

1. the supervisor has a qualified or explicitly bounded status;
2. modern typed paths are canonical;
3. legacy false-success and false-capability paths are removed or explicitly quarantined;
4. every live claim has live evidence;
5. every unavailable capability remains visibly unavailable;
6. clean packages install without sibling source trees;
7. no qualified dependency points to mutable main;
8. exact release artifacts exist or an exact blocking reason is recorded;
9. the reference workflow succeeds or emits an honest failure receipt;
10. the workflow survives state-owner restart;
11. receipt reuse and stale-receipt rejection are both demonstrated;
12. Python and MCP clients use the same canonical service;
13. external clients cannot bypass authority;
14. the audit package is reproducible;
15. the final decision uses the closed vocabulary;
16. the supervisor does not expand beyond PCPR.

The residual-gap report cannot automatically generate another architecture campaign.

## Supervisor health and non-stall checks

Starting a process is not sufficient. The handoff agent must observe at least two bounded status samples after launch. Readiness requires:

- the Quack state owner is alive, ready, and identity-consistent;
- the supervisor master is alive and bound to the expected owner generation;
- expected lane supervisors and implementation daemons are alive with fresh projections;
- executor bootstrap is admitted and ready;
- authoritative task state is queryable;
- blocked count is zero at bootstrap;
- PCPR-004 is dependency-ready or active;
- heartbeat age remains fresh and an event cursor, task state, attempt, or progress receipt advances;
- no fatal, quarantine, unknown-outcome blind retry, or authority-fallback event appears.

Recovery uses only the canonical lifecycle, reconciliation, retry, rescue, or PlanDelta interfaces. Manual SQL and direct task-table edits are prohibited.

## Final operator report

Report exact changed commits for all repositories; supervisor and board status; selected canonical paths; legacy dispositions; import and fallback behavior; live storage, compute, and solver results; clean installs; dependency reproducibility; package hashes; SBOM and compatibility identities; objective and ContextPack identities; plan epochs; task and event history; proof and test reuse; stale-receipt rejection; restart recovery; Python and MCP interoperability; negative authority tests; token, model-call, compute, cost, and human-intervention totals; final closed outcome; residual gaps; and the evidence-supported deployment class.

Permitted deployment classes are further internal development only, controlled engineering pilot, private customer pilot, external security review, public beta, and production use. Never claim a class above the admitted evidence.

## Initially unresolved operator questions

- Whether repository permissions allow branch protection and protected signed tags.
- Whether a live NVIDIA CUDA host is available; absence forces a blocker or CPU-only candidate.
- Whether Iroh, Linux FUSE, Windows WinFsp, container FUSE, Lean, Coq, cvc5, and Z3 live environments exist.
- Which signing identity may authorize release tags and portfolio manifests.
- Which provider or local model server is approved for the real model path.
- Whether a non-promoted supervisor receives a bounded operator override.
- Which independent reviewer may later change external_audit_ready to externally_audited.

These questions create typed operator gates. They never authorize broader scope or indefinite blocking.
