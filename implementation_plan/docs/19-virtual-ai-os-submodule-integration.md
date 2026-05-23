# Virtual AI OS Submodule Integration Plan

## Status

Comprehensive integration plan for turning the current HandsFree monorepo plus its component repositories into a virtualized AI operating system with Meta glasses as a remote audio and display endpoint.

Created: 2026-05-22

## Goal

Unify the submodule stack into one operational system with clear control planes:

- `ipfs_datasets_py` as the semantic routing, dataset, todo-daemon, and MCP grounding plane.
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
  - staged root gitlink: `a1b42fd96269cb6ec7bf0475ee0a6b0f49242bae`
  - cached `origin/main`: `a1b42fd96269cb6ec7bf0475ee0a6b0f49242bae`
  - local checkout is clean at the same reviewed commit, so the root gitlink can align directly with the current upstream-tracking checkout.
- `external/ipfs_accelerate`
  - target upstream: `https://github.com/endomorphosis/ipfs_accelerate_py`
  - target HEAD: `ff61c14b4df44529ff6f73efa5e26fadeda649d5`
- `external/ipfs_kit`
  - target upstream: `https://github.com/endomorphosis/ipfs_kit_py`
  - target HEAD: `3133d4fdc85a885ba7d776465bdee48f7a867e01`
- `swissknife`
  - upstream: `https://github.com/endomorphosis/swissknife`
  - reviewed HEAD: `5b4598e15709203c0fe2265fdab2f51ea822b0f2`
- `hallucinate_app`
  - upstream: `https://github.com/endomorphosis/hallucinate_app.git`
  - reviewed HEAD: `e5fb3381aead5a3f174095063c71131d30797520`
- compatibility reference submodules that remain part of the full-stack validation path:
  - `external/meta-wearables-dat-android` at `25f3a6d4479b7a4a72f877977b865a11af990d04`
  - `external/meta-wearables-dat-ios` at `a739e94181221e7f321304273bcda2272821b163`

### Upstream blocker

- Requested upstream `https://github.com/endomorphosis/mcp_plus_plus` did not resolve via `git ls-remote` on 2026-05-22.
- Current repo evidence suggests MCP++ is presently represented as a protocol and implementation surface distributed across `swissknife`, `ipfs_accelerate_py`, and `ipfs_datasets_py`, not yet as a root-tracked standalone submodule in this monorepo.
- Treat canonical `mcp_plus_plus` source resolution as a blocking ops task before adding a root submodule entry for it.

### Canonical-source resolution

- Resolution date: 2026-05-22.
- Decision: keep `mcp_plus_plus` out of the root `.gitmodules` file until a valid canonical upstream exists.
- Evidence: [data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-22.md](../data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-22.md) records the `Repository not found` result and the rationale for continuing to treat MCP++ as a distributed protocol surface.
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

### Residual follow-up after the initial backlog

- Physical-device rollout evidence still has to be collected from real DAT-capable hardware runs; the repo now contains the checklist and fallback contracts, but not the run artifacts themselves.
- Hallucinate desktop E2E coverage remains the operator-console complement to the backend/mobile hardware-free harnesses and should continue to gather evidence under real packaging/runtime conditions.
- Canonical standalone `mcp_plus_plus` source discovery should only be revisited if a valid upstream repository appears with scope that is distinct from the already-reviewed distributed protocol surfaces.

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
- the discovery artifact for this closeout is [data/virtual_ai_os/discovery/no-new-unknowns-2026-05-22.md](../data/virtual_ai_os/discovery/no-new-unknowns-2026-05-22.md)

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

Use the `ipfs_datasets_py` todo daemon and supervisor to advance backlog items, but keep:

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

### Workstream D: UI and operator plane

- Swissknife becomes the composable interface and ORB surface.
- Verified in the current review cycle with the hardware-free descriptor-to-mobile-render harness and the Meta glasses ORB adapter/service surfaces in the `swissknife` worktree.
- Hallucinate App becomes the operator console, daemon/session monitor, and SwissKnife virtual desktop shell.
- HandsFree mobile stays the companion control surface.
- Meta glasses become the remote audio/display terminal.

### Workstream E: Device interface plane

Merge the audio and display stories into one remote-interface contract:

- audio input/output routing,
- display widget rendering,
- action receipts,
- fallback rendering,
- live task progress,
- policy-safe confirmations.

### Workstream F: Full-stack test and rollout discipline

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

- `mcp_plus_plus` upstream is unresolved; do not encode a broken submodule URL.
- `external/ipfs_datasets` currently contains local modifications; advancing the root gitlink must not overwrite that nested worktree.
- `swissknife` also contains local modifications; leave its working tree untouched during the submodule alignment work.
- Meta display APIs remain developer preview surfaces and cannot be required for default CI-safe builds.
- Nested submodules inside upstream repos remain inconsistent; do not assume recursive bootstrap is reliable without explicit guardrails.

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

- let the todo daemon/supervisor advance backlog items in isolated worktrees
- require evidence-backed validation and retry-budget handling

### Phase 4: physical rollout and observability

- validate Android/iOS/device behavior
- document operational readiness, rollback, and metrics

## Daemon-backed Backlog

The machine-readable task board for this plan is:

- `implementation_plan/docs/19-virtual-ai-os-submodule-integration.todo.md`

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