#!/usr/bin/python3.12
"""LA-020 reproducible source-to-effect trace from frozen LA-015 identities.

Replays selected A4 cells with retained intermediate artifacts. Compact LA-015
outcomes remain the scored identities. This is not a closed-loop generated-code
study, not a kernel theorem, and not independent human gold.
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
LA015 = LIVE / "receipts" / "snapshots" / "LA-015"
PYTHON = "/usr/bin/python3.12"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
HARNESS_VERSION = "la-020-worked-trace/v1"
SCHEMA = "law-to-action-worked-source-to-effect-trace/v1"
SEED = 104729
ARM_ID = "A4"
VARIANT_MUTATIONS = (
    "wrong_audience",
    "undeclared_handler_effect",
    "replay",
)
STUB_EVIDENCE_CID = "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"
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


class TraceError(RuntimeError):
    """Worked-trace construction cannot proceed."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    payload = text if text.endswith("\n") else text + "\n"
    temporary.write_text(payload, encoding="utf-8")
    os.replace(temporary, path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TraceError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_la015():
    return load_module("la015_fixed_actions", LA015 / "run_fixed_actions.py")


def jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, bytes):
        return {"encoding": "sha256", "sha256": sha256_bytes(value), "bytes": len(value)}
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if hasattr(value, "to_dict"):
        return jsonable(value.to_dict())
    return str(value)


def compact_obligation(obligation: Mapping[str, Any]) -> dict[str, Any]:
    provider = obligation.get("provider") or {}
    checker = obligation.get("checker") or {}
    return {
        "allowed": bool(obligation.get("allowed")),
        "authority_kind": obligation.get("authority_kind") or "satisfiability",
        "theorem_proof": False,
        "provider": {
            "status": provider.get("status"),
            "authority_kind": provider.get("authority_kind"),
            "provider": provider.get("provider"),
            "algorithm": provider.get("algorithm"),
            "nvars": provider.get("nvars"),
            "nclauses": provider.get("nclauses"),
            "model": provider.get("model"),
        },
        "checker": {
            "status": checker.get("status"),
            "authority_kind": checker.get("authority_kind"),
            "checker": checker.get("checker"),
            "agrees_with_provider": checker.get("agrees_with_provider"),
            "theorem_proof": False,
            "forged_evidence": bool(checker.get("forged_evidence")),
        },
    }


def pin_file(path: Path) -> dict[str, Any]:
    return {
        "path": str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path),
        "present": path.is_file(),
        "sha256": sha256_file(path) if path.is_file() else None,
        "size_bytes": path.stat().st_size if path.is_file() else None,
    }


def source_excerpt(record: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not record:
        return None
    prediction = record.get("prediction") or {}
    linkage = record.get("source_span_linkage") or {}
    schema = record.get("parse_schema_validity") or {}
    compiler = record.get("compiler_checker") or {}
    legal_compiler = ((prediction.get("legal_ir_compiler") if isinstance(prediction, dict) else None) or {})
    typed = compiler.get("typed_compiler") or {}
    cve = record.get("cve_behavior") or {}
    return {
        "case_id": record.get("case_id"),
        "population": record.get("population"),
        "source_id": record.get("source_id"),
        "split": record.get("split"),
        "adapter": record.get("adapter"),
        "status": record.get("status"),
        "mutation_class": record.get("mutation_class"),
        "independent_human_gold": False,
        "span_linkage": {
            "linked": linkage.get("linked"),
            "span_count": linkage.get("span_count"),
            "hash_matches": linkage.get("hash_matches"),
            "hash_mismatches": linkage.get("hash_mismatches"),
            "reconstructed_sha256": linkage.get("reconstructed_sha256"),
            "checker": (linkage.get("checker") or {}).get("id"),
        },
        "schema_valid": schema.get("valid"),
        "prediction_kind": prediction.get("kind"),
        "document_id": prediction.get("document_id") or schema.get("document_id"),
        "document_sha256": prediction.get("document_sha256"),
        "candidate_cid": prediction.get("candidate_cid"),
        "source_record_id": prediction.get("source_record_id"),
        "action_count": prediction.get("action_count"),
        "control_edge_count": prediction.get("control_edge_count"),
        "statement_count": prediction.get("statement_count"),
        "element_count": prediction.get("element_count"),
        "legal_ir_compiler_available": legal_compiler.get("available"),
        "legal_ir_compiler_selected": legal_compiler.get("selected"),
        "typed_compiler_available": typed.get("available"),
        "untrusted_markdown_executed": prediction.get("untrusted_markdown_executed"),
        "cve_polarity_supported": cve.get("polarity_supported_by_contract"),
        "cve_untrusted_source_executed": cve.get("untrusted_source_executed"),
        "cve_transfer_to_export_json": cve.get("transfer_to_export_json"),
        "supported_unsupported_fields": record.get("supported_unsupported_fields"),
        "unmeasured": record.get("unmeasured"),
    }


def source_manifest_excerpt(sources: Mapping[str, Any], source_id: str, family_id: str) -> dict[str, Any]:
    artifacts = {row.get("artifact_id"): row for row in sources.get("source_artifacts") or []}
    record = None
    for row in sources.get("source_records") or sources.get("sources") or []:
        if row.get("source_id") == source_id or row.get("lineage_family_id") == family_id:
            record = row
            break
    if record is None:
        return {"source_id": source_id, "lineage_family_id": family_id, "found": False}
    artifact = artifacts.get(record.get("artifact_id")) or {}
    locator = record.get("source_locator") or {}
    return {
        "found": True,
        "source_id": record.get("source_id"),
        "lineage_family_id": record.get("lineage_family_id"),
        "population": record.get("population"),
        "artifact_id": record.get("artifact_id"),
        "source_record_sha256": record.get("source_record_sha256"),
        "normalized_source_sha256": record.get("normalized_source_sha256"),
        "source_uri": artifact.get("source_uri") or locator.get("source_url"),
        "revision": artifact.get("revision") or locator.get("skill_id") or locator.get("repository"),
        "artifact_sha256": artifact.get("sha256"),
        "redistribution": (artifact.get("redistribution") or {}).get("status"),
        "ipfs_cid_published": False,
        "content_identity": record.get("source_record_sha256") or artifact.get("sha256"),
        "source_locator": {
            key: locator.get(key)
            for key in ("skill_id", "repository", "source_url", "cve_id", "pair_id")
            if locator.get(key)
        },
        "status": record.get("status"),
        "source_to_ir_status": (record.get("source_to_ir") or {}).get("status"),
    }


def traced_run_ucan(
    la015: Any,
    baselines: Any,
    *,
    config: Mapping[str, Any],
    plan: Any,
    nonce: str,
    tmp: Path,
    shared: Mapping[str, Any],
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
            "token_present": False,
            "signature_present": False,
            "fabricated_signature": False,
        }
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from ipfs_kit_py.mcp_server.mcplusplus.revocation import RevocationLedger

    ledger = RevocationLedger(tmp / "ucan-ledger.json")
    root_key = shared["root_key"]
    ledger.register_public_key(baselines.ISSUER, "root-v1", public_key_bytes(root_key))
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
    token_sha = sha256_text(token)
    parts = token.split(".") if isinstance(token, str) else []
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
    gate = AuthorizationGate(
        policy_provider=baselines.DeclaredLightweightPolicy(),
        ucan_verifier=verifier,
        ledger=ledger,
        audit_store=EventDAGStore(storage_dir=str(tmp / "dag")),
        envelope_validator=mcplusplus.validate_packet,
        validator_available=True,
    )
    common = {
        "crypto": "real-ed25519",
        "verifier_kind": "real-ucan-verifier",
        "policy_provider": baselines.DeclaredLightweightPolicy.provider_id,
        "token_audience": audience,
        "token_present": True,
        "token_sha256": token_sha,
        "token_parts": len(parts),
        "signature_present": len(parts) == 3 and all(parts),
        "fabricated_signature": False,
        "issuer": baselines.ISSUER,
        "resource": plan.policy_resource,
        "ability": baselines.TOOL,
        "kid": kid,
    }
    try:
        decision = gate.authorize(
            tool=baselines.TOOL,
            arguments={"resource": plan.policy_resource, "policy": policy},
            envelope=envelope,
        )
        return {
            **common,
            "decision": "allow",
            "reason": "ucan_and_declared_policy",
            "authorization_event_cid": decision.authorization_event_cid,
        }
    except AuthorizationDenied as exc:
        return {**common, "decision": "deny", "reason": exc.code}


def snapshot_cas(store: Any) -> dict[str, Any] | None:
    cas = getattr(store, "last_cas", None)
    if not cas:
        return None
    return jsonable(cas)


def detailed_run_a4(
    la015: Any,
    baselines: Any,
    *,
    slot: Mapping[str, Any],
    candidate: Mapping[str, Any],
    config: Mapping[str, Any],
    plan: Any,
    shared: Mapping[str, Any],
    store: Any,
    work: Path,
) -> dict[str, Any]:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorPreInvocationEnforcement,
    )

    tmp = Path(tempfile.mkdtemp(prefix="la020-a4-", dir=work))
    state_dir = Path(tempfile.mkdtemp(prefix="la020-A4-state-", dir=work))
    run_id = f"la020-A4-{slot['attempt_id'].replace(':', '_')}"
    nonce = la015.attempt_nonce(slot["attempt_id"])
    calls = 0
    failure = None
    decision = "deny"
    observation: dict[str, Any] = {"observed_effect_count": 0, "journal_event_count": 0}
    handler_event = None
    journal_events: list[Any] = []
    obligation = None
    gate = None
    receipt_meta = {"built": False, "kind": "internal_bound_context_receipt"}
    capability_meta = {"built": False}
    warmup_cas = None
    consume_cas = None
    enforce_decision = None
    denial_reason = None
    delegate_called = False
    try:
        obligation = baselines.check_obligation(candidate)
        gate = traced_run_ucan(
            la015,
            baselines,
            config=config,
            plan=plan,
            nonce=f"u-{sha256_text(slot['attempt_id'])[:24]}",
            tmp=tmp,
            shared=shared,
        )
        pre_allow = bool(obligation["allowed"] and gate["decision"] == "allow")
        receipt_audience = "audience:supervisor-dispatcher" if pre_allow and not plan.forged_receipt else "audience:wrong"
        receipt = None
        capability = None
        if not plan.missing_receipt and not plan.forged_receipt:
            receipt = la015.attempt_receipt(
                baselines,
                candidate,
                audience_id=receipt_audience,
                nonce=nonce,
                receipt_id=f"receipt:{sha256_text(slot['attempt_id'])[:24]}",
            )
            receipt_meta = {
                "built": True,
                "kind": "internal_bound_context_receipt",
                "receipt_id": getattr(receipt, "receipt_id", None) or f"receipt:{sha256_text(slot['attempt_id'])[:24]}",
                "audience_id": receipt_audience,
                "nonce": nonce,
                "theorem_proof": False,
                "selected_evidence_cids_are_harness_constants": True,
                "selected_evidence_cids_not_published_proof": True,
                "stub_cid_present_in_harness": STUB_EVIDENCE_CID in str(getattr(receipt, "selected_evidence_cids", ())),
            }
            if pre_allow:
                capability = la015.attempt_capability(
                    receipt, capability_id=f"capability:la-015-{sha256_text(slot['attempt_id'])[:20]}"
                )
                capability_meta = {
                    "built": True,
                    "capability_id": f"capability:la-015-{sha256_text(slot['attempt_id'])[:20]}",
                    "allowed_effects": ["effect:filesystem.export_json"],
                    "require_strict_subset": True,
                }
        if plan.forged_receipt:
            receipt = "forged"
            capability = None
            receipt_meta = {"built": False, "kind": "forged_receipt_sentinel", "forged": True}
        context = la015.attempt_supervisor_context(
            baselines,
            candidate,
            nonce=nonce,
            extra_effects=plan.extra_effect_ids,
            wrong_environment=plan.wrong_environment,
        )
        expected_roots = baselines.bound_roots()
        if plan.wrong_roots:
            from ipfs_datasets_py.logic.admissibility.receipt import BoundRoots

            expected_roots = BoundRoots(
                policy_root="policy:root-v2",
                corpus_roots=("corpus:legal-v1", "corpus:security-v1"),
                revocation_root="revocation:root-v1",
                circuit_roots=("circuit:auth-v1",),
                vk_roots=("vk:auth-v1",),
            )
        clock = (lambda: "2026-07-28T12:11:00Z") if plan.expired_clock else (lambda: baselines.CLOCK)
        delegate = la015.CountingDelegate(lambda: la015.dispatch_handler(baselines, candidate, state_dir, run_id))
        enforcer = SupervisorPreInvocationEnforcement(
            mode="enforce",
            store=store,
            expected_roots=expected_roots,
            clock=clock,
        )
        if plan.replay and pre_allow and capability is not None and receipt not in (None, "forged"):
            warmup = la015.CountingDelegate(lambda: None)
            enforcer.authorize_and_delegate(context, warmup, receipt=receipt, capability=capability)
            warmup_cas = snapshot_cas(store)
        outcome = enforcer.authorize_and_delegate(context, delegate, receipt=receipt, capability=capability)
        consume_cas = snapshot_cas(store)
        enforce_decision = la015.map_enforce_decision(outcome)
        denial_reason = outcome.observation.denial_reason
        delegate_called = bool(outcome.delegate_called)
        allowed = pre_allow and enforce_decision == "allow" and delegate.calls == 1
        if enforce_decision == "abstain":
            decision = "abstain"
        else:
            decision = "allow" if allowed else "deny"
        calls = delegate.calls
        if decision == "deny" and calls > 0:
            failure = "A4 decision deny but handler was invoked; effect counters retained"
        if (state_dir / "effects.jsonl").is_file():
            journal_events = [json.loads(line) for line in (state_dir / "effects.jsonl").read_text().splitlines() if line.strip()]
        exports = list((state_dir / "exports").glob("*.json")) if (state_dir / "exports").is_dir() else []
        if exports:
            handler_event = {
                "path": str(exports[0].relative_to(state_dir)),
                "sha256": sha256_file(exports[0]),
                "bytes": exports[0].stat().st_size,
            }
    except Exception as exc:
        failure = f"{type(exc).__name__}: {exc}"
        decision = "abstain"
    observation = la015.observe(baselines, state_dir, run_id)
    shutil.rmtree(tmp, ignore_errors=True)
    shutil.rmtree(state_dir, ignore_errors=True)
    compact = la015.finish_record(
        slot=slot,
        candidate=candidate,
        arm=next(row for row in config["arms"] if row["id"] == ARM_ID),
        decision=decision,
        calls=calls,
        observation=observation,
        mechanism={
            "obligation": compact_obligation(obligation or {}),
            "ucan": {key: gate[key] for key in (gate or {}) if key != "authorization_event_cid"} if gate else {},
            "enforce_decision": enforce_decision,
            "enforce_mode": "enforce",
            "store_kind": getattr(store, "store_kind", type(store).__name__),
            "in_memory_store": bool(getattr(store, "in_memory", False)),
            "delegate_called": delegate_called,
            "denial_reason": denial_reason,
            "crypto": "real-ed25519",
            "arbitrary_generated_source_execution": False,
        },
        revision="replay",
        scored=False,
        failure=failure,
        identity=la015.identity_view(candidate),
        run_id=run_id,
    )
    return {
        "attempt_id": slot["attempt_id"],
        "run_id": run_id,
        "seed": slot["seed"],
        "arm_id": ARM_ID,
        "case_id": candidate["candidate_id"],
        "lineage_family_id": candidate["lineage_family_id"],
        "source_id": candidate["source_id"],
        "population": candidate["population"],
        "split": candidate["split"],
        "oracle_label": candidate["oracle_label"],
        "mutation": candidate["mutation"],
        "identity": la015.identity_view(candidate),
        "plan": {
            "name": plan.name,
            "wrong_audience": bool(plan.wrong_audience),
            "extra_effect_ids": bool(plan.extra_effect_ids),
            "replay": bool(plan.replay),
            "policy_resource": plan.policy_resource,
        },
        "decision": compact["decision"],
        "terminal_outcome": compact["terminal_outcome"],
        "handler_calls": compact["handler_calls"],
        "observed_effect_count": compact["observed_effect_count"],
        "journal_event_count": compact["journal_event_count"],
        "observed_forbidden_effect": compact["observed_forbidden_effect"],
        "useful_work": compact["useful_work"],
        "failure": failure,
        "sat": compact_obligation(obligation or {}),
        "sat_raw": jsonable(obligation) if obligation else None,
        "ucan": gate,
        "receipt": receipt_meta,
        "capability": capability_meta,
        "enforce": {
            "mode": "enforce",
            "decision": enforce_decision,
            "denial_reason": denial_reason,
            "delegate_called": delegate_called,
            "store_kind": getattr(store, "store_kind", type(store).__name__),
            "in_memory_store": bool(getattr(store, "in_memory", False)),
        },
        "owner": {
            "warmup_cas": warmup_cas,
            "consume_cas": consume_cas,
            "transport": getattr(store, "TRANSPORT", None),
        },
        "handler": {
            "version": "bounded-export-handler/v2",
            "arbitrary_generated_source_execution": False,
            "event": handler_event,
            "journal_events": journal_events,
            "observation": jsonable(observation),
        },
        "compact_replay": compact,
    }


def select_cases(
    families: list[dict[str, Any]],
    mutations: Mapping[str, str],
    source_ir: dict[str, dict[str, Any]],
    la015_by_attempt: Mapping[str, dict[str, Any]],
) -> dict[str, Any]:
    skill_allowed = []
    for family in families:
        case0 = family["planned_case_ids"][0]
        if family["population"] != "skill" or mutations[case0] != "none":
            continue
        attempt_id = f"{SEED}:{ARM_ID}:{case0}"
        row = la015_by_attempt.get(attempt_id)
        ir = source_ir.get(case0) or {}
        schema = (ir.get("parse_schema_validity") or {}).get("valid")
        if row and row.get("useful_work") and row.get("terminal_outcome") == "success":
            skill_allowed.append((1 if schema else 0, case0, family, row, ir))
    if not skill_allowed:
        raise TraceError("no successful A4 skill export cell was found in LA-015 seed 104729")
    skill_allowed.sort(key=lambda item: (-item[0], item[1]))
    _, permitted_id, permitted_family, permitted_row, permitted_ir = skill_allowed[0]

    variants = []
    used_families = {permitted_family["lineage_family_id"]}
    for mutation in VARIANT_MUTATIONS:
        found = None
        for family in families:
            case0, case1 = family["planned_case_ids"]
            if mutations[case1] != mutation:
                continue
            allow_id = f"{SEED}:{ARM_ID}:{case0}"
            deny_id = f"{SEED}:{ARM_ID}:{case1}"
            allow_row = la015_by_attempt.get(allow_id)
            deny_row = la015_by_attempt.get(deny_id)
            if not allow_row or not deny_row:
                continue
            found = {
                "mutation": mutation,
                "family": family,
                "allowed_case_id": case0,
                "forbidden_case_id": case1,
                "allowed_attempt_id": allow_id,
                "forbidden_attempt_id": deny_id,
                "allowed_row": allow_row,
                "forbidden_row": deny_row,
            }
            if family["lineage_family_id"] not in used_families:
                break
        if found is None:
            raise TraceError(f"no matched LA-015 A4 pair for mutation {mutation}")
        used_families.add(found["family"]["lineage_family_id"])
        variants.append(found)
    return {
        "permitted": {
            "case_id": permitted_id,
            "family": permitted_family,
            "attempt_id": f"{SEED}:{ARM_ID}:{permitted_id}",
            "row": permitted_row,
            "source_ir": permitted_ir,
        },
        "variants": variants,
    }


def evidence_ref(*parts: str) -> str:
    return str(Path("papers/completion/law_to_action/receipts/snapshots/LA-020").joinpath(*parts))


def step_record(
    *,
    number: int,
    name: str,
    status: str,
    summary: str,
    attempt_id: str,
    case_id: str,
    evidence: list[dict[str, Any]],
    notes: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "step": number,
        "name": name,
        "status": status,
        "summary": summary,
        "attempt_id": attempt_id,
        "case_id": case_id,
        "run_identity": {"source_run": "LA-015", "seed": SEED, "arm_id": ARM_ID, "attempt_id": attempt_id},
        "evidence": evidence,
        "notes": notes or [],
    }


def build_steps(
    permitted: Mapping[str, Any],
    detailed: Mapping[str, Any],
    source: Mapping[str, Any] | None,
    manifest: Mapping[str, Any],
    la015_row: Mapping[str, Any],
) -> list[dict[str, Any]]:
    attempt_id = permitted["attempt_id"]
    case_id = permitted["case_id"]
    sat = detailed.get("sat") or {}
    ucan = detailed.get("ucan") or {}
    enforce = detailed.get("enforce") or {}
    owner = detailed.get("owner") or {}
    handler = detailed.get("handler") or {}
    ir_path = evidence_ref("evidence", "source_ir_selected.json")
    man_path = evidence_ref("evidence", "source_manifest_selected.json")
    det_path = evidence_ref("traces", "attempts", f"{attempt_id.replace(':', '_')}.json")
    la_path = evidence_ref("evidence", "la015_selected.json")
    ident = detailed["identity"]
    compiler_ran = bool((source or {}).get("adapter"))
    legal_compiler = (source or {}).get("legal_ir_compiler_available")
    typed_compiler = (source or {}).get("typed_compiler_available")
    cid = (source or {}).get("candidate_cid") or (source or {}).get("source_record_id")
    return [
        step_record(
            number=1,
            name="Resolve source and declaration manifests by exact revision/CID",
            status="ran",
            summary=(
                f"Frozen source_id {manifest.get('source_id')} with content identity "
                f"{manifest.get('content_identity')}; IPFS publication was not performed."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[
                {"path": man_path, "field": "content_identity"},
                {"path": la_path, "field": attempt_id},
            ],
            notes=[
                "No source body CID was published for this paper artifact.",
                "SHA-256 content identity is the retained pin.",
            ],
        ),
        step_record(
            number=2,
            name="Import skill procedure as data; derive or validate IntentIR",
            status="ran" if (source or {}).get("population") == "skill" and compiler_ran else "partial",
            summary=(
                f"SkillCenter normalizer produced { (source or {}).get('prediction_kind') } "
                f"document_id={(source or {}).get('document_id')} schema_valid={(source or {}).get('schema_valid')}. "
                f"Typed compiler available={typed_compiler}."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": ir_path, "field": "document_id"}, {"path": det_path, "field": "source_ir"}],
            notes=["Untrusted Markdown was not executed.", "Typed Intent compiler remains unavailable."],
        ),
        step_record(
            number=3,
            name="Select applicable LegalIR and reviewed SecurityIR constraints",
            status="partial",
            summary=(
                "LegalIRCompilerAPI was not the selected adapter. Independent human legal/security "
                "review was not used. Machine-contract span linkage ran."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": ir_path, "field": "legal_ir_compiler_available"}, {"path": ir_path, "field": "span_linkage"}],
            notes=[
                f"legal_ir_compiler_available={legal_compiler}",
                "Expert legal fidelity remains unmeasured.",
            ],
        ),
        step_record(
            number=4,
            name="Bind actual requested tool, arguments, actor and expected effects",
            status="ran",
            summary=(
                f"Bound actor={ident['actor']} tool=export_json path={ident['arguments']['path']} "
                f"candidate_digest={ident['candidate_digest'][:16]}."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": det_path, "field": "identity"}, {"path": la_path, "field": "identity_digest"}],
        ),
        step_record(
            number=5,
            name="Correlate intent-side effects with code/handler-side observations",
            status="partial",
            summary=(
                "The handler accepts a declarative export_json instruction, not generated source. "
                "LA-016 produced 0 generated programs. Declared filesystem.export_json effects were "
                "compared with the independent journal observer."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[
                {"path": det_path, "field": "identity.declared_effects"},
                {"path": det_path, "field": "handler.observation"},
            ],
            notes=[
                "Independent generated-code AST analysis did not run.",
                "No model-generated program exists for this identity.",
            ],
        ),
        step_record(
            number=6,
            name="Compose and execute the required formal jobs; retain non-successes",
            status="ran",
            summary=(
                f"QF_BOOL SAT provider={ (sat.get('provider') or {}).get('status') } "
                f"checker agrees={(sat.get('checker') or {}).get('agrees_with_provider')}. "
                "Authority is satisfiability, not theorem_proof."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": det_path, "field": "sat"}, {"path": det_path, "field": "sat_raw"}],
            notes=["SAT/UNSAT cannot authorize theorem_proof allows."],
        ),
        step_record(
            number=7,
            name="Produce an exact-context decision, not an effect",
            status="ran",
            summary=(
                "An internal BoundContext decision receipt and capability were derived for the "
                "exact actor/tool/args digest. Harness selected_evidence_cids are constants, not a published proof."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": det_path, "field": "receipt"}, {"path": det_path, "field": "capability"}],
            notes=[
                "Do not treat the harness stub CID as a proof receipt.",
                f"stub_cid_labeled_not_proof={STUB_EVIDENCE_CID}",
            ],
        ),
        step_record(
            number=8,
            name="Check signed delegation and host-controlled current policy/state",
            status="ran",
            summary=(
                f"Real Ed25519 UCAN verifier decision={ucan.get('decision')} "
                f"token_sha256={(ucan.get('token_sha256') or '')[:16]} "
                f"signature_present={ucan.get('signature_present')}."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": det_path, "field": "ucan"}, {"path": evidence_ref("traces", "attempts", f"{attempt_id.replace(':', '_')}.ucan-meta.json"), "field": "token_sha256"}],
            notes=["Signature bytes are from cryptography Ed25519, not a fixture verifier."],
        ),
        step_record(
            number=9,
            name="In enforce mode, revalidate and consume the exact permitted use",
            status="ran",
            summary=(
                f"ENFORCE decision={enforce.get('decision')} store={enforce.get('store_kind')} "
                f"in_memory={enforce.get('in_memory_store')} consume={ (owner.get('consume_cas') or {}).get('outcome') }."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": det_path, "field": "enforce"}, {"path": det_path, "field": "owner"}],
        ),
        step_record(
            number=10,
            name="Dispatch once through the selected protected path",
            status="ran",
            summary=(
                f"BoundedExportHandler.export_json handler_calls={detailed['handler_calls']} "
                f"delegate_called={enforce.get('delegate_called')}."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": det_path, "field": "handler"}, {"path": la_path, "field": "handler_calls"}],
        ),
        step_record(
            number=11,
            name="Record observed outcome separately from proof and authorization",
            status="ran",
            summary=(
                f"Independent observer v2 counted effects={detailed['observed_effect_count']} "
                f"journal={detailed['journal_event_count']} useful_work={detailed['useful_work']} "
                f"(LA-015 compact useful_work={la015_row.get('useful_work')})."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[
                {"path": det_path, "field": "handler.observation"},
                {"path": la_path, "field": "observed_effect_count"},
            ],
        ),
        step_record(
            number=12,
            name="Commit operational progression through the DuckDB owner",
            status="ran" if owner.get("consume_cas") else "partial",
            summary=(
                f"Typed Quack owner consume CAS outcome={(owner.get('consume_cas') or {}).get('outcome')} "
                f"generation={(owner.get('consume_cas') or {}).get('generation')} "
                f"revision={(owner.get('consume_cas') or {}).get('revision')}."
            ),
            attempt_id=attempt_id,
            case_id=case_id,
            evidence=[{"path": det_path, "field": "owner.consume_cas"}],
            notes=["Quack Unix-socket gateway is not claimed; embedded exclusive-lock owner ran."],
        ),
    ]


def pdf_escape(text: str) -> str:
    cleaned = "".join(ch if 32 <= ord(ch) <= 126 else "?" for ch in text)
    return cleaned.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def wrap(text: str, width: int) -> list[str]:
    words: list[str] = []
    for word in text.split():
        if len(word) <= width:
            words.append(word)
            continue
        for index in range(0, len(word), width):
            words.append(word[index : index + width])
    lines: list[str] = []
    current = ""
    for word in words:
        trial = word if not current else current + " " + word
        if len(trial) <= width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


def draw_page(commands: list[str], y: float, size: int, text: str, *, x: float = 36, leading: float | None = None) -> float:
    leading = leading or (size + 3)
    commands.append(f"BT /F1 {size} Tf {x:.1f} {y:.1f} Td ({pdf_escape(text)}) Tj ET")
    return y - leading


def write_pdf(path: Path, payload: Mapping[str, Any]) -> None:
    pages: list[list[str]] = []
    width, height = 792, 612

    def new_page() -> list[str]:
        commands: list[str] = []
        commands.append("0.15 0.18 0.22 rg 36 576 720 18 re f")
        commands.append("1 1 1 rg")
        commands.append("BT /F1 12 Tf 42 581 Td (Source-to-effect trace: bounded export under A4 ENFORCE) Tj ET")
        commands.append("0 0 0 rg")
        pages.append(commands)
        return commands

    c1 = new_page()
    y = 558
    run = payload["run_identity"]
    permitted = payload["illustrated"]["permitted_useful_work"]
    y = draw_page(c1, y, 9, f"LA-015 identity {permitted['attempt_id']}  revision {run['implementation_revision'][:16]}")
    y = draw_page(c1, y, 8, f"case {permitted['case_id']}  population={permitted['population']}  mutation={permitted['mutation']}  decision={permitted['decision']}  useful_work={permitted['useful_work']}  effects={permitted['observed_effect_count']}")
    y = draw_page(c1, y, 8, "Each row is a retained transition for this attempt. Absent/partial steps are labeled; SAT is satisfiability, not a kernel theorem.")
    y -= 6
    y = draw_page(c1, y, 10, "Appendix D twelve-step trace (permitted useful work)")
    y -= 2
    headers = [("Stp", 36), ("Status", 62), ("Method", 108), ("Observed evidence", 330)]
    c1.append("0.92 0.93 0.95 rg 36 %.1f 720 14 re f" % (y - 2))
    c1.append("0 0 0 rg")
    for title, x in headers:
        c1.append(f"BT /F1 8 Tf {x:.1f} {y:.1f} Td ({pdf_escape(title)}) Tj ET")
    y -= 14
    for step in payload["twelve_steps"]:
        status = step["status"]
        name_lines = wrap(str(step["name"]), 42)
        summary_lines = wrap(str(step["summary"]), 78)
        row_h = 11 * max(len(name_lines), len(summary_lines), 1) + 4
        if y - row_h < 48:
            c1 = new_page()
            y = 558
        if status == "ran":
            c1.append("0.86 0.94 0.86 rg 36 %.1f 720 %.1f re f" % (y - row_h + 10, row_h))
        elif status == "partial":
            c1.append("0.98 0.94 0.82 rg 36 %.1f 720 %.1f re f" % (y - row_h + 10, row_h))
        else:
            c1.append("0.95 0.90 0.90 rg 36 %.1f 720 %.1f re f" % (y - row_h + 10, row_h))
        c1.append("0 0 0 rg")
        c1.append(f"BT /F1 8 Tf 40 {y:.1f} Td ({step['step']}) Tj ET")
        c1.append(f"BT /F1 8 Tf 62 {y:.1f} Td ({pdf_escape(status)}) Tj ET")
        ty = y
        for line in name_lines:
            c1.append(f"BT /F1 7 Tf 108 {ty:.1f} Td ({pdf_escape(line)}) Tj ET")
            ty -= 10
        ty = y
        for line in summary_lines:
            c1.append(f"BT /F1 7 Tf 330 {ty:.1f} Td ({pdf_escape(line)}) Tj ET")
            ty -= 10
        y -= row_h
    y -= 8
    if y < 80:
        c1 = new_page()
        y = 558
    y = draw_page(c1, y, 10, "Matched A4 variants from the same seed/arm run")
    c2 = c1
    headers2 = [("Variant", 36), ("Attempt identity", 150), ("Decision", 430), ("Effects", 500), ("Useful", 560), ("Forbidden", 620)]
    c2.append("0.92 0.93 0.95 rg 36 %.1f 720 14 re f" % (y - 2))
    c2.append("0 0 0 rg")
    for title, x in headers2:
        c2.append(f"BT /F1 8 Tf {x:.1f} {y:.1f} Td ({pdf_escape(title)}) Tj ET")
    y -= 14
    rows = [
        {
            "label": "permitted export",
            "attempt_id": permitted["attempt_id"],
            "decision": permitted["decision"],
            "effects": permitted["observed_effect_count"],
            "useful": permitted["useful_work"],
            "forbidden": permitted["observed_forbidden_effect"],
        }
    ]
    for variant in payload["illustrated"]["variants"]:
        forbidden = variant["forbidden"]
        rows.append(
            {
                "label": variant["kind"],
                "attempt_id": forbidden["attempt_id"],
                "decision": forbidden["decision"],
                "effects": forbidden["observed_effect_count"],
                "useful": forbidden["useful_work"],
                "forbidden": forbidden["observed_forbidden_effect"],
            }
        )
    for row in rows:
        if y < 70:
            c2 = new_page()
            y = 558
        color = "0.86 0.94 0.86" if row["decision"] == "allow" else "0.95 0.90 0.90"
        id_lines = wrap(str(row["attempt_id"]), 52)
        row_h = 11 * max(len(id_lines), 1) + 4
        c2.append(f"{color} rg 36 {y - row_h + 10:.1f} 720 {row_h:.1f} re f")
        c2.append("0 0 0 rg")
        c2.append(f"BT /F1 7 Tf 38 {y:.1f} Td ({pdf_escape(str(row['label']))}) Tj ET")
        ty = y
        for line in id_lines:
            c2.append(f"BT /F1 7 Tf 150 {ty:.1f} Td ({pdf_escape(line)}) Tj ET")
            ty -= 10
        c2.append(f"BT /F1 7 Tf 430 {y:.1f} Td ({pdf_escape(str(row['decision']))}) Tj ET")
        c2.append(f"BT /F1 7 Tf 500 {y:.1f} Td ({row['effects']}) Tj ET")
        c2.append(f"BT /F1 7 Tf 560 {y:.1f} Td ({row['useful']}) Tj ET")
        c2.append(f"BT /F1 7 Tf 620 {y:.1f} Td ({row['forbidden']}) Tj ET")
        y -= row_h
    y -= 10
    if y < 90:
        c2 = new_page()
        y = 558
    y = draw_page(c2, y, 10, "Retained identities (unbroken)")
    for row in rows:
        if y < 48:
            c2 = new_page()
            y = 558
        y = draw_page(c2, y, 7, f"{row['label']}: {row['attempt_id']}")
    y -= 6
    y = draw_page(c2, y, 10, "Explicit non-claims")
    for line in (
        "No fabricated Ed25519 signature or theorem_proof receipt is shown.",
        "SAT UNSAT is satisfiability authority only.",
        "Harness selected_evidence_cids are constants, not published proofs.",
        "Generated-code AST analysis and closed-loop model programs did not run.",
        "Independent human gold and expert legal fidelity remain unmeasured.",
    ):
        y = draw_page(c2, y, 8, line)

    objects: list[bytes] = []

    def add(obj: bytes) -> int:
        objects.append(obj)
        return len(objects)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    page_ids = []
    content_ids = []
    for commands in pages:
        stream = ("\n".join(commands) + "\n").encode("ascii")
        content_ids.append(add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream"))
    pages_id = len(objects) + len(pages) + 1
    for content_id in content_ids:
        page_ids.append(
            add(
                (
                    f"<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 {width} {height}] "
                    f"/Resources << /Font << /F1 {font} 0 R >> >> /Contents {content_id} 0 R >>"
                ).encode("ascii")
            )
        )
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    pages_obj = add(f"<< /Type /Pages /Count {len(page_ids)} /Kids [{kids}] >>".encode("ascii"))
    assert pages_obj == pages_id
    catalog = add(f"<< /Type /Catalog /Pages {pages_obj} 0 R >>".encode("ascii"))
    info_title = "Source-to-effect trace"
    info_subject = permitted["attempt_id"]
    info = add(
        (
            f"<< /Title ({pdf_escape(info_title)}) /Subject ({pdf_escape(info_subject)}) "
            f"/Producer (LA-020 worked trace) /Creator (LA-020) >>"
        ).encode("ascii")
    )
    # Keep the figure UTF-8 text so the snapshot copy is proposal-admissible.
    # Only the live PDF path is listed in the task binary envelope.
    out = bytearray(b"%PDF-1.4\n% ASCII source-to-effect figure; no binary objects\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend(
        (
            f"trailer << /Size {len(objects) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    data = bytes(out)
    data.decode("ascii")
    if b"\0" in data or not data.startswith(b"%PDF") or b"%%EOF" not in data[-64:]:
        raise TraceError("PDF figure is not an ASCII text PDF")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid4().hex)
    temporary.write_bytes(data)
    os.replace(temporary, path)


def render_markdown(payload: Mapping[str, Any]) -> str:
    permitted = payload["illustrated"]["permitted_useful_work"]
    lines = [
        "# Worked source-to-effect trace",
        "",
        "This replaces the manuscript §7 composition walkthrough and Appendix D twelve-step list with a replay of frozen LA-015 A4 identities. Compact LA-015 rows remain the scored outcomes. Intermediate SAT, UCAN, ENFORCE, handler, and DuckDB artifacts below were retained on a detailed replay of those identities. No kernel theorem, generated program, or independent human gold is claimed.",
        "",
        "## Run identity",
        "",
        f"- Source run: `{payload['run_identity']['source_run']}`",
        f"- Implementation revision: `{payload['run_identity']['implementation_revision']}`",
        f"- Seed / arm: `{payload['run_identity']['seed']}` / `{payload['run_identity']['arm_id']}`",
        f"- Permitted attempt: `{permitted['attempt_id']}`",
        f"- Case: `{permitted['case_id']}` ({permitted['population']}, mutation `{permitted['mutation']}`)",
        f"- Decision / useful work / effects: `{permitted['decision']}` / `{permitted['useful_work']}` / `{permitted['observed_effect_count']}`",
        "",
        "## Twelve-step trace for permitted useful work",
        "",
        "| Step | Status | Transition | Attempt |",
        "| ---: | --- | --- | --- |",
    ]
    for step in payload["twelve_steps"]:
        lines.append(
            f"| {step['step']} | {step['status']} | {step['name']}. {step['summary']} | `{step['attempt_id']}` |"
        )
    lines.extend(["", "## Matched forbidden variants", ""])
    for variant in payload["illustrated"]["variants"]:
        forbidden = variant["forbidden"]
        allowed = variant["allowed"]
        lines.extend(
            [
                f"### {variant['kind']}",
                "",
                f"- Family `{variant['lineage_family_id']}` mutation `{variant['mutation']}`",
                f"- Allowed control `{allowed['attempt_id']}`: decision `{allowed['decision']}`, useful_work `{allowed['useful_work']}`, effects `{allowed['observed_effect_count']}`",
                f"- Forbidden `{forbidden['attempt_id']}`: decision `{forbidden['decision']}`, forbidden_effect `{forbidden['observed_forbidden_effect']}`, effects `{forbidden['observed_effect_count']}`, denial `{forbidden.get('denial_reason')}`",
                f"- Divergence: {variant['divergence']}",
                "",
            ]
        )
    lines.extend(["## Absent or narrowed steps", ""])
    for item in payload["absent_or_narrowed"]:
        lines.append(f"- **{item['step']}**: {item['reason']}")
    lines.extend(["", "## Claim limits", ""])
    for item in payload["claim_limits"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines)


def variant_kind(mutation: str) -> str:
    return {
        "wrong_audience": "rejected_recipient",
        "undeclared_handler_effect": "undeclared_effect",
        "replay": "replay",
    }[mutation]


def variant_divergence(mutation: str, detailed: Mapping[str, Any]) -> str:
    if mutation == "wrong_audience":
        ucan = detailed.get("ucan") or {}
        return (
            f"Step 8 signed delegation: UCAN audience {ucan.get('token_audience')} "
            f"decision={ucan.get('decision')} reason={ucan.get('reason')}; handler was not dispatched."
        )
    if mutation == "undeclared_handler_effect":
        return (
            "Step 9 ENFORCE revalidation: supervisor context listed an extra undeclared effect "
            f"and enforce_decision={ (detailed.get('enforce') or {}).get('decision') } "
            f"denial={ (detailed.get('enforce') or {}).get('denial_reason') }."
        )
    warmup = (detailed.get("owner") or {}).get("warmup_cas") or {}
    consume = (detailed.get("owner") or {}).get("consume_cas") or {}
    return (
        "Step 9 consumption: warmup consume "
        f"{warmup.get('outcome')} then replay consume {consume.get('outcome')}; "
        f"enforce_decision={ (detailed.get('enforce') or {}).get('decision') }."
    )


def probe_environment() -> dict[str, Any]:
    import cryptography

    python = Path(PYTHON)
    return {
        "observed_at": utc_now(),
        "path": os.environ.get("PATH", ""),
        "home": os.environ.get("HOME", ""),
        "home_is_validation_prefix": "ipfs-accelerate-validation-home-" in str(os.environ.get("HOME", "")),
        "python": PYTHON,
        "python_version": sys.version.split()[0],
        "python_sha256": sha256_file(python) if python.is_file() else None,
        "cryptography_version": getattr(cryptography, "__version__", None),
        "HAVE_CRYPTO_ED25519": True,
        "sympy_origin": str(Path("/opt/ipfs-validation-site-packages/sympy/__init__.py")),
        "duckdb_origin": str(Path("/opt/ipfs-validation-site-packages/duckdb/__init__.py")),
    }


def run(out_dir: Path, figure_path: Path, snapshot_dir: Path) -> dict[str, Any]:
    os.environ["PATH"] = SEALED_PATH
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    os.environ.setdefault("LANG", "C.UTF-8")
    for key, value in THREAD_ENV.items():
        os.environ[key] = value
    started = utc_now()
    la015 = load_la015()
    baselines = la015.load_baselines()
    config = baselines.load_arms()
    families = la015.frozen_families()
    mutations = la015.assign_mutations(families)
    candidates = la015.build_candidates(baselines, families, mutations)
    by_case = {row["candidate_id"]: row for row in candidates}
    la015_rows = load_jsonl(LIVE / "results" / "fixed_actions" / "raw.jsonl")
    la015_by_attempt = {row["attempt_id"]: row for row in la015_rows}
    source_ir_rows = load_jsonl(LIVE / "results" / "source_ir" / "raw.jsonl")
    source_ir = {row["case_id"]: row for row in source_ir_rows}
    sources = load_json(BENCHMARK / "manifests" / "sources.json")
    selected = select_cases(families, mutations, source_ir, la015_by_attempt)

    needed_ids = [selected["permitted"]["case_id"]]
    for variant in selected["variants"]:
        needed_ids.extend([variant["allowed_case_id"], variant["forbidden_case_id"]])
    needed_attempts = [f"{SEED}:{ARM_ID}:{case_id}" for case_id in needed_ids]

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import public_key_bytes
    from ipfs_kit_py.mcp_server.mcplusplus.revocation import RevocationLedger

    durable = baselines.load_durable()
    work = Path(tempfile.mkdtemp(prefix="la020-run-"))
    ledger_path = work / "shared-ucan-ledger.json"
    root_key = Ed25519PrivateKey.generate()
    ledger = RevocationLedger(ledger_path)
    ledger.register_public_key(baselines.ISSUER, "root-v1", public_key_bytes(root_key))
    shared = {"root_key": root_key, "ledger_path": str(ledger_path)}
    database = work / "control.duckdb"
    store = durable.DuckDBCapabilityConsumptionStore(database, owner_id="owner:la-020")
    detailed_by_attempt: dict[str, dict[str, Any]] = {}
    try:
        store.attach()
        for attempt_id in needed_attempts:
            case_id = attempt_id.split(":", 2)[2]
            candidate = by_case[case_id]
            slot = {"attempt_id": attempt_id, "seed": SEED, "arm_id": ARM_ID, "case_id": case_id, "schedule_index": 0}
            plan = la015.mutation_plan(candidate["mutation"])
            detailed_by_attempt[attempt_id] = detailed_run_a4(
                la015,
                baselines,
                slot=slot,
                candidate=candidate,
                config=config,
                plan=plan,
                shared=shared,
                store=store,
                work=work,
            )
    finally:
        store.close()
        shutil.rmtree(work, ignore_errors=True)

    mismatches = []
    for attempt_id, detailed in detailed_by_attempt.items():
        original = la015_by_attempt[attempt_id]
        for field in ("decision", "handler_calls", "observed_effect_count", "useful_work", "observed_forbidden_effect", "terminal_outcome"):
            if original.get(field) != detailed.get(field):
                mismatches.append(
                    {
                        "attempt_id": attempt_id,
                        "field": field,
                        "la015": original.get(field),
                        "replay": detailed.get(field),
                    }
                )
    if mismatches:
        raise TraceError("detailed replay diverged from LA-015 compact outcomes: " + json.dumps(mismatches))

    permitted_attempt = selected["permitted"]["attempt_id"]
    permitted_detailed = detailed_by_attempt[permitted_attempt]
    permitted_ir = source_excerpt(source_ir.get(selected["permitted"]["case_id"]))
    permitted_manifest = source_manifest_excerpt(
        sources, selected["permitted"]["family"]["source_id"], selected["permitted"]["family"]["lineage_family_id"]
    )
    steps = build_steps(
        selected["permitted"],
        permitted_detailed,
        permitted_ir,
        permitted_manifest,
        selected["permitted"]["row"],
    )

    illustrated_variants = []
    for variant in selected["variants"]:
        forbidden_detailed = detailed_by_attempt[variant["forbidden_attempt_id"]]
        allowed_detailed = detailed_by_attempt[variant["allowed_attempt_id"]]
        illustrated_variants.append(
            {
                "kind": variant_kind(variant["mutation"]),
                "mutation": variant["mutation"],
                "lineage_family_id": variant["family"]["lineage_family_id"],
                "population": variant["family"]["population"],
                "source_id": variant["family"]["source_id"],
                "divergence": variant_divergence(variant["mutation"], forbidden_detailed),
                "allowed": {
                    "attempt_id": variant["allowed_attempt_id"],
                    "case_id": variant["allowed_case_id"],
                    "decision": allowed_detailed["decision"],
                    "terminal_outcome": allowed_detailed["terminal_outcome"],
                    "useful_work": allowed_detailed["useful_work"],
                    "observed_effect_count": allowed_detailed["observed_effect_count"],
                    "observed_forbidden_effect": allowed_detailed["observed_forbidden_effect"],
                    "identity_digest": allowed_detailed["identity"]["candidate_digest"],
                },
                "forbidden": {
                    "attempt_id": variant["forbidden_attempt_id"],
                    "case_id": variant["forbidden_case_id"],
                    "decision": forbidden_detailed["decision"],
                    "terminal_outcome": forbidden_detailed["terminal_outcome"],
                    "useful_work": forbidden_detailed["useful_work"],
                    "observed_effect_count": forbidden_detailed["observed_effect_count"],
                    "observed_forbidden_effect": forbidden_detailed["observed_forbidden_effect"],
                    "denial_reason": (forbidden_detailed.get("enforce") or {}).get("denial_reason")
                    or (forbidden_detailed.get("ucan") or {}).get("reason"),
                    "identity_digest": forbidden_detailed["identity"]["candidate_digest"],
                    "sat_status": (forbidden_detailed.get("sat") or {}).get("provider", {}).get("status"),
                    "ucan_decision": (forbidden_detailed.get("ucan") or {}).get("decision"),
                    "enforce_decision": (forbidden_detailed.get("enforce") or {}).get("decision"),
                    "consume_outcome": ((forbidden_detailed.get("owner") or {}).get("consume_cas") or {}).get("outcome"),
                },
            }
        )

    pins = {
        "la015_run_fixed_actions.py": pin_file(LA015 / "run_fixed_actions.py"),
        "baselines.py": pin_file(BENCHMARK / "baselines.py"),
        "effects.py": pin_file(BENCHMARK / "handlers" / "effects.py"),
        "durable_consumption.py": pin_file(BENCHMARK / "durable_consumption.py"),
        "splits.json": pin_file(BENCHMARK / "manifests" / "splits.json"),
        "sources.json": pin_file(BENCHMARK / "manifests" / "sources.json"),
        "source_ir_raw.jsonl": pin_file(LIVE / "results" / "source_ir" / "raw.jsonl"),
        "fixed_actions_raw.jsonl": pin_file(LIVE / "results" / "fixed_actions" / "raw.jsonl"),
        "admissibility_enforcement.py": pin_file(
            ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py"
        ),
        "authorization.py": pin_file(ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py"),
        "ucan.py": pin_file(ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/ucan.py"),
    }
    payload = {
        "schema": SCHEMA,
        "task": "LA-020",
        "status": "executed_detailed_replay_of_frozen_identities",
        "harness_version": HARNESS_VERSION,
        "started_at": started,
        "completed_at": utc_now(),
        "run_identity": {
            "source_run": "LA-015",
            "implementation_revision": selected["permitted"]["row"]["implementation_revision"],
            "seed": SEED,
            "arm_id": ARM_ID,
            "harness_version": "la-015-fixed-action-harness/v1",
            "detailed_replay_harness": HARNESS_VERSION,
        },
        "selection_rule": (
            "One successful skill bounded-export A4 cell at seed 104729, plus the matched "
            "case-0/case-1 A4 pairs whose case-1 mutations are wrong_audience, "
            "undeclared_handler_effect, and replay."
        ),
        "illustrated": {
            "permitted_useful_work": {
                "attempt_id": permitted_attempt,
                "case_id": selected["permitted"]["case_id"],
                "population": selected["permitted"]["family"]["population"],
                "split": selected["permitted"]["family"]["split"],
                "mutation": "none",
                "source_id": selected["permitted"]["family"]["source_id"],
                "lineage_family_id": selected["permitted"]["family"]["lineage_family_id"],
                "identity_digest": permitted_detailed["identity"]["candidate_digest"],
                "decision": permitted_detailed["decision"],
                "terminal_outcome": permitted_detailed["terminal_outcome"],
                "useful_work": permitted_detailed["useful_work"],
                "observed_effect_count": permitted_detailed["observed_effect_count"],
                "observed_forbidden_effect": permitted_detailed["observed_forbidden_effect"],
                "sat_status": (permitted_detailed.get("sat") or {}).get("provider", {}).get("status"),
                "ucan_crypto": (permitted_detailed.get("ucan") or {}).get("crypto"),
                "ucan_token_sha256": (permitted_detailed.get("ucan") or {}).get("token_sha256"),
                "enforce_mode": "enforce",
                "store_kind": (permitted_detailed.get("enforce") or {}).get("store_kind"),
                "source": permitted_ir,
                "manifest": permitted_manifest,
            },
            "variants": illustrated_variants,
        },
        "twelve_steps": steps,
        "absent_or_narrowed": [
            {
                "step": "Generated-code AST / model program",
                "status": "absent",
                "reason": "LA-016 generated_program_count=0; the handler consumes a declarative export_json instruction, not generated source text.",
            },
            {
                "step": "LegalIRCompilerAPI",
                "status": "absent",
                "reason": "LegalIRCompilerAPI was not selected; the deterministic deontic parser is the recorded adapter. Independent legal review was not used.",
            },
            {
                "step": "Kernel theorem_proof",
                "status": "absent",
                "reason": "The executed job is QF_BOOL SAT with satisfiability authority. SAT/UNSAT cannot authorize theorem_proof allows.",
            },
            {
                "step": "Published IPFS proof CID",
                "status": "absent",
                "reason": "Source pins are SHA-256 content identities. Harness selected_evidence_cids include a constant stub CID that is labeled not-proof and is not shown as a receipt.",
            },
            {
                "step": "Independent human gold",
                "status": "absent",
                "reason": "independent_human_gold remains false on the frozen LA-015 and LA-009 records.",
            },
        ],
        "claim_limits": [
            "Allowed and forbidden refer only to the frozen modeled policy and machine-checkable behavior contract.",
            "Independent effect observation is the filesystem-journal observer, not an outside human reviewer.",
            "No expert legal fidelity, real-world legality, or independent human gold is claimed.",
            "SAT/UNSAT cannot authorize theorem_proof allows.",
            "No fabricated signature or conceptual step is presented as executed.",
            "Closed-loop model-generated programs remain unrun.",
            "Detailed replay artifacts recover omitted intermediate fields; compact LA-015 rows remain the scored identities.",
        ],
        "replay_matches_la015": True,
        "mismatch_count": 0,
        "environment": probe_environment(),
        "pins": pins,
        "empirical_benchmark_result": True,
        "independent_human_gold": False,
        "theorem_proof": False,
        "fabricated_signature": False,
        "model_calls": 0,
        "generated_program_count": 0,
    }

    snap_out = snapshot_dir / "outputs"
    evidence_dir = snapshot_dir / "evidence"
    attempts_dir = snapshot_dir / "traces" / "attempts"
    for directory in (out_dir, figure_path.parent, snap_out / "results" / "worked_trace", snap_out / "results" / "figures", evidence_dir, attempts_dir, snapshot_dir / "probe"):
        directory.mkdir(parents=True, exist_ok=True)

    selected_la015 = {attempt_id: la015_by_attempt[attempt_id] for attempt_id in needed_attempts}
    selected_ir = {case_id: source_ir.get(case_id) for case_id in needed_ids}
    selected_manifests = {}
    for family in [selected["permitted"]["family"], *[row["family"] for row in selected["variants"]]]:
        selected_manifests[family["source_id"]] = source_manifest_excerpt(sources, family["source_id"], family["lineage_family_id"])
    write_json(evidence_dir / "la015_selected.json", selected_la015)
    write_json(evidence_dir / "source_ir_selected.json", selected_ir)
    write_json(evidence_dir / "source_manifest_selected.json", selected_manifests)
    write_json(
        snapshot_dir / "traces" / "selection.json",
        {
            "seed": SEED,
            "arm_id": ARM_ID,
            "permitted_attempt_id": permitted_attempt,
            "attempt_ids": needed_attempts,
            "mutations": {row["mutation"]: row["forbidden_attempt_id"] for row in selected["variants"]},
        },
    )
    for attempt_id, detailed in detailed_by_attempt.items():
        stem = attempt_id.replace(":", "_")
        write_json(attempts_dir / f"{stem}.json", detailed)
        ucan_meta = {
            "attempt_id": attempt_id,
            "token_sha256": (detailed.get("ucan") or {}).get("token_sha256"),
            "signature_present": (detailed.get("ucan") or {}).get("signature_present"),
            "crypto": (detailed.get("ucan") or {}).get("crypto"),
            "fabricated_signature": False,
            "authorization_event_cid": (detailed.get("ucan") or {}).get("authorization_event_cid"),
        }
        write_json(attempts_dir / f"{stem}.ucan-meta.json", ucan_meta)

    write_json(out_dir / "trace.json", payload)
    write_text(out_dir / "trace.md", render_markdown(payload))
    write_pdf(figure_path, payload)
    shutil.copy2(out_dir / "trace.json", snap_out / "results" / "worked_trace" / "trace.json")
    shutil.copy2(out_dir / "trace.md", snap_out / "results" / "worked_trace" / "trace.md")
    shutil.copy2(figure_path, snap_out / "results" / "figures" / "source_to_effect_trace.pdf")
    write_json(snapshot_dir / "probe" / "environment.json", payload["environment"])
    write_json(
        snapshot_dir / "traces" / "run_head.json",
        {
            "attempts": len(detailed_by_attempt),
            "permitted_attempt_id": permitted_attempt,
            "useful_work": permitted_detailed["useful_work"],
            "variants": [row["kind"] for row in illustrated_variants],
            "replay_matches_la015": True,
            "theorem_proof": False,
        },
    )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("run",))
    parser.add_argument("--out", default=str(LIVE / "results" / "worked_trace"))
    parser.add_argument("--figure", default=str(LIVE / "results" / "figures" / "source_to_effect_trace.pdf"))
    parser.add_argument("--snapshot", default=str(SNAPSHOT))
    args = parser.parse_args(argv)
    payload = run(Path(args.out), Path(args.figure), Path(args.snapshot))
    print(
        json.dumps(
            {
                "task": "LA-020",
                "permitted_attempt_id": payload["illustrated"]["permitted_useful_work"]["attempt_id"],
                "useful_work": payload["illustrated"]["permitted_useful_work"]["useful_work"],
                "variants": [row["kind"] for row in payload["illustrated"]["variants"]],
                "replay_matches_la015": payload["replay_matches_la015"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        traceback.print_exc()
        raise SystemExit(f"LA-020 build failed: {exc}") from exc
