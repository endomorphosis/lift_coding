"""Profile H's native HTTP control plane must not execute protected work."""

from __future__ import annotations

import pytest

from mcplusplus_profile_h.http import ProfileHHttpApp
from mcplusplus_profile_h.interop import CASES, FIXED_NOW_MS, MockFacilitator, _authorization, _context, build_service


def _request_context(context):
    return {
        "requestCid": context.request_cid,
        "idempotencyKey": context.idempotency_key,
        "authorized": context.authorized,
        "policyAllowed": context.policy_allowed,
        "attributes": dict(context.attributes),
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("case", CASES, ids=lambda case: case.seller)
async def test_profile_h_http_control_lifecycle_is_durable_and_non_executing(tmp_path, case):
    service = build_service(case, tmp_path / case.seller, MockFacilitator())
    app = ProfileHHttpApp(service.control_plane)
    context = _context(case, "http-control")
    request_context = _request_context(context)

    status, _headers, profile = await app.handle("GET", "/mcp/payments/profile")
    assert status == 200
    assert profile["ready"] is True
    assert profile["mode"] == "local-test"
    assert set(profile["transports"]) == {"http", "libp2p"}

    # The signed catalog is public discovery material. It must not require a
    # request context, otherwise a client cannot form a request-bound quote.
    status, headers, catalog = await app.handle("GET", "/mcp/payments/catalog")
    assert status == 200
    assert headers["etag"] == f'"{catalog["signedCatalogCid"]}"'

    quote_request = {
        "operation": case.operation,
        "params": case.params,
        "requestContext": request_context,
    }
    status, _headers, quote = await app.handle("POST", "/mcp/payments/quote", payload=quote_request)
    assert status == 200
    assert quote["decision"] == "payment_required"
    assert quote["paymentRequired"]["error"] == "H_PAYMENT_REQUIRED"

    payment_context = _authorization(quote["paymentRequired"], quote["quote"])
    payment_request = {**quote_request, "paymentContext": payment_context}
    status, _headers, verification = await app.handle("POST", "/mcp/payments/verify", payload=payment_request)
    assert status == 200
    assert verification["decision"] == "paid"
    assert service.runtime.ledger.get(context.idempotency_key).state == "verified"

    status, _headers, settlement = await app.handle("POST", "/mcp/payments/settle", payload=payment_request)
    assert status == 200
    assert settlement["decision"] == "paid"
    # Control-plane settlement deliberately stops before the protected callback.
    assert service.runtime.ledger.get(context.idempotency_key).state == "settled"

    status, _headers, receipt = await app.handle(
        "GET",
        f'/mcp/payments/receipts/{settlement["receiptCid"]}',
        # Dataset requests derive a canonical commercial request CID from the
        # caller CID and protected query commitment. The quote publishes that
        # CID, so later evidence lookups do not need to expose query content.
        query={"requestContext": {**request_context, "requestCid": quote["quote"]["requestCid"]}},
    )
    assert status == 200
    assert receipt["state"] == "settled"
    assert receipt["artifact"]["schema"] == "mcp++/profile-h/settlement-receipt@1.0"
    assert receipt["artifact"]["settledAt"] >= FIXED_NOW_MS
