# MCP++ Risk, Neighborhood Coordination, and Distributed Scheduling Plan

Status: proposed implementation plan
Created: 2026-07-12
Scope: SwissKnife virtual desktop, `ipfs_accelerate_py`, `ipfs_datasets_py`,
`ipfs_kit_py`, and the MCP++ HTTP/libp2p interoperability surface

## Objective

Turn the current non-normative risk, neighborhood-consensus, and scheduling
guidance into an optional, interoperable MCP++ extension that lets multiple
MCP++ peers execute goal-derived work in parallel without double execution,
unbounded retries, or a global coordinator.

The target system must:

1. Derive a durable task graph from goals, subgoals, and Tree-of-Thought
   candidate plans.
2. Schedule ready tasks fairly and efficiently across multiple daemon peers.
3. Bind each task, claim, risk input, decision, and result to CIDs and Profile
   F Event DAG provenance.
4. Enforce Profile C UCAN authority and Profile D policy before a peer claims
   or executes work.
5. Use neighborhood agreement to improve placement and resolve duplicate
   claims, while avoiding a claim that it is global consensus.
6. Work equivalently through MCP++ HTTP and `/mcp+p2p/1.0.0` libp2p sessions.
7. Provide operator-visible status and controls in the SwissKnife Agent
   Supervisor desktop app.

## Draft Review

The published working draft intentionally describes risk scoring,
locality-sensitive grouping, priority frontiers, Fibonacci heaps, and
neighborhood agreement at a high level. It explicitly leaves scheduling
non-normative and says neighborhood coordination is not a global-consensus
requirement. The local draft has stronger Profile F retention semantics than
the public branch, but the risk/scheduling chapter is still only a short
conceptual note.

This plan preserves that design boundary. The extension is **Profile G: Risk,
Neighborhood Coordination, and Scheduling** with capability key
`mcp++/risk-scheduling`. No service may advertise the key until its models,
JSON-RPC/REST bindings, HTTP/libp2p proof, and cross-language vectors are
complete.

## Current Inventory

| Area | Existing asset | Limitation to close |
| --- | --- | --- |
| SwissKnife | `src/services/mcp/mcp-scheduler.ts` calculates Event-DAG risk and runs an in-memory binary-heap scheduler. | No durable task graph, remote claims, lease protocol, peer membership, or protocol evidence. |
| SwissKnife UI | `web/js/apps/agent-supervisor.js` and `agent-supervisor-console-gateway.ts` model goals, subgoals, taskboard links, and governed commands. | Browser health is live, but scheduling state is not reconciled from a multi-peer protocol. |
| `ipfs_accelerate_py` | `mcp_server/mcplusplus/risk_scheduler.py` has deterministic actor risk records and a frontier; the agent supervisor creates Fibonacci-prioritized objective bundles and isolated daemon lanes. | The frontier is process-local and task claims are not CID-native, lease-safe, or interoperable with the other services. |
| `ipfs_accelerate_py` | `mcp_server/mcplusplus/task_queue.py` and `workflow_scheduler.py` wrap P2P queue/workflow functionality. | They need one canonical task schema, explicit scheduling receipts, UCAN/policy gates, and MCP++ HTTP/libp2p exposure. |
| `ipfs_datasets_py` | P2P workflow/task-queue engines, consensus mechanisms, formal logic, and provenance persistence are available. | Consensus/reputation code is domain-oriented and has no signed, privacy-aware scheduling-attestation contract. |
| `ipfs_kit_py` | `fibonacci_heap.py`, daemon managers, and content-addressed storage integration exist. | It is not yet the durable archive/lease/artifact substrate for distributed task coordination. |

## Architecture Decisions

### 1. Separate planning, authorization, scheduling, and execution

These concepts must remain distinct:

- A **goal** is a desired outcome.
- A **subgoal** refines a goal and records its parent goal CID.
- A **plan branch** is a Tree-of-Thought candidate. It is advisory until
  selected and must never itself grant authority.
- A **task** is a concrete, idempotent work item derived from a selected branch.
- A **claim** is a time-bounded request by a peer to execute one task.
- A **lease** is the accepted claim with an expiry and fencing token.
- An **execution** is a Profile B envelope with Profile C/D authorization and
  Profile F events/receipts.

Task execution is forbidden unless the task is dependency-ready, the claim
lease is current, the UCAN capability is valid, and the Profile D decision is
allow or allow-with-obligations.

### 2. Canonical CID-native artifacts

All implementations must canonicalize the following DAG-JSON artifacts with
an explicit schema version and CIDv1 `sha2-256`:

| Artifact | Required links |
| --- | --- |
| `Goal` | parent goal CIDs, objective text commitment, owner DID, policy CID |
| `Subgoal` | goal CID, decomposition method, selected-plan CID |
| `PlanBranch` | subgoal CID, candidate inputs, score explanation, evaluator CID |
| `TaskSpec` | subgoal CID, plan CID, interface CID, tool, input CID, dependencies, idempotency key, resource class, deadline |
| `RiskEvidence` | observed event/receipt/decision CIDs, scoring-model CID, redaction classification |
| `RiskAssessment` | task CID, score, factor vector, evidence CIDs, model CID, expiry |
| `NeighborhoodRecord` | peer DID, capabilities, capacity commitment, interface/tool affinities, signed health evidence, expiry |
| `ScheduleProposal` | task CID, candidate peers, deterministic ranking inputs, policy CID, risk assessment CID |
| `TaskClaim` | task CID, claimant DID, lease duration, fencing token, capability/proof CIDs, proposal CID |
| `ClaimResolution` | accepted claim CID or deterministic conflict result, attestation CIDs, retry/backoff |
| `TaskReceipt` | Profile B receipt CID, claim CID, output CID, resource use, failure class, next-state |

The task CID is immutable. Retry attempts create new claim and receipt CIDs
linked to the same task CID; they do not mutate task history.

### 3. Risk scoring is deterministic, explainable, and versioned

Risk is not a free-form reputation number. A scheduler computes a score in
`[0,1]` from a versioned `RiskModel` CID and a bounded set of verified evidence:

- Profile D denials, policy violations, and overdue obligations.
- Profile C failures, revoked delegations, and unauthorised attempts.
- Profile B failure classes, retries, timeouts, and resource overruns.
- Profile F disputes, rollbacks, archive inclusion evidence, and bounded causal
  history.
- Capacity/health evidence only when it is signed by the reporting peer and
  within its stated freshness interval.

The model defines factor weights, saturation, confidence, missing-evidence
handling, and a maximum history budget. Results include the factor vector and
evidence CIDs. High-risk or low-confidence tasks require a policy-defined
approval or a smaller, more trusted neighborhood; they must not silently be
deprioritized into starvation.

### 4. Neighborhood agreement is placement coordination, not global truth

A neighborhood is a deterministic, bounded candidate set derived from:

- compatible MCP-IDL interface CID and tool capability,
- resource class and signed capacity/health record,
- data locality and required artifact reachability,
- policy/trust domain,
- optional LSH/k-nearest-neighbor hints.

LSH and embeddings are local performance optimizations only. The canonical
neighborhood result must contain explicit peer DIDs, descriptor CIDs, and the
selection-policy CID so independent peers can reproduce or challenge it.

Peers exchange signed attestations for a scheduling proposal. Quorum means
"sufficient placement confidence"; it never establishes global ordering or
overrides UCAN/policy checks. A task may proceed without quorum only when its
policy allows unilateral execution and the task is idempotent.

### 5. Leases prevent duplicate execution

The protocol uses optimistic claims with fencing tokens:

1. A peer publishes a `TaskClaim` with a logical epoch, expiry, and proof CID.
2. Peers validate authority, policy, task state, and claimed capacity.
3. Conflicting valid claims are resolved by a deterministic tuple such as
   `(logical_epoch, risk_bucket, capability_fit, expected_finish, claimant_did,
   claim_cid)`; ties are lexical and documented.
4. The winner obtains a lease; losing claims become conflict events, not hidden
   queue mutations.
5. A worker renews before expiry and includes the fencing token in every
   execution envelope and receipt.
6. The executor rejects stale tokens. After expiry, another peer may claim the
   task and records the takeover in the Event DAG.

Wall-clock timestamps are advisory. Conflict ordering must use the task's
logical epoch and Event DAG parents so clock skew cannot create an authoritative
winner.

### 6. Fibonacci heaps are local implementation details

`ipfs_kit_py` and the agent supervisor may use a Fibonacci heap where frequent
priority updates make `decrease-key` useful. The distributed protocol does not
serialize heap nodes or depend on a particular heap implementation. Every peer
derives the same sortable priority tuple from canonical artifacts, then uses its
own efficient local queue implementation.

The priority tuple must include dependency readiness, deadline class,
risk-action, fairness/aging, expected value, resource fit, retry backoff, and
a stable task-CID tie-breaker. Aging is mandatory so low-value safe work cannot
starve forever. A peer's local priority update creates a `ScheduleProposal` or
  `RiskAssessment` event; it is not an opaque queue mutation.

### 7. Canonical-provider reuse and fallback order

The Python backends must not duplicate specialist engines merely because they
need their results. Each operation declares a provider chain and records the
provider used in its receipt:

| Domain | Canonical owner | Python fallback order | Failure behavior |
| --- | --- | --- | --- |
| formal logic, policy-aware risk factors, ToT selection validation | `ipfs_datasets_py` | package import; versioned datasets CLI JSON contract; datasets MCP++ operation | fail closed for claims/execution; planning may remain explicitly pending |
| daemon capacity, task execution, worktree/goal bundle lifecycle | `ipfs_accelerate_py` | package import; accelerator CLI JSON contract; accelerator MCP++ operation | do not issue a claim without fresh capacity evidence |
| CID persistence, archive/retrieval, durable lease recovery indexes | `ipfs_kit_py` | package import; kit CLI JSON contract; kit MCP++ operation | retain pending state; do not acknowledge durable completion |

SwissKnife retains its pure TypeScript implementation for client-side
validation, display, deterministic priority calculation, and conformance tests.
It does not require Python to render or validate the wire contract. Every
fallback must identify the canonical schema/model version and return the same
CIDs; a fallback that changes semantics is not permitted.

## Proposed MCP++ Profile G Surface

### Capability negotiation

Clients request `capabilities.experimental["mcp++/risk-scheduling"] = true`.
Servers return it only when they expose the versioned surface below. Initialize
metadata must include `profile_name`, `artifact_schema_versions`,
`risk_model_cids`, `lease_clock`, maximum history/neighbor bounds, and supported
transport modes.

### JSON-RPC and REST bindings

| Operation | JSON-RPC | REST | Notes |
| --- | --- | --- | --- |
| profile metadata | `mcp++/risk/profile` | `GET /mcp/risk/profile` | model and limits |
| goal graph | `mcp++/goals/{create,get,list,decompose,select}` | `/mcp/goals/...` | selected ToT branch only becomes actionable |
| task graph | `mcp++/tasks/{create,get,list,ready}` | `/mcp/tasks/...` | CID-native immutable task specs |
| risk | `mcp++/risk/{assess,evidence,history}` | `/mcp/risk/...` | bounded, redacted evidence |
| neighborhood | `mcp++/neighborhood/{query,attest}` | `/mcp/neighborhood/...` | signed membership and attestation |
| scheduling | `mcp++/schedule/{propose,claim,renew,release,resolve}` | `/mcp/schedule/...` | leases and deterministic conflicts |
| queue state | `mcp++/schedule/{frontier,status,reconcile}` | `/mcp/schedule/...` | diagnostics and recovery |

Every mutating request must accept `proof_cid`/UCAN material, `policy_cid`,
`parents[]`, `correlation_id`, and an idempotency key. Responses return CIDs for
the emitted event, decision, claim/lease, and receipt. Equivalent operations
must work over Profile E without translating JSON-RPC method names or payloads.

### Event types

Profile F events add canonical types: `goal_created`, `goal_decomposed`,
`plan_branch_proposed`, `plan_branch_selected`, `task_created`,
`risk_assessed`, `neighborhood_attested`, `schedule_proposed`, `task_claimed`,
`lease_renewed`, `claim_conflicted`, `claim_expired`, `task_completed`,
`task_failed`, and `task_reconciled`.

## Responsibilities by Repository

### SwissKnife

- Implement the canonical TypeScript artifact codecs, priority tuple, risk
  model evaluator, lease/fencing validation, and Profile G connector methods.
- Extend the MCP++ Explorer and Agent Supervisor to show real goals, subgoals,
  plan branches, tasks, queue frontier, neighborhood peers, leases, risk
  explanation, and DAG links from the live gateway.
- Keep Tree-of-Thought prompts and candidate branches operator-reviewable;
  selecting a branch requires the configured Profile C/D authority path.
- Add ORB/IDL descriptors for read-only scheduling telemetry and separately
  governed claim/cancel/steering commands. Meta glasses receive summaries and
  approvals, never unrestricted daemon controls.

### ipfs_accelerate_py

- Make the objective graph, backlog refinery, bundle supervisor, implementation
  daemons, and local Fibonacci-priority heap emit/consume the canonical artifacts.
- Adapt P2P task queues and workflow scheduler to claims, leases, fencing,
  idempotency, retry budgets, and remote capacity records.
- Run worker daemons only after accepted claims, persist progress/heartbeat
  receipts, and publish resource telemetry with explicit freshness bounds.

### ipfs_datasets_py

- Own the reusable policy-aware goal/task schema validators, formal-logic rule
  integration, dataset/provenance storage, and deterministic risk-model vectors.
- Adapt consensus mechanisms into signed scheduling attestations with explicit
  quorum policy, conflict records, confidence calibration, and privacy/redaction.
- Supply dataset/vector/LSH lookup as an optional neighborhood candidate source,
  never as the sole canonical membership decision.

### ipfs_kit_py

- Persist and retrieve task, lease, risk, and scheduling artifacts through
  Helia/IPFS with content integrity, pin/retention policy, and archive support.
- Provide daemon health/capacity evidence, artifact reachability checks, and
  durable lease/claim indexes where local recovery needs fast lookup.
- Keep its Fibonacci heap as a local queue optimization behind the shared
  priority-tuple contract.

## Phased Delivery

### Phase 0: Contract and threat-model review

Define what a task is allowed to claim, which operations are idempotent, how
leases are bounded, which telemetry is sensitive, and how a peer can challenge
bad risk/attestation data. This phase must settle the Profile G name, wire key,
artifact schemas, and whether any operation needs a stronger coordination
backend for a particular policy domain.

### Phase 1: Canonical artifacts and local parity

Implement codecs and deterministic vectors in TypeScript and Python. Port the
existing goal/subgoal/ToT, risk, and Fibonacci scheduling concepts to the
shared schemas without changing daemon behavior yet. Verify CID equivalence,
priority equivalence, and denial behavior across all implementations.

### Phase 2: Gateway and transport support

Expose the Profile G methods through all three MCP++ adapters and the native
Python servers. Add HTTP and libp2p request/response parity tests, including
malformed/oversized frame handling and rejected stale leases.

### Phase 3: Multi-peer execution

Run at least three independently started peers. Demonstrate goal decomposition,
task publication, placement, duplicate-claim conflict, lease renewal, executor
crash, takeover, result reconciliation, and event-DAG audit without a shared
memory queue.

### Phase 4: Throughput, fairness, and UI

Measure throughput, latency, resource utilization, duplicate execution rate,
fairness, and recovery time against a single-supervisor baseline. Ship the
live SwissKnife UI and operator controls only after protocol evidence is green.

## Acceptance Matrix

| Concern | Required proof |
| --- | --- |
| Cross-language artifact parity | TypeScript, accelerator, datasets, and kit create byte/CID-identical fixtures. |
| Authority | Invalid/revoked UCAN or denied Profile D decision prevents claim, renewal, and execution. |
| Idempotency | Repeated create/claim/complete calls with the same key yield the same artifact or a harmless already-exists result. |
| Duplicate claims | Concurrent peers select one deterministic lease winner; losers cannot execute using stale fencing tokens. |
| Recovery | A crashed claimant expires; another peer takes over with an Event DAG lineage and no lost task. |
| Network parity | Every Profile G operation has identical semantic results through HTTP and libp2p. |
| Bounded state | Frontier/history/neighborhood/risk queries enforce limits and return archive boundaries/CIDs. |
| Privacy | Sensitive raw task content and telemetry are not leaked in neighborhood/risk broadcasts; redaction is testable. |
| Performance | Multi-peer benchmark demonstrates a pre-agreed throughput gain without exceeding duplicate, starvation, or policy-bypass thresholds. |
| UI | Agent Supervisor displays live state, errors, leases, proofs, receipts, and fallback decisions; it never presents sample data as live. |

## Metrics and Release Gates

The release gate must publish, at minimum:

- ready/running/blocked/completed task counts by goal and peer,
- queue wait, execution latency, retry count, and lease takeover latency,
- throughput and resource utilization per daemon/resource class,
- duplicate-claim and duplicate-execution rates,
- risk-score distribution, challenge rate, policy denial rate, and false
  positive/negative review samples,
- neighborhood size, quorum success, attestation disagreement, and partition
  recovery outcomes,
- CID/receipt/Event DAG coverage for every completed task,
- HTTP/libp2p conformance results for every configured service.

The system is NO_GO when a required task can run without a valid lease,
UCAN/policy decision, or traceable receipt; when a stale claim can execute; when
transport behavior differs; or when benchmark gains rely on silently dropping
work, bypassing policy, or hiding duplicate execution.

## Taskboard

## SVD-080 Profile D HTTP and libp2p transport parity prerequisite

- Status: completed
- Priority: P0
- Track: mcp
- Depends on: none
- Outputs: `swissknife/test-results/virtual-desktop-ipfs-mcp-orb/profile-d-policy-http-libp2p.json`
- Acceptance: Completed in the parent virtual-desktop taskboard. Profile G work
  starts only after the three backend services have matching Profile D results
  over HTTP and libp2p.

## SVD-082 Define Profile G contract, threat model, provider chains, and conformance vectors

- Status: completed
- Priority: P0
- Track: specification
- Depends on: SVD-080
- Outputs: `Mcp-Plus-Plus/docs/spec/risk-scheduling.md`,
  `Mcp-Plus-Plus/docs/spec/mcp++-profiles-draft.md`,
  `Mcp-Plus-Plus/conformance/vectors/profile_g_*.json`
- Acceptance: The optional capability, artifact schemas, method/REST bindings,
  lease semantics, conflict tuple, bounds, error codes, security model, and
  package-import/CLI/MCP fallback rules are reviewed and represented by
  valid/invalid vectors.

## SVD-083 Implement canonical goal/task/risk/lease codecs and vectors

- Status: completed
- Priority: P0
- Track: shared-runtime
- Depends on: SVD-082
- Outputs: TypeScript and Python canonical codec modules, fixture runners, CID
  parity evidence.
- Acceptance: All four implementations agree on CIDs, priority tuples, and
  validation failures for the shared vector corpus.

## SVD-084 Add datasets-backed goal decomposition and scheduling attestations

- Status: waiting
- Priority: P0
- Track: datasets
- Depends on: SVD-082, SVD-083
- Outputs: `ipfs_datasets_py` goal/plan validators, risk evidence store,
  signed neighborhood attestation engine, Profile G server methods.
- Acceptance: ToT branches remain non-authoritative until selected; bounded,
  redacted, policy-aware attestations are reproducible from CIDs.

## SVD-085 Adapt accelerator agent supervisor and daemon lanes to leases

- Status: waiting
- Priority: P0
- Track: accelerator
- Depends on: SVD-083, SVD-084
- Outputs: goal-bundle/task adapters, claim/renew/release logic, fencing-token
  enforcement, daemon capacity/heartbeat receipts, queue bridge tests.
- Acceptance: Multiple daemon lanes execute only accepted leases, recover from
  expiry, and emit task receipts linked to goals and subgoals.

## SVD-086 Implement IPFS Kit durable coordination storage and recovery

- Status: waiting
- Priority: P0
- Track: storage
- Depends on: SVD-083
- Outputs: IPFS/Helia artifact persistence, claim/lease indexes, retention and
  archive policy, daemon-health records, retrieval tests.
- Acceptance: Every shared coordination artifact remains retrievable by CID
  after restart and Profile F compaction.

## SVD-087 Add SwissKnife Profile G connector and Agent Supervisor UI

- Status: waiting
- Priority: P0
- Track: desktop
- Depends on: SVD-083, SVD-084, SVD-085, SVD-086
- Outputs: TypeScript connector methods, governed gateway mappings, MCP++
  Explorer protocol operations, live Agent Supervisor views, ORB/IDL contracts.
- Acceptance: The desktop displays live multi-peer goals, subgoals, tasks,
  claims, risk explanations, and receipts; mutations are explicit and policy
  governed.

## SVD-088 Expose Profile G through all MCP++ HTTP and libp2p services

- Status: waiting
- Priority: P0
- Track: transport
- Depends on: SVD-084, SVD-085, SVD-086
- Outputs: native/compat server dispatch, REST handlers, Profile E bindings,
  descriptor updates, capability negotiation evidence.
- Acceptance: All listed Profile G methods have semantic HTTP/libp2p parity and
  reject invalid frames, requests, authority, and stale fencing tokens.

## SVD-089 Prove three-peer claim, conflict, takeover, and reconciliation

- Status: waiting
- Priority: P0
- Track: integration
- Depends on: SVD-087, SVD-088
- Outputs: repeatable three-peer test harness, Event DAG evidence, conformance
  report, failure-injection fixtures.
- Acceptance: Tests cover simultaneous claim, partition, replay, restart,
  expired lease takeover, conflicting completion, and idempotent reconciliation.

## SVD-090 Benchmark throughput, fairness, and fault recovery

- Status: waiting
- Priority: P1
- Track: performance
- Depends on: SVD-089
- Outputs: benchmark suite, baseline comparison, fairness/starvation report,
  capacity and recovery dashboards.
- Acceptance: The published workload demonstrates pre-agreed throughput gains
  with zero policy bypasses, bounded duplicates, and no starvation.

## SVD-091 Add release gate, documentation, and Meta glasses summaries

- Status: waiting
- Priority: P1
- Track: release
- Depends on: SVD-089, SVD-090
- Outputs: all-profile evidence gate, operator runbook, updated MCP++ draft,
  virtual-desktop screenshots, and read-only Meta glasses summary handoff.
- Acceptance: Release evidence demonstrates cross-transport, multi-peer
  behavior and makes every degraded, denied, or conflicted state observable.
