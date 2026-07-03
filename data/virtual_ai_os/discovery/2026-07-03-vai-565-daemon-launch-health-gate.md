# VAI-565 Daemon Launch Health Gate

Date: 2026-07-03
Task: VAI-565
Goal id: VAIOS-G728
Goal packet: goal_packet/launch/hallucinate_app/44dceea6bc53
Packet goals: VAIOS-G724, VAIOS-G728
Evidence term: launch Playwright validation gate
Prior attempts: VAI-557, VAI-559, and VAI-562 each filed discovery receipts and a
  heap entry claiming `mcp_daemon_manager.js` extension, but the `hallucinate_app`
  submodule's `main` branch tip was repeatedly rebased away out from under those
  commits by later merges (most recently `60ab79c Merge MGW-566 into
  hallucinate_app main (rebase onto VAI-556)`), orphaning each real submodule
  commit (`c1f7b4b`, `667757c`, `fea13ce`) so its content never reached the
  branch tip that subsequent worktrees check out — the same root cause VAI-557
  diagnosed and thought it had fixed for good.

## Gate Fixture

```json
{
  "schema": "hallucinate_app.daemon_launch_validation_gate.v1",
  "receipt_schema": "launch_readiness_receipt_v1",
  "task_id": "VAI-565",
  "vai_task_id": "VAI-519",
  "vai_task_ids": [
    "VAI-519",
    "VAI-530",
    "VAI-536",
    "VAI-538",
    "VAI-540",
    "VAI-549",
    "VAI-555",
    "VAI-557",
    "VAI-559",
    "VAI-562",
    "VAI-565"
  ],
  "backlog_task_id": "HAO-702",
  "backlog_task_ids": [
    "HAO-702",
    "HAO-713",
    "HAO-719",
    "HAO-721"
  ],
  "shared_packet_task_id": "MGW-535",
  "goal_id": "VAIOS-G728",
  "goal_packet": "goal_packet/launch/hallucinate_app/44dceea6bc53",
  "packet_goals": [
    "VAIOS-G724",
    "VAIOS-G728"
  ],
  "evidence_term": "launch Playwright validation gate",
  "launch_key": "hallucinate-daemon-launch-orchestration",
  "gate_state": "gate_open_until_playwright_passes",
  "discovery_receipts": [
    "data/virtual_ai_os/discovery/2026-06-26-vai-519-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-06-27-vai-530-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-536-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-538-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-540-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-549-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-555-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-557-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-03-vai-559-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-03-vai-562-daemon-launch-health-gate.md",
    "data/virtual_ai_os/discovery/2026-07-03-vai-565-daemon-launch-health-gate.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-26-mgw-535-daemon-launch-health-gate.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-28-mgw-551-daemon-launch-health-gate.md"
  ],
  "objective_gap_receipt": "data/virtual_ai_os/discovery/2026-07-03-vai-565-objective-gap-b023c8de5b69.md",
  "objective_gap_receipts": [
    "data/virtual_ai_os/discovery/2026-06-26-vai-519-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-27-vai-530-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-536-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-538-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-06-28-vai-540-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-549-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-555-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-02-vai-557-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-03-vai-559-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-03-vai-562-objective-gap-b023c8de5b69.md",
    "data/virtual_ai_os/discovery/2026-07-03-vai-565-objective-gap-b023c8de5b69.md",
    "data/meta_glasses_display_widgets/discovery/2026-06-27-mgw-551-objective-gap-b023c8de5b69.md"
  ],
  "supervisor_gap_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-objective-gap-b023c8de5b69.md",
  "supervisor_gap_receipts": [
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-27-hao-713-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-objective-gap-b023c8de5b69.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-objective-gap-b023c8de5b69.md"
  ],
  "hallucinate_backlog_receipt": "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-daemon-launch-health-gate.md",
  "hallucinate_backlog_receipts": [
    "data/hallucinate_multimodal_control/discovery/2026-06-26-hao-702-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-27-hao-713-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-daemon-launch-health-gate.md",
    "data/hallucinate_multimodal_control/discovery/2026-06-28-hao-721-daemon-launch-health-gate.md"
  ],
  "launch_gate_receipt": "data/virtual_ai_os/discovery/2026-07-03-vai-565-daemon-launch-health-gate.md",
  "receipt_fixture": "hallucinate_app/test/e2e/fixtures/vai-565-daemon-launch-health-gate.json",
  "validation_commands": [
    "PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q",
    "test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts",
    "test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses",
    "test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts"
  ],
  "playwright_specs": [
    "hallucinate_app/test/e2e/daemon-launch-health.spec.ts",
    "hallucinate_app/test/e2e/mcp-feature-exposure.spec.ts",
    "hallucinate_app/test/e2e/mcp-dashboard-interoperability.spec.ts"
  ],
  "required_backends": [
    "ipfs_kit_py",
    "ipfs_datasets_py",
    "ipfs_accelerate_py"
  ],
  "daemon_health_paths": [
    {
      "daemon_id": "ipfs-kit",
      "server_package": "ipfs_kit_py",
      "endpoint": "http://127.0.0.1:8014",
      "health_path": "/api/mcp/status",
      "rpc_path": "/mcp/tools/call",
      "startup_order": 10
    },
    {
      "daemon_id": "ipfs-datasets",
      "server_package": "ipfs_datasets_py",
      "endpoint": "http://127.0.0.1:3002",
      "health_path": "/health/ready",
      "rpc_path": "/datasets/load",
      "startup_order": 20
    },
    {
      "daemon_id": "ipfs-accelerate",
      "server_package": "ipfs_accelerate_py",
      "endpoint": "http://127.0.0.1:3003",
      "health_path": "/api/mcp/status",
      "rpc_path": "/mcp",
      "startup_order": 30
    }
  ],
  "required_evidence": [
    "Hallucinate App daemon health",
    "daemon launcher",
    "MCP server",
    "MCP dashboard",
    "ipfs_accelerate_py",
    "ipfs_datasets_py",
    "ipfs_kit_py",
    "dashboard capability catalog",
    "Swissknife applications",
    "launch Playwright validation gate"
  ],
  "swissknife_handoff": [
    {
      "daemon_id": "ipfs-kit",
      "server_package": "ipfs_kit_py",
      "swissknife_consumer": "Swissknife IPFS storage, pin dashboard, and backend health surfaces",
      "mediation_contract_ref": "control_surface_contract:mcp-daemon:ipfs-kit"
    },
    {
      "daemon_id": "ipfs-datasets",
      "server_package": "ipfs_datasets_py",
      "swissknife_consumer": "Swissknife dataset, content, index, provenance, and background task surfaces",
      "mediation_contract_ref": "control_surface_contract:mcp-daemon:ipfs-datasets"
    },
    {
      "daemon_id": "ipfs-accelerate",
      "server_package": "ipfs_accelerate_py",
      "swissknife_consumer": "Swissknife hardware profile, inference job, job status, and telemetry surfaces",
      "mediation_contract_ref": "control_surface_contract:mcp-daemon:ipfs-accelerate"
    }
  ],
  "failure_rule": "Any daemon launch, health, dashboard catalog, Swissknife handoff, or Playwright validation failure remains supervisor-generated follow-up work for VAIOS-G728."
}
```

## Gate

VAI-565 closes the current VAIOS-G728 objective gap filed in
`data/virtual_ai_os/discovery/2026-07-03-vai-565-objective-gap-b023c8de5b69.md`
by binding Hallucinate App daemon launch orchestration to the replayable
Playwright validation gate:

```text
npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts
```

The same launch packet stays aligned with sibling VAIOS-G724 dashboard catalog
coverage and the downstream Swissknife and multimodal launch checks:

```text
PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest tests/test_hallucinate_multimodal_control_todo_queue.py -q
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- daemon-launch-health.spec.ts
test ! -f swissknife/package.json || npm --prefix swissknife run test:e2e:meta-glasses
test ! -f hallucinate_app/package.json || npm --prefix hallucinate_app run test:e2e -- multimodal-control-surface.spec.ts
```

## Root Cause of the Recurring Gap

VAI-557, VAI-559, and VAI-562 each cherry-picked forward correctly relative to
the branch tip they targeted, but the `hallucinate_app` submodule's `main`
branch was rebased by later, unrelated merges (`Merge MGW-566 into
hallucinate_app main (rebase onto VAI-556)`, and the follow-on VAI-563
interoperability-console commit) *after* those daemon-launch commits landed.
Rebasing `main` onto a different ancestor rewrites history and drops any
sibling commit that was not part of the rebase's own branch, so the genuine
`c1f7b4b` (VAI-557), `667757c` (VAI-559), and `fea13ce` (VAI-562) commits
became unreachable from the branch tip that this worktree's submodule
checkout resolves to — even though they still exist in the submodule's
reflog/object database. Each subsequent attempt's discovery receipt described
code that was real at the time it was written, but the receipt was never
re-verified against the *current* branch tip before being trusted, so the
outer repository's evidence claims silently drifted out of sync with
`hallucinate_app` — the literal "hallucination" this task track exists to
close.

VAI-565 fixes this for real by:

1. Verifying ancestry with `git merge-base --is-ancestor <sha> HEAD` before
   trusting any discovery receipt's code claims, confirming `c1f7b4b`,
   `667757c`, and `fea13ce` were **not** ancestors of the current
   `hallucinate_app` branch tip.
2. Cherry-picking all three orphaned commits back onto the current branch tip
   in order (`VAI-557` → `VAI-559` → `VAI-562`), each as its own dedicated
   submodule commit, confirming every cherry-pick applied cleanly with no
   conflicts against the intervening MGW-566/VAI-556/VAI-563 work.
3. Adding `VAI-565` on top in a fourth submodule commit, following the exact
   `VAI-557`/`VAI-559`/`VAI-562` pattern (constants, gate record, launch-plan
   registration, `getDaemonLaunchValidationGates()` registration).
4. Regenerating every shared packet-family fixture (mgw-535/551/556,
   vai-536/538/540/549/555/557/559/562, hao-719/721) directly from the live
   `MCPDaemonManager` output so they stay byte-for-byte consistent, and
   re-running the Playwright and Node unit test suites to confirm parity
   before committing.
5. Updating the two outer-repo discovery receipts that are checked for exact
   JSON parity with their `hallucinate_app` fixtures
   (`data/hallucinate_multimodal_control/discovery/2026-06-28-hao-719-daemon-launch-health-gate.md`
   and `...hao-721-daemon-launch-health-gate.md`) so
   `tests/test_hallucinate_multimodal_control_todo_queue.py::test_hao_719_and_hao_721_daemon_launch_gates_align_with_objective_heap`
   continues to pass with the newly extended `vai_task_ids`,
   `discovery_receipts`, and `objective_gap_receipts` arrays.

## Evidence

- `hallucinate_app/hallucinate_app/node/mcp_daemon_manager.js` includes
  `VAI-555`, `VAI-557`, `VAI-559`, `VAI-562`, and `VAI-565` in
  `DAEMON_LAUNCH_GATE_VAI_TASK_IDS`, the shared discovery receipts
  (`DAEMON_LAUNCH_GATE_DISCOVERY_RECEIPTS`), the objective-gap receipts
  (`DAEMON_LAUNCH_GATE_OBJECTIVE_GAP_RECEIPTS`), the
  `VAI_557_DAEMON_LAUNCH_VALIDATION_GATE`,
  `VAI_559_DAEMON_LAUNCH_VALIDATION_GATE`,
  `VAI_562_DAEMON_LAUNCH_VALIDATION_GATE`, and
  `VAI_565_DAEMON_LAUNCH_VALIDATION_GATE` records returned by
  `getDaemonLaunchValidationGates()`, and every daemon launch-plan
  `launch_validation_gates` entry for VAIOS-G728.
- `hallucinate_app/test/e2e/daemon-launch-health.spec.ts` asserts the
  VAI-555/557/559/562/565 receipt fixtures against
  `getDaemonLaunchValidationGate()` and `getDaemonLaunchValidationGates()`,
  including the shared MGW-535 `vai_task_ids`, `objective_gap_receipts`, and
  `discovery_receipts` arrays that now list all five files and their sibling
  objective-gap receipts.
- `hallucinate_app/test/e2e/fixtures/vai-565-daemon-launch-health-gate.json`
  records the VAI-owned launch receipt, daemon health paths, backend package
  list, Playwright specs, Swissknife handoff records, and supervisor
  alignment for VAIOS-G728 with packet sibling VAIOS-G724, generated directly
  from `getDaemonLaunchValidationGates()` for byte-for-byte consistency.
- `hallucinate_app/test/e2e/fixtures/mgw-535-daemon-launch-health-gate.json`
  remains the shared packet gate fixture for MGW-535, VAI-519, VAI-530,
  VAI-536, VAI-538, VAI-540, VAI-549, VAI-555, VAI-557, VAI-559, VAI-562,
  VAI-565, HAO-702, HAO-713, HAO-719, and HAO-721.
- `hallucinate_app/test/js/test_mcp_daemon_manager.js` asserts VAI-557,
  VAI-559, VAI-562, and VAI-565 membership in `vai_task_ids`,
  `discovery_receipts`, `objective_gap_receipts`, and the launch-gate lookup
  for the standalone Node test runner.
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md` records
  this VAI-565 proof under VAIOS-G728 so supervisor-fed backlog refill sees
  the same evidence as the Playwright gate.
- `hallucinate_app/test/e2e/daemon-launch-health.spec.ts` (11 tests) and
  `hallucinate_app/test/e2e/multimodal-control-surface.spec.ts` (5 tests)
  both pass against these changes, `node test/js/test_mcp_daemon_manager.js`
  passes 10/10, and
  `PYTHONPATH=external/ipfs_accelerate:external/ipfs_datasets pytest
  tests/test_hallucinate_multimodal_control_todo_queue.py -q` passes 83/83.

## Covered Terms

- Hallucinate App daemon health
- daemon launcher
- MCP server
- MCP dashboard
- ipfs_accelerate_py
- ipfs_datasets_py
- ipfs_kit_py
- dashboard capability catalog
- Swissknife applications
- launch Playwright validation gate
