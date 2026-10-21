# Virtual Desktop ORB/IDL GUI Taskboard (VOG)

Consumable by `ipfs_accelerate_py.agent_supervisor` with task prefix `## VOG-`.

Companion objectives:
`implementation_plan/docs/52-virtual-desktop-orb-idl-gui.objectives.md`.

Runtime profile:
`config/virtual_desktop_orb_idl_gui_supervisor.json`.

Lane inventory:
`config/virtual_desktop_orb_idl_gui_lane_inventory.json`.

Program decision: **NO_GO** until `vog/orb-idl-gui-coverage.json` says `decision: GO`, `passed: true`, and `clicked: true`.

Do not edit the VDG or VDL boards. Do not mark VDG-060 or VDL-020 complete.

## Parallel execution contract

- A task is selectable only when every `Depends on` task is completed.
- Ready tasks whose `Predicted files` overlap fail closed.
- Browser runs are chained. One live-click target owns the desktop.
- The rescue watchdog runs one lane, `vog-planning`, one ready task per cycle.
- Only lane `vog-planning` edits this file or the objectives file.
- Workers do not push. Merge target is `agent/virtual-desktop-orb-idl-gui`.
- The watchdog cannot mark a task complete.
- VOG-090 is the only command that exits 75. It is not selectable early.

## Execution waves

| Wave | Tasks | Parallelism |
| --- | --- | --- |
| 0 | 000, 001 | Operator seal |
| 1 | 010, 070, 011, 013, 016, 018, 019 | Ledger and watchdog commands, then disjoint edits |
| 2 | 012, 014, 020, 031, 032, 033, 034, 035, 036 | Census, join, and route edits |
| 3 | 021 then 041, 042, 043, 044, 045, 046 | One browser target at a time |
| 4 | 080 then 090 | Aggregate, then closeout |

## VOG-000 Publish the submodule sync receipt

- Status: completed
- Completion: operator 2026-10-19. Direct origin/main fast-forward, recurse off, no parent gitlink commit.
- Priority: P0
- Track: ops
- Depends on:
- Goal id: VOG-G001
- Outputs: data/agent_supervisor/virtual_desktop_orb_idl_gui/submodule-sync.json
- Validation: python3 -m json.tool data/agent_supervisor/virtual_desktop_orb_idl_gui/submodule-sync.json
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/ops
- Parallel lane: vog-planning
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: data/agent_supervisor/virtual_desktop_orb_idl_gui/submodule-sync.json
- Conflict policy: Do not commit parent gitlinks. Do not force-push. Do not push Facebook wearables. Do not recurse into the ipfs_accelerate_py and ipfs_datasets_py cycle.
- Acceptance: Every direct submodule has an action other than force. Dirty trees were not pushed.

## VOG-001 Seal the ORB/IDL GUI program

- Status: completed
- Completion: operator 2026-10-19. Profile, lane inventory, objectives, and this todo exist. The VDG watchdog was left running.
- Priority: P0
- Track: planning
- Depends on: VOG-000
- Goal id: VOG-G001
- Outputs: implementation_plan/docs/52-virtual-desktop-orb-idl-gui.objectives.md, implementation_plan/docs/52-virtual-desktop-orb-idl-gui.todo.md, config/virtual_desktop_orb_idl_gui_supervisor.json, config/virtual_desktop_orb_idl_gui_lane_inventory.json
- Validation: python3 -m json.tool config/virtual_desktop_orb_idl_gui_supervisor.json
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/planning
- Parallel lane: vog-planning
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: implementation_plan/docs/52-virtual-desktop-orb-idl-gui.objectives.md, implementation_plan/docs/52-virtual-desktop-orb-idl-gui.todo.md, config/virtual_desktop_orb_idl_gui_supervisor.json, config/virtual_desktop_orb_idl_gui_lane_inventory.json
- Conflict policy: Own this board only. Do not edit the VDG or VDL boards. Do not start a second VDG watchdog.
- Acceptance: Goal and task ids are unique, dependencies are acyclic, and simultaneously ready tasks have disjoint predicted files.

## VOG-010 Refresh the live-binding gap ledger

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-18T23:19:26Z
- Priority: P0
- Track: inventory
- Depends on: VOG-001
- Goal id: VOG-G010
- Outputs: swissknife/docs/all-app-live-binding-gap-ledger.md
- Deterministic command: node swissknife/scripts/build-all-app-live-binding-gap-ledger.cjs
- Validation: test -f swissknife/docs/all-app-live-binding-gap-ledger.md
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/inventory
- Parallel lane: vog-inventory
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/scripts/build-all-app-live-binding-gap-ledger.cjs, swissknife/docs/all-app-live-binding-gap-ledger.md, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/all-app-live-binding-gap-ledger.json
- Conflict policy: Recompute exact-name counts. Do not add GUI calls. Do not edit app source.
- Acceptance: The ledger states its generated time. Manifest rows are not execution.

## VOG-011 Write the rendered-control census

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T00:54:46Z
- Priority: P0
- Track: census
- Depends on: VOG-001
- Goal id: VOG-G011
- Outputs: swissknife/scripts/build-rendered-control-census.cjs
- Validation: node --check swissknife/scripts/build-rendered-control-census.cjs
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/census
- Parallel lane: vog-census
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/scripts/build-rendered-control-census.cjs
- Conflict policy: Do not click tool buttons. Do not edit app source or main-simple.js.
- Acceptance: The script launches every manifest app after render, records app_id, launch_id, selector, role, and accessible name, rejects selectors that contain ${ or escapeHTML, sets source_template false and clicked false, and writes swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/rendered-control-census.json. Schema is swissknife.rendered-control-census.v1.

## VOG-012 Run the rendered-control census

- Status: completed
- Completion: satisfied by VOG-R012 at 2026-10-19T05:04:21Z
- Priority: P0
- Track: census
- Depends on: VOG-011
- Goal id: VOG-G011
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/rendered-control-census.json
- Deterministic command: node swissknife/scripts/build-rendered-control-census.cjs
- Validation: python3 swissknife/scripts/vog_rendered_census_requires_live_dom.py
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/census
- Parallel lane: vog-census
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/rendered-control-census.json
- Conflict policy: Do not run beside a live-click target. Do not edit the census script in this task.
- Acceptance: At least 45 apps and no template selectors. clicked is false.

## VOG-013 Write the ORB/IDL join

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-18T23:47:47Z
- Priority: P0
- Track: join
- Depends on: VOG-001
- Goal id: VOG-G012
- Outputs: swissknife/scripts/build-orb-idl-control-matrix.cjs
- Validation: node --check swissknife/scripts/build-orb-idl-control-matrix.cjs
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/join
- Parallel lane: vog-join
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/scripts/build-orb-idl-control-matrix.cjs
- Conflict policy: Do not edit the census script or app source.
- Acceptance: The script reads the rendered census and the gap ledger, assigns one disposition and one idl_method per control, and writes swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-control-matrix.json. Schema is swissknife.orb-idl-control-matrix.v1. IDL methods are read_status, read_receipts, request_action, request_fallback, request_prompt_steering, or none. Shell chrome is local-only. openrouter is external-provider. A data-live-gateway-binding is invoke or confirm-then-invoke and names that tool id. request_prompt_steering belongs only to agent-supervisor.

## VOG-014 Run the ORB/IDL join

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-19T05:04:28Z
- Priority: P0
- Track: join
- Depends on: VOG-010, VOG-012, VOG-013
- Goal id: VOG-G012
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-control-matrix.json
- Deterministic command: node swissknife/scripts/build-orb-idl-control-matrix.cjs
- Validation: python3 swissknife/scripts/vog_orb_idl_matrix_requires_join.py
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/join
- Parallel lane: vog-join
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-control-matrix.json
- Conflict policy: Do not edit the join script. Fail closed when an app has no family.
- Acceptance: uncovered_app_visible_count is 0. Invoke rows carry an mcp++ tool id and an IDL method other than none.

## VOG-016 Bind listeners after render

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T05:15:18Z
- Priority: P0
- Track: listeners
- Depends on: VOG-001
- Goal id: VOG-G021
- Outputs: swissknife/web/js/main-simple.js
- Validation: node swissknife/scripts/check-listener-after-render.cjs
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/listeners
- Parallel lane: vog-listeners
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/main-simple.js
- Conflict policy: This is the only task that edits main-simple.js. Keep the file-manager and todo calls added on origin/main 30156d0c.
- Acceptance: Every create* success path that assigns contentElement.innerHTML calls setupEventListeners or mount after that assignment. The checker exits 0. Generated surfaces for datasets-browser, accelerate-panel, idl-explorer, orb-auto-ui, and glasses-preview are included.

## VOG-018 Move the shared artifact helper onto tools/call

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T05:20:52Z
- Priority: P0
- Track: routes
- Depends on: VOG-001
- Goal id: VOG-G022
- Outputs: swissknife/web/js/apps/real-artifact.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/real-artifact.js
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/routes
- Parallel lane: vog-routes
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/apps/real-artifact.js
- Conflict policy: This is the only task that edits real-artifact.js. Family tasks consume it after this task completes.
- Acceptance: The helper persists and reads artifacts with POST /mcp/tools/call. Quoted /mcp/artifacts and /mcp/dag paths are gone. Receipt CID and event-DAG CID stay on the observation.

## VOG-019 Compute the live-click decision

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T05:24:16Z
- Priority: P0
- Track: harness
- Depends on: VOG-001
- Goal id: VOG-G023
- Outputs: swissknife/test/e2e/helpers/live-click-session.ts
- Validation: node swissknife/scripts/check-live-click-decision.cjs
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/harness
- Parallel lane: vog-harness
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/test/e2e/helpers/live-click-session.ts
- Conflict policy: Do not edit app source. Do not edit the VDL board. A visual_review note cannot set GO.
- Acceptance: The report type allows GO or no_go. decision is GO only when every visible row was clicked, invoke and deny rows have a complete POST /mcp/tools/call observation, and zero-call dispositions recorded zero calls. A CID prompt is filled with the fixture CID before the row is judged. A private /mcp/artifacts request is a failure reason, not an observation.

## VOG-020 Wire image-viewer through MCP++

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T05:34:02Z
- Priority: P0
- Track: pilot
- Depends on: VOG-016, VOG-018
- Goal id: VOG-G030
- Outputs: swissknife/web/js/apps/image-viewer.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/image-viewer.js
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/pilot
- Parallel lane: vog-pilot
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/apps/image-viewer.js
- Conflict policy: Do not edit main-simple.js, real-artifact.js, or the live-click helper.
- Acceptance: retrieveCidImage and publish use POST /mcp/tools/call. The retrieve tool id is mcp++:ipfs_kit_py/artifacts/get. The IDL method is request_action. Zoom, pan, and filters stay local-only.

## VOG-021 Click the image-viewer pilot

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T20:48:21Z
- Reopened: 2026-10-20T20:26:17Z; Pilot report predates current owner-health and owner-execution validation; rerun with the current harness.
- Previous completion: lane_resume validation already passed during attempt backoff at 2026-10-19T18:47:14Z
- Priority: P0
- Track: pilot
- Depends on: VOG-012, VOG-019, VOG-020
- Goal id: VOG-G030
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs pilot
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json pilot
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/pilot
- Parallel lane: vog-pilot
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json
- Conflict policy: One browser. Do not edit app source. Do not mark VDL-020 complete. Do not flip the VDG coverage file.
- Acceptance: decision is GO, clicked is true, and the retrieve row has a /mcp/tools/call observation. Before and after PNGs exist for every clicked row.

## VOG-031 Wire storage and media routes

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T05:55:16Z
- Priority: P1
- Track: storage
- Depends on: VOG-016, VOG-018
- Goal id: VOG-G041
- Outputs: swissknife/web/js/apps/ipfs-explorer.js, swissknife/web/js/apps/media-player.js, swissknife/web/js/apps/peertube.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/ipfs-explorer.js swissknife/web/js/apps/media-player.js swissknife/web/js/apps/peertube.js
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/storage
- Parallel lane: vog-storage
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/apps/ipfs-explorer.js, swissknife/web/js/apps/media-player.js, swissknife/web/js/apps/peertube.js
- Conflict policy: Do not edit image-viewer.js. Do not edit the shared helper.
- Acceptance: Quoted private /mcp paths are gone. Reads use read_status or request_action through /mcp/tools/call. Writes stay confirm-then-invoke.

## VOG-032 Wire dataset-family routes

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T06:26:05Z
- Priority: P1
- Track: datasets
- Depends on: VOG-016, VOG-018
- Goal id: VOG-G042
- Outputs: swissknife/web/js/apps/notes.js, swissknife/web/js/apps/vibecode.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/notes.js swissknife/web/js/apps/vibecode.js
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/datasets
- Parallel lane: vog-datasets
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/apps/notes.js, swissknife/web/js/apps/vibecode.js
- Conflict policy: Do not edit main-simple.js. datasets-browser and accelerate-panel stay in the listener task.
- Acceptance: Notes and vibecode quotes no private /mcp path. Dataset publish still finds dataset_id inside dataset_data.

## VOG-033 Wire accelerate-family routes

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T06:47:21Z
- Priority: P1
- Track: accelerate
- Depends on: VOG-016, VOG-018
- Goal id: VOG-G043
- Outputs: swissknife/web/js/apps/neural-network-designer.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/neural-network-designer.js
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/accelerate
- Parallel lane: vog-accelerate
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/apps/neural-network-designer.js
- Conflict policy: Do not edit the datasets files or main-simple.js.
- Acceptance: The designer quotes no private /mcp path. Model and training reads use read_status.

## VOG-034 Wire network-family routes

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T07:13:47Z
- Priority: P1
- Track: network
- Depends on: VOG-016, VOG-018
- Goal id: VOG-G044
- Outputs: swissknife/web/js/apps/friends-list.js, swissknife/web/js/apps/p2p-chat.js, swissknife/web/js/apps/p2p-chat-unified.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/friends-list.js swissknife/web/js/apps/p2p-chat.js swissknife/web/js/apps/p2p-chat-unified.js
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/network
- Parallel lane: vog-network
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/apps/friends-list.js, swissknife/web/js/apps/p2p-chat.js, swissknife/web/js/apps/p2p-chat-unified.js
- Conflict policy: Do not edit the storage or dataset app files.
- Acceptance: Chat and friends quotes no private /mcp path. A send is confirm-then-invoke.

## VOG-035 Wire the MCP++ explorer

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T07:34:56Z
- Priority: P1
- Track: control
- Depends on: VOG-016, VOG-018
- Goal id: VOG-G045
- Outputs: swissknife/web/js/apps/mcp-plus-plus-explorer.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/mcp-plus-plus-explorer.js
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/control
- Parallel lane: vog-control
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/apps/mcp-plus-plus-explorer.js
- Conflict policy: Do not edit main-simple.js. idl-explorer and orb-auto-ui are generated surfaces owned by VOG-016.
- Acceptance: The explorer quotes no private /mcp path. IDL methods shown to the user are the desktop four, plus request_prompt_steering only for agent-supervisor.

## VOG-036 Wire local-only negatives

- Status: completed
- Completion: lane_resume bounded implement validation exit 0 at 2026-10-19T07:50:37Z
- Priority: P1
- Track: local
- Depends on: VOG-016, VOG-018
- Goal id: VOG-G046
- Outputs: swissknife/web/js/apps/calendar.js, swissknife/web/js/apps/clock.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/calendar.js swissknife/web/js/apps/clock.js
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/local
- Parallel lane: vog-local
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/web/js/apps/calendar.js, swissknife/web/js/apps/clock.js
- Conflict policy: Do not edit network or storage files. openrouter stays external-provider.
- Acceptance: Calendar and clock quote no private /mcp path. Their visible controls are local-only and must call no tool.

## VOG-041 Click storage and media

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T02:50:58Z
- Priority: P1
- Track: storage
- Depends on: VOG-021, VOG-031
- Goal id: VOG-G041
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs storage
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json family
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/storage
- Parallel lane: vog-storage
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Conflict policy: Do not start another browser target. Do not edit app source.
- Acceptance: decision GO and clicked true. Every invoke row has a tools/call observation and a PNG pair. Shell chrome has zero calls.

## VOG-042 Click datasets, notes, models, and chat

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T03:28:39Z
- Priority: P1
- Track: datasets
- Depends on: VOG-041, VOG-032
- Goal id: VOG-G042
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/datasets.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs datasets
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/datasets.json family
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/datasets
- Parallel lane: vog-datasets
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/datasets.json
- Conflict policy: Do not start another browser target. Do not edit app source.
- Acceptance: decision GO and clicked true. ai-chat remains on this family.

## VOG-043 Click accelerate and neural apps

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T04:30:38Z
- Priority: P1
- Track: accelerate
- Depends on: VOG-042, VOG-033
- Goal id: VOG-G043
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/accelerate.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs accelerate
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/accelerate.json family
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/accelerate
- Parallel lane: vog-accelerate
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/accelerate.json
- Conflict policy: Do not start another browser target. Do not edit app source.
- Acceptance: decision GO and clicked true. huggingface and accelerate-panel stay on this family.

## VOG-044 Click network apps

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T05:10:53Z
- Priority: P1
- Track: network
- Depends on: VOG-043, VOG-034
- Goal id: VOG-G044
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/network.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs network
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/network.json family
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/network
- Parallel lane: vog-network
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/network.json
- Conflict policy: Do not start another browser target. Do not edit app source.
- Acceptance: decision GO and clicked true. Send stays confirm-then-invoke.

## VOG-045 Click the control plane

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T06:27:08Z
- Priority: P1
- Track: control
- Depends on: VOG-044, VOG-035
- Goal id: VOG-G045
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/control.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs control
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/control.json family
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/control
- Parallel lane: vog-control
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/control.json
- Conflict policy: Do not start another browser target. Do not edit app source. Prompt steering stays behind confirmation.
- Acceptance: decision GO and clicked true. orb-auto-ui and idl-explorer are in this report.

## VOG-046 Click local-only and external-provider apps

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T08:44:55Z
- Priority: P1
- Track: local
- Depends on: VOG-045, VOG-036
- Goal id: VOG-G046
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/local.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs local
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/local.json local
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/local
- Parallel lane: vog-local
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/local.json
- Conflict policy: Do not start another browser target. Do not edit app source. A local click that calls a tool fails the report.
- Acceptance: decision GO, clicked true, and every row has mcp_call_count 0. openrouter is external-provider.

## VOG-070 Exit a blocked lane instead of heartbeating forever

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-18T23:20:28Z
- Priority: P0
- Track: watchdog
- Depends on: VOG-001
- Goal id: VOG-G070
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py
- Deterministic command: python3 external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/run_repo_pytest.py -q external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py -k live_blocked_resume_exits --tb=line -p no:cacheprovider
- Validation: test -f external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: accelerate/agent-supervisor/rescue
- Parallel lane: vog-watchdog
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py, external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py
- Conflict policy: Do not restart the running VDG watchdog. Do not set work_complete. gate_withheld must keep looping. Provider rescue stays off.
- Acceptance: serve returns when the cycle phase is deterministic_resume_unavailable and leaves state blocked. The dead lane is resumable once. The same signature then writes a body-free packet. A new missing_handler must be named in the watchdog test before VOG-090 can exit 0.

## VOG-080 Aggregate the ORB/IDL GUI coverage

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T20:48:21Z
- Reopened: 2026-10-20T20:26:17Z; Revalidate after refreshing VOG-021 pilot evidence; all seven underlying reports must pass current validation.
- Previous completion: lane_resume deterministic command exit 0 at 2026-10-20T08:44:55Z
- Priority: P0
- Track: gate
- Depends on: VOG-014, VOG-021, VOG-041, VOG-042, VOG-043, VOG-044, VOG-045, VOG-046
- Goal id: VOG-G050
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-gui-coverage.json
- Deterministic command: node swissknife/scripts/build-orb-idl-gui-coverage.cjs
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-gui-coverage.json
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/gate
- Parallel lane: vog-gate
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/scripts/build-orb-idl-gui-coverage.cjs, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-gui-coverage.json
- Conflict policy: Do not read or write gui-mcp-coverage.json. Do not flip a partial family to GO.
- Acceptance: The file lists all seven targets. decision is GO only when every target is GO, clicked, and passed. work_complete stays false.

## VOG-090 Close out only on GO

- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-20T20:48:52Z
- Reopened: 2026-10-20T20:26:17Z; Revalidate after refreshing VOG-021 pilot evidence; all seven underlying reports must pass current validation.
- Previous completion: lane_resume deterministic command exit 0 at 2026-10-20T08:45:25Z
- Priority: P0
- Track: planning
- Depends on: VOG-070, VOG-080
- Goal id: VOG-G090
- Outputs: implementation_plan/docs/52-virtual-desktop-orb-idl-gui.todo.md
- Deterministic command: python3 swissknife/scripts/vog_closeout_requires_go.py
- Validation: python3 swissknife/scripts/vog_closeout_requires_go.py
- Board namespace: virtual-desktop-orb-idl-gui-v1
- Bundle: swissknife/virtual-desktop/orb-idl-gui/closeout
- Parallel lane: vog-planning
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: implementation_plan/docs/52-virtual-desktop-orb-idl-gui.todo.md
- Conflict policy: Do not delete gap rows. Do not complete this task while the report is missing, no_go, or an untested repair handler exists. This command exits 75 while withheld.
- Acceptance: Status becomes completed only when the VOG coverage report says GO, passed, and clicked, and every body-free missing_handler is named in the watchdog test.

## VOG-R012 Refill the rendered census from the live DOM
- Status: completed
- Completion: lane_resume deterministic command exit 0 at 2026-10-19T05:04:21Z
- Priority: P0
- Track: census
- Depends on: VOG-011
- Goal id: VOG-G011-R
- Satisfies: VOG-012
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/rendered-control-census.json
- Deterministic command: node swissknife/scripts/run-rendered-census.mjs
- Validation: python3 swissknife/scripts/vog_rendered_census_requires_live_dom.py
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/rendered-control-census.json
- Conflict policy: Do not click tool buttons. Do not edit app source.
- Acceptance: Live DOM census, source_template false, clicked false, at least 45 apps, no template selectors.
