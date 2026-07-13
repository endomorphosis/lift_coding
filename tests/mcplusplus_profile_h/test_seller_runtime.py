from __future__ import annotations

import asyncio

import pytest

from mcplusplus_profile_h import (
    CallbackFacilitator,
    CapabilityCatalog,
    Decision,
    DuckDBPaymentLedger,
    FileCIDArtifactStore,
    PaidCapability,
    PaymentContext,
    PaymentPolicyEngine,
    PaymentRequirement,
    RequestContext,
    SellerRuntime,
    SettlementResult,
    VerificationResult,
    http_response,
)
from mcplusplus_profile_h.canonical import cid_for
from mcplusplus_profile_h.errors import REQUEST_MISMATCH, ProfileHError


def requirement() -> PaymentRequirement:
    return PaymentRequirement("exact", "eip155:84532", "0xtest", "1000", "0xseller")


def context(key: str = "request-1", *, authorized: bool = True) -> RequestContext:
    return RequestContext(cid_for({"request": key}), key, authorized=authorized)


def build(tmp_path, *, pause=False):
    paid = PaidCapability("tool:pin", (requirement(),))
    catalog = CapabilityCatalog([PaidCapability("tool:status", free=True), paid])
    ledger = DuckDBPaymentLedger(tmp_path / "payments.duckdb")
    calls = {"verify": 0, "settle": 0}

    def verify(payload, selected):
        calls["verify"] += 1
        return VerificationResult(True, "H_PAYMENT_VERIFIED", evidence={"provider": "test"})

    def settle(payload, selected):
        calls["settle"] += 1
        return SettlementResult(True, selected.network, "0xprivate-transaction-reference")

    facilitator = CallbackFacilitator(verify, settle)
    policy = PaymentPolicyEngine(catalog, emergency_pause=pause)
    runtime = SellerRuntime(
        policy,
        ledger,
        facilitator,
        FileCIDArtifactStore(tmp_path / "blocks"),
        seller_did="did:web:seller.test",
        descriptor_cid=cid_for({"descriptor": 1}),
    )
    return runtime, calls


def test_policy_decisions_are_deterministic(tmp_path):
    runtime, _ = build(tmp_path)
    ctx = context()
    assert runtime.policy.evaluate("tool:status", ctx).decision == Decision.FREE
    assert runtime.policy.evaluate("tool:unknown", ctx).decision == Decision.FREE
    assert runtime.policy.evaluate("tool:pin", ctx).decision == Decision.PAYMENT_REQUIRED
    assert runtime.policy.evaluate("tool:pin", context(authorized=False)).decision == Decision.DENIED
    runtime.policy.emergency_pause = True
    assert runtime.policy.evaluate("tool:pin", ctx).decision == Decision.UNAVAILABLE


@pytest.mark.asyncio
async def test_paid_dispatch_settles_immediately_before_effect_and_replays_result(tmp_path):
    runtime, calls = build(tmp_path)
    ctx = context()
    effects = 0

    async def effect():
        nonlocal effects
        effects += 1
        assert runtime.ledger.get(ctx.idempotency_key).state == "executing"
        return {"cid": "result"}

    required = await runtime.dispatch("tool:pin", ctx, effect)
    assert required.decision.decision == Decision.PAYMENT_REQUIRED
    status, headers, _ = http_response(required)
    assert status == 402 and "PAYMENT-REQUIRED" in headers
    payload = {"x402Version": 2, "accepted": requirement().wire(), "payload": {"signature": "not-persisted"}}
    paid = await runtime.dispatch(
        "tool:pin",
        ctx,
        effect,
        payment=PaymentContext(payload, required.receipt_cid, ctx.request_cid),
    )
    assert paid.decision.decision == Decision.PAID
    assert effects == calls["verify"] == calls["settle"] == 1
    replay = await runtime.dispatch("tool:pin", ctx, effect)
    assert replay.replayed is True
    assert effects == calls["settle"] == 1
    assert runtime.ledger.get(ctx.idempotency_key).state == "executed"

    stored = "".join(path.read_text() for path in (tmp_path / "blocks").iterdir())
    assert "not-persisted" not in stored
    assert "0xprivate-transaction-reference" not in stored


@pytest.mark.asyncio
async def test_substitution_rejected_before_verification_or_effect(tmp_path):
    runtime, calls = build(tmp_path)
    ctx = context()
    required = await runtime.dispatch("tool:pin", ctx, lambda: None)
    payload = {"x402Version": 2, "accepted": {**requirement().wire(), "amount": "999"}, "payload": {"sig": "x"}}
    with pytest.raises(ProfileHError) as raised:
        await runtime.dispatch("tool:pin", ctx, lambda: pytest.fail("effect ran"), payment=PaymentContext(payload, required.receipt_cid, ctx.request_cid))
    assert raised.value.code == REQUEST_MISMATCH
    assert calls == {"verify": 0, "settle": 0}


@pytest.mark.asyncio
async def test_concurrent_retry_executes_and_settles_at_most_once(tmp_path):
    runtime, calls = build(tmp_path)
    ctx = context()
    required = await runtime.dispatch("tool:pin", ctx, lambda: None)
    payload = {"x402Version": 2, "accepted": requirement().wire(), "payload": {"sig": "private"}}
    payment = PaymentContext(payload, required.receipt_cid, ctx.request_cid)
    effects = 0

    async def effect():
        nonlocal effects
        effects += 1
        await asyncio.sleep(0)
        return "done"

    results = await asyncio.gather(
        runtime.dispatch("tool:pin", ctx, effect, payment=payment),
        runtime.dispatch("tool:pin", ctx, effect, payment=payment),
        return_exceptions=True,
    )
    assert any(not isinstance(result, Exception) for result in results)
    assert effects <= 1
    assert calls["settle"] <= 1


@pytest.mark.asyncio
async def test_settled_crash_boundary_resumes_effect_without_resettlement(tmp_path):
    runtime, calls = build(tmp_path)
    ctx = context()
    required = await runtime.dispatch("tool:pin", ctx, lambda: None)
    entry = runtime.ledger.get(ctx.idempotency_key)
    runtime.ledger.bind_payment(ctx.idempotency_key, "committed-payment")
    runtime.ledger.mark_verified(ctx.idempotency_key, "verification")
    runtime.ledger.begin_settlement(ctx.idempotency_key, "lease")
    runtime.ledger.mark_settled(ctx.idempotency_key, "settlement")

    effects = 0

    def effect():
        nonlocal effects
        effects += 1
        return "recovered"

    result = await runtime.dispatch("tool:pin", ctx, effect)
    assert required.receipt_cid == entry.quote_cid
    assert result.value == "recovered"
    assert effects == 1
    assert calls["settle"] == 0
