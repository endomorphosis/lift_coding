"""FACP-004: Kit evidence, backend, and proof-role inventory gate.

Validates that ``kit_evidence.json`` preserves Kit's honest distinctions,
binds exact adapter seams, records zero live-qualified backends from current
tree evidence, and does not propose a weaker replacement.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from facp_historical_git import (
    assert_historical_ancestor,
    current_head,
    superproject_gitlink,
)

REPORT_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "kit_evidence.json"
)
KIT_ROOT = REPO_ROOT / "external" / "ipfs_kit"
KIT_MANIFEST = KIT_ROOT / "docs" / "runtime_readiness" / "backend_support_manifest.json"
KIT_SUPPORT_MATRIX = KIT_ROOT / "docs" / "kernel_vfs" / "support_matrix.json"
KIT_EXTERNAL_RECEIPT_INDEX = (
    KIT_ROOT / "docs" / "runtime_readiness" / "backend_external_receipts" / "index.json"
)

REQUIRED_DISTINCTION_KEYS = (
    "kernel_vfs_claim_classes",
    "backend_support_tiers",
    "configured_selected_states",
    "proof_roles",
    "cas_wal_recovery",
    "receipt_freshness",
)

REQUIRED_CLAIM_CLASSES = ("hermetic", "conditional", "live")
REQUIRED_PROOF_ROLES = ("candidate", "admitted", "current")
REQUIRED_CONFIG_STATES = (
    "absent",
    "configured",
    "selected",
    "receipt-required",
    "unsupported",
)


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), f"missing inventory report: {REPORT_PATH}"
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def kit_manifest() -> dict[str, Any]:
    assert KIT_MANIFEST.is_file(), f"missing Kit support manifest: {KIT_MANIFEST}"
    payload = json.loads(KIT_MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def kit_support_matrix() -> dict[str, Any]:
    assert KIT_SUPPORT_MATRIX.is_file(), f"missing Kernel VFS support matrix: {KIT_SUPPORT_MATRIX}"
    payload = json.loads(KIT_SUPPORT_MATRIX.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _git_kit_head() -> str:
    return current_head(KIT_ROOT)


def _gitlink_commit() -> str:
    return superproject_gitlink(REPO_ROOT, "HEAD", "external/ipfs_kit")


def test_report_task_and_schema_binding(report: dict[str, Any]) -> None:
    assert report["task_id"] == "FACP-004"
    assert report["goal_id"] == "FACP-G010"
    assert report["schema"] == "FACPKitEvidenceInventory@1"
    assert report["behavior_change"] is False
    assert report["bundle"] == "facp/inventory/kit"
    assert set(report["evidence_subset"]) >= {
        "hermetic_conditional_live_support",
        "configured_selected_states",
        "candidate_admitted_current_proof_roles",
        "cas_wal_recovery",
        "receipt_freshness",
    }


def test_source_binding_matches_exact_kit_gitlink(report: dict[str, Any]) -> None:
    binding = report["source_binding"]
    assert binding["submodule_path"] == "external/ipfs_kit"
    assert binding["planning_revision"] == binding["gitlink_commit"]
    current_gitlink = _gitlink_commit()
    assert _git_kit_head() == current_gitlink
    assert_historical_ancestor(KIT_ROOT, binding["gitlink_commit"], current_gitlink)
    assert binding["worktree_status"] == "clean"
    dirty = subprocess.run(
        ["git", "-C", str(KIT_ROOT), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert dirty == ""


def test_preserves_honest_distinctions(
    report: dict[str, Any], kit_support_matrix: dict[str, Any]
) -> None:
    distinctions = report["honest_distinctions"]
    for key in REQUIRED_DISTINCTION_KEYS:
        assert key in distinctions, f"missing distinction section: {key}"

    claim_classes = distinctions["kernel_vfs_claim_classes"]["classes"]
    for name in REQUIRED_CLAIM_CLASSES:
        assert name in claim_classes
        assert claim_classes[name]["id"] == f"claim:{name}"

    matrix_classes = kit_support_matrix["claim_classes"]
    for name in REQUIRED_CLAIM_CLASSES:
        assert name in matrix_classes
        assert claim_classes[name]["promotion_power"] == matrix_classes[name]["promotion_power"]

    assert kit_support_matrix["policy"]["hermetic_green_is_not_live"] is True
    assert (
        "hermetic_green_is_not_live"
        in distinctions["kernel_vfs_claim_classes"]["policy_invariants"]
    )

    tiers = distinctions["backend_support_tiers"]
    for value in (
        "production",
        "conditional",
        "configuration-only",
        "experimental",
        "unsupported",
    ):
        assert value in tiers["inventory_values"]
    assert "parallel_to_kernel_vfs" in tiers

    ladder_states = {
        entry["state"] for entry in distinctions["configured_selected_states"]["ladder"]
    }
    for state in REQUIRED_CONFIG_STATES:
        assert state in ladder_states

    roles = {entry["role"] for entry in distinctions["proof_roles"]["roles"]}
    for role in REQUIRED_PROOF_ROLES:
        assert role in roles

    transport = distinctions["proof_roles"]["proof_certificate_transport"]
    assert transport["role"] == "immutable_bytes_cas_transport_only"
    assert "never" in transport["explicit_non_authority"].lower()


def test_identifies_exact_adapter_seams(report: dict[str, Any]) -> None:
    seams = report["adapter_seams"]
    assert isinstance(seams, list) and len(seams) >= 8
    seen_ids: set[str] = set()
    for seam in seams:
        seam_id = seam["id"]
        assert seam_id not in seen_ids
        seen_ids.add(seam_id)
        path = REPO_ROOT / seam["path"]
        assert path.is_file(), f"adapter seam path missing: {seam['path']}"
        assert isinstance(seam["symbols"], list) and seam["symbols"]
        assert isinstance(seam["role"], str) and seam["role"]

    required_ids = {
        "handsfree_ipfs_kit_adapter",
        "backend_inventory_spec",
        "provider_adapter_catalog",
        "hermetic_filesystem_adapter",
        "hermetic_ipfs_fixture_adapter",
        "durable_state_root_adapter",
        "proof_certificate_store_transport",
        "semantic_governor_promotion",
        "legacy_vfs_adapter",
        "mcp_operation_adapter",
    }
    assert required_ids <= seen_ids


def test_zero_live_qualified_backends(report: dict[str, Any], kit_manifest: dict[str, Any]) -> None:
    live = report["live_qualification"]
    assert live["live_qualified_backend_count"] == 0
    assert live["storage_selectable_count"] == 0
    assert live["inventory_production_count"] == 0
    assert live["live_production_count"] == 0
    assert live["zero_qualified_is_valid_honest_state"] is True

    summary = kit_manifest["summary"]
    assert summary["production_count"] == 0
    assert summary["live_production_count"] == 0
    assert summary["storage_selectable_count"] == 0
    assert summary["honesty"]["production_backends_at_join"] == 0
    assert summary["honesty"]["silent_pass_on_missing_evidence"] == 0

    selectable = [
        backend for backend in kit_manifest["backends"] if backend["routing"]["storage_selectable"]
    ]
    assert selectable == []

    receipt_index = json.loads(KIT_EXTERNAL_RECEIPT_INDEX.read_text(encoding="utf-8"))
    assert receipt_index.get("receipts") == []
    assert (
        report["honest_distinctions"]["receipt_freshness"]["external_receipt_authority"][
            "active_receipts"
        ]
        == 0
    )

    iroh = live["sole_storage_capable_inventory_entry"]
    assert iroh["canonical_name"] == "iroh"
    assert iroh["storage_selectable"] is False
    assert iroh["inventory_tier"] == "conditional"
    assert iroh["availability"] == "receipt-required"

    manifest_iroh = next(
        backend for backend in kit_manifest["backends"] if backend["canonical_name"] == "iroh"
    )
    assert manifest_iroh["routing"]["storage_selectable"] is False
    assert manifest_iroh["availability"] == "receipt-required"
    assert manifest_iroh["live_tier"] == "conditional"


def test_does_not_propose_weaker_replacement(report: dict[str, Any]) -> None:
    forbidden = report["weaker_replacements_forbidden"]
    assert isinstance(forbidden, list) and len(forbidden) >= 8
    collapses = {entry["collapse"] for entry in forbidden}
    required = {
        "hermetic_equals_live",
        "inventory_tier_equals_live_tier_equals_storage_selectable",
        "configured_equals_selected",
        "candidate_equals_admitted_equals_current",
        "stale_or_empty_receipts_equal_current_evidence",
        "zero_live_backends_is_a_defect_to_paper_over",
        "proof_certificate_transport_equals_reuse_oracle",
        "kernel_vfs_claim_classes_merged_with_backend_support_tiers",
    }
    assert required <= collapses
    for entry in forbidden:
        assert entry["reason"]

    disposition = report["adaptation_disposition"]
    assert disposition["replacement_policy"] == "adapt_not_replace"
    assert "weaken" not in disposition["for_facp_015"].lower()

    acceptance = report["acceptance"]
    assert acceptance["preserves_honest_distinctions"] is True
    assert acceptance["identifies_exact_adapter_seams"] is True
    assert acceptance["live_qualified_backends"] == 0
    assert acceptance["proposes_weaker_replacement"] is False

    prohibited = report["authority"]["prohibited_effects"]
    assert "relabel_hermetic_evidence_as_live" in prohibited
    assert "propose_weaker_replacement_semantics" in prohibited


def test_key_encoding_tests_and_cas_wal_paths_exist(report: dict[str, Any]) -> None:
    for relative in report["key_encoding_tests"]:
        assert (REPO_ROOT / relative).is_file(), f"missing encoding test: {relative}"

    cas_wal = report["honest_distinctions"]["cas_wal_recovery"]
    for section in ("cas", "wal", "recovery"):
        for relative in cas_wal[section]["paths"]:
            assert (REPO_ROOT / relative).is_file(), f"missing {section} path: {relative}"
        assert cas_wal[section]["invariants"]

    for role_entry in report["honest_distinctions"]["proof_roles"]["roles"]:
        for relative in role_entry["paths"]:
            assert (REPO_ROOT / relative).is_file(), f"missing proof-role path: {relative}"
