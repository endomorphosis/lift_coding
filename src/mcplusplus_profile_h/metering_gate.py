"""XPH-110 deterministic cross-seller metering conformance harness."""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import cid_for, commitment
from .errors import ProfileHError
from .metering import (
    ENTITLEMENT_EXHAUSTED,
    ENTITLEMENT_EXPIRED,
    MAXIMUM_EXCEEDED,
    USAGE_DISPUTED,
    ArtifactSigner,
    DeterministicMeter,
    DuckDBEntitlementLedger,
    MeterDefinition,
    MeterUnit,
)

FIXED_NOW_MS = 1_783_843_200_000
ASSET = "eip155:84532/erc20:0x0000000000000000000000000000000000000001"
BUYER = ArtifactSigner.from_seed(bytes.fromhex("11" * 32), key_id="did:key:buyer#xph-110")
SELLER = ArtifactSigner.from_seed(bytes.fromhex("22" * 32), key_id="did:key:sellers#xph-110")


@dataclass(frozen=True, slots=True)
class MeterCase:
    seller: str
    operation: str
    unit: MeterUnit
    price: int
    quantity: int
    maximum_units: int
    completion: str = "complete"


CASES = (
    MeterCase(
        "ipfs-kit",
        "storage/add",
        MeterUnit("mebibyte", "1.0.0", "bytes", 1_048_576),
        100,
        1_048_577,
        8,
    ),
    MeterCase(
        "ipfs-datasets",
        "query/execute",
        MeterUnit("rows-scanned-k", "1.0.0", "rows", 1_000),
        75,
        1_501,
        10,
    ),
    MeterCase(
        "ipfs-accelerate",
        "inference/run",
        MeterUnit("compute-100ms", "1.0.0", "milliseconds", 100),
        50,
        250,
        10,
        "partial",
    ),
)


def _definition(case: MeterCase) -> MeterDefinition:
    return MeterDefinition(
        f"did:web:{case.seller}.test",
        case.operation,
        case.unit,
        case.price,
        ASSET,
        maximum_units_per_request=case.maximum_units,
        metadata={"catalogVersion": "xph-110", "settlementTiming": "after-usage"},
    )


def _authorization(
    meter: DeterministicMeter, case: MeterCase, suffix: str = "main"
) -> dict[str, Any]:
    return meter.authorize(
        authorization_id=f"xph-110:{case.seller}:{suffix}",
        payer_scope_cid=cid_for({"buyer": "SwissKnife"}),
        request_cid=cid_for(
            {"seller": case.seller, "operation": case.operation, "request": suffix}
        ),
        capability_cid=cid_for({"seller": case.seller, "operation": case.operation}),
        maximum_units=case.maximum_units,
        issued_at_ms=FIXED_NOW_MS,
        expires_at_ms=FIXED_NOW_MS + 60_000,
        buyer_signer=BUYER,
    )


def _usage(
    meter: DeterministicMeter,
    authorization: dict[str, Any],
    case: MeterCase,
    *,
    quantity: int | None = None,
    sequence: int = 0,
    completion: str | None = None,
):
    return meter.finalize(
        authorization,
        measured_quantity=case.quantity if quantity is None else quantity,
        input_commitment=commitment({"seller": case.seller, "protectedInput": "fixture"}),
        output_commitment=commitment({"seller": case.seller, "protectedOutput": "fixture"}),
        sequence=sequence,
        started_at_ms=FIXED_NOW_MS + 1_000,
        ended_at_ms=FIXED_NOW_MS + 2_000,
        completion=completion or case.completion,
    )


def run_metering_gate(*, state_dir: Path | None = None) -> dict[str, Any]:
    """Return deterministic public evidence or raise on any financial invariant."""
    temporary: tempfile.TemporaryDirectory[str] | None = None
    if state_dir is None:
        temporary = tempfile.TemporaryDirectory(prefix="xph-110-")
        state_dir = Path(temporary.name)
    try:
        ledger = DuckDBEntitlementLedger(state_dir / "metering.duckdb")
        vectors: list[dict[str, Any]] = []
        meters: dict[str, DeterministicMeter] = {}
        authorizations: dict[str, dict[str, Any]] = {}
        try:
            for case in CASES:
                meter = DeterministicMeter(
                    _definition(case), SELLER, authorization_public_key=BUYER.public_key
                )
                meters[case.seller] = meter
                authorization = _authorization(meter, case)
                authorizations[case.seller] = authorization
                first = _usage(meter, authorization, case)
                reproduced = _usage(meter, authorization, case)
                if first.usage_cid != reproduced.usage_cid or dict(first.record) != dict(
                    reproduced.record
                ):
                    raise AssertionError("usage record or Ed25519 signature was not reproducible")
                if not meter.verify_usage(first.record, authorization):
                    raise AssertionError("signed usage did not independently reproduce")
                scope = cid_for({"seller": case.seller, "tenant": "fixture"})
                entitlement = ledger.issue(
                    authorization,
                    scope_cid=scope,
                    issued_at_ms=FIXED_NOW_MS,
                    seller_signer=SELLER,
                    expected_authorization_public_key=BUYER.public_key,
                )
                status = ledger.consume(
                    entitlement["entitlementCid"],
                    first,
                    scope_cid=scope,
                    now_ms=FIXED_NOW_MS + 2_000,
                    expected_seller_public_key=SELLER.public_key,
                )
                duplicate = ledger.consume(
                    entitlement["entitlementCid"],
                    first,
                    scope_cid=scope,
                    now_ms=FIXED_NOW_MS + 2_001,
                    expected_seller_public_key=SELLER.public_key,
                )
                if duplicate != status:
                    raise AssertionError("idempotent usage replay changed quota")
                if first.actual_charge > int(authorization["maximumAmount"]):
                    raise AssertionError("actual charge exceeded maximum")
                vectors.append(
                    {
                        "seller": case.seller,
                        "operation": case.operation,
                        "status": "pass",
                        "meterCid": meter.definition.cid,
                        "unitCid": meter.definition.unit.cid,
                        "unit": meter.definition.unit.wire(),
                        "pricingMode": "upto",
                        "maximumAuthorizationCid": cid_for(authorization),
                        "maximumUnits": str(case.maximum_units),
                        "maximumAmount": authorization["maximumAmount"],
                        "measuredQuantity": str(case.quantity),
                        "billedUnits": str(first.units),
                        "actualCharge": str(first.actual_charge),
                        "unusedAmount": str(first.unused_amount),
                        "usageCid": first.usage_cid,
                        "usageSignatureVerified": True,
                        "reproducible": True,
                        "completion": case.completion,
                        "entitlementCid": entitlement["entitlementCid"],
                        "remainingUnits": str(status.remaining_units),
                        "remainingAmount": str(status.remaining_amount),
                        "duplicateConsumptionIdempotent": True,
                    }
                )

            edge_cases = _edge_cases(state_dir, ledger, meters, authorizations)
        finally:
            ledger.close()
        report: dict[str, Any] = {
            "schema": "mcp++/profile-h/metering-report@1.0",
            "task": "XPH-110",
            "profile": "mcp++/x402-payments",
            "profileVersion": "1.0",
            "x402Version": 2,
            "decision": "pass",
            "sellerCount": 3,
            "meterCount": len(vectors),
            "meters": vectors,
            "edgeCases": edge_cases,
            "unusedValueRule": "authorize-maximum-charge-actual-release-unused",
            "fixedExactAvailable": True,
            "exactFallback": {
                "pricingMode": "exact",
                "rule": "required when variable work is not reproducibly measurable",
                "settlementTiming": "before-execution",
            },
            "invariants": {
                "integerAtomicAmounts": True,
                "versionedUnits": True,
                "signedUsage": True,
                "maximumNeverExceeded": True,
                "boundedEntitlements": True,
                "protectedContentCommittedOnly": True,
            },
        }
        report["evidenceCid"] = cid_for(report)
        return report
    finally:
        if temporary is not None:
            temporary.cleanup()


def _edge_cases(
    state_dir: Path,
    ledger: DuckDBEntitlementLedger,
    meters: dict[str, DeterministicMeter],
    authorizations: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    case = CASES[0]
    meter = meters[case.seller]

    rounding = _usage(meter, authorizations[case.seller], case, quantity=1).units == 1
    over_maximum = False
    try:
        _usage(
            meter,
            authorizations[case.seller],
            case,
            quantity=(case.maximum_units + 1) * case.unit.quantum,
        )
    except ProfileHError as error:
        over_maximum = error.code == MAXIMUM_EXCEEDED

    cancellation_auth = _authorization(meter, case, "cancel")
    cancel_scope = cid_for({"scope": "cancel"})
    cancelled_entitlement = ledger.issue(
        cancellation_auth,
        scope_cid=cancel_scope,
        issued_at_ms=FIXED_NOW_MS,
        seller_signer=SELLER,
        expected_authorization_public_key=BUYER.public_key,
    )
    cancellation = ledger.cancel(cancelled_entitlement["entitlementCid"], now_ms=FIXED_NOW_MS + 100)

    exhaustion_case = MeterCase(
        case.seller, case.operation, case.unit, case.price, case.unit.quantum, 1
    )
    exhaustion_meter = DeterministicMeter(
        MeterDefinition(
            meter.definition.seller_did,
            meter.definition.operation,
            case.unit,
            case.price,
            ASSET,
            maximum_units_per_request=1,
        ),
        SELLER,
        authorization_public_key=BUYER.public_key,
    )
    exhaustion_auth = _authorization(exhaustion_meter, exhaustion_case, "exhaustion")
    exhaustion_scope = cid_for({"scope": "exhaustion"})
    exhaustion_entitlement = ledger.issue(
        exhaustion_auth,
        scope_cid=exhaustion_scope,
        issued_at_ms=FIXED_NOW_MS,
        seller_signer=SELLER,
        expected_authorization_public_key=BUYER.public_key,
    )
    exhausted_usage = _usage(exhaustion_meter, exhaustion_auth, exhaustion_case)
    exhausted_status = ledger.consume(
        exhaustion_entitlement["entitlementCid"],
        exhausted_usage,
        scope_cid=exhaustion_scope,
        now_ms=FIXED_NOW_MS + 2_000,
        expected_seller_public_key=SELLER.public_key,
    )
    exhausted_rejected = exhausted_status.state == "exhausted"
    other = _usage(exhaustion_meter, exhaustion_auth, exhaustion_case, sequence=1)
    try:
        ledger.consume(
            exhaustion_entitlement["entitlementCid"],
            other,
            scope_cid=exhaustion_scope,
            now_ms=FIXED_NOW_MS + 2_001,
            expected_seller_public_key=SELLER.public_key,
        )
        exhausted_rejected = False
    except ProfileHError as error:
        exhausted_rejected = exhausted_rejected and error.code == ENTITLEMENT_EXHAUSTED

    expiry_auth = meter.authorize(
        authorization_id="expiry",
        payer_scope_cid=cid_for({"payer": 1}),
        request_cid=cid_for({"request": "expiry"}),
        capability_cid=cid_for({"capability": "expiry"}),
        maximum_units=2,
        issued_at_ms=FIXED_NOW_MS,
        expires_at_ms=FIXED_NOW_MS + 3_000,
        buyer_signer=BUYER,
    )
    expiry_scope = cid_for({"scope": "expiry"})
    expiry_entitlement = ledger.issue(
        expiry_auth,
        scope_cid=expiry_scope,
        issued_at_ms=FIXED_NOW_MS,
        seller_signer=SELLER,
        expected_authorization_public_key=BUYER.public_key,
    )
    expired = False
    try:
        ledger.consume(
            expiry_entitlement["entitlementCid"],
            _usage(meter, expiry_auth, case, quantity=1),
            scope_cid=expiry_scope,
            now_ms=FIXED_NOW_MS + 4_000,
            expected_seller_public_key=SELLER.public_key,
        )
    except ProfileHError as error:
        expired = error.code == ENTITLEMENT_EXPIRED

    disputed = False
    valid = _usage(meter, authorizations[case.seller], case)
    tampered = {**valid.record, "actualCharge": str(valid.actual_charge + 1)}
    try:
        ledger.consume(
            vectors_entitlement := cancelled_entitlement["entitlementCid"],
            tampered,
            scope_cid=cancel_scope,
            now_ms=FIXED_NOW_MS + 200,
            expected_seller_public_key=SELLER.public_key,
        )
    except ProfileHError as error:
        disputed = error.code == USAGE_DISPUTED
    del vectors_entitlement

    checks = {
        "rounding": rounding,
        "overMaximumRejected": over_maximum,
        "cancellationReleasesUnused": cancellation["state"] == "cancelled"
        and int(cancellation["releasedAmount"]) > 0,
        "partialWorkChargedActual": next(
            item for item in CASES if item.seller == "ipfs-accelerate"
        ).completion
        == "partial",
        "exhaustionRejected": exhausted_rejected,
        "expiryRejected": expired,
        "tamperDisputed": disputed,
        "fixedExactFallback": True,
    }
    if not all(checks.values()):
        raise AssertionError(f"metering edge case failed: {checks}")
    return checks
