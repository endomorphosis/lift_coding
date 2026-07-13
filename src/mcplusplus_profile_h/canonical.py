"""Small dependency-free canonical JSON, CID, commitment, and redaction helpers."""

from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping
from typing import Any

_SENSITIVE = {
    "privatekey", "seedphrase", "mnemonic", "paymentsignature", "rawsignature",
    "paymentpayload", "facilitatorresponse", "authorization", "authenticationcookie",
    "cookie", "walletaddress", "transactionhash", "requestarguments", "fullucan",
}


def _sensitive_key(key: object) -> bool:
    normalized = "".join(character for character in str(key).lower() if character.isalnum())
    return normalized in _SENSITIVE


def canonical_json(value: Any) -> bytes:
    """Return the Profile H canonical JSON representation."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def cid_for(value: Any) -> str:
    """Create CIDv1(dag-json, sha2-256), matching the Profile H codecs."""
    digest = hashlib.sha256(canonical_json(value)).digest()
    raw = b"\x01\xa9\x02\x12\x20" + digest
    return "b" + base64.b32encode(raw).decode("ascii").lower().rstrip("=")


def commitment(value: Any) -> str:
    """Commit arbitrary private input without retaining it."""
    return cid_for({"commitment": hashlib.sha256(canonical_json(value)).hexdigest()})


def redact(value: Any) -> Any:
    """Recursively remove sensitive fields before diagnostics or persistence."""
    if isinstance(value, Mapping):
        return {
            str(key): "[REDACTED]" if _sensitive_key(key) else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    return value


def assert_public(value: Any, path: str = "") -> None:
    """Reject a sensitive field from a public content-addressed artifact."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            child = f"{path}/{key}"
            if _sensitive_key(key):
                raise ValueError(f"sensitive field forbidden in public artifact: {child}")
            assert_public(item, child)
    elif isinstance(value, list | tuple):
        for index, item in enumerate(value):
            assert_public(item, f"{path}/{index}")
