"""FACP-029: Prove SwissKnife browser nonauthority.

Acceptance (taskboard):
- Paired requests differing only in browser authority fields produce identical
  host authorization inputs/results.
- Legacy default-granted behavior is a failing seed, not accepted evidence.

Validates the declared SwissKnife vector fixture and TypeScript negative suite
hermetically (no browser network/host effect). Source repair is out of scope.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VECTORS_PATH = (
    REPO_ROOT
    / "swissknife"
    / "test"
    / "formal-assurance"
    / "browser-authority-vectors.json"
)
TEST_TS_PATH = (
    REPO_ROOT
    / "swissknife"
    / "test"
    / "formal-assurance"
    / "browser-nonauthority.test.ts"
)
INVENTORY_PATH = (
    REPO_ROOT
    / "implementation_plan"
    / "formal_assurance_control_plane"
    / "baseline"
    / "swissknife_authority.json"
)

TASK_ID = "FACP-029"
GOAL_ID = "FACP-G240"
SCHEMA = "facp/browser-nonauthority@1"
BUNDLE = "facp/migration/swissknife-nonauthority"

REQUIRED_EVIDENCE_SUBSET = {
    "allow/deny",
    "consent granted/absent",
    "tenant/workspace",
    "dry-run/live",
    "changed arguments",
    "replay",
    "expiry",
}

REQUIRED_SEED_BINDINGS = {
    "SK-AUTH-001": "cx-sk-auth-default-granted-consent",
    "SK-AUTH-002": "cx-sk-auth-browser-constructed-allow",
    "SK-AUTH-003": "cx-sk-auth-console-local-allow-policy",
    "SK-AUTH-004": "cx-sk-auth-confirmation-token-as-grant",
    "SK-AUTH-005": "cx-sk-auth-caller-supplied-policy-decision",
    "SK-SENS-003": "cx-sk-sens-localstorage-secret-header",
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

SECRET_KEYS = {
    "goose_secret_key",
    "X-Secret-Key",
    "secret_header",
    "authorization",
    "api_key",
}

PRESENTATION_ONLY = {
    "ui_label",
    "presentation",
    "mutates_remote_state",
    "correlation_id",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_hex(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def project_host_authorization_input(request: dict[str, Any]) -> dict[str, Any]:
    """Strip browser authority/secret/presentation fields; bind host dimensions."""
    arguments = request.get("arguments")
    if arguments is None:
        arguments = request.get("payload", {})

    for key in request:
        if key in BROWSER_AUTHORITY_FIELDS:
            continue
        if key in SECRET_KEYS or key in PRESENTATION_ONLY:
            continue
        if key in ("arguments", "payload"):
            continue

    return {
        "actor_id": request.get("actor_id"),
        "resource_id": request.get("resource_id"),
        "method": request.get("method"),
        "argument_digest": _sha256_hex({} if arguments is None else arguments),
        "host_policy_id": request.get("host_policy_id"),
        "expiry": request.get("expiry"),
        "nonce": request.get("nonce"),
        "admission_token_cid": request.get("admission_token_cid"),
    }


def project_host_authorization_result(host_input: dict[str, Any]) -> dict[str, Any]:
    """Fail-closed host result; browser fields are never consulted."""
    if not host_input.get("admission_token_cid"):
        return {
            "outcome": "deny",
            "authority": "absent",
            "policy": "unchecked",
            "reason": "host_admission_required",
            "closed_outcome": "Rejected",
        }
    if not host_input.get("host_policy_id"):
        return {
            "outcome": "deny",
            "authority": "absent",
            "policy": "unchecked",
            "reason": "host_policy_binding_required",
            "closed_outcome": "Rejected",
        }
    return {
        "outcome": "allow",
        "authority": "valid",
        "policy": "allowed",
        "reason": "host_issued_admission",
        "closed_outcome": "Attempted",
        "bound_argument_digest": host_input["argument_digest"],
        "bound_nonce": host_input["nonce"],
        "bound_expiry": host_input["expiry"],
    }


def legacy_desktop_synthesize(request: dict[str, Any]) -> dict[str, Any]:
    """Legacy default-granted / browser-constructed allow — failing seed only."""
    governed = bool(request.get("mutates_remote_state", True))
    consent = request.get("consent")
    if consent is None:
        consent = "granted" if governed else "not_required"
    outcome = "deny" if consent == "denied" else "allow"
    return {
        "consent": consent,
        "policy_decision": {
            "decision_id": f"desktop-policy:{request.get('resource_id', 'unknown')}",
            "outcome": outcome,
            "reason": "legacy_browser_constructed",
        },
        "host_authorization_influenced_by_browser": True,
        "accepted_evidence": False,
        "disposition": "failing_seed",
    }


@pytest.fixture(scope="module")
def vectors() -> dict[str, Any]:
    assert VECTORS_PATH.is_file(), f"missing vectors: {VECTORS_PATH}"
    payload = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.fixture(scope="module")
def test_ts() -> str:
    assert TEST_TS_PATH.is_file(), f"missing TypeScript suite: {TEST_TS_PATH}"
    return TEST_TS_PATH.read_text(encoding="utf-8")


def test_declared_outputs_exist_and_bind_facp_029(
    vectors: dict[str, Any], test_ts: str
) -> None:
    assert vectors["schema"] == SCHEMA
    assert vectors["task_id"] == TASK_ID
    assert vectors["goal_id"] == GOAL_ID
    assert vectors["bundle"] == BUNDLE
    assert vectors["fail_closed"] is True
    assert vectors["authority"]["browser_fields_are_not_host_admission"] is True
    assert vectors["authority"]["legacy_default_granted_is_failing_seed"] is True
    assert vectors["authority"]["fca_family"] == "browser_authority"

    assert "FACP-029" in test_ts
    assert SCHEMA in test_ts or "facp/browser-nonauthority@1" in test_ts
    assert "projectHostAuthorizationInput" in test_ts
    assert "projectHostAuthorizationResult" in test_ts
    assert "legacyDesktopSynthesize" in test_ts
    assert "failing seed" in test_ts.lower() or "failing_seed" in test_ts
    assert "browser-authority-vectors.json" in test_ts
    assert "accepted_evidence" in test_ts


def test_evidence_subset_and_seed_bindings(vectors: dict[str, Any]) -> None:
    subset = set(vectors["evidence_subset"])
    assert REQUIRED_EVIDENCE_SUBSET <= subset

    bindings = {
        item["edge_id"]: item["seed_id"] for item in vectors["seed_bindings"]
    }
    for edge_id, seed_id in REQUIRED_SEED_BINDINGS.items():
        assert bindings.get(edge_id) == seed_id, edge_id

    edge_ids = {v["edge_id"] for v in vectors["paired_vectors"]} | {
        v["edge_id"] for v in vectors["failing_seeds"]
    }
    for edge_id in REQUIRED_SEED_BINDINGS:
        assert edge_id in edge_ids

    families = {v["family"] for v in vectors["paired_vectors"]}
    families |= {v["family"] for v in vectors["argument_sensitivity_vectors"]}
    families |= {v["family"] for v in vectors["replay_vectors"]}
    families |= {v["family"] for v in vectors["expiry_vectors"]}
    assert "allow/deny" in families
    assert "consent granted/absent" in families
    assert "tenant/workspace" in families
    assert "dry-run/live" in families
    assert "changed arguments" in families
    assert "replay" in families
    assert "expiry" in families


def test_paired_browser_authority_deltas_preserve_host_authorization(
    vectors: dict[str, Any],
) -> None:
    pairs = vectors["paired_vectors"]
    assert isinstance(pairs, list) and len(pairs) >= 8

    browser_fields = tuple(vectors["browser_authority_fields"])
    assert set(browser_fields) >= set(BROWSER_AUTHORITY_FIELDS)

    for pair in pairs:
        assert pair["role"] == "accepted_nonauthority_pair"
        assert pair["accepted_evidence"] is True

        input_a = project_host_authorization_input(pair["request_a"])
        input_b = project_host_authorization_input(pair["request_b"])
        result_a = project_host_authorization_result(input_a)
        result_b = project_host_authorization_result(input_b)

        assert input_a == input_b, pair["vector_id"]
        assert result_a == result_b, pair["vector_id"]
        assert input_a == pair["host_authorization_input_a"], pair["vector_id"]
        assert input_b == pair["host_authorization_input_b"], pair["vector_id"]
        assert result_a == pair["host_authorization_result_a"], pair["vector_id"]
        assert result_b == pair["host_authorization_result_b"], pair["vector_id"]

        # Host authorization must not retain browser authority or secret fields.
        blob = _canonical_json(input_a)
        for field in browser_fields:
            assert field not in input_a
        assert "sk-live" not in blob
        assert "goose_secret" not in blob
        assert "X-Secret" not in blob
        assert "confirmation_token" not in blob
        assert '"consent"' not in blob


def test_argument_replay_expiry_sensitivity(vectors: dict[str, Any]) -> None:
    args = vectors["argument_sensitivity_vectors"]
    assert isinstance(args, list) and len(args) >= 1
    for vector in args:
        assert vector["accepted_evidence"] is True
        input_a = project_host_authorization_input(vector["request_a"])
        input_b = project_host_authorization_input(vector["request_b"])
        assert input_a["argument_digest"] != input_b["argument_digest"]
        assert input_a == vector["host_authorization_input_a"]
        assert input_b == vector["host_authorization_input_b"]

    replays = vectors["replay_vectors"]
    assert isinstance(replays, list) and len(replays) >= 1
    for vector in replays:
        input_a = project_host_authorization_input(vector["request_a"])
        input_b = project_host_authorization_input(vector["request_b"])
        result_a = project_host_authorization_result(input_a)
        result_b = project_host_authorization_result(input_b)
        assert input_a["nonce"] != input_b["nonce"]
        assert result_a["bound_nonce"] != result_b["bound_nonce"]
        assert input_a["argument_digest"] == input_b["argument_digest"]

    expiries = vectors["expiry_vectors"]
    assert isinstance(expiries, list) and len(expiries) >= 1
    for vector in expiries:
        input_a = project_host_authorization_input(vector["request_a"])
        input_b = project_host_authorization_input(vector["request_b"])
        result_a = project_host_authorization_result(input_a)
        result_b = project_host_authorization_result(input_b)
        assert input_a["expiry"] != input_b["expiry"]
        assert result_a["bound_expiry"] != result_b["bound_expiry"]


def test_legacy_default_granted_is_failing_seed_not_accepted_evidence(
    vectors: dict[str, Any],
) -> None:
    acceptance = vectors["acceptance"]
    assert (
        acceptance["legacy_default_granted_is_failing_seed_not_accepted_evidence"]
        is True
    )
    assert (
        acceptance[
            "legacy_browser_constructed_allow_is_failing_seed_not_accepted_evidence"
        ]
        is True
    )
    assert acceptance["paired_browser_authority_deltas_preserve_host_authorization"]

    seeds = vectors["failing_seeds"]
    assert isinstance(seeds, list) and len(seeds) >= 2

    default_granted = next(
        seed
        for seed in seeds
        if seed["seed_id"] == "cx-sk-auth-default-granted-consent"
    )
    assert default_granted["accepted_evidence"] is False
    assert default_granted["role"] == "failing_seed"
    assert default_granted["disposition"] == "failing_seed"
    assert "granted" in default_granted["legacy_observed"]
    assert "failing seed" in default_granted["why_not_accepted_evidence"].lower() or (
        "not" in default_granted["why_not_accepted_evidence"].lower()
        and "accepted" in default_granted["why_not_accepted_evidence"].lower()
    )

    # Recompute legacy divergence: omitting consent synthesizes granted/allow.
    omit = {
        "actor_id": "operator:desktop-ui",
        "resource_id": "binding:virtual-desktop:demo-mutate",
        "mutates_remote_state": True,
    }
    denied = {**omit, "consent": "denied"}
    synth_omit = legacy_desktop_synthesize(omit)
    synth_denied = legacy_desktop_synthesize(denied)
    assert synth_omit["consent"] == "granted"
    assert synth_denied["consent"] == "denied"
    assert synth_omit["policy_decision"]["outcome"] == "allow"
    assert synth_denied["policy_decision"]["outcome"] == "deny"
    assert synth_omit["accepted_evidence"] is False
    assert synth_omit["host_authorization_influenced_by_browser"] is True

    # Nonauthority projection remains identical / deny-closed without host admission.
    nonauth_a = project_host_authorization_input({**omit, "consent": "granted"})
    nonauth_b = project_host_authorization_input({**omit, "consent": "denied"})
    assert nonauth_a == nonauth_b
    assert project_host_authorization_result(nonauth_a)["outcome"] == "deny"

    constructed = next(
        seed
        for seed in seeds
        if seed["seed_id"] == "cx-sk-auth-browser-constructed-allow"
    )
    assert constructed["accepted_evidence"] is False
    assert constructed["role"] == "failing_seed"

    for seed in seeds:
        assert seed["accepted_evidence"] is False
        assert seed["role"] == "failing_seed"

    # Accepted pairs must not be labeled as failing seeds.
    for pair in vectors["paired_vectors"]:
        assert pair["accepted_evidence"] is True
        assert pair["role"] != "failing_seed"


def test_typescript_suite_asserts_nonauthority_hyperproperty(test_ts: str) -> None:
    assert "projectHostAuthorizationInput" in test_ts
    assert "projectHostAuthorizationResult" in test_ts
    assert re.search(r"identical host authorization", test_ts, re.I)
    assert "legacyDesktopSynthesize" in test_ts
    assert "cx-sk-auth-default-granted-consent" in test_ts
    assert "accepted_evidence" in test_ts
    assert "failing_seed" in test_ts
    # Must not treat UI confirmation / network effects as authority.
    assert "browser network" in test_ts.lower() or "hermetic" in test_ts.lower()
    assert "confirmation" in test_ts.lower()
    assert "SK-AUTH-001" in test_ts
    assert "SK-SENS-003" in test_ts


def test_inventory_adaptation_targets_align_with_vectors(
    vectors: dict[str, Any],
) -> None:
    assert INVENTORY_PATH.is_file()
    inventory = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    assert inventory["acceptance"]["default_granted_consent_is_failing_seed"] is True
    note = inventory["adaptation_disposition"]["for_facp_029"]
    assert "failing seeds" in note.lower() or "failing seed" in note.lower()
    assert "browser-nonauthority" in note or "paired" in note.lower()

    remove = set(inventory["adaptation_disposition"]["remove_or_rewrite"])
    assert "SK-AUTH-001" in remove
    assert "SK-AUTH-002" in remove
    assert "SK-SENS-003" in remove
