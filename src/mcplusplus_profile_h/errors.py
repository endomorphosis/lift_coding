"""Stable Profile H seller-runtime errors."""

from __future__ import annotations


class ProfileHError(RuntimeError):
    """An error safe to expose at a Profile H protocol boundary."""

    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable

    def as_dict(self) -> dict[str, object]:
        return {"code": self.code, "message": self.message, "retryable": self.retryable}


PAYMENT_REQUIRED = "H_PAYMENT_REQUIRED"
PAYMENT_DECLINED = "H_PAYMENT_DECLINED"
QUOTE_EXPIRED = "H_QUOTE_EXPIRED"
REQUEST_MISMATCH = "H_REQUEST_MISMATCH"
PAYMENT_REPLAY = "H_PAYMENT_REPLAY"
VERIFICATION_FAILED = "H_VERIFICATION_FAILED"
SETTLEMENT_FAILED = "H_SETTLEMENT_FAILED"
POLICY_DENIED = "H_PAYMENT_POLICY_DENIED"
FACILITATOR_UNAVAILABLE = "H_FACILITATOR_UNAVAILABLE"
RECONCILIATION_REQUIRED = "H_RECONCILIATION_REQUIRED"

