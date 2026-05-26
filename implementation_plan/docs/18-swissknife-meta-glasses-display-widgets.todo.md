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
- Validation: cd mobile/android && env JAVA_HOME=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8 PATH=/home/barberb/lift_coding/.tools/jdk17/jdk-17.0.18+8/bin:$PATH ./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false
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
- Acceptance: After the initial backlog completes, investigate the Swissknife, HandsFree backend, mobile DAT bridge, external Meta DAT references, and hardware-free test harness code paths for missed work. Append new daemon-parseable MGW tasks for discovered gaps, or write a dated no-new-unknowns discovery report with evidence and commands run.

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

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md:24. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-25-mgw-021-codebase-scan-55c0165aa8e2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

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

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-053-resolution.md
- Validation: test -f data/hallucinate_multimodal_control/discovery/2026-05-25-hao-053-resolution.md
- Acceptance: Codebase scan filed this finding from data/hallucinate_multimodal_control/discovery/2026-05-25-hao-053-resolution.md:10. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-25-mgw-024-codebase-scan-5ebb02bc2f3e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-025 Resolve merge retry-budget failure for MGW-020

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-025-implementation-unknowns.md
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'MGW-020'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-020. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-025-mgw-020-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove MGW-020 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## MGW-026 Resolve merge retry-budget failure for MGW-021

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'MGW-021'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-021. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-026-mgw-021-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove MGW-021 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## MGW-027 Resolve merge retry-budget failure for MGW-022

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-044-hao-042-merge-unblock.md
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'MGW-022'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-022. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-027-mgw-022-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove MGW-022 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## MGW-028 Resolve merge retry-budget failure for MGW-023

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-051-resolution.md
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'MGW-023'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-023. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-028-mgw-023-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove MGW-023 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## MGW-029 Resolve merge retry-budget failure for MGW-024

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-053-resolution.md
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'MGW-024'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-024. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-029-mgw-024-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove MGW-024 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## MGW-030 Resolve merge retry-budget failure for MGW-026

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-041-validation-unblock.md
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'MGW-026'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-026. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-030-mgw-026-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove MGW-026 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## MGW-031 Resolve merge retry-budget failure for MGW-027

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-044-hao-042-merge-unblock.md
- Validation: python3 -c 'exec("import json, pathlib\nstrategy = json.loads(pathlib.Path('"'"'/home/barberb/lift_coding/data/meta_glasses_display_widgets/state/meta_glasses_display_strategy.json'"'"').read_text(encoding='"'"'utf-8'"'"'))\nassert '"'"'MGW-027'"'"' not in strategy.get('"'"'blocked_tasks'"'"', [])")'
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-027. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-031-mgw-027-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then remove MGW-027 from the strategy blocked_tasks list so the original backlog item can continue without an indefinite retry loop.

## MGW-032 Resolve implementation retry-budget failure for MGW-028

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/hallucinate_multimodal_control/discovery/2026-05-25-hao-051-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-032-mgw-028-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-028. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-032-mgw-028-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-028 from strategy blocked_tasks.
