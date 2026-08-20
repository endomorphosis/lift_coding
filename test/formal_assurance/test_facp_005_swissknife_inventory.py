"""FACP-005: SwissKnife authority and information-flow inventory gate.

Validates that ``swissknife_authority.json`` binds the exact SwissKnife
gitlink, that every browser-to-host authority and sensitive-flow edge carries
a reproducible source span, owner, trust label, negative test seed, and
removal/adaptation target, and that missing rights remain explicit without
legal inference.
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
    blob_text,
    current_head,
    superproject_gitlink,
    tree_path_exists,
)

REPORT_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "swissknife_authority.json"
)
SWISSKNIFE_ROOT = REPO_ROOT / "swissknife"

REQUIRED_EVIDENCE = {
    "browser policy/consent defaults",
    "tenant selection",
    "dry-run/live projection",
    "host dispatch",
    "secrets/paths/logs/prompts",
    "license/provenance",
}

REQUIRED_EDGE_FIELDS = (
    "edge_id",
    "category",
    "family",
    "title",
    "path",
    "symbol",
    "line_start",
    "line_end",
    "quote",
    "owner",
    "trust_label",
    "negative_test_seed",
    "removal_or_adaptation_target",
)

FORBIDDEN_RIGHTS_DISPOSITIONS = {
    "compatible",
    "compatibility_inferred",
    "inferred_compatible",
    "resolved",
    "no_conflict",
    "cleared",
    "spdx_ok",
}

FORBIDDEN_AUTHORITY_CONCLUSIONS = {
    "browser_authority_is_host_admission",
    "default_granted_consent_is_safe",
    "ui_confirmation_token_equals_host_policy",
}


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), f"missing inventory report: {REPORT_PATH}"
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _git_swissknife_head() -> str:
    commit = current_head(SWISSKNIFE_ROOT)
    assert len(commit) == 40
    return commit


def _gitlink_commit() -> str:
    return superproject_gitlink(REPO_ROOT, "HEAD", "swissknife")


def _read_span(commit: str, path: str, line_start: int, line_end: int) -> str:
    relative_path = str(Path(path).relative_to("swissknife"))
    lines = blob_text(SWISSKNIFE_ROOT, commit, relative_path).splitlines()
    assert 1 <= line_start <= line_end <= len(lines), (
        f"span out of range for {path}: {line_start}-{line_end} (file has {len(lines)} lines)"
    )
    return "\n".join(lines[line_start - 1 : line_end])


def _assert_quote_in_span(record: dict[str, Any], *, commit: str, label: str) -> None:
    path = record["path"]
    quote = record["quote"]
    span = _read_span(commit, path, int(record["line_start"]), int(record["line_end"]))
    assert quote in span, (
        f"{label} quote not reproducible at {path}:"
        f"{record['line_start']}-{record['line_end']}: {quote!r}"
    )
    for secondary in record.get("secondary_spans") or []:
        secondary_span = _read_span(
            commit,
            secondary["path"],
            int(secondary["line_start"]),
            int(secondary["line_end"]),
        )
        assert secondary["quote"] in secondary_span, (
            f"{label} secondary quote not reproducible at {secondary['path']}:"
            f"{secondary['line_start']}-{secondary['line_end']}: "
            f"{secondary['quote']!r}"
        )


def _assert_edge_complete(edge: dict[str, Any], *, commit: str, expected_category: str) -> None:
    for field in REQUIRED_EDGE_FIELDS:
        assert field in edge, f"{edge.get('edge_id', '<missing>')} missing {field}"
    assert edge["category"] == expected_category
    assert isinstance(edge["owner"], str) and edge["owner"]
    assert isinstance(edge["trust_label"], str) and edge["trust_label"]
    seed = edge["negative_test_seed"]
    assert isinstance(seed, dict)
    assert seed.get("id")
    assert seed.get("oracle")
    target = edge["removal_or_adaptation_target"]
    assert isinstance(target, dict)
    assert target.get("action")
    assert "follow_on" in target
    _assert_quote_in_span(edge, commit=commit, label=edge["edge_id"])


def test_report_task_and_schema_binding(report: dict[str, Any]) -> None:
    assert report["schema"] == "FACPSwissKnifeAuthorityInventory@1"
    assert report["task_id"] == "FACP-005"
    assert report["goal_id"] == "FACP-G010"
    assert report["bundle"] == "facp/inventory/swissknife"
    assert report["behavior_change"] is False
    assert report["discovery_is_not_completion"] is True
    assert set(report["evidence_subset"]) >= REQUIRED_EVIDENCE
    prohibited = set(report["prohibited_conclusions"])
    assert FORBIDDEN_AUTHORITY_CONCLUSIONS <= prohibited
    assert "infer_license_rights" in report["authority"]["prohibited_effects"]
    assert (
        "treat_default_granted_consent_as_accepted_evidence"
        in report["authority"]["prohibited_effects"]
    )


def test_source_binding_matches_exact_swissknife_gitlink(
    report: dict[str, Any],
) -> None:
    binding = report["source_binding"]
    assert binding["submodule_path"] == "swissknife"
    assert binding["gitlink_path"] == "swissknife"
    assert binding["planning_revision"] == binding["gitlink_commit"]
    current_gitlink = _gitlink_commit()
    assert _git_swissknife_head() == current_gitlink
    assert_historical_ancestor(SWISSKNIFE_ROOT, binding["gitlink_commit"], current_gitlink)
    assert binding["worktree_status"] == "clean"
    dirty = subprocess.run(
        ["git", "-C", str(SWISSKNIFE_ROOT), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert dirty == ""


def test_authority_edges_are_complete_and_reproducible(
    report: dict[str, Any],
) -> None:
    bound_commit = report["source_binding"]["gitlink_commit"]
    edges = report["authority_edges"]
    assert isinstance(edges, list) and len(edges) >= 10

    seen: set[str] = set()
    families = {edge["family"] for edge in edges}
    for required in (
        "browser_policy_consent_defaults",
        "tenant_selection",
        "dry_run_live_projection",
        "host_dispatch",
    ):
        assert required in families, f"missing authority family: {required}"

    for edge in edges:
        edge_id = edge["edge_id"]
        assert edge_id not in seen
        seen.add(edge_id)
        assert edge_id.startswith("SK-AUTH-")
        _assert_edge_complete(edge, commit=bound_commit, expected_category="authority_edge")
        assert edge["trust_label"] in report["trust_label_vocabulary"]


def test_sensitive_flow_edges_are_complete_and_reproducible(
    report: dict[str, Any],
) -> None:
    bound_commit = report["source_binding"]["gitlink_commit"]
    edges = report["sensitive_flow_edges"]
    assert isinstance(edges, list) and len(edges) >= 5

    seen: set[str] = set()
    families = {edge["family"] for edge in edges}
    assert "secrets_paths_logs_prompts" in families
    assert "dry_run_live_projection" in families

    blob = json.dumps(edges)
    assert "host_path" in blob
    assert "prompt" in blob.lower() or "[prompt redacted]" in blob
    assert "secret" in blob.lower() or "goose_secret_key" in blob

    for edge in edges:
        edge_id = edge["edge_id"]
        assert edge_id not in seen
        seen.add(edge_id)
        assert edge_id.startswith("SK-SENS-")
        _assert_edge_complete(edge, commit=bound_commit, expected_category="sensitive_flow")
        assert edge["trust_label"] in report["trust_label_vocabulary"]


def test_default_granted_consent_is_failing_seed_not_accepted_evidence(
    report: dict[str, Any],
) -> None:
    default_granted = next(
        edge for edge in report["authority_edges"] if edge["edge_id"] == "SK-AUTH-001"
    )
    assert "granted" in default_granted["quote"]
    assert default_granted["trust_label"] == "untrusted_browser"
    assert default_granted["removal_or_adaptation_target"]["keep"] is False
    seed = default_granted["negative_test_seed"]
    assert seed["id"] == "cx-sk-auth-default-granted-consent"
    assert "must not synthesize consent=granted" in seed["oracle"]

    constructed_allow = next(
        edge for edge in report["authority_edges"] if edge["edge_id"] == "SK-AUTH-002"
    )
    assert "allow" in constructed_allow["quote"]
    assert constructed_allow["trust_label"] == "browser_constructed_policy"

    acceptance = report["acceptance"]
    assert acceptance["default_granted_consent_is_failing_seed"] is True
    assert "SK-AUTH-001" in report["adaptation_disposition"]["remove_or_rewrite"]
    assert "SK-AUTH-002" in report["adaptation_disposition"]["remove_or_rewrite"]


def test_missing_rights_remain_explicit_without_legal_inference(
    report: dict[str, Any],
) -> None:
    bound_commit = report["source_binding"]["gitlink_commit"]
    gaps = report["missing_rights"]
    assert isinstance(gaps, list) and len(gaps) >= 2

    license_gap = next(gap for gap in gaps if gap["gap_id"] == "SK-RIGHTS-001")
    assert license_gap["disposition"] == "unresolved_human_legal_review"
    assert license_gap["inferred_compatibility"] is False
    assert license_gap["disposition"] not in FORBIDDEN_RIGHTS_DISPOSITIONS
    assert license_gap["trust_label"] == "rights_unresolved"
    assert license_gap["negative_test_seed"]["id"]
    assert license_gap["removal_or_adaptation_target"]["action"]

    declarations = license_gap["declarations"]
    assert any(item["declared_license"] == "" for item in declarations)
    assert any("AGPL" in str(item.get("declared_license")) for item in declarations)
    for item in declarations:
        _assert_quote_in_span(item, commit=bound_commit, label=f"rights:{item['path']}")

    missing = license_gap["missing_artifacts"]
    assert any(
        item["path"] == "swissknife/LICENSE.md" and item["status"] == "absent_in_exact_gitlink"
        for item in missing
    )
    assert not tree_path_exists(SWISSKNIFE_ROOT, bound_commit, "LICENSE.md")

    tenant_gap = next(gap for gap in gaps if gap["gap_id"] == "SK-RIGHTS-002")
    assert tenant_gap["family"] == "tenant_selection"
    assert tenant_gap["disposition"] == "explicit_gap_unresolved"
    assert tenant_gap["inferred_compatibility"] is False
    assert tenant_gap["negative_test_seed"]["id"]
    for item in tenant_gap["declarations"]:
        _assert_quote_in_span(item, commit=bound_commit, label=f"tenant-gap:{item['path']}")

    serialized = json.dumps(gaps)
    for forbidden in (
        "licenses_are_compatible",
        "inferred_compatible",
        "spdx_cleared",
        "no_conflict",
        "tenant_binding_satisfied",
    ):
        assert forbidden not in serialized

    assert report["acceptance"]["missing_rights_remain_explicit"] is True
    assert report["acceptance"]["license_rights_not_inferred"] is True


def test_inventory_covers_evidence_subset_topics(report: dict[str, Any]) -> None:
    blob = json.dumps(report).lower()
    assert "consent" in blob
    assert "dry_run" in blob or "dry-run" in blob
    assert "tenant" in blob
    assert "host" in blob and "dispatch" in blob
    assert "secret" in blob or "goose_secret_key" in blob
    assert "host_path" in blob
    assert "prompt" in blob
    assert "agpl" in blob
    assert "license" in blob
    assert "unresolved_human_legal_review" in blob

    families = {
        edge["family"] for edge in report["authority_edges"] + report["sensitive_flow_edges"]
    }
    assert "browser_policy_consent_defaults" in families
    assert "tenant_selection" in families or any(
        gap["family"] == "tenant_selection" for gap in report["missing_rights"]
    )
    assert "dry_run_live_projection" in families
    assert "host_dispatch" in families
    assert "secrets_paths_logs_prompts" in families
    assert any(gap["family"] == "license_provenance" for gap in report["missing_rights"])


def test_every_edge_has_removal_or_adaptation_and_owner_trust(
    report: dict[str, Any],
) -> None:
    edges = report["authority_edges"] + report["sensitive_flow_edges"]
    assert len(edges) >= 15
    for edge in edges:
        target = edge["removal_or_adaptation_target"]
        assert isinstance(target.get("follow_on"), list) and target["follow_on"]
        assert "keep" in target
        assert edge["owner"]
        assert edge["trust_label"] in report["trust_label_vocabulary"]
        assert edge["negative_test_seed"]["id"].startswith("cx-sk-")

    acceptance = report["acceptance"]
    for key in (
        "every_authority_edge_has_source_span",
        "every_authority_edge_has_owner",
        "every_authority_edge_has_trust_label",
        "every_authority_edge_has_negative_test_seed",
        "every_authority_edge_has_removal_or_adaptation_target",
        "every_sensitive_flow_edge_complete",
        "missing_rights_remain_explicit",
    ):
        assert acceptance[key] is True
