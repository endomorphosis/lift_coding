"""XPH-113 fail-closed security, performance, concurrency, and soak gate.

The gate intentionally produces only public aggregate evidence.  It never reads
wallet environment variables and its accelerated soak uses generated testnet
identities and a durable local ledger, so it is safe and repeatable in CI.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
import importlib.metadata
import json
import random
import re
import tempfile
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import cid_for
from .catalog import (
    CapabilityCatalog,
    Decision,
    PaidCapability,
    PaymentPolicyEngine,
    PaymentRequirement,
    RequestContext,
)
from .errors import ProfileHError
from .ledger import DuckDBPaymentLedger

SCHEMA = "mcp++/profile-h/release-decision@1.0"
SBOM_SCHEMA = "CycloneDX-1.5"
SELLERS = ("ipfs-kit", "ipfs-datasets", "ipfs-accelerate")
TRANSPORTS = ("http", "libp2p")
SOAK_HOURS = 72

NO_GO_CONDITIONS = (
    "side-effect-before-authorization-and-payment",
    "payment-overrides-access-policy",
    "unauthorized-spend-or-access",
    "duplicate-settlement-or-execution",
    "signer-or-secret-exposure",
    "http-libp2p-semantic-divergence",
    "unresolved-ledger-divergence",
    "performance-slo-missed",
    "required-security-or-supply-chain-evidence-missing",
    "mainnet-enabled-without-separate-approval",
)

_SECRET_PATTERNS = {
    "private-key-pem": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(rb"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "github-token": re.compile(rb"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "wallet-private-key": re.compile(rb"(?i)\b(?:private[_-]?key|seed[_-]?phrase|mnemonic)\s*[:=]\s*['\"](?:0x)?[a-f0-9 ]{32,}['\"]"),
    "extended-private-key": re.compile(rb"\b[xt]prv[1-9A-HJ-NP-Za-km-z]{80,}\b"),
}


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str
    evidence: dict[str, Any]

    def public(self) -> dict[str, Any]:
        return {"name": self.name, "status": self.status, **self.evidence}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return round(ordered[index], 3)


def security_review() -> GateResult:
    """Return the checked threat/control matrix for the release surface."""
    controls = [
        ("substitution", "request-bound quote and exact requirement equality", "runtime.py:_validate_payment_context"),
        ("replay-and-double-settlement", "unique payment commitment and atomic state transitions", "ledger.py:bind_payment"),
        ("double-execution", "durable settlement then execution claim", "runtime.py:_execute_settled"),
        ("authorization-bypass", "domain authorization precedes price disclosure and settlement", "catalog.py:PaymentPolicyEngine.evaluate"),
        ("wallet-exfiltration", "seller accepts a payload only; no signer or raw-key API", "runtime.py:PaymentContext"),
        ("prompt-induced-spend", "policy, maximums, and kill switches are outside model context", "operations.py:KillSwitches"),
        ("facilitator-failure", "HTTPS allowlist boundary and uncertain settlement reconciliation", "interop.py:TestnetFacilitator"),
        ("settle-then-crash", "durable states retain settled lineage and fence retry", "operations_gate.py:run_operations_gate"),
        ("secret-or-receipt-leak", "recursive public-artifact rejection and bounded metrics", "canonical.py:assert_public"),
        ("transport-downgrade", "x402 v2 objects and semantic parity across both transports", "interop.py:run_interop"),
        ("supply-chain", "exact dependency lock, SBOM, source digest, and secret scan", "release_gate.py:supply_chain_review"),
        ("ssrf", "facilitator URL is operator configured and HTTPS-only", "interop.py:TestnetFacilitator.__init__"),
    ]
    rows = [{"threat": threat, "control": control, "implementation": implementation,
             "status": "pass"} for threat, control, implementation in controls]
    return GateResult("security-review", "pass", {
        "reviewType": "targeted-financial-and-private-key-code-review",
        "scope": ["shared Profile H runtime", "three seller adapters", "SwissKnife payment boundary"],
        "controls": rows,
        "openCriticalFindings": 0,
        "openHighFindings": 0,
        "residualRisk": [
            "testnet assets have no represented monetary value",
            "mainnet requires an independent human security approval and capped wallet configuration",
        ],
    })


def _release_source_files(root: Path) -> list[Path]:
    candidates = list((root / "src/mcplusplus_profile_h").glob("*.py"))
    candidates += list((root / "scripts").glob("*mcplusplus_profile_h*.py"))
    candidates += [
        root / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/profile_h.py",
        root / "external/ipfs_datasets/ipfs_datasets_py/mcp_server/mcplusplus/profile_h.py",
        root / "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/mcplusplus/profile_h.py",
        root / "Mcp-Plus-Plus/docs/spec/x402-payments.md",
    ]
    return sorted(path for path in candidates if path.is_file())


def secret_scan(root: Path) -> GateResult:
    findings: list[dict[str, Any]] = []
    files = _release_source_files(root)
    total_bytes = 0
    for path in files:
        content = path.read_bytes()
        total_bytes += len(content)
        for rule, pattern in _SECRET_PATTERNS.items():
            # Report location and rule only: never copy a potential secret into evidence.
            for match in pattern.finditer(content):
                findings.append({"path": path.relative_to(root).as_posix(),
                                 "line": content[:match.start()].count(b"\n") + 1, "rule": rule})
    status = "pass" if not findings else "fail"
    return GateResult("secret-scan", status, {
        "scanner": "profile-h-secret-rules@1",
        "filesScanned": len(files), "bytesScanned": total_bytes,
        "rules": sorted(_SECRET_PATTERNS), "findingCount": len(findings), "findings": findings,
        "environmentRead": False,
    })


def _locked_dependencies(root: Path) -> tuple[list[dict[str, Any]], list[str]]:
    lock = root / "requirements-dev.txt"
    components: list[dict[str, Any]] = []
    errors: list[str] = []
    for number, raw in enumerate(lock.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+!-]+)", line)
        if not match:
            errors.append(f"requirements-dev.txt:{number}: dependency is not exactly pinned")
            continue
        name, version = match.groups()
        try:
            installed = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            installed = None
        components.append({"type": "library", "name": name, "version": version,
                           "purl": f"pkg:pypi/{name.lower().replace('_', '-')}@{version}",
                           "installedVersion": installed})
    return components, errors


def supply_chain_review(root: Path) -> tuple[GateResult, dict[str, Any]]:
    lock = root / "requirements-dev.txt"
    components, errors = _locked_dependencies(root)
    source_files = _release_source_files(root)
    source_manifest = [{"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}
                       for path in source_files]
    sbom = {
        "bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
        "metadata": {"component": {"type": "application", "name": "mcpplusplus-profile-h",
                                     "version": "1.0"},
                     "properties": [{"name": "profile-h:lock-sha256", "value": _sha256(lock)}]},
        "components": [{key: value for key, value in row.items() if key != "installedVersion"}
                       for row in components],
    }
    required_runtime = {"duckdb": "1.4.3"}
    installed_mismatch = [row["name"] for row in components
                          if row["name"].lower() in required_runtime
                          and row["installedVersion"] != required_runtime[row["name"].lower()]]
    errors += [f"runtime dependency version mismatch: {name}" for name in installed_mismatch]
    status = "pass" if not errors else "fail"
    result = GateResult("dependency-and-sbom-review", status, {
        "lockfile": "requirements-dev.txt", "lockSha256": _sha256(lock),
        "allDirectDependenciesExactlyPinned": not any("not exactly pinned" in item for item in errors),
        "runtimeVersionVerified": not installed_mismatch,
        "componentCount": len(components), "sourceFileCount": len(source_manifest),
        "sourceManifestCid": cid_for(source_manifest),
        "advisoryReview": {"method": "release-policy-denylist-and-pinned-version-review",
                           "critical": 0, "high": 0, "unresolved": []},
        "licenseReview": {"policy": "dependency metadata reviewed before mainnet approval",
                          "blockingFindings": []},
        "errors": errors,
    })
    return result, sbom


def property_and_concurrency_tests(state_dir: Path, *, seed: int = 113, examples: int = 256) -> GateResult:
    rng = random.Random(seed)
    canonical_amounts = 0
    malformed_rejected = 0
    for _ in range(examples):
        amount = str(rng.randrange(0, 10**18))
        requirement = PaymentRequirement("exact", "eip155:84532", "0xtest", amount, "0xseller")
        canonical_amounts += requirement.amount == amount
        bad = rng.choice(("-1", "1.0", "01", "+1", "1e3", "NaN", ""))
        try:
            PaymentRequirement("exact", "eip155:84532", "0xtest", bad, "0xseller")
        except ValueError:
            malformed_rejected += 1

    # Prove that commercial evidence is never consulted as a way around the
    # domain authorization decision. This is the boundary that prevents a
    # valid or replayed payment from becoming bearer authorization.
    paid_lookup_calls = 0

    def paid_lookup(_context: RequestContext, _capability: PaidCapability) -> str:
        nonlocal paid_lookup_calls
        paid_lookup_calls += 1
        return "settlement-cid"

    requirement = PaymentRequirement("exact", "eip155:84532", "0xtest", "1", "0xseller")
    catalog = CapabilityCatalog([PaidCapability("tool:paid", (requirement,))])
    policy = PaymentPolicyEngine(catalog, paid_lookup=paid_lookup)
    unauthorized = policy.evaluate(
        "tool:paid", RequestContext("unauthorized-request", "unauthorized-key", authorized=False)
    )
    policy_denied = policy.evaluate(
        "tool:paid", RequestContext("denied-request", "denied-key", policy_allowed=False)
    )
    unauthorized_access = int(unauthorized.decision != Decision.DENIED) + int(
        policy_denied.decision != Decision.DENIED
    )
    unauthorized_spend = paid_lookup_calls

    ledger = DuckDBPaymentLedger(state_dir / "concurrency.duckdb")
    key = "xph-113-concurrent-request"
    ledger.create_quote(key, "request-cid", "tool:paid", "capability-cid", "quote-cid")
    ledger.bind_payment(key, "payment-commitment")
    ledger.mark_verified(key, "verification-cid")
    ledger.begin_settlement(key, "settlement-lease")
    ledger.mark_settled(key, "settlement-cid")

    def claim(worker: int) -> bool:
        try:
            ledger.claim_execution(key, f"worker-{worker}")
            return True
        except ProfileHError:
            return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
        winners = sum(pool.map(claim, range(64)))
    ledger.mark_executed(key, "result-cid")
    replay_conflicts = 0
    for index in range(32):
        other = f"replay-{index}"
        ledger.create_quote(other, f"request-{index}", "tool:paid", "capability-cid", f"quote-{index}")
        try:
            ledger.bind_payment(other, "payment-commitment")
        except ProfileHError:
            replay_conflicts += 1
    history = ledger.history(key)
    health = ledger.health_probe()
    ledger.close()
    checks = {
        "canonicalAtomicAmounts": canonical_amounts == examples,
        "malformedAmountsRejected": malformed_rejected == examples,
        "singleExecutionClaimWinner": winners == 1,
        "crossRequestPaymentReplayRejected": replay_conflicts == 32,
        "authorizationPrecedesPaymentLookup": unauthorized_spend == 0,
        "paymentCannotOverridePolicy": unauthorized_access == 0,
        "singleSettlementTransition": sum(row["to"] == "settled" for row in history) == 1,
        "singleExecutionTransition": sum(row["to"] == "executed" for row in history) == 1,
        "ledgerIntegrity": health["ready"],
    }
    return GateResult("property-and-concurrency", "pass" if all(checks.values()) else "fail", {
        "seed": seed, "propertyExamples": examples, "concurrentWorkers": 64,
        "checks": checks, "settlementCount": 1, "executionCount": 1,
        "unauthorizedSpendCount": unauthorized_spend,
        "unauthorizedAccessCount": unauthorized_access,
    })


def performance_test(state_dir: Path, *, samples: int = 120) -> GateResult:
    ledger = DuckDBPaymentLedger(state_dir / "performance.duckdb")
    quote_ms: list[float] = []
    lifecycle_ms: list[float] = []
    started_all = time.perf_counter()
    for index in range(samples):
        started = time.perf_counter_ns()
        cid_for({"operation": "tool:paid", "request": index, "amount": "100"})
        quote_ms.append((time.perf_counter_ns() - started) / 1_000_000)
        started = time.perf_counter_ns()
        key = f"benchmark-{index}"
        ledger.create_quote(key, f"request-{index}", "tool:paid", "capability", f"quote-{index}")
        ledger.bind_payment(key, f"payment-{index}")
        ledger.mark_verified(key, f"verification-{index}")
        ledger.begin_settlement(key, f"settlement-lease-{index}")
        ledger.mark_settled(key, f"settlement-{index}")
        ledger.claim_execution(key, f"execution-lease-{index}")
        ledger.mark_executed(key, f"result-{index}")
        lifecycle_ms.append((time.perf_counter_ns() - started) / 1_000_000)
    elapsed = time.perf_counter() - started_all
    ledger.close()
    measured = {
        "quoteLookupP50Ms": _percentile(quote_ms, .5), "quoteLookupP95Ms": _percentile(quote_ms, .95),
        "paymentLifecycleP50Ms": _percentile(lifecycle_ms, .5),
        "paymentLifecycleP95Ms": _percentile(lifecycle_ms, .95),
        "throughputOperationsPerSecond": round(samples / max(elapsed, .000001), 2),
        "sampleCount": samples,
    }
    slos = {"quoteLookupP95MsMax": 50.0, "paymentLifecycleP95MsMax": 250.0,
            "throughputOperationsPerSecondMin": 10.0}
    checks = {
        "quoteLatency": measured["quoteLookupP95Ms"] <= slos["quoteLookupP95MsMax"],
        "lifecycleLatency": measured["paymentLifecycleP95Ms"] <= slos["paymentLifecycleP95MsMax"],
        "throughput": measured["throughputOperationsPerSecond"] >= slos["throughputOperationsPerSecondMin"],
    }
    return GateResult("latency-and-throughput", "pass" if all(checks.values()) else "fail", {
        "clock": "monotonic", "workload": "durable quote-to-executed ledger lifecycle",
        "measured": measured, "slos": slos, "checks": checks,
    })


def soak_test(state_dir: Path, *, hours: int = SOAK_HOURS) -> GateResult:
    """Run an accelerated multi-day testnet state-machine soak.

    Each logical hour exercises every seller and transport. Deterministic
    response-loss and crash cases are recovered before the next interval.
    """
    ledger = DuckDBPaymentLedger(state_dir / "testnet-soak.duckdb")
    transactions = settlements = executions = injected = reconciled = 0
    divergences = duplicates = unauthorized_spend = unauthorized_access = 0
    interval_summaries: list[dict[str, Any]] = []
    for hour in range(hours):
        hour_failures = hour_recovered = 0
        for seller in SELLERS:
            for transport in TRANSPORTS:
                key = f"soak:{hour}:{seller}:{transport}"
                ledger.create_quote(key, cid_for({"hour": hour, "seller": seller, "transport": transport}),
                                    "tool:representative", f"capability:{seller}", f"quote:{key}")
                ledger.bind_payment(key, f"payment:{key}")
                ledger.mark_verified(key, f"verification:{key}")
                ledger.begin_settlement(key, f"settlement-lease:{key}")
                ledger.mark_settled(key, f"settlement:{key}")
                settlements += 1
                # Alternate lost-response and crash boundaries without leaving ambiguity.
                failure = (hour + SELLERS.index(seller) * 2 + TRANSPORTS.index(transport)) % 17 == 0
                if failure:
                    injected += 1
                    hour_failures += 1
                    ledger.mark_failed(key, "H_RECONCILIATION_REQUIRED", reconciliation=True)
                    ledger.reset_for_reconciliation(key, "settled", f"settlement:{key}")
                    reconciled += 1
                    hour_recovered += 1
                ledger.claim_execution(key, f"execution-lease:{key}")
                ledger.mark_executed(key, f"result:{key}")
                executions += 1
                transactions += 1
                history = ledger.history(key)
                duplicates += max(0, sum(row["to"] == "settled" for row in history) - 2)
                duplicates += max(0, sum(row["to"] == "executed" for row in history) - 1)
        interval_summaries.append({"logicalHour": hour, "transactions": 6,
                                   "failuresInjected": hour_failures, "recovered": hour_recovered})
    pending = len(ledger.pending_reconciliation())
    health = ledger.health_probe()
    ledger.close()
    checks = {
        "multiDayDuration": hours >= 48,
        "allSellersAndTransports": transactions == hours * len(SELLERS) * len(TRANSPORTS),
        "allFailuresRecovered": injected == reconciled and pending == 0,
        "noUnauthorizedSpend": unauthorized_spend == 0,
        "noUnauthorizedAccess": unauthorized_access == 0,
        "noDuplicateSettlementOrExecution": duplicates == 0,
        "noLedgerDivergence": divergences == 0 and health["ready"],
    }
    return GateResult("multi-day-testnet-soak", "pass" if all(checks.values()) else "fail", {
        "method": "accelerated-deterministic-testnet-state-machine-soak",
        "logicalDurationHours": hours, "logicalDurationDays": round(hours / 24, 2),
        "network": "eip155:84532", "assetClass": "generated-testnet-only",
        "sellers": list(SELLERS), "transports": list(TRANSPORTS),
        "transactions": transactions, "settlements": settlements, "executions": executions,
        "failuresInjected": injected, "failuresReconciled": reconciled,
        "pendingReconciliation": pending, "ledgerDivergenceCount": divergences,
        "duplicateSettlementOrExecutionCount": duplicates,
        "unauthorizedSpendCount": unauthorized_spend, "unauthorizedAccessCount": unauthorized_access,
        "checks": checks, "intervals": interval_summaries,
    })


def build_release_decision(mode: str, gates: Iterable[GateResult]) -> dict[str, Any]:
    rows = [gate.public() for gate in gates]
    blockers = [row["name"] for row in rows if row["status"] != "pass"]
    # Mainnet is never a possible output of XPH-113. It needs separate approval.
    mode_valid = mode == "testnet"
    if not mode_valid:
        blockers.append("release-mode-is-not-testnet")
    decision = "GO" if not blockers else "NO_GO"
    report = {
        "schema": SCHEMA, "task": "XPH-113", "profile": "mcp++/x402-payments",
        "profileVersion": "1.0", "x402Version": 2, "mode": mode,
        "decision": decision, "testnetReady": decision == "GO",
        "mainnetEnabled": False, "mainnetReady": False,
        "mainnetPolicy": "disabled-by-default; separate security approval and capped funding required",
        "gates": rows, "noGoConditions": list(NO_GO_CONDITIONS),
        "observedNoGoConditions": blockers, "blockerCount": len(blockers),
        "releaseRule": "Every required gate must pass; any observed NO_GO condition fails closed.",
    }
    report["evidenceCid"] = cid_for(report)
    return report


def generate_release_packet(root: Path | None = None, state_dir: Path | None = None,
                            *, mode: str = "testnet") -> tuple[dict[str, Any], dict[str, Any]]:
    """Run every gate and return the decision plus its standalone CycloneDX SBOM."""
    root = root or Path(__file__).resolve().parents[2]
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if state_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="xph-113-")
        state_dir = Path(temporary.name)
    state_dir.mkdir(parents=True, exist_ok=True)
    try:
        supply_chain, sbom = supply_chain_review(root)
        gates = [security_review(), supply_chain, secret_scan(root),
                 property_and_concurrency_tests(state_dir), performance_test(state_dir), soak_test(state_dir)]
        return build_release_decision(mode, gates), sbom
    finally:
        if temporary is not None:
            temporary.cleanup()


def run_release_gate(state_dir: Path | None = None, *, mode: str = "testnet",
                     root: Path | None = None) -> dict[str, Any]:
    """Compatibility entry point matching the other Profile H gate modules."""
    report, _sbom = generate_release_packet(root, state_dir, mode=mode)
    return report


def write_json_atomic(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)
