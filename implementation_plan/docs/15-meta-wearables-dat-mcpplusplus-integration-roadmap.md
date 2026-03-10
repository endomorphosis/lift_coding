# Meta Wearables DAT + MCP++ Integration Roadmap

## Status
Active implementation roadmap for integrating the Meta wearables reference repositories with the existing HandsFree backend, mobile app, and MCP++/IPFS execution stack.

Current implementation baseline in this repo:

- Meta DAT repositories are retained as reference submodules, not required runtime dependencies
- the shipping mobile integration path is a first-party wearables bridge rooted in `mobile/modules/expo-meta-wearables-dat`
- normalized MCP result envelopes are already flowing through backend tasks, notifications, router cards, and mobile card builders
- wearables connectivity receipts now expose a documented local action contract:
  - `mobile_open_wearables_diagnostics`
  - `mobile_reconnect_wearables_target`

## Scope
This roadmap covers integration across these repositories:

- `facebook/meta-wearables-dat-android`
- `facebook/meta-wearables-dat-ios`
- `endomorphosis/ipfs_kit_py`
- `endomorphosis/ipfs_accelerate_py`
- `endomorphosis/ipfs_datasets_py`
- `endomorphosis/Mcp-Plus-Plus`

It is intended to complement, not replace:

- `implementation_plan/docs/12-meta-glasses-ipfs-tool-integration.md`
- `implementation_plan/docs/14-mcp-plus-plus-ipfs-server-integration.md`
- `docs/meta-ai-glasses.md`
- `ARCHITECTURE.md`

## Repository snapshot (2026-03-09)
Planning assumptions in this document are based on the current checked-out upstream state:

- `external/meta-wearables-dat-android` at `437020ce09a578c80bb131df018aa7d19c991c3c`
- `external/meta-wearables-dat-ios` at `6fba4ee1aa58d87a94560662f5b42648320cc8ae`
- `external/ipfs_kit` at `06d6dae977673f6496df6417c27440fa8ab12eb3`
- `external/ipfs_accelerate` at `17a9b1a67932e39043fcd6f9f0e610541b43eb49`
- `external/ipfs_datasets` at `8cef1878ec958641d9aedabea691145f158178fc`
- `endomorphosis/Mcp-Plus-Plus` remote `HEAD` at `29343be704da4e193ff143bac7daae9b0f98435d`

If any upstream contract or packaging model changes after these revisions, update this roadmap before starting platform-specific implementation.

## Current codebase facts that shape the plan

### Mobile app
- React Native + Expo development client under `mobile/`
- existing local native module pattern already exists through `mobile/modules/expo-glasses-audio`
- `mobile/app.json` currently has no Expo config plugins registered
- current glasses integration is audio-first, with diagnostics and Bluetooth peer-bridge work already present

### Backend control plane
- FastAPI backend already owns command routing, task lifecycle, notifications, persistence, and voice-safe response shaping
- MCP server-family configuration already exists in `src/handsfree/mcp/config.py`
- canonical provider and capability catalog seams already exist in `src/handsfree/mcp/catalog.py`
- optional direct-import adapter seams already exist for `ipfs_kit_py` and `ipfs_accelerate_py`
- command router already understands MCP execution-mode preferences and capability-aware reruns

### Architectural consequence
This is not a greenfield integration. The correct strategy is to extend the existing seams and avoid introducing a second orchestration layer in mobile or in a standalone MCP gateway.

## Executive summary
The project already has the right high-level shape for this integration:

1. a voice-first mobile surface for Meta glasses
2. a FastAPI backend that already owns command routing, agent delegation, notifications, and task lifecycle
3. a growing MCP integration layer under `src/handsfree/mcp`
4. existing IPFS-oriented provider seams and direct adapters

The new opportunity is to turn those separate pieces into one coherent execution fabric:

- **HandsFree wearables bridge** becomes the supported device-access layer on iOS and Android, using Meta DAT repos as reference inputs and optional future acceleration points
- **HandsFree mobile** remains the end-user orchestration shell for voice, cards, notifications, and task review
- **HandsFree backend** remains the control plane and policy boundary
- **MCP++** becomes the protocol contract for remote tool execution, provenance, delegation, and policy-aware routing
- **`ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`** become specialized capability servers behind that control plane

The recommended rollout is **not** a big-bang rewrite. We should preserve the existing glasses audio path and current agent/task abstractions, then incrementally add:

- bridge-backed device access on mobile
- a stable HandsFree capability registry
- MCP++ runtime hardening
- provider parity across direct and remote execution
- voice-safe flows for task creation, progress, completion, and result follow-up

## Non-goals

- replacing the current audio routing module on the first DAT milestone
- exposing raw MCP++ protocol concepts directly in the mobile UI
- making every `ipfs_datasets_py` tool available to users on day one
- coupling mobile-native DAT SDK calls directly to IPFS or MCP++ servers without backend control-plane mediation

---

## Repository role map

### 1. `lift_coding` (this repo)
Current role:

- voice-first mobile + backend application
- command interpretation
- GitHub workflow assistant
- agent task lifecycle
- notifications and TTS/STT
- emerging MCP-backed provider surface

Key integration assets already present:

- `src/handsfree/agent_providers.py`
- `src/handsfree/agents/service.py`
- `src/handsfree/commands/router.py`
- `src/handsfree/mcp/*`
- `mobile/*`
- `docs/meta-ai-glasses.md`
- `implementation_plan/docs/14-mcp-plus-plus-ipfs-server-integration.md`

### 2. `facebook/meta-wearables-dat-ios`
Role in target architecture:

- supported iOS device-access SDK for Meta AI glasses
- native capability surface for device connection and media features
- official path for capabilities such as camera/photo/video and device-aware interactions

Important facts from upstream:

- distributed through Swift Package Manager
- developer preview SDK
- includes analytics behavior that can be opted out via `Info.plist`
- intended to help mobile apps reliably connect to Meta AI glasses

### 3. `facebook/meta-wearables-dat-android`
Role in target architecture:

- supported Android device-access SDK for Meta AI glasses
- package-based integration through GitHub Packages / Maven
- includes official artifacts such as `mwdat-core`, `mwdat-camera`, and mock device support

Important facts from upstream:

- requires package registry access and a `GITHUB_TOKEN` or local package credential
- analytics opt-out is manifest driven
- explicitly supports wearable device access and camera workflows

Planning consequence in this repo:

- Android DAT package access is not assumed
- the production baseline must continue to compile and function without GitHub Packages resolution
- official DAT artifacts remain an optional future enhancement rather than a hard dependency

### 4. `endomorphosis/ipfs_kit_py`
Role in target architecture:

- IPFS storage, pinning, retrieval, clustering, VFS, and packaging substrate
- best choice for persistent content management and CID lifecycle operations
- can act as both direct-import utility and MCP server family

Important upstream features relevant here:

- pin/add/get operations
- clustering and replication
- VFS and metadata indexing
- AI/ML storage support
- MCP server support
- health, metrics, and operational dashboards

### 5. `endomorphosis/ipfs_datasets_py`
Role in target architecture:

- high-level data, retrieval, knowledge graph, vector, legal reasoning, and web/archive tool family
- broadest MCP tool catalog
- ideal for research, discovery, ingestion, enrichment, and multi-step data workflows

Important upstream features relevant here:

- 200+ MCP tools across many categories
- vector search and IPLD vector store
- web archive / Common Crawl / media processing
- knowledge graph extraction and reasoning
- theorem-prover-backed workflows
- dashboard and analytics support

### 6. `endomorphosis/ipfs_accelerate_py`
Role in target architecture:

- accelerated inference and heavy compute backend
- canonical MCP++ runtime reference in the current stack
- likely source of truth for MCP++ cutover patterns and P2P task handling

Important upstream features relevant here:

- canonical `mcp_server` runtime
- MCP++ profile support
- hardware-aware inference and batching
- content-addressed model loading and caching
- remote libp2p task pickup integration path
- observability and control-plane features

### 7. `endomorphosis/Mcp-Plus-Plus`
Role in target architecture:

- protocol-level contract and documentation source
- defines optional profiles for more rigorous execution semantics beyond baseline MCP

Important upstream concepts relevant here:

- MCP-IDL / content-addressed interface contracts
- immutable execution envelopes and receipts
- UCAN capability delegation chains
- temporal deontic policy evaluation
- event DAG provenance and ordering
- optional P2P transport bindings

---

## Target end-state

A user wearing Meta AI glasses should be able to say commands like:

- “Find recent legal datasets about labor law.”
- “Pin the result to IPFS.”
- “Run the accelerated summarization workflow on the latest dataset.”
- “Capture a photo and attach it to this investigation.”
- “Open the latest task result.”

And the system should:

1. capture the voice or device event through bridge-backed mobile integrations
2. send a normalized command to HandsFree backend
3. resolve a canonical HandsFree capability
4. route execution via direct mode or MCP++ remote mode
5. store result metadata, task traces, and optional CID artifacts
6. speak back concise progress and completion summaries
7. expose deep result navigation in the mobile UI

---

## Architectural principles

### 1. Keep HandsFree as the control plane
Do not move command interpretation, policy checks, or user-facing task state into mobile SDK wrappers or raw MCP servers.

HandsFree backend should continue to own:

- intent resolution
- confirmation policy
- user/task correlation
- notification fanout
- trace normalization
- persistence and auditing

### 2. Treat DAT as an edge capability layer, not the application brain
The DAT SDKs should provide device primitives and official device access, while the app keeps all business logic in the existing React Native + backend stack.

### 3. Treat MCP++ as transport + contract, not user experience
Users should never hear protocol jargon. MCP++ should strengthen execution guarantees, traceability, and policy routing without leaking implementation complexity into spoken UX.

### 4. Preserve dual execution modes
For at least the next several milestones, every important capability should support one of these routes:

- `direct_import`
- `direct_cli`
- `mcp_remote`

This is essential for:

- local development
- rapid iteration
- schema discovery
- parity testing
- staged production cutover

### 5. Capability IDs must be stable even if server tools evolve
The planner, command system, mobile UI cards, and notifications should target canonical HandsFree capability IDs rather than upstream tool names.

---

## Proposed target architecture

```text
[Meta AI Glasses]
        │
        │ DAT / Bluetooth / media events
        ▼
[iOS app / Android app]
        │
        │ HTTPS / WebSocket
        ▼
[HandsFree Backend Control Plane]
  ├─ Command + Intent Router
  ├─ Task / Notification Service
  ├─ Capability Registry
  ├─ MCP Runtime Adapter
  └─ Policy / Audit / Trace Layer
        │
        ├──────────────┬──────────────┬──────────────┐
        ▼              ▼              ▼              ▼
 [ipfs_datasets]   [ipfs_kit]   [ipfs_accelerate]  [GitHub / other providers]
   MCP++ server      MCP server     MCP++ server
        │              │              │
        └─────── content / models / CIDs / receipts ───────┘
                           │
                           ▼
                    [IPFS / storage layer]
```

## Cross-repository implementation matrix

| Repository | Primary role in end-state | First integration milestone | Main owners in this repo |
| --- | --- | --- | --- |
| `lift_coding` | control plane, mobile UX, routing, persistence | capability registry + DAT wrapper shells | `src/handsfree/*`, `mobile/*` |
| `meta-wearables-dat-ios` | official iOS wearable access | native Expo module bridge, session state, media capture | `mobile/modules/expo-meta-wearables-dat/ios/*` |
| `meta-wearables-dat-android` | official Android wearable access | Android Expo module bridge, package auth, mock-device harness | `mobile/modules/expo-meta-wearables-dat/android/*` |
| `ipfs_kit_py` | storage, pinning, packaging, CID lifecycle | normalized add/pin/read/resolve capabilities | `src/handsfree/ipfs_kit_adapters.py`, `src/handsfree/mcp/*` |
| `ipfs_datasets_py` | discovery, search, ingestion, enrichment | dataset search/load/vector capabilities | `src/handsfree/mcp/*`, command/planner bindings |
| `ipfs_accelerate_py` | accelerated compute + strongest current MCP path | first full remote MCP++ production path | `src/handsfree/ipfs_accelerate_adapters.py`, provider/task runtime |
| `Mcp-Plus-Plus` | protocol and profile contract | negotiation, receipts, provenance model | `src/handsfree/mcp/*`, trace persistence |

## Environment and secret prerequisites

### Meta DAT prerequisites
- Wearables Developer Center application and release-channel setup for both mobile platforms
- iOS target configuration for `MWDAT` analytics opt-out and release metadata
- Android `GITHUB_TOKEN` or `github_token` local property for GitHub Packages resolution
- Android app manifest metadata for `APPLICATION_ID` and analytics opt-out

### MCP/IPFS prerequisites
- one reachable MCP endpoint per server family for staging and production
- auth secret distribution for each MCP server family
- explicit execution-mode policy per environment: local hybrid vs staging shadow vs production remote-only
- CID persistence policy for user-generated content and task outputs

### CI/CD prerequisites
- separate mobile jobs for DAT-disabled and DAT-enabled builds
- secret-scoped Android package resolution in CI
- integration environments for long-running MCP task polling
- a contract-test fixture set so capability behavior can be validated without live wearable hardware

---

## Workstream A: mobile integration with first-party wearables bridge

## Goal
Adopt the official DAT SDKs where they add reliability or new capabilities, without breaking the existing Expo/React Native experience.

## Strategy
Use a **layered mobile migration**:

### A1. Keep current audio routing path as baseline
Do not replace the existing audio capture/playback path on day one.

Current path remains useful for:

- STT/TTS loops
- diagnostics
- fallback when DAT integration is unavailable
- regression comparison

### A2. Introduce a new native abstraction for wearable device access
Add a new mobile native bridge, for example:

- `mobile/modules/expo-meta-wearables-dat/ios/*`
- `mobile/modules/expo-meta-wearables-dat/android/*`

Responsibilities:

- device connection state
- supported feature discovery
- camera/photo/video capability access
- official session lifecycle hooks
- metadata surfaced to JS
- selected target persistence
- reconnect and connect flows
- rich state-change events for MCP-trigger handoff

Recommended implementation detail:

- model it after the existing local Expo module pattern, not as ad hoc native code inside generated app folders
- add an Expo config plugin so iOS `Info.plist` and Android `AndroidManifest.xml` entries can be injected from app config
- keep all DAT-specific identifiers in environment-driven or app-config driven settings rather than hardcoded constants

### A3. Expose bridge capabilities to React Native via a narrow JS contract
Recommended JS-facing contract:

- `isDatAvailable()`
- `getConnectedDevice()`
- `getCapabilities()`
- `startDeviceSession()`
- `stopDeviceSession()`
- `getAdapterState()`
- `scanKnownAndNearbyDevices()`
- `getSelectedDeviceTarget()`
- `reconnectSelectedDeviceTarget()`
- `connectSelectedDeviceTarget()`
- `capturePhoto()`
- `startVideoStream()` / `stopVideoStream()`
- `subscribeDeviceEvents()`

This contract should be intentionally smaller than the native SDK surface.

Recommended JS module layout:

- `mobile/modules/expo-meta-wearables-dat/package.json`
- `mobile/modules/expo-meta-wearables-dat/app.plugin.js`
- `mobile/src/native/metaWearablesDat.js`
- `mobile/src/hooks/useMetaWearablesDat.js`
- `mobile/src/hooks/useWearablesCapabilityMatrix.js`

### A4. Use capability detection, not hard assumptions
Per platform, the app should dynamically decide whether to use:

- DAT-backed camera/media features
- existing audio route features
- fallback phone-only flows

### A5. Add a mobile “wearables capability matrix” screen
Extend diagnostics UI to show:

- connected device model
- bridge session status
- available features: audio, camera, media, controls
- analytics opt-out state
- current backend routing mode
- last task / last result / last CID
- selected target, RSSI, and last-seen state
- local receipt actions for diagnostics and reconnect

## Expected DAT-driven feature additions

### iOS
- supported Meta AI glasses session integration
- official device metadata and session state
- easier photo/video integration than raw Bluetooth-only handling

### Android
- official core + camera + mock-device paths
- better parity with supported Meta wearable device access
- stronger testability using mock-device support

## Mobile deliverables

1. DAT native wrapper module for iOS
2. DAT native wrapper module for Android
3. shared JS contract + hooks
4. diagnostics and feature capability UI
5. camera/media capture workflows wired into backend uploads
6. analytics opt-out configuration documented and applied

## Mobile phase gates

### Gate A1: diagnostics-only integration
- prove the bridge module loads on device builds
- expose availability, session state, target state, and capability discovery in diagnostics
- no command-surface dependency yet

Current status:

- completed in a bridge-first form for DAT-disabled Android builds
- diagnostics, selection, reconnect, connect, and event payloads are implemented
- wearables receipt actions are now consistent across backend cards, notifications, mobile builders, and OpenAPI examples

### Gate A2: media artifact capture
- capture photo or stream metadata through DAT
- upload artifacts to backend
- attach artifacts to tasks or result records

### Gate A3: command-surface usage
- allow a limited command set such as photo capture and attach
- keep audio capture/TTS on the current path until DAT adds measurable reliability or feature advantage

---

## Workstream B: HandsFree capability registry and execution routing

## Goal
Create one stable capability model shared across commands, agent delegation, UI cards, planners, and MCP providers.

## Recommended additions

### B1. Expand local capability registry
Build on the existing MCP-related seams with a canonical registry containing:

- `capability_id`
- provider family
- direct-import fallback support
- direct-cli fallback support
- remote MCP tool mapping
- input schema
- output normalization schema
- confirmation requirement
- voice formatter
- persistence strategy
- CID/result deep-link strategy

### B2. Separate execution intent from execution mode
The backend should choose mode at runtime:

- local development → `direct_import` or `direct_cli`
- staging → optional shadow `mcp_remote`
- production → `mcp_remote`

### B3. Normalize outputs into HandsFree result envelopes
Every execution route should produce a normalized object containing:

- `capability_id`
- `provider`
- `status`
- `spoken_text`
- `summary`
- `structured_output`
- `trace`
- `ipfs_cid` if relevant
- `follow_up_actions`

Additional normalized fields needed for MCP++:

- `receipt_ref`
- `event_dag_ref`
- `delegation_ref`
- `provider_profiles`
- `needs_input_schema`

### B4. Make cards and task results capability-driven
Mobile cards and notifications should be derived from normalized capability results rather than provider-specific one-offs.

---

## Workstream C: MCP++ runtime hardening in HandsFree

## Current state
There is already an MCP scaffold in `src/handsfree/mcp`.

That is the correct home for continued work.

## Goal
Evolve the current MCP client/config layer into a production-ready MCP++ runtime that can speak to `ipfs_accelerate_py`, `ipfs_datasets_py`, and `ipfs_kit_py` consistently.

## Required enhancements

### C1. Capability discovery and schema caching
The runtime should support:

- tool discovery at startup or lazily on first use
- schema caching with TTL
- provider health status and version metadata
- profile negotiation metadata where available

### C2. Profile-aware MCP++ negotiation
Align client behavior with upstream MCP++ concepts:

- content-addressed interface contracts
- execution receipts
- optional UCAN / policy hooks
- optional event/provenance DAG support
- optional P2P transport hints

HandsFree should not require every profile at first, but it should record which profiles a server advertises and use that to enable progressive behavior.

Minimum viable negotiation contract:

1. baseline MCP transport and tool discovery
2. optional profile advertisement capture
3. per-run storage of negotiated profile set
4. graceful downgrade when advanced profiles are absent

### C3. Long-running run lifecycle support
For any remote server that supports asynchronous runs, HandsFree should track:

- submit
- running
- needs input
- completed
- failed
- cancelled

And persist:

- upstream run id
- request id
- provider family
- retry count
- last server status
- poll cursor / checkpoint if applicable

### C4. Result receipts and provenance capture
When upstream servers expose richer provenance, HandsFree should persist references to:

- execution envelope CID
- receipt CID
- event DAG head CID
- policy evaluation summaries
- delegation chain references

Persistence rule:
store references and normalized summaries by default, and only store full raw envelopes when needed for replay, debugging, or explicit audit retention policy.

### C5. Runtime policy shims
Use HandsFree policy gates before submission, and preserve room for server-side policy evaluation after submission.

That means two layers:

1. preflight allow / deny / confirm in HandsFree
2. downstream policy-aware execution inside MCP++ server family

---

## Workstream D: provider-family integration plans

## Provider sequencing rationale

1. `ipfs_accelerate_py` first because it already presents a concrete MCP server runtime and long-running workflow shape.
2. `ipfs_kit_py` second because storage and CID lifecycle are core follow-up actions for many other features.
3. `ipfs_datasets_py` third because its breadth is high; it should be integrated behind the registry only after the runtime and result-envelope model are stable.

## D1. `ipfs_kit_py` integration plan
Primary responsibilities:

- add/get/cat/read content
- pin/unpin lifecycle
- packaging and manifest generation
- storage durability and replication metadata

HandsFree use cases:

- “pin this CID”
- “save this result to IPFS”
- “read the stored output”
- “package the fetched artifacts”
- “show replication health”

Recommended first-class capabilities:

- `ipfs.content.add_bytes`
- `ipfs.content.read_ai_output`
- `ipfs.kit.pin`
- `ipfs.kit.unpin`
- `ipfs.kit.resolve`
- `ipfs.kit.package_dataset`

## D2. `ipfs_datasets_py` integration plan
Primary responsibilities:

- dataset discovery
- vector search
- web archive and ingestion
- knowledge graph enrichment
- reasoning / legal workflows

HandsFree use cases:

- “find legal datasets”
- “search Common Crawl for AI policy documents”
- “build a knowledge graph from these results”
- “rerun that dataset search with a narrower query”

Recommended first-class capabilities:

- `ipfs.datasets.search`
- `ipfs.datasets.load`
- `ipfs.vector.search`
- `ipfs.web.archive`
- `ipfs.knowledge.extract`
- `ipfs.reasoning.verify`

## D3. `ipfs_accelerate_py` integration plan
Primary responsibilities:

- accelerated text generation and embedding
- hardware execution selection across compute backends
- large-scale batching and compute-intensive workflows
- canonical MCP++ runtime reference behavior

HandsFree use cases:

- “accelerate failure analysis”
- “embed these texts”
- “generate and store the summary”
- “run the ingestion pipeline on the fastest available backend”

Recommended first-class capabilities:

- `ipfs.accelerate.generate`
- `ipfs.accelerate.embed`
- `ipfs.accelerate.generate_and_store`
- `github.check.accelerated_failure_explain`

---

## Workstream E: user experience and voice flows

## Goal
Make all of this usable from glasses-first interaction patterns.

## UX rules

### E1. Spoken output must stay concise
Good:

- “Dataset search started.”
- “I found three strong matches.”
- “Pin completed.”
- “I need the CID.”

Bad:

- protocol errors read aloud verbatim
- raw tool JSON in TTS
- run ids or request ids spoken to the user

### E2. Long-running work must become tracked tasks
If the action is not clearly sub-second, route it through task semantics and notify progress asynchronously.

### E3. “Needs input” should ask for one missing field
Examples:

- “Which CID should I pin?”
- “What search query should I use?”
- “Do you want me to store the result in IPFS?”

### E4. Every completed task should have follow-up actions
Examples:

- open result
- share CID
- pin result
- rerun with new query
- summarize result

Current wearables-specific baseline:

- connectivity receipts render as a distinct receipt type
- normalized `follow_up_actions` flow through result envelopes
- backend and mobile both prepend local wearables actions for diagnostics and reconnect
- OpenAPI now documents those local `mobile_*` action IDs

### E5. DAT-only media actions should degrade gracefully
If a device supports photo/video via DAT but not on the current platform/build, the app should explain the limitation and offer fallback capture paths.

---

## Workstream F: API and data model changes

## Backend API additions
Potential additions or refinements:

- richer task detail payloads for capability-native results
- device capability status endpoint for mobile diagnostics
- result receipt / provenance endpoint for CID-backed outputs
- media upload + artifact attach endpoints for DAT-driven photo/video capture

## Database additions
Likely persistence expansions:

- wearable device sessions
- device capability snapshots
- media artifact registry
- MCP execution receipts / envelope references
- event DAG / provenance references
- capability registry versioning metadata

## Suggested trace fields

- `capability_id`
- `execution_mode`
- `server_family`
- `tool_name`
- `mcp_profiles`
- `request_id`
- `run_id`
- `receipt_cid`
- `event_dag_cid`
- `result_cid`
- `device_context`
- `media_artifact_ids`

## Suggested new persistence tables or expansions

- `wearable_device_sessions`
- `wearable_capability_snapshots`
- `media_artifacts`
- `mcp_execution_receipts`
- `mcp_event_dag_refs`
- `mcp_profile_negotiations`

---

## Workstream G: security, privacy, and policy

## DAT-specific requirements

- explicitly document analytics opt-out on both iOS and Android
- separate developer-preview-only features from production-ready features
- avoid storing unnecessary device telemetry in backend traces

## MCP++ / IPFS requirements

- schema validation before remote invocation
- secret redaction in traces and logs
- preflight confirmation for destructive or externally visible actions
- optional delegated capability chain recording when available
- ability to force `mcp_remote` and disable direct fallbacks in production

## Content and provenance requirements

- any persisted artifact should include origin metadata
- content intended for sharing should surface CID and provenance clearly in UI
- policy-sensitive workflows should preserve enough receipt metadata for audit/replay

---

## Workstream H: observability and operator tooling

## Required metrics

- command → capability resolution success rate
- per-capability latency by execution mode
- per-provider success/failure rates
- DAT session reliability by platform/device type
- task completion funnel
- `needs_input` rate
- fallback usage rate (`direct_import` or `direct_cli` when remote unavailable)
- CID persistence success rate

## Required logs

- capability routing decisions
- MCP profile negotiation results
- remote run transitions
- device session attach/detach events
- media upload events
- provenance/reference capture events

## Operator dashboards
Recommended dashboard groups:

1. mobile/device health
2. MCP runtime health
3. IPFS content lifecycle
4. task/result funnel
5. security and policy exceptions

## Testing and validation strategy

### Unit and contract tests
- capability-registry resolution and provider alias tests
- execution-mode selection tests
- MCP result-envelope normalization tests
- DAT JS hook tests with native module mocks
- provenance and receipt serialization tests

### Integration tests
- backend-to-MCP task lifecycle tests against fixture MCP servers
- direct-import vs remote parity tests for the initial six capability IDs
- backend artifact upload plus CID persistence tests
- mobile diagnostics tests for DAT availability and capability rendering

### Hardware and platform tests
- iOS physical-device DAT validation with supported Meta glasses
- Android physical-device DAT validation with supported Meta glasses
- Android mock-device validation using DAT mock-device support
- regression runs for the existing Bluetooth audio path after each DAT milestone

### Rollout tests
- shadow-mode execution where remote MCP runs in parallel with the existing direct path for selected capabilities
- canary rollout on one provider family before enabling remote-only production policy

---

## Delivery plan

## Phase 0 — repository setup and discovery
Completed / immediate:

- add DAT iOS and Android repos as submodules under `external/`
- inventory current MCP scaffold and mobile native module seams
- capture upstream package install constraints and auth requirements
- capture exact upstream revision snapshots used for planning

## Phase 1 — capability and routing foundation
Deliverables:

- canonical HandsFree capability registry
- execution-mode selector
- output normalization contract
- parity test matrix for direct vs MCP routes
- provider-profile negotiation storage

Acceptance criteria:

- at least 6 core IPFS capabilities run through one normalized runtime
- cards and task results derive from capability metadata

## Phase 2 — DAT mobile wrapper baseline
Deliverables:

- iOS DAT wrapper module
- Android DAT wrapper module
- JS API + diagnostics UI
- analytics opt-out support documented and implemented
- Expo config plugin wiring for both platforms

Acceptance criteria:

- app can report DAT availability and connected-device capability surface on both platforms
- no regression in current audio flows

## Phase 3 — first production MCP++ path
Deliverables:

- hardened remote execution path for one server family first
- recommended first target: `ipfs_accelerate_py` because it already emphasizes canonical MCP++ runtime behavior
- receipt / run-id persistence
- task polling + cancellation parity
- negotiated profile capture and downgrade behavior

Acceptance criteria:

- one remote capability family works end-to-end from command to completion notification
- execution metadata is persisted without leaking secrets

## Phase 4 — storage and dataset family expansion
Deliverables:

- `ipfs_kit_py` storage capabilities
- `ipfs_datasets_py` search/discovery capabilities
- CID-backed result cards and follow-up actions
- artifact attachment model for DAT-captured media

Acceptance criteria:

- one dataset discovery workflow and one pin/save workflow work in both direct and remote modes

## Phase 5 — voice-first productization
Deliverables:

- concise spoken progress/cancel/complete copy
- follow-up actions in notifications and result cards
- media capture flow for DAT-supported photo/video use cases

Acceptance criteria:

- glasses user can create, monitor, and inspect an MCP-backed task without touching raw protocol/debug views

## Phase 6 — policy/provenance hardening
Deliverables:

- receipt capture
- provenance references
- policy-aware audit expansion
- staged production cutover switches

Acceptance criteria:

- production profile can run remote-only with operator-visible provenance and rollback controls

---

## Recommended PR sequence

### PR 1
Submodules + documentation + mobile DAT feasibility notes

### PR 2
HandsFree capability registry and execution-mode abstraction

### PR 3
DAT iOS wrapper + diagnostics integration

### PR 4
DAT Android wrapper + diagnostics integration

### PR 5
MCP runtime hardening for remote runs, receipts, and discovery

### PR 6
`ipfs_accelerate_py` production-path integration

### PR 7
`ipfs_kit_py` content and pinning integration

### PR 8
`ipfs_datasets_py` dataset and retrieval integration

### PR 9
voice/card/task UX polish for follow-up actions and result navigation

### PR 10
policy/provenance/observability hardening and remote-only rollout controls

## Detailed engineering backlog by layer

### Mobile native layer
- create `expo-meta-wearables-dat` local module scaffold
- add iOS Swift bridge for DAT availability, session lifecycle, and media APIs
- add Android Kotlin bridge for DAT availability, session lifecycle, and media APIs
- add config plugin for Info.plist and AndroidManifest metadata injection
- add build flags so app still compiles when DAT credentials or package access are absent

### Mobile JS layer
- add a native wrapper and hook-based state model
- extend diagnostics screen with a DAT capability matrix
- add media capture actions and upload flows
- add cards and task detail views for media artifacts and CID-backed outputs

### Backend MCP/runtime layer
- harden tool discovery, schema caching, and health checks
- persist negotiated profile metadata and receipt references
- add task submit/status/cancel wrappers with normalized errors
- add remote-only enforcement switch and shadow-mode instrumentation

### Backend product layer
- map canonical capability IDs to spoken summaries and card builders
- attach DAT media artifacts to tasks, notifications, and result views
- expose diagnostics endpoints for wearable capability state and backend routing state
- add policy checks for external publishing, pinning, and long-running workflows

### Ops layer
- document developer setup for DAT iOS, DAT Android, MCP endpoints, and IPFS servers
- add dashboards for routing decisions, remote task health, and wearable session reliability
- add CI jobs for fixture MCP integration and DAT-disabled mobile safety builds

---

## Concrete code touchpoints

## Mobile
Likely files and areas:

- `mobile/modules/*`
- `mobile/src/screens/GlassesDiagnosticsScreen.js`
- `mobile/src/screens/CommandScreen.js`
- `mobile/src/api/client.js`
- `mobile/src/hooks/*`
- `mobile/App.js`

## Backend
Likely files and areas:

- `src/handsfree/mcp/client.py`
- `src/handsfree/mcp/config.py`
- `src/handsfree/mcp/catalog.py`
- `src/handsfree/mcp/capabilities.py`
- `src/handsfree/agent_providers.py`
- `src/handsfree/agents/service.py`
- `src/handsfree/commands/router.py`
- `src/handsfree/models.py`
- `src/handsfree/api.py`
- `src/handsfree/db/*`

## Testing
Likely additions:

- direct vs remote parity tests
- DAT availability and mock-device tests
- task lifecycle contract tests
- provenance/result receipt tests
- voice/card action contract tests

---

## Risks and open questions

### 1. DAT scope vs current audio module overlap
Open question:
Should DAT replace only camera/media/device access, or also own audio/session flows where possible?

Recommendation:
Start with device access and media features first. Keep current audio route logic as the primary STT/TTS path until DAT-based audio advantages are proven.

### 2. Android package access and CI
Open question:
How will CI securely resolve GitHub Packages for `meta-wearables-dat-android`?

Recommendation:
Treat package credentials as environment-backed secrets in CI and local dev setup docs. Add a build-time capability flag so Android builds can still proceed without DAT-enabled package resolution when needed.

### 3. Which upstream MCP server family is the best first production target?
Recommendation:
Start with `ipfs_accelerate_py` for MCP++ protocol maturity, then add `ipfs_kit_py`, then `ipfs_datasets_py`.

### 4. How much MCP++ profile support is needed on day one?
Recommendation:
Require baseline MCP execution plus negotiated profile visibility. Make UCAN, event DAG, and P2P profile usage additive rather than blocking the first remote rollout.

### 5. How much result data should be persisted to IPFS by default?
Recommendation:
Default to opt-in or policy-driven persistence at first, especially for user-generated or potentially sensitive results.

---

## Success criteria

This roadmap is successful when all of the following are true:

1. the mobile app can detect and expose DAT-backed capabilities on both iOS and Android
2. HandsFree can route the same capability through direct and MCP++ remote modes with normalized outputs
3. `ipfs_accelerate_py`, `ipfs_kit_py`, and `ipfs_datasets_py` are all reachable through the same capability registry and provider model
4. users get concise, voice-safe progress and completion summaries
5. operators get audit, trace, and provenance visibility without exposing secrets
6. production can enforce remote-only execution with rollback controls

---

## Immediate next actions

1. land this roadmap and treat it as the umbrella document
2. keep `14-mcp-plus-plus-ipfs-server-integration.md` as the protocol/runtime deep dive
3. start Phase 1 with a concrete capability registry and execution parity matrix
4. start Phase 2 with DAT diagnostics wrappers before attempting full media workflows
5. choose `ipfs_accelerate_py` as the first full MCP++ production-path integration target
6. split the first implementation PRs so mobile DAT diagnostics and backend MCP runtime changes can land independently
