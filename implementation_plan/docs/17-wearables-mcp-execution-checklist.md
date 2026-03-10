# Wearables + MCP++ Execution Checklist

## Purpose
This is the execution version of the broader roadmap in `15-meta-wearables-dat-mcpplusplus-integration-roadmap.md`.

Use this document to track implementation order, current baseline, dependencies, and exit criteria across:

- the first-party wearables bridge
- backend MCP result-envelope and workflow routing
- `ipfs_kit_py`
- `ipfs_accelerate_py`
- `ipfs_datasets_py`
- `Mcp-Plus-Plus`

## Current baseline
Already completed in this repo:

- Meta DAT iOS and Android repos added as reference submodules
- first-party wearables bridge scaffold under `mobile/modules/expo-meta-wearables-dat`
- Android-safe bridge builds validated without DAT package artifacts
- normalized MCP result envelopes flowing through providers, tasks, notifications, router cards, and mobile card builders
- wearables connectivity receipt workflow routed through `ipfs_accelerate_mcp`
- local wearables receipt actions implemented and documented:
  - `mobile_open_wearables_diagnostics`
  - `mobile_reconnect_wearables_target`

## Rules of execution
- Keep the first-party wearables bridge as the shipping baseline.
- Treat Meta DAT repos as reference inputs unless package access changes.
- Keep backend as the control plane for routing, policy, receipts, and persistence.
- Keep MCP++ concepts behind normalized task/result contracts.
- Do not make mobile depend directly on upstream tool naming.

## Milestone 1: Capability and envelope contract
Status: complete baseline, continue hardening

Deliverables:
- canonical capability registry
- normalized MCP result envelope
- deterministic execution-mode selection
- consistent follow-up-action propagation

Primary files:
- `src/handsfree/mcp/catalog.py`
- `src/handsfree/mcp/models.py`
- `src/handsfree/mcp/capabilities.py`
- `src/handsfree/agent_providers.py`
- `src/handsfree/agents/service.py`
- `src/handsfree/commands/router.py`
- `src/handsfree/api.py`

Exit criteria:
- backend task/result/notification surfaces expose one normalized result contract
- direct and remote providers produce the same top-level envelope shape
- result cards and notifications consume server follow-up actions consistently

## Milestone 2: Wearables bridge diagnostics baseline
Status: in place, continue expanding device-side capability

Deliverables:
- Expo native module on iOS and Android
- bridge wrapper in JS
- diagnostics UI for availability, adapter state, candidate devices, selected target, last seen, and RSSI
- reconnect/connect flows
- bridge state-change events

Primary files:
- `mobile/modules/expo-meta-wearables-dat/*`
- `mobile/src/native/wearablesBridge.js`
- `mobile/src/native/metaWearablesDat.js`
- `mobile/src/screens/GlassesDiagnosticsScreen.js`

Exit criteria:
- app works when DAT artifacts are unavailable
- Android debug build succeeds with bridge-only path
- diagnostics screen shows real bridge-owned Bluetooth/device state
- selected target persists across app relaunches

## Milestone 3: Wearables-triggered MCP workflow
Status: baseline implemented

Deliverables:
- mobile bridge event delegates to backend on target-connected transition
- backend recognizes `wearables_bridge` client context
- `ipfs_accelerate_mcp` emits `wearables_bridge_connectivity` receipt envelopes
- receipt cards render as a distinct result type

Primary files:
- `mobile/src/api/client.js`
- `mobile/src/screens/GlassesDiagnosticsScreen.js`
- `src/handsfree/agents/delegation.py`
- `src/handsfree/agent_providers.py`
- `src/handsfree/commands/router.py`

Exit criteria:
- a connected wearable target can trigger an MCP-backed workflow without polling
- the resulting receipt includes summary, structured output, CID/deep-link, and follow-up actions
- router and mobile surfaces identify the receipt distinctly

## Milestone 4: Local wearables action contract
Status: implemented

Deliverables:
- local action IDs present in backend cards, notifications, mobile builders, and OpenAPI examples
- shared mobile executor for local wearables actions

Action IDs:
- `mobile_open_wearables_diagnostics`
- `mobile_reconnect_wearables_target`

Primary files:
- `mobile/src/utils/agentCards.js`
- `mobile/src/utils/agentActions.js`
- `mobile/src/screens/ResultsScreen.js`
- `mobile/src/screens/TaskDetailScreen.js`
- `mobile/src/screens/NotificationsScreen.js`
- `mobile/src/screens/StatusScreen.js`
- `src/handsfree/db/notifications.py`
- `src/handsfree/commands/router.py`
- `src/handsfree/models.py`
- `src/handsfree/api.py`

Exit criteria:
- the same local wearables actions appear on result cards, task detail, notifications, and OpenAPI examples
- mobile handles those actions without `/v1/commands/action`

## Milestone 5: `ipfs_accelerate_py` production path
Status: next high-value backend slice

Deliverables:
- stable remote MCP++ execution for workflow and agentic-fetch family
- receipt persistence with request/run/tool metadata
- better status polling and timeout behavior
- profile-aware routing and environment flags

Dependencies:
- Milestone 1 complete
- current wearables connectivity receipt baseline

Exit criteria:
- `ipfs_accelerate_mcp` is the default remote production path for wearables connectivity workflows
- failures and partial states produce normalized, voice-safe summaries
- task trace contains enough provenance for replay and debugging

## Milestone 6: `ipfs_kit_py` parity
Status: partially in place, expand

Deliverables:
- full parity for pin/save/read/unpin flows
- stable local vs remote execution equivalence
- consistent CID lifecycle behavior across cards and notifications

Dependencies:
- Milestone 1 complete

Exit criteria:
- `ipfs_pin`, `save_result_to_ipfs`, and related actions produce matching envelopes across execution modes
- notifications and task detail show consistent CID follow-up actions

## Milestone 7: `ipfs_datasets_py` parity
Status: partially in place, expand

Deliverables:
- dataset discovery and retrieval flows on the same normalized contract
- promptable rerun actions and structured outputs
- richer result serialization for downstream workflows

Dependencies:
- Milestone 1 complete
- Milestone 5 useful for remote orchestration reuse

Exit criteria:
- dataset discovery results can spawn follow-on MCP workflows without provider-specific UI branches
- mobile cards and notifications render dataset outputs from envelopes only

## Milestone 8: MCP++ protocol hardening
Status: planned

Deliverables:
- explicit receipt refs and provenance refs in result envelopes
- profile negotiation support where required
- stronger mapping between HandsFree capability IDs and MCP++ profile/runtime contracts

Dependencies:
- Milestones 1, 5, 6, and 7

Exit criteria:
- result envelopes can point at receipt/provenance references without changing mobile UX contracts
- remote workflows can be replayed or audited from persisted metadata

## Milestone 9: Bridge media and artifact workflows
Status: planned, do not start until bridge baseline is stable

Deliverables:
- bridge-owned camera/media capture contract
- backend artifact attach flow
- receipt/result views for media-backed tasks

Dependencies:
- Milestone 2 stable on real devices
- Milestone 8 provenance model ready

Exit criteria:
- media capture does not bypass backend control plane
- artifacts attach to tasks and result envelopes using the same CID/receipt model

## Verification checklist
- Python:
  - `tests/test_mcp_result_envelope.py`
  - `tests/test_mcp_ipfs_provider.py`
  - `tests/test_agent_provider_selection.py`
  - `tests/test_agent_commands.py`
  - `tests/test_notifications_api.py`
  - `tests/test_api_contract.py`
- Mobile:
  - `mobile/src/utils/__tests__/agentCards.test.js`
  - `mobile/src/utils/__tests__/agentActions.test.js`
  - `mobile/src/native/__tests__/wearablesBridge.test.js`
  - `mobile/src/native/__tests__/metaWearablesDat.test.js`
  - `mobile/src/api/__tests__/client.test.js`
- Android:
  - `./gradlew :app:assembleDebug -PmetaWearablesDatAndroidEnabled=false`

## Recommended implementation order from here
1. Harden `ipfs_accelerate_mcp` as the primary remote wearables workflow path.
2. Finish parity and regression coverage for `ipfs_kit_py` result storage actions.
3. Finish parity and richer outputs for `ipfs_datasets_py`.
4. Add MCP++ receipt/provenance refs without changing the mobile envelope contract.
5. Only then begin bridge media capture and artifact attachment work.

## Ownership split
- Mobile/native:
  - bridge module
  - diagnostics UI
  - local action executor
- Backend/control plane:
  - capability registry
  - provider routing
  - result envelopes
  - notifications and OpenAPI contract
- External server integration:
  - `ipfs_accelerate_py`
  - `ipfs_kit_py`
  - `ipfs_datasets_py`
  - `Mcp-Plus-Plus` profile/receipt alignment
