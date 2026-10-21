# Virtual Desktop ORB/IDL GUI Objective Heap (VOG)

Machine-ingestible planning state for `ipfs_accelerate_py.agent_supervisor`.
The executable projection is
`implementation_plan/docs/52-virtual-desktop-orb-idl-gui.todo.md` with task prefix
`## VOG-`.

Profile: `config/virtual_desktop_orb_idl_gui_supervisor.json`.
Lane inventory: `config/virtual_desktop_orb_idl_gui_lane_inventory.json`.
Runtime root: `data/agent_supervisor/virtual_desktop_orb_idl_gui/`.

This board does not edit
`implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md` or
`implementation_plan/docs/51-virtual-desktop-live-click.todo.md`.
Do not mark VDG-060 or VDL-020 complete. Do not retarget the running VDG watchdog.

## North star

Every SwissKnife virtual-desktop app, after its window HTML is in the document,
binds its controls. Each visible control is clicked once, photographed before
and after, and has one ORB/IDL outcome:

- `read_status`, `read_receipts`, `request_action`, `request_fallback`, or
  `request_prompt_steering` is invoked as MCP++ `POST /mcp/tools/call`, with
  the tool id, transport, correlation id, policy outcome, receipt CID, and
  event-DAG CID, or
- the control is `local-only`, `external-provider`, `deny`, or `unsupported`,
  and the click records zero `/mcp/tools/call` requests.

A private `client.get` or `client.post` to `/mcp/artifacts/` or `/mcp/dag/` is
not an ORB/IDL call. A source-template selector, a manifest count, and a PNG
with no click row are not execution evidence.

## Decision

Release decision stays **NO_GO** until
`swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-gui-coverage.json`
says `decision: GO`, `passed: true`, and `clicked: true`. The watchdog cannot
set `work_complete` or `completion_authority`. VOG-090 is the only task whose
command exits 75, and it depends on every other task.

## Goal tree

```text
VOG-G000  Every rendered control invokes its ORB/IDL method or has a zero-call proof
|-- VOG-G001  Program sealed and submodule sync receipt published
|-- VOG-G010  Live inventory
|   |-- VOG-G011  Rendered-control census
|   `-- VOG-G012  ORB/IDL method join
|-- VOG-G020  Shared harness
|   |-- VOG-G021  Listeners bind after render
|   |-- VOG-G022  Private /mcp routes move to /mcp/tools/call
|   `-- VOG-G023  Live-click decision is computed
|-- VOG-G030  Image-viewer pilot
|-- VOG-G040  Family proofs
|   |-- VOG-G041  Storage and media
|   |-- VOG-G042  Datasets, notes, models, vibecode, ai-chat
|   |-- VOG-G043  Accelerate, training, devices, neural apps
|   |-- VOG-G044  Network, chat, friends, navi
|   |-- VOG-G045  Control plane, idl-explorer, mcp-plus-plus, orb-auto-ui
|   `-- VOG-G046  Local-only and external-provider negatives
|-- VOG-G050  Coverage aggregate
|-- VOG-G070  Supervisor block becomes a dead lane the watchdog can see
`-- VOG-G090  Closeout
```

## VOG-G000 Every rendered control has an ORB/IDL outcome

- Status: active
- Parent:
- Priority: P0
- Track: virtual-desktop-orb-idl-gui
- Bundle: swissknife/virtual-desktop/orb-idl-gui/root
- Goal: Prove a GUI-originated MCP++ invocation or a zero-call disposition for every rendered control, with a before PNG and an after PNG.
- Evidence: VOGEV000ROOT
- Outputs: implementation_plan/docs/52-virtual-desktop-orb-idl-gui.objectives.md, implementation_plan/docs/52-virtual-desktop-orb-idl-gui.todo.md
- Validation: test -f implementation_plan/docs/52-virtual-desktop-orb-idl-gui.todo.md
- Acceptance: VOG-090 completes only after the VOG coverage report says decision GO, passed true, and clicked true.
- Gap task: The 2026-10-17 VDG report is no_go with executed_tool_count 0. The 2026-10-18 image-viewer pilot clicked the CID control, opened a dialog, and recorded zero /mcp/tools/call requests.

## VOG-G001 Program sealed and submodule sync receipt published

- Status: active
- Parent: VOG-G000
- Priority: P0
- Track: planning
- Bundle: swissknife/virtual-desktop/orb-idl-gui/planning
- Goal: Record the 2026-10-19 one-level fast-forward and seal this board without moving parent gitlinks or starting a second VDG watchdog.
- Evidence: VOGEV001SEAL
- Outputs: data/agent_supervisor/virtual_desktop_orb_idl_gui/submodule-sync.json, config/virtual_desktop_orb_idl_gui_supervisor.json, config/virtual_desktop_orb_idl_gui_lane_inventory.json
- Validation: python3 -m json.tool config/virtual_desktop_orb_idl_gui_supervisor.json
- Acceptance: Direct submodules were fetched with recurse off. Dirty trees were not pushed. Facebook wearables were not pushed.

## VOG-G010 Live inventory

- Status: pending
- Parent: VOG-G000
- Priority: P0
- Track: inventory
- Bundle: swissknife/virtual-desktop/orb-idl-gui/inventory
- Goal: Refresh the exact-name ledger, census controls from the live DOM, and join each control to one IDL method.
- Evidence: VOGEV010INVENTORY
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-control-matrix.json
- Validation: python3 swissknife/scripts/vog_orb_idl_matrix_requires_join.py
- Acceptance: Selectors that contain `${` or `escapeHTML` are gaps. Shell chrome is local-only. `openrouter` is external-provider.

## VOG-G011 Rendered-control census

- Status: pending
- Parent: VOG-G010
- Priority: P0
- Track: census
- Bundle: swissknife/virtual-desktop/orb-idl-gui/census
- Goal: Launch every manifest app and record the controls that exist after render.
- Evidence: VOGEV011CENSUS
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/rendered-control-census.json
- Validation: python3 swissknife/scripts/vog_rendered_census_requires_live_dom.py
- Acceptance: `source_template` is false and `clicked` is false. The census does not click tool buttons.

## VOG-G012 ORB/IDL method join

- Status: pending
- Parent: VOG-G010
- Priority: P0
- Track: join
- Bundle: swissknife/virtual-desktop/orb-idl-gui/join
- Goal: Give every rendered control one disposition and one IDL method.
- Evidence: VOGEV012JOIN
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-control-matrix.json
- Validation: python3 swissknife/scripts/vog_orb_idl_matrix_requires_join.py
- Acceptance: Invoke, confirm-then-invoke, and deny rows name an `mcp++` tool id and an IDL method other than `none`. Uncovered app-visible tools stay at count 0 only when each one has an originating control.

## VOG-G020 Shared harness

- Status: pending
- Parent: VOG-G000
- Priority: P0
- Track: harness
- Bundle: swissknife/virtual-desktop/orb-idl-gui/harness
- Goal: Bind listeners after render, send backend work through `/mcp/tools/call`, and compute the live-click decision from those observations.
- Evidence: VOGEV020HARNESS
- Outputs: swissknife/web/js/main-simple.js, swissknife/web/js/apps/real-artifact.js, swissknife/test/e2e/helpers/live-click-session.ts
- Validation: node swissknife/scripts/check-listener-after-render.cjs
- Acceptance: Family lanes do not edit these three files. A CID dialog receives the fixture CID before the click is judged done.

## VOG-G021 Listeners bind after render

- Status: pending
- Parent: VOG-G020
- Priority: P0
- Track: harness
- Bundle: swissknife/virtual-desktop/orb-idl-gui/listeners
- Goal: Call `setupEventListeners` or `mount` after `contentElement.innerHTML` for every `create*` path that inserts app HTML.
- Evidence: VOGEV021LISTEN
- Outputs: swissknife/web/js/main-simple.js
- Validation: node swissknife/scripts/check-listener-after-render.cjs
- Acceptance: The 2026-10-19 `origin/main` fix for file-manager and todo stays. The checker currently names 33 create functions that still return before binding.

## VOG-G022 Private MCP routes move to tools/call

- Status: pending
- Parent: VOG-G020
- Priority: P0
- Track: harness
- Bundle: swissknife/virtual-desktop/orb-idl-gui/routes
- Goal: Replace quoted `/mcp/artifacts/` and `/mcp/dag/` calls with `POST /mcp/tools/call`.
- Evidence: VOGEV022ROUTE
- Outputs: swissknife/web/js/apps/real-artifact.js
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/real-artifact.js
- Acceptance: `real-artifact.js` is the shared helper. App files that still quote a private route are family tasks, not this goal.

## VOG-G023 Live-click decision is computed

- Status: pending
- Parent: VOG-G020
- Priority: P0
- Track: harness
- Bundle: swissknife/virtual-desktop/orb-idl-gui/decision
- Goal: Stop hardcoding `decision: 'no_go'` after a passing click run.
- Evidence: VOGEV023DECISION
- Outputs: swissknife/test/e2e/helpers/live-click-session.ts
- Validation: node swissknife/scripts/check-live-click-decision.cjs
- Acceptance: Decision is `GO` only when every visible row was clicked, every invoke or deny row has a complete `/mcp/tools/call` observation, and every zero-call disposition recorded zero calls. A PNG review cannot set GO.

## VOG-G030 Image-viewer pilot

- Status: pending
- Parent: VOG-G000
- Priority: P0
- Track: pilot
- Bundle: swissknife/virtual-desktop/orb-idl-gui/pilot
- Goal: Make Retrieve CID call `mcp++:ipfs_kit_py/artifacts/get` through `/mcp/tools/call`, then click the app and store the PNG pair.
- Evidence: VOGEV030PILOT
- Outputs: swissknife/web/js/apps/image-viewer.js, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json
- Validation: node swissknife/scripts/check-app-mcp-route.cjs swissknife/web/js/apps/image-viewer.js
- Acceptance: The click submits a fixture CID. A dialog with `mcp_call_count` 0 is not a pass. Family browser runs wait for this report.

## VOG-G040 Family proofs

- Status: pending
- Parent: VOG-G000
- Priority: P0
- Track: families
- Bundle: swissknife/virtual-desktop/orb-idl-gui/families
- Goal: Click the six family targets after their private routes are gone.
- Evidence: VOGEV040FAMILIES
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json family
- Acceptance: One browser target runs at a time. `ai-chat` and `orb-auto-ui` stay on their existing families. An alias is not a second tool list.

## VOG-G041 Storage and media

- Status: pending
- Parent: VOG-G040
- Priority: P1
- Track: vog-storage
- Bundle: swissknife/virtual-desktop/orb-idl-gui/storage
- Goal: ipfs-explorer, media-player, and peertube quote no private `/mcp/` route, then the storage target is clicked. image-viewer is the pilot's file.
- Evidence: VOGEV041STORAGE
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json family
- Acceptance: file-manager, cinema, and the image-viewer pilot report stay green. Shell chrome records zero MCP++ calls.

## VOG-G042 Datasets, notes, models, vibecode, ai-chat

- Status: pending
- Parent: VOG-G040
- Priority: P1
- Track: vog-datasets
- Bundle: swissknife/virtual-desktop/orb-idl-gui/datasets
- Goal: notes and vibecode use `/mcp/tools/call`, then the datasets target is clicked.
- Evidence: VOGEV042DATASETS
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/datasets.json
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/datasets.json family
- Acceptance: Dataset publish reads `dataset_id` from `dataset_data` the way `start-ipfs-datasets-mcp-compat.cjs` does on origin/main `3c2194dd`.

## VOG-G043 Accelerate, training, devices, neural apps

- Status: pending
- Parent: VOG-G040
- Priority: P1
- Track: vog-accelerate
- Bundle: swissknife/virtual-desktop/orb-idl-gui/accelerate
- Goal: neural-network-designer uses `/mcp/tools/call`, then the accelerate target is clicked.
- Evidence: VOGEV043ACCEL
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/accelerate.json
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/accelerate.json family
- Acceptance: huggingface stays on this family. Training and device controls that only read status use `read_status`.

## VOG-G044 Network, chat, friends, navi

- Status: pending
- Parent: VOG-G040
- Priority: P1
- Track: vog-network
- Bundle: swissknife/virtual-desktop/orb-idl-gui/network
- Goal: friends-list, p2p-chat, and p2p-chat-unified use `/mcp/tools/call`, then the network target is clicked.
- Evidence: VOGEV044NETWORK
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/network.json
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/network.json family
- Acceptance: Chat send is confirm-then-invoke and stays dry-run unless the policy outcome is an explicit allow for a read.

## VOG-G045 Control plane

- Status: pending
- Parent: VOG-G040
- Priority: P1
- Track: vog-control
- Bundle: swissknife/virtual-desktop/orb-idl-gui/control
- Goal: mcp-plus-plus-explorer uses `/mcp/tools/call`, then the control target is clicked.
- Evidence: VOGEV045CONTROL
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/control.json
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/control.json family
- Acceptance: idl-explorer shows the four desktop IDL methods. agent-supervisor `request_prompt_steering` stays behind confirmation. orb-auto-ui stays on this family.

## VOG-G046 Local-only and external-provider negatives

- Status: pending
- Parent: VOG-G040
- Priority: P1
- Track: vog-local
- Bundle: swissknife/virtual-desktop/orb-idl-gui/local
- Goal: calendar and clock stop quoting private artifact routes, then the local target is clicked with zero `/mcp/tools/call` requests.
- Evidence: VOGEV046LOCAL
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/local.json
- Validation: python3 swissknife/scripts/vog_live_click_requires_observation.py swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/local.json local
- Acceptance: openrouter stays external-provider. Calculator, terminal, and clock chrome do not invoke a tool.

## VOG-G050 Coverage aggregate

- Status: pending
- Parent: VOG-G000
- Priority: P0
- Track: gate
- Bundle: swissknife/virtual-desktop/orb-idl-gui/gate
- Goal: Write one coverage file from the seven live-click reports.
- Evidence: VOGEV050GATE
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-gui-coverage.json
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/vog/orb-idl-gui-coverage.json
- Acceptance: Partial family greens do not flip the decision. This file is not the VDG coverage file.

## VOG-G070 Supervisor block becomes a dead lane

- Status: pending
- Parent: VOG-G000
- Priority: P0
- Track: watchdog
- Bundle: accelerate/agent-supervisor/rescue
- Goal: A lane that can run no safe command exits while its status stays blocked, so the watchdog sees a dead lane with pending work.
- Evidence: VOGEV070WATCH
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/lane_resume.py, external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py
- Validation: python3 external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/run_repo_pytest.py -q external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py -k live_blocked_resume_exits --tb=line -p no:cacheprovider
- Acceptance: `gate_withheld` keeps looping. Exit 75 stays the closeout signal. A second observation of the same dead-lane signature writes a body-free repair packet and does not spawn again. `work_complete` stays false.

## VOG-G090 Closeout

- Status: pending
- Parent: VOG-G000
- Priority: P0
- Track: planning
- Bundle: swissknife/virtual-desktop/orb-idl-gui/closeout
- Goal: Complete only when the coverage report says GO and every body-free repair handler is named in the watchdog test.
- Evidence: VOGEV090CLOSE
- Outputs: implementation_plan/docs/52-virtual-desktop-orb-idl-gui.todo.md
- Validation: python3 swissknife/scripts/vog_closeout_requires_go.py
- Acceptance: A missing or no_go report exits 75 and leaves this task pending. The watchdog does not mark it complete.
