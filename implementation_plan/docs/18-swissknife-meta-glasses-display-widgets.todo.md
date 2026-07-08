# Swissknife Meta Glasses Display Widgets Todo Board

This is the machine-readable backlog for the ipfs_datasets_py todo supervisor/daemon.
It operationalizes `implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md`.

Run from the repository root:

```bash
python3 scripts/meta_glasses_display_todo_daemon.py --once
python3 scripts/meta_glasses_display_todo_supervisor.py --once
python3 scripts/meta_glasses_display_llm_router.py --task-id MGW-001
```

To allow autonomous implementation in isolated worktrees, pass `--implement` to the supervisor or daemon and provide an implementation command if the default Codex/Copilot fallback is not desired.

## MGW-000 Bootstrap supervised display-widget backlog processing

- Status: completed
- Completion: manual
- Priority: P0
- Track: ops
- Depends on:
- Outputs: implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md, scripts/meta_glasses_display_todo_daemon.py, scripts/meta_glasses_display_todo_supervisor.py, scripts/meta_glasses_display_llm_router.py, tests/test_meta_glasses_display_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_datasets python3 scripts/meta_glasses_display_todo_daemon.py --once; PYTHONPATH=external/ipfs_datasets python3 scripts/meta_glasses_display_todo_supervisor.py --once; PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py
- Acceptance: The display-widget roadmap is available as a daemon-parseable MGW task board with wrapper scripts and parser tests.

## MGW-001 Record source alignment and version guardrails

- Status: completed
- Completion: manual
- Priority: P0
- Track: ops
- Depends on: MGW-000
- Outputs: implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Validation: rg -n "Swissknife|Meta DAT|developer preview|mwdat-display|display unavailable" implementation_plan/docs/15-meta-wearables-dat-mcpplusplus-integration-roadmap.md implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Acceptance: The roadmap records the Swissknife version/commit, Meta DAT sample revisions, developer-preview caveats, optional mwdat-display packaging, and a native-display-unavailable fallback.

## MGW-002 Define the Swissknife glasses display profile

- Status: completed
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: MGW-001
- Outputs: swissknife/src/services/meta-glasses-display-profile.ts, swissknife/test/mcp-plus-plus/meta-glasses-display-profile.test.ts
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-display-profile.ts src/services/mcp-ui-profile.ts src/services/mcp-idl.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-display-profile.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: A descriptor validates as both a Swissknife MCP UI profile and a Meta glasses display widget profile, with stable validation error codes for unsafe display contracts.

## MGW-003 Build descriptor, native, and lifecycle fixture foundations

- Status: completed
- Completion: manual
- Priority: P0
- Track: quality
- Depends on: MGW-002
- Outputs: swissknife/test/fixtures/meta-glasses-display/valid-task-progress-widget.json, swissknife/test/fixtures/meta-glasses-display/invalid-widget-cases.json, mobile/src/native/__fixtures__/metaWearablesDisplayStates.js
- Validation: cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-display-profile.test.ts --config=config/jest/jest.config.cjs --runInBand; cd mobile && npm test -- --runInBand src/native/__tests__/wearablesBridge.test.js
- Acceptance: Hardware-free fixtures cover valid and invalid descriptors, DAT unavailable/disabled/unsupported/ready states, Android DisplayAccess-style lifecycle states, and iOS fallback states.

## MGW-004 Implement deterministic widget schema and compiler

- Status: completed
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: MGW-002, MGW-003
- Outputs: swissknife/src/services/meta-glasses-widget-compiler.ts, swissknife/test/mcp-plus-plus/meta-glasses-widget-compiler.test.ts
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-display-profile.ts src/services/meta-glasses-widget-compiler.ts src/services/mcp-idl.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-widget-compiler.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Valid widget descriptors compile to deterministic manifests with widget CIDs, viewport, regions, focus order, actions, media, state, TTL, and fallback metadata; unsafe layouts are rejected.

## MGW-005 Add ORB widget runtime and policy handling

- Status: completed
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: MGW-004
- Outputs: swissknife/src/services/meta-glasses-display-orb-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-display-orb-adapter.test.ts
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-display-orb-adapter.ts src/services/mcp-orb-capability-router.ts src/services/meta-glasses-widget-compiler.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-display-orb-adapter.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: ORB handlers cover render/update/clear/focus/activate/reset/video/stream operations with receipts, policy denials, idempotency, rate limits, retry, circuit breaker behavior, and stream recovery tests.

## MGW-006 Add HandsFree backend widget action contract

- Status: completed
- Completion: manual
- Priority: P0
- Track: backend
- Depends on: MGW-004
- Outputs: src/handsfree/models.py, src/handsfree/agent_providers.py, spec/openapi.yaml, tests/test_meta_glasses_display_widget_actions.py
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_display_widget_actions.py tests/test_api_contract.py
- Acceptance: Backend models and OpenAPI examples support display widget render/update/clear/focus/activate/reset actions with descriptor CID, widget CID, ORB receipt CID, policy decision, and mobile action payloads.

## MGW-007 Add mobile bridge widget methods and mocked fallback states

- Status: completed
- Completion: manual
- Priority: P0
- Track: mobile
- Depends on: MGW-003, MGW-006
- Outputs: mobile/src/native/wearablesBridge.js, mobile/src/native/metaWearablesDat.js, mobile/src/hooks/useMetaWearablesDat.js, mobile/src/utils/agentActions.js, mobile/src/native/__tests__/wearablesBridge.test.js, mobile/src/utils/__tests__/agentActions.test.js
- Validation: cd mobile && npm test -- --runInBand src/native/__tests__/wearablesBridge.test.js src/native/__tests__/metaWearablesDat.test.js src/utils/__tests__/agentActions.test.js
- Acceptance: Mobile exposes renderDisplayWidget/updateDisplayWidget/clearDisplayWidget/focusDisplayWidget/activateDisplayWidgetAction/resetDisplayWidgetSession and returns structured unsupported responses when native DAT display is unavailable.

## MGW-008 Build full hardware-free descriptor-to-mobile-render harness

- Status: completed
- Completion: manual
- Priority: P0
- Track: quality
- Depends on: MGW-005, MGW-006, MGW-007
- Outputs: tests/test_meta_glasses_display_widget_harness.py, mobile/src/utils/__tests__/displayWidgetHarness.test.js, swissknife/test/mcp-plus-plus/meta-glasses-display-harness.test.ts
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_display_widget_harness.py; cd mobile && npm test -- --runInBand src/utils/__tests__/displayWidgetHarness.test.js; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-display-harness.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: A complete lifecycle can run without hardware: publish descriptor, compile manifest, ORB discover/bind/invoke, backend serialize action, mobile execute action, mocked bridge render/update/clear, and receipt/diagnostics update.

## MGW-009 Add display webapp fallback renderer and readiness gates

- Status: completed
- Completion: manual
- Priority: P1
- Track: ui
- Depends on: MGW-004, MGW-006
- Outputs: swissknife/src/services/meta-glasses-webapp-renderer.ts, config/display_webapp_readiness.meta_glasses_widget.example.json, tests/test_display_webapp_widget_readiness.py
- Validation: PYTHONPATH=./src python3 scripts/lint_display_webapp_readiness.py config/display_webapp_readiness.meta_glasses_widget.example.json; PYTHONPATH=./src pytest tests/test_display_webapp_widget_readiness.py
- Acceptance: Every webapp-target widget can render in a browser preview and pass HTTPS, 600x600 viewport, focus navigation, dark theme, and contrast readiness checks before rollout.

## MGW-010 Add Android native DAT display renderer path

- Status: completed
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: MGW-007, MGW-008
- Outputs: mobile/modules/expo-meta-wearables-dat/android/src/main/java/expo/modules/metawearablesdat/ExpoMetaWearablesDatModule.kt, mobile/modules/expo-meta-wearables-dat/__tests__/index.test.js, docs/meta-wearables-dat-display-physical-validation-checklist.md
- Validation: cd mobile && npm ci && npm run android:validate:local
- Acceptance: Android follows the DisplayAccess lifecycle when DAT display SDK linkage is available, while the default bridge-only build still succeeds without Meta package credentials or paired glasses.

## MGW-011 Add Swissknife widget authoring CLI and gallery

- Status: completed
- Completion: manual
- Priority: P1
- Track: ui
- Depends on: MGW-004, MGW-005, MGW-008
- Outputs: swissknife/src/commands/meta-glasses-widget.ts, swissknife/test/mcp-plus-plus/meta-glasses-widget-cli.test.ts, swissknife/docs/meta-glasses-display-widgets.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/commands/meta-glasses-widget.ts src/services/meta-glasses-widget-compiler.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-widget-cli.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Developers can init, lint, compile, preview, publish, and invoke display widgets without editing mobile native code, and the gallery includes task progress, confirmation, summary, timer, media, checklist, and metric examples.

## MGW-012 Add rollout flags, observability, and physical evidence workflow

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: MGW-008, MGW-009, MGW-010
- Outputs: docs/meta-wearables-dat-display-rollout-evidence-template.md, docs/configuration-reference.md, src/handsfree/config.py, tests/test_meta_glasses_display_config.py
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_display_config.py; rg -n "HANDSFREE_DISPLAY_WIDGETS" docs src tests
- Acceptance: Display widget rendering is feature-flagged, observable, and rollback-safe, with documented rollout evidence, failure modes, privacy review notes, and metrics for render success, policy denials, bridge errors, and latency.

## MGW-013 Investigate implementation unknowns and expand the backlog

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on: MGW-001, MGW-002, MGW-003, MGW-004, MGW-005, MGW-006, MGW-007, MGW-008, MGW-009, MGW-010, MGW-011, MGW-012
- Outputs: implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; rg -n "MGW-013|unknown unknowns|Discovery Expansion|discovered" implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Acceptance: After the initial backlog completes, investigate the Swissknife, HandsFree backend, mobile DAT bridge, external Meta DAT references, and hardware-free test harness code paths for missed work. Append new daemon-parseable MGW tasks for discovered gaps, or write a dated no-new-unknowns discovery report with evidence and commands run. Discovery Expansion evidence is recorded in `data/meta_glasses_display_widgets/discovery/2026-05-22-mgw-013-discovery-expansion.md`.

## MGW-014 Add supervisor validation-environment and retry-budget guardrails

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-013
- Outputs: scripts/meta_glasses_display_todo_supervisor.py, scripts/meta_glasses_display_todo_daemon.py, tests/test_meta_glasses_display_todo_queue.py, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; PYTHONPATH=external/ipfs_datasets python3 scripts/meta_glasses_display_todo_supervisor.py --once
- Acceptance: Discovered during MGW-010: Android validation needs the repo-local JDK 17/Android SDK environment, and repeated validation failures should become evidence-backed discovery follow-up items instead of indefinite retry loops. The supervisor documents/enforces the validation environment and records retry-budget findings as daemon-parseable backlog work.

## MGW-015 Close optional display widget operation contract gaps

- Status: completed
- Completion: manual
- Priority: P1
- Track: backend
- Depends on: MGW-013
- Outputs: src/handsfree/models.py, src/handsfree/agent_providers.py, spec/openapi.yaml, mobile/src/native/wearablesBridge.js, mobile/src/native/metaWearablesDat.js, mobile/src/utils/agentActions.js, tests/test_meta_glasses_display_widget_actions.py, mobile/src/native/__tests__/wearablesBridge.test.js, mobile/src/utils/__tests__/agentActions.test.js, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_display_widget_actions.py; cd mobile && npm test -- --runInBand src/native/__tests__/wearablesBridge.test.js src/utils/__tests__/agentActions.test.js
- Acceptance: Discovered during MGW-013 Discovery Expansion: Swissknife emits `mobile_play_display_widget_video` and `mobile_subscribe_display_widget_updates` for `play_video` and `subscribe_updates`, but the HandsFree backend models/OpenAPI contract and mobile local-action executor only accept render/update/clear/focus/activate/reset. Backend and mobile serialize, validate, execute, and return structured fallback results for `play_video` and `subscribe_updates` with ORB receipt, policy, correlation, and diagnostics metadata.

## MGW-016 Preserve full widget action metadata through native DAT bridge calls

- Status: completed
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: MGW-013, MGW-015
- Outputs: mobile/modules/expo-meta-wearables-dat/index.ts, mobile/modules/expo-meta-wearables-dat/android/src/main/java/expo/modules/metawearablesdat/ExpoMetaWearablesDatModule.kt, mobile/modules/expo-meta-wearables-dat/ios/ExpoMetaWearablesDatModule.swift, mobile/modules/expo-meta-wearables-dat/__tests__/index.test.js, mobile/src/native/wearablesBridge.js, mobile/src/native/__tests__/wearablesBridge.test.js, data/meta_glasses_display_widgets/discovery
- Validation: cd mobile && npm test -- --runInBand modules/expo-meta-wearables-dat/__tests__/index.test.js src/native/__tests__/wearablesBridge.test.js; cd mobile/android && env JAVA_HOME=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8 PATH=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8/bin:$PATH ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false
- Acceptance: Discovered during MGW-013 Discovery Expansion: JS action execution passes a full widget action payload as context, but the native module boundary currently receives only the manifest, patch, widget id, focus direction, or action id. Native bridge methods accept and preserve the full widget action payload/context for display widget operations, diagnostics expose descriptor CID, widget CID, receipt CID, policy decision, correlation ID, request ID, fallback, and render path consistently, and bridge-only/default builds keep structured unsupported responses.

## MGW-017 Render compiled widget manifest regions on Android native DAT display

- Status: completed
- Completion: manual
- Priority: P1
- Track: mobile
- Depends on: MGW-013, MGW-016
- Outputs: mobile/modules/expo-meta-wearables-dat/android/src/main/java/expo/modules/metawearablesdat/ExpoMetaWearablesDatModule.kt, mobile/modules/expo-meta-wearables-dat/__tests__/index.test.js, docs/meta-wearables-dat-display-physical-validation-checklist.md, data/meta_glasses_display_widgets/discovery
- Validation: cd mobile && npm test -- --runInBand modules/expo-meta-wearables-dat/__tests__/index.test.js; cd mobile/android && env JAVA_HOME=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8 PATH=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8/bin:$PATH ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false
- Acceptance: Discovered during MGW-013 Discovery Expansion: Android follows the DisplayAccess session lifecycle, but the native content sender renders a title/detail/footer summary instead of the compiled manifest regions, actions, media, focus order, and video fallbacks. Android maps safe manifest text/progress/action/media regions into the DAT Display DSL root content, respects the 600x600 manifest constraints and DisplayAccess root view rules, and records unsupported region/media fallbacks without crashing.

## MGW-018 Add iOS DisplayAccess native-display bridge parity

- Status: completed
- Completion: manual
- Priority: P2
- Track: mobile
- Depends on: MGW-013, MGW-016
- Outputs: mobile/modules/expo-meta-wearables-dat/ios/ExpoMetaWearablesDatModule.swift, mobile/modules/expo-meta-wearables-dat/index.ts, mobile/modules/expo-meta-wearables-dat/__tests__/index.test.js, docs/meta-wearables-dat-display-physical-validation-checklist.md, data/meta_glasses_display_widgets/discovery
- Validation: cd mobile && npm test -- --runInBand modules/expo-meta-wearables-dat/__tests__/index.test.js
- Acceptance: Discovered during MGW-013 Discovery Expansion: the external iOS DisplayAccess sample and `MWDATDisplay` skill document a native display lifecycle, but this repo's iOS DAT module remains reference-only and exposes no display widget native methods. iOS either implements a gated `MWDATDisplay` render/update/clear/focus/activate/reset path when SDK linkage is available or returns explicit SDK-unlinked widget responses with the same diagnostics and fallback contract as Android.

## MGW-019 Broaden the hardware-free display widget harness for discovered lifecycle gaps

- Status: completed
- Completion: manual
- Priority: P1
- Track: quality
- Depends on: MGW-013, MGW-015, MGW-016
- Outputs: tests/test_meta_glasses_display_widget_harness.py, mobile/src/utils/__tests__/displayWidgetHarness.test.js, swissknife/test/mcp-plus-plus/meta-glasses-display-harness.test.ts, mobile/src/native/__fixtures__/metaWearablesDisplayStates.js, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_display_widget_harness.py; cd mobile && npm test -- --runInBand src/utils/__tests__/displayWidgetHarness.test.js; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-display-harness.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Discovered during MGW-013 Discovery Expansion: the current hardware-free harness proves render/update/clear success, while focus, activate, reset, `play_video`, `subscribe_updates`, policy denial, native-unavailable fallback, firmware update required, DAT glasses app update required, and lifecycle error paths remain unverified end to end. Harness fixtures and tests cover those paths and assert receipt, diagnostic, fallback, and event metadata without requiring Meta credentials, DAT package access, or paired glasses.

## MGW-020 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-025-implementation-unknowns.md:22

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-025-implementation-unknowns.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-025-implementation-unknowns.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-025-implementation-unknowns.md:22. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-25-mgw-020-codebase-scan-09a5288b833b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-021 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md:24

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md:24. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-25-mgw-021-codebase-scan-55c0165aa8e2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-022 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-044-hao-042-merge-unblock.md:25

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-044-hao-042-merge-unblock.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-044-hao-042-merge-unblock.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-044-hao-042-merge-unblock.md:25. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-25-mgw-022-codebase-scan-894285209757.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-023 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-051-resolution.md:8

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-051-resolution.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-051-resolution.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-051-resolution.md:8. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-25-mgw-023-codebase-scan-5e7f9214abc2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-024 Resolve code annotation in data/hallucinate_multimodal_control/discovery/2026-05-25-hao-053-resolution.md:10

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-053-resolution.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-053-resolution.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-053-resolution.md:10. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-25-mgw-024-codebase-scan-5ebb02bc2f3e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-025 Resolve 1 dirty backlogged worktrees blocked by content_not_in_target

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Fingerprint: b48a92facf4059c6b9970692d2f4253f48d23205
- Dedupe key: reconciliation_guardrail:dirty_backlogged_worktree:content_not_in_target
- Depends on:
- Outputs: data/meta_glasses_display_widgets/state/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-025-reconciliation-12735569962d.md
- Acceptance: Reconciliation guardrail filed this because 1 branch or worktree cleanup candidates are blocked by content_not_in_target. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-025-reconciliation-12735569962d.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## MGW-026 Resolve validation retry-budget failure for MGW-003

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-002
- Outputs: swissknife/test/fixtures/meta-glasses-display/valid-task-progress-widget.json, swissknife/test/fixtures/meta-glasses-display/invalid-widget-cases.json, mobile/src/native/__fixtures__/metaWearablesDisplayStates.js, data/meta_glasses_display_widgets/state/discovery
- Validation: cd mobile && npm test -- --runInBand src/native/__tests__/wearablesBridge.test.js
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-003. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-026-mgw-003-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-003 from strategy blocked_tasks.

## MGW-027 Resolve validation retry-budget failure for MGW-008

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-005, MGW-006, MGW-007
- Outputs: tests/test_meta_glasses_display_widget_harness.py, mobile/src/utils/__tests__/displayWidgetHarness.test.js, swissknife/test/mcp-plus-plus/meta-glasses-display-harness.test.ts, data/meta_glasses_display_widgets/state/discovery
- Validation: cd mobile && npm test -- --runInBand src/utils/__tests__/displayWidgetHarness.test.js
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-008. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-027-mgw-008-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-008 from strategy blocked_tasks.

## MGW-028 Resolve validation retry-budget failure for MGW-010

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-007, MGW-008
- Outputs: mobile/modules/expo-meta-wearables-dat/android/src/main/java/expo/modules/metawearablesdat/ExpoMetaWearablesDatModule.kt, mobile/modules/expo-meta-wearables-dat/__tests__/index.test.js, docs/meta-wearables-dat-display-physical-validation-checklist.md, data/meta_glasses_display_widgets/state/discovery
- Validation: cd mobile && npm ci && npm run android:validate:local
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-010. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-028-mgw-010-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-010 from strategy blocked_tasks.

## MGW-363 Research current Meta glasses I/O capability surface

- Status: completed
- Completion: manual
- Priority: P0
- Track: research
- Depends on: MGW-001
- Outputs: data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-363-meta-glasses-io-research.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Validation: rg -n "MGW-363|camera|microphone|speaker|headphone|Meta Neural Band|captouch|Bluetooth|Wi-Fi|Mock Device Kit|Device Access Toolkit|Web Apps" data/meta_glasses_display_widgets/discovery implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Acceptance: Research the current official Meta Wearables DAT, display developer-preview, Web Apps, Mock Device Kit, Android DAT, and iOS DAT sources before implementing expanded hardware assumptions. Distinguish native DAT phone-app capabilities from display Web Apps capabilities; document camera photo/video capture, microphone and speaker/headphone Bluetooth-profile routing, display lifecycle, Meta Neural Band and captouch events, motion/orientation, phone GPS, local storage, unsupported or unknown surfaces, release-channel/package constraints, and how these facts shape IPFS/libp2p/MCP++ bridge envelopes.

## MGW-364 Define Swissknife Meta glasses I/O capability contract

- Status: completed
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: MGW-363
- Outputs: swissknife/src/services/meta-glasses-io-profile.ts, swissknife/test/mcp-plus-plus/meta-glasses-io-profile.test.ts, swissknife/docs/meta-glasses-io-contract.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-io-profile.ts src/services/mcp-idl.ts src/services/mcp-ui-profile.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-profile.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Swissknife has a versioned Meta glasses I/O profile covering camera photo/video capture, microphone input, speaker/headphone output, display output, Meta Neural Band, captouch, motion/orientation, phone GPS, permission scopes, capability readiness, unsupported/degraded states, application interaction bindings, fallback routing, policy decisions, control-plane route decisions, content-addressed payload references, libp2p peer/session identifiers, and MCP++ receipt metadata.

## MGW-365 Add hardware-free mocks for expanded Meta glasses I/O

- Status: completed
- Completion: manual
- Priority: P0
- Track: quality
- Depends on: MGW-363, MGW-364
- Outputs: swissknife/test/fixtures/meta-glasses-io, mobile/src/native/__fixtures__/metaWearablesIoStates.js, tests/test_meta_glasses_io_mocks.py
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_io_mocks.py; cd mobile && npm test -- --runInBand src/native/__tests__/wearablesBridge.test.js; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-profile.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Hardware-free fixtures and mocks cover DAT camera photo capture, DAT video stream readiness, microphone route readiness, speaker/headphone route readiness, display lifecycle, Meta Neural Band gestures, captouch events, motion/orientation events, phone GPS context, Swissknife app capability bindings, control-plane event envelopes, permission denial, disconnect, unsupported capability, degraded capability, stale session, route loss, and recovery without requiring Meta credentials, DAT package access, paired glasses, or physical hardware.

## MGW-366 Model Bluetooth and Wi-Fi bridge envelopes for IPFS/libp2p/MCP++

- Status: completed
- Completion: manual
- Priority: P0
- Track: transport
- Depends on: MGW-364
- Outputs: swissknife/src/services/meta-glasses-io-transport.ts, swissknife/test/mcp-plus-plus/meta-glasses-io-transport.test.ts, docs/meta-glasses-io-transport-envelope.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-io-transport.ts src/services/meta-glasses-io-profile.ts src/services/mcp-idl.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-transport.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Bluetooth and Wi-Fi inputs are represented as app-level bridge envelopes with device ID, session ID, app binding ID, bridge route, control-plane route decision, permission state, latency, backpressure, payload size limits, content CIDs, libp2p peer IDs where applicable, MCP++ tool/event receipt IDs, policy decisions, and privacy redaction metadata. The contract explicitly avoids claiming raw Bluetooth or Wi-Fi transport is IPFS/libp2p/MCP++ unless the phone app or webapp bridge provides that layer.

## MGW-367 Expose camera capture and video stream descriptors to Swissknife apps

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: MGW-364, MGW-365, MGW-366
- Outputs: swissknife/src/services/meta-glasses-camera-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-camera-adapter.test.ts, swissknife/docs/meta-glasses-camera-app-descriptors.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-camera-adapter.ts src/services/meta-glasses-io-profile.ts src/services/meta-glasses-io-transport.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-camera-adapter.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Swissknife applications can declare camera photo and video stream requirements, bind camera interactions to app-level actions, receive mock/unsupported/ready/degraded states, request capture with explicit permission and policy checks, publish capture outputs as IPFS content references when storage is enabled, pass normalized capture events and payload references into the control plane, record libp2p/session routing metadata where available, and emit MCP++ receipts for capture request, capture result, fallback, denial, and error paths.

## MGW-368 Expose microphone and speaker/headphone audio routes to Swissknife apps

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: MGW-364, MGW-365, MGW-366
- Outputs: swissknife/src/services/meta-glasses-audio-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-audio-adapter.test.ts, swissknife/docs/meta-glasses-audio-app-descriptors.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-audio-adapter.ts src/services/meta-glasses-io-profile.ts src/services/meta-glasses-io-transport.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-audio-adapter.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Swissknife applications can declare microphone capture and speaker/headphone playback route requirements through platform Bluetooth-profile abstractions, bind audio interactions to app-level actions, receive mock/unsupported/ready/degraded route states, enforce permissions and privacy redaction, avoid raw-audio leakage by default, map allowed audio artifacts to content-addressed references, pass normalized audio route/capture/playback events into the control plane, and emit MCP++ receipts for route selection, capture/playback start, fallback, denial, and error paths.

## MGW-369 Expose Neural Band, captouch, motion, and GPS inputs to Swissknife apps

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: MGW-364, MGW-365, MGW-366
- Outputs: swissknife/src/services/meta-glasses-input-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-input-adapter.test.ts, swissknife/docs/meta-glasses-input-app-descriptors.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-input-adapter.ts src/services/meta-glasses-io-profile.ts src/services/meta-glasses-io-transport.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-input-adapter.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Meta Neural Band gestures, captouch input, motion/orientation events, and phone GPS context are normalized as Swissknife event and intent descriptors that applications can bind to commands, views, and agent actions. Hallucinate App policy can authorize and route those descriptors into the control plane. Fixtures cover allowed, denied, unsupported, stale, high-frequency throttled, disconnected, and replayed events, with session identity, control-plane route decisions, MCP++ receipts, and privacy-safe payloads.

## MGW-370 Route expanded Meta glasses I/O through the Swissknife control plane

- Status: completed
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: MGW-367, MGW-368, MGW-369
- Outputs: swissknife/src/services/meta-glasses-control-plane-router.ts, swissknife/test/mcp-plus-plus/meta-glasses-control-plane-router.test.ts, swissknife/docs/meta-glasses-control-plane-routing.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-control-plane-router.ts src/services/meta-glasses-camera-adapter.ts src/services/meta-glasses-audio-adapter.ts src/services/meta-glasses-input-adapter.ts src/services/meta-glasses-io-profile.ts src/services/meta-glasses-io-transport.ts src/services/mcp-orb-capability-router.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-control-plane-router.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Swissknife applications can register Meta glasses camera, microphone, speaker/headphone, display, Meta Neural Band, captouch, motion/orientation, and GPS interaction bindings and pass normalized events or content-addressed payload references into the control plane. The router maps app binding IDs to ORB/MCP++ tool calls, Hallucinate App policy handoff, app session state, libp2p/session routing metadata, replay protection, backpressure, privacy redaction, fallback handling, and deterministic MCP++ receipts.

## MGW-371 Add IPFS/libp2p/MCP++ conformance tests for Meta glasses I/O

- Status: completed
- Completion: manual
- Priority: P1
- Track: quality
- Depends on: MGW-365, MGW-366, MGW-367, MGW-368, MGW-369, MGW-370
- Outputs: swissknife/test/mcp-plus-plus/meta-glasses-io-conformance.test.ts, tests/test_meta_glasses_io_mcpplusplus_contract.py, docs/meta-glasses-io-conformance.md
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_io_mcpplusplus_contract.py; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-conformance.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Conformance tests assert that camera, audio, Neural Band, captouch, motion/GPS, and display mock flows include stable content CIDs when payloads are persisted, libp2p peer/session identifiers when routed through network peers, MCP++ tool/event receipts for every operation, explicit policy decisions, privacy redaction metadata, bridge route state, control-plane route decisions, app binding IDs, fallback behavior, Bluetooth/Wi-Fi envelope metadata, and deterministic validation failures for malformed envelopes or unauthorized control-plane handoffs.

## MGW-372 Add Playwright coverage for Swissknife apps using Meta glasses I/O

- Status: completed
- Completion: manual
- Priority: P1
- Track: quality
- Depends on: MGW-367, MGW-368, MGW-369, MGW-370, MGW-371
- Outputs: swissknife/test/e2e/meta-glasses-io-apps.spec.ts, swissknife/playwright.config.ts, swissknife/docs/meta-glasses-io-playwright.md
- Validation: cd swissknife && npx playwright test test/e2e/meta-glasses-io-apps.spec.ts --config=playwright.config.ts
- Acceptance: Playwright opens Swissknife applications against mocked Meta glasses camera, microphone, speaker/headphone, Meta Neural Band, captouch, motion/GPS, and display capabilities. Tests verify visible app state, app interaction bindings, permission prompts or denials, fallback UI, receipt display or diagnostics, content-addressed capture references, bridge-route metadata, and control-plane handoff evidence without physical glasses.

## MGW-373 Aggregate expanded Meta glasses I/O launch readiness evidence

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-371, MGW-372
- Outputs: docs/meta-glasses-io-launch-readiness.md, docs/meta-wearables-dat-display-rollout-evidence-template.md, data/meta_glasses_display_widgets/discovery
- Validation: rg -n "Meta glasses I/O|camera|microphone|headphone|Meta Neural Band|captouch|control plane|IPFS|libp2p|MCP\\+\\+|Playwright" docs data/meta_glasses_display_widgets/discovery implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Acceptance: Launch readiness evidence summarizes the official Meta research baseline, capability contract, mocks, Bluetooth/Wi-Fi bridge envelope, Swissknife app interaction bindings, control-plane routing evidence, IPFS/libp2p/MCP++ conformance results, Playwright results, hardware-free coverage, remaining physical-device validation steps, and fallback behavior for unsupported hardware, missing DAT credentials, missing display access, denied permissions, and unavailable audio routes.

## MGW-374 Resolve code annotation in implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md:194

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Validation: test -f implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md:194. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-374-codebase-scan-4c9f09d4fb78.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-375 Resolve code annotation in implementation_plan/docs/19-virtual-ai-os-submodule-integration.md:267

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Validation: test -f implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/19-virtual-ai-os-submodule-integration.md:267. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-375-codebase-scan-7898b4efd7d1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-376 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:74

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:74. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-376-codebase-scan-a303db6c8c70.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-377 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:192

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:192. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-377-codebase-scan-4c7fbc7a7cb1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-378 Resolve code annotation in implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md:194

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Validation: test -f implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md:194. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-378-codebase-scan-4c9f09d4fb78.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-379 Resolve code annotation in implementation_plan/docs/19-virtual-ai-os-submodule-integration.md:267

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Validation: test -f implementation_plan/docs/19-virtual-ai-os-submodule-integration.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/19-virtual-ai-os-submodule-integration.md:267. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-379-codebase-scan-7898b4efd7d1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-380 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:74

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:74. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-380-codebase-scan-a303db6c8c70.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-381 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:192

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:192. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-381-codebase-scan-4c7fbc7a7cb1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-382 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:216

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:216. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-382-codebase-scan-210b6a0bd043.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-383 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:239

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:239. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-383-codebase-scan-4dc1f7f08722.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-384 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:262

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:262. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-384-codebase-scan-0b738229dfc8.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-385 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:377

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:377. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-385-codebase-scan-e052213700f2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-386 Resolve merge retry-budget failure for MGW-363

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-001
- Outputs: data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-363-meta-glasses-io-research.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-386-mgw-363-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-363. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-386-mgw-363-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-363 from strategy blocked_tasks.

## MGW-387 Resolve 8 preflight-conflicting backlogged worktree merges

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Fingerprint: ba986381ed0580b8f7e21a96812053930665ac71
- Dedupe key: reconciliation_guardrail:preflight_merge_conflict
- Depends on:
- Outputs: data/meta_glasses_display_widgets/state/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-387-reconciliation-6979a5daafb9.md
- Acceptance: Reconciliation guardrail filed this because 8 branch or worktree cleanup candidates are blocked by preflight_merge_conflict. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-387-reconciliation-6979a5daafb9.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## MGW-388 Resolve code annotation in implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:859

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Validation: test -f implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md
- Acceptance: Codebase scan filed this finding from implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md:859. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-388-codebase-scan-309a8676f15b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-389 Resolve code annotation in src/handsfree/agents/runner.py:113

- Status: blocked
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/agents/runner.py
- Validation: python3 -m py_compile src/handsfree/agents/runner.py
- Acceptance: Codebase scan filed this finding from src/handsfree/agents/runner.py:113. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-389-codebase-scan-dc304b98262d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-390 Resolve code annotation in src/handsfree/agents/runner.py:122

- Status: blocked
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/agents/runner.py
- Validation: python3 -m py_compile src/handsfree/agents/runner.py
- Acceptance: Codebase scan filed this finding from src/handsfree/agents/runner.py:122. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-390-codebase-scan-24a8dfd921a5.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-391 Resolve code annotation in src/handsfree/agents/runner.py:147

- Status: blocked
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/agents/runner.py
- Validation: python3 -m py_compile src/handsfree/agents/runner.py
- Acceptance: Codebase scan filed this finding from src/handsfree/agents/runner.py:147. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-391-codebase-scan-d503a3e145f0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-392 Resolve code annotation in tests/test_agent_runner.py:417

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_agent_runner.py
- Validation: python3 -m py_compile tests/test_agent_runner.py
- Acceptance: Codebase scan filed this finding from tests/test_agent_runner.py:417. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-392-codebase-scan-d23bab9bfb8a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-393 Resolve code annotation in tests/test_agent_runner.py:438

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_agent_runner.py
- Validation: python3 -m py_compile tests/test_agent_runner.py
- Acceptance: Codebase scan filed this finding from tests/test_agent_runner.py:438. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-393-codebase-scan-027afb1b5def.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-394 Resolve code annotation in tests/test_implementation_daemon_merge_lock_retry.py:101

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_implementation_daemon_merge_lock_retry.py
- Validation: python3 -m py_compile tests/test_implementation_daemon_merge_lock_retry.py
- Acceptance: Codebase scan filed this finding from tests/test_implementation_daemon_merge_lock_retry.py:101. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-394-codebase-scan-2f375dbd1119.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-395 Resolve code annotation in tests/test_implementation_daemon_merge_lock_retry.py:114

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_implementation_daemon_merge_lock_retry.py
- Validation: python3 -m py_compile tests/test_implementation_daemon_merge_lock_retry.py
- Acceptance: Codebase scan filed this finding from tests/test_implementation_daemon_merge_lock_retry.py:114. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-395-codebase-scan-04bfc0065834.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-396 Resolve code annotation in tests/test_agent_runner.py:441

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_agent_runner.py
- Validation: python3 -m py_compile tests/test_agent_runner.py
- Acceptance: Codebase scan filed this finding from tests/test_agent_runner.py:441. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-396-codebase-scan-fbeb6b584d7c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-397 Resolve code annotation in tests/test_implementation_daemon_merge_lock_retry.py:121

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_implementation_daemon_merge_lock_retry.py
- Validation: python3 -m py_compile tests/test_implementation_daemon_merge_lock_retry.py
- Acceptance: Codebase scan filed this finding from tests/test_implementation_daemon_merge_lock_retry.py:121. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-397-codebase-scan-76cb4c034940.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-398 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:106

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_meta_glasses_display_todo_queue.py
- Validation: python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_meta_glasses_display_todo_queue.py:106. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-398-codebase-scan-66cf63fffa8e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-399 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:49

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:49. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-399-codebase-scan-7359bf5ddb37.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-400 Resolve code annotation in tests/test_agent_runner.py:435

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_agent_runner.py
- Validation: python3 -m py_compile tests/test_agent_runner.py
- Acceptance: Codebase scan filed this finding from tests/test_agent_runner.py:435. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-400-codebase-scan-4e05798c3058.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-401 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:54

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:54. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-401-codebase-scan-1aa0d0120649.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-402 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:63

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:63. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-402-codebase-scan-5a3102335d9c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-403 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:110

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:110. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-403-codebase-scan-f5182b96f0db.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-404 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:173

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:173. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-404-codebase-scan-f2142bd7e8ca.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-405 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:237

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:237. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-405-codebase-scan-09159eaa4473.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-406 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:288

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:288. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-406-codebase-scan-5f281694481a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-407 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:292

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:292. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-407-codebase-scan-465e51445a76.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-408 Resolve code annotation in tests/test_supervisor_objective_task_janitor.py:376

- Status: blocked
- Completion: manual
- Priority: P3
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_supervisor_objective_task_janitor.py
- Validation: python3 -m py_compile tests/test_supervisor_objective_task_janitor.py
- Acceptance: Codebase scan filed this finding from tests/test_supervisor_objective_task_janitor.py:376. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-408-codebase-scan-5a569d75b7f7.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-409 Resolve code annotation in tracking/PR-079-agent-runner-minimal.md:56

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-079-agent-runner-minimal.md
- Validation: test -f tracking/PR-079-agent-runner-minimal.md
- Acceptance: Codebase scan filed this finding from tracking/PR-079-agent-runner-minimal.md:56. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-409-codebase-scan-0a3992f37e3e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-410 Resolve code annotation in swissknife/DESKTOP_VERIFICATION_REPORT.md:122

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/DESKTOP_VERIFICATION_REPORT.md
- Validation: test -f swissknife/DESKTOP_VERIFICATION_REPORT.md
- Acceptance: Codebase scan filed this finding from swissknife/DESKTOP_VERIFICATION_REPORT.md:122. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-410-codebase-scan-0dbc6e6537b4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-411 Resolve code annotation in swissknife/DESKTOP_VERIFICATION_REPORT.md:174

- Status: blocked
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/DESKTOP_VERIFICATION_REPORT.md
- Validation: test -f swissknife/DESKTOP_VERIFICATION_REPORT.md
- Acceptance: Codebase scan filed this finding from swissknife/DESKTOP_VERIFICATION_REPORT.md:174. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-411-codebase-scan-e301b099e13e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-412 Resolve dirty main checkout blocking 10 worktree merges

- Status: completed
- Completion: manual 2026-06-24: merged the useful MGW-010 Android DAT display readiness changes into main, preserved the newer MGW-413+ expanded-I/O task split, and pruned the stopped-run implementation worktrees so cleanup no longer blocks launch steering.
- Priority: P1
- Track: ops
- Fingerprint: f5f568a78ed6f1980014a10fddeee21c2a7f6286
- Dedupe key: reconciliation_guardrail:main_checkout_dirty
- Depends on:
- Outputs: data/meta_glasses_display_widgets/state/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-412-reconciliation-454d98962911.md
- Acceptance: Reconciliation guardrail filed this because 8 branch or worktree cleanup candidates are blocked by main_checkout_dirty. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-23-mgw-412-reconciliation-454d98962911.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## MGW-413 Refresh official Meta glasses I/O source matrix

- Status: completed
- Completion: manual
- Priority: P0
- Track: research
- Depends on: MGW-363
- Outputs: data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-413-expanded-io-source-refresh.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Validation: rg -n "MGW-413|DAT|Web Apps|Meta Neural Band|captouch|Bluetooth audio route|IPFS/libp2p/MCP\\+\\+" data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-413-expanded-io-source-refresh.md implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Acceptance: Refresh the official-source matrix before native hardware assumptions change. The record must compare Meta Wearables FAQ, display developer announcement, Android DAT/iOS DAT 0.7 samples and changelogs, Web Apps starter kit behavior, Mock Device Kit limits, release-channel/package constraints, and unsupported surfaces. It must explicitly separate native DAT camera/display/audio-route capabilities from Web Apps Neural Band/captouch/motion/GPS inputs and explain how IPFS/libp2p/MCP++ compatibility lives in app-level bridge envelopes, not raw Bluetooth or Wi-Fi packets.

## MGW-414 Add Swissknife Meta glasses app capability registry

- Status: completed
- Completion: manual
- Priority: P0
- Track: runtime
- Depends on: MGW-364, MGW-413
- Outputs: swissknife/src/services/meta-glasses-app-capability-registry.ts, swissknife/test/mcp-plus-plus/meta-glasses-app-capability-registry.test.ts, swissknife/docs/meta-glasses-app-capability-registry.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-app-capability-registry.ts src/services/meta-glasses-io-profile.ts src/services/mcp-interface-registry.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-app-capability-registry.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Swissknife applications can enumerate and request Meta glasses camera, microphone route, speaker/headphone route, display, Meta Neural Band, captouch, motion/orientation, phone GPS, fallback, and unsupported capabilities without importing DAT SDK objects. Registry entries include app binding IDs, permission scopes, route readiness, policy requirements, control-plane route decisions, MCP++ descriptor references, and fallback behavior.

## MGW-415 Build Meta glasses I/O fixture corpus from DAT and Web Apps samples

- Status: completed
- Completion: manual
- Priority: P0
- Track: quality
- Depends on: MGW-365, MGW-413
- Outputs: swissknife/test/fixtures/meta-glasses-io/source-matrix, mobile/src/native/__fixtures__/metaWearablesDatSourceMatrix.js, tests/fixtures/meta_glasses_io_source_matrix.json
- Validation: PYTHONPATH=./src pytest tests/test_meta_glasses_io_mocks.py; cd mobile && npm test -- --runInBand src/native/__tests__/wearablesBridge.test.js; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-profile.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Fixture corpus mirrors the public DAT DisplayAccess and CameraAccess lifecycle shapes, v0.7 display session states, camera stream/photo states, Bluetooth audio route readiness, Web Apps Arrow/Enter Neural Band and captouch input, motion/orientation, phone GPS, local storage limits, permission denial, unsupported display, release-channel missing, firmware/app update required, route loss, backpressure, and recovery. Fixtures must run without Meta credentials, DAT package access, paired glasses, or physical hardware.

## MGW-416 Add privacy and policy threat model for expanded Meta glasses I/O

- Status: completed
- Completion: manual
- Priority: P0
- Track: security
- Depends on: MGW-364, MGW-413
- Outputs: docs/meta-glasses-io-privacy-threat-model.md, swissknife/docs/meta-glasses-io-contract.md, hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md
- Validation: rg -n "camera|microphone|speaker|headphone|GPS|Meta Neural Band|captouch|policy decision|redaction|retention|consent" docs/meta-glasses-io-privacy-threat-model.md swissknife/docs/meta-glasses-io-contract.md hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md
- Acceptance: Threat model covers camera capture, microphone route/capture, speaker/headphone playback, display content, phone GPS, motion/orientation, Neural Band/captouch inputs, app binding IDs, control-plane routing, IPFS persistence, libp2p peer/session metadata, MCP++ receipts, consent, redaction, retention, auditability, replay protection, and denial paths before implementation emits real user data.

## MGW-417 Define mobile bridge route contracts for camera, audio, and display

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: MGW-365, MGW-366, MGW-367, MGW-368
- Outputs: mobile/src/native/metaWearablesIoBridge.js, mobile/src/native/__tests__/metaWearablesIoBridge.test.js, docs/meta-glasses-mobile-bridge-routes.md
- Validation: cd mobile && npm test -- --runInBand src/native/__tests__/metaWearablesIoBridge.test.js
- Acceptance: Mobile bridge contract emits normalized camera, microphone route, speaker/headphone route, display, permission, unsupported, disconnected, stale session, degraded route, firmware update, DAT app update, and fallback events. Events carry app binding IDs, bridge route metadata, Bluetooth/Wi-Fi route labels, policy decisions, control-plane route decisions, payload CIDs where enabled, privacy redaction metadata, latency/backpressure, and MCP++ receipts without claiming raw radio packets are IPFS/libp2p transports.

## MGW-418 Add Web Apps input adapter for Neural Band, captouch, motion, and GPS

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: MGW-369, MGW-413, MGW-415
- Outputs: swissknife/src/services/meta-glasses-webapp-input-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-webapp-input-adapter.test.ts, swissknife/docs/meta-glasses-webapp-input-adapter.md
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-webapp-input-adapter.ts src/services/meta-glasses-input-adapter.ts src/services/meta-glasses-io-profile.ts; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-webapp-input-adapter.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Web Apps adapter maps Arrow/Enter input from Meta Neural Band and captouch into normalized Swissknife intent descriptors, folds motion/orientation and phone GPS into privacy-safe context descriptors, rejects unsupported camera/microphone/audio assumptions for Web Apps, rate-limits high-frequency sensor events, preserves app binding IDs, and emits control-plane route decisions plus MCP++ receipts for allowed, denied, fallback, stale, and replayed events.

## MGW-419 Integrate Hallucinate App policy for expanded Meta glasses I/O

- Status: completed
- Completion: manual
- Priority: P1
- Track: policy
- Depends on: MGW-370, MGW-416
- Outputs: hallucinate_app/python/hallucinate_app/meta_glasses_io_policy.py, hallucinate_app/tests/test_meta_glasses_io_policy.py, hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md
- Validation: PYTHONPATH=hallucinate_app/python pytest hallucinate_app/tests/test_meta_glasses_io_policy.py -q
- Acceptance: Hallucinate App policy can authorize or deny camera, microphone, speaker/headphone, display, Neural Band, captouch, motion/orientation, phone GPS, IPFS persistence, libp2p relay, and MCP++ tool/event handoffs before Swissknife routes events into the control plane. Tests cover consent missing, sensitive capture, location redaction, denied audio capture, denied display output, allowed mock route, replayed receipt, and unsupported hardware fallback.

## MGW-420 Prove IPFS/libp2p/MCP++ bridge-envelope compatibility

- Status: completed
- Completion: manual
- Priority: P1
- Track: transport
- Depends on: MGW-371, MGW-417, MGW-419
- Outputs: tests/integration/test_meta_glasses_io_bridge_envelope.py, docs/meta-glasses-io-transport-envelope.md, swissknife/test/mcp-plus-plus/meta-glasses-io-conformance.test.ts
- Validation: PYTHONPATH=./src pytest tests/integration/test_meta_glasses_io_bridge_envelope.py; cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-conformance.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Bridge-envelope tests prove camera, audio, Neural Band/captouch, motion/GPS, and display mock flows can carry IPFS CIDs, libp2p peer/session IDs, MCP++ receipts, policy decisions, control-plane route decisions, app binding IDs, replay protection, latency/backpressure, payload limits, and fallback states. Tests also prove malformed envelopes, missing policy decisions, unauthorized relays, raw Bluetooth/Wi-Fi transport claims, and missing receipts fail deterministically.

## MGW-421 Add Swissknife demo app for expanded Meta glasses interaction methods

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: MGW-414, MGW-417, MGW-418, MGW-419
- Outputs: swissknife/examples/meta-glasses-control-plane-demo, swissknife/docs/meta-glasses-control-plane-demo.md, swissknife/test/mcp-plus-plus/meta-glasses-demo-bindings.test.ts
- Validation: cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-demo-bindings.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Demo Swissknife app binds camera capture, microphone route status, speaker/headphone route status, display output, Neural Band/captouch commands, motion/orientation, and phone GPS to app actions and visible diagnostics. The demo runs entirely on mocks, emits control-plane handoff receipts, shows fallback UI when native DAT/Web Apps routes are unavailable, and records content-addressed capture references only when policy allows persistence.

## MGW-422 Add Playwright E2E coverage for expanded Meta glasses I/O in Swissknife apps

- Status: completed
- Completion: manual
- Priority: P1
- Track: quality
- Depends on: MGW-372, MGW-420, MGW-421
- Outputs: swissknife/test/e2e/meta-glasses-expanded-io.spec.ts, swissknife/playwright.config.ts, swissknife/docs/meta-glasses-io-playwright.md
- Validation: cd swissknife && npx playwright test test/e2e/meta-glasses-expanded-io.spec.ts --config=playwright.config.ts
- Acceptance: Playwright opens a Swissknife app with mocked Meta glasses camera, microphone route, speaker/headphone route, display, Neural Band/captouch Arrow/Enter input, motion/orientation, phone GPS, bridge-route metadata, and control-plane receipts. The test verifies visible app state, permission prompts or denials, fallback UI, app interaction bindings, content-addressed capture references, MCP++ receipts, and no unauthorized control-plane handoff.

## MGW-423 Add native DAT feature gates and physical validation checklist for expanded I/O

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-413, MGW-417, MGW-418
- Outputs: docs/meta-glasses-expanded-io-physical-validation-checklist.md, docs/meta-wearables-dat-display-physical-validation-checklist.md, scripts/validate_meta_glasses_io_feature_gates.py
- Validation: python3 scripts/validate_meta_glasses_io_feature_gates.py --check-docs
- Acceptance: Native DAT feature gates for camera, display, and Bluetooth audio routes remain optional unless package credentials, Developer Mode or release channel, app registration, firmware/app update state, paired hardware, and capability checks succeed. The physical validation checklist covers Android and iOS DAT v0.7, display-capable device selection, camera stream/photo capture, Bluetooth route diagnostics, Web Apps HTTPS deployment, Neural Band/captouch input validation, motion/GPS, fallback evidence, privacy review, and rollback.

## MGW-424 Aggregate expanded MGW launch priorities for the supervisor

- Status: completed
- Completion: manual
- Priority: P0
- Track: ops
- Depends on: MGW-413, MGW-414, MGW-415, MGW-416, MGW-417, MGW-418, MGW-419, MGW-420, MGW-421, MGW-422, MGW-423
- Outputs: data/meta_glasses_display_widgets/discovery/2026-06-23-mgw-424-expanded-io-launch-priorities.md, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md
- Validation: rg -n "MGW-424|Swissknife applications|camera|microphone|speaker/headphone|Meta Neural Band|captouch|Playwright|control-plane|IPFS|libp2p|MCP\\+\\+" data/meta_glasses_display_widgets/discovery implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Acceptance: Launch priority note tells the supervisor to prefer implementation tasks that make Swissknife applications use Meta glasses interaction methods through contracts, mocks, policy checks, control-plane routes, IPFS/libp2p/MCP++ receipts, and Playwright validation. It must deprioritize generic code-annotation cleanup whenever there are open P0/P1 expanded-I/O tasks with unmet contracts, mocks, tests, or launch-readiness evidence.

## MGW-425 Resolve code annotation in swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts:573

- Status: blocked
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts
- Validation: test -f swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts:573. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-425-codebase-scan-2d67c01d3acc.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-426 Resolve code annotation in swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts:574

- Status: blocked
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts
- Validation: test -f swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts:574. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-426-codebase-scan-e90a6112f5fa.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-427 Resolve code annotation in swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts:575

- Status: blocked
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts
- Validation: test -f swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/src/p2p/network-manager.ts:575. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-427-codebase-scan-849612e9edb6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-428 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_fault_tolerant_cross_browser_model_sharding.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_fault_tolerant_cross_browser_model_sharding.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_fault_tolerant_cross_browser_model_sharding.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_fault_tolerant_cross_browser_model_sharding.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-428-codebase-scan-d5e80576db69.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-429 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_firefox_webgpu_compute_shaders.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_firefox_webgpu_compute_shaders.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_firefox_webgpu_compute_shaders.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_firefox_webgpu_compute_shaders.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-429-codebase-scan-defbcedebe03.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-430 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_ipfs_accelerate_webnn_webgpu.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_ipfs_accelerate_webnn_webgpu.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_ipfs_accelerate_webnn_webgpu.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_ipfs_accelerate_webnn_webgpu.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-430-codebase-scan-ee57d2a45b3b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-431 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_ipfs_accelerate_with_real_webnn_webgpu.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_ipfs_accelerate_with_real_webnn_webgpu.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_ipfs_accelerate_with_real_webnn_webgpu.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_ipfs_accelerate_with_real_webnn_webgpu.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-431-codebase-scan-dc52194613c1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-432 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_ipfs_with_webnn_webgpu.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_ipfs_with_webnn_webgpu.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_ipfs_with_webnn_webgpu.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_ipfs_with_webnn_webgpu.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-432-codebase-scan-4f33a0ad65fb.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-433 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_real_webnn_webgpu.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_real_webnn_webgpu.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_real_webnn_webgpu.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_real_webnn_webgpu.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-433-codebase-scan-66825794ba9f.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-434 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_real_webnn_webgpu_implementations.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_real_webnn_webgpu_implementations.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_real_webnn_webgpu_implementations.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_real_webnn_webgpu_implementations.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-434-codebase-scan-c72286879ecc.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-435 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_safari_webgpu_fallback.ts:1

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_safari_webgpu_fallback.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_safari_webgpu_fallback.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_safari_webgpu_fallback.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-435-codebase-scan-dc36a218425f.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-436 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_safari_webgpu_support.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_safari_webgpu_support.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_safari_webgpu_support.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_safari_webgpu_support.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-436-codebase-scan-025dd1a14a04.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-437 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_inference.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_inference.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_inference.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_inference.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-437-codebase-scan-f47b62254b61.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-438 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_llm_inference.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_llm_inference.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_llm_inference.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_llm_inference.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-438-codebase-scan-f38469457e95.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-439 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_model_coverage.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_model_coverage.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_model_coverage.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_4bit_model_coverage.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-439-codebase-scan-1e2d44aa227a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-440 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_browsers_comparison.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_browsers_comparison.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_browsers_comparison.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_browsers_comparison.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-440-codebase-scan-1d39953b62c2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-441 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_compute_shaders.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_compute_shaders.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_compute_shaders.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_compute_shaders.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-441-codebase-scan-f7f312005529.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-442 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_compute_transfer_overlap.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_compute_transfer_overlap.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_compute_transfer_overlap.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_compute_transfer_overlap.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-442-codebase-scan-d636463c9d64.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-443 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_kv_cache_optimization.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_kv_cache_optimization.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_kv_cache_optimization.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_kv_cache_optimization.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-443-codebase-scan-da8f80493ff9.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-444 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_low_latency.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_low_latency.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_low_latency.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_low_latency.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-444-codebase-scan-aba0d5c2673b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-445 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_shader_precompilation.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_shader_precompilation.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_shader_precompilation.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_shader_precompilation.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-445-codebase-scan-b71e1b7130ac.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-446 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_transformer_compute_shaders.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_transformer_compute_shaders.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_transformer_compute_shaders.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_transformer_compute_shaders.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-446-codebase-scan-ff96ed86fa8c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-447 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_video_compute_shaders.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_video_compute_shaders.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_video_compute_shaders.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_video_compute_shaders.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-447-codebase-scan-4f381d39a54c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-448 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webgpu_webnn_bridge.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webgpu_webnn_bridge.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webgpu_webnn_bridge.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webgpu_webnn_bridge.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-448-codebase-scan-fd706f9227d1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-449 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webnn_cross_browser.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webnn_cross_browser.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webnn_cross_browser.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webnn_cross_browser.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-449-codebase-scan-067c64675c26.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-450 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webnn_implementation.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webnn_implementation.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webnn_implementation.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webnn_implementation.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-450-codebase-scan-69a234bf9d55.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-451 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webnn_minimal.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webnn_minimal.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webnn_minimal.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webnn_minimal.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-451-codebase-scan-07a35e081f65.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-452 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webnn_webgpu_integration.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webnn_webgpu_integration.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webnn_webgpu_integration.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webnn_webgpu_integration.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-452-codebase-scan-2907c83d600b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-453 Resolve code annotation in swissknife/ipfs_accelerate_js/test/browser/test_webnn_webgpu_simplified.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/browser/test_webnn_webgpu_simplified.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/browser/test_webnn_webgpu_simplified.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/browser/test_webnn_webgpu_simplified.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-453-codebase-scan-8162a1533a49.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-454 Resolve code annotation in swissknife/ipfs_accelerate_js/test/performance/test_benchmark.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/performance/test_benchmark.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/performance/test_benchmark.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/performance/test_benchmark.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-454-codebase-scan-f0debd6b16cf.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-455 Resolve code annotation in swissknife/ipfs_accelerate_js/test/performance/test_predictive_performance_system.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/performance/test_predictive_performance_system.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/performance/test_predictive_performance_system.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/performance/test_predictive_performance_system.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-455-codebase-scan-34218144f2c4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-456 Resolve code annotation in swissknife/ipfs_accelerate_js/test/performance/test_time_series_performance.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/performance/test_time_series_performance.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/performance/test_time_series_performance.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/performance/test_time_series_performance.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-456-codebase-scan-189bc4a84a14.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-457 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_active_learning.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_active_learning.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_active_learning.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_active_learning.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-457-codebase-scan-103085e1d7ec.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-458 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_all_models.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_all_models.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_all_models.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_all_models.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-458-codebase-scan-5bdd54dddcc6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-459 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_automated_hardware_compatibility.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_automated_hardware_compatibility.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_automated_hardware_compatibility.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_automated_hardware_compatibility.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-459-codebase-scan-8c17c2df11b1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-460 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_batch_generator.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_batch_generator.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_batch_generator.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_batch_generator.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-460-codebase-scan-593be57237f0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-461 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_batch_generator_minimal.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_batch_generator_minimal.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_batch_generator_minimal.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_batch_generator_minimal.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-461-codebase-scan-7ff199b75d27.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-462 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_batch_inference.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_batch_inference.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_batch_inference.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_batch_inference.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-462-codebase-scan-6ff7e98d2c3a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-463 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_comprehensive_hardware.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_comprehensive_hardware.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_comprehensive_hardware.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_comprehensive_hardware.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-463-codebase-scan-2fc84a992650.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-464 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_comprehensive_hardware_coverage.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_comprehensive_hardware_coverage.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_comprehensive_hardware_coverage.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_comprehensive_hardware_coverage.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-464-codebase-scan-87a1ababe545.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-465 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_cross_platform_4bit.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_cross_platform_4bit.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_cross_platform_4bit.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_cross_platform_4bit.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-465-codebase-scan-5f7907e8e561.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-466 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_cuda_debug.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_cuda_debug.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_cuda_debug.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_cuda_debug.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-466-codebase-scan-ca6a1281e07b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-467 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_default_embed.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_default_embed.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_default_embed.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_default_embed.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-467-codebase-scan-bfe30187a7bb.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-468 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_enhanced_openvino.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_enhanced_openvino.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_enhanced_openvino.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_enhanced_openvino.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-468-codebase-scan-c2b12d295679.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-469 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_generator.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_generator.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_generator.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_generator.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-469-codebase-scan-ec18be8c273c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-470 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hardware_selection.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hardware_selection.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hardware_selection.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hardware_selection.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-470-codebase-scan-44d16881da6f.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-471 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf___help.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf___help.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf___help.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf___help.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-471-codebase-scan-1067af266d5f.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-472 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf___model.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf___model.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf___model.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf___model.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-472-codebase-scan-0d21592b7e59.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-473 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_align.ts:1

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_align.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_align.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_align.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-473-codebase-scan-2b9fd9737a44.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-474 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_autoformer.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_autoformer.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_autoformer.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_autoformer.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-474-codebase-scan-8017793e8291.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-475 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_backslash.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_backslash.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_backslash.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_backslash.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-475-codebase-scan-2e5c7623ea98.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-476 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_bark.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_bark.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_bark.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_bark.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-476-codebase-scan-da19273702c3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-477 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_big_bird.ts:1

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_big_bird.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_big_bird.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_big_bird.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-477-codebase-scan-89a91bb14b86.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-478 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_bigbird_pegasus.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_bigbird_pegasus.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_bigbird_pegasus.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_bigbird_pegasus.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-478-codebase-scan-bb4ec37257b5.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-479 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_bit.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_bit.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_bit.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_bit.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-479-codebase-scan-2104a536dfcc.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-480 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_blenderbot.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_blenderbot.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_blenderbot.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_blenderbot.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-480-codebase-scan-f9289a36b91d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-481 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_blenderbot_small.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_blenderbot_small.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_blenderbot_small.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_blenderbot_small.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-481-codebase-scan-d4ed79ea4296.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-482 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_blip2.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_blip2.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_blip2.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_blip2.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-482-codebase-scan-b62d131629ca.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-483 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_blip_2.ts:1

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_blip_2.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_blip_2.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_blip_2.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-483-codebase-scan-e990af756aa3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-484 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_bridgetower.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_bridgetower.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_bridgetower.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_bridgetower.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-484-codebase-scan-e6f79f4bc645.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-485 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_bros.ts:1

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_bros.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_bros.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_bros.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-485-codebase-scan-15372f754d23.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-486 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_canine.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_canine.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_canine.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_canine.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-486-codebase-scan-4e01ce3fd165.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-487 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_chameleon.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_chameleon.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_chameleon.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_chameleon.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-487-codebase-scan-8a46ed903a02.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-488 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_claude3_haiku.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_claude3_haiku.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_claude3_haiku.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_claude3_haiku.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-488-codebase-scan-ef24d56686d4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-489 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_clvp.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_clvp.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_clvp.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_clvp.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-489-codebase-scan-cbf59dd145d8.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-490 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_cm3.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_cm3.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_cm3.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_cm3.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-490-codebase-scan-95c78eeaccd0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-491 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_codegen.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_codegen.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_codegen.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_codegen.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-491-codebase-scan-95748755efba.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-492 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_cogvlm2.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_cogvlm2.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_cogvlm2.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_cogvlm2.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-492-codebase-scan-4f7f9fbe12a8.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-493 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_cohere.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_cohere.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_cohere.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_cohere.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-493-codebase-scan-a9cbc076e898.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-494 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_command_r.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_command_r.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_command_r.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_command_r.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-494-codebase-scan-36a5165c924e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-495 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_convnext.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_convnext.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_convnext.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_convnext.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-495-codebase-scan-1d1434428e78.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-496 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_cpmant.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_cpmant.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_cpmant.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_cpmant.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-496-codebase-scan-2adda538b8c5.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-497 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_ctrl.ts:1

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_ctrl.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_ctrl.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_ctrl.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-497-codebase-scan-4b1f305031f6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-498 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_cvt.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_cvt.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_cvt.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_cvt.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-498-codebase-scan-584127fea95e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-499 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_dac.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_dac.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_dac.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_dac.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-499-codebase-scan-77865dbd5032.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-500 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_data2vec_text.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_data2vec_text.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_data2vec_text.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_data2vec_text.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-500-codebase-scan-b9d105999d3a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-501 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_dbrx.ts:1

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_dbrx.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_dbrx.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_dbrx.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-501-codebase-scan-81637d10675d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-502 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_dbrx_instruct.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_dbrx_instruct.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_dbrx_instruct.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_dbrx_instruct.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-502-codebase-scan-56bd19bf79e7.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-503 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_decision_transformer.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_decision_transformer.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_decision_transformer.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_decision_transformer.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-503-codebase-scan-295167feddbd.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-504 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-504-codebase-scan-7e78f5b85c0d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-505 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_coder.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_coder.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_coder.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_coder.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-505-codebase-scan-4f239a29b61b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-506 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_distil.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_distil.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_distil.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_distil.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-506-codebase-scan-ca5abd94b6cd.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-507 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_r1.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_r1.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_r1.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_r1.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-507-codebase-scan-7aec3a87b450.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-508 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_r1_distil.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_r1_distil.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_r1_distil.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_deepseek_r1_distil.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-508-codebase-scan-8b3d8ba89074.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-509 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_dinat.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_dinat.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_dinat.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_dinat.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-509-codebase-scan-9a74b88e06cf.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-510 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_dino.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_dino.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_dino.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_dino.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-510-codebase-scan-669a61083619.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-511 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_dinov2.ts:1

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_dinov2.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_dinov2.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_dinov2.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-511-codebase-scan-18950e1154bd.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-512 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_donut.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_donut.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_donut.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_donut.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-512-codebase-scan-e79c1d962235.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-513 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_donut_swin.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_donut_swin.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_donut_swin.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_donut_swin.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-513-codebase-scan-529279e8394e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-514 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_dpr.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_dpr.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_dpr.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_dpr.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-514-codebase-scan-5481b197a30a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-515 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_dpt.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_dpt.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_dpt.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_dpt.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-515-codebase-scan-7e535b05d1d8.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-516 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_efficientformer.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_efficientformer.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_efficientformer.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_efficientformer.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-516-codebase-scan-81177723e089.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-517 Resolve code annotation in swissknife/ipfs_accelerate_js/test/unit/test_hf_efficientnet.ts:1

- Status: blocked
- Completion: manual
- Priority: P2
- Track: quality
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, swissknife/ipfs_accelerate_js/test/unit/test_hf_efficientnet.ts
- Validation: test -f swissknife/ipfs_accelerate_js/test/unit/test_hf_efficientnet.ts
- Acceptance: Codebase scan filed this finding from swissknife/ipfs_accelerate_js/test/unit/test_hf_efficientnet.ts:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-24-mgw-517-codebase-scan-7b300c0284ff.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

- Blocked reason: Deferred by objective-task janitor during launch steering because off_mission_codebase_scan_task; this keeps lanes focused on Swissknife, Hallucinate App, MCP++, Meta glasses, and Playwright launch readiness.

## MGW-518 Define Meta glasses multimodal IO transport contracts for Swissknife

- Status: completed
- Completion: manual
- Priority: P0
- Track: integration
- Depends on: MGW-002, MGW-005, MGW-007, MGW-008, MGW-010
- Outputs: implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md, data/meta_glasses_display_widgets/discovery, swissknife, mobile, tests
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; rg -n "MGW-518|camera|microphone|headphones|Neural Band|captouch|IPFS|libp2p|MCP\\+\\+|control plane" implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.md data/meta_glasses_display_widgets/discovery swissknife mobile tests
- Acceptance: Define the hardware-free contract and mock boundary for Meta glasses camera, microphone, headphones, display, captouch, and Neural Band inputs as Swissknife control-plane events, including Bluetooth/Wi-Fi transport assumptions, DAT availability fallbacks, IPFS/libp2p handoff metadata, and MCP++ envelope compatibility.

## MGW-519 Add Meta glasses control-plane mocks and Playwright-ready fixtures

- Status: completed
- Completion: manual
- Priority: P0
- Track: validation
- Depends on: MGW-518
- Outputs: swissknife, mobile, tests, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_datasets pytest tests/test_meta_glasses_display_todo_queue.py; rg -n "MGW-519|Meta glasses|control-plane|Playwright|camera|microphone|headphones|Neural Band" swissknife mobile tests data/meta_glasses_display_widgets/discovery
- Acceptance: Add or specify reusable mocks and Playwright-ready fixtures that let Swissknife applications consume Meta glasses display/audio/camera/neural-band events through the control plane without paired hardware, while preserving receipts that can later be replayed against physical DAT devices.

## MGW-520 Resolve validation retry-budget failure for MGW-364

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-363
- Outputs: swissknife/src/services/meta-glasses-io-profile.ts, swissknife/test/mcp-plus-plus/meta-glasses-io-profile.test.ts, swissknife/docs/meta-glasses-io-contract.md, data/meta_glasses_display_widgets/state/discovery
- Validation: cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-io-profile.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-364. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-24-mgw-520-mgw-364-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-364 from strategy blocked_tasks.

## MGW-521 Resolve validation retry-budget failure for MGW-414

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-364, MGW-413
- Outputs: swissknife/src/services/meta-glasses-app-capability-registry.ts, swissknife/test/mcp-plus-plus/meta-glasses-app-capability-registry.test.ts, swissknife/docs/meta-glasses-app-capability-registry.md, data/meta_glasses_display_widgets/state/discovery
- Validation: cd swissknife && npx jest test/mcp-plus-plus/meta-glasses-app-capability-registry.test.ts --config=config/jest/jest.config.cjs --runInBand
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-414. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-24-mgw-521-mgw-414-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-414 from strategy blocked_tasks.

## MGW-522 Resolve validation retry-budget failure for MGW-365

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-363, MGW-364
- Outputs: swissknife/test/fixtures/meta-glasses-io, mobile/src/native/__fixtures__/metaWearablesIoStates.js, tests/test_meta_glasses_io_mocks.py, data/meta_glasses_display_widgets/state/discovery
- Validation: cd mobile && npm test -- --runInBand src/native/__tests__/wearablesBridge.test.js
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-365. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-24-mgw-522-mgw-365-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-365 from strategy blocked_tasks.

## MGW-523 Resolve validation retry-budget failure for MGW-366

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-364
- Outputs: swissknife/src/services/meta-glasses-io-transport.ts, swissknife/test/mcp-plus-plus/meta-glasses-io-transport.test.ts, docs/meta-glasses-io-transport-envelope.md, data/meta_glasses_display_widgets/state/discovery
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-io-transport.ts src/services/meta-glasses-io-profile.ts src/services/mcp-idl.ts
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-366. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-24-mgw-523-mgw-366-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-366 from strategy blocked_tasks.

## MGW-524 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-25-mgw-524-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-525 Resolve validation retry-budget failure for MGW-524

- Status: completed
- Completion: manual 2026-06-26: verified the MGW-524 retry-budget blocker is resolved by the Hallucinate App headless-aware MCP dashboard Playwright gate; the required validation command passes without a display server and MGW-524 is absent from strategy blocked_tasks.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests, data/meta_glasses_display_widgets/state/discovery
- Validation: npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-524. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-25-mgw-525-mgw-524-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-524 from strategy blocked_tasks.

## MGW-526 Make Meta glasses MCP dashboard validation use the headless-aware Hallucinate runner

- Status: completed
- Completion: manual
- Priority: P0
- Track: validation
- Depends on: MGW-524, MGW-525
- Outputs: hallucinate_app/scripts/run_playwright_test.mjs, tests/test_virtual_ai_os_launch_readiness_gate.py, data/meta_glasses_display_widgets/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py tests/test_meta_glasses_display_todo_queue.py -q; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78)
- Bundle: objective/launch/meta-glasses-mcp-dashboard-validation
- Bundle strategy: explicit
- Graph parents: VAIOS-G723
- Graph depth: 1
- Parallel lane: meta-glasses-playwright-headless
- Conflict policy: keep Meta glasses dashboard validation attached to the same Hallucinate MCP dashboard Playwright gate, but surface display/Xvfb environment failures as repair work instead of feature failures.
- Goal id: VAIOS-G723
- Missing evidence: Meta glasses interaction contracts validated through a non-skipped Hallucinate MCP dashboard Playwright gate
- Embedding query: Meta glasses Swissknife Hallucinate MCP dashboard Playwright headless xvfb-run missing display control plane validation
- AST query: run_playwright_test, missing_xvfb_for_electron_playwright, mcp-feature-exposure, meta glasses, control plane
- Surplus group: objective/VAIOS-G723
- Merge key: vaios-g723-mgw-playwright-validation-environment
- Merge family: objective/VAIOS-G723
- Merge role: validation_environment_gate
- Work item count: 1
- Work scope: launch_validation_environment
- Candidate kind: validation_gate
- Acceptance: Ensure MGW launch validation inherits the headless-aware Hallucinate Playwright runner so Meta glasses camera/microphone/headphones/neural-band control-plane tests fail only for real contract gaps, while missing DISPLAY/Xvfb is recorded as a repairable launch-environment blocker.

## MGW-527 Resolve 1 dirty backlogged worktrees blocked by unsupported_status

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Fingerprint: a77eba7df32c8299d7d4ab9472cef5ba6c3a0b5b
- Dedupe key: reconciliation_guardrail:dirty_backlogged_worktree:unsupported_status
- Depends on:
- Outputs: data/meta_glasses_display_widgets/state/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-527-reconciliation-f77180faeb9c.md
- Acceptance: Reconciliation guardrail filed this because 1 branch or worktree cleanup candidates are blocked by unsupported_status. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-527-reconciliation-f77180faeb9c.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## MGW-528 Resolve dependency guardrail for MGW-412

- Status: completed
- Completion: manual 2026-06-26: verified the MGW-411 blocked-reason metadata is separated from the MGW-412 heading, leaving a single MGW-412 task id with no real dependencies.
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/state/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-528-dependency-guardrail.md
- Acceptance: Dependency guardrail filed this because MGW-412 has missing, self-referential, cyclic, or duplicate task-id metadata. Use the evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-528-dependency-guardrail.md to repair the todo board metadata or add the missing prerequisite task, then verify the original task can become ready once its real dependencies complete.

## MGW-529 Resolve validation retry-budget failure for MGW-369

- Status: completed
- Completion: manual 2026-06-26: restored the MGW-369 input adapter outputs, verified the focused Jest suite, and corrected the retry-budget validation blocker by removing TypeScript's unsupported `--ignoreConfig` flag from the repair task validation metadata.
- Priority: P1
- Track: ops
- Depends on: MGW-364, MGW-365, MGW-366
- Outputs: swissknife/src/services/meta-glasses-input-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-input-adapter.test.ts, swissknife/docs/meta-glasses-input-app-descriptors.md, data/meta_glasses_display_widgets/state/discovery
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-input-adapter.ts src/services/meta-glasses-io-profile.ts src/services/meta-glasses-io-transport.ts
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-369. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-529-mgw-369-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-369 from strategy blocked_tasks.

## MGW-530 Resolve validation retry-budget failure for MGW-368

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-364, MGW-365, MGW-366
- Outputs: swissknife/src/services/meta-glasses-audio-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-audio-adapter.test.ts, swissknife/docs/meta-glasses-audio-app-descriptors.md, data/meta_glasses_display_widgets/state/discovery
- Validation: cd swissknife && npx -y -p typescript tsc --noEmit --ignoreConfig --strict --skipLibCheck --module NodeNext --moduleResolution NodeNext --target ES2022 --typeRoots /usr/share/nodejs/@types --types node src/services/meta-glasses-audio-adapter.ts src/services/meta-glasses-io-profile.ts src/services/meta-glasses-io-transport.ts
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-368. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-530-mgw-368-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-368 from strategy blocked_tasks.

## MGW-531 Resolve implementation retry-budget failure for MGW-369

- Status: completed
- Completion: manual 2026-06-26: verified the MGW-369 implementation setup blocker is resolved by the submodule worktree fallback in `external/ipfs_accelerate` (`b14f4df49c35ffb2891df1e25c171d446c083327`), which fetches and falls back to source `HEAD` when a nested gitlink ref is unavailable; see `data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-531-resolution.md`.
- Priority: P1
- Track: ops
- Depends on: MGW-364, MGW-365, MGW-366
- Outputs: swissknife/src/services/meta-glasses-input-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-input-adapter.test.ts, swissknife/docs/meta-glasses-input-app-descriptors.md, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-531-mgw-369-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-369. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-531-mgw-369-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-369 from strategy blocked_tasks.

## MGW-532 Resolve implementation retry-budget failure for MGW-368

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-364, MGW-365, MGW-366
- Outputs: swissknife/src/services/meta-glasses-audio-adapter.ts, swissknife/test/mcp-plus-plus/meta-glasses-audio-adapter.test.ts, swissknife/docs/meta-glasses-audio-app-descriptors.md, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-532-mgw-368-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-368. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-532-mgw-368-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-368 from strategy blocked_tasks.

## MGW-533 Close virtual AI OS launch objective gap: Hallucinate App MCP dashboard capability catalog

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts, hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts
- Validation: npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard-capability-catalog
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard-capability-catalog.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/hallucinate-mcp-dashboard-capability-catalog
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G724
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App MCP dashboard dashboard capability catalog tools/list tools/call ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife Playwright
- AST query: hallucinate_app, swissknife, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py, tools/list, tools/call, daemon health, MCP dashboard
- Surplus group: objective/VAIOS-G724
- Merge key: 9a625fd9f839651a
- Merge family: goal_packet/launch/hallucinate_app/44dceea6bc53
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Goal packet role: packet_anchor
- Goal packet goals: VAIOS-G724, VAIOS-G728
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: 573509f5885861c3
- Acceptance: Objective scan filed this gap for VAIOS-G724. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-533-objective-gap-3e00ad2a0074.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/hallucinate_app/44dceea6bc53; when practical, make one cohesive change that advances the packet goals (VAIOS-G724, VAIOS-G728) and covers the shared packet evidence without expanding the prompt. Refine the objective heap if the gap needs smaller child goals.

## MGW-534 Close virtual AI OS launch objective gap: Meta glasses control-plane input routing

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, external/meta-wearables-dat-android, external/meta-wearables-dat-ios, mobile, swissknife, hallucinate_app, tests/test_hallucinate_multimodal_control_todo_queue.py, tests/test_virtual_ai_os_launch_readiness_gate.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_launch_readiness_gate.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/meta-glasses-control-plane-input-routing
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-meta-glasses-control-plane-input-routing.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/meta-glasses-control-plane-input-routing
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G727
- Missing evidence: launch Playwright validation gate
- Embedding query: Meta glasses camera microphone headphones Neural Band captouch Bluetooth Wi-Fi Swissknife control plane IPFS libp2p MCP++
- AST query: Meta Wearables DAT, camera, microphone, headphones, Neural Band, captouch, Bluetooth, Wi-Fi, Swissknife, control plane
- Surplus group: objective/VAIOS-G727
- Merge key: d40a3d3f5fd702f0
- Merge family: goal_packet/launch/external/ec964340486b
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/external/ec964340486b
- Goal packet role: packet_anchor
- Goal packet goals: VAIOS-G727, VAIOS-G729
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: 2ac1fa3810e3a6b9
- Acceptance: Objective scan filed this gap for VAIOS-G727. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-534-objective-gap-2f00e48f3541.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/external/ec964340486b; when practical, make one cohesive change that advances the packet goals (VAIOS-G727, VAIOS-G729) and covers the shared packet evidence without expanding the prompt. Refine the objective heap if the gap needs smaller child goals.

## MGW-535 Close virtual AI OS launch objective gap: Hallucinate App daemon launch orchestration

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/daemon-launch-health.spec.ts
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-daemon-launch-orchestration
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-daemon-launch-orchestration.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/hallucinate-daemon-launch-orchestration
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G728
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App daemon launch health MCP server dashboard ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife
- AST query: hallucinate_app, daemon health, MCP server, MCP dashboard, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Surplus group: objective/VAIOS-G728
- Merge key: 7e544b4df4e28611
- Merge family: goal_packet/launch/hallucinate_app/44dceea6bc53
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G724, VAIOS-G728
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: e514497464ba6ea4
- Acceptance: Objective scan filed this gap for VAIOS-G728. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-535-objective-gap-b023c8de5b69.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/hallucinate_app/44dceea6bc53; when practical, make one cohesive change that advances the packet goals (VAIOS-G724, VAIOS-G728) and covers the shared packet evidence without expanding the prompt. Refine the objective heap if the gap needs smaller child goals.

## MGW-536 Close virtual AI OS launch objective gap: Objective heap active steering and validation repair

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor, tests/test_supervisor_objective_task_janitor.py, tests/test_reconciliation_guardrail_refresh.py
- Validation: PYTHONPATH=external/ipfs_accelerate pytest tests/test_supervisor_objective_task_janitor.py tests/test_reconciliation_guardrail_refresh.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/objective-heap-autosteer-validation-repair
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-objective-heap-autosteer-validation-repair.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/objective-heap-autosteer-validation-repair
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G729
- Missing evidence: launch Playwright validation gate
- Embedding query: objective heap fibonacci priority supervisor active management failed validation repair Playwright VAI MGW HAO production readiness
- AST query: objective heap, supervisor, validation repair, Playwright, VAI, MGW, HAO
- Surplus group: objective/VAIOS-G729
- Merge key: a5e079ff4b5db8d6
- Merge family: goal_packet/launch/external/ec964340486b
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/external/ec964340486b
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G727, VAIOS-G729
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: d39b2c2a61955cdf
- Acceptance: Objective scan filed this gap for VAIOS-G729. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-536-objective-gap-9f377c75e074.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/external/ec964340486b; when practical, make one cohesive change that advances the packet goals (VAIOS-G727, VAIOS-G729) and covers the shared packet evidence without expanding the prompt. Refine the objective heap if the gap needs smaller child goals.

## MGW-537 Close virtual AI OS launch objective gap: Swissknife MCP++ server dashboard interoperability

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, swissknife, Mcp-Plus-Plus, hallucinate_app, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, swissknife/test/e2e/mcp-dashboard.spec.ts
- Validation: npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/swissknife-mcp-plus-plus-server-dashboard-interop
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-swissknife-mcp-plus-plus-server-dashboard-interop.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/swissknife-mcp-plus-plus-server-dashboard-interop
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G725
- Missing evidence: launch Playwright validation gate
- Embedding query: Swissknife MCP++ MCP server dashboard control plane tools/list tools/call ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py
- AST query: swissknife, Mcp-Plus-Plus, MCP++, MCP server, tools/list, tools/call, control plane
- Surplus group: objective/VAIOS-G725
- Merge key: 519b37a2b9cdc0fa
- Merge family: objective/VAIOS-G725
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: ecc1cf6efb3e5be5
- Acceptance: Objective scan filed this gap for VAIOS-G725. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-537-objective-gap-1d0c6a56cf6c.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## MGW-538 Close virtual AI OS launch objective gap: Cross-device virtual desktop offload launch replay

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, mobile, swissknife, hallucinate_app, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, tests/test_virtual_ai_os_launch_readiness_gate.py
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_virtual_ai_os_launch_readiness_gate.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/cross-device-virtual-desktop-offload-replay
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-cross-device-virtual-desktop-offload-replay.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/cross-device-virtual-desktop-offload-replay
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G726
- Missing evidence: launch Playwright validation gate
- Embedding query: phone hosted Swissknife virtual desktop desktop peer offload mobile IPFS libp2p MCP++ launch readiness receipt Playwright
- AST query: mobile, swissknife, hallucinate_app, desktop peer offload, launch readiness, Playwright
- Surplus group: objective/VAIOS-G726
- Merge key: 7d9425a3e3360384
- Merge family: objective/VAIOS-G726
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 12be0e10facbf533
- Acceptance: Objective scan filed this gap for VAIOS-G726. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-538-objective-gap-4ca32c914d33.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## MGW-539 Resolve implementation retry-budget failure for MGW-537

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, swissknife, Mcp-Plus-Plus, hallucinate_app, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, swissknife/test/e2e/mcp-dashboard.spec.ts, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-539-mgw-537-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-537. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-539-mgw-537-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-537 from strategy blocked_tasks.

## MGW-540 Resolve implementation retry-budget failure for MGW-538

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, mobile, swissknife, hallucinate_app, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, tests/test_virtual_ai_os_launch_readiness_gate.py, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-540-mgw-538-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-538. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-540-mgw-538-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-538 from strategy blocked_tasks.

## MGW-541 Resolve implementation retry-budget failure for MGW-533

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts, hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-541-mgw-533-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-533. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-541-mgw-533-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-533 from strategy blocked_tasks.

## MGW-542 Resolve implementation retry-budget failure for MGW-534

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, external/meta-wearables-dat-android, external/meta-wearables-dat-ios, mobile, swissknife, hallucinate_app, tests/test_hallucinate_multimodal_control_todo_queue.py, tests/test_virtual_ai_os_launch_readiness_gate.py, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-542-mgw-534-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-534. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-542-mgw-534-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-534 from strategy blocked_tasks.

## MGW-543 Resolve implementation retry-budget failure for MGW-535

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/daemon-launch-health.spec.ts, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-543-mgw-535-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-535. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-543-mgw-535-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-535 from strategy blocked_tasks.

## MGW-544 Resolve implementation retry-budget failure for MGW-536

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor, tests/test_supervisor_objective_task_janitor.py, tests/test_reconciliation_guardrail_refresh.py, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-544-mgw-536-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-536. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-544-mgw-536-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-536 from strategy blocked_tasks.

## MGW-545 Resolve validation retry-budget failure for MGW-417

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: MGW-365, MGW-366, MGW-367, MGW-368
- Outputs: mobile/src/native/metaWearablesIoBridge.js, mobile/src/native/__tests__/metaWearablesIoBridge.test.js, docs/meta-glasses-mobile-bridge-routes.md, data/meta_glasses_display_widgets/state/discovery
- Validation: cd mobile && npm test -- --runInBand src/native/__tests__/metaWearablesIoBridge.test.js
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-417. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-26-mgw-545-mgw-417-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-417 from strategy blocked_tasks.

## MGW-546 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-546-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-547 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-547-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-548 Resolve validation retry-budget failure for MGW-546

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests, data/meta_glasses_display_widgets/state/discovery
- Validation: npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-546. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-27-mgw-548-mgw-546-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-546 from strategy blocked_tasks. For launch tasks, this repair validation preserves the launch Playwright validation gate.

## MGW-549 Resolve validation retry-budget failure for MGW-547

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests, data/meta_glasses_display_widgets/state/discovery
- Validation: npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-547. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-27-mgw-549-mgw-547-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-547 from strategy blocked_tasks. For launch tasks, this repair validation preserves the launch Playwright validation gate.

## MGW-550 Close objective gap: Hallucinate App MCP dashboard capability catalog

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts, hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts
- Validation: npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard-capability-catalog
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard-capability-catalog.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/hallucinate-mcp-dashboard-capability-catalog
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G724
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App MCP dashboard dashboard capability catalog tools/list tools/call ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife Playwright
- AST query: hallucinate_app, swissknife, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py, tools/list, tools/call, daemon health, MCP dashboard
- Surplus group: objective/VAIOS-G724
- Merge key: 9a625fd9f839651a
- Merge family: goal_packet/launch/hallucinate_app/44dceea6bc53
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Goal packet role: packet_anchor
- Goal packet goals: VAIOS-G724, VAIOS-G728
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: 573509f5885861c3
- Acceptance: Objective scan filed this gap for VAIOS-G724. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-550-objective-gap-3e00ad2a0074.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/hallucinate_app/44dceea6bc53; when practical, make one cohesive change that advances the packet goals (VAIOS-G724, VAIOS-G728) and covers the shared packet evidence without expanding the prompt. Refine the objective heap if the gap needs smaller child goals.

## MGW-551 Close objective gap: Hallucinate App daemon launch orchestration

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/daemon-launch-health.spec.ts
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-daemon-launch-orchestration
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-daemon-launch-orchestration.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/hallucinate-daemon-launch-orchestration
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G728
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App daemon launch health MCP server dashboard ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife
- AST query: hallucinate_app, daemon health, MCP server, MCP dashboard, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Surplus group: objective/VAIOS-G728
- Merge key: 7e544b4df4e28611
- Merge family: goal_packet/launch/hallucinate_app/44dceea6bc53
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G724, VAIOS-G728
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: e514497464ba6ea4
- Acceptance: Objective scan filed this gap for VAIOS-G728. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-551-objective-gap-b023c8de5b69.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/hallucinate_app/44dceea6bc53; when practical, make one cohesive change that advances the packet goals (VAIOS-G724, VAIOS-G728) and covers the shared packet evidence without expanding the prompt. Refine the objective heap if the gap needs smaller child goals.

## MGW-552 Resolve validation retry-budget failure for MGW-551

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/daemon-launch-health.spec.ts, data/meta_glasses_display_widgets/state/discovery
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-551. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-27-mgw-552-mgw-551-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-551 from strategy blocked_tasks. For launch tasks, this repair validation preserves the launch Playwright validation gate.

## MGW-553 Resolve merge retry-budget failure for MGW-551

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/daemon-launch-health.spec.ts, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-28-mgw-553-mgw-551-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-551. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-28-mgw-553-mgw-551-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-551 from strategy blocked_tasks.

## MGW-554 Resolve merge retry-budget failure for MGW-547

- Status: completed
- Completion: manual 2026-06-28: cleared the MGW-547 merge retry-budget blocker by verifying the intended MGW-547 top-level and submodule commits exist in their owning repositories, confirming the dirty `hallucinate_app` main-checkout condition is gone, and recording the remaining merge shape as semantic submodule pointer reconciliation.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-28-mgw-554-mgw-547-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-547. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-28-mgw-554-mgw-547-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-547 from strategy blocked_tasks.

## MGW-555 Close objective gap: Hallucinate App MCP dashboard capability catalog

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts, hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts
- Validation: npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard-capability-catalog
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard-capability-catalog.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/hallucinate-mcp-dashboard-capability-catalog
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G724
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App MCP dashboard dashboard capability catalog tools/list tools/call ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife Playwright
- AST query: hallucinate_app, swissknife, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py, tools/list, tools/call, daemon health, MCP dashboard
- Surplus group: objective/VAIOS-G724
- Merge key: 9a625fd9f839651a
- Merge family: goal_packet/launch/hallucinate_app/44dceea6bc53
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Goal packet role: packet_anchor
- Goal packet goals: VAIOS-G724, VAIOS-G728
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: 573509f5885861c3
- Acceptance: Objective scan filed this gap for VAIOS-G724. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-555-objective-gap-3e00ad2a0074.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/hallucinate_app/44dceea6bc53; when practical, make one cohesive change that advances the packet goals (VAIOS-G724, VAIOS-G728) and covers the shared packet evidence without expanding the prompt. Refine the objective heap if the gap needs smaller child goals.

## MGW-556 Close objective gap: Hallucinate App daemon launch orchestration

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/daemon-launch-health.spec.ts
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts) && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-daemon-launch-orchestration
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-daemon-launch-orchestration.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/hallucinate-daemon-launch-orchestration
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G728
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App daemon launch health MCP server dashboard ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife
- AST query: hallucinate_app, daemon health, MCP server, MCP dashboard, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Surplus group: objective/VAIOS-G728
- Merge key: 7e544b4df4e28611
- Merge family: goal_packet/launch/hallucinate_app/44dceea6bc53
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G724, VAIOS-G728
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: e514497464ba6ea4
- Acceptance: Objective scan filed this gap for VAIOS-G728. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-556-objective-gap-b023c8de5b69.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/hallucinate_app/44dceea6bc53; when practical, make one cohesive change that advances the packet goals (VAIOS-G724, VAIOS-G728) and covers the shared packet evidence without expanding the prompt. Refine the objective heap if the gap needs smaller child goals.

## MGW-557 Resolve implementation retry-budget failure for MGW-547

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests, data/meta_glasses_display_widgets/state/discovery
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-28-mgw-557-mgw-547-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-547. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/state/discovery/2026-06-28-mgw-557-mgw-547-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-547 from strategy blocked_tasks.

## MGW-558 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-29-mgw-558-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-559 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-29-mgw-559-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-560 Resolve merge retry-budget failure for MGW-559

- Status: completed
- Completion: manual 2026-06-29: verified MGW-559 attempt 6 is merged in the superproject at `d438f06b`, repaired the original `external/ipfs_accelerate` dirty-checkout blocker by committing the owning submodule at `546dfdcd` and the superproject gitlink at `f8f0f42f`, synchronized the `hallucinate_app` launch-gate fixtures at `68d4f60`, and recorded that no semantic `ipfs-accelerate-agent-merge-resolver --apply` run was required because the retry-budget evidence was `main_checkout_dirty_conflict`.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-29-mgw-560-mgw-559-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-559. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-29-mgw-560-mgw-559-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-559 from strategy blocked_tasks.

## MGW-561 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-30-mgw-561-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-562 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-30-mgw-562-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-563 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-01-mgw-563-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-564 Close objective gap: Hallucinate App MCP dashboard capability catalog

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts, hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts
- Validation: npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard-capability-catalog
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard-capability-catalog.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/hallucinate-mcp-dashboard-capability-catalog
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G724
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App MCP dashboard dashboard capability catalog tools/list tools/call ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife Playwright
- AST query: hallucinate_app, swissknife, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py, tools/list, tools/call, daemon health, MCP dashboard
- Surplus group: objective/VAIOS-G724
- Merge key: 9a625fd9f839651a
- Merge family: goal_packet/launch/hallucinate_app/44dceea6bc53
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Goal packet role: packet_anchor
- Goal packet goals: VAIOS-G724, VAIOS-G728
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: 573509f5885861c3
- Acceptance: Objective scan filed this gap for VAIOS-G724. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-564-objective-gap-3e00ad2a0074.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/hallucinate_app/44dceea6bc53; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G724, VAIOS-G728) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-565 Close objective gap: Hallucinate App daemon launch orchestration

- Status: todo
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/daemon-launch-health.spec.ts
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts) && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-daemon-launch-orchestration
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-daemon-launch-orchestration.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/launch/hallucinate-daemon-launch-orchestration
- Conflict policy: prefer launch-critical integration evidence; use the LLM merge resolver when dashboard, daemon, or mobile control-plane edits conflict
- Goal id: VAIOS-G728
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App daemon launch health MCP server dashboard ipfs_accelerate_py ipfs_datasets_py ipfs_kit_py Swissknife
- AST query: hallucinate_app, daemon health, MCP server, MCP dashboard, ipfs_accelerate_py, ipfs_datasets_py, ipfs_kit_py
- Surplus group: objective/VAIOS-G728
- Merge key: 7e544b4df4e28611
- Merge family: goal_packet/launch/hallucinate_app/44dceea6bc53
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate; goal_subgoal_packet
- Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G724, VAIOS-G728
- Goal packet task count: 2
- Goal packet work item count: 2
- Candidate kind: validation_gate
- Todo vector key: e514497464ba6ea4
- Acceptance: Objective scan filed this gap for VAIOS-G728. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-565-objective-gap-b023c8de5b69.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/launch/hallucinate_app/44dceea6bc53; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G724, VAIOS-G728) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-566 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: completed
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-566-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-567 Resolve merge retry-budget failure for MGW-564

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, external/ipfs_accelerate, external/ipfs_datasets, external/ipfs_kit, hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts, hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-567-mgw-564-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-564. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-567-mgw-564-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-564 from strategy blocked_tasks.

## MGW-568 Resolve merge retry-budget failure for MGW-566

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-568-mgw-566-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-566. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-02-mgw-568-mgw-566-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-566 from strategy blocked_tasks.

## MGW-569 Close objective gap: Interoperate swissknife with mobile

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_swissknife_mobile_interop.py, docs/integration/swissknife-mobile.md, swissknife, mobile, mobile/src/orb/metaGlassesOrbDescriptors.js, mobile/src/utils/metaWearablesDatDisplayWidgetContract.js, swissknife/contracts/control_surface_contract.schema.json, swissknife/contracts/interaction_envelope.schema.json
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/swissknife-mobile
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-swissknife-mobile.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/swissknife-mobile
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G700
- Missing evidence: objective validation repair
- Embedding query: swissknife mobile interoperability integration test interface descriptor Bio PIL __future__ argparse asyncio base64 collections concurrent contextlib cross cross_browser_model_sharding dataclasses
- AST query: swissknife, mobile, interface contract, integration test, Bio, PIL, __future__, argparse, asyncio, base64, collections, concurrent, contextlib, cross, cross_browser_model_sharding, dataclasses
- Surplus group: objective/VAIOS-G700
- Merge key: 51d2d704bb124dec
- Merge family: goal_packet/interoperability/swissknife/06921590135c
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/swissknife/06921590135c
- Goal packet role: packet_anchor
- Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
- Goal packet task count: 7
- Goal packet work item count: 7
- Candidate kind: validation_gate
- Todo vector key: 6f5ab1cbfcdc3026
- Acceptance: Objective scan filed this gap for VAIOS-G700. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-569-objective-gap-d33307f93408.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/swissknife/06921590135c; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-570 Close objective gap: Interoperate swissknife with external/ipfs_accelerate

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_swissknife_external_ipfs_accelerate_interop.py, docs/integration/swissknife-external_ipfs_accelerate.md, swissknife, external/ipfs_accelerate, external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql, external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/swissknife-external_ipfs_accelerate
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-swissknife-external_ipfs_accelerate.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/swissknife-external_ipfs_accelerate
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G701
- Missing evidence: objective validation repair
- Embedding query: swissknife external/ipfs_accelerate interoperability integration test interface descriptor Bio PIL __future__ _jsonnet abc anyio argparse ast asyncio atexit base64 boto3
- AST query: swissknife, external/ipfs_accelerate, interface contract, integration test, Bio, PIL, __future__, _jsonnet, abc, anyio, argparse, ast, asyncio, atexit, base64, boto3
- Surplus group: objective/VAIOS-G701
- Merge key: 73a289c5baecf2dc
- Merge family: goal_packet/interoperability/swissknife/06921590135c
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/swissknife/06921590135c
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
- Goal packet task count: 7
- Goal packet work item count: 7
- Candidate kind: validation_gate
- Todo vector key: 7114ccc7230426cd
- Acceptance: Objective scan filed this gap for VAIOS-G701. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-570-objective-gap-2394e45d2012.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/swissknife/06921590135c; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-571 Close objective gap: Interoperate swissknife with external/ipfs_datasets

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_swissknife_external_ipfs_datasets_interop.py, docs/integration/swissknife-external_ipfs_datasets.md, swissknife, external/ipfs_datasets, external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json, external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/swissknife-external_ipfs_datasets
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-swissknife-external_ipfs_datasets.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/swissknife-external_ipfs_datasets
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G702
- Missing evidence: objective validation repair
- Embedding query: swissknife external/ipfs_datasets interoperability integration test interface descriptor Bio PIL __future__ _jsonnet abc anyio argparse ast asyncio atexit base64 boto3
- AST query: swissknife, external/ipfs_datasets, interface contract, integration test, Bio, PIL, __future__, _jsonnet, abc, anyio, argparse, ast, asyncio, atexit, base64, boto3
- Surplus group: objective/VAIOS-G702
- Merge key: 2c80d7fe82fec311
- Merge family: goal_packet/interoperability/swissknife/06921590135c
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/swissknife/06921590135c
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
- Goal packet task count: 7
- Goal packet work item count: 7
- Candidate kind: validation_gate
- Todo vector key: bf639e7f481bbb5a
- Acceptance: Objective scan filed this gap for VAIOS-G702. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-571-objective-gap-c21adb3eb488.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/swissknife/06921590135c; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-572 Close objective gap: Interoperate swissknife with external/ipfs_kit

- Status: completed
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_swissknife_external_ipfs_kit_interop.py, docs/integration/swissknife-external_ipfs_kit.md, swissknife, external/ipfs_kit, external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py, external/ipfs_kit/data/deprecations_report.schema.json
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/swissknife-external_ipfs_kit
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-swissknife-external_ipfs_kit.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/swissknife-external_ipfs_kit
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G703
- Missing evidence: objective validation repair
- Embedding query: swissknife external/ipfs_kit interoperability integration test interface descriptor Bio PIL __future__ aiofiles aiohttp anyio argparse ast asyncio atexit base64 binascii
- AST query: swissknife, external/ipfs_kit, interface contract, integration test, Bio, PIL, __future__, aiofiles, aiohttp, anyio, argparse, ast, asyncio, atexit, base64, binascii
- Surplus group: objective/VAIOS-G703
- Merge key: 5a95a3711a64a61f
- Merge family: goal_packet/interoperability/swissknife/06921590135c
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/swissknife/06921590135c
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
- Goal packet task count: 7
- Goal packet work item count: 7
- Candidate kind: validation_gate
- Todo vector key: 0756dbe3aed2c834
- Acceptance: Objective scan filed this gap for VAIOS-G703. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-572-objective-gap-f463532ba4e3.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/swissknife/06921590135c; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-573 Close objective gap: Interoperate swissknife with Mcp-Plus-Plus

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_swissknife_mcp_plus_plus_interop.py, docs/integration/swissknife-mcp_plus_plus.md, swissknife, Mcp-Plus-Plus, Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json, swissknife/contracts/control_surface_contract.schema.json, swissknife/contracts/interaction_envelope.schema.json, swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/swissknife-mcp_plus_plus
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-swissknife-mcp_plus_plus.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/swissknife-mcp_plus_plus
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G704
- Missing evidence: objective validation repair
- Embedding query: swissknife Mcp-Plus-Plus interoperability integration test interface descriptor Bio PIL __future__ argparse asyncio base64 collections concurrent contextlib cross cross_browser_model_sharding dataclasses
- AST query: swissknife, Mcp-Plus-Plus, interface contract, integration test, Bio, PIL, __future__, argparse, asyncio, base64, collections, concurrent, contextlib, cross, cross_browser_model_sharding, dataclasses
- Surplus group: objective/VAIOS-G704
- Merge key: 9221543d39ab1ebb
- Merge family: goal_packet/interoperability/swissknife/06921590135c
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/swissknife/06921590135c
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
- Goal packet task count: 7
- Goal packet work item count: 7
- Candidate kind: validation_gate
- Todo vector key: d3588c0baeb3a11e
- Acceptance: Objective scan filed this gap for VAIOS-G704. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-objective-gap-57359897bf4f.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/swissknife/06921590135c; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-574 Close objective gap: Interoperate swissknife with external/meta-wearables-dat-android

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py, docs/integration/swissknife-external_meta_wearables_dat_android.md, swissknife, external/meta-wearables-dat-android, swissknife/contracts/control_surface_contract.schema.json, swissknife/contracts/interaction_envelope.schema.json, swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json, swissknife/contracts/mediation_receipt.schema.json
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/swissknife-external_meta_wearables_dat_android
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-swissknife-external_meta_wearables_dat_android.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/swissknife-external_meta_wearables_dat_android
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G705
- Missing evidence: objective validation repair
- Embedding query: swissknife external/meta-wearables-dat-android interoperability integration test interface descriptor Bio PIL __future__ argparse asyncio base64 collections concurrent contextlib cross cross_browser_model_sharding dataclasses
- AST query: swissknife, external/meta-wearables-dat-android, interface contract, integration test, Bio, PIL, __future__, argparse, asyncio, base64, collections, concurrent, contextlib, cross, cross_browser_model_sharding, dataclasses
- Surplus group: objective/VAIOS-G705
- Merge key: 326e147a49d08a18
- Merge family: goal_packet/interoperability/swissknife/06921590135c
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/swissknife/06921590135c
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
- Goal packet task count: 7
- Goal packet work item count: 7
- Candidate kind: validation_gate
- Todo vector key: 1baf9e93bd03ee60
- Acceptance: Objective scan filed this gap for VAIOS-G705. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-574-objective-gap-73dd061c433c.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/swissknife/06921590135c; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-575 Close objective gap: Interoperate swissknife with external/meta-wearables-dat-ios

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop.py, docs/integration/swissknife-external_meta_wearables_dat_ios.md, swissknife, external/meta-wearables-dat-ios, swissknife/contracts/control_surface_contract.schema.json, swissknife/contracts/interaction_envelope.schema.json, swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json, swissknife/contracts/mediation_receipt.schema.json
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/swissknife-external_meta_wearables_dat_ios
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-swissknife-external_meta_wearables_dat_ios.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/swissknife-external_meta_wearables_dat_ios
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G706
- Missing evidence: objective validation repair
- Embedding query: swissknife external/meta-wearables-dat-ios interoperability integration test interface descriptor Bio PIL __future__ argparse asyncio base64 collections concurrent contextlib cross cross_browser_model_sharding dataclasses
- AST query: swissknife, external/meta-wearables-dat-ios, interface contract, integration test, Bio, PIL, __future__, argparse, asyncio, base64, collections, concurrent, contextlib, cross, cross_browser_model_sharding, dataclasses
- Surplus group: objective/VAIOS-G706
- Merge key: 5e04b98b01c0fac7
- Merge family: goal_packet/interoperability/swissknife/06921590135c
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/swissknife/06921590135c
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
- Goal packet task count: 7
- Goal packet work item count: 7
- Candidate kind: validation_gate
- Todo vector key: 7d62c199aa475d01
- Acceptance: Objective scan filed this gap for VAIOS-G706. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-575-objective-gap-d6bdae3a60cc.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/swissknife/06921590135c; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-576 Close objective gap: Interoperate external/meta-wearables-dat-android with external/ipfs_accelerate

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py, docs/integration/external_meta_wearables_dat_android-external_ipfs_accelerate.md, external/meta-wearables-dat-android, external/ipfs_accelerate, external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql, external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_accelerate
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-external_meta_wearables_dat_android-external_ipfs_accelerate.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_accelerate
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G709
- Missing evidence: objective validation repair
- Embedding query: external/meta-wearables-dat-android external/ipfs_accelerate interoperability integration test interface descriptor __future__ _jsonnet abc anyio argparse ast asyncio atexit base64 boto3 bs4 cProfile
- AST query: external/meta-wearables-dat-android, external/ipfs_accelerate, interface contract, integration test, __future__, _jsonnet, abc, anyio, argparse, ast, asyncio, atexit, base64, boto3, bs4, cProfile
- Surplus group: objective/VAIOS-G709
- Merge key: 84954eaa36d6bdab
- Merge family: goal_packet/interoperability/external/6595cbbfadb9
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/external/6595cbbfadb9
- Goal packet role: packet_anchor
- Goal packet goals: VAIOS-G709, VAIOS-G710, VAIOS-G711
- Goal packet task count: 3
- Goal packet work item count: 3
- Candidate kind: validation_gate
- Todo vector key: 7b1f274f3b485b7d
- Acceptance: Objective scan filed this gap for VAIOS-G709. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-576-objective-gap-56ff358535c4.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/external/6595cbbfadb9; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G709, VAIOS-G710, VAIOS-G711) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-577 Close objective gap: Interoperate external/meta-wearables-dat-android with external/ipfs_datasets

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py, docs/integration/external_meta_wearables_dat_android-external_ipfs_datasets.md, external/meta-wearables-dat-android, external/ipfs_datasets, external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json, external/ipfs_datasets/.tools/ipfs_kit_py/docs/implementation/BUCKET_VFS_INTERFACES_COMPLETE.md, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_bucket_vfs_interfaces.py, external/ipfs_datasets/.tools/ipfs_kit_py/examples/demo_unified_bucket_interface.py
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_datasets
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-external_meta_wearables_dat_android-external_ipfs_datasets.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_datasets
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G710
- Missing evidence: objective validation repair
- Embedding query: external/meta-wearables-dat-android external/ipfs_datasets interoperability integration test interface descriptor __future__ _jsonnet abc anyio argparse ast asyncio atexit base64 boto3 bs4 cProfile
- AST query: external/meta-wearables-dat-android, external/ipfs_datasets, interface contract, integration test, __future__, _jsonnet, abc, anyio, argparse, ast, asyncio, atexit, base64, boto3, bs4, cProfile
- Surplus group: objective/VAIOS-G710
- Merge key: a21f55ab34a02e7c
- Merge family: goal_packet/interoperability/external/6595cbbfadb9
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/external/6595cbbfadb9
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G709, VAIOS-G710, VAIOS-G711
- Goal packet task count: 3
- Goal packet work item count: 3
- Candidate kind: validation_gate
- Todo vector key: a08852876b7a22bb
- Acceptance: Objective scan filed this gap for VAIOS-G710. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-577-objective-gap-136ccea7b51c.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/external/6595cbbfadb9; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G709, VAIOS-G710, VAIOS-G711) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-578 Close objective gap: Interoperate external/meta-wearables-dat-android with external/ipfs_kit

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py, docs/integration/external_meta_wearables_dat_android-external_ipfs_kit.md, external/meta-wearables-dat-android, external/ipfs_kit, external/ipfs_kit/archive/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/archive_clutter/fix_scripts/fix_mcp_schema.py, external/ipfs_kit/backup/patches/fixes/fix_mcp_schema.py, external/ipfs_kit/data/deprecations_report.schema.json
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_kit
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-external_meta_wearables_dat_android-external_ipfs_kit.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/external_meta_wearables_dat_android-external_ipfs_kit
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G711
- Missing evidence: objective validation repair
- Embedding query: external/meta-wearables-dat-android external/ipfs_kit interoperability integration test interface descriptor __future__ aiofiles aiohttp anyio argparse ast atexit binascii boto3 botocore check_high_level_api_syntax collections
- AST query: external/meta-wearables-dat-android, external/ipfs_kit, interface contract, integration test, __future__, aiofiles, aiohttp, anyio, argparse, ast, atexit, binascii, boto3, botocore, check_high_level_api_syntax, collections
- Surplus group: objective/VAIOS-G711
- Merge key: a0a21995a64795d9
- Merge family: goal_packet/interoperability/external/6595cbbfadb9
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair; goal_subgoal_packet
- Goal packet: goal_packet/interoperability/external/6595cbbfadb9
- Goal packet role: packet_member
- Goal packet goals: VAIOS-G709, VAIOS-G710, VAIOS-G711
- Goal packet task count: 3
- Goal packet work item count: 3
- Candidate kind: validation_gate
- Todo vector key: 3ff7c962d8ab58b5
- Acceptance: Objective scan filed this gap for VAIOS-G711. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-578-objective-gap-853e023f8d1d.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap. This task is part of goal_packet/interoperability/external/6595cbbfadb9; implement a complete, cohesive change that fully advances the packet goals (VAIOS-G709, VAIOS-G710, VAIOS-G711) and covers all the shared packet evidence in one comprehensive pass. Refine the objective heap if the gap needs smaller child goals.

## MGW-579 Close objective gap: Interoperate hallucinate_app with mobile

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_hallucinate_app_mobile_interop.py, docs/integration/hallucinate_app-mobile.md, hallucinate_app, mobile, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql, hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/hallucinate_app-mobile
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-hallucinate_app-mobile.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/hallucinate_app-mobile
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G707
- Missing evidence: objective validation repair
- Embedding query: hallucinate_app mobile interoperability integration test interface descriptor __future__ _jsonnet abc anyio argparse ast asyncio atexit base64 both boto3 bs4
- AST query: hallucinate_app, mobile, interface contract, integration test, __future__, _jsonnet, abc, anyio, argparse, ast, asyncio, atexit, base64, both, boto3, bs4
- Surplus group: objective/VAIOS-G707
- Merge key: dce12a84320c8baf
- Merge family: objective/VAIOS-G707
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: c28bf5e5280df451
- Acceptance: Objective scan filed this gap for VAIOS-G707. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-579-objective-gap-7edb316279e5.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## MGW-580 Close objective gap: Interoperate mobile with external/ipfs_accelerate

- Status: todo
- Completion: manual
- Priority: P1
- Track: interoperability
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_mobile_external_ipfs_accelerate_interop.py, docs/integration/mobile-external_ipfs_accelerate.md, mobile, external/ipfs_accelerate, external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql, external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py
- Validation: python -m pytest tests/integration -q
- Bundle: objective/interoperability/mobile-external_ipfs_accelerate
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-interoperability-mobile-external_ipfs_accelerate.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G000
- Graph depth: 1
- Parallel lane: objective/interoperability/mobile-external_ipfs_accelerate
- Conflict policy: keep pair-specific integration edits isolated; use the LLM merge resolver for conflicts
- Goal id: VAIOS-G719
- Missing evidence: objective validation repair
- Embedding query: mobile external/ipfs_accelerate interoperability integration test interface descriptor __future__ _jsonnet abc anyio argparse ast asyncio atexit base64 boto3 bs4 cProfile
- AST query: mobile, external/ipfs_accelerate, interface contract, integration test, __future__, _jsonnet, abc, anyio, argparse, ast, asyncio, atexit, base64, boto3, bs4, cProfile
- Surplus group: objective/VAIOS-G719
- Merge key: 64e26db5b0fa2426
- Merge family: objective/VAIOS-G719
- Merge role: validation_gate
- Work item count: 1
- Work scope: objective_validation_repair
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: abd3dcae203fdb6b
- Acceptance: Objective scan filed this gap for VAIOS-G719. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-580-objective-gap-c1edafa875e6.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (objective validation repair), and keep the supervisor-fed backlog aligned with the objective heap.  Refine the objective heap if the gap needs smaller child goals.

## MGW-581 Close objective gap: Hallucinate MCP dashboard interoperability console

- Status: todo
- Completion: manual
- Priority: P0
- Track: launch
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, hallucinate_app, swissknife, docs/launch/phone_desktop_glasses_readiness.md, data/hallucinate_multimodal_control/discovery, tests
- Validation: PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py tests/test_virtual_ai_os_todo_queue.py -q; npm --prefix hallucinate_app run test:daemon-manager; npm --prefix hallucinate_app run test:e2e -- mcp-feature-exposure.spec.ts mcp-dashboard-interoperability.spec.ts; cd hallucinate_app && (env -u DISPLAY -u WAYLAND_DISPLAY HALLUCINATE_APP_E2E_NO_BOOTSTRAP=true node scripts/run_playwright_test.mjs --help || test $? -eq 78); npm --prefix swissknife run test:e2e:mcp && (test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses) && (test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts)
- Bundle: objective/launch/hallucinate-mcp-dashboard
- Bundle shard: data/meta_glasses_display_widgets/objective_bundles/objective-launch-hallucinate-mcp-dashboard.todo.md
- Bundle strategy: explicit
- Graph parents: VAIOS-G697
- Graph depth: 1
- Parallel lane: hallucinate-mcp-dashboard
- Conflict policy: keep Hallucinate App dashboard, daemon manager, and Swissknife catalog edits additive; preserve one shared catalog and one receipt schema when resolving parallel UI/test changes
- Goal id: VAIOS-G723
- Missing evidence: launch Playwright validation gate
- Embedding query: Hallucinate App menus dashboards MCP dashboard capability catalog daemon health tools/list tools/call ipfs_kit_py ipfs_datasets_py ipfs_accelerate_py Swissknife MCP++ Playwright launch interoperability
- AST query: MenuGenerator, mcpServers, dashboardMcpServers, getLaunchPlan, getDashboardCapabilityCatalog, mcp_daemon_manager, mcp-feature-exposure, mcp-dashboard-interoperability, ControlSurfaceInvocationGate
- Surplus group: objective/VAIOS-G723
- Merge key: 3997b2fdaa13d4a4
- Merge family: objective/VAIOS-G723
- Merge role: validation_gate
- Work item count: 1
- Work scope: launch_validation_gate
- Goal packet: 
- Goal packet role: 
- Goal packet goals: 
- Goal packet task count: 0
- Goal packet work item count: 0
- Candidate kind: validation_gate
- Todo vector key: 423c5c08373fafe1
- Acceptance: Objective scan filed this gap for VAIOS-G723. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-581-objective-gap-7ea369464239.md, add code/tests/docs or child goals that prove the missing evidence terms are covered (launch Playwright validation gate), and keep the supervisor-fed backlog aligned with the objective heap.  Add child goals for catalog normalization, dashboard UI wiring, mediated tool-call receipts, Swissknife consumers, Playwright coverage, and supervisor-generated follow-up subtasks if any dashboard or backend validation fails.

## MGW-582 Resolve validation retry-budget failure for MGW-579

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_hallucinate_app_mobile_interop.py, docs/integration/hallucinate_app-mobile.md, hallucinate_app, mobile, hallucinate_app/hallucinate_app/node/dashboard/content_browser/search_interface.js, hallucinate_app/hallucinate_app/node/views/test_interface.html, hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql, hallucinate_app/ipfs_accelerate_py/data/duckdb/scripts/create_benchmark_schema.py
- Validation: python -m pytest tests/integration -q
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-579. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-582-mgw-579-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-579 from strategy blocked_tasks.

## MGW-583 Resolve validation retry-budget failure for MGW-569

- Status: completed
- Completion: manual 2026-07-08: restored the missing external/Mcp-Plus-Plus Python validator package used by integration conformance tests, retagged Swissknife/mobile validation evidence from copied VAI-661 paths to MGW-569/MGW-583, recorded the repair discovery packet, removed MGW-569 from strategy blocked_tasks, and verified `python -m pytest tests/integration -q` passes.
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_swissknife_mobile_interop.py, docs/integration/swissknife-mobile.md, swissknife, mobile, mobile/src/orb/metaGlassesOrbDescriptors.js, mobile/src/utils/metaWearablesDatDisplayWidgetContract.js, swissknife/contracts/control_surface_contract.schema.json, swissknife/contracts/interaction_envelope.schema.json
- Validation: python -m pytest tests/integration -q
- Acceptance: Retry-budget guardrail filed this from repeated validation failures in MGW-569. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-583-mgw-569-retry-budget.md to fix the validation blocker, then mark this repair task completed so the supervisor can release MGW-569 from strategy blocked_tasks.

## MGW-584 Resolve merge retry-budget failure for MGW-580

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md, tests/integration/test_mobile_external_ipfs_accelerate_interop.py, docs/integration/mobile-external_ipfs_accelerate.md, mobile, external/ipfs_accelerate, external/ipfs_accelerate/data/duckdb/db_schema/time_series_schema.sql, external/ipfs_accelerate/data/duckdb/scripts/create_benchmark_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_database_schema.py, external/ipfs_accelerate/data/duckdb/utils/check_db_schema.py
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-584-mgw-580-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-580. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-584-mgw-580-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-580 from strategy blocked_tasks.
