"""Executable three-seller Profile H HTTP/libp2p interoperability harness.

The harness intentionally calls the public seller facades rather than their
shared runtime directly.  This catches drift in route mapping, x402 header
encoding, Profile E envelopes, request binding, and seller-owned receipts.
"""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .adapters import SettlementResult, VerificationResult
from .canonical import canonical_json, cid_for, commitment
from .catalog import RequestContext
from .errors import ProfileHError


NETWORK = "eip155:84532"
ASSET = "0x0000000000000000000000000000000000000001"
PAY_TO = "0x1111111111111111111111111111111111111111"
FIXED_NOW_MS = 1_783_843_200_000
ROOT = Path(__file__).resolve().parents[2]
_SELLER_MODULES: tuple[Any, Any, Any] | None = None


class MockFacilitator:
    """Stateful, secret-free facilitator with controllable failure boundaries."""

    mode = "mock-facilitator"

    def __init__(self) -> None:
        self.verify_calls = 0
        self.settle_calls = 0
        self.lookup_calls = 0
        self._settled: dict[str, SettlementResult] = {}

    async def verify(self, payload: Mapping[str, Any], requirement: Any) -> VerificationResult:
        self.verify_calls += 1
        signature = payload.get("payload", {}).get("signature")
        valid = isinstance(signature, str) and signature not in {"", "invalid"}
        return VerificationResult(valid, "H_PAYMENT_VERIFIED" if valid else "H_VERIFICATION_FAILED",
                                  "did:web:mock-facilitator.test")

    async def settle(self, payload: Mapping[str, Any], requirement: Any) -> SettlementResult:
        self.settle_calls += 1
        behavior = payload.get("payload", {}).get("behavior", "success")
        result = SettlementResult(True, requirement.network,
                                  "0x" + commitment(payload)[-40:], response={"source": self.mode})
        if behavior == "decline":
            return SettlementResult(False, requirement.network, reason_code="H_SETTLEMENT_FAILED")
        if behavior == "timeout-after-commit":
            self._settled[commitment(payload)] = result
            raise TimeoutError("simulated response loss after facilitator commit")
        self._settled[commitment(payload)] = result
        return result

    async def lookup(self, payment_commitment: str) -> SettlementResult | None:
        self.lookup_calls += 1
        return self._settled.get(payment_commitment)

    async def health(self) -> bool:
        return True


class TestnetFacilitator:
    """Minimal x402 v2 facilitator HTTP adapter for opt-in testnet runs.

    Payment authorization material is accepted only from an environment
    variable by the CLI and is never included in the evidence report.
    """

    mode = "testnet-facilitator"

    def __init__(self, url: str, *, timeout: float = 20.0) -> None:
        if not url.startswith("https://"):
            raise ValueError("testnet facilitator URL must use HTTPS")
        self.url = url.rstrip("/")
        self.timeout = timeout

    def _post(self, endpoint: str, payload: Mapping[str, Any], requirement: Any) -> dict[str, Any]:
        body = canonical_json({"paymentPayload": dict(payload), "paymentRequirements": requirement.wire()})
        request = urllib.request.Request(self.url + endpoint, data=body,
                                         headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                value = json.loads(response.read())
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
            raise ProfileHError("H_FACILITATOR_UNAVAILABLE", "testnet facilitator unavailable", retryable=True) from error
        if not isinstance(value, dict):
            raise ProfileHError("H_INVALID_PAYMENT_MESSAGE", "facilitator returned a non-object")
        return value

    async def verify(self, payload: Mapping[str, Any], requirement: Any) -> VerificationResult:
        value = await asyncio.to_thread(self._post, "/verify", payload, requirement)
        valid = bool(value.get("isValid", value.get("valid", False)))
        return VerificationResult(valid, str(value.get("invalidReason", "H_PAYMENT_VERIFIED")),
                                  "did:web:testnet-facilitator")

    async def settle(self, payload: Mapping[str, Any], requirement: Any) -> SettlementResult:
        value = await asyncio.to_thread(self._post, "/settle", payload, requirement)
        return SettlementResult(bool(value.get("success")), str(value.get("network", requirement.network)),
                                value.get("transaction"), str(value.get("errorReason", "")))

    async def lookup(self, payment_commitment: str) -> SettlementResult | None:
        return None

    async def health(self) -> bool:
        try:
            request = urllib.request.Request(self.url + "/supported", method="GET")
            await asyncio.to_thread(urllib.request.urlopen, request, None, self.timeout)
            return True
        except (urllib.error.URLError, TimeoutError):
            return False


@dataclass(frozen=True)
class SellerCase:
    seller: str
    operation: str
    route: str
    params: dict[str, Any]
    attributes: dict[str, Any]


CASES = (
    SellerCase("ipfs-kit", "storage/add", "/mcp/tools/storage/add",
               {"namespace": "tenant-a", "units": 1},
               {"subject": "swissknife-buyer", "namespaces": ("tenant-a",)}),
    SellerCase("ipfs-datasets", "query/execute", "/mcp/datasets/query",
               {"datasetId": "medical-records", "version": "3", "fields": ["diagnosis"],
                "filters": {"region": "us-west"}, "privacy": {"mode": "aggregate", "k": 5}, "limit": 10},
               {"subject": "swissknife-buyer", "tenant": "clinic-a", "licenses": ("research-only-v2",)}),
    SellerCase("ipfs-accelerate", "inference/run", "/mcp/accelerate/inference",
               {"tier": "interactive-cpu", "model": "text-small", "hardware": "cpu", "units": 1},
               {"subject": "swissknife-buyer", "models": ("text-small",), "hardware": ("cpu", "cuda")}),
)


def _load_sellers() -> tuple[Any, Any, Any]:
    # The checkouts vendor overlapping top-level package names. Loading exact
    # files prevents sys.path order from accidentally testing a vendored copy.
    global _SELLER_MODULES
    if _SELLER_MODULES is not None:
        return _SELLER_MODULES

    def exact(name: str, path: Path) -> Any:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load seller adapter: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    kit = exact("_xph109_ipfs_kit_profile_h",
                ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/profile_h.py")
    datasets = exact("_xph109_ipfs_datasets_profile_h",
                     ROOT / "external/ipfs_datasets/ipfs_datasets_py/mcp_server/mcplusplus/profile_h.py")
    accelerator = exact("_xph109_ipfs_accelerate_profile_h",
                        ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/mcp_server/mcplusplus/profile_h.py")
    _SELLER_MODULES = (
        (kit.PaidKitService, kit.KitPaymentConfig, kit.KitOperationTerms),
        (datasets.PaidDatasetService, datasets.DatasetPaymentConfig, datasets.DatasetPolicy),
        (accelerator.PaidAcceleratorService, accelerator.AcceleratorPaymentConfig, accelerator.ComputeTier),
    )
    return _SELLER_MODULES


def build_service(case: SellerCase, state: Path, facilitator: Any) -> Any:
    kit, datasets, accelerator = _load_sellers()
    common = dict(seller_did=f"did:web:{case.seller}.test", descriptor_cid=cid_for({"seller": case.seller}),
                  pay_to=PAY_TO, asset=ASSET, network=NETWORK, catalog_version="xph-109")
    if case.seller == "ipfs-kit":
        service, config, terms = kit
        value = config(**common, operations={"storage/add": terms("100", quota_units=8, unit="mebibyte",
                       max_request_units=8, namespaces=("tenant-a",))})
    elif case.seller == "ipfs-datasets":
        service, config, policy = datasets
        value = config(**common, datasets={"medical-v3": policy(
            dataset_id="medical-records", version="3", amount="75", license_id="research-only-v2",
            tenants=("clinic-a",), operations=("query/execute",), allowed_fields=("diagnosis",),
            row_constraints={"region": ("us-west",)}, privacy_modes=("aggregate",), max_rows=100, minimum_k=5)})
    else:
        service, config, tier = accelerator
        value = config(**common, tiers={"interactive-cpu": tier("50", unit="inference",
                       operations=("inference/run",), models=("text-small",), hardware=("cpu",))})
    return service(value, state, facilitator, clock_ms=lambda: FIXED_NOW_MS)


def _context(case: SellerCase, transport: str, suffix: str = "paid", *, authorized: bool = True) -> RequestContext:
    key = f"xph-109:{case.seller}:{transport}:{suffix}"
    return RequestContext(cid_for({"buyer": "SwissKnife", "key": key}), key, authorized=authorized,
                          attributes=case.attributes)


def _effect(case: SellerCase) -> Any:
    result_cid = cid_for({"seller": case.seller, "operation": case.operation, "result": "representative"})
    if case.seller == "ipfs-kit":
        return lambda: {"ok": True, "resultCid": result_cid}
    return lambda _handoff=None: {"ok": True, "resultCid": result_cid}


def _authorization(required: Mapping[str, Any], quote: Mapping[str, Any], *, signature: str = "isolated-wallet-signature",
                   behavior: str = "success", supplied_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    inner = dict(supplied_payload) if supplied_payload is not None else {"signature": signature, "behavior": behavior}
    return {"payload": {"x402Version": 2, "accepted": required["accepts"][0], "payload": inner},
            "quoteCid": cid_for(quote), "requestCid": quote["requestCid"], "requirementIndex": 0}


def _http_payment(value: Mapping[str, Any]) -> str:
    return base64.b64encode(canonical_json(value)).decode("ascii")


def _decode_header(value: str) -> dict[str, Any]:
    decoded = json.loads(base64.b64decode(value, validate=True))
    if not isinstance(decoded, dict):
        raise AssertionError("x402 header did not decode to an object")
    return decoded


def _artifact_check(service: Any, cid: str) -> dict[str, Any]:
    artifact = service.artifacts.get(cid)
    if artifact is None or cid_for(artifact) != cid:
        raise AssertionError(f"missing or invalid content-addressed artifact {cid}")
    return artifact


def _event_dag(service: Any, key: str, scenario: str) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    parent: str | None = None
    for transition in service.runtime.ledger.history(key):
        event = {"schema": "mcp++/profile-h/interop-event@1.0", "scenario": scenario,
                 "sequence": transition["sequence"], "from": transition["from"], "to": transition["to"],
                 "artifactCid": transition["artifactCid"], "reasonCode": transition["reasonCode"],
                 "parents": [parent] if parent else []}
        event_cid = cid_for(event)
        events.append({**event, "eventCid": event_cid})
        parent = event_cid
    return {"scenario": scenario, "rootCids": [events[-1]["eventCid"]] if events else [], "events": events,
            "acyclic": all(event["eventCid"] not in event["parents"] for event in events)}


async def _invoke_unpaid(service: Any, case: SellerCase, transport: str, context: RequestContext) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    if transport == "http":
        status, headers, body = await service.handle_http("POST", case.route, context, case.params, _effect(case))
        if status != 402 or "PAYMENT-REQUIRED" not in headers:
            raise AssertionError(f"{case.seller} HTTP did not return normative 402")
        return body, _decode_header(headers["PAYMENT-REQUIRED"]), body["quote"]
    wire = await service.handle_libp2p({"operation": case.operation, "params": case.params}, context, _effect(case))
    error = wire.get("error", {})
    if error.get("code") != "H_PAYMENT_REQUIRED":
        raise AssertionError(f"{case.seller} libp2p did not return payment-required envelope")
    return wire, error["payment_required"], error["quote"]


async def _invoke_paid(service: Any, case: SellerCase, transport: str, context: RequestContext,
                       authorization: Mapping[str, Any]) -> tuple[Any, dict[str, Any]]:
    if transport == "http":
        status, headers, body = await service.handle_http("POST", case.route, context, case.params, _effect(case),
                                                          payment_header=_http_payment(authorization))
        if status != 200 or "PAYMENT-RESPONSE" not in headers:
            raise AssertionError(f"{case.seller} HTTP payment did not settle")
        return body, _decode_header(headers["PAYMENT-RESPONSE"])
    wire = await service.handle_libp2p({"operation": case.operation, "params": case.params,
                                       "payment_context": authorization}, context, _effect(case))
    if "result" not in wire or not wire.get("payment_response", {}).get("success"):
        raise AssertionError(f"{case.seller} libp2p payment did not settle")
    return wire["result"], wire["payment_response"]


async def _row(root: Path, case: SellerCase, transport: str, facilitator: Any,
               supplied_payload: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    service = build_service(case, root / case.seller / transport, facilitator)
    context = _context(case, transport)
    unpaid_wire, required, quote = await _invoke_unpaid(service, case, transport, context)
    quote_cid = cid_for(quote)
    _artifact_check(service, quote_cid)
    authorization = _authorization(required, quote, supplied_payload=supplied_payload)
    result, settlement = await _invoke_paid(service, case, transport, context, authorization)
    entry = service.runtime.ledger.get(context.idempotency_key)
    if entry is None or entry.state != "executed" or not entry.settlement_cid or not entry.result_cid:
        raise AssertionError("paid operation did not reach durable executed state")
    settlement_artifact = _artifact_check(service, entry.settlement_cid)
    access_artifact = _artifact_check(service, entry.result_cid)
    replay_before = facilitator.settle_calls if hasattr(facilitator, "settle_calls") else None
    replay = await service.dispatch(case.operation, context, case.params, _effect(case))
    replay_ok = replay.replayed and (replay_before is None or facilitator.settle_calls == replay_before)

    denied_context = _context(case, transport, "denied", authorized=False)
    denied = await service.dispatch(case.operation, denied_context, case.params, _effect(case))
    auth_denied = str(denied.decision.decision) == "denied" and service.runtime.ledger.get(denied_context.idempotency_key) is None

    invalid_service = build_service(case, root / case.seller / (transport + "-invalid"), MockFacilitator())
    invalid_context = _context(case, transport, "invalid")
    _, invalid_required, invalid_quote = await _invoke_unpaid(invalid_service, case, transport, invalid_context)
    invalid_auth = _authorization(invalid_required, invalid_quote, signature="invalid")
    invalid_rejected = False
    try:
        await _invoke_paid(invalid_service, case, transport, invalid_context, invalid_auth)
    except ProfileHError as error:
        invalid_rejected = error.code == "H_PAYMENT_DECLINED"
    invalid_entry = invalid_service.runtime.ledger.get(invalid_context.idempotency_key)
    invalid_rejected = invalid_rejected and invalid_entry is not None and invalid_entry.state == "failed"

    semantic_result = result.get("resultCid") if isinstance(result, Mapping) else None
    row = {
        "seller": case.seller, "operation": case.operation, "transport": transport,
        "status": "pass", "buyer": "SwissKnife", "decision": "paid",
        "requirementsObjectCid": cid_for(required),
        "requirementsSemanticCid": cid_for({"x402Version": required.get("x402Version"),
                                             "error": required.get("error"), "accepts": required.get("accepts")}),
        "quoteCid": quote_cid,
        "settlementReceiptCid": entry.settlement_cid, "accessReceiptCid": entry.result_cid,
        "resultCid": semantic_result, "settlementNetwork": settlement.get("network"),
        "checks": {"unpaid": required.get("error") == "H_PAYMENT_REQUIRED", "invalid": invalid_rejected,
                   "authDenied": auth_denied, "duplicate": replay_ok, "receiptCids": True,
                   "settled": settlement_artifact.get("outcome") == "settled",
                   "accessAllowed": access_artifact.get("decision") == "allow"},
    }
    if not semantic_result or not all(row["checks"].values()):
        raise AssertionError(f"interop checks failed: {row}")
    decoded = {"seller": case.seller, "transport": transport, "paymentRequired": required,
               "paymentRequiredCid": cid_for(required), "quote": quote, "quoteCid": quote_cid,
               "paymentResponse": {key: value for key, value in settlement.items() if key != "transaction"},
               "unpaidEnvelopeCid": cid_for(unpaid_wire)}
    return row, decoded


async def _failure_dags(root: Path) -> list[dict[str, Any]]:
    case = CASES[0]
    dags: list[dict[str, Any]] = []

    facilitator = MockFacilitator()
    service = build_service(case, root / "failures" / "timeout", facilitator)
    context = _context(case, "failure", "timeout")
    _, required, quote = await _invoke_unpaid(service, case, "libp2p", context)
    try:
        await _invoke_paid(service, case, "libp2p", context,
                           _authorization(required, quote, behavior="timeout-after-commit"))
    except (ProfileHError, TimeoutError):
        pass
    if service.runtime.ledger.get(context.idempotency_key).state != "reconciliation_required":
        raise AssertionError("timeout was not fenced for reconciliation")
    reconciled = await service.reconcile()
    if not reconciled or reconciled[0].get("state") != "settled":
        raise AssertionError("unknown settlement did not reconcile by commitment")
    dags.append(_event_dag(service, context.idempotency_key, "timeout-and-reconciliation"))

    crash = build_service(case, root / "failures" / "crash", MockFacilitator())
    crash_context = _context(case, "failure", "crash")
    _, required, quote = await _invoke_unpaid(crash, case, "libp2p", crash_context)
    def fail() -> Any:
        raise RuntimeError("simulated crash at protected effect boundary")
    try:
        authorization = _authorization(required, quote)
        await crash.handle_libp2p({"operation": case.operation, "params": case.params,
                                   "payment_context": authorization}, crash_context, fail)
    except RuntimeError:
        pass
    if crash.runtime.ledger.get(crash_context.idempotency_key).state != "reconciliation_required":
        raise AssertionError("effect crash was not fenced")
    dags.append(_event_dag(crash, crash_context.idempotency_key, "crash-after-settlement"))

    restart_state = root / "failures" / "restart"
    restart_facilitator = MockFacilitator()
    first = build_service(case, restart_state, restart_facilitator)
    restart_context = _context(case, "failure", "restart")
    _, required, quote = await _invoke_unpaid(first, case, "libp2p", restart_context)
    await _invoke_paid(first, case, "libp2p", restart_context, _authorization(required, quote))
    first.runtime.ledger.connection.close()
    restarted = build_service(case, restart_state, restart_facilitator)
    before = restart_facilitator.settle_calls
    replay = await restarted.dispatch(case.operation, restart_context, case.params,
                                      lambda: (_ for _ in ()).throw(AssertionError("restart duplicated effect")))
    if not replay.replayed or restart_facilitator.settle_calls != before:
        raise AssertionError("restart did not preserve replay fence")
    dags.append(_event_dag(restarted, restart_context.idempotency_key, "durable-restart-replay"))
    if not all(dag["acyclic"] and dag["events"] for dag in dags):
        raise AssertionError("failure evidence is not a non-empty event DAG")
    return dags


def _parity(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    matrix = []
    for case in CASES:
        values = [row for row in rows if row["seller"] == case.seller]
        if {row["transport"] for row in values} != {"http", "libp2p"}:
            raise AssertionError(f"transport coverage missing for {case.seller}")
        left, right = sorted(values, key=lambda row: row["transport"])
        checks = {
            # quoteCid/requestCid extensions are correctly request-specific;
            # the offered commercial requirements must be transport-identical.
            "requirements": left["requirementsSemanticCid"] == right["requirementsSemanticCid"],
            "accessDecision": left["decision"] == right["decision"] == "paid",
            "results": left["resultCid"] == right["resultCid"],
            "receiptSemantics": all(row["checks"]["settled"] and row["checks"]["accessAllowed"] for row in values),
            "cidIntegrity": all(row["checks"]["receiptCids"] for row in values),
        }
        matrix.append({"seller": case.seller, "operation": case.operation, "http": "pass", "libp2p": "pass",
                       "checks": checks, "status": "pass" if all(checks.values()) else "fail"})
    if any(row["status"] != "pass" for row in matrix):
        raise AssertionError(f"HTTP/libp2p semantic parity failed: {matrix}")
    return matrix


async def run_interop(*, state_dir: Path | None = None, facilitator: Any | None = None,
                      supplied_payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Run all sellers/transports and return public, secret-free evidence."""
    facilitator = facilitator or MockFacilitator()
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if state_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="xph-109-")
        state_dir = Path(temporary.name)
    try:
        rows: list[dict[str, Any]] = []
        decoded: list[dict[str, Any]] = []
        for case in CASES:
            for transport in ("http", "libp2p"):
                payload = supplied_payload
                if supplied_payload is not None and isinstance(supplied_payload.get("payments"), Mapping):
                    selected = supplied_payload["payments"].get(f"{case.seller}:{transport}")
                    if not isinstance(selected, Mapping):
                        raise ValueError(f"testnet payload is missing payments.{case.seller}:{transport}")
                    payload = selected
                row, objects = await _row(state_dir, case, transport, facilitator, payload)
                rows.append(row)
                decoded.append(objects)
        matrix = _parity(rows)
        dags = await _failure_dags(state_dir)
        report = {
            "schema": "mcp++/profile-h/three-seller-interop@1.0", "task": "XPH-109",
            "profile": "mcp++/x402-payments", "profileVersion": "1.0", "x402Version": 2,
            "mode": facilitator.mode, "network": NETWORK, "buyer": "SwissKnife",
            "decision": "pass", "sellerCount": 3, "transportCount": 2,
            "representativePayments": rows, "parityMatrix": matrix,
            "decodedX402Objects": decoded, "eventDags": dags,
            "failureCoverage": ["unpaid", "invalid", "auth-denied", "duplicate", "timeout", "crash", "reconciliation", "restart"],
            "secretsPersisted": False,
        }
        report["evidenceCid"] = cid_for(report)
        return report
    finally:
        if temporary is not None:
            temporary.cleanup()


def load_testnet_payload_from_env() -> dict[str, Any]:
    raw = os.environ.get("X402_INTEROP_PAYMENT_PAYLOAD")
    if not raw:
        raise ValueError("testnet mode requires X402_INTEROP_PAYMENT_PAYLOAD in the process environment")
    value = json.loads(raw)
    if not isinstance(value, dict) or not value:
        raise ValueError("X402_INTEROP_PAYMENT_PAYLOAD must be a non-empty JSON object")
    return value
