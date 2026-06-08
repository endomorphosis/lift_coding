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

- Status: completed
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

- Status: completed
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

## MGW-033 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-unblock.md:11

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-unblock.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-unblock.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-unblock.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-033-codebase-scan-693c6508faa9.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-034 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-unblock.md:18

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-unblock.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-unblock.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-26-vai-027-vai-019-merge-unblock.md:18. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-034-codebase-scan-806430f05751.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-035 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-unblock.md:13

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-unblock.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-unblock.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-unblock.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-035-codebase-scan-b4023560fbdd.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-036 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-unblock.md:26

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-unblock.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-unblock.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-26-vai-028-vai-020-merge-unblock.md:26. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-036-codebase-scan-ff1cd3f4e0b7.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-037 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-26-vai-031-vai-026-merge-unblock.md:11

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-26-vai-031-vai-026-merge-unblock.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-26-vai-031-vai-026-merge-unblock.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-26-vai-031-vai-026-merge-unblock.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-037-codebase-scan-5fb02bb41fbf.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-038 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-26-vai-032-vai-028-merge-unblock.md:13

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-26-vai-032-vai-028-merge-unblock.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-26-vai-032-vai-028-merge-unblock.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-26-vai-032-vai-028-merge-unblock.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-038-codebase-scan-ad4e36b82b97.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-039 Resolve code annotation in data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-22.md:16

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-22.md
- Validation: test -f data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-22.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-22.md:16. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-039-codebase-scan-7f82c7dc3d74.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-040 Review swallowed exception path in src/handsfree/ipfs_kit_adapters.py:347

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/ipfs_kit_adapters.py
- Validation: python3 -m py_compile src/handsfree/ipfs_kit_adapters.py
- Acceptance: Codebase scan filed this finding from src/handsfree/ipfs_kit_adapters.py:347. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-040-codebase-scan-6b0df05ca4a0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-041 Replace placeholder runtime path in src/handsfree/ocr/stub_provider.py:38

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/ocr/stub_provider.py
- Validation: python3 -m py_compile src/handsfree/ocr/stub_provider.py
- Acceptance: Codebase scan filed this finding from src/handsfree/ocr/stub_provider.py:38. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-041-codebase-scan-914627da8285.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-042 Review swallowed exception path in src/handsfree/peer_chat.py:122

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/peer_chat.py
- Validation: python3 -m py_compile src/handsfree/peer_chat.py
- Acceptance: Codebase scan filed this finding from src/handsfree/peer_chat.py:122. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-042-codebase-scan-e0404f01baad.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-043 Review swallowed exception path in src/handsfree/redis_client.py:77

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/redis_client.py
- Validation: python3 -m py_compile src/handsfree/redis_client.py
- Acceptance: Codebase scan filed this finding from src/handsfree/redis_client.py:77. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-043-codebase-scan-7a1ac1883655.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-044 Review swallowed exception path in src/handsfree/sessions.py:229

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/sessions.py
- Validation: python3 -m py_compile src/handsfree/sessions.py
- Acceptance: Codebase scan filed this finding from src/handsfree/sessions.py:229. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-044-codebase-scan-b1039b93eb48.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-045 Replace placeholder runtime path in src/handsfree/stt/stub_provider.py:42

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/stt/stub_provider.py
- Validation: python3 -m py_compile src/handsfree/stt/stub_provider.py
- Acceptance: Codebase scan filed this finding from src/handsfree/stt/stub_provider.py:42. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-045-codebase-scan-b40c594b84b1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-046 Review swallowed exception path in src/handsfree/transport/libp2p_bluetooth.py:1244

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, src/handsfree/transport/libp2p_bluetooth.py
- Validation: python3 -m py_compile src/handsfree/transport/libp2p_bluetooth.py
- Acceptance: Codebase scan filed this finding from src/handsfree/transport/libp2p_bluetooth.py:1244. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-046-codebase-scan-74ff113b87c6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-047 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:13

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-047-codebase-scan-cfe0d4fe2a26.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-048 Replace placeholder runtime path in data/virtual_ai_os/discovery/2026-05-26-vai-045-resolution.md:9

- Status: completed
- Completion: manual
- Priority: P1
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-26-vai-045-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-26-vai-045-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-26-vai-045-resolution.md:9. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-048-codebase-scan-9477780ff54f.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-049 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:110

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:110. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-049-codebase-scan-9e6407080e55.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-050 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:149

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:149. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-050-codebase-scan-113fa6a2035a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-051 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:159

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:159. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-051-codebase-scan-0886ebe3b4a6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-052 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:188

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:188. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-052-codebase-scan-acbf277a215b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-053 Resolve dependency guardrail for MGW-048

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-053-dependency-guardrail.md
- Acceptance: Dependency guardrail filed this because MGW-048 has missing, self-referential, cyclic, or duplicate task-id metadata. Use the evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-053-dependency-guardrail.md to repair the todo board metadata or add the missing prerequisite task, then verify the original task can become ready once its real dependencies complete.

## MGW-054 Resolve dependency guardrail for MGW-049

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-054-dependency-guardrail.md
- Acceptance: Dependency guardrail filed this because MGW-049 has missing, self-referential, cyclic, or duplicate task-id metadata. Use the evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-054-dependency-guardrail.md to repair the todo board metadata or add the missing prerequisite task, then verify the original task can become ready once its real dependencies complete.

## MGW-055 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:267

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:267. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-055-codebase-scan-733817068892.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-056 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:355

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:355. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-056-codebase-scan-bfdf8c8d6101.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-057 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:375

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:375. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-057-codebase-scan-cd77c93b537e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-058 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:536

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:536. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-058-codebase-scan-9b4272e295ff.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-059 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:555

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:555. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-059-codebase-scan-d4dff9e91d68.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-060 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:604

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:604. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-060-codebase-scan-ed0eacf2c1e0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-061 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:609

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:609. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-061-codebase-scan-56be23fb68eb.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-062 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:614

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:614. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-062-codebase-scan-5a5d7575aa1d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-063 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:620

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:620. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-063-codebase-scan-0857aa9175ad.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-064 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:621

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:621. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-064-codebase-scan-a5472eeb1373.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-065 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:658

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:658. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-065-codebase-scan-001cb9133cf2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-066 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:789

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:789. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-066-codebase-scan-b43023aacb4e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-067 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:805

- Status: completed
- Completion: manual
- Priority: P2
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:805. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-067-codebase-scan-a0a0a8322d54.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-068 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:807

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:807. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-068-codebase-scan-5140fcf09a78.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-069 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:811

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:811. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-069-codebase-scan-61100d34bad2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-070 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:877

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:877. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-070-codebase-scan-9b10aebbda3b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-071 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:917

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:917. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-071-codebase-scan-e2226ae85245.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-072 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:953

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:953. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-072-codebase-scan-085efe1dec11.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-073 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:970

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:970. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-073-codebase-scan-281e3fc47920.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-074 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1022

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1022. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-074-codebase-scan-a13f54fcc8a8.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-075 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1077

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1077. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-075-codebase-scan-7d61e2dbf380.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-076 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1122

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1122. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-076-codebase-scan-d3c194c9a502.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-077 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1151

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1151. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-077-codebase-scan-a09b28c44b13.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-078 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1207

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1207. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-078-codebase-scan-2f1ae855af90.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-079 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1290

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1290. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-079-codebase-scan-17564903e9a4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-080 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1358

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1358. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-080-codebase-scan-aab0f3427c80.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-081 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1364

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1364. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-081-codebase-scan-32731d81765a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-082 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1369

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1369. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-082-codebase-scan-5e4940c0b2f4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-083 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1375

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1375. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-083-codebase-scan-2b5db7864878.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-084 Resolve code annotation in tests/test_hallucinate_multimodal_control_todo_queue.py:1443

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: python3 -m py_compile tests/test_hallucinate_multimodal_control_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_hallucinate_multimodal_control_todo_queue.py:1443. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-084-codebase-scan-bbf696f672cc.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-085 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:14

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_meta_glasses_display_todo_queue.py
- Validation: python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_meta_glasses_display_todo_queue.py:14. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-085-codebase-scan-f33ba3deb8e3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-086 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:79

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_meta_glasses_display_todo_queue.py
- Validation: python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_meta_glasses_display_todo_queue.py:79. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-086-codebase-scan-94b03405a362.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-087 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:150

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_meta_glasses_display_todo_queue.py
- Validation: python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_meta_glasses_display_todo_queue.py:150. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-087-codebase-scan-2776ff4a6e63.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-088 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:156

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_meta_glasses_display_todo_queue.py
- Validation: python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_meta_glasses_display_todo_queue.py:156. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-088-codebase-scan-8ecf27f2c989.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-089 Resolve code annotation in tests/test_meta_glasses_display_todo_queue.py:179

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_meta_glasses_display_todo_queue.py
- Validation: python3 -m py_compile tests/test_meta_glasses_display_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_meta_glasses_display_todo_queue.py:179. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-26-mgw-089-codebase-scan-2147ab0540df.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-090 Replace placeholder runtime path in tests/test_notification_delivery.py:16

- Status: completed
- Completion: manual
- Priority: P1
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_notification_delivery.py
- Validation: python3 -m py_compile tests/test_notification_delivery.py
- Acceptance: Codebase scan filed this finding from tests/test_notification_delivery.py:16. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-090-codebase-scan-7ea0a035e91b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-091 Resolve code annotation in tests/test_virtual_ai_os_end_to_end.py:140

- Status: todo
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_end_to_end.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_end_to_end.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_end_to_end.py:140. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-091-codebase-scan-43df8518618b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-092 Resolve code annotation in tests/test_virtual_ai_os_end_to_end.py:169

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_end_to_end.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_end_to_end.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_end_to_end.py:169. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-092-codebase-scan-b52448303122.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-093 Resolve code annotation in tests/test_virtual_ai_os_end_to_end.py:170

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_end_to_end.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_end_to_end.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_end_to_end.py:170. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-093-codebase-scan-38d32e5240d3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-094 Resolve code annotation in tests/test_virtual_ai_os_end_to_end.py:228

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_end_to_end.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_end_to_end.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_end_to_end.py:228. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-094-codebase-scan-9da25a3fe7ab.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-095 Resolve code annotation in tests/test_virtual_ai_os_task_orchestration.py:69

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_task_orchestration.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_task_orchestration.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_task_orchestration.py:69. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-095-codebase-scan-e9739c3e25ee.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-096 Resolve code annotation in tests/test_virtual_ai_os_task_orchestration.py:99

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_task_orchestration.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_task_orchestration.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_task_orchestration.py:99. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-096-codebase-scan-c270de6a3cd0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-097 Resolve code annotation in tests/test_virtual_ai_os_task_orchestration.py:111

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_task_orchestration.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_task_orchestration.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_task_orchestration.py:111. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-097-codebase-scan-352e1337216e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-098 Resolve code annotation in tests/test_virtual_ai_os_todo_queue.py:12

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_todo_queue.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_todo_queue.py:12. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-098-codebase-scan-4f48f7ac5f3e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-099 Resolve code annotation in tests/test_virtual_ai_os_todo_queue.py:109

- Status: completed
- Completion: manual
- Priority: P3
- Track: quality
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tests/test_virtual_ai_os_todo_queue.py
- Validation: python3 -m py_compile tests/test_virtual_ai_os_todo_queue.py
- Acceptance: Codebase scan filed this finding from tests/test_virtual_ai_os_todo_queue.py:109. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-099-codebase-scan-6955fef82baf.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-100 Resolve code annotation in tracking/PR-049-ios-glasses-player.md:20

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-049-ios-glasses-player.md
- Validation: test -f tracking/PR-049-ios-glasses-player.md
- Acceptance: Codebase scan filed this finding from tracking/PR-049-ios-glasses-player.md:20. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-100-codebase-scan-96a924114f2f.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-101 Resolve code annotation in tracking/PR-050-android-audio-route-monitor.md:18

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-050-android-audio-route-monitor.md
- Validation: test -f tracking/PR-050-android-audio-route-monitor.md
- Acceptance: Codebase scan filed this finding from tracking/PR-050-android-audio-route-monitor.md:18. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-101-codebase-scan-83311bfea1d3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-102 Resolve code annotation in tracking/PR-051-android-glasses-recorder-player.md:21

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-051-android-glasses-recorder-player.md
- Validation: test -f tracking/PR-051-android-glasses-recorder-player.md
- Acceptance: Codebase scan filed this finding from tracking/PR-051-android-glasses-recorder-player.md:21. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-102-codebase-scan-d61ca3057077.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-103 Resolve code annotation in tracking/PR-052-glasses-js-integration-tts.md:26

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-052-glasses-js-integration-tts.md
- Validation: test -f tracking/PR-052-glasses-js-integration-tts.md
- Acceptance: Codebase scan filed this finding from tracking/PR-052-glasses-js-integration-tts.md:26. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-103-codebase-scan-27b8b4431606.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-104 Resolve code annotation in tracking/PR-079-agent-runner-minimal.md:7

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-079-agent-runner-minimal.md
- Validation: test -f tracking/PR-079-agent-runner-minimal.md
- Acceptance: Codebase scan filed this finding from tracking/PR-079-agent-runner-minimal.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-104-codebase-scan-fbadc1c37e4e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-105 Resolve code annotation in tracking/PR-079-agent-runner-minimal.md:7

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-079-agent-runner-minimal.md
- Validation: test -f tracking/PR-079-agent-runner-minimal.md
- Acceptance: Codebase scan filed this finding from tracking/PR-079-agent-runner-minimal.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-105-codebase-scan-e84a8c85ab29.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-106 Resolve code annotation in tracking/PR-079-agent-runner-minimal.md:16

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-079-agent-runner-minimal.md
- Validation: test -f tracking/PR-079-agent-runner-minimal.md
- Acceptance: Codebase scan filed this finding from tracking/PR-079-agent-runner-minimal.md:16. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-106-codebase-scan-d65e6d946f62.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-107 Resolve code annotation in tracking/PR-079-agent-runner-minimal.md:35

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-079-agent-runner-minimal.md
- Validation: test -f tracking/PR-079-agent-runner-minimal.md
- Acceptance: Codebase scan filed this finding from tracking/PR-079-agent-runner-minimal.md:35. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-107-codebase-scan-13883aa045ec.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-108 Resolve code annotation in tracking/PR-081-privacy-mode-per-profile.md:7

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-081-privacy-mode-per-profile.md
- Validation: test -f tracking/PR-081-privacy-mode-per-profile.md
- Acceptance: Codebase scan filed this finding from tracking/PR-081-privacy-mode-per-profile.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-108-codebase-scan-d0d2e565dde4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-109 Resolve code annotation in tracking/PR-083-android-expo-glasses-audio-wav-playback.md:7

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, tracking/PR-083-android-expo-glasses-audio-wav-playback.md
- Validation: test -f tracking/PR-083-android-expo-glasses-audio-wav-playback.md
- Acceptance: Codebase scan filed this finding from tracking/PR-083-android-expo-glasses-audio-wav-playback.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-109-codebase-scan-587ddb056b2b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-110 Resolve code annotation in work/PR-047-ios-audio-route-monitor.md:14

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, work/PR-047-ios-audio-route-monitor.md
- Validation: test -f work/PR-047-ios-audio-route-monitor.md
- Acceptance: Codebase scan filed this finding from work/PR-047-ios-audio-route-monitor.md:14. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-110-codebase-scan-98ff09f42056.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-111 Resolve code annotation in work/PR-048-ios-glasses-recorder-wav.md:14

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, work/PR-048-ios-glasses-recorder-wav.md
- Validation: test -f work/PR-048-ios-glasses-recorder-wav.md
- Acceptance: Codebase scan filed this finding from work/PR-048-ios-glasses-recorder-wav.md:14. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-111-codebase-scan-841f4db539b0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-112 Resolve code annotation in work/PR-081-privacy-mode-per-profile.md:18

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, work/PR-081-privacy-mode-per-profile.md
- Validation: test -f work/PR-081-privacy-mode-per-profile.md
- Acceptance: Codebase scan filed this finding from work/PR-081-privacy-mode-per-profile.md:18. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-112-codebase-scan-6dfbe572b893.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-113 Resolve code annotation in work/PR-090-agent-runner-docs-sync.md:1

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, work/PR-090-agent-runner-docs-sync.md
- Validation: test -f work/PR-090-agent-runner-docs-sync.md
- Acceptance: Codebase scan filed this finding from work/PR-090-agent-runner-docs-sync.md:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-113-codebase-scan-9b624a3cfffc.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-114 Resolve code annotation in work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md:180

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md
- Validation: test -f work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md
- Acceptance: Codebase scan filed this finding from work/REMAINING_GAPS_AND_PR_INSTRUCTIONS.md:180. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-114-codebase-scan-4b6fa8e6e4e8.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-115 Resolve code annotation in hallucinate_app/MENU_STRUCTURE.md:11

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/MENU_STRUCTURE.md
- Validation: test -f hallucinate_app/MENU_STRUCTURE.md
- Acceptance: Codebase scan filed this finding from hallucinate_app/MENU_STRUCTURE.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-115-codebase-scan-adf5c0aa0a20.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-116 Resolve code annotation in hallucinate_app/docs/INDEX.md:24

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/docs/INDEX.md
- Validation: test -f hallucinate_app/docs/INDEX.md
- Acceptance: Codebase scan filed this finding from hallucinate_app/docs/INDEX.md:24. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-116-codebase-scan-58d2ea49839a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-117 Resolve code annotation in hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md:3

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md
- Validation: test -f hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md
- Acceptance: Codebase scan filed this finding from hallucinate_app/docs/MULTIMODAL_CONTROL_SURFACE_LOGIC_IDL.md:3. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-117-codebase-scan-b52e44553a92.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-118 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/SUPPORT.md:1

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/SUPPORT.md
- Validation: test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/SUPPORT.md
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/SUPPORT.md:1. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-118-codebase-scan-b9a9faa1f210.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-119 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/webnn/efficientnet-lite4/config.json:490

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/webnn/efficientnet-lite4/config.json
- Validation: python3 -m json.tool hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/webnn/efficientnet-lite4/config.json >/dev/null
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/image-classification/models/webnn/efficientnet-lite4/config.json:490. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-119-codebase-scan-7360c608d6cd.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-120 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-27-vai-100-resolution.md:11

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-27-vai-100-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-27-vai-100-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-27-vai-100-resolution.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-120-codebase-scan-7bcebb35f4e4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-121 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js:874

- Status: todo
- Completion: manual
- Priority: P3
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js
- Validation: test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/stable-diffusion-1.5/index.js:874. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-121-codebase-scan-a73074e556ec.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-122 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js:52

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js
- Validation: test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/generation_utils.js:52. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-122-codebase-scan-af1c8f84f823.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-123 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/static/js/audioMotion-analyzer.js:1257

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/static/js/audioMotion-analyzer.js
- Validation: test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/static/js/audioMotion-analyzer.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/static/js/audioMotion-analyzer.js:1257. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-123-codebase-scan-fbaaa894a103.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-124 Resolve code annotation in hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/whisper.js:232

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/whisper.js
- Validation: test -f hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/whisper.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/experiments/webnn-developer-preview/demos/whisper-base/whisper.js:232. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-124-codebase-scan-249bb3d996f7.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-125 Resolve code annotation in hallucinate_app/hallucinate_app/node/dashboard/auth_dashboard.js:1167

- Status: todo
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/auth_dashboard.js
- Validation: test -f hallucinate_app/hallucinate_app/node/dashboard/auth_dashboard.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/dashboard/auth_dashboard.js:1167. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-125-codebase-scan-b703c77d6df0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-126 Resolve code annotation in hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js:663

- Status: todo
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Validation: test -f hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js:663. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-126-codebase-scan-43d9c2282080.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-127 Resolve code annotation in hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js:677

- Status: todo
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Validation: test -f hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js:677. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-127-codebase-scan-da82d68a141b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-128 Resolve code annotation in hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js:856

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Validation: test -f hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js:856. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-128-codebase-scan-8e7612d2b02c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-129 Resolve code annotation in hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js:1304

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Validation: test -f hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js:1304. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-129-codebase-scan-c2481cea1af4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-130 Resolve merge retry-budget failure for MGW-125

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/auth_dashboard.js
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-130-mgw-125-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-125. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-130-mgw-125-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-125 from strategy blocked_tasks.

## MGW-131 Resolve merge retry-budget failure for MGW-126

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-131-mgw-126-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-126. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-131-mgw-126-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-126 from strategy blocked_tasks.

## MGW-132 Resolve merge retry-budget failure for MGW-130

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/auth_dashboard.js
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-132-mgw-130-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-130. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-132-mgw-130-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-130 from strategy blocked_tasks.

## MGW-133 Resolve merge retry-budget failure for MGW-127

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/dashboard/security/security_panel.js
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-133-mgw-127-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-127. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-27-mgw-133-mgw-127-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-127 from strategy blocked_tasks.

## MGW-134 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:421

- Status: todo
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/menu_generator.js
- Validation: test -f hallucinate_app/hallucinate_app/node/menu_generator.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/menu_generator.js:421. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-134-codebase-scan-dc01283308ea.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-135 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:433

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/menu_generator.js
- Validation: test -f hallucinate_app/hallucinate_app/node/menu_generator.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/menu_generator.js:433. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-135-codebase-scan-616298b7fd51.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-136 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:439

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/menu_generator.js
- Validation: test -f hallucinate_app/hallucinate_app/node/menu_generator.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/menu_generator.js:439. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-136-codebase-scan-8b095211ac35.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-137 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:444

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/menu_generator.js
- Validation: test -f hallucinate_app/hallucinate_app/node/menu_generator.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/menu_generator.js:444. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-137-codebase-scan-049d1ee62326.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-138 Resolve code annotation in hallucinate_app/hallucinate_app/node/menu_generator.js:449

- Status: completed
- Completion: manual
- Priority: P3
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/node/menu_generator.js
- Validation: test -f hallucinate_app/hallucinate_app/node/menu_generator.js
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/node/menu_generator.js:449. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-138-codebase-scan-924df9ad9af7.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-139 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md:8

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md:8. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-139-codebase-scan-b5eb73958205.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-140 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md:9

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md:9. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-140-codebase-scan-07a5da531281.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-141 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md:15

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-110-resolution.md:15. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-141-codebase-scan-dc8f41e77400.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-142 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:8

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:8. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-142-codebase-scan-7af98f5b9f1b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-143 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:9

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:9. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-143-codebase-scan-1358e4f052cd.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-144 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:9

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:9. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-144-codebase-scan-cc97d1a5184d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-145 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:11

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-145-codebase-scan-c2172d26ed8e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-146 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:16

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-111-resolution-notes.md:16. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-146-codebase-scan-2c458f92c554.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-147 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-112-resolution.md:9

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-112-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-112-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-112-resolution.md:9. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-147-codebase-scan-4125b0dad9ea.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-148 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-112-resolution.md:14

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-112-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-112-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-112-resolution.md:14. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-148-codebase-scan-29b0ee13e826.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-149 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-113-resolution.md:9

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-113-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-113-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-113-resolution.md:9. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-149-codebase-scan-a37583185a60.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-150 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-113-resolution.md:47

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-113-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-113-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-113-resolution.md:47. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-150-codebase-scan-ee03c0f1168e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-151 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:12

- Status: done
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:12. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-151-codebase-scan-1319c934ae21.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-152 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:14

- Status: todo
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:14. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-152-codebase-scan-9b674961bf69.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-153 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:23

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:23. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-153-codebase-scan-f66b1bb020b3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-154 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:15

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-114-resolution.md:15. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-154-codebase-scan-6c2f0210fbe0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-155 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-115-resolution.md:20

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-115-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-115-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-115-resolution.md:20. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-155-codebase-scan-97a05be9ef11.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-156 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-116-resolution.md:11

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-116-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-116-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-116-resolution.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-156-codebase-scan-a624e94e4795.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-157 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:9

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:9. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-157-codebase-scan-8c1a125f6071.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-158 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:11

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-158-codebase-scan-6ccf495c3e3c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-159 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-159-codebase-scan-d80c02149e48.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-160 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:16

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-117-resolution.md:16. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-160-codebase-scan-b163add98dbd.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-161 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md:11

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-161-codebase-scan-e738b61b41a6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-162 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-162-codebase-scan-c292469b1301.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-163 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md:17

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-163-codebase-scan-92bf23562ca9.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-164 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md:13

- Status: todo
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-118-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-164-codebase-scan-9006ca71fa45.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-165 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md:10

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md:10. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-165-codebase-scan-e7b5e04e30c7.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-166 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md:11

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-119-resolution.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-166-codebase-scan-a83ddc64fab6.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-167 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:15

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:15. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-167-codebase-scan-12546a480492.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-168 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:36

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:36. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-28-mgw-168-codebase-scan-3e99d3a38aeb.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-169 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md:15

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md:15. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-169-codebase-scan-3022a5796138.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-170 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md:17

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-170-codebase-scan-e8e0ebaa1820.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-171 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md:30

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md:30. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-171-codebase-scan-75f6e1527b28.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-172 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-123-resolution.md:9

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-123-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-123-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-123-resolution.md:9. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-172-codebase-scan-781ecdeb0f7d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-173 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-124-resolution.md:16

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-124-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-124-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-124-resolution.md:16. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-173-codebase-scan-12a56b11e733.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-174 Resolve implementation retry-budget failure for MGW-169

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-174-mgw-169-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-169. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-174-mgw-169-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-169 from strategy blocked_tasks.

## MGW-175 Resolve merge retry-budget failure for MGW-174

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-122-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-175-mgw-174-merge-retry-budget.md
- Acceptance: Merge retry-budget guardrail filed this from repeated merge failures in MGW-174. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-175-mgw-174-merge-retry-budget.md to fix the merge blocker, verify the intended implementation changes are committed in their owning repository or submodule, run `ipfs-accelerate-agent-merge-resolver --events-path ... --apply` when the conflict is semantic, then mark this repair task completed so the supervisor can release MGW-174 from strategy blocked_tasks.

## MGW-176 Resolve implementation retry-budget failure for MGW-173

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-124-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-176-mgw-173-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-173. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-176-mgw-173-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-173 from strategy blocked_tasks.

## MGW-177 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:11

- Status: todo
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-177-codebase-scan-dff7136c9adb.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-178 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:301

- Status: todo
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, scripts/hallucinate_multimodal_control_todo_supervisor.py
- Validation: python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
- Acceptance: Codebase scan filed this finding from scripts/hallucinate_multimodal_control_todo_supervisor.py:301. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-178-codebase-scan-7d52a8f929c8.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-179 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:303

- Status: completed
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, scripts/hallucinate_multimodal_control_todo_supervisor.py
- Validation: python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
- Acceptance: Codebase scan filed this finding from scripts/hallucinate_multimodal_control_todo_supervisor.py:303. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-179-codebase-scan-fbd7ce184cdf.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-180 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:283

- Status: completed
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Validation: python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:283. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-180-codebase-scan-46e73526b874.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-181 Review swallowed exception path in hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:338

- Status: todo
- Completion: manual
- Priority: P1
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Validation: python3 -m py_compile hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Acceptance: Codebase scan filed this finding from hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py:338. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-181-codebase-scan-96df5fcdd59e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-182 Resolve implementation retry-budget failure for MGW-181

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-182-mgw-181-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-181. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-182-mgw-181-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-181 from strategy blocked_tasks.

## MGW-183 Resolve implementation retry-budget failure for MGW-182

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-183-mgw-182-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-182. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-183-mgw-182-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-182 from strategy blocked_tasks.

## MGW-184 Resolve implementation retry-budget failure for MGW-183

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-184-mgw-183-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-183. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-184-mgw-183-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-183 from strategy blocked_tasks.

## MGW-185 Resolve implementation retry-budget failure for MGW-184

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-185-mgw-184-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-184. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-185-mgw-184-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-184 from strategy blocked_tasks.

## MGW-186 Resolve implementation retry-budget failure for MGW-185

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-186-mgw-185-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-185. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-186-mgw-185-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-185 from strategy blocked_tasks.

## MGW-187 Resolve implementation retry-budget failure for MGW-186

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, hallucinate_app/hallucinate_app/python/hallucinate_app/ipfs_model_manager.py
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-187-mgw-186-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-186. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-30-mgw-187-mgw-186-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-186 from strategy blocked_tasks.

## MGW-188 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: todo
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-188-codebase-scan-929aa289911e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-189 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:304

- Status: completed
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, scripts/hallucinate_multimodal_control_todo_supervisor.py
- Validation: python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
- Acceptance: Codebase scan filed this finding from scripts/hallucinate_multimodal_control_todo_supervisor.py:304. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-189-codebase-scan-9f8f16918698.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-190 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:305

- Status: todo
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, scripts/hallucinate_multimodal_control_todo_supervisor.py
- Validation: python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
- Acceptance: Codebase scan filed this finding from scripts/hallucinate_multimodal_control_todo_supervisor.py:305. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-190-codebase-scan-969bf9b8ee48.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-191 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:307

- Status: todo
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, scripts/hallucinate_multimodal_control_todo_supervisor.py
- Validation: python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
- Acceptance: Codebase scan filed this finding from scripts/hallucinate_multimodal_control_todo_supervisor.py:307. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-191-codebase-scan-06466d54cc2a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-192 Resolve code annotation in scripts/hallucinate_multimodal_control_todo_supervisor.py:308

- Status: completed
- Completion: manual
- Priority: P3
- Track: runtime
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, scripts/hallucinate_multimodal_control_todo_supervisor.py
- Validation: python3 -m py_compile scripts/hallucinate_multimodal_control_todo_supervisor.py
- Acceptance: Codebase scan filed this finding from scripts/hallucinate_multimodal_control_todo_supervisor.py:308. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-192-codebase-scan-c0b8d370e688.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-193 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-193-codebase-scan-afa610afba71.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-194 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:20

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:20. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-194-codebase-scan-b88972cdf755.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-195 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:18

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:18. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-195-codebase-scan-5963f47aa38e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-196 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:11

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:11. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-196-codebase-scan-37557cc8dc64.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-197 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:12

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:12. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-197-codebase-scan-e90585996588.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-198 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-198-codebase-scan-1b7e7fc3aefe.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-199 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:20

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:20. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-199-codebase-scan-9d74607d993a.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-200 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:18

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:18. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-200-codebase-scan-cbc7c82cd83e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-201 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-201-codebase-scan-33582516e040.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-202 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-202-codebase-scan-7baabfef3647.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-203 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: todo
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-203-codebase-scan-c647d1e12d3c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-204 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-204-codebase-scan-7132ce0ffbac.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-205 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-205-codebase-scan-a8026067cd00.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-206 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-206-codebase-scan-02fa5d40d071.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-207 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-207-codebase-scan-5013c2cad7fa.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-208 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-208-codebase-scan-58a84faedac7.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-209 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-209-codebase-scan-80d778590ccc.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-210 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-210-codebase-scan-d9a53de7f959.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-211 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-211-codebase-scan-575e2a290493.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-212 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-212-codebase-scan-2df57b305ce0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-213 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-213-codebase-scan-9c168aaaa4d8.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-214 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-214-codebase-scan-92e89b8dc811.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-215 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-215-codebase-scan-433597df4b06.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-216 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-216-codebase-scan-673730b1fd8e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-217 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-217-codebase-scan-5e003fb75438.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-218 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-218-codebase-scan-2d018ad7c12b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-219 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-219-codebase-scan-49c203c3160f.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-220 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-220-codebase-scan-ba53d64433a9.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-221 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-221-codebase-scan-5b1c92d4adaf.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-222 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-222-codebase-scan-51e6555c2c74.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-223 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-223-codebase-scan-f93597363c8f.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-224 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-224-codebase-scan-d4f2db557d9c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-225 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-225-codebase-scan-30c01700a219.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-226 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-160-resolution.md:46. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-226-codebase-scan-c296c637a9e0.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-227 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-161-resolution.md:27. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-05-31-mgw-227-codebase-scan-ee10063021cb.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-228 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: todo
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-228-codebase-scan-5a9dcf62f5b3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-229 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-229-codebase-scan-7fbf55b5bf81.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-230 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-230-codebase-scan-01a2ecbf29ab.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-231 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-231-codebase-scan-1cc5d7cf1d63.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-232 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:8

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:8. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-232-codebase-scan-0f15e36edfb4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-233 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: done
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-233-codebase-scan-d877d8b313d3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-234 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-234-codebase-scan-59615e80d16d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-235 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-235-codebase-scan-89a32a75e4b3.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-236 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-236-codebase-scan-b76bb3f767b1.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-237 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:8

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:8. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-237-codebase-scan-4539b8d277a4.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-238 Resolve implementation retry-budget failure for MGW-233

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-238-mgw-233-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-233. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-06-mgw-238-mgw-233-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-233 from strategy blocked_tasks.

## MGW-239 Resolve dirty main checkout blocking 15 worktree merges

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Fingerprint: 52bc47f297ac62dfafbab35d35f658324a2fd2c2
- Dedupe key: reconciliation_guardrail:main_checkout_dirty
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md
- Acceptance: Reconciliation guardrail filed this because 15 branch or worktree cleanup candidates are blocked by main_checkout_dirty. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-239-reconciliation-58c94934bd81.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## MGW-240 Resolve 91 dirty backlogged worktrees blocked by content_not_in_target

- Status: completed
- Completion: manual
- Priority: P2
- Track: ops
- Fingerprint: ba8605bb3e3ecfc5e86be5f3ca4ee26cceae6221
- Dedupe key: reconciliation_guardrail:dirty_backlogged_worktree:content_not_in_target
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-240-reconciliation-bf6cac4e7a57.md
- Acceptance: Reconciliation guardrail filed this because 91 branch or worktree cleanup candidates are blocked by content_not_in_target. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-240-reconciliation-bf6cac4e7a57.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## MGW-241 Resolve 2 dirty backlogged worktrees blocked by unsupported_status

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Fingerprint: 731f0bb0db091c0d6d7bbf9d8746d1f86e43646e
- Dedupe key: reconciliation_guardrail:dirty_backlogged_worktree:unsupported_status
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-241-reconciliation-731f0bb0db09.md
- Acceptance: Reconciliation guardrail filed this because 2 branch or worktree cleanup candidates are blocked by unsupported_status. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-241-reconciliation-731f0bb0db09.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## MGW-242 Resolve 14 preflight-conflicting backlogged worktree merges

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Fingerprint: 612a1b40801b3fb511b53919982125f61f623117
- Dedupe key: reconciliation_guardrail:preflight_merge_conflict
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, implementation_plan/docs/18-swissknife-meta-glasses-display-widgets.todo.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-242-reconciliation-ef2bec545f8a.md
- Acceptance: Reconciliation guardrail filed this because 14 branch or worktree cleanup candidates are blocked by preflight_merge_conflict. Use evidence and the machine-readable reconciliation plan in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-242-reconciliation-ef2bec545f8a.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.

## MGW-243 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:14

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:14. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-243-codebase-scan-78ba9bc0d511.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-244 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:15

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:15. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-244-codebase-scan-2c46d79b298b.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-245 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:22

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:22. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-245-codebase-scan-f9d52b4adf9e.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-246 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:33

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:33. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-246-codebase-scan-13c59c1bd5b2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-247 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:35

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md:35. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-247-codebase-scan-729d43852a00.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-248 Resolve implementation retry-budget failure for MGW-244

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on:
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-28-vai-120-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-248-mgw-244-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-244. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-248-mgw-244-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-244 from strategy blocked_tasks.

## MGW-249 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13

- Status: completed
- Completion: manual
- Priority: P2
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-30-vai-147-resolution.md:13. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-249-codebase-scan-34b56cd1c047.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-250 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-hao-266-resolution.md:17. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-250-codebase-scan-e24cf6a2ed70.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-251 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-159-resolution.md:44. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-251-codebase-scan-260c89e10d17.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-252 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7

- Status: completed
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:7. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-252-codebase-scan-31ff8ec733f2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-253 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:8

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-162-resolution.md:8. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-253-codebase-scan-edfd1babbc1c.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-254 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md:18

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md:18. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-254-codebase-scan-063f5d004ddc.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-255 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md:24

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md:24. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-255-codebase-scan-a8da08b5474d.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-256 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md:30

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md:30. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-256-codebase-scan-7ea54a2c23c2.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-257 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-164-false-positive-resolution.md:10

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-164-false-positive-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-164-false-positive-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-164-false-positive-resolution.md:10. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-257-codebase-scan-e48c42cb0e10.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-258 Resolve code annotation in data/virtual_ai_os/discovery/2026-05-31-vai-164-false-positive-resolution.md:15

- Status: todo
- Completion: manual
- Priority: P3
- Track: docs
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-164-false-positive-resolution.md
- Validation: test -f data/virtual_ai_os/discovery/2026-05-31-vai-164-false-positive-resolution.md
- Acceptance: Codebase scan filed this finding from data/virtual_ai_os/discovery/2026-05-31-vai-164-false-positive-resolution.md:15. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-258-codebase-scan-8b059d2cce39.md, fix the bug or improvement, add or update focused validation when appropriate, and keep the supervisor-fed backlog parseable.

## MGW-259 Resolve implementation retry-budget failure for MGW-254

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-259-mgw-254-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-254. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-259-mgw-254-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-254 from strategy blocked_tasks.

## MGW-260 Resolve implementation retry-budget failure for MGW-259

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-260-mgw-259-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-259. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-260-mgw-259-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-259 from strategy blocked_tasks.

## MGW-261 Resolve implementation retry-budget failure for MGW-260

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-261-mgw-260-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-260. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-261-mgw-260-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-260 from strategy blocked_tasks.

## MGW-262 Resolve implementation retry-budget failure for MGW-261

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-262-mgw-261-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-261. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-262-mgw-261-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-261 from strategy blocked_tasks.

## MGW-263 Resolve implementation retry-budget failure for MGW-262

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-263-mgw-262-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-262. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-263-mgw-262-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-262 from strategy blocked_tasks.

## MGW-264 Resolve implementation retry-budget failure for MGW-263

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-264-mgw-263-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-263. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-264-mgw-263-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-263 from strategy blocked_tasks.

## MGW-265 Resolve implementation retry-budget failure for MGW-264

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-265-mgw-264-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-264. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-265-mgw-264-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-264 from strategy blocked_tasks.

## MGW-266 Resolve implementation retry-budget failure for MGW-265

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-266-mgw-265-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-265. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-266-mgw-265-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-265 from strategy blocked_tasks.

## MGW-267 Resolve implementation retry-budget failure for MGW-266

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-267-mgw-266-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-266. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-267-mgw-266-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-266 from strategy blocked_tasks.

## MGW-268 Resolve implementation retry-budget failure for MGW-267

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-268-mgw-267-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-267. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-268-mgw-267-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-267 from strategy blocked_tasks.

## MGW-269 Resolve implementation retry-budget failure for MGW-268

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-269-mgw-268-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-268. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-269-mgw-268-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-268 from strategy blocked_tasks.

## MGW-270 Resolve implementation retry-budget failure for MGW-269

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-270-mgw-269-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-269. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-270-mgw-269-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-269 from strategy blocked_tasks.

## MGW-271 Resolve implementation retry-budget failure for MGW-270

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-271-mgw-270-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-270. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-271-mgw-270-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-270 from strategy blocked_tasks.

## MGW-272 Resolve implementation retry-budget failure for MGW-271

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-272-mgw-271-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-271. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-272-mgw-271-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-271 from strategy blocked_tasks.

## MGW-273 Resolve implementation retry-budget failure for MGW-272

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-273-mgw-272-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-272. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-273-mgw-272-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-272 from strategy blocked_tasks.

## MGW-274 Resolve implementation retry-budget failure for MGW-273

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-274-mgw-273-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-273. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-274-mgw-273-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-273 from strategy blocked_tasks.

## MGW-275 Resolve implementation retry-budget failure for MGW-274

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-275-mgw-274-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-274. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-275-mgw-274-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-274 from strategy blocked_tasks.

## MGW-276 Resolve implementation retry-budget failure for MGW-275

- Status: todo
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-276-mgw-275-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-275. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-276-mgw-275-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-275 from strategy blocked_tasks.

## MGW-277 Resolve implementation retry-budget failure for MGW-276

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-277-mgw-276-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-276. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-277-mgw-276-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-276 from strategy blocked_tasks.

## MGW-278 Resolve implementation retry-budget failure for MGW-277

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-278-mgw-277-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-277. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-278-mgw-277-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-277 from strategy blocked_tasks.

## MGW-279 Resolve implementation retry-budget failure for MGW-278

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-279-mgw-278-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-278. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-279-mgw-278-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-278 from strategy blocked_tasks.

## MGW-280 Resolve implementation retry-budget failure for MGW-279

- Status: completed
- Completion: manual
- Priority: P1
- Track: ops
- Depends on: 
- Outputs: data/meta_glasses_display_widgets/discovery, data/virtual_ai_os/discovery/2026-05-31-vai-163-resolution.md
- Validation: test -f /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-280-mgw-279-implementation-retry-budget.md
- Acceptance: Implementation retry-budget guardrail filed this from repeated implementation failures in MGW-279. Use evidence in /home/barberb/lift_coding/data/meta_glasses_display_widgets/discovery/2026-06-07-mgw-280-mgw-279-implementation-retry-budget.md to fix the setup, runtime, or timeout blocker, then mark this repair task completed so the supervisor can release MGW-279 from strategy blocked_tasks.
