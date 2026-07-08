# SwissKnife Mcp-Plus-Plus Interop

VAI-665 repairs the objective validation gap for `VAIOS-G704` and MGW-573
re-confirms the same objective validation repair for the meta-glasses scanner
gap in
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-objective-gap-57359897bf4f.md`.
Attempt 2 records the current executable repair in
`data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-attempt-2-validation-repair.md`.
Both entries belong to the shared
`goal_packet/interoperability/swissknife/06921590135c` packet covering
VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, and
VAIOS-G706.

The repaired `interface contract swissknife Mcp-Plus-Plus` path is:

- `swissknife/src/services/mcp/mcp-plus-plus-interop-descriptor.ts` defines
  `SWISSKNIFE_MCP_PLUS_PLUS_INTEROP_INTERFACE`, a canonical MCP-IDL (Profile A)
  `MCPPPInterfaceDescriptor` describing the SwissKnife<->Mcp-Plus-Plus
  interop surface (`mcpplusplus.negotiate_capabilities`,
  `mcpplusplus.execute_with_envelope`, `mcpplusplus.create_delegation`,
  `mcpplusplus.evaluate_policy`, `mcpplusplus.get_dag_frontier`,
  `mcpplusplus.check_compatibility`, `mcpplusplus.create_p2p_session`), and
  `SWISSKNIFE_MCP_PLUS_PLUS_INTEROP_DESCRIPTOR`, which binds that interface to
  SwissKnife's policy-mediation schema refs and to the objective-heap
  validation lineage (task id, goal id, gap, and repair references).
- `registerSwissKnifeMcpPlusPlusInterop()` and
  `createMCPPlusPlusClientWithSwissKnifeInterop()` register the interop
  descriptor on a live `MCPPlusPlus` runtime instance (the same
  `registerInterface`/`getInterface`/`queryInterfaces`/`checkCompatibility`
  registry used by the pre-built `IPFS_KIT_INTERFACE`,
  `IPFS_ACCELERATE_INTERFACE`, and `IPFS_DATASETS_INTERFACE` descriptors),
  proving real runtime handoff behavior rather than static metadata alone.
- `toMcpIdlValidatorDescriptor()` converts the descriptor to the plain MCP-IDL
  Profile A shape (`name`, `namespace`, `version`, `methods`, `errors`,
  `requires`, `compatibility`) expected by the upstream Mcp-Plus-Plus Python
  validator (`Mcp-Plus-Plus/tests-py/validators/mcp_idl.py`
  `MCPIDLValidator.validate_descriptor`).
- `buildSwissKnifeMcpPlusPlusControlSurfaceContract()` and
  `buildSwissKnifeMcpPlusPlusInteractionEnvelope()` build representative
  payloads that validate against
  `swissknife/contracts/control_surface_contract.schema.json` and
  `swissknife/contracts/interaction_envelope.schema.json`. The policy fields
  preserve the scanner-visible `agent_identity`, `allowed_surfaces`, and
  `arguments_hash` terms as the agent identity, allowed surfaces, and
  arguments hash checks that mediate Mcp-Plus-Plus calls before dispatch.
- `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`,
  `swissknife/contracts/mediation_receipt.schema.json`, and
  `swissknife/contracts/policy_decision.schema.json` remain the receipt and
  decision schema refs advertised by the descriptor's `schema_refs`. The
  compatibility receipt schema accepts the VAI-665 Mcp-Plus-Plus receipt
  identity (`task_id: VAI-665`, `daemon_id: mcp_plus_plus`,
  `server_package: Mcp-Plus-Plus`) used by the descriptor's receipt builder,
  with MGW-573 attempt 2 covered as the scanner-visible meta-glasses repair
  task.
- `Mcp-Plus-Plus/tests-py/fixtures/valid/swissknife_mcp_plus_plus_interop_descriptor.json`
  mirrors the TypeScript descriptor as a plain MCP-IDL payload so the
  upstream Python validator has a real, committed SwissKnife-authored fixture
  to validate. `Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json`
  now links to it via `swissknife_interop_ref` so both fixtures are
  discoverable together.

Validation evidence lives in
`tests/integration/test_swissknife_mcp_plus_plus_interop.py`. It:

1. Reads the SwissKnife interop descriptor module and asserts the exported
   interface name, namespace, objective goals (all seven
   `goal_packet/interoperability/swissknife/06921590135c` goals), schema refs,
   and runtime-handoff surfaces are present.
2. Validates representative SwissKnife control-surface-contract and
   interaction-envelope payloads for the Mcp-Plus-Plus handoff against the
   SwissKnife JSON Schemas with `jsonschema`.
3. Validates the representative Mcp-Plus-Plus compatibility receipt against
   `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`,
   proving the receipt identity advertised by the descriptor is executable
   contract evidence rather than documentation-only evidence.
4. Imports the upstream Mcp-Plus-Plus `MCPIDLValidator`
   (`Mcp-Plus-Plus/tests-py/validators/mcp_idl.py`) and validates both the
   SwissKnife-authored interop descriptor fixture and the pre-existing
   generic `mcp_idl_descriptor.json` fixture, proving the two repositories'
   descriptor shapes remain mutually compatible.
5. Asserts this objective validation repair is recorded in the MGW-573
   discovery evidence
   `data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-attempt-2-validation-repair.md`,
   the source gap
   `data/meta_glasses_display_widgets/discovery/2026-07-08-mgw-573-objective-gap-57359897bf4f.md`,
   and the objective heap
   (`implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`).

## Validation

Focused validation target:

`python -m pytest tests/integration/test_swissknife_mcp_plus_plus_interop.py -q`

Full supervisor target:

`python -m pytest tests/integration -q`
