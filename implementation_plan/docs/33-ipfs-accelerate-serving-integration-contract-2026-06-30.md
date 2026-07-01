# IPFS Accelerate Serving Integration Contract (2026-06-30)

Status: Authoritative contract for canonical model serving/runtime integration
Scope: `external/ipfs_accelerate/ipfs_accelerate_py` canonical serving surfaces only

## Canonical Runtime Entry Points

Authoritative entry points:
- Model server runtime: `ipfs_accelerate_py/hf_model_server/server.py`
- Unified service seam: `ipfs_accelerate_py/unified_inference_service.py`
- Endpoint multiplexer: `ipfs_accelerate_py/inference_backend_manager.py`
- Local containerizer: `ipfs_accelerate_py/docker_executor.py`
- Kubernetes backend: `ipfs_accelerate_py/container_backends/kubernetes/kubernetes.py`
- Agent orchestration runtime: `ipfs_accelerate_py/p2p_tasks/orchestrator.py`
- Agent execution runtime: `ipfs_accelerate_py/p2p_tasks/worker.py`
- Model registry runtime: `ipfs_accelerate_py/model_manager.py`

Non-canonical surfaces excluded from release gating:
- `ipfs_accelerate_py_legacy.py`
- `backup/`, `archive/`, `reorganization_backup*`
- mirrored nested submodule trees under `external/ipfs_accelerate`

## Required Cross-Library Call Matrix

## Inference Completion Contract

Owner:
- `unified_inference_service.py`
- `inference_backend_manager.py`

Required call order:
1. Optional input persistence: `IPFSKitStorage.store(...) -> input_cid`
2. Output persistence: `IPFSKitStorage.store(...) -> output_cid`
3. Audit event: `DatasetsManager.log_event("inference_completed" | "inference_failed", payload, ...)`
4. Provenance record: `DatasetsManager.track_provenance("inference", payload)`
5. Finalized metadata envelope: `InferenceBackendManager.finalize_inference_result(...)`

Required run metadata keys:
- `run_id`
- `task`
- `model`
- `backend_id`
- `backend_type`
- `endpoint`
- `input_cid`
- `output_cid`
- `provenance_cid`
- `status`
- `duration_ms`

## Model Artifact Registration Contract

Owner:
- `model_manager.py`

Required call order:
1. Store model/config/tokenizer artifacts: `IPFSKitStorage.store(...)`
2. Audit event: `DatasetsManager.log_event("model_registered" | "model_loaded", payload, ...)`
3. Provenance record: `DatasetsManager.track_provenance("model_registration" | "model_load", payload)`
4. Persist artifact linkage fields in model metadata store

Required model metadata keys:
- `model_id`
- `model_name`
- `model_version`
- `model_cid`
- `config_cid`
- `tokenizer_cid`
- `last_used_at`
- `inference_count`

## Container Execution Contract (Docker + Kubernetes)

Owner:
- `docker_executor.py`
- `container_backends/kubernetes/kubernetes.py`

Required call order:
1. Optional model materialization from CID: `IPFSKitStorage.retrieve(...)`
2. Execute container/job
3. Persist outputs/logs/artifacts: `IPFSKitStorage.store(...)`
4. Audit event: `DatasetsManager.log_event("container_execution_completed" | "container_execution_failed", payload, ...)`
5. Provenance record: `ProvenanceLogger.log_transformation(...)` or datasets provenance equivalent

Required execution metadata keys:
- `execution_id`
- `image`
- `exit_code`
- `status`
- `execution_time_ms`
- `output_cid`
- `provenance_cid`
- `node_name`
- `namespace`

## Orchestrator Task Lifecycle Contract

Owner:
- `p2p_tasks/orchestrator.py`
- `p2p_tasks/worker.py`

Required call order:
1. Dispatch with lineage context (`workflow_id`, `task_id`, `model_id`, policies)
2. Route inference execution via `InferenceBackendManager.execute_task(...)`
3. Persist completion/failure lineage metadata and CIDs
4. Emit workflow audit/provenance events via datasets integration

Required task result metadata keys:
- `workflow_id`
- `task_id`
- `model_id`
- `backend_id`
- `output_cid`
- `provenance_cid`
- `status`
- `error`

## Contract Test References

The following tests are canonical contract/baseline gates:
- `external/ipfs_accelerate/test/api/test_serving_readiness_contracts.py`
- `external/ipfs_accelerate/test/api/test_serving_benchmark_contracts.py`
- `external/ipfs_accelerate/test/api/test_serving_integration_contract_doc.py`

## Enforcement Notes

- All new serving features must attach to one of the canonical owners above.
- Any path that bypasses this call order is a contract violation.
- Release readiness requires this contract, readiness gates, benchmark gates, and evidence artifact generation to remain aligned.
