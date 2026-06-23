# Virtual AI OS Submodule Integration Plan

## Status

Comprehensive integration plan for turning the current HandsFree monorepo plus its component repositories into a virtualized AI operating system with Meta glasses as a remote audio and display endpoint.

Created: 2026-05-22
Refreshed: 2026-05-23
MCP++ source re-check: 2026-06-12
VAI-013 MCP++ source resolution: 2026-06-23
VAI-001 topology checkpoint: 2026-06-12
VAI-002 source alignment: 2026-06-12
VAI-023 iPhone native DAT handoff packet: 2026-06-12

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

### 2026-06-12 VAI-001 topology checkpoint

This checkpoint records the reviewed root topology in the current autonomous
worktree without advancing submodule gitlinks or rewriting root `.gitmodules`.
VAI-327 repaired the VAI-001 merge retry-budget blocker by confirming the
failed branch only carried stale topology observations; the current checkpoint
below is canonical and should not be overwritten by
`implementation/vai-001-attempt-1-1781238154`.
The root gitlinks at `HEAD` are:

| Path | Recorded gitlink |
| --- | --- |
| `Mcp-Plus-Plus` | `29343be704da4e193ff143bac7daae9b0f98435d` |
| `external/ipfs_accelerate` | `7913fc3a66b95cc1dc75143b84a2c4c77b838af1` |
| `external/ipfs_datasets` | `45ff065a4208e01ed7b1034a35e1ef2ffc6420b9` |
| `external/ipfs_kit` | `58873ab257104981aa9ba7bee0c2368369716be7` |
| `external/meta-wearables-dat-android` | `25f3a6d4479b7a4a72f877977b865a11af990d04` |
| `external/meta-wearables-dat-ios` | `a739e94181221e7f321304273bcda2272821b163` |
| `hallucinate_app` | `f2a935154a4124b95c897fc0e5964eb43bc51a09` |
| `swissknife` | `8865ff3b872bda4bab492433bbfb858587b03df1` |

Pin guardrails:

- VAI-001 is a topology-recording task only; do not advance any root gitlink
  from this checkpoint.
- Root `.gitmodules` still maps the three IPFS paths to non-`_py` URLs in this
  checkout. Treat any URL rewrite as VAI-002 source-alignment scope, not a
  VAI-001 side effect.
- Root `git submodule status` is safe for this checkpoint. Full recursive
  submodule traversal is not a safe guardrail yet because it currently fails in
  nested IPFS submodules on a missing `.gitmodules` mapping for
  `ipfs_accelerate_py`.
- `Mcp-Plus-Plus` remains the case-sensitive standalone MCP++ spec/docs source;
  do not add a lowercase `mcp_plus_plus` root submodule without a new canonical
  source resolution.
- Evidence:
  [data/virtual_ai_os/discovery/source-topology-vai-001-2026-06-12.md](../../data/virtual_ai_os/discovery/source-topology-vai-001-2026-06-12.md)

### 2026-06-12 VAI-002 source alignment

Root `.gitmodules` now maps the three IPFS root gitlinks to their canonical
`_py` upstream repositories:

| Path | Canonical upstream |
| --- | --- |
| `external/ipfs_datasets` | `https://github.com/endomorphosis/ipfs_datasets_py` |
| `external/ipfs_accelerate` | `https://github.com/endomorphosis/ipfs_accelerate_py` |
| `external/ipfs_kit` | `https://github.com/endomorphosis/ipfs_kit_py` |

This alignment is a wiring-only change. It does not advance root gitlinks,
initialize additional submodules, or alter the case-sensitive `Mcp-Plus-Plus`
or `hallucinate_app` upstream mappings.

Evidence:
[data/virtual_ai_os/discovery/source-alignment-vai-002-2026-06-12.md](../../data/virtual_ai_os/discovery/source-alignment-vai-002-2026-06-12.md)

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
  - recorded root gitlink after VAI-021: `d40eab72b9383519edee54331636350985b4ba79`
  - reviewed upstream base on 2026-05-23: `3133d4fdc85a885ba7d776465bdee48f7a867e01`
  - current branch: `implementation/vai-029-attempt-2-1779760032-submodule-external-ipfs_kit`
  - state: VAI-021 adds the missing nested `ipfs_accelerate_py` mapping in `external/ipfs_kit/.gitmodules`, so `git -C external/ipfs_kit submodule status` and root `git submodule status --recursive` can inspect the topology without failing on an orphan gitlink.
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
- `Mcp-Plus-Plus`
  - upstream: `https://github.com/endomorphosis/Mcp-Plus-Plus.git`
  - recorded root gitlink at repo `HEAD`: `29343be704da4e193ff143bac7daae9b0f98435d`
  - live local checkout on 2026-05-25: `29343be704da4e193ff143bac7daae9b0f98435d`
  - current branch: `implementation/vai-025-attempt-1-1779757879-submodule-Mcp-Plus-Plus`
  - state: clean standalone MCP++ spec/docs source; root `.gitmodules` now maps the existing gitlink to the case-sensitive upstream URL.
- compatibility reference submodules that remain part of the full-stack validation path:
  - `external/meta-wearables-dat-android` recorded and checked out at `25f3a6d4479b7a4a72f877977b865a11af990d04`
  - `external/meta-wearables-dat-ios` recorded and checked out at `a739e94181221e7f321304273bcda2272821b163`

### 2026-05-23 submodule refresh findings

- Root `.gitmodules` wiring is still canonical for `ipfs_datasets_py`, `ipfs_accelerate_py`, `ipfs_kit_py`, `swissknife`, and `hallucinate_app`; local IPFS submodule remotes were synced to those `_py` URLs before fetching.
- `hallucinate_app` required explicit submodule initialization in local Git config before it appeared as a live worktree in `git submodule status`.
- `external/ipfs_datasets` is the only reviewed component whose local checkout currently differs from the recorded superproject gitlink; advancing that pin should be treated as a deliberate superproject change, not an incidental refresh side effect.
- `swissknife` has local modifications in its worktree; protect it from any automated pin or checkout step during backlog automation.
- Recursive submodule status traversal is restored for the reviewed topology: the root `Mcp-Plus-Plus` gitlink has a matching `.gitmodules` entry, and `external/ipfs_kit` now declares its nested `ipfs_accelerate_py` gitlink.
- Until `external/ipfs_kit` advances the nested `ipfs_accelerate_py` gitlink to a verified upstream pin, local bootstrap should avoid recursive update traversal through `external/ipfs_kit`. Use `git submodule update --init external/ipfs_kit` followed by `git -C external/ipfs_kit submodule status` for status-only hygiene; initialize specific nested dependencies only after their pins are verified.
- Evidence: [data/virtual_ai_os/discovery/submodule-refresh-2026-05-23.md](../../data/virtual_ai_os/discovery/submodule-refresh-2026-05-23.md)

### 2026-06-12 VAI-025 MCP++ canonical-source re-check

- The requested snake-case upstream `https://github.com/endomorphosis/mcp_plus_plus` still returns `Repository not found` via `git ls-remote`.
- The case-sensitive upstream `https://github.com/endomorphosis/Mcp-Plus-Plus.git` still resolves; `HEAD` and `refs/heads/main` both point to `29343be704da4e193ff143bac7daae9b0f98435d`.
- Root `.gitmodules` already maps the existing `Mcp-Plus-Plus` gitlink to the case-sensitive upstream URL, and `git submodule status -- Mcp-Plus-Plus` reports the same recorded pin.
- Decision: keep `Mcp-Plus-Plus` as the standalone MCP++ spec/docs source, keep the root pin at `29343be704da4e193ff143bac7daae9b0f98435d`, and do not add or rename to a lowercase `mcp_plus_plus` submodule.
- Runtime MCP++ behavior remains a distributed protocol surface across SwissKnife, `ipfs_datasets_py`, and `ipfs_accelerate_py` until a distinct standalone service implementation is reviewed.
- Evidence: [data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-06-12.md](../../data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-06-12.md)

### 2026-06-23 VAI-013 MCP++ canonical-source resolution

- The requested snake-case upstream `https://github.com/endomorphosis/mcp_plus_plus` still returns `Repository not found` via `git ls-remote`.
- The case-sensitive upstream `https://github.com/endomorphosis/Mcp-Plus-Plus.git` resolves; `HEAD` and `refs/heads/main` both point to `29343be704da4e193ff143bac7daae9b0f98435d`.
- Root `.gitmodules` maps the existing `Mcp-Plus-Plus` gitlink to the case-sensitive upstream URL, and `git submodule status Mcp-Plus-Plus` reports the same recorded pin.
- Decision: keep `Mcp-Plus-Plus` as the standalone MCP++ spec/docs source, keep the root pin at `29343be704da4e193ff143bac7daae9b0f98435d`, and do not add or rename to a lowercase `mcp_plus_plus` submodule.
- Runtime MCP++ behavior remains a distributed protocol surface across SwissKnife, `ipfs_datasets_py`, and `ipfs_accelerate_py` until a distinct standalone service implementation is reviewed.
- Evidence: [data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-vai-013-2026-06-23.md](../../data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-vai-013-2026-06-23.md)

### 2026-05-25 MCP++ canonical-source re-check

- The requested snake-case upstream `https://github.com/endomorphosis/mcp_plus_plus` still returns `Repository not found` via `git ls-remote`.
- The case-sensitive upstream `https://github.com/endomorphosis/Mcp-Plus-Plus.git` resolves; `HEAD` and `refs/heads/main` both point to `29343be704da4e193ff143bac7daae9b0f98435d`.
- The root index already records `Mcp-Plus-Plus` as a gitlink at that same commit, so the scoped fix is to add the missing root `.gitmodules` mapping rather than create a second snake-case `mcp_plus_plus` entry.
- Treat `Mcp-Plus-Plus` as the standalone MCP++ spec/docs source. Runtime MCP++ behavior remains a distributed protocol surface across SwissKnife, `ipfs_datasets_py`, and `ipfs_accelerate_py` until a distinct standalone service implementation is reviewed.
- Evidence: [data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-25.md](../../data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-05-25.md)

### Upstream blocker history

- Requested upstream `https://github.com/endomorphosis/mcp_plus_plus` did not resolve via `git ls-remote` on 2026-05-22 and still does not resolve on the 2026-06-12 VAI-025 re-check.
- The valid canonical source uses the case-sensitive repository name `Mcp-Plus-Plus`; do not encode the broken snake-case URL in root submodule metadata.
- Keep MCP++ runtime implementation as a distributed protocol surface until a reviewed standalone service exists beyond the already-integrated MCP, ORB, and routing surfaces in `swissknife`, `ipfs_accelerate_py`, and `ipfs_datasets_py`.

### Canonical-source resolution

- Initial resolution date: 2026-05-22.
- Re-check date: 2026-06-12.
- Decision: wire the existing `Mcp-Plus-Plus` root gitlink in `.gitmodules` to `https://github.com/endomorphosis/Mcp-Plus-Plus.git` and keep the pin at `29343be704da4e193ff143bac7daae9b0f98435d`.
- Evidence: [data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-06-12.md](../../data/virtual_ai_os/discovery/mcp_plus_plus-source-resolution-2026-06-12.md) records the current `Repository not found` result for the snake-case URL, the successful case-sensitive upstream resolution, and the decision to treat `Mcp-Plus-Plus` as the standalone spec/docs source.
- Re-open the runtime-service decision only when a reviewed upstream implementation exists and can be pinned without duplicating the already-integrated MCP, ORB, and routing surfaces in `swissknife`, `ipfs_accelerate_py`, and `ipfs_datasets_py`.

## Current Integration Baseline

### What already exists

- HandsFree already has direct `ipfs_datasets_py` adapter seams in `src/handsfree/ipfs_datasets_routers.py`.
- HandsFree already has a delegated task/provider model under `src/handsfree/agents/`, `src/handsfree/agent_providers.py`, and `src/handsfree/mcp/`.
- Swissknife already provides MCP-IDL, ORB routing, and widget-authoring surfaces.
- Swissknife now has a hardware-free Meta glasses descriptor-to-mobile-render harness that exercises ORB discovery, binding, invocation, bridge receipts, and operator-safe fallback behavior in `test/mcp-plus-plus/meta-glasses-display-harness.test.ts`.
- Hallucinate App now positions itself as the operator console and daemon manager shell that hosts SwissKnife virtual desktop workflows for the virtual AI OS.
- VAI-024 adds desktop operator E2E coverage across Hallucinate App and SwissKnife: `hallucinate_app/test/e2e/mcp-daemon-manager.spec.ts` simulates inspecting, routing, rendering, and recovering a daemon task from the desktop console, while `swissknife/test/mcp-plus-plus/meta-glasses-display-harness.test.ts` and `swissknife/test/mcp-plus-plus/meta-glasses-mobile-orb-bridge.test.ts` prove the same task can fall back from unpaired Meta glasses hardware to Hallucinate App and SwissKnife operator surfaces.
- The repo already contains one machine-readable daemon backlog pattern for the Meta glasses widget stream.
- Mobile plus backend already contain Meta DAT display and action-routing primitives.
- A dedicated simulation plan now exists in `implementation_plan/docs/20-meta-rayban-display-interface-simulator.md` for browser-first Meta Ray-Ban interface validation before iPhone handoff.
- VAI-023 prepared the iPhone native DAT handoff bundle and physical evidence gate in `data/virtual_ai_os/discovery/2026-06-12-vai-023-iphone-native-dat-handoff.md`.

### Residual follow-up after the initial backlog

- Physical-device rollout evidence still has to be collected from real DAT-capable hardware runs; the repo now contains the checklist and fallback contracts, but not the run artifacts themselves.
- Hallucinate desktop E2E coverage remains the operator-console complement to the backend/mobile hardware-free harnesses and should continue to gather evidence under real packaging/runtime conditions.
- Canonical standalone `Mcp-Plus-Plus` spec/docs source is pinned; runtime-service discovery should only be revisited if a valid upstream implementation appears with scope that is distinct from the already-reviewed distributed protocol surfaces.
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
- Keep the canonical `Mcp-Plus-Plus` spec/docs submodule wired to the case-sensitive upstream and avoid adding the broken snake-case `mcp_plus_plus` URL.
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
- future standalone `Mcp-Plus-Plus` services once runtime-service scope is resolved.

This runtime is the operating-system scheduler equivalent for the stack.

### Workstream D: Meta Ray-Ban simulation and iPhone handoff

- Use `implementation_plan/docs/20-meta-rayban-display-interface-simulator.md` as the canonical implementation plan for the pre-hardware simulation track.
- Use `data/virtual_ai_os/discovery/2026-06-12-vai-023-iphone-native-dat-handoff.md` as the physical-run handoff packet for iPhone native DAT validation.
- Treat Meta Web Apps browser preview plus DAT Mock Device tooling as the official pre-hardware inputs that we can actually verify today.
- Build one canonical 600x600 manifest-driven simulator that feeds browser preview, Web App packaging, mobile fixture tests, and DAT-native adapter validation.
- Keep the simulator bridge-compatible with the current HandsFree mobile ORB/display-widget contracts so simulator traces can become integration-test fixtures instead of throwaway mocks.

### Workstream E: UI and operator plane

- Swissknife becomes the composable interface and ORB surface.
- Verified in the current review cycle with the hardware-free descriptor-to-mobile-render harness and the Meta glasses ORB adapter/service surfaces in the `swissknife` worktree.
- Hallucinate App becomes the operator console, daemon/session monitor, and SwissKnife virtual desktop shell.
- Desktop operator coverage now includes a hardware-free daemon task path: inspect through the Hallucinate App daemon manager, route through SwissKnife ORB/virtual desktop, render to the desktop fallback panel when Meta glasses are unpaired, and recover the task with receipt-backed state updates.
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

#### VAI-008 Meta Glasses Remote Terminal Contract

The Meta glasses path is defined as a constrained terminal for mobile-hosted
virtual AI OS sessions, not as an unconstrained secondary display. HandsFree
owns the stable route contract in
`src/handsfree/meta_glasses_remote_terminal.py` under
`handsfree.meta-glasses/remote-terminal@0.1.0`.

Required route shape:

- `surface_id: mobile_glasses`
- `terminal_kind: meta_glasses_remote_terminal`
- endpoints:
  - `meta_glasses_audio_input` for audio command capture through the mobile
    `expo_glasses_audio` bridge, with `phone_microphone` fallback
  - `meta_glasses_audio_output` for spoken response playback, with
    `phone_speaker` fallback
  - `meta_glasses_display_widget` for visual status output through the mobile
    ORB/display-widget runtime, with `display_webapp_or_mobile_card` fallback
- `session_contract.host_mode: mobile_hosted`
- `terminal_constraints.hardware_required: false`
- `terminal_constraints.input_channels: audio_command`
- `terminal_constraints.output_channels: visual_status` and `tts`
- permitted terminal actions limited to confirm, cancel, retry pairing, switch
  to phone preview, and open desktop-offload status

Pairing and disconnection semantics:

- `pairing.state` carries `unpaired`, `pairing`, `paired`, or
  `pairing_lost`.
- An unpaired or disconnected glasses path must keep the mobile session alive
  and fall back to `mobile-card` rendering.
- `disconnection_handling.on_pairing_lost` must mark display unavailable,
  continue the mobile session, and expose a reconnect action.
- Audio command capture falls back to the phone microphone; visual status falls
  back to the display Web App or mobile card.

Desktop-offload visibility:

- `desktop_offload.visibility` is always visible in the terminal session
  contract, even when no peer is selected.
- `desktop_offload.status_region` maps to the widget `peer_offload` region
  proven by the VAI-006 Swissknife ORB path and VAI-007 Hallucinate App
  operator-console path.
- If desktop offload disconnects or fails, compute placement falls back to
  `phone_local` while status remains visible on mobile/glasses fallback
  surfaces.

VAI-008 validation evidence:

- `tests/test_meta_glasses_display_todo_queue.py` validates the constrained
  route manifest through `build_meta_glasses_remote_terminal_route()`.
- `data/virtual_ai_os/discovery/2026-06-23-vai-008-meta-glasses-remote-terminal.md`
  records the reviewed device-plane evidence and dependency handoff from
  VAI-003, VAI-004, VAI-006, and VAI-007.

#### VAI-022 Browser Web App Package for HTTPS Glasses Loading

The glasses-accessible browser Web App is the static package at
`dev/meta-rayban-display-simulator/webapp/`. It is the required HTTPS glasses
loading path before native iPhone DAT display rollout. The package is
self-contained and must remain copy-deployable to a static host without a build
step:

- `index.html` is the fixed 600x600 entrypoint for the Meta display viewport.
- `manifest.webmanifest` declares fullscreen display mode and PNG icons,
  including the 52x52 minimum icon used by the glasses Web App surface.
- `app.js` owns D-pad focus, Enter activation, and local ORB event persistence.
- `readiness.json` is the deployment contract and linter input for public
  hosting, manifest metadata, widget IDs, focus order, and the final
  `deployment_url`.

Required HTTPS loading modes:

- Local development mode: serve the directory from localhost for simulator and
  desktop browser checks only. This mode may validate layout, focus order,
  readiness metadata, and fixture parity, but it is not glasses-loadable unless
  exposed through a public HTTPS URL.
- Phone-hosted mode: keep the phone as the mobile session host from VAI-008 and
  open the hosted Web App through the Meta AI app Web Apps connection. The
  phone carries pairing, audio routing, command session state, and fallback to
  mobile-card rendering; the glasses load only the HTTPS Web App URL registered
  from `readiness.json`.
- Desktop-hosted mode: serve the same static package from a desktop-controlled
  public HTTPS origin such as GitHub Pages, Netlify, Vercel, or an approved
  tunnel fronted by a trusted certificate. The desktop may own operator console
  and offload state, but glasses loading still targets the hosted Web App URL
  and must keep VAI-008 terminal constraints and mobile fallback semantics.

Operational contract:

- Private IPs, unauthenticated local LAN URLs, and plain HTTP are acceptable for
  developer preview only and must not be used as the final glasses loading URL.
- The deployed `index.html`, `manifest.webmanifest`, `readiness.json`, icons,
  CSS, and JS must return HTTP 200 without authentication.
- `readiness.json.deployment_url` must be updated to the exact HTTPS URL used
  for glasses registration before collecting physical run evidence.
- Browser packaging evidence is recorded in
  `data/virtual_ai_os/discovery/2026-06-23-vai-022-browser-web-app-https-loading.md`.

### Workstream G: Full-stack test and rollout discipline

Build a layered test matrix:

- unit: individual adapter contracts
- contract: capability registry and schema validation
- integration: component-to-component routing
- harness: hardware-free end-to-end flows
- device: Android/iOS physical validation
- ops: repo-local backlog daemon, implementation supervisor, and worktree automation: isolate each implementation attempt in its own worktree, verify worktree isolation before merge, and confirm the supervisor backlog remains parseable after each cycle.

## Test Matrix

### Priority integration scenarios

1. Planner selects a task, daemon marks it ready, runtime routes execution through `ipfs_datasets_py` plus `ipfs_accelerate_py`, stores artifacts with `ipfs_kit_py`, then emits mobile/glasses progress updates.
2. Swissknife authors a UI descriptor, HandsFree validates it, Hallucinate App exposes it in the desktop shell, and mobile/glasses render a safe fallback view.
3. A long-running agent task streams status to Hallucinate App, mobile, and Meta glasses from one shared task state source.
4. A failure path produces one normalized error contract across backend, Swissknife, Hallucinate App, and glasses surfaces.
5. A no-native-display environment falls back to web/mobile rendering without changing the workflow semantics.

### Required validation layers

- daemon board parseability tests (supervisor must parse backlog after each worktree cycle)
- wrapper dry-run tests for `llm_router`
- capability registry contract tests
- backend API and OpenAPI tests
- mobile bridge tests
- Swissknife Jest/TypeScript tests
- Hallucinate App e2e smoke tests
- Android/iOS build or sample-flow checks

## Risks and Constraints

- The snake-case `mcp_plus_plus` upstream remains unresolved; do not encode that broken submodule URL. Use the case-sensitive `Mcp-Plus-Plus` spec/docs pin instead.
- `external/ipfs_datasets` currently contains local modifications; advancing the root gitlink must not overwrite that nested worktree.
- `swissknife` also contains local modifications; leave its working tree untouched during the submodule alignment work.
- Meta display APIs remain developer preview surfaces and cannot be required for default CI-safe builds.
- Nested submodules inside upstream repos remain inconsistent; use status-only recursive checks for hygiene and avoid recursive `update --init` through `external/ipfs_kit` until its nested `ipfs_accelerate_py` pin is verified upstream.
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

- operate the repo-local backlog daemon and implementation supervisor with per-task isolated worktrees
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

## Component Repo Contracts

VAI-009 defines the environment, pin, and bootstrap contract for component
repositories in `src/handsfree/virtual_ai_os_components.py` and surfaces it
through `get_virtual_ai_os_observability_contract`.

The contract keeps these guardrails stable:

- Root `.gitmodules` is the component source contract. The code-level contract
  must match every root submodule path and URL.
- The superproject gitlink is the reviewed pin. Bootstrap code may initialize
  or sync a component worktree, but must not fetch, checkout, or advance a
  component without an explicit pin-refresh task.
- Recursive bootstrap remains disabled for the component set. `external/ipfs_kit`
  uses a status-only nested bootstrap mode until nested pins are explicitly
  reviewed.
- Meta DAT Android and iOS repositories are optional device-validation
  references. They remain status-only unless a physical/native validation task
  needs the local checkout.
- Component root overrides are environment-driven:
  `HANDSFREE_VAI_IPFS_DATASETS_ROOT`,
  `HANDSFREE_VAI_IPFS_ACCELERATE_ROOT`,
  `HANDSFREE_VAI_IPFS_KIT_ROOT`,
  `HANDSFREE_VAI_SWISSKNIFE_ROOT`,
  `HANDSFREE_VAI_HALLUCINATE_APP_ROOT`,
  `HANDSFREE_VAI_MCP_PLUS_PLUS_ROOT`,
  `HANDSFREE_VAI_META_DAT_ANDROID_ROOT`, and
  `HANDSFREE_VAI_META_DAT_IOS_ROOT`.

Evidence:
[data/virtual_ai_os/discovery/component-repo-contracts-vai-009-2026-06-12.md](../../data/virtual_ai_os/discovery/component-repo-contracts-vai-009-2026-06-12.md)

## Observability, Policy, and Rollback Artifacts

VAI-011 defines stable supervisor reconciliation artifacts in
`src/handsfree/virtual_ai_os_observability.py` and exposes the advertised
schema through `get_virtual_ai_os_observability_contract()["artifact_contract"]`.

The artifact contract is
`handsfree.virtual-ai-os/observability-artifacts@0.1.0` and uses
`task_id`, `correlation_id`, and `artifact_id` as the durable reconcile keys.
Supervisors can persist or replay the ordered bundle without searching logs or
mobile ORB in-memory state.

Stable artifact types:

- `policy_decision`: records permit, deny, or confirmation decisions with the
  policy ref, reason, actor, timestamp, and evidence refs.
- `placement_change`: records transitions such as phone-local to desktop-peer
  execution with parent links back to the policy decision.
- `remote_execution_receipt`: records the remote surface, operation, status,
  receipt ref, and stream refs emitted by SwissKnife ORB, MCP/MCP++, mobile, or
  glasses paths.
- `validation_failure`: records validator name, failure code, message,
  retryability, and evidence refs for failed schema, runtime, or dispatch
  checks.
- `rollback_event`: records fallback or rollback action, restored placement or
  ref, reason, and parent validation-failure artifact.

The VAI-010 hardware-free harness remains the behavioral source for dispatch,
offload, streaming, and recovery. VAI-011 adds the retry/reconcile artifact
layer around those events so a daemon supervisor can resume from the latest
rollback artifact or reconcile the full chain by artifact id.

Evidence:
[data/virtual_ai_os/discovery/2026-06-23-vai-011-observability-policy-rollback.md](../../data/virtual_ai_os/discovery/2026-06-23-vai-011-observability-policy-rollback.md)

## Success Criteria

The plan is successful when:

1. the root repo tracks the correct component sources and reviewed pins,
2. one daemon-parseable backlog governs the integration sequence,
3. one capability-routing contract spans all component repos,
4. Meta glasses function as a remote audio/display endpoint for the system,
5. end-to-end integration tests can exercise the virtual AI OS without requiring physical hardware for every run.
