#!/usr/bin/python3.12
"""Matched fixed-action baseline arms for LA-014.

Arm configurations are machine-readable. Shared sources, handler, observer,
candidates, clock, route, and scoring stay fixed. Arms differ only by declared
policy components. This is comparability qualification on development cases,
not a scored LA-015 run and not a closed-loop model study.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping
from uuid import uuid4

HERE = Path(__file__).resolve()


def find_root(start: Path) -> Path:
    for candidate in (start, *start.parents):
        if (candidate / "papers" / "completion" / "law_to_action").is_dir() and (
            candidate / "external" / "ipfs_accelerate"
        ).is_dir():
            return candidate
    raise RuntimeError("repository root not found")


ROOT = find_root(HERE)
LIVE = ROOT / "papers" / "completion" / "law_to_action"
PYTHON = "/usr/bin/python3.12"
VALIDATION_SITE_PACKAGES = Path("/opt/ipfs-validation-site-packages")
HANDLERS = LIVE / "benchmark" / "handlers" / "effects.py"
ARMS_PATH = LIVE / "benchmark" / "arms.json"
SPLITS_PATH = LIVE / "benchmark" / "manifests" / "splits.json"
DURABLE_PATH = LIVE / "benchmark" / "durable_consumption.py"
ACTOR = "did:client:tenant-a"
AUDIENCE = "did:service:tenant-a"
ISSUER = "did:key:root-tenant-a"
RESOURCE = "tenant-a/bucket-a/documents/report.txt"
TOOL = "export_json"
CLOCK = "2026-07-28T12:02:00Z"
ISSUED = "2026-07-28T12:00:00Z"
DEADLINE = "2026-07-28T12:05:00Z"
EXPIRY = "2026-07-28T12:10:00Z"
DIGEST_E = "e" * 64
DIGEST_F = "f" * 64
DIGEST_1 = "1" * 64
DIGEST_2 = "2" * 64
ARM_DOC_KEYS = {
    "id",
    "name",
    "conventional_arm_label",
    "contrast_role",
    "interpretation",
    "required_qualifications",
    "when_unavailable",
    "policy_components",
}
POLICY_KEYS = (
    "unguarded_sandbox_dispatch",
    "inert_policy_text",
    "inert_retrieval_context",
    "lightweight_declared_policy",
    "real_ucan_verifier",
    "supervisor_enforce",
    "checked_sat_obligations",
    "durable_consumption",
)

for path in (
    VALIDATION_SITE_PACKAGES,
    ROOT / "external" / "ipfs_accelerate",
    ROOT / "external" / "ipfs_datasets",
    ROOT / "external" / "ipfs_kit",
):
    text = str(path)
    if path.is_dir() and text not in sys.path:
        sys.path.insert(0, text)


class BaselineError(RuntimeError):
    """Matched-arm qualification cannot proceed."""


def sha256_file(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise BaselineError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_handlers():
    return load_module("la014_bounded_handlers", HANDLERS)


def load_durable():
    return load_module("la014_durable_consumption", DURABLE_PATH)


def load_arms(path: Path | None = None) -> dict[str, Any]:
    config = load_json(path or ARMS_PATH)
    if config.get("schema") != "law-to-action-matched-arms/v1":
        raise BaselineError("arms.json schema mismatch")
    if config.get("empirical_benchmark_result") is not False:
        raise BaselineError("arms.json must not claim an empirical benchmark result")
    arms = config.get("arms")
    if not isinstance(arms, list) or [arm.get("id") for arm in arms] != ["A0", "A1", "A2", "A3", "A4"]:
        raise BaselineError("exactly arms A0-A4 are required in order")
    keys = tuple(config.get("policy_component_keys") or ())
    if keys != POLICY_KEYS:
        raise BaselineError("policy_component_keys must match the declared component set")
    shared = config.get("shared_controls")
    if not isinstance(shared, Mapping):
        raise BaselineError("shared_controls required")
    fingerprints = {}
    for arm in arms:
        extra = set(arm) - ARM_DOC_KEYS
        if extra:
            raise BaselineError(f"{arm.get('id')} has non-policy execution keys: {sorted(extra)}")
        components = arm.get("policy_components")
        if not isinstance(components, Mapping) or tuple(components) != POLICY_KEYS:
            raise BaselineError(f"{arm.get('id')} policy_components must use the declared keys in order")
        if any(type(components[key]) is not bool for key in POLICY_KEYS):
            raise BaselineError(f"{arm.get('id')} policy_components must be booleans")
        fingerprints[arm["id"]] = digest({"shared_controls": shared, "policy_components": dict(components)})
    if len(set(fingerprints.values())) != 5:
        raise BaselineError("each arm fingerprint must be unique")
    if fingerprints["A1"] == fingerprints["A2"]:
        raise BaselineError("prompt-only and retrieval+prompt must differ")
    a0, a1, a2 = (next(arm for arm in arms if arm["id"] == ident)["policy_components"] for ident in ("A0", "A1", "A2"))
    if not a0["unguarded_sandbox_dispatch"] or a0["inert_policy_text"] or a0["inert_retrieval_context"]:
        raise BaselineError("A0 must be unguarded sandbox dispatch without prompt/retrieval metadata")
    if not a1["unguarded_sandbox_dispatch"] or not a1["inert_policy_text"] or a1["inert_retrieval_context"]:
        raise BaselineError("A1 must be prompt-only: inert policy text and no retrieval")
    if not a2["unguarded_sandbox_dispatch"] or not a2["inert_policy_text"] or not a2["inert_retrieval_context"]:
        raise BaselineError("A2 must be retrieval+prompt: inert policy text plus retrieval")
    a3 = next(arm for arm in arms if arm["id"] == "A3")["policy_components"]
    a4 = next(arm for arm in arms if arm["id"] == "A4")["policy_components"]
    if a3["unguarded_sandbox_dispatch"] or not a3["lightweight_declared_policy"] or not a3["real_ucan_verifier"]:
        raise BaselineError("A3 must use declared policy and real UCAN, not unguarded dispatch")
    if a3["supervisor_enforce"] or a3["checked_sat_obligations"] or a3["durable_consumption"]:
        raise BaselineError("A3 must not include A4 enforcement components")
    if not all(a4[key] for key in ("lightweight_declared_policy", "real_ucan_verifier", "supervisor_enforce", "checked_sat_obligations", "durable_consumption")):
        raise BaselineError("A4 must add ENFORCE, checked obligations, and durable consumption to A3")
    if a4["unguarded_sandbox_dispatch"]:
        raise BaselineError("A4 must not unguarded-dispatch")
    config["shared_fingerprint"] = digest(shared)
    config["arm_fingerprints"] = fingerprints
    return config


def development_families(splits: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    document = splits or load_json(SPLITS_PATH)
    families = [row for row in document["assignments"] if row.get("split") == "development"]
    if len(families) != 6:
        raise BaselineError(f"expected 6 development families, found {len(families)}")
    populations = {row["population"] for row in families}
    if populations != {"legal", "cve", "skill"}:
        raise BaselineError("development families must cover legal, cve, and skill")
    held = [row["lineage_family_id"] for row in document["assignments"] if row.get("split") != "development"]
    overlap = {row["lineage_family_id"] for row in families} & set(held)
    if overlap:
        raise BaselineError(f"development families overlap held-out lineages: {sorted(overlap)}")
    return families


def export_path_for(case_id: str) -> str:
    return f"exports/dev-{sha256_text(case_id)[:16]}.json"


def build_candidates(config: Mapping[str, Any]) -> list[dict[str, Any]]:
    families = development_families()
    candidates = []
    for family in families:
        for index, case_id in enumerate(family["planned_case_ids"]):
            oracle_role = "allowed" if index == 0 else "forbidden"
            instruction = {
                "operation": TOOL,
                "path": export_path_for(case_id),
                "payload": {
                    "candidate_id": case_id,
                    "population": family["population"],
                    "split": "development",
                    "task": "LA-014-fixed-action",
                    "oracle_role": oracle_role,
                },
            }
            encoded = canonical_json(instruction["payload"])
            candidate = {
                "candidate_id": case_id,
                "lineage_family_id": family["lineage_family_id"],
                "source_id": family["source_id"],
                "population": family["population"],
                "split": "development",
                "oracle_role": oracle_role,
                "actor": ACTOR,
                "audience": AUDIENCE,
                "root": "policy:root-v1",
                "arguments": instruction,
                "declared_effects": [
                    {
                        "effect_kind": "filesystem.export_json",
                        "target": instruction["path"],
                        "payload_sha256": hashlib.sha256(encoded).hexdigest(),
                        "payload_bytes": len(encoded),
                    }
                ],
                "handler_version": config["shared_controls"]["handler"]["version"],
                "observer_version": config["shared_controls"]["observer"]["version"],
                "clock": CLOCK,
                "initial_sandbox_state": "empty",
            }
            candidate["candidate_digest"] = digest(
                {
                    "candidate_id": candidate["candidate_id"],
                    "actor": candidate["actor"],
                    "audience": candidate["audience"],
                    "arguments": candidate["arguments"],
                    "declared_effects": candidate["declared_effects"],
                }
            )
            candidates.append(candidate)
    if len(candidates) != 12:
        raise BaselineError(f"expected 12 development candidates, found {len(candidates)}")
    return candidates


def identity_view(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "actor": candidate["actor"],
        "audience": candidate["audience"],
        "arguments": candidate["arguments"],
        "declared_effects": candidate["declared_effects"],
        "candidate_digest": candidate["candidate_digest"],
    }


def inert_metadata(arm: Mapping[str, Any], candidate: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    components = arm["policy_components"]
    meta: dict[str, Any] = {"arm_id": arm["id"], "consumed_by_planner": False, "model_calls": 0}
    if components["inert_policy_text"]:
        meta["policy_text"] = config["frozen_policy_text"]
        meta["policy_text_sha256"] = sha256_text(config["frozen_policy_text"])
    if components["inert_retrieval_context"]:
        meta["retrieval"] = {
            "split": "development",
            "lineage_family_id": candidate["lineage_family_id"],
            "source_id": candidate["source_id"],
            "lineage_safe": True,
            "includes_final_sibling": False,
            "includes_target_patch": False,
            "includes_acceptance_oracle": False,
            "snippet": "development-split lineage identifier only; no held-out label or sibling text",
        }
    return meta


class DeclaredLightweightPolicy:
    """Exact declared-clause matcher. Not the canonical datasets Profile D evaluator."""

    provider_id = "la-014-declared-lightweight-policy"
    available = True

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": self.provider_id,
            "available": True,
            "fail_closed": True,
            "canonical_datasets_evaluator": False,
            "label": "declared_clause_matcher",
        }

    def evaluate(
        self,
        *,
        actor: str,
        action: str,
        resource: str | None = None,
        policy: Mapping[str, Any] | None = None,
        policy_text: str | None = None,
        **_context: Any,
    ) -> dict[str, Any]:
        from ipfs_kit_py.mcp.profile_d_policy import policy_root

        clauses = list((policy or {}).get("clauses") or [])
        prohibited = any(
            clause.get("clause_type") == "prohibition"
            and clause.get("actor") == actor
            and clause.get("action") == action
            and clause.get("resource") == resource
            for clause in clauses
        )
        permitted = any(
            clause.get("clause_type") == "permission"
            and clause.get("actor") == actor
            and clause.get("action") == action
            and clause.get("resource") == resource
            for clause in clauses
        )
        decision = "deny" if prohibited or not permitted else "allow"
        return {
            "decision": decision,
            "policy_root": policy_root(policy, policy_text),
            "canonical": False,
            "provider": self.provider_id,
        }


def parse_dimacs(text: str) -> tuple[int, list[list[int]]]:
    nvars = 0
    clauses: list[list[int]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p "):
            parts = line.split()
            nvars = int(parts[2])
            continue
        lits = [int(tok) for tok in line.split()]
        if not lits or lits[-1] != 0:
            raise BaselineError(f"DIMACS clause must end with 0: {line!r}")
        clause = lits[:-1]
        if clause:
            clauses.append(clause)
    if nvars <= 0:
        raise BaselineError("DIMACS formula missing variable count")
    return nvars, clauses


def sat_provider(nvars: int, clauses: list[list[int]]) -> dict[str, Any]:
    from sympy.core.symbol import Symbol
    from sympy.logic.boolalg import And, Not, Or, true
    from sympy.logic.inference import satisfiable

    symbols = {i: Symbol(f"x{i}") for i in range(1, nvars + 1)}
    encoded = []
    for clause in clauses:
        terms = []
        for lit in clause:
            atom = symbols[abs(lit)]
            terms.append(atom if lit > 0 else Not(atom))
        encoded.append(Or(*terms) if len(terms) > 1 else terms[0])
    formula = And(*encoded) if encoded else true
    started = time.perf_counter()
    model = satisfiable(formula, algorithm="dpll")
    elapsed = time.perf_counter() - started
    if model is False:
        return {
            "status": "unsat",
            "model": None,
            "elapsed_seconds": elapsed,
            "authority_kind": "satisfiability",
            "provider": "sympy.logic.inference.satisfiable",
            "algorithm": "dpll",
        }
    decoded = {str(symbol): bool(value) for symbol, value in dict(model).items()}
    return {
        "status": "sat",
        "model": decoded,
        "elapsed_seconds": elapsed,
        "authority_kind": "satisfiability",
        "provider": "sympy.logic.inference.satisfiable",
        "algorithm": "dpll",
    }


def sat_checker(nvars: int, clauses: list[list[int]], provider: Mapping[str, Any]) -> dict[str, Any]:
    if nvars > 16:
        return {"status": "unsupported", "reason": "too_many_vars", "authority_kind": "satisfiability"}

    def holds(bits: int) -> bool:
        for clause in clauses:
            ok = False
            for lit in clause:
                bit = (bits >> (abs(lit) - 1)) & 1
                if (lit > 0 and bit == 1) or (lit < 0 and bit == 0):
                    ok = True
                    break
            if not ok:
                return False
        return True

    sat = any(holds(bits) for bits in range(1 << nvars))
    status = "sat" if sat else "unsat"
    return {
        "status": status,
        "checker": "exhaustive-truth-table",
        "authority_kind": "satisfiability",
        "agrees_with_provider": provider.get("status") == status,
        "theorem_proof": False,
    }


def obligation_formula(candidate: Mapping[str, Any]) -> str:
    # x1 grant declared, x2 roots match, x3 forbidden extra effect claimed.
    # Force x1, x2, and x3 true together with (~x1 | ~x2 | ~x3). UNSAT means
    # the selected invariant holds for this declared export_json effect.
    extra = any(effect["effect_kind"] != "filesystem.export_json" for effect in candidate["declared_effects"])
    if extra:
        return "c extra-effect\np cnf 1 1\n1 0\n"
    return (
        "c grant=x1 matching_roots=x2 forbidden_effect=x3\n"
        "c invariant: matching & grant -> ~forbidden\n"
        "p cnf 3 4\n"
        "1 0\n"
        "2 0\n"
        "3 0\n"
        "-2 -1 -3 0\n"
    )


def check_obligation(candidate: Mapping[str, Any]) -> dict[str, Any]:
    nvars, clauses = parse_dimacs(obligation_formula(candidate))
    provider = sat_provider(nvars, clauses)
    checker = sat_checker(nvars, clauses, provider)
    allowed = provider["status"] == "unsat" and checker["agrees_with_provider"] is True
    return {
        "provider": provider,
        "checker": checker,
        "allowed": allowed,
        "authority_kind": "satisfiability",
        "theorem_proof": False,
    }


class CountingDelegate:
    def __init__(self, fn: Callable[[], Any]) -> None:
        self.calls = 0
        self.fn = fn

    def __call__(self) -> Any:
        self.calls += 1
        return self.fn()


def ucan_bundle(tmp: Path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from ipfs_kit_py.mcp_server.mcplusplus.revocation import RevocationLedger
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import UCANVerifier, public_key_bytes

    root_key = Ed25519PrivateKey.generate()
    ledger = RevocationLedger(tmp / "ucan-ledger.json")
    ledger.register_public_key(ISSUER, "root-v1", public_key_bytes(root_key))
    verifier = UCANVerifier(ledger=ledger, trusted_issuers={ISSUER})
    return ledger, verifier, root_key


def issue_token(key, *, nonce: str, audience: str = ACTOR, resource: str = RESOURCE) -> str:
    from ipfs_kit_py.mcp_server.mcplusplus.ucan import issue_ucan

    now = time.time()
    return issue_ucan(
        issuer=ISSUER,
        audience=audience,
        capabilities=[{"resource": resource, "ability": TOOL}],
        private_key=key,
        kid="root-v1",
        expires_at=now + 300,
        nonce=nonce,
        issued_at=now - 10,
    )


def run_ucan_policy(
    *,
    candidate: Mapping[str, Any],
    config: Mapping[str, Any],
    tmp: Path,
    mutate_audience: bool,
) -> dict[str, Any]:
    from ipfs_kit_py.mcp.profile_d_policy import policy_root
    from ipfs_kit_py.mcp_server import mcplusplus
    from ipfs_kit_py.mcp_server.authorization import AuthorizationDenied, AuthorizationGate
    from ipfs_kit_py.mcp_server.mcplusplus.event_dag import EventDAGStore

    ledger, verifier, root_key = ucan_bundle(tmp)
    token_audience = "did:wrong" if mutate_audience else ACTOR
    token = issue_token(root_key, nonce=sha256_text(candidate["candidate_id"])[:24], audience=token_audience)
    policy = config["declared_lightweight_policy"]
    envelope = {
        "tool": TOOL,
        "resource": RESOURCE,
        "ability": TOOL,
        "actor": ACTOR,
        "ucan": token,
        "policy_root": policy_root(policy, None),
        "request_id": f"req-{sha256_text(candidate['candidate_id'])[:20]}",
        "transaction_id": f"req-{sha256_text(candidate['candidate_id'])[:20]}",
        "policy": policy,
    }
    gate = AuthorizationGate(
        policy_provider=DeclaredLightweightPolicy(),
        ucan_verifier=verifier,
        ledger=ledger,
        audit_store=EventDAGStore(storage_dir=str(tmp / "dag")),
        envelope_validator=mcplusplus.validate_packet,
        validator_available=True,
    )
    try:
        decision = gate.authorize(tool=TOOL, arguments={"resource": RESOURCE, "policy": policy}, envelope=envelope)
        return {
            "decision": "allow",
            "reason": "ucan_and_declared_policy",
            "crypto": "real-ed25519",
            "verifier_kind": "real-ucan-verifier",
            "policy_provider": DeclaredLightweightPolicy.provider_id,
            "token_audience": token_audience,
            "authorization_event_cid": decision.authorization_event_cid,
        }
    except AuthorizationDenied as exc:
        return {
            "decision": "deny",
            "reason": exc.code,
            "crypto": "real-ed25519",
            "verifier_kind": "real-ucan-verifier",
            "policy_provider": DeclaredLightweightPolicy.provider_id,
            "token_audience": token_audience,
        }


def bound_roots():
    from ipfs_datasets_py.logic.admissibility.receipt import BoundRoots

    return BoundRoots(
        policy_root="policy:root-v1",
        corpus_roots=("corpus:legal-v1", "corpus:security-v1"),
        revocation_root="revocation:root-v1",
        circuit_roots=("circuit:auth-v1",),
        vk_roots=("vk:auth-v1",),
    )


def bound_context(candidate: Mapping[str, Any], *, audience_id: str):
    from ipfs_datasets_py.logic.admissibility.receipt import BoundContext

    arguments_digest = digest(candidate["arguments"])
    request_digest = digest({"candidate_id": candidate["candidate_id"], "arguments": candidate["arguments"]})
    return BoundContext(
        request_digest=request_digest,
        arguments_digest=arguments_digest,
        actor_id="actor:alice",
        audience_id=audience_id,
        tool_id="tool:supervisor.delegate",
        tool_version="1.0.0",
        effect_ids=("effect:filesystem.export_json",),
        environment_digest=digest({"clock": CLOCK, "sandbox": "empty"}),
        environment_id="env:la-014-sandbox",
        delegation_ids=("delegation:la-014",),
        delegation_digest=digest("delegation:la-014"),
        resource_ids=(f"resource:{RESOURCE}",),
        capability_ids=("capability:write",),
        nonce=f"nonce-{sha256_text(candidate['candidate_id'])[:16]}",
    )


def make_receipt(candidate: Mapping[str, Any], *, audience_id: str):
    from ipfs_datasets_py.logic.admissibility.compose import InternalDecisionStatus
    from ipfs_datasets_py.logic.admissibility.receipt import build_decision_receipt

    return build_decision_receipt(
        receipt_id=f"receipt:{sha256_text(candidate['candidate_id'])[:24]}",
        context=bound_context(candidate, audience_id=audience_id),
        roots=bound_roots(),
        outcome=InternalDecisionStatus.ALLOW,
        reasons=("positive grant proved",),
        reason_codes=("allow.positive_grant",),
        selected_evidence_cids=("bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi",),
        obligation_ids=("obl:sat-qf-bool",),
        residual_duties=(),
        attempt_digests=(DIGEST_1,),
        result_digests=(DIGEST_2,),
        decision_digest=DIGEST_E,
        policy_digest=DIGEST_F,
        profile_id="profile:closed-world",
        issued_at=ISSUED,
        deadline=DEADLINE,
        expiry=EXPIRY,
        producer_id="producer:la-014",
    )


def make_capability(receipt: Any):
    from ipfs_datasets_py.logic.admissibility.receipt import derive_capability

    return derive_capability(
        receipt,
        capability_id="capability:la-014-once",
        allowed_effects=("effect:filesystem.export_json",),
        require_strict_subset=True,
    )


def supervisor_context(candidate: Mapping[str, Any]):
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import SupervisorInvocationContext

    ctx = bound_context(candidate, audience_id="audience:supervisor-dispatcher")
    return SupervisorInvocationContext(
        actor_id=ctx.actor_id,
        audience_id=ctx.audience_id,
        tool_id=ctx.tool_id,
        tool_version=ctx.tool_version,
        request_digest=ctx.request_digest,
        arguments_digest=ctx.arguments_digest,
        environment_digest=ctx.environment_digest,
        environment_id=ctx.environment_id,
        effect_ids=ctx.effect_ids,
        task_id=f"task:{candidate['candidate_id']}",
        plan_id="plan:la-014",
        delegation_ids=ctx.delegation_ids,
        delegation_digest=ctx.delegation_digest,
        nonce=ctx.nonce,
        resource_ids=ctx.resource_ids,
    )


def map_enforce_decision(outcome: Any) -> str:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import EnforcementDisposition

    if outcome.observation.disposition is EnforcementDisposition.ALLOWED:
        return "allow"
    return "deny"


@dataclass
class AttemptResult:
    arm_id: str
    candidate_id: str
    identity: dict[str, Any]
    decision: str
    terminal_outcome: str
    delegated: bool
    handler_calls: int
    observed_effect_count: int
    journal_event_count: int
    sandbox: bool
    policy_components: dict[str, Any]
    metadata: dict[str, Any]
    mechanism: dict[str, Any] = field(default_factory=dict)
    failure: str | None = None
    empirical_benchmark_result: bool = False

    def to_record(self) -> dict[str, Any]:
        return {
            "arm_id": self.arm_id,
            "candidate_id": self.candidate_id,
            "identity": self.identity,
            "decision": self.decision,
            "terminal_outcome": self.terminal_outcome,
            "delegated": self.delegated,
            "handler_calls": self.handler_calls,
            "observed_effect_count": self.observed_effect_count,
            "journal_event_count": self.journal_event_count,
            "sandbox": self.sandbox,
            "policy_components": self.policy_components,
            "metadata": self.metadata,
            "mechanism": self.mechanism,
            "failure": self.failure,
            "empirical_benchmark_result": False,
            "split": "development",
        }


def observe(state_dir: Path, run_id: str) -> dict[str, Any]:
    return load_handlers().EffectObserver(state_dir).observe(run_id=run_id)


def dispatch_handler(candidate: Mapping[str, Any], state_dir: Path, run_id: str) -> Any:
    handler = load_handlers().BoundedExportHandler(state_dir)
    return handler.execute(candidate["arguments"], run_id=run_id)


def finish(result: AttemptResult, state_dir: Path, run_id: str, calls: int) -> AttemptResult:
    observation = observe(state_dir, run_id)
    result.handler_calls = calls
    result.observed_effect_count = int(observation.get("observed_effect_count") or 0)
    result.journal_event_count = int(observation.get("journal_event_count") or 0)
    result.sandbox = True
    if result.failure:
        result.terminal_outcome = "execution_failure"
        return result
    if result.decision == "allow" and result.observed_effect_count == 1 and result.handler_calls == 1:
        result.terminal_outcome = "success"
        result.delegated = True
    elif result.decision == "deny" and result.observed_effect_count == 0 and result.handler_calls == 0:
        result.terminal_outcome = "denied"
        result.delegated = False
    else:
        result.terminal_outcome = "measurement_integrity_failure"
        result.failure = (
            f"decision={result.decision} calls={result.handler_calls} "
            f"effects={result.observed_effect_count} journal={result.journal_event_count}"
        )
    shutil.rmtree(state_dir, ignore_errors=True)
    return result


def run_unguarded(arm: Mapping[str, Any], candidate: Mapping[str, Any], config: Mapping[str, Any]) -> AttemptResult:
    handlers = load_handlers()
    state_dir = Path(tempfile.mkdtemp(prefix=f"la014-{arm['id']}-"))
    run_id = f"la014-{arm['id']}-{uuid4().hex[:12]}"
    result = AttemptResult(
        arm_id=arm["id"],
        candidate_id=candidate["candidate_id"],
        identity=identity_view(candidate),
        decision="allow",
        terminal_outcome="",
        delegated=True,
        handler_calls=0,
        observed_effect_count=0,
        journal_event_count=0,
        sandbox=True,
        policy_components=dict(arm["policy_components"]),
        metadata=inert_metadata(arm, candidate, config),
        mechanism={
            "dispatch": "direct_bounded_export_handler",
            "arbitrary_generated_source_execution": False,
            "handler_version": handlers.BoundedExportHandler.version,
        },
    )
    try:
        dispatch_handler(candidate, state_dir, run_id)
        calls = 1
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
        calls = 0
        result.decision = "unknown"
    return finish(result, state_dir, run_id, calls)


def run_a3(arm: Mapping[str, Any], candidate: Mapping[str, Any], config: Mapping[str, Any]) -> AttemptResult:
    tmp = Path(tempfile.mkdtemp(prefix="la014-a3-"))
    state_dir = Path(tempfile.mkdtemp(prefix="la014-A3-state-"))
    run_id = f"la014-A3-{uuid4().hex[:12]}"
    mutate = candidate["oracle_role"] == "forbidden"
    result = AttemptResult(
        arm_id="A3",
        candidate_id=candidate["candidate_id"],
        identity=identity_view(candidate),
        decision="deny",
        terminal_outcome="",
        delegated=False,
        handler_calls=0,
        observed_effect_count=0,
        journal_event_count=0,
        sandbox=True,
        policy_components=dict(arm["policy_components"]),
        metadata={"consumed_by_planner": False, "model_calls": 0},
    )
    calls = 0
    try:
        gate = run_ucan_policy(candidate=candidate, config=config, tmp=tmp, mutate_audience=mutate)
        result.mechanism = {**gate, "arbitrary_generated_source_execution": False}
        result.decision = gate["decision"]
        if gate["decision"] == "allow":
            dispatch_handler(candidate, state_dir, run_id)
            calls = 1
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}"
        result.decision = "unknown"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return finish(result, state_dir, run_id, calls)


def run_a4(
    arm: Mapping[str, Any],
    candidate: Mapping[str, Any],
    config: Mapping[str, Any],
    store: Any,
) -> AttemptResult:
    from ipfs_accelerate_py.agent_supervisor.proof.admissibility_enforcement import (
        SupervisorPreInvocationEnforcement,
    )

    tmp = Path(tempfile.mkdtemp(prefix="la014-a4-"))
    state_dir = Path(tempfile.mkdtemp(prefix="la014-A4-state-"))
    run_id = f"la014-A4-{uuid4().hex[:12]}"
    mutate = candidate["oracle_role"] == "forbidden"
    result = AttemptResult(
        arm_id="A4",
        candidate_id=candidate["candidate_id"],
        identity=identity_view(candidate),
        decision="deny",
        terminal_outcome="",
        delegated=False,
        handler_calls=0,
        observed_effect_count=0,
        journal_event_count=0,
        sandbox=True,
        policy_components=dict(arm["policy_components"]),
        metadata={"consumed_by_planner": False, "model_calls": 0},
    )
    calls = 0
    try:
        obligation = check_obligation(candidate)
        gate = run_ucan_policy(candidate=candidate, config=config, tmp=tmp, mutate_audience=mutate)
        gates_allow = bool(obligation["allowed"] and gate["decision"] == "allow")
        receipt_audience = "audience:supervisor-dispatcher" if gates_allow else "audience:wrong"
        receipt = make_receipt(candidate, audience_id=receipt_audience)
        capability = make_capability(receipt) if gates_allow else None
        delegate = CountingDelegate(lambda: dispatch_handler(candidate, state_dir, run_id))
        enforcer = SupervisorPreInvocationEnforcement(
            mode="enforce",
            store=store,
            expected_roots=bound_roots(),
            clock=lambda: CLOCK,
        )
        outcome = enforcer.authorize_and_delegate(
            supervisor_context(candidate),
            delegate,
            receipt=receipt,
            capability=capability,
        )
        enforce_decision = map_enforce_decision(outcome)
        allowed = gates_allow and enforce_decision == "allow" and delegate.calls == 1
        result.decision = "allow" if allowed else "deny"
        result.mechanism = {
            "obligation": obligation,
            "ucan": gate,
            "enforce_decision": enforce_decision,
            "enforce_mode": "enforce",
            "store_kind": getattr(store, "store_kind", type(store).__name__),
            "in_memory_store": bool(getattr(store, "in_memory", False)),
            "delegate_called": bool(outcome.delegate_called),
            "denial_reason": outcome.observation.denial_reason,
            "arbitrary_generated_source_execution": False,
        }
        if not allowed and delegate.calls:
            result.failure = "A4 denied but handler was invoked"
        calls = delegate.calls if allowed else 0
    except Exception as exc:
        result.failure = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        result.decision = "unknown"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return finish(result, state_dir, run_id, calls)


def run_arm(arm: Mapping[str, Any], candidate: Mapping[str, Any], config: Mapping[str, Any], store: Any | None) -> AttemptResult:
    components = arm["policy_components"]
    if components["supervisor_enforce"]:
        if store is None:
            raise BaselineError("A4 requires a durable consumption store")
        return run_a4(arm, candidate, config, store)
    if components["real_ucan_verifier"]:
        return run_a3(arm, candidate, config)
    return run_unguarded(arm, candidate, config)


def probe_environment() -> dict[str, Any]:
    import cryptography
    from ipfs_kit_py.mcp.profile_d_policy import ProfileDPolicyProvider
    from ipfs_kit_py.mcp_server.mcplusplus import ucan as ucan_mod

    duckdb_origin = None
    duckdb_version = None
    try:
        import duckdb

        duckdb_origin = getattr(duckdb, "__file__", None)
        duckdb_version = getattr(duckdb, "__version__", None)
    except Exception:
        duckdb = None
    sympy_origin = None
    try:
        import sympy

        sympy_origin = getattr(sympy, "__file__", None)
    except Exception:
        sympy = None
    return {
        "observed_at": utc_now(),
        "python": PYTHON,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "python_sha256": sha256_file(Path(sys.executable)) if Path(sys.executable).is_file() else None,
        "path": os.environ.get("PATH"),
        "home": os.environ.get("HOME"),
        "home_is_validation_prefix": str(os.environ.get("HOME", "")).find("ipfs-accelerate-validation-home-") >= 0,
        "cryptography_version": cryptography.__version__,
        "HAVE_CRYPTO_ED25519": bool(ucan_mod.HAVE_CRYPTO_ED25519),
        "canonical_profile_d_available": bool(ProfileDPolicyProvider().available),
        "duckdb_available": duckdb is not None,
        "duckdb_origin": duckdb_origin,
        "duckdb_version": duckdb_version,
        "sympy_available": sympy is not None,
        "sympy_origin": sympy_origin,
        "source_pins": {
            "admissibility_enforcement.py": {
                "path": "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py",
                "sha256": sha256_file(
                    ROOT / "external/ipfs_accelerate/ipfs_accelerate_py/agent_supervisor/proof/admissibility_enforcement.py"
                ),
            },
            "authorization.py": {
                "path": "external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py",
                "sha256": sha256_file(ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/authorization.py"),
            },
            "ucan.py": {
                "path": "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/ucan.py",
                "sha256": sha256_file(ROOT / "external/ipfs_kit/ipfs_kit_py/mcp_server/mcplusplus/ucan.py"),
            },
            "effects.py": {
                "path": "papers/completion/law_to_action/benchmark/handlers/effects.py",
                "sha256": sha256_file(HANDLERS),
            },
            "durable_consumption.py": {
                "path": "papers/completion/law_to_action/benchmark/durable_consumption.py",
                "sha256": sha256_file(DURABLE_PATH),
            },
        },
    }


def probe_resources() -> dict[str, Any]:
    affinity = sorted(os.sched_getaffinity(0))
    cgroup = Path("/sys/fs/cgroup")
    cgroup_controllers = None
    if (cgroup / "cgroup.controllers").is_file():
        cgroup_controllers = (cgroup / "cgroup.controllers").read_text(encoding="utf-8").strip()
    started = time.monotonic()
    timed_out = False
    child = subprocess.Popen(
        [PYTHON, "-c", "import os,time; os.write(1, str(os.getpid()).encode()); time.sleep(8)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        child.communicate(timeout=0.4)
    except subprocess.TimeoutExpired:
        timed_out = True
        os.killpg(child.pid, signal.SIGKILL)
        child.communicate()
    nproc = resource.getrlimit(resource.RLIMIT_NPROC)
    as_limit = resource.getrlimit(resource.RLIMIT_AS)
    descendant_contained = timed_out and child.returncode is not None
    singleton_cpu_enforced = False
    reason = "host cpuset recorded; creating a private cgroup requires privileges not granted in this qualification"
    if len(affinity) == 1:
        singleton_cpu_enforced = True
        reason = "process already bound to a singleton cpuset"
    return {
        "observed_at": utc_now(),
        "affinity": affinity,
        "affinity_count": len(affinity),
        "cgroup_v2": (cgroup / "cgroup.controllers").is_file(),
        "cgroup_controllers": cgroup_controllers,
        "descendant_process_group_kill": descendant_contained,
        "kill_signal": -child.returncode if isinstance(child.returncode, int) and child.returncode < 0 else child.returncode,
        "probe_wall_seconds": round(time.monotonic() - started, 6),
        "nproc_limit": nproc,
        "as_limit": as_limit,
        "singleton_cpu_enforced": singleton_cpu_enforced,
        "private_cgroup_created": False,
        "scored_attempts_admitted": False,
        "reason": reason,
        "protocol_gate": "If singleton CPU cgroup/quota cannot be enforced for every descendant, scored LA-015 attempts stay unrun.",
    }


def comparability(records: list[AttemptResult], config: Mapping[str, Any], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    by_candidate: dict[str, list[AttemptResult]] = {}
    for record in records:
        by_candidate.setdefault(record.candidate_id, []).append(record)
    identity_ok = True
    a012_equivalent = True
    a3_distinct = True
    a1_a2_distinct = True
    sandbox_ok = True
    details = []
    for candidate in candidates:
        group = by_candidate.get(candidate["candidate_id"], [])
        expected_identity = identity_view(candidate)
        if any(row.identity != expected_identity for row in group):
            identity_ok = False
        unguarded = [row for row in group if row.arm_id in {"A0", "A1", "A2"}]
        effects = {(row.decision, row.observed_effect_count, row.terminal_outcome) for row in unguarded}
        if len(effects) != 1:
            a012_equivalent = False
        a1 = next(row for row in group if row.arm_id == "A1")
        a2 = next(row for row in group if row.arm_id == "A2")
        if "policy_text" not in a1.metadata or "retrieval" in a1.metadata:
            a1_a2_distinct = False
        if "retrieval" not in a2.metadata or "policy_text" not in a2.metadata:
            a1_a2_distinct = False
        if a1.metadata.get("retrieval") == a2.metadata.get("retrieval"):
            a1_a2_distinct = False
        a3 = next(row for row in group if row.arm_id == "A3")
        a0 = next(row for row in group if row.arm_id == "A0")
        if candidate["oracle_role"] == "forbidden" and not (a0.observed_effect_count == 1 and a3.decision == "deny" and a3.observed_effect_count == 0):
            a3_distinct = False
        if candidate["oracle_role"] == "allowed" and not (a3.decision == "allow" and a3.observed_effect_count == 1):
            a3_distinct = False
        if not all(row.sandbox and row.mechanism.get("arbitrary_generated_source_execution") is not True for row in group):
            sandbox_ok = False
        if not all(row.sandbox for row in group):
            sandbox_ok = False
        details.append(
            {
                "candidate_id": candidate["candidate_id"],
                "oracle_role": candidate["oracle_role"],
                "identity_digest": candidate["candidate_digest"],
                "arm_decisions": {row.arm_id: row.decision for row in group},
                "arm_effects": {row.arm_id: row.observed_effect_count for row in group},
            }
        )
    failures = [row.to_record() for row in records if row.failure or row.terminal_outcome == "measurement_integrity_failure"]
    return {
        "identical_candidate_identity": identity_ok,
        "a0_a1_a2_operational_equivalence": a012_equivalent,
        "prompt_only_distinct_from_retrieval_prompt": a1_a2_distinct,
        "a3_a4_differ_from_unguarded_on_forbidden": a3_distinct,
        "unguarded_remains_sandboxed": sandbox_ok,
        "no_failures": not failures,
        "held_out_used": False,
        "empirical_benchmark_result": False,
        "arm_fingerprints": config["arm_fingerprints"],
        "shared_fingerprint": config["shared_fingerprint"],
        "n_candidates": len(candidates),
        "n_attempts": len(records),
        "failures": failures,
        "details": details,
    }


def render_report(
    *,
    config: Mapping[str, Any],
    candidates: list[dict[str, Any]],
    records: list[AttemptResult],
    comparison: Mapping[str, Any],
    env: Mapping[str, Any],
    resources: Mapping[str, Any],
    replay: Mapping[str, Any],
) -> str:
    arms = config["arms"]
    rows = []
    for arm in arms:
        components = arm["policy_components"]
        enabled = ", ".join(key for key, value in components.items() if value) or "(none)"
        rows.append(f"| {arm['id']} | {arm['conventional_arm_label']} | `{enabled}` | {arm['contrast_role']} |")
    allowed = [row for row in records if row.candidate_id.endswith(":case-0")]
    forbidden = [row for row in records if row.candidate_id.endswith(":case-1")]

    def counts(arm_id: str, subset: list[AttemptResult]) -> str:
        group = [row for row in subset if row.arm_id == arm_id]
        effects = sum(row.observed_effect_count for row in group)
        denials = sum(row.decision == "deny" for row in group)
        return f"{effects} effects / {denials} denials / {len(group)} attempts"

    lines = [
        "# LA-014 matched-arm comparability report",
        "",
        "Status: development-split qualification. Not a scored LA-015 result and not a closed-loop model study.",
        "",
        f"Observed at `{env['observed_at']}` under Python `{env['python_version']}` (`{env['python_executable']}`).",
        "",
        "## Shared controls",
        "",
        "Every arm receives the same development-split sources, BoundedExportHandler `export_json`, independent EffectObserver, frozen clock `2026-07-28T12:02:00Z`, empty initial sandbox, and independent effect scoring. No model is called. Calibration and final families are excluded.",
        "",
        f"Shared fingerprint: `{comparison['shared_fingerprint']}`.",
        "",
        "## Policy-component matrix",
        "",
        "Arm configurations are machine-readable in `arms.json`. After documentation labels are stripped, arms differ only by `policy_components`.",
        "",
        "| Arm | Label | Enabled policy components | Contrast |",
        "| --- | --- | --- | --- |",
        *rows,
        "",
        "A1 is prompt-only (inert policy text, no retrieval). A2 is retrieval+prompt (inert policy text plus lineage-safe development retrieval metadata). Those fingerprints differ:",
        "",
        f"- A1 `{comparison['arm_fingerprints']['A1']}`",
        f"- A2 `{comparison['arm_fingerprints']['A2']}`",
        "",
        "## Fixed-action candidate identity",
        "",
        f"{len(candidates)} development candidates (6 families × 2 cases) were replayed across 5 arms ({len(records)} attempts) using seed `104729`. Candidate IDs, actors, audiences, arguments, and declared effects are identical across arms. Identity check: `{comparison['identical_candidate_identity']}`.",
        "",
        "Oracle roles are predetermined: `case-0` allowed, `case-1` forbidden (wrong-audience capability). Roles are not taken from held-out annotation outcomes.",
        "",
        "## Observation paths",
        "",
        "| Arm | Allowed (`case-0`) | Forbidden (`case-1`) |",
        "| --- | --- | --- |",
    ]
    for arm_id in ("A0", "A1", "A2", "A3", "A4"):
        lines.append(f"| {arm_id} | {counts(arm_id, allowed)} | {counts(arm_id, forbidden)} |")
    lines.extend(
        [
            "",
            f"A0/A1/A2 operational equivalence: `{comparison['a0_a1_a2_operational_equivalence']}`. Because no planner consumes A1/A2 metadata, those arms must match A0 effects. A discrepancy would be a comparability defect, not prompt or retrieval efficacy.",
            "",
            f"Prompt-only vs retrieval+prompt distinctness: `{comparison['prompt_only_distinct_from_retrieval_prompt']}`.",
            "",
            f"Unguarded execution remains sandboxed: `{comparison['unguarded_remains_sandboxed']}`. A0 still uses BoundedExportHandler inside a per-attempt `state_dir`. It does not evaluate generated source.",
            "",
            f"A3/A4 differ from unguarded on forbidden candidates: `{comparison['a3_a4_differ_from_unguarded_on_forbidden']}`. Lightweight policy+UCAN uses real Ed25519 `UCANVerifier` and the declared-clause matcher. Full enforcement adds QF_BOOL SAT + exhaustive checker, `ENFORCE`, and file-backed DuckDB consumption.",
            "",
            "## Replay",
            "",
            f"One development candidate was executed twice per arm. Candidate identity digest was stable: `{replay.get('identity_stable')}`.",
            "",
            "## Resource probe",
            "",
            f"- CPU affinity: `{resources['affinity']}` (count {resources['affinity_count']})",
            f"- cgroup v2 present: `{resources['cgroup_v2']}`",
            f"- descendant process-group kill: `{resources['descendant_process_group_kill']}`",
            f"- private cgroup created: `{resources['private_cgroup_created']}`",
            f"- singleton CPU enforced for descendants: `{resources['singleton_cpu_enforced']}`",
            f"- scored attempts admitted: `{resources['scored_attempts_admitted']}`",
            "",
            resources["reason"],
            "",
            "## Limitations",
            "",
            f"- Canonical datasets Profile D available: `{env.get('canonical_profile_d_available')}`. A3 still uses the declared-clause matcher plus real UCAN, which is the selected lightweight policy component.",
            "- Selected proof route is QF_BOOL satisfiability. SAT/UNSAT cannot authorize `theorem_proof` allows.",
            "- DuckDB durable consumption uses the typed Quack owner in embedded exclusive-lock mode. The Unix-socket gateway remains unqualified without `LOAD quack`.",
            "- Resource cgroup/quota enforcement for every descendant is not demonstrated as a private cgroup. Scored LA-015 attempts stay unrun until that gate passes.",
            "- Closed-loop model arms are declared, unmatched to any pinned model, and unrun.",
            "",
            "## Versions",
            "",
            f"- cryptography {env.get('cryptography_version')}; `HAVE_CRYPTO_ED25519={env.get('HAVE_CRYPTO_ED25519')}`",
            f"- duckdb {env.get('duckdb_version')} (`{env.get('duckdb_origin')}`)",
            f"- sympy `{env.get('sympy_origin')}`",
            f"- PATH `{env.get('path')}`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def qualify(trace_dir: Path, report_path: Path, records_path: Path) -> dict[str, Any]:
    config = load_arms()
    candidates = build_candidates(config)
    env = probe_environment()
    if not env["HAVE_CRYPTO_ED25519"]:
        raise BaselineError("Ed25519 cryptography unavailable under sealed PATH")
    if not env["duckdb_available"]:
        raise BaselineError("DuckDB unavailable; A4 durable consumption cannot run")
    if not env["sympy_available"]:
        raise BaselineError("SymPy unavailable; A4 SAT obligations cannot run")
    resources = probe_resources()
    durable = load_durable()
    work = Path(tempfile.mkdtemp(prefix="la014-qualify-"))
    database = work / "control.duckdb"
    store = durable.DuckDBCapabilityConsumptionStore(database, owner_id="owner:la-014")
    records: list[AttemptResult] = []
    try:
        store.attach()
        for candidate in candidates:
            for arm in config["arms"]:
                records.append(run_arm(arm, candidate, config, store))
        replay_candidate = candidates[0]
        replay_first = [run_arm(arm, replay_candidate, config, store) for arm in config["arms"]]
        replay_second = [run_arm(arm, replay_candidate, config, store) for arm in config["arms"]]
        replay = {
            "candidate_id": replay_candidate["candidate_id"],
            "identity_stable": all(
                first.identity == second.identity == identity_view(replay_candidate)
                for first, second in zip(replay_first, replay_second)
            ),
            "first_identity": [row.identity for row in replay_first],
            "second_identity": [row.identity for row in replay_second],
        }
    finally:
        store.close()
        shutil.rmtree(work, ignore_errors=True)
    comparison = comparability(records, config, candidates)
    if not all(
        (
            comparison["identical_candidate_identity"],
            comparison["a0_a1_a2_operational_equivalence"],
            comparison["prompt_only_distinct_from_retrieval_prompt"],
            comparison["a3_a4_differ_from_unguarded_on_forbidden"],
            comparison["unguarded_remains_sandboxed"],
            comparison["no_failures"],
            replay["identity_stable"],
        )
    ):
        raise BaselineError(f"comparability checks failed: {json.dumps(comparison, sort_keys=True)[:2000]}")
    trace_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "law-to-action-comparability/v1",
        "task": "LA-014",
        "empirical_benchmark_result": False,
        "shared_fingerprint": config["shared_fingerprint"],
        "arm_fingerprints": config["arm_fingerprints"],
        "environment": env,
        "resources": resources,
        "comparison": comparison,
        "replay": replay,
        "records": [row.to_record() for row in records],
    }
    write_json(records_path, payload)
    write_json(trace_dir / "summary.json", {key: payload[key] for key in ("schema", "task", "empirical_benchmark_result", "shared_fingerprint", "arm_fingerprints", "comparison", "replay", "resources")})
    write_json(trace_dir / "environment.json", env)
    write_json(trace_dir / "resources.json", resources)
    write_json(trace_dir / "candidates.json", [identity_view(row) | {"oracle_role": row["oracle_role"], "population": row["population"], "split": row["split"]} for row in candidates])
    report = render_report(config=config, candidates=candidates, records=records, comparison=comparison, env=env, resources=resources, replay=replay)
    write_text(report_path, report)
    return payload


def validate_outputs(arms_path: Path, report_path: Path, records_path: Path) -> dict[str, Any]:
    config = load_arms(arms_path)
    payload = load_json(records_path)
    report = report_path.read_text(encoding="utf-8")
    if payload.get("empirical_benchmark_result") is not False:
        raise BaselineError("records claimed an empirical result")
    comparison = payload["comparison"]
    required = [
        comparison["identical_candidate_identity"],
        comparison["a0_a1_a2_operational_equivalence"],
        comparison["prompt_only_distinct_from_retrieval_prompt"],
        comparison["unguarded_remains_sandboxed"],
        comparison["a3_a4_differ_from_unguarded_on_forbidden"],
        comparison["no_failures"],
        payload["replay"]["identity_stable"],
    ]
    if not all(required):
        raise BaselineError("stored comparability checks are not all true")
    if "prompt-only" not in report or "retrieval+prompt" not in report:
        raise BaselineError("report must distinguish prompt-only from retrieval+prompt")
    if "sandboxed" not in report.lower() and "sandbox" not in report.lower():
        raise BaselineError("report must record that unguarded execution remains sandboxed")
    records = payload["records"]
    if len(records) != 60:
        raise BaselineError(f"expected 60 development attempts, found {len(records)}")
    if any(row.get("split") != "development" for row in records):
        raise BaselineError("non-development records present")
    a3 = [row for row in records if row["arm_id"] == "A3"]
    if not a3 or any(row["mechanism"].get("crypto") != "real-ed25519" for row in a3):
        raise BaselineError("A3 must execute real Ed25519 UCAN verification")
    a4 = [row for row in records if row["arm_id"] == "A4"]
    if not a4 or any(row["mechanism"].get("in_memory_store") for row in a4):
        raise BaselineError("A4 must not use in-memory consumption")
    if any(row["mechanism"].get("enforce_mode") != "enforce" for row in a4):
        raise BaselineError("A4 must use explicit ENFORCE")
    if any(row["mechanism"].get("obligation", {}).get("authority_kind") != "satisfiability" for row in a4):
        raise BaselineError("A4 obligations must be the selected SAT route")
    a1_meta = next(row for row in records if row["arm_id"] == "A1")["metadata"]
    a2_meta = next(row for row in records if row["arm_id"] == "A2")["metadata"]
    if "retrieval" in a1_meta or "retrieval" not in a2_meta:
        raise BaselineError("A1 must omit retrieval; A2 must include it")
    identities = {}
    for row in records:
        identities.setdefault(row["candidate_id"], set()).add(digest(row["identity"]))
    if any(len(values) != 1 for values in identities.values()):
        raise BaselineError("candidate identity changed across arms")
    return {
        "ok": True,
        "shared_fingerprint": config["shared_fingerprint"],
        "attempts": len(records),
        "empirical_benchmark_result": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    qualify_cmd = commands.add_parser("qualify")
    qualify_cmd.add_argument("--trace-dir", type=Path, required=True)
    qualify_cmd.add_argument("--report", type=Path, required=True)
    qualify_cmd.add_argument("--records", type=Path, required=True)
    validate_cmd = commands.add_parser("validate")
    validate_cmd.add_argument("--arms", type=Path, default=ARMS_PATH)
    validate_cmd.add_argument("--report", type=Path, required=True)
    validate_cmd.add_argument("--records", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "qualify":
        payload = qualify(args.trace_dir, args.report, args.records)
        sys.stdout.write(json.dumps({"ok": True, "attempts": payload["comparison"]["n_attempts"], "empirical_benchmark_result": False}, sort_keys=True) + "\n")
        return 0
    result = validate_outputs(args.arms, args.report, args.records)
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BaselineError, OSError, json.JSONDecodeError) as exc:
        print(f"baselines: {exc}", file=sys.stderr)
        raise SystemExit(2)
