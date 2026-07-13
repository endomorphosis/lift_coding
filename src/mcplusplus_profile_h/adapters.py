"""Replaceable local and facilitator-backed x402 verification adapters."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from .catalog import PaymentRequirement
from .errors import FACILITATOR_UNAVAILABLE, SETTLEMENT_FAILED, VERIFICATION_FAILED, ProfileHError


@dataclass(frozen=True, slots=True)
class VerificationResult:
    valid: bool
    reason_code: str = ""
    verifier_did: str = "did:key:local-verifier"
    evidence: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SettlementResult:
    success: bool
    network: str
    transaction: str | None = None
    reason_code: str = ""
    response: Mapping[str, Any] = field(default_factory=dict)


class VerifierFacilitator(Protocol):
    async def verify(self, payload: Mapping[str, Any], requirement: PaymentRequirement) -> VerificationResult: ...
    async def settle(self, payload: Mapping[str, Any], requirement: PaymentRequirement) -> SettlementResult: ...
    async def lookup(self, payment_commitment: str) -> SettlementResult | None: ...
    async def health(self) -> bool: ...


async def _await(value: Any) -> Any:
    return await value if inspect.isawaitable(value) else value


class CallbackFacilitator:
    """Explicit adapter for local verifiers, testnets, and service integrations."""

    def __init__(
        self,
        verify: Callable[[Mapping[str, Any], PaymentRequirement], VerificationResult | Awaitable[VerificationResult]],
        settle: Callable[[Mapping[str, Any], PaymentRequirement], SettlementResult | Awaitable[SettlementResult]],
        *,
        lookup: Callable[[str], SettlementResult | None | Awaitable[SettlementResult | None]] | None = None,
        health: Callable[[], bool | Awaitable[bool]] | None = None,
    ) -> None:
        self._verify = verify
        self._settle = settle
        self._lookup = lookup
        self._health = health

    async def verify(self, payload: Mapping[str, Any], requirement: PaymentRequirement) -> VerificationResult:
        try:
            result = await _await(self._verify(payload, requirement))
        except ProfileHError:
            raise
        except Exception as exc:
            raise ProfileHError(FACILITATOR_UNAVAILABLE, "payment verifier unavailable", retryable=True) from exc
        if not isinstance(result, VerificationResult):
            raise TypeError("verify callback must return VerificationResult")
        return result

    async def settle(self, payload: Mapping[str, Any], requirement: PaymentRequirement) -> SettlementResult:
        try:
            result = await _await(self._settle(payload, requirement))
        except ProfileHError:
            raise
        except Exception as exc:
            raise ProfileHError(FACILITATOR_UNAVAILABLE, "payment facilitator unavailable", retryable=True) from exc
        if not isinstance(result, SettlementResult):
            raise TypeError("settle callback must return SettlementResult")
        return result

    async def lookup(self, payment_commitment: str) -> SettlementResult | None:
        return await _await(self._lookup(payment_commitment)) if self._lookup else None

    async def health(self) -> bool:
        try:
            return bool(await _await(self._health())) if self._health else True
        except Exception:
            return False


class X402SDKAdapter:
    """Narrow adapter around the pinned x402 Python facilitator client.

    SDK versions have changed method signatures. The injected client is kept
    behind this boundary and must expose ``verify``/``settle``; their returned
    objects may be mappings or pydantic-style models.
    """

    def __init__(self, client: Any, *, verifier_did: str = "did:web:facilitator.invalid") -> None:
        self.client = client
        self.verifier_did = verifier_did

    @staticmethod
    def _mapping(value: Any) -> dict[str, Any]:
        if isinstance(value, Mapping):
            return dict(value)
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if hasattr(value, "dict"):
            return value.dict()
        raise TypeError("unsupported x402 SDK response")

    async def verify(self, payload: Mapping[str, Any], requirement: PaymentRequirement) -> VerificationResult:
        try:
            raw = await _await(self.client.verify(dict(payload), requirement.wire()))
            value = self._mapping(raw)
        except Exception as exc:
            raise ProfileHError(FACILITATOR_UNAVAILABLE, "payment verifier unavailable", retryable=True) from exc
        valid = bool(value.get("isValid", value.get("valid", value.get("success", False))))
        reason = str(value.get("invalidReason", value.get("reason", "")))
        return VerificationResult(valid, reason or ("H_PAYMENT_VERIFIED" if valid else VERIFICATION_FAILED), self.verifier_did)

    async def settle(self, payload: Mapping[str, Any], requirement: PaymentRequirement) -> SettlementResult:
        try:
            raw = await _await(self.client.settle(dict(payload), requirement.wire()))
            value = self._mapping(raw)
        except Exception as exc:
            raise ProfileHError(FACILITATOR_UNAVAILABLE, "payment facilitator unavailable", retryable=True) from exc
        success = bool(value.get("success", False))
        return SettlementResult(
            success,
            str(value.get("network", requirement.network)),
            str(value["transaction"]) if value.get("transaction") else None,
            str(value.get("errorReason", "")) or ("H_PAYMENT_SETTLED" if success else SETTLEMENT_FAILED),
        )

    async def lookup(self, payment_commitment: str) -> SettlementResult | None:
        method = getattr(self.client, "lookup", None) or getattr(self.client, "get_status", None)
        if method is None:
            return None
        raw = await _await(method(payment_commitment))
        if raw is None:
            return None
        value = self._mapping(raw)
        return SettlementResult(bool(value.get("success")), str(value.get("network", "unknown:unknown")), value.get("transaction"), str(value.get("errorReason", "")))

    async def health(self) -> bool:
        method = getattr(self.client, "health", None)
        if method is None:
            return True
        try:
            return bool(await _await(method()))
        except Exception:
            return False
