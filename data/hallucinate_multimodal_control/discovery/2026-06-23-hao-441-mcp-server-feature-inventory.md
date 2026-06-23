# HAO-441 MCP Server Feature Inventory

Date: 2026-06-23
Task: HAO-441
Track: launch
Scope: Swissknife integration contracts for `ipfs_accelerate_py`, `ipfs_datasets_py`, and `ipfs_kit_py`.

## Summary

This MCP server feature inventory treats the three IPFS Python servers as
explicit launch contracts. Swissknife can discover and render UI surfaces from
descriptor packs, but Hallucinate App mediation remains the policy boundary for
all daemon-managed invocations.

The launch-safe contract is:

- `ipfs_datasets_py`: hierarchical MCP meta-tools, with `tools_dispatch` used to
  call dataset, IPFS, index, provenance, and background-task categories.
- `ipfs_accelerate_py`: canonical MCP++ runtime, with hierarchical meta-tools
  plus `tools_runtime_metrics` for compute and telemetry surfaces.
- `ipfs_kit_py`: concrete IPFS, pin-management, storage, migration, search, and
  streaming tools or REST-style endpoints; no generic `tools_dispatch` contract
  is assumed for Swissknife task delegation.

## Launch Contracts

| Server | Daemon id | Entrypoints | Default launch port | Transport and protocol assumptions | Swissknife consumers |
| --- | --- | --- | --- | --- | --- |
| `ipfs_datasets_py` | `ipfs-datasets` / `ipfs_datasets_mcp` | `python -m ipfs_datasets_py.mcp_server`; HTTP compatibility path `python -m ipfs_datasets_py.mcp_server --http --port 3002`; package startup `start_stdio_server()` or `start_server(host, port)` | Electron daemon doc: `3002`; HandsFree config baseline: `8010`; upstream default HTTP arg: `8000` | Preferred MCP stdio for editor clients; Hallucinate/HandsFree HTTP JSON-RPC uses `initialize`, `tools/list`, and `tools/call` at `/mcp`; HTTP mode is documented as legacy in the package entrypoint. | Dataset browser, content get, index, pin, publish, sync, and progress surfaces from `swissknife/src/services/mcp-ipfs-datasets-descriptor-pack.ts`. |
| `ipfs_accelerate_py` | `ipfs-accelerate` / `ipfs_accelerate_mcp` | `ipfs-accelerate mcp start`; `python -m ipfs_accelerate_py.mcp.cli`; `python -m ipfs_accelerate_py.mcp_server.fastapi_service`; `python -m ipfs_accelerate_py.mcp_server`; embedded `create_server()` | Electron daemon doc: `3003`; HandsFree config baseline: `8012`; upstream FastAPI env default: `8000` mounted at `/mcp` | MCP++ FastAPI service, process-level helper, and MCP+p2p paths are documented; Hallucinate/HandsFree uses HTTP JSON-RPC MCP at `/mcp` unless a per-server stdio override is configured. | Hardware profile, inference job, job status, and telemetry surfaces from `swissknife/src/services/mcp-ipfs-accelerate-descriptor-pack.ts`. |
| `ipfs_kit_py` | `ipfs-kit` / `ipfs_kit_mcp` | `ipfs-kit mcp start`; `python -m ipfs_kit_py.cli mcp start`; direct FastAPI server `ipfs_kit_py.mcp.direct_mcp_server:app`; enhanced servers under `ipfs_kit_py.mcp.enhanced_*` | Electron daemon doc: `3001`; HandsFree config baseline: `8011`; upstream dashboard example: `8004` | Concrete HTTP/JSON-RPC and REST-style endpoints, including `/mcp/tools/call`, `/api/v0/*`, `/api/v0/jsonrpc`, `/health`, and dashboard paths; do not assume a generic MCP meta-dispatch tool. | MCP control, IPFS storage, pin dashboard, content browser, backend health, and legacy IPFS CLI/VFS consumers. Swissknife must bind a concrete tool such as `ipfs_add` or `list_pins` when delegating through Hallucinate App. |

## Tool Names And Feature Surface

### `ipfs_datasets_py`

Stable control-plane tool names:

- `tools_list_categories`
- `tools_list_tools`
- `tools_get_schema`
- `tools_dispatch`

Launch-relevant categories and sample tool names:

| Category | Tool names used by launch surfaces |
| --- | --- |
| `dataset_tools` | `load_dataset`, `save_dataset`, `process_dataset`, `convert_dataset_format`, `text_to_fol`, `legal_text_to_deontic` |
| `ipfs_tools` | `pin_to_ipfs`, `get_from_ipfs` |
| `index_management_tools` | `load_index` and index lifecycle helpers |
| `background_task_tools` | `manage_background_tasks`, `check_task_status`, `get_task_status` |
| `provenance_tools` | `record_provenance` |
| `pdf_tools` | `pdf_graphrag_process`, `pdf_semantic_search`, `pdf_batch_process` |
| `embedding_tools` | `generate_embedding`, `generate_batch_embeddings`, `shard_embeddings` |
| `web_archive_tools` | `brave_search`, `common_crawl_search`, `wayback_machine_fetch`, `github_search`, `huggingface_search` |
| `logic_tools` | `tdfol_prove`, `tdfol_parse`, `cec_prove`, `logic_capabilities`, `logic_health` |
| `vector_tools` / `vector_store_tools` | `create_vector_index`, `search_vector_index`, vector store management helpers |

Swissknife descriptor consumers map these to normalized `dataset_ref`,
`content_ref`, `job_ref`, `artifact_ref`, `progress_event`, and
`provenance_ref` payloads.

### `ipfs_accelerate_py`

Stable control-plane tool names:

- `tools_list_categories`
- `tools_list_tools`
- `tools_get_schema`
- `tools_dispatch`
- `tools_runtime_metrics`

Canonical MCP++ profiles advertised by the server:

- `mcp++/profile-a-idl`
- `mcp++/profile-b-cid-artifacts`
- `mcp++/profile-c-ucan`
- `mcp++/profile-d-temporal-policy`
- `mcp++/profile-e-mcp-p2p`

Launch-relevant categories and bindings:

| Category or binding | Tool names or backend functions |
| --- | --- |
| `ipfs` | migrated Wave A IPFS category exposed through the unified registry |
| `workflow` | migrated Wave A workflow category exposed through the unified registry |
| `p2p` | migrated Wave A P2P category exposed through the unified registry |
| `background_task_tools` | `manage_background_tasks`, `get_task_status` for task delegation |
| Hardware profile | `HardwareDetector.get_available_hardware`, fallback `detect_hardware` |
| Inference jobs | `llm_router.submit_task`, `WorkflowCoordinator.submit_task` |
| Job status | `llm_router.get_task`, `ProvenanceLogger.log_inference` |
| Telemetry | `PrometheusMetrics.generate_metrics`, `HealthChecker.check_detailed`, `tools_runtime_metrics` |

Swissknife descriptor consumers normalize these to `hardware_profile_ref`,
`model_ref`, `dataset_ref`, `inference_input_ref`, `inference_job_ref`,
`telemetry_event`, `artifact_ref`, and `provenance_ref`.

### `ipfs_kit_py`

Stable concrete tool names from the production server documentation:

- Core IPFS: `ipfs_add`, `ipfs_cat`, `ipfs_pin_add`, `ipfs_pin_rm`,
  `ipfs_pin_ls`, `ipfs_pin_update`, `ipfs_version`, `ipfs_id`
- Pin dashboard: `list_pins`, `get_pin_stats`, `get_pin_metadata`,
  `unpin_content`, `bulk_unpin`, `export_pins`
- System: `system_health`, `get_backend_status`, `list_backends`

Launch-relevant API groups in `direct_mcp_server.py`:

- `/api/v0/ipfs/version`, `/api/v0/ipfs/add`, `/api/v0/ipfs/cat/{cid}`,
  `/api/v0/ipfs/pin/add`, `/api/v0/ipfs/pin/ls`, `/api/v0/ipfs/pin/rm`
- `/api/v0/storage/backends`, `/api/v0/storage/add`,
  `/api/v0/storage/get/{backend}/{cid}`, `/api/v0/storage/list/{backend}`
- `/api/v0/migration/policies`, `/api/v0/migration/policy`,
  `/api/v0/migration/execute/{policy_name}`, `/api/v0/migration/task/{task_id}`
- `/api/v0/search/status`, `/api/v0/search/index`, `/api/v0/search/text`,
  `/api/v0/search/vector`, `/api/v0/search/hybrid`
- `/api/v0/stream/status`, `/api/v0/stream/upload/chunk`,
  `/api/v0/stream/upload/finalize`, `/api/v0/stream/download/{backend}/{cid}`
- `/api/v0/jsonrpc`, `/api/v0/admin/system/status`, `/health`,
  `/api/v0/status`

Swissknife consumers should treat `ipfs_kit_py` as the storage and pin
operations provider. Hallucinate App must reject generic task delegation unless
the request names a concrete tool or endpoint binding.

## Security Boundaries

- Hallucinate App mediation is the pre-invocation policy boundary for
  `mcp-server`, HTTP, websocket, stdio, local, and ORB adapters.
- `ipfs_datasets_py` and `ipfs_accelerate_py` may apply their own MCP++ gates
  such as UCAN validation, risk scoring, temporal/deontic policy, event-DAG
  provenance, and artifact CIDs. Those are upstream controls, not substitutes
  for Hallucinate App policy receipts.
- `ipfs_kit_py` controls storage backends, IPFS daemon operations, migration,
  search indexing, and streaming. These operations can mutate local or remote
  storage, so Hallucinate App must require explicit service, method, arguments
  hash, actor, and policy decision receipts before dispatch.
- Raw payloads, prompts, transcripts, media, credentials, bearer tokens,
  delegation chains, and storage object bodies must not be written into daemon
  dashboards or launch readiness receipts. Receipts should carry CIDs, hashes,
  schemas, status, and redacted summaries.
- `ipfs_kit_py` authentication and RBAC middleware are server-local defenses.
  Swissknife and Hallucinate App must still use configured auth secrets or
  bearer tokens and record whether transport authentication was present.

## Hallucinate App Receipt Fields

Every mediated MCP invocation that contributes to launch readiness needs these
receipt fields:

- `receipt_schema`: `mcp_server_invocation_receipt_v1`
- `task_id`: `HAO-441` when used as inventory evidence, or the invoking launch
  task id for runtime receipts
- `server_package`: one of `ipfs_datasets_py`, `ipfs_accelerate_py`,
  `ipfs_kit_py`
- `daemon_id`: `ipfs-datasets`, `ipfs-accelerate`, or `ipfs-kit`
- `entrypoint`: exact command or embedded startup path
- `transport`: `stdio`, `http`, `websocket`, `mcp-server`, `local`, or `orb`
- `protocol`: MCP JSON-RPC method and version, or concrete REST endpoint
- `rpc_path`: `/mcp`, `/mcp/tools/call`, `/api/v0/jsonrpc`, or endpoint path
- `tool_name`: meta-tool name or concrete `ipfs_kit_py` tool name
- `tool_category`: category for hierarchical dispatch, when present
- `upstream_function`: concrete package function or API endpoint
- `swissknife_consumer`: descriptor pack, app, or surface requesting the call
- `interaction_envelope_id`, `session_id`, `correlation_id`, `request_id`
- `actor`, `device_surface`, `source_surface`, `target_surface`
- `policy_decision_id`, `policy_outcome`, `policy_receipt_id`,
  `mediation_receipt_id`
- `control_surface_contract_ref`, `descriptor_id`, `interface_cid`,
  `tool_schema_hash`
- `arguments_hash`, `payload_contracts`, `redaction_profile`
- `dispatch_allowed`, `fallback_path`, `recovery_state`
- `upstream_status`, `upstream_task_id`, `artifact_cid`, `event_cid`,
  `decision_cid`, `receipt_cid`, `parent_receipt_cid`
- `started_at`, `completed_at`, `duration_ms`
- `auth_context`: redacted boolean/issuer/scope summary only

## Launch Readiness Notes

- `ipfs_datasets_py` and `ipfs_accelerate_py` are launch-ready for generic
  Swissknife dispatch only through the listed meta-tools and configured task
  category bindings.
- `ipfs_kit_py` is launch-ready for storage and pin workflows only when the
  concrete tool or endpoint is named in the descriptor or mediation request.
- Swissknife UI support must not be inferred from package presence. It is
  launch-scoped only when a descriptor pack or app route names the expected
  surface and Hallucinate App records a matching mediation receipt.
