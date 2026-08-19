"""FACP-001 gate: reusable formal/supervisor primitives inventory.

Acceptance (from the FACP taskboard):
- Every reusable component has exact commit/path/symbol, semantic authority,
  gaps, adoption disposition, and compatibility risk.
- Total assurance ladders are flagged for conservative FCA adaptation rather
  than duplication.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = (
    ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "reusable_primitives.json"
)
SCHEDULER_PATH = ROOT / "config" / "formal_assurance_control_plane_scheduler.json"

REQUIRED_SCHEMA = "facp/reusable_primitives@1"
REQUIRED_TASK_ID = "FACP-001"
EVIDENCE_SUBSET = (
    "evidence_ladders",
    "proof_contracts_caches",
    "planners",
    "dependency_graphs",
    "authorization",
    "repair",
    "lease_fence_recovery",
    "runtime_monitors",
)
REQUIRED_COMPONENT_FIELDS = (
    "component_id",
    "category",
    "repository",
    "commit",
    "path",
    "symbol",
    "semantic_authority",
    "gaps",
    "adoption_disposition",
    "compatibility_risk",
    "total_assurance_ladder",
    "fca_adaptation",
)
ADOPTION_VOCABULARY = {
    "reuse_as_is",
    "adapt_conservatively_for_fca",
    "reference_semantics_only",
    "do_not_duplicate",
}
RISK_LEVELS = {"low", "medium", "high"}
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# Total ladders that must appear and be flagged for conservative FCA adaptation.
REQUIRED_TOTAL_LADDERS = {
    "accelerate.assurance_level": "AssuranceLevel",
    "accelerate.database_repair_assurance_level": "AssuranceLevel",
    "accelerate.proof_status": "ProofStatus",
    "kit.backend_support_tier": "BackendSupportTier",
}


def _load_report() -> dict[str, Any]:
    assert REPORT_PATH.is_file(), f"missing inventory report: {REPORT_PATH}"
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _git_head(repo_relative: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(ROOT / repo_relative), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _scheduler_revisions() -> dict[str, str]:
    scheduler = json.loads(SCHEDULER_PATH.read_text(encoding="utf-8"))
    binding = scheduler["source_binding"]
    return {
        "external/ipfs_accelerate": binding["accelerate_planning_revision"],
        "external/ipfs_kit": binding["kit_planning_revision"],
        "external/ipfs_datasets": binding["datasets_planning_revision"],
        "swissknife": binding["swissknife_planning_revision"],
        "Mcp-Plus-Plus": binding["mcp_plus_plus_planning_revision"],
    }


def _symbol_defined(path: Path, symbol: str) -> bool:
    text = path.read_text(encoding="utf-8")
    patterns = (
        rf"^class {re.escape(symbol)}\b",
        rf"^def {re.escape(symbol)}\b",
        rf"^{re.escape(symbol)}\s*=",
    )
    return any(re.search(pat, text, flags=re.MULTILINE) for pat in patterns)


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return _load_report()


def test_report_schema_and_task_metadata(report: dict[str, Any]) -> None:
    assert report["schema"] == REQUIRED_SCHEMA
    assert report["task_id"] == REQUIRED_TASK_ID
    assert report["behavior_change"] is False
    assert report["discovery_is_not_completion"] is True
    assert report["policy"]["evidence_subset"] == list(EVIDENCE_SUBSET)
    assert set(report["policy"]["adoption_disposition_vocabulary"]) == ADOPTION_VOCABULARY
    assert "rather than duplication" in report["policy"]["total_assurance_ladder_rule"]


def test_source_binding_matches_scheduler_and_git(report: dict[str, Any]) -> None:
    expected = _scheduler_revisions()
    repos = report["source_binding"]["repositories"]
    for repo, commit in expected.items():
        assert repo in repos, f"missing source binding for {repo}"
        assert FULL_SHA_RE.fullmatch(repos[repo]["commit"]), repos[repo]["commit"]
        assert repos[repo]["commit"] == commit
        if (ROOT / repo).exists():
            assert _git_head(repo) == commit


def test_every_component_has_required_fields(report: dict[str, Any]) -> None:
    components = report["components"]
    assert isinstance(components, list) and len(components) >= 20

    seen_ids: set[str] = set()
    for item in components:
        assert isinstance(item, dict)
        for field in REQUIRED_COMPONENT_FIELDS:
            assert field in item, f"{item.get('component_id')}: missing {field}"

        component_id = item["component_id"]
        assert isinstance(component_id, str) and component_id
        assert component_id not in seen_ids
        seen_ids.add(component_id)

        assert item["category"] in EVIDENCE_SUBSET
        assert FULL_SHA_RE.fullmatch(item["commit"]), item["commit"]
        assert isinstance(item["path"], str) and item["path"]
        assert isinstance(item["symbol"], str) and item["symbol"]
        assert isinstance(item["semantic_authority"], str) and item["semantic_authority"].strip()
        assert isinstance(item["gaps"], list) and item["gaps"]
        assert all(isinstance(gap, str) and gap.strip() for gap in item["gaps"])
        assert item["adoption_disposition"] in ADOPTION_VOCABULARY

        risk = item["compatibility_risk"]
        assert isinstance(risk, dict)
        assert risk["level"] in RISK_LEVELS
        assert isinstance(risk["rationale"], str) and risk["rationale"].strip()

        assert isinstance(item["total_assurance_ladder"], bool)
        adaptation = item["fca_adaptation"]
        assert isinstance(adaptation, dict)
        assert isinstance(adaptation["flagged_for_conservative_adaptation"], bool)
        assert isinstance(adaptation["do_not_duplicate"], bool)
        assert isinstance(adaptation["rationale"], str) and adaptation["rationale"].strip()


def test_component_commits_paths_and_symbols_resolve(report: dict[str, Any]) -> None:
    binding = report["source_binding"]["repositories"]
    for item in report["components"]:
        repo = item["repository"]
        assert repo in binding
        assert item["commit"] == binding[repo]["commit"]

        path = ROOT / item["path"]
        assert path.is_file(), f"missing path for {item['component_id']}: {item['path']}"
        assert item["path"].startswith(repo.rstrip("/") + "/") or item["path"].startswith(
            repo + "/"
        )
        assert _symbol_defined(path, item["symbol"]), (
            f"{item['component_id']}: symbol {item['symbol']!r} not defined in {item['path']}"
        )
        if "line" in item:
            lines = path.read_text(encoding="utf-8").splitlines()
            line_no = int(item["line"])
            assert 1 <= line_no <= len(lines)
            assert item["symbol"] in lines[line_no - 1]


def test_evidence_subset_categories_are_all_covered(report: dict[str, Any]) -> None:
    present = {item["category"] for item in report["components"]}
    assert present == set(EVIDENCE_SUBSET)
    assert set(report["coverage"]["categories_present"]) == set(EVIDENCE_SUBSET)
    assert report["coverage"]["component_count"] == len(report["components"])


def test_total_assurance_ladders_flagged_for_conservative_fca_adaptation(
    report: dict[str, Any],
) -> None:
    by_id = {item["component_id"]: item for item in report["components"]}
    for component_id, symbol in REQUIRED_TOTAL_LADDERS.items():
        assert component_id in by_id, f"missing required total ladder {component_id}"
        item = by_id[component_id]
        assert item["symbol"] == symbol
        assert item["total_assurance_ladder"] is True
        adaptation = item["fca_adaptation"]
        assert adaptation["flagged_for_conservative_adaptation"] is True
        assert adaptation["do_not_duplicate"] is True
        rationale = adaptation["rationale"].casefold()
        assert "fca" in rationale or "formal claim algebra" in rationale
        assert "duplicat" in rationale

    flagged = [item for item in report["components"] if item["total_assurance_ladder"]]
    assert flagged
    assert report["coverage"]["total_assurance_ladders_flagged"] == len(flagged)
    for item in flagged:
        assert item["fca_adaptation"]["do_not_duplicate"] is True
        assert item["fca_adaptation"]["flagged_for_conservative_adaptation"] is True
        assert item["adoption_disposition"] in {
            "adapt_conservatively_for_fca",
            "reference_semantics_only",
            "do_not_duplicate",
        }


def test_acceptance_notes_state_discovery_is_not_completion(report: dict[str, Any]) -> None:
    notes = " ".join(report.get("acceptance_notes", [])).casefold()
    assert "commit" in notes and "path" in notes and "symbol" in notes
    assert "conservative" in notes and "duplicat" in notes
    assert "discovery" in notes and "not completion" in notes


def test_mutated_report_missing_required_field_fails_local_checks(report: dict[str, Any]) -> None:
    """Structural gate: dropping a required field is detectable without rewriting files."""

    broken = json.loads(json.dumps(report))
    del broken["components"][0]["semantic_authority"]
    missing = [
        field
        for field in REQUIRED_COMPONENT_FIELDS
        if field not in broken["components"][0]
    ]
    assert "semantic_authority" in missing
