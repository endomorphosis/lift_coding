"""FACP-003: Datasets import, outcome, and rights defect inventory gate.

Validates that datasets_claims.json binds the exact Datasets gitlink, that every
import-effect and false-success span is reproducible against current source,
and that the MIT/AGPL conflict is encoded as unresolved human legal review
rather than inferred compatibility.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from facp_historical_git import (
    assert_historical_ancestor,
    blob_text,
    current_head,
    superproject_gitlink,
)

CLAIMS_PATH = (
    ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "datasets_claims.json"
)
DATASETS_GITLINK = ROOT / "external" / "ipfs_datasets"
DATASETS_GITLINK_PATH = "external/ipfs_datasets"

REQUIRED_EVIDENCE = {
    "module-top-level effects",
    "installer reachability",
    "PATH/environment writes",
    "download/upload fallbacks",
    "semantic results",
    "MIT/AGPL declarations",
}

FORBIDDEN_RIGHTS_DISPOSITIONS = {
    "compatible",
    "compatibility_inferred",
    "inferred_compatible",
    "mit_overrides_agpl",
    "agpl_overrides_mit",
    "resolved",
    "no_conflict",
}


def _load_claims() -> dict:
    assert CLAIMS_PATH.is_file(), f"missing inventory report: {CLAIMS_PATH}"
    payload = json.loads(CLAIMS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _gitlink_commit() -> str:
    return current_head(DATASETS_GITLINK)


def _parent_gitlink_commit() -> str:
    return superproject_gitlink(ROOT, "HEAD", DATASETS_GITLINK_PATH)


def _read_span(commit: str, path: str, line_start: int, line_end: int) -> str:
    relative_path = str(Path(path).relative_to(DATASETS_GITLINK_PATH))
    lines = blob_text(DATASETS_GITLINK, commit, relative_path).splitlines()
    assert 1 <= line_start <= line_end <= len(lines), (
        f"span out of range for {path}: {line_start}-{line_end} (file has {len(lines)} lines)"
    )
    return "\n".join(lines[line_start - 1 : line_end])


def _assert_quote_in_span(record: dict, *, commit: str, label: str) -> None:
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
            f"{secondary['line_start']}-{secondary['line_end']}: {secondary['quote']!r}"
        )


def test_claims_report_exists_and_binds_task_metadata() -> None:
    claims = _load_claims()
    assert claims["schema_version"] == "facp-datasets-claims/v1"
    assert claims["task_id"] == "FACP-003"
    assert claims["bundle"] == "facp/inventory/datasets"
    assert claims["behavior_change"] is False
    assert claims["discovery_is_not_completion"] is True
    assert set(claims["evidence_subset"]) >= REQUIRED_EVIDENCE
    assert "legal_compatibility_inference" in claims["prohibited_conclusions"]


def test_source_binding_matches_exact_gitlink_commit() -> None:
    claims = _load_claims()
    binding = claims["source_binding"]
    assert binding["gitlink_path"] == "external/ipfs_datasets"
    assert binding["repository"] == "external/ipfs_datasets"
    bound = binding["commit"]
    current_gitlink = _parent_gitlink_commit()
    assert _gitlink_commit() == current_gitlink
    assert_historical_ancestor(DATASETS_GITLINK, bound, current_gitlink)


def test_import_effect_traces_are_reproducible() -> None:
    claims = _load_claims()
    bound_commit = claims["source_binding"]["commit"]
    traces = claims["import_effect_traces"]
    assert isinstance(traces, list) and len(traces) >= 4

    families = {item["family"] for item in traces}
    assert "module_top_level_environment_write" in families
    assert "installer_construction_path_and_fs_mutation" in families
    assert "installer_reachability_pip_subprocess" in families
    assert any("path" in family for family in families)

    for item in traces:
        assert item["category"] == "import_effect"
        assert item["defect_id"].startswith("DS-IMPORT-")
        assert item["repair_class"] in {"import_purity", "explicit_initialization"}
        assert item["counterexample_seed"]["id"]
        assert item["call_flow"]
        _assert_quote_in_span(item, commit=bound_commit, label=item["defect_id"])


def test_false_success_spans_are_reproducible() -> None:
    claims = _load_claims()
    bound_commit = claims["source_binding"]["commit"]
    spans = claims["false_success_spans"]
    assert isinstance(spans, list) and len(spans) >= 5

    families = {item["family"] for item in spans}
    assert any("download" in family for family in families)
    assert any("upload" in family or "cid" in family for family in families)
    assert any("semantic" in family for family in families)

    for item in spans:
        assert item["category"] == "false_success"
        assert item["defect_id"].startswith("DS-FALSE-")
        assert item["repair_class"] == "fca_outcomes"
        assert item["outcome_shape"]["durable_effect"] is False
        assert item["counterexample_seed"]["id"]
        _assert_quote_in_span(item, commit=bound_commit, label=item["defect_id"])


def test_rights_conflict_is_unresolved_human_legal_review() -> None:
    claims = _load_claims()
    bound_commit = claims["source_binding"]["commit"]
    rights = claims["rights_conflict"]
    assert rights["defect_id"] == "DS-RIGHTS-001"
    assert rights["disposition"] == "unresolved_human_legal_review"
    assert rights["inferred_compatibility"] is False
    assert rights["disposition"] not in FORBIDDEN_RIGHTS_DISPOSITIONS
    assert rights["repair_class"] == "human_legal_review"

    declarations = rights["declarations"]
    declared = {item["declared_license"] for item in declarations}
    assert "MIT" in declared
    assert "AGPL-3.0" in declared
    assert len(declarations) >= 4

    for item in declarations:
        _assert_quote_in_span(item, commit=bound_commit, label=f"rights:{item['path']}")

    # Explicitly forbid encoding a compatibility conclusion.
    serialized = json.dumps(rights)
    for forbidden in (
        "licenses_are_compatible",
        "inferred_compatible",
        "treat_as_mit",
        "treat_as_agpl_only",
        "no_conflict",
    ):
        assert forbidden not in serialized


def test_inventory_covers_evidence_subset_without_legal_inference() -> None:
    claims = _load_claims()
    blob = json.dumps(claims)

    assert "IPFS_DATASETS_AUTO_INSTALL" in blob or "auto_install" in blob.lower()
    assert "PATH" in blob
    assert "pip" in blob
    assert "simulated" in blob.lower() or "mock" in blob.lower()
    assert "semantic" in blob.lower()
    assert "MIT" in blob and "AGPL" in blob
    assert "unresolved_human_legal_review" in blob
    assert claims["rights_conflict"]["inferred_compatibility"] is False


def test_cold_import_probe_reproduces_auto_install_default_effect() -> None:
    """Network/process/write-denied probe of the import-time env defaulting logic.

    Executes only the documented `_enable_default_auto_install` behavior in an
    isolated interpreter with auto-install env cleared. Does not import the full
    package (which would mkdir/PATH-mutate) and does not install packages.
    """
    claims = _load_claims()
    auto_install = next(
        item for item in claims["import_effect_traces"] if item["defect_id"] == "DS-IMPORT-001"
    )
    bound_commit = claims["source_binding"]["commit"]
    _assert_quote_in_span(auto_install, commit=bound_commit, label="cold-import-seed")

    probe = textwrap.dedent(
        """
        import os
        import re

        source = os.environ["FACP003_SOURCE"]

        # Extract and exec only the documented helper; do not import the package.
        match = re.search(
            r"def _enable_default_auto_install\\(\\) -> None:.*?\\n(?=\\n_enable_default_auto_install\\(\\))",
            source,
            flags=re.S,
        )
        assert match is not None, "helper not found"
        ns = {"os": os}
        exec(match.group(0), ns)

        for key in ("IPFS_DATASETS_AUTO_INSTALL", "IPFS_KIT_AUTO_INSTALL_DEPS"):
            os.environ.pop(key, None)

        before = {
            "IPFS_DATASETS_AUTO_INSTALL": os.environ.get("IPFS_DATASETS_AUTO_INSTALL"),
            "IPFS_KIT_AUTO_INSTALL_DEPS": os.environ.get("IPFS_KIT_AUTO_INSTALL_DEPS"),
        }
        ns["_enable_default_auto_install"]()
        after = {
            "IPFS_DATASETS_AUTO_INSTALL": os.environ.get("IPFS_DATASETS_AUTO_INSTALL"),
            "IPFS_KIT_AUTO_INSTALL_DEPS": os.environ.get("IPFS_KIT_AUTO_INSTALL_DEPS"),
        }
        print(json_dumps := __import__("json").dumps({"before": before, "after": after}))
        assert before["IPFS_DATASETS_AUTO_INSTALL"] is None
        assert after["IPFS_DATASETS_AUTO_INSTALL"] == "true"
        assert after["IPFS_KIT_AUTO_INSTALL_DEPS"] == "1"
        """
    )

    env = os.environ.copy()
    env["FACP003_SOURCE"] = blob_text(
        DATASETS_GITLINK, bound_commit, "ipfs_datasets_py/__init__.py"
    )
    # Deny auto-install / ensure-installer for any accidental broader import.
    env["IPFS_DATASETS_AUTO_INSTALL"] = "false"
    env["IPFS_KIT_AUTO_INSTALL_DEPS"] = "0"
    env["IPFS_DATASETS_ENSURE_INSTALLER"] = "0"
    env["IPFS_DATASETS_PY_MINIMAL_IMPORTS"] = "1"
    # Best-effort network denial markers used by some installer paths.
    env["NO_NETWORK"] = "1"
    env["PIP_NO_INDEX"] = "1"

    result = subprocess.run(
        [sys.executable, "-c", probe],
        cwd=ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"cold-import probe failed\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    payload = json.loads(result.stdout.strip().splitlines()[-1])
    assert payload["after"]["IPFS_DATASETS_AUTO_INSTALL"] == "true"
    assert payload["after"]["IPFS_KIT_AUTO_INSTALL_DEPS"] == "1"


def test_every_defect_has_counterexample_seed_and_follow_on() -> None:
    claims = _load_claims()
    records = list(claims["import_effect_traces"]) + list(claims["false_success_spans"])
    assert records
    for item in records:
        seed = item["counterexample_seed"]
        assert seed["id"].startswith("cx-ds-")
        assert seed["oracle"]
        assert item.get("proposed_follow_on"), item["defect_id"]


@pytest.mark.parametrize(
    "forbidden",
    sorted(FORBIDDEN_RIGHTS_DISPOSITIONS),
)
def test_rights_disposition_is_not_a_forbidden_compatibility_label(forbidden: str) -> None:
    claims = _load_claims()
    assert claims["rights_conflict"]["disposition"] != forbidden
