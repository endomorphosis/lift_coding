# Virtual Desktop Live Click Objective Heap (VDL)

Machine-ingestible planning state for `ipfs_accelerate_py.agent_supervisor`.
The executable projection is
`implementation_plan/docs/51-virtual-desktop-live-click.todo.md` with task prefix
`## VDL-`.

Profile: `config/virtual_desktop_live_click_supervisor.json`.
Lane inventory: `config/virtual_desktop_live_click_lane_inventory.json`.
Runtime root: `data/agent_supervisor/virtual_desktop_live_click/`.

This board is separate from `implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md`.
Do not add VDL tasks to that todo. Do not mark VDG-060 complete. Do not change
`swissknife/test-results/virtual-desktop-ipfs-mcp-orb/gui-mcp-coverage.json`.

## North star

Every visible interactive control in every SwissKnife virtual-desktop app is
clicked with one Playwright `locator.click()`, photographed before and after,
and tied to one MCP++ outcome. A source census, a disposition matrix, a
fixture page, and a screenshot with no click row are not execution evidence.

## Decision

Release decision stays **NO_GO** until
`swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-click-coverage.json`
says `decision: GO` and `clicked: true`. The watchdog cannot set
`work_complete` or `completion_authority`. A `visual_review` note on a PNG is
proposal-only and cannot grant GO.

## Goal tree

```text
VDL-G000  Every visible control has been clicked, photographed, and given one MCP++ outcome
|-- VDL-G001  Program sealed
|-- VDL-G010  Click harness frozen
|   |-- VDL-G011  Shared live-click session
|   `-- VDL-G012  Owned-port Playwright config
|-- VDL-G020  Image-viewer pilot
|-- VDL-G030  Family click lanes
|   |-- VDL-G031  Storage and media
|   |-- VDL-G032  Datasets, notes, models, vibecode, ai-chat
|   |-- VDL-G033  Accelerate, training, devices, neural apps
|   |-- VDL-G034  Network, chat, friends, navi
|   |-- VDL-G035  Control plane, supervisor, github, keys, orb-auto-ui
|   `-- VDL-G036  Local-only and external-provider negatives
|-- VDL-G040  Live click coverage aggregate
`-- VDL-G060  Closeout
```

## VDL-G000 Every visible control has been clicked

- Status: active
- Parent:
- Priority: P0
- Track: virtual-desktop-live-click
- Bundle: swissknife/virtual-desktop/live-click/root
- Goal: Click each visible control, store a before PNG and an after PNG of the app window, and record the MCP++ observation or the zero-call proof.
- Evidence: VDLEV000ROOT
- Outputs: implementation_plan/docs/51-virtual-desktop-live-click.objectives.md, implementation_plan/docs/51-virtual-desktop-live-click.todo.md
- Validation: test -f implementation_plan/docs/51-virtual-desktop-live-click.todo.md
- Acceptance: VDL-060 completes only after the live-click coverage report says decision GO and clicked true.
- Gap task: The VDG matrix has clicked false. Do not cite it as a click.

## VDL-G001 Program sealed

- Status: active
- Parent: VDL-G000
- Priority: P0
- Track: planning
- Bundle: swissknife/virtual-desktop/live-click/planning
- Goal: Publish this profile and lane inventory without starting a second VDG watchdog and without retargeting swissknife off agent/ui-ux-ir.
- Evidence: VDLEV001SEAL
- Outputs: config/virtual_desktop_live_click_supervisor.json, config/virtual_desktop_live_click_lane_inventory.json
- Validation: test -f config/virtual_desktop_live_click_supervisor.json
- Acceptance: Only vdl-planning edits the objective and the todo. Workers do not push.

## VDL-G010 Click harness frozen

- Status: pending
- Parent: VDL-G000
- Priority: P0
- Track: harness
- Bundle: swissknife/virtual-desktop/live-click/harness
- Goal: Launch one app with no gatewayOnly flag, click one control, and record screenshots plus /mcp/tools/call.
- Evidence: VDLEV010HARNESS
- Outputs: swissknife/test/e2e/helpers/live-click-session.ts, swissknife/build-tools/configs/playwright.live-click.config.ts
- Validation: test -f swissknife/test/e2e/helpers/live-click-session.ts
- Acceptance: evaluateAll batch clicks do not count. Family lanes do not edit the helper, the gateway panel, or app source to make a click pass.

## VDL-G020 Image-viewer pilot

- Status: pending
- Parent: VDL-G000
- Priority: P0
- Track: pilot
- Bundle: swissknife/virtual-desktop/live-click/pilot
- Goal: Click image-viewer, including the gateway binding mcp++:ipfs_kit_py/artifacts/get, native controls, and shell chrome.
- Evidence: VDLEV020PILOT
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json
- Acceptance: Every image-viewer control row has clicked true before any family lane starts. A live tool button the matrix called unsupported fails closed.

## VDL-G030 Family click lanes

- Status: pending
- Parent: VDL-G000
- Priority: P0
- Track: families
- Bundle: swissknife/virtual-desktop/live-click/families
- Goal: Click the six family app sets after the pilot report is green.
- Evidence: VDLEV030FAMILIES
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Acceptance: ai-chat and orb-auto-ui stay on their families and the report says the VDG objective text did not name them. An empty window is a failed visual row. An alias is a second window, not a second tool list.

## VDL-G040 Live click coverage aggregate

- Status: pending
- Parent: VDL-G000
- Priority: P0
- Track: gate
- Bundle: swissknife/virtual-desktop/live-click/gate
- Goal: Write live-click-coverage.json. GO only when every launch was clicked and the MCP++ rules hold.
- Evidence: VDLEV040GATE
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-click-coverage.json
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-click-coverage.json
- Acceptance: Partial family greens do not flip the decision. Screenshot smoke is not execution evidence.

## VDL-G060 Closeout

- Status: pending
- Parent: VDL-G000
- Priority: P0
- Track: planning
- Bundle: swissknife/virtual-desktop/live-click/closeout
- Goal: Exit 0 only when the aggregate says GO, passed true, and clicked true. Until then exit 75 and leave the task pending.
- Evidence: VDLEV060CLOSE
- Outputs: swissknife/scripts/vdl_closeout_requires_go.py
- Validation: test -f swissknife/scripts/vdl_closeout_requires_go.py
- Acceptance: The lane keeps checking. Do not complete this task while the report is missing or NO_GO.
