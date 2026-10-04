# Proof-Grounded IR Learning Fabric Supervisor Runbook

This runbook operates the dependency board for `ProofGroundedIRLearningFabric`.
It documents the current `ipfs_accelerate_py` supervisor; it does not define a
second agent framework, scheduler, proof cache, semantic authority, or model
promotion path.

The objective heap is durable intent. The task board is its schedulable
projection. A drained board, successful process, provider response, reduced
loss, or model assertion is not completion evidence by itself.

## 1. Authority and campaign layout

The campaign is bound to the identities declared at the top of
`proof_grounded_ir_learning_fabric.todo.md`:

- `SRC-DATASETS-AUTH-1`: semantic source authority commit
  `df93e91e6338c84a17c3208ef68b88de8566f78c`, tree
  `37b9cb40644831c85c6fdf07d0228e45061e239a`.
- `SRC-ACCEL-AUTH-1`: operational source authority commit
  `8d46a6d25dd006c8cab3c9d9612707d2a014e79c`, tree
  `697ee660025fbf14a1cbe6c24fd8da5365df84d5`.
- `SRCSET-1`: the ordered pair of those authorities. Reviewed revisions are
  comparison inputs, not substitute execution trees.
- `JDAO-PINSET-1`: `justice_dao_pinset.yaml`, SHA-256
  `8e3a4b1bd81639393ddda35e5dfb3b95f9e7320afa898bde0b3eb9a0317a6b76`.
  It pins 21 Hub repository revisions and initially admits none for
  proof-grounded training.

The original dirty, detached checkouts under `hallucinate_app/` are evidence
sources only. Never run implementation workers in them and never use
`--auto-commit-generated-dirty` to turn their unrelated changes into campaign
history.

The current isolated campaign layout is:

```text
/home/barberb/lift_coding/.pgir_campaign/
├── worktrees/
│   ├── accelerate-authority/  agent/proof-grounded-ir-learning
│   └── datasets-authority/    agent/proof-grounded-ir-learning-datasets
└── runtime/
    ├── master/                bounded multi-supervisor wrapper state
    ├── track/                 PGIR implementation-supervisor state and logs
    ├── preflight/             historical preflight evidence only
    ├── worktrees/             isolated per-attempt implementation worktrees
    └── merge_queue/           serialized merge queue and DuckDB state
```

The clean accelerator controller branch contains a seed commit above
`SRC-ACCEL-AUTH-1`. The seed adds the control artifacts and advances the
`ipfs_datasets_py` gitlink to `SRC-DATASETS-AUTH-1`; it does not replace either
source authority. At the time this runbook was written, the controller seed was
`8b42722897be2d2b88e416a40370c6a56b04bad8` and both authority worktrees were
clean. Every resume must re-read the current accepted branch and receipts
rather than treating this observation as a permanent head.

Canonical plan copies and materialized controller paths are:

| Role | Planning copy | Controller path | SHA-256 at seed |
| --- | --- | --- | --- |
| Objective heap | `implementation_plan/proof_grounded_ir_learning_fabric/proof_grounded_ir_learning_fabric.objectives.md` | `docs/architecture/proof_grounded_ir_learning.objectives.md` | `db68de695d10e4c354fe3a470ef85f7c3b9529195aa4f5e1b0c3e2e84eaa9b82` |
| Task board | `implementation_plan/proof_grounded_ir_learning_fabric/proof_grounded_ir_learning_fabric.todo.md` | `docs/architecture/proof_grounded_ir_learning.todo.md` | `edf672a7f603f4003e0ff39cd14e362da2659126a83075b97f6aa18d0e179c37` |
| Hub pinset | `implementation_plan/proof_grounded_ir_learning_fabric/justice_dao_pinset.yaml` | `data/agent_supervisor/proof_grounded_ir_learning/justice_dao_pinset.yaml` | `8e3a4b1bd81639393ddda35e5dfb3b95f9e7320afa898bde0b3eb9a0317a6b76` |

The seed has 12 `PGIR-G###` goals and 37 `PGIR-###` tasks. A changed population
requires a new admitted plan/task projection identity; do not silently copy a
changed planning file over a live controller board.

## 2. Canonical current supervisor components

All paths in this section are relative to the accelerator controller root.

| Responsibility | Canonical implementation |
| --- | --- |
| Package topology and ownership | `ipfs_accelerate_py/agent_supervisor/README.md` |
| Operator semantics | `docs/guides/AGENT_SUPERVISOR_GUIDE.md` |
| Objective reconciliation and projections | `ipfs_accelerate_py/agent_supervisor/objectives/objective_daemon.py` |
| Bounded refill | `ipfs_accelerate_py/agent_supervisor/objectives/backlog_refinery.py` |
| Goal completion | `ipfs_accelerate_py/agent_supervisor/objectives/goal_completion.py` |
| Bundle planning and leased lane launch | `ipfs_accelerate_py/agent_supervisor/objectives/bundle_supervisor.py` |
| Formal plan compilation/validation | `ipfs_accelerate_py/agent_supervisor/planning/formal_plan_compiler.py`, `formal_plan_validator.py`, `proof_carrying_planner.py` |
| Canonical task projection and identity | `ipfs_accelerate_py/agent_supervisor/task_sources/markdown_task_source.py`, `taskboard_store.py`, `task_identity.py` |
| Implementation daemon | `ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_daemon.py` |
| Watchdog, recovery, refill, and resume | `ipfs_accelerate_py/agent_supervisor/todo_daemon/implementation_supervisor.py` |
| Stable supervisor script | `scripts/ops/agent_supervisor/implementation_supervisor_entry.py` |
| Finite multi-track wrapper | `ipfs_accelerate_py/agent_supervisor/runtime/multi_supervisor_runner.py` |
| Resource admission | `ipfs_accelerate_py/agent_supervisor/runtime/resource_scheduler.py` |
| Provider batching | `ipfs_accelerate_py/agent_supervisor/runtime/provider_batch_scheduler.py` |
| Endpoint-usage admission extensions | `ipfs_accelerate_py/agent_supervisor/resource_scheduler.py`, `provider_batch_scheduler.py` |
| Provider execution/accounting | `ipfs_accelerate_py/agent_supervisor/provider_execution.py`, `provider_usage.py` |
| Leases, fences, and checkout lock | `ipfs_accelerate_py/agent_supervisor/merge/lease_coordination.py`, `leased_lane.py`, `checkout_lock.py` |
| Merge queue and Git merge train | `ipfs_accelerate_py/agent_supervisor/merge/merge_queue.py`, `merge_train.py` |
| Operational recovery checkpoints | `ipfs_accelerate_py/agent_supervisor/rescue/supervisor_recovery.py`, `merge/merge_checkpoint.py` |
| Content-addressed runtime evidence | `ipfs_accelerate_py/agent_supervisor/runtime/runtime_cas.py`, `artifact_store.py`, `event_log.py` |
| Validation and admission | `ipfs_accelerate_py/agent_supervisor/validation/`, `control/` |

`merge_train.py` is a Git merge train, not model training. Operational and
merge recovery checkpoints are not learned-model checkpoint manifests.

### Proof and model roles

- Generic bounded proof transport:
  `agent_supervisor/proof/formal_verification_provider.py`.
- Capability metadata and executable probes:
  `agent_supervisor/proof/formal_verification_capabilities.py`. Discovery does
  not establish proof authority.
- Lean-capable proposal adapter:
  `agent_supervisor/proof/leanstral_proof_provider.py`. The similarly named
  root module is only a migration marker. The configured local MCP++ topology
  is `ipfs_accelerate_py/mcplusplus_module/leanstral_topology.py`.
- Tactician and proof planning:
  `agent_supervisor/proof/goal_directed_tactician.py`,
  `counterexample_guided_tactician.py`, `goal_tactician_lifecycle.py`, and
  `proof_scheduler.py`.
- Hammer/ATP/SMT integration:
  `agent_supervisor/integrations/ipfs_datasets_logic_provider.py`. It delegates
  semantic translation and solver behavior to the datasets-owned logic stack.
- Prover routing and resources:
  `agent_supervisor/proof/multi_prover_router.py`,
  `multi_prover_resources.py`, and `prover_matrix_registry.py`.
- Independent proof authority:
  `agent_supervisor/proof/kernel_verification.py`, with attestations and
  evidence in `proof_attestation.py` and `prover_evidence_store.py`.
- Existing proof cache:
  `agent_supervisor/proof/formal_verification_cache.py`. Reuse it; do not add
  another proof cache.

Leanstral, any other Lean-capable model, the tactician, and the hammer produce
candidate evidence. A kernel or declared independent checker alone may confer
the corresponding proof authority.

## 3. Current implementation gaps

The current supervisor provides a strong implementation-campaign runtime, but
the following requested learning-specific surfaces do not yet exist as
qualified canonical implementations:

- `IRLearningCampaign@1` and its create/plan/start/resume/status/steer/refill,
  proof-replay, compare, promote, reject, and report operations;
- a model-training job contract and trainer adapter bound to corpus, split,
  compiler, tokenizer, loss, optimizer, random state, and resource identities;
- learned-model checkpoint lifecycle and compatible-resume validation;
- deterministic checkpoint qualification and promotion handlers;
- IR-learning experiment tracking and controlled-comparison manifests;
- a supervisor-owned append-only Hugging Face publication adapter;
- literal `semantic_governor` or `incremental_proof_sealer` supervisor modules.

These gaps are assigned to `PGIR-060` through `PGIR-062`, `PGIR-070` through
`PGIR-072`, `PGIR-081`, and `PGIR-090`. Until those tasks pass, use current
generic supervisor primitives only for implementation work. Do not describe
operational recovery state as a model checkpoint, generic Hugging Face
inference/discovery modules as qualified publication, or task completion as
checkpoint promotion.

## 4. Board grammar and dependency rules

The current implementation-supervisor launch consumes the supported heading
grammar. The CLI prefix includes the Markdown heading: `"## PGIR-"`.

### Objective heap

Each goal is one second-level heading followed by closed, one-line fields:

```markdown
## PGIR-G080 Supervisor campaign, leases, resources, refill, and resume

- Status: active
- Parent: PGIR-G000
- Depends on: PGIR-G070
- Priority: P0
- Goal: Durable statement of intent.
- Evidence: content-addressed evidence paths
- Outputs: expected roots
- Validation: bounded validation command
- Acceptance: evidence-based completion criteria
- Conflict policy: shared authority policy
- Interfaces: versioned contracts
- Resource class: cpu-medium
```

Root goals have an empty `Parent`. Parent and dependency references must exist,
and the graph must remain acyclic. Objective status is not inferred from a
drained board.

### Executable tasks

Each task is one second-level heading:

```markdown
## PGIR-060 Implement IR learning campaign contracts and APIs

- Status: todo
- Completion: validated-implementation
- Is schedulable: true
- Priority: P0
- Track: campaign
- Parent goal: PGIR-G080
- Subgoal: campaign-work-graph
- Owning repository: ipfs_accelerate_py
- Owned paths: exact paths or bounded globs
- Base source revisions: SRCSET-1
- Source dataset revisions: exact revision or dependency result
- Data split identity: exact split root or not-applicable
- Compiler identity: exact identity or dependency result
- Decompiler identity: exact identity or dependency result
- Model checkpoint identity: explicit identity or none
- Objective: one coherent change
- Depends on: PGIR-014
- Resource profile: RP-CPU-M
- Expected inputs: immutable identities
- Expected outputs: immutable artifacts and/or code
- Allowed effects: explicit effects
- Prohibited effects: explicit authority and mutation boundaries
- Acceptance criteria: testable gates
- Required proof or evaluation evidence: exact receipts
- Lease and checkpoint policy: LEASE-DEFAULT, key campaign-plan
- Rollback procedure: ROLLBACK-DEFAULT
- Result identity: RESULT(PGIR-060)
- Outputs: machine-readable output paths
- Validation: bounded exact command
- Bundle: pgir/campaign/contracts
- Parallel lane: campaign-contracts
- Predicted files: paths used for conflict planning
- Conflict policy: exclusive or disjoint policy
```

Valid operational task states include `todo`, `ready`, `in_progress`,
`completed`, and `blocked`; terminal or policy-specific dispositions must stay
explicit in result evidence. Additional `- Field: value` metadata is preserved
by the heading parser. Never replace this board with checkbox syntax.

`task_sources/markdown_task_source.py` also implements a stronger
content-addressed projection with plan root, repository root, record CIDs, and
a canonical metadata marker. The direct implementation daemon supports
`--task-source-kind markdown` and expected-root fences. The current
implementation-supervisor/bundle launch does not expose those source flags, so
this campaign uses the objective heap and generated/signed heading projection.
Adding root forwarding is implementation work, not an operator-side format
substitution.

### Freeze and parallelism

`PGIR-001` through `PGIR-014` are the freeze chain. No learned-model,
pair-mining, proof-curriculum, training, evaluation, promotion, or publication
task may receive a lease before `RESULT(PGIR-014)` binds the admitted schema,
source, split, compiler/decompiler, tokenizer-policy, loss-authority, and
proof-authority roots.

PGIR-001 is the serial revision gate. After it is accepted, inventory-only
tasks may fan out when their owned repositories or paths are disjoint. The
shared-resource claims deliberately serialize PGIR-002 and PGIR-004 because
both mutate the managed datasets submodule. Schema, corpus, split, tokenizer,
loss, and promotion-authority mutations remain dependency-ordered and
exclusive; learned and experimental fan-out still waits for PGIR-014.

## 5. Read-only launch gate

Set paths without repurposing system environment variables:

```bash
PGIR_ROOT=/home/barberb/lift_coding/.pgir_campaign
PGIR_REPO="$PGIR_ROOT/worktrees/accelerate-authority"
PGIR_DATASETS="$PGIR_ROOT/worktrees/datasets-authority"
PGIR_RUNTIME="$PGIR_ROOT/runtime"
PGIR_PY=/home/barberb/.local/bin/python
PGIR_CODEX=/usr/local/bin/codex
PGIR_TARGET=agent/proof-grounded-ir-learning
PGIR_DATASETS_TARGET=agent/proof-grounded-ir-learning-datasets
PGIR_TODO=docs/architecture/proof_grounded_ir_learning.todo.md
PGIR_OBJECTIVES=docs/architecture/proof_grounded_ir_learning.objectives.md
```

Before every start or resume, require all of the following:

```bash
test -x "$PGIR_PY"
test "$(git -C "$PGIR_REPO" branch --show-current)" = "$PGIR_TARGET"
test "$(git -C "$PGIR_DATASETS" branch --show-current)" = "$PGIR_DATASETS_TARGET"
test -z "$(git -C "$PGIR_REPO" status --porcelain)"
test -z "$(git -C "$PGIR_DATASETS" status --porcelain)"
test "$(git -C "$PGIR_REPO" rev-parse HEAD)" = \
  a5db9edc6fa24c25b349f82184a0c375a0fab761
test "$(git -C "$PGIR_DATASETS" rev-parse HEAD)" = \
  df93e91e6338c84a17c3208ef68b88de8566f78c
test "$(git -C "$PGIR_REPO" rev-parse HEAD:ipfs_datasets_py)" = \
  df93e91e6338c84a17c3208ef68b88de8566f78c
test "$(sha256sum "$PGIR_REPO/$PGIR_OBJECTIVES" | cut -d' ' -f1)" = \
  db68de695d10e4c354fe3a470ef85f7c3b9529195aa4f5e1b0c3e2e84eaa9b82
test "$(sha256sum "$PGIR_REPO/$PGIR_TODO" | cut -d' ' -f1)" = \
  a0659db2f6dbd53e0bd09cf3b913dbbdf539a0d2868092e387a112c6b8b388db
test "$(sha256sum "$PGIR_REPO/data/agent_supervisor/proof_grounded_ir_learning/justice_dao_pinset.yaml" | cut -d' ' -f1)" = \
  8e3a4b1bd81639393ddda35e5dfb3b95f9e7320afa898bde0b3eb9a0317a6b76
```

The exact `HEAD` assertion is the current accepted PGIR-001 result. After an
accepted task merge, replace it with verification against the latest accepted
`RESULT(task)` chain and controller receipt. Never weaken it to “branch
exists.”

Verify one interpreter can import both the stable entry point and managed
daemon in the daemon's safe-path (`-P`) mode. Bind the clean controller root
explicitly because `-P` removes the implicit current-directory import path:

```bash
cd "$PGIR_REPO"
PYTHONPATH="$PGIR_REPO" "$PGIR_PY" -P -c \
  'import sys; import ipfs_accelerate_py; from ipfs_accelerate_py.agent_supervisor.todo_daemon import implementation_daemon, implementation_supervisor; print(sys.executable, ipfs_accelerate_py.__file__)'
```

Reject the launch if the printed interpreter is not `PGIR_PY`, the package is
not loaded from `PGIR_REPO`, either import fails, the branches are dirty, the
gitlink differs, or a materialized control hash differs.

## 6. Reconciliation preflight

Use a fresh preflight state namespace. This invokes no implementation provider
and performs dry-run worktree classification, but it writes diagnostic state
and receipts under the selected preflight directory.

```bash
PGIR_PREFLIGHT="$PGIR_RUNTIME/preflight-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$PGIR_PREFLIGHT"
cd "$PGIR_REPO"
"$PGIR_PY" scripts/ops/agent_supervisor/implementation_supervisor_entry.py \
  --once \
  --reconciliation-only \
  --fail-on-reconciliation-error \
  --worktree-reconciliation-dry-run \
  --todo-path "$PGIR_TODO" \
  --task-prefix "## PGIR-" \
  --state-dir "$PGIR_PREFLIGHT" \
  --state-prefix pgir_preflight \
  --worktree-root "$PGIR_RUNTIME/worktrees" \
  --merge-queue-dir "$PGIR_RUNTIME/merge_queue" \
  --merge-target-branch "$PGIR_TARGET" \
  --worktree-submodule-path ipfs_datasets_py \
  --implementation-protected-path "$PGIR_OBJECTIVES" \
  --implementation-protected-path "$PGIR_TODO" \
  --implementation-protected-path \
    data/agent_supervisor/proof_grounded_ir_learning/justice_dao_pinset.yaml
```

Require exit status zero, a current supervisor-status receipt, no unresolved
merge/worktree incident, and no live process belonging to a different state
root. Preserve a failed preflight directory; do not rerun over or delete it.

## 7. Dependency projection and lane planning

When an objective reconciliation is required, omit submission first:

```bash
cd "$PGIR_REPO"
"$PGIR_PY" -m \
  ipfs_accelerate_py.agent_supervisor.objectives.objective_daemon \
  --repo-root "$PGIR_REPO" \
  --objective-path "$PGIR_OBJECTIVES" \
  --todo-path "$PGIR_TODO" \
  --discovery-dir data/agent_supervisor/proof_grounded_ir_learning/discovery \
  --bundle-dir data/agent_supervisor/proof_grounded_ir_learning/bundles \
  --dataset-dir data/agent_supervisor/proof_grounded_ir_learning/datasets \
  --graph-path data/agent_supervisor/proof_grounded_ir_learning/objective_graph.json \
  --task-prefix PGIR- \
  --refine-objective-heap \
  --generate-plan-branches \
  --plan-branch-count 3
```

Inspect the graph, rejected candidates, bundle index, exact task population,
dependency order, protected paths, and predicted conflicts. A generated
projection must preserve every task field required by this campaign. Commit
the accepted projection through its protected control path before workers use
it.

Plan bundle lanes without starting them:

```bash
"$PGIR_PY" -m \
  ipfs_accelerate_py.agent_supervisor.objectives.bundle_supervisor \
  --bundle-index-path \
    "$PGIR_REPO/data/agent_supervisor/proof_grounded_ir_learning/bundles/index.json" \
  --repo-root "$PGIR_REPO" \
  --state-root "$PGIR_RUNTIME/bundles" \
  --worktree-root "$PGIR_RUNTIME/worktrees" \
  --log-dir "$PGIR_RUNTIME/bundles/logs" \
  --manifest-path "$PGIR_RUNTIME/bundles/bundle_lanes.json" \
  --metrics-path "$PGIR_RUNTIME/bundles/scheduler_metrics.json" \
  --task-prefix PGIR- \
  --coordination-path "$PGIR_RUNTIME/bundles/coordination.duckdb" \
  --max-lanes 1 \
  --once
```

Before `PGIR-014`, multiple lanes are admitted only for inventory work after
PGIR-001 and remain subject to repository/path resource claims. Learned,
training, proof-curriculum, evaluation, promotion, and publication fan-out
requires the PGIR-014 freeze plus current host/provider/prover telemetry and a
reviewed conflict plan. A lane number is a ceiling, not a demand.

## 8. Bounded start

The current campaign uses three deterministic implementation-supervisor lanes
for an eight-hour window. Use the same verified Python executable and explicit clean
controller `PYTHONPATH` for the master, track supervisor, and managed daemon.
The interpreter, import root, and capability-probed implementation command are
mandatory. The installed Codex 0.147.0 does not accept the legacy
`--full-auto` flag.

```bash
PGIR_STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
cd "$PGIR_REPO"
PYTHONPATH="$PGIR_REPO" "$PGIR_PY" -m \
  ipfs_accelerate_py.agent_supervisor.runtime.multi_supervisor_runner \
  --python-executable "$PGIR_PY" \
  --repo-root "$PGIR_REPO" \
  --duration-seconds 28800 \
  --heartbeat-interval-seconds 30 \
  --supervisor-status-stale-seconds 600 \
  --stop-grace-seconds 10 \
  --stamp "$PGIR_STAMP" \
  --master-dir "$PGIR_RUNTIME/master" \
  --master-log "$PGIR_RUNTIME/master/pgir_parallel_master_${PGIR_STAMP}.log" \
  --master-pid-path "$PGIR_RUNTIME/master/pgir_parallel_master_${PGIR_STAMP}.pid" \
  --label proof-grounded-ir-learning-parallel \
  --implementation-track \
    "pgir|scripts/ops/agent_supervisor/implementation_supervisor_entry.py|$PGIR_RUNTIME/parallel|pgir_parallel" \
  --implementation-supervisor-defaults \
  --implementation-supervisor-command \
    "$PGIR_CODEX exec --approve-for-me --ephemeral" \
  --implementation-supervisor-lanes-per-track 3 \
  --implementation-supervisor-max-restarts 3 \
  --implementation-supervisor-timeout 7200 \
  --implementation-supervisor-log-stall-seconds 900 \
  --common-arg=--todo-path \
  --common-arg="$PGIR_TODO" \
  --common-arg=--task-prefix \
  --common-arg="## PGIR-" \
  --common-arg=--max-task-attempts \
  --common-arg=3 \
  --common-arg=--worktree-root \
  --common-arg="$PGIR_RUNTIME/worktrees" \
  --common-arg=--merge-queue-dir \
  --common-arg="$PGIR_RUNTIME/merge_queue" \
  --common-arg=--merge-target-branch \
  --common-arg="$PGIR_TARGET" \
  --common-arg=--worktree-submodule-path \
  --common-arg=ipfs_datasets_py \
  --common-arg=--implementation-protected-path \
  --common-arg="$PGIR_OBJECTIVES" \
  --common-arg=--implementation-protected-path \
  --common-arg="$PGIR_TODO" \
  --common-arg=--implementation-protected-path \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/justice_dao_pinset.yaml \
  --common-arg=--objective-path \
  --common-arg="$PGIR_OBJECTIVES" \
  --common-arg=--objective-graph-path \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/objective_graph.json \
  --common-arg=--objective-bundle-dir \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/bundles \
  --common-arg=--objective-dataset-dir \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/datasets \
  --common-arg=--objective-discovery-dir \
  --common-arg=data/agent_supervisor/proof_grounded_ir_learning/discovery \
  --common-arg=--objective-goal-prefix \
  --common-arg=PGIR-G \
  --common-arg=--objective-root-goal-id \
  --common-arg=PGIR-G000
```

For a new environment, do not add `--detach` until foreground startup has
produced a live supervisor status, a live managed-daemon PID, a parsed task
state, and at least one healthy heartbeat. The already-probed campaign may use
`--detach` while retaining the same command and state identity. Do not launch a
second master merely because the track appears idle. First classify the
existing master and child PID files.

The bounded defaults in this command are policy, not suggestions:

| Bound | Value |
| --- | ---: |
| Initial lanes | 3 |
| Master duration | 28,800 seconds |
| Master heartbeat | 30 seconds |
| Supervisor status stale threshold | 600 seconds |
| Task/supervisor stale threshold | 1,800 seconds (profile default) |
| Implementation hard timeout | 7,200 seconds |
| Quiet-log threshold | 900 seconds |
| Supervisor restarts | 3 |
| Attempts per canonical task identity | 3 |
| Stop grace | 10 seconds |

The board separately imposes `LEASE-DEFAULT`: one renewable 30-minute task
lease, heartbeat no slower than 60 seconds, monotonically increasing fence,
and at most three attempts. Proof, provider, training, and curriculum tasks
have their additional task-specific limits.

## 9. Provider and resource telemetry

Implementation-provider selection is operational configuration. The documented
profiles support, among others:

```bash
export IPFS_ACCELERATE_AGENT_IMPLEMENTATION_PROVIDER=grok
export IPFS_ACCELERATE_AGENT_GROK_MODEL=grok-4.5
export IPFS_ACCELERATE_AGENT_CODEX_MODEL=gpt-5.6-terra
```

Set only providers that are installed, authenticated, policy-permitted, and
successfully capability-probed. Never print tokens or serialize credentials in
the board, prompts, logs, capacity files, receipts, or task results. Model
identity and revision must be recorded for each chargeable call.

The current bounded smoke run uses the installed Codex fallback explicitly:

```bash
"$PGIR_CODEX" exec --approve-for-me --ephemeral --skip-git-repo-check \
  'Reply exactly READY. Do not inspect or modify files.'
```

Require exit status zero and the exact `READY` response before admitting task
work. This verifies provider transport and authentication, not the quality or
authority of later task output.

The bundle scheduler accepts current capacity through
`--provider-capacity-path`, `IPFS_ACCELERATE_LLM_ROUTER_CAPACITY_PATH`, fenced
worker heartbeats, or an injected supplier. Prefer a protected file containing
a provider list/map or `{ "providers": ... }`. It must carry current provider
identity/revision, observation time/freshness, health/circuit state,
concurrency, quota/tokens, context, latency, and retry-after information.

Missing or stale telemetry means zero new provider capacity. The
`--allow-missing-provider-telemetry` option is an explicit degraded smoke
override only. It is prohibited for GPU training, proof campaigns, held-out
evaluation, promotion, or publication.

The current generic single-track implementation path does not itself prove
the complete CPU/GPU/prover/I/O/token/network admission behavior required by
this campaign. `PGIR-061` must qualify that behavior before parallel learning
stages begin.

## 10. Leases, fencing, checkpoints, and shared authorities

Use existing lease and CAS implementations. The bundle coordination path must
be a DuckDB store, for example:

```text
/home/barberb/lift_coding/.pgir_campaign/runtime/bundles/coordination.duckdb
```

Use distinct exclusive keys for:

- corpus-build ownership;
- source and split manifest ownership;
- compiler/decompiler contracts;
- tokenizer and vocabulary;
- loss configuration;
- training run and checkpoint writes;
- proof-replay and evaluation shards;
- curriculum revision;
- promotion pointer; and
- Hugging Face publication.

A claim, heartbeat, result, merge, promotion, or publication must carry the
current lease ID and monotonically increasing fencing token. A stale worker may
finish computing but may not publish or become the accepted result. Duplicate
attempts may exist; compare-and-swap admits one `RESULT(task)` for one canonical
input root.

Do not share mutable checkpoint files between trainers. Write a new immutable
checkpoint root, validate it, then advance an admitted pointer by CAS. Do not
delete lease, merge-queue, JSONL, recovery, or artifact state to recover a
campaign.

Current supervisor recovery checkpoints cover implementation and Git recovery.
They do not satisfy the model-checkpoint bindings required by `PGIR-062` and
`PGIR-070`.

## 11. Status and observability

Read the current state without mutating it:

```bash
PGIR_TRACK="$PGIR_RUNTIME/track"
jq '{status,updated_at,supervisor_pid,supervisor_pid_alive,daemon_pid,daemon_pid_alive,restart_count,current_status_path}' \
  "$PGIR_TRACK/pgir_supervisor_status.json"
jq . "$PGIR_TRACK/pgir_task_state.json"
jq . "$PGIR_TRACK/pgir_strategy.json"
tail -n 100 "$PGIR_TRACK/pgir_supervisor_events.jsonl"
tail -n 100 "$PGIR_TRACK/pgir_events.jsonl"
tail -n 100 "$PGIR_TRACK"/pgir_implementation_daemon_*.log
tail -n 100 "$PGIR_RUNTIME/master"/pgir_master_*.log
```

Treat a missing task-state file as a startup failure until explained. Do not
infer health from a live master PID alone. For each PID marker, validate both
liveness and command identity:

```bash
for PGIR_PID_FILE in \
  "$PGIR_RUNTIME/master"/*.pid \
  "$PGIR_TRACK"/pgir_supervisor.pid \
  "$PGIR_TRACK"/pgir_managed_daemon.pid
do
  test -f "$PGIR_PID_FILE" || continue
  PGIR_PID="$(tr -cd '0-9' < "$PGIR_PID_FILE")"
  printf '%s pid=%s ' "$PGIR_PID_FILE" "$PGIR_PID"
  if test -n "$PGIR_PID" && kill -0 "$PGIR_PID" 2>/dev/null; then
    tr '\0' ' ' < "/proc/$PGIR_PID/cmdline"
    printf '\n'
  else
    printf 'not-live\n'
  fi
done
```

The unified `ipfs-accelerate agent status|health|metrics|events|receipts`
surface is preferred when its repository, tree, objective, policy, caller,
state-root, permit, and backend bindings are configured. It intentionally
requires all nine target bindings and bounded pagination/watch settings; never
invent those bindings merely to obtain a prettier status display.

## 12. Resume

The low-level implementation supervisor has no separate resume flag. Resume is
reconciliation: re-run the same launch with the same accepted board,
repository/tree identity, state directory/prefix, worktree root, merge queue,
target branch, protected paths, submodule path, provider policy, and bounds.

Before resume:

1. Preserve all state and logs.
2. Verify whether the master, track supervisor, daemon, and worker processes
   are actually live and match the expected command.
3. Stop or let the bounded wrapper stop the old master; never run two masters
   against the same track state.
4. Re-run the read-only launch gate and reconciliation preflight.
5. Verify current leases/fences and any in-progress merge.
6. Re-run the bounded start with a new master stamp and the same track state.
7. Require a live daemon heartbeat and parsed task state before declaring the
   resume successful.

Use the typed control-plane `resume` operation only when its backend,
authorization decision, lease/fence, idempotency key, and expected effects are
configured. It is not a substitute for launching the OS-level supervisor.

## 13. No-progress and blocked diagnostics

`implementation_supervisor.is_stuck()` distinguishes:

- a worktree phase that requires a worker but has none;
- an implementation log that has been quiet beyond policy;
- a stale active-task heartbeat;
- no progress on a ready active task; and
- an unresolved merge failure.

An active implementation, validation, or proof subprocess within its hard
timeout suppresses a false quiet-log diagnosis. Timeout, provider unavailable,
or missing tool is not a semantic falsehood or proof failure.

Use this order:

1. Read status, health, task state, strategy, recent daemon/supervisor events,
   implementation log, and merge receipts.
2. Classify the reason: environment/startup, dependency, resource/provider,
   lease/fence, implementation, validation/proof, merge, or bounded exhaustion.
3. Pause new admission or drain admitted work when a typed control backend is
   available.
4. Run one reconciliation-only supervisor pass against the same state.
5. Replay validation only with the exact tree and validation identity.
6. Retry only a transient failure with a recorded changed trigger.
7. Quarantine a persistently failing task, provider, or lane.
8. Produce a repair task or documented no-go when the bounded policy is
   exhausted.

Common diagnoses and responses:

| Signal | Meaning | Response |
| --- | --- | --- |
| `ModuleNotFoundError: ipfs_accelerate_py` before task state exists | Interpreter/environment launch failure | Stop duplicate restart loops, bind verified `--python-executable`, rerun import gate and reconciliation; do not consume or relabel a semantic task |
| `all_selectable_ready_tasks_reached_max_task_attempts` | Bounded attempt exhaustion | Keep evidence, create an admitted repair/no-go result; do not set attempts to unlimited |
| Waiting on `PGIR-###` | Dependency gate | Complete or explicitly no-go the dependency; do not remove the edge |
| Missing/stale provider capacity | Fail-closed resource admission | Restore current telemetry or keep blocked; do not use the missing-telemetry override for real work |
| Stale fence/lease ownership | Another or expired claimant controls publication | Reconcile the coordination store and accept only the current fence; never delete the store |
| Protected-path or dirty-checkout incident | Worker crossed authority boundary | Quarantine, preserve diff/receipt, repair in a separately admitted task; never auto-commit unrelated changes |
| Worktree/merge failure | Integration state unresolved | Dry-run worktree reconciliation, inspect merge queue/receipts, use bounded resolver or quarantine |
| Prover timeout/unavailable | Inconclusive operational outcome | Record timeout/unavailable, adjust routing/curriculum only under policy; never label false/unprovable |
| Board drained | No currently schedulable projection | Reconcile objective completion and refill evidence; do not declare the root goal complete |

Never delete JSONL logs, PID evidence, task state, strategy, merge queue,
coordination database, recovery checkpoints, or CAS artifacts to “unstick” the
campaign.

### Observed startup incident on 2026-08-16

The first bounded master used `/home/barberb/.local/bin/python`, but its track
wrapper used the default `python3`, which resolved to `/usr/bin/python3`. The
managed daemon then failed before producing task state:

```text
/usr/bin/python3: Error while finding module specification for
'ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon'
(ModuleNotFoundError: No module named 'ipfs_accelerate_py')
```

At observation time, the master PID was live, the track supervisor status was
`stopped`, `daemon_pid` was absent, `restart_count` was one, and
`pgir_task_state.json` did not exist. This is an environment/interpreter
failure, not a blocked PGIR task. Preserve the incident evidence. A corrected
restart must pass `--python-executable "$PGIR_PY"`, bind the clean controller
root through `PYTHONPATH`, and pass the `-P` import gate above; it must not erase
state or mark any task attempted/completed because of this failure.

The first correctly imported daemon then selected `PGIR-001`, but the live
configured default implementation provider resolved to Grok. That provider
exited before implementation with `Not signed in`; the failed attempt remains
an operational provider receipt. The installed Codex 0.147.0 fallback was
capability-probed with `--approve-for-me --ephemeral`, and the identical
campaign state was resumed using the explicit implementation command above.
Do not discard or reinterpret the Grok failure as semantic evidence.

## 14. Focused qualification before implementation

Run these from the clean accelerator controller with the verified interpreter.
They are deterministic focused tests; capability-gated live provider/prover
tests remain separate and bounded.

```bash
cd "$PGIR_REPO"
"$PGIR_PY" -m pytest -q \
  test/api/test_agent_supervisor_markdown_task_source.py \
  test/api/test_agent_supervisor_task_source_e2e.py \
  test/api/test_agent_supervisor_formal_plan_compiler.py \
  test/api/test_agent_supervisor_formal_plan_validator.py \
  test/api/test_agent_supervisor_objective_graph.py \
  test/api/test_agent_supervisor_bundle_plan_cache.py \
  test/api/test_agent_supervisor_implementation_daemon_runner.py \
  test/api/test_agent_supervisor_implementation_supervisor_runner.py \
  test/api/test_agent_supervisor_supervisor_watchdog.py \
  test/api/test_agent_supervisor_task_attempt_limit.py \
  test/api/test_agent_supervisor_daemon_restart_durability.py \
  test/api/test_agent_supervisor_daemon_recovery_lease.py \
  test/api/test_agent_supervisor_resource_scheduler.py \
  test/api/test_agent_supervisor_provider_batch_scheduler.py \
  test/api/test_agent_supervisor_lease_coordination.py

"$PGIR_PY" -m pytest -q \
  test/api/test_agent_supervisor_formal_verification_capabilities.py \
  test/api/test_agent_supervisor_formal_verification_provider.py \
  test/api/test_agent_supervisor_ipfs_datasets_logic_provider.py \
  test/api/test_agent_supervisor_leanstral_proof_provider.py \
  test/api/test_agent_supervisor_leanstral_proof_gate.py \
  test/api/test_agent_supervisor_proof_scheduler.py \
  test/api/test_agent_supervisor_multi_prover_router.py \
  test/api/test_agent_supervisor_multi_prover_resources.py \
  test/api/test_agent_supervisor_kernel_verification.py \
  test/api/test_goal_tactician_supervisor_lifecycle.py \
  test/api/test_goal_tactician_supervisor_restart.py \
  test/api/test_formal_verification_tactician_rollout.py \
  test/security/test_formal_verification_tactician_adversarial.py
```

Record test command, interpreter, environment identity, exact parent/tree and
datasets gitlink, start/end time, resource use, exit status, failing node IDs,
and output digest. A failed or skipped required test remains visible.

## 15. Stop, rollback, and handoff

Prefer the typed `pause`, `drain`, and `stop` operations when the control
backend is configured. For the finite multi-supervisor wrapper, stop only the
exact PID resolved from its campaign-specific master PID file, request graceful
termination, and honor the configured stop grace. Never use `pkill`, a process
name wildcard, or a PID from an unverified stale marker.

Rollback follows `ROLLBACK-DEFAULT`: stop descendants, retain immutable
attempt/evidence records, revert only the task commit or an unaccepted pointer,
and restore a prior content-addressed root with CAS. Never reset the authority
branches, delete evidence, rewrite a Hub release, or discard another lane's
worktree.

A handoff must include:

- current controller and datasets commits/trees/gitlink;
- objective, board, pinset, plan-root, and task-population identities;
- master/track/daemon liveness and exact commands;
- current task, phase, attempt, lease ID, and fence;
- state, events, logs, merge queue, CAS, and checkpoint paths;
- provider/prover/resource telemetry revisions and freshness;
- accepted results, failed/inconclusive results, bounded exhaustion, and
  quarantines; and
- the exact safe next operator action.

The campaign may claim a qualified compiler/decompiler checkpoint only after
the semantic owner, independent proof/checker evidence, held-out evaluation,
supervisor policy, and configured human approval have all admitted the same
content-addressed checkpoint. Until then, every learned output remains a
candidate.
