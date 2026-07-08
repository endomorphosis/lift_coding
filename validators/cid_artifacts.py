"""Profile B CID-native execution artifact validator."""

from __future__ import annotations

import re
from typing import Any, Dict

from .base_mcp import ValidationResult


CID_PATTERN = re.compile(r"^(Qm[1-9A-HJ-NP-Za-km-z]{44}|b[a-z2-7]{58})$")


class CIDExecutionValidator:
    """Validate MCP++ CID execution envelopes and receipts."""

    REQUIRED_ENVELOPE_FIELDS = ("interface_cid", "input_cid")
    REQUIRED_RECEIPT_FIELDS = ("output_cid", "receipt_cid")
    OPTIONAL_CID_FIELDS = (
        "intent_cid",
        "policy_cid",
        "proof_cid",
        "decision_cid",
        "event_cid",
        "output_cid",
        "receipt_cid",
    )

    def validate_execution_envelope(self, envelope: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(is_valid=True, message_type="execution_envelope")
        if not isinstance(envelope, dict):
            result.add_error("Envelope must be an object")
            return result

        for field in self.REQUIRED_ENVELOPE_FIELDS:
            self._require_cid(envelope, field, result)

        for field in self.OPTIONAL_CID_FIELDS:
            if field in envelope:
                self._validate_cid_field(envelope, field, result)

        parents = envelope.get("parents", [])
        if parents is not None:
            if not isinstance(parents, list):
                result.add_error("'parents' must be an array")
            else:
                for index, parent in enumerate(parents):
                    if not self._is_valid_cid(parent):
                        result.add_error(f"Invalid parent CID at index {index}: {parent}")

        return result

    def validate_execution_receipt(self, receipt: Dict[str, Any]) -> ValidationResult:
        result = ValidationResult(is_valid=True, message_type="execution_receipt")
        if not isinstance(receipt, dict):
            result.add_error("Receipt must be an object")
            return result

        for field in self.REQUIRED_RECEIPT_FIELDS:
            self._require_cid(receipt, field, result)

        for field in ("envelope_cid", "decision_cid", "event_cid"):
            if field in receipt:
                self._validate_cid_field(receipt, field, result)

        if "success" in receipt and not isinstance(receipt["success"], bool):
            result.add_error("'success' must be a boolean when present")

        return result

    def _require_cid(self, payload: Dict[str, Any], field: str, result: ValidationResult) -> None:
        if field not in payload:
            result.add_error(f"Missing required field: {field}")
            return
        self._validate_cid_field(payload, field, result)

    def _validate_cid_field(
        self, payload: Dict[str, Any], field: str, result: ValidationResult
    ) -> None:
        cid = payload.get(field)
        if not self._is_valid_cid(cid):
            result.add_error(f"Invalid {field} format: {cid}")

    @staticmethod
    def _is_valid_cid(cid: Any) -> bool:
        return isinstance(cid, str) and bool(CID_PATTERN.match(cid))
