from __future__ import annotations

import asyncio

import pytest

from mcplusplus_profile_h import CallbackFacilitator, DuckDBPaymentLedger
from mcplusplus_profile_h.operations import KillSwitches, RedactedMetrics, facilitator_health_probe
from mcplusplus_profile_h.operations_gate import run_operations_gate


def test_operations_gate_covers_all_failure_stages_and_restore(tmp_path):
    report = run_operations_gate(state_dir=tmp_path)
    assert report["decision"] == "pass"
    assert report["observability"]["failureStages"] == [
        "quote", "verify", "settlement", "entitlement", "access", "execution"
    ]
    assert report["killSwitches"]["recoveryAvailableWhilePaused"] is True
    assert report["incidentRecovery"]["idempotencyReplayFenced"] is True
    assert report["incidentRecovery"]["settledLineagePreserved"] is True
    serialized = str(report).lower()
    assert "privatekey" not in serialized and "paymentpayload" not in serialized


def test_metrics_reject_high_cardinality_or_sensitive_dimensions():
    metrics = RedactedMetrics(sellers={"seller-a"})
    metrics.observe("quote", "success", "seller-a", reason_code="H_OK")
    with pytest.raises(ValueError):
        metrics.observe("request-123", "success", "seller-a")
    with pytest.raises(ValueError):
        metrics.observe("quote", "failure", "seller-a", reason_code="0xwallet")
    assert "H_OK" in metrics.prometheus()


def test_kill_switch_state_survives_restart_and_recovery_is_available(tmp_path):
    path = tmp_path / "controls.json"
    first = KillSwitches(path, sellers={"seller-a", "seller-b"})
    first.set_pause(paused=True, seller="seller-a")
    second = KillSwitches(path, sellers={"seller-a", "seller-b"})
    assert second.allows_new_work("seller-a") is False
    assert second.allows_new_work("seller-b") is True
    assert second.allows_recovery() is True


def test_health_probes_collapse_dependency_exceptions(tmp_path):
    ledger = DuckDBPaymentLedger(tmp_path / "ledger.duckdb")
    assert ledger.health_probe()["ready"] is True

    async def broken():
        raise RuntimeError("must not leak this upstream detail")

    facilitator = CallbackFacilitator(lambda *_: None, lambda *_: None, health=broken)
    result = asyncio.run(facilitator_health_probe(facilitator))
    assert result["ready"] is False
    assert "detail" not in result and "error" not in result

