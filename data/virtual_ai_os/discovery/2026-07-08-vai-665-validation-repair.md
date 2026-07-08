# VAI-665 Objective Validation Repair

Date: 2026-07-08
Task: VAI-665
Goal: VAIOS-G704
Goal packet: goal_packet/interoperability/swissknife/06921590135c
Goal packet goals: VAIOS-G700, VAIOS-G701, VAIOS-G702, VAIOS-G703, VAIOS-G704, VAIOS-G705, VAIOS-G706
Source objective gap: data/virtual_ai_os/discovery/2026-07-08-vai-665-objective-gap-57359897bf4f.md

## Objective Validation Repair

This repair makes the `interface contract swissknife Mcp-Plus-Plus` handoff
scanner-visible and testable in the expected VAI-665 outputs. SwissKnife owns
the MCP++ Profile A/B/C/D/E client implementation, the policy-mediated
control surface contract, and the interaction envelope. Mcp-Plus-Plus owns
the canonical MCP-IDL spec, the reference `MCPIDLValidator`, and the
conformance fixtures that any MCP++ implementation must satisfy.

Evidence term: objective validation repair.
Evidence term: interface contract swissknife Mcp-Plus-Plus.
Evidence term: agent identity.
Evidence term: agent_identity.
Evidence term: allowed surfaces.
Evidence term: allowed_surfaces.
Evidence term: arguments hash.
Evidence term: arguments_hash.

- `tests/integration/test_swissknife_mcp_plus_plus_interop.py`
- `docs/integration/swissknife-mcp_plus_plus.md`
- `swissknife/src/services/mcp/mcp-plus-plus-interop-descriptor.ts`
- `swissknife/contracts/control_surface_contract.schema.json`
- `swissknife/contracts/interaction_envelope.schema.json`
- `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`
- `Mcp-Plus-Plus/tests-py/fixtures/valid/mcp_idl_descriptor.json`
- `Mcp-Plus-Plus/tests-py/fixtures/valid/swissknife_mcp_plus_plus_interop_descriptor.json`
- `implementation_plan/docs/23-virtual-ai-os-objective-goal-heap.md`

## Runtime Handoff Evidence

`swissknife/src/services/mcp/mcp-plus-plus-interop-descriptor.ts` exports
`SWISSKNIFE_MCP_PLUS_PLUS_INTEROP_INTERFACE` (a canonical MCP-IDL Profile A
`MCPPPInterfaceDescriptor`) and `SWISSKNIFE_MCP_PLUS_PLUS_INTEROP_DESCRIPTOR`.
The descriptor records the allowed agent, mcp_server, and remote-client
surfaces, the negotiated MCP++ profiles, and the SwissKnife schema refs used
for mediation.

`registerSwissKnifeMcpPlusPlusInterop()` and
`createMCPPlusPlusClientWithSwissKnifeInterop()` register the interop
descriptor on a live `MCPPlusPlus` client instance using the same
`registerInterface`/`getInterface`/`queryInterfaces`/`checkCompatibility`
registry that the pre-built `IPFS_KIT_INTERFACE`, `IPFS_ACCELERATE_INTERFACE`,
and `IPFS_DATASETS_INTERFACE` descriptors use, proving real runtime handoff
behavior.

`toMcpIdlValidatorDescriptor()` converts the descriptor to the plain MCP-IDL
shape expected by Mcp-Plus-Plus's own Python `MCPIDLValidator`
(`Mcp-Plus-Plus/tests-py/validators/mcp_idl.py`), and
`Mcp-Plus-Plus/tests-py/fixtures/valid/swissknife_mcp_plus_plus_interop_descriptor.json`
commits that exact shape as a fixture so the upstream repository's own test
fixtures now include a SwissKnife-authored descriptor.

## Validation

Focused validation target:

`python -m pytest tests/integration/test_swissknife_mcp_plus_plus_interop.py -q`

Full supervisor target:

`python -m pytest tests/integration -q`
