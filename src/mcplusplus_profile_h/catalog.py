"""Immutable paid-capability catalog and deterministic policy decisions."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Any

from .canonical import cid_for


class Decision(StrEnum):
    FREE = "free"
    PAYMENT_REQUIRED = "payment_required"
    PAID = "paid"
    DENIED = "denied"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True)
class Operation:
    kind: str
    name: str
    http_method: str | None = None
    http_route: str | None = None

    @property
    def key(self) -> str:
        if self.kind == "http":
            return f"http:{(self.http_method or '').upper()}:{self.http_route or self.name}"
        return f"{self.kind}:{self.name}"

    @classmethod
    def parse(cls, value: Operation | str) -> Operation:
        if isinstance(value, cls):
            return value
        parts = value.split(":", 2)
        if len(parts) == 3 and parts[0] == "http":
            return cls("http", parts[2], parts[1].upper(), parts[2])
        if len(parts) == 2:
            return cls(parts[0], parts[1])
        return cls("tool", value)


@dataclass(frozen=True, slots=True)
class PaymentRequirement:
    scheme: str
    network: str
    asset: str
    amount: str
    pay_to: str
    max_timeout_seconds: int = 60
    extra: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.amount.isdigit() or (len(self.amount) > 1 and self.amount.startswith("0")):
            raise ValueError("amount must be a canonical atomic-unit integer string")
        if int(self.amount) < 0 or not self.scheme or ":" not in self.network:
            raise ValueError("invalid payment requirement")
        if not 1 <= self.max_timeout_seconds <= 3600:
            raise ValueError("max_timeout_seconds is out of range")
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def wire(self) -> dict[str, Any]:
        return {
            "scheme": self.scheme,
            "network": self.network,
            "asset": self.asset,
            "amount": self.amount,
            "payTo": self.pay_to,
            "maxTimeoutSeconds": self.max_timeout_seconds,
            "extra": dict(self.extra),
        }


@dataclass(frozen=True, slots=True)
class PaidCapability:
    operation: Operation | str
    requirements: tuple[PaymentRequirement, ...] = ()
    free: bool = False
    enabled: bool = True
    capability_cid: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        operation = Operation.parse(self.operation)
        object.__setattr__(self, "operation", operation)
        object.__setattr__(self, "requirements", tuple(self.requirements))
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        if self.free and self.requirements:
            raise ValueError("a free capability cannot have payment requirements")
        if not self.free and self.enabled and not self.requirements:
            raise ValueError("a paid capability needs at least one requirement")
        if self.capability_cid is None:
            public = {
                "operation": operation.key,
                "requirements": [item.wire() for item in self.requirements],
                "free": self.free,
                "enabled": self.enabled,
                "metadata": dict(self.metadata),
            }
            object.__setattr__(self, "capability_cid", cid_for(public))


class CapabilityCatalog:
    """A versioned snapshot. Duplicate operation identities are rejected."""

    def __init__(self, capabilities: tuple[PaidCapability, ...] | list[PaidCapability], *, version: str = "1") -> None:
        ordered = sorted(capabilities, key=lambda item: item.operation.key)
        by_key = {item.operation.key: item for item in ordered}
        if len(by_key) != len(ordered):
            raise ValueError("duplicate operation in payment catalog")
        self.version = version
        self._items = tuple(ordered)
        self._by_key = MappingProxyType(by_key)
        self.cid = cid_for({"version": version, "capabilities": [self._public(item) for item in ordered]})

    @staticmethod
    def _public(item: PaidCapability) -> dict[str, Any]:
        return {
            "operation": item.operation.key,
            "requirements": [requirement.wire() for requirement in item.requirements],
            "free": item.free,
            "enabled": item.enabled,
            "capabilityCid": item.capability_cid,
            "metadata": dict(item.metadata),
        }

    def resolve(self, operation: Operation | str) -> PaidCapability | None:
        return self._by_key.get(Operation.parse(operation).key)

    def public_document(self) -> dict[str, Any]:
        return {"version": self.version, "catalogCid": self.cid, "capabilities": [self._public(i) for i in self._items]}


@dataclass(frozen=True, slots=True)
class RequestContext:
    request_cid: str
    idempotency_key: str
    authorized: bool = True
    policy_allowed: bool = True
    entitlement_cid: str | None = None
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PaymentDecision:
    decision: Decision
    operation: Operation
    reason_code: str
    capability: PaidCapability | None = None
    requirements: tuple[PaymentRequirement, ...] = ()
    evidence_cid: str | None = None


class PaymentPolicyEngine:
    """Commercial policy independent of HTTP, MCP, and libp2p transports."""

    def __init__(
        self,
        catalog: CapabilityCatalog,
        *,
        paid_lookup: Callable[[RequestContext, PaidCapability], str | None] | None = None,
        enabled: bool = True,
        emergency_pause: bool = False,
        unlisted: Decision = Decision.FREE,
    ) -> None:
        if unlisted not in (Decision.FREE, Decision.DENIED):
            raise ValueError("unlisted policy must be free or denied")
        self.catalog = catalog
        self.paid_lookup = paid_lookup
        self.enabled = enabled
        self.emergency_pause = emergency_pause
        self.unlisted = unlisted

    def evaluate(self, operation: Operation | str, context: RequestContext) -> PaymentDecision:
        op = Operation.parse(operation)
        capability = self.catalog.resolve(op)
        if not context.authorized or not context.policy_allowed:
            return PaymentDecision(Decision.DENIED, op, "H_PAYMENT_POLICY_DENIED", capability)
        if capability is None:
            reason = "H_FREE_OPERATION" if self.unlisted == Decision.FREE else "H_PAYMENT_POLICY_DENIED"
            return PaymentDecision(self.unlisted, op, reason)
        if not capability.enabled:
            return PaymentDecision(Decision.DENIED, op, "H_PAYMENT_POLICY_DENIED", capability)
        if capability.free:
            return PaymentDecision(Decision.FREE, op, "H_FREE_OPERATION", capability)
        if not self.enabled or self.emergency_pause:
            return PaymentDecision(Decision.UNAVAILABLE, op, "H_FACILITATOR_UNAVAILABLE", capability)
        evidence = self.paid_lookup(context, capability) if self.paid_lookup else None
        if evidence:
            return PaymentDecision(Decision.PAID, op, "H_PAYMENT_SATISFIED", capability, evidence_cid=evidence)
        return PaymentDecision(
            Decision.PAYMENT_REQUIRED,
            op,
            "H_PAYMENT_REQUIRED",
            capability,
            capability.requirements,
        )
