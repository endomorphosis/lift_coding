"""A distinct bounded profile over the generic native SemanticCapsule APIs.

The sealed terminal adapter's 256-edge refusal remains an observed refusal.
This experiment retains the complete five-file native state under its own
explicit 512-edge envelope. Capsule freshness compares the supplied immutable
bundle with itself; current-source/head ownership must be checked separately
by the actual native owner before and after use. No raw-source substitution,
behavioral proof, task satisfaction, or supervisor admission is established.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json


SCHEMA = "terminal-source-native-capsules@1"
PROFILE = "five-public-source-generic-semantic-capsules-57-symbols-512-edges@1"
PATHS = frozenset({
    "headless-terminal/environment/base_terminal.py",
    "feal-differential-cryptanalysis/environment/feal.py",
    "break-filter-js-from-html/environment/filter.py",
    "llm-inference-batching-scheduler/environment/task_file/scripts/baseline_packer.py",
    "llm-inference-batching-scheduler/environment/task_file/scripts/cost_model.py",
})
LIMITS = {"source_entries": 5, "max_symbols": 57, "max_edges": 512,
    "max_blocks": 1024, "max_source_file_bytes": 8192, "max_source_total_bytes": 15788,
    "max_state_bytes": 1048576, "max_native_block_bytes": 8 * 1024**2,
    "max_report_bytes": 8 * 1024**2}
AUTHORITY = {name: False for name in (
    "proof_authority", "execution_authority", "completion_authority", "mutation_authority",
    "omission_authority", "source_semantics_verified", "runtime_behavior_verified",
    "current_owner_verified", "current_head_verified", "source_origin_verified",
    "production_admitted", "full_task_satisfaction_proved", "source_model_equivalence_proved",
    "training_convergence_proved", "capsule_native_freshness_grants_source_omission")}


class NativeCapsuleError(ValueError):
    """The complete native data or this distinct bounded profile is invalid."""


def _need(condition, message):
    if not condition:
        raise NativeCapsuleError(message)


def _bytes(value):
    from ipfs_datasets_py.logic.software_contracts.content import canonical_dag_json_bytes
    try:
        return canonical_dag_json_bytes(value)
    except (TypeError, ValueError, RecursionError) as error:
        raise NativeCapsuleError("finite native canonical DAG JSON required") from error


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True)
class _NativeInput:
    repository_id: str
    symbols: tuple
    artifacts: tuple
    edges: tuple
    extractor_name: str
    extractor_version: str
    schema: str
    producer: object
    analysis_limitations: tuple


def _inputs(manifest, expected_head):
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest, CodebaseUnit
    from ipfs_datasets_py.logic.software_contracts.semantic_index.models import (
        ArtifactRecord, DependencyEdge, RepositoryState, SourceSpan, SymbolRecord)
    from ipfs_datasets_py.logic.software_contracts.semantic_index.snapshot import RepositorySnapshot, SnapshotEntry

    _need(type(manifest) is CodebaseIRManifest and type(expected_head) is CodebaseHead,
        "exact native CodebaseIRManifest and complete CodebaseHead required")
    _need(type(manifest.snapshot) is RepositorySnapshot and type(manifest.semantic_state) is RepositoryState,
        "exact native snapshot and semantic state required")
    for values, kind in ((manifest.snapshot.entries, SnapshotEntry), (manifest.units, CodebaseUnit),
        (manifest.semantic_state.symbols, SymbolRecord), (manifest.semantic_state.artifacts, ArtifactRecord),
        (manifest.semantic_state.edges, DependencyEdge)):
        _need(all(type(item) is kind for item in values), "exact immutable nested native records required")
    _need(all(item.span is None or type(item.span) is SourceSpan
        for item in (*manifest.semantic_state.symbols, *manifest.semantic_state.edges)),
        "exact native original source spans required")
    snapshot, state = manifest.snapshot, manifest.semantic_state
    _need(len(snapshot.entries) == LIMITS["source_entries"] and {entry.path for entry in snapshot.entries} == PATHS,
        "exact five named public source snapshot entries required")
    _need(all(not entry.is_opaque and type(entry.size_bytes) is int
        and 0 < entry.size_bytes <= LIMITS["max_source_file_bytes"] for entry in snapshot.entries),
        "complete bounded nonopaque native source inventory required")
    _need(sum(entry.size_bytes for entry in snapshot.entries) == LIMITS["max_source_total_bytes"],
        "exact admitted public source byte membership differs")
    _need(0 < len(state.symbols) <= LIMITS["max_symbols"] and len(state.edges) <= LIMITS["max_edges"],
        "distinct generic capsule profile inventory bound exceeded")
    _need(len(_bytes(state.to_dict())) <= LIMITS["max_state_bytes"], "native state byte bound exceeded")
    original_manifest, original_head = _bytes(manifest.to_dict()), _bytes(expected_head.to_dict())
    try:
        manifest = CodebaseIRManifest.from_dict(json.loads(original_manifest))
        expected_head = CodebaseHead.from_dict(json.loads(original_head))
    except (TypeError, ValueError, KeyError) as error:
        raise NativeCapsuleError("native structural roundtrip failed") from error
    _need(expected_head.repository_id == manifest.snapshot.repository_id
        and expected_head.manifest_cid == manifest.cid
        and expected_head.snapshot_cid == manifest.snapshot.snapshot_cid
        and expected_head.ast_revision_id == manifest.ast_revision_id,
        "complete native head does not bind the exact structural manifest")
    return manifest, expected_head


def _limitations(state):
    from ipfs_datasets_py.logic.software_contracts.semantic_state.models import AnalysisLimitation
    rows = [AnalysisLimitation(code="structural_capsules_no_runtime_or_omission_authority",
        message="Every original source must remain available and be read before editing or proving; capsule freshness is relative to the supplied historical bundle only.",
        confidence="opaque")]
    for symbol in state.symbols:
        if symbol.confidence != "exact":
            rows.append(AnalysisLimitation(code="symbol_confidence:" + symbol.confidence,
                message="Original native symbol confidence retained without source substitution authority.",
                subject_id=symbol.stable_id, confidence=symbol.confidence))
    for edge in state.edges:
        if edge.confidence != "exact":
            rows.append(AnalysisLimitation(code="edge_confidence:" + edge.confidence,
                message="Original native dependency confidence and unresolved targets retained.",
                subject_id=edge.edge_id, confidence=edge.confidence))
    return tuple(sorted(rows, key=lambda row: row.limitation_cid))


def _complete_projection_blocks(bundle, state, binding_set):
    from ipfs_datasets_py.logic.software_contracts.semantic_state.api import view_semantic_state_bundle
    from ipfs_datasets_py.logic.software_contracts.semantic_state.bindings import relevant_binding_projection_for_symbol
    from ipfs_datasets_py.logic.software_contracts.semantic_state.models import EnvironmentBindingSet, SemanticStateBundle

    view, blocks = view_semantic_state_bundle(bundle), dict(bundle.blocks)
    original = set(blocks)
    for symbol in state.symbols:
        membership = relevant_binding_projection_for_symbol(symbol, binding_set)
        selected = EnvironmentBindingSet(bindings=tuple(item for item in binding_set.bindings
            if item.binding_id in membership.binding_ids))
        projection = relevant_binding_projection_for_symbol(symbol, selected)
        _need(projection.projection_cid == view.capsule(symbol.stable_id).relevant_binding_projection_cid,
            "native relevant binding projection identity changed")
        raw = _bytes(projection.identity_payload())
        _need(projection.projection_cid not in blocks or blocks[projection.projection_cid] == raw,
            "native projection block bytes conflict")
        blocks[projection.projection_cid] = raw
    return SemanticStateBundle(root=bundle.root, blocks=blocks), sorted(set(blocks) - original)


def build_native_capsules(manifest, expected_head):
    """Build all native capsules and blocks without source, storage or job I/O.

    A fully populated input binding is data, not a receipt of current ownership.
    The caller must use the real native structural owner at each use boundary.
    """
    from benchmarks.agent_supervisor.container_coding.terminal_native_semantic_capsule import (
        LIMITS as sealed_limits, NativeSemanticCapsuleError, build_native_semantic_capsule_set)
    from ipfs_datasets_py.logic.software_contracts.content import cid_for_structured
    from ipfs_datasets_py.logic.software_contracts.semantic_state.api import (
        build_semantic_state, verify_semantic_state_bundle, view_semantic_state_bundle)
    from ipfs_datasets_py.logic.software_contracts.semantic_state.bindings import build_environment_binding_set
    from ipfs_datasets_py.logic.software_contracts.semantic_state.capsules import (
        compile_semantic_capsules, verify_capsule_compile_result)
    from ipfs_datasets_py.logic.software_contracts.semantic_state.freshness import (
        assess_capsule_freshness, is_safe_substitute, requires_raw_source)
    from ipfs_datasets_py.logic.software_contracts.semantic_state.models import SemanticStateProducer

    manifest, expected_head = _inputs(manifest, expected_head)
    state, snapshot = manifest.semantic_state, manifest.snapshot
    try:
        bounded = build_native_semantic_capsule_set(manifest=manifest, expected_head=expected_head)
    except NativeSemanticCapsuleError as error:
        sealed_outcome = {"schema": "sealed-native-capsule-profile-outcome@1", "status": "refused",
            "actual_adapter_called": True, "error_type": type(error).__name__, "error": str(error),
            "limits": dict(sealed_limits), "symbols": len(state.symbols), "edges": len(state.edges),
            "pinned_profile_modified": False, "records_dropped_to_fit": False}
    else:
        sealed_outcome = {"schema": "sealed-native-capsule-profile-outcome@1", "status": "accepted",
            "actual_adapter_called": True, "capsule_set_id": bounded["capsule_set_id"],
            "limits": dict(sealed_limits), "symbols": len(state.symbols), "edges": len(state.edges),
            "pinned_profile_modified": False, "records_dropped_to_fit": False}
    producer = SemanticStateProducer(repository_state_cid=state.state_cid,
        repository_snapshot_cid=snapshot.snapshot_cid, git_commit_oid_or_null=snapshot.git_commit,
        git_tree_oid_or_null=snapshot.git_tree, source_manifest_cid=manifest.cid,
        semantic_index_schema=state.schema, extractor_name=state.extractor_name,
        extractor_version=state.extractor_version)
    limitations = _limitations(state)
    supplied = _NativeInput(state.repository_id, tuple(state.symbols), tuple(state.artifacts),
        tuple(state.edges), state.extractor_name, state.extractor_version, state.schema,
        producer, limitations)
    cold = build_semantic_state(supplied, environment_bindings=())
    verify_semantic_state_bundle(cold)
    _need(cold.root.producer.to_dict() == producer.to_dict(), "native full producer binding differs")
    incremental = build_semantic_state(supplied, environment_bindings=(), previous_bundle=cold)
    verify_semantic_state_bundle(incremental)
    _need(cold.root.to_dict() == incremental.root.to_dict() and dict(cold.blocks) == dict(incremental.blocks),
        "cold and incremental native bundle bytes differ")
    binding_set = build_environment_binding_set((), repository_state=state)
    _need(binding_set.binding_set_cid == cold.root.environment_binding_set_cid, "native binding set differs")
    cold, supplemental = _complete_projection_blocks(cold, state, binding_set)
    incremental, incremental_supplemental = _complete_projection_blocks(incremental, state, binding_set)
    verify_semantic_state_bundle(cold)
    verify_semantic_state_bundle(incremental)
    _need(supplemental == incremental_supplemental and cold.root.to_dict() == incremental.root.to_dict()
        and dict(cold.blocks) == dict(incremental.blocks), "complete projection block replay differs")
    _need(len(cold.blocks) <= LIMITS["max_blocks"]
        and sum(len(raw) for raw in cold.blocks.values()) <= LIMITS["max_native_block_bytes"],
        "complete generic native bundle exceeds its distinct finite envelope")
    view = view_semantic_state_bundle(cold)
    compiled = compile_semantic_capsules(state, binding_set=binding_set)
    verify_capsule_compile_result(compiled)
    _need(compiled.capsule_index_cid == cold.root.capsule_index_cid, "native capsule index differs")
    entries = {entry.path: entry for entry in snapshot.entries}
    units = {unit.source_key: unit for unit in manifest.units}
    capsules = []
    for symbol in state.symbols:
        capsule = view.capsule(symbol.stable_id)
        fact = view.symbol_fact(symbol.stable_id)
        _need(capsule.to_dict() == compiled.capsule(symbol.stable_id).to_dict()
            and capsule.source_cid == symbol.source_cid and capsule.version_cid == symbol.version_cid
            and capsule.symbol_fact_cid == fact.fact_cid and fact.symbol.to_dict() == symbol.to_dict(),
            "complete native capsule/symbol/source join differs")
        freshness = assess_capsule_freshness(capsule, current_state=view)
        entry = entries[symbol.module_path]
        unit = units[entry.source_key]
        capsules.append({"capsule": capsule.to_dict(), "native_freshness": freshness.to_dict(),
            "native_requires_raw_source": requires_raw_source(freshness),
            "native_safe_substitute_against_supplied_bundle": is_safe_substitute(freshness),
            "freshness_scope": "supplied_immutable_historical_bundle_only",
            "raw_source_required_by_experiment": True, "omission_authority": False,
            "original_source_expansion": {"path": entry.path, "source_cid": entry.source_cid,
                "entry_cid": entry.entry_cid, "source_bytes": entry.size_bytes,
                "source_span": None if symbol.span is None else symbol.span.to_dict(),
                "stable_symbol_id": symbol.stable_id, "version_cid": symbol.version_cid,
                "ast_cid": unit.ast_cid, "snapshot_cid": snapshot.snapshot_cid,
                "raw_source_required_before_edit_or_proving": True, "proof_transfer": False}})
    artifacts = [view.artifact_fact(item.artifact_id).to_dict() for item in state.artifacts]
    links = [view.semantic_link(item.edge_id).to_dict() for item in state.edges]
    retained_limitations = [view.analysis_limitation(item.limitation_cid).to_dict() for item in limitations]
    result = {"schema": SCHEMA, "profile": PROFILE, "head": expected_head.to_dict(),
        "manifest_cid": manifest.cid, "snapshot_cid": snapshot.snapshot_cid,
        "semantic_state_cid": state.state_cid, "producer": producer.to_dict(),
        "native_root": cold.root.to_dict(), "environment_bindings": binding_set.to_dict(),
        "capsules": capsules, "artifact_facts": artifacts, "semantic_links": links,
        "analysis_limitations": retained_limitations,
        "blocks": [{"cid": cid, "bytes": len(raw), "sha256": _sha(raw), "bytes_hex": raw.hex()}
            for cid, raw in sorted(cold.blocks.items())],
        "source_bindings": [{"path": entry.path, "source_cid": entry.source_cid,
            "entry_cid": entry.entry_cid, "bytes": entry.size_bytes, "source_key": entry.source_key,
            "ast_cid": units[entry.source_key].ast_cid} for entry in snapshot.entries],
        "complete_inventory": {"source_entries": len(snapshot.entries), "symbols": len(state.symbols),
            "edges": len(state.edges), "artifacts": len(state.artifacts), "capsules": len(capsules),
            "block_count": len(cold.blocks), "native_block_bytes": sum(len(raw) for raw in cold.blocks.values()),
            "dropped_symbols": 0, "dropped_edges": 0, "dropped_artifacts": 0},
        "sealed_adapter_outcome": sealed_outcome,
        "native_cold_incremental_equal": True, "supplemental_projection_cids": supplemental,
        "supplemental_projection_source": "native relevant_binding_projection_for_symbol over full and selected native binding sets",
        "root_and_capsule_identity_preserved": True, "limits": dict(LIMITS),
        "required_source_policy": "expand exact originals before editing or proving; freshness alone cannot discharge this requirement",
        "requires_actual_native_owner_observation_before_and_after_use": True,
        "required_observation_api": "RepositoryCodebaseIndex.observe_current",
        "source_body_executed": False, "database_accessed": False, "provider_calls": 0,
        "training_steps": 0, "prover_invocations": 0, **AUTHORITY}
    result["capsule_set_id"] = cid_for_structured(result)
    _need(len(_bytes(result)) <= LIMITS["max_report_bytes"], "complete generic capsule report byte bound exceeded")
    return result


def verify_native_capsules(manifest, expected_head, expected):
    """Rebuild all native data exactly; validate no live ownership or proving call."""
    _need(type(expected) is dict, "plain complete native capsule report required")
    raw = _bytes(expected)
    _need(len(raw) <= LIMITS["max_report_bytes"], "complete capsule report byte bound exceeded")
    observed = build_native_capsules(manifest, expected_head)
    _need(raw == _bytes(observed), "complete generic native capsule replay differs")
    return {"schema": "terminal-source-native-capsule-replay@1", "data_verified": True,
        "capsule_set_id": observed["capsule_set_id"], "native_root_cid": observed["native_root"]["root_cid"],
        "complete_inventory": observed["complete_inventory"], "native_cold_incremental_equal": True,
        "required_source_policy": observed["required_source_policy"],
        "requires_actual_native_owner_observation_before_and_after_use": True,
        **AUTHORITY}


__all__ = ["SCHEMA", "PROFILE", "LIMITS", "AUTHORITY", "NativeCapsuleError",
           "build_native_capsules", "verify_native_capsules"]
