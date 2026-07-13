"""Redacted Profile H telemetry, dependency health, controls, and recovery.

The module intentionally accepts only bounded operational dimensions. Request,
wallet, transaction, content, tenant, and artifact identifiers never enter the
metrics surface.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import time
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import canonical_json, cid_for
from .ledger import DuckDBPaymentLedger

STAGES = frozenset({
    "quote", "verify", "settlement", "entitlement", "access", "execution",
    "refund", "reconciliation",
})
OUTCOMES = frozenset({"success", "failure", "denied", "timeout", "paused", "pending"})
_SAFE_VALUE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.:-]{0,63}$")
_SAFE_REASON = re.compile(r"^H_[A-Z0-9_]{1,61}$")


class RedactedMetrics:
    """In-process Prometheus-style counters with a fixed, low-cardinality schema."""

    def __init__(self, *, sellers: Iterable[str]) -> None:
        configured = frozenset(sellers)
        if not configured or any(not _SAFE_VALUE.fullmatch(item) for item in configured):
            raise ValueError("sellers must be a non-empty set of safe bounded labels")
        self._sellers = configured
        self._events: Counter[tuple[str, str, str, str]] = Counter()
        self._duration_ms: dict[tuple[str, str, str], list[int]] = defaultdict(list)
        self._lock = threading.RLock()

    def observe(
        self, stage: str, outcome: str, seller: str, *, duration_ms: int = 0,
        reason_code: str = "H_NONE",
    ) -> None:
        if stage not in STAGES or outcome not in OUTCOMES or seller not in self._sellers:
            raise ValueError("unbounded Profile H metric dimension")
        if not _SAFE_REASON.fullmatch(reason_code):
            raise ValueError("reason_code must be a stable H_* code, never request data")
        if isinstance(duration_ms, bool) or not isinstance(duration_ms, int) or not 0 <= duration_ms <= 3_600_000:
            raise ValueError("duration_ms is outside the operational bound")
        with self._lock:
            self._events[(stage, outcome, seller, reason_code)] += 1
            # Retain a bounded rolling window; counters remain cumulative.
            samples = self._duration_ms[(stage, outcome, seller)]
            samples.append(duration_ms)
            if len(samples) > 1024:
                del samples[:-1024]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            events = [
                {"stage": stage, "outcome": outcome, "seller": seller,
                 "reasonCode": reason, "count": count}
                for (stage, outcome, seller, reason), count in sorted(self._events.items())
            ]
            latency = []
            for (stage, outcome, seller), values in sorted(self._duration_ms.items()):
                ordered = sorted(values)
                latency.append({
                    "stage": stage, "outcome": outcome, "seller": seller,
                    "count": len(values), "sumMs": sum(values),
                    "maxMs": ordered[-1], "p95Ms": ordered[min(len(ordered) - 1, (len(ordered) * 95) // 100)],
                })
        return {"schema": "mcp++/profile-h/redacted-metrics@1.0", "events": events, "latency": latency}

    def prometheus(self) -> str:
        lines = [
            "# HELP mcplusplus_profile_h_events_total Redacted Profile H lifecycle outcomes.",
            "# TYPE mcplusplus_profile_h_events_total counter",
        ]
        snapshot = self.snapshot()
        for item in snapshot["events"]:
            labels = (f'stage="{item["stage"]}",outcome="{item["outcome"]}",'
                      f'seller="{item["seller"]}",reason_code="{item["reasonCode"]}"')
            lines.append(f"mcplusplus_profile_h_events_total{{{labels}}} {item['count']}")
        lines.extend([
            "# HELP mcplusplus_profile_h_stage_latency_ms Profile H bounded stage latency summary.",
            "# TYPE mcplusplus_profile_h_stage_latency_ms summary",
        ])
        for item in snapshot["latency"]:
            labels = f'stage="{item["stage"]}",outcome="{item["outcome"]}",seller="{item["seller"]}"'
            lines.append(f"mcplusplus_profile_h_stage_latency_ms_sum{{{labels}}} {item['sumMs']}")
            lines.append(f"mcplusplus_profile_h_stage_latency_ms_count{{{labels}}} {item['count']}")
        return "\n".join(lines) + "\n"


class KillSwitches:
    """Durable global/per-seller pause controls; recovery is never disabled."""

    def __init__(self, path: str | Path, *, sellers: Iterable[str]) -> None:
        self.path = Path(path)
        self.sellers = frozenset(sellers)
        if not self.sellers or any(not _SAFE_VALUE.fullmatch(item) for item in self.sellers):
            raise ValueError("invalid seller set")
        self._lock = threading.RLock()
        if not self.path.exists():
            self._write({"schema": "mcp++/profile-h/kill-switches@1.0", "generation": 0,
                         "globalPaused": False, "sellers": {item: False for item in sorted(self.sellers)},
                         "reasonCode": "H_NONE", "updatedAt": 0})
        self._read()

    def _read(self) -> dict[str, Any]:
        value = json.loads(self.path.read_text(encoding="utf-8"))
        if value.get("schema") != "mcp++/profile-h/kill-switches@1.0":
            raise OSError("invalid kill-switch state")
        if set(value.get("sellers", {})) != self.sellers:
            raise OSError("kill-switch seller set does not match configuration")
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(prefix=".profile-h-controls-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(canonical_json(value) + b"\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def set_pause(self, *, paused: bool, seller: str | None = None, reason_code: str = "H_OPERATOR_PAUSE") -> dict[str, Any]:
        if not _SAFE_REASON.fullmatch(reason_code):
            raise ValueError("invalid public reason code")
        if seller is not None and seller not in self.sellers:
            raise KeyError(seller)
        with self._lock:
            state = self._read()
            if seller is None:
                state["globalPaused"] = bool(paused)
            else:
                state["sellers"][seller] = bool(paused)
            state["generation"] += 1
            state["reasonCode"] = reason_code
            state["updatedAt"] = time.time_ns() // 1_000_000
            self._write(state)
            return state

    def allows_new_work(self, seller: str) -> bool:
        if seller not in self.sellers:
            raise KeyError(seller)
        state = self._read()
        return not state["globalPaused"] and not state["sellers"][seller]

    @staticmethod
    def allows_recovery() -> bool:
        return True

    def status(self) -> dict[str, Any]:
        return self._read()


async def facilitator_health_probe(facilitator: Any, *, timeout_ms: int = 2_000) -> dict[str, Any]:
    """Bounded readiness probe. Exceptions are collapsed and never serialized."""
    started = time.monotonic_ns()
    try:
        ready = bool(await asyncio.wait_for(facilitator.health(), timeout_ms / 1000))
        status = "ready" if ready else "degraded"
    except TimeoutError:
        ready, status = False, "timeout"
    except Exception:
        ready, status = False, "unavailable"
    return {"component": "profile-h-facilitator", "status": status, "ready": ready,
            "latencyMs": max(0, (time.monotonic_ns() - started) // 1_000_000)}


def dashboard_definition() -> dict[str, Any]:
    """Portable dashboard contract consumed by Grafana/UI adapters."""
    return {
        "schema": "mcp++/profile-h/operations-dashboard@1.0",
        "title": "MCP++ Profile H payment operations",
        "privacy": "aggregate-only-no-identifiers-or-protected-content",
        "variables": ["seller", "stage", "outcome", "reason_code"],
        "panels": [
            {"title": "Lifecycle failures", "type": "timeseries", "metric": "mcplusplus_profile_h_events_total", "groupBy": ["stage", "seller", "reason_code"]},
            {"title": "Stage latency", "type": "timeseries", "metric": "mcplusplus_profile_h_stage_latency_ms", "groupBy": ["stage", "seller"]},
            {"title": "Facilitator readiness", "type": "status", "probe": "profile-h-facilitator"},
            {"title": "Ledger integrity and recovery queue", "type": "status", "probe": "profile-h-ledger"},
            {"title": "Kill switches", "type": "status", "source": "kill-switches"},
        ],
    }


def alert_definitions() -> list[dict[str, Any]]:
    return [
        {"name": "ProfileHFacilitatorUnavailable", "severity": "critical", "for": "2m", "condition": "facilitator_ready == 0", "action": "pause-new-spend-and-reconcile"},
        {"name": "ProfileHLedgerIntegrity", "severity": "critical", "for": "0m", "condition": "ledger_integrity != 1", "action": "global-pause-preserve-ledger"},
        {"name": "ProfileHSettlementFailures", "severity": "warning", "for": "5m", "condition": "settlement_failure_rate > 0.05", "action": "seller-pause-and-facilitator-check"},
        {"name": "ProfileHRecoveryBacklog", "severity": "warning", "for": "15m", "condition": "pending_reconciliation > 0", "action": "run-reconciliation"},
        {"name": "ProfileHExecutionFailures", "severity": "warning", "for": "5m", "condition": "execution_failure_rate > 0.05", "action": "pause-new-work-preserve-refunds"},
    ]


@dataclass(frozen=True, slots=True)
class RecoverySnapshot:
    root: Path
    manifest: dict[str, Any]


class BackupManager:
    """Consistent ledger plus immutable-artifact backup and verified restore."""

    def __init__(self, ledger: DuckDBPaymentLedger, artifact_root: str | Path) -> None:
        self.ledger, self.artifact_root = ledger, Path(artifact_root)

    def create(self, destination: str | Path) -> RecoverySnapshot:
        destination = Path(destination)
        if destination.exists():
            raise FileExistsError(destination)
        staging = destination.with_name(f".{destination.name}.tmp-{os.getpid()}")
        shutil.rmtree(staging, ignore_errors=True)
        try:
            staging.mkdir(parents=True)
            # Artifacts are persisted before their ledger references. Taking
            # the ledger checkpoint first therefore cannot leave the snapshot
            # with a committed reference to an absent immutable block.
            ledger_evidence = self.ledger.backup(staging / "ledger.duckdb")
            artifacts = staging / "artifacts"
            shutil.copytree(self.artifact_root, artifacts)
            artifact_hashes: dict[str, str] = {}
            for item in sorted(path for path in artifacts.iterdir() if path.is_file()):
                raw = item.read_bytes()
                value = json.loads(raw)
                if cid_for(value) != item.name:
                    raise OSError("artifact backup contains corrupt content")
                artifact_hashes[item.name] = hashlib.sha256(raw).hexdigest()
            manifest = {
                "schema": "mcp++/profile-h/recovery-snapshot@1.0",
                "ledger": ledger_evidence,
                "artifacts": artifact_hashes,
                "artifactCount": len(artifact_hashes),
            }
            manifest["evidenceCid"] = cid_for(manifest)
            (staging / "manifest.json").write_bytes(canonical_json(manifest) + b"\n")
            os.replace(staging, destination)
            return RecoverySnapshot(destination, manifest)
        finally:
            shutil.rmtree(staging, ignore_errors=True)

    @staticmethod
    def restore(snapshot: str | Path, *, ledger_path: str | Path, artifact_root: str | Path) -> dict[str, Any]:
        snapshot = Path(snapshot)
        manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
        if manifest.get("schema") != "mcp++/profile-h/recovery-snapshot@1.0":
            raise OSError("unsupported recovery snapshot schema")
        expected_cid = manifest.pop("evidenceCid", None)
        if expected_cid != cid_for(manifest):
            raise OSError("recovery manifest commitment mismatch")
        manifest["evidenceCid"] = expected_cid
        source_artifacts = snapshot / "artifacts"
        target_artifacts = Path(artifact_root)
        target_ledger = Path(ledger_path)
        if target_ledger.exists():
            raise FileExistsError("ledger restore target already exists")
        if target_artifacts.exists() and any(target_artifacts.iterdir()):
            raise FileExistsError("artifact restore target is not empty")
        artifact_staging = target_artifacts.with_name(f".{target_artifacts.name}.restore-{os.getpid()}")
        shutil.rmtree(artifact_staging, ignore_errors=True)
        try:
            artifact_staging.mkdir(parents=True)
            for cid, digest in manifest["artifacts"].items():
                raw = (source_artifacts / cid).read_bytes()
                if hashlib.sha256(raw).hexdigest() != digest or cid_for(json.loads(raw)) != cid:
                    raise OSError("artifact snapshot digest mismatch")
                (artifact_staging / cid).write_bytes(raw)
            DuckDBPaymentLedger.restore_backup(snapshot / "ledger.duckdb", target_ledger,
                                                sha256=manifest["ledger"]["sha256"])
            if target_artifacts.exists():
                target_artifacts.rmdir()
            os.replace(artifact_staging, target_artifacts)
            return manifest
        except Exception:
            target_ledger.unlink(missing_ok=True)
            target_ledger.with_suffix(target_ledger.suffix + ".wal").unlink(missing_ok=True)
            raise
        finally:
            shutil.rmtree(artifact_staging, ignore_errors=True)


def assert_redacted_surface(value: Any) -> None:
    """Defense-in-depth gate for generated dashboards, probes, and evidence."""
    encoded = canonical_json(value).lower()
    forbidden = (b"privatekey", b"seedphrase", b"mnemonic", b"paymentsignature",
                 b"walletaddress", b"transactionhash", b"requestarguments",
                 b"protectedinput", b"protectedoutput", b"paymentpayload")
    if any(token in encoded for token in forbidden):
        raise ValueError("operational surface contains a forbidden sensitive field")
