# Virtual Desktop Live Click Tasks (VDL)

Executable projection of `implementation_plan/docs/51-virtual-desktop-live-click.objectives.md`.
Task prefix `## VDL-`. Only lane `vdl-planning` edits this file.
Do not edit `implementation_plan/docs/50-virtual-desktop-gui-mcp.todo.md`.

Lane commands use `node` or `python3` because those argv0 names are allowlisted.
`npm run evidence:live-click -- <target>` from the swissknife directory calls the same wrapper.

## VDL-001 Seal the live-click program

- Status: pending
- Priority: P0
- Track: planning
- Depends on:
- Goal id: VDL-G001
- Outputs: config/virtual_desktop_live_click_supervisor.json
- Deterministic command: python3 -m json.tool config/virtual_desktop_live_click_supervisor.json
- Validation: test -f config/virtual_desktop_live_click_lane_inventory.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/planning
- Parallel lane: vdl-planning
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: config/virtual_desktop_live_click_supervisor.json, config/virtual_desktop_live_click_lane_inventory.json
- Conflict policy: Do not start the VDL watchdog in the same step as writing this board. Do not start a second VDG watchdog. Do not retarget swissknife.
- Acceptance: Profile task prefix is ## VDL- and root goal is VDL-G000. Watchdog cannot set work_complete.

## VDL-010 Freeze the live-click session

- Status: pending
- Priority: P0
- Track: harness
- Depends on: VDL-001
- Goal id: VDL-G011
- Outputs: swissknife/test/e2e/helpers/live-click-session.ts
- Deterministic command: node swissknife/scripts/check-live-click-session.cjs
- Validation: test -f swissknife/test/e2e/helpers/live-click-session.ts
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/harness
- Parallel lane: vdl-harness
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/test/e2e/helpers/live-click-session.ts, swissknife/test/e2e/helpers/live-click-png.cjs
- Conflict policy: Launch with launchApp and no gatewayOnly flag. One locator.click per control. Do not edit app source or the gateway panel.
- Acceptance: The helper records the app-window PNG pair, page errors, and /mcp/tools/call fields.

## VDL-011 Add the owned-port Playwright config

- Status: pending
- Priority: P0
- Track: harness
- Depends on: VDL-010
- Goal id: VDL-G012
- Outputs: swissknife/build-tools/configs/playwright.live-click.config.ts
- Deterministic command: node swissknife/scripts/check-live-click-config.cjs
- Validation: test -f swissknife/build-tools/configs/playwright.live-click.config.ts
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/harness
- Parallel lane: vdl-harness
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/build-tools/configs/playwright.live-click.config.ts, swissknife/test/e2e/virtual-desktop-live-click.spec.ts, swissknife/scripts/run-live-click.mjs
- Conflict policy: reuseExistingServer stays false. workers stays 1. fullyParallel stays false. channel stays chrome. Each run leases a port.
- Acceptance: npm script evidence:live-click and node swissknife/scripts/run-live-click.mjs run one target on an owned port.

## VDL-020 Click the image-viewer pilot

- Status: pending
- Priority: P0
- Track: pilot
- Depends on: VDL-011
- Goal id: VDL-G020
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs pilot
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/pilot
- Parallel lane: vdl-pilot
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/pilot/image-viewer.json
- Conflict policy: Do not rewrite the control-tool matrix. A live tool button the matrix called unsupported fails the command. Not-visible controls fail the command. Empty or single-color PNGs fail the command.
- Acceptance: The command exits 0 only when every image-viewer control row has clicked true.

## VDL-031 Click storage and media

- Status: pending
- Priority: P0
- Track: storage
- Depends on: VDL-020
- Goal id: VDL-G031
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs storage
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/storage
- Parallel lane: vdl-storage
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/storage.json
- Conflict policy: Apps are file-manager, ipfs-explorer, image-viewer, media-player, cinema, and peertube. Do not edit the shared helper or app source. Own the port and the storage screenshot directory.
- Acceptance: The command exits 0 only when the storage report has clicked true.

## VDL-032 Click datasets, notes, models, and chat

- Status: pending
- Priority: P0
- Track: datasets
- Depends on: VDL-020
- Goal id: VDL-G032
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/datasets.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs datasets
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/datasets.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/datasets
- Parallel lane: vdl-datasets
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/datasets.json
- Conflict policy: Apps are notes, datasets-browser, model-browser, vibecode, and ai-chat. The report says the VDG objective text did not name ai-chat. Apps with no JS file are still launched.
- Acceptance: The command exits 0 only when the datasets report has clicked true.

## VDL-033 Click accelerate and neural apps

- Status: pending
- Priority: P0
- Track: accelerate
- Depends on: VDL-020
- Goal id: VDL-G033
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/accelerate.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs accelerate
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/accelerate.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/accelerate
- Parallel lane: vdl-accelerate
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/accelerate.json
- Conflict policy: Apps are device-manager, huggingface, training-manager, accelerate-panel, neural-network-designer, and neural-photoshop. Mutating tools stay dry-run.
- Acceptance: The command exits 0 only when the accelerate report has clicked true.

## VDL-034 Click network apps

- Status: pending
- Priority: P0
- Track: network
- Depends on: VDL-020
- Goal id: VDL-G034
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/network.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs network
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/network.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/network
- Parallel lane: vdl-network
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/network.json
- Conflict policy: Apps are p2p-network, p2p-chat, p2p-chat-unified, friends-list, and navi. An alias is a second window, not a second tool list.
- Acceptance: The command exits 0 only when the network report has clicked true.

## VDL-035 Click the control plane

- Status: pending
- Priority: P0
- Track: control
- Depends on: VDL-020
- Goal id: VDL-G035
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/control.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs control
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/control.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/control
- Parallel lane: vdl-control
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/control.json
- Conflict policy: Apps are mcp-control, mcp-plus-plus, idl-explorer, agent-supervisor, system-monitor, github, api-keys, and orb-auto-ui. The report says the VDG objective text did not name orb-auto-ui. MCP Control registry reads may run. Every other mutating tool stays dry-run. Ordinary windows must not call supervisor_only or desktop_mobile_only tools.
- Acceptance: The command exits 0 only when the control report has clicked true.

## VDL-036 Click local-only and external-provider apps

- Status: pending
- Priority: P0
- Track: local
- Depends on: VDL-020
- Goal id: VDL-G036
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/local.json
- Deterministic command: node swissknife/scripts/run-live-click.mjs local
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/local.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/local
- Parallel lane: vdl-local
- Resource class: cpu-browser
- Implementation timeout seconds: 7200
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-clicks/local.json
- Conflict policy: Apps are calculator, clock, terminal, glasses-preview, settings, todo, calendar, cron, task-manager, music-studio, music-studio-unified, strudel, strudel-ai-daw, oauth-login, and openrouter. Local-only and external-provider clicks produce zero /mcp/tools/call requests. Shell chrome is clicked and is local-only.
- Acceptance: The command exits 0 only when the local report has clicked true.

## VDL-040 Aggregate live-click coverage

- Status: pending
- Priority: P0
- Track: gate
- Depends on: VDL-031, VDL-032, VDL-033, VDL-034, VDL-035, VDL-036
- Goal id: VDL-G040
- Outputs: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-click-coverage.json
- Deterministic command: node swissknife/scripts/build-live-click-coverage.cjs
- Validation: test -f swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-click-coverage.json
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/gate
- Parallel lane: vdl-gate
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/test-results/virtual-desktop-ipfs-mcp-orb/live-click-coverage.json
- Conflict policy: decision is GO only when every family report has clicked true, every invoke and deny row has receipt and event-DAG CIDs, local-only and external-provider rows have zero MCP++ calls, and no ordinary window called a supervisor-only tool. Otherwise decision is no_go and passed is false.
- Acceptance: Partial family greens do not flip the decision. visual_review cannot grant GO.

## VDL-060 Close out only on GO

- Status: pending
- Priority: P0
- Track: planning
- Depends on: VDL-040
- Goal id: VDL-G060
- Outputs: swissknife/scripts/vdl_closeout_requires_go.py
- Deterministic command: python3 swissknife/scripts/vdl_closeout_requires_go.py
- Validation: test -f swissknife/scripts/vdl_closeout_requires_go.py
- Board namespace: virtual-desktop-live-click-v1
- Bundle: swissknife/virtual-desktop/live-click/closeout
- Parallel lane: vdl-planning
- Resource class: cpu-small
- Implementation timeout seconds: 1800
- Predicted files: swissknife/scripts/vdl_closeout_requires_go.py
- Conflict policy: Do not complete this task while live-click-coverage.json is missing or NO_GO. Do not edit the VDG todo. Do not set work_complete or completion_authority.
- Acceptance: The command exits 0 only when decision is GO and passed is true and clicked is true. Until then it exits 75 and this task stays pending.
