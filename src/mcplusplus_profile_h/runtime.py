"""Transport-neutral Profile H seller orchestration and effect guard."""

from __future__ import annotations

import asyncio
import base64
import inspect
import secrets
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .adapters import SettlementResult, VerifierFacilitator
from .artifacts import ArtifactStore
from .canonical import canonical_json, commitment
from .catalog import (
    Decision,
    Operation,
    PaymentDecision,
    PaymentPolicyEngine,
    PaymentRequirement,
    RequestContext,
)
from .errors import (
    PAYMENT_DECLINED,
    PAYMENT_REQUIRED,
    QUOTE_EXPIRED,
    REQUEST_MISMATCH,
    SETTLEMENT_FAILED,
    VERIFICATION_FAILED,
    ProfileHError,
)
from .ledger import DuckDBPaymentLedger, LedgerEntry
from .operations import KillSwitches, RedactedMetrics, facilitator_health_probe


@dataclass(frozen=True, slots=True)
class PaymentContext:
    """Private, request-scoped payment input. Never persisted verbatim."""

    payload: Mapping[str, Any]
    quote_cid: str
    request_cid: str
    requirement_index: int = 0


@dataclass(frozen=True, slots=True)
class SellerResult:
    decision: PaymentDecision
    value: Any = None
    quote: Mapping[str, Any] | None = None
    payment_required: Mapping[str, Any] | None = None
    settlement_response: Mapping[str, Any] | None = None
    receipt_cid: str | None = None
    replayed: bool = False


class SellerRuntime:
    """Verify/settle and fence execution immediately before side effects."""

    def __init__(
        self,
        policy: PaymentPolicyEngine,
        ledger: DuckDBPaymentLedger,
        facilitator: VerifierFacilitator,
        artifacts: ArtifactStore,
        *,
        seller_did: str,
        descriptor_cid: str,
        quote_lifetime_ms: int = 60_000,
        clock_ms: Callable[[], int] | None = None,
        metrics: RedactedMetrics | None = None,
        kill_switches: KillSwitches | None = None,
        seller_name: str | None = None,
    ) -> None:
        if not 1_000 <= quote_lifetime_ms <= 300_000:
            raise ValueError("quote_lifetime_ms must be in [1000, 300000]")
        self.policy = policy
        self.ledger = ledger
        self.facilitator = facilitator
        self.artifacts = artifacts
        self.seller_did = seller_did
        self.descriptor_cid = descriptor_cid
        self.quote_lifetime_ms = quote_lifetime_ms
        self.clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self.metrics = metrics
        self.kill_switches = kill_switches
        self.seller_name = seller_name or seller_did.removeprefix("did:web:").split(".", 1)[0]
        # Let policy decisions discover settled entries without transport state.
        if self.policy.paid_lookup is None:
            self.policy.paid_lookup = lambda context, capability: self.ledger.paid_evidence(
                context.request_cid, capability.capability_cid or ""
            )

    async def dispatch(
        self,
        operation: Operation | str,
        context: RequestContext,
        effect: Callable[[], Any | Awaitable[Any]],
        *,
        payment: PaymentContext | None = None,
    ) -> SellerResult:
        """Guard an effect; the callback is invoked only after durable settlement."""
        decision = self.policy.evaluate(operation, context)
        if decision.decision in (Decision.DENIED, Decision.UNAVAILABLE):
            self._observe("access", "denied", decision.reason_code)
            return SellerResult(decision)
        if decision.decision == Decision.FREE:
            value = await self._call(effect)
            return SellerResult(decision, value=value)
        capability = decision.capability
        assert capability is not None and capability.capability_cid is not None

        if self.kill_switches is not None and not self.kill_switches.allows_new_work(self.seller_name):
            self._observe("access", "paused", "H_OPERATOR_PAUSE")
            paused = PaymentDecision(Decision.UNAVAILABLE, decision.operation, "H_FACILITATOR_UNAVAILABLE", capability)
            return SellerResult(paused)

        existing = self.ledger.get(context.idempotency_key)
        if existing and existing.request_cid != context.request_cid:
            raise ProfileHError(REQUEST_MISMATCH, "idempotency key is bound to another request")
        if existing and existing.state == "executed":
            paid = PaymentDecision(Decision.PAID, decision.operation, "H_PAYMENT_SATISFIED", capability, evidence_cid=existing.settlement_cid)
            return SellerResult(paid, receipt_cid=existing.result_cid, replayed=True)
        if existing and existing.state == "settled":
            paid = PaymentDecision(Decision.PAID, decision.operation, "H_PAYMENT_SATISFIED", capability, evidence_cid=existing.settlement_cid)
            return await self._execute_settled(paid, context, effect, existing.settlement_cid or commitment({}))
        if decision.decision == Decision.PAID and existing is None:
            # Reusable/domain entitlements are already validated by paid_lookup.
            # The domain entitlement store owns quota consumption fencing.
            value = await self._call(effect)
            return SellerResult(decision, value=value, receipt_cid=decision.evidence_cid)

        if payment is None and existing and existing.state == "quoted" and existing.quote_cid:
            # An unpaid retry must return the originally fenced quote. Issuing a
            # fresh nonce while retaining the old ledger binding makes neither
            # quote payable and is observable as a false request mismatch.
            quote = self.artifacts.get(existing.quote_cid)
            if quote is None:
                raise ProfileHError("H_RECONCILIATION_REQUIRED", "fenced quote artifact is missing", retryable=True)
            required = {
                "x402Version": 2,
                "error": PAYMENT_REQUIRED,
                "accepts": [item.wire() for item in decision.requirements],
                "extensions": {"mcp++/profile-h": {"quoteCid": existing.quote_cid, "requestCid": context.request_cid}},
            }
            return SellerResult(decision, quote=quote, payment_required=required, receipt_cid=existing.quote_cid, replayed=True)

        if payment is None:
            quote, quote_cid = self._issue_quote(decision, context)
            self.ledger.create_quote(
                context.idempotency_key,
                context.request_cid,
                decision.operation.key,
                capability.capability_cid,
                quote_cid,
            )
            required = {
                "x402Version": 2,
                "error": PAYMENT_REQUIRED,
                "accepts": [item.wire() for item in decision.requirements],
                "extensions": {"mcp++/profile-h": {"quoteCid": quote_cid, "requestCid": context.request_cid}},
            }
            self._observe("quote", "success")
            return SellerResult(decision, quote=quote, payment_required=required, receipt_cid=quote_cid)

        self._validate_payment_context(existing, context, payment, len(capability.requirements))
        requirement = capability.requirements[payment.requirement_index]
        self._validate_selected_requirement(payment.payload, requirement)
        payment_commitment = commitment(payment.payload)
        self.ledger.bind_payment(context.idempotency_key, payment_commitment)

        current = self.ledger.get(context.idempotency_key)
        assert current is not None
        if current.state == "quoted":
            started = time.monotonic_ns()
            verification = await self.facilitator.verify(payment.payload, requirement)
            if not verification.valid:
                self._observe("verify", "failure", verification.reason_code or VERIFICATION_FAILED, started)
                self.ledger.mark_failed(context.idempotency_key, verification.reason_code or VERIFICATION_FAILED)
                raise ProfileHError(PAYMENT_DECLINED, "payment verification declined")
            self._observe("verify", "success", "H_PAYMENT_VERIFIED", started)
            verification_artifact = {
                "schema": "mcp++/profile-h/payment-verification@1.0",
                "authorizationCid": payment_commitment,
                "verifierDid": verification.verifier_did,
                "decision": "verified",
                "reasonCode": verification.reason_code or "H_PAYMENT_VERIFIED",
                "verifiedAt": self.clock_ms(),
                "evidenceCid": commitment(dict(verification.evidence)),
            }
            verification_cid = self.artifacts.put(verification_artifact)
            current = self.ledger.mark_verified(context.idempotency_key, verification_cid)
        elif current.state != "verified":
            raise ProfileHError(
                "H_RECONCILIATION_REQUIRED",
                f"payment is fenced in state {current.state}",
                retryable=True,
            )
        verification_cid = current.verification_cid
        assert verification_cid is not None

        # Re-check non-payment authorization after verification and before the
        # irreversible settlement call. Payment never substitutes for policy.
        post_verification = self.policy.evaluate(operation, context)
        if post_verification.decision in (Decision.DENIED, Decision.UNAVAILABLE):
            self.ledger.mark_failed(context.idempotency_key, post_verification.reason_code)
            return SellerResult(post_verification)

        settlement_lease = secrets.token_urlsafe(24)
        self.ledger.begin_settlement(context.idempotency_key, settlement_lease)
        settlement_started = time.monotonic_ns()
        try:
            settlement = await self.facilitator.settle(payment.payload, requirement)
        except Exception:
            # Outcome is unknown after an I/O failure; reconciliation must query
            # by the non-secret payment commitment before any retry settles.
            self.ledger.mark_failed(context.idempotency_key, "H_RECONCILIATION_REQUIRED", reconciliation=True)
            self._observe("settlement", "failure", "H_RECONCILIATION_REQUIRED", settlement_started)
            raise
        if not settlement.success:
            self._observe("settlement", "failure", settlement.reason_code or SETTLEMENT_FAILED, settlement_started)
            self.ledger.mark_failed(context.idempotency_key, settlement.reason_code or SETTLEMENT_FAILED)
            raise ProfileHError(SETTLEMENT_FAILED, "payment settlement failed", retryable=True)
        self._observe("settlement", "success", "H_PAYMENT_SETTLED", settlement_started)
        settlement_cid = self._persist_settlement(verification_cid, requirement, settlement)
        self.ledger.mark_settled(context.idempotency_key, settlement_cid)
        paid = PaymentDecision(Decision.PAID, decision.operation, "H_PAYMENT_SATISFIED", capability, evidence_cid=settlement_cid)
        return await self._execute_settled(paid, context, effect, settlement_cid, settlement)

    def dispatch_sync(self, *args: Any, **kwargs: Any) -> SellerResult:
        """Synchronous convenience hook for WSGI/plain MCP dispatchers."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.dispatch(*args, **kwargs))
        raise RuntimeError("dispatch_sync cannot run inside an event loop; await dispatch instead")

    async def quote(self, operation: Operation | str, context: RequestContext) -> SellerResult:
        """Issue or recover a request-bound quote without invoking an effect."""
        decision = self.policy.evaluate(operation, context)
        if decision.decision in (Decision.DENIED, Decision.UNAVAILABLE, Decision.FREE, Decision.PAID):
            return SellerResult(decision, receipt_cid=decision.evidence_cid)
        capability = decision.capability
        assert capability is not None and capability.capability_cid is not None
        existing = self.ledger.get(context.idempotency_key)
        if existing and existing.request_cid != context.request_cid:
            raise ProfileHError(REQUEST_MISMATCH, "idempotency key is bound to another request")
        if existing:
            if not existing.quote_cid:
                raise ProfileHError("H_RECONCILIATION_REQUIRED", "payment record has no quote", retryable=True)
            quote = self.artifacts.get(existing.quote_cid)
            if quote is None:
                raise ProfileHError("H_RECONCILIATION_REQUIRED", "fenced quote artifact is missing", retryable=True)
            required = self._payment_required(decision, context, existing.quote_cid)
            return SellerResult(decision, quote=quote, payment_required=required,
                                receipt_cid=existing.quote_cid, replayed=True)
        quote, quote_cid = self._issue_quote(decision, context)
        self.ledger.create_quote(context.idempotency_key, context.request_cid,
                                 decision.operation.key, capability.capability_cid, quote_cid)
        self._observe("quote", "success")
        return SellerResult(decision, quote=quote,
                            payment_required=self._payment_required(decision, context, quote_cid),
                            receipt_cid=quote_cid)

    async def verify_only(
        self, operation: Operation | str, context: RequestContext, payment: PaymentContext,
    ) -> SellerResult:
        """Durably verify a payment. This method never settles or executes."""
        decision = self.policy.evaluate(operation, context)
        if decision.decision in (Decision.DENIED, Decision.UNAVAILABLE):
            return SellerResult(decision)
        capability = decision.capability
        if capability is None or capability.capability_cid is None:
            return SellerResult(decision)
        entry = self._validate_payment_context(
            self.ledger.get(context.idempotency_key), context, payment, len(capability.requirements),
        )
        requirement = capability.requirements[payment.requirement_index]
        self._validate_selected_requirement(payment.payload, requirement)
        payment_commitment = commitment(payment.payload)
        if entry.payment_commitment and entry.payment_commitment != payment_commitment:
            raise ProfileHError("H_PAYMENT_REPLAY", "different payment already bound to request")
        if not entry.payment_commitment:
            entry = self.ledger.bind_payment(context.idempotency_key, payment_commitment)
        if entry.state in {"verified", "settling", "settled", "executing", "executed"}:
            paid = PaymentDecision(Decision.PAID, decision.operation, "H_PAYMENT_VERIFIED", capability,
                                   evidence_cid=entry.verification_cid)
            return SellerResult(paid, receipt_cid=entry.verification_cid, replayed=True)
        if entry.state != "quoted":
            raise ProfileHError("H_RECONCILIATION_REQUIRED", f"payment is fenced in state {entry.state}", retryable=True)
        started = time.monotonic_ns()
        verification = await self.facilitator.verify(payment.payload, requirement)
        if not verification.valid:
            self._observe("verify", "failure", verification.reason_code or VERIFICATION_FAILED, started)
            self.ledger.mark_failed(context.idempotency_key, verification.reason_code or VERIFICATION_FAILED)
            raise ProfileHError(PAYMENT_DECLINED, "payment verification declined")
        artifact = {
            "schema": "mcp++/profile-h/payment-verification@1.0",
            "authorizationCid": payment_commitment,
            "verifierDid": verification.verifier_did,
            "decision": "verified",
            "reasonCode": verification.reason_code or "H_PAYMENT_VERIFIED",
            "verifiedAt": self.clock_ms(),
            "evidenceCid": commitment(dict(verification.evidence)),
        }
        verification_cid = self.artifacts.put(artifact)
        self.ledger.mark_verified(context.idempotency_key, verification_cid)
        self._observe("verify", "success", "H_PAYMENT_VERIFIED", started)
        verified = PaymentDecision(Decision.PAID, decision.operation, "H_PAYMENT_VERIFIED", capability,
                                   evidence_cid=verification_cid)
        return SellerResult(verified, value=artifact, receipt_cid=verification_cid)

    async def settle_only(
        self, operation: Operation | str, context: RequestContext, payment: PaymentContext,
    ) -> SellerResult:
        """Durably settle a verified payment without reserving or executing work."""
        verified = await self.verify_only(operation, context, payment)
        if verified.decision.decision != Decision.PAID:
            return verified
        decision = self.policy.evaluate(operation, context)
        if decision.decision in (Decision.DENIED, Decision.UNAVAILABLE):
            self.ledger.mark_failed(context.idempotency_key, decision.reason_code)
            return SellerResult(decision)
        capability = decision.capability
        assert capability is not None
        entry = self.ledger.get(context.idempotency_key)
        assert entry is not None
        if entry.state in {"settled", "executing", "executed"} and entry.settlement_cid:
            paid = PaymentDecision(Decision.PAID, decision.operation, "H_PAYMENT_SATISFIED", capability,
                                   evidence_cid=entry.settlement_cid)
            return SellerResult(paid, value=self.artifacts.get(entry.settlement_cid),
                                receipt_cid=entry.settlement_cid, replayed=True)
        if entry.state != "verified":
            raise ProfileHError("H_RECONCILIATION_REQUIRED", f"payment is fenced in state {entry.state}", retryable=True)
        requirement = capability.requirements[payment.requirement_index]
        lease = secrets.token_urlsafe(24)
        self.ledger.begin_settlement(context.idempotency_key, lease)
        started = time.monotonic_ns()
        try:
            settlement = await self.facilitator.settle(payment.payload, requirement)
        except Exception:
            self.ledger.mark_failed(context.idempotency_key, "H_RECONCILIATION_REQUIRED", reconciliation=True)
            self._observe("settlement", "failure", "H_RECONCILIATION_REQUIRED", started)
            raise
        if not settlement.success:
            self.ledger.mark_failed(context.idempotency_key, settlement.reason_code or SETTLEMENT_FAILED)
            self._observe("settlement", "failure", settlement.reason_code or SETTLEMENT_FAILED, started)
            raise ProfileHError(SETTLEMENT_FAILED, "payment settlement failed", retryable=True)
        settlement_cid = self._persist_settlement(entry.verification_cid or commitment({}), requirement, settlement)
        self.ledger.mark_settled(context.idempotency_key, settlement_cid)
        self._observe("settlement", "success", "H_PAYMENT_SETTLED", started)
        paid = PaymentDecision(Decision.PAID, decision.operation, "H_PAYMENT_SATISFIED", capability,
                               evidence_cid=settlement_cid)
        return SellerResult(paid, value=self.artifacts.get(settlement_cid),
                            settlement_response=dict(settlement.response), receipt_cid=settlement_cid)

    async def reconcile(self, *, stale_before_ms: int | None = None) -> list[dict[str, Any]]:
        """Reconcile uncertain settlement boundaries without re-settling."""
        outcomes: list[dict[str, Any]] = []
        for entry in self.ledger.pending_reconciliation(stale_before_ms=stale_before_ms):
            if entry.state == "executing":
                # Whether the domain effect happened is unknowable here. Keep it
                # fenced for operator/domain-specific idempotency reconciliation.
                if entry.state != "reconciliation_required":
                    self.ledger.mark_failed(entry.idempotency_key, "H_RECONCILIATION_REQUIRED", reconciliation=True)
                outcomes.append({"idempotencyKey": entry.idempotency_key, "state": "reconciliation_required"})
                continue
            if entry.state in {"settled", "verified"}:
                outcomes.append({"idempotencyKey": entry.idempotency_key, "state": entry.state})
                continue
            if not entry.payment_commitment:
                self.ledger.reset_for_reconciliation(entry.idempotency_key, "failed")
                outcomes.append({"idempotencyKey": entry.idempotency_key, "state": "failed"})
                continue
            status = await self.facilitator.lookup(entry.payment_commitment)
            if status and status.success:
                requirement = self._requirement_for(entry)
                cid = self._persist_settlement(entry.verification_cid or commitment({}), requirement, status)
                self.ledger.reset_for_reconciliation(entry.idempotency_key, "settled", cid)
                outcomes.append({"idempotencyKey": entry.idempotency_key, "state": "settled", "settlementCid": cid})
            elif status is not None:
                self.ledger.reset_for_reconciliation(entry.idempotency_key, "failed")
                outcomes.append({"idempotencyKey": entry.idempotency_key, "state": "failed"})
            else:
                outcomes.append({"idempotencyKey": entry.idempotency_key, "state": "reconciliation_required"})
        return outcomes

    async def diagnostics(self) -> dict[str, Any]:
        facilitator = await facilitator_health_probe(self.facilitator)
        ledger = self.ledger.health_probe()
        return {
            "ready": bool(facilitator["ready"] and ledger["ready"]),
            "sellerDid": self.seller_did,
            "descriptorCid": self.descriptor_cid,
            "catalogCid": self.policy.catalog.cid,
            "facilitator": facilitator,
            "ledger": ledger,
            "emergencyPause": self.policy.emergency_pause,
            "killSwitches": self.kill_switches.status() if self.kill_switches else None,
        }

    def _issue_quote(self, decision: PaymentDecision, context: RequestContext) -> tuple[dict[str, Any], str]:
        capability = decision.capability
        assert capability is not None
        now = self.clock_ms()
        quote = {
            "schema": "mcp++/profile-h/payment-quote@1.0",
            "capabilityCid": capability.capability_cid,
            "catalogCid": self.policy.catalog.cid,
            "descriptorCid": self.descriptor_cid,
            "requestCid": context.request_cid,
            "requirements": [item.wire() for item in decision.requirements],
            "nonce": secrets.token_urlsafe(24),
            "createdAt": now,
            "expiresAt": now + self.quote_lifetime_ms,
            "idempotencyKey": context.idempotency_key,
            "sellerDid": self.seller_did,
        }
        return quote, self.artifacts.put(quote)

    @staticmethod
    def _payment_required(decision: PaymentDecision, context: RequestContext, quote_cid: str) -> dict[str, Any]:
        return {
            "x402Version": 2,
            "error": PAYMENT_REQUIRED,
            "accepts": [item.wire() for item in decision.requirements],
            "extensions": {"mcp++/profile-h": {"quoteCid": quote_cid, "requestCid": context.request_cid}},
        }

    def _validate_payment_context(self, entry: LedgerEntry | None, context: RequestContext, payment: PaymentContext, count: int) -> LedgerEntry:
        if entry is None:
            raise ProfileHError(PAYMENT_REQUIRED, "a server-issued quote is required")
        if payment.quote_cid != entry.quote_cid or payment.request_cid != context.request_cid:
            raise ProfileHError(REQUEST_MISMATCH, "payment does not match quote and request")
        if not 0 <= payment.requirement_index < count:
            raise ProfileHError(REQUEST_MISMATCH, "payment requirement selection is invalid")
        quote = self.artifacts.get(payment.quote_cid)
        if quote is None or quote.get("requestCid") != context.request_cid:
            raise ProfileHError(REQUEST_MISMATCH, "quote is missing or request-bound differently")
        if entry.state == "quoted" and self.clock_ms() >= int(quote["expiresAt"]):
            raise ProfileHError(QUOTE_EXPIRED, "payment quote expired")
        return entry

    @staticmethod
    def _validate_selected_requirement(payload: Mapping[str, Any], expected: PaymentRequirement) -> None:
        if payload.get("x402Version") != 2:
            raise ProfileHError(VERIFICATION_FAILED, "only x402 v2 payment payloads are accepted")
        accepted = payload.get("accepted")
        if not isinstance(accepted, Mapping) or dict(accepted) != expected.wire():
            raise ProfileHError(REQUEST_MISMATCH, "selected payment requirement was substituted")
        if not isinstance(payload.get("payload"), Mapping):
            raise ProfileHError(VERIFICATION_FAILED, "signed payment payload is missing")

    def _persist_settlement(self, verification_cid: str, requirement: PaymentRequirement, result: SettlementResult) -> str:
        artifact = {
            "schema": "mcp++/profile-h/settlement-receipt@1.0",
            "verificationCid": verification_cid,
            "outcome": "settled" if result.success else "failed",
            "amount": requirement.amount,
            "network": requirement.network,
            "networkReferenceCommitment": commitment(result.transaction or "undisclosed"),
            "disclosurePolicy": "commitment-only",
            "paymentResponseCid": commitment(self._settlement_response(result)),
            "settledAt": self.clock_ms(),
        }
        return self.artifacts.put(artifact)

    async def _execute_settled(
        self,
        decision: PaymentDecision,
        context: RequestContext,
        effect: Callable[[], Any | Awaitable[Any]],
        settlement_cid: str,
        settlement: SettlementResult | None = None,
    ) -> SellerResult:
        final_policy = self.policy.evaluate(decision.operation, context)
        if final_policy.decision in (Decision.DENIED, Decision.UNAVAILABLE):
            return SellerResult(final_policy)
        execution_lease = secrets.token_urlsafe(24)
        self.ledger.claim_execution(context.idempotency_key, execution_lease)
        execution_started = time.monotonic_ns()
        try:
            # This call is deliberately adjacent to claim_execution: no payment
            # or policy work can drift below the final effect boundary.
            value = await self._call(effect)
        except Exception:
            self.ledger.mark_failed(context.idempotency_key, "H_RECONCILIATION_REQUIRED", reconciliation=True)
            self._observe("execution", "failure", "H_RECONCILIATION_REQUIRED", execution_started)
            raise
        access = {
            "schema": "mcp++/profile-h/access-receipt@1.0",
            "operationName": decision.operation.name,
            "requestCid": context.request_cid,
            "commercialEvidenceCid": settlement_cid,
            "decision": "allow",
            "resultCid": commitment(value),
            "reasonCode": "H_PAYMENT_SATISFIED",
            "decidedAt": self.clock_ms(),
        }
        access_cid = self.artifacts.put(access)
        self.ledger.mark_executed(context.idempotency_key, access_cid)
        self._observe("execution", "success", "H_PAYMENT_SATISFIED", execution_started)
        response = self._settlement_response(settlement) if settlement else None
        return SellerResult(decision, value=value, settlement_response=response, receipt_cid=access_cid)

    @staticmethod
    def _settlement_response(result: SettlementResult) -> dict[str, Any]:
        response: dict[str, Any] = {"success": result.success, "network": result.network}
        if result.transaction:
            response["transaction"] = result.transaction
        if result.reason_code and not result.success:
            response["errorReason"] = result.reason_code
        return response

    def _requirement_for(self, entry: LedgerEntry) -> PaymentRequirement:
        capability = self.policy.catalog.resolve(entry.operation_key)
        if capability is None or not capability.requirements:
            raise KeyError(entry.operation_key)
        return capability.requirements[0]

    @staticmethod
    async def _call(callback: Callable[[], Any | Awaitable[Any]]) -> Any:
        value = callback()
        return await value if inspect.isawaitable(value) else value

    def _observe(self, stage: str, outcome: str, reason_code: str = "H_NONE", started_ns: int | None = None) -> None:
        if self.metrics is not None:
            duration = 0 if started_ns is None else max(0, (time.monotonic_ns() - started_ns) // 1_000_000)
            public_code = reason_code if reason_code.startswith("H_") and reason_code.replace("_", "").isalnum() else "H_OTHER"
            self.metrics.observe(stage, outcome, self.seller_name, duration_ms=duration, reason_code=public_code[:63])


def encode_x402_header(value: Mapping[str, Any]) -> str:
    return base64.b64encode(canonical_json(dict(value))).decode("ascii")


def http_response(result: SellerResult) -> tuple[int, dict[str, str], Any]:
    """Map a transport-neutral result to normative x402 v2 HTTP fields."""
    if result.decision.decision == Decision.PAYMENT_REQUIRED:
        assert result.payment_required is not None
        return 402, {"PAYMENT-REQUIRED": encode_x402_header(result.payment_required)}, {
            "error": result.decision.reason_code,
            "quote": result.quote,
        }
    if result.decision.decision in (Decision.DENIED, Decision.UNAVAILABLE):
        status = 403 if result.decision.decision == Decision.DENIED else 503
        return status, {}, {"error": result.decision.reason_code}
    headers = {}
    if result.settlement_response:
        headers["PAYMENT-RESPONSE"] = encode_x402_header(result.settlement_response)
    return 200, headers, result.value


def libp2p_response(result: SellerResult) -> dict[str, Any]:
    """Map a result to Profile E's typed (non-upstream) payment envelope."""
    if result.decision.decision == Decision.PAYMENT_REQUIRED:
        return {"error": {"code": PAYMENT_REQUIRED, "payment_required": result.payment_required, "quote": result.quote}}
    if result.decision.decision in (Decision.DENIED, Decision.UNAVAILABLE):
        return {"error": {"code": result.decision.reason_code}}
    return {"result": result.value, "payment_response": result.settlement_response, "receipt_cid": result.receipt_cid}
