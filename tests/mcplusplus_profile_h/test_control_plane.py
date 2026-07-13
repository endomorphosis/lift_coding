from __future__ import annotations

import pytest

from mcplusplus_profile_h import (
    CallbackFacilitator,
    CapabilityCatalog,
    CommercialBinding,
    DuckDBPaymentLedger,
    FileCIDArtifactStore,
    PaidCapability,
    PaymentPolicyEngine,
    PaymentRequirement,
    ProfileHControlPlane,
    SellerRuntime,
    SettlementResult,
    VerificationResult,
)
from mcplusplus_profile_h.canonical import cid_for


def _request_context(request_cid: str, key: str) -> dict[str, object]:
    return {
        "requestCid": request_cid,
        "idempotencyKey": key,
        "authorized": True,
        "policyAllowed": True,
        "attributes": {"subject": "did:key:buyer"},
    }


@pytest.mark.asyncio
async def test_control_plane_exposes_complete_durable_lifecycle_without_executing(tmp_path):
    selected = PaymentRequirement("exact", "eip155:84532", "0xtest", "1000", "0xseller")
    catalog = CapabilityCatalog([PaidCapability("tool:pin", (selected,))])
    calls = {"verify": 0, "settle": 0}

    def verify(_payload, _requirement):
        calls["verify"] += 1
        return VerificationResult(True, "H_PAYMENT_VERIFIED", evidence={"provider": "local-test"})

    def settle(_payload, requirement):
        calls["settle"] += 1
        return SettlementResult(True, requirement.network, "0xprivate")

    runtime = SellerRuntime(
        PaymentPolicyEngine(catalog),
        DuckDBPaymentLedger(tmp_path / "payments.duckdb"),
        CallbackFacilitator(verify, settle),
        FileCIDArtifactStore(tmp_path / "blocks"),
        seller_did="did:web:seller.test",
        descriptor_cid=cid_for({"descriptor": "test"}),
    )

    def bind(operation, context, _arguments):
        assert operation == "pin"
        return CommercialBinding("tool:pin", context)

    control = ProfileHControlPlane(
        runtime=runtime,
        catalog=catalog.public_document,
        bind=bind,
        reconcile=runtime.reconcile,
        mode="local-test",
        upstream_x402_http_conformance=False,
    )

    profile = await control.dispatch("mcp++/payments/profile")
    assert profile["ready"] is True
    assert profile["transports"] == ["http", "libp2p"]
    assert profile["mode"] == "local-test"
    assert profile["upstreamX402HttpConformance"] is False
    assert profile["durability"]["ledger"] == "durable"

    request_cid = cid_for({"request": 1})
    common = {
        "operation": "pin",
        "params": {"cid": "bafy-test"},
        "requestContext": _request_context(request_cid, "request-1"),
    }
    quote = await control.dispatch("mcp++/payments/quote", common)
    assert quote["decision"] == "payment_required"
    assert calls == {"verify": 0, "settle": 0}

    payment = {
        **common,
        "paymentContext": {
            "quoteCid": quote["receiptCid"],
            "requestCid": request_cid,
            "payload": {
                "x402Version": 2,
                "accepted": selected.wire(),
                "payload": {"signature": "never-persisted"},
            },
        },
    }
    verified = await control.dispatch("mcp++/payments/verify", payment)
    assert verified["decision"] == "paid"
    assert calls == {"verify": 1, "settle": 0}

    settled = await control.dispatch("mcp++/payments/settle", payment)
    assert settled["decision"] == "paid"
    assert calls == {"verify": 1, "settle": 1}

    receipt = await control.dispatch("mcp++/payments/receipt/get", {
        "receiptCid": settled["receiptCid"],
        "requestContext": common["requestContext"],
    })
    assert receipt["state"] == "settled"
    assert receipt["artifact"]["outcome"] == "settled"

    refund = await control.dispatch("mcp++/payments/refund/request", {
        "settlementCid": settled["receiptCid"],
        "reasonCode": "customer_request",
        "requestContext": common["requestContext"],
    })
    assert refund["status"] == "pending"
    assert refund["artifact"]["parents"] == [settled["receiptCid"]]

    reconciled = await control.dispatch("mcp++/payments/reconcile", {
        "requestContext": common["requestContext"],
    })
    assert reconciled == {
        "status": "reconciled",
        "outcomes": [{"idempotencyKey": "request-1", "state": "settled"}],
    }


@pytest.mark.asyncio
async def test_http_binding_rejects_unknown_routes_before_seller_dispatch(tmp_path):
    selected = PaymentRequirement("exact", "eip155:1", "asset", "1", "payee")
    catalog = CapabilityCatalog([PaidCapability("tool:paid", (selected,))])
    runtime = SellerRuntime(
        PaymentPolicyEngine(catalog),
        DuckDBPaymentLedger(tmp_path / "payments.duckdb"),
        CallbackFacilitator(
            lambda *_: VerificationResult(True),
            lambda *_: SettlementResult(True, "eip155:1"),
        ),
        FileCIDArtifactStore(tmp_path / "blocks"),
        seller_did="did:web:seller.test",
        descriptor_cid=cid_for({"descriptor": 1}),
    )
    control = ProfileHControlPlane(
        runtime=runtime,
        catalog=catalog.public_document,
        bind=lambda _operation, context, _arguments: CommercialBinding("tool:paid", context),
        reconcile=runtime.reconcile,
        mode="local-test",
        upstream_x402_http_conformance=False,
    )
    status, _, body = await control.handle_http("DELETE", "/mcp/payments/catalog")
    assert status == 404
    assert body["error"] == "H_METHOD_NOT_SUPPORTED"
