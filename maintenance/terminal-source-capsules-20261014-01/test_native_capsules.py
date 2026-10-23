"""Complete public native capsule replay and authority-preservation controls."""
from copy import deepcopy
from dataclasses import replace
import hashlib
import json
from pathlib import Path

import pytest

from native_capsules import (
    AUTHORITY, LIMITS, NativeCapsuleError, build_native_capsules, verify_native_capsules)


ROOT = Path(__file__).resolve().parent
TYPED = ROOT.parent / "terminal-typed-ir-proof-index-20261014-01"


@pytest.fixture(scope="module")
def actual_native_inputs():
    """Read only the named public structural report; no DB/CAS/source bodies."""
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest

    value = json.loads((TYPED / "experiment-03" / "result.json").read_bytes())["structural"]
    manifest, head = CodebaseIRManifest.from_dict(value["manifest"]), CodebaseHead.from_dict(value["head"])
    assert len(manifest.snapshot.entries) == 5
    assert len(manifest.semantic_state.symbols) == 57
    assert len(manifest.semantic_state.edges) == 382
    return manifest, head


@pytest.fixture(scope="module")
def actual_capsules(actual_native_inputs):
    return build_native_capsules(*actual_native_inputs)


def test_actual_sealed_bound_refusal_is_retained_before_distinct_generic_profile(actual_capsules):
    old = actual_capsules["sealed_adapter_outcome"]
    assert old["actual_adapter_called"] is True
    assert old["status"] == "refused"
    assert old["error_type"] == "NativeSemanticCapsuleError"
    assert old["error"] == "semantic inventory bound exceeded"
    assert old["limits"]["max_edges"] == 256
    assert old["edges"] == 382
    assert old["pinned_profile_modified"] is False
    assert old["records_dropped_to_fit"] is False
    assert actual_capsules["limits"]["max_edges"] == 512
    assert actual_capsules["profile"] != "terminal-native-semantic-capsule-set@1"


def test_complete_actual_inventory_survives_native_compilation(actual_native_inputs, actual_capsules):
    manifest, head = actual_native_inputs
    counts = actual_capsules["complete_inventory"]
    assert counts["source_entries"] == 5
    assert counts["symbols"] == counts["capsules"] == 57
    assert counts["edges"] == len(actual_capsules["semantic_links"]) == 382
    assert counts["artifacts"] == len(actual_capsules["artifact_facts"]) == 1
    assert all(counts[key] == 0 for key in ("dropped_symbols", "dropped_edges", "dropped_artifacts"))
    assert {row["capsule"]["stable_symbol_id"] for row in actual_capsules["capsules"]} == {
        row.stable_id for row in manifest.semantic_state.symbols}
    assert actual_capsules["producer"]["source_manifest_cid"] == manifest.cid
    assert actual_capsules["producer"]["repository_snapshot_cid"] == head.snapshot_cid
    assert actual_capsules["producer"]["repository_state_cid"] == manifest.semantic_state.state_cid
    assert actual_capsules["head"] == head.to_dict()


def test_every_native_block_byte_hash_cid_and_bound_replays(actual_capsules):
    from ipfs_datasets_py.logic.software_contracts.semantic_state.models import verify_block_bytes

    blocks = actual_capsules["blocks"]
    assert len(blocks) == actual_capsules["complete_inventory"]["block_count"] <= LIMITS["max_blocks"]
    for row in blocks:
        raw = bytes.fromhex(row["bytes_hex"])
        assert raw.hex() == row["bytes_hex"]
        assert len(raw) == row["bytes"]
        assert hashlib.sha256(raw).hexdigest() == row["sha256"]
        verify_block_bytes(row["cid"], raw)
    assert sum(row["bytes"] for row in blocks) == actual_capsules["complete_inventory"]["native_block_bytes"]
    assert actual_capsules["native_cold_incremental_equal"] is True
    assert actual_capsules["root_and_capsule_identity_preserved"] is True
    assert set(actual_capsules["supplemental_projection_cids"]) <= {row["cid"] for row in blocks}


def test_native_freshness_never_discharges_original_source_or_task_requirements(actual_capsules):
    assert actual_capsules["capsules"]
    for row in actual_capsules["capsules"]:
        assert row["freshness_scope"] == "supplied_immutable_historical_bundle_only"
        assert row["raw_source_required_by_experiment"] is True
        assert row["omission_authority"] is False
        assert row["original_source_expansion"]["raw_source_required_before_edit_or_proving"] is True
        assert row["original_source_expansion"]["proof_transfer"] is False
    for key in AUTHORITY:
        assert actual_capsules[key] is False
    assert actual_capsules["requires_actual_native_owner_observation_before_and_after_use"] is True
    assert actual_capsules["required_observation_api"] == "RepositoryCodebaseIndex.observe_current"
    assert actual_capsules["database_accessed"] is False
    assert actual_capsules["source_body_executed"] is False
    assert actual_capsules["provider_calls"] == actual_capsules["training_steps"] == actual_capsules["prover_invocations"] == 0


def test_exact_native_capsule_report_replays_all_data(actual_native_inputs, actual_capsules):
    replay = verify_native_capsules(*actual_native_inputs, actual_capsules)
    assert replay["data_verified"] is True
    assert replay["capsule_set_id"] == actual_capsules["capsule_set_id"]
    assert replay["complete_inventory"] == actual_capsules["complete_inventory"]
    assert all(replay[key] is False for key in AUTHORITY)


@pytest.mark.parametrize("change", ["capsule", "edge", "block", "bytes", "head", "authority", "raw_required"])
def test_modified_or_omitted_data_cannot_replay_the_full_capsule_set(actual_native_inputs, actual_capsules, change):
    value = deepcopy(actual_capsules)
    if change == "capsule":
        value["capsules"].pop()
    elif change == "edge":
        value["semantic_links"].pop()
    elif change == "block":
        value["blocks"].pop()
    elif change == "bytes":
        value["blocks"][0]["bytes_hex"] += "00"
    elif change == "head":
        value["head"]["generation"] += 1
    elif change == "authority":
        value["proof_authority"] = True
    else:
        value["capsules"][0]["raw_source_required_by_experiment"] = False
    with pytest.raises(NativeCapsuleError, match="complete generic native capsule replay differs"):
        verify_native_capsules(*actual_native_inputs, value)


def test_changed_full_head_does_not_replay_old_data_even_with_identical_manifest(actual_native_inputs, actual_capsules):
    manifest, head = actual_native_inputs
    changed = replace(head, generation=head.generation + 1)
    with pytest.raises(NativeCapsuleError, match="replay differs"):
        verify_native_capsules(manifest, changed, actual_capsules)
    # A new supplied head remains unverified historical data, never a live
    # receipt. Only the real owner may establish whether that head exists.
    new = build_native_capsules(manifest, changed)
    assert new["current_head_verified"] is False
    assert new["current_owner_verified"] is False
    assert new["head"] == changed.to_dict()


@pytest.mark.parametrize("change", ["mapping_manifest", "mapping_head", "manifest_subclass", "head_subclass"])
def test_fake_or_overridable_native_receipts_are_refused_before_conversion(actual_native_inputs, change):
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest

    manifest, head = actual_native_inputs
    if change == "mapping_manifest":
        manifest = manifest.to_dict()
    elif change == "mapping_head":
        head = head.to_dict()
    elif change == "manifest_subclass":
        class FakeManifest(CodebaseIRManifest):
            def to_dict(self):
                raise AssertionError("overridable conversion must not be called")
        manifest = FakeManifest(manifest.snapshot, manifest.semantic_state, manifest.ast_revision_id, manifest.units)
    else:
        class FakeHead(CodebaseHead):
            def to_dict(self):
                raise AssertionError("overridable conversion must not be called")
        head = FakeHead(head.repository_id, head.generation, head.manifest_cid,
            head.snapshot_cid, head.ast_revision_id, head.receipt_cid)
    with pytest.raises(NativeCapsuleError, match="exact native CodebaseIRManifest"):
        build_native_capsules(manifest, head)


def test_head_from_another_manifest_or_repository_is_refused(actual_native_inputs):
    from ipfs_datasets_py.duckdb_control.codebase_catalog import CodebaseHead

    manifest, head = actual_native_inputs
    changed = CodebaseHead("different:repository", head.generation, head.manifest_cid,
        head.snapshot_cid, "rev:different:repository:snapshot:" + head.snapshot_cid, head.receipt_cid)
    with pytest.raises(NativeCapsuleError, match="complete native head"):
        build_native_capsules(manifest, changed)


def test_snapshot_source_substitution_cannot_acquire_omission_authority(actual_native_inputs):
    from ipfs_datasets_py.logic.software_contracts.codebase_ir import CodebaseIRManifest

    manifest, head = actual_native_inputs
    value = manifest.to_dict()
    value["coverage"]["checked_properties"] = 1
    with pytest.raises(ValueError):
        CodebaseIRManifest.from_dict(value)
    # A bare public dictionary with a forged claim cannot bypass exact native
    # typed input checks, regardless of recomputable data hashes.
    with pytest.raises(NativeCapsuleError):
        build_native_capsules(value, head)


def test_bundle_export_is_integer_string_transport_without_learned_scalar_floats(actual_capsules):
    def visit(value):
        if type(value) is dict:
            for key, item in value.items():
                assert type(key) is str
                visit(item)
        elif type(value) is list:
            for item in value:
                visit(item)
        else:
            assert type(value) in (str, int, bool, type(None))
    visit(actual_capsules)
