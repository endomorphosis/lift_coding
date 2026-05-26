# Virtual AI OS Submodule Integration Plan

## Status

Comprehensive integration plan for turning the current HandsFree monorepo plus its component repositories into a virtualized AI operating system with Meta glasses as a remote audio and display endpoint.

Created: 2026-05-22
Refreshed: 2026-05-23

## Goal

Unify the submodule stack into one operational system with clear control planes:

- `ipfs_datasets_py` as the semantic routing, dataset, backlog orchestration, and MCP grounding plane.
- `ipfs_accelerate_py` as the execution-placement and acceleration plane.
- `ipfs_kit_py` as the IPFS content, packaging, and provenance plane.
- `swissknife` as the local UI, ORB, MCP++, and operator-facing virtual desktop plane.
- `hallucinate_app` as the GUI shell, daemon manager, and developer workstation plane.
- HandsFree backend/mobile as the policy, workflow, and device transport plane.
- Meta glasses audio plus Meta display widgets as the remote terminal surface for that virtualized system.

The target state is not a loose collection of tools. It is one system that can:

1. plan work,
2. route tasks to the right runtime,
3. persist artifacts and provenance,
4. expose human-usable UI and operator controls,
5. stream progress to mobile and glasses,
6. validate behavior through repeatable integration tests.

## Reviewed Source Topology

### Root-tracked submodules after alignment

- `external/ipfs_datasets`
  - target upstream: `https://github.com/endomorphosis/ipfs_datasets_py`
  - recorded root gitlink at repo `HEAD`: `c68759c211f4a46ea22d34aa05e2679ddc5b2e34`
  - live local checkout on 2026-05-23: `3ea8d7aa6e24bc39df56e1a9de16567db45ebcfd`
  - current branch: `main`
  - state: clean submodule worktree, but local checkout is ahead of the recorded superproject gitlink and should be advanced only as an explicit pin refresh.
- `external/ipfs_accelerate`
  - target upstream: `https://github.com/endomorphosis/ipfs_accelerate_py`
  - recorded root gitlink at repo `HEAD`: `ff61c14b4df44529ff6f73efa5e26fadeda649d5`
  - live local checkout on 2026-05-23: `ff61c14b4df44529ff6f73efa5e26fadeda649d5`
  - current branch: `main`
  - state: clean and aligned with the recorded gitlink.
- `external/ipfs_kit`
  - target upstream: `https://github.com/endomorphosis/ipfs_kit_py`
  - recorded root gitlink at repo `HEAD`: `3133d4fdc85a885ba7d776465bdee48f7a867e01`
  - live local checkout on 2026-05-23: `3133d4fdc85a885ba7d776465bdee48f7a867e01`
  - current branch: `main`
  - state: VAI-021 repaired the missing nested `ipfs_accelerate_py` metadata in `external/ipfs_kit/.gitmodules`, so `git -C external/ipfs_kit submodule status` and root `git submodule status --recursive` can inspect the topology without failing on an orphan gitlink.
- `swissknife`
  - upstream: `https://github.com/endomorphosis/swissknife`
  - recorded root gitlink at repo `HEAD`: `5b4598e15709203c0fe2265fdab2f51ea822b0f2`
  - live local checkout on 2026-05-23: `5b4598e15709203c0fe2265fdab2f51ea822b0f2`
  - current branch: `main`
  - state: dirty local worktree; do not auto-advance or overwrite during submodule refresh work.
- `hallucinate_app`
  - upstream: `https://github.com/endomorphosis/hallucinate_app.git`
  - recorded root gitlink at repo `HEAD`: `0fc4e0ccb8d6cb5c74a6bbf769d610dd600ff7c5`
  - live local checkout on 2026-05-23 after explicit submodule init: `0fc4e0ccb8d6cb5c74a6bbf769d610dd600ff7c5`
  - current branch: `main`
  - state: initialized and clean.
- compatibility reference submodules that remain part of the full-stack validation path:
  - `external/meta-wearables-dat-android` recorded and checked out at `25f3a6d4479b7a4a72f877977b865a11af990d04`
  - `external/meta-wearables-dat-ios` recorded and checked out at `a739e94181221e7f321304273bcda2272821b163`

### 2026-05-23 submodule refresh findings

- Root `.gitmodules` wiring is still canonical for `ipfs_datasets_py`, `ipfs_accelerate_py`, `ipfs_kit_py`, `swissknife`, and `hallucinate_app`; local IPFS submodule remotes were synced to those `_py` URLs before fetching.
- `hallucinate_app` required explicit submodule initialization in local Git config before it appeared as a live worktree in `git submodule status`.
- `external/ipfs_datasets` is the only reviewed component whose local checkout currently differs from the recorded superproject gitlink; advancing that pin should be treated as a deliberate superproject change, not an incidental refresh side effect.
- `swissknife` has local modifications in its worktree; protect it from any automated pin or checkout step during backlog automation.
- Recursive submodule status traversal is restored for the reviewed topology: the root `Mcp-Plus-Plus` gitlink now has a matching `.gitmodules` entry, and `external/ipfs_kit` now declares its nested `ipfs_accelerate_py` gitlink.
- Until `external/ipfs_kit` advances the nested `ipfs_accelerate_py` gitlink to a reachable upstream pin, local bootstrap should avoid recursive update traversal through `external/ipfs_kit`. Use `git submodule update --init external/ipfs_kit` followed by `git -C external/ipfs_kit submodule status` for status-only hygiene; initialize specific nested dependencies only after their pins are verified.
- Evidence: [data/virtual_ai_os/discovery/submodule-refresh-2026-05-23.md](../../data/virtual_ai_os/discovery/submodule-refresh-2026-05-23.md)

### Upstream blocker

- Requested upstream `https://github.com/endomorphosis/mcp_plus_plus` did not resolve via `git ls-remote` on 2026-05-22.
- Current repo evidence still treats lowercase `mcp_plus_plus` as unresolved. VAI-021 maps the existing CamelCase `Mcp-Plus-Plus` gitlink only so Git can traverse the committed topology without failing on missing metadata.
- Treat canonical lowercase `mcp_plus_plus` source resolution as a blocking ops task before adding or renaming any canonical standalone MCP++ root submodule.

### Canonical-source resolution

- Resolution date: 2026-05-22.
- Decision: keep lowercase `mcp_plus_plus` out of the root `.gitmodules` file until a valid canonical upstream exists; keep the existing CamelCase `Mcp-Plus-Plus` mapping for gitlink hygiene.
- Evidence: [data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-22.md](../../data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-22.md) records the `Repository not found` result and the rationale for continuing to treat MCP++ as a distributed protocol surface.
- Re-open this decision only when a reviewed upstream repository exists and can be pinned without duplicating the already-integrated MCP, ORB, and routing surfaces in `swissknife`, `ipfs_accelerate_py`, and `ipfs_datasets_py`.

## Current Integration Baseline

### What already exists

- HandsFree already has direct `ipfs_datasets_py` adapter seams in `src/handsfree/ipfs_datasets_routers.py`.
- HandsFree already has a delegated task/provider model under `src/handsfree/agents/`, `src/handsfree/agent_providers.py`, and `src/handsfree/mcp/`.
- Swissknife already provides MCP-IDL, ORB routing, and widget-authoring surfaces.
- Swissknife now has a hardware-free Meta glasses descriptor-to-mobile-render harness that exercises ORB discovery, binding, invocation, bridge receipts, and operator-safe fallback behavior in `test/mcp-plus-plus/meta-glasses-display-harness.test.ts`.
- Hallucinate App now positions itself as the operator console and daemon manager shell that hosts SwissKnife virtual desktop workflows for the virtual AI OS.
- The repo already contains one machine-readable daemon backlog pattern for the Meta glasses widget stream.
- Mobile plus backend already contain Meta DAT display and action-routing primitives.
- A dedicated simulation plan now exists in `implementation_plan/docs/20-meta-rayban-display-interface-simulator.md` for browser-first Meta Ray-Ban interface validation before iPhone handoff.

### Residual follow-up after the initial backlog

- Physical-device rollout evidence still has to be collected from real DAT-capable hardware runs; the repo now contains the checklist and fallback contracts, but not the run artifacts themselves.
- Hallucinate desktop E2E coverage remains the operator-console complement to the backend/mobile hardware-free harnesses and should continue to gather evidence under real packaging/runtime conditions.
- Canonical standalone `mcp_plus_plus` source discovery should only be revisited if a valid upstream repository appears with scope that is distinct from the already-reviewed distributed protocol surfaces.
- The Meta/Ray-Ban simulator track now needs to move from planning into implementation: browser 600x600 rendering, D-pad/focus traces, Web App readiness export, and fixture parity with the mobile DAT bridge.
- Public Meta evidence reviewed on 2026-05-23 shows developer-preview Web App and DAT testing paths plus Mock Device support, but no verified official native display desktop simulator. Treat our local browser simulator plus DAT mock-device flows as the supported pre-hardware path.

## Discovery closeout (2026-05-22)

The final backlog discovery pass reviewed the control-plane, UI-plane, device-plane, and daemon-integration surfaces added during `VAI-003` through `VAI-013`.

Evidence reviewed:

- control plane: capability registry, runtime router, daemon-backed task orchestration, and observability contract surfaces in `src/handsfree/`
- UI plane: Swissknife ORB/display harness and Hallucinate App operator-console documentation
- device plane: backend/mobile Meta-glasses display-widget contracts and hardware-free mobile harnesses
- ops plane: daemon wrappers, backlog parser tests, bootstrap documentation, and canonical-source discovery artifacts

Discovery result:

- no new implementation unknowns were found that warrant additional `VAI-` backlog items for this review cycle
- the remaining work is evidence collection and future upstream-change handling, not a newly discovered code-path gap
- the discovery artifact for this closeout is [data/virtual_ai_os/discovery/no-new-unknowns-2026-05-22.md](../../data/virtual_ai_os/discovery/no-new-unknowns-2026-05-22.md)

## Virtual AI OS Architecture

```text
User / operator / agent
        |
        v
Intent + workflow planner
        |
        v
HandsFree capability registry
        |
        +-------------------------------+
        |                               |
        v                               v
ipfs_datasets_py                 Swissknife / Hallucinate App
semantic routing                 UI + ORB + desktop control plane
todo supervisor                  daemon management
MCP grounding                    remote operator surfaces
        |                               |
        +---------------+---------------+
                        |
                        v
            execution placement layer
             ipfs_accelerate_py
                        |
                        v
             content + provenance layer
                 ipfs_kit_py / IPFS
                        |
                        v
            HandsFree backend + mobile bridge
                        |
                        v
       Meta glasses audio + display widget endpoint
```

## Design Decisions

### 1. Treat submodules as product surfaces, not vendored libraries

Each tracked repo must have one explicit responsibility in the virtual AI OS. Avoid duplicate orchestration logic in multiple codebases.

### 2. Keep capability routing above implementation choice

Capability ids should be stable even when the runtime changes between:

- direct Python import,
- local CLI,
- local daemon,
- MCP/MCP++ remote execution,
- Swissknife ORB invocation,
- Hallucinate App desktop command.

### 3. Meta glasses are a remote terminal, not only a notification device

The glasses surface should support:

- audio-first command and confirmation,
- glanceable display widgets,
- progress/status streaming,
- safe action approval,
- fallback to mobile or webapp rendering when native display is unavailable.

### 4. Autonomous work must stay supervised

Use the repo-local `ipfs_datasets_py` implementation supervisor to advance daemon-backed backlog items, while preserving:

- typed validation commands,
- explicit acceptance criteria,
- dependency ordering,
- rollback-safe submodule pinning,
- discovery-expansion tasks for unknowns.

## Integration Workstreams

### Workstream A: Source and pin hygiene

- Align root `.gitmodules` URLs with canonical upstream repositories.
- Promote `hallucinate_app` to a root-tracked submodule so the monorepo records the reviewed GUI shell revision.
- Record exact pins in this plan and in daemon tasks.
- Resolve the canonical `mcp_plus_plus` upstream before wiring it as a submodule.
- Advance the `external/ipfs_datasets` gitlink only through an explicit reviewed pin refresh, and leave `swissknife` untouched while it has a dirty worktree.

### Workstream B: Shared capability registry

Define one registry that maps capability ids to:

- owner component,
- execution mode,
- fallback mode,
- confirmation policy,
- artifact output shape,
- voice/display summary formatter,
- test harness coverage.

Initial families:

- planning and queue management
- LLM generation and revision
- embeddings and retrieval
- dataset search and selection
- IPFS package/pin/resolve/provenance
- accelerated inference and batching
- UI/render session control
- device/render transport

### Workstream C: Virtual runtime control plane

Add a runtime orchestration seam in HandsFree that can choose among:

- `ipfs_datasets_py` direct routers,
- `ipfs_accelerate_py` execution placement,
- `ipfs_kit_py` storage/package operations,
- Swissknife ORB tools,
- Hallucinate App daemon-manager actions,
- future standalone `mcp_plus_plus` services once source is resolved.

This runtime is the operating-system scheduler equivalent for the stack.

### Workstream D: Meta Ray-Ban simulation and iPhone handoff

- Use `implementation_plan/docs/20-meta-rayban-display-interface-simulator.md` as the canonical implementation plan for the pre-hardware simulation track.
- Treat Meta Web Apps browser preview plus DAT Mock Device tooling as the official pre-hardware inputs that we can actually verify today.
- Build one canonical 600x600 manifest-driven simulator that feeds browser preview, Web App packaging, mobile fixture tests, and DAT-native adapter validation.
- Keep the simulator bridge-compatible with the current HandsFree mobile ORB/display-widget contracts so simulator traces can become integration-test fixtures instead of throwaway mocks.

### Workstream E: UI and operator plane

- Swissknife becomes the composable interface and ORB surface.
- Verified in the current review cycle with the hardware-free descriptor-to-mobile-render harness and the Meta glasses ORB adapter/service surfaces in the `swissknife` worktree.
- Hallucinate App becomes the operator console, daemon/session monitor, and SwissKnife virtual desktop shell.
- HandsFree mobile stays the companion control surface.
- Meta glasses become the remote audio/display terminal.

### Workstream F: Device interface plane

Merge the audio and display stories into one remote-interface contract:

- audio input/output routing,
- display widget rendering,
- action receipts,
- fallback rendering,
- live task progress,
- policy-safe confirmations.

### Workstream G: Full-stack test and rollout discipline

Build a layered test matrix:

- unit: individual adapter contracts
- contract: capability registry and schema validation
- integration: component-to-component routing
- harness: hardware-free end-to-end flows
- device: Android/iOS physical validation
- ops: daemon, supervisor, and worktree automation

## Test Matrix

### Priority integration scenarios

1. Planner selects a task, daemon marks it ready, runtime routes execution through `ipfs_datasets_py` plus `ipfs_accelerate_py`, stores artifacts with `ipfs_kit_py`, then emits mobile/glasses progress updates.
2. Swissknife authors a UI descriptor, HandsFree validates it, Hallucinate App exposes it in the desktop shell, and mobile/glasses render a safe fallback view.
3. A long-running agent task streams status to Hallucinate App, mobile, and Meta glasses from one shared task state source.
4. A failure path produces one normalized error contract across backend, Swissknife, Hallucinate App, and glasses surfaces.
5. A no-native-display environment falls back to web/mobile rendering without changing the workflow semantics.

### Required validation layers

- daemon board parseability tests
- wrapper dry-run tests for `llm_router`
- capability registry contract tests
- backend API and OpenAPI tests
- mobile bridge tests
- Swissknife Jest/TypeScript tests
- Hallucinate App e2e smoke tests
- Android/iOS build or sample-flow checks

## Risks and Constraints

- Lowercase `mcp_plus_plus` upstream is unresolved; do not encode that broken URL. The existing CamelCase `Mcp-Plus-Plus` gitlink is mapped to `https://github.com/endomorphosis/Mcp-Plus-Plus.git` for submodule hygiene.
- `external/ipfs_datasets` currently contains local modifications; advancing the root gitlink must not overwrite that nested worktree.
- `swissknife` also contains local modifications; leave its working tree untouched during the submodule alignment work.
- Meta display APIs remain developer preview surfaces and cannot be required for default CI-safe builds.
- Nested submodules inside upstream repos remain inconsistent; use status-only recursive checks for hygiene and avoid recursive `update --init` through `external/ipfs_kit` until its nested `ipfs_accelerate_py` pin is verified upstream.

## Delivery Strategy

### Phase 0: pin and topology alignment

- update `.gitmodules`
- advance the root gitlink for `external/ipfs_datasets`
- add `hallucinate_app` as a tracked root submodule
- capture exact reviewed revisions
- create daemon-backed backlog and wrappers

### Phase 1: control-plane contracts

- add the shared capability registry
- add execution-placement interfaces
- define the normalized task/artifact/event model

### Phase 2: UI and device convergence

- bind Swissknife and Hallucinate App into the same runtime model
- completed Swissknife ORB/UI binding validation through the Meta glasses display harness and reviewed adapter surfaces
- connect mobile and glasses rendering to task and artifact state

### Phase 3: autonomous supervised execution

- run the repo-local backlog daemon and implementation supervisor to advance queued work in isolated worktrees
- require evidence-backed validation and retry-budget handling

### Phase 4: physical rollout and observability

- validate Android/iOS/device behavior
- document operational readiness, rollback, and metrics

## Daemon-backed Backlog

The machine-readable task board for this plan is:

```text
implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md
```

Run from the repo root:

```bash
python3 scripts/virtual_ai_os_todo_daemon.py --once
python3 scripts/virtual_ai_os_todo_supervisor.py --once
python3 scripts/virtual_ai_os_llm_router.py --task-id VAI-003
```

Use `--implement` with the supervisor when you want the `ipfs_datasets_py` implementation supervisor to start working tasks in ephemeral worktrees.

## Success Criteria

The plan is successful when:

1. the root repo tracks the correct component sources and reviewed pins,
2. one daemon-parseable backlog governs the integration sequence,
3. one capability-routing contract spans all component repos,
4. Meta glasses function as a remote audio/display endpoint for the system,
5. end-to-end integration tests can exercise the virtual AI OS without requiring physical hardware for every run.
