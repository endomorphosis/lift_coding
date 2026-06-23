# HAO-445 Mcp-Plus-Plus Compatibility Evidence

Date: 2026-06-23
Task: HAO-445
Track: launch
Depends on: HAO-441

## Summary

Hallucinate App and Swissknife are compatible with the local Mcp-Plus-Plus
launch contract when Swissknife discovers MCP++ capability descriptors, chooses
an explicit transport, and routes every tool call through Hallucinate App
mediation before the Python daemon command contract from HAO-441 is invoked.

The compatibility boundary is intentionally layered:

- Swissknife owns MCP++ descriptor rendering, generated app routing, and Profile
  A-E client behavior.
- Hallucinate App owns policy mediation, command authorization, and receipt
  lineage before daemon dispatch.
- Python MCP daemons own server-local execution, JSON-RPC or REST errors, and
  optional MCP++ server-side checks.

## Negotiation Contract

Protocol negotiation follows the MCP++ initialization shape already implemented
by Swissknife:

1. Client sends `initialize` with `protocolVersion`, `clientInfo`, and
   `capabilities.mcpPlusPlusProfiles`.
2. Server responds with its protocol version, server identity, standard MCP
   capabilities, and MCP++ profiles it accepts.
3. Client sends `notifications/initialized`.
4. Hallucinate App records the negotiated profile set, daemon id, package,
   transport, endpoint, session id, and correlation id in the same command
   receipt lineage used for Python daemon invocations.

Launch-compatible profile names are normalized to the `mcp++/` vocabulary used
by Swissknife services and HAO-441:

- `mcp++/profile-a-idl` or `mcp++/idl`
- `mcp++/profile-b-cid-artifacts` or `mcp++/cid-envelope`
- `mcp++/profile-c-ucan` or `mcp++/ucan`
- `mcp++/profile-d-temporal-policy`
- `mcp++/profile-e-mcp-p2p`
- `mcp++/event-dag`

Profile negotiation is advisory for transport selection but mandatory for
evidence: if a server omits a profile required by a capability descriptor, the
receipt must record a downgraded or incompatible verdict before dispatch.

## Capability Descriptor Compatibility

Swissknife capability descriptor compatibility is anchored in
`swissknife/src/services/mcp-idl.ts` and `swissknife/src/services/mcp-ui-profile.ts`.
The descriptor fields that must survive Hallucinate App mediation are:

| Contract area | Required evidence |
| --- | --- |
| Identity | descriptor id, `interface_cid`, `name`, `namespace`, `version`, and optional `schema_hash` |
| Methods | MCP++ method names, input/output schema or schema CIDs, event schemas, and error schema CIDs |
| Compatibility | `requires[]`, `compatibility.compatible_with`, `compatibility.supersedes`, and `interfaces/compat` verdict |
| UI binding | Swissknife service id, app id, operation list, template mapping, permissions, and state model |
| Policy binding | `control_surface_contract_ref`, selected logic bindings, policy bundle ref, and compiled policy CID |

The descriptor cannot authorize execution by itself. It only describes the
operation and requested capability. Hallucinate App still emits the
`interaction_envelope`, `policy_decision`, and `mediation_receipt` before a
tool dispatch is allowed.

## Transport Compatibility

Compatible launch transports are:

| Transport | Compatibility rule |
| --- | --- |
| `mcp-server` / `http` | Use JSON-RPC `initialize`, `tools/list`, and `tools/call` at `/mcp` or the configured daemon path. |
| `stdio` | Preserve the same MCP JSON-RPC methods and receipt fields; record the daemon command as the endpoint. |
| `websocket` | Allowed only when the descriptor or daemon config names the websocket endpoint and lifecycle events are captured. |
| `local` / `orb` | Allowed for in-process Swissknife or ORB adapters only when the same Hallucinate App before-invoke policy hook is used. |
| `mcp-p2p` | Optional MCP++ Profile E transport using `/mcp+p2p/1.0.0`; peer identity does not replace Hallucinate App execution authority. |

Every transport receipt must include `transport`, `protocol_path`, endpoint or
command, auth-present boolean, redaction profile, request id, and correlation
id.

## Tool Calls, Errors, And Receipts

The HAO-441 daemon command contract remains the source of truth:

- `ipfs_datasets_py`: use `tools_dispatch` for hierarchical categories such as
  `dataset_tools`, `ipfs_tools`, `index_management_tools`,
  `background_task_tools`, and `provenance_tools`.
- `ipfs_accelerate_py`: use `tools_dispatch` and `tools_runtime_metrics` for
  compute, workflow, P2P, telemetry, and inference surfaces.
- `ipfs_kit_py`: use concrete tools or endpoints such as `ipfs_add`,
  `ipfs_cat`, `ipfs_pin_add`, `list_pins`, `system_health`, or `/api/v0/*`;
  generic task delegation is incompatible unless a concrete binding is named.

Errors are compatible when both failure domains are preserved:

- Hallucinate App policy outcomes: `deny`, `require_confirmation`, `defer`,
  `rewrite`, `fallback_surface`, and `rate_limit`.
- Daemon outcomes: JSON-RPC error code and name, transport timeout,
  unavailable daemon, upstream execution error, or schema mismatch.

Tool receipt lineage must include `interaction_envelope_id`,
`policy_decision_id`, `mediation_receipt_id`, descriptor/interface CID,
tool schema hash, argument hash, upstream status, event CID, decision CID,
receipt CID, and parent receipt CID. Raw payloads, credentials, media,
prompts, transcripts, and bearer tokens remain redacted.

## Lifecycle Events

The minimum compatible lifecycle sequence is:

1. `daemon_start`
2. `daemon_health`
3. `initialize`
4. `initialized`
5. `descriptor_refresh`
6. `invocation_queued`
7. `policy_decision`
8. `dispatch` or fail-closed policy result
9. `upstream_result` or `upstream_error`
10. `receipt_emitted`
11. `daemon_stop` or `daemon_recovery` when applicable

Lifecycle events are evidence only when they share the same session,
correlation id, daemon id, policy ids, and receipt lineage as the tool call.

## Compatibility Verdict

HAO-445 verifies the compatibility shape, not a live daemon run. The compatible
launch contract is:

- Mcp-Plus-Plus protocol negotiation is represented by MCP `initialize` plus
  negotiated `mcpPlusPlusProfiles`.
- Swissknife capability descriptors remain MCP++ Profile A descriptors with UI,
  permission, state, and control-surface bindings layered on top.
- Hallucinate App remains the mediation and receipt authority.
- Python MCP daemon commands from HAO-441 remain unchanged.
- Compatibility evidence is recorded with
  `swissknife/contracts/mcp_plus_plus_compatibility_receipt.schema.json`.
- Mcp-Plus-Plus protocol-side launch evidence is recorded in
  `Mcp-Plus-Plus/docs/compatibility/HAO-445-hallucinate-swissknife.md`.
