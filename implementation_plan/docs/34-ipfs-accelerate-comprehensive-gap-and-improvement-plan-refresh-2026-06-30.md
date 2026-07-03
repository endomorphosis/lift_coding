# IPFS Accelerate Comprehensive Gap And Improvement Plan Refresh (2026-06-30)

Status: Fresh investigation after serving readiness, call-matrix, and orchestrator backend-targeting slices
Scope: external/ipfs_accelerate/ipfs_accelerate_py model server, API endpoint multiplexer, containerizer, Kubernetes cluster manager, and agent orchestrator, with explicit required calls into ipfs_kit_py and ipfs_datasets_py

## 1. Executive Summary

The serving foundation is materially improved and test-gated, but there are still high-priority integration and productionization gaps that should be closed before release hardening is considered complete.

Most important current findings:
1. High severity: Unified inference result recorder contract mismatch can silently bypass persistence/provenance recording when called through backend finalization.
2. High severity: HF model server inference and model-management endpoints are still placeholders and are not wired into the canonical backend-manager and storage/provenance seams.
3. Medium severity: Worker backend-targeting forwards preferred types as plain strings, but backend selection expects BackendType values.
4. Medium severity: Kubernetes backend lacks deep cluster error/event enrichment (conditions/events/reasons) in execution metadata compared to desired parity.
5. Medium severity: Model manager usage-linkage synchronization to datasets exists, but event schema normalization is incomplete for inference-linkage observability.

## 2. Current Confirmed Baseline

Strong areas already in place:
- Canonical serving contract document: implementation_plan/docs/33-ipfs-accelerate-serving-integration-contract-2026-06-30.md
- Readiness and benchmark contract gates with passing evidence report:
  - external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py
  - external/ipfs_accelerate/test/api/test_serving_benchmark_contracts.py
  - implementation_plan/docs/31-ipfs-accelerate-model-serving-readiness-report.json
- Docker and Kubernetes execution envelope parity with CID pre-materialization support
- Worker/orchestrator lineage routing and backend-manager dispatch seam

## 3. Gap Register (Prioritized)

### P0-1: Unified recorder call-signature mismatch

Where:
- external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py
- external/ipfs_accelerate/ipfs_accelerate_py/unified_inference_service.py

Issue:
- Backend finalization passes protocol and placement arguments into the configured result recorder.
- UnifiedInferenceService.record_inference_result currently does not accept these additional keyword arguments.
- In live execution this can raise argument errors and result recorder execution is skipped by exception handling, causing silent loss of expected persistence/provenance metadata.

Required fix:
1. Make the result recorder signature forward-compatible.
2. Ensure protocol/hardware/placement fields are persisted into run metadata.
3. Add a regression test that uses the real service recorder with backend finalization.

### P0-2: HF model server endpoints are non-canonical placeholders

Where:
- external/ipfs_accelerate/ipfs_accelerate_py/hf_model_server/server.py

Issue:
- Completions, chat, embeddings, model load, and unload endpoints still return placeholders.
- No canonical execution route through InferenceBackendManager.execute_task.
- No required persistence and provenance call-order into IPFSKitStorage and DatasetsManager for these endpoints.

Required fix:
1. Route inference endpoints through backend-manager execute path.
2. Route model load and unload through model-manager lifecycle hooks.
3. Emit canonical success and failure metadata (output_cid, provenance_cid, backend routing metadata, status, error).
4. Add route-level contract tests for inference completion and load/unload lifecycle events.

### P1-1: Preferred backend type normalization in worker routing

Where:
- external/ipfs_accelerate/ipfs_accelerate_py/p2p_tasks/worker.py
- external/ipfs_accelerate/ipfs_accelerate_py/inference_backend_manager.py

Issue:
- Worker forwarding now supports preferred backend type aliases, but currently forwards strings.
- Backend manager selection sorting expects BackendType enum values, so preferred-type priority can be ignored.

Required fix:
1. Normalize preferred type strings to BackendType values in worker or backend manager.
2. Preserve backward compatibility for payload aliases.
3. Add a routing-priority test proving type preference changes selection order.

### P1-2: Kubernetes event and failure-detail parity not complete

Where:
- external/ipfs_accelerate/ipfs_accelerate_py/container_backends/kubernetes/kubernetes.py

Issue:
- Current implementation captures result envelope and high-level status, but does not consistently enrich metadata from Kubernetes conditions/events for failure diagnosis.
- Missing structured cause details reduce parity with required release observability for cluster failures.

Required fix:
1. Fetch and persist Job and Pod condition snapshots.
2. Capture relevant Event reasons/messages and include compact summaries.
3. Include structured failure taxonomy fields (phase, reason, message, retryable).
4. Add tests covering API-available and simulated fallback modes.

### P1-3: Model manager datasets sync normalization

Where:
- external/ipfs_accelerate/ipfs_accelerate_py/model_manager.py

Issue:
- Model registration and access events are emitted, but usage-linkage events are not yet standardized around inference linkage schema.
- Observability queries in datasets may require normalized usage fields for direct joinability with inference runs.

Required fix:
1. Emit explicit model_inference_linked event on mark_model_used with run_id and inference cid.
2. Include normalized usage fields in both audit and provenance payloads.
3. Add contract tests that assert event payload completeness and consistency after usage updates.

## 4. Required Cross-Library Call Contracts (Per Subsystem)

### 4.1 Model Server (inference lifecycle)

Required call order:
1. DatasetsManager.log_event("inference_started", payload)
2. InferenceBackendManager.execute_task(...)
3. IPFSKitStorage.store(output_payload) -> output_cid
4. DatasetsManager.log_event("inference_completed" or "inference_failed", payload)
5. DatasetsManager.track_provenance("inference", payload)
6. InferenceBackendManager.finalize_inference_result(...)

Required payload keys:
- run_id
- task
- model
- backend_id
- backend_type
- endpoint
- protocol
- hardware_type
- placement_node
- output_cid
- provenance_cid
- status
- duration_ms
- error

### 4.2 API Endpoint Multiplexer (backend execution metadata)

Required call order:
1. select_backend_for_task(...)
2. execute backend method
3. record_request(...)
4. finalize_inference_result(...)
5. invoke configured result_recorder for storage/provenance

Required payload keys:
- selection_reason
- backend_id
- backend_type
- endpoint
- protocol and protocols
- hardware_type and hardware_types
- placement_node

### 4.3 Containerizer and Kubernetes manager (execution lifecycle)

Required call order:
1. Optional IPFSKitStorage.retrieve(model_artifact_cid)
2. Execute container/job
3. IPFSKitStorage.store(execution payload/logs) -> output_cid
4. DatasetsManager.log_event("container_execution_completed" or "container_execution_failed", payload)
5. DatasetsManager.track_provenance("container_execution", payload) or ProvenanceLogger.log_transformation(...)

Required payload keys:
- execution_id or job_id
- image
- command
- node_name
- namespace
- exit_code
- status
- execution_time_ms
- output_cid
- provenance_cid
- failure_reason
- failure_message

### 4.4 Agent orchestrator (workflow lineage)

Required call order:
1. Orchestrator attaches lineage and routing hints
2. Worker routes inference via backend-manager execute_task
3. Worker emits completion/failure lineage payload
4. DatasetsManager.log_event(workflow_dispatch/workflow_completed/workflow_failed)
5. DatasetsManager.track_provenance(workflow event type)

Required payload keys:
- workflow_id
- task_id
- model_id
- backend_id
- output_cid
- provenance_cid
- status
- error
- peer_id
- orchestrator_id

### 4.5 Model manager (artifact and usage lineage)

Required call order:
1. IPFSKitStorage.store(model/config/tokenizer artifacts)
2. DatasetsManager.log_event("model_registered", payload)
3. DatasetsManager.track_provenance("model_registration", payload)
4. Persist CID and revision lineage fields
5. On usage: DatasetsManager.log_event("model_inference_linked", payload)
6. On usage: DatasetsManager.track_provenance("model_usage", payload)

Required payload keys:
- model_id
- model_version
- revision_id
- parent_model_id
- model_cid
- config_cid
- tokenizer_cid
- last_run_id
- last_inference_cid
- inference_count
- last_used_at

## 5. Delivery Plan

### Phase 1 (P0 closure, 2-3 days)
1. Fix recorder signature mismatch and add regression coverage.
2. Replace HF server placeholders with canonical backend-manager execution path.
3. Add route-level persistence and provenance tests for completions, chat, embeddings, load, and unload.

### Phase 2 (P1 integration completeness, 3-5 days)
1. Normalize worker preferred backend types to BackendType.
2. Add Kubernetes conditions/events enrichment into execution metadata.
3. Standardize model usage-linkage events and test payload consistency.

### Phase 3 (hardening and CI, 2-3 days)
1. Expand call-matrix enforcement tests with negative-path assertions.
2. Add end-to-end scenario tests that verify call order across server -> multiplexer -> storage/datasets.
3. Regenerate readiness report from CI and block release on contract drift.

## 6. Validation Matrix

Required passing gates after implementation:
- external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py
- external/ipfs_accelerate/test/api/test_serving_call_matrix_enforcement.py
- external/ipfs_accelerate/test/api/test_task_orchestrator_backend_targeting.py
- external/ipfs_accelerate/test/test_unified_inference.py
- New: hf_model_server route contract suite for lifecycle persistence/provenance
- New: kubernetes event-enrichment contract suite
- New: model usage-linkage datasets payload contract suite

## 7. Definition Of Done

Done when all are true:
1. No canonical inference/model/container/workflow path can complete without the required IPFSKitStorage and DatasetsManager side effects for its lifecycle stage.
2. Model server endpoints use real backend execution and model lifecycle paths, not placeholders.
3. Routing and execution metadata are complete and queryable across backend manager, container backends, and orchestrator outputs.
4. Contract and regression tests enforce the call matrix and fail on drift.
5. Readiness evidence artifact is regenerated automatically with passing gates.
