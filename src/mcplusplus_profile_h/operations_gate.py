"""XPH-112 deterministic observability and disaster-recovery evidence gate."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

from .adapters import CallbackFacilitator, SettlementResult, VerificationResult
from .artifacts import FileCIDArtifactStore
from .canonical import cid_for
from .errors import PAYMENT_REPLAY, ProfileHError
from .ledger import DuckDBPaymentLedger
from .operations import (
    BackupManager,
    KillSwitches,
    RedactedMetrics,
    alert_definitions,
    assert_redacted_surface,
    dashboard_definition,
    facilitator_health_probe,
)

SELLERS = ("ipfs-kit", "ipfs-datasets", "ipfs-accelerate")


async def _healthy_facilitator() -> CallbackFacilitator:
    async def verify(_payload: Any, _requirement: Any) -> VerificationResult:
        return VerificationResult(True)

    async def settle(_payload: Any, requirement: Any) -> SettlementResult:
        return SettlementResult(True, requirement.network)

    return CallbackFacilitator(verify, settle, health=lambda: True)


def run_operations_gate(*, state_dir: Path | None = None) -> dict[str, Any]:
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if state_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="xph-112-")
        state_dir = Path(temporary.name)
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        metrics = RedactedMetrics(sellers=SELLERS)
        for seller in SELLERS:
            for stage in ("quote", "verify", "settlement", "entitlement", "access", "execution"):
                metrics.observe(stage, "success", seller, duration_ms=7, reason_code="H_TEST_PASS")
            # Every operational failure family is distinguishable by stage and stable code.
            metrics.observe("quote", "failure", seller, reason_code="H_QUOTE_EXPIRED")
            metrics.observe("verify", "failure", seller, reason_code="H_VERIFICATION_FAILED")
            metrics.observe("settlement", "timeout", seller, reason_code="H_FACILITATOR_UNAVAILABLE")
            metrics.observe("entitlement", "denied", seller, reason_code="H_ENTITLEMENT_EXHAUSTED")
            metrics.observe("access", "denied", seller, reason_code="H_PAYMENT_POLICY_DENIED")
            metrics.observe("execution", "failure", seller, reason_code="H_RECONCILIATION_REQUIRED")
        metrics.observe("refund", "pending", "ipfs-kit", reason_code="H_REFUND_REQUESTED")
        metrics.observe("reconciliation", "success", "ipfs-kit", reason_code="H_PAYMENT_RECONCILED")

        rejected_sensitive_label = False
        try:
            metrics.observe("quote", "failure", "ipfs-kit", reason_code="wallet-0x-secret")
        except ValueError:
            rejected_sensitive_label = True
        if not rejected_sensitive_label:
            raise AssertionError("metric label accepted request-controlled data")

        artifact_root = state_dir / "artifacts"
        artifacts = FileCIDArtifactStore(artifact_root)
        ledger_path = state_dir / "ledger.duckdb"
        ledger = DuckDBPaymentLedger(ledger_path)
        quote = artifacts.put({"schema": "mcp++/profile-h/ops-fixture@1.0", "kind": "quote"})
        verification = artifacts.put({"schema": "mcp++/profile-h/ops-fixture@1.0", "kind": "verification", "parent": quote})
        settlement = artifacts.put({"schema": "mcp++/profile-h/ops-fixture@1.0", "kind": "settlement", "parent": verification})
        access = artifacts.put({"schema": "mcp++/profile-h/ops-fixture@1.0", "kind": "access", "parent": settlement})
        ledger.create_quote("ops-idempotency", "request-commitment", "tool:pin", "capability-commitment", quote)
        ledger.bind_payment("ops-idempotency", "payment-commitment")
        ledger.mark_verified("ops-idempotency", verification)
        ledger.begin_settlement("ops-idempotency", "short-lived-lease")
        ledger.mark_settled("ops-idempotency", settlement)
        ledger.claim_execution("ops-idempotency", "short-lived-execution-lease")
        ledger.mark_executed("ops-idempotency", access)
        # Preserve a separate uncertain settlement for the recovery queue.
        ledger.create_quote("recovery-idempotency", "request-2", "tool:get", "capability-2", quote)
        ledger.bind_payment("recovery-idempotency", "payment-commitment-2")
        ledger.mark_verified("recovery-idempotency", verification)
        ledger.begin_settlement("recovery-idempotency", "recovery-lease")

        ledger_probe = ledger.health_probe()
        facilitator_probe = asyncio.run(facilitator_health_probe(asyncio.run(_healthy_facilitator())))
        if not ledger_probe["ready"] or not facilitator_probe["ready"]:
            raise AssertionError("healthy dependencies did not pass readiness")

        controls = KillSwitches(state_dir / "kill-switches.json", sellers=SELLERS)
        controls.set_pause(paused=True, seller="ipfs-datasets", reason_code="H_INCIDENT_SELLER")
        seller_isolated = not controls.allows_new_work("ipfs-datasets") and controls.allows_new_work("ipfs-kit")
        controls.set_pause(paused=True, reason_code="H_INCIDENT_GLOBAL")
        globally_paused = all(not controls.allows_new_work(seller) for seller in SELLERS)
        recovery_while_paused = controls.allows_recovery() and bool(ledger.pending_reconciliation())
        controls.set_pause(paused=False, reason_code="H_INCIDENT_RECOVERED")
        controls.set_pause(paused=False, seller="ipfs-datasets", reason_code="H_INCIDENT_RECOVERED")

        snapshot = BackupManager(ledger, artifact_root).create(state_dir / "backup")
        original_history = ledger.history("ops-idempotency")
        ledger.close()

        restored_ledger_path = state_dir / "restored" / "ledger.duckdb"
        restored_artifacts = state_dir / "restored" / "artifacts"
        manifest = BackupManager.restore(snapshot.root, ledger_path=restored_ledger_path,
                                         artifact_root=restored_artifacts)
        restored = DuckDBPaymentLedger(restored_ledger_path)
        restored_entry = restored.get("ops-idempotency")
        lineage_preserved = restored.history("ops-idempotency") == original_history
        recovery_queue_preserved = restored.get("recovery-idempotency").state == "settling"
        replay_fenced = False
        try:
            restored.bind_payment("ops-idempotency", "different-payment")
        except ProfileHError as exc:
            replay_fenced = exc.code == PAYMENT_REPLAY
        restore_ready = restored.health_probe()["ready"]
        restored.close()
        artifacts_preserved = all((restored_artifacts / cid).exists() for cid in manifest["artifacts"])
        if not all((restored_entry and restored_entry.state == "executed", lineage_preserved,
                    recovery_queue_preserved, replay_fenced, restore_ready, artifacts_preserved)):
            raise AssertionError("backup/restore lost payment safety or lineage")

        dashboard, alerts = dashboard_definition(), alert_definitions()
        report: dict[str, Any] = {
            "schema": "mcp++/profile-h/operations-gate@1.0", "task": "XPH-112",
            "decision": "pass", "sellerCount": len(SELLERS),
            "observability": {
                "metrics": metrics.snapshot(), "prometheusExport": metrics.prometheus(),
                "dashboard": dashboard, "alerts": alerts,
                "failureStages": ["quote", "verify", "settlement", "entitlement", "access", "execution"],
                "boundedLabels": True, "sensitiveLabelRejected": rejected_sensitive_label,
            },
            "health": {"facilitator": facilitator_probe, "ledger": ledger_probe},
            "killSwitches": {"sellerIsolation": seller_isolated, "globalPause": globally_paused,
                             "recoveryAvailableWhilePaused": recovery_while_paused,
                             "finalState": controls.status()},
            "incidentRecovery": {
                "snapshotEvidenceCid": manifest["evidenceCid"],
                "artifactCount": manifest["artifactCount"], "settledLineagePreserved": lineage_preserved,
                "uncertainSettlementPreserved": recovery_queue_preserved,
                "idempotencyReplayFenced": replay_fenced, "restoredLedgerReady": restore_ready,
                "artifactsVerified": artifacts_preserved,
                "refundWorkflow": ["request", "policy-review", "record-outcome", "reconcile-ledger"],
            },
            "runbook": "docs/mcplusplus-profile-h-incident-recovery.md",
        }
        assert_redacted_surface(report)
        report["evidenceCid"] = cid_for(report)
        return report
    finally:
        if temporary is not None:
            temporary.cleanup()

