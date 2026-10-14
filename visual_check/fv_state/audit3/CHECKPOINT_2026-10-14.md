# Audit3 — GUI interaction-coverage audit checkpoint (2026-10-14)

Status: IN PROGRESS. Inventory + static trace complete for all 45 apps; supervisor
deep-dive complete (static + code-level); fixes designed, NOT yet applied; live
verification NOT yet run. All changes so far uncommitted (only audit3 evidence dir).

## Evidence files (audit3/)
- inventory-raw.json — per-app control inventory (buttons/inputs/selects/handlers,
  descriptor invokes, external fetches, canned-receipt counts) for all 45 apps +
  6 generated surfaces. Scanner: scan_inventory.mjs (same dir).
- This checkpoint.

## Key files read in full
- swissknife/web/js/core/mcp-plus-plus-desktop-client.js (createSupervisorGateway:
  maps 9 Profile-G reads + supervisor.health.read + 6 Profile-G writes; EVERYTHING
  else → typed capability_unavailable)
- swissknife/web/js/apps/agent-supervisor.js (2,085 lines)
- swissknife/web/js/main-simple.js (3,152 lines) — gateway panel mounts per app
  (lines ~613/631/640); generated surfaces: createDatasetsBrowserSurface (1832),
  createORBAutoUISurface (2001), createGlassesPreviewSurface (2188),
  createIDLExplorerSurface (2357), createAcceleratePanelSurface (2518),
  createAgentSupervisorApp (2650). NO global [data-action] delegated handler.
- swissknife/src/services/mcp/agent-supervisor-console-gateway.ts (TS owner design:
  accelerate = state authority, datasets = search authority, kit = evidence authority)
- Adapters: swissknife/scripts/mcp-plus-plus-ipfs-kit-adapter.mjs (has REAL artifact
  routes POST /mcp/artifacts/put, GET /mcp/artifacts/<cid>, DAG routes),
  scripts/all-tools-evidence-lib.cjs (accelerate compat server has mcp++/dag/history
  backed by a real EventDag; NO prompt_steering/task_control routes anywhere in
  ipfs_accelerate_py/mcp_server)

## Supervisor capability trace (console → browser gateway → backend)
EXECUTES live (Profile-G mapped): health.read, queue.read, goals.read, subgoals.read,
  receipts.read (via Profile-G reads).
UNMAPPED → typed capability_unavailable (verified: no genuine backend feature exists):
  taskboard.links.read (no impl in ipfs_datasets_py), run-history.search (none),
  policy.assist (none), semantic-goal.assist (none),
  prompt-steering CONFIRMED submit (facade Supervisor.steer exists in
  ipfs_accelerate_py/agent_supervisor/entrypoints/facade.py but NO MCP adapter route
  serves it — genuine backend gap, do NOT simulate),
  dispatch, receipts.persist/retrieve/event-dag.checkpoint — BUT these three ARE
  fixable: kit adapter artifact/DAG routes are genuine (see fix c).
  logs.read — fixable: accelerate adapter mcp++/dag/history is a genuine
  mediated-state-service log (see fix d).

## Gaps found (new R-entries to write into BROKEN_CONTRACT_MAP.md)
- R-a console truthfulness leak: readLiveSnapshot uses listDataOr(result, SAMPLE_*)
  per capability → in LIVE mode the 5 unmapped capabilities' panes render SAMPLE
  fixtures as if live. Fix: live mode → empty lists; SAMPLE only in full-fallback mode.
- R-b P11 regression: steering dry-run previously used localPromptSteeringResult;
  post-G3 gateway install it errors capability_unavailable. Fix: in invokeCapability,
  fall back to local preview ONLY for dry-run; confirmed keeps typed error.
- R-c receipt ops unmapped despite genuine kit routes. Fix in createSupervisorGateway:
  content.retrieve → kit artifacts GET; receipts.persist → kit artifacts PUT
  (confirmation-gated); event-dag.checkpoint → kit dag append (confirmation-gated).
- R-d logs.read unmapped despite genuine dag/history. Fix: map in gateway with
  event→log-entry normalization.
- R-e VDA-G054 dead buttons: 8 workflowActionButton buttons in console workflow-proof
  section have NO handlers in bindEvents; section always renders SAMPLE refs.
  Fix: wire to real pane navigation.
- R-f datasets-browser canned surface (tool_backed!): 6 buttons + 2 selects; handlers
  only rewrite DOM with hardcoded CIDs/receipts (bafydatasetg048customerintent,
  receipt:datasets-browser:g048:*). Zero backend calls. Fix: wire to real
  invokeDescriptorOperation datasets ops (browse/semantic_search exist in registry),
  strip fabricated receipts; reframe non-mappable honestly.
- R-g accelerate-panel canned surface (tool_backed!): 5 buttons; "Run Inference"
  claims a completed WebGPU run; zero backend calls. Fix: wire to real descriptor ops
  (run_inference_job, hardware ops, job_status); strip fabricated claims.
- OK as-is: idl-explorer (Run Fixture genuinely invokes ipfs_datasets_py.browse;
  Invalid Input = genuine client-side schema validation), orb-auto-ui (Confirm
  genuinely invokes descriptor op; rest operate on real registry data),
  glasses-preview (browser_local declared; canned replays match disposition).
- External-direct flows (github api.github.com, openrouter, oauth-login
  accounts.google.com, p2p-network cloudflare/workers): app front-end function, not
  ORB/IDL claims — verify UI makes no MCP++ backing claim (spot-check pending).
- 12 tool_backed apps carry static data-svd-workflow evidence sections with fixture
  receipts (p2p-chat-unified, neural-network-designer, clock, calendar, peertube,
  friends-list, image-viewer, notes, media-player, strudel-ai-daw, p2p-chat,
  mcp-plus-plus): static display only per scan; per-app interactivity/claim check
  still pending (worklist step remaining).

## Remaining work
1. Per-app trace table (interactions inventoried / backend-connected /
   declared-local-or-external / unmapped) from inventory-raw.json + dispositions.
2. Apply fixes R-a..R-g in source (uncommitted), re-run refuting check after each.
3. Live verification: bring-up.sh stack; execute new mappings live
   (persist→retrieve receipt, checkpoint, logs.history, datasets-browser search,
   accelerate run_inference); browser-drive console full interaction set
   (Playwright — NOTE: subagent cannot drive live browser; parent must delegate
   browser-driving or accept program-state probes via HTTP + node).
4. Close out: BROKEN_CONTRACT_MAP.md (new P-entry + R-a..R-g), FEATURE_MATRIX.md row,
   SWISSKNIFE_FIX_NOTES.md dated section; integration suite re-run
   (baseline 528 passed / 29 skipped / 0 failed) + affected vitest batches.
