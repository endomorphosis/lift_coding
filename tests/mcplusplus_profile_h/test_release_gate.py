from __future__ import annotations

import json
from pathlib import Path

from mcplusplus_profile_h.canonical import cid_for
from mcplusplus_profile_h.release_gate import (
    build_release_decision,
    generate_release_packet,
    performance_test,
    property_and_concurrency_tests,
    secret_scan,
    security_review,
    soak_test,
)

ROOT = Path(__file__).resolve().parents[2]


def test_property_concurrency_performance_and_soak_are_fail_closed(tmp_path):
    properties = property_and_concurrency_tests(tmp_path / "properties", examples=32)
    performance = performance_test(tmp_path / "performance", samples=12)
    soak = soak_test(tmp_path / "soak", hours=2)
    assert properties.status == "pass"
    assert properties.evidence["settlementCount"] == 1
    assert properties.evidence["executionCount"] == 1
    assert performance.status == "pass"
    # A short diagnostic run exercises the state machine but cannot claim the
    # multi-day acceptance condition.
    assert soak.status == "fail"
    assert soak.evidence["checks"]["multiDayDuration"] is False


def test_release_decision_rejects_failure_and_mainnet():
    passed = security_review()
    failed = type(passed)("required-check", "fail", {"reason": "injected"})
    assert build_release_decision("testnet", [passed])["decision"] == "GO"
    assert build_release_decision("testnet", [passed, failed])["decision"] == "NO_GO"
    mainnet = build_release_decision("mainnet", [passed])
    assert mainnet["decision"] == "NO_GO"
    assert mainnet["mainnetEnabled"] is False


def test_secret_scan_reports_location_but_never_copies_secret(tmp_path):
    source = tmp_path / "src/mcplusplus_profile_h"
    source.mkdir(parents=True)
    marker = "-----BEGIN PRIVATE KEY-----"
    (source / "bad.py").write_text(f"value = {marker!r}\n", encoding="utf-8")
    result = secret_scan(tmp_path)
    assert result.status == "fail"
    assert result.evidence["findingCount"] == 1
    assert marker not in json.dumps(result.public())


def test_full_release_packet_is_go_and_content_addressed(tmp_path):
    report, sbom = generate_release_packet(ROOT, tmp_path, mode="testnet")
    assert report["decision"] == "GO"
    assert report["testnetReady"] is True
    assert report["mainnetEnabled"] is False
    assert not report["observedNoGoConditions"]
    evidence_cid = report.pop("evidenceCid")
    assert evidence_cid == cid_for(report)
    assert sbom["bomFormat"] == "CycloneDX"
    assert sbom["specVersion"] == "1.5"
