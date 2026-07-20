# SwissKnife All-App MCP++ Improvement Program

Status: active program plan
Created: 2026-07-20
Taskboard: `implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md` (`SVD-132` through `SVD-182`)
Objective graph: this document (`VDA-G000` through `VDA-G054`)

## Purpose

Use the `ipfs_accelerate_py` agent supervisor to take every canonical
SwissKnife virtual-desktop application from launchable UI to a verified,
polished, browser-safe operator surface. Each application must make a useful,
policy-governed contribution to the three MCP++ backend families:

- `ipfs_kit_py` (K): CIDs, content retrieval, persistence, peer transport,
  storage receipts, and event-DAG checkpoints.
- `ipfs_datasets_py` (D): data search, metadata, provenance, policy/logic,
  semantic context, and evidence analysis.
- `ipfs_accelerate_py` (A): model execution, hardware-aware jobs, scheduling,
  supervisor operations, telemetry, and bounded automation.

The program does not add meaningless backend calls to local utilities. Every
app still displays all three backend health and policy states, while its primary
workflow uses the backend roles that are semantically useful. A missing,
denied, unavailable, or intentionally local capability is an explicit UI state
with a recovery path, never a hidden fake success.

The canonical scope is the 45 applications in
`virtual-desktop-app-manifest.ts`. The larger simulator screenshot count also
contains Agent Supervisor operations; those are exercised as interaction
scenarios of the `agent-supervisor` application rather than treated as separate
desktop applications.

## Root Goal

## VDA-G000 Polish every canonical SwissKnife desktop app around MCP++

- Status: active
- Fib priority: 1
- Track: virtual-desktop
- Bundle: objective/virtual-desktop/all-app-program
- Parallel lane: all-app-program
- Goal: Every canonical app has a reliable launch path, a useful primary
  workflow, mediated MCP++ capability use, visible policy and recovery states,
  responsive accessible UI, and current browser evidence for desktop and mobile
  viewports.
- Evidence: app manifest, app-improvement matrix, live backend execution
  receipts, Playwright screenshots, accessibility report, release evidence.
- Outputs: `swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-improvement/`,
  `swissknife/docs/virtual-desktop-app-improvement-matrix.md`.
- Validation: `cd swissknife && npm run test:e2e:app-improvement && npm run test:run -- test/e2e/virtual-desktop-all-app-improvement.spec.ts`.
- Conflict policy: Keep the manifest as the source of truth. Add adapters and
  focused controls rather than duplicating app registries or exposing backend
  URLs, credentials, host paths, or Python processes to the browser.

## Shared Subgoals

## VDA-G001 Observable all-app launch and interaction baseline

- Status: active
- Parent: VDA-G000
- Fib priority: 1
- Track: test
- Goal: Open every manifest app from the desktop launcher, execute its primary
  visible action, record focus/layout/console/network evidence, and preserve a
  deterministic failure screenshot.
- Evidence: `virtual-desktop-app-manifest.ts`, Playwright app runner, per-app
  desktop/mobile screenshots, console and network records.
- Taskboard: SVD-133

## VDA-G002 Three-backend mediated capability contract

- Status: active
- Parent: VDA-G000
- Fib priority: 1
- Track: mcp
- Goal: Each application exposes browser-safe status for K/D/A, uses the
  shared gateway for its declared primary operations, and retains CID,
  correlation, policy, receipt, and recovery information without direct backend
  connections from the browser.
- Evidence: all-app gateway, capability matrix, live HTTP/libp2p receipts,
  policy and recovery envelopes.
- Taskboard: SVD-134

## VDA-G003 Per-app workflow completion

- Status: active
- Parent: VDA-G000
- Fib priority: 2
- Track: apps
- Goal: Complete the app-specific goals listed in the application matrix below.
- Evidence: one namespaced app-improvement report and screenshot pair per app.
- Taskboard: SVD-135 through SVD-179

## VDA-G004 Visual quality, accessibility, and recovery consistency

- Status: active
- Parent: VDA-G000
- Fib priority: 2
- Track: ux
- Goal: Every application remains usable at desktop and narrow mobile widths,
  has clear loading/empty/error/denied states, keyboard focus order, readable
  status, and no clipped or overlapping controls.
- Evidence: multi-viewport Playwright and accessibility report.
- Taskboard: SVD-180

## VDA-G005 Cross-service release proof and supervisor operation

- Status: active
- Parent: VDA-G000
- Fib priority: 3
- Track: release
- Goal: Prove real read-only HTTP and libp2p tool calls, governed write dry
  runs, cross-service workflows, and Agent Supervisor goal/task lifecycle
  through the desktop before release evidence is refreshed.
- Evidence: app-improvement tool matrix, all-app receipt catalog, release
  evidence, supervisor state and event log.
- Taskboard: SVD-181, SVD-182

## Per-Application Goals and End States

Each row is an active subgoal of `VDA-G003`. K/D/A identifies the useful role
of each backend family. Every app also has the shared K/D/A status and recovery
panel from `VDA-G002`.

| Goal | Task | App | End-state primary workflow | K / D / A backend roles | UI/UX completion criteria |
| --- | --- | --- | --- | --- | --- |
| VDA-G010 | SVD-135 | terminal | Run mediated safe commands against selected workspace content. | K: CID files; D: indexed workspace/policy; A: bounded command planning. | Command, streamed result, CID/receipt link, denial and timeout output remain readable. |
| VDA-G011 | SVD-136 | vibecode | Search, inspect, and improve a code artifact with evidence. | K: source snapshots; D: code knowledge/provenance; A: analysis job. | Editor focus, diff/result, loading/error panels, and keyboard operations are stable. |
| VDA-G012 | SVD-137 | music-studio-unified | Save a project, inspect sample rights, and run an optional assisted render. | K: project/media CIDs; D: sample metadata/rights; A: render or generation job. | Transport controls never shift; job progress, audio fallback, and failed render are clear. |
| VDA-G013 | SVD-138 | ai-chat | Ask a grounded question and preserve the cited conversation artifact. | K: conversation CID; D: retrieval/policy/provenance; A: inference. | Streaming, citations, stop/retry, denied action, and narrow layout are usable. |
| VDA-G014 | SVD-139 | file-manager | Browse, preview, store, and recover content through mediated actions. | K: files/pins/retrieval; D: metadata/classification; A: preview/processing job. | Selection, progress, empty folder, offline retrieval, and destructive confirmation are visible. |
| VDA-G015 | SVD-140 | task-manager | Inspect desktop and backend task state without pretending local tasks are remote jobs. | K: receipt/event references; D: task search/history; A: job telemetry/control. | Status grouping, cancellation confirmation, stale state, and keyboard navigation remain clear. |
| VDA-G016 | SVD-141 | todo | Turn a goal into a policy-checked, synchronized task list. | K: taskboard CID; D: goal decomposition/policy; A: supervisor dispatch. | Add/edit/complete, dependency blocker, sync state, and dispatch confirmation are explicit. |
| VDA-G017 | SVD-142 | model-browser | Find a model, inspect evaluation evidence, and run a bounded test. | K: model artifacts; D: model/dataset evidence; A: inference and hardware fit. | Model comparison, capability warning, run progress, and unsupported hardware state are legible. |
| VDA-G018 | SVD-143 | huggingface | Discover a model or dataset and turn it into a governed local workflow. | K: cached artifacts; D: cards/dataset metadata; A: inference benchmark. | Search/filter, provenance, download state, and quota/error recovery are polished. |
| VDA-G019 | SVD-144 | openrouter | Route a prompt through a policy-approved external-provider workflow. | K: opaque request receipt; D: provider/model policy; A: route and execution telemetry. | Provider status, cost/confirmation, retry, and provider failure do not leak credentials. |
| VDA-G020 | SVD-145 | ipfs-explorer | Inspect and retrieve CID content with provenance and assistive analysis. | K: primary CID/pin/retrieval; D: metadata/provenance; A: retrieval diagnostics. | CID entry, preview, pin confirmation, unavailable peer, and content-type fallback are clear. |
| VDA-G021 | SVD-146 | device-manager | Inspect available devices and submit bounded hardware diagnostics. | K: peer/device receipts; D: device knowledge/config policy; A: hardware detection/benchmark. | Device cards, permission/unsupported state, live refresh, and diagnostics progress are accessible. |
| VDA-G022 | SVD-147 | settings | Change preferences through policy-governed configuration operations. | K: versioned settings CID; D: configuration policy; A: apply/restart job status. | Dirty state, validation, save rollback, and sensitive setting boundaries are obvious. |
| VDA-G023 | SVD-148 | mcp-control | Discover all servers/tools and execute only approved diagnostics. | K: descriptor/receipt CIDs; D: tool catalog/policy; A: adapter health. | Server status, tool schemas, transport choice, dry run, and unavailable endpoint recovery are usable. |
| VDA-G024 | SVD-149 | api-keys | Manage opaque credential references without revealing secret values. | K: encrypted reference/receipt; D: access policy; A: rotation/revocation job state. | No secret is rendered or logged; confirmation, policy denial, and recovery are explicit. |
| VDA-G025 | SVD-150 | github | Review repository context and create governed automation requests. | K: artifact snapshots; D: code search/review evidence; A: automation job. | PR/action confirmation, evidence links, auth failure, and rate-limit state are understandable. |
| VDA-G026 | SVD-151 | oauth-login | Complete an external authorization handoff with no token exposure. | K: opaque session receipt; D: grant policy; A: authorization lifecycle telemetry. | Redirect/popup failure, expired grant, and mobile fallback are visible and safe. |
| VDA-G027 | SVD-152 | cron | Create a scheduled, policy-checked workflow with receipts. | K: schedule/event CID; D: policy/calendar context; A: scheduled execution. | Next run, pause/resume, failure history, and destructive schedule confirmation are clear. |
| VDA-G028 | SVD-153 | navi | Translate a user intent into a previewable cross-service action. | K: retrieval route; D: semantic intent/policy; A: dispatch plan. | Intent preview, confirmation, ambiguity resolution, and fallback suggestions are concise. |
| VDA-G029 | SVD-154 | p2p-network | Inspect peers, DHT/bootstrap health, and safe network diagnostics. | K: libp2p peers/CIDs; D: trust/provenance; A: load/scheduling metrics. | Peer list, transport distinction, reconnect state, and privacy warning are readable. |
| VDA-G030 | SVD-155 | p2p-chat-unified | Exchange a message with context and safe synchronization. | K: pubsub/offline message refs; D: moderation/context; A: summary or transcription. | Composer, delivery/receipt, offline queue, moderation denial, and audio fallback work. |
| VDA-G031 | SVD-156 | neural-network-designer | Design a graph, validate its data contract, and submit a compile workflow. | K: graph artifact; D: dataset/schema validation; A: compile/train plan. | Canvas controls, invalid edge feedback, progress, and result artifact are stable. |
| VDA-G032 | SVD-157 | training-manager | Configure, launch, observe, and stop a governed training job. | K: checkpoints/artifacts; D: training-data provenance; A: queue/training telemetry. | Validation, capacity queue, logs, cancel confirmation, and resume state are clear. |
| VDA-G033 | SVD-158 | calculator | Persist/share a calculation and offer an optional verified explanation. | K: calculation CID; D: formula logic/provenance; A: bounded explain/solve job. | Keypad focus, large values, error input, history, and result copying work across viewports. |
| VDA-G034 | SVD-159 | clock | Persist timers and create policy-checked reminders. | K: timer/event receipt; D: reminder context/policy; A: scheduling forecast. | Timer accuracy, alarm permission, pause/restart, and compact display remain reliable. |
| VDA-G035 | SVD-160 | calendar | Create and search events with provenance-aware reminders. | K: calendar artifacts; D: semantic event context; A: reminder scheduling. | Date navigation, conflict state, invite failure, and mobile summary are polished. |
| VDA-G036 | SVD-161 | peertube | Retrieve and play content with captions and quality recovery. | K: video CIDs/retrieval; D: catalog/captions; A: transcode/quality diagnostics. | Playback, buffering, unavailable content, captions, and media fallback are observable. |
| VDA-G037 | SVD-162 | friends-list | Manage contacts and safe social identity context. | K: contact references; D: relationship graph/policy; A: optional suggestions. | Empty state, invitation confirmation, blocked contact, and presence freshness are clear. |
| VDA-G038 | SVD-163 | image-viewer | Open CID-backed imagery and run optional analysis/enhancement. | K: image retrieval; D: metadata/OCR; A: enhancement job. | Zoom/pan, loading, unsupported format, analysis progress, and alt text remain usable. |
| VDA-G039 | SVD-164 | notes | Create, search, cite, and synchronize provenance-rich notes. | K: note CIDs; D: semantic search/provenance; A: summary job. | Editing, conflict recovery, citation links, sync state, and keyboard shortcuts are coherent. |
| VDA-G040 | SVD-165 | media-player | Play CID-backed media with metadata and quality diagnostics. | K: media CIDs; D: captions/metadata; A: transcode/recommendation diagnostics. | Seek, volume, loading, missing codec, and background audio states are polished. |
| VDA-G041 | SVD-166 | system-monitor | Explain system health from current telemetry and retained evidence. | K: telemetry receipts; D: diagnostic history; A: live metrics analysis. | Charts, refresh, stale data, alert severity, and screen-reader summaries are clear. |
| VDA-G042 | SVD-167 | neural-photoshop | Generate or edit an image with provenance and job controls. | K: source/result CIDs; D: prompt/model metadata; A: image generation/editing. | Prompt state, preview, cancellation, policy denial, and output comparison are usable. |
| VDA-G043 | SVD-168 | cinema | Edit a project and submit a render with media provenance. | K: project/media CIDs; D: clip metadata/rights; A: render job. | Timeline, render queue, failed export, and playback fallback do not overlap or lose state. |
| VDA-G044 | SVD-169 | strudel | Save live-code sessions and use optional pattern assistance. | K: session/sample CIDs; D: pattern library/rights; A: assisted composition. | Editor/audio controls, compile error, audio permission, and session restore are reliable. |
| VDA-G045 | SVD-170 | strudel-ai-daw | Compose with AI assistance while retaining editable local control. | K: project/media CIDs; D: library context; A: composition/render job. | Latency, generation progress, undo, failed audio backend, and compact controls are polished. |
| VDA-G046 | SVD-171 | music-studio | Preserve classic studio projects while adding safe artifact workflows. | K: project assets; D: catalog/rights; A: optional render/analysis. | Legacy workflow stays intact; save, fallback, and responsive layout are verified. |
| VDA-G047 | SVD-172 | p2p-chat | Preserve the legacy chat path with explicit upgrade guidance. | K: pubsub/peer state; D: moderation/provenance; A: notification/summary. | Legacy alias, offline state, delivery failure, and migration route are visible. |
| VDA-G048 | SVD-173 | datasets-browser | Browse, inspect, and prepare datasets for downstream work. | K: dataset artifacts; D: primary search/vector/provenance; A: embedding/preparation jobs. | Schema preview, filter state, failed query, job progress, and result CIDs are clear. |
| VDA-G049 | SVD-174 | accelerate-panel | Configure and observe model and hardware execution. | K: model/run artifacts; D: evaluation/policy evidence; A: primary inference/job control. | Hardware fit, queue state, logs, cancellation, and no-capacity recovery are polished. |
| VDA-G050 | SVD-175 | idl-explorer | Inspect schemas and invoke governed descriptor fixtures. | K: descriptor CIDs; D: schema/policy explanation; A: compatibility execution. | Schema navigation, invalid input, transport badge, and receipt inspection are readable. |
| VDA-G051 | SVD-176 | glasses-preview | Replay ORB handoff packets through the supported device simulator. | K: replay bundle CIDs; D: permission/privacy policy; A: display/audio analysis. | Display/camera/mic/speaker states, denial, and fallback target are visible. |
| VDA-G052 | SVD-177 | orb-auto-ui | Render descriptor-driven applications with safe execution controls. | K: generated artifact CIDs; D: intent/schema policy; A: generated workflow execution. | Generated controls, schema errors, confirmation, and fallback renderer are coherent. |
| VDA-G053 | SVD-178 | mcp-plus-plus | Diagnose profiles, peers, event DAGs, policies, and tool transport. | K: peer/CID/event DAG; D: formal policy/provenance; A: scheduling and receipt analysis. | HTTP/libp2p distinction, DID identity, unavailable profile, and evidence drill-down work. |
| VDA-G054 | SVD-179 | agent-supervisor | Steer goals, subgoals, tasks, and dispatch with bounded authority. | K: task receipts/event DAG; D: goal/policy reasoning; A: queue, scheduler, and workers. | Goal graph, prompt preview, confirmation, progress, timeout/reassignment, and taskboard links are complete. |

## Required Evidence Per App

Each app task produces an `app-improvement/<app-id>.json` record containing:

1. manifest version, app id, launch selector, and primary action selector;
2. desktop and narrow-mobile screenshot paths, focus/keyboard result, console
   errors, and layout/accessibility assertions;
3. K/D/A health observations and the precise reason for any unavailable role;
4. at least one real safe read through the shared gateway when a role is
   declared available, plus a confirmation-gated or dry-run record for writes;
5. HTTP/libp2p transport, peer DID, descriptor CID, correlation id, policy
   result, receipt/event-DAG CID, and user-visible recovery state where
   applicable; and
6. a reviewer-readable description of the primary workflow and the failure
   path that was exercised.

## Supervisor Operating Model

The `ipfs_accelerate_py` supervisor owns prioritization, task selection,
objective evidence, and implementation events. It does not own the active
checkout merely by running. The all-tools writer launch must use the
SwissKnife checkout lease, set `IPFS_ACCELERATE_AGENT_MAX_DIRTY_ATTEMPTS=0`,
and use the existing SVD board/state identity. The first implementation task is
SVD-133, which creates the common app-open and evidence harness; individual
app tasks can then proceed independently with namespaced artifacts.

The supervisor is started in observation mode first to validate parsing and
dependencies. Implementation mode is started only through the exact leased
all-tools wrapper after the committed board is clean. The supervisor must not
reset, stash, force-clean, expose secrets, or claim a live backend action based
only on a manifest or static descriptor.

## Program Completion

The program is complete only when all 45 application tasks, the global UI/UX
gate, the cross-service HTTP/libp2p proof, and the freshness-aware release gate
are complete. A release report remains `NO_GO` for any app lacking a current
primary-workflow proof, any missing backend disposition, a hidden policy/error
state, or a broken layout/accessibility assertion.
