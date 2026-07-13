"""Transport-neutral Profile H control plane shared by seller integrations."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from typing import Any

from .canonical import commitment
from .catalog import Decision, RequestContext
from .errors import ProfileHError
from .runtime import PaymentContext, SellerResult, SellerRuntime


PROFILE_H = "mcp++/x402-payments"
PROFILE_H_VERSION = "1.0"
PROFILE_H_METHODS = (
    "mcp++/payments/profile", "mcp++/payments/catalog", "mcp++/payments/quote",
    "mcp++/payments/verify", "mcp++/payments/settle", "mcp++/payments/receipt/get",
    "mcp++/payments/entitlement/get", "mcp++/payments/usage/get",
    "mcp++/payments/refund/request", "mcp++/payments/reconcile",
)


@dataclass(frozen=True, slots=True)
class CommercialBinding:
    """Service-normalized operation and request commitment."""

    operation: str
    context: RequestContext


class ProfileHControlPlane:
    """Complete HTTP/libp2p-neutral seller administration surface.

    The service owns operation scoping and domain evidence. This class owns the
    common quote/verification/settlement lifecycle and ensures that control
    methods cannot cross the protected-operation effect boundary.
    """

    def __init__(
        self,
        *,
        runtime: SellerRuntime,
        catalog: Callable[[], Mapping[str, Any]],
        bind: Callable[[str, RequestContext, Mapping[str, Any]], CommercialBinding],
        reconcile: Callable[[], Any],
        evidence: Callable[[str, str, RequestContext], Mapping[str, Any] | None] | None = None,
        transports: tuple[str, ...] = ("http", "libp2p"),
        mode: str = "facilitator",
        upstream_x402_http_conformance: bool = True,
    ) -> None:
        if set(transports) != {"http", "libp2p"}:
            raise ValueError("Profile H requires both HTTP and libp2p transports")
        if mode not in {"facilitator", "local-test"}:
            raise ValueError("Profile H mode must be facilitator or local-test")
        if mode == "local-test" and upstream_x402_http_conformance:
            raise ValueError("a local-test facilitator cannot claim upstream x402 settlement")
        self.runtime = runtime
        self._catalog = catalog
        self._bind = bind
        self._reconcile = reconcile
        self._evidence = evidence
        self.transports = transports
        self.mode = mode
        self.upstream_x402_http_conformance = upstream_x402_http_conformance

    async def profile(self) -> dict[str, Any]:
        diagnostics = await self.runtime.diagnostics()
        ledger = diagnostics.get("ledger", {})
        ready = bool(diagnostics.get("ready") and ledger.get("durable") is True)
        catalog = dict(self._catalog())
        return {
            "profile": PROFILE_H,
            "version": PROFILE_H_VERSION,
            "ready": ready,
            "sellerDid": self.runtime.seller_did,
            "descriptorCid": self.runtime.descriptor_cid,
            "catalogCid": str(catalog.get("signedCatalogCid") or catalog.get("catalogCid") or ""),
            "methods": list(PROFILE_H_METHODS),
            "transports": list(self.transports),
            "mode": self.mode,
            "upstreamX402HttpConformance": self.upstream_x402_http_conformance,
            "durability": {
                "ledger": "durable" if ledger.get("durable") else "ephemeral",
                "artifactStore": "content-addressed",
                "reconciliation": True,
            },
            "facilitator": diagnostics.get("facilitator"),
        }

    async def dispatch(self, method: str, params: Mapping[str, Any] | None = None) -> dict[str, Any]:
        values = dict(params or {})
        if method == "mcp++/payments/profile":
            return await self.profile()
        if method == "mcp++/payments/catalog":
            return dict(self._catalog())
        context = self._context(values)
        self._require_authorized(context)
        if method in {"mcp++/payments/quote", "mcp++/payments/verify", "mcp++/payments/settle"}:
            operation = str(values.get("operation") or values.get("operationName") or "")
            arguments = values.get("params", values.get("arguments", {}))
            if not operation or not isinstance(arguments, Mapping):
                raise ProfileHError("H_REQUEST_MISMATCH", "operation and structured params are required")
            binding = self._bind(operation, context, arguments)
            if method == "mcp++/payments/quote":
                return self._seller_result(await self.runtime.quote(binding.operation, binding.context))
            payment = self._payment(values, binding.context)
            if method == "mcp++/payments/verify":
                return self._seller_result(await self.runtime.verify_only(binding.operation, binding.context, payment))
            return self._seller_result(await self.runtime.settle_only(binding.operation, binding.context, payment))
        if method == "mcp++/payments/receipt/get":
            return self._receipt(self._cid(values, "receipt_cid"), context)
        if method in {"mcp++/payments/entitlement/get", "mcp++/payments/usage/get"}:
            kind = "entitlement" if method.endswith("entitlement/get") else "usage"
            cid = self._cid(values, f"{kind}_cid")
            item = self._evidence(kind, cid, context) if self._evidence else None
            if item is None:
                raise ProfileHError("H_EVIDENCE_NOT_FOUND", f"{kind} evidence was not found")
            return dict(item)
        if method == "mcp++/payments/refund/request":
            return self._request_refund(values, context)
        if method == "mcp++/payments/reconcile":
            outcome = self._reconcile()
            if hasattr(outcome, "__await__"):
                outcome = await outcome
            return {"status": "reconciled", "outcomes": outcome}
        raise ProfileHError("H_METHOD_NOT_SUPPORTED", f"unsupported Profile H method: {method}")

    async def handle_http(
        self, method: str, path: str, params: Mapping[str, Any] | None = None,
    ) -> tuple[int, dict[str, str], dict[str, Any]]:
        """Apply the canonical REST bindings without changing decoded objects."""
        verb, values = method.upper(), dict(params or {})
        static = {
            ("GET", "/mcp/payments/profile"): "mcp++/payments/profile",
            ("GET", "/mcp/payments/catalog"): "mcp++/payments/catalog",
            ("POST", "/mcp/payments/quote"): "mcp++/payments/quote",
            ("POST", "/mcp/payments/verify"): "mcp++/payments/verify",
            ("POST", "/mcp/payments/settle"): "mcp++/payments/settle",
            ("POST", "/mcp/payments/refunds"): "mcp++/payments/refund/request",
            ("POST", "/mcp/payments/reconcile"): "mcp++/payments/reconcile",
        }
        rpc_method = static.get((verb, path))
        for prefix, candidate, field in (
            ("/mcp/payments/receipts/", "mcp++/payments/receipt/get", "receipt_cid"),
            ("/mcp/payments/entitlements/", "mcp++/payments/entitlement/get", "entitlement_cid"),
            ("/mcp/payments/usage/", "mcp++/payments/usage/get", "usage_cid"),
        ):
            if verb == "GET" and path.startswith(prefix) and path.removeprefix(prefix):
                rpc_method, values[field] = candidate, path.removeprefix(prefix)
                break
        if rpc_method is None:
            return 404, {"content-type": "application/json"}, {
                "error": "H_METHOD_NOT_SUPPORTED", "message": "unknown Profile H route",
            }
        try:
            result = await self.dispatch(rpc_method, values)
            headers = {"content-type": "application/json"}
            if rpc_method == "mcp++/payments/catalog" and result.get("signedCatalogCid"):
                headers["etag"] = str(result["signedCatalogCid"])
            return 200, headers, result
        except ProfileHError as error:
            status = 403 if error.code == "H_PAYMENT_POLICY_DENIED" else (
                404 if error.code == "H_EVIDENCE_NOT_FOUND" else
                409 if error.code in {"H_REQUEST_MISMATCH", "H_PAYMENT_REPLAY", "H_RECONCILIATION_REQUIRED"} else 400
            )
            return status, {"content-type": "application/json"}, {
                "error": error.code, "message": str(error), "retryable": error.retryable,
            }

    @staticmethod
    def _context(values: Mapping[str, Any]) -> RequestContext:
        raw = values.get("requestContext", values.get("request_context", {}))
        raw = raw if isinstance(raw, Mapping) else {}
        request_cid = str(raw.get("requestCid", raw.get("request_cid", values.get("requestCid", values.get("request_cid", "")))))
        key = str(raw.get("idempotencyKey", raw.get("idempotency_key", values.get("idempotencyKey", values.get("idempotency_key", "")))))
        attributes = raw.get("attributes", values.get("attributes", {}))
        if isinstance(attributes, str):
            try:
                attributes = json.loads(attributes)
            except json.JSONDecodeError as error:
                raise ProfileHError("H_REQUEST_MISMATCH", "attributes must be a JSON object") from error
        if not request_cid or not key or not isinstance(attributes, Mapping):
            raise ProfileHError("H_REQUEST_MISMATCH", "requestCid, idempotencyKey, and attributes are required")
        return RequestContext(
            request_cid, key,
            ProfileHControlPlane._boolean(raw.get("authorized", values.get("authorized", True)), "authorized"),
            ProfileHControlPlane._boolean(
                raw.get("policyAllowed", raw.get("policy_allowed", values.get("policyAllowed", True))),
                "policyAllowed",
            ),
            str(raw.get("entitlementCid")) if raw.get("entitlementCid") else None,
            dict(attributes),
        )

    @staticmethod
    def _boolean(value: Any, field: str) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, str) and value.lower() in {"true", "false"}:
            return value.lower() == "true"
        raise ProfileHError("H_REQUEST_MISMATCH", f"{field} must be a boolean")

    @staticmethod
    def _payment(values: Mapping[str, Any], context: RequestContext) -> PaymentContext:
        raw = values.get("payment_context", values.get("paymentContext", values.get("payment", {})))
        if not isinstance(raw, Mapping):
            raise ProfileHError("H_INVALID_PAYMENT_MESSAGE", "payment context must be an object")
        payload = raw.get("payload", raw.get("paymentPayload"))
        if not isinstance(payload, Mapping):
            raise ProfileHError("H_INVALID_PAYMENT_MESSAGE", "payment payload is required")
        return PaymentContext(
            payload,
            str(raw.get("quoteCid", raw.get("quote_cid", ""))),
            str(raw.get("requestCid", raw.get("request_cid", context.request_cid))),
            int(raw.get("requirementIndex", raw.get("requirement_index", 0))),
        )

    @staticmethod
    def _seller_result(result: SellerResult) -> dict[str, Any]:
        return {key: value for key, value in {
            "decision": result.decision.decision.value,
            "reasonCode": result.decision.reason_code,
            "quote": result.quote,
            "paymentRequired": result.payment_required,
            "paymentResponse": result.settlement_response,
            "receiptCid": result.receipt_cid,
            "replayed": result.replayed,
            "result": result.value,
        }.items() if value is not None}

    def _receipt(self, cid: str, context: RequestContext) -> dict[str, Any]:
        entry = self.runtime.ledger.get_by_artifact(cid)
        if entry is None or entry.request_cid != context.request_cid:
            raise ProfileHError("H_EVIDENCE_NOT_FOUND", "receipt was not found for this request")
        artifact = self.runtime.artifacts.get(cid)
        if artifact is None:
            raise ProfileHError("H_RECONCILIATION_REQUIRED", "receipt index exists but artifact is missing", retryable=True)
        return {"receiptCid": cid, "state": entry.state, "artifact": artifact}

    def _request_refund(self, values: Mapping[str, Any], context: RequestContext) -> dict[str, Any]:
        settlement_cid = self._cid(values, "settlement_cid")
        entry = self.runtime.ledger.get_by_artifact(settlement_cid)
        if entry is None or entry.request_cid != context.request_cid or entry.settlement_cid != settlement_cid:
            raise ProfileHError("H_EVIDENCE_NOT_FOUND", "settlement is not available to this request")
        artifact = {
            "schema": "mcp++/profile-h/refund-request@1.0",
            "createdAt": self.runtime.clock_ms(),
            "parents": [settlement_cid],
            "settlementCid": settlement_cid,
            "requestCid": context.request_cid,
            "subjectCommitment": commitment(context.attributes.get("subject", "anonymous")),
            "reasonCode": str(values.get("reasonCode", values.get("reason_code", "H_REFUND_REQUESTED")))[:64],
            "status": "pending",
        }
        refund_cid = self.runtime.artifacts.put(artifact)
        return {"refundRequestCid": refund_cid, "status": "pending", "artifact": artifact}

    @staticmethod
    def _cid(values: Mapping[str, Any], key: str) -> str:
        camel = key.split("_")[0] + "".join(part.title() for part in key.split("_")[1:])
        value = values.get(key, values.get(camel, values.get("cid", "")))
        if not isinstance(value, str) or not value:
            raise ProfileHError("H_REQUEST_MISMATCH", f"{key} is required")
        return value

    @staticmethod
    def _require_authorized(context: RequestContext) -> None:
        if not context.authorized or not context.policy_allowed:
            raise ProfileHError("H_PAYMENT_POLICY_DENIED", "Profile C/D disclosure policy denied")


__all__ = [
    "CommercialBinding", "PROFILE_H", "PROFILE_H_METHODS", "PROFILE_H_VERSION",
    "ProfileHControlPlane",
]
