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

Current known blockers from the latest local inspection:

- `npm run services:audit` currently fails because five root-level service shim
  files remain under `src/services`:
  - `src/services/mcp-idl.ts`
  - `src/services/mcp-ui-profile.ts`
  - `src/services/meta-glasses-display-profile.ts`
  - `src/services/meta-glasses-widget-compiler.ts`
  - `src/services/swissknife-mcp-capability-registry.ts`
- `npm run typecheck` currently exits non-zero only on the existing `TS6305`
  declaration-output mismatch class; no non-`TS6305` diagnostics were present in
  the filtered check.
- Browser-facing service entrypoint scans did not show obvious `node:*`,
  `child_process`, `Buffer.from`, or remote/Python bridge imports.

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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
- Completion: manual
- Priority: P1
- Track: refactor/ci
- Fingerprint: 51e4424fe130482a0405dcf1498736953070f248
- Dedupe key: swissknife_refactor:ci_release_gates
- Depends on: SWR-001, SWR-003, SWR-004, SWR-008
- Outputs: swissknife/package.json, swissknife/.github, swissknife/scripts, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md
- Validation: cd swissknife && npm run services:audit && npm run typecheck && npm run test:fast && npm run test:browser-compat && npm run build:web
- Acceptance: Release candidates cannot pass with service-boundary drift, browser-host leakage, typecheck failure, missing browser compatibility tests, or stale MCP/glasses evidence.

## SWR-010 Keep refactor documentation and evidence current

- Status: todo
- Completion: manual
- Priority: P3
- Track: refactor/docs
- Fingerprint: c885909123a26a724aa6b427d52a6dce8635bc1b
- Dedupe key: swissknife_refactor:documentation_evidence
- Depends on: SWR-001
- Outputs: implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md, swissknife/src/services/MODULE_BOUNDARIES.md, swissknife/docs
- Validation: test -f implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md && cd swissknife && npm run services:audit
- Acceptance: The refactoring plan, service boundary docs, task board statuses, validation commands, and evidence links remain synchronized with the current repository state after each milestone.

## SWR-011 Build repository-wide browser compatibility inventory

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
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

- Status: todo
- Completion: manual
- Priority: P2
- Track: refactor/supervisor
- Fingerprint: 44ac479612a864bf2bc60c9e95c44caee9183f07
- Dedupe key: swissknife_refactor:supervisor_state_hardening
- Depends on: SWR-010
- Outputs: tmp/swissknife_refactor_supervisor/state, implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md, swissknife/docs/supervisor-refactor-runbook.md
- Validation: python -m ipfs_accelerate_py.agent_supervisor.todo_daemon.implementation_supervisor --once --todo-path implementation_plan/docs/38-swissknife-repository-refactoring-plan-2026-07-08.todo.md --state-dir tmp/swissknife_refactor_supervisor/state --task-prefix '## SWR-' --state-prefix swissknife_refactor --no-implement --no-ephemeral-worktree --no-worktree-reconciliation --no-retry-budget-guardrail --no-dependency-guardrail --no-reconciliation-guardrail
- Acceptance: SwissKnife refactor tasks can be parsed and supervised in bounded `--once --no-implement` mode without autonomous code edits; state paths, invocation flags, known daemon `git gc` behavior, and safe escalation rules are documented.
