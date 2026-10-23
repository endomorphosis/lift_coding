# Virtual Desktop GUI to MCP++ Objective Heap (VDG)

Machine-ingestible planning state for `ipfs_accelerate_py.agent_supervisor`.
The executable projection is
`implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md` with task prefix
`## VDG-`.

Profile: `config/virtual_desktop_gui_mcp_supervisor.json`.
Lane inventory: `config/virtual_desktop_gui_mcp_lane_inventory.json`.
Runtime root: `data/agent_supervisor/virtual_desktop_gui_mcp/`.

## North star

Every interactive control in the SwissKnife virtual desktop has one MCP++
disposition, and every app-visible backend tool is invocable from the GUI that
owns it. Screenshot smoke, ORB/IDL descriptors, and manifest counts are not
execution evidence. An invocation counts only when the app window originates it
and the connector records the exact tool name, correlation id, policy outcome,
receipt CID, and event-DAG CID.

## Decision

Release decision stays **NO_GO** until VDG-040 writes
`swissknife/test-results/virtual-desktop-ipfs-mcp-orb/gui-mcp-coverage.json`
with `decision: GO`. The watchdog cannot set `work_complete`.

## Goal tree

```text
VDG-G000  Every desktop control has an MCP++ disposition
|-- VDG-G001  Program sealed and submodule sync receipt published
|-- VDG-G010  Fresh control and tool inventory
|   |-- VDG-G011  Native control census per app
|   `-- VDG-G012  App-visible tool census and gap ledger refresh
|-- VDG-G020  Shared invocation harness frozen
|-- VDG-G030  Family proofs
|   |-- VDG-G031  Storage and media
|   |-- VDG-G032  Datasets, notes, models, vibecode
|   |-- VDG-G033  Accelerate, training, devices, neural apps
|   |-- VDG-G034  Network, chat, friends, navi
|   |-- VDG-G035  Control plane, supervisor, github, keys
|   `-- VDG-G036  Local-only and external-provider negatives
|-- VDG-G040  Receipt, event-DAG, and policy gate
|-- VDG-G050  Supervisor self-heal for block and stall
`-- VDG-G060  Closeout
```

## VDG-G000 Every desktop control has an MCP++ disposition

- Status: active
- Parent:
- Priority: P0
- Track: virtual-desktop-gui-mcp
- Bundle: swissknife/virtual-desktop/gui-mcp/root
- Goal: Prove GUI-originated MCP++ invocation or an explicit non-invoke disposition for every interactive control, and cover every app-visible tool.
- Evidence: VDGEV000ROOT
- Outputs: implementation_plan/docs/50-virtual-desktop-gui-mcp.objectives.md, implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md
- Validation: test -f implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md
- Acceptance: VDG-060 completes only after VDG-040 reports decision GO.
- Gap task: Execute VDG-010 onward. Do not treat the 2026-07-22 gap ledger as current.

## VDG-G001 Program sealed and submodule sync receipt published

- Status: active
- Parent: VDG-G000
- Priority: P0
- Track: planning
- Bundle: swissknife/virtual-desktop/gui-mcp/planning
- Goal: Publish the sync receipt and the sealed board without moving parent gitlinks or force-pushing.
- Evidence: VDGEV001SEAL
- Outputs: data/agent_supervisor/virtual_desktop_gui_mcp/submodule-sync.json, config/virtual_desktop_gui_mcp_supervisor.json, config/virtual_desktop_gui_mcp_lane_inventory.json
- Validation: python3 -m json.tool config/virtual_desktop_gui_mcp_supervisor.json >/dev/null && python3 -m json.tool data/agent_supervisor/virtual_desktop_gui_mcp/submodule-sync.json >/dev/null
- Acceptance: Receipt has an action for every direct submodule, no force action, and Facebook rows are not pushes.

## VDG-G010 Fresh control and tool inventory

- Status: pending
- Parent: VDG-G000
- Priority: P0
- Track: inventory
- Bundle: swissknife/virtual-desktop/gui-mcp/inventory
- Goal: Remeasure exact-name execution and enumerate native controls separately from the 79-button gateway panel.
- Evidence: VDGEV010INVENTORY
- Outputs: swissknife/docs/all-app-live-binding-gap-ledger.md, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/control-census.json, swissknife/test-results/virtual-desktop-ipfs-mcp-orb/control-tool-matrix.json
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/control-tool-matrix.json
- Acceptance: Every manifest app is launched. Unclassified controls and uncovered app-visible tools are named gaps.

## VDG-G011 Native control census per app

- Status: pending
- Parent: VDG-G010
- Priority: P0
- Track: census
- Bundle: swissknife/virtual-desktop/gui-mcp/census
- Goal: Record each interactive element without clicking tool buttons. Shell chrome is local-only.
- Evidence: VDGEV011CENSUS
- Outputs: swissknife/test/e2e/virtual-desktop-control-census.spec.ts
- Validation: test -f swissknife/test/e2e/virtual-desktop-control-census.spec.ts
- Acceptance: Census rows include app id, launch id, selector, role, accessible name, and data attributes.

## VDG-G012 App-visible tool census and gap ledger refresh

- Status: pending
- Parent: VDG-G010
- Priority: P0
- Track: inventory
- Bundle: swissknife/virtual-desktop/gui-mcp/inventory
- Goal: Join the census to the executable backend contract. One disposition per control. One or more originating controls per app-visible tool.
- Evidence: VDGEV012JOIN
- Outputs: swissknife/test/mcp-plus-plus/virtual-desktop-control-tool-matrix.test.ts
- Validation: test -f swissknife/test/mcp-plus-plus/virtual-desktop-control-tool-matrix.test.ts
- Acceptance: supervisor_only and desktop_mobile_only tools are negative obligations, not ordinary app invokes.

## VDG-G020 Shared invocation harness frozen

- Status: pending
- Parent: VDG-G000
- Priority: P0
- Track: harness
- Bundle: swissknife/virtual-desktop/gui-mcp/harness
- Goal: Make native controls and gateway-panel buttons emit the same swissknife:live-gateway-result observation.
- Evidence: VDGEV020HARNESS
- Outputs: swissknife/src/services/mcp/virtual-desktop-live-gateway.ts, swissknife/web/src/live-tool-gateway-panel.ts, swissknife/test/e2e/helpers/mcp-invocation-observer.ts
- Validation: test -f swissknife/test/e2e/helpers/mcp-invocation-observer.ts
- Acceptance: Family lanes do not edit the harness after this goal's task completes.

## VDG-G030 Family proofs

- Status: pending
- Parent: VDG-G000
- Priority: P0
- Track: families
- Bundle: swissknife/virtual-desktop/gui-mcp/families
- Goal: Six disjoint app families prove invoke, deny, error recovery, and local-only negatives on the real desktop.
- Evidence: VDGEV030FAMILIES
- Outputs: swissknife/test/e2e/families/
- Validation: test -d swissknife/test/e2e/families
- Acceptance: Gateway-panel-only clicks do not satisfy a native control. Mutating tools stay dry-run unless already reviewed as safe reads.

## VDG-G031 Storage and media

- Status: pending
- Parent: VDG-G030
- Priority: P1
- Track: vdg-storage
- Bundle: swissknife/virtual-desktop/gui-mcp/storage
- Goal: file-manager, ipfs-explorer, image-viewer, media-player, cinema, peertube.
- Evidence: VDGEV031STORAGE
- Outputs: swissknife/test/e2e/families/storage-media-mcp-invoke.spec.ts
- Validation: test -f swissknife/test/e2e/families/storage-media-mcp-invoke.spec.ts
- Acceptance: Each app-visible tool in these apps has an originating invocation on each declared transport.

## VDG-G032 Datasets, notes, models, vibecode

- Status: pending
- Parent: VDG-G030
- Priority: P1
- Track: vdg-datasets
- Bundle: swissknife/virtual-desktop/gui-mcp/datasets
- Goal: notes, datasets-browser, model-browser, vibecode.
- Evidence: VDGEV032DATASETS
- Outputs: swissknife/test/e2e/families/datasets-mcp-invoke.spec.ts
- Validation: test -f swissknife/test/e2e/families/datasets-mcp-invoke.spec.ts
- Acceptance: Same invocation rule as VDG-G031.

## VDG-G033 Accelerate, training, devices, neural apps

- Status: pending
- Parent: VDG-G030
- Priority: P1
- Track: vdg-accelerate
- Bundle: swissknife/virtual-desktop/gui-mcp/accelerate
- Goal: device-manager, huggingface, training-manager, accelerate-panel, neural-network-designer, neural-photoshop.
- Evidence: VDGEV033ACCEL
- Outputs: swissknife/test/e2e/families/accelerate-mcp-invoke.spec.ts
- Validation: test -f swissknife/test/e2e/families/accelerate-mcp-invoke.spec.ts
- Acceptance: Same invocation rule as VDG-G031.

## VDG-G034 Network, chat, friends, navi

- Status: pending
- Parent: VDG-G030
- Priority: P1
- Track: vdg-network
- Bundle: swissknife/virtual-desktop/gui-mcp/network
- Goal: p2p-network, p2p-chat, p2p-chat-unified, friends-list, navi.
- Evidence: VDGEV034NET
- Outputs: swissknife/test/e2e/families/network-mcp-invoke.spec.ts
- Validation: test -f swissknife/test/e2e/families/network-mcp-invoke.spec.ts
- Acceptance: Same invocation rule as VDG-G031.

## VDG-G035 Control plane, supervisor, github, keys

- Status: pending
- Parent: VDG-G030
- Priority: P1
- Track: vdg-control
- Bundle: swissknife/virtual-desktop/gui-mcp/control
- Goal: mcp-control, mcp-plus-plus, idl-explorer, agent-supervisor, system-monitor, github, api-keys.
- Evidence: VDGEV035CONTROL
- Outputs: swissknife/test/e2e/families/control-plane-mcp-invoke.spec.ts
- Validation: test -f swissknife/test/e2e/families/control-plane-mcp-invoke.spec.ts
- Acceptance: Confirmation-gated and supervisor-only tools are negatives on ordinary clicks. MCP Control safe reads may be real.

## VDG-G036 Local-only and external-provider negatives

- Status: pending
- Parent: VDG-G030
- Priority: P1
- Track: vdg-local
- Bundle: swissknife/virtual-desktop/gui-mcp/local
- Goal: calculator, clock, terminal, glasses-preview, settings, todo, calendar, cron, task-manager, music-studio, music-studio-unified, strudel, strudel-ai-daw, oauth-login, openrouter.
- Evidence: VDGEV036LOCAL
- Outputs: swissknife/test/e2e/families/local-negative-mcp.spec.ts
- Validation: test -f swissknife/test/e2e/families/local-negative-mcp.spec.ts
- Acceptance: local-only interactions produce zero /mcp/tools/call requests.

## VDG-G040 Receipt, event-DAG, and policy gate

- Status: pending
- Parent: VDG-G000
- Priority: P0
- Track: gate
- Bundle: swissknife/virtual-desktop/gui-mcp/gate
- Goal: Aggregate family evidence into one GO/NO_GO report.
- Evidence: VDGEV040GATE
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/gui-mcp-coverage.json
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/gui-mcp-coverage.json
- Acceptance: decision is GO only when every rule in VDG-040 of the todo holds.

## VDG-G050 Supervisor self-heal for block and stall

- Status: active
- Parent: VDG-G000
- Priority: P0
- Track: vdg-watchdog
- Bundle: accelerate/agent-supervisor/rescue
- Goal: A live PID with a fresh heartbeat, a quiet log, and no task transition for 900 seconds is a progress stall. The second quarantine of the same incident writes a body-free repair packet and does not loop restarts. completion_authority stays false.
- Evidence: VDGEV050WATCH
- Outputs: external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/rescue/supervisor_watchdog.py
- Validation: PYTHONPATH=external/ipfs_accelerate python3 -m pytest -q external/ipfs_accelerate/test/api/test_agent_supervisor_supervisor_watchdog.py -k 'progress_stall or second_quarantine'
- Acceptance: Tests show progress_stalled without work_complete, and the second quarantine packet is body-free.
- Gap task: VDG-051 still has to rearm locally validated blocked rows through the existing fleet heal recipe.

## VDG-G060 Closeout

- Status: pending
- Parent: VDG-G000
- Priority: P0
- Track: planning
- Bundle: swissknife/virtual-desktop/gui-mcp/closeout
- Goal: Close the program only when VDG-040 says GO.
- Evidence: VDGEV060CLOSE
- Outputs: implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md
- Validation: python3 -c 'import json,pathlib; p=pathlib.Path("swissknife/test-results/virtual-desktop-ipfs-mcp-orb/gui-mcp-coverage.json"); assert json.loads(p.read_text())["decision"]=="GO"'
- Acceptance: Gaps are not deleted to force a pass.
