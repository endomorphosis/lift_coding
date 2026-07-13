from __future__ import annotations

import pytest

from mcplusplus_profile_h import (
    ArtifactSigner,
    DeterministicMeter,
    DuckDBEntitlementLedger,
    MeterDefinition,
    MeterUnit,
)
from mcplusplus_profile_h.canonical import cid_for, commitment
from mcplusplus_profile_h.errors import ProfileHError
from mcplusplus_profile_h.metering import (
    ENTITLEMENT_EXHAUSTED,
    ENTITLEMENT_SCOPE_MISMATCH,
    MAXIMUM_EXCEEDED,
    METER_INVALID,
    USAGE_DISPUTED,
)

NOW = 1_783_843_200_000
BUYER = ArtifactSigner.from_seed(b"b" * 32, key_id="buyer")
SELLER = ArtifactSigner.from_seed(b"s" * 32, key_id="seller")


def build(maximum=4):
    unit = MeterUnit("kilobyte", "1.0.0", "bytes", 1000)
    definition = MeterDefinition(
        "did:web:seller.test",
        "storage/add",
        unit,
        7,
        "test:asset",
        maximum_units_per_request=maximum,
    )
    meter = DeterministicMeter(definition, SELLER, authorization_public_key=BUYER.public_key)
    authorization = meter.authorize(
        authorization_id="auth-1",
        payer_scope_cid=cid_for({"payer": 1}),
        request_cid=cid_for({"request": 1}),
        capability_cid=cid_for({"capability": 1}),
        maximum_units=maximum,
        issued_at_ms=NOW,
        expires_at_ms=NOW + 10_000,
        buyer_signer=BUYER,
    )
    return meter, authorization


def usage(meter, authorization, quantity=1001, sequence=0):
    return meter.finalize(
        authorization,
        measured_quantity=quantity,
        input_commitment=commitment({"input": 1}),
        output_commitment=commitment({"output": 1}),
        sequence=sequence,
        started_at_ms=NOW + 1,
        ended_at_ms=NOW + 2,
    )


def test_versioned_unit_rounding_and_signed_usage_are_reproducible():
    meter, authorization = build()
    first = usage(meter, authorization)
    second = usage(meter, authorization)
    assert first.units == 2 and first.actual_charge == 14 and first.unused_amount == 14
    assert first.usage_cid == second.usage_cid
    assert dict(first.record) == dict(second.record)
    assert meter.verify_usage(first.record, authorization)
    assert first.record["unit"]["version"] == "1.0.0"


def test_maximum_is_enforced_before_a_charge_can_be_created():
    meter, authorization = build(maximum=2)
    with pytest.raises(ProfileHError) as raised:
        usage(meter, authorization, quantity=2001)
    assert raised.value.code == MAXIMUM_EXCEEDED


def test_authorization_must_be_signed_by_configured_buyer():
    meter, authorization = build()
    attacker = ArtifactSigner.from_seed(b"a" * 32, key_id="attacker")
    forged = attacker.sign(
        {
            key: value
            for key, value in authorization.items()
            if key not in {"signature", "signatureAlg", "signingKeyId", "publicKey"}
        }
    )
    with pytest.raises(ProfileHError) as raised:
        usage(meter, forged)
    assert raised.value.code == METER_INVALID


def test_quota_consumption_is_idempotent_and_exhaustion_is_bounded(tmp_path):
    meter, authorization = build(maximum=2)
    ledger = DuckDBEntitlementLedger(tmp_path / "quota.duckdb")
    scope = cid_for({"scope": 1})
    entitlement = ledger.issue(
        authorization,
        scope_cid=scope,
        issued_at_ms=NOW,
        seller_signer=SELLER,
        expected_authorization_public_key=BUYER.public_key,
    )
    record = usage(meter, authorization, quantity=2000)
    first = ledger.consume(
        entitlement["entitlementCid"],
        record,
        scope_cid=scope,
        now_ms=NOW + 3,
        expected_seller_public_key=SELLER.public_key,
    )
    replay = ledger.consume(
        entitlement["entitlementCid"],
        record,
        scope_cid=scope,
        now_ms=NOW + 4,
        expected_seller_public_key=SELLER.public_key,
    )
    assert first == replay and first.state == "exhausted" and first.remaining_units == 0
    with pytest.raises(ProfileHError) as raised:
        ledger.consume(
            entitlement["entitlementCid"],
            usage(meter, authorization, 1, 1),
            scope_cid=scope,
            now_ms=NOW + 5,
            expected_seller_public_key=SELLER.public_key,
        )
    assert raised.value.code == ENTITLEMENT_EXHAUSTED


def test_entitlements_are_scoped_and_tampered_usage_is_disputed(tmp_path):
    meter, authorization = build()
    ledger = DuckDBEntitlementLedger(tmp_path / "scope.duckdb")
    scope = cid_for({"scope": 1})
    entitlement = ledger.issue(
        authorization,
        scope_cid=scope,
        issued_at_ms=NOW,
        seller_signer=SELLER,
        expected_authorization_public_key=BUYER.public_key,
    )
    record = usage(meter, authorization)
    with pytest.raises(ProfileHError) as mismatch:
        ledger.consume(
            entitlement["entitlementCid"],
            record,
            scope_cid=cid_for({"scope": 2}),
            now_ms=NOW + 3,
            expected_seller_public_key=SELLER.public_key,
        )
    assert mismatch.value.code == ENTITLEMENT_SCOPE_MISMATCH
    tampered = {**record.record, "actualCharge": "1"}
    with pytest.raises(ProfileHError) as disputed:
        ledger.consume(
            entitlement["entitlementCid"],
            tampered,
            scope_cid=scope,
            now_ms=NOW + 3,
            expected_seller_public_key=SELLER.public_key,
        )
    assert disputed.value.code == USAGE_DISPUTED
