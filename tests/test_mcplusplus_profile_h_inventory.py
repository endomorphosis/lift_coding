"""Regression tests for the XPH-100 discovery inventory gate."""

from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate_mcplusplus_profile_h_inventory.py"
REPORT_PATH = ROOT / "data" / "mcplusplus_profile_h" / "x402-inventory.json"


def _load_validator():
    spec = importlib.util.spec_from_file_location("xph_inventory_validator", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _report() -> dict:
    return json.loads(REPORT_PATH.read_text(encoding="utf-8"))


def test_repository_inventory_is_valid() -> None:
    validator = _load_validator()
    assert validator.validate(_report()) == []


def test_alternate_runtime_dispatcher_cannot_be_omitted() -> None:
    validator = _load_validator()
    report = copy.deepcopy(_report())
    report["dispatchers"] = [
        item for item in report["dispatchers"] if item["id"] != "accelerate-trio-http"
    ]

    failures = validator.validate(report)

    assert "known MCP++ dispatch seams are missing" in failures


def test_alternate_buyer_transport_cannot_be_omitted() -> None:
    validator = _load_validator()
    report = copy.deepcopy(_report())
    report["wallet_client_seams"] = [
        item
        for item in report["wallet_client_seams"]
        if item["kind"] != "alternate MCP SDK buyer transport"
    ]

    failures = validator.validate(report)

    assert any("alternate client" in failure for failure in failures)


def test_primary_cli_buyer_transport_cannot_be_omitted() -> None:
    validator = _load_validator()
    report = copy.deepcopy(_report())
    report["dispatchers"] = [
        item
        for item in report["dispatchers"]
        if item["id"] != "swissknife-host-sdk-client"
    ]

    failures = validator.validate(report)

    assert "known MCP++ dispatch seams are missing" in failures


def test_version_aware_buyer_router_cannot_be_omitted() -> None:
    validator = _load_validator()
    report = copy.deepcopy(_report())
    report["wallet_client_seams"] = [
        item
        for item in report["wallet_client_seams"]
        if item["kind"] != "version-aware buyer router"
    ]

    failures = validator.validate(report)

    assert any("alternate client" in failure for failure in failures)


def test_profile_h_claims_are_rejected_during_discovery() -> None:
    validator = _load_validator()
    report = copy.deepcopy(_report())
    report["capability_descriptors"][0]["current_profile_h"] = True

    failures = validator.validate(report)

    assert any("incorrectly claims Profile H" in failure for failure in failures)


def test_dependency_scan_cannot_omit_an_alternate_lockfile() -> None:
    validator = _load_validator()
    report = copy.deepcopy(_report())
    swissknife = next(
        item for item in report["dependency_version_matrix"]
        if item["component"] == "swissknife"
    )
    swissknife["manifests_scanned"].remove("swissknife/yarn.lock")

    failures = validator.validate(report)

    assert any("canonical dependency manifest" in failure for failure in failures)


def test_legacy_paid_access_bypass_surface_cannot_be_omitted() -> None:
    validator = _load_validator()
    report = copy.deepcopy(_report())
    report["non_mcplusplus_execution_surfaces"] = [
        item for item in report["non_mcplusplus_execution_surfaces"]
        if item["id"] != "accelerate-legacy-fastapi-rollback"
    ]

    failures = validator.validate(report)

    assert "legacy or direct paid-access bypass surfaces are missing" in failures


def test_validator_is_safe_for_legacy_backtick_wrapped_task_metadata() -> None:
    """An already-parsed retry must not execute the PASS diagnostic as shell."""
    command = f"`python {VALIDATOR_PATH} --report {REPORT_PATH}`"

    completed = subprocess.run(
        ["/bin/bash", "-lc", command],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert completed.stdout == ""
    assert "PASS: XPH-100 inventory covers" in completed.stderr
    assert "command not found" not in completed.stderr
