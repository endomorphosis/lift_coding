# Swissknife Meta Glasses Display Widgets Plan

## Status

Comprehensive improvement plan for making HandsFree compatible with Meta Ray-Ban Display-style glasses by using the local `swissknife` package as the descriptor, generation, and Object Request Broker layer for arbitrary display widgets.

Created: 2026-05-22

## Goal

Enable a developer or agent to define a Meta glasses display widget as a Swissknife MCP-IDL/UI descriptor, publish it through a descriptor registry, bind it through the Swissknife ORB, and render it on display-capable Meta glasses through the existing HandsFree mobile DAT bridge.

Target workflow:

1. Author a widget descriptor in Swissknife's MCP-IDL + UI profile format.
2. Validate the descriptor against display-safe widget rules.
3. Generate a compact glasses widget manifest and preview surface.
4. Publish the descriptor to a local or remote Swissknife interface registry.
5. Let the ORB discover, bind, authorize, invoke, stream, and recover widget operations.
6. Route render/update/clear/video commands through HandsFree backend and the mobile DAT bridge.
7. Validate on simulator, webapp readiness checks, Android DisplayAccess-style sample flow, and physical glasses.

## Current Baseline

### HandsFree

- Display bridge scaffolding exists under `mobile/modules/expo-meta-wearables-dat`.
- JS wrappers already expose `renderDisplayTest`, `clearDisplay`, `playDisplayVideo`, and `resetDisplaySession` through `mobile/src/native/wearablesBridge.js`, `mobile/src/native/metaWearablesDat.js`, and `mobile/src/hooks/useMetaWearablesDat.js`.
- Mobile local action execution already routes display actions in `mobile/src/utils/agentActions.js`.
- Backend follow-up actions already include display lifecycle actions in `src/handsfree/agent_providers.py`.
- Display webapp readiness checks already exist in `src/handsfree/display_webapp_compat.py`, `scripts/lint_display_webapp_readiness.py`, and `config/display_webapp_readiness.example.json`.
- Existing display docs capture DAT 0.7 baseline and physical rollout gates:
  - `docs/meta-wearables-dat-display-integration.md`
  - `docs/meta-wearables-dat-display-physical-validation-checklist.md`
  - `docs/meta-wearables-dat-display-rollout-evidence-template.md`

### Swissknife

- MCP-IDL descriptor primitives exist in `swissknife/src/services/mcp-idl.ts`.
- Swissknife UI profile descriptor model exists in `swissknife/src/services/mcp-ui-profile.ts`.
- Descriptor registry and launch discovery exist in `swissknife/src/services/mcp-interface-registry.ts`.
- Schema-driven UI generation exists in `swissknife/src/services/mcp-schema-ui-generator.ts`.
- ORB capability routing exists in `swissknife/src/services/mcp-orb-capability-router.ts`.
- Descriptor fixtures and tests exist under `swissknife/test/mcp-plus-plus`.
- Current Swissknife templates target desktop apps, not constrained wearable display widgets.

### Meta Display Direction

Meta's May 14, 2026 display developer announcement describes two developer-preview paths for Meta Ray-Ban Display: extending iOS/Android apps and building Web Apps. The Android `DisplayAccess` sample in the public DAT repo demonstrates the lifecycle shape this repo should target: connect to a display-capable device, start a device session, attach the display capability, wait for readiness, then render content.

### Source Alignment and Version Guardrails

Recorded by MGW-001 on 2026-05-22:

- Swissknife source baseline is `swissknife@0.0.53`, commit `5b4598e15709203c0fe2265fdab2f51ea822b0f2`, from the local checkout at `/home/barberb/lift_coding/swissknife`.
- Meta DAT Android display planning uses `samples/DisplayAccess` from `/home/barberb/lift_coding/external/meta-wearables-dat-android`, commit `25f3a6d4479b7a4a72f877977b865a11af990d04`.
- Meta DAT iOS display planning uses `samples/DisplayAccess` from `/home/barberb/lift_coding/external/meta-wearables-dat-ios`, commit `a739e94181221e7f321304273bcda2272821b163`.
- Meta display APIs are developer preview surfaces and may require release-channel access, organization enablement, app-model metadata, entitlements, or SDK/package access that is not available in every build environment.
- Android `mwdat-display` remains optional. Default and CI-safe builds must not require Meta package credentials; native display code only links or runs when package access and runtime capability checks both succeed.
- Every widget descriptor, compiler output, ORB handler, backend action, and mobile bridge operation must include a native-display-unavailable fallback. If DAT native display is unavailable, return a structured `display unavailable` result and route to a display-webapp preview, simulator preview, mobile card, notification, or audio-first summary.

## Non-Goals

- Do not expose raw Swissknife or MCP++ terminology to end users in the mobile UI.
- Do not let mobile bypass the HandsFree backend policy boundary for agent-generated widgets.
- Do not treat arbitrary HTML/CSS as automatically safe for the glasses display.
- Do not make Meta DAT package artifacts mandatory for default app builds until package and release-channel access is stable.
- Do not replace the existing audio-first Meta glasses flow.

## Target Architecture

```text
Agent / developer prompt
        |
        v
Swissknife widget descriptor authoring
        |
        v
MCP-IDL + glasses UI profile validator
        |
        v
Descriptor registry publishes interface CID
        |
        v
Swissknife ORB discovers and binds widget operations
        |
        v
HandsFree backend action contract and policy checks
        |
        v
Mobile bridge command: render / update / clear / video / reset
        |
        v
Meta DAT display session or webapp display path
        |
        v
Physical glasses display
```

## Descriptor Model

Add a glasses-specific extension to Swissknife's existing `MCPUIProfileDescriptor`. The MCP-IDL method list remains the canonical operation contract. The new display profile should only add display constraints and widget layout metadata.

Proposed descriptor shape:

```ts
interface MetaGlassesDisplayProfile {
  profile: 'handsfree.meta-glasses/display-widget';
  profile_version: '0.1.0';
  target: {
    display_class: 'meta-ray-ban-display';
    viewport: { width: 600; height: 600 };
    input: Array<'dpad' | 'gesture' | 'voice' | 'mobile_action'>;
    render_path: 'dat-native' | 'display-webapp' | 'simulator';
  };
  layout: {
    template:
      | 'single-card'
      | 'stack'
      | 'list'
      | 'status'
      | 'progress'
      | 'media'
      | 'confirmation'
      | 'freeform-grid';
    regions: MetaGlassesDisplayRegion[];
  };
  constraints: {
    max_text_blocks: number;
    max_actions: number;
    requires_high_contrast: boolean;
    requires_focus_order: boolean;
    max_update_hz: number;
    ttl_ms?: number;
  };
  fallback: {
    when: Array<'dat_native_display_unavailable' | 'display_unsupported' | 'session_not_ready'>;
    render_path: 'display-webapp' | 'simulator' | 'mobile-card' | 'notification' | 'audio-summary';
    message: string;
  };
}
```

Required widget operations:

- `render_widget`: create or replace the active display widget.
- `update_widget`: patch state without rebuilding the session.
- `clear_widget`: remove active content.
- `focus_next` and `focus_previous`: deterministic D-pad/focus navigation.
- `activate`: invoke the selected action.
- `reset_session`: recover from stale display state.
- `play_video`: optional operation for video-capable descriptors.
- `subscribe_updates`: optional stream for progress, telemetry, task status, or countdown widgets.

## Widget Safety Contract

Every generated widget must pass these checks before the backend can emit a mobile render action:

- Viewport is fixed to the display target advertised by the descriptor, initially `600x600`.
- Text fits within bounded regions and declares overflow behavior.
- Focusable controls have a stable order and no unreachable action.
- Color tokens pass high-contrast requirements.
- Motion and streaming updates have a maximum update frequency.
- Media operations declare type, duration, size, transport, and fallback content.
- All actions map to backend-approved local or remote action IDs.
- Descriptor publish requires provenance metadata and a trust policy decision.
- ORB invocation requires correlation ID, receipt, policy outcome, and lifecycle record.
- A native-display-unavailable fallback is required before publish; DAT native display unavailable must be treated as a normal fallback state, not a renderer crash.

## Implementation Todo List

### Daemon Processing

The checklist below is also mirrored as an ipfs_datasets_py implementation-daemon task board:

- `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md`

Use these repository-local wrappers so the daemon, supervisor, and llm_router run with the correct task prefix, state directory, and `external/ipfs_datasets` import path:

```bash
python3 scripts/meta_glasses_display_todo_daemon.py --once
python3 scripts/meta_glasses_display_todo_supervisor.py --once
python3 scripts/meta_glasses_display_llm_router.py --task-id MGW-001
```

The daemon-facing task IDs use the `MGW-*` prefix. The llm_router wrapper defaults to a dry-run preflight and only calls `llm_router.generate_text` when `--generate` is passed.

The machine-readable board includes `MGW-013`, a final discovery-expansion task. Once the initial implementation tasks are complete, the supervisor should run that task to inspect the resulting codebase and append additional daemon-parseable `MGW-*` tasks for gaps discovered during implementation. If no new work is found, the task must record a dated no-new-unknowns report with the evidence and commands used.

The first discovered operational follow-up is `MGW-014`: Android validation must run with the repo-local JDK 17/Android SDK environment, and repeated validation failures should become evidence-backed backlog items instead of an indefinite retry loop.

### Phase 0: Source Alignment and Version Guardrails

- [ ] Record the current checked-out Swissknife commit or package version in `implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md`.
- [ ] Record the current Meta DAT Android/iOS sample revisions used for display planning.
- [ ] Add a compatibility note that Meta display APIs are developer preview and may require release-channel or organization enablement.
- [ ] Add an explicit "DAT native display unavailable" fallback path to every widget plan.
- [ ] Keep `mwdat-display` optional until package access is confirmed in the target release channel.

MGW-001 recorded these guardrails in this document and in `implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md`. Keep the checklist open for the backlog daemon; future tasks should update the dated guardrail block when any source pin, release-channel requirement, or packaging rule changes.

### Phase 1: Swissknife Glasses Display Profile

- [ ] Add `swissknife/src/services/meta-glasses-display-profile.ts`.
- [ ] Define `MetaGlassesDisplayProfile`, `MetaGlassesWidgetDescriptor`, `MetaGlassesDisplayRegion`, `MetaGlassesActionBinding`, and `MetaGlassesRenderTarget`.
- [ ] Extend or wrap `MCPUIProfileDescriptor` without breaking existing desktop UI descriptors.
- [ ] Add validator errors with stable codes for:
  - missing viewport
  - unsupported render path
  - missing focus order
  - unbounded text
  - unsupported media type
  - action not bound to a method
  - method not present in MCP-IDL `methods`
  - unsafe update rate
  - missing clear/reset operation
- [ ] Add Jest tests under `swissknife/test/mcp-plus-plus/meta-glasses-display-profile.test.ts`.
- [ ] Add descriptor examples for `status`, `task-progress`, `confirmation`, `notification-summary`, and `video-preview` widgets.

Exit criteria:

- A descriptor can be validated as both a normal Swissknife MCP UI profile and a glasses display widget profile.
- Invalid display widgets fail before registry publish.

### Phase 2: Widget Schema and Compiler

- [ ] Add `swissknife/src/services/meta-glasses-widget-compiler.ts`.
- [ ] Compile descriptor + state into a compact widget manifest:
  - `widget_id`
  - `interface_cid`
  - `operation`
  - `viewport`
  - `regions`
  - `focus_order`
  - `actions`
  - `media`
  - `state`
  - `ttl_ms`
  - `fallback`
- [ ] Generate deterministic widget CIDs using Swissknife `computeCID`.
- [ ] Add JSON Schema for the compiled manifest.
- [ ] Add text fitting and region collision checks.
- [ ] Add renderer hints for native DAT and display-webapp targets.
- [ ] Add snapshot tests for compiled manifests.

Exit criteria:

- A valid descriptor compiles to a deterministic, display-safe manifest.
- The compiler rejects widgets that cannot fit or cannot be navigated.

### Phase 3: ORB Widget Runtime

- [ ] Add an ORB local adapter handler set for widget operations:
  - `render_widget`
  - `update_widget`
  - `clear_widget`
  - `focus_next`
  - `focus_previous`
  - `activate`
  - `reset_session`
  - `play_video`
  - `subscribe_updates`
- [ ] Add a `MetaGlassesDisplayORBAdapter` wrapper that converts ORB invocation results into HandsFree mobile action payloads.
- [ ] Add operation policies for:
  - user confirmation for destructive actions
  - rate limits for streaming updates
  - idempotency for render/update calls
  - circuit breaker for repeated display bridge failures
  - timeout and retry for stale sessions
- [ ] Persist ORB receipts and widget manifest CIDs in backend task metadata.
- [ ] Add stream recovery tests for progress/status widgets.

Exit criteria:

- ORB lifecycle records show discover, bind, authorize, invoke, stream, and recover for widget operations.
- Denied operations are visible to generated UI and do not reach the mobile bridge.

### Phase 4: HandsFree Backend Contract

- [ ] Add backend models for display widget actions:
  - `mobile_render_display_widget`
  - `mobile_update_display_widget`
  - `mobile_clear_display_widget`
  - `mobile_focus_display_widget`
  - `mobile_activate_display_widget_action`
  - `mobile_reset_display_widget_session`
- [ ] Add OpenAPI examples for widget action payloads and receipts.
- [ ] Extend `src/handsfree/agent_providers.py` to emit widget follow-up actions when descriptors are display-compatible.
- [ ] Add backend validation for compiled widget manifests before sending them to mobile.
- [ ] Add storage for widget descriptors, CIDs, latest manifest, active session ID, and last bridge response.
- [ ] Add audit records linking prompt, descriptor CID, ORB receipt CID, and display render result.
- [ ] Add tests for action serialization, policy rejection, and notification/card rendering.

Exit criteria:

- Backend can receive a compiled Swissknife widget manifest and emit a mobile-local display action without provider-specific UI branches.
- Mobile card builders can render widget action state from normalized backend envelopes.

### Phase 5: Mobile Bridge and Native Display Runtime

- [ ] Add JS wrapper methods to `mobile/src/native/wearablesBridge.js`:
  - `renderDisplayWidget(manifest)`
  - `updateDisplayWidget(patch)`
  - `clearDisplayWidget(widgetId?)`
  - `focusDisplayWidget(direction)`
  - `activateDisplayWidgetAction(actionId)`
  - `resetDisplayWidgetSession()`
- [ ] Keep existing `renderDisplayTest`, `clearDisplay`, `playDisplayVideo`, and `resetDisplaySession` as compatibility shims.
- [ ] Extend `mobile/modules/expo-meta-wearables-dat/index.ts` types for widget manifests and display bridge responses.
- [ ] Implement native Android DAT display path by following the DisplayAccess pattern:
  - select display-capable device
  - start session
  - attach display capability
  - wait until ready
  - render guided/native content
  - handle firmware/app update required states
- [ ] Implement iOS path when equivalent display APIs are available; otherwise return structured unsupported responses with fallback webapp preview metadata.
- [ ] Add bridge events for `display_widget_rendered`, `display_widget_updated`, `display_widget_cleared`, `display_widget_action`, `display_widget_error`, and `display_widget_session_reset`.
- [ ] Add diagnostics rows for active widget ID, descriptor CID, manifest CID, render path, focus target, update count, and last error.

Exit criteria:

- Mobile can execute widget actions in bridge-reference mode without crashing.
- Android can render a simple widget through real DAT display APIs when SDK linkage and hardware are available.
- iOS emits explicit capability status until native display APIs are wired.

### Phase 6: Display Webapp Fallback

- [ ] Add a generated webapp renderer for compiled widget manifests.
- [ ] Reuse `src/handsfree/display_webapp_compat.py` readiness checks for every webapp-target widget.
- [ ] Add constraints for HTTPS deployment, focus navigation, dark theme, and contrast.
- [ ] Add a local preview page for desktop/mobile development.
- [ ] Add a hosted deployment metadata descriptor for staged rollout.
- [ ] Add tests that the generated webapp has no unsupported viewport, navigation, or contrast violations.

Exit criteria:

- Every widget can render in a browser preview.
- Webapp-target widgets pass the existing readiness linter before release evidence is generated.

### Phase 7: Arbitrary Widget Authoring UX

- [ ] Add a Swissknife CLI command:
  - `swissknife meta-glasses widget init`
  - `swissknife meta-glasses widget lint`
  - `swissknife meta-glasses widget compile`
  - `swissknife meta-glasses widget preview`
  - `swissknife meta-glasses widget publish`
  - `swissknife meta-glasses widget invoke`
- [ ] Add prompt-to-widget generation that emits descriptor JSON, not raw native code.
- [ ] Add a small widget gallery:
  - task progress
  - inbox summary
  - confirmation prompt
  - timer/countdown
  - navigation/status
  - video card
  - checklist
  - metric dashboard
- [ ] Add generated documentation per widget with operation contracts and validation results.
- [ ] Add a "why rejected" explainer for failed safety checks.

Exit criteria:

- A developer can author a new display widget without editing mobile native code.
- Agent-generated widgets are constrained by descriptor validation and backend policy.

### Phase 8: Testing and Verification

- [ ] Build comprehensive hardware-free mocks, fixtures, and simulators before relying on physical glasses:
  - Swissknife descriptor fixtures for valid and invalid widget profiles.
  - Compiled widget manifest fixtures for each supported template.
  - ORB mock transport adapters for success, denial, retry, timeout, stale handle, stream recovery, and bridge failure paths.
  - Backend fixture envelopes that include descriptor CID, widget CID, ORB receipt CID, policy decision, and mobile action payload.
  - Mobile native-module mocks for DAT unavailable, DAT disabled, display unsupported, display ready, render success, render failure, update success, clear success, and session reset.
  - Android fake DisplayAccess-style lifecycle fixtures for device discovery, selected target, session start, display attach, display ready, firmware update required, app update required, and disconnect.
  - iOS fake capability fixtures that distinguish unsupported, webapp fallback, and future native display support.
  - Golden JSON fixtures for every backend-to-mobile widget action payload.
  - Browser preview fixtures for `600x600` render snapshots and focus navigation.
- [ ] Add a hardware-free display harness that can run a complete widget lifecycle:
  - publish descriptor
  - compile manifest
  - ORB discover/bind/invoke
  - backend action serialization
  - mobile local action execution
  - mocked bridge render/update/clear response
  - receipt and diagnostics state update
- [ ] Add CI jobs that run the hardware-free suite without Meta credentials, DAT package access, or paired glasses.
- [ ] Add fixture versioning rules so changes to descriptor schema, manifest schema, or bridge payloads require explicit snapshot updates.
- [ ] Add negative tests for unsafe agent-generated widgets:
  - oversized text
  - overlapping regions
  - missing focus order
  - unsupported media
  - untrusted descriptor
  - unknown action ID
  - excessive stream update rate
  - missing clear/reset operation
- [ ] Swissknife unit tests:
  - descriptor validation
  - compiler determinism
  - ORB binding/invocation
  - policy denials
  - stream recovery
- [ ] HandsFree backend tests:
  - manifest validation
  - action serialization
  - card and notification rendering
  - policy rejection
  - receipt persistence
- [ ] Mobile JS tests:
  - bridge wrapper fallback behavior
  - local action handling
  - diagnostics state merge
  - event handling
- [ ] Android tests:
  - bridge-only build with DAT disabled
  - DAT-enabled build when credentials are present
  - MockDeviceKit or sample-compatible display session where available
- [ ] Physical validation:
  - run `docs/meta-wearables-dat-display-physical-validation-checklist.md`
  - record evidence in `docs/meta-wearables-dat-display-rollout-evidence-template.md`

Exit criteria:

- CI can validate descriptor and fallback paths without Meta credentials.
- A full descriptor-to-mobile-render lifecycle can be tested on a developer laptop without display-capable glasses.
- Every native DAT/display branch has a deterministic mock fixture and at least one regression test.
- Hardware validation gates real DAT display rendering before release.

### Phase 9: Release and Rollout

- [ ] Add feature flags:
  - `HANDSFREE_DISPLAY_WIDGETS_ENABLED`
  - `HANDSFREE_DISPLAY_WIDGETS_REQUIRE_TRUSTED_DESCRIPTOR`
  - `HANDSFREE_DISPLAY_WIDGETS_ALLOW_WEBAPP_FALLBACK`
  - `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_ANDROID`
  - `HANDSFREE_DISPLAY_WIDGETS_NATIVE_DAT_IOS`
- [ ] Add staged rollout checklist for internal, test organization, and production channels.
- [ ] Add failure-mode guidance for unsupported glasses, stale sessions, missing release-channel access, missing DAT packages, and failed descriptor validation.
- [ ] Add observability dashboards for render success rate, bridge errors, policy denials, and widget update latency.
- [ ] Add privacy review notes for descriptor provenance, user prompts, display content retention, and analytics opt-out settings.

Exit criteria:

- Widget rendering can be enabled per environment and rolled back without app-store/native code changes.
- Operators can diagnose display compatibility from backend, mobile diagnostics, and rollout evidence.

## Priority Backlog

P0:

- [ ] Define and validate `MetaGlassesDisplayProfile`.
- [ ] Build deterministic widget compiler.
- [ ] Add ORB widget handlers and policies.
- [ ] Add backend action payload contract.
- [ ] Add mobile bridge wrapper methods with structured unsupported fallback.
- [ ] Add first `task-progress` and `confirmation` widget fixtures.
- [ ] Add hardware-free mocks and golden fixtures for descriptor, ORB, backend action, mobile action, and DAT bridge states.

P1:

- [ ] Add Android native DAT display rendering path.
- [ ] Add webapp fallback renderer and linter integration.
- [ ] Add Swissknife CLI commands for lint/compile/preview/publish.
- [ ] Add stream update and recovery for progress widgets.
- [ ] Add persistence for descriptor CID, widget CID, and ORB receipt CID.
- [ ] Add a full descriptor-to-mobile-render test harness that runs without paired glasses.

P2:

- [ ] Add prompt-to-widget generation.
- [ ] Add widget gallery and preview UI.
- [ ] Add visual regression tests for 600x600 display previews.
- [ ] Add physical-device evidence automation.
- [ ] Add iOS native display path once SDK APIs are available and linked.

## First Vertical Slice

The first slice should be intentionally narrow:

1. Swissknife descriptor: `handsfree.task-progress-widget`.
2. Operations: `render_widget`, `update_widget`, `clear_widget`, `subscribe_updates`.
3. Layout: `status` template with title, short summary, progress bar, and one action.
4. Render path: simulator + mobile bridge fallback.
5. Backend action: `mobile_render_display_widget`.
6. Mobile action: call `renderDisplayWidget(manifest)`, falling back to `renderDisplayTest()` if the native method is missing and to the descriptor fallback when DAT native display is unavailable.
7. Hardware-free fixtures: mocked descriptor registry, ORB local adapter, backend envelope, mobile action executor, and DAT bridge response.
8. Tests: descriptor validation, manifest compile, ORB local invocation, backend action serialization, mobile fallback wrapper, and mocked bridge lifecycle.

Done means an agent can generate a task-progress widget descriptor, the compiler produces a manifest, ORB invokes it, backend emits a local mobile display action, and mobile returns a structured bridge response.

## Open Questions

- Which Meta display API surface should be the production renderer for non-video native widgets on Android: a native layout tree, a declarative DAT content model, or a webapp URL?
- Does iOS expose the same display capability lifecycle as Android in the target SDK version, or should iOS remain webapp/fallback first?
- What minimum trust policy should apply to agent-generated descriptors before they can reach a physical display?
- Should display widgets be stored as task-scoped artifacts only, or should trusted descriptors be reusable app-level capabilities?
- What maximum text length and update frequency should be enforced for voice-first development workflows?

## Source References

- Meta display developer announcement, May 14, 2026: https://developers.meta.com/blog/build-for-display-glasses/
- Meta Wearables DAT Android repository: https://github.com/facebook/meta-wearables-dat-android
- Meta Wearables DAT Android DisplayAccess sample: https://github.com/facebook/meta-wearables-dat-android/tree/main/samples/DisplayAccess
- Meta Wearables DAT iOS repository: https://github.com/facebook/meta-wearables-dat-ios
- Existing HandsFree display baseline: `docs/meta-wearables-dat-display-integration.md`
- Existing Swissknife MCP++ UI plan: `swissknife/docs/mcp-plus-plus/IMPLEMENTATION_PLAN_TODO_QUEUE.md`
