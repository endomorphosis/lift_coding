# SwissKnife Repository Refactoring Plan

Status: Proposed
Scope: `swissknife` repository-wide modularization, browser compatibility, TS/WASM
runtime purity, test/build consolidation, and release-readiness gates.

Generated: 2026-07-08

## Current Baseline

The immediate architectural foundation is already mostly in place under
`swissknife/src/services`: service modules have explicit ownership metadata,
browser/host barrels exist for the key runtime areas, and MCP/libp2p browser
runtime tests exist.

Current repository state from the synchronized refactor evidence:

- `npm run services:audit` is the strict service/source boundary gate. It fails
  on unknown files, forbidden imports, legacy compatibility shims, and legacy
  root import specifiers, and refreshes `swissknife/docs/service-boundary-audit.json`
  plus the module-boundary freshness receipt.
- The former MCP, IPFS, glasses, and app-surface service shims have been moved
  into owned submodules under `src/services/mcp`, `src/services/ipfs`,
  `src/services/glasses`, and `src/services/apps`.
- Service boundaries are documented in
  `swissknife/src/services/MODULE_BOUNDARIES.md`; repository-wide module
  boundaries are documented in `swissknife/docs/source-module-boundaries.md`.
- Evidence maintenance is documented in
  `swissknife/docs/refactor-evidence-maintenance.md`. Release evidence
  freshness is tracked in `swissknife/docs/release-evidence-freshness.md`.
- The current generated service/source audit has 46 manifest modules, 0 unknown
  files, 0 forbidden imports, 0 legacy compatibility shims, and 0 legacy root
  import specifiers. It still reports 15 owned top-level source compatibility
  files outside `src/services`; those are repository module debt, not service
  shim debt.

## Refactoring Objective

Make `swissknife` a modular, browser-compatible TypeScript/WASM codebase with
clear host/browser boundaries, enforced module ownership, stable test/build
gates, and no accidental Python/native-wrapper dependency in browser paths.

## Architecture Principles

1. Behavior belongs inside owned modules, not root-level compatibility files.
2. Browser entrypoints must be pure browser-safe TypeScript/WASM.
3. Host/native adapters must be explicit and isolated behind `host.ts` or CLI
   entrypoints.
4. Test gates must match runtime surfaces: services audit, browser purity,
   web build, focused domain tests, and release gates.
5. Python references may be used as offline differential oracles only; browser
   runtime code must use TS/WASM implementations.
6. Refactoring should be incremental and gate-driven, with small slices that can
   be accepted independently by the agent supervisor.

## Phase 1: Re-Stabilize Service Boundaries

Remove the remaining root service shims, retarget active imports to module-owned
paths, and restore `npm run services:audit` as a strict architectural gate.

Acceptance target:

- `cd swissknife && npm run services:audit`
- Audit reports:
  - `root files: 0`
  - `unknown files: 0`
  - `forbidden imports: 0`
  - `legacy root import specifiers: 0`

## Phase 2: Browser/Host Boundary Hardening

Treat every service module as having explicit runtime boundaries:

- `browser.ts`: browser-safe TS/WASM only.
- `host.ts`: Node, filesystem, subprocess, terminal, native binary, and remote
  bridge adapters.
- `index.ts`: environment-neutral exports only, or clearly documented
  compatibility.

Primary browser gate:

- MCP/libp2p browser runtime tests.
- WASM prover browser purity tests.
- Web bundle scan for host-only strings/imports.
- `npm run build:web`.

## Phase 3: TypeScript Project Health

Resolve the `TS6305` declaration-output mismatch so the repo has a real
green `npm run typecheck` signal.

Likely remediation paths:

- Remove stale generated declaration outputs from the root compiler input.
- Convert the repo to proper `tsc -b` project references.
- Split typecheck scripts by target:
  - `typecheck:cli`
  - `typecheck:web`
  - `typecheck:services`
  - `typecheck:ipfs-accelerate`

Acceptance target:

- `cd swissknife && npm run typecheck` exits `0`.
- No filtered-diagnostic workaround is required.

## Phase 4: Test System Consolidation

Consolidate the current Jest/Vitest/Playwright sprawl into documented lanes:

- Vitest for TypeScript unit and service tests.
- Playwright for web, MCP dashboard, Meta glasses, and screenshot/evidence flows.
- Jest only for legacy suites until migrated.

Recommended scripts:

- `test:fast`
- `test:services`
- `test:browser-compat`
- `test:e2e:mcp`
- `test:release`

Acceptance target:

- The documented fast gate is short and reliable.
- The release gate is comprehensive and deterministic.

## Phase 5: Pure TS/WASM Provers and ZKP

Keep Python/native prover bridges out of browser runtime paths.

Required shape:

- Browser prover entrypoints use pure TS and WASM implementations.
- Host-only wrappers remain behind `host.ts` or CLI entrypoints.
- Simulated proof paths are never presented as production proof paths.
- Offline Python differential tests may remain as conformance oracles.

Acceptance target:

- Browser bundle contains no Python/remote prover bridge.
- ZKP/prover browser tests exercise real TS/WASM behavior.
- Any fallback is explicitly reported as unavailable or simulated test mode.

## Phase 6: App, Glasses, IPFS, and MCP Product Surfaces

Clarify ownership:

- `apps`: virtual desktop manifests, app capability policy, app result
  envelopes, composite descriptors.
- `glasses`: display/orb/control-plane adapters and Meta glasses integration.
- `ipfs`: IPFS descriptors, storage/cache integration points, UI profiles.
- `mcp`: protocol, transport, envelopes, registries, policy mediation, MCP++
  descriptors.

Acceptance target:

- App manifest tests pass.
- Glasses coverage tests pass.
- MCP dashboard consumer script passes.
- Playwright evidence exists for the virtual desktop/MCP/glasses flows.

## Phase 7: Top-Level Repository Modularization

After `src/services` is stable, apply the same discipline across `src`:

- `commands` and `entrypoints`: CLI/host-only.
- `components`, `screens`, `hooks`: UI-only.
- `storage`, `tasks`, `workers`: runtime modules with browser/host splits where
  needed.
- `ai`, `models`, `inference`: provider/model abstractions with browser-safe
  adapters separated from Node SDK adapters.
- `utils` and `shared`: shrink aggressively by moving domain-specific helpers
  back into owning modules.

Acceptance target:

- No large catch-all utility/module directories own domain behavior by default.
- Cross-module imports follow documented dependency direction.

## Phase 8: Dependency and Bundle Cleanup

Separate browser dependencies from CLI/host dependencies.

Targets:

- Reduce accidental browser polyfills.
- Track libp2p bundle cost explicitly.
- Add browser bundle budget checks.
- Remove stale archived config/test paths from active scans where possible.

Acceptance target:

- `npm run build:web` passes without host polyfill leakage.
- Browser bundle scan is repeatable and documented.
- Dependency ownership is clear.

## Phase 9: CI and Release Gates

Wire the final gate stack into CI/release:

- `services:audit`
- `typecheck`
- `test:fast`
- `test:browser-compat`
- `build:web`
- `test:e2e:mcp`
- release evidence generation

Acceptance target:

- A release candidate cannot pass with service-boundary drift, browser-host
  leakage, typecheck failure, or missing MCP/glasses evidence.

## Supervisor Usage

The SwissKnife refactor backlog is parseable by the `ipfs_accelerate_py`
implementation supervisor with explicit SWR task and state prefixes. Use the
bounded parse/supervision check before any autonomous implementation run:

```bash
python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor \
  --once \
  --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md \
  --state-dir tmp/swissknife_refactor_supervisor/state \
  --task-prefix '## SWR-' \
  --state-prefix swissknife_refactor \
  --no-implement \
  --no-ephemeral-worktree \
  --no-worktree-reconciliation \
  --no-retry-budget-guardrail \
  --no-dependency-guardrail \
  --no-reconciliation-guardrail
```

This mode is intentionally read-mostly for backlog parsing and supervisor state
refresh. It may update supervisor state files under
`tmp/swissknife_refactor_supervisor/state`, including
`swissknife_refactor_task_state.json`, `swissknife_refactor_strategy.json`,
`swissknife_refactor_supervisor_status.json`, `task_queue.json`, event logs,
and `gc_state.json`; it must not launch implementation agents or make
autonomous code edits because `--no-implement` is present. Operational details,
state file meanings, known daemon `git gc` behavior, and escalation rules are
documented in `swissknife/docs/supervisor-refactor-runbook.md`.

Run implementation mode only after a bounded check is green and only with the
same `--todo-path`, `--task-prefix`, `--state-prefix`, and `--state-dir`
values. Avoid running a bounded check against the same state directory while a
long-running `--implement` supervisor is active unless the purpose is explicit
state observation.

# Agent Todos

## SWR-001 Restore strict service-boundary audit

- Status: completed
- Completion: automated
- Priority: P1
- Track: refactor/services
- Fingerprint: 8f8e9fb3dd6e53cc004d9c55eeb213bac2c462f8
- Dedupe key: swissknife_refactor:service_boundary_reset
- Depends on:
- Outputs: swissknife/src/services/MODULE_BOUNDARIES.md, swissknife/src/services/module-ownership.json, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: cd swissknife && npm run services:audit (passes; root files 0, unknown files 0, forbidden imports 0, legacy root import specifiers 0)
- Acceptance: Remove or relocate the five root-level `src/services/*.ts` shim files, retarget active imports to module-owned paths, and make `npm run services:audit` pass with zero root files, zero unknown files, zero forbidden imports, and zero legacy root import specifiers.

## SWR-002 Harden browser and host entrypoint boundaries

- Status: completed
- Completion: automated
- Priority: P1
- Track: refactor/browser
- Fingerprint: f1e769a0f2ec46b8da2c248fed2a22cb1f47275e
- Dedupe key: swissknife_refactor:browser_host_boundary
- Depends on: SWR-001
- Outputs: swissknife/src/services/*/browser.ts, swissknife/src/services/*/host.ts, swissknife/test/mcp-plus-plus/wasm-prover-browser-purity.test.ts
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/mcp-browser-entrypoint.test.ts test/mcp-plus-plus/wasm-prover-browser-purity.test.ts test/mcp-plus-plus/mcp-transport-libp2p-runtime.test.ts && npm run test:run -- test/unit/services/mcp/mcpTransport.test.ts && npm run build:web && rg -n "node:fs|node:path|child_process|Buffer\\.from|mcp-remote-deontic-engine|RemoteDeonticEngine|pyodide|spawn\\(|execFile\\(" web/dist/assets web/dist/index.html (all pass; bundle scan returns no matches)
- Acceptance: Browser entrypoints import only browser-safe TS/WASM code, host-only adapters remain behind host entrypoints, libp2p browser defaults stay enabled, and generated web assets contain no host-only remote/Python bridge or Node-native transport strings.

## SWR-003 Resolve TypeScript TS6305 project-output drift

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/typescript
- Fingerprint: bb10fae826e83a4eedea353fb79bf6b6095a7f36
- Dedupe key: swissknife_refactor:typecheck_ts6305
- Depends on: SWR-001
- Outputs: swissknife/tsconfig.json, swissknife/web/tsconfig.json, swissknife/ipfs_accelerate_js/tsconfig.json, swissknife/package.json
- Validation: cd swissknife && npm run typecheck
- Current finding: `npm run typecheck` still exits 2 with only `TS6305` under the existing root config, but exercising/removing the project-reference path exposes broader pre-existing TypeScript debt; this needs a dedicated typecheck-lane cleanup rather than a config-only suppression.
- Acceptance: `npm run typecheck` exits zero without filtering diagnostics; the existing TS6305 declaration-output mismatch class is eliminated by fixing compiler inputs, generated outputs, or project-reference configuration.

## SWR-004 Consolidate test lanes and scripts

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/tests
- Fingerprint: 6eb08fb6e8eabad0d06cac9fcfbf62a861cccd29
- Dedupe key: swissknife_refactor:test_matrix_consolidation
- Depends on: SWR-003
- Outputs: swissknife/package.json, swissknife/build-tools/configs, swissknife/config/jest, swissknife/test
- Validation: cd swissknife && npm run test:fast && npm run test:browser-compat
- Acceptance: The repo has documented fast, service, browser-compatibility, E2E/MCP, and release test lanes; archived configs and backup tests are excluded from active gates; the fast and browser-compatibility gates are deterministic.

## SWR-005 Enforce pure TS/WASM prover and ZKP browser runtime

- Status: completed
- Completion: automated
- Priority: P1
- Track: refactor/provers-zkp
- Fingerprint: 51853060a861a652508bfb9ed5608f02c6406302
- Dedupe key: swissknife_refactor:pure_ts_wasm_provers_zkp
- Depends on: SWR-002
- Outputs: swissknife/src/services/provers/browser.ts, swissknife/src/services/provers/host.ts, swissknife/src/services/zkp/browser.ts, swissknife/src/services/zkp/host.ts, swissknife/test/mcp-plus-plus
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/wasm-prover-browser-purity.test.ts test/mcp-plus-plus/wasm-prover-browser-zkp-real.test.ts test/mcp-plus-plus/wasm-prover-browser-groth16-semantic.test.ts && npm run build:web (passes; real browser Groth16 semantic proof generation and verification covered)
- Acceptance: Browser prover/ZKP paths use pure TS/WASM implementations only; Python/native wrappers remain host-only; simulated proof paths are explicitly marked as test/simulation and cannot masquerade as production proof paths.

## SWR-006 Clarify apps, glasses, IPFS, and MCP ownership

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/product-surfaces
- Fingerprint: caab0765fb195eb1e42d5fc6eb854cc0da93e94a
- Dedupe key: swissknife_refactor:apps_glasses_mcp_ipfs_surfaces
- Depends on: SWR-001
- Outputs: swissknife/src/services/apps, swissknife/src/services/glasses, swissknife/src/services/ipfs, swissknife/src/services/mcp
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/glasses-manifest-coverage.test.ts test/mcp-plus-plus/mobile-orb-edge-all-apps.test.ts && node scripts/test-mcp-dashboard-consumer.cjs
- Acceptance: App manifests and capability policies live under `apps`, display/orb adapters under `glasses`, protocol/transport/mediation under `mcp`, and IPFS descriptors/storage integration under `ipfs`; focused coverage and dashboard consumer validation pass.

## SWR-007 Extend module-boundary discipline beyond services

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/repo-modules
- Fingerprint: 89471136d057f0cf260692e0f37c1522c4dc4736
- Dedupe key: swissknife_refactor:top_level_module_boundaries
- Depends on: SWR-001, SWR-004
- Outputs: swissknife/src/commands, swissknife/src/entrypoints, swissknife/src/components, swissknife/src/storage, swissknife/src/tasks, swissknife/src/workers, swissknife/src/utils, swissknife/src/shared
- Validation: cd swissknife && npm run lint && npm run test:fast
- Acceptance: Top-level source directories have documented ownership and dependency direction; host-only CLI code, browser UI code, runtime workers, storage, AI/model adapters, and shared utilities are separated so domain behavior is not hidden in catch-all utility folders.

## SWR-008 Clean browser dependencies and bundle budgets

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/dependencies
- Fingerprint: 8fa1be26eeb65987ed9f257a106f6c679432cc52
- Dedupe key: swissknife_refactor:dependency_bundle_cleanup
- Depends on: SWR-002, SWR-005
- Outputs: swissknife/package.json, swissknife/package-lock.json, swissknife/vite.web.config.ts, swissknife/scripts
- Validation: cd swissknife && npm run build:web && ! rg -n "node:fs|node:path|child_process|Buffer\\.from|mcp-remote-deontic-engine" dist/assets dist/index.html
- Acceptance: Browser bundle builds without host polyfill leakage, libp2p bundle cost is tracked, dependency ownership is documented, and accidental browser imports of host-only libraries are blocked by a repeatable scan.

## SWR-009 Wire CI and release readiness gates

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/ci
- Fingerprint: 51e4424fe130482a0405dcf1498736953070f248
- Dedupe key: swissknife_refactor:ci_release_gates
- Depends on: SWR-001, SWR-003, SWR-004, SWR-008
- Outputs: swissknife/package.json, swissknife/.github, swissknife/scripts, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: cd swissknife && npm run services:audit && npm run typecheck && npm run test:fast && npm run test:browser-compat && npm run build:web (all pass; `npm run release:gate` orchestrates the same gates plus MCP/glasses evidence and writes docs/release-readiness-report.{json,md})
- Acceptance: Release candidates cannot pass with service-boundary drift, browser-host leakage, typecheck failure, missing browser compatibility tests, or stale MCP/glasses evidence. Added `services:audit` (fails on unknown/forbidden/legacy-shim/legacy-root-import drift), fixed a `tsconfig.host.json` TS6053 path regression left over from the SWR-006 service moves so `npm run typecheck` is green again, added `evidence:mcp-glasses`/`evidence:dashboard-consumer` gates that re-validate glasses manifest and MCP dashboard capability coverage against live source instead of trusting stale fixtures, added `scripts/release-readiness-gate.mjs` (`npm run release:gate`) as a single orchestrator used by `preversion`/`prepublishOnly`/`release:prepare`, and added `.github/workflows/release-readiness-gates.yml` wiring all gates as required CI jobs plus an aggregate blocking job.

## SWR-010 Keep refactor documentation and evidence current

- Status: completed
- Completion: manual
- Priority: P3
- Track: refactor/docs
- Fingerprint: c885909123a26a724aa6b427d52a6dce8635bc1b
- Dedupe key: swissknife_refactor:documentation_evidence
- Depends on: SWR-001
- Outputs: implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md, swissknife/src/services/MODULE_BOUNDARIES.md, swissknife/docs
- Validation: test -f implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md && cd swissknife && npm run services:audit
- Evidence: swissknife/src/services/MODULE_BOUNDARIES.md, swissknife/docs/refactor-evidence-maintenance.md, swissknife/docs/service-boundary-audit.json, swissknife/docs/release-evidence-freshness.md
- Acceptance: The refactoring plan, service boundary docs, task board statuses, validation commands, and evidence links remain synchronized with the current repository state after each milestone. The plan now records the current audit state instead of the obsolete five-shim blocker, `src/services/MODULE_BOUNDARIES.md` defines service ownership and maintenance rules, and `docs/refactor-evidence-maintenance.md` maps every refactor evidence artifact to its regeneration command.

## SWR-011 Build repository-wide browser compatibility inventory

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/browser-inventory
- Fingerprint: 8bdc66d0c857fc6a6b7b4d432a813a96374d1f44
- Dedupe key: swissknife_refactor:browser_inventory
- Depends on: SWR-001, SWR-002
- Outputs: swissknife/docs/browser-compatibility-inventory.md, swissknife/scripts/audit-browser-compat.mjs
- Validation: cd swissknife && node scripts/audit-browser-compat.mjs --report docs/browser-compatibility-inventory.md
- Acceptance: Inventory every browser-facing entrypoint, lazy bundle, service barrel, worker, web app, and shared utility that can reach `web/dist`; classify each as browser-safe, host-only, simulated/test-only, or unknown; include concrete import-chain evidence for any Node, Python, Pyodide, subprocess, filesystem, native binary, or remote-wrapper dependency.

## SWR-012 Add top-level source module ownership manifest

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/repo-modules
- Fingerprint: 13d7c53593bf3c310f627d478285b6b274e5af98
- Dedupe key: swissknife_refactor:top_level_ownership_manifest
- Depends on: SWR-011
- Outputs: swissknife/src/module-ownership.json, swissknife/docs/source-module-boundaries.md
- Validation: cd swissknife && test -f src/module-ownership.json && test -f docs/source-module-boundaries.md
- Acceptance: Define ownership, allowed imports, browser/host classification, and public entrypoints for `commands`, `entrypoints`, `components`, `screens`, `hooks`, `services`, `storage`, `tasks`, `workers`, `ai`, `models`, `inference`, `shared`, and `utils`; document dependency direction so new work has an explicit home.

## SWR-013 Split CLI and process entrypoints from browser runtime

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/host-boundary
- Fingerprint: f034cba6c22b09b148619121fae506ee1f46fbb4
- Dedupe key: swissknife_refactor:cli_entrypoint_host_split
- Depends on: SWR-011, SWR-012
- Outputs: swissknife/src/entrypoints, swissknife/src/commands, swissknife/src/platform/host.ts, swissknife/src/platform/browser.ts
- Validation: cd swissknife && node scripts/audit-browser-compat.mjs --fail-on-host-imports && npm run build:web
- Acceptance: CLI, terminal, filesystem, process, Node SDK, and command execution code is reachable only through host entrypoints; browser entrypoints cannot statically import CLI/process modules, even through shared utilities or service barrels.

## SWR-014 Enforce UI import boundaries for browser surfaces

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/ui-browser
- Fingerprint: 450156187fe9bf104dd0a013f21ecf0be56b7d43
- Dedupe key: swissknife_refactor:ui_import_boundary
- Depends on: SWR-011, SWR-012
- Outputs: swissknife/src/components, swissknife/src/screens, swissknife/src/hooks, swissknife/scripts/audit-ui-imports.mjs
- Validation: cd swissknife && node scripts/audit-ui-imports.mjs && npm run build:web
- Acceptance: UI modules import only browser-safe platform, service browser barrels, app descriptors, and pure shared helpers; UI cannot import host commands, Node storage, native model providers, external prover wrappers, or test fixtures.

## SWR-015 Harden browser libp2p bootstrap and defaults

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/libp2p
- Fingerprint: 6fc3c539fe8539ea5f847ab923b3e3c3b0ba3d11
- Dedupe key: swissknife_refactor:libp2p_browser_bootstrap
- Depends on: SWR-002
- Outputs: swissknife/src/services/mcp/libp2p-browser-runtime.ts, swissknife/src/services/mcp/mcp-discovery.ts, swissknife/test/mcp-plus-plus
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/mcp-transport-libp2p-runtime.test.ts test/mcp-plus-plus/wasm-prover-browser-purity.test.ts
- Acceptance: Browser libp2p remains enabled by default with WebRTC, WebSockets, circuit relay v2, Noise, Yamux, Identify, and GossipSub where installed; unavailable optional packages are reported as capability gaps, not silently replaced by fake transports.

## SWR-016 Track libp2p and browser bundle budgets

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/libp2p
- Fingerprint: a87e090208371d5a7e38993d924375c20efd1aea
- Dedupe key: swissknife_refactor:libp2p_bundle_budget
- Depends on: SWR-015
- Outputs: swissknife/scripts/audit-web-bundle.mjs, swissknife/docs/browser-bundle-budget.md, swissknife/vite.web.config.ts
- Validation: cd swissknife && npm run build:web && node scripts/audit-web-bundle.mjs --fail-on-host-leakage --report docs/browser-bundle-budget.md
- Acceptance: Web bundle audit records total bundle size, libp2p-related chunks, host-only leakage patterns, Python/Pyodide exposure, and dependency ownership; release gates fail on host imports or unbudgeted libp2p growth.

## SWR-017 Define browser IPFS transport strategy

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/ipfs-browser
- Fingerprint: 3b69697363421e755eb5a06ee0ff20cdc027927b
- Dedupe key: swissknife_refactor:ipfs_browser_transport
- Depends on: SWR-011, SWR-015
- Outputs: swissknife/src/services/ipfs/browser.ts, swissknife/src/services/ipfs/host.ts, swissknife/docs/ipfs-browser-transport.md
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/ipfs-ui-descriptors.test.ts test/mcp-plus-plus/ipfs-accelerate-descriptor-pack.test.ts && node scripts/audit-browser-compat.mjs --module ipfs
- Acceptance: IPFS browser runtime uses browser-safe gateway/libp2p/HTTP adapters with explicit capability reporting; host-only daemon, filesystem, Python, and native IPFS operations remain behind host entrypoints.

## SWR-018 Make browser storage runtime explicit

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/storage-browser
- Fingerprint: 72450726ac1320d99f5d63c2dc89d3510a6ef54d
- Dedupe key: swissknife_refactor:browser_storage_runtime
- Depends on: SWR-011, SWR-014
- Outputs: swissknife/src/storage/browser.ts, swissknife/src/storage/host.ts, swissknife/test/browser
- Validation: cd swissknife && node scripts/audit-browser-compat.mjs --module storage && npm run test:run -- test/browser
- Acceptance: Browser storage code uses IndexedDB, OPFS where available, cache storage, or injected IPFS adapters; Node filesystem, path, and process storage are host-only and cannot enter web bundles.

## SWR-019 Separate Web Worker and Node worker runtimes

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/workers
- Fingerprint: 20d61415f5930d5260373b86fa7de53cd2ee446a
- Dedupe key: swissknife_refactor:web_worker_boundary
- Depends on: SWR-011, SWR-014
- Outputs: swissknife/src/workers/browser.ts, swissknife/src/workers/host.ts, swissknife/build-tools/configs/vite.workers.config.ts
- Validation: cd swissknife && npm run build:workers && node scripts/audit-browser-compat.mjs --module workers
- Acceptance: Browser workers use Web Worker APIs and transferable messages only; Node `worker_threads`, filesystem, and subprocess workers are host-only; Vite worker builds do not include host modules.

## SWR-020 Split model/provider adapters by browser and host capability

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/models
- Fingerprint: d6b3f382c3224cdf5fef3975ad85efa23c4a9987
- Dedupe key: swissknife_refactor:model_provider_browser_host_split
- Depends on: SWR-011, SWR-013
- Outputs: swissknife/src/ai/browser.ts, swissknife/src/ai/host.ts, swissknife/src/models/browser.ts, swissknife/src/models/host.ts
- Validation: cd swissknife && node scripts/audit-browser-compat.mjs --module ai --module models && npm run build:web
- Acceptance: Browser provider adapters use fetch-compatible or user-injected clients only; Node SDKs, Bedrock/Vertex host credentials, local model files, subprocess inference, and native loaders remain host-only.

## SWR-021 Make Pyodide optional and sandboxed, never default runtime

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/browser-safety
- Fingerprint: 028546c5199391f5a35cd4fca526981739025be1
- Dedupe key: swissknife_refactor:pyodide_optional_sandbox
- Depends on: SWR-011, SWR-016
- Outputs: swissknife/src/services/integrations/spacy-wasm-nlp.ts, swissknife/docs/browser-python-policy.md, swissknife/scripts/audit-web-bundle.mjs
- Validation: cd swissknife && npm run build:web && node scripts/audit-web-bundle.mjs --fail-on-default-pyodide
- Acceptance: Pyodide is treated as an explicit optional sandbox capability, not a default browser runtime dependency; ordinary web bundles and service/browser barrels do not load Pyodide unless a user-selected sandbox feature imports it lazily.

## SWR-022 Harden browser ZKP artifact loading and integrity

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/zkp-browser
- Fingerprint: 992c872e7d4bb5b1138cb8e215667aed369a23c8
- Dedupe key: swissknife_refactor:zkp_artifact_loader
- Depends on: SWR-005, SWR-016
- Outputs: swissknife/src/services/zkp/browser-snarkjs-backend.ts, swissknife/src/services/zkp/artifacts, swissknife/docs/browser-zkp-artifacts.md
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/wasm-prover-browser-groth16-semantic.test.ts test/mcp-plus-plus/wasm-prover-browser-zkp-real.test.ts && npm run build:web
- Acceptance: Browser ZKP uses real snarkjs/WASM artifacts with integrity metadata, deterministic artifact resolution, and explicit unavailable errors; simulated proof helpers remain test-only and cannot be selected as production proof backends.

## SWR-023 Normalize app manifests and lazy imports for the web bundle

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/apps-browser
- Fingerprint: 4294cb3f24248ed60725b031891d5d71ea7a45be
- Dedupe key: swissknife_refactor:app_manifest_lazy_imports
- Depends on: SWR-006, SWR-014
- Outputs: swissknife/src/services/apps, swissknife/web/src, swissknife/docs/app-browser-manifest-policy.md
- Validation: cd swissknife && npm run test:run -- test/mcp-plus-plus/all-tools-app-binding-matrix.test.ts test/mcp-plus-plus/all-tools-policy-classifier.test.ts && npm run build:web
- Acceptance: App manifests declare runtime class, browser support, required capabilities, and lazy import target; web builds include only browser-safe app code unless a host-only app is represented as an unavailable/remote capability.

## SWR-024 Add repository module-boundary audit

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/repo-modules
- Fingerprint: fbabac6f2ced96207c1ebcf7b8ae4277c1ea49b6
- Dedupe key: swissknife_refactor:repo_module_audit_script
- Depends on: SWR-012
- Outputs: swissknife/scripts/audit-source-modules.mjs, swissknife/src/module-ownership.json
- Validation: cd swissknife && node scripts/audit-source-modules.mjs --fail-on-unknown --fail-on-forbidden
- Acceptance: A strict audit covers top-level `src` modules with root debt, unknown files, forbidden imports, and legacy compatibility shims reported like `services:audit`; the audit is deterministic and suitable for CI.

## SWR-025 Decompose typecheck into browser-safe lanes

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/typescript
- Fingerprint: 5bd41fe4f8f1e2cf054fb4fa0a372b912bd61989
- Dedupe key: swissknife_refactor:typecheck_lane_decomposition
- Depends on: SWR-003, SWR-011
- Outputs: swissknife/tsconfig.json, swissknife/tsconfig.browser.json, swissknife/tsconfig.host.json, swissknife/package.json
- Validation: cd swissknife && npm run typecheck:browser && npm run typecheck:services
- Acceptance: Browser and service typecheck lanes are green and do not depend on stale declaration outputs; the remaining legacy host/type debt is isolated behind explicit scripts instead of hiding browser regressions.

## SWR-026 Clean legacy web JavaScript from active type/build lanes

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/web-legacy
- Fingerprint: be867ff6965dfff2700fa90d3607500e2b93eeb4
- Dedupe key: swissknife_refactor:legacy_web_js_cleanup
- Depends on: SWR-011, SWR-025
- Outputs: swissknife/web, swissknife/web/tsconfig.json, swissknife/docs/legacy-web-cleanup.md
- Validation: cd swissknife && npm run typecheck:browser && npm run build:web
- Acceptance: Broken backup/corrupt web JavaScript files are archived or excluded from active type/build lanes with documented ownership; browser typecheck covers maintained web code without parsing legacy backup files as production source.

## SWR-027 Make MCP dashboard browser truth explicit

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/mcp-dashboard
- Fingerprint: 4c64b9287b09a837a7dabf8b0b4f34bf52bebc9a
- Dedupe key: swissknife_refactor:mcp_dashboard_browser_truth
- Depends on: SWR-006, SWR-014, SWR-017
- Outputs: swissknife/web/js/apps/mcp-control.js, swissknife/src/services/mcp, swissknife/docs/mcp-dashboard-browser-policy.md
- Validation: cd swissknife && node scripts/test-mcp-dashboard-consumer.cjs && npm run build:web && node scripts/audit-web-bundle.mjs --fail-on-host-leakage
- Acceptance: MCP dashboard distinguishes browser-connectable HTTP/WebSocket/libp2p remotes from host-managed daemon commands; example Python command text cannot be mistaken for browser runtime Python execution.

## SWR-028 Add browser libp2p Playwright evidence

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/libp2p-evidence
- Fingerprint: ec40120479a593b5f5a9e88aac6d39b5601328ab
- Dedupe key: swissknife_refactor:browser_libp2p_playwright_evidence
- Depends on: SWR-015, SWR-016
- Outputs: swissknife/test/e2e, swissknife/test-results/libp2p-browser, swissknife/docs/browser-libp2p-evidence.md
- Validation: cd swissknife && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.libp2p-browser.config.ts
- Acceptance: Playwright evidence captures browser libp2p initialization, unavailable package reporting, relay/bootstrap configuration, and MCP+p2p connection UI state across desktop and mobile viewports.

## SWR-029 Wire browser bundle policy into release gates

- Status: completed
- Completion: manual
- Priority: P1
- Track: refactor/release
- Fingerprint: cd179e0039e16ac037389dedba76e0a031fa34ba
- Dedupe key: swissknife_refactor:release_gate_bundle_policy
- Depends on: SWR-016, SWR-024, SWR-025, SWR-028
- Outputs: swissknife/package.json, swissknife/.github, swissknife/scripts, swissknife/docs/release-browser-gates.md
- Validation: cd swissknife && npm run services:audit && node scripts/audit-source-modules.mjs --fail-on-unknown --fail-on-forbidden && npm run typecheck:browser && npm run test:browser-compat && npm run build:web && node scripts/audit-web-bundle.mjs --fail-on-host-leakage
- Acceptance: Release candidates fail on service/source boundary drift, browser host leakage, libp2p budget drift, missing browser typecheck, missing browser compatibility tests, or stale browser/libp2p evidence.

## SWR-030 Harden supervisor usage for SwissKnife refactor tasks

- Status: completed
- Completion: manual
- Priority: P2
- Track: refactor/supervisor
- Fingerprint: 44ac479612a864bf2bc60c9e95c44caee9183f07
- Dedupe key: swissknife_refactor:supervisor_state_hardening
- Depends on: SWR-010
- Outputs: tmp/swissknife_refactor_supervisor/state, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md, swissknife/docs/supervisor-refactor-runbook.md
- Validation: python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor --once --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md --state-dir tmp/swissknife_refactor_supervisor/state --task-prefix '## SWR-' --state-prefix swissknife_refactor --no-implement --no-ephemeral-worktree --no-worktree-reconciliation --no-retry-budget-guardrail --no-dependency-guardrail --no-reconciliation-guardrail
- Evidence: `tmp/swissknife_refactor_supervisor/state` records bounded supervisor state; `swissknife/docs/supervisor-refactor-runbook.md` documents invocation, state files, daemon `git gc` behavior, and escalation rules.
- Acceptance: SwissKnife refactor tasks can be parsed and supervised in bounded `--once --no-implement` mode without autonomous code edits; state paths, invocation flags, known daemon `git gc` behavior, and safe escalation rules are documented.

## SWR-031 Review completed SwissKnife refactor commit set

- Status: completed
- Priority: P1
- Track: refactor/integration
- Fingerprint: 8cf5183f0cf30e1c95d0ec8138d760efaedb67a3
- Dedupe key: swissknife_refactor:review_completed_commit_set
- Depends on: SWR-029, SWR-030
- Outputs: swissknife/docs/refactor-integration-review.md
- Validation: cd swissknife && test -f docs/refactor-integration-review.md && rg -n "Browser runtime|libp2p|Module boundaries|ZKP|IPFS|Storage|Workers|Release gates" docs/refactor-integration-review.md
- Acceptance: The completed refactor work is grouped by domain with concrete commit/file evidence, review risks, and recommended integration order; the review distinguishes committed SwissKnife changes from unrelated root-repo dirt.

## SWR-032 Re-run clean release-readiness gate and archive output

- Status: completed
- Priority: P1
- Track: refactor/release
- Fingerprint: b52f536feb96b75b970e01d0bc770f4269b20c3e
- Dedupe key: swissknife_refactor:clean_release_gate_archive
- Depends on: SWR-029, SWR-031
- Outputs: swissknife/docs/release-readiness-report.md, swissknife/docs/release-readiness-report.json, swissknife/docs/refactor-release-gate-output.md
- Validation: cd swissknife && npm run release:readiness
- Acceptance: The documented release-readiness gate runs from a clean shell, archives command output and generated reports, and fails if any required service/source audit, browser typecheck, browser compatibility test, web build, bundle audit, or evidence freshness check fails.

## SWR-033 Confirm browser bundle host-leakage and Pyodide policy

- Status: completed
- Priority: P1
- Track: refactor/browser-policy
- Fingerprint: 1da992e3dbcd271cfb4d1e376d5da6267922166a
- Dedupe key: swissknife_refactor:bundle_host_pyodide_policy
- Depends on: SWR-016, SWR-021, SWR-032
- Outputs: swissknife/docs/browser-bundle-budget.md, swissknife/docs/browser-python-policy.md, swissknife/docs/refactor-release-gate-output.md
- Validation: cd swissknife && npm run build:web && node scripts/audit-web-bundle.mjs --dist dist --report docs/browser-bundle-budget.md --json docs/browser-bundle-budget.json --fail-on-host-leakage --fail-on-default-pyodide
- Acceptance: Browser bundle evidence explicitly records zero host leakage and zero default Pyodide runtime exposure; any remaining Python/Pyodide references are documented as optional, sandboxed, or test/evidence-only and are not default browser execution paths.

## SWR-034 Refresh browser libp2p Playwright evidence

- Status: completed
- Priority: P1
- Track: refactor/libp2p
- Fingerprint: e0cf988bf0c32c65268b8a2bcb369866f4442d1c
- Dedupe key: swissknife_refactor:libp2p_playwright_evidence_refresh
- Depends on: SWR-015, SWR-028, SWR-032
- Outputs: swissknife/docs/browser-libp2p-evidence.md, swissknife/docs/browser-libp2p-evidence.fingerprint.json, swissknife/test/e2e, swissknife/build-tools/configs/playwright.libp2p-browser.config.ts
- Validation: cd swissknife && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.libp2p-browser.config.ts
- Acceptance: Browser libp2p evidence is fresh, includes the real browser runtime path, confirms libp2p is enabled by default for browser transport surfaces, and records whether WebRTC, WebSockets, circuit relay v2, Identify, Noise, Yamux, and GossipSub are configured or explicitly unavailable.

## SWR-035 Prepare SwissKnife main-branch merge package

- Status: completed
- Priority: P1
- Track: refactor/integration
- Fingerprint: 5d6420059d17255f49ac839c28fe98e5b48ff936
- Dedupe key: swissknife_refactor:main_branch_merge_package
- Depends on: SWR-031, SWR-032, SWR-033, SWR-034
- Outputs: swissknife/docs/refactor-merge-package.md
- Validation: cd swissknife && test -f docs/refactor-merge-package.md && git status --short && git log --oneline -20
- Acceptance: The merge package identifies the target branch, current SwissKnife HEAD, refactor commits, validation evidence, residual risks, and exact recommended merge commands; it must not rewrite history or merge unrelated root-repo changes without explicit operator approval.

## SWR-036 Create residual browser-compatibility follow-up board

- Status: completed
- Priority: P2
- Track: refactor/follow-up
- Fingerprint: 3317b0ecb15f399f6ec384d5d28cb716421738b7
- Dedupe key: swissknife_refactor:residual_browser_compat_followup_board
- Depends on: SWR-011, SWR-024, SWR-033, SWR-035
- Outputs: implementation_plan/docs/39-swissknife-browser-compatibility-followups-2026-07-08.todo.md, swissknife/docs/browser-compatibility-inventory.md, swissknife/docs/service-boundary-audit.json
- Validation: test -f implementation_plan/docs/39-swissknife-browser-compatibility-followups-2026-07-08.todo.md && cd swissknife && node scripts/audit-browser-compat.mjs --report docs/browser-compatibility-inventory.md && node scripts/audit-source-modules.mjs --fail-on-unknown --fail-on-forbidden
- Acceptance: A new follow-up board exists only for concrete residual `host-only` or `unknown` browser inventory items, with one task per actionable module family; completed SWR work is not duplicated, and every follow-up has validation and browser-compatibility acceptance criteria.

## SWR-037 Audit package exports and browser entry conditions

- Status: completed
- Priority: P1
- Track: refactor/package-browser-api
- Fingerprint: 3a531cd7e771c4f08d3631b1bb5d6f942d9cbad2
- Dedupe key: swissknife_refactor:package_exports_browser_conditions
- Depends on: SWR-035, SWR-036
- Outputs: swissknife/package.json, swissknife/docs/browser-public-api.md, swissknife/scripts/audit-package-browser-exports.mjs
- Validation: cd swissknife && node scripts/audit-package-browser-exports.mjs --fail-on-host-leakage --report docs/browser-public-api.md && npm run typecheck:browser
- Acceptance: Public browser exports resolve only to browser-safe TS/WASM modules; host-only exports are explicitly marked host/runtime-specific; `package.json` browser/import conditions cannot expose Node filesystem, subprocess, Python, native binary, or terminal modules to browser consumers.

## SWR-038 Enforce browser dependency allowlist and Node builtin denylist

- Status: completed
- Priority: P1
- Track: refactor/dependencies
- Fingerprint: b029fded8f0e250a4f49337b8f4954c86bb52e66
- Dedupe key: swissknife_refactor:browser_dependency_allowlist
- Depends on: SWR-032, SWR-033, SWR-037
- Outputs: swissknife/docs/browser-dependency-policy.md, swissknife/scripts/audit-browser-dependencies.mjs, swissknife/package.json
- Validation: cd swissknife && node scripts/audit-browser-dependencies.mjs --fail-on-node-builtins --fail-on-unapproved-polyfills --report docs/browser-dependency-policy.md && npm run build:web
- Acceptance: Browser builds have a documented dependency allowlist, no accidental Node builtin imports, no unapproved browser polyfills, and clear ownership for libp2p, snarkjs/WASM, IPFS, storage, and UI dependencies.

## SWR-039 Make libp2p browser defaults visible in app settings and MCP control

- Status: completed
- Priority: P1
- Track: refactor/libp2p
- Fingerprint: d8656e302ec5d43aa5acdfbe24746904f53797f3
- Dedupe key: swissknife_refactor:libp2p_browser_defaults_ui
- Depends on: SWR-015, SWR-027, SWR-034
- Outputs: swissknife/web/js/apps/mcp-control.js, swissknife/web/js/apps/p2p-network.js, swissknife/src/services/mcp/libp2p-browser-runtime.ts, swissknife/docs/ipfs-browser-transport.md
- Validation: cd swissknife && npm run build:web && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.libp2p-browser.config.ts
- Acceptance: Browser UI and MCP control surfaces show real libp2p browser transport status by default, including WebRTC, WebSockets, circuit relay v2, Identify, Noise, Yamux, and GossipSub; unavailable packages are shown as capability gaps, not hidden fallbacks or fake transports.

## SWR-040 Harden browser WASM asset, integrity, and isolation policy

- Status: completed
- Priority: P1
- Track: refactor/wasm
- Fingerprint: 947c1e63f0ad5ea7b55a99de20ef438f2e2441ec
- Dedupe key: swissknife_refactor:browser_wasm_integrity_isolation
- Depends on: SWR-005, SWR-022, SWR-033
- Outputs: swissknife/docs/browser-wasm-asset-policy.md, swissknife/docs/browser-zkp-artifacts.md, swissknife/src/services/zkp/artifacts, swissknife/scripts/audit-browser-wasm-assets.mjs
- Validation: cd swissknife && node scripts/audit-browser-wasm-assets.mjs --fail-on-missing-integrity --report docs/browser-wasm-asset-policy.md && npm run test:run -- test/mcp-plus-plus/wasm-prover-browser-zkp-real.test.ts test/mcp-plus-plus/wasm-prover-browser-groth16-semantic.test.ts
- Acceptance: Browser WASM assets used by theorem proving, ZKP, and optional NLP/inference paths have deterministic resolution, integrity metadata, cache policy, and documented COOP/COEP/CSP requirements where needed; simulated proof assets remain test-only.

## SWR-041 Add browser deployment policy for CSP, workers, storage, and offline mode

- Status: completed
- Priority: P2
- Track: refactor/browser-deployment
- Fingerprint: acb8db980d9cb88a8bcde5e5d780f97de3fcb67e
- Dedupe key: swissknife_refactor:browser_deployment_policy
- Depends on: SWR-018, SWR-019, SWR-033, SWR-040
- Outputs: swissknife/docs/browser-deployment-policy.md, swissknife/scripts/audit-browser-deployment-policy.mjs, swissknife/build-tools/configs/vite.web.config.ts
- Validation: cd swissknife && node scripts/audit-browser-deployment-policy.mjs --report docs/browser-deployment-policy.md && npm run build:web && npm run test:browser-compat
- Acceptance: Browser deployment requirements for CSP, worker creation, storage APIs, OPFS/IndexedDB/cache storage, WASM isolation, and offline behavior are documented and audited; host-only worker and storage paths cannot enter browser deployment bundles.

## SWR-042 Remediate residual browser inventory host-only and unknown items

- Status: completed
- Priority: P1
- Track: refactor/browser-inventory
- Fingerprint: 55ca9a9299dc0cff5d92eab5978750568d1e956a
- Dedupe key: swissknife_refactor:residual_host_unknown_remediation
- Depends on: SWR-036, SWR-037, SWR-038, SWR-041
- Outputs: swissknife/docs/browser-compatibility-inventory.md, implementation_plan/docs/39-swissknife-browser-compatibility-followups-2026-07-08.todo.md, swissknife/src/platform, swissknife/src/services
- Validation: cd swissknife && node scripts/audit-browser-compat.mjs --report docs/browser-compatibility-inventory.md --json docs/browser-compatibility-inventory.json && node scripts/audit-source-modules.mjs --fail-on-unknown --fail-on-forbidden && npm run build:web
- Acceptance: Each residual `host-only` or `unknown` browser inventory item is either remediated, moved behind an explicit host boundary, or represented in the follow-up board with a concrete owner, import-chain evidence, and validation command.

## SWR-043 Add browser smoke matrix across desktop, mobile, and constrained capabilities

- Status: completed
- Priority: P2
- Track: refactor/e2e
- Fingerprint: b0b83a7632ac2d810fd94ddc6549a76b808f6888
- Dedupe key: swissknife_refactor:browser_smoke_matrix
- Depends on: SWR-028, SWR-034, SWR-039, SWR-042
- Outputs: swissknife/test/e2e/browser-smoke-matrix.spec.ts, swissknife/docs/browser-smoke-matrix-evidence.md, swissknife/build-tools/configs/playwright.browser-smoke.config.ts
- Validation: cd swissknife && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.browser-smoke.config.ts
- Acceptance: Playwright evidence covers desktop and mobile viewport startup, MCP dashboard, libp2p-capable and libp2p-constrained capability states, storage availability, worker availability, and browser-safe app lazy loading without host-module leakage.

## SWR-044 Wire phase-11 browser hardening into release readiness

- Status: completed
- Priority: P1
- Track: refactor/release
- Fingerprint: f50803f4ba49799d1c883541021d367fc1055671
- Dedupe key: swissknife_refactor:phase11_release_readiness
- Depends on: SWR-037, SWR-038, SWR-040, SWR-041, SWR-043
- Outputs: swissknife/scripts/release-readiness-gate.mjs, swissknife/docs/release-browser-gates.md, swissknife/.github/workflows/release-readiness-gates.yml
- Validation: cd swissknife && npm run release:readiness
- Acceptance: Release readiness fails on package export browser leakage, browser dependency allowlist drift, missing WASM integrity metadata, missing deployment policy evidence, stale browser smoke evidence, host leakage, default Pyodide, or stale libp2p evidence.

## SWR-045 Perform final SwissKnife merge dry-run and residual-risk signoff

- Status: completed
- Priority: P1
- Track: refactor/integration
- Fingerprint: dff3b9b093c005b7ab7c0a8249f6317af8e0371f
- Dedupe key: swissknife_refactor:final_merge_dry_run_signoff
- Depends on: SWR-035, SWR-042, SWR-044
- Outputs: swissknife/docs/refactor-merge-package.md, swissknife/docs/refactor-final-signoff.md
- Validation: cd swissknife && test -f docs/refactor-final-signoff.md && npm run release:readiness && git status --short && git log --oneline -30
- Acceptance: Final signoff documents the merge dry-run result, exact commits to merge, release-readiness output, residual browser-compatibility risks, and rollback plan; no unrelated root-repo changes are included in the SwissKnife merge package without explicit operator approval.

## SWR-046 Add browser package-consumer fixture

- Status: completed
- Priority: P1
- Track: refactor/package-browser-api
- Fingerprint: 7c7d3ff03ed3c507f8731b9d90c252798b3439b6
- Dedupe key: swissknife_refactor:browser_package_consumer_fixture
- Depends on: SWR-037, SWR-044
- Outputs: swissknife/test/browser/package-consumer-fixture, swissknife/docs/browser-public-api.md, swissknife/scripts/test-browser-package-consumer.mjs
- Validation: cd swissknife && node scripts/test-browser-package-consumer.mjs && npm run build:web
- Acceptance: A minimal browser-only consumer can import the published browser/API surface without Node builtins, filesystem, subprocess, Python, native binary, terminal UI, or host-only SDK dependencies; failures produce concrete import-chain evidence.

## SWR-047 Add browser libp2p bootstrap and relay matrix

- Status: completed
- Priority: P1
- Track: refactor/libp2p
- Fingerprint: a931c507f55e54d2ae94df29ab0b6e73f5b59c6d
- Dedupe key: swissknife_refactor:browser_libp2p_bootstrap_relay_matrix
- Depends on: SWR-034, SWR-039, SWR-043
- Outputs: swissknife/docs/browser-libp2p-bootstrap-matrix.md, swissknife/test/e2e/libp2p-bootstrap-matrix.spec.ts, swissknife/src/services/mcp/libp2p-browser-runtime.ts
- Validation: cd swissknife && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.libp2p-browser.config.ts --grep "bootstrap|relay|capability"
- Acceptance: Browser libp2p evidence covers default bootstrap behavior, relay-only fallback, WebRTC unavailable mode, WebSocket-only mode, GossipSub availability, and explicit capability-gap reporting without simulated transports.

## SWR-048 Add service worker and offline cache compatibility gate

- Status: completed
- Priority: P2
- Track: refactor/browser-deployment
- Fingerprint: 98424b6635af1d51036ff045f5705070498c8f3f
- Dedupe key: swissknife_refactor:service_worker_offline_cache_gate
- Depends on: SWR-041, SWR-043
- Outputs: swissknife/docs/browser-offline-cache-policy.md, swissknife/test/e2e/browser-offline-cache.spec.ts, swissknife/scripts/audit-browser-offline-cache.mjs
- Validation: cd swissknife && node scripts/audit-browser-offline-cache.mjs --report docs/browser-offline-cache-policy.md && node scripts/run_playwright_test.mjs test -c build-tools/configs/playwright.browser-smoke.config.ts --grep "offline|cache|service worker"
- Acceptance: Offline/cache behavior is explicit for the browser build; service worker, Cache Storage, IndexedDB, OPFS, WASM artifacts, and libp2p bootstrap assets are either cached safely or documented as online-only with user-visible capability state.

## SWR-049 Add browser security headers and cross-origin isolation evidence

- Status: completed
- Priority: P1
- Track: refactor/browser-security
- Fingerprint: 17d72bd7d7f0c55d375a7c3533c172831c4764a0
- Dedupe key: swissknife_refactor:browser_security_headers_isolation
- Depends on: SWR-040, SWR-041, SWR-048
- Outputs: swissknife/docs/browser-security-isolation.md, swissknife/scripts/audit-browser-security-headers.mjs, swissknife/build-tools/configs
- Validation: cd swissknife && node scripts/audit-browser-security-headers.mjs --report docs/browser-security-isolation.md && npm run build:web
- Acceptance: The browser deployment plan documents and validates CSP, COOP, COEP, CORP, worker-src, connect-src for libp2p/WebSocket/gateway traffic, WASM execution requirements, and secure fallback behavior when cross-origin isolation is unavailable.

## SWR-050 Add browser observability without host leakage

- Status: completed
- Priority: P2
- Track: refactor/observability
- Fingerprint: 54e483ab7c968ed4399aa4e6d5d682c9dd5d6a0e
- Dedupe key: swissknife_refactor:browser_observability_no_host_leakage
- Depends on: SWR-038, SWR-043, SWR-049
- Outputs: swissknife/docs/browser-observability-policy.md, swissknife/src/platform/browser.ts, swissknife/scripts/audit-browser-observability.mjs
- Validation: cd swissknife && node scripts/audit-browser-observability.mjs --report docs/browser-observability-policy.md && npm run build:web && node scripts/audit-web-bundle.mjs --fail-on-host-leakage
- Acceptance: Browser diagnostics expose libp2p, IPFS, storage, worker, WASM, and ZKP capability states using browser-safe telemetry only; no Node OpenTelemetry/Sentry server SDK, filesystem logs, process metrics, or host exporters enter browser bundles.

## SWR-051 Add browser API contract tests for MCP, IPFS, storage, workers, and ZKP

- Status: completed
- Priority: P1
- Track: refactor/browser-contracts
- Fingerprint: 94adef36bb31510610ebc7ed88201f1182419828
- Dedupe key: swissknife_refactor:browser_api_contract_tests
- Depends on: SWR-042, SWR-046, SWR-047, SWR-050
- Outputs: swissknife/test/browser/browser-api-contracts.test.ts, swissknife/docs/browser-api-contracts.md
- Validation: cd swissknife && npm run test:browser-compat && npm run test:run -- test/browser/browser-api-contracts.test.ts
- Acceptance: Browser API contract tests exercise MCP transport status, IPFS browser adapters, storage browser adapters, Web Worker adapters, real WASM/ZKP availability, and explicit unavailable states for host-only capabilities.

## SWR-052 Final browser compatibility release candidate gate

- Status: completed
- Priority: P1
- Track: refactor/release
- Fingerprint: d6a1cfca1cdb32b1a340ac0e6c47345a61cc4a32
- Dedupe key: swissknife_refactor:final_browser_compat_release_candidate_gate
- Depends on: SWR-045, SWR-046, SWR-047, SWR-048, SWR-049, SWR-050, SWR-051
- Outputs: swissknife/docs/refactor-final-signoff.md, swissknife/docs/release-readiness-report.md, swissknife/docs/browser-compatibility-inventory.md
- Validation: cd swissknife && npm run release:readiness && node scripts/audit-browser-compat.mjs --report docs/browser-compatibility-inventory.md && git status --short
- Acceptance: The final release-candidate gate proves the browser build is host-leak-free, libp2p is browser-enabled by default with evidence, Python/Pyodide are non-default optional/sandboxed paths, WASM/ZKP assets are integrity-audited, browser package exports are safe, and residual risks are documented before merge.

## SWR-053 Add browser import-map and CDN packaging policy

- Status: completed
- Priority: P2
- Track: refactor/browser-distribution
- Fingerprint: 2f706282c5f8f4e985345e189104ba1f60792748
- Dedupe key: swissknife_refactor:browser_import_map_cdn_packaging
- Depends on: SWR-046, SWR-052
- Outputs: swissknife/docs/browser-distribution-policy.md, swissknife/scripts/audit-browser-distribution.mjs, swissknife/package.json
- Validation: cd swissknife && node scripts/audit-browser-distribution.mjs --report docs/browser-distribution-policy.md && npm run build:web
- Acceptance: Browser distribution policy documents import-map/CDN consumption, ESM entrypoints, asset base paths, WASM artifact paths, libp2p package expectations, and host-only exclusions; generated browser artifacts can be hosted statically without Node server assumptions.

## SWR-054 Add browser dependency upgrade and lockfile drift gate

- Status: completed
- Priority: P2
- Track: refactor/dependencies
- Fingerprint: b18a8614f136f89ef99a5deceaa70a6193798e43
- Dedupe key: swissknife_refactor:browser_dependency_upgrade_lockfile_gate
- Depends on: SWR-038, SWR-052
- Outputs: swissknife/docs/browser-dependency-policy.md, swissknife/scripts/audit-browser-lockfile.mjs, swissknife/package-lock.json
- Validation: cd swissknife && node scripts/audit-browser-lockfile.mjs --report docs/browser-dependency-policy.md && npm run build:web
- Acceptance: Browser-critical dependencies such as libp2p, WebRTC/WebSockets transports, snarkjs/WASM tooling, IPFS/browser storage packages, Vite, Playwright, and Vitest have explicit lockfile drift checks and documented upgrade review criteria.

## SWR-055 Add real-device browser test checklist and evidence template

- Status: completed
- Priority: P2
- Track: refactor/evidence
- Fingerprint: 602b2e3a51c967e810f069e38f495d5f5a9b3b8a
- Dedupe key: swissknife_refactor:real_device_browser_evidence_template
- Depends on: SWR-043, SWR-047, SWR-052
- Outputs: swissknife/docs/browser-real-device-checklist.md, swissknife/docs/browser-smoke-matrix-evidence.md
- Validation: cd swissknife && test -f docs/browser-real-device-checklist.md && rg -n "Chrome|Firefox|Safari|Android|iOS|WebRTC|IndexedDB|WASM|libp2p" docs/browser-real-device-checklist.md
- Acceptance: Real-device validation has an explicit checklist for desktop Chrome/Firefox/Safari, Android, iOS/iPadOS, constrained storage, WebRTC availability, WASM/ZKP execution, libp2p capability gaps, offline behavior, and screenshot/evidence capture.

## SWR-056 Add browser error taxonomy and user-visible capability states

- Status: completed
- Priority: P1
- Track: refactor/browser-ux
- Fingerprint: f51ad49723495d2ae311ce3b8a2e19fed19ce9b4
- Dedupe key: swissknife_refactor:browser_error_taxonomy_capability_states
- Depends on: SWR-039, SWR-050, SWR-051
- Outputs: swissknife/docs/browser-capability-error-taxonomy.md, swissknife/src/platform/browser.ts, swissknife/web/js
- Validation: cd swissknife && node scripts/audit-browser-observability.mjs --report docs/browser-observability-policy.md && npm run build:web
- Acceptance: Browser users see explicit capability states for unavailable libp2p transports, blocked storage APIs, missing cross-origin isolation, missing WASM artifacts, unavailable ZKP backends, and host-only actions; errors do not imply Python/native fallback in browser mode.

## SWR-057 Add browser performance budget and startup regression gate

- Status: completed
- Priority: P2
- Track: refactor/performance
- Fingerprint: 48bb45d5a06440f05f4c49e4837e83f63ad9599c
- Dedupe key: swissknife_refactor:browser_performance_budget_startup_gate
- Depends on: SWR-016, SWR-043, SWR-052
- Outputs: swissknife/docs/browser-performance-budget.md, swissknife/scripts/audit-browser-performance-budget.mjs, swissknife/docs/browser-bundle-budget.md
- Validation: cd swissknife && node scripts/audit-browser-performance-budget.mjs --report docs/browser-performance-budget.md && npm run build:web
- Acceptance: Browser startup, lazy-app chunks, libp2p chunks, WASM/ZKP assets, and total gzip/raw bundle budgets are documented and audited; regressions require an explicit budget update with evidence.

## SWR-058 Add browser rollback and feature-flag safety plan

- Status: completed
- Priority: P2
- Track: refactor/release
- Fingerprint: d45ef2c9401bdca46c0428e47e2ff43461efb2fa
- Dedupe key: swissknife_refactor:browser_rollback_feature_flag_plan
- Depends on: SWR-045, SWR-052, SWR-056
- Outputs: swissknife/docs/browser-release-rollback-plan.md, swissknife/docs/refactor-final-signoff.md
- Validation: cd swissknife && test -f docs/browser-release-rollback-plan.md && rg -n "rollback|feature flag|libp2p|WASM|storage|MCP|ZKP" docs/browser-release-rollback-plan.md
- Acceptance: The browser release has documented rollback steps and feature-flag controls for libp2p browser defaulting, MCP dashboard remote modes, optional Pyodide/sandbox features, WASM/ZKP backends, storage providers, and offline/cache behavior.

## SWR-059 Add browser architecture decision records

- Status: completed
- Priority: P3
- Track: refactor/docs
- Fingerprint: 3f3f946c9784d4769924656ea4ad0127ec5e639e
- Dedupe key: swissknife_refactor:browser_architecture_decision_records
- Depends on: SWR-041, SWR-049, SWR-052
- Outputs: swissknife/docs/adr/browser-runtime-boundaries.md, swissknife/docs/adr/browser-libp2p-defaults.md, swissknife/docs/adr/browser-wasm-zkp-policy.md
- Validation: cd swissknife && test -f docs/adr/browser-runtime-boundaries.md && test -f docs/adr/browser-libp2p-defaults.md && test -f docs/adr/browser-wasm-zkp-policy.md
- Acceptance: ADRs capture the permanent decisions for browser/host boundaries, libp2p browser defaults and capability gaps, WASM/ZKP integrity and simulation policy, and why Python/native wrappers are excluded from browser runtime paths.

## SWR-060 Final supervisor closeout and handoff report

- Status: completed
- Priority: P1
- Track: refactor/supervisor
- Fingerprint: 69d64dbb72b34fc3938789f4a3dbd7a6d477b784
- Dedupe key: swissknife_refactor:final_supervisor_closeout_handoff
- Depends on: SWR-052, SWR-053, SWR-054, SWR-055, SWR-056, SWR-057, SWR-058, SWR-059
- Outputs: swissknife/docs/refactor-final-signoff.md, swissknife/docs/supervisor-refactor-runbook.md, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor --once --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md --state-dir tmp/swissknife_refactor_supervisor/state --task-prefix '## SWR-' --state-prefix swissknife_refactor --no-implement --no-ephemeral-worktree --no-worktree-reconciliation --no-retry-budget-guardrail --no-dependency-guardrail --no-reconciliation-guardrail (passes on 2026-07-09; `stuck: False`, `active_task_id: SWR-060`, `completed_count: 59`, `blocked_task_ids: []` while this closeout attempt was still active)
- Closeout: `swissknife/docs/refactor-final-signoff.md` records the SWR task accounting, validation evidence for SWR-052 through SWR-059, generated follow-up board state, merge-readiness state, supervisor state paths, and residual browser-compatibility risks. `swissknife/docs/supervisor-refactor-runbook.md` records the bounded parse command, expected final task-count interpretation, state review commands, follow-up board handling, and merge handoff checklist.
- Acceptance: Final closeout report records task completion counts, validation evidence, generated follow-up boards, merge-readiness state, supervisor state paths, and any remaining browser-compatibility risks; no active SWR tasks remain unaccounted for. All SWR tasks in this board are now accounted for as completed in durable task metadata.

## Phase 13: Service De-Duplication And Browser Runtime Hardening

This phase reopens the supervisor queue after the SWR-060 closeout because the
working tree may contain restored or parallel service files. Start with service
duplicate cleanup, then continue the repository refactor with browser/libp2p as
the default runtime target. The browser contract remains: no Python wrapper,
native subprocess, Node-only builtin, simulated ZKP fallback, or host-only
libp2p path may be used by default from browser entrypoints.

Current duplicate-risk scan:

- No byte-identical duplicates were found under `swissknife/src/services`.
- Duplicate basenames requiring ownership decisions:
  - `logic-formatter.ts`: `src/services/fol-utils` and `src/services/fol`.
  - `nlp-predicate-extractor.ts`: `src/services/fol-utils` and root `src/services`.
  - `spacy-wasm-nlp.ts`: root shim and `src/services/integrations`.
  - `zkp-ucan-bridge.ts`: root implementation and `src/services/zkp`.
  - `index.ts`: intentional per-module barrels unless audit proves otherwise.
- Legacy sprint-named service files requiring descriptive module-owned names:
  `cec-sprint63-utils.ts`, `sprint64-modules.ts`,
  `sprint65-storage-parsers.ts`, `sprint65-utils.ts`,
  `sprint66-dcec-types.ts`, `sprint66-prover-utils.ts`,
  `sprint67-crypto-utils.ts`, `sprint67-groth16-cec.ts`,
  `sprint67-nlp-types.ts`, `sprint68-eth-bridge.ts`,
  `sprint68-prover-wrappers.ts`, and `sprint68-utils-types.ts`.

## SWR-061 Audit and remediate restored duplicate service files

- Status: completed
- Priority: P0
- Track: refactor/services
- Dedupe key: swissknife_refactor:service_duplicate_remediation
- Depends on: SWR-060
- Outputs: swissknife/docs/services-duplicate-file-audit.md, swissknife/docs/service-boundary-audit.json, swissknife/src/module-ownership.json
- Validation: cd swissknife && npm run services:audit
- Acceptance: Produce a durable duplicate-file audit that distinguishes intentional module barrels from accidental restored files; consolidate or remove accidental root service duplicates; update imports to canonical module-owned paths; preserve compatibility only where explicitly documented as a temporary deprecation bridge; keep the service audit strict with no unknown files, no forbidden imports, and no legacy root import specifiers.

## SWR-062 Rename legacy sprint service files into descriptive owned modules

- Status: completed
- Priority: P0
- Track: refactor/services
- Dedupe key: swissknife_refactor:rename_legacy_sprint_services
- Depends on: SWR-061
- Outputs: swissknife/docs/services-sprint-rename-map.md, swissknife/src/services/MODULE_BOUNDARIES.md, swissknife/src/module-ownership.json
- Validation: cd swissknife && npm run services:audit && ! find src/services -type f -name '*sprint*' | grep .
- Acceptance: Replace sprint-number filenames with descriptive module-owned names, update all imports and tests, document the rename map for reviewers, and avoid long-lived sprint compatibility shims unless an external public import is proven and recorded with an explicit deprecation date.

## SWR-063 Define canonical service public APIs after duplicate cleanup

- Status: completed
- Priority: P0
- Track: refactor/services
- Dedupe key: swissknife_refactor:canonical_service_public_apis
- Depends on: SWR-061, SWR-062
- Outputs: swissknife/docs/source-module-boundaries.md, swissknife/src/services/MODULE_BOUNDARIES.md, swissknife/src/module-ownership.json
- Validation: cd swissknife && npm run services:audit && npm run typecheck:services
- Acceptance: Each service family exposes one canonical browser-safe or environment-neutral public API barrel; root-level service imports are either removed or documented as host-only/deprecated; internal helpers stay within their owning module; cross-module imports go through documented public APIs.

## SWR-064 Re-run browser compatibility inventory after service de-duplication

- Status: completed
- Priority: P0
- Track: browser/refactor
- Dedupe key: swissknife_refactor:post_duplicate_browser_inventory
- Depends on: SWR-063
- Outputs: swissknife/docs/browser-compatibility-inventory.md, swissknife/docs/browser-compatibility-report.json, swissknife/docs/browser-compatibility-inventory.json
- Validation: cd swissknife && npm run browser:compat:inventory
- Acceptance: Refresh the browser compatibility inventory after the service cleanup and prove that canonical service paths are classified correctly as browser-safe, host-only, optional sandbox, or test-only; any remaining unknown service item must have a follow-up task or a failing gate.

## SWR-065 Make browser libp2p the default in web-facing service consumers

- Status: completed
- Priority: P0
- Track: browser/libp2p
- Dedupe key: swissknife_refactor:libp2p_browser_default_consumers
- Depends on: SWR-063, SWR-064
- Outputs: swissknife/src/services/mcp/libp2p-browser-runtime.ts, swissknife/web/js/apps/p2p-network.js, swissknife/web/js/apps/mcp-control.js, swissknife/docs/browser-smoke-matrix-evidence.md
- Validation: cd swissknife && npm run test:browser-smoke
- Acceptance: Web-facing MCP, P2P, and control-surface consumers instantiate the browser libp2p runtime by default where capability is available; unsupported capabilities surface typed browser capability states instead of silently falling back to host/native transports.

## SWR-066 Enforce post-cleanup browser no-host-leakage gates

- Status: completed
- Priority: P0
- Track: browser/security
- Dedupe key: swissknife_refactor:post_cleanup_browser_no_host_leakage
- Depends on: SWR-064, SWR-065
- Outputs: swissknife/docs/browser-bundle-budget.md, swissknife/docs/browser-bundle-budget.json, swissknife/docs/browser-dependency-policy.md
- Validation: cd swissknife && npm run audit:web-bundle && npm run audit:browser-lockfile
- Acceptance: Browser bundles and dependency gates fail on accidental Node builtin imports, subprocess/filesystem bindings, Python wrapper paths, native prover shims, or host libp2p transports in browser entrypoints.

## SWR-067 Prove browser ZKP paths use real TS/WASM proof backends by default

- Status: completed
- Priority: P0
- Track: browser/zkp
- Dedupe key: swissknife_refactor:browser_zkp_real_backend_regression_gate
- Depends on: SWR-063, SWR-066
- Outputs: swissknife/docs/browser-wasm-zkp-policy.md, swissknife/docs/browser-api-contracts.md, swissknife/test/browser/browser-api-contracts.test.ts
- Validation: cd swissknife && npm run test:browser-api-contracts
- Acceptance: Browser ZKP service contracts exercise real TS/WASM proof generation and verification by default; simulated/test-only provers are explicitly named, opt-in, and rejected by the default browser API contract gate.

## SWR-068 Add browser package-consumer regression for canonical service APIs

- Status: completed
- Priority: P1
- Track: browser/packaging
- Dedupe key: swissknife_refactor:browser_package_consumer_canonical_services
- Depends on: SWR-063, SWR-066, SWR-067
- Outputs: swissknife/test/browser-compat/browser-entrypoints.test.js, swissknife/docs/browser-distribution-policy.md, swissknife/package.json
- Validation: cd swissknife && npm run test:browser-entrypoints
- Acceptance: A browser-like package consumer can import canonical service APIs, MCP/libp2p browser runtime, IPFS browser runtime, worker-safe helpers, and ZKP browser APIs without resolving host-only modules or Python/native wrapper code.

## SWR-069 Refresh release readiness after service duplicate cleanup

- Status: completed
- Priority: P1
- Track: release
- Dedupe key: swissknife_refactor:post_duplicate_release_readiness
- Depends on: SWR-064, SWR-065, SWR-066, SWR-067, SWR-068
- Outputs: swissknife/docs/release-readiness-report.md, swissknife/docs/release-readiness-report.json, swissknife/docs/release-evidence-freshness.md, swissknife/docs/refactor-final-signoff.md
- Validation: cd swissknife && npm run release:readiness
- Acceptance: Release-readiness evidence is regenerated after duplicate cleanup and records service-boundary status, browser/libp2p default status, browser no-host-leakage status, ZKP real-backend status, and residual risks with no untracked active SWR tasks.

## SWR-070 Supervisor handoff for the reopened service/browser refactor phase

- Status: completed
- Priority: P1
- Track: refactor/supervisor
- Dedupe key: swissknife_refactor:phase_13_supervisor_handoff
- Depends on: SWR-061, SWR-062, SWR-063, SWR-064, SWR-065, SWR-066, SWR-067, SWR-068, SWR-069
- Outputs: swissknife/docs/refactor-final-signoff.md, swissknife/docs/supervisor-refactor-runbook.md, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor --once --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md --state-dir tmp/swissknife_refactor_supervisor/state --task-prefix '## SWR-' --state-prefix swissknife_refactor --no-implement --no-ephemeral-worktree --no-worktree-reconciliation --no-retry-budget-guardrail --no-dependency-guardrail --no-reconciliation-guardrail
- Evidence: `swissknife/docs/refactor-final-signoff.md` records Phase 13 accounting for SWR-061 through SWR-070, evidence paths, validation commands, live supervisor PID/state/log paths, and residual browser/service risks. `swissknife/docs/supervisor-refactor-runbook.md` records the bounded parse command, Phase 13 closeout checklist, active state inspection commands, per-task validation matrix, and handoff rules for a live `--implement` supervisor. Runtime receipts are under `tmp/swissknife_refactor_supervisor/state`, including `swissknife_refactor_task_state.json`, `swissknife_refactor_supervisor_status.json`, `swissknife_refactor_events.jsonl`, and `implementation_logs/swr-061-attempt-1.log` through `implementation_logs/swr-070-attempt-1.log`.
- Handoff: At the SWR-070 handoff snapshot, SWR-061 through SWR-069 were completed with passing supervisor validation receipts, SWR-070 was the only active ready task, waiting and blocked task counts were zero, and no reopened Phase 13 task was unaccounted for. The final SWR-070 status transition remains owned by the implementation supervisor after validation.
- Acceptance: The supervisor handoff records the reopened Phase 13 task accounting, evidence paths, validation commands, active process/state paths, and any remaining browser compatibility or service duplicate risks; no Phase 13 task remains unaccounted for.

## Phase 14: Regression-Proof Service Ownership And Browser Libp2p Runtime

This phase reopens the queue because the live `src/services` tree still contains
duplicate-prone root service files and legacy sprint-named files after the prior
closeout. The first priority is not another document-only audit: make the
service/source audit fail on restored duplicate files, ambiguous root service
targets, and legacy sprint filenames so these regressions cannot silently return.

Fresh scan inputs:

- Duplicate basenames currently present under `swissknife/src/services`:
  - `logic-formatter.ts`: `src/services/fol-utils/logic-formatter.ts` and `src/services/fol/logic-formatter.ts`.
  - `nlp-predicate-extractor.ts`: `src/services/fol-utils/nlp-predicate-extractor.ts` and root `src/services/nlp-predicate-extractor.ts`.
  - `spacy-wasm-nlp.ts`: `src/services/integrations/spacy-wasm-nlp.ts` and root `src/services/spacy-wasm-nlp.ts`.
  - `zkp-ucan-bridge.ts`: `src/services/zkp/zkp-ucan-bridge.ts` and root `src/services/zkp-ucan-bridge.ts`.
  - `index.ts`: module barrels under `fol-utils` and `zkp/artifacts`; allow only if explicitly allowlisted.
- Legacy sprint-named service files currently present:
  `cec-sprint63-utils.ts`, `sprint64-modules.ts`,
  `sprint65-storage-parsers.ts`, `sprint65-utils.ts`,
  `sprint66-dcec-types.ts`, `sprint66-prover-utils.ts`,
  `sprint67-crypto-utils.ts`, `sprint67-groth16-cec.ts`,
  `sprint67-nlp-types.ts`, `sprint68-eth-bridge.ts`,
  `sprint68-prover-wrappers.ts`, and `sprint68-utils-types.ts`.
- Web runtime work currently has an untracked `web/js/services/mcp/libp2p-browser-runtime.js`;
  it must be reconciled with canonical TypeScript/browser packaging rather than
  becoming an unmanaged parallel runtime.

## SWR-071 Make restored duplicate service files a failing audit gate

- Status: completed
- Priority: P0
- Track: refactor/services
- Dedupe key: swissknife_refactor:duplicate_service_gate_regression
- Depends on: SWR-070
- Outputs: swissknife/scripts/audit-source-modules.mjs, swissknife/src/module-ownership.json, swissknife/docs/service-boundary-audit.json, swissknife/docs/services-duplicate-file-audit.md
- Validation: cd swissknife && npm run services:audit
- Acceptance: The service/source audit fails on non-allowlisted duplicate service basenames, restored root duplicate targets, and imports that resolve to legacy root service files; intentional module barrels are explicitly allowlisted with reasons; the current restored duplicate files are either removed, moved, or marked with a temporary deprecation plan that still fails browser entrypoints if imported.

## SWR-072 Remove restored root service duplicates and retarget imports

- Status: completed
- Priority: P0
- Track: refactor/services
- Dedupe key: swissknife_refactor:remove_restored_root_service_duplicates
- Depends on: SWR-071
- Outputs: swissknife/docs/services-duplicate-file-audit.md, swissknife/src/services/MODULE_BOUNDARIES.md, swissknife/src/module-ownership.json
- Validation: cd swissknife && npm run services:audit && test ! -e src/services/nlp-predicate-extractor.ts && test ! -e src/services/spacy-wasm-nlp.ts && test ! -e src/services/zkp-ucan-bridge.ts
- Acceptance: Root duplicate service files are removed or replaced only by explicitly documented public compatibility exports outside browser paths; active imports target canonical module-owned paths under `fol-utils`, `integrations`, and `zkp`; no browser entrypoint imports a root duplicate or compatibility shim.

## SWR-073 Rename legacy sprint service files into descriptive module-owned files

- Status: completed
- Priority: P0
- Track: refactor/services
- Dedupe key: swissknife_refactor:remove_sprint_named_services_regression
- Depends on: SWR-071
- Outputs: swissknife/docs/services-sprint-rename-map.md, swissknife/src/services/MODULE_BOUNDARIES.md, swissknife/src/module-ownership.json
- Validation: cd swissknife && npm run services:audit && ! find src/services -type f -name '*sprint*' | grep .
- Acceptance: Every `*sprint*` service file is renamed to a descriptive module-owned filename, all imports/tests are retargeted, and the audit fails if future sprint-number service filenames are introduced.

## SWR-074 Canonicalize logic language and deontic NLP service ownership

- Status: completed
- Priority: P0
- Track: refactor/logic
- Dedupe key: swissknife_refactor:logic_language_deontic_nlp_ownership
- Depends on: SWR-072, SWR-073
- Outputs: swissknife/src/services/logic-language-pipeline.ts, swissknife/src/services/deontic-nlp-ontology-types.ts, swissknife/docs/source-module-boundaries.md
- Validation: cd swissknife && npm run typecheck:services && npm run services:audit
- Acceptance: Logic-language and deontic NLP code has one canonical module owner, no sprint-number or root-duplicate helper path, and browser-safe exports are separated from host-only or optional sandbox functionality.

## SWR-075 Reconcile web JavaScript libp2p runtime with canonical TypeScript services

- Status: completed
- Priority: P0
- Track: browser/libp2p
- Dedupe key: swissknife_refactor:web_js_libp2p_runtime_reconciliation
- Depends on: SWR-072, SWR-074
- Outputs: swissknife/src/services/mcp/libp2p-browser-runtime.ts, swissknife/web/js/services/mcp/libp2p-browser-runtime.js, swissknife/web/js/apps/mcp-control.js, swissknife/web/js/apps/p2p-network.js
- Validation: cd swissknife && npm run test:browser-smoke
- Acceptance: Web-facing JavaScript uses the canonical browser libp2p runtime contract rather than an unmanaged parallel implementation; libp2p is enabled by default where browser capabilities exist, and unavailable transports surface typed capability states instead of falling back to host/native paths.

## SWR-076 Add browser runtime package fixture for service de-duplication regressions

- Status: completed
- Priority: P0
- Track: browser/packaging
- Dedupe key: swissknife_refactor:browser_fixture_service_dedup_regressions
- Depends on: SWR-072, SWR-075
- Outputs: swissknife/test/browser-compat/browser-entrypoints.test.js, swissknife/docs/browser-distribution-policy.md, swissknife/package.json
- Validation: cd swissknife && npm run test:browser-entrypoints
- Acceptance: A browser-like package consumer can import MCP/libp2p, IPFS, logic-language, deontic NLP, and ZKP APIs without resolving root duplicate services, sprint-named services, Node builtins, Python wrappers, subprocess adapters, or native prover shims.

## SWR-077 Refresh browser inventory and no-host-leakage evidence after cleanup

- Status: completed
- Priority: P0
- Track: browser/security
- Dedupe key: swissknife_refactor:post_dedup_browser_inventory_no_host_leakage
- Depends on: SWR-075, SWR-076
- Outputs: swissknife/docs/browser-compatibility-inventory.md, swissknife/docs/browser-compatibility-report.json, swissknife/docs/browser-bundle-budget.md, swissknife/docs/browser-bundle-budget.json
- Validation: cd swissknife && npm run browser:compat:inventory && npm run audit:web-bundle
- Acceptance: Browser inventory and bundle scans are regenerated after duplicate cleanup; browser entrypoints have no Node builtin, filesystem, subprocess, Python wrapper, native prover, or host-libp2p leakage; remaining unknown or host-only items are tracked with explicit non-browser boundaries.

## SWR-078 Re-verify browser ZKP uses real TS/WASM paths after service cleanup

- Status: completed
- Priority: P0
- Track: browser/zkp
- Dedupe key: swissknife_refactor:post_dedup_real_zkp_browser_gate
- Depends on: SWR-072, SWR-077
- Outputs: swissknife/docs/browser-wasm-zkp-policy.md, swissknife/docs/browser-api-contracts.md, swissknife/test/browser/browser-api-contracts.test.ts
- Validation: cd swissknife && npm run test:browser-api-contracts
- Acceptance: Browser ZKP proof generation and verification exercise real TS/WASM backends by default; simulated/test-only proofs are opt-in, clearly named, and rejected by default browser API contract tests.

## SWR-079 Run release-readiness and merge-hygiene report for Phase 14

- Status: completed
- Priority: P1
- Track: release
- Dedupe key: swissknife_refactor:phase_14_release_readiness_merge_hygiene
- Depends on: SWR-076, SWR-077, SWR-078
- Outputs: swissknife/docs/release-readiness-report.md, swissknife/docs/release-readiness-report.json, swissknife/docs/refactor-final-signoff.md
- Validation: cd swissknife && npm run release:readiness
- Acceptance: Release readiness records duplicate-service gate status, sprint-file removal status, browser-default libp2p evidence, no-host-leakage evidence, real browser ZKP evidence, dirty worktree summary, and merge risks.
- Evidence: 2026-07-09 `cd swissknife && npm run release:readiness` completed with `overallStatus: passed`; the persisted report records 9 passed, 0 failed, and 2 skipped gates after separately refreshed build evidence. `docs/service-boundary-audit.json` recorded `serviceDuplicateBasenames: 0` and `legacySprintServiceFiles: 0`; `npm run build:web` recorded host leakage 0 and default Pyodide 0; browser/libp2p Playwright freshness was regenerated and fresh.

## SWR-080 Supervisor closeout for Phase 14 regression-proofing

- Status: completed
- Priority: P1
- Track: refactor/supervisor
- Dedupe key: swissknife_refactor:phase_14_supervisor_closeout
- Depends on: SWR-071, SWR-072, SWR-073, SWR-074, SWR-075, SWR-076, SWR-077, SWR-078, SWR-079
- Outputs: swissknife/docs/refactor-final-signoff.md, swissknife/docs/supervisor-refactor-runbook.md, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor --once --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md --state-dir tmp/swissknife_refactor_supervisor/state --task-prefix '## SWR-' --state-prefix swissknife_refactor --no-implement --no-ephemeral-worktree --no-worktree-reconciliation --no-retry-budget-guardrail --no-dependency-guardrail --no-reconciliation-guardrail
- Acceptance: Phase 14 closeout records task accounting, validation evidence, supervisor state paths, duplicate-regression gates, browser/libp2p runtime evidence, real ZKP evidence, and residual risks; no Phase 14 task remains unaccounted for.
- Evidence: 2026-07-09 Phase 14 closeout recorded after service duplicate cleanup, descriptive service renames, browser libp2p default-status runtime export repair, release-readiness pass, and regenerated browser/libp2p evidence. Supervisor state path remains `tmp/swissknife_refactor_supervisor/state/swissknife_refactor_task_state.json`; no implement-mode supervisor is left running after cleanup.

## Phase 15: Exhaustive MCP Hierarchy And Virtual Desktop Tool Closure

This phase tracks the remaining issues found by the live MCP hierarchy diagnosis
after the release evidence returned to `GO`. The configured SwissKnife endpoints
are reachable and representative dispatch works, but the taskboard must now close
the difference between "visible as flat descriptors" and "fully routable through
the hierarchical MCP++ facade", then prove every virtual desktop app has an
intentional backend and ORB/glasses simulator route.

Fresh scan inputs:

- `test-results/virtual-desktop-ipfs-mcp-orb/hierarchical-tools-evidence.json`
  reports all three configured services available with the full facade present:
  `tools_list_categories`, `tools_list_tools`, `tools_get_schema`, and
  `tools_dispatch`.
- The live configured tool surface is 553 tools across `ipfs_kit_py`,
  `ipfs_datasets_py`, and the `ipfs_accelerate_py` compatibility adapter; the
  all-tools ledger records 661 tools when the real-local accelerate source
  surface is included.
- `ipfs_datasets_py` remains the open hierarchy gap: 336 flat non-meta
  descriptors, 131 category-listed hierarchical entries, a 205 aggregate count
  gap, and a stricter normalized-name gap currently reported as 236 descriptors.
  Examples include direct/root policy and compliance tools such as
  `policy_list`, `interface_list`, and `compliance_list_rules`, plus legacy
  category-qualified descriptors such as `admin_tools.admin_tools` and
  `development_tools.github_cli_tools`.
- The current all-tools matrix proves 38 virtual desktop apps, 553 app-visible
  tools, 104 ORB/IDL descriptors, and 104 glasses projections, but only three
  app ids currently own generated all-tools bindings: `ipfs-explorer`,
  `mcp-control`, and `model-browser`.
- The Meta glasses validation lane must use simulator evidence rather than
  assuming a desktop can pair directly to physical glasses.

## SWR-081 Close the ipfs_datasets_py flat-to-hierarchical catalog gap

- Status: completed
- Priority: P0
- Track: mcp/hierarchy
- Dedupe key: swissknife_refactor:ipfs_datasets_flat_hierarchy_gap_closure
- Depends on: SWR-080
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/hierarchical-tools-evidence.json, swissknife/docs/ipfs-datasets-hierarchical-tool-gap.md
- Validation: cd swissknife && node scripts/capture-hierarchical-mcp-tools-evidence.cjs
- Acceptance: Every live `ipfs_datasets_py` non-meta flat descriptor is either listed through `tools_list_categories` plus `tools_list_tools`, explicitly marked as direct-only with a documented reason and policy class, or removed from the SwissKnife app-visible ledger; the hierarchy evidence reports zero unexplained flat/direct descriptor gaps for `ipfs_datasets_py`.

## SWR-082 Add normalized category/name aliasing for datasets hierarchical dispatch

- Status: completed
- Priority: P0
- Track: mcp/hierarchy
- Dedupe key: swissknife_refactor:ipfs_datasets_hierarchy_name_aliases
- Depends on: SWR-081
- Outputs: swissknife/scripts/capture-hierarchical-mcp-tools-evidence.cjs, swissknife/src/services/mcp, swissknife/test/mcp-plus-plus
- Validation: cd swissknife && node scripts/capture-hierarchical-mcp-tools-evidence.cjs && npm run evidence:mcp-glasses
- Acceptance: Hierarchical routing accepts and validates canonical, category-qualified, and underscore-qualified tool names where the server exposes equivalent descriptors; representative examples such as `bespoke_tools.system_status`, `bespoke_tools/system_status`, and direct root policy/compliance tools either dispatch successfully or produce a typed direct-only response with receipt evidence.

## SWR-083 Promote the hierarchical MCP evidence report into the release gate

- Status: completed
- Priority: P0
- Track: release/evidence
- Dedupe key: swissknife_refactor:hierarchical_mcp_release_gate
- Depends on: SWR-081, SWR-082
- Outputs: swissknife/scripts/build-virtual-desktop-release-evidence.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/release-evidence.json, swissknife/docs/release-readiness-report.md
- Validation: cd swissknife && node scripts/capture-hierarchical-mcp-tools-evidence.cjs && node scripts/build-virtual-desktop-release-evidence.cjs && npm run release:readiness
- Acceptance: The virtual-desktop release gate consumes `hierarchical-tools-evidence.json`, fails on missing facade meta-tools or failed representative dispatch, and records any remaining direct-only descriptors as explicit warnings or blockers rather than silent pass-through.

## SWR-084 Expand all-tools bindings from three generated app families to every intended virtual desktop app

- Status: completed
- Priority: P0
- Track: virtual-desktop/apps
- Dedupe key: swissknife_refactor:all_virtual_desktop_app_tool_binding_coverage
- Depends on: SWR-083
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-tools-app-bindings.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/capability-matrix.json, swissknife/docs/virtual-desktop-all-tools-app-coverage.md
- Validation: cd swissknife && node scripts/capture-ipfs-mcp-all-tools-ledger.cjs && node scripts/build-all-tools-capability-matrix.cjs
- Acceptance: Every virtual desktop app has an intentional MCP backend binding state: concrete app-owned tool bindings where the app should use `ipfs_kit_py`, `ipfs_datasets_py`, or `ipfs_accelerate_py`, or an explicit `manifest_only`/`not_applicable` rationale where the app is deliberately not tool-backed. The matrix must distinguish app-visible, desktop/mobile-only, and supervisor-only capabilities without hiding unbound apps behind the three generic generated app ids.

## SWR-085 Add end-to-end UI/UX smoke coverage for tool-backed virtual desktop apps

- Status: completed
- Priority: P0
- Track: virtual-desktop/e2e
- Dedupe key: swissknife_refactor:tool_backed_virtual_desktop_ui_smoke
- Depends on: SWR-084
- Outputs: swissknife/test/mcp-plus-plus, swissknife/docs/virtual-desktop-tool-ui-smoke-evidence.md, swissknife/test-results/virtual-desktop-ipfs-mcp-orb
- Validation: cd swissknife && npm run test:e2e:mcp && npm run evidence:mcp-glasses
- Acceptance: Each app with MCP-backed capabilities has at least one UI path that opens the app, renders the relevant control state, handles success/fallback/error states, and records a receipt or screenshot artifact proving the app uses the intended backend without breaking the desktop UX.

## SWR-086 Use the Meta glasses simulator for ORB/IDL handoff evidence

- Status: completed
- Priority: P0
- Track: glasses/simulator
- Dedupe key: swissknife_refactor:meta_glasses_simulator_orb_idl_handoff
- Depends on: SWR-084, SWR-085
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/glasses-simulator-handoff.json, swissknife/docs/meta-glasses-simulator-evidence.md, swissknife/test/mcp-plus-plus
- Validation: cd swissknife && npm run test:e2e:meta-glasses && npm run evidence:mcp-glasses
- Acceptance: Meta glasses handoff validation uses simulator-driven evidence for display, camera, speaker, and microphone capabilities; no task assumes direct desktop pairing to physical glasses. ORB/IDL projections must prove simulator-visible display states, audio/microphone capability policy states, camera permission/fallback states, and desktop/mobile handoff behavior.

## SWR-087 Preserve accelerate compatibility adapter readiness and PID evidence

- Status: completed
- Priority: P1
- Track: mcp/accelerate
- Dedupe key: swissknife_refactor:accelerate_compat_adapter_process_evidence
- Depends on: SWR-083
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ipfs-accelerate-compat.pid, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ipfs-accelerate-adapter-coverage.json, swissknife/docs/ipfs-accelerate-compat-adapter-runbook.md
- Validation: cd swissknife && node scripts/capture-ipfs-accelerate-adapter-coverage.cjs && ss -ltnp | grep ':3003'
- Acceptance: The configured `ipfs_accelerate_py` compatibility adapter remains restartable and verifiable, exposes the full hierarchical facade, maps normalized required aliases to real upstream tools, and records PID/listener evidence so future supervisor runs do not mistake stale process state for a live adapter.

## SWR-088 Supervisor closeout for exhaustive MCP hierarchy and app coverage

- Status: pending
- Priority: P1
- Track: refactor/supervisor
- Dedupe key: swissknife_refactor:phase_15_supervisor_closeout
- Depends on: SWR-081, SWR-082, SWR-083, SWR-084, SWR-085, SWR-086, SWR-087
- Outputs: swissknife/docs/refactor-final-signoff.md, swissknife/docs/supervisor-refactor-runbook.md, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor --once --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md --state-dir tmp/swissknife_refactor_supervisor/state --task-prefix '## SWR-' --state-prefix swissknife_refactor --no-implement --no-ephemeral-worktree --no-worktree-reconciliation --no-retry-budget-guardrail --no-dependency-guardrail --no-reconciliation-guardrail
- Acceptance: Phase 15 closeout records task accounting, live hierarchy counts, any remaining direct-only descriptor decisions, all-app binding coverage, UI/UX smoke evidence, Meta glasses simulator evidence, accelerate adapter process evidence, and the final `GO`/`NO_GO` release status.

## Phase 16 — browser-first module containment and duplicate-regression closure

Phase 16 exists because duplicate/root service files can be restored by merges or
supervisor reconciliation even after the module refactor appears complete. The
first task in this phase is intentionally a P0 duplicate-service cleanup gate; no
new browser/libp2p surface should be treated as release-ready while duplicate
service basenames, sprint-named service files, Python wrappers, or host-only
imports remain reachable from browser-facing entrypoints.

## SWR-089 Remove restored duplicate service files and sprint-named service regressions

- Status: completed
- Priority: P0
- Track: services/module-boundary
- Dedupe key: swissknife_refactor:restored_duplicate_service_files_and_sprint_name_regression
- Depends on: SWR-084
- Outputs: swissknife/src/services, swissknife/scripts/audit-source-modules.mjs, swissknife/docs/service-boundary-audit.json
- Validation: cd swissknife && find src/services -type f -printf '%f\t%p\n' | awk -F '\t' '{count[$1]++; paths[$1]=paths[$1] "\n" $2} END {for (name in count) if (count[name] > 1 && name !~ /^index\./) print name paths[name]}' | tee /tmp/swr-089-duplicate-services.txt && test ! -s /tmp/swr-089-duplicate-services.txt && ! find src/services -maxdepth 2 -type f | grep -E '(^|/)cec-sprint[0-9]|(^|/)sprint[0-9]' && npm run services:audit
- Acceptance: The restored root duplicates `src/services/nlp-predicate-extractor.ts`, `src/services/spacy-wasm-nlp.ts`, and `src/services/zkp-ucan-bridge.ts` are removed or replaced by canonical module-owned implementations; all `src/services/sprint*` and `src/services/cec-sprint*` files are renamed to durable module names; imports and tests point at canonical paths; `services:audit` fails on future duplicate service basenames and legacy sprint service filenames.
- Evidence: 2026-07-09 restored duplicate cleanup completed manually after pausing the stale SwissKnife `SWR-085` worker. Raw duplicate-basename scan returned no rows, sprint-file scan returned no rows, `npm run services:audit` passed with `serviceDuplicateBasenames: 0` and `legacySprintServiceFiles: 0`, and `npm run typecheck:services` passed.

## SWR-090 Make module ownership the single source of truth for service containment

- Status: completed
- Priority: P0
- Track: services/ownership
- Dedupe key: swissknife_refactor:module_ownership_single_source_service_containment
- Depends on: SWR-089
- Outputs: swissknife/src/module-ownership.json, swissknife/docs/source-module-boundaries.md, swissknife/test/architecture/source-module-boundaries.test.js
- Validation: cd swissknife && npm run audit:module-boundary && npm run services:audit
- Acceptance: Every service-facing source file is owned by exactly one module family, compatibility root files are explicitly inventoried or removed, and the architecture test/audit pair rejects new root service wrappers, unowned service files, forbidden service imports, and browser-unsafe ownership drift.

## SWR-091 Lock browser package exports and default browser entrypoints

- Status: completed
- Priority: P0
- Track: browser/packaging
- Dedupe key: swissknife_refactor:browser_exports_default_entrypoint_lock
- Depends on: SWR-089, SWR-090
- Outputs: swissknife/package.json, swissknife/test/browser-compat, swissknife/docs/browser-distribution-policy.md
- Validation: cd swissknife && npm run test:browser-compat && npm run build:web
- Acceptance: Browser package consumers resolve browser-safe exports for MCP, libp2p, IPFS, storage, workers, logic-language, deontic NLP, and ZKP APIs without pulling Node builtins, Python wrappers, subprocess adapters, native prover shims, or root duplicate service files.

## SWR-092 Keep libp2p enabled by default in browser-safe runtime paths

- Status: completed
- Priority: P0
- Track: browser/libp2p
- Dedupe key: swissknife_refactor:libp2p_browser_default_runtime_real_modules
- Depends on: SWR-091
- Outputs: swissknife/src/services/mcp/libp2p-browser-runtime.ts, swissknife/web/js/apps/mcp-control.js, swissknife/web/js/apps/p2p-network.js, swissknife/docs/browser-libp2p-evidence.md
- Validation: cd swissknife && npm run evidence:libp2p-browser && npm run audit:bundle-host-leakage
- Acceptance: Browser libp2p remains enabled by default using real browser-capable libp2p modules; missing optional packages are reported as typed capability gaps instead of silent fallbacks; MCP Control and P2P Network render live default-status/gap evidence; bundle audit records host leakage 0 and default Pyodide 0.

## SWR-093 Split host-only adapters from browser-safe service contracts

- Status: completed
- Priority: P0
- Track: browser/host-boundary
- Dedupe key: swissknife_refactor:host_only_adapter_contract_split
- Depends on: SWR-090, SWR-091
- Outputs: swissknife/src/services, swissknife/src/shared, swissknife/docs/browser-compatibility-inventory.md
- Validation: cd swissknife && npm run browser:compat:inventory && npm run audit:bundle-host-leakage && npm run typecheck:services
- Acceptance: Browser-facing code imports shared contracts or browser implementations only; host-only filesystem, subprocess, Python, native prover, Electron, and daemon adapters live behind explicit host modules and cannot be reached transitively from browser entrypoints.

## SWR-094 Verify real browser ZKP and WASM paths after containment cleanup

- Status: completed
- Priority: P0
- Track: browser/zkp
- Dedupe key: swissknife_refactor:real_browser_zkp_wasm_after_containment
- Depends on: SWR-089, SWR-093
- Outputs: swissknife/src/services/zkp, swissknife/src/services/zkp-browser-schnorr.ts, swissknife/docs/browser-wasm-zkp-policy.md, swissknife/test/mcp-plus-plus
- Validation: cd swissknife && npm run test:browser-compat && npm run test:fast -- test/mcp-plus-plus/wasm-prover-browser-purity.test.ts
- Acceptance: Browser ZKP proof generation and verification use real TypeScript/WASM-backed paths by default; simulated or test-only proof paths are opt-in, visibly named, and rejected by browser-purity tests unless a test fixture explicitly requests simulation.

## SWR-095 Add a browser/service duplicate regression sentinel to release readiness

- Status: completed
- Priority: P0
- Track: release/gates
- Dedupe key: swissknife_refactor:duplicate_service_browser_release_sentinel
- Depends on: SWR-089, SWR-091, SWR-092, SWR-093, SWR-094
- Outputs: swissknife/scripts/release-readiness-gate.mjs, swissknife/docs/release-readiness-report.md, swissknife/docs/refactor-final-signoff.md
- Validation: cd swissknife && npm run release:readiness
- Acceptance: Release readiness fails if duplicate service basenames, sprint-named services, root duplicate wrappers, browser-host leakage, default Pyodide exposure, stale browser/libp2p evidence, or browser-ZKP simulation drift are present; skipped gates must include an explicit reason and cannot hide browser-safety failures.

## SWR-096 Prove all tool-backed virtual desktop apps remain browser-compatible

- Status: pending
- Priority: P1
- Track: virtual-desktop/browser
- Dedupe key: swissknife_refactor:tool_backed_virtual_desktop_browser_compatibility
- Depends on: SWR-085, SWR-091, SWR-092, SWR-093
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb, swissknife/docs/virtual-desktop-tool-ui-smoke-evidence.md, swissknife/web/js
- Validation: cd swissknife && npm run test:e2e:mcp && npm run evidence:mcp-glasses && npm run audit:bundle-host-leakage
- Acceptance: Every tool-backed app renders a browser-safe success/fallback/error UI path and records a receipt or screenshot; no app smoke path requires Node builtins, Python wrappers, host subprocesses, physical glasses, or unavailable native adapters in the browser.

## SWR-097 Keep Meta glasses and ORB/IDL evidence simulator-driven

- Status: pending
- Priority: P1
- Track: glasses/browser
- Dedupe key: swissknife_refactor:meta_glasses_simulator_browser_safe_orb_idl
- Depends on: SWR-086, SWR-092, SWR-096
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/glasses-simulator-handoff.json, swissknife/docs/meta-glasses-simulator-evidence.md, swissknife/test/mcp-plus-plus
- Validation: cd swissknife && npm run test:e2e:meta-glasses && npm run evidence:mcp-glasses
- Acceptance: ORB/IDL handoff evidence uses simulator-visible display/audio/camera/microphone policy states; browser paths remain hardware-free, and physical-device-only features degrade through explicit simulator/desktop handoff receipts.

## SWR-098 Preserve ipfs_accelerate_py supervisor/adapter evidence without hiding browser constraints

- Status: completed
- Priority: P1
- Track: mcp/supervisor
- Dedupe key: swissknife_refactor:ipfs_accelerate_supervisor_adapter_browser_boundary_evidence
- Depends on: SWR-087, SWR-093, SWR-095
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ipfs-accelerate-compat.pid, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/ipfs-accelerate-adapter-coverage.json, swissknife/docs/ipfs-accelerate-compat-adapter-runbook.md
- Validation: cd swissknife && node scripts/capture-ipfs-accelerate-adapter-coverage.cjs && npm run evidence:mcp-glasses && npm run audit:bundle-host-leakage
- Acceptance: The supervisor-managed compatibility adapter is restartable and verified with PID/listener/tool coverage evidence, while browser bundles continue to expose only browser-safe descriptors and never execute the Python adapter directly.

## SWR-099 Phase 16 supervisor closeout and merge-readiness report

- Status: pending
- Priority: P1
- Track: refactor/supervisor
- Dedupe key: swissknife_refactor:phase_16_browser_module_supervisor_closeout
- Depends on: SWR-089, SWR-090, SWR-091, SWR-092, SWR-093, SWR-094, SWR-095, SWR-096, SWR-097, SWR-098
- Outputs: swissknife/docs/refactor-final-signoff.md, swissknife/docs/release-readiness-report.md, swissknife/docs/supervisor-refactor-runbook.md, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor --once --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md --state-dir tmp/swissknife_refactor_supervisor/state --task-prefix '## SWR-' --state-prefix swissknife_refactor --no-implement --no-ephemeral-worktree --no-worktree-reconciliation --no-retry-budget-guardrail --no-dependency-guardrail --no-reconciliation-guardrail
- Acceptance: Phase 16 closeout records duplicate-service cleanup evidence, module ownership gate evidence, browser exports evidence, browser-default libp2p evidence, host-boundary evidence, real ZKP/WASM evidence, all-app browser smoke evidence, Meta glasses simulator evidence, adapter/supervisor process evidence, release-readiness status, active supervisor PID/state/log paths, and residual merge risks.

## Phase 17: Exhaustive Virtual Desktop Backend Closure And Agent Supervisor Console

This phase turns the existing desktop-wide evidence work into an operational
contract. It covers every registered SwissKnife virtual-desktop app, the full
live tool catalogs of `ipfs_kit_py`, `ipfs_datasets_py`, and
`ipfs_accelerate_py`, both MCP and MCP++/libp2p discovery routes, and the
ORB/IDL handoff contract used by the Meta glasses simulator.

"All tools" is enforced as a catalog and policy guarantee, rather than by
blindly invoking every side-effectful tool. Every discovered descriptor must
have a typed owner, schema, availability state, policy class, and safe
verification route. Read-only tools require live receipt evidence; mutating,
credential, and host-only tools require schema/discovery evidence plus a
controlled confirmation, dry-run, or fixture route. No tool may be silently
lost behind a representative app sample.

The new `agent-supervisor` virtual-desktop application is a browser-safe
operations console. It exposes the `ipfs_accelerate_py` supervisor's goals,
subgoals, queue, taskboard links, receipts, and bounded prompt steering through
typed remote capabilities. It must never import Python, read local supervisor
state files, or spawn processes from browser code. Its backend integration also
uses `ipfs_kit_py` for immutable evidence/receipt storage and
`ipfs_datasets_py` for searchable task, goal, and run-history indexes.

## SWR-100 Freeze the exhaustive app-to-backend capability contract

- Status: pending
- Priority: P0
- Track: virtual-desktop/contracts
- Dedupe key: swissknife_refactor:exhaustive_app_backend_capability_contract
- Depends on: SWR-085, SWR-096
- Outputs: swissknife/src/services/apps/virtual-desktop-app-manifest.ts, swissknife/contracts/swissknife_virtual_desktop_app_manifest.schema.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-backend-contract.json, swissknife/docs/virtual-desktop-all-tools-app-coverage.md
- Validation: cd swissknife && node scripts/capture-ipfs-mcp-all-tools-ledger.cjs && node scripts/build-all-tools-capability-matrix.cjs && npm run test:e2e:mcp
- Acceptance: Every registered desktop app, generated app, legacy alias, and the new `agent-supervisor` app has one canonical ID, launch owner, backend capability set, ORB/IDL state, glasses strategy, and success/fallback/error UX scenario. Each backend capability identifies `ipfs_kit_py`, `ipfs_datasets_py`, or `ipfs_accelerate_py`, its MCP and MCP++ transport eligibility, policy class, and receipt strategy. Apps that intentionally use no remote tool have an explicit local-only rationale; no app or descriptor is omitted because it is not one of the generic generated app families.

## SWR-101 Prove complete MCP and MCP++/libp2p catalog reachability

- Status: pending
- Priority: P0
- Track: mcp/catalog
- Dedupe key: swissknife_refactor:complete_mcp_mcp_plus_plus_libp2p_catalog_reachability
- Depends on: SWR-100
- Outputs: swissknife/scripts/capture-mcp-live-probe-evidence.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-server-tool-catalog.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/mcp-plus-plus-libp2p-catalog.json, swissknife/docs/mcp-all-tool-catalog-evidence.md
- Validation: cd swissknife && node scripts/capture-mcp-live-probe-evidence.cjs && node scripts/capture-hierarchical-mcp-tools-evidence.cjs && npm run evidence:libp2p-browser
- Acceptance: SwissKnife records live discovery for every configured `ipfs_kit_py`, `ipfs_datasets_py`, and `ipfs_accelerate_py` descriptor through MCP and, where advertised, MCP++/libp2p. Each descriptor is reconciled by normalized name and schema to an app or global operations surface, or marked direct-only/host-only with a reason. Read-only tools have live dispatch receipts; mutating, credential, and destructive tools have policy-gated dry-run, fixture, or confirmation-route evidence. The evidence fails on a missing server, missing hierarchical facade, unexplained catalog delta, or unreachable advertised libp2p endpoint.

## SWR-102 Generate exhaustive per-app UI/UX workflow scenarios

- Status: pending
- Priority: P0
- Track: virtual-desktop/e2e
- Dedupe key: swissknife_refactor:per_app_backend_ui_ux_workflow_matrix
- Depends on: SWR-100, SWR-101
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-workflow-matrix.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/app-screenshots, swissknife/docs/virtual-desktop-tool-ui-smoke-evidence.md
- Validation: cd swissknife && npm run test:e2e:mcp && npm run evidence:mcp-glasses
- Acceptance: Every canonical desktop app has an executable UI workflow with launch, intended backend action or local-only rationale, visible loading/success/fallback/error states, keyboard and pointer accessibility checks, receipt or controlled-fixture evidence, and a screenshot. Tool-backed workflows cover all three server families across their owning apps and route complete tool catalogs through MCP Control, Terminal, or the Supervisor Console without hiding unavailable capability states.

## SWR-103 Make the virtual desktop app matrix a release-blocking gate

- Status: pending
- Priority: P0
- Track: release/virtual-desktop
- Dedupe key: swissknife_refactor:complete_app_matrix_release_gate
- Depends on: SWR-102
- Outputs: swissknife/scripts/build-virtual-desktop-release-evidence.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/release-evidence.json, swissknife/docs/release-evidence-freshness.md
- Validation: cd swissknife && node scripts/build-virtual-desktop-release-evidence.cjs && npm run release:readiness
- Acceptance: Release readiness fails if an app lacks a canonical backend contract, UI/UX workflow, screenshot, success/fallback/error state, ORB/IDL projection, or required server/tool catalog reconciliation. The gate reports exact missing app IDs, capability IDs, servers, tool classes, and simulator modalities; aggregate counts alone cannot pass it.

## SWR-104 Define browser-safe agent-supervisor gateway capabilities

- Status: pending
- Priority: P0
- Track: supervisor/contracts
- Dedupe key: swissknife_refactor:agent_supervisor_browser_safe_gateway_contract
- Depends on: SWR-093, SWR-100, SWR-101
- Outputs: swissknife/src/services/mcp, swissknife/src/shared, swissknife/contracts/agent-supervisor-console.schema.json, swissknife/docs/agent-supervisor-console-security-model.md
- Validation: cd swissknife && npm run typecheck:services && npm run test:browser-compat && npm run audit:bundle-host-leakage
- Acceptance: A typed, browser-safe gateway defines read capabilities for supervisor health, queue, goals, subgoals, taskboard links, logs, and receipts; governed write capabilities for prompt steering and task-control requests; and typed unavailable/denied states. `ipfs_accelerate_py` owns supervisor state and governed actions, `ipfs_kit_py` owns immutable evidence/receipt persistence, and `ipfs_datasets_py` owns searchable task/goal/run-history indexes. Browser bundles contain no Python imports, filesystem reads, subprocess calls, or direct implementation-supervisor invocation.

## SWR-105 Build the Agent Supervisor virtual-desktop application

- Status: pending
- Priority: P0
- Track: virtual-desktop/supervisor-console
- Dedupe key: swissknife_refactor:agent_supervisor_virtual_desktop_application
- Depends on: SWR-104
- Outputs: swissknife/web/js/apps/agent-supervisor.js, swissknife/web/js/descriptors/apps/agent-supervisor.descriptor.js, swissknife/src/services/apps/virtual-desktop-app-manifest.ts, swissknife/test/e2e
- Validation: cd swissknife && npm run build:web && npm run test:e2e:mcp && npm run test:browser-compat
- Acceptance: The virtual desktop exposes an `agent-supervisor` application with a goals/subgoals tree, taskboard-linked queue, active-task and receipt views, server and MCP++/libp2p health, and compact cross-links to the app/backend contract. It has stable desktop and narrow viewport layouts, keyboard navigation, loading/empty/error states, no nested card clutter, and no browser access to host-only supervisor internals.

## SWR-106 Add governed prompt steering for goals, subgoals, and tasks

- Status: pending
- Priority: P0
- Track: supervisor/policy
- Dedupe key: swissknife_refactor:governed_prompt_steering_goal_subgoal_taskboard
- Depends on: SWR-104, SWR-105
- Outputs: swissknife/src/services/mcp, swissknife/web/js/apps/agent-supervisor.js, swissknife/test/mcp-plus-plus, swissknife/docs/agent-supervisor-console-security-model.md
- Validation: cd swissknife && npm run test:fast -- test/mcp-plus-plus && npm run test:e2e:mcp
- Acceptance: A user can select a goal, subgoal, or taskboard task; draft a steering prompt; review normalized target, policy class, affected tasks, and planned MCP action; explicitly confirm submission; and receive a correlation ID and immutable receipt. Prompt content is size-bounded, redacted in logs where required, never treated as shell input, and cannot bypass task dependencies, branch protections, confirmation policy, or the supervisor's execution budget.

## SWR-107 Verify the Supervisor Console against all three IPFS server families

- Status: pending
- Priority: P0
- Track: supervisor/integration
- Dedupe key: swissknife_refactor:agent_supervisor_console_three_server_integration
- Depends on: SWR-101, SWR-105, SWR-106
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/agent-supervisor-console-e2e.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/agent-supervisor-console-receipts.json, swissknife/docs/agent-supervisor-console-evidence.md
- Validation: cd swissknife && node scripts/capture-mcp-live-probe-evidence.cjs && npm run test:e2e:mcp && npm run evidence:mcp-glasses
- Acceptance: End-to-end tests prove the console reads live supervisor/taskboard state through `ipfs_accelerate_py`, stores or resolves an evidence receipt through `ipfs_kit_py`, and searches the corresponding indexed goal/task/run record through `ipfs_datasets_py`. Success, server-unavailable, denied, stale-state, and transport-fallback paths are visible and produce correlated evidence without requiring a destructive supervisor action.

## SWR-108 Extend ORB/IDL contracts for the complete desktop and Supervisor Console

- Status: pending
- Priority: P0
- Track: orb/idl
- Dedupe key: swissknife_refactor:complete_desktop_orb_idl_and_supervisor_console
- Depends on: SWR-100, SWR-107
- Outputs: swissknife/src/services/glasses, swissknife/contracts, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/orb-idl-complete-coverage.json, swissknife/docs/orb-idl-virtual-desktop-contract.md
- Validation: cd swissknife && npm run evidence:mcp-glasses && npm run typecheck:services
- Acceptance: Every canonical app, including `agent-supervisor`, has a validated ORB/IDL descriptor with explicit display, camera, speaker, microphone, input, action-policy, and fallback semantics. The console's glasses projection is read-only for status and receipts by default; any steering request requires the same confirmed policy path as desktop. Missing or unsupported modalities produce typed fallback descriptors rather than omitted fields or fabricated hardware availability.

## SWR-109 Run Meta glasses simulator modality and handoff workflows

- Status: pending
- Priority: P0
- Track: glasses/simulator
- Dedupe key: swissknife_refactor:meta_glasses_simulator_full_modality_handoff
- Depends on: SWR-103, SWR-108
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/meta-glasses-simulator-modalities.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/glasses-screenshots, swissknife/docs/meta-glasses-simulator-evidence.md
- Validation: cd swissknife && npm run test:e2e:meta-glasses && npm run evidence:mcp-glasses
- Acceptance: The configured Meta glasses simulator is launched and exercised for each handoff profile. Evidence covers display rendering, camera permission/grant/denial and fallback, speaker/audio policy and state, microphone permission/transcript/denial behavior, touch/voice input mapping, and desktop-to-simulator handoff receipts. The test harness records simulator/device profile identity and fails if it substitutes a physical-desktop pairing assumption for simulator evidence.

## SWR-110 Gate complete desktop, all-tools, and simulator evidence in release readiness

- Status: pending
- Priority: P0
- Track: release/evidence
- Dedupe key: swissknife_refactor:complete_desktop_all_tools_supervisor_simulator_release_gate
- Depends on: SWR-103, SWR-107, SWR-109
- Outputs: swissknife/scripts/release-readiness-gate.mjs, swissknife/docs/release-readiness-report.json, swissknife/docs/release-readiness-report.md, swissknife/docs/release-evidence-freshness.json
- Validation: cd swissknife && npm run release:readiness
- Acceptance: The final release gate requires fresh, internally consistent evidence for every app, all three MCP servers, MCP++/libp2p discovery where advertised, per-tool policy classification, app UI/UX workflows, Agent Supervisor Console integration, ORB/IDL coverage, and the Meta glasses simulator's display/camera/speaker/microphone workflows. It reports `NO_GO` with concrete missing evidence paths and must not downgrade missing coverage to warnings.

## SWR-111 Phase 17 supervisor closeout and operational handoff

- Status: pending
- Priority: P1
- Track: refactor/supervisor
- Dedupe key: swissknife_refactor:phase_17_complete_desktop_supervisor_console_closeout
- Depends on: SWR-100, SWR-101, SWR-102, SWR-103, SWR-104, SWR-105, SWR-106, SWR-107, SWR-108, SWR-109, SWR-110
- Outputs: swissknife/docs/refactor-final-signoff.md, swissknife/docs/supervisor-refactor-runbook.md, swissknife/docs/agent-supervisor-console-evidence.md, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor --once --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md --state-dir tmp/swissknife_refactor_supervisor/state --task-prefix '## SWR-' --state-prefix swissknife_refactor --no-implement --no-ephemeral-worktree --no-worktree-reconciliation --no-retry-budget-guardrail --no-dependency-guardrail --no-reconciliation-guardrail
- Acceptance: Closeout records every task's evidence, explicit policy decisions for non-invoked side-effectful tools, all-app workflow status, three-server and libp2p availability, Supervisor Console receipt chain, ORB/IDL coverage, Meta glasses simulator modality evidence, active supervisor PID/state/log paths, final release decision, and any residual external simulator or server prerequisites.
