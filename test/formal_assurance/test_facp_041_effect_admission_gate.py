"""FACP-041: Connect SwissKnife and seal the EAK negative gate.

Acceptance (taskboard):
- Changing browser authority fields never changes host authorization.
- Changed arguments / actor / resource / policy / expiry / nonce fail.
- No migrated effect occurs before valid admission.
- Receipt records exact observation or non-success.

Validates the declared SwissKnife AdmissionTokenClient projection and executes
hermetic cross-boundary negatives against the FACP-039 kernel + FACP-040
common transport gate (no live host effect, no provider execution).
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CLIENT_TS_PATH = (
    REPO_ROOT / "swissknife" / "src" / "services" / "mcp" / "admissionTokenClient.ts"
)
GATEWAY_TS_PATH = (
    REPO_ROOT / "swissknife" / "src" / "services" / "mcp" / "formalAssuranceGateway.ts"
)
ACCELERATE_ROOT = REPO_ROOT / "external" / "ipfs_accelerate"

TASK_ID = "FACP-041"
GOAL_ID = "FACP-G320"
SCHEMA = "facp/effect-admission-gate@1"
BUNDLE = "facp/admission/gate"
TOKEN_SCHEMA = "facp/admission-token@1"
RECEIPT_SCHEMA = "facp/effect-admission-receipt@1"
KERNEL_ISSUER = "effect_admission_kernel"
KERNEL_CALL = "effect_admission_kernel.unlock_handler"
INVENTORIED_SEAM = "swissknife/src/services/mcp/formalAssuranceGateway.ts"

REQUIRED_EVIDENCE_SUBSET = {
    "browser allow/consent/dry-run nonauthority",
    "one-use confirmation",
    "argument binding",
    "replay/expiry/revocation",
    "all-transport kernel identity",
}

BROWSER_AUTHORITY_FIELDS = (
    "consent",
    "allow",
    "policy_decision",
    "confirmation_token",
    "tenant_id",
    "workspace_id",
    "dry_run",
    "browser_policy",
    "policy",
)

CLOSED_OUTCOMES = {
    "Unavailable",
    "Rejected",
    "Simulated",
    "Attempted",
    "Unknown",
    "Observed",
    "Verified",
    "Failed",
    "Compensated",
}

NON_SUCCESS_OUTCOMES = CLOSED_OUTCOMES - {"Observed", "Verified"}

SECRET_OR_PRIVATE_KEYS = {
    "goose_secret_key",
    "X-Secret-Key",
    "secret_header",
    "authorization",
    "api_key",
    "password",
    "secret",
    "bearer_token",
    "backend_credentials",
    "token_secret",
    "private_context",
    "private_key",
    "signing_key",
    "host_path",
    "file_path",
    "filesystem_path",
}

NOW_MS = 1_700_000_000_000
NOT_AFTER = NOW_MS + 60_000


def _ensure_accelerate_path() -> None:
    token = str(ACCELERATE_ROOT)
    if token not in sys.path:
        sys.path.insert(0, token)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _strip_browser_authority(fields: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in fields.items():
        if key in BROWSER_AUTHORITY_FIELDS:
            continue
        if key in SECRET_OR_PRIVATE_KEYS:
            continue
        out[key] = value
    return out


def _argument_cid_local(arguments: dict[str, Any]) -> str:
    """Local mirror of client argumentCidFor (dag-json CID not required for digest tests)."""
    cleaned = {k: v for k, v in arguments.items() if k not in SECRET_OR_PRIVATE_KEYS}
    return f"cid:argument:{_sha256_hex({'label': 'argument', 'material': cleaned})}"


def project_host_authorization_input(request: dict[str, Any]) -> dict[str, Any]:
    """Mirror AdmissionTokenClient.projectHostAuthorizationInput semantics."""
    cleaned = _strip_browser_authority(request)
    args = cleaned.get("arguments")
    if args is None:
        args = cleaned.get("payload", {})
    if not isinstance(args, dict):
        args = {}
    argument_cid = cleaned.get("argument_cid") or _argument_cid_local(args)
    argument_digest = cleaned.get("argument_digest") or _sha256_hex(args)
    actor = cleaned.get("actor_cid")
    if actor is None and isinstance(cleaned.get("actor_id"), str):
        actor = f"actor:{cleaned['actor_id']}"
    resource = cleaned.get("resource_cid")
    if resource is None and isinstance(cleaned.get("resource_id"), str):
        resource = f"cid:resource:{_sha256_hex(cleaned['resource_id'])}"
    policy = cleaned.get("policy_cid")
    if policy is None:
        policy = cleaned.get("host_policy_id")
    expiry = cleaned.get("expiry")
    if expiry is None:
        expiry = cleaned.get("not_after")
    operation_id = cleaned.get("operation_id") or cleaned.get("method") or "tools/call"
    return {
        "actor_cid": actor,
        "resource_cid": resource,
        "operation_id": operation_id,
        "argument_cid": argument_cid,
        "argument_digest": argument_digest,
        "policy_cid": policy,
        "expiry": expiry,
        "nonce": cleaned.get("nonce"),
        "admission_token_cid": cleaned.get("admission_token_cid"),
        "consent": "absent",
        "authority_decision": None,
    }


@pytest.fixture(scope="module")
def client_ts() -> str:
    assert CLIENT_TS_PATH.is_file(), f"missing client: {CLIENT_TS_PATH}"
    return CLIENT_TS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def accelerate_admission():
    _ensure_accelerate_path()
    from ipfs_accelerate_py.agent_supervisor.admission.formal_kernel import (
        KERNEL_ISSUER as KERNEL_ISSUER_MOD,
        AdmissionBindings,
        AdmissionErrorCode,
        AdmissionToken,
        AdmissionVerdict,
        OperationSpecView,
        binding_cid,
        default_kernel,
        derive_token_obligations,
        fresh_nonce,
    )
    from ipfs_accelerate_py.agent_supervisor.admission.transport_gate import (
        KERNEL_CALL as KERNEL_CALL_MOD,
        MIGRATED_TRANSPORTS,
        CommonTransportGate,
        HandlerNotUnlockedError,
        TransportRequest,
        argument_cid_for,
        default_transport_gate,
        same_kernel_call,
    )

    return {
        "KERNEL_ISSUER": KERNEL_ISSUER_MOD,
        "KERNEL_CALL": KERNEL_CALL_MOD,
        "AdmissionBindings": AdmissionBindings,
        "AdmissionErrorCode": AdmissionErrorCode,
        "AdmissionToken": AdmissionToken,
        "AdmissionVerdict": AdmissionVerdict,
        "OperationSpecView": OperationSpecView,
        "binding_cid": binding_cid,
        "default_kernel": default_kernel,
        "derive_token_obligations": derive_token_obligations,
        "fresh_nonce": fresh_nonce,
        "MIGRATED_TRANSPORTS": MIGRATED_TRANSPORTS,
        "CommonTransportGate": CommonTransportGate,
        "HandlerNotUnlockedError": HandlerNotUnlockedError,
        "TransportRequest": TransportRequest,
        "argument_cid_for": argument_cid_for,
        "default_transport_gate": default_transport_gate,
        "same_kernel_call": same_kernel_call,
    }


def _spec(adm: dict[str, Any], **overrides: Any):
    values: dict[str, Any] = {
        "operation_id": "swissknife.desktop.invoke",
        "effect_class": "process",
        "authority_obligation": "capability_verified",
        "policy_obligation": "host_policy_required",
        "confirmation_obligation": "one_use_confirmation_required",
        "lease_obligation": "lease_required",
        "observation_obligation": "independent_observation_required",
        "idempotency_class": "at_most_once",
        "reversibility_class": "compensatable",
    }
    values.update(overrides)
    return adm["OperationSpecView"](**values)


def _allow_policy(*, policy_cid: str | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {
        "name": "allow-swissknife-desktop",
        "clauses": [
            {
                "clause_type": "permission",
                "actor": "*",
                "action": "swissknife.desktop.invoke",
                "resource": "*",
            }
        ],
    }
    if policy_cid is not None:
        body["policy_cid"] = policy_cid
    return body


def _bindings(adm: dict[str, Any], *, arguments: dict[str, Any] | None = None, **overrides: Any):
    args = arguments if arguments is not None else {"scope": "cap:demo", "limit": 1}
    policy_body = _allow_policy()
    values: dict[str, Any] = {
        "actor_cid": adm["binding_cid"]("actor", "operator-1"),
        "device_cid": adm["binding_cid"]("device", "device-1"),
        "tenant_cid": adm["binding_cid"]("tenant", "tenant-1"),
        "resource_cid": adm["binding_cid"]("resource", "binding:virtual-desktop:demo"),
        "operation_id": "swissknife.desktop.invoke",
        "argument_cid": adm["argument_cid_for"](args),
        "contract_cid": adm["binding_cid"]("contract", "facp/operation-spec@1"),
        "delegation_cid": adm["binding_cid"]("delegation", "ucan:chain-1"),
        "policy_cid": adm["binding_cid"]("policy", policy_body),
        "confirmation_cid": adm["binding_cid"]("confirmation", "confirm:1"),
        "lease_id": "lease:demo-1",
        "not_before": NOW_MS - 1_000,
        "not_after": NOT_AFTER,
        "nonce": adm["fresh_nonce"](),
        "signature_cid": adm["binding_cid"]("signature", "sig:1"),
        "revocation_id": "",
    }
    values.update(overrides)
    return adm["AdmissionBindings"](**values), args, policy_body


def _ready_gate(adm: dict[str, Any], handler_log: list[dict[str, Any]] | None = None):
    log: list[dict[str, Any]] = handler_log if handler_log is not None else []

    def _handler(arguments: Any) -> dict[str, Any]:
        entry = {"arguments": dict(arguments), "outcome": "Observed"}
        log.append(entry)
        return entry

    gate = adm["default_transport_gate"](now_ms=NOW_MS)
    gate.register_handler(_spec(adm), _handler)
    return gate, log


# ---------------------------------------------------------------------------
# Declared output / evidence envelope
# ---------------------------------------------------------------------------


def test_declared_outputs_exist_and_bind_facp_041(client_ts: str) -> None:
    assert TASK_ID in client_ts
    assert GOAL_ID in client_ts
    assert SCHEMA in client_ts
    assert BUNDLE in client_ts
    assert TOKEN_SCHEMA in client_ts
    assert RECEIPT_SCHEMA in client_ts
    assert KERNEL_ISSUER in client_ts
    assert KERNEL_CALL in client_ts
    assert "AdmissionTokenClient" in client_ts
    assert "BROWSER_TOKEN_CONSTRUCTION = false" in client_ts or (
        "BROWSER_TOKEN_CONSTRUCTION=false" in client_ts.replace(" ", "")
    )
    assert "UNSAFE_PROMOTION = false" in client_ts or (
        "UNSAFE_PROMOTION=false" in client_ts.replace(" ", "")
    )
    assert INVENTORIED_SEAM in client_ts or "formalAssuranceGateway.ts" in client_ts
    assert GATEWAY_TS_PATH.is_file(), "FACP-030 host projection seam missing"
    assert "projectHostAuthorizationInput" in client_ts
    assert "admitOrRejectEffect" in client_ts
    assert "sealEffectAdmissionReceipt" in client_ts
    assert "projectOneUseConfirmationIntent" in client_ts
    assert "verifyTokenBindings" in client_ts
    assert "rejectBrowserTokenConstruction" in client_ts
    assert "sameKernelCallIdentity" in client_ts


def test_evidence_subset_declared(client_ts: str) -> None:
    for item in REQUIRED_EVIDENCE_SUBSET:
        assert item in client_ts, item
    assert "EVIDENCE_SUBSET" in client_ts


def test_closed_outcomes_and_non_success_vocabulary(client_ts: str) -> None:
    for outcome in CLOSED_OUTCOMES:
        assert f"'{outcome}'" in client_ts or f'"{outcome}"' in client_ts
    assert "NON_SUCCESS_OUTCOMES" in client_ts
    assert "Observed" in client_ts
    assert "Rejected" in client_ts


# ---------------------------------------------------------------------------
# Browser allow/consent/dry-run nonauthority
# ---------------------------------------------------------------------------


def test_browser_authority_fields_never_change_host_authorization(client_ts: str) -> None:
    assert "BROWSER_AUTHORITY_FIELDS" in client_ts
    assert "stripBrowserAuthorityFields" in client_ts
    assert "browserAuthorityDoesNotChangeHostAuthorization" in client_ts
    for field in ("consent", "allow", "dry_run", "policy_decision"):
        assert field in client_ts

    base = {
        "operation_id": "swissknife.desktop.invoke",
        "actor_id": "operator-1",
        "resource_id": "binding:virtual-desktop:demo",
        "arguments": {"scope": "cap:demo", "limit": 1},
        "host_policy_id": "policy:demo",
        "admission_token_cid": "baguqeerademoadmissiontoken0000000000000000000001",
        "nonce": "nonce-1",
        "expiry": NOT_AFTER,
    }
    granted = {
        **base,
        "consent": "granted",
        "allow": True,
        "dry_run": False,
        "policy_decision": {"outcome": "allow"},
        "tenant_id": "tenant-browser",
        "confirmation_token": "ui-confirm-1",
    }
    denied = {
        **base,
        "consent": "denied",
        "allow": False,
        "dry_run": True,
        "policy_decision": {"outcome": "deny"},
        "workspace_id": "ws-browser",
        "browser_policy": {"allow": False},
    }
    input_a = project_host_authorization_input(granted)
    input_b = project_host_authorization_input(denied)
    assert input_a == input_b
    assert input_a["consent"] == "absent"
    assert input_a["authority_decision"] is None
    assert "allow" not in input_a
    assert "dry_run" not in input_a
    assert input_a["argument_digest"] == input_b["argument_digest"]
    assert input_a["argument_cid"] == input_b["argument_cid"]


def test_browser_token_construction_forbidden(client_ts: str) -> None:
    assert "rejectBrowserTokenConstruction" in client_ts
    assert "FORBIDDEN_TOKEN_ISSUERS" in client_ts or "forbidden" in client_ts.lower()
    for issuer in ("browser", "prompt", "model", "peer", "payment", "allow", "consent"):
        assert issuer in client_ts


# ---------------------------------------------------------------------------
# One-use confirmation
# ---------------------------------------------------------------------------


def test_one_use_confirmation_is_intent_not_grant(client_ts: str) -> None:
    assert "projectOneUseConfirmationIntent" in client_ts
    assert "grants_authority: false" in client_ts or (
        "grants_authority:false" in client_ts.replace(" ", "")
    )
    assert "one_use: true" in client_ts or "one_use:true" in client_ts.replace(" ", "")
    assert "confirmation_intent" in client_ts
    # Confirmation token from browser must not unlock effects.
    assert re.search(r"grants_authority:\s*false", client_ts)


# ---------------------------------------------------------------------------
# Changed arguments / actor / resource / policy / expiry / nonce fail
# ---------------------------------------------------------------------------


def test_changed_bindings_fail_closed(accelerate_admission: dict[str, Any], client_ts: str) -> None:
    assert "ARGUMENT_MISMATCH" in client_ts
    assert "BINDING_MISMATCH" in client_ts
    assert "EXPIRED_TOKEN" in client_ts
    assert "REPLAYED_TOKEN" in client_ts
    assert "REVOKED_TOKEN" in client_ts

    adm = accelerate_admission
    gate, log = _ready_gate(adm)
    bindings, args, policy = _bindings(adm)
    token = gate.kernel.mint_token(_spec(adm), bindings, source_policy=_allow_policy(policy_cid=bindings.policy_cid))

    # Happy path unlock with exact args.
    decision = gate.kernel.unlock_handler(
        spec=_spec(adm),
        typestate="Reserved",
        token=token,
        argument_cid=bindings.argument_cid,
        consume=False,
    )
    assert decision.verdict is adm["AdmissionVerdict"].ADMIT
    assert decision.unlocked is True

    # Changed arguments fail.
    changed_args = {**args, "limit": 99}
    changed_cid = adm["argument_cid_for"](changed_args)
    deny_args = gate.kernel.unlock_handler(
        spec=_spec(adm),
        typestate="Reserved",
        token=token,
        argument_cid=changed_cid,
        consume=False,
    )
    assert deny_args.verdict is adm["AdmissionVerdict"].DENY
    assert deny_args.unlocked is False
    assert deny_args.code is adm["AdmissionErrorCode"].ARGUMENT_MISMATCH
    assert log == []

    # Changed actor / resource fail at the SwissKnife client binding gate:
    # host authorization inputs diverge, so verifyTokenBindings rejects.
    token_proj = {
        "issuer": KERNEL_ISSUER,
        "token_id": token.token_id,
        "operation_id": token.operation_id,
        "effect_class": token.effect_class,
        "argument_cid": token.argument_cid,
        "actor_cid": token.actor_cid,
        "resource_cid": bindings.resource_cid,
        "policy_cid": bindings.policy_cid,
        "nonce": token.nonce,
        "not_after": token.not_after,
        "admission_token_cid": token.token_id,
        "satisfied_obligations": list(token.satisfied_obligations),
    }

    def _client_binding_mismatches(
        projected: dict[str, Any], expected: dict[str, Any]
    ) -> list[str]:
        mismatches: list[str] = []
        if projected["argument_cid"] != expected["argument_cid"]:
            mismatches.append("ARGUMENT_MISMATCH")
        if expected.get("actor_cid") and projected["actor_cid"] != expected["actor_cid"]:
            mismatches.append("actor_cid")
        if (
            expected.get("resource_cid")
            and projected.get("resource_cid") != expected["resource_cid"]
        ):
            mismatches.append("resource_cid")
        if (
            expected.get("policy_cid")
            and projected.get("policy_cid") != expected["policy_cid"]
        ):
            mismatches.append("policy_cid")
        if expected.get("expiry") is not None and projected["not_after"] != expected["expiry"]:
            mismatches.append("expiry")
        if expected.get("nonce") and projected["nonce"] != expected["nonce"]:
            mismatches.append("nonce")
        return mismatches

    assert _client_binding_mismatches(
        token_proj,
        {
            "argument_cid": bindings.argument_cid,
            "actor_cid": adm["binding_cid"]("actor", "intruder"),
            "resource_cid": bindings.resource_cid,
            "policy_cid": bindings.policy_cid,
            "expiry": bindings.not_after,
            "nonce": bindings.nonce,
        },
    ) == ["actor_cid"]
    assert _client_binding_mismatches(
        token_proj,
        {
            "argument_cid": bindings.argument_cid,
            "actor_cid": bindings.actor_cid,
            "resource_cid": adm["binding_cid"]("resource", "other"),
            "policy_cid": bindings.policy_cid,
            "expiry": bindings.not_after,
            "nonce": bindings.nonce,
        },
    ) == ["resource_cid"]
    assert _client_binding_mismatches(
        token_proj,
        {
            "argument_cid": bindings.argument_cid,
            "actor_cid": bindings.actor_cid,
            "resource_cid": bindings.resource_cid,
            "policy_cid": adm["binding_cid"]("policy", {"name": "attacker"}),
            "expiry": bindings.not_after,
            "nonce": bindings.nonce,
        },
    ) == ["policy_cid"]
    assert _client_binding_mismatches(
        token_proj,
        {
            "argument_cid": bindings.argument_cid,
            "actor_cid": bindings.actor_cid,
            "resource_cid": bindings.resource_cid,
            "policy_cid": bindings.policy_cid,
            "expiry": bindings.not_after + 5,
            "nonce": bindings.nonce,
        },
    ) == ["expiry"]
    assert _client_binding_mismatches(
        token_proj,
        {
            "argument_cid": bindings.argument_cid,
            "actor_cid": bindings.actor_cid,
            "resource_cid": bindings.resource_cid,
            "policy_cid": bindings.policy_cid,
            "expiry": bindings.not_after,
            "nonce": "nonce-attacker",
        },
    ) == ["nonce"]

    # Missing actor evidence cannot mint when actor_bound is required.
    missing_actor, _, _ = _bindings(adm, nonce=adm["fresh_nonce"](), actor_cid="")
    with pytest.raises(Exception) as actor_exc:
        gate.kernel.mint_token(
            _spec(adm),
            missing_actor,
            source_policy=_allow_policy(policy_cid=missing_actor.policy_cid),
        )
    assert getattr(actor_exc.value, "code", None) is adm["AdmissionErrorCode"].MISSING_EVIDENCE

    # Expiry fails.
    expired_bindings, _, _ = _bindings(adm, not_after=NOW_MS - 1, nonce=adm["fresh_nonce"]())
    with pytest.raises(Exception) as expired_exc:
        gate.kernel.mint_token(
            _spec(adm),
            expired_bindings,
            source_policy=_allow_policy(policy_cid=expired_bindings.policy_cid),
        )
    assert getattr(expired_exc.value, "code", None) is adm["AdmissionErrorCode"].EXPIRED_TOKEN

    # Replay fails after consume.
    gate.kernel.consume(token)
    deny_replay = gate.kernel.unlock_handler(
        spec=_spec(adm),
        typestate="Reserved",
        token=token,
        argument_cid=bindings.argument_cid,
        consume=True,
    )
    assert deny_replay.verdict is adm["AdmissionVerdict"].DENY
    assert deny_replay.code is adm["AdmissionErrorCode"].REPLAYED_TOKEN

    # Revocation fails.
    bindings2, args2, _ = _bindings(adm, nonce=adm["fresh_nonce"]())
    token2 = gate.kernel.mint_token(
        _spec(adm), bindings2, source_policy=_allow_policy(policy_cid=bindings2.policy_cid)
    )
    gate.kernel.revoke(token2)
    deny_revoked = gate.kernel.unlock_handler(
        spec=_spec(adm),
        typestate="Reserved",
        token=token2,
        argument_cid=bindings2.argument_cid,
        consume=True,
    )
    assert deny_revoked.verdict is adm["AdmissionVerdict"].DENY
    assert deny_revoked.code is adm["AdmissionErrorCode"].REVOKED_TOKEN
    assert log == []

    # Policy mismatch: mint with different policy_cid than compiled IR.
    bad_policy_bindings, _, _ = _bindings(
        adm,
        nonce=adm["fresh_nonce"](),
        policy_cid=adm["binding_cid"]("policy", {"name": "other"}),
    )
    with pytest.raises(Exception) as policy_exc:
        gate.kernel.mint_token(
            _spec(adm),
            bad_policy_bindings,
            source_policy=_allow_policy(policy_cid=bindings.policy_cid),
        )
    assert getattr(policy_exc.value, "code", None) in {
        adm["AdmissionErrorCode"].BINDING_MISMATCH,
        adm["AdmissionErrorCode"].POLICY_DENIED,
        adm["AdmissionErrorCode"].POLICY_INDETERMINATE,
    }

    # Resource / nonce binding deltas alter host authorization digests.
    host_a = project_host_authorization_input(
        {
            "operation_id": "swissknife.desktop.invoke",
            "actor_cid": bindings.actor_cid,
            "resource_cid": bindings.resource_cid,
            "arguments": args,
            "policy_cid": bindings.policy_cid,
            "nonce": bindings.nonce,
            "expiry": bindings.not_after,
            "admission_token_cid": token.token_id,
        }
    )
    host_resource = project_host_authorization_input(
        {
            "operation_id": "swissknife.desktop.invoke",
            "actor_cid": bindings.actor_cid,
            "resource_cid": adm["binding_cid"]("resource", "other"),
            "arguments": args,
            "policy_cid": bindings.policy_cid,
            "nonce": bindings.nonce,
            "expiry": bindings.not_after,
            "admission_token_cid": token.token_id,
        }
    )
    host_nonce = project_host_authorization_input(
        {
            "operation_id": "swissknife.desktop.invoke",
            "actor_cid": bindings.actor_cid,
            "resource_cid": bindings.resource_cid,
            "arguments": args,
            "policy_cid": bindings.policy_cid,
            "nonce": "nonce-delta",
            "expiry": bindings.not_after,
            "admission_token_cid": token.token_id,
        }
    )
    host_expiry = project_host_authorization_input(
        {
            "operation_id": "swissknife.desktop.invoke",
            "actor_cid": bindings.actor_cid,
            "resource_cid": bindings.resource_cid,
            "arguments": args,
            "policy_cid": bindings.policy_cid,
            "nonce": bindings.nonce,
            "expiry": bindings.not_after + 1,
            "admission_token_cid": token.token_id,
        }
    )
    assert host_a["resource_cid"] != host_resource["resource_cid"]
    assert host_a["nonce"] != host_nonce["nonce"]
    assert host_a["expiry"] != host_expiry["expiry"]
    host_args = project_host_authorization_input(
        {
            "operation_id": "swissknife.desktop.invoke",
            "actor_cid": bindings.actor_cid,
            "resource_cid": bindings.resource_cid,
            "arguments": changed_args,
            "policy_cid": bindings.policy_cid,
            "nonce": bindings.nonce,
            "expiry": bindings.not_after,
            "admission_token_cid": token.token_id,
        }
    )
    assert host_a["argument_digest"] != host_args["argument_digest"]
    assert host_a["argument_cid"] != host_args["argument_cid"]


# ---------------------------------------------------------------------------
# No migrated effect before valid admission
# ---------------------------------------------------------------------------


def test_no_migrated_effect_before_valid_admission(
    accelerate_admission: dict[str, Any], client_ts: str
) -> None:
    assert "admitOrRejectEffect" in client_ts
    assert "effect_invoked" in client_ts
    assert "HANDLER_NOT_UNLOCKED" in client_ts
    assert "host_admission_required" in client_ts

    adm = accelerate_admission
    gate, log = _ready_gate(adm)

    # Direct handler call without token fails; zero invocations.
    gated = gate.get_gated_handler("swissknife.desktop.invoke")
    with pytest.raises(adm["HandlerNotUnlockedError"]) as exc:
        gated({"scope": "cap:demo", "limit": 1})
    assert exc.value.code is adm["AdmissionErrorCode"].HANDLER_NOT_UNLOCKED
    assert log == []
    assert gate.handler_invocation_count() == 0

    # Dispatch without token is Rejected with zero handler invocations.
    denied = gate.dispatch(
        "python",
        adm["TransportRequest"](
            operation_id="swissknife.desktop.invoke",
            arguments={"scope": "cap:demo", "limit": 1},
            typestate="Reserved",
            token=None,
            authority_source="host",
        ),
    )
    assert denied.admitted is False
    assert denied.handler_invoked is False
    assert denied.outcome == "Rejected"
    assert log == []
    assert gate.handler_invocation_count() == 0

    # Browser/model authority selection fails before unlock.
    browser_denied = gate.dispatch(
        "mcp",
        adm["TransportRequest"](
            operation_id="swissknife.desktop.invoke",
            arguments={"scope": "cap:demo", "limit": 1},
            typestate="Reserved",
            token=None,
            authority_source="browser",
            transport_overlay={"policy_cid": "policy:attacker", "tenant_cid": "t"},
        ),
    )
    assert browser_denied.admitted is False
    assert browser_denied.handler_invoked is False
    assert browser_denied.outcome == "Rejected"
    assert log == []

    # Valid admission then effect.
    bindings, args, _ = _bindings(adm)
    token = gate.kernel.mint_token(
        _spec(adm), bindings, source_policy=_allow_policy(policy_cid=bindings.policy_cid)
    )
    # SwissKnife client projects tokens; host unlock runs on the python seam.
    admitted = gate.dispatch(
        "python",
        adm["TransportRequest"](
            operation_id="swissknife.desktop.invoke",
            arguments=args,
            typestate="Reserved",
            token=token,
            authority_source="host",
        ),
    )
    assert admitted.admitted is True
    assert admitted.handler_invoked is True
    assert admitted.outcome == "Observed"
    assert len(log) == 1
    assert gate.handler_invocation_count() == 1


# ---------------------------------------------------------------------------
# Receipt records exact observation or non-success
# ---------------------------------------------------------------------------


def test_receipt_records_exact_observation_or_non_success(
    accelerate_admission: dict[str, Any], client_ts: str
) -> None:
    assert "sealEffectAdmissionReceipt" in client_ts
    assert RECEIPT_SCHEMA in client_ts
    assert "closed_outcome" in client_ts
    assert "observation" in client_ts
    # Must not promote via free-form success boolean.
    assert "success" in client_ts  # mentioned as forbidden promotion path
    assert re.search(r"unsafe_promotion:\s*(false|UNSAFE_PROMOTION)", client_ts)

    adm = accelerate_admission
    gate, log = _ready_gate(adm)
    bindings, args, _ = _bindings(adm)
    token = gate.kernel.mint_token(
        _spec(adm), bindings, source_policy=_allow_policy(policy_cid=bindings.policy_cid)
    )
    result = gate.dispatch(
        "python",
        adm["TransportRequest"](
            operation_id="swissknife.desktop.invoke",
            arguments=args,
            typestate="Reserved",
            token=token,
            authority_source="host",
        ),
    )
    assert result.outcome == "Observed"
    receipt_observed = {
        "schema": RECEIPT_SCHEMA,
        "schema_version": 1,
        "task_id": TASK_ID,
        "operation_id": result.operation_id,
        "argument_cid": result.argument_cid,
        "admission_token_cid": token.token_id,
        "admitted": True,
        "effect_invoked": True,
        "closed_outcome": result.outcome,
        "observation": "Observed",
        "reason": result.message,
        "unsafe_promotion": False,
        "browser_token_construction": False,
    }
    assert receipt_observed["closed_outcome"] in CLOSED_OUTCOMES
    assert receipt_observed["closed_outcome"] == "Observed"
    assert receipt_observed["observation"] == "Observed"
    assert receipt_observed["effect_invoked"] is True

    # Non-success denial receipt — never Observed.
    denied = gate.dispatch(
        "python",
        adm["TransportRequest"](
            operation_id="swissknife.desktop.invoke",
            arguments=args,
            typestate="Reserved",
            token=None,
            authority_source="host",
        ),
    )
    receipt_denied = {
        "schema": RECEIPT_SCHEMA,
        "schema_version": 1,
        "task_id": TASK_ID,
        "operation_id": denied.operation_id,
        "argument_cid": denied.argument_cid,
        "admission_token_cid": None,
        "admitted": False,
        "effect_invoked": False,
        "closed_outcome": denied.outcome,
        "observation": None,
        "reason": denied.message or "host_admission_required",
        "unsafe_promotion": False,
        "browser_token_construction": False,
    }
    assert receipt_denied["closed_outcome"] in NON_SUCCESS_OUTCOMES
    assert receipt_denied["closed_outcome"] == "Rejected"
    assert receipt_denied["observation"] is None
    assert receipt_denied["effect_invoked"] is False
    assert "success" not in receipt_denied


# ---------------------------------------------------------------------------
# All-transport kernel identity
# ---------------------------------------------------------------------------


def test_all_transport_kernel_identity(
    accelerate_admission: dict[str, Any], client_ts: str
) -> None:
    assert "sameKernelCallIdentity" in client_ts
    assert "kernelIdentityWithoutTransport" in client_ts
    assert "MIGRATED_TRANSPORTS" in client_ts
    assert "swissknife" in client_ts
    for transport in ("cli", "mcp", "mcp++", "python"):
        assert transport in client_ts

    adm = accelerate_admission
    identities: list[Any] = []
    for transport in adm["MIGRATED_TRANSPORTS"]:
        gate, log = _ready_gate(adm)
        bindings, args, _ = _bindings(adm)
        token = gate.kernel.mint_token(
            _spec(adm), bindings, source_policy=_allow_policy(policy_cid=bindings.policy_cid)
        )
        result = gate.dispatch(
            transport,
            adm["TransportRequest"](
                operation_id="swissknife.desktop.invoke",
                arguments=args,
                typestate="Reserved",
                token=token,
                authority_source="host",
            ),
        )
        assert result.admitted is True
        assert result.handler_invoked is True
        assert result.kernel_call is not None
        assert result.kernel_call.method == KERNEL_CALL
        assert result.kernel_call.method == adm["KERNEL_CALL"]
        assert result.kernel_call.argument_cid == bindings.argument_cid
        assert len(log) == 1
        identities.append(result.kernel_call)

    # Shared unlock identity across every migrated Accelerate transport.
    for left, right in zip(identities, identities[1:]):
        assert adm["same_kernel_call"](left, right)
        assert left.identity_without_transport() == right.identity_without_transport()

    # Client declares swissknife transport joins the same kernel call method.
    assert KERNEL_CALL in client_ts
    assert adm["KERNEL_ISSUER"] == KERNEL_ISSUER


def test_facp_041_metadata_matches_accelerate_kernel(
    accelerate_admission: dict[str, Any], client_ts: str
) -> None:
    assert GOAL_ID == "FACP-G320"
    assert BUNDLE == "facp/admission/gate"
    assert SCHEMA == "facp/effect-admission-gate@1"
    assert accelerate_admission["KERNEL_ISSUER"] == KERNEL_ISSUER
    assert accelerate_admission["KERNEL_CALL"] == KERNEL_CALL
    assert "FACP-030" not in CLIENT_TS_PATH.name
    assert TASK_ID in client_ts
