# Monorepo CI deferred suite re-enables task board (CIG)

Consumable by `ipfs_accelerate_py.agent_supervisor` with task prefix `## CIG-`.
Companion plan: `implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.md`.

Board namespace: `monorepo-ci-deferred-suite-reenables-v1`.

## Normative execution contract

- Prefer re-enabling a suite by aligning monorepo tests and pins to current
  submodule truth over reverting submodule product behavior.
- Every claimable task lists non-overlapping `predicted_files` so leased
  worktrees can run Wave A in parallel.
- Only CIG-040 may rewrite the residual multi-suite `Makefile` `test-ci` ignore
  block as a final closeout; individual tasks may remove **their own** ignore
  line when they list that path and the single ignore string in outputs.
- Validation always forces a green `make fmt-check` when Python sources change
  and a focused pytest of the re-enabled suite before claiming completion.
- Missing nested submodule paths are resolved by either restoring the expected
  artifact on the pinned revision or updating the monorepo assert to the
  canonical relocated path—never by skipping the suite silently.

## Parallel claimable waves

- **Wave A (interop):** CIG-010, CIG-011, CIG-012, CIG-013, CIG-014, CIG-015,
  CIG-016, CIG-017, CIG-018, CIG-019, CIG-020 (all depend only on CIG-000).
- **Wave B (large boards):** CIG-030, CIG-031 (depend on CIG-000; optional
  soft-dep on related interops is **not** hard-required).
- **Wave C (closeout):** CIG-040 depends on all Wave A+B task ids.

## CIG-000 Seal the CIG supervisor board

- Status: completed
- Completion: manual
- Completion evidence: Operator-authored plan, executable CIG board, thin supervisor wrapper, and parser smoke tests committed for monorepo CI deferred suite re-enables.
- Is schedulable: false
- Review only: false
- Priority: P0
- Track: ops
- Depends on:
- Outputs: implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.md, implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.todo.md, scripts/monorepo_ci_reenables_todo_supervisor.py, tests/test_monorepo_ci_reenables_todo_queue.py
- Validation: PYTHONPATH=external/ipfs_accelerate python3 -c "from pathlib import Path; from ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_daemon import parse_task_file; t=parse_task_file(Path('implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.todo.md'), '## CIG-'); assert any(x.task_id=='CIG-000' for x in t)"; PYTHONPATH=external/ipfs_accelerate pytest tests/test_monorepo_ci_reenables_todo_queue.py -q
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/board-seal
- Parallel lane: cig-ops
- Resource class: cpu-light
- Implementation timeout seconds: 1800
- Predicted files: implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.md, implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.todo.md, scripts/monorepo_ci_reenables_todo_supervisor.py, tests/test_monorepo_ci_reenables_todo_queue.py
- Submodules: external/ipfs_accelerate
- Acceptance: The deferred CI re-enable inventory is available as a daemon-parseable CIG board with non-overlapping Wave A predicted files and a closeout task.

## CIG-010 Re-enable SwissKnife MCP++ interop in test-ci

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_swissknife_mcp_plus_plus_interop.py, Makefile, swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json
- Predicted files: tests/integration/test_swissknife_mcp_plus_plus_interop.py
- Validation: PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_swissknife_mcp_plus_plus_interop.py -q; rg -n "test_swissknife_mcp_plus_plus_interop" Makefile; test -z "$(rg -n 'ignore=tests/integration/test_swissknife_mcp_plus_plus_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/mcp-plus-plus-interop
- Parallel lane: cig-mcp
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Submodules: swissknife, Mcp-Plus-Plus
- Fingerprint: cig-mcp-plus-plus-interop-reenables-v1
- Dedupe key: cig:reenable:swissknife_mcp_plus_plus_interop
- Preconditions: swissknife receipt schema multi-daemon enums and monorepo fixture task_id/daemon_id drift understood from wave-8 probe.
- Effects: Aligns monorepo MCP++ interop tests with current swissknife contracts and removes the suite from test-ci ignores.
- Acceptance: `tests/integration/test_swissknife_mcp_plus_plus_interop.py` passes under CI PYTHONPATH; Makefile no longer ignores that path; receipt fixtures validate against the live schema enums.

## CIG-011 Re-enable SwissKnife mobile interop in test-ci

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_swissknife_mobile_interop.py, Makefile, mobile/src/orb/metaGlassesOrbDescriptors.js
- Predicted files: tests/integration/test_swissknife_mobile_interop.py
- Validation: PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_swissknife_mobile_interop.py -q; test -z "$(rg -n 'ignore=tests/integration/test_swissknife_mobile_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/swissknife-mobile-interop
- Parallel lane: cig-mobile
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Submodules: swissknife
- Fingerprint: cig-swissknife-mobile-interop-reenables-v1
- Dedupe key: cig:reenable:swissknife_mobile_interop
- Preconditions: Wave-8 probe showed validation.task_id MGW-569 vs expected VAI-661 and missing validation.attempt keys.
- Effects: Aligns mobile interop descriptor assertions with current MGW renumber and re-enables the suite.
- Acceptance: Mobile interop suite passes; ignore line removed; task_id/attempt/repair refs match `mobile/src/orb/metaGlassesOrbDescriptors.js`.

## CIG-012 Refresh ORB dynamic renderer tests for UIR-035 and re-enable

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_orb_dynamic_renderer.py, Makefile, swissknife/web/src/orb-dynamic-app-renderer.ts
- Predicted files: tests/integration/test_orb_dynamic_renderer.py
- Validation: PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_orb_dynamic_renderer.py -q; test -z "$(rg -n 'ignore=tests/integration/test_orb_dynamic_renderer' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/orb-dynamic-renderer
- Parallel lane: cig-orb
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Submodules: swissknife
- Fingerprint: cig-orb-dynamic-renderer-uir035-v1
- Dedupe key: cig:reenable:orb_dynamic_renderer
- Preconditions: UIR-035 security rewrite removed Expected Output / AbortSignal.timeout / direct HTTP helper strings.
- Effects: Rewrites monorepo ORB renderer contract tests to the governed invoker/result-panel model and re-enables the suite.
- Acceptance: ORB dynamic renderer suite passes against `swissknife/web/src/orb-dynamic-app-renderer.ts`; ignore line removed.

## CIG-013 Re-enable SwissKnife datasets interop in test-ci

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_swissknife_external_ipfs_datasets_interop.py, Makefile
- Predicted files: tests/integration/test_swissknife_external_ipfs_datasets_interop.py
- Validation: PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_swissknife_external_ipfs_datasets_interop.py -q; test -z "$(rg -n 'ignore=tests/integration/test_swissknife_external_ipfs_datasets_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/datasets-interop
- Parallel lane: cig-datasets
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Submodules: swissknife, external/ipfs_datasets
- Fingerprint: cig-datasets-interop-reenables-v1
- Dedupe key: cig:reenable:swissknife_external_ipfs_datasets_interop
- Preconditions: Probe missing `external/ipfs_datasets/.tools/ipfs_kit_py/data/deprecations_report.schema.json` on the monorepo pin.
- Effects: Restores or relocates datasets interop disk artifacts/asserts and re-enables the suite.
- Acceptance: Datasets interop suite passes on the pinned datasets revision; ignore line removed.

## CIG-014 Re-enable hallucinate_app mobile interop in test-ci

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_hallucinate_app_mobile_interop.py, Makefile
- Predicted files: tests/integration/test_hallucinate_app_mobile_interop.py
- Validation: PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_hallucinate_app_mobile_interop.py -q; test -z "$(rg -n 'ignore=tests/integration/test_hallucinate_app_mobile_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/hallucinate-mobile-interop
- Parallel lane: cig-hallucinate-mobile
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Submodules: hallucinate_app, external/ipfs_accelerate
- Fingerprint: cig-hallucinate-mobile-interop-reenables-v1
- Dedupe key: cig:reenable:hallucinate_app_mobile_interop
- Preconditions: Probe missing nested `hallucinate_app/ipfs_accelerate_py/data/duckdb/db_schema/time_series_schema.sql`.
- Effects: Aligns hallucinate mobile interop descriptor paths with the pinned tree and re-enables the suite.
- Acceptance: Hallucinate mobile interop suite passes; ignore line removed.

## CIG-015 Re-enable glasses control plane suite in test-ci

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P2
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_glasses_control_plane.py, Makefile, swissknife/src/services/meta-glasses-mobile-orb-bridge.ts
- Predicted files: tests/integration/test_glasses_control_plane.py
- Validation: PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_glasses_control_plane.py -q; test -z "$(rg -n 'ignore=tests/integration/test_glasses_control_plane' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/glasses-control-plane
- Parallel lane: cig-glasses
- Resource class: cpu-medium
- Implementation timeout seconds: 7200
- Submodules: swissknife
- Fingerprint: cig-glasses-control-plane-reenables-v1
- Dedupe key: cig:reenable:glasses_control_plane
- Preconditions: Probe missing `swissknife/src/services/meta-glasses-mobile-orb-bridge.ts` (bridge may have moved or been renamed).
- Effects: Locates the live mobile-orb bridge module and updates readiness asserts, then re-enables the suite.
- Acceptance: Glasses control plane suite passes (or skip-only hardware paths remain explicitly skipped); ignore line removed.

## CIG-016 Re-enable SwissKnife meta-wearables Android interop

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P2
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py, Makefile
- Predicted files: tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py
- Validation: git submodule update --init --depth 1 external/meta-wearables-dat-android; PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_swissknife_external_meta_wearables_dat_android_interop.py -q; test -z "$(rg -n 'ignore=tests/integration/test_swissknife_external_meta_wearables_dat_android_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/meta-android-swissknife
- Parallel lane: cig-meta-android
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Submodules: swissknife, external/meta-wearables-dat-android
- Fingerprint: cig-meta-android-swissknife-interop-v1
- Dedupe key: cig:reenable:swissknife_meta_wearables_dat_android_interop
- Preconditions: Nested DAT android checkout required; descriptor task ids may have renumbered (MGW-574 family).
- Effects: Aligns SwissKnife↔DAT android interop tests with the pin and re-enables the suite.
- Acceptance: Suite passes with DAT android submodule initialized; ignore line removed.

## CIG-017 Re-enable SwissKnife meta-wearables iOS interop

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P2
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop.py, Makefile
- Predicted files: tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop.py
- Validation: git submodule update --init --depth 1 external/meta-wearables-dat-ios; PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop.py -q; test -z "$(rg -n 'ignore=tests/integration/test_swissknife_external_meta_wearables_dat_ios_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/meta-ios-swissknife
- Parallel lane: cig-meta-ios
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Submodules: swissknife, external/meta-wearables-dat-ios
- Fingerprint: cig-meta-ios-swissknife-interop-v1
- Dedupe key: cig:reenable:swissknife_meta_wearables_dat_ios_interop
- Preconditions: Nested DAT iOS checkout required; VAI-667-class descriptor alignment.
- Effects: Aligns SwissKnife↔DAT iOS interop tests with the pin and re-enables the suite.
- Acceptance: Suite passes with DAT iOS submodule initialized; ignore line removed.

## CIG-018 Re-enable meta-wearables Android × accelerate interop

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P2
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py, Makefile
- Predicted files: tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py
- Validation: git submodule update --init --depth 1 external/meta-wearables-dat-android; PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop.py -q; test -z "$(rg -n 'ignore=tests/integration/test_external_meta_wearables_dat_android_external_ipfs_accelerate_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/meta-android-accelerate
- Parallel lane: cig-meta-android-accelerate
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Submodules: external/meta-wearables-dat-android, external/ipfs_accelerate
- Fingerprint: cig-meta-android-accelerate-interop-v1
- Dedupe key: cig:reenable:meta_android_accelerate_interop
- Preconditions: Nested DAT android + accelerate pins must both be present in CI init list (already true for accelerate).
- Effects: Restores cross-repo descriptor/path contracts and re-enables the suite.
- Acceptance: Suite passes; ignore line removed.

## CIG-019 Re-enable meta-wearables Android × datasets interop

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P2
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py, Makefile
- Predicted files: tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py
- Validation: git submodule update --init --depth 1 external/meta-wearables-dat-android; PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop.py -q; test -z "$(rg -n 'ignore=tests/integration/test_external_meta_wearables_dat_android_external_ipfs_datasets_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/meta-android-datasets
- Parallel lane: cig-meta-android-datasets
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Submodules: external/meta-wearables-dat-android, external/ipfs_datasets
- Fingerprint: cig-meta-android-datasets-interop-v1
- Dedupe key: cig:reenable:meta_android_datasets_interop
- Preconditions: Nested DAT android + datasets pins.
- Effects: Restores cross-repo descriptor/path contracts and re-enables the suite.
- Acceptance: Suite passes; ignore line removed.

## CIG-020 Re-enable meta-wearables Android × kit interop

- Status: completed
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P2
- Track: ci/interop
- Depends on: CIG-000
- Outputs: tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py, Makefile
- Predicted files: tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py
- Validation: git submodule update --init --depth 1 external/meta-wearables-dat-android; PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop.py -q; test -z "$(rg -n 'ignore=tests/integration/test_external_meta_wearables_dat_android_external_ipfs_kit_interop' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/meta-android-kit
- Parallel lane: cig-meta-android-kit
- Resource class: cpu-medium
- Implementation timeout seconds: 9000
- Submodules: external/meta-wearables-dat-android, external/ipfs_kit
- Fingerprint: cig-meta-android-kit-interop-v1
- Dedupe key: cig:reenable:meta_android_kit_interop
- Preconditions: Nested DAT android + kit pins.
- Effects: Restores cross-repo descriptor/path contracts and re-enables the suite.
- Acceptance: Suite passes; ignore line removed.

## CIG-030 Re-enable virtual AI OS todo-queue suite in test-ci

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P2
- Track: ci/boards
- Depends on: CIG-000
- Outputs: tests/test_virtual_ai_os_todo_queue.py, Makefile
- Predicted files: tests/test_virtual_ai_os_todo_queue.py
- Validation: PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/test_virtual_ai_os_todo_queue.py -q; test -z "$(rg -n 'ignore=tests/test_virtual_ai_os_todo_queue' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/vai-todo-queue
- Parallel lane: cig-vai-todo
- Resource class: cpu-heavy
- Implementation timeout seconds: 14400
- Submodules: external/ipfs_accelerate, external/ipfs_datasets, swissknife, hallucinate_app
- Fingerprint: cig-virtual-ai-os-todo-queue-reenables-v1
- Dedupe key: cig:reenable:virtual_ai_os_todo_queue
- Preconditions: Large board fixture (~5.5k LOC); may need discovery path / board pin updates rather than product changes.
- Effects: Makes the VAI todo-queue daemon harness part of required CI again.
- Acceptance: Full `tests/test_virtual_ai_os_todo_queue.py` passes in CI time budget or is split with remaining shards still tracked; ignore line removed for the re-enabled entrypoint.

## CIG-031 Re-enable hallucinate multimodal control todo-queue suite in test-ci

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P2
- Track: ci/boards
- Depends on: CIG-000
- Outputs: tests/test_hallucinate_multimodal_control_todo_queue.py, Makefile
- Predicted files: tests/test_hallucinate_multimodal_control_todo_queue.py
- Validation: PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q; test -z "$(rg -n 'ignore=tests/test_hallucinate_multimodal_control_todo_queue' Makefile || true)"
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/hao-todo-queue
- Parallel lane: cig-hao-todo
- Resource class: cpu-heavy
- Implementation timeout seconds: 14400
- Submodules: hallucinate_app, external/ipfs_accelerate
- Fingerprint: cig-hallucinate-multimodal-todo-queue-reenables-v1
- Dedupe key: cig:reenable:hallucinate_multimodal_control_todo_queue
- Preconditions: Large board fixture (~7.5k LOC); tokenized todo filenames must remain scan-safe.
- Effects: Makes the hallucinate multimodal control todo-queue harness part of required CI again.
- Acceptance: Full suite passes in CI time budget or is split with remaining shards still tracked; ignore line removed.

## CIG-040 Close out deferred test-ci ignores

- Status: todo
- Completion: manual
- Is schedulable: true
- Review only: false
- Priority: P1
- Track: ops
- Depends on: CIG-010, CIG-011, CIG-012, CIG-013, CIG-014, CIG-015, CIG-016, CIG-017, CIG-018, CIG-019, CIG-020, CIG-030, CIG-031
- Outputs: Makefile, implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.md, data/ci/discovery/cig-040-closeout.md
- Predicted files: Makefile, implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.md, data/ci/discovery/cig-040-closeout.md
- Validation: rg -n "test-ci:|--ignore=" Makefile; PYTHONPATH=src:external/ipfs_accelerate:external/ipfs_kit:external/ipfs_datasets make test-ci
- Board namespace: monorepo-ci-deferred-suite-reenables-v1
- Bundle: cig/closeout
- Parallel lane: cig-closeout
- Resource class: cpu-heavy
- Implementation timeout seconds: 18000
- Submodules: swissknife, Mcp-Plus-Plus, hallucinate_app, external/ipfs_accelerate, external/ipfs_kit, external/ipfs_datasets, external/meta-wearables-dat-android, external/meta-wearables-dat-ios
- Fingerprint: cig-closeout-test-ci-ignores-v1
- Dedupe key: cig:closeout:test_ci_ignores
- Preconditions: All Wave A/B tasks completed or explicitly waived with permanent-ignore rationale recorded in discovery.
- Effects: Final Makefile ignore audit; documents any intentional long-term exclusions; proves make test-ci green.
- Acceptance: No deferred suite from this board remains ignored without a permanent-ignore rationale in `data/ci/discovery/cig-040-closeout.md`; `make test-ci` is green on the closeout branch.

## CIG-041 Resolve 1 preflight-conflicting backlogged worktree merges

- Status: blocked
- Completion: manual
- Is schedulable: false
- Review only: true
- Blocked reason: operator_reconciliation_required
- Priority: P1
- Track: ops
- Generated by: ipfs_accelerate_py.agent_supervisor.reconciliation-guardrail@1
- Reconciliation kind: preflight_merge_conflict
- Reconciliation reason: preflight_merge_conflict
- Reconciliation fingerprint: 0d9db8a4806ed151bc05b3104fe34e94724edf03
- Reconciliation discovery: data/ci/cig/discovery/2026-08-06-cig-041-reconciliation-0d9db8a4806e.md
- Canonical board task: false
- Fingerprint: 0d9db8a4806ed151bc05b3104fe34e94724edf03
- Dedupe key: reconciliation_guardrail:preflight_merge_conflict
- Depends on:
- Outputs: data/ci/cig/discovery, implementation_plan/docs/47-monorepo-ci-deferred-suite-reenables.todo.md
- Validation: test -f data/ci/cig/discovery/2026-08-06-cig-041-reconciliation-0d9db8a4806e.md
- Acceptance: Reconciliation guardrail filed this because 1 branch or worktree cleanup candidates are blocked by preflight_merge_conflict. This task is intentionally operator-gated because unknown dirty checkout content must not be committed, stashed, or discarded automatically. Use evidence and the machine-readable reconciliation plan in data/ci/cig/discovery/2026-08-06-cig-041-reconciliation-0d9db8a4806e.md, reconcile the dirty checkout or dirty worktree group deliberately, then rerun the supervisor cleanup/reconciliation pass and confirm that the blocked candidate count decreases.
