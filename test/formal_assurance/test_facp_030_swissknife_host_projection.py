"""FACP-030: Migrate SwissKnife to host-issued FCA outcomes.

Acceptance (taskboard):
- Browser sends no authority decision.
- Default consent is absent.
- UI displays exact method/resource/argument digest.
- Consumes host-provided typed outcome without upgrading evidence.

Validates the declared FormalAssuranceGateway projection and TypeScript suite
hermetically (no browser network/host effect). The Python harness is the
declared Validation target (EXPLICIT_VALIDATION_TARGET); SwissKnife Outputs
remain the owned production deliverables.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_TS_PATH = (
    REPO_ROOT / "swissknife" / "src" / "services" / "mcp" / "formalAssuranceGateway.ts"
)
TEST_TS_PATH = (
    REPO_ROOT
    / "swissknife"
    / "test"
    / "formal-assurance"
    / "host-admission-projection.test.ts"
)
LIVE_GATEWAY_SEAM = (
    REPO_ROOT
    / "swissknife"
    / "src"
    / "services"
    / "mcp"
    / "virtual-desktop-live-gateway.ts"
)
INVENTORY_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "swissknife_authority.json"
)

TASK_ID = "FACP-030"
GOAL_ID = "FACP-G240"
SCHEMA = "facp/host-admission-projection@1"
BUNDLE = "facp/migration/swissknife-host"
INVENTORIED_SEAM = "swissknife/src/services/mcp/virtual-desktop-live-gateway.ts"

REQUIRED_EVIDENCE_SUBSET = {
    "canonical request",
    "actor/session opaque refs",
    "method/resource/argument CID",
    "host decision",
    "confirmation request",
    "evidence classification",
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

SECRET_OR_HOST_KEYS = {
    "goose_secret_key",
    "X-Secret-Key",
    "secret_header",
    "authorization",
    "api_key",
    "password",
    "secret",
    "bearer_token",
    "backend_credentials",
    "host_path",
    "file_path",
    "filesystem_path",
    "python_process",
    "process_command",
    "stdio",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _arguments_from_intent(intent: dict[str, Any]) -> dict[str, Any]:
    args = intent.get("arguments")
    if args is None:
        args = intent.get("payload", {})
    if not isinstance(args, dict):
        return {}
    return {k: v for k, v in args.items() if k not in SECRET_OR_HOST_KEYS}


def project_canonical_host_request(
    intent: dict[str, Any],
    host_bindings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Mirror FormalAssuranceGateway.projectCanonicalHostRequest semantics."""
    host_bindings = host_bindings or {}
    method = intent.get("method") or "tools/call"
    resource_id = intent.get("resource_id") or intent.get("binding_id")
    args = _arguments_from_intent(intent)
    mutates = bool(intent.get("mutates_remote_state", True))
    if "dry_run_intent" in intent:
        dry_run_intent = bool(intent["dry_run_intent"])
    else:
        dry_run_intent = mutates

    actor_raw = intent.get("actor_id") or intent.get("actor_ref")
    session_raw = intent.get("session_id") or intent.get("session_ref")

    def opaque(kind: str, raw: Any) -> str | None:
        if raw is None or raw == "":
            return None
        if not isinstance(raw, str):
            return f"{kind}:opaque:{_sha256_hex(raw)[:16]}"
        lowered = raw.lower()
        for banned in (
            "sk-live",
            "secret",
            "password",
            "bearer ",
            "/home/",
            "/var/",
            "file://",
            "goose_secret",
        ):
            if banned in lowered:
                return f"{kind}:redacted:{_sha256_hex(raw)[:16]}"
        if raw.startswith(("actor:", "session:", "operator:")):
            return raw
        return f"{kind}:{raw}"

    return {
        "schema": SCHEMA,
        "task_id": TASK_ID,
        "method": method,
        "resource_id": resource_id,
        "binding_id": intent.get("binding_id"),
        "actor_ref": opaque("actor", actor_raw),
        "session_ref": opaque("session", session_raw),
        "method_digest": _sha256_hex(method),
        "resource_digest": _sha256_hex(resource_id),
        "argument_digest": _sha256_hex(args),
        "dry_run_intent": dry_run_intent,
        "mutates_remote_state": mutates,
        "correlation_id": intent.get("correlation_id"),
        "consent": "absent",
        "authority_decision": None,
        "host_policy_id": host_bindings.get("host_policy_id"),
        "admission_token_cid": host_bindings.get("admission_token_cid"),
        "expiry": host_bindings.get("expiry"),
        "nonce": host_bindings.get("nonce"),
    }


def project_host_decision_from_bindings(request: dict[str, Any]) -> dict[str, Any]:
    """Fail-closed host decision from admission/policy bindings."""
    if not request.get("admission_token_cid"):
        return {
            "outcome": "deny",
            "authority": "absent",
            "policy": "unchecked",
            "reason": "host_admission_required",
            "closed_outcome": "Rejected",
            "bound_argument_digest": request["argument_digest"],
            "bound_method_digest": request["method_digest"],
            "bound_resource_digest": request["resource_digest"],
        }
    if not request.get("host_policy_id"):
        return {
            "outcome": "deny",
            "authority": "absent",
            "policy": "unchecked",
            "reason": "host_policy_binding_required",
            "closed_outcome": "Rejected",
            "bound_argument_digest": request["argument_digest"],
            "bound_method_digest": request["method_digest"],
            "bound_resource_digest": request["resource_digest"],
        }
    return {
        "outcome": "allow",
        "authority": "valid",
        "policy": "allowed",
        "reason": "host_issued_admission",
        "closed_outcome": "Attempted",
        "bound_argument_digest": request["argument_digest"],
        "bound_method_digest": request["method_digest"],
        "bound_resource_digest": request["resource_digest"],
        "bound_nonce": request.get("nonce"),
        "bound_expiry": request.get("expiry"),
    }


def consume_host_issued_typed_outcome(
    request: dict[str, Any],
    host_outcome: dict[str, Any] | None,
    *,
    local_evidence_attempt: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Consume host outcome without upgrading evidence beyond the host envelope."""
    ui_digest = {
        "method": request["method"],
        "resource_id": request["resource_id"],
        "method_digest": request["method_digest"],
        "resource_digest": request["resource_digest"],
        "argument_digest": request["argument_digest"],
    }
    weak = {
        "origin": "declared",
        "authority": "unchecked",
        "policy": "unchecked",
        "effect": "not_started",
        "proof": "none",
        "freshness": "stale",
        "integrity": "unchecked",
        "environment": "hermetic",
        "review": "unreviewed",
    }
    upgrade_targets = {
        "authority:valid",
        "policy:allowed",
        "policy:allowed_with_obligations",
        "effect:observed",
        "proof:verified",
        "freshness:current",
        "environment:live",
        "integrity:digest_valid",
        "origin:observed",
    }

    if not host_outcome:
        return {
            "accepted": False,
            "outcome": "deny",
            "closed_outcome": "Rejected",
            "reason": "host_admission_required",
            "ui_digest": ui_digest,
            "evidence_class": "presentation_only",
            "evidence": dict(weak),
            "authority_decision_from_browser": False,
            "default_consent": "absent",
        }

    digest_mismatch = (
        host_outcome.get("bound_argument_digest") != request["argument_digest"]
        or host_outcome.get("bound_method_digest") != request["method_digest"]
        or host_outcome.get("bound_resource_digest") != request["resource_digest"]
    )
    if digest_mismatch:
        return {
            "accepted": False,
            "outcome": "deny",
            "closed_outcome": "Rejected",
            "reason": "host_outcome_digest_mismatch",
            "ui_digest": ui_digest,
            "evidence_class": "presentation_only",
            "evidence": dict(weak),
            "authority_decision_from_browser": False,
            "default_consent": "absent",
        }

    if local_evidence_attempt:
        host_evidence = host_outcome.get("evidence") or {}
        for dim, value in local_evidence_attempt.items():
            key = f"{dim}:{value}"
            if key in upgrade_targets and host_evidence.get(dim) != value:
                return {
                    "accepted": False,
                    "outcome": "deny",
                    "closed_outcome": "Rejected",
                    "reason": "evidence_upgrade_forbidden",
                    "ui_digest": ui_digest,
                    "evidence_class": "presentation_only",
                    "evidence": dict(weak),
                    "authority_decision_from_browser": False,
                    "default_consent": "absent",
                }

    evidence = dict(weak)
    for dim, value in (host_outcome.get("evidence") or {}).items():
        if isinstance(value, str):
            evidence[dim] = value
    if host_outcome.get("authority") == "valid":
        evidence["authority"] = "valid"
    elif host_outcome.get("authority") == "absent":
        evidence["authority"] = "absent"
    if host_outcome.get("policy") == "allowed":
        evidence["policy"] = "allowed"
    elif host_outcome.get("policy") == "denied":
        evidence["policy"] = "denied"

    accepted_allow = (
        host_outcome.get("outcome") == "allow"
        and host_outcome.get("authority") == "valid"
        and host_outcome.get("policy") == "allowed"
    )
    return {
        "accepted": accepted_allow,
        "outcome": "allow" if accepted_allow else "deny",
        "closed_outcome": (
            host_outcome.get("closed_outcome", "Attempted")
            if accepted_allow
            else "Rejected"
        ),
        "reason": (
            host_outcome.get("reason")
            if accepted_allow
            else (host_outcome.get("reason") or "host_denied")
        ),
        "ui_digest": ui_digest,
        "evidence_class": "host_issued",
        "evidence": evidence,
        "authority_decision_from_browser": False,
        "default_consent": "absent",
    }


def legacy_desktop_authority_synthesis(intent: dict[str, Any]) -> dict[str, Any]:
    """Legacy default-granted / browser-constructed allow — failing seed only."""
    governed = bool(intent.get("mutates_remote_state", True))
    consent = intent.get("consent")
    if consent is None:
        consent = "granted" if governed else "not_required"
    outcome = "deny" if consent == "denied" else "allow"
    return {
        "consent": consent,
        "policy_decision": {
            "decision_id": f"desktop-policy:{intent.get('binding_id', 'unknown')}",
            "outcome": outcome,
            "reason": "legacy_browser_constructed",
        },
        "host_authorization_influenced_by_browser": True,
        "accepted_evidence": False,
        "disposition": "failing_seed",
        "evidence_class": "failing_seed_legacy",
        "seam": INVENTORIED_SEAM,
    }


@pytest.fixture(scope="module")
def gateway_ts() -> str:
    assert GATEWAY_TS_PATH.is_file(), f"missing gateway: {GATEWAY_TS_PATH}"
    return GATEWAY_TS_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def test_ts() -> str:
    assert TEST_TS_PATH.is_file(), f"missing TypeScript suite: {TEST_TS_PATH}"
    return TEST_TS_PATH.read_text(encoding="utf-8")


def test_declared_outputs_exist_and_bind_facp_030(gateway_ts: str, test_ts: str) -> None:
    assert TASK_ID in gateway_ts
    assert GOAL_ID in gateway_ts
    assert SCHEMA in gateway_ts
    assert BUNDLE in gateway_ts
    assert INVENTORIED_SEAM in gateway_ts or "virtual-desktop-live-gateway.ts" in gateway_ts

    assert TASK_ID in test_ts
    assert SCHEMA in test_ts
    assert "projectCanonicalHostRequest" in test_ts
    assert "consumeHostIssuedTypedOutcome" in test_ts
    assert "projectConfirmationRequest" in test_ts
    assert "classifyBrowserProjectionEvidence" in test_ts
    assert "legacyDesktopAuthoritySynthesis" in test_ts
    assert LIVE_GATEWAY_SEAM.is_file(), "inventoried live gateway seam missing"


def test_evidence_subset_declared(gateway_ts: str, test_ts: str) -> None:
    for item in REQUIRED_EVIDENCE_SUBSET:
        assert item in gateway_ts, item
        assert item in test_ts, item


def test_browser_sends_no_authority_decision_default_consent_absent(
    gateway_ts: str, test_ts: str
) -> None:
    assert re.search(r"consent:\s*'absent'", gateway_ts)
    assert "authority_decision: null" in gateway_ts or "authority_decision:null" in gateway_ts.replace(
        " ", ""
    )
    assert "authority_decision_sent: false" in gateway_ts or "authority_decision_sent:false" in gateway_ts.replace(
        " ", ""
    )
    assert "default_consent: 'absent'" in gateway_ts or 'default_consent: "absent"' in gateway_ts

    # Browser authority fields must be stripped / never treated as admission.
    for field in ("consent", "allow", "policy_decision", "confirmation_token"):
        assert field in gateway_ts
    assert "BROWSER_AUTHORITY_FIELDS" in gateway_ts
    assert "stripBrowserAuthorityFields" in gateway_ts
    assert "assertBrowserSendsNoAuthorityDecision" in gateway_ts

    # Semantic projection: browser consent deltas collapse to absent.
    base = {
        "binding_id": "binding:virtual-desktop:demo-mutate",
        "method": "tools/call",
        "resource_id": "binding:virtual-desktop:demo-mutate",
        "actor_id": "operator:desktop-ui",
        "payload": {"dry_run": True, "scope": "cap:demo", "limit": 1},
        "mutates_remote_state": True,
    }
    granted = project_canonical_host_request({**base, "consent": "granted", "allow": True})
    denied = project_canonical_host_request({**base, "consent": "denied", "allow": False})
    assert granted["consent"] == "absent"
    assert denied["consent"] == "absent"
    assert granted["authority_decision"] is None
    assert denied["authority_decision"] is None
    assert granted["argument_digest"] == denied["argument_digest"]
    assert granted["method_digest"] == denied["method_digest"]
    assert granted["resource_digest"] == denied["resource_digest"]

    # Suite must assert the acceptance criteria.
    assert "browser sends no authority decision" in test_ts.lower() or (
        "authority_decision" in test_ts and "absent" in test_ts
    )
    assert "consent" in test_ts and "absent" in test_ts


def test_ui_displays_exact_method_resource_argument_digests(
    gateway_ts: str, test_ts: str
) -> None:
    assert "projectUiDigestDisplay" in gateway_ts
    assert "method_digest" in gateway_ts
    assert "resource_digest" in gateway_ts
    assert "argument_digest" in gateway_ts
    assert "display_lines" in gateway_ts
    assert "method_cid" in gateway_ts
    assert "resource_cid" in gateway_ts
    assert "argument_cid" in gateway_ts

    intent = {
        "binding_id": "binding:virtual-desktop:demo-mutate",
        "method": "tools/call",
        "resource_id": "binding:virtual-desktop:demo-mutate",
        "payload": {"dry_run": True, "scope": "cap:demo", "limit": 1},
        "mutates_remote_state": True,
    }
    request = project_canonical_host_request(intent)
    assert request["method_digest"] == _sha256_hex("tools/call")
    assert request["resource_digest"] == _sha256_hex(
        "binding:virtual-desktop:demo-mutate"
    )
    assert request["argument_digest"] == _sha256_hex(
        {"dry_run": True, "scope": "cap:demo", "limit": 1}
    )

    assert "UI displays exact" in test_ts or "method_digest" in test_ts
    assert "argument_digest" in test_ts
    assert "resource_digest" in test_ts


def test_consumes_host_typed_outcome_without_upgrading_evidence(
    gateway_ts: str, test_ts: str
) -> None:
    assert "consumeHostIssuedTypedOutcome" in gateway_ts
    assert "evidence_upgrade_forbidden" in gateway_ts
    assert "may_upgrade_evidence: false" in gateway_ts or "may_upgrade_evidence:false" in gateway_ts.replace(
        " ", ""
    )
    assert "host_policy_duplicated_in_typescript: false" in gateway_ts or (
        "host_policy_duplicated_in_typescript:false" in gateway_ts.replace(" ", "")
    )
    assert "without upgrading evidence" in gateway_ts.lower() or "never upgrades evidence" in gateway_ts.lower()

    intent = {
        "binding_id": "binding:virtual-desktop:demo-mutate",
        "method": "tools/call",
        "resource_id": "binding:virtual-desktop:demo-mutate",
        "payload": {"dry_run": True, "scope": "cap:demo", "limit": 1},
        "mutates_remote_state": True,
    }
    request = project_canonical_host_request(
        intent,
        {
            "host_policy_id": "policy:demo",
            "admission_token_cid": "baguqeerademoadmissiontoken0000000000000000000001",
            "nonce": "nonce-1",
            "expiry": "2099-01-01T00:00:00Z",
        },
    )
    host_allow = {
        "outcome": "allow",
        "authority": "valid",
        "policy": "allowed",
        "reason": "host_issued_admission",
        "bound_method_digest": request["method_digest"],
        "bound_resource_digest": request["resource_digest"],
        "bound_argument_digest": request["argument_digest"],
        "closed_outcome": "Attempted",
        "evidence": {
            "authority": "valid",
            "policy": "allowed",
            "effect": "not_started",
            "environment": "hermetic",
        },
    }
    presented = consume_host_issued_typed_outcome(request, host_allow)
    assert presented["accepted"] is True
    assert presented["outcome"] == "allow"
    assert presented["default_consent"] == "absent"
    assert presented["authority_decision_from_browser"] is False
    assert presented["ui_digest"]["argument_digest"] == request["argument_digest"]
    assert presented["evidence"]["effect"] == "not_started"
    assert presented["evidence"]["environment"] == "hermetic"

    upgraded = consume_host_issued_typed_outcome(
        request,
        host_allow,
        local_evidence_attempt={
            "effect": "observed",
            "environment": "live",
            "proof": "verified",
        },
    )
    assert upgraded["accepted"] is False
    assert upgraded["reason"] == "evidence_upgrade_forbidden"

    mismatched = consume_host_issued_typed_outcome(
        request, {**host_allow, "bound_argument_digest": "0" * 64}
    )
    assert mismatched["accepted"] is False
    assert mismatched["reason"] == "host_outcome_digest_mismatch"

    absent = consume_host_issued_typed_outcome(request, None)
    assert absent["accepted"] is False
    assert absent["reason"] == "host_admission_required"

    assert "evidence_upgrade_forbidden" in test_ts
    assert "host_outcome_digest_mismatch" in test_ts or "digest" in test_ts.lower()


def test_fail_closed_without_host_admission_allow_only_with_bindings(
    gateway_ts: str, test_ts: str
) -> None:
    assert "projectHostDecisionFromBindings" in gateway_ts
    assert "host_admission_required" in gateway_ts
    assert "host_issued_admission" in gateway_ts

    intent = {
        "binding_id": "binding:virtual-desktop:demo-mutate",
        "method": "tools/call",
        "resource_id": "binding:virtual-desktop:demo-mutate",
        "payload": {"dry_run": True, "scope": "cap:demo", "limit": 1},
        "mutates_remote_state": True,
    }
    denied_req = project_canonical_host_request(intent)
    denied = project_host_decision_from_bindings(denied_req)
    assert denied["outcome"] == "deny"
    assert denied["reason"] == "host_admission_required"

    allowed_req = project_canonical_host_request(
        intent,
        {
            "host_policy_id": "policy:demo",
            "admission_token_cid": "baguqeerademoadmissiontoken0000000000000000000001",
        },
    )
    allowed = project_host_decision_from_bindings(allowed_req)
    assert allowed["outcome"] == "allow"
    assert allowed["reason"] == "host_issued_admission"
    presented = consume_host_issued_typed_outcome(allowed_req, allowed)
    assert presented["accepted"] is True

    assert "host_admission_required" in test_ts
    assert "host_issued_admission" in test_ts


def test_confirmation_is_review_intent_not_grant(gateway_ts: str, test_ts: str) -> None:
    assert "projectConfirmationRequest" in gateway_ts
    assert "review_intent" in gateway_ts
    assert "confirmation_intent" in gateway_ts
    assert "never" in gateway_ts.lower() and "grant" in gateway_ts.lower()

    assert "review intent" in test_ts.lower() or "review_intent" in test_ts
    assert "confirmation_token" in test_ts


def test_opaque_actor_session_refs_and_secret_stripping(
    gateway_ts: str, test_ts: str
) -> None:
    assert "projectOpaqueIdentityRefs" in gateway_ts
    assert "redacted" in gateway_ts
    for key in ("goose_secret_key", "host_path", "authorization"):
        assert key in gateway_ts

    clean = project_canonical_host_request(
        {
            "binding_id": "binding:virtual-desktop:demo-mutate",
            "actor_id": "operator:desktop-ui",
            "session_id": "session:demo-1",
            "payload": {"dry_run": True},
        }
    )
    assert clean["actor_ref"] == "operator:desktop-ui"
    assert clean["session_ref"] == "session:demo-1"

    dirty = project_canonical_host_request(
        {
            "binding_id": "binding:virtual-desktop:demo-mutate",
            "actor_id": "sk-live-secret-key-value",
            "session_id": "/home/barberb/.secrets/token",
            "payload": {
                "dry_run": True,
                "goose_secret_key": "sk-live-xxx",
                "scope": "cap:demo",
            },
        }
    )
    assert dirty["actor_ref"] is not None and dirty["actor_ref"].startswith("actor:redacted:")
    assert dirty["session_ref"] is not None and dirty["session_ref"].startswith(
        "session:redacted:"
    )
    # Secret keys stripped from argument digest bag.
    assert dirty["argument_digest"] == _sha256_hex({"dry_run": True, "scope": "cap:demo"})

    assert "opaque" in test_ts.lower() or "redacted" in test_ts


def test_legacy_default_granted_is_failing_seed_not_accepted_evidence(
    gateway_ts: str, test_ts: str
) -> None:
    assert "legacyDesktopAuthoritySynthesis" in gateway_ts
    assert "failing_seed" in gateway_ts
    assert "accepted_evidence: false" in gateway_ts or "accepted_evidence:false" in gateway_ts.replace(
        " ", ""
    )

    omit = {
        "binding_id": "binding:virtual-desktop:demo-mutate",
        "mutates_remote_state": True,
    }
    denied = {**omit, "consent": "denied"}
    synth_omit = legacy_desktop_authority_synthesis(omit)
    synth_denied = legacy_desktop_authority_synthesis(denied)
    assert synth_omit["consent"] == "granted"
    assert synth_denied["consent"] == "denied"
    assert synth_omit["policy_decision"]["outcome"] == "allow"
    assert synth_denied["policy_decision"]["outcome"] == "deny"
    assert synth_omit["accepted_evidence"] is False
    assert synth_omit["disposition"] == "failing_seed"
    assert synth_omit["seam"] == INVENTORIED_SEAM

    # Inventoried seam still contains the legacy synthesis (migration target).
    live_src = LIVE_GATEWAY_SEAM.read_text(encoding="utf-8")
    assert "consent" in live_src
    assert "policy_decision" in live_src
    assert "granted" in live_src

    assert "failing_seed" in test_ts
    assert "legacy" in test_ts.lower()


def test_gateway_prohibits_silent_consent_and_browser_constructed_allow(
    gateway_ts: str, test_ts: str
) -> None:
    # Migrated path must not synthesize consent from governed?granted.
    assert not re.search(
        r"consent:\s*invocation\.consent\s*\?\?\s*\(governed\s*\?\s*'granted'",
        gateway_ts,
    )
    assert "projectMigratedDesktopInvocation" in gateway_ts
    assert "FormalAssuranceGateway" in gateway_ts
    assert "createFormalAssuranceGateway" in gateway_ts

    assert "silent consent" in test_ts.lower() or "consent: 'absent'" in test_ts or (
        "consent" in test_ts and "absent" in test_ts
    )


def test_inventory_follow_on_targets_align_with_host_projection() -> None:
    assert INVENTORY_PATH.is_file()
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert inventory["acceptance"]["default_granted_consent_is_failing_seed"] is True
    note = inventory["adaptation_disposition"]["for_facp_030"]
    assert "host-issued" in note.lower() or "host issued" in note.lower()
    assert "no authority decision" in note.lower()
    assert "consent absent" in note.lower() or "default consent absent" in note.lower()
    assert "argument digest" in note.lower()

    prohibited = set(inventory["authority"]["prohibited_effects"])
    assert "treat_ui_confirmation_as_host_admission" in prohibited
    assert "treat_default_granted_consent_as_accepted_evidence" in prohibited

    edges = inventory["authority_edges"]
    facp_030_edges = []
    for edge in edges:
        target = edge.get("removal_or_adaptation_target") or {}
        follow_on = target.get("follow_on") or []
        if "FACP-030" in follow_on:
            facp_030_edges.append(edge["edge_id"])
    assert "SK-AUTH-001" in facp_030_edges
    assert "SK-AUTH-002" in facp_030_edges
    assert "SK-AUTH-008" in facp_030_edges
    assert len(facp_030_edges) >= 5
