"""Deterministic ``upto`` metering and bounded Profile H entitlements.

Amounts and measured quantities are integers throughout this module.  A meter
definition is immutable and content addressed; changing a unit, quantum,
rounding rule, or price therefore creates a new meter CID.  Public usage
records commit to protected inputs/outputs and are signed by the seller.
"""

from __future__ import annotations

import base64
import json
import os
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Any

import duckdb
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_json, cid_for
from .errors import ProfileHError

METER_INVALID = "H_METER_INVALID"
MAXIMUM_EXCEEDED = "H_MAXIMUM_EXCEEDED"
ENTITLEMENT_EXHAUSTED = "H_ENTITLEMENT_EXHAUSTED"
ENTITLEMENT_EXPIRED = "H_ENTITLEMENT_EXPIRED"
ENTITLEMENT_SCOPE_MISMATCH = "H_ENTITLEMENT_SCOPE_MISMATCH"
USAGE_REPLAY = "H_USAGE_REPLAY"
USAGE_DISPUTED = "H_USAGE_DISPUTED"


def _canonical_uint(value: int | str, name: str, *, positive: bool = False) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    if isinstance(value, str):
        if not value.isdigit() or (len(value) > 1 and value.startswith("0")):
            raise ValueError(f"{name} must be a canonical unsigned integer")
        parsed = int(value)
    elif isinstance(value, int):
        parsed = value
    else:
        raise ValueError(f"{name} must be an integer")
    if parsed < (1 if positive else 0):
        raise ValueError(f"{name} is out of range")
    return parsed


@dataclass(frozen=True, slots=True)
class MeterUnit:
    """Versioned reproducible conversion from a base quantity to billed units."""

    name: str
    version: str
    base_quantity: str
    quantum: int
    rounding: str = "ceil"

    def __post_init__(self) -> None:
        if not self.name or not self.version or not self.base_quantity:
            raise ValueError("meter unit identity fields must be non-empty")
        object.__setattr__(self, "quantum", _canonical_uint(self.quantum, "quantum", positive=True))
        if self.rounding not in {"ceil", "floor", "exact"}:
            raise ValueError("rounding must be ceil, floor, or exact")

    def wire(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "baseQuantity": self.base_quantity,
            "quantum": str(self.quantum),
            "rounding": self.rounding,
        }

    @property
    def cid(self) -> str:
        return cid_for({"schema": "mcp++/profile-h/meter-unit@1.0", **self.wire()})

    def units_for(self, quantity: int | str) -> int:
        value = _canonical_uint(quantity, "measured quantity")
        quotient, remainder = divmod(value, self.quantum)
        if self.rounding == "ceil":
            return quotient + bool(remainder)
        if self.rounding == "floor":
            return quotient
        if remainder:
            raise ProfileHError(
                METER_INVALID, "quantity is not an exact multiple of the meter quantum"
            )
        return quotient


@dataclass(frozen=True, slots=True)
class MeterDefinition:
    seller_did: str
    operation: str
    unit: MeterUnit
    atomic_price_per_unit: int
    asset: str
    pricing_mode: str = "upto"
    maximum_units_per_request: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.seller_did.startswith("did:") or not self.operation or not self.asset:
            raise ValueError("invalid meter definition identity")
        object.__setattr__(
            self,
            "atomic_price_per_unit",
            _canonical_uint(self.atomic_price_per_unit, "atomic price", positive=True),
        )
        if self.pricing_mode not in {"upto", "exact"}:
            raise ValueError("pricing_mode must be upto or exact")
        if self.maximum_units_per_request is not None:
            object.__setattr__(
                self,
                "maximum_units_per_request",
                _canonical_uint(self.maximum_units_per_request, "maximum units", positive=True),
            )
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata or {})))

    def wire(self) -> dict[str, Any]:
        return {
            "schema": "mcp++/profile-h/meter-definition@1.0",
            "sellerDid": self.seller_did,
            "operation": self.operation,
            "pricingMode": self.pricing_mode,
            "unit": self.unit.wire(),
            "unitCid": self.unit.cid,
            "atomicPricePerUnit": str(self.atomic_price_per_unit),
            "asset": self.asset,
            "maximumUnitsPerRequest": (
                str(self.maximum_units_per_request)
                if self.maximum_units_per_request is not None
                else None
            ),
            "metadata": dict(self.metadata),
        }

    @property
    def cid(self) -> str:
        return cid_for(self.wire())


class ArtifactSigner:
    """Ed25519 signer for public artifacts; private key material is never exposed."""

    def __init__(self, private_key: Ed25519PrivateKey, *, key_id: str) -> None:
        if not key_id:
            raise ValueError("key_id must be non-empty")
        self._key = private_key
        self.key_id = key_id

    @classmethod
    def from_seed(cls, seed: bytes, *, key_id: str) -> ArtifactSigner:
        if len(seed) != 32:
            raise ValueError("Ed25519 seed must be exactly 32 bytes")
        return cls(Ed25519PrivateKey.from_private_bytes(seed), key_id=key_id)

    @classmethod
    def load_or_create(cls, path: str | Path, *, key_id: str) -> ArtifactSigner:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            raw = target.read_bytes()
        except FileNotFoundError:
            raw = os.urandom(32)
            try:
                descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                raw = target.read_bytes()
            else:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(raw)
                    stream.flush()
                    os.fsync(stream.fileno())
        if len(raw) != 32:
            raise ValueError("persisted Ed25519 key must contain 32 bytes")
        if target.stat().st_mode & 0o077:
            raise PermissionError("meter signing key permissions must be 0600 or stricter")
        return cls.from_seed(raw, key_id=key_id)

    @property
    def public_key(self) -> str:
        raw = self._key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        return base64.b64encode(raw).decode("ascii")

    def sign(self, artifact: Mapping[str, Any]) -> dict[str, Any]:
        unsigned = dict(artifact)
        for field_name in ("signature", "signatureAlg", "signingKeyId", "publicKey"):
            unsigned.pop(field_name, None)
        signed = {
            **unsigned,
            "signatureAlg": "Ed25519",
            "signingKeyId": self.key_id,
            "publicKey": self.public_key,
        }
        return {
            **signed,
            "signature": base64.b64encode(self._key.sign(canonical_json(signed))).decode("ascii"),
        }

    @staticmethod
    def verify(artifact: Mapping[str, Any], *, expected_public_key: str | None = None) -> bool:
        try:
            unsigned = dict(artifact)
            signature = base64.b64decode(str(unsigned.pop("signature")), validate=True)
            public_text = str(unsigned.get("publicKey"))
            if unsigned.get("signatureAlg") != "Ed25519" or (
                expected_public_key and public_text != expected_public_key
            ):
                return False
            public = base64.b64decode(public_text, validate=True)
            Ed25519PublicKey.from_public_bytes(public).verify(signature, canonical_json(unsigned))
            return True
        except (KeyError, ValueError, TypeError, InvalidSignature):
            return False


@dataclass(frozen=True, slots=True)
class MaximumAuthorization:
    authorization_id: str
    payer_scope_cid: str
    request_cid: str
    capability_cid: str
    meter_cid: str
    maximum_units: int
    maximum_amount: int
    asset: str
    issued_at_ms: int
    expires_at_ms: int
    unused_value_rule: str = "release"

    def __post_init__(self) -> None:
        for name in (
            "authorization_id",
            "payer_scope_cid",
            "request_cid",
            "capability_cid",
            "meter_cid",
            "asset",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        object.__setattr__(
            self,
            "maximum_units",
            _canonical_uint(self.maximum_units, "maximum units", positive=True),
        )
        object.__setattr__(
            self,
            "maximum_amount",
            _canonical_uint(self.maximum_amount, "maximum amount", positive=True),
        )
        if self.expires_at_ms <= self.issued_at_ms:
            raise ValueError("authorization expiry must follow issuance")
        if self.unused_value_rule != "release":
            raise ValueError("upto authorizations must release unused value")

    def artifact(self) -> dict[str, Any]:
        return {
            "schema": "mcp++/profile-h/maximum-authorization@1.0",
            "authorizationId": self.authorization_id,
            "pricingMode": "upto",
            "payerScopeCid": self.payer_scope_cid,
            "requestCid": self.request_cid,
            "capabilityCid": self.capability_cid,
            "meterCid": self.meter_cid,
            "maximumUnits": str(self.maximum_units),
            "maximumAmount": str(self.maximum_amount),
            "asset": self.asset,
            "issuedAt": self.issued_at_ms,
            "expiresAt": self.expires_at_ms,
            "unusedValueRule": self.unused_value_rule,
        }


@dataclass(frozen=True, slots=True)
class UsageResult:
    record: Mapping[str, Any]
    usage_cid: str
    units: int
    actual_charge: int
    unused_amount: int


class DeterministicMeter:
    """Finalize and verify signed usage against a buyer-approved maximum."""

    def __init__(
        self,
        definition: MeterDefinition,
        signer: ArtifactSigner,
        *,
        authorization_public_key: str | None = None,
    ) -> None:
        self.definition = definition
        self.signer = signer
        self.authorization_public_key = authorization_public_key

    def authorize(
        self,
        *,
        authorization_id: str,
        payer_scope_cid: str,
        request_cid: str,
        capability_cid: str,
        maximum_units: int,
        issued_at_ms: int,
        expires_at_ms: int,
        buyer_signer: ArtifactSigner,
    ) -> dict[str, Any]:
        units = _canonical_uint(maximum_units, "maximum units", positive=True)
        if self.definition.pricing_mode != "upto":
            raise ProfileHError(
                METER_INVALID, "maximum authorization is unavailable for exact pricing"
            )
        if (
            self.definition.maximum_units_per_request
            and units > self.definition.maximum_units_per_request
        ):
            raise ProfileHError(MAXIMUM_EXCEEDED, "requested units exceed the catalog maximum")
        maximum = units * self.definition.atomic_price_per_unit
        value = MaximumAuthorization(
            authorization_id,
            payer_scope_cid,
            request_cid,
            capability_cid,
            self.definition.cid,
            units,
            maximum,
            self.definition.asset,
            issued_at_ms,
            expires_at_ms,
        )
        return buyer_signer.sign(value.artifact())

    def finalize(
        self,
        authorization: Mapping[str, Any],
        *,
        measured_quantity: int,
        input_commitment: str,
        output_commitment: str,
        sequence: int,
        started_at_ms: int,
        ended_at_ms: int,
        completion: str = "complete",
    ) -> UsageResult:
        self._validate_authorization(authorization, ended_at_ms)
        if completion not in {"complete", "partial", "cancelled", "timed_out"}:
            raise ValueError("invalid completion status")
        if ended_at_ms < started_at_ms:
            raise ValueError("usage end precedes start")
        units = self.definition.unit.units_for(measured_quantity)
        maximum_units = int(authorization["maximumUnits"])
        if units > maximum_units:
            raise ProfileHError(MAXIMUM_EXCEEDED, "measured usage exceeds the approved maximum")
        charge = units * self.definition.atomic_price_per_unit
        maximum = int(authorization["maximumAmount"])
        if charge > maximum:
            raise ProfileHError(MAXIMUM_EXCEEDED, "actual charge exceeds the approved maximum")
        record = {
            "schema": "mcp++/profile-h/usage-record@1.0",
            "meterCid": self.definition.cid,
            "unit": self.definition.unit.wire(),
            "unitCid": self.definition.unit.cid,
            "authorizationCid": cid_for(dict(authorization)),
            "authorizationId": authorization["authorizationId"],
            "requestCid": authorization["requestCid"],
            "capabilityCid": authorization["capabilityCid"],
            "sequence": _canonical_uint(sequence, "sequence"),
            "measuredQuantity": str(measured_quantity),
            "billedUnits": str(units),
            "atomicPricePerUnit": str(self.definition.atomic_price_per_unit),
            "actualCharge": str(charge),
            "maximumAmount": str(maximum),
            "asset": self.definition.asset,
            "completion": completion,
            "startedAt": started_at_ms,
            "endedAt": ended_at_ms,
            "inputCommitment": input_commitment,
            "outputCommitment": output_commitment,
            "roundingApplied": self.definition.unit.rounding,
            "unusedAmount": str(maximum - charge),
            "unusedValueDisposition": "released",
        }
        signed = self.signer.sign(record)
        return UsageResult(
            MappingProxyType(signed), cid_for(signed), units, charge, maximum - charge
        )

    def _validate_authorization(self, value: Mapping[str, Any], now_ms: int) -> None:
        if not self.authorization_public_key:
            raise ProfileHError(METER_INVALID, "no trusted buyer authorization key is configured")
        if not ArtifactSigner.verify(value, expected_public_key=self.authorization_public_key):
            raise ProfileHError(METER_INVALID, "maximum authorization signature is invalid")
        if (
            value.get("schema") != "mcp++/profile-h/maximum-authorization@1.0"
            or value.get("pricingMode") != "upto"
        ):
            raise ProfileHError(METER_INVALID, "unsupported maximum authorization")
        if (
            value.get("meterCid") != self.definition.cid
            or value.get("asset") != self.definition.asset
        ):
            raise ProfileHError(
                ENTITLEMENT_SCOPE_MISMATCH, "authorization does not match this meter"
            )
        maximum_units = _canonical_uint(value.get("maximumUnits"), "maximum units", positive=True)
        maximum_amount = _canonical_uint(
            value.get("maximumAmount"), "maximum amount", positive=True
        )
        if maximum_amount != maximum_units * self.definition.atomic_price_per_unit:
            raise ProfileHError(
                METER_INVALID, "authorization amount does not reproduce from its units"
            )
        if now_ms > int(value["expiresAt"]):
            raise ProfileHError(ENTITLEMENT_EXPIRED, "maximum authorization expired")

    def verify_usage(self, record: Mapping[str, Any], authorization: Mapping[str, Any]) -> bool:
        try:
            if not ArtifactSigner.verify(record, expected_public_key=self.signer.public_key):
                return False
            if (
                record.get("meterCid") != self.definition.cid
                or record.get("unitCid") != self.definition.unit.cid
            ):
                return False
            if record.get("authorizationCid") != cid_for(dict(authorization)):
                return False
            units = self.definition.unit.units_for(record["measuredQuantity"])
            charge = units * self.definition.atomic_price_per_unit
            return (
                str(units) == record.get("billedUnits")
                and str(charge) == record.get("actualCharge")
                and charge <= int(authorization["maximumAmount"])
                and int(record["unusedAmount"]) == int(authorization["maximumAmount"]) - charge
            )
        except (KeyError, TypeError, ValueError, ProfileHError):
            return False


@dataclass(frozen=True, slots=True)
class EntitlementStatus:
    entitlement_cid: str
    state: str
    remaining_units: int
    remaining_amount: int
    expires_at_ms: int


class DuckDBEntitlementLedger:
    """Transactional quota consumption indexed by immutable usage CIDs."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = duckdb.connect(self.path)
        self._lock = threading.RLock()
        self.connection.execute("""CREATE TABLE IF NOT EXISTS profile_h_entitlements (
            entitlement_cid VARCHAR PRIMARY KEY, artifact_json JSON NOT NULL, scope_cid VARCHAR NOT NULL,
            meter_cid VARCHAR NOT NULL, remaining_units BIGINT NOT NULL, remaining_amount HUGEINT NOT NULL,
            expires_at_ms BIGINT NOT NULL, state VARCHAR NOT NULL, updated_at_ms BIGINT NOT NULL)""")
        self.connection.execute("""CREATE TABLE IF NOT EXISTS profile_h_usage_consumption (
            usage_cid VARCHAR PRIMARY KEY, entitlement_cid VARCHAR NOT NULL, sequence BIGINT NOT NULL,
            units BIGINT NOT NULL, amount HUGEINT NOT NULL, consumed_at_ms BIGINT NOT NULL,
            UNIQUE(entitlement_cid, sequence))""")

    def issue(
        self,
        authorization: Mapping[str, Any],
        *,
        scope_cid: str,
        issued_at_ms: int,
        seller_signer: ArtifactSigner,
        expected_authorization_public_key: str | None = None,
    ) -> dict[str, Any]:
        if not expected_authorization_public_key:
            raise ProfileHError(METER_INVALID, "no trusted buyer authorization key is configured")
        if not ArtifactSigner.verify(
            authorization, expected_public_key=expected_authorization_public_key
        ):
            raise ProfileHError(
                METER_INVALID, "cannot issue entitlement from invalid authorization"
            )
        artifact = seller_signer.sign(
            {
                "schema": "mcp++/profile-h/paid-entitlement@1.0",
                "authorizationCid": cid_for(dict(authorization)),
                "scopeCid": scope_cid,
                "requestCid": authorization["requestCid"],
                "capabilityCid": authorization["capabilityCid"],
                "meterCid": authorization["meterCid"],
                "quotaUnits": authorization["maximumUnits"],
                "quotaAmount": authorization["maximumAmount"],
                "asset": authorization["asset"],
                "issuedAt": issued_at_ms,
                "expiresAt": authorization["expiresAt"],
                "unusedValueRule": "release",
            }
        )
        entitlement_cid = cid_for(artifact)
        with self._lock:
            self.connection.execute(
                """INSERT INTO profile_h_entitlements VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?)
                ON CONFLICT DO NOTHING""",
                [
                    entitlement_cid,
                    canonical_json(artifact).decode(),
                    scope_cid,
                    authorization["meterCid"],
                    int(authorization["maximumUnits"]),
                    int(authorization["maximumAmount"]),
                    int(authorization["expiresAt"]),
                    issued_at_ms,
                ],
            )
        return {**artifact, "entitlementCid": entitlement_cid}

    def consume(
        self,
        entitlement_cid: str,
        usage: UsageResult | Mapping[str, Any],
        *,
        scope_cid: str,
        now_ms: int | None = None,
        expected_seller_public_key: str | None = None,
    ) -> EntitlementStatus:
        now = now_ms if now_ms is not None else time.time_ns() // 1_000_000
        record = dict(usage.record if isinstance(usage, UsageResult) else usage)
        usage_cid = usage.usage_cid if isinstance(usage, UsageResult) else cid_for(record)
        if not ArtifactSigner.verify(record, expected_public_key=expected_seller_public_key):
            raise ProfileHError(USAGE_DISPUTED, "usage record signature is invalid")
        units = _canonical_uint(record.get("billedUnits"), "billed units")
        amount = _canonical_uint(record.get("actualCharge"), "actual charge")
        sequence = _canonical_uint(record.get("sequence"), "sequence")
        with self._lock:
            existing = self.connection.execute(
                "SELECT entitlement_cid FROM profile_h_usage_consumption WHERE usage_cid = ?",
                [usage_cid],
            ).fetchone()
            if existing:
                if existing[0] != entitlement_cid:
                    raise ProfileHError(
                        USAGE_REPLAY, "usage record was consumed by another entitlement"
                    )
                return self.status(entitlement_cid, now_ms=now)
            row = self.connection.execute(
                """SELECT scope_cid, meter_cid, remaining_units, remaining_amount,
                expires_at_ms, state, artifact_json FROM profile_h_entitlements WHERE entitlement_cid = ?""",
                [entitlement_cid],
            ).fetchone()
            if not row:
                raise KeyError(entitlement_cid)
            if row[0] != scope_cid or row[1] != record.get("meterCid"):
                raise ProfileHError(
                    ENTITLEMENT_SCOPE_MISMATCH, "entitlement scope or meter does not match usage"
                )
            entitlement = json.loads(row[6]) if isinstance(row[6], str) else row[6]
            if record.get("authorizationCid") != entitlement.get("authorizationCid"):
                raise ProfileHError(
                    ENTITLEMENT_SCOPE_MISMATCH, "usage belongs to another authorization"
                )
            if now > row[4]:
                self.connection.execute(
                    "UPDATE profile_h_entitlements SET state = 'expired', updated_at_ms = ? WHERE entitlement_cid = ?",
                    [now, entitlement_cid],
                )
                raise ProfileHError(ENTITLEMENT_EXPIRED, "entitlement expired")
            if row[5] != "active" or units > row[2] or amount > row[3]:
                raise ProfileHError(ENTITLEMENT_EXHAUSTED, "entitlement quota exhausted")
            state = "exhausted" if units == row[2] or amount == row[3] else "active"
            try:
                self.connection.execute("BEGIN TRANSACTION")
                self.connection.execute(
                    """INSERT INTO profile_h_usage_consumption VALUES (?, ?, ?, ?, ?, ?)""",
                    [usage_cid, entitlement_cid, sequence, units, amount, now],
                )
                self.connection.execute(
                    """UPDATE profile_h_entitlements SET remaining_units = remaining_units - ?,
                    remaining_amount = remaining_amount - ?, state = ?, updated_at_ms = ? WHERE entitlement_cid = ?""",
                    [units, amount, state, now, entitlement_cid],
                )
                self.connection.execute("COMMIT")
            except duckdb.ConstraintException as exc:
                self.connection.execute("ROLLBACK")
                raise ProfileHError(USAGE_REPLAY, "usage sequence was already consumed") from exc
            except Exception:
                self.connection.execute("ROLLBACK")
                raise
            return self.status(entitlement_cid, now_ms=now)

    def cancel(self, entitlement_cid: str, *, now_ms: int | None = None) -> dict[str, Any]:
        now = now_ms if now_ms is not None else time.time_ns() // 1_000_000
        with self._lock:
            status = self.status(entitlement_cid, now_ms=now)
            if status.state == "active":
                self.connection.execute(
                    "UPDATE profile_h_entitlements SET state = 'cancelled', updated_at_ms = ? WHERE entitlement_cid = ?",
                    [now, entitlement_cid],
                )
                status = self.status(entitlement_cid, now_ms=now)
            return {
                "entitlementCid": entitlement_cid,
                "state": status.state,
                "releasedUnits": str(status.remaining_units),
                "releasedAmount": str(status.remaining_amount),
                "unusedValueDisposition": "released",
            }

    def status(self, entitlement_cid: str, *, now_ms: int | None = None) -> EntitlementStatus:
        row = self.connection.execute(
            "SELECT state, remaining_units, remaining_amount, expires_at_ms FROM profile_h_entitlements WHERE entitlement_cid = ?",
            [entitlement_cid],
        ).fetchone()
        if not row:
            raise KeyError(entitlement_cid)
        now = now_ms if now_ms is not None else time.time_ns() // 1_000_000
        state = "expired" if row[0] == "active" and now > row[3] else row[0]
        return EntitlementStatus(entitlement_cid, state, int(row[1]), int(row[2]), int(row[3]))

    def close(self) -> None:
        self.connection.close()
