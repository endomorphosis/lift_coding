# SwissKnife real-desktop visual and functional improvement plan

Created: 2026-10-24. Program: `swissknife-visual-functional-v1` (SVF).

The outcome is a desktop whose applications perform their intended user tasks:
an image appears, a note reopens with the saved text, a dataset displays actual
rows, an inference produces a useful result, and a scheduled task exposes its
real state. Backend status panels and recorded button clicks support diagnosis;
they do not establish those outcomes.

The executable plan has 197 tasks and 193 goals/subgoals for the 45 canonical
applications. Each app receives a real baseline, a visual review, a scoped
repair, and independent workflow verification. Shared infrastructure, three
backend qualification tasks, a full regression, three cross-app workflows and
a strict final aggregate complete the program.

## Authoritative artifacts

| Artifact | Role |
| --- | --- |
| [Objective heap](53-swissknife-visual-functional-mcplusplus.objectives.md) | Root goal, shared goals and four goal records per app, including its visual, functional and backend boundary subgoals. |
| [Execution board](53-swissknife-visual-functional-mcplusplus.todo.md) | Single runtime task-status authority; `## SVF-` tasks with dependencies, declared outputs, deterministic commands and validators. |
| `config/swissknife_visual_functional_tasks.json` | Initial canonical JSON/DuckDB ingestion snapshot, preserving executable validation argv and explicit goal references. It does not overwrite runtime statuses. |
| `config/swissknife_visual_functional_supervisor.json` | Exact provider/model, backend endpoints, budgets, scope and safety policy. |
| `swissknife/config/visual-functional-app-contracts.json` | All 45 intended workflows, fixture inputs, concrete actions/results, persistence/reopen, error/recovery, visual checks and genuine backend roles. |
| `data/agent_supervisor/swissknife_visual_functional/` | Namespaced runtime evidence, original screenshots, model invocation records, owned-source hashes, task receipts and lane state. |

The canonical manifest and executable backend contract remain the inventory
authorities. Aliases are tested as launch behavior rather than counted as extra
apps. A changed manifest requires explicit scope reconciliation before closeout.

## Starting evidence and gaps

This plan continues the intended behavior documented in program 43 and its
VDA/SVD goals. It establishes a new execution and acceptance projection; it
does not change historical task statuses or restart their supervisors.

The retained VOG evidence reports 888 clicks and the later VDG evidence reports
458 executed invocations. Those remain useful transport and control evidence.
They do not prove successful user workflows, saved writes, playable media,
usable inference, or the visual quality of every app today.

The older all-app accessibility report used a simulated `page.setContent`
surface. Its pass does not inspect the actual app layouts. The historical
app-improvement report and screenshot collection are missing in this checkout.
Its old harness also accepts generic emitted events for 20 apps and fabricated
looking CID/receipt prefixes for some others. Those acceptance rules must be
replaced with actual state, content hashes and independently retained receipts.

Two retained October 20 samples identify useful pilot questions: Image Viewer
selects a sample without demonstrating decoded image content, while Calculator
devotes much of its visible area to diagnostic cards and crops the keypad.
These are historical observations; fresh baseline captures determine today's
defects. Fix primary task content first and place optional diagnostics behind
compact disclosure controls.

The fresh October 24 Image Viewer preflight confirmed a layout defect: the
selected sample does decode, but its preview lies below the useful app area
(approximately y=876 at desktop size and y=1864 at mobile size). The narrow
toolbar is also obstructed by a graphics warning. Native image decoding and
visible usable preview are separate requirements. The original screenshots,
DOM/layout observations and direct visual inspection are retained in
`data/agent_supervisor/swissknife_visual_functional/preflight/image-viewer-baseline/`.
They remain baseline evidence, not an accepted workflow.

Read-only October 24 checks found reachable MCP++ adapters for all three
owners. The Accelerate adapter nevertheless reports `upstream_available:false`.
That is a specific readiness repair, not a healthy inference backend. Its
qualification task must discover the actual native schema and execute a bounded
operation. A health-only endpoint on another port is insufficient.

## Goal structure

```text
SVF-G000  Every real desktop app performs its intended workflow
  G001  Canonical ingestion and safe autonomous execution
  G010  Exact model route and real K/D/A readiness
  G020  Real desktop/mobile baselines and actionable visual findings
  G030  Trustworthy workflow runner and usable accessible surfaces
  G040  Application repairs
    G101..G145  One goal per canonical application
      -V  Real visual inspection
      -F  Semantic result, persistence and failure recovery
      -M  Correct MCP++ or local/external/policy boundary
  G050  Fresh full regression and cross-application workflows
  G090  Evidence-based closeout
```

All goals begin `active`; tasks begin in the canonical `ready` state and
dependencies decide whether they are selectable. Task completion supplies
evidence to the goal lifecycle. It does not promote a goal to
`verified_complete` or grant `work_complete`/`completion_authority`.

## Execution order

1. **Ingest and prove the route.** SVF-000 checks unique identities, a valid goal
   tree, an independently checked acyclic task graph, canonical status values,
   complete app coverage and preserved execution validators. It imports the
   plan into a dedicated DuckDB snapshot without network extension installation.
   SVF-010 performs a real bounded Grok 4.7 router invocation and retains its
   effective route and native completion record.
2. **Audit owners without hiding degraded service.** SVF-011 records adapter
   health and upstream availability separately. It is an audit task, so local
   visual work can proceed even while an owner needs repair. SVF-040/041/042
   separately qualify K/D/A. App verification depends on the owners it actually
   uses, avoiding a circular gate that waits for an unstarted transport task.
3. **Capture and inspect actual apps.** Each baseline opens a canonical desktop
   app and captures 1440×900 and 390×844 full and primary-area screenshots plus
   DOM, console, layout, source and network observations. Baseline capture
   blocks unapproved remote side effects and explicitly reports
   `baseline_only:true` and `acceptance_decision:not_evaluated`. Pinned-model
   reviews turn those screenshots into evidence-linked defect findings.
4. **Build the trustworthy workflow driver.** SVF-031 tests strict scenario
   admission and independent observation detectors. SVF-032 implements actual
   desktop lifecycle and actions; SVF-033 adds genuine raw MCP proof collection
   and report assembly; SVF-034 runs a real Calculator integration pilot.
   Each stage retains immutable source snapshots so later extensions preserve
   historical evidence. SVF-030 reruns all current foundation checks and verifies
   the actual pilot before application repair can proceed. The pilot is driver
   integration evidence and does not establish full Calculator acceptance.
   This R3 decomposition preserves all 93 completed inspection task contracts
   and replaces the oversized implementation request that repeatedly timed out.
   The maintained lifecycle/action implementation is now supplied in source;
   SVF-032 runs its complete tests and foundation detectors deterministically,
   preserving its original acceptance instead of regenerating correct code.
   SVF-030 replaces synthetic or
   generic action acceptance with actual-app Playwright scenarios and the
   independent report contract below. The first inspection is Image Viewer;
   Notes and Accelerate Panel provide the D and A pilots. The model cannot edit
   the campaign's acceptance contracts, status board or independent validator.
5. **Repair every app.** Each implementation task is scoped to the app's source
   and its declarative workflow scenario. Use existing design tokens, retain
   original useful controls and state, and address the captured defects.
   Syntax/contract checks validate implementation artifacts; the separate
   verification task must demonstrate actual user behavior. Failed verification
   can request bounded scoped repairs and rerun fresh evidence.
6. **Refresh the complete release view.** SVF-900 serially reruns all 45 app
   workflows against final shared source. Changes to CSS, generated surfaces,
   gateway behavior or contracts cannot preserve stale earlier acceptance.
7. **Prove composed workflows.** SVF-910 verifies dataset → inference → saved
   result; SVF-920 verifies CID media → edit/export → reopen; SVF-930 verifies
   goal → task dispatch → real worker result → verified acceptance and recovery.
8. **Close only on current acceptance.** SVF-990 revalidates every current app
   report and all cross-app receipts. Missing, degraded, unverified or stale
   evidence remains an explicit gap. Historical GO and model assertions cannot
   override it.

## Backend and policy contract

All browser-originated owner operations pass through the existing MCP++
gateway and `/mcp/tools/call`. Preserve the declared owner, exact tool/schema,
transport, correlation ID, policy outcome, receipt CID, event-DAG CID and
verified peer identity. Reuse the established HTTP/libp2p connector and UCAN
checks; do not substitute a private `/mcp/artifacts` request for a mediated app
operation or mislabel one transport as another.

- **K / `ipfs_kit_py`:** store and retrieve controlled content, independently
  hash bytes against the CID, inspect real pin/peer state and retain provenance.
- **D / `ipfs_datasets_py`:** display genuine dataset rows and schemas, validate
  search relevance/citations and use actual metadata/provenance results.
- **A / `ipfs_accelerate_py`:** discover actual model/hardware/job capabilities,
  execute bounded real work and validate useful result artifacts and lifecycle
  state. Queued, failed, cancelled, unavailable and completed are distinct.

The current dispositions are 28 tool-backed, 14 browser-local, two external
provider and one policy-blocked app. Browser-local utilities must stay useful
without meaningless backend calls. OpenRouter/OAuth test unconfigured or denied
states honestly when no account is configured. API Keys exposes opaque
references, never secret values. Adding a new remote capability requires a
separate manifest, executable contract and policy change.

Reads and previews can establish read behavior. They cannot prove a durable
write, delivered peer message, trained model or exported playable media. Test
writes use a campaign-specific namespace and confirmation through the existing
UI policy surface, followed by independent read-back and reopen. Do not mutate
user datasets, contacts, repositories, accounts or schedules.

Fixture budgets: small deterministic text/image/media content, at most 1 MiB
per ordinary artifact, bounded dataset samples, and short real inference/job
requests. Training tests use an explicitly supported tiny fixture and a
bounded real step. Resource, provider and ownership failures produce truthful
diagnostics and bounded retries rather than a fallback model or fake result.

## Functional and visual acceptance

Every app contract names an input fixture, exact actions, expected user-visible
results, persistence/reopen, a concrete failure and recovery. A click event,
changed value, static status label, diagram or screenshot alone is insufficient.

At both viewports inspect primary content, legibility, clipping, overlapping
controls, intentional scroll areas, empty/loading/error/denial states, Tab and
Shift+Tab order, visible focus, Enter/Escape behavior and recovery without losing
input. Images must decode, media must play, editors must retain content,
calculations must be correct and live telemetry must identify its source/time.

The workflow driver emits `swissknife.visual-functional-workflow.v1` in
`workflow.json`: `app_id`, `actual_desktop:true`, `source_template:false`,
`contract_sha256`, current `source_sha256`, retained artifact hashes, concrete
checks and app-specific semantic assertions. Required categories include
`primary_result`, `keyboard`, `desktop_layout`, `mobile_layout`, and
`error_recovery`. Semantic IDs cover `result_1..N`, `persist_reopen` and
`failure_recovery`; observations must be independently evaluated values, not
truthy prose or copied expectations. The worker's closed assertion schema is
the executable authority for their shape.

For tool-backed operations retain raw receipt and event-DAG artifacts, verify
their content addresses and expected owner/tool/correlation/outcome, and compare
semantic results against actual output bytes/state. The independent validator
must not trust a report's `receipt_verified:true` without its retained proof.
Unexpected backend calls fail local/external/policy-boundary cases.

Grok visual findings are proposals grounded in immutable captured PNGs and
native read activity. The adapter records the limits of its observation: tool
read counts and model-reported paths do not independently prove pixel delivery.
Do not turn that limitation into an invented visual attestation. Actual browser
observations, retained screenshots, semantic assertions and the separate review
decision together support acceptance; unresolved visual findings remain gaps.

## Model, ownership and recovery

The configured route is `ipfs_accelerate_py.llm_router.generate_text` with
`provider="grok_cli"`, `model_name="grok-4.7"`, temperature zero,
`allow_local_fallback=False`, `allow_cross_provider_fallback=False`, and model
retry disabled. This uses the existing authenticated Grok CLI session. It does
not silently switch to Codex, a local model, another Grok version or the stale
implicit REST default. Exact effective-route/native completion evidence is
required. The model receives bounded relevant context and native read-only
tools; edits are checked proposals applied by the lease-owning worker.

Every model call has a deadline, output limit and turn budget. Each worker
attempt has a finite deadline and bounded repair loop. Source-before hashes,
declared paths, input/evidence hashes and independent validation protect against
stale or overlapping edits. Persisted retries begin after failure; changed
declared source/command contracts can rearm their task budget. A fresh heartbeat
is not proof of meaningful progress.

The foreground runner is the real `ipfs_accelerate_py.agent_supervisor.rescue`
lane, with direct provider CLI implementation disabled. All task commands call
the controlled Python worker, which alone invokes the pinned router adapter.
The registered `swissknife-visual-functional` lane holds the existing parent Git
common-directory checkout lease for its entire lifetime. Worker ancestry and
exact PID/birth/UUID identity are verified even when commands use new process
groups. A systemd user service restarts the foreground runner and contains its
command descendants in the same control group.

Before launch and each source write, check ownership, Git interruption state,
operator holds and predicted-file overlap. Keep
`IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS=0`, disable ephemeral worktrees and
worktree reconciliation, and never reset, stash, clean, force-checkout or replace
another owner's files. The old VOG/VDG supervisors and foreign services remain
untouched. Lease contention or unowned overlap is an explicit ownership wait,
not permission to steal work. The planner avoids avoidable waits through scoped
outputs, known dependencies and an initial selectable frontier.

## Operating the program

From the parent repository:

```bash
python3 scripts/swissknife_visual_functional_supervisor.py --preflight-only
python3 scripts/swissknife_visual_functional_llm.py \
  --profile config/swissknife_visual_functional_supervisor.json \
  --task-id SVF-010 --check-route
python3 scripts/swissknife_visual_functional_supervisor.py --print-systemd-unit
```

The service uses the exact registered lease-wrapper command from
`swissknife/docs/supervisor-lane-inventory.json`; do not bypass that wrapper.
The intended user unit is `swissknife-visual-functional-supervisor.service`.
Its runtime lives only under `data/agent_supervisor/swissknife_visual_functional`.
Check its lifecycle JSON, current task, task transitions, model progress and
owned browser activity. An active process alone is not the startup success
criterion: ingestion, exact-model invocation and a genuine task transition must
be observed. Subsequent visual baseline capture must use the actual app.

Use this execution board to track work. Do not regenerate it after execution
starts: the generator deliberately refuses to overwrite completed/in-progress
statuses. Revise requirements through explicit scoped task/goal changes and
repeat preflight. Do not commit runtime secrets, raw credential material or
transient process state.

## Persistent watchdog and recovery

`swissknife-visual-functional-watchdog.service` observes the registered
foreground service every 30 seconds using the reusable accelerator
`rescue.leased_service_watchdog` module. Its configuration is
`config/swissknife_visual_functional_watchdog.json`; current telemetry and
incident records live under
`data/agent_supervisor/swissknife_visual_functional/watchdog/leased-service/`.

The watchdog verifies the loaded systemd unit, its file hash, exact registered
arguments, the checkout lease, process births, launch trampoline, actual
foreground ancestry and control group. Recovery restarts only that registered
service, allowing its lease wrapper and cgroup to perform cleanup and
replacement. Holds, foreign owners and unowned dirty outputs suppress actions.
Restart attempts and cooldowns persist; changing timestamps or verbose output
cannot replenish their budget or extend declared task deadlines.

The October 24 watchdog audit found an actual ordering bug: document-order
selection let lower-priority visual reviews run before the ready P0 workflow
harness. The rescue scheduler now applies stable explicit P-tier priority
ordering while preserving legacy ordering when priorities are absent.
Remaining SVF tasks also declare read-only `Execution inputs`. Content changes
to an imported model adapter, router, capture helper or configuration can
rearm that task's exhausted contract budget without deleting counters or
granting write permission to those files. Timestamp-only changes do not rearm.

The Notes review exposed another failure class: valid image-tool messages
exceeded the default 256 KiB stream-frame limit. Image reviews now request a
verified image-sized bounded frame budget, while ordinary router calls retain
the original default and malformed/oversized output still fails closed.
Review context is limited to the actual app and supplied images. Atomic native
progress counters distinguish ongoing model work from silence, and immutable
invocation archives preserve each failure. The formerly failing Notes review
completed with four image reads and zero oversized frames after these changes.

Operational checks:

```bash
systemctl --user status swissknife-visual-functional-supervisor.service
systemctl --user status swissknife-visual-functional-watchdog.service
python3 scripts/watch_swissknife_visual_functional_supervisor.py --once
```

The watchdog reports provider failures and blocked dependency frontiers as
actionable incidents. It never marks tasks complete or substitutes activity
for acceptance. Source repairs, bounded worker retries and independent
validators remain responsible for advancing the taskboard.

The R3 watchdog persists failure history by task and execution contract before
starting work. Worker or service PID changes and fresh native frames cannot
erase failures. Repeated failures, an exhausted required dependency and work
without semantic validation produce degraded incidents. Six unchanged semantic
failures exhaust the task's bounded budget while independent ready tasks can
continue. A content change to declared execution inputs permits a fresh bounded
attempt; timestamps and cooldown expiry alone do not. Semantic incidents do
not justify a service restart. Ownership loss and expired physical deadlines
retain their separate bounded recovery checks.

Repair proposals use the pinned Grok route with compact per-task context;
foundation implementation stages request at most sixteen turns and 12,288 output
tokens. The initial scoped stage used 96 KiB of model context; later stages allow
up to 256 KiB to hold the expanded maintained runner and tests in full, plus only
their compact protocol or Calculator context. Complete editable files take priority
within that budget. The initial eight-turn, 48 KiB setting exhausted its read budget
before proposing changes. After complete-source calls still spent the entire
300 seconds in one reasoning turn without output, the provider deadline was
calibrated to 600 seconds. Task deadlines and finite unchanged-failure budgets
remain independently enforced. Optional per-task `reasoningEffort` is validated
and retained in receipts; requesting `low` did not resolve those timed-out calls.
Oversized secondary sources include explicit line excerpts, full hashes and read
paths. Declared new files may have absent parents during planning;
parent creation and source application occur only under repeated lease/hold
checks, with no-clobber publication and rollback that preserves foreign work.
Startup accepts existing campaign source only when its exact current hash
matches the ownership ledger. Node test validation requires an actual positive
pass count in either TAP or the current spec reporter, and rejects zero passes.

Structurally valid but rejected literal-edit proposals are retained with hashes
and typed path/hunk/match-count diagnostics, with no source application or success
authority. The next scheduled repair receives feedback bound to the same task
and exact source hashes; changed sources or task contracts invalidate it. Native
stderr/thought bodies, credential content and unallowlisted proposals are never
retry inputs. Repairing a declared contract renews its bounded retry budget but
retains degraded failure health until actual semantic validation passes.

## Automatic foreground recovery (R4)

A task-declared repair now runs after a finite semantic failure budget. Its
admission is persisted before dispatch, bound to the current journal row and
source hashes, and executed inside the existing checkout lease. Only approved
production files or explicit fixtures may change; controllers, validators and
unit tests remain protected. A no-op, failed, interrupted or replayed admission
grants no producer probe. A successful source change permits the original
producer and original checks to run; the repair never completes the task.
At most two admissions per task survive service and PID changes.

SVF-005 proves this path using an isolated JSON canary and immutable checker.
On 2026-10-25 its real producer failed once, Grok4.7 through `llm_router` repaired
only the admitted fixture with zero native tools, then the original checker
and validator passed. The spent budget stayed 1/1 and failure history remained.
This operational rehearsal grants no application acceptance.

Repair calls now use supplied source with native tools disabled, preventing
the repeated 30–54 reads that exhausted the implementation frontier. Visual
reviews retain image reads. Blocked responses and needs-changes responses
without edits cannot complete repairs. Nonempty retained proposals are checked
against the caller's explicit source allowlist before and after application.

Repair calls default to `repairReasoningEffort: low` and request a small patch
to existing code and its workflow scenario. Reviews and route probes keep
their own settings. A timeout with thought events but no response is recorded
separately; native activity never extends the task deadline.

The October 25 Image Viewer repair also exposed a router defect: presentation
cleanup stripped HTML tags and decoded entities inside JSON edit strings.
Grok output now preserves literal response content, including code, HTML and
entities. Seventy-four transport tests cover the actual stream/parser return
path and legacy outcomes. The campaign's 192 unit tests also pass. The retained
audits are under `watchdog/request-20261025/` in the runtime directory above.

Completed canary validation checks immutable model/context/feedback artifacts,
the current applied journal row and exact repaired fixture bytes. Later
controller changes do not erase that historical proof. This evidence-only
check cannot authorize another producer; recovery dispatch still requires
strict current source hashes and an unspent admitted journal row.

Every app repair, including browser-verification retries, receives the exact
readonly input scenario specification. Its root/phase/action/probe fields are
separate from the runner's observed output report. The supplied example is
checked by the actual scenario parser without launching a browser or calling
an owner. Scenario validity still supplies no workflow acceptance.

The continuation audit on October 25 found that failed browser attempts left
the fixed output directory nonempty, so later retries failed before launching
Chrome. Each invocation now uses a fresh immutable attempt directory. Receipts
bind the successful report to its exact producer and screenshot set; failed
attempts remain available. A failed final visual review supplies its actual
findings to the next repair rather than only a generic error.

Canonical workflow JSON is production input: its hash participates in both
recovery admission and material source-change detection. Generated reports and
runtime proof files remain excluded. Complete edit targets stay mandatory;
readonly global catalogues are represented by the app's canonical contract and
original source hashes, which are rechecked after the call. This keeps the real
Accelerate Panel repair prompt within its existing budget without truncating
the editable source. Lane health also retains failures on other pending tasks
while a fresh active task runs. Source changes do not erase that history.

The continuation's preflight, recovery tests, real prompt-budget audit and live
observations are retained under `watchdog/request-20261025-0516/`.

Revision `SVF-20261025-R5-native-owner-recovery` adds the actual desktop, Vite,
gateway, connector, owner SDK and service sources to unfinished tasks' readonly
execution inputs. The canonical supervisor API ingested 197 tasks, 193 goals,
197 validators, 192 goal edges and 399 task dependencies into an isolated audit
database. Migration preserved all 115 completed task objects and board blocks;
82 tasks remain pending. Dependency graphs and stored execution inputs were
checked without launching tasks or changing live completion status.

Two enabled user services provide this campaign's genuine Kit path:
`swissknife-visual-functional-native-kit.service` runs the pinned Python SDK on
loopback port 18314, and `swissknife-visual-functional-kit-facade.service` exposes
the MCP++ facade on port 18316. Strict forwarding propagates native failures;
cached artifacts cannot substitute for native SDK results. Existing unrelated
owner services are unchanged. The workflow receives the configured Kit,
Datasets and Accelerate endpoints through its child process environment.

An actual Chrome primary-flow diagnostic passed all 13 checks with trusted UI
consent and genuine native SDK image bytes. A separate same-connector probe
passed 17 functional checks: an unpublished CID failed, then the valid image
was retrieved immediately afterward. The gateway represents a failed native
operation with HTTP 200 and `ok:false`; the probe retains its original HTTP
status expectation mismatch. Neither diagnostic supplies full application
acceptance. The application task must still pass its complete persistence,
genuine failure/recovery, viewport and final visual checks.

The October 26 continuation found 134 completed tasks and 63 pending tasks.
Revision `SVF-20261026-R6-observed-failure-recovery` preserves all completed
JSON objects and board blocks while binding unfinished verification recovery
to each task's actual `last-execution-failure.json`. Failure observations are
separate from rejected model proposals, so a model refusal cannot replace the
original assertion failure with an uninformative refusal code.

Failed workflows retain bounded, sanitized actual/expected values, probe and
phase details, owner responses and rendered DOM observations before closing
their owned resources. These are diagnostic artifacts with no acceptance
authority. The worker hashes and fences those artifacts, and the recovery
bridge supplies their immutable copies to the model in full. Existing edit
targets and the original checks still control what may change and what passes.
Repair proposals do not require performing final visual review; that separate
review remains mandatory for application acceptance.

A typed, task-bound browser-contention refusal exits 75 and enters a resource
wait instead of requesting application edits or spending semantic recovery.
Acquisition attempts have a persisted bounded window and capped backoff. A
closed window waits five minutes, then retries automatically even when source
has not changed, so a long-running foreign browser cannot leave a permanent
resource block. Total refusals and recent window history survive restarts;
prior semantic failures and spent model-recovery budgets remain intact.
The source fixes, real browser qualifications and ingestion audit are retained
under `watchdog/request-20261026-0315/`.

Revision `SVF-20261026-R7-native-fixtures-blocked-cache` addresses the next
observed blockers while preserving the same 197 tasks, 193 goals and all 134
completed entries. The campaign now uses dedicated loopback Datasets port
18312 and Accelerate port 18315, alongside Kit port 18316. Existing unrelated
listeners are unchanged. Qualified owner inputs are explicit readonly data in
`config/swissknife_visual_functional_payload_fixtures.json`, passed to the
browser child and model repair context by the supervisor profile.

Native JSON error blocks now retain bounded, sanitized error messages and
typed codes through the mediator. This exposed a missing Notes index and a
missing inference model, rather than treating every owner rejection as the
same opaque failure. A validated blocked proposal is retained with its concrete
failure, route, task and original source hashes. Identical failures do not call
the paid model again; changed sources, dependencies, scope or actual errors
can qualify a new proposal. A cache hit remains a failure, grants no acceptance,
and replenishes no recovery budget. Correlation IDs and timestamps do not
defeat this check. Readonly recovery source-map identities are projected for
model context; the full original admission remains protected by bridge fences.

The owned native accelerator executes the actual `InferenceBackendManager`
with cached GPT-2 weights on CPU, offline and without an external provider.
Each request has a 30-second subprocess limit and generates at most four new
tokens. Catalog, hardware and synchronous completed-record operations remain
honest; unsupported operations and cancellation are not advertised. The MCP++
facade retains its genuine Profile A descriptors, UCAN and receipt machinery.
SDK/backend/service source drift restarts only this supervised native service.
Fresh readiness verifies actual generated tokens and matching record readback;
historical queue-only readiness evidence remains unchanged.

Notes uses an explicitly prepared, isolated existing collection. A matched-only
SDK option stores actual indexed documents in the authoritative DuckDB store
and resolves only published, non-tombstoned matches. Existing collections keep
their default document policy. Search returns the real matched document/title
and provenance; the app can open that returned content. Local editor changes
are explicitly not claimed to have been indexed automatically. Preparation and
readback are operator fixture checks, not application acceptance. The original
browser workflows and final visual review still decide each task.

Source, native SDK, fixture, browser and canonical-ingestion evidence for this
continuation is retained under `watchdog/request-20261026-0437/`.

The maintained proof/report runner, real Calculator pilot and three owner
utilities now execute deterministic checks instead of regenerating implemented
code. Owner readiness verifies genuine IPFS bytes, actual dataset rows and an
executed bounded scheduler job; scheduler evidence is explicitly not inference
or GUI acceptance. The Calculator pilot performs actual arithmetic, keyboard
and error recovery at both viewports, retaining source-bound screenshots.
Full app acceptance remains with the individual application tasks.

## Shared desktop and required-phase recovery (R8)

`SVF-035` owns the shared desktop notice and backend status presentation under
`SVF-G030`. Pending app verification depends on its protected checks. Shared
defects have a declared repair owner; individual app edit scopes remain narrow.
Warnings retain their real state and full details through accessible disclosure,
while primary application controls remain usable on both viewports.

Each task's required final visual phase has a durable, finite paid repair
budget across source changes and restarts. Qualified retained visual repair
receipts seed the ledger; new admissions are saved before model dispatch.
Exhaustion retains an actionable scoped gap and the failed review evidence.
Only the original validated passing phase closes that barrier. Existing
foreground recovery spend, task completion and acceptance rules are preserved.

The Notes negative case must recover through a fresh authoritative search,
opening the real returned note, and successful local save/readback after
clearing the failed reference. Focusing an editor cannot establish recovery.
Local editing readiness remains distinct from recovery of a remote conflict.

Maintenance and fresh canonical plan ingestion evidence is retained under
`watchdog/request-20261026-0535/`. The watchdog stays active during maintenance,
honors the recorded hold, and resumes monitoring the original service after
preflight. Remaining app tasks still require real workflows, genuine MCP++
receipts and the pinned Grok 4.7 visual gate through `llm_router`.

## Native API and remaining workflow repairs (R9)

Recovery context identifies the canonical module API, exact binding policy,
tool candidates and readonly gateway/helper hashes. Native apps import
`invokeNativeTool` directly; a binding ID is not a reviewed network tool key.
The scenario runner refuses a request to show a confirmation dialog for an
ungoverned binding before opening Chrome. Governed bindings still require a
real trusted confirmation, including storage reads governed by a broader
write capability. Native Kit errors preserve bounded, sanitized owner causes
through the facade so an agent can repair the actual failure.

File and repository inputs are actual IPFS Kit SDK stored bytes with verified
raw CIDs and readback. Catalog input is the actual local accelerator model
catalog, stored through Kit and retrieved through Datasets. Fixture arguments
are typed, hash fenced and separately qualified; preparation is not app
acceptance. Model Manager's existing governed binding now includes actual
catalog and inference operations; status or hardware lookups cannot substitute
for generated output. Unsupported download, credentials and model choices stay
explicit without fabricated weights or results.

Calendar displays the actual selected date, event, timezone and conflict.
Cinema scopes its timeline styles away from globally loaded application CSS
and preserves saved state only for the exact verified project snapshot.
AI Chat derives cited reference facts from retrieved, CID-checked catalog
bytes separately from the actual model continuation. Selected context enters
the bounded model request exactly once; cached transcripts do not claim fresh
verification. Its consent scenario uses genuine keyboard confirmation so
keyboard interaction is joined to its observed answer. Model Manager and
Hugging Face retain clearly labelled stored catalog metadata on reopen while
requiring actual owner results for current availability. IPFS Explorer checks
retained bytes against their CID before reconstructing a verified preview.
Every stylesheet loaded by the desktop is a readonly execution dependency.
All 162 previously completed task contracts and board blocks are preserved;
the 36 pending tasks retain their acceptance, permissions and recovery spend.
The original workflow, independent validator and final Grok visual review
still decide completion. Evidence is retained under
`watchdog/request-20261026-2341/`.

## Per-application scope

The following table is generated from the 45 explicit behavior contracts.
Detailed inputs, actions, expected outcomes, persistence, negative cases,
backend tool candidates and visual checks are in the contract JSON and each
app's linked execution tasks.

<!-- SVF-APP-TABLE -->

| App | Boundary | Intended primary result |
| --- | --- | --- |
| `terminal` | browser_local | Output describes the real local operation, history retains entered commands, and the prompt remains usable |
| `vibecode` | tool_backed | Editor and reopened bytes contain the intended change; diff and any requested analysis describe that function |
| `music-studio-unified` | browser_local | Track/note state reflects edits and audible playback or a truthful audio-permission state is present |
| `ai-chat` | tool_backed | Answer addresses the known question, cites retrieved content and preserves user/assistant messages with authentic owner results |
| `file-manager` | tool_backed | Selection, preview and reopened file agree with actual bytes; the original remains intact |
| `task-manager` | browser_local | List and filter reflect the actual open applications; unavailable host metrics are explicitly labeled |
| `todo` | browser_local | Edited title and completion state are correct; dependencies are shown honestly without claiming remote dispatch |
| `model-browser` | tool_backed | Selected model is in the owner catalog; a terminal owner result contains usable prompt-related output and actual run status |
| `huggingface` | tool_backed | Selected card and prepared artifact refer to the same actual item; unsupported download or inference stays explicit |
| `openrouter` | external_provider | Actual provider output or truthful unavailable/authentication state is visible; secret values never enter DOM or evidence |
| `ipfs-explorer` | tool_backed | Retrieved bytes hash to the requested CID and visible preview matches their type; pin state is actual observed state |
| `device-manager` | tool_backed | Browser device access and owner hardware are labeled separately; values have a real source and observation time |
| `settings` | browser_local | Saved preference changes actual browser UI state; invalid values remain rejected and reversible |
| `mcp-control` | tool_backed | Schema, owner, exact tool and result agree; actual status and authentic correlation/receipt are inspectable |
| `api-keys` | policy_blocked | Credential values are absent from rendered/evidence output and every Python-owner dispatch remains policy-blocked |
| `github` | tool_backed | Displayed repository/file identity and review evidence refer to actual selected content; any write remains confirmation-bound |
| `oauth-login` | external_provider | Provider lifecycle is truthful; authorization codes/tokens are not rendered, logged or retained in screenshots |
| `cron` | browser_local | Next-run and paused state match local configuration; local timers are not labeled backend jobs |
| `navi` | tool_backed | Matched context is relevant and any executed action has an actual owner result; ambiguity is not silently guessed |
| `p2p-network` | tool_backed | Known peer, connected peer and empty swarm states are distinct and come from actual owner responses |
| `p2p-chat-unified` | tool_backed | A sent/delivered state is supported by actual peer acknowledgement; queued is not delivered; message content remains exact |
| `neural-network-designer` | tool_backed | Graph geometry and schema agree; invalid shapes are rejected; any compile result belongs to the exact saved graph |
| `training-manager` | tool_backed | Job identity, queue/running/terminal transitions and output/checkpoint are actual owner state; previews are labeled previews |
| `calculator` | browser_local | 12.5 × 4 equals 50; invalid arithmetic remains explicit; history restores the exact expression without fake proof IDs |
| `clock` | browser_local | Elapsed timer state follows wall time within declared tolerance and notification state is honest |
| `calendar` | browser_local | Event is on the correct date/time, edit persists and overlapping events remain understandable |
| `peertube` | tool_backed | Video frames or supported audio decode, playback time advances, seeking changes time and failure is honest |
| `friends-list` | tool_backed | Contact identity and state changes are actual retained records; unavailable presence is not called online |
| `image-viewer` | tool_backed | An image is visibly decoded with positive natural dimensions; transformed image remains usable and CID bytes match |
| `notes` | tool_backed | Saved/reopened text matches the editor and search returns relevant actual notes with meaningful provenance |
| `media-player` | tool_backed | Playback currentTime advances, seek position is honored and media identity/duration come from decoded content |
| `system-monitor` | tool_backed | Values come from actual observations, stale age is explicit and unavailable metrics are never randomly generated |
| `neural-photoshop` | tool_backed | Canvas pixels/layer state reflect the edit; actual output image decodes and corresponds to the requested operation |
| `cinema` | tool_backed | Timeline changes persist; export is an actual playable artifact or clearly unsupported, never a fabricated render |
| `strudel` | browser_local | Valid pattern executes in the local audio engine; syntax errors identify the real failure and do not claim remote inference |
| `strudel-ai-daw` | browser_local | Local composition and undo are real; assistance is not labeled executed unless a declared genuine capability exists |
| `music-studio` | browser_local | Classic workflow remains usable and local; legacy alias does not silently open another app or claim remote rendering |
| `p2p-chat` | tool_backed | Legacy message delivery is backed by real peer state, offline messages remain queued and migration is explicit |
| `datasets-browser` | tool_backed | Visible rows and schema match real loaded data; filtering selects the known record and failures are honest |
| `accelerate-panel` | tool_backed | Actual model output is usable for the input; queue/running/terminal states reflect owner state and preview is not execution |
| `idl-explorer` | browser_local | Displayed schema matches selected descriptor, valid input passes and invalid field has a useful local explanation |
| `glasses-preview` | browser_local | Preview content matches packet data and its display constraints; physical device delivery is never claimed by the simulator |
| `orb-auto-ui` | tool_backed | Rendered field requirements match schema, invalid arguments cannot execute and output belongs to the chosen owner/tool |
| `mcp-plus-plus` | tool_backed | Transport is actual observed HTTP/libp2p, peer identity verifies and retained result/receipt agree on owner/tool/correlation |
| `agent-supervisor` | tool_backed | Task completion follows actual output validation, dependencies explain blockers and heartbeat alone is not progress |


### R10: storage admission, shared styles and regular source identities

The supervisor supplies exact, bounded readonly shared CSS rule excerpts after a failed visual review. Rules retain complete source hashes, conditional headers and the actual stylesheet order from the fenced desktop document. Complete editable files remain inline; omitted rule counts are explicit. The excerpts diagnose source interactions and cannot establish rendered acceptance or expand edit authority. Ordinary nonvisual repairs retain their existing context budget.

Strudel continues launching through its existing app alias. Its canonical source identity and pending repair/verification contracts name the regular `web/js/apps/strudel-grandma.js` implementation. Source and evidence readers continue refusing symlinks. Completed task objects, Markdown blocks, goal hierarchy, acceptance conditions and lifetime recovery spending remain preserved.

The watchdog checks durable storage before recovery admission and service restart spending. ENOSPC and EDQUOT produce private emergency telemetry and a storage wait without restarting a healthy owner or repeatedly exiting the watchdog. Unpersisted restart reservations are rolled back before any service action. Writable storage must pass the original durable probe before recovery resumes; unrelated I/O and permission failures remain failures. Automatic cleanup never authorizes deletion of host backups or foreign evidence.

AI Chat explicitly uses a desktop row layout while preserving the narrow column layout. Training Manager avoids desktop flex-basis values stretching mobile status rows. Navi retrieves the qualified native dataset catalog CID, verifies the returned content bytes, and resolves only actual matching rows; reopen and recovery checks require the selected target and actual returned matches. These changes still require fresh original browser workflows and independent final visual review before task completion.


### R11: genuine native observations and embedding context

Kit node identity and swarm peer observations use public pinned SDK operations against the configured Kubo node. Explicit Kubo `Peers: null` is retained as raw owner data, normalized to an empty list, and bound by a labelled canonical observation hash; missing or erroneous responses never establish an empty swarm. Native services and facades verify the exact SDK operation, source, correlation and observations. No pubsub delivery is invented.

Accelerator diagnostics execute the actual SDK `HealthChecker.check_detailed` and `PrometheusMetrics.generate_metrics` in bounded local subprocesses. Health reports SDK liveness separately from native inference readiness. CPU and memory values are actual OS samples; exported process metrics are explicitly scoped to the observation subprocess. GPU utilization remains unmeasured. There is no model inference, external provider fallback, fake loaded-model component or noop exporter in these diagnostics. The existing CPU inference limits and routes remain unchanged.

Repair context includes a bounded exact quotation of the native content-slot and operation-disclosure embedding contract, with complete readonly source hashes. Models can locate injected native disclosure siblings without guessing unseen code. Optional CSS projection adapts before provider admission while complete edits and required failure data remain intact. Remaining tasks acquire only three new readonly observation dependencies; all167 completed task objects and Markdown blocks, the 193-goal hierarchy, acceptance conditions and lifetime spending remain preserved.

AI Chat keeps disclosures in its vertical chat area and provides explicit transcript navigation. Hugging Face content receives a bounded flex-height chain, readable status and wrapped narrow tabs. MCP Control and P2P Network display actual typed owner observations and retain provenance; checks do not accept a tool label or a count-only response as successful execution. Fresh original workflows and final visual reviews still decide task completion.

### R12: storage admission and the owned IPFS runtime

Revision `SVF-20261027-R12-storage-admission-and-owned-ipfs` binds the clean storage-capacity helper and the campaign-owned Kubo watchdog, configuration and two service templates as readonly execution dependencies for the 31 unfinished tasks. These files receive no edit or recovery authority. All 167 completed task objects and Markdown blocks, the 193-goal hierarchy, original validators, app acceptance, dependencies and lifetime budgets remain preserved.

Storage pressure remains a resource wait before a new semantic or model admission. Already admitted work keeps its durable spending. Recovery requires the existing capacity and durability checks; it grants no task completion. The replacement Kubo runtime uses a separate campaign-owned repository and identity, loopback endpoints and bounded resources, preserving the shared legacy daemon. Actual SDK add/cat, content-CID and byte-digest evidence qualify controlled backend fixtures only. The readonly owner-watchdog bindings do not grant application or final visual acceptance.


## R13: native messaging and supervisor task dispatch

The incremental R13 plan adds SVF-043 and SVF-044 under the existing backend-readiness goal. It preserves every completed task object and board block, all goals and canonical app requirements, and all existing repair/recovery budgets. The started board remains the runtime status authority; the original generator refuses to regenerate it.

SVF-043 implements real SDK delivery between two newly owned loopback peers. Its protected qualification joins actual original-SDK calls, independent receiver and acknowledgement bytes, strict scope/input refusals and deduplicated retry. Accepted publication alone is not delivered or durable. The first foundation excludes real stopped-node recovery; original chat offline/recovery, consent, receipt and visual acceptance remains mandatory. Primary storage5031 and shared legacy5021 are preserved.

SVF-044 implements the existing supervisor wire alias using actual IntentRepository, DatabaseTaskSource and VerificationProcessRunner. Protected offline workers, a separate output validator, real process/resource evidence, dependency readiness, evidence-fenced CAS, cancellation/timeout and actual readback qualify the isolated fixture. It never instantiates quarantined WorkflowCoordinator or accepts browser code/commands/paths. Ordinary cached CPU inference is preserved.

The protected ownership helper reloads only a pre-registered native/facade pair under the actual active foundation worker and physical checkout lease, with verified source, PID birth, cgroup and listening sockets. SDK tracing uses a short explicit capture window; expiry or capture limits do not permanently break ordinary backend calls. Protected gate and native observer code is outside model edit scope. Full implementation API and compact app-only contracts are in swissknife/docs/svf-native-foundation-contracts.md and the declared app contract JSON files.

The worker also fences repeated reviews of an unchanged exhausted visual phase. Actual source remediation enables the original acceptance checks again; the guard never refunds repair spend or grants completion. Each new backend foundation must complete before its dependent app tasks; their original browser, real data, keyboard, reopen/recovery and Grok4.7 final visual review remain required.


## R14: Independent final acceptance at both viewports

Actual Media Player evidence exposed a coverage gap: the earlier runner executed semantics once at desktop size, then reopened the application and checked mobile layout. Its mobile image could show initial/demo state. Existing accepted receipts remain historical evidence; they cannot satisfy final dual-viewport program coverage.

The45 final-app-verify tasks SVF-1001 through SVF-1045 depend on all45 original app verification tasks and the real pubsub/supervisor foundations. Each uses its own existing-size3600-second bound (or its original app bound), complete original scenario in separate initially canonical desktop/mobile sessions, source-bound immutable child reports and exact result images, and fresh Grok4.7 review through llm_router. These readonly tasks create no repair budget. Actual failures require separately authorized scoped remediation using existing budgets.

SVF900 consumes all45 current validated final-app receipts and joins; SVF990 independently checks those joins, current sources and all3 original cross-app receipts. Missing mobile semantics, stale/swapped screenshots, missing/failed visual review or old V1 layout-only reports refuse final acceptance. The original task900/990 deadlines, all original acceptance text, completed task objects/blocks, profile route and existing budgets remain unchanged.
