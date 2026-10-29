# Watchdog operation and native adapter contract

`watchdog_loop.py` is an executable, standard-library-only host process. It detects persistent idle/stalled/blocked work, emits bounded typed recovery requests, and persists its action outbox, in-flight operations, admitted source task set and budgets. Sustained operation exits successfully on native verified completion; `--once` can also exit zero after a normal observation without claiming completion. It never edits the site, repairs Python source itself, rewrites task status, selects an emergency provider, kills a process, or certifies a patch. Those actions use existing native `ipfs_accelerate_py` authorities through the adapter delivered in WWL-004 and the repair bindings in WWL-102. This division is necessary: the current native watchdog's CLI does not bind the optional restart and code-repair handlers.

The loop and tests run now. Live automatic supervisor repair requires those first-milestone bindings and their readiness canary. Do not interpret passing policy tests as evidence that a live campaign or provider has run.

## Commands

From the website root after installing this package:

```bash
python3 implementation_plan/worldwide_legal_search/validate_plan.py
python3 implementation_plan/worldwide_legal_search/validate_plan.py --native-root /home/barberb/ipfs_accelerate_py
python3 -m unittest discover -s implementation_plan/worldwide_legal_search -p 'test_*.py'
python3 implementation_plan/worldwide_legal_search/watchdog_loop.py --snapshot implementation_plan/worldwide_legal_search/fixtures/healthy.snapshot.json --once
```

Once WWL-004/005/102 have delivered the native adapter, set its installed module on `PYTHONPATH` through the host's existing supervisor environment. The following argv is the planned public adapter interface to implement, not a claim that the module already exists:

```bash
python3 implementation_plan/worldwide_legal_search/watchdog_loop.py \
  --adapter-argv-json '["python3", "-m", "ipfs_accelerate_py.agent_supervisor.project_adapters.worldwide_legal_search_watchdog", "--repository", "/home/barberb/worldwidelaws.github.io", "--run-id", "<admitted-native-run-id>"]' \
  --state .worldwide-supervisor/watchdog.json \
  --execute
```

Omit `--execute` for observation-only operation with the same adapter. `--once` performs a single poll; ordinary operation polls every 30 seconds. A native adapter handshake is required before live execution and must advertise tested lifecycle/repair bindings and the exact task set. Missing adapters, stale observations or mismatched state fail with an actionable error. An invocation without either a snapshot or adapter does not start background work. A user-systemd service may manage the loop after bootstrap; its start condition must respect the native HOLD/STOP markers and it must not start another writer directly.

## Wire protocol

Invoke the supplied argv with one appended operation: `ready`, `observe`, or `dispatch`. Pass one UTF-8 JSON request on stdin; consume exactly one JSON object on stdout. Do not use a shell or put credentials in argv. Native logging belongs on stderr. Return at most 1 MiB. The adapter must bound its own execution; the loop also has a 60-second subprocess timeout. An adapter timeout during dispatch is an unknown effect, not a retryable negative acknowledgment.

The input to `ready` is `{schema: "wwl.watchdog.request@1", operation: "ready", policy_id, required_task_ids}`. Return:

```json
{
  "schema": "wwl.watchdog.ready@1",
  "run_id": "native-run-id",
  "policy_id": "worldwide-legal-search-recovery-v1",
  "repository": "/home/barberb/worldwidelaws.github.io",
  "native_revision": "accepted-operational-commit",
  "admitted_plan_revision": "native-plan-revision",
  "readiness_receipt": "native-verified-canary-receipt-id",
  "required_task_ids": ["WWL-000", "...exact complete plan task set..."],
  "bindings": {
    "task_source": true,
    "lifecycle_restart": true,
    "rescue_planner": true,
    "rescue_orchestrator": true,
    "route_policy": true,
    "independent_validation": true,
    "validated_promotion": true,
    "incident_deduplication": true,
    "meaningful_progress": true
  }
}
```

The readiness receipt is resolved and verified by native admission; a worker-written boolean or arbitrary receipt path cannot mint the permission. Use the registered accepted adapter, not candidate repair code, for this interface. Bind the handshake to the current run, source revision, policy and task authority on every poll. This package's loop validates the protocol and identity; semantic trust in evidence remains native.

`observe` takes the same request envelope with operation changed, plus `run_id`. Its response is `wwl.watchdog.snapshot@1` with the fields illustrated in `fixtures/healthy.snapshot.json`. Timestamps are UTC Unix seconds. `observed_at` must be fresh. `progress_token` changes only for useful work verified by native authority; heartbeat/log writes are excluded. A snapshot includes the required task IDs, the verified current task IDs, the task-authority revision and the current accepted tree. Completion additionally requires a resolved native root-goal completion receipt, no runnable task and no active task. Do not set `completion_verified` from task counts alone.

The initial required set is the core board. WWL-018 can add source tasks matching `plan.json.source_expansion.id_pattern`. An expanded readiness response must include `expansion_receipt`, resolved by the native adapter against the pinned inventory and admitted plan. The snapshot repeats `admitted_plan_revision`. On a changed observed task set or plan revision, the loop repeats the readiness handshake, requires the same run and every prior required task, and preserves its persistent incident/action counters. Both the required task set and plan revision are stored durably: startup also checks readiness against the pre-restart task set. Unknown task families, removals or an unproved expansion are refused. The native completion verifier must include every expanded child task in its root-goal proof.

`blocked_kind` is one of `none`, `credentials`, `permission`, `source_unavailable`, `rights`, `budget`, `software_defect`. `dependency_running` means no runnable task exists because a dependency is actively progressing. A software defect needs a stable `failure_key` and `reproducer_receipt`; the adapter verifies the receipt. `effects_unknown` always takes precedence over retry or code repair. Fresh heartbeat plus frozen progress remains diagnosable. If another independent task is runnable, a blocker on one task must not globally hold the campaign.

`dispatch` receives `wwl.watchdog.action@1`: run and policy identity, incident ID, unique action ID, action kind, reason, active task/stage, authority revision, accepted tree, and previous unacknowledged action. Allowed kinds are `reconcile`, `recover` and `repair`. The native dispatcher rechecks the observation revision, roots, leases, route policy and effect authority immediately before mutation. A stale action is a recorded refusal. Action IDs are idempotency keys stored by the native dispatcher before effects, so re-observation after a lost response cannot double-start a worker or promote a repair twice.

Return `wwl.watchdog.action-result@1` with matching `action_id`, `status` (`accepted`, `blocked`, or `unknown`) and a nonempty native `receipt`. An accepted result also includes `deadline_at`: no later than 5,400 seconds after the original action's `issued_at` for a repair, or the native recovery deadline (120 seconds by default) for reconciliation/recovery. Acceptance means admission, not completion. Accepted actions stay in the persisted `inflight` map, preventing another repair while an admitted repair is still running. Unknown acknowledgments remain in the outbox. A zero exit code or model prose without the envelope is an unknown outcome.

Each observation request includes `action_ids` for all unsettled operations. Return a snapshot `action_observations` list with entries containing `schema: "wwl.watchdog.action-observation@1"`, matching `action_id`, status (`running`, `succeeded`, `failed`, `blocked`, `unknown`), native `receipt` and `effects_verified`. A running observation also has a deadline; it may not extend the originally admitted bound. Terminal observations require `effects_verified: true` and a native settlement receipt before the loop removes the action. Missing observations wait only until the original bounded deadline. Expired/unknown outcomes request reconciliation referencing every unsettled action ID, rather than starting another repair. Neither action accounting nor the admitted deadline is refunded on restart. Root completion waits for all pending/admitted operations to settle.

## State and budgets

The loop owns only its JSON state, advisory owner lock, and action requests. Native task/goal/lease/provider/merge authority stays in the supervisor. State writes are atomic, with the outbox recorded before dispatch. Restarting the loop must load the same run and policy digest or refuse; it must not reset retry counts or forget expanded tasks. A healthy, waiting, held or externally blocked observation resets the confirmation streak while preserving charged attempts, so intermittent faults cannot accumulate into a false persistent stall. Per-incident and campaign-wide bounds prevent repeated PID/stage changes from creating unlimited retries. External blockers remain visible, and independent native ready work can continue. Observation-only mode does not write state or call dispatch.

Fault tests cover persistent idle confirmation, live-heartbeat stalls, progress refresh, deadline expiry, missing handlers, external blockers, independent ready work, holds, unknown effects, lost dispatch acknowledgments, incident/repair budgets, and verified completion. WWL-103/105 add real process/lease/provider/native-repair fault injection before campaign activation.
