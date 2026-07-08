# SwissKnife Virtual Desktop IPFS MCP++ ORB Meta Glasses Plan

Status: comprehensive integration plan
Created: 2026-07-07
Updated: 2026-07-08 with exhaustive all MCP/MCP++ tool coverage expansion
Scope: SwissKnife virtual desktop apps, IPFS MCP/MCP++ tools, ORB/IDL handoff, and Meta glasses display/audio/input layers

## Objective

Make every SwissKnife virtual desktop application work through a consistent
service, capability, descriptor, and handoff model:

1. Each desktop app launches reliably and exposes a real operational surface.
2. Each app declares the IPFS and MCP/MCP++ capabilities it needs.
3. Calls into `ipfs_datasets_py`, `ipfs_accelerate_py`, and `ipfs_kit_py` go
   through normalized descriptors, capability IDs, result envelopes, receipts,
   and fallback behavior.
4. The same ORB/IDL contracts that power desktop apps can compile or condense
   into Meta glasses surfaces.
5. Meta glasses handoff works through the phone/backend control plane with
   policy checks, receipts, fallback render targets, and repeatable evidence.

This plan assumes `Mcp-Plus-Plus` remains the case-sensitive protocol/spec
source while runtime MCP++ behavior is distributed across SwissKnife, the IPFS
server repositories, and the HandsFree/Hallucinate App control plane.

## Current Baseline

The repository already has the major pieces, but they are not yet locked
together as one executable contract.

Relevant existing assets:

- `swissknife/web/index.html` and `swissknife/web/js/apps/*` provide the current
  virtual desktop shell and app implementations.
- `swissknife/scripts/list-all-applications.cjs`,
  `swissknife/scripts/comprehensive-app-testing.cjs`, and
  `swissknife/scripts/validate-apps.cjs` enumerate app sets, but they disagree
  with one another and with newer runtime registries.
- `swissknife/src/services/module-ownership.json` defines the intended module
  boundaries for `mcp`, `glasses`, `ipfs`, `logic`, `provers`, `zkp`, and
  integrations.
- `swissknife/src/services/mcp/mcp-ipfs-kit-descriptor-pack.ts`,
  `mcp-ipfs-datasets-descriptor-pack.ts`, and
  `mcp-ipfs-accelerate-descriptor-pack.ts` already define descriptor-pack
  surfaces for the three IPFS server families.
- `swissknife/web/src/orb-dynamic-app-renderer.ts` can generate desktop app UI
  from IDL descriptors.
- `swissknife/src/services/glasses/idl-to-glasses-compiler.ts` can compile IDL
  descriptors into Meta glasses display profiles for IPFS Explorer, Datasets
  Browser, and Accelerate Panel.
- `swissknife/src/services/glasses/glasses-app-control-plane.ts` defines
  manually authored glasses displays for several desktop apps, plus dynamic
  registration for IDL-generated apps.
- `swissknife/src/services/glasses/deployment-readiness-validator.ts` already
  checks app registry, display constraints, IDL compilation, voice aliases,
  gesture routing, state sync, notification, and mobile bridge readiness.
- `implementation_plan/docs/14-mcp-plus-plus-ipfs-server-integration.md`,
  `15-meta-wearables-dat-mcpplusplus-integration-roadmap.md`,
  `18-swissknife-meta-glasses-display-widgets.md`,
  `21-swissknife-mobile-orb-bridge.md`,
  `22-multimodal-control-surface-logic-idl.md`,
  `27-ipfs-kit-vfs-readiness-improvement-plan-2026-06-28.md`, and
  `33-ipfs-accelerate-serving-integration-contract-2026-06-30.md` define the
  adjacent plans and contracts this plan depends on.

Primary gap:

There is no single source of truth that says, for every SwissKnife desktop app:

- what app ID is canonical,
- what component opens it,
- what backend or MCP capability it needs,
- whether the app is direct code, descriptor-generated UI, or a hybrid,
- what ORB/IDL interface it exposes,
- what Meta glasses display profile or fallback it has,
- what tests and screenshots prove it is working.

## Target Architecture

```text
SwissKnife desktop app manifest
        |
        v
App launch adapter + app capability contract
        |
        v
ORB/IDL interface descriptor
        |
        v
Capability registry and policy broker
        |
        v
MCP or MCP++ execution gateway
        |
        +--> ipfs_kit_py: storage, pins, DAG, VFS, IPNS, retrieval
        +--> ipfs_datasets_py: datasets, search, vectors, KG, provenance, logic
        +--> ipfs_accelerate_py: models, inference, hardware, jobs, telemetry
        |
        v
Normalized result envelope + event DAG + receipt references
        |
        v
Desktop window / generated Auto-UI / Hallucinate App panel
        |
        v
Mobile ORB edge descriptor
        |
        v
Meta glasses display, audio, camera, input, or fallback target
```

## Design Rules

- The app manifest is the source of truth. HTML icons, Start menu entries,
  Playwright tests, glasses registry entries, and documentation must derive from
  or validate against it.
- Desktop apps must not hard-code service URLs or raw fetch routes once a
  capability exists. They call a local app gateway, which resolves capability ID,
  transport, policy, and endpoint.
- MCP and MCP++ are execution details below the app capability contract. Apps
  should see canonical operations and normalized results.
- Every side-effectful action needs a policy classification, confirmation rule,
  correlation ID, and receipt.
- Every app has a Meta glasses story: native display profile, display-webapp
  profile, audio/mobile fallback, or explicit "not displayable" rationale with a
  safe fallback.
- Meta DAT native display remains optional and runtime-gated. Unsupported native
  display is a normal fallback state.
- Health verification for the live IPFS MCP services should prefer `/mcp`
  endpoint checks over `/health` where the service family currently behaves
  that way.

## Canonical App Inventory To Freeze

The first work item is not implementation. It is freezing the app inventory.
The current evidence points to an app count drift between 34 and 38 apps, plus
additional descriptor-generated apps. The target manifest should include these
IDs and allow aliases for legacy names.

| App ID | User Surface | Primary Service Families | Glasses Strategy |
| --- | --- | --- | --- |
| `terminal` | Command shell | `ipfs_kit`, `ipfs_datasets`, `ipfs_accelerate` | manual compact command card |
| `vibecode` | Code editor | `ipfs_kit`, `ipfs_accelerate`, `ipfs_datasets` | manual code/status card |
| `music-studio-unified` | Music studio | `ipfs_kit`, `ipfs_accelerate` | media/status fallback first |
| `ai-chat` | Assistant chat | `ipfs_datasets`, `ipfs_accelerate`, `ipfs_kit` | manual conversation card plus audio |
| `file-manager` | Files and content | `ipfs_kit`, `ipfs_datasets` | manual file list card |
| `task-manager` | Processes and jobs | `ipfs_accelerate`, `ipfs_datasets` | manual task-progress card |
| `todo` | Todos and goals | `ipfs_datasets`, `ipfs_kit` | manual list card |
| `model-browser` | Model catalog | `ipfs_accelerate`, `ipfs_kit`, `ipfs_datasets` | manual model list card |
| `huggingface` | HF catalog | `ipfs_accelerate`, `ipfs_datasets`, `ipfs_kit` | descriptor or generated search card |
| `openrouter` | Model routing | `ipfs_accelerate`, `ipfs_datasets` | descriptor or generated status card |
| `ipfs-explorer` | IPFS storage | `ipfs_kit` | IDL-generated plus manual polish |
| `device-manager` | Devices and runtime | `ipfs_accelerate`, `ipfs_kit` | manual device status card |
| `settings` | Configuration | all, policy | manual status card |
| `mcp-control` | MCP control | all, `Mcp-Plus-Plus` | descriptor browser card |
| `api-keys` | Credentials | policy, UCAN | fallback/mobile card only unless safe |
| `github` | GitHub integration | `ipfs_datasets`, `ipfs_kit` | summary card plus confirmation |
| `oauth-login` | OAuth | policy, UCAN | mobile-only fallback |
| `cron` | Scheduled automation | `ipfs_accelerate`, `ipfs_datasets` | job schedule card |
| `navi` | Navigation assistant | all | voice-first dispatch card |
| `p2p-network` | P2P network | `ipfs_kit`, `ipfs_accelerate` | peer status card |
| `p2p-chat-unified` | P2P chat | `ipfs_kit`, `ipfs_datasets` | notification/audio fallback |
| `p2p-chat` | Legacy P2P chat | `ipfs_kit` | alias or legacy fallback |
| `neural-network-designer` | Network design | `ipfs_accelerate`, `ipfs_kit` | design summary fallback |
| `training-manager` | Training jobs | `ipfs_accelerate`, `ipfs_datasets`, `ipfs_kit` | task-progress card |
| `calculator` | Calculator | none or local logic | manual compact utility card |
| `clock` | Clock and timers | none or local | manual timer card |
| `calendar` | Calendar | `ipfs_datasets`, `ipfs_kit` | schedule summary card |
| `peertube` | P2P video | `ipfs_kit`, `ipfs_accelerate` | media fallback and playback state |
| `friends-list` | Social/network | `ipfs_kit`, `ipfs_datasets` | contact/status card |
| `image-viewer` | Image viewer | `ipfs_kit`, `ipfs_accelerate` | display/media fallback |
| `notes` | Notes | `ipfs_kit`, `ipfs_datasets` | note list and read-aloud |
| `media-player` | Media player | `ipfs_kit`, `ipfs_accelerate` | playback state card |
| `system-monitor` | Runtime metrics | `ipfs_accelerate` | metrics card |
| `neural-photoshop` | Image generation/editing | `ipfs_accelerate`, `ipfs_kit` | job/progress card, media fallback |
| `cinema` | Video editor | `ipfs_accelerate`, `ipfs_kit` | media/job fallback |
| `strudel` | Live coding music | `ipfs_kit`, `ipfs_accelerate` | audio/status fallback |
| `strudel-ai-daw` | AI DAW | `ipfs_accelerate`, `ipfs_kit` | audio/job fallback |
| `strudel-grandma` | Classic studio | `ipfs_kit` | alias/fallback |
| `p2p-chat-offline` | Offline chat | `ipfs_kit` | alias/fallback |
| `datasets-browser` | Generated datasets app | `ipfs_datasets` | IDL-generated |
| `accelerate-panel` | Generated accelerate app | `ipfs_accelerate` | IDL-generated |
| `idl-explorer` | IDL interface browser | all descriptors | manual descriptor card |
| `orb-auto-ui` | Generated app launcher | all descriptors | manual ORB launcher card |
| `mcp-plus-plus` | MCP++ explorer | all descriptors, receipts | manual protocol card |
| `glasses-preview` | Glasses simulator | glasses layer | manual preview card |

Definition of done for inventory:

- `swissknife/src/services/apps/virtual-desktop-app-manifest.ts` exists.
- `swissknife/contracts/swissknife_virtual_desktop_app_manifest.schema.json`
  exists.
- The desktop HTML/icon list, Start menu, app loader, app docs, and Playwright
  app list either generate from this manifest or fail tests when they diverge.
- Legacy aliases are explicit, not hidden in tests or random switch statements.

## Capability Contract

Each app operation should map to one canonical capability ID. The capability
entry should include:

- `capability_id`
- `server_family`
- `descriptor_pack_id`
- `mcp_tool_name` or `mcp_plus_plus_interface`
- `execution_modes`: `mock`, `direct_import`, `direct_cli`, `mcp_remote`,
  `mcp_plus_plus_remote`
- `default_execution_mode`
- `input_schema`
- `result_schema`
- `policy_class`: read, write, destructive, credential, media, compute,
  external_network
- `confirmation_policy`
- `receipt_policy`
- `desktop_result_renderer`
- `glasses_summary_renderer`
- `fallback_strategy`

Initial capability families:

| Capability Family | Owner | Examples |
| --- | --- | --- |
| `ipfs.kit.storage` | `ipfs_kit_py` | add, cat, pin, unpin, list pins, DAG get/put, IPNS |
| `ipfs.kit.vfs` | `ipfs_kit_py` | mount, read, write, sync, metadata event |
| `ipfs.datasets.discovery` | `ipfs_datasets_py` | list/load datasets, semantic search, faceted search |
| `ipfs.datasets.vector` | `ipfs_datasets_py` | embed, vector index, vector search |
| `ipfs.datasets.provenance` | `ipfs_datasets_py` | record provenance, audit events, knowledge graph |
| `ipfs.datasets.logic` | `ipfs_datasets_py` | policy compile/evaluate, theorem/prover calls |
| `ipfs.accelerate.models` | `ipfs_accelerate_py` | list models, hardware profile, endpoint status |
| `ipfs.accelerate.inference` | `ipfs_accelerate_py` | inference job, embeddings, multimodal jobs |
| `ipfs.accelerate.jobs` | `ipfs_accelerate_py` | submit task, poll status, metrics, telemetry |
| `mcp.registry` | SwissKnife and MCP++ | discover, bind, inspect, trust, invoke |
| `glasses.edge` | SwissKnife and mobile | register edge, publish event, dispatch response |

## Workstream 0: Baseline And Evidence Freeze

Goal: know what is real before refactoring.

Tasks:

- Run current app enumeration from HTML, runtime registries, app scripts, and
  docs.
- Run the current desktop Playwright launch test against all app IDs.
- Capture screenshots, console errors, network errors, and launch status.
- Run existing MCP++ descriptor-pack tests:
  - `test/mcp-plus-plus/ipfs-kit-descriptor-pack.test.ts`
  - `test/mcp-plus-plus/ipfs-datasets-descriptor-pack.test.ts`
  - `test/mcp-plus-plus/ipfs-accelerate-descriptor-pack.test.ts`
  - `test/mcp-plus-plus/mcp-orb-capability-router.test.ts`
  - `test/mcp-plus-plus/meta-glasses-widget-compiler.test.ts`
- Verify live MCP services with `/mcp` endpoint checks where available.
- Save evidence under `swissknife/test-results/virtual-desktop-ipfs-mcp-orb/`.

Exit criteria:

- One JSON inventory report.
- One screenshot set for every app.
- One service health report for `ipfs_kit`, `ipfs_datasets`, and
  `ipfs_accelerate`.
- Known broken, placeholder, partial, and real apps are classified without
  relying on old validation reports.

## Workstream 1: Single App Manifest

Goal: stop app ID and app count drift.

Implementation shape:

```text
swissknife/src/services/apps/
  virtual-desktop-app-manifest.ts
  virtual-desktop-app-manifest.schema.ts
  virtual-desktop-app-manifest-validator.ts
  browser.ts
  host.ts
```

Each manifest entry should include:

```ts
interface VirtualDesktopAppManifestEntry {
  id: string;
  aliases: string[];
  title: string;
  category: string;
  owner_module: string;
  launch: {
    kind: 'manual' | 'descriptor_generated' | 'external_url' | 'alias';
    component?: string;
    descriptor_ref?: string;
  };
  capabilities: string[];
  service_families: Array<'ipfs_kit' | 'ipfs_datasets' | 'ipfs_accelerate' | 'mcp' | 'glasses' | 'local'>;
  glasses: {
    strategy: 'manual_profile' | 'idl_generated' | 'audio_summary' | 'mobile_card' | 'not_displayable';
    profile_ref?: string;
    fallback_required: true;
  };
  tests: {
    launch: boolean;
    service_contract: boolean;
    glasses_handoff: boolean;
    screenshot: boolean;
  };
}
```

Exit criteria:

- App loader rejects unknown IDs with a structured app-not-registered result.
- The manifest drives desktop launch tests.
- `GLASSES_APP_REGISTRY` plus IDL auto-registration covers every displayable app
  or records a deliberate fallback.

## Workstream 2: IPFS MCP/MCP++ Gateway

Goal: one gateway for desktop, generated apps, ORB, and glasses handoff.

Implementation shape:

```text
swissknife/src/services/mcp/
  swissknife-mcp-capability-registry.ts
  mcp-plus-plus-connector.ts
  mcp-orb-capability-router.ts
  mcp-envelope.ts
  mcp-event-dag.ts

swissknife/src/services/ipfs/
  ipfs-interface-registry.ts
  ipfs-idl-descriptors.ts
  ipfs-orb-profiles.ts
  ipfs-ui-profiles.ts

swissknife/src/services/apps/
  app-capability-gateway.ts
```

Gateway responsibilities:

- Load descriptor packs for the three IPFS server families.
- Normalize tool schemas into app-facing operation contracts.
- Select `direct_import`, `mcp_remote`, or `mcp_plus_plus_remote`.
- Attach correlation IDs, policy decisions, and receipt expectations.
- Return one app result envelope for every call.
- Convert network and tool failures into visible degraded states.

Required result envelope:

```json
{
  "schema": "swissknife.app_result.v1",
  "app_id": "ipfs-explorer",
  "capability_id": "ipfs.kit.pin",
  "server_family": "ipfs_kit",
  "execution_mode": "mcp_plus_plus_remote",
  "status": "completed",
  "summary": "Pinned bafy...",
  "structured_output": {},
  "artifact_refs": {
    "cid": "bafy...",
    "receipt_cid": "bafy...",
    "event_dag_cid": "bafy..."
  },
  "policy": {
    "decision": "allow",
    "confirmation_id": null
  },
  "trace": {
    "correlation_id": "corr_...",
    "interface_cid": "bafy...",
    "tool_name": "pin_to_ipfs",
    "latency_ms": 123
  }
}
```

Exit criteria:

- No app uses a one-off backend route when a registered capability exists.
- Direct and remote modes produce the same top-level envelope.
- Descriptor-pack tests verify every required surface is routable.

## Workstream 3: App Refactor By Dependency Class

Goal: update apps incrementally, starting with those that exercise the IPFS
stack and glasses handoff most directly.

Phase A: core IPFS and MCP apps

- `ipfs-explorer`
- `mcp-control`
- `idl-explorer`
- `orb-auto-ui`
- `mcp-plus-plus`
- `file-manager`
- `terminal`

Required changes:

- Replace hard-coded route tables with the app capability gateway.
- Add capability-aware status indicators.
- Add result renderers for CID, provenance, job, telemetry, and receipt refs.
- Add degraded UI states when a service is unavailable.
- Add app-level Playwright tests that invoke one read and one write capability.

Phase B: AI/model/data apps

- `ai-chat`
- `model-browser`
- `huggingface`
- `openrouter`
- `task-manager`
- `training-manager`
- `neural-network-designer`
- `neural-photoshop`

Required changes:

- Route model discovery and inference through `ipfs_accelerate`.
- Route dataset search, vector, and provenance workflows through
  `ipfs_datasets`.
- Store heavy outputs and media artifacts through `ipfs_kit`.
- Make long-running jobs visible through progress envelopes and telemetry.

Phase C: content, media, social, productivity, utility apps

- `notes`
- `calendar`
- `todo`
- `peertube`
- `media-player`
- `image-viewer`
- `cinema`
- `music-studio-unified`
- `strudel`
- `strudel-ai-daw`
- `p2p-network`
- `p2p-chat-unified`
- `friends-list`
- `device-manager`
- `system-monitor`
- `calculator`
- `clock`
- `settings`
- `api-keys`
- `github`
- `oauth-login`
- `cron`
- `navi`

Required changes:

- Declare capabilities even when the first implementation is local-only.
- Add fallback-only glasses profiles for apps that are unsafe or too rich for
  immediate display rendering.
- Move credential and OAuth actions behind strict policy and mobile-only
  fallbacks.

Exit criteria:

- Every app has a manifest entry, launch test, screenshot, capability mapping,
  and glasses strategy.
- Critical apps have service-contract tests.
- Non-critical apps have at least launch, screenshot, and fallback tests.

## Workstream 4: ORB/IDL Descriptor Coverage

Goal: every service-backed app has an interface descriptor that can be used by
desktop UI, ORB routing, MCP++ receipts, and glasses compilation.

Descriptor requirements:

- `namespace`
- `name`
- `version`
- deterministic interface CID
- method schemas
- output schemas
- error codes
- policy classifications
- UI profile reference
- glasses profile or fallback reference
- result envelope mapping
- receipt/event DAG mapping

Service descriptor priorities:

1. `ipfs_kit` manifest-generated descriptors from
   `mcp-ipfs-kit-tools-manifest.json`.
2. `ipfs_datasets` descriptor pack for browse, get, index, pin, publish, sync,
   progress, vector, provenance, and logic surfaces.
3. `ipfs_accelerate` descriptor pack for hardware profile, inference jobs, job
   status, and telemetry.
4. App-level composite descriptors for workflows that chain server families.

Composite descriptor examples:

- File Manager "pin selected file":
  `local.file.read` -> `ipfs.kit.add` -> `ipfs.kit.pin` ->
  `ipfs.datasets.provenance.record`.
- AI Chat "answer with cited dataset context":
  `ipfs.datasets.semantic_search` -> `ipfs.accelerate.inference` ->
  `ipfs.kit.add` -> receipt.
- Training Manager "train with dataset":
  `ipfs.datasets.load` -> `ipfs.accelerate.submit_task` ->
  `ipfs.accelerate.job_status` -> `ipfs.kit.store_artifact`.

Exit criteria:

- Descriptor inspector can inspect every descriptor without schema errors.
- ORB router can discover, bind, invoke, stream, and recover each descriptor.
- Generated Auto-UI opens for every descriptor marked `descriptor_generated`.

## Workstream 5: Meta Glasses Handoff

Goal: the ORB/IDL layer can hand off each app to Meta glasses layers without
special cases.

Handoff layers:

- Mobile ORB edge descriptor:
  `spec/meta_glasses_mobile_orb_bridge_interface.json`.
- Display widget descriptor:
  `spec/meta_glasses_display_widget_orb_interface.json`.
- App capability registry:
  `swissknife/src/services/glasses/meta-glasses-app-capability-registry.ts`.
- Control plane:
  `swissknife/src/services/glasses/glasses-app-control-plane.ts` and
  `glasses-enhanced-control-plane.ts`.
- IDL compiler:
  `swissknife/src/services/glasses/idl-to-glasses-compiler.ts`.
- Mobile bridge and DAT/native/webapp fallback surfaces.

Per-app glasses contract:

- `open_app`
- `focus_next`
- `focus_previous`
- `activate`
- `dispatch_result`
- `read_aloud` when appropriate
- `show_fallback`
- `clear`
- `recover_session`

Per-app profile requirements:

- viewport fixed to 600 x 600 for display-class widgets.
- no more than three primary actions unless a profile explicitly supports a
  paged control surface.
- text regions have bounded lines and overflow behavior.
- every action maps to an IDL method or an approved local action.
- every media ref is CID-backed or HTTPS-backed with fallback.
- every app has a native-display-unavailable fallback.

Exit criteria:

- `DeploymentReadinessValidator` checks all apps, not only the current subset.
- `meta-glasses-virtual-os.spec.ts` can replay open, focus, activate, response
  dispatch, and fallback for every displayable app.
- `meta-glasses-io-apps.spec.ts` covers camera, audio, display, Neural Band,
  captouch, motion, GPS, and route fallback for app classes that need them.
- Physical-device gates remain separated from hardware-free CI gates.

## Workstream 6: Policy, Security, And Receipts

Goal: make service execution safe enough for voice, glasses, and generated UI.

Required policy classes:

- read-only local
- read-only remote
- write content
- destructive content
- credential or OAuth
- external network
- heavy compute
- media capture
- user communication
- agent/autonomous action

Policy execution rules:

- Read-only actions may run with a visible receipt.
- Write actions require an explicit app policy entry.
- Destructive, credential, OAuth, media capture, and communication actions
  require confirmation.
- Agent/autonomous actions require an actor/delegation chain.
- Glasses actions include surface, event type, focus target, and confidence in
  the decision receipt.
- User-authored control rules compile through the multimodal control-surface
  policy IDL path instead of scattered UI booleans.

Receipt requirements:

- correlation ID
- actor identity or session identity
- app ID
- capability ID
- method/interface CID
- policy decision
- input refs, redacted where needed
- output refs
- fallback path when used
- event DAG parent refs
- timestamp and latency

Exit criteria:

- No side-effectful app action lacks a receipt.
- Policy failures render as structured app/glasses fallback results, not thrown
  exceptions.
- Sensitive apps (`api-keys`, `oauth-login`, credential settings) are mobile or
  desktop controlled and do not expose unsafe glasses actions.

## Workstream 7: Testing And Release Gates

Goal: prove the system works with evidence, not screenshots alone.

Test layers:

1. Unit tests:
   - app manifest validation
   - capability registry lookup
   - execution-mode selection
   - descriptor pack validation
   - result envelope normalization
   - policy classification
2. Integration tests:
   - desktop app to app gateway
   - app gateway to mocked MCP servers
   - app gateway to live local `/mcp` services when available
   - ORB discover/bind/invoke/stream/recover
   - receipt and event DAG persistence
3. E2E tests:
   - launch every app
   - screenshot every app
   - perform one representative read action per service-backed app
   - perform one confirmed write action for critical IPFS apps
   - generate and open Auto-UI apps from descriptors
   - hand off each app to glasses simulator and verify bounded layout
4. Hardware-free glasses tests:
   - DAT unavailable fallback
   - display-webapp fallback
   - mobile card fallback
   - audio summary fallback
   - stale session and recovery
5. Real-device gates:
   - Android/iOS DAT availability
   - display-capable device session
   - Bluetooth audio route readiness
   - physical display render and cleanup

Required evidence artifacts:

```text
swissknife/test-results/virtual-desktop-ipfs-mcp-orb/
  app-inventory.json
  service-health.json
  capability-matrix.json
  descriptor-validation.json
  app-launch-report.json
  app-screenshots/
  glasses-handoff-report.json
  receipt-samples.json
  playwright-report/
```

CI gates:

- Manifest drift gate: app IDs match HTML, app loader, docs, Playwright, and
  glasses registry.
- Descriptor gate: all descriptor packs validate.
- App launch gate: every app opens without uncaught error.
- Capability gate: every declared capability resolves to a gateway route.
- Glasses gate: every displayable app compiles to a valid display profile.
- Fallback gate: every app has a tested fallback.
- Live service gate: optional on developer machines, required for release
  evidence against configured local services.

## Workstream 8: Rollout Sequence

### Milestone 1: Inventory And Drift Closure

- Create app manifest and schema.
- Generate/validate app list from manifest.
- Update app tests to consume manifest.
- Capture baseline screenshots and classify current failures.

Done when app count and app IDs stop drifting.

### Milestone 2: Gateway And Capability Registry

- Implement app capability gateway.
- Connect descriptor packs for `ipfs_kit`, `ipfs_datasets`, and
  `ipfs_accelerate`.
- Add result envelope normalization.
- Add mocked MCP/MCP++ execution tests.

Done when app code can call capabilities without hard-coded service routes.

### Milestone 3: Core IPFS Apps

- Refactor `ipfs-explorer`, `mcp-control`, `idl-explorer`, `orb-auto-ui`,
  `terminal`, and `file-manager`.
- Add read/write service tests.
- Add receipt and CID renderers.

Done when IPFS Explorer can add, pin, list, cat, and show receipts through the
gateway.

### Milestone 4: Data And Accelerate Apps

- Refactor AI/model/search/training apps.
- Wire model discovery, hardware status, inference, job status, dataset search,
  vector, and provenance routes.
- Add job-progress event streams.

Done when Model Browser, AI Chat, Task Manager, and Training Manager can execute
representative `ipfs_accelerate` and `ipfs_datasets` flows.

### Milestone 5: ORB/IDL Descriptor Completeness

- Add composite descriptors.
- Ensure descriptor inspector covers all app/service descriptors.
- Generate desktop Auto-UI for descriptor-backed apps.

Done when descriptor-generated desktop apps and manual apps share the same
gateway, result envelope, and receipt model.

### Milestone 6: Glasses Handoff Completeness

- Extend control plane to all manifest apps.
- Generate display profiles for descriptor-backed apps.
- Add fallback profiles for rich/media/credential apps.
- Run hardware-free glasses handoff tests for every app.

Done when every app can be opened, summarized, or safely declined through the
glasses layer.

### Milestone 7: Live MCP/MCP++ Service Evidence

- Start or connect to real local `ipfs_kit`, `ipfs_datasets`, and
  `ipfs_accelerate` MCP endpoints.
- Verify `/mcp` responses and descriptor discovery.
- Run critical user flows against live services.
- Save evidence artifacts and receipt samples.

Done when release evidence proves real services, not only mocks.

### Milestone 8: Physical Meta Glasses Readiness

- Keep default builds free of mandatory Meta DAT package access.
- Run device-capability diagnostics.
- Validate native display when available.
- Validate display-webapp, mobile-card, notification, and audio fallback paths.

Done when physical rollout can be attempted without breaking CI or non-DAT
developer machines.

## Definition Of Done For The Overall Program

- Every canonical SwissKnife app has:
  - manifest entry
  - launch path
  - ownership module
  - capability mapping
  - service/fallback policy
  - Playwright launch test
  - screenshot evidence
  - glasses strategy
  - result envelope renderer
- Every IPFS service family has:
  - descriptor pack validation
  - capability registry entries
  - local/mock execution tests
  - live `/mcp` verification path
  - result envelope mapping
  - receipt/event DAG mapping
- The ORB/IDL layer can:
  - discover descriptors
  - bind service interfaces
  - invoke methods
  - stream progress
  - recover stale sessions
  - compile display profiles
  - generate Auto-UI apps
- The Meta glasses layer can:
  - open or summarize every app
  - handle focus and activation
  - dispatch service results
  - show native display, webapp, mobile-card, notification, or audio fallback
  - preserve correlation IDs and receipts
- CI and local release gates fail on:
  - app manifest drift
  - missing descriptor coverage
  - app launch failure
  - missing capability route
  - unbounded glasses UI
  - unsafe side-effectful action without policy
  - missing fallback

## Immediate Next Tasks

1. Create `virtual-desktop-app-manifest.ts` and manifest schema.
2. Replace hard-coded Playwright app lists with manifest-driven lists.
3. Add a manifest drift test covering `web/index.html`, `web/src/browser-main.ts`,
   `web/js/main.js`, `GLASSES_APP_REGISTRY`, and app docs.
4. Add `app-capability-gateway.ts` with mock MCP execution and normalized result
   envelope.
5. Wire `ipfs-explorer` through the gateway as the first vertical slice.
6. Compile and test IPFS Explorer's glasses handoff through the IDL compiler and
   deployment readiness validator.
7. Repeat the same vertical slice for Datasets Browser and Accelerate Panel.
8. Expand to all app classes using the milestone order above.

## Supervisor Task Board

This is a machine-readable backlog for the `ipfs_accelerate_py` agent
supervisor. It operationalizes this plan with the dedicated task prefix
`SVD-*` for SwissKnife Virtual Desktop work.

Run from the repository root with the existing supervisor wrappers and explicit
path/prefix overrides:

```bash
python3 scripts/virtual_ai_os_todo_daemon.py \
  --todo-path implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md \
  --task-prefix "## SVD-" \
  --state-prefix swissknife_virtual_desktop \
  --once

python3 scripts/virtual_ai_os_todo_supervisor.py \
  --todo-path implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md \
  --task-prefix "## SVD-" \
  --state-prefix swissknife_virtual_desktop \
  --once
```

To run implementation agents, pass the same `--todo-path`, `--task-prefix`, and
`--state-prefix` values with `--implement`. Prefer `--no-ephemeral-worktree`
when the current dirty SwissKnife checkout state is the intended integration
state for the task.

## SVD-000 Bootstrap supervised SwissKnife virtual desktop backlog

- Status: completed
- Priority: P0
- Track: ops
- Depends on:
- Outputs: implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md, data/virtual_ai_os/state/swissknife_virtual_desktop_task_state.json, data/virtual_ai_os/state/swissknife_virtual_desktop_strategy.json, data/virtual_ai_os/state/swissknife_virtual_desktop_events.jsonl, data/swissknife_virtual_desktop/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets python3 scripts/virtual_ai_os_todo_daemon.py --todo-path implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md --task-prefix "## SVD-" --state-prefix swissknife_virtual_desktop --once
- Acceptance: The plan contains a daemon-parseable `SVD-*` task board and the existing ipfs_accelerate supervisor wrappers can parse it with explicit path, prefix, and state overrides.
- Completion: 2026-07-07: Parsed 23 `SVD-*` tasks with the ipfs_accelerate todo daemon wrapper and generated `swissknife_virtual_desktop_*` supervisor state under `data/virtual_ai_os/state/`.

## SVD-001 Freeze the canonical SwissKnife virtual desktop app inventory

- Status: completed
- Priority: P0
- Track: discovery
- Depends on: SVD-000
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-inventory.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-inventory.md, data/swissknife_virtual_desktop/discovery/app-inventory-baseline.md
- Validation: (cd swissknife && node scripts/list-all-applications.cjs && rg -n "data-app=|openApplication|GLASSES_APP_REGISTRY|IPFS_IDL_DESCRIPTORS" web src/services test/e2e scripts docs/applications)
- Acceptance: Produce a current app inventory that reconciles desktop HTML icons, Start menu entries, runtime launch registries, Playwright app lists, documentation app IDs, glasses registry entries, generated IDL apps, and legacy aliases without changing app code.
- Completion: 2026-07-07: Captured current source-set inventory and drift findings in `swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-inventory.json`, `swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-inventory.md`, and `data/swissknife_virtual_desktop/discovery/app-inventory-baseline.md`.

## SVD-002 Add a manifest schema for all desktop applications

- Status: completed
- Priority: P0
- Track: architecture
- Depends on: SVD-001
- Outputs: swissknife/contracts/swissknife_virtual_desktop_app_manifest.schema.json, swissknife/src/services/apps/virtual-desktop-app-manifest.ts, swissknife/src/services/apps/virtual-desktop-app-manifest-validator.ts, swissknife/test/mcp-plus-plus/virtual-desktop-app-manifest.test.ts
- Validation: cd swissknife && npx jest test/mcp-plus-plus/virtual-desktop-app-manifest.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: A typed manifest exists for every canonical app and records ID, aliases, title, category, owner module, launch kind, capabilities, service families, glasses strategy, and required test coverage; invalid or duplicate app IDs fail validation.
- Completion: 2026-07-07: Added the manifest schema, typed 44-app manifest, validator, alias resolver, and focused Jest coverage. Validation passed with 7 tests.

## SVD-003 Add manifest drift gates across desktop, tests, docs, and glasses registry

- Status: completed
- Priority: P0
- Track: quality
- Depends on: SVD-002
- Outputs: swissknife/test/e2e/virtual-desktop-manifest-drift.spec.ts, swissknife/scripts/validate-virtual-desktop-manifest.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/manifest-drift.json
- Validation: cd swissknife && node scripts/validate-virtual-desktop-manifest.cjs && PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/virtual-desktop-manifest-drift.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: The gate fails when `web/index.html`, app launch registries, Playwright app lists, app documentation, `GLASSES_APP_REGISTRY`, or IDL-generated app descriptors diverge from the manifest.
- Completion: 2026-07-07: Added a manifest drift validator, report output, Playwright wrapper, and no-server Playwright config path for source-only gates. Validation passed with `node scripts/validate-virtual-desktop-manifest.cjs` and `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/virtual-desktop-manifest-drift.spec.ts -c build-tools/configs/playwright.config.ts`.

## SVD-004 Capture launch, screenshot, console, and network baseline evidence for every app

- Status: completed
- Priority: P0
- Track: quality
- Depends on: SVD-002
- Outputs: swissknife/test/e2e/virtual-desktop-all-apps-evidence.spec.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-launch-report.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-screenshots
- Validation: cd swissknife && PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/virtual-desktop-all-apps-evidence.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: Every manifest app is launched in Playwright, screenshots are captured, uncaught browser errors and failed network requests are recorded, and each app is classified as real, partial, placeholder, broken, alias, or generated without relying on stale validation reports.
- Completion: 2026-07-07: Added the all-app evidence Playwright spec and static server path to avoid the Vite watcher limit. Validation passed with 44/44 apps opened, 45 screenshots captured including desktop overview, and `app-launch-report.json` classifying 26 real, 7 generated, 6 placeholder, and 5 broken current-runtime apps.

## SVD-005 Implement the app capability gateway and normalized result envelope

- Status: completed
- Priority: P0
- Track: runtime
- Depends on: SVD-002
- Outputs: swissknife/src/services/apps/app-capability-gateway.ts, swissknife/src/services/apps/app-result-envelope.ts, swissknife/test/mcp-plus-plus/app-capability-gateway.test.ts
- Validation: cd swissknife && npx jest test/mcp-plus-plus/app-capability-gateway.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Apps can invoke canonical capability IDs through one gateway that selects execution mode, attaches correlation ID and policy metadata, and returns a stable result envelope with status, summary, structured output, artifact refs, receipt refs, event DAG refs, and trace metadata.
- Completion: 2026-07-07: Added a manifest-backed app capability gateway, normalized result envelope contract, policy denial path, execution-mode transport dispatch, fallback receipt/event refs, alias resolution, and focused Jest coverage. Validation passed with 6 tests.

## SVD-006 Register IPFS service capability families from descriptor packs

- Status: completed
- Priority: P0
- Track: integration
- Depends on: SVD-005
- Outputs: swissknife/src/services/apps/ipfs-app-capability-registry.ts, swissknife/test/mcp-plus-plus/ipfs-app-capability-registry.test.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/capability-matrix.json
- Validation: cd swissknife && npx jest test/mcp-plus-plus/ipfs-kit-descriptor-pack.test.ts test/mcp-plus-plus/ipfs-datasets-descriptor-pack.test.ts test/mcp-plus-plus/ipfs-accelerate-descriptor-pack.test.ts test/mcp-plus-plus/ipfs-app-capability-registry.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` descriptor packs produce app-facing capability entries with input schemas, result schemas, policy classes, execution modes, UI render hints, glasses summary hints, and fallback strategies.
- Completion: 2026-07-07: Added the IPFS app capability registry, descriptor-derived gateway capability tests, and `capability-matrix.json`. Validation passed with 24 Jest tests across the kit, datasets, accelerate, and registry suites; the emitted matrix contains 146 app-facing capability rows across 28 `ipfs_kit_py`, 6 `ipfs_datasets_py`, and 4 `ipfs_accelerate_py` descriptor operations.

## SVD-007 Replace hard-coded IPFS routes in Terminal and IPFS Explorer

- Status: completed
- Priority: P0
- Track: ui
- Depends on: SVD-005, SVD-006
- Outputs: swissknife/web/src/browser-main.ts, swissknife/web/js/core/app-capability-gateway.js, swissknife/web/js/apps/terminal.js, swissknife/web/js/apps/ipfs-explorer.js, swissknife/test/e2e/ipfs-explorer-capability-gateway.spec.ts, swissknife/test/e2e/terminal-ipfs-capability-gateway.spec.ts
- Validation: cd swissknife && npx playwright test test/e2e/ipfs-explorer-capability-gateway.spec.ts test/e2e/terminal-ipfs-capability-gateway.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: Terminal IPFS commands and IPFS Explorer actions use the app capability gateway for add, cat, pin, unpin, list pins, stat, DAG get/put, IPNS publish/resolve, and service status; degraded service states render visible result envelopes instead of uncaught fetch failures.
- Completion: 2026-07-07: Added the browser app capability gateway adapter, routed Terminal `ipfs`/`sk-ipfs` commands and IPFS Explorer actions through normalized app result envelopes, removed raw `/v1/ipfs` requests from the targeted UI paths, and added Playwright coverage for the required operation set. Validation passed with `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/ipfs-explorer-capability-gateway.spec.ts test/e2e/terminal-ipfs-capability-gateway.spec.ts -c build-tools/configs/playwright.config.ts` and the manifest drift validator remained valid.

## SVD-008 Wire MCP Control, IDL Explorer, MCP++ Explorer, and ORB Auto-UI to descriptors

- Status: completed
- Priority: P0
- Track: ui
- Depends on: SVD-005, SVD-006
- Outputs: swissknife/web/src/orb-dynamic-app-renderer.ts, swissknife/web/src/browser-main.ts, swissknife/web/js/apps/mcp-control.js, swissknife/test/e2e/mcp-orb-descriptor-apps.spec.ts
- Validation: cd swissknife && npx playwright test test/e2e/mcp-orb-descriptor-apps.spec.ts -c build-tools/configs/playwright.config.ts; cd swissknife && npx jest test/mcp-plus-plus/mcp-orb-capability-router.test.ts test/mcp-plus-plus/mcp-descriptor-inspector.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: MCP Control, IDL Explorer, MCP++ Explorer, and ORB Auto-UI discover the same descriptor registry, inspect method schemas, launch generated Auto-UI apps, invoke through the gateway, and surface receipts/event DAG metadata.
- Completion: 2026-07-07: Added the browser MCP descriptor registry, extended the browser app capability gateway for `ipfs_datasets_py` and `ipfs_accelerate_py` descriptor operations, wired MCP Control/generated service surfaces/IDL/MCP++/ORB Auto-UI to registry-backed schemas and gateway envelopes, and added Playwright coverage for descriptor discovery, generated Auto-UI launch, receipts, and event DAG refs. Validation passed with `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/mcp-orb-descriptor-apps.spec.ts -c build-tools/configs/playwright.config.ts`, `npx jest test/mcp-plus-plus/mcp-orb-capability-router.test.ts test/mcp-plus-plus/mcp-descriptor-inspector.test.ts --config=config/jest/jest.config.cjs --runInBand`, JS syntax checks, and the virtual desktop manifest validator.

## SVD-009 Add composite descriptors for cross-service app workflows

- Status: completed
- Priority: P1
- Track: integration
- Depends on: SVD-006
- Outputs: swissknife/src/services/apps/composite-app-descriptors.ts, swissknife/test/mcp-plus-plus/composite-app-descriptors.test.ts, swissknife/docs/applications/composite-ipfs-workflows.md
- Validation: cd swissknife && npx jest test/mcp-plus-plus/composite-app-descriptors.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Composite descriptors exist for File Manager pin selected file, AI Chat answer with cited dataset context, Training Manager train with dataset, Neural Photoshop generate-and-store media, and Task Manager monitor accelerate jobs, with typed multi-step result envelopes and receipt lineage.
- Completion: 2026-07-07: Added `src/services/apps/composite-app-descriptors.ts`, `test/mcp-plus-plus/composite-app-descriptors.test.ts`, and `docs/applications/composite-ipfs-workflows.md`. The catalog now defines the five required cross-service workflows with typed inputs, multi-step IPFS/MCP capability bindings, `swissknife.app-result-envelope.v1` output schemas, receipt lineage, event-DAG requirements for write/provenance steps, and fallback summaries. Validation passed with `npx jest test/mcp-plus-plus/composite-app-descriptors.test.ts --config=config/jest/jest.config.cjs --runInBand`.

## SVD-010 Refactor File Manager, Notes, Calendar, Todo, and GitHub around storage and provenance capabilities

- Status: completed
- Priority: P1
- Track: ui
- Depends on: SVD-005, SVD-006, SVD-009
- Outputs: swissknife/web/js/apps/file-manager.js, swissknife/web/js/apps/notes.js, swissknife/web/js/apps/calendar.js, swissknife/web/js/apps/todo.js, swissknife/web/js/apps/github.js, swissknife/test/e2e/storage-provenance-apps.spec.ts
- Validation: cd swissknife && npx playwright test test/e2e/storage-provenance-apps.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: The productivity and content apps declare and exercise storage, CID, dataset discovery, and provenance capabilities through the gateway, including safe fallbacks when services are unavailable.
- Completion: 2026-07-07: Added shared browser storage/provenance workflow wiring for File Manager, Notes, Calendar, Todo, and GitHub. Each app now declares storage, CID, dataset-discovery, and provenance gateway capabilities and exposes `exerciseStorageProvenanceGateway()` for supervisor/browser validation. The browser gateway and MCP descriptor registry now include `ipfs.datasets.operation.record_provenance`, and `test/e2e/storage-provenance-apps.spec.ts` validates safe degraded envelopes with receipt refs and event DAG refs when live MCP services are unavailable. Validation passed with `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/storage-provenance-apps.spec.ts -c build-tools/configs/playwright.config.ts` and `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/mcp-orb-descriptor-apps.spec.ts test/e2e/storage-provenance-apps.spec.ts -c build-tools/configs/playwright.config.ts`; the exact non-skipped command was blocked locally by Vite `ENOSPC` filesystem watcher exhaustion before tests started.

## SVD-011 Refactor AI, model, training, and compute-heavy apps around accelerate and datasets capabilities

- Status: completed
- Priority: P1
- Track: ui
- Depends on: SVD-005, SVD-006, SVD-009
- Outputs: swissknife/web/js/apps/ai-chat.js, swissknife/web/js/apps/model-browser.js, swissknife/web/js/apps/huggingface.js, swissknife/web/js/apps/openrouter.js, swissknife/web/js/apps/task-manager.js, swissknife/web/js/apps/training-manager.js, swissknife/web/js/apps/neural-network-designer.js, swissknife/test/e2e/accelerate-datasets-apps.spec.ts
- Validation: cd swissknife && npx playwright test test/e2e/accelerate-datasets-apps.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: AI/model/training apps use `ipfs_accelerate_py` for model discovery, hardware profile, inference jobs, job status, and telemetry; they use `ipfs_datasets_py` for dataset discovery, vector search, embedding, and provenance; long-running jobs show progress envelopes.
- Completion: 2026-07-07: Added shared browser accelerate/datasets workflow wiring for AI Chat, Model Browser, Hugging Face, OpenRouter, Task Manager, Training Manager, and Neural Network Designer. Each app now declares model discovery, hardware profile, inference job, job status, telemetry, dataset discovery, embedding, vector search, semantic search, and provenance capabilities and exposes `exerciseAccelerateDatasetsGateway()` for supervisor/browser validation. The browser gateway and MCP descriptor registry now include the additional `ipfs_accelerate_py` and `ipfs_datasets_py` operations required by the workflow. `test/e2e/accelerate-datasets-apps.spec.ts` validates degraded fallback result envelopes, job progress envelopes, receipt refs, and event DAG refs across all seven apps. Validation passed with `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/accelerate-datasets-apps.spec.ts -c build-tools/configs/playwright.config.ts` and `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/mcp-orb-descriptor-apps.spec.ts test/e2e/storage-provenance-apps.spec.ts test/e2e/accelerate-datasets-apps.spec.ts -c build-tools/configs/playwright.config.ts`; the exact non-skipped command was blocked locally by Vite `ENOSPC` filesystem watcher exhaustion before tests started.

## SVD-012 Refactor media and creative apps around artifact storage, media refs, and job progress

- Status: completed
- Priority: P1
- Track: ui
- Depends on: SVD-005, SVD-006, SVD-009
- Outputs: swissknife/web/js/apps/neural-photoshop.js, swissknife/web/js/apps/cinema.js, swissknife/web/js/apps/media-player.js, swissknife/web/js/apps/image-viewer.js, swissknife/web/js/apps/music-studio-unified.js, swissknife/web/js/apps/strudel.js, swissknife/web/js/apps/strudel-ai-daw.js, swissknife/test/e2e/media-artifact-apps.spec.ts
- Validation: cd swissknife && npx playwright test test/e2e/media-artifact-apps.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: Media and creative apps store outputs through `ipfs_kit_py`, run heavy generation or processing through `ipfs_accelerate_py`, attach content-addressed media refs to result envelopes, and expose job/progress/fallback states.
- Completion: 2026-07-07: Added shared browser media artifact workflow wiring for Neural Photoshop, Cinema, Media Player, Image Viewer, Unified Music Studio, Strudel, and Strudel AI DAW. Each app now declares inference job, job status, telemetry, artifact storage, pinning, and provenance capabilities and exposes `exerciseMediaArtifactGateway()` for supervisor/browser validation. `test/e2e/media-artifact-apps.spec.ts` validates content-addressed media refs, progress envelopes, receipt refs, event DAG refs, and degraded descriptor-backed fallbacks across all seven apps. Validation passed with `npx tsc --noEmit --pretty false test/e2e/media-artifact-apps.spec.ts --module esnext --moduleResolution bundler --target es2022 --types node`, `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/media-artifact-apps.spec.ts -c build-tools/configs/playwright.config.ts`, and `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/mcp-orb-descriptor-apps.spec.ts test/e2e/storage-provenance-apps.spec.ts test/e2e/accelerate-datasets-apps.spec.ts test/e2e/media-artifact-apps.spec.ts -c build-tools/configs/playwright.config.ts`; the exact non-skipped command was blocked locally by Vite `ENOSPC` filesystem watcher exhaustion before tests started.

## SVD-013 Refactor network, device, system, navigation, and local utility apps

- Status: completed
- Priority: P2
- Track: ui
- Depends on: SVD-005, SVD-006
- Outputs: swissknife/web/js/apps/p2p-network.js, swissknife/web/js/apps/p2p-chat-unified.js, swissknife/web/js/apps/friends-list.js, swissknife/web/js/apps/device-manager.js, swissknife/web/js/apps/system-monitor.js, swissknife/web/js/apps/navi.js, swissknife/web/js/apps/settings.js, swissknife/web/js/apps/calculator.js, swissknife/web/js/apps/clock.js, swissknife/test/e2e/system-network-local-apps.spec.ts
- Validation: cd swissknife && npx playwright test test/e2e/system-network-local-apps.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: Network, device, system, assistant, settings, and local utility apps have manifest-backed capabilities, explicit local-vs-remote service families, safe fallback behavior, and no hidden dependencies on stale app IDs.
- Completion: 2026-07-07: Added shared browser system/network/local workflow wiring for P2P Network, Unified P2P Chat, Friends List, Device Manager, System Monitor, NAVI, Settings, Calculator, and Clock. Each app now exposes `exerciseSystemNetworkLocalGateway()` and declares explicit `browser-local` capabilities separately from any gateway-backed `ipfs_kit_py`, `ipfs_accelerate_py`, or `ipfs_datasets_py` checks. Calculator and Clock validate as local-only utilities with no remote service dependency; the network/system apps validate safe degraded gateway envelopes, receipts, and event DAG refs when remote services are unavailable. Validation passed with `npx tsc --noEmit --pretty false test/e2e/system-network-local-apps.spec.ts --module esnext --moduleResolution bundler --target es2022 --types node`, `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/system-network-local-apps.spec.ts -c build-tools/configs/playwright.config.ts`, and `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/mcp-orb-descriptor-apps.spec.ts test/e2e/storage-provenance-apps.spec.ts test/e2e/accelerate-datasets-apps.spec.ts test/e2e/media-artifact-apps.spec.ts test/e2e/system-network-local-apps.spec.ts -c build-tools/configs/playwright.config.ts`; the exact non-skipped command was blocked locally by Vite `ENOSPC` filesystem watcher exhaustion before tests started.

## SVD-014 Add policy classifications, confirmation rules, and receipt requirements to all app capabilities

- Status: completed
- Priority: P0
- Track: security
- Depends on: SVD-005, SVD-006
- Outputs: swissknife/src/services/apps/app-capability-policy.ts, swissknife/test/mcp-plus-plus/app-capability-policy.test.ts, swissknife/docs/applications/app-capability-policy.md
- Validation: cd swissknife && npx jest test/mcp-plus-plus/app-capability-policy.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Each app capability is classified as read-only, write, destructive, credential, OAuth, external network, heavy compute, media capture, communication, or autonomous action; side-effectful actions require policy and receipt metadata, and sensitive apps default to desktop/mobile-only fallbacks.
- Completion: 2026-07-07: Added `app-capability-policy.ts`, policy catalog validation, and policy documentation. The catalog merges manifest capabilities with descriptor-derived IPFS/MCP operation capabilities, classifies every rule across the required security classes, enforces confirmation/receipt/event-DAG requirements for side-effectful actions, and gates credential/OAuth/media-sensitive paths to desktop/mobile-only fallbacks. Validation passed with `npx jest test/mcp-plus-plus/app-capability-policy.test.ts --config=config/jest/jest.config.cjs --runInBand`.

## SVD-015 Extend glasses control plane coverage to every manifest app

- Status: completed
- Priority: P0
- Track: glasses
- Depends on: SVD-002, SVD-006, SVD-014
- Outputs: swissknife/src/services/glasses/glasses-app-control-plane.ts, swissknife/src/services/glasses/idl-to-glasses-compiler.ts, swissknife/test/mcp-plus-plus/glasses-manifest-coverage.test.ts
- Validation: cd swissknife && npx jest test/mcp-plus-plus/glasses-manifest-coverage.test.ts test/mcp-plus-plus/meta-glasses-widget-compiler.test.ts test/mcp-plus-plus/meta-glasses-display-profile.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Every manifest app has a glasses strategy: manual display profile, IDL-generated display profile, audio summary, mobile card, or explicit not-displayable fallback; every displayable profile satisfies viewport, text, action, focus, update-rate, media, and fallback constraints.
- Completion: 2026-07-07: Added the manifest glasses control-plane coverage layer and normalized IDL-to-glasses compiler wrapper under `src/services/glasses/`. Coverage now emits one entry for every manifest app, reuses manual profiles when present, compiles IDL-generated profiles for descriptor-backed apps, records audio/mobile/fallback strategies, and validates displayable profiles against viewport, text, action, focus, update-rate, media, and fallback constraints. Validation passed with `npx jest test/mcp-plus-plus/glasses-manifest-coverage.test.ts test/mcp-plus-plus/meta-glasses-widget-compiler.test.ts test/mcp-plus-plus/meta-glasses-display-profile.test.ts --config=config/jest/jest.config.cjs --runInBand`.

## SVD-016 Add hardware-free glasses handoff replay for all displayable apps

- Status: completed
- Priority: P0
- Track: glasses
- Depends on: SVD-015
- Outputs: swissknife/test/e2e/meta-glasses-all-app-handoff.spec.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/glasses-handoff-report.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/glasses-screenshots
- Validation: cd swissknife && npm run test:e2e:meta-glasses -- --grep "all app handoff"
- Acceptance: Playwright replays open app, focus next, focus previous, activate, dispatch result, fallback, clear, and recover session for every displayable app without Meta hardware, DAT package credentials, or paired glasses.
- Completion: 2026-07-07: Added `test/e2e/meta-glasses-all-app-handoff.spec.ts`, included it in the Meta glasses Playwright config, and generated the hardware-free handoff evidence under `test-results/virtual-desktop-ipfs-mcp-orb/`. The replay now compiles each displayable coverage entry into a Meta glasses widget manifest, opens the app in the glasses viewport, focuses next/previous, activates the focused action, dispatches an MCP++ result, exercises fallback, clears the viewport, and recovers the session. Validation passed with `npm run test:e2e:meta-glasses -- --grep "all app handoff"`; the report recorded 13/13 displayable apps passed and 26 screenshots.

## SVD-017 Integrate mobile ORB edge handoff contracts and fallback render targets

- Status: completed
- Priority: P1
- Track: mobile
- Depends on: SVD-015, SVD-016
- Outputs: spec/meta_glasses_mobile_orb_bridge_interface.json, spec/meta_glasses_display_widget_orb_interface.json, swissknife/src/services/glasses/meta-glasses-mobile-orb-bridge.ts, swissknife/src/services/glasses/meta-glasses-display-orb-adapter.ts, swissknife/test/mcp-plus-plus/mobile-orb-edge-all-apps.test.ts
- Validation: cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-mobile-orb-bridge.test.ts test/mcp-plus-plus/meta-glasses-display-orb-adapter.test.ts test/mcp-plus-plus/mobile-orb-edge-all-apps.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Mobile ORB edge operations can register app capabilities, publish glasses events, bind services, invoke app capabilities, subscribe to updates, dispatch responses, revoke bindings, and select native display, display-webapp, mobile-card, notification, or audio-summary fallbacks for every app class.
- Completion: 2026-07-07: Added the glasses-folder mobile/display ORB bridge exports, canonical mobile ORB render-target selection, all-app fallback planning from the manifest glasses coverage, and `mobile-orb-edge-all-apps.test.ts`. Dispatch responses now include a normalized `fallback_selection` that preserves legacy `display_widget`/`audio` aliases while selecting `native_display`, `display_webapp`, `mobile_card`, `notification`, or `audio_summary` according to edge DAT capabilities. Validation passed with `npx jest test/mcp-plus-plus/meta-glasses-mobile-orb-bridge.test.ts test/mcp-plus-plus/meta-glasses-display-orb-adapter.test.ts test/mcp-plus-plus/mobile-orb-edge-all-apps.test.ts --config=config/jest/jest.config.cjs --runInBand`.

## SVD-018 Add live MCP service health and descriptor discovery evidence

- Status: completed
- Priority: P1
- Track: ops
- Depends on: SVD-006, SVD-007, SVD-008
- Outputs: swissknife/scripts/capture-ipfs-mcp-service-evidence.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/service-health.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/descriptor-discovery.json
- Validation: cd swissknife && node scripts/capture-ipfs-mcp-service-evidence.cjs
- Acceptance: The evidence script probes configured `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` MCP endpoints using `/mcp` where applicable, records listener/endpoint availability, descriptor discovery responses, and normalized failures without treating `/health` 404s as service failure.
- Completion: 2026-07-07: Added `scripts/capture-ipfs-mcp-service-evidence.cjs` and generated `service-health.json` plus `descriptor-discovery.json` under `test-results/virtual-desktop-ipfs-mcp-orb/`. The script probes listeners, `/mcp` JSON-RPC, tool-list endpoints, interface endpoints, and health endpoints for `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`; it records normalized endpoint failures and explicitly ignores `/health` 404s as service failures. Validation passed with `node scripts/capture-ipfs-mcp-service-evidence.cjs`; the current local run recorded all three services unavailable with `ECONNREFUSED` and static descriptor fallback counts of 28 kit, 14 datasets, and 12 accelerate operations.

## SVD-019 Run live critical-path desktop to IPFS MCP flows

- Status: completed
- Priority: P1
- Track: integration
- Depends on: SVD-007, SVD-008, SVD-018
- Outputs: swissknife/test/e2e/live-ipfs-mcp-critical-flows.spec.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-critical-flows.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/receipt-samples.json
- Validation: cd swissknife && npx playwright test test/e2e/live-ipfs-mcp-critical-flows.spec.ts -c build-tools/configs/playwright.mcp-dashboard.config.ts
- Acceptance: Against configured live MCP services, the desktop proves at least one read and one write flow for `ipfs_kit_py`, one dataset/vector/provenance flow for `ipfs_datasets_py`, and one model/hardware/inference/job-status flow for `ipfs_accelerate_py`, with receipt samples saved.
- Blocked: 2026-07-07: Refreshed `node scripts/capture-ipfs-mcp-service-evidence.cjs`; current configured service availability remains `available_count: 0` for `ipfs_kit_py` on `127.0.0.1:8014`, `ipfs_datasets_py` on `127.0.0.1:3002`, and `ipfs_accelerate_py` on `127.0.0.1:3003`. Local listener discovery found `ipfs_accelerate_py` running on `9000` and MCP++ on TLS `9002`, with `/mcp/health` OK and `/mcp/tools` returning 108 tools on `9000`. It also found an `ipfs_datasets_py` dashboard on `8899` with `/api/mcp/status` running but `tools_available: 0` and `/api/mcp/tools/list` returning HTTP 500 `"__name__" not in globals`. No `ipfs_kit_py` MCP listener was available. SVD-019 cannot satisfy its live read/write, dataset/vector/provenance, and accelerate inference/job-status acceptance criteria until the configured live services are started or the task is retargeted to the discovered endpoints and the datasets/ipfs_kit services are healthy.
- Update: 2026-07-08: SVD-024 refreshed `service-health.json` and `descriptor-discovery.json`; configured endpoints are now reachable for all three services (`ipfs_kit_py` at `127.0.0.1:8014`, `ipfs_datasets_py` at `127.0.0.1:3002`, and `ipfs_accelerate_py` at `127.0.0.1:3003`) with live tool discovery counts of 91, 340, and 3 respectively. SVD-019 remained blocked only until `live-critical-flows.json` and `receipt-samples.json` were produced by the Playwright live critical-path spec.
- Completion: 2026-07-08: Added `swissknife/test/e2e/live-ipfs-mcp-critical-flows.spec.ts` and updated `build-tools/configs/playwright.mcp-dashboard.config.ts` so the spec is included without wiping release evidence. The live run now exercises six required flows: `ipfs_kit_py` bucket write/read, `ipfs_datasets_py` dataset save, vector index creation, provenance verify, and `ipfs_accelerate_py` hardware recommendation through `tools_dispatch`. Validation passed with `npx playwright test test/e2e/live-ipfs-mcp-critical-flows.spec.ts -c build-tools/configs/playwright.mcp-dashboard.config.ts`; `live-critical-flows.json` reports `status: passed`, `flow_count: 6`, `passed_count: 6`, and `receipt-samples.json` contains 6 receipt samples.

## SVD-020 Add full release evidence aggregation and dashboard report

- Status: completed
- Priority: P1
- Track: quality
- Depends on: SVD-004, SVD-006, SVD-016, SVD-018, SVD-019
- Outputs: swissknife/scripts/build-virtual-desktop-release-evidence.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/release-evidence.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/release-evidence.md
- Validation: cd swissknife && node scripts/build-virtual-desktop-release-evidence.cjs
- Acceptance: One machine-readable and one human-readable evidence report summarize app inventory, launch status, screenshot coverage, capability matrix, descriptor validation, service health, glasses handoff, fallback coverage, receipt samples, and go/no-go state.
- Completion: 2026-07-07: Added `scripts/build-virtual-desktop-release-evidence.cjs` and generated `release-evidence.json` plus `release-evidence.md` under `test-results/virtual-desktop-ipfs-mcp-orb/`. The aggregator summarizes the 44-app manifest, app launch evidence, app and glasses screenshot coverage, capability matrix, descriptor discovery, service health, glasses handoff, gateway fallback spec coverage, live receipt sample availability, and a release go/no-go decision. Validation passed with `node --check scripts/build-virtual-desktop-release-evidence.cjs`, `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/virtual-desktop-all-apps-evidence.spec.ts -c build-tools/configs/playwright.config.ts`, and `node scripts/build-virtual-desktop-release-evidence.cjs`.
- Update: 2026-07-08: After SVD-019 and SVD-023 through SVD-026, the release bundle is complete. `node scripts/capture-virtual-desktop-app-inventory.cjs` emits the 44-app inventory JSON/markdown and baseline, `node scripts/validate-virtual-desktop-manifest.cjs` regenerates a valid `manifest-drift.json`, `node scripts/capture-ipfs-mcp-service-evidence.cjs` records all three configured IPFS MCP services as available, `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/virtual-desktop-all-apps-evidence.spec.ts -c build-tools/configs/playwright.config.ts` opens 44/44 apps with `broken: 0`, `npx playwright test test/e2e/live-ipfs-mcp-critical-flows.spec.ts -c build-tools/configs/playwright.mcp-dashboard.config.ts` produces 6/6 live flow receipts, and `node scripts/build-virtual-desktop-release-evidence.cjs` reports `decision: go`, `blocker_count: 0`, and `warning_count: 0`.

## SVD-021 Add physical Meta glasses rollout readiness gates

- Status: completed
- Priority: P2
- Track: device
- Depends on: SVD-016, SVD-017, SVD-020
- Outputs: docs/meta-glasses-expanded-io-physical-validation-checklist.md, docs/meta-wearables-dat-display-rollout-evidence-template.md, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/physical-rollout-readiness.md
- Validation: rg -n "SVD-021|physical|DAT|native display|display-webapp|fallback|release-channel|firmware|Developer Mode" docs swissknife/test-results/virtual-desktop-ipfs-mcp-orb implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md
- Acceptance: Physical rollout gates document DAT package/linkage requirements, release-channel and firmware prerequisites, native display lifecycle, Web App fallback, Bluetooth audio route readiness, camera/media constraints, paired-device evidence, privacy checks, and manual go/no-go steps without making default CI depend on Meta hardware.
- Completion: 2026-07-07: Updated `docs/meta-glasses-expanded-io-physical-validation-checklist.md` and `docs/meta-wearables-dat-display-rollout-evidence-template.md` with SVD-021 SwissKnife ORB/IDL artifact links and physical release-channel/Developer Mode requirements. Added `swissknife/test-results/virtual-desktop-ipfs-mcp-orb/physical-rollout-readiness.md` with a current physical rollout `NO_GO` decision. The readiness record keeps native DAT display optional and disabled by default until a physical run proves DAT package/linkage state, release-channel or Developer Mode, firmware/app update state, paired display-capable glasses, native display lifecycle, display-webapp fallback, Bluetooth audio routes, camera/media constraints, privacy review, and rollback. Validation passed with `rg -n "SVD-021|physical|DAT|native display|display-webapp|fallback|release-channel|firmware|Developer Mode" docs swissknife/test-results/virtual-desktop-ipfs-mcp-orb implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md`.

## SVD-022 Investigate implementation unknowns and expand the backlog

- Status: completed
- Priority: P2
- Track: discovery
- Depends on: SVD-020
- Outputs: implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md, data/swissknife_virtual_desktop/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py; rg -n "SVD-022|no-new-unknowns|discovered|SVD-" implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md data/swissknife_virtual_desktop/discovery
- Acceptance: After the initial SVD backlog reaches release-evidence aggregation, inspect SwissKnife, Hallucinate App, IPFS MCP service integrations, ORB/IDL descriptors, generated apps, and Meta glasses handoff code paths for missed implementation gaps. Append new daemon-parseable `SVD-*` tasks for discovered gaps, or write a dated no-new-unknowns discovery report with commands, evidence, and residual risk.
- Completion: 2026-07-08: Added `data/swissknife_virtual_desktop/discovery/2026-07-08-svd-022-discovered-gaps.md` and appended SVD-023 through SVD-026 for the discovered release blockers. The discovery report records commands, evidence, residual risk, and the reason this is not a `no-new-unknowns` report: TypeScript service module path regressions block manifest drift evidence, live MCP service endpoints do not match configured release gates, 5 apps still classify as broken in launch evidence, and inventory/drift artifacts are not reproducibly present.

## SVD-023 Repair TypeScript service module re-export paths for manifest and glasses gates

- Status: completed
- Priority: P1
- Track: quality
- Depends on: SVD-020, SVD-022
- Outputs: swissknife/src/services/swissknife-mcp-capability-registry.ts, swissknife/src/services/meta-glasses-display-profile.ts, swissknife/src/services/glasses/glasses-app-control-plane.ts, swissknife/scripts/validate-virtual-desktop-manifest.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/manifest-drift.json
- Validation: cd swissknife && node scripts/validate-virtual-desktop-manifest.cjs && npx jest test/mcp-plus-plus/glasses-manifest-coverage.test.ts test/mcp-plus-plus/meta-glasses-display-profile.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Manifest drift validation and glasses coverage tests load the reorganized service modules without `MODULE_NOT_FOUND` errors; `manifest-drift.json` is regenerated and valid.
- Completion: 2026-07-08: Repaired the service import surface needed by the manifest and glasses gates. Added root compatibility re-exports for `swissknife-mcp-capability-registry`, `meta-glasses-display-profile`, and `meta-glasses-widget-compiler`, retargeted the manifest validator imports to the current `src/services/glasses/*` modules, excluded non-application docs from docs-app drift, and added manifest-driven glasses control-plane coverage helpers with default manifest metadata and `app_title` compatibility. Validation passed with `node scripts/validate-virtual-desktop-manifest.cjs` (`valid: true`, `strict_source_count: 10`, `manifest-drift.json` regenerated), `npx jest test/mcp-plus-plus/glasses-manifest-coverage.test.ts test/mcp-plus-plus/meta-glasses-display-profile.test.ts --config=config/jest/jest.config.cjs --runInBand` (2 suites / 15 tests passed), and the Meta glasses handoff replay.

## SVD-024 Restore or retarget live IPFS MCP service readiness for SVD-019

- Status: completed
- Priority: P1
- Track: ops
- Depends on: SVD-018, SVD-019, SVD-022
- Outputs: swissknife/scripts/capture-ipfs-mcp-service-evidence.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/service-health.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/descriptor-discovery.json
- Validation: cd swissknife && node --check scripts/capture-ipfs-mcp-service-evidence.cjs && node scripts/capture-ipfs-mcp-service-evidence.cjs && node scripts/build-virtual-desktop-release-evidence.cjs
- Acceptance: Evidence captures the actual live MCP/MCP++ endpoints for `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py`; all configured services are reachable or each unavailable service has a documented start command, endpoint correction, and normalized blocker that SVD-019 can consume.
- Completion: 2026-07-08: Fixed `scripts/capture-ipfs-mcp-service-evidence.cjs` so live tool/interface metadata is derived from the full parsed payload before body samples are truncated. Re-ran service capture against the configured endpoints and refreshed `service-health.json` plus `descriptor-discovery.json`: `ipfs_kit_py` is available at `http://127.0.0.1:8014` with 91 live tools, `ipfs_datasets_py` is available at `http://127.0.0.1:3002` with 340 live tools via JSON-RPC, and `ipfs_accelerate_py` is available at `http://127.0.0.1:3003` through `scripts/start-ipfs-accelerate-mcp-compat.cjs` with 3 live compatibility tools for hardware recommendation and dispatch. Static descriptor fallback is no longer used. The configured MCP service availability blocker is cleared.

## SVD-025 Fix broken virtual desktop launch classifications

- Status: completed
- Priority: P1
- Track: ui
- Depends on: SVD-004, SVD-020, SVD-022
- Outputs: swissknife/test/e2e/virtual-desktop-all-apps-evidence.spec.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-launch-report.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-screenshots
- Validation: cd swissknife && PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/virtual-desktop-all-apps-evidence.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: The all-app launch report opens 44/44 apps and no app is classified as `broken`; any remaining placeholder or degraded app states are intentional, visible, and mapped to follow-up tasks.
- Completion: 2026-07-08: Fixed the all-app evidence harness so the local static server serves `.mjs` modules as JavaScript, which resolves the MCP Control dynamic import failure through `hallucinate-backend-bridge.js`. Tightened broken classification to actual rendered error surfaces or load-failure text instead of generic status/filter vocabulary such as "Failed" or "Error". Validation passed with `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/virtual-desktop-all-apps-evidence.spec.ts -c build-tools/configs/playwright.config.ts` (1 passed in 1.0m). The regenerated `app-launch-report.json` opens 44/44 apps with `broken: 0`, `real: 30`, `placeholder: 7`, and `generated: 7`.

## SVD-026 Restore reproducible app inventory and drift artifact generation

- Status: completed
- Priority: P2
- Track: quality
- Depends on: SVD-001, SVD-003, SVD-020, SVD-022, SVD-023
- Outputs: swissknife/scripts/capture-virtual-desktop-app-inventory.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-inventory.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-inventory.md, data/swissknife_virtual_desktop/discovery/app-inventory-baseline.md
- Validation: cd swissknife && node scripts/capture-virtual-desktop-app-inventory.cjs && node scripts/validate-virtual-desktop-manifest.cjs && node scripts/build-virtual-desktop-release-evidence.cjs
- Acceptance: App inventory, manifest drift, and release evidence artifacts can be regenerated from the current checkout with stable counts, canonical app IDs, alias decisions, source-set comparisons, and no missing required release-evidence inventory fields.
- Completion: 2026-07-08: Added `scripts/capture-virtual-desktop-app-inventory.cjs` to generate `app-inventory.json`, `app-inventory.md`, and `data/swissknife_virtual_desktop/discovery/app-inventory-baseline.md` from the manifest plus source-set scans. The inventory records 44 apps, 3 aliases, 10 source sets, source-set counts, canonical IDs, categories, launch kinds, owner modules, service families, glasses strategies, and drift status. Validation passed with `node --check scripts/capture-virtual-desktop-app-inventory.cjs`, `node scripts/capture-virtual-desktop-app-inventory.cjs` (`app_count: 44`, `drift_source_count: 0`), `node scripts/validate-virtual-desktop-manifest.cjs` (`valid: true`), and `node scripts/build-virtual-desktop-release-evidence.cjs` (`decision: go`, `blocker_count: 0`, `warning_count: 0`). Release evidence marks `app_inventory` as present.

## All MCP/MCP++ Tool Coverage Expansion

The current release evidence proves that the desktop, gateway, representative
MCP service calls, and hardware-free Meta glasses handoff are wired end to end.
It does not yet prove exhaustive coverage of every discoverable
`ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` MCP/MCP++ tool.
This expansion defines the next plan layer: every tool must be discovered,
classified, mapped to app capabilities or a deliberate non-app surface, routed
through ORB/IDL where appropriate, and assigned a Meta glasses projection or
fallback policy.

The term `ifps_datasets_py` in requests and notes is treated as a typo or alias
for `ipfs_datasets_py`; generated artifacts should use the canonical
`ipfs_datasets_py` spelling and may record the typo only as an input alias.

### Exhaustive Definition Of Done

A tool is covered only when all of these are true:

- It appears in the all-tools ledger from live MCP discovery, MCP++ interface
  discovery, static descriptor packs, or an explicit tombstone source.
- It has a stable `tool_id`, service family, category, canonical operation
  name, input schema, output schema, policy class, receipt rule, fallback rule,
  and owner module.
- It is either mapped to at least one SwissKnife app capability or marked as
  `admin_only`, `server_internal`, `deprecated`, `unsafe_without_human_review`,
  or `not_app_surface` with a reason.
- It has at least one execution fixture: mock, dry-run, live read-only,
  live side-effectful with cleanup, or blocked with a normalized blocker.
- It has an ORB/IDL descriptor when it is app-routable, automation-routable, or
  glasses-routable.
- It has a Meta glasses behavior: native/display-webapp widget, mobile-card,
  notification, audio-summary, physical-device-only, or not-displayable with a
  safe fallback.
- It participates in release evidence so missing classifications, stale tools,
  or unmapped new tools fail the exhaustive gate.

### Tool Coverage Levels

| Level | Name | Meaning | Release Use |
| --- | --- | --- | --- |
| L0 | Discovered | Tool is seen in live/static discovery with stable identity. | Required for all tools. |
| L1 | Classified | Tool has schemas, policy, receipt, and fallback metadata. | Required for all tools. |
| L2 | Routed | Tool has gateway binding or explicit non-app disposition. | Required for all tools. |
| L3 | Exercised | Tool has mock/dry-run/live evidence and result envelope shape. | Required for app-routable tools. |
| L4 | ORB/IDL | Tool can compile into deterministic interface descriptors. | Required for routable automation and generated UI. |
| L5 | Glasses | Tool has a Meta glasses projection or safe fallback. | Required for app-visible tools. |
| L6 | Physical | Tool is validated on real Meta glasses or deliberately simulator-only. | Required only for physical rollout. |

### Tool Ledger Schema

The all-tools ledger should be generated under
`swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-ledger.json`
and mirrored as markdown for review.

```json
{
  "schema": "swissknife.ipfs-mcp-all-tools-ledger.v1",
  "generated_at": "2026-07-08T00:00:00.000Z",
  "services": [
    {
      "service_family": "ipfs_datasets_py",
      "endpoint": "http://127.0.0.1:3002/mcp",
      "live_tool_count": 340,
      "static_tool_count": 0,
      "tools": [
        {
          "tool_id": "ipfs_datasets_py.dataset_tools.save_dataset",
          "canonical_name": "dataset_tools.save_dataset",
          "source": "mcp_json_rpc_tools_list",
          "category": "dataset_tools",
          "policy_class": "write_content",
          "receipt_policy": "required_for_side_effects",
          "execution_modes": ["mock", "dry_run", "mcp_remote"],
          "app_bindings": ["datasets-browser", "file-manager", "ai-chat"],
          "orb_idl_required": true,
          "glasses_behavior": "mobile-card",
          "coverage_level": "L5",
          "blockers": []
        }
      ]
    }
  ]
}
```

### App Binding Rules

- User-facing tools map to the app that owns the primary workflow.
- Shared storage and provenance tools may map to multiple apps, but each tool
  must have one primary owner for UI copy, policy defaults, and fallback text.
- Admin, auth, secrets, wallet, destructive, or compliance tools default to
  desktop/mobile confirmation and are not directly activatable from glasses.
- Long-running compute, media, scraper, vector, and workflow tools must expose
  progress envelopes and cancellation/recovery semantics before app UI depends
  on them.
- Generated apps can expose broad tool families, but the canonical app manifest
  still records each generated surface and its fallback.

### ORB/IDL And Meta Glasses Rules

- Every app-routable tool gets an IDL method with deterministic schemas,
  deterministic interface CID, policy tags, error codes, and envelope mapping.
- Tool groups with many similar methods should compile into grouped IDL
  interfaces by category, not one massive interface.
- Generated ORB/IDL surfaces must preserve the original MCP/MCP++ tool identity
  for audit and receipt lookup.
- Meta glasses display profiles should expose summaries and high-confidence
  actions, not raw tool catalogs.
- Glasses activation must never bypass desktop/mobile policy for credential,
  OAuth, destructive, media capture, communication, autonomous, or external
  network actions.
- Native DAT display remains an optional physical gate; display-webapp,
  mobile-card, notification, and audio-summary fallbacks remain the default
  safe rollout path until physical evidence exists.

### Exhaustive Release Gates

The representative release gate remains useful, but the all-tools release gate
should add these blockers:

- Any discovered tool is missing from the all-tools ledger.
- Any ledger tool is missing classification, policy, receipt, fallback, or owner.
- Any app-routable tool lacks gateway binding or IDL descriptor coverage.
- Any app-visible tool lacks glasses projection or safe fallback.
- Any high-risk tool is exposed to glasses without confirmation gating.
- Any live service loses discovery parity compared with the previous accepted
  baseline and the change is not recorded as a tombstone.
- Any generated app exposes a tool whose result envelope cannot be rendered.

## Exhaustive All-Tools Taskboard

The following tasks extend the completed SVD-000 through SVD-026 baseline. They
are intended for the `ipfs_accelerate_py` agent supervisor and should be treated
as the next taskboard phase.

## SVD-027 Generate the all MCP/MCP++ tools ledger

- Status: completed
- Priority: P0
- Track: discovery
- Depends on: SVD-018, SVD-024, SVD-026
- Outputs: swissknife/scripts/capture-ipfs-mcp-all-tools-ledger.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-ledger.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-ledger.md
- Validation: cd swissknife && node --check scripts/capture-ipfs-mcp-all-tools-ledger.cjs && node scripts/capture-ipfs-mcp-all-tools-ledger.cjs
- Acceptance: The ledger records every tool discoverable from `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` live MCP endpoints, every tool in static descriptor packs, duplicate/alias/tombstone decisions, service endpoint metadata, category counts, schema hashes, and drift against the previous accepted ledger.
- Completion note 2026-07-08: Added the all-tools ledger capture script and generated `all-tools-ledger.json` plus `all-tools-ledger.md`. Validation passed with 488 exact tool records: 434 live exact tools (`ipfs_kit_py` 91, `ipfs_datasets_py` 340, `ipfs_accelerate_py` 3), 54 static exact descriptor names, 13 unambiguous static-to-live alias decisions, and 0 tombstones on the first accepted ledger run. The current `ipfs_accelerate_py` live count reflects the local compatibility MCP endpoint; SVD-031 remains responsible for replacing or explicitly accepting that boundary.

## SVD-028 Classify every discovered tool by policy, receipt, fallback, and owner

- Status: completed
- Priority: P0
- Track: security
- Depends on: SVD-014, SVD-027
- Outputs: swissknife/src/services/apps/all-tools-policy-classifier.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-policy-matrix.json, swissknife/docs/applications/all-mcp-tools-policy.md
- Validation: cd swissknife && npx jest test/mcp-plus-plus/all-tools-policy-classifier.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Every ledger tool has exactly one owner module, one policy class, one confirmation rule, one receipt rule, one fallback rule, and one exposure disposition. Credential, OAuth, destructive, media capture, communication, autonomous, and external-network tools fail validation unless they are desktop/mobile-confirmed or explicitly not app-visible.
- Completion note 2026-07-08: Added the all-tools policy classifier, Jest contract, policy matrix artifact, and documentation. Validation passed with 488/488 ledger tools classified exactly once. Class counts: read 219, write 68, destructive 12, credential 29, OAuth 0, external_network 77, heavy_compute 46, media_capture 9, communication 8, autonomous_action 20. Exposure counts: app_visible 219, app_visible_with_confirmation 199, desktop_or_mobile_only 50, supervisor_only 20.

## SVD-029 Map every tool to app capabilities or a deliberate non-app disposition

- Status: completed
- Priority: P0
- Track: apps
- Depends on: SVD-005, SVD-006, SVD-027, SVD-028
- Outputs: swissknife/src/services/apps/all-tools-app-binding-matrix.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-app-bindings.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-app-bindings.md
- Validation: cd swissknife && npx jest test/mcp-plus-plus/all-tools-app-binding-matrix.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Every tool is mapped to one or more app IDs or has a normalized disposition: `admin_only`, `server_internal`, `deprecated`, `unsafe_without_human_review`, or `not_app_surface`. Every manifest app has a coverage summary showing which tool families it owns, consumes, hides, or delegates to generated Auto-UI.
- Completion note 2026-07-08: Added the all-tools app binding matrix and Jest contract, then generated `all-tools-app-bindings.json` and `all-tools-app-bindings.md`. Validation passed with 488/488 ledger tools bound exactly once: 47 existing app capabilities, 371 generated descriptor app capabilities, 50 desktop/mobile-only bindings normalized as `unsafe_without_human_review`, 20 supervisor-only internal bindings normalized as `server_internal`, and 0 blocked/non-app rows. App counts: datasets-browser 282, ipfs-explorer 79, idl-explorer 55, mcp-control 26, accelerate-panel 13, p2p-network 7, file-manager 6.

## SVD-030 Build exhaustive tool execution fixtures and result-envelope tests

- Status: completed
- Priority: P0
- Track: quality
- Depends on: SVD-005, SVD-019, SVD-027, SVD-029
- Outputs: swissknife/test/mcp-plus-plus/all-tools-execution-fixtures.test.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-execution-report.json
- Validation: cd swissknife && npx jest test/mcp-plus-plus/all-tools-execution-fixtures.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Every app-routable tool has a mock or dry-run fixture that validates input schema, output schema, normalized envelope, policy metadata, receipt metadata, fallback rendering, and error rendering. Live tests are required for representative read/write/dataset/vector/provenance/hardware families; destructive live tests must use dry-run or isolated cleanup fixtures.
- Completion note 2026-07-08: Added exhaustive dry-run execution fixtures and generated `all-tools-execution-report.json`. Validation passed with 488 total fixtures: 418 app-routable dry-run envelopes, 70 denied envelopes for supervisor-only or desktop/mobile-only tools, and 269 side-effect receipt/event-DAG fixture pairs. Representative fixture coverage includes read (`IPFS.ipfs_cat`), write (`dataset_tools.save_dataset`), dataset (`dataset_tools.load_dataset`), vector (`bespoke_tools.create_vector_store`), provenance (`provenance_tools.record_provenance`), hardware (`hardware_recommend`), and destructive dry-run (`Files.files_rm`). Live invocation remains representative-only and must stay bounded by SVD-031/SVD-036.

## SVD-031 Replace the accelerate compatibility shim with full ipfs_accelerate_py MCP coverage or an explicit accepted boundary

- Status: completed
- Priority: P0
- Track: ops
- Depends on: SVD-024, SVD-027
- Outputs: swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ipfs-accelerate-endpoint-decision.md
- Validation: cd swissknife && node scripts/capture-ipfs-mcp-service-evidence.cjs && node scripts/capture-ipfs-mcp-all-tools-ledger.cjs
- Acceptance: Either the real `ipfs_accelerate_py` MCP/MCP++ endpoint exposes the full expected tool surface on the configured SwissKnife endpoint, or the compatibility endpoint is documented as a bounded bridge with every missing accelerate tool marked by tool ID, desired upstream endpoint, app impact, and follow-up task. No release report may imply full accelerate coverage while only compatibility hardware tools are available.
- Completion note 2026-07-08: Added `ipfs-accelerate-endpoint-decision.md` and accepted the configured `http://127.0.0.1:3003` endpoint as a bounded SwissKnife compatibility bridge, not full accelerate coverage. Validation passed with `node scripts/capture-ipfs-mcp-service-evidence.cjs` and `node scripts/capture-ipfs-mcp-all-tools-ledger.cjs`: configured live counts remain `ipfs_kit_py` 91, `ipfs_datasets_py` 340, and `ipfs_accelerate_py` 3. The real local accelerate service is separately reachable at `http://127.0.0.1:9000/mcp/tools` with 108 tools, but it does not expose the configured base-MCP JSON-RPC `/mcp` `tools/list` shape; downstream SVD-032/SVD-038 work must keep static-only accelerate tools marked adapter-required until a normalizing adapter or endpoint retarget is implemented.

## SVD-032 Refactor each app family against the all-tools binding matrix

- Status: completed
- Priority: P1
- Track: ui
- Depends on: SVD-029, SVD-030
- Outputs: swissknife/web/js/apps/*, swissknife/test/e2e/all-tools-app-family-coverage.spec.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-app-family-coverage.json
- Validation: cd swissknife && PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/all-tools-app-family-coverage.spec.ts -c build-tools/configs/playwright.config.ts
- Acceptance: Each app family exposes the intended capabilities from the binding matrix with visible ready, running, success, degraded, blocked, and fallback states. Generated and placeholder surfaces must be explicit; no app may silently hide a mapped primary tool family without a documented UI reason.
- Completion note 2026-07-08: Added `all-tools-app-family-coverage.spec.ts`, wired it into the Playwright config, and generated `all-tools-app-family-coverage.json`. Validation passed with `PLAYWRIGHT_SKIP_WEB_SERVER=1 npx playwright test test/e2e/all-tools-app-family-coverage.spec.ts -c build-tools/configs/playwright.config.ts`. The report covers 7 app families and 418 app-visible tools: datasets-browser 282, ipfs-explorer 79, idl-explorer 55, mcp-control 26, accelerate-panel 13, p2p-network 7, and file-manager 6. Each family reports ready/running/success/degraded/blocked/fallback state coverage; accelerate-panel carries 11 adapter-required rows from the SVD-031 bounded endpoint decision.

## SVD-033 Generate composite workflows that exercise cross-service tool chains

- Status: completed
- Priority: P1
- Track: integration
- Depends on: SVD-009, SVD-027, SVD-029, SVD-030
- Outputs: swissknife/src/services/apps/all-tools-composite-workflows.ts, swissknife/test/mcp-plus-plus/all-tools-composite-workflows.test.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-composite-workflows.json
- Validation: cd swissknife && npx jest test/mcp-plus-plus/all-tools-composite-workflows.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: The workflow catalog covers storage-to-provenance, dataset-to-vector, search-to-inference, media-generation-to-IPFS, hardware-selection-to-job, wallet/credential-safe, and admin/reporting tool chains. Each workflow has typed steps, rollback or cleanup behavior, event DAG lineage, and a glasses fallback summary.
- Completion note 2026-07-08: Added `all-tools-composite-workflows.ts`, `all-tools-composite-workflows.test.ts`, and generated `all-tools-composite-workflows.json`. Validation passed with `npx jest test/mcp-plus-plus/all-tools-composite-workflows.test.ts --config=config/jest/jest.config.cjs --runInBand` (5 passed). The catalog covers 7 required workflow families and 27 typed steps: storage-to-provenance, dataset-to-vector, search-to-inference, media-generation-to-IPFS, hardware-selection-to-job, wallet/credential-safe, and admin/reporting. Service coverage is `ipfs_kit_py` 5 steps, `ipfs_datasets_py` 15 steps, and `ipfs_accelerate_py` 7 steps; 6 accelerate steps are marked adapter-required under the SVD-031 bounded endpoint decision, and 3 credential steps remain desktop/mobile-only with glasses-denial handoff.

## SVD-034 Generate ORB/IDL descriptors for every app-routable tool and workflow

- Status: completed
- Priority: P0
- Track: orb-idl
- Depends on: SVD-008, SVD-027, SVD-029, SVD-033
- Outputs: swissknife/src/services/all-tools-idl-generator.ts, swissknife/test/mcp-plus-plus/all-tools-idl-generator.test.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-idl-coverage.json
- Validation: cd swissknife && npx jest test/mcp-plus-plus/all-tools-idl-generator.test.ts test/mcp-plus-plus/mcp-orb-capability-router.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Every app-routable tool and composite workflow has a deterministic ORB/IDL descriptor, method schema, output schema, error code set, policy tags, receipt mapping, interface CID, and generated UI profile. Descriptor generation must group large tool families by category so UI and glasses surfaces remain navigable.
- Completion note 2026-07-08: Added `all-tools-idl-generator.ts`, `all-tools-idl-generator.test.ts`, and generated `all-tools-idl-coverage.json`. Validation passed with `npx jest test/mcp-plus-plus/all-tools-idl-generator.test.ts test/mcp-plus-plus/mcp-orb-capability-router.test.ts --config=config/jest/jest.config.cjs --runInBand` (20 passed). The catalog contains 96 deterministic IDL descriptors: 89 tool-group descriptors plus 7 workflow descriptors. Coverage includes all 418 app-routable tools, all 7 composite workflows, 445 total IDL methods, 96 unique interface CIDs, generated UI profiles, policy tags, receipt mappings, error code sets, and ORB discovery coverage. Adapter-required coverage is 17 methods total: 11 app-routable accelerate tool methods plus 6 workflow step methods under the SVD-031 bounded endpoint decision.

## SVD-035 Extend Meta glasses coverage to every app-visible tool family

- Status: completed
- Priority: P0
- Track: glasses
- Depends on: SVD-015, SVD-016, SVD-017, SVD-029, SVD-034
- Outputs: swissknife/src/services/all-tools-glasses-projection.ts, swissknife/test/mcp-plus-plus/all-tools-glasses-projection.test.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-glasses-coverage.json
- Validation: cd swissknife && npx jest test/mcp-plus-plus/all-tools-glasses-projection.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Every app-visible tool family has one Meta glasses behavior: native/display-webapp widget, mobile-card, notification, audio-summary, physical-device-only, or not-displayable. Hardware-free replay must prove open, focus, activate, dispatch result, fallback, clear, recover, and policy-block rendering for each displayable family.
- Completion note 2026-07-08: Added `all-tools-glasses-projection.ts`, `all-tools-glasses-projection.test.ts`, and generated `all-tools-glasses-coverage.json`. Validation passed with `npx jest test/mcp-plus-plus/all-tools-glasses-projection.test.ts --config=config/jest/jest.config.cjs --runInBand` (5 passed). The catalog includes 96 projections: 89 tool-family projections and 7 workflow projections, matching the SVD-034 IDL descriptor catalog. Hardware-free replay covers 768 frames across open, focus, activate, dispatch-result, fallback, clear, recover, and policy-block states. Behavior counts are native-display 29, display-webapp 63, mobile-card 3, physical-device-only 1, notification 0, audio-summary 0, and not-displayable 0; 7 projections are adapter-required under the SVD-031 endpoint boundary.

## SVD-036 Add full-tool policy receipt and audit release gates

- Status: completed
- Priority: P0
- Track: security
- Depends on: SVD-028, SVD-030, SVD-034, SVD-035
- Outputs: swissknife/src/services/apps/all-tools-release-policy-gates.ts, swissknife/test/mcp-plus-plus/all-tools-release-policy-gates.test.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-policy-release-gate.json
- Validation: cd swissknife && npx jest test/mcp-plus-plus/all-tools-release-policy-gates.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Release fails when any tool lacks policy, receipt, fallback, owner, app disposition, ORB/IDL descriptor, or glasses behavior required by its exposure level. High-risk tools must demonstrate confirmation and blocked-state rendering in desktop/mobile/glasses contexts.
- Completion note 2026-07-08: Added `all-tools-release-policy-gates.ts`, `all-tools-release-policy-gates.test.ts`, and generated `all-tools-policy-release-gate.json`. Validation passed with `npx jest test/mcp-plus-plus/all-tools-release-policy-gates.test.ts --config=config/jest/jest.config.cjs --runInBand` (4 passed). The exhaustive gate report evaluates 8 required gates across 488 tool records and 418 app-visible tools. Seven gates pass: ledger coverage, policy classification, app bindings, execution fixtures, ORB/IDL descriptors, Meta glasses projections, and high-risk confirmation/receipt policy. The report intentionally returns `decision: no_go` with 1 blocker because SVD-031 accepted only a bounded `ipfs_accelerate_py` compatibility endpoint; 11 app-routable accelerate tools and 17 IDL methods remain adapter-required until the full accelerate MCP adapter boundary is closed.

## SVD-037 Wire all-tools tasks into the ipfs_accelerate_py agent supervisor

- Status: completed
- Priority: P1
- Track: supervisor
- Depends on: SVD-027, SVD-028, SVD-029, SVD-030
- Outputs: implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md, data/swissknife_virtual_desktop/all_tools_supervisor_queue.json
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py
- Acceptance: The agent supervisor can parse SVD-027 through SVD-040, assign owners, track dependencies, resume failed tasks, record evidence paths, and avoid treating generated evidence churn as source implementation work.
- Completion note 2026-07-08: Added `data/swissknife_virtual_desktop/all_tools_supervisor_queue.json` with SVD-027 through SVD-040 task metadata, dependency graph, owners, validation commands, generated evidence globs, and resume contract. Added pytest coverage that verifies the queue is parseable, tracks completed and ready tasks, records evidence paths, and keeps generated evidence separate from source outputs. Validation passed with `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py` (70 passed).

## SVD-038 Extend release evidence aggregation to the exhaustive all-tools gate

- Status: completed
- Priority: P0
- Track: quality
- Depends on: SVD-027, SVD-028, SVD-029, SVD-030, SVD-034, SVD-035, SVD-036
- Outputs: swissknife/scripts/build-virtual-desktop-release-evidence.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/release-evidence.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-release-evidence.md
- Validation: cd swissknife && node scripts/build-virtual-desktop-release-evidence.cjs
- Acceptance: The release report includes all-tools ledger counts, classification coverage, app binding coverage, execution fixture coverage, ORB/IDL coverage, glasses coverage, policy gate status, tombstones, new-tool drift, and go/no-go blockers. `decision: go` is allowed only when both the representative app gate and exhaustive all-tools gate pass.
- Completion note 2026-07-08: Added `scripts/build-virtual-desktop-release-evidence.cjs` and regenerated `release-evidence.json`, `release-evidence.md`, and `all-tools-release-evidence.md`. Validation passed with `node --check scripts/build-virtual-desktop-release-evidence.cjs` and `node scripts/build-virtual-desktop-release-evidence.cjs`. The representative app gate is `go`, the exhaustive all-tools gate is `no_go`, and the combined release decision is `no_go` with 1 blocker from the SVD-031 bounded `ipfs_accelerate_py` adapter boundary. The report carries all-tools ledger, policy, binding, app-family fallback state, execution fixture, ORB/IDL, glasses projection, policy gate, tombstone, and new-tool drift counts.

## SVD-039 Run physical Meta glasses validation waves for high-risk and high-value tool families

- Status: blocked
- Priority: P2
- Track: device
- Depends on: SVD-021, SVD-035, SVD-036, SVD-038
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/physical-all-tools-glasses-validation.md, docs/meta-glasses-expanded-io-physical-validation-checklist.md
- Validation: rg -n "physical-all-tools|SVD-039|native DAT|display-webapp|mobile-card|audio-summary" docs swissknife/test-results/virtual-desktop-ipfs-mcp-orb
- Acceptance: Physical device validation covers representative storage, dataset/vector/provenance, accelerate hardware/job, media, credential-blocked, and admin-blocked families. The physical rollout remains `NO_GO` until native DAT/display-webapp behavior, input routing, Bluetooth audio, camera/privacy constraints, rollback, and receipts are proven on real hardware.
- Blocked note 2026-07-08: Added `physical-all-tools-glasses-validation.md` and linked it from the expanded physical checklist. The task is intentionally blocked, not completed, because this workspace run has no paired physical Meta glasses device, native DAT release-channel build, package credential evidence, firmware/app-version evidence, or on-device capture logs. Hardware-free ORB/IDL and glasses projection coverage remains valid, but native DAT, display-webapp, mobile-card, and audio-summary physical waves still require real hardware evidence.

## SVD-040 Produce an all-tools no-unknowns closeout or append the next discovered backlog

- Status: completed
- Priority: P1
- Track: discovery
- Depends on: SVD-038
- Outputs: data/swissknife_virtual_desktop/discovery/all-tools-no-new-unknowns.md or appended SVD tasks
- Validation: rg -n "SVD-040|no-new-unknowns|all-tools|discovered" data/swissknife_virtual_desktop/discovery implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md
- Acceptance: After the exhaustive gate runs, record either a no-new-unknowns report with commands, counts, evidence paths, and residual risk, or append new SVD tasks for every remaining tool, app, ORB/IDL, policy, service, or Meta glasses gap.
- Completion note 2026-07-08: Added `data/swissknife_virtual_desktop/discovery/all-tools-no-new-unknowns.md`. Validation passed with `rg -n "SVD-040|no-new-unknowns|all-tools|discovered" data/swissknife_virtual_desktop/discovery implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md`. No new unknown all-tools integration class was discovered beyond the existing SVD-031/SVD-036/SVD-038 accelerate adapter boundary and the SVD-039 physical hardware block. SVD-041 through SVD-047 were later appended as an explicit phase-two release plan, not as newly discovered unknowns from SVD-040.

## Agent Supervisor Execution Overlay 2026-07-08

This overlay is the supervisor-facing execution plan for completing the
all-tools program. The `ipfs_accelerate_py` agent supervisor should treat
SVD-027 through SVD-040 as one resumable task graph, using generated evidence
files as state checkpoints and source files/tests as implementation outputs.

Current checkpoints:

- SVD-027 completed: all-tools ledger generated from live `ipfs_kit_py`,
  `ipfs_datasets_py`, `ipfs_accelerate_py`, and static descriptor packs.
- SVD-028 completed: every ledger row has policy, receipt, fallback, owner,
  exposure, and glasses gating classification.
- SVD-029 completed: every ledger row has an app binding or deliberate
  non-app/supervisor-only disposition.
- SVD-030 completed: every ledger row has a dry-run execution fixture or
  denied-envelope fixture with receipt/event-DAG coverage where required.
- SVD-031 completed: the configured accelerate endpoint is explicitly accepted
  only as a bounded compatibility bridge; full local accelerate service coverage
  remains adapter-required.
- SVD-032 completed: app-family coverage now proves visible, blocked,
  degraded, and fallback states for every app family with all-tools bindings.
- SVD-033 completed: composite workflows now cover all seven required
  cross-service tool-chain families with typed steps, cleanup behavior,
  event-DAG lineage, glasses fallbacks, and SVD-031 adapter flags.
- SVD-034 completed: ORB/IDL descriptor generation now covers every
  app-routable tool and composite workflow with deterministic interface CIDs,
  generated UI profiles, receipt mappings, and ORB discovery validation.
- SVD-035 completed: Meta glasses projections now cover every generated
  tool-family and workflow descriptor with behavior assignments and
  hardware-free replay for open/focus/activate/result/fallback/clear/recover/block.
- SVD-036 completed: exhaustive policy release gates now fail the all-tools
  release when receipt, policy, app binding, ORB/IDL, glasses projection, or
  accepted accelerate adapter-boundary evidence is incomplete.
- SVD-037 completed: the supervisor queue can schedule SVD-027 through SVD-040
- SVD-038 completed: release evidence now merges representative app evidence
  with exhaustive all-tools evidence and remains `no_go` on the accepted
  `ipfs_accelerate_py` adapter boundary.
- SVD-039 blocked: physical Meta glasses validation is not complete because no
  paired device, native DAT build, credentials, firmware evidence, or on-device
  logs are available in this workspace run.
- SVD-040 completed: discovery closeout found no new unknown task class beyond
  the known accelerate adapter boundary and physical-device validation block.
- Supervisor terminal state: SVD-027 through SVD-038 and SVD-040 are completed;
  SVD-039 is blocked; no runnable ready task remains.

Supervisor work packets:

1. Quality fixtures packet: run SVD-030 to generate mock/dry-run execution
   fixtures and envelope validation for every app-routable tool.
2. Accelerate endpoint packet: run SVD-031 to decide whether the compatibility
   `ipfs_accelerate_py` endpoint is accepted or must be replaced by a full MCP
   endpoint before release.
3. App integration packet: run SVD-032 to update each virtual desktop app
   family against `all-tools-app-bindings.json` and remove hard-coded service
   assumptions.
4. Cross-service workflow packet: run SVD-033 to exercise storage, dataset,
   vector/provenance, and accelerate workflows that span multiple service
   families.
5. ORB/IDL packet: run SVD-034 to generate ORB/IDL descriptors for every
   app-visible tool and workflow, including fallback descriptors for
   supervisor-only and desktop/mobile-only tools.
6. Glasses packet: run SVD-035 to compile Meta glasses display/mobile/audio
   handoff profiles for every app-visible family, while preserving hard blocks
   for credential, media, destructive, and autonomous tools.
7. Policy and audit gate packet: run SVD-036 to fail release evidence when
   receipts, confirmation, policy metadata, event DAG refs, or tombstones are
   missing.
8. Supervisor wiring packet: run SVD-037 so the agent supervisor can parse this
   taskboard, schedule dependencies, resume failed tasks, and record evidence
   paths without treating ignored generated evidence as source churn.
9. Release aggregation packet: run SVD-038 to merge representative app evidence
   and exhaustive all-tools evidence into one go/no-go report.
10. Physical rollout packet: run SVD-039 only after SVD-038 is green; record
    real Meta glasses DAT/display-webapp/mobile-card/audio results.
11. Closeout packet: run SVD-040 to record no-new-unknowns or append new SVD
    backlog items for every remaining gap.

Supervisor resume contract:

- Source outputs are authoritative when tracked by git.
- Evidence outputs under
  `swissknife/test-results/virtual-desktop-ipfs-mcp-orb/` are authoritative
  for the current run even when ignored by git.
- A task is resumable when its validation command exits 0 and its expected
  evidence file exists.
- A task is blocked only when its dependency evidence is missing, the live MCP
  service boundary is unavailable, or physical Meta glasses hardware is
  required.
- The supervisor must not mark a downstream app, ORB/IDL, glasses, or release
  gate task complete if SVD-031 records the accelerate compatibility endpoint
  as insufficient for that task's required surface.

## Agent Supervisor Phase Two 2026-07-08

This phase keeps the SVD-027 through SVD-040 evidence as the accepted baseline
and adds the remaining implementation tasks required for all SwissKnife virtual
desktop applications to work correctly with every discovered
`ipfs_kit_py`, `ipfs_datasets_py`, `ipfs_accelerate_py`, MCP, and MCP++ tool.
The phase-two queue is intentionally concrete: it separates local evidence
cleanup from the real release blocker, which is the incomplete full
`ipfs_accelerate_py` adapter surface.

## SVD-041 Append phase-two all-tools supervisor plan

- Status: completed
- Priority: P0
- Track: supervisor
- Depends on: SVD-038, SVD-040
- Outputs: implementation_plan/docs/37-swissknife-virtual-desktop-ipfs-mcp-orb-meta-glasses-plan-2026-07-07.md, data/swissknife_virtual_desktop/all_tools_supervisor_queue.json, tests/test_virtual_ai_os_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py
- Acceptance: The agent supervisor can resume the all-tools program beyond SVD-040, with completed local cleanup tasks, the next runnable adapter task, waiting downstream tasks, and physical Meta glasses blockers represented explicitly.
- Completion note 2026-07-08: Appended SVD-041 through SVD-047 as the next supervisor phase. The queue now treats SVD-044 as the next runnable task and keeps physical Meta glasses work blocked on real hardware evidence.

## SVD-042 Generate the all-app all-tools capability matrix

- Status: completed
- Priority: P0
- Track: quality
- Depends on: SVD-029, SVD-032, SVD-034, SVD-035, SVD-038
- Outputs: swissknife/scripts/build-all-tools-capability-matrix.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/capability-matrix.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/capability-matrix.md
- Validation: cd swissknife && node --check scripts/build-all-tools-capability-matrix.cjs && node scripts/build-all-tools-capability-matrix.cjs && node scripts/build-virtual-desktop-release-evidence.cjs
- Acceptance: Every manifest app has one capability matrix row that summarizes manifest service families, app-visible tools, service counts, policy classes, receipt/confirmation counts, execution fixture coverage, ORB/IDL descriptors, Meta glasses projections, hardware-free replay states, and adapter-required tools.
- Completion note 2026-07-08: Added the capability matrix generator and generated `capability-matrix.json` plus `capability-matrix.md`. The matrix covers 44 apps, 7 all-tools-bound app families, 418 app-visible tools, 96 ORB/IDL descriptors, 96 Meta glasses projections, 768 replay states, and 11 adapter-required tools. Regenerating release evidence removed the previous missing capability-matrix warning.

## SVD-043 Reconcile legacy Playwright app selectors with the manifest

- Status: completed
- Priority: P1
- Track: quality
- Depends on: SVD-018, SVD-038
- Outputs: swissknife/test/e2e/validate-all-applications.test.ts, swissknife/scripts/validate-virtual-desktop-manifest.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/manifest-drift.json
- Validation: cd swissknife && node --check scripts/validate-virtual-desktop-manifest.cjs && node scripts/validate-virtual-desktop-manifest.cjs && npx tsc --noEmit --pretty false --allowJs false --skipLibCheck --moduleResolution node --module commonjs --target es2020 --types node,playwright test/e2e/validate-all-applications.test.ts
- Acceptance: Legacy app selectors such as `files`, `tasks`, `ipfs`, `devices`, `oauth`, `ai-cron`, `nn-designer`, `training`, `images`, `monitor`, and `friends` are replaced with canonical manifest app IDs, and manifest drift evidence reports zero warnings for the legacy validation test.
- Completion note 2026-07-08: Updated `validate-all-applications.test.ts` to the canonical 44-app manifest IDs, fixed its desktop icon count assertion, added a manifest drift validator, and regenerated `manifest-drift.json` with `valid: true`, `error_count: 0`, and `warning_count: 0`. Release evidence now has only the MCP endpoint-probe warning plus the known accelerate adapter release blocker.

## SVD-044 Normalize the full ipfs_accelerate_py MCP adapter boundary

- Status: ready
- Priority: P0
- Track: ops
- Depends on: SVD-031, SVD-036, SVD-038, SVD-042
- Outputs: swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs, swissknife/src/services/apps/all-tools-release-policy-gates.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ipfs-accelerate-adapter-coverage.json
- Validation: cd swissknife && node scripts/capture-ipfs-mcp-service-evidence.cjs && node scripts/capture-ipfs-mcp-all-tools-ledger.cjs && npx jest test/mcp-plus-plus/all-tools-release-policy-gates.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: The configured SwissKnife `ipfs_accelerate_py` MCP endpoint exposes the adapter-required accelerate tools through a normalized MCP/MCP++ list/call shape, or the release gate records an explicit tool-by-tool non-app disposition. SVD-036 must no longer fail `accelerate_adapter_boundary` for app-routable methods.

## SVD-045 Add all-app ORB/IDL handoff packet fixtures

- Status: waiting
- Priority: P0
- Track: orb-idl
- Depends on: SVD-034, SVD-035, SVD-042, SVD-044
- Outputs: swissknife/test/mcp-plus-plus/all-tools-glasses-handoff-packets.test.ts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-glasses-handoff-packets.json
- Validation: cd swissknife && npx jest test/mcp-plus-plus/all-tools-glasses-handoff-packets.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Every capability-matrix app row has a deterministic ORB/IDL handoff packet or explicit non-displayable disposition for Meta glasses layers, with app ID, interface CID, method refs, policy tags, receipt refs, fallback target, and replay-state linkage.

## SVD-046 Ingest physical Meta glasses evidence when hardware is available

- Status: blocked
- Priority: P2
- Track: device
- Depends on: SVD-039, SVD-045
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/physical-all-tools-glasses-validation.md, docs/meta-glasses-expanded-io-physical-validation-checklist.md
- Validation: rg -n "paired physical|native DAT|display-webapp|mobile-card|audio-summary|firmware|receipt" swissknife/test-results/virtual-desktop-ipfs-mcp-orb/physical-all-tools-glasses-validation.md docs/meta-glasses-expanded-io-physical-validation-checklist.md
- Acceptance: Real paired Meta glasses evidence is attached for native DAT display, Display Web App, mobile-card fallback, audio-summary/Bluetooth routing, rollback, firmware/app versions, package credentials, operator-visible fallback decisions, and receipts. This task remains blocked without physical hardware.

## SVD-047 Re-run the all-tools release closeout after adapter and device evidence

- Status: waiting
- Priority: P0
- Track: release
- Depends on: SVD-044, SVD-045, SVD-046
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/release-evidence.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-release-evidence.md, data/swissknife_virtual_desktop/discovery/all-tools-no-new-unknowns.md
- Validation: cd swissknife && node scripts/build-all-tools-capability-matrix.cjs && node scripts/build-virtual-desktop-release-evidence.cjs && rg -n "Decision: \\*\\*GO\\*\\*|Decision: \\*\\*NO-GO\\*\\*|Blockers" test-results/virtual-desktop-ipfs-mcp-orb/all-tools-release-evidence.md
- Acceptance: Release evidence is regenerated after SVD-044 through SVD-046. A `go` decision is allowed only if the representative app gate, exhaustive all-tools gate, accelerate adapter boundary, and physical Meta glasses evidence are all satisfied; otherwise the report must carry explicit blockers and no new unknown task class.

## Agent Supervisor Phase Three 2026-07-08

This phase records the current checkout recovery work needed to keep the
all-tools program runnable by the `ipfs_accelerate_py` agent supervisor. The
phase does not weaken the release gate: configured `ipfs_kit_py` and
`ipfs_datasets_py` are currently live, the configured `ipfs_accelerate_py`
compatibility endpoint is live, and the real local `ipfs_accelerate_py` service
exposes a larger tool surface, but the configured SwissKnife adapter still must
normalize the required accelerate tool aliases before SVD-044 can be completed.

## SVD-048 Restore current-checkout all-tools evidence scripts

- Status: completed
- Priority: P0
- Track: supervisor
- Depends on: SVD-041, SVD-042, SVD-043
- Outputs: swissknife/scripts/all-tools-evidence-lib.cjs, swissknife/scripts/capture-ipfs-mcp-service-evidence.cjs, swissknife/scripts/capture-ipfs-mcp-all-tools-ledger.cjs, swissknife/scripts/capture-ipfs-accelerate-adapter-coverage.cjs, swissknife/scripts/build-all-tools-capability-matrix.cjs, swissknife/scripts/build-virtual-desktop-release-evidence.cjs, swissknife/scripts/validate-virtual-desktop-manifest.cjs, swissknife/scripts/start-ipfs-accelerate-mcp-compat.cjs
- Validation: cd swissknife && node --check scripts/all-tools-evidence-lib.cjs && node --check scripts/capture-ipfs-mcp-service-evidence.cjs && node --check scripts/capture-ipfs-mcp-all-tools-ledger.cjs && node --check scripts/capture-ipfs-accelerate-adapter-coverage.cjs && node --check scripts/build-all-tools-capability-matrix.cjs && node --check scripts/build-virtual-desktop-release-evidence.cjs && node --check scripts/validate-virtual-desktop-manifest.cjs && node --check scripts/start-ipfs-accelerate-mcp-compat.cjs
- Acceptance: The current checkout contains the source scripts required to regenerate service health, descriptor discovery, all-tools ledger, adapter coverage, capability matrix, manifest drift, and release evidence without relying on deleted generated source from an older supervisor run.
- Completion note 2026-07-08: Restored the all-tools evidence library and script entrypoints in `swissknife/scripts/`. Validation passed with `node --check` across all restored scripts.

## SVD-049 Capture current live MCP/MCP++ service and adapter evidence

- Status: completed
- Priority: P0
- Track: ops
- Depends on: SVD-031, SVD-048
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/service-health.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/descriptor-discovery.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-ledger.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ipfs-accelerate-adapter-coverage.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/release-evidence.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-release-evidence.md
- Validation: cd swissknife && node scripts/capture-ipfs-accelerate-adapter-coverage.cjs && node scripts/capture-ipfs-mcp-service-evidence.cjs && node scripts/capture-ipfs-mcp-all-tools-ledger.cjs && node scripts/validate-virtual-desktop-manifest.cjs && node scripts/build-all-tools-capability-matrix.cjs && node scripts/build-virtual-desktop-release-evidence.cjs
- Acceptance: Evidence records current live configured tool counts for `ipfs_kit_py`, `ipfs_datasets_py`, and the configured `ipfs_accelerate_py` adapter, records the real local `ipfs_accelerate_py` tool surface separately, and leaves release `NO-GO` until configured accelerate adapter parity is proven.
- Completion note 2026-07-08: Captured live evidence. Configured services are available: `ipfs_kit_py` on `127.0.0.1:8014` with 91 tools, `ipfs_datasets_py` on `127.0.0.1:3002` with 340 tools, and configured `ipfs_accelerate_py` on `127.0.0.1:3003` with 3 compatibility tools. The real local `ipfs_accelerate_py` endpoint on `127.0.0.1:9000` exposes 108 tools but does not expose the configured JSON-RPC `/mcp` shape. The regenerated all-tools ledger has 586 records, the capability matrix has 38 current app rows, 120 ORB/IDL descriptors, and 120 Meta glasses projections. Release evidence remains `NO-GO` with the accelerate adapter boundary blocker.

## SVD-050 Resume SVD-044 with the restored adapter source and redeploy the configured accelerate endpoint

- Status: waiting
- Priority: P0
- Track: ops
- Depends on: SVD-044, SVD-049
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ipfs-accelerate-adapter-coverage.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-policy-release-gate.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/release-evidence.json
- Validation: cd swissknife && node scripts/capture-ipfs-accelerate-adapter-coverage.cjs && node scripts/capture-ipfs-mcp-service-evidence.cjs && node scripts/capture-ipfs-mcp-all-tools-ledger.cjs && npx jest test/mcp-plus-plus/all-tools-release-policy-gates.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: The configured `127.0.0.1:3003` adapter process is restarted or replaced from the restored `scripts/start-ipfs-accelerate-mcp-compat.cjs` source, exposes all required accelerate aliases through JSON-RPC `tools/list` and `tools/call`, and clears the `accelerate_adapter_boundary` release blocker without hiding missing upstream behavior.
