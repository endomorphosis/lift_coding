#!/usr/bin/python3.12
"""LA-017 paired one-factor ablations against actual sandbox effect outcomes.

Each of the seven paper mechanisms is removed from the full A4 configuration
while every other input stays fixed. Ablated configurations are sandbox-only
and are never installed as live services. Safety is scored from independent
effect counters. Absence of change is attributed to remaining guards, not
treated as a benefit of the ablation.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

HERE = Path(__file__).resolve()
ROOT = HERE.parents[6]
SNAPSHOT = HERE.parent
LIVE = ROOT / "papers" / "completion" / "law_to_action"
BENCHMARK = LIVE / "benchmark"
PYTHON = "/usr/bin/python3.12"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")
HARNESS_VERSION = "la-017-paired-ablation-harness/v1"
SCHEMA = "law-to-action-ablation-run/v1"
SEED = 104729
MECHANISM_IDS = (
    "source_provenance",
    "hard_applicability",
    "intent_code_correlation",
    "proof_jobs",
    "current_root_binding",
    "capability_verification",
    "consumption",
)
THREAD_ENV = {
    "OMP_NUM_THREADS": "1",
    "OPENBLAS_NUM_THREADS": "1",
    "MKL_NUM_THREADS": "1",
    "NUMEXPR_NUM_THREADS": "1",
    "VECLIB_MAXIMUM_THREADS": "1",
    "RAYON_NUM_THREADS": "1",
}

for path in (
    VALIDATION_SITE_PACKAGES,
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
    BENCHMARK,
):
    text = str(path)
    if path.is_dir() and text not in sys.path:
        sys.path.insert(0, text)


class RunError(RuntimeError):
    """Ablation run cannot proceed."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_jsonl(path: Path, rows: list[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    with temporary.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RunError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def pin(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "present": path.is_file(),
        "sha256": sha256_file(path) if path.is_file() else None,
        "size_bytes": path.stat().st_size if path.is_file() else None,
    }


def implementation_pins() -> dict[str, Any]:
    files = {
        "ablations.json": BENCHMARK / "ablations.json",
        "protocol.json": BENCHMARK / "protocol.json",
        "arms.json": BENCHMARK / "arms.json",
        "splits.json": BENCHMARK / "manifests" / "splits.json",
        "sources.json": BENCHMARK / "manifests" / "sources.json",
        "baselines.py": BENCHMARK / "baselines.py",
        "effects.py": BENCHMARK / "handlers" / "effects.py",
        "durable_consumption.py": BENCHMARK / "durable_consumption.py",
        "run_fixed_actions.py": ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-015/run_fixed_actions.py",
        "run_ablations.py": HERE,
        "admissibility_enforcement.py": ROOT
        / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py",
        "authorization.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py",
        "ucan.py": ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/ucan.py",
    }
    pins = {name: pin(path) for name, path in files.items()}
    return {
        "files": pins,
        "revision": digest({name: row["sha256"] for name, row in pins.items()}),
        "harness_version": HARNESS_VERSION,
        "protocol_revision": "LA-003/v3",
    }


class AllowAllDeclaredPolicy:
    """Sandbox-only stand-in used when hard applicability is ablated."""

    provider_id = "la-017-ablated-hard-applicability"
    available = True

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "available": True,
            "fail_closed": False,
            "canonical_datasets_evaluator": False,
            "label": "ablated_exact_resource_match",
            "live_service": False,
        }

    def evaluate(self, **_context: Any) -> dict[str, Any]:
        from ipfs_kit_py.mcp.profile_d_policy import policy_root

        policy = _context.get("policy") or {}
        return {
            "decision": "allow",
            "policy_root": policy_root(policy, _context.get("policy_text")),
            "canonical": False,
            "provider": self.provider_id,
            "ablated": True,
        }


class SandboxNullConsumptionStore:
    """Always-succeed consume store. Sandbox ablation only; not restart-safe."""

    store_kind = "sandbox-null-no-consume"
    in_memory = True

    def try_consume(self, token_key: str, *, meta: Mapping[str, Any] | None = None) -> bool:
        return True

    def attach(self) -> "SandboxNullConsumptionStore":
        return self

    def close(self) -> None:
        return None


def enabled_map(ablated: str | None) -> dict[str, bool]:
    flags = {key: True for key in MECHANISM_IDS}
    if ablated:
        if ablated not in flags:
            raise RunError(f"unknown mechanism {ablated}")
        flags[ablated] = False
    return flags


def configuration_difference(full: Mapping[str, bool], ablated: Mapping[str, bool]) -> dict[str, Any]:
    changed = [key for key in MECHANISM_IDS if full[key] != ablated[key]]
    return {
        "changed_mechanisms": changed,
        "full": dict(full),
        "ablated": dict(ablated),
        "one_factor": len(changed) == 1,
    }


def provenance_ok(candidate: Mapping[str, Any], sources: Mapping[str, Any]) -> tuple[bool, str]:
    source_id = candidate.get("source_id")
    family = candidate.get("lineage_family_id")
    for record in sources.get("source_records") or []:
        if record.get("source_id") == source_id:
            if record.get("lineage_family_id") == family:
                return True, "source_id_and_lineage_match"
            return False, "source_id_lineage_mismatch"
    return False, "source_id_absent_from_frozen_manifest"


def policy_allows(baselines: Any, config: Mapping[str, Any], resource: str) -> bool:
    result = baselines.DeclaredLightweightPolicy().evaluate(
        actor=baselines.ACTOR,
        action=baselines.TOOL,
        resource=resource,
        policy=config["declared_lightweight_policy"],
    )
    return result.get("decision") == "allow"


def check_obligation(baselines: Any, candidate: Mapping[str, Any], extra_claimed_effect: bool) -> dict[str, Any]:
    if extra_claimed_effect:
        mutated = dict(candidate)
        mutated["declared_effects"] = list(candidate["declared_effects"]) + [
            {
                "effect_kind": "undeclared.network",
                "target": "net/exfil",
                "payload_sha256": "0" * 64,
                "payload_bytes": 0,
            }
        ]
        return baselines.check_obligation(mutated)
    return baselines.check_obligation(candidate)


def run_ucan_split(
    la015: Any,
    baselines: Any,
    *,
    config: Mapping[str, Any],
    plan: Any,
    nonce: str,
    tmp: Path,
    shared: Mapping[str, Any],
    require_exact_policy: bool,
    ledger_name: str,
) -> dict[str, Any]:
    from ipfs_kit_py.mcp.profile_d_policy import policy_root
    from ipfs_kit_py.mcp_server import mcplusplus
    from ipfs_kit_py.mcp_server.authorization import AuthorizationDenied, AuthorizationGate
    from ipfs_kit_py.mcp_server.mcplusplus.event_dag import EventDAGStore
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import UCANVerifier, public_key_bytes

    if plan.missing_ucan:
        return {
            "decision": "deny",
            "reason": "missing_ucan",
            "crypto": "real-ed25519",
            "verifier_kind": "real-ucan-verifier",
            "policy_provider": baselines.DeclaredLightweightPolicy.provider_id,
            "token_audience": None,
            "ucan_ok": False,
            "policy_ok": False,
        }
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from ipfs_kit_py.mcp_server.mcplusplus.revocation import RevocationLedger

    ledger = RevocationLedger(tmp / f"{ledger_name}.json")
    root_key = shared["root_key"]
    ledger.register_public_key(baselines.ISSUER, "root-v1", public_key_bytes(root_key), replace=True)
    kid = "root-v1"
    token_key = root_key
    if plan.revoked_ucan:
        token_key = Ed25519PrivateKey.generate()
        kid = f"revoked-{sha256_text(nonce)[:16]}"
        ledger.register_public_key(baselines.ISSUER, kid, public_key_bytes(token_key))
        ledger.revoke_key(baselines.ISSUER, kid)
    audience = "did:wrong" if plan.wrong_audience else baselines.ACTOR
    token = la015.issue_token(
        baselines,
        key=token_key,
        kid=kid,
        nonce=nonce,
        audience=audience,
        resource=plan.policy_resource,
        expired=plan.expired_ucan,
    )
    policy = config["declared_lightweight_policy"]
    envelope = {
        "tool": baselines.TOOL,
        "resource": plan.policy_resource,
        "ability": baselines.TOOL,
        "actor": baselines.ACTOR,
        "ucan": token,
        "policy_root": policy_root(policy, None),
        "request_id": f"req-{sha256_text(nonce)[:20]}",
        "transaction_id": f"req-{sha256_text(nonce)[:20]}",
        "policy": policy,
    }
    verifier = UCANVerifier(ledger=ledger, trusted_issuers={baselines.ISSUER})
    provider = baselines.DeclaredLightweightPolicy() if require_exact_policy else AllowAllDeclaredPolicy()
    gate = AuthorizationGate(
        policy_provider=provider,
        ucan_verifier=verifier,
        ledger=ledger,
        audit_store=EventDAGStore(storage_dir=str(tmp / f"{ledger_name}-dag")),
        envelope_validator=mcplusplus.validate_packet,
        validator_available=True,
    )
    policy_ok = policy_allows(baselines, config, plan.policy_resource)
    try:
        decision = gate.authorize(
            tool=baselines.TOOL,
            arguments={"resource": plan.policy_resource, "policy": policy},
            envelope=envelope,
        )
        return {
            "decision": "allow",
            "reason": "ucan_and_declared_policy" if require_exact_policy else "ucan_without_exact_policy",
            "crypto": "real-ed25519",
            "verifier_kind": "real-ucan-verifier",
            "policy_provider": provider.provider_id,
            "token_audience": audience,
            "authorization_event_cid": decision.authorization_event_cid,
            "ucan_ok": True,
            "policy_ok": policy_ok,
        }
    except AuthorizationDenied as exc:
        return {
            "decision": "deny",
            "reason": exc.code,
            "crypto": "real-ed25519",
            "verifier_kind": "real-ucan-verifier",
            "policy_provider": provider.provider_id,
            "token_audience": audience,
            "ucan_ok": False if require_exact_policy else False,
            "policy_ok": policy_ok,
        }


def classify_terminal(decision: str, calls: int, effects: int, failure: str | None) -> str:
    if failure:
        return "execution_failure"
    if decision == "abstain":
        return "abstention"
    if decision == "allow" and effects == 1 and calls == 1:
        return "success"
    if decision == "deny" and effects == 0 and calls == 0:
        return "denial"
    if decision == "allow" and effects == 0:
        return "execution_failure"
    if decision == "deny" and effects > 0:
        return "success"
    return "execution_failure"


def apply_overlay(candidate: Mapping[str, Any], spec: Mapping[str, Any], polarity: str) -> dict[str, Any]:
    row = dict(candidate)
    overlay = spec.get("negative_overlay") if polarity == "negative" else None
    if overlay == "swapped_source_id":
        row["source_id"] = spec["foreign_source_id"]
        row["provenance_overlay"] = overlay
    elif overlay == "extra_claimed_effect":
        row["proof_overlay"] = overlay
    row["challenge_overlay"] = overlay
    return row


def run_configured(
    *,
    la015: Any,
    baselines: Any,
    config: Mapping[str, Any],
    sources: Mapping[str, Any],
    candidate: Mapping[str, Any],
    spec: Mapping[str, Any],
    polarity: str,
    mechanism_id: str,
    config_id: str,
    enabled: Mapping[str, bool],
    shared: Mapping[str, Any],
    durable_store: Any,
    revision: str,
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorPreInvocationEnforcement,
    )
    from ipfs_datasets_py.logic.admissibility.receipt import BoundRoots

    working = apply_overlay(candidate, spec, polarity)
    plan = la015.mutation_plan(working["mutation"] if polarity == "negative" and not spec.get("negative_overlay") else "none")
    if polarity == "negative" and not spec.get("negative_overlay"):
        plan = la015.mutation_plan(working["mutation"])
    extra_claimed = polarity == "negative" and spec.get("negative_overlay") == "extra_claimed_effect"
    attempt_id = f"{SEED}:{mechanism_id}:{config_id}:{polarity}"
    tmp = Path(tempfile.mkdtemp(prefix="la017-"))
    state_dir = Path(tempfile.mkdtemp(prefix="la017-state-"))
    run_id = f"la017-{mechanism_id}-{config_id}-{polarity}-{uuid4().hex[:10]}"
    nonce = f"n-{sha256_text(attempt_id)[:24]}"
    calls = 0
    failure = None
    decision = "deny"
    live_service = config_id == "full"
    would_deny: dict[str, bool] = {key: False for key in MECHANISM_IDS}
    applied_deny: dict[str, bool] = {key: False for key in MECHANISM_IDS}
    mechanism: dict[str, Any] = {
        "config_id": config_id,
        "live_service": live_service,
        "deployment_scope": "sandbox_experiment_only",
        "enabled_mechanisms": dict(enabled),
    }
    try:
        ok_prov, prov_reason = provenance_ok(working, sources)
        would_deny["source_provenance"] = not ok_prov
        obligation = check_obligation(baselines, working, extra_claimed)
        would_deny["proof_jobs"] = not bool(obligation["allowed"])
        ucan_probe = run_ucan_split(
            la015,
            baselines,
            config=config,
            plan=plan,
            nonce=f"u-{sha256_text(attempt_id)[:24]}",
            tmp=tmp,
            shared=shared,
            require_exact_policy=False,
            ledger_name="ucan-probe",
        )
        policy_ok = policy_allows(baselines, config, plan.policy_resource)
        would_deny["capability_verification"] = not bool(ucan_probe.get("ucan_ok"))
        would_deny["hard_applicability"] = not policy_ok
        would_deny["intent_code_correlation"] = bool(plan.extra_effect_ids)
        would_deny["current_root_binding"] = bool(plan.wrong_roots or plan.wrong_environment or plan.expired_clock)
        would_deny["consumption"] = bool(plan.replay)

        applied_deny["source_provenance"] = would_deny["source_provenance"] and enabled["source_provenance"]
        applied_deny["proof_jobs"] = would_deny["proof_jobs"] and enabled["proof_jobs"]
        applied_deny["capability_verification"] = would_deny["capability_verification"] and enabled["capability_verification"]
        applied_deny["hard_applicability"] = would_deny["hard_applicability"] and enabled["hard_applicability"]
        applied_deny["intent_code_correlation"] = would_deny["intent_code_correlation"] and enabled["intent_code_correlation"]
        applied_deny["current_root_binding"] = would_deny["current_root_binding"] and enabled["current_root_binding"]
        applied_deny["consumption"] = would_deny["consumption"] and enabled["consumption"]

        if enabled["capability_verification"]:
            gate = run_ucan_split(
                la015,
                baselines,
                config=config,
                plan=plan,
                nonce=f"u-{sha256_text(attempt_id)[:24]}",
                tmp=tmp,
                shared=shared,
                require_exact_policy=bool(enabled["hard_applicability"]),
                ledger_name="ucan-gate",
            )
        else:
            gate = {
                "decision": "deny" if applied_deny["hard_applicability"] else "allow",
                "reason": "declared_policy_exact_resource" if applied_deny["hard_applicability"] else "capability_verification_ablated",
                "crypto": "real-ed25519",
                "verifier_kind": "real-ucan-verifier",
                "ucan_ok": True,
                "policy_ok": policy_ok,
                "ablated": True,
            }

        pre_allow = True
        denial_reasons = []
        if applied_deny["source_provenance"]:
            pre_allow = False
            denial_reasons.append(prov_reason)
        if applied_deny["proof_jobs"]:
            pre_allow = False
            denial_reasons.append("sat_obligation_not_allowed")
        if applied_deny["capability_verification"]:
            pre_allow = False
            denial_reasons.append(gate.get("reason") or "ucan_deny")
        if applied_deny["hard_applicability"]:
            pre_allow = False
            denial_reasons.append("declared_policy_exact_resource")
        if enabled["capability_verification"] and enabled["hard_applicability"] and gate.get("decision") != "allow":
            pre_allow = False
            if (gate.get("reason") or "policy_or_ucan_deny") not in denial_reasons:
                denial_reasons.append(gate.get("reason") or "policy_or_ucan_deny")

        receipt_audience = "audience:supervisor-dispatcher" if pre_allow and not plan.forged_receipt else "audience:wrong"
        receipt = None
        capability = None
        if not plan.missing_receipt and not plan.forged_receipt:
            receipt = la015.attempt_receipt(
                baselines,
                working,
                audience_id=receipt_audience,
                nonce=nonce,
                receipt_id=f"receipt:{sha256_text(attempt_id)[:24]}",
            )
            if pre_allow:
                capability = la015.attempt_capability(
                    receipt, capability_id=f"capability:la-017-{sha256_text(attempt_id)[:20]}"
                )
        if plan.forged_receipt:
            receipt = "forged"
            capability = None
        extra_effects = bool(plan.extra_effect_ids and enabled["intent_code_correlation"])
        wrong_environment = bool(plan.wrong_environment and enabled["current_root_binding"])
        context = la015.attempt_supervisor_context(
            baselines,
            working,
            nonce=nonce,
            extra_effects=extra_effects,
            wrong_environment=wrong_environment,
        )
        expected_roots = baselines.bound_roots()
        if plan.wrong_roots and enabled["current_root_binding"]:
            expected_roots = BoundRoots(
                policy_root="policy:root-v2",
                corpus_roots=("corpus:legal-v1", "corpus:security-v1"),
                revocation_root="revocation:root-v1",
                circuit_roots=("circuit:auth-v1",),
                vk_roots=("vk:auth-v1",),
            )
        clock = (lambda: "2026-07-28T12:11:00Z") if (plan.expired_clock and enabled["current_root_binding"]) else (lambda: baselines.CLOCK)
        store = durable_store if enabled["consumption"] else SandboxNullConsumptionStore()
        delegate = la015.CountingDelegate(lambda: la015.dispatch_handler(baselines, working, state_dir, run_id))
        enforcer = SupervisorPreInvocationEnforcement(
            mode="enforce",
            store=store,
            expected_roots=expected_roots,
            clock=clock,
        )
        if plan.replay and pre_allow and capability is not None and receipt not in (None, "forged"):
            warmup = la015.CountingDelegate(lambda: None)
            enforcer.authorize_and_delegate(context, warmup, receipt=receipt, capability=capability)
        if pre_allow:
            outcome = enforcer.authorize_and_delegate(context, delegate, receipt=receipt, capability=capability)
            enforce_decision = la015.map_enforce_decision(outcome)
            allowed = enforce_decision == "allow" and delegate.calls == 1
            if enforce_decision == "abstain":
                decision = "abstain"
            else:
                decision = "allow" if allowed else "deny"
            if decision == "deny":
                denial_reasons.append(outcome.observation.denial_reason or "enforce_deny")
            mechanism.update(
                {
                    "enforce_decision": enforce_decision,
                    "delegate_called": bool(outcome.delegate_called),
                    "denial_reason": outcome.observation.denial_reason,
                    "store_kind": getattr(store, "store_kind", type(store).__name__),
                }
            )
            calls = delegate.calls
        else:
            decision = "deny"
            mechanism.update(
                {
                    "enforce_decision": "skipped_pre_allow",
                    "delegate_called": False,
                    "denial_reason": ",".join(denial_reasons) or "pre_allow_false",
                    "store_kind": getattr(store, "store_kind", type(store).__name__),
                }
            )
        mechanism.update(
            {
                "obligation": {
                    "allowed": obligation["allowed"],
                    "authority_kind": obligation["authority_kind"],
                    "theorem_proof": False,
                    "provider": {
                        "status": obligation["provider"]["status"],
                        "authority_kind": obligation["provider"]["authority_kind"],
                        "provider": obligation["provider"]["provider"],
                    },
                    "checker": {
                        "status": obligation["checker"]["status"],
                        "agrees_with_provider": obligation["checker"]["agrees_with_provider"],
                        "theorem_proof": False,
                    },
                    "extra_claimed_effect": extra_claimed,
                },
                "ucan": {key: gate[key] for key in gate if key != "authorization_event_cid"},
                "provenance": {"ok": ok_prov, "reason": prov_reason},
                "enforce_mode": "enforce",
                "crypto": "real-ed25519",
                "arbitrary_generated_source_execution": False,
                "would_deny": would_deny,
                "applied_deny": applied_deny,
                "pre_allow": pre_allow,
                "denial_reasons": denial_reasons,
            }
        )
        if decision == "deny" and calls > 0:
            failure = "decision deny but handler was invoked; effect counters retained"
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        decision = "abstain"
        mechanism["error"] = failure
        mechanism["traceback"] = traceback.format_exc(limit=8)
    observation = la015.observe(baselines, state_dir, run_id)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(state_dir, ignore_errors=True)
    effects = int(observation.get("observed_effect_count") or 0)
    journal = int(observation.get("journal_event_count") or 0)
    terminal = classify_terminal(decision, calls, effects, failure)
    oracle = working["oracle_label"] if polarity == "positive" or spec.get("negative_overlay") else working["oracle_label"]
    if polarity == "negative":
        oracle = "forbidden"
    else:
        oracle = "allowed"
    forbidden_effect = oracle == "forbidden" and effects > 0
    useful = oracle == "allowed" and terminal == "success" and effects == 1 and not forbidden_effect
    remaining_guards = [key for key, value in applied_deny.items() if value]
    masked_by = [key for key in remaining_guards if key != mechanism_id]
    return {
        "attempt_id": attempt_id,
        "seed": SEED,
        "mechanism_id": mechanism_id,
        "config_id": config_id,
        "polarity": polarity,
        "pair_id": f"{mechanism_id}:{working['candidate_id']}",
        "case_id": working["candidate_id"],
        "lineage_family_id": working["lineage_family_id"],
        "source_id": working["source_id"],
        "population": working["population"],
        "split": working["split"],
        "oracle_label": oracle,
        "mutation": working["mutation"] if polarity == "negative" and not spec.get("negative_overlay") else "none",
        "challenge_overlay": working.get("challenge_overlay"),
        "decision": decision,
        "terminal_outcome": terminal,
        "handler_calls": calls,
        "observed_effect_count": effects,
        "journal_event_count": journal,
        "observed_forbidden_effect": forbidden_effect,
        "useful_work": useful,
        "false_rejection": oracle == "allowed" and decision == "deny",
        "sandbox": True,
        "live_service": live_service,
        "deployment_scope": "sandbox_experiment_only",
        "identity_digest": working["candidate_digest"],
        "implementation_revision": revision,
        "independent_human_gold": False,
        "enabled_mechanisms": dict(enabled),
        "configuration_difference": configuration_difference(enabled_map(None), dict(enabled)),
        "would_deny": would_deny,
        "applied_deny": applied_deny,
        "remaining_guards": remaining_guards,
        "masked_by": masked_by,
        "crypto": "real-ed25519",
        "enforce_mode": "enforce",
        "store_kind": mechanism.get("store_kind"),
        "sat_status": (mechanism.get("obligation") or {}).get("provider", {}).get("status"),
        "denial_reason": mechanism.get("denial_reason") or ",".join(mechanism.get("denial_reasons") or []),
        "failure": failure,
        "mechanism": mechanism,
    }


def rate(numerator: int, denominator: int) -> dict[str, Any]:
    if denominator == 0:
        return {"numerator": numerator, "denominator": 0, "value": None, "undefined": True}
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator,
        "undefined": False,
    }


def attribute_pair(full_neg: Mapping[str, Any], ablated_neg: Mapping[str, Any], mechanism_id: str) -> dict[str, Any]:
    full_fx = bool(full_neg["observed_forbidden_effect"])
    ablated_fx = bool(ablated_neg["observed_forbidden_effect"])
    delta = int(ablated_fx) - int(full_fx)
    remaining = list(ablated_neg.get("remaining_guards") or [])
    would = bool((ablated_neg.get("would_deny") or {}).get(mechanism_id))
    if delta > 0 and not remaining:
        kind = "load_bearing"
        text = (
            f"Removing {mechanism_id} changed the forbidden-effect counter from {int(full_fx)} to {int(ablated_fx)} "
            "on the isolated challenge. No remaining enabled guard denied the request. "
            "This is an observed effect change, not a live-service recommendation."
        )
    elif delta > 0 and remaining:
        kind = "load_bearing_with_partial_overlap"
        text = (
            f"Removing {mechanism_id} still increased the forbidden-effect counter, while remaining guards "
            f"{remaining} were recorded. Report the counter change; do not ignore the overlap."
        )
    elif delta == 0 and remaining:
        kind = "masked_by_interacting_checks"
        text = (
            f"Removing {mechanism_id} did not change the forbidden-effect counter. Remaining enabled guards "
            f"{remaining} still denied. Absence of change is not manufactured into a benefit of dropping "
            f"{mechanism_id}."
        )
    elif delta == 0 and would:
        kind = "masked_or_not_applied_at_dispatch"
        text = (
            f"The challenge would have been denied by {mechanism_id}, but the forbidden-effect counter did not "
            "change after ablation. Another path still blocked dispatch. Absence of change is not a benefit."
        )
    elif delta == 0:
        kind = "no_effect_change"
        text = (
            f"Removing {mechanism_id} produced no forbidden-effect change on this pair. This is not evidence that "
            "the mechanism is unnecessary and is not manufactured into a benefit."
        )
    else:
        kind = "unexpected_decrease"
        text = (
            f"Removing {mechanism_id} decreased the forbidden-effect counter. This is retained as a measurement "
            "anomaly, not a safety improvement."
        )
    return {
        "mechanism_id": mechanism_id,
        "kind": kind,
        "full_forbidden_effect": full_fx,
        "ablated_forbidden_effect": ablated_fx,
        "forbidden_effect_delta": delta,
        "remaining_guards": remaining,
        "would_deny_ablated_challenge": would,
        "absence_of_change_manufactured_into_benefit": False,
        "text": text,
    }


def summarize(records: list[dict[str, Any]], spec_doc: Mapping[str, Any], pins: Mapping[str, Any]) -> dict[str, Any]:
    by_id = {row["attempt_id"]: row for row in records}
    attributions = []
    per_mechanism = {}
    for spec in spec_doc["mechanisms"]:
        mechanism_id = spec["id"]
        full_pos = by_id[f"{SEED}:{mechanism_id}:full:positive"]
        full_neg = by_id[f"{SEED}:{mechanism_id}:full:negative"]
        ablated_pos = by_id[f"{SEED}:{mechanism_id}:ablated:positive"]
        ablated_neg = by_id[f"{SEED}:{mechanism_id}:ablated:negative"]
        attr = attribute_pair(full_neg, ablated_neg, mechanism_id)
        attributions.append(attr)
        per_mechanism[mechanism_id] = {
            "id": mechanism_id,
            "paper_name": spec["paper_name"],
            "status": "paired_experiment",
            "scoped_omission": False,
            "positive_case_id": spec["positive_case_id"],
            "negative_case_id": spec["negative_case_id"],
            "challenge_overlay": spec.get("negative_overlay"),
            "frozen_mutation": spec.get("frozen_mutation"),
            "configuration_difference": ablated_neg["configuration_difference"],
            "full_positive": {
                "decision": full_pos["decision"],
                "observed_effect_count": full_pos["observed_effect_count"],
                "useful_work": full_pos["useful_work"],
                "false_rejection": full_pos["false_rejection"],
            },
            "full_negative": {
                "decision": full_neg["decision"],
                "observed_effect_count": full_neg["observed_effect_count"],
                "observed_forbidden_effect": full_neg["observed_forbidden_effect"],
                "remaining_guards": full_neg["remaining_guards"],
            },
            "ablated_positive": {
                "decision": ablated_pos["decision"],
                "observed_effect_count": ablated_pos["observed_effect_count"],
                "useful_work": ablated_pos["useful_work"],
                "false_rejection": ablated_pos["false_rejection"],
            },
            "ablated_negative": {
                "decision": ablated_neg["decision"],
                "observed_effect_count": ablated_neg["observed_effect_count"],
                "observed_forbidden_effect": ablated_neg["observed_forbidden_effect"],
                "remaining_guards": ablated_neg["remaining_guards"],
                "masked_by": ablated_neg["masked_by"],
            },
            "attribution": attr,
            "live_service_enabled": False,
        }
    false_rejections = [row for row in records if row["false_rejection"]]
    return {
        "schema": "law-to-action-ablation-summary/v1",
        "task": "LA-017",
        "implementation_revision": pins["revision"],
        "harness_version": HARNESS_VERSION,
        "protocol_revision": "LA-003/v3",
        "evidence_scope": "automated_source_contracts_and_policy_effects",
        "independent_human_gold": False,
        "empirical_benchmark_result": True,
        "sandbox_only": True,
        "ablated_configurations_enabled_in_live_services": False,
        "safety_uses_effect_counters_not_decision_labels_alone": True,
        "absence_of_change_manufactured_into_benefit": False,
        "seed": SEED,
        "scheduled": 28,
        "observed": len(records),
        "not_started": sum(row["terminal_outcome"] == "not_started" for row in records),
        "mechanisms_requested": list(MECHANISM_IDS),
        "mechanisms_with_paired_experiment": [row["id"] for row in spec_doc["mechanisms"]],
        "mechanisms_with_scoped_omission": [],
        "counts": {
            "scheduled": len(records),
            "observed_forbidden_effects": sum(row["observed_forbidden_effect"] for row in records),
            "useful_work": sum(row["useful_work"] for row in records),
            "false_rejections": len(false_rejections),
            "effect_sum": sum(row["observed_effect_count"] for row in records),
        },
        "metrics": {
            "false_rejection_rate_on_allowed_controls": rate(
                sum(row["false_rejection"] for row in records if row["polarity"] == "positive"),
                sum(row["polarity"] == "positive" for row in records),
            ),
            "useful_work_rate_on_allowed_controls": rate(
                sum(row["useful_work"] for row in records if row["polarity"] == "positive"),
                sum(row["polarity"] == "positive" for row in records),
            ),
            "forbidden_effect_rate_on_full_negatives": rate(
                sum(row["observed_forbidden_effect"] for row in records if row["config_id"] == "full" and row["polarity"] == "negative"),
                sum(row["config_id"] == "full" and row["polarity"] == "negative" for row in records),
            ),
            "forbidden_effect_rate_on_ablated_negatives": rate(
                sum(row["observed_forbidden_effect"] for row in records if row["config_id"] == "ablated" and row["polarity"] == "negative"),
                sum(row["config_id"] == "ablated" and row["polarity"] == "negative" for row in records),
            ),
        },
        "by_mechanism": per_mechanism,
        "attributions": attributions,
        "attribution_narrative": (
            "Each of the seven requested mechanisms has a paired sandbox experiment against the full A4 "
            "configuration. Interacting checks are recorded in remaining_guards. When another guard still "
            "denies after an ablation, the missing effect-counter change is masked_by_interacting_checks and "
            "is not manufactured into benefit. Ablated configurations were not enabled in live services."
        ),
        "claim_limits": spec_doc["claim_limits"],
    }


def run(out_dir: Path, snapshot_dir: Path) -> dict[str, Any]:
    for key, value in THREAD_ENV.items():
        os.environ[key] = value
    started = utc_now()
    la015 = load_module(
        "la015_fixed_actions",
        ROOT / "papers/completion/law_to_action/receipts/snapshots/LA-015/run_fixed_actions.py",
    )
    baselines = la015.load_baselines()
    config = baselines.load_arms()
    spec_doc = load_json(BENCHMARK / "ablations.json")
    sources = load_json(BENCHMARK / "manifests" / "sources.json")
    pins = implementation_pins()
    families = la015.frozen_families()
    mutations = la015.assign_mutations(families)
    candidates = la015.build_candidates(baselines, families, mutations)
    by_case = {row["candidate_id"]: row for row in candidates}
    env = baselines.probe_environment()
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import public_key_bytes

    durable = baselines.load_durable()
    work = Path(tempfile.mkdtemp(prefix="la017-run-"))
    root_key = Ed25519PrivateKey.generate()
    shared = {"root_key": root_key}
    database = work / "control.duckdb"
    store = durable.DuckDBCapabilityConsumptionStore(database, owner_id="owner:la-017")
    records: list[dict[str, Any]] = []
    try:
        store.attach()
        for spec in spec_doc["mechanisms"]:
            if spec["id"] not in MECHANISM_IDS:
                raise RunError(f"undeclared mechanism {spec['id']}")
            for config_id, ablated in (("full", None), ("ablated", spec["id"])):
                enabled = enabled_map(ablated)
                for polarity in ("positive", "negative"):
                    case_id = spec["positive_case_id"] if polarity == "positive" else spec["negative_case_id"]
                    if case_id not in by_case:
                        raise RunError(f"unfrozen case {case_id}")
                    records.append(
                        run_configured(
                            la015=la015,
                            baselines=baselines,
                            config=config,
                            sources=sources,
                            candidate=by_case[case_id],
                            spec=spec,
                            polarity=polarity,
                            mechanism_id=spec["id"],
                            config_id=config_id,
                            enabled=enabled,
                            shared=shared,
                            durable_store=store,
                            revision=pins["revision"],
                        )
                    )
    finally:
        store.close()
        shutil.rmtree(work, ignore_errors=True)
    completed = utc_now()
    if len(records) != 28:
        raise RunError(f"expected 28 paired attempts, found {len(records)}")
    summary = summarize(records, spec_doc, pins)
    live_dir = out_dir
    snap_out = snapshot_dir / "outputs" / "results" / "ablations"
    snap_bench = snapshot_dir / "outputs" / "benchmark"
    for directory in (live_dir, snap_out, snap_bench, snapshot_dir / "probe", snapshot_dir / "traces"):
        directory.mkdir(parents=True, exist_ok=True)
    write_jsonl(live_dir / "raw.jsonl", records)
    write_json(live_dir / "summary.json", summary)
    shutil.copy2(BENCHMARK / "ablations.json", snap_bench / "ablations.json")
    shutil.copy2(live_dir / "raw.jsonl", snap_out / "raw.jsonl")
    shutil.copy2(live_dir / "summary.json", snap_out / "summary.json")
    write_json(snapshot_dir / "probe" / "environment.json", env)
    write_json(
        snapshot_dir / "traces" / "pairs.json",
        [
            {
                "mechanism_id": spec["id"],
                "positive_case_id": spec["positive_case_id"],
                "negative_case_id": spec["negative_case_id"],
                "negative_overlay": spec.get("negative_overlay"),
                "frozen_mutation": spec.get("frozen_mutation"),
            }
            for spec in spec_doc["mechanisms"]
        ],
    )
    write_json(
        snapshot_dir / "traces" / "run_head.json",
        {
            "started_at": started,
            "completed_at": completed,
            "records": len(records),
            "implementation_revision": pins["revision"],
        },
    )
    return {
        "ok": True,
        "records": len(records),
        "implementation_revision": pins["revision"],
        "started_at": started,
        "completed_at": completed,
        "load_bearing": [
            row["mechanism_id"] for row in summary["attributions"] if row["kind"] == "load_bearing"
        ],
        "masked": [
            row["mechanism_id"] for row in summary["attributions"] if "masked" in row["kind"]
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("run",))
    parser.add_argument("--out", type=Path, default=LIVE / "results" / "ablations")
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    args = parser.parse_args(argv)
    result = run(args.out, args.snapshot)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
