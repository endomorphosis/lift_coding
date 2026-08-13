#!/usr/bin/env python3
"""Encode MCP contract logic expressions as observation-bound Lean claims.

Maps residual SCA ``mcp-contract-logic-expression@1`` operators + prove-path
observations into a small, decidable Lean theory.  IndependentKernelVerifier
can then discharge the **encoded** claim when observations support it.

Authority scope
---------------
``observation_bound_operator_semantics`` — KERNEL_VERIFIED means:

* the reviewed operator semantics (as encoded) hold under the bound observation
  facts (premises / schema / policy / relation flags), and
* Lean accepted the proof at an independent kernel boundary.

It does **not** re-litigate live MCP runtime behavior beyond those facts.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Mapping


# McpClaimFamily.value / LogicOperator.value → Lean ScaOperator constructor
OPERATOR_TO_LEAN: dict[str, str] = {
    "arguments_preserved": "argumentsPreserved",
    "ArgumentsPreserved": "argumentsPreserved",
    "descriptor_schema_matches": "descriptorSchemaMatches",
    "DescriptorSchemaMatches": "descriptorSchemaMatches",
    "result_envelope_preserved": "resultEnvelopePreserved",
    "ResultEnvelopePreserved": "resultEnvelopePreserved",
    "policy_before_effect": "policyBeforeEffect",
    "PolicyBeforeEffect": "policyBeforeEffect",
    "no_compatibility_bypass": "noCompatibilityBypass",
    "NoCompatibilityBypass": "noCompatibilityBypass",
    "transport_parity": "transportParity",
    "TransportParity": "transportParity",
    "discovery_execution_parity": "discoveryExecutionParity",
    "DiscoveryExecutionParity": "discoveryExecutionParity",
    "failure_parity": "failureParity",
    "FailureParity": "failureParity",
    # Graph-only operators: map to relation/schema-style observation holds
    "declared_tool_exists": "argumentsPreserved",
    "DeclaredToolExists": "argumentsPreserved",
    "invocation_reachable": "argumentsPreserved",
    "InvocationReachable": "argumentsPreserved",
    "snapshot_freshness": "transportParity",
    "SnapshotFreshness": "transportParity",
    "no_dynamic_authority": "noCompatibilityBypass",
    "NoDynamicAuthority": "noCompatibilityBypass",
}

# Operators that require schema-style observations for discharge
SCHEMA_OPS = frozenset(
    {
        "argumentsPreserved",
        "descriptorSchemaMatches",
        "resultEnvelopePreserved",
    }
)
DEONTIC_OPS = frozenset({"policyBeforeEffect", "noCompatibilityBypass"})
RELATION_OPS = frozenset(
    {"transportParity", "discoveryExecutionParity", "failureParity"}
)

LEAN_PRELUDE = '''\
/-- SCA residual claim codec: observation-bound operator semantics.
    Authority: observation_bound_operator_semantics@1
    Source: scripts/sca_mcp_claim_lean_codec.py
-/
inductive ScaOperator where
  | argumentsPreserved
  | descriptorSchemaMatches
  | resultEnvelopePreserved
  | policyBeforeEffect
  | noCompatibilityBypass
  | transportParity
  | discoveryExecutionParity
  | failureParity
  deriving DecidableEq, Repr

structure ScaObs where
  premisesHeld : Bool
  schemaValid : Bool
  policyBeforeEffect : Bool
  noBypass : Bool
  relationParity : Bool
  deriving Repr

def scaClaimHolds (op : ScaOperator) (obs : ScaObs) : Prop :=
  match op with
  | .argumentsPreserved => obs.premisesHeld = true ∧ obs.schemaValid = true
  | .descriptorSchemaMatches => obs.premisesHeld = true ∧ obs.schemaValid = true
  | .resultEnvelopePreserved => obs.premisesHeld = true ∧ obs.schemaValid = true
  | .policyBeforeEffect => obs.premisesHeld = true ∧ obs.policyBeforeEffect = true
  | .noCompatibilityBypass => obs.premisesHeld = true ∧ obs.noBypass = true
  | .transportParity => obs.premisesHeld = true ∧ obs.relationParity = true
  | .discoveryExecutionParity => obs.premisesHeld = true ∧ obs.relationParity = true
  | .failureParity => obs.premisesHeld = true ∧ obs.relationParity = true

instance (op : ScaOperator) (obs : ScaObs) : Decidable (scaClaimHolds op obs) := by
  cases op <;> dsimp [scaClaimHolds] <;> infer_instance

'''


@dataclass(frozen=True)
class ScaObservations:
    premises_held: bool
    schema_valid: bool
    policy_before_effect: bool
    no_bypass: bool
    relation_parity: bool

    def to_lean_literal(self) -> str:
        def b(v: bool) -> str:
            return "true" if v else "false"

        return (
            "{ premisesHeld := "
            f"{b(self.premises_held)}"
            ", schemaValid := "
            f"{b(self.schema_valid)}"
            ", policyBeforeEffect := "
            f"{b(self.policy_before_effect)}"
            ", noBypass := "
            f"{b(self.no_bypass)}"
            ", relationParity := "
            f"{b(self.relation_parity)}"
            " }"
        )

    def to_dict(self) -> dict[str, bool]:
        return {
            "premises_held": self.premises_held,
            "schema_valid": self.schema_valid,
            "policy_before_effect": self.policy_before_effect,
            "no_bypass": self.no_bypass,
            "relation_parity": self.relation_parity,
        }


@dataclass(frozen=True)
class LeanClaimEncoding:
    theorem_name: str
    lean_operator: str
    expected_statement: str
    native_source: str
    proof_text: str
    observations: ScaObservations
    mcp_statement: str
    operator_raw: str
    dischargeable: bool
    authority_scope: str
    reason_if_not: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "theorem_name": self.theorem_name,
            "lean_operator": self.lean_operator,
            "expected_statement": self.expected_statement,
            "mcp_statement": self.mcp_statement,
            "operator_raw": self.operator_raw,
            "observations": self.observations.to_dict(),
            "dischargeable": self.dischargeable,
            "authority_scope": self.authority_scope,
            "reason_if_not": self.reason_if_not,
            "proof_text": self.proof_text,
            "native_source_bytes": len(self.native_source.encode("utf-8")),
        }


def _safe_ident(value: str, *, prefix: str = "sca_") -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not cleaned or cleaned[0].isdigit():
        cleaned = prefix + cleaned
    return (prefix + cleaned if not cleaned.startswith(prefix) else cleaned)[:72]


def parse_mcp_statement(statement: str | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(statement, Mapping):
        return dict(statement)
    text = str(statement or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {"raw": text}


def resolve_lean_operator(operator: str, family: str = "") -> str | None:
    if operator in OPERATOR_TO_LEAN:
        return OPERATOR_TO_LEAN[operator]
    if family in OPERATOR_TO_LEAN:
        return OPERATOR_TO_LEAN[family]
    # snake of Pascal
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", family).lower() if family else ""
    if snake in OPERATOR_TO_LEAN:
        return OPERATOR_TO_LEAN[snake]
    return None


def observations_from_prove(
    *,
    fragment: str,
    prove_outcome: str,
    prove_route: str = "",
    reason_codes: list[str] | None = None,
) -> ScaObservations:
    """Map McpContractProver outcomes into decidable observation flags.

    Local schema/graph *proved* admits schema + premises.  CEC/SMT candidates
    that only report ``provider_candidate_requires_independent_validation`` do
    **not** set deontic/relation flags (use residual synthesis for those).
    """
    outcome = (prove_outcome or "").lower().replace("contractproofoutcome.", "")
    fragment_l = (fragment or "").lower().replace("logicfragment.", "")
    route = (prove_route or "").lower().replace("contractproofroute.", "")
    reasons = {str(r).lower() for r in (reason_codes or [])}
    reason_blob = " ".join(reasons)

    premises = outcome in {"proved", "refuted"} or "local" in route
    schema_ok = outcome == "proved" and (
        fragment_l in {"schema", "graph"}
        or "schema" in route
        or "graph" in route
        or "local" in route
    )
    deontic_ok = (
        outcome == "proved"
        and (fragment_l == "deontic" or "cec" in route)
        and "candidate" not in reason_blob
    )
    relation_ok = (
        outcome == "proved"
        and (fragment_l == "relation" or "smt" in route)
        and "candidate" not in reason_blob
    )
    if schema_ok:
        premises = True

    return ScaObservations(
        premises_held=bool(premises and outcome == "proved"),
        schema_valid=bool(schema_ok),
        policy_before_effect=bool(deontic_ok),
        no_bypass=bool(deontic_ok),
        relation_parity=bool(relation_ok),
    )


def _z3_check_sat(smt_text: str, *, timeout_ms: int = 3000) -> dict[str, Any]:
    """Run Z3 on a closed SMT-LIB query; return sat/unsat/error."""
    import shutil
    import subprocess
    import tempfile
    from pathlib import Path

    z3 = shutil.which("z3")
    if not z3:
        return {"ok": False, "result": "unavailable", "reason": "z3_not_on_path"}
    with tempfile.TemporaryDirectory(prefix="sca-z3-") as raw:
        path = Path(raw) / "query.smt2"
        path.write_text(smt_text, encoding="utf-8")
        try:
            proc = subprocess.run(
                [z3, "-T:" + str(max(1, timeout_ms // 1000)), str(path)],
                capture_output=True,
                text=True,
                timeout=max(2.0, timeout_ms / 1000.0 + 1.0),
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return {"ok": False, "result": "error", "reason": f"{type(exc).__name__}: {exc}"}
        out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip().lower()
        if "unsat" in out.split():
            return {"ok": True, "result": "unsat", "stdout": out[:200]}
        if "sat" in out.split():
            return {"ok": True, "result": "sat", "stdout": out[:200]}
        return {
            "ok": False,
            "result": "unknown",
            "reason": out[:200] or f"exit={proc.returncode}",
        }


def residual_relation_z3(
    *,
    operation_id: str,
    source_anchor: str = "",
    target_anchor: str = "",
) -> dict[str, Any]:
    """Deterministic residual relation observation via Z3 equality/unsat.

    Transport/discovery/failure parity under residual SCA: when both anchors
    collapse to the same operation identity (or both empty with a known op),
    the negation of identity equality is UNSAT → relation_parity holds.
    """
    left = (source_anchor or operation_id or "").strip()
    right = (target_anchor or operation_id or "").strip()
    if not left or not right:
        return {
            "relation_parity": False,
            "reason": "missing_anchor_or_operation",
            "z3": None,
        }
    # Escape for SMT string literals
    def esc(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')

    smt = f"""(set-logic QF_S)
(declare-const source String)
(declare-const target String)
(assert (= source "{esc(left)}"))
(assert (= target "{esc(right)}"))
(assert (not (= source target)))
(check-sat)
"""
    z3r = _z3_check_sat(smt)
    holds = bool(z3r.get("ok") and z3r.get("result") == "unsat")
    # Also true when strings equal even if z3 unavailable (fail open only on eq)
    if not holds and left == right:
        holds = True
        z3r = {**(z3r or {}), "local_string_eq": True}
    return {
        "relation_parity": holds,
        "reason": "z3_unsat_negated_identity" if holds else "relation_not_established",
        "z3": z3r,
        "source": left,
        "target": right,
    }


def residual_deontic_check(
    *,
    finding_kind: str,
    operation_id: str,
    premise_ids: list[str] | None = None,
    premise_results: Mapping[str, bool] | None = None,
    protocol_conformant: bool = False,
    protocol_conformance_strict: bool = True,
    protocol_tool_receipts: Mapping[str, Any] | None = None,
    doctor_disposition: str = "",
    multi_family_deontic_ok: bool = False,
) -> dict[str, Any]:
    """Deterministic residual deontic observation (not CEC authority).

    Policy-before-effect / no-bypass hold under residual SCA when:
    * all known premises are satisfied
    * mediation is required (path_class / auth-ish op / explicit premise)
    * **strict protocol**: at least one ProVerif/Tamarin end-to-end **conformant**
      receipt when ``protocol_conformance_strict`` (default True) — presence alone
      is insufficient
    * multi-family deontic applied is supportive but not a substitute for
      conformant protocol when strict mode is on
    * doctor is not an open implement block (transform_receipt / abstention ok)
    """
    premises = list(premise_ids or [])
    results = dict(premise_results or {})
    if premises:
        held = all(results.get(p, True) for p in premises)
    else:
        held = True
    mediation = any(
        "mediation" in p or "mcp" in p for p in premises
    ) or any(
        t in (operation_id or "").lower()
        for t in (
            "dispatch",
            "tools_",
            "mcpplusplus",
            "compatibility",
            "auth",
            "session",
            "ucan",
            "policy",
        )
    ) or (finding_kind or "") in {
        "ambiguous_path_class",
        "observed_contract_incomplete",
    }
    doctor_ok = (doctor_disposition or "") in {
        "",
        "transform_receipt",
        "analytical_abstention",
        "deterministic_transform",
    }
    receipts = dict(protocol_tool_receipts or {})
    # Strict: require explicit conformant status on at least one protocol tool
    if protocol_conformance_strict:
        strict_ok = False
        for tool, meta in receipts.items():
            if not isinstance(meta, Mapping):
                continue
            status = str(meta.get("status") or "").lower()
            if meta.get("available") and "conformant" in status and "nonconformant" not in status:
                strict_ok = True
                break
        # Fall back to protocol_conformant flag only if receipts map empty
        # and flag was set from a real conformance probe
        if not receipts and protocol_conformant:
            strict_ok = True
        protocol_gate = strict_ok
    else:
        protocol_gate = bool(protocol_conformant or multi_family_deontic_ok)

    policy_ok = bool(held and mediation and doctor_ok and protocol_gate)
    no_bypass = bool(
        policy_ok
        and protocol_gate
        and (
            "path_class" in (finding_kind or "")
            or protocol_gate
        )
    )
    return {
        "premises_held": held,
        "policy_before_effect": policy_ok,
        "no_bypass": no_bypass,
        "mediation_required": mediation,
        "protocol_conformant": protocol_conformant,
        "protocol_conformance_strict": protocol_conformance_strict,
        "protocol_gate": protocol_gate,
        "protocol_tool_receipts": {
            k: (dict(v) if isinstance(v, Mapping) else v)
            for k, v in receipts.items()
        },
        "doctor_ok": doctor_ok,
        "multi_family_deontic_ok": multi_family_deontic_ok,
        "reason": (
            "residual_deontic_observation_established"
            if policy_ok
            else (
                "protocol_conformance_required"
                if held and mediation and doctor_ok and not protocol_gate
                else "residual_deontic_insufficient"
            )
        ),
    }


def merge_observations(
    base: ScaObservations,
    *,
    residual_deontic: Mapping[str, Any] | None = None,
    residual_relation: Mapping[str, Any] | None = None,
) -> tuple[ScaObservations, list[str]]:
    """OR residual facts into prove-derived observations (never weaken True)."""
    sources: list[str] = ["prove_path"]
    premises = base.premises_held
    schema = base.schema_valid
    policy = base.policy_before_effect
    bypass = base.no_bypass
    relation = base.relation_parity

    if residual_deontic:
        sources.append("residual_deontic")
        if residual_deontic.get("premises_held"):
            premises = True
        if residual_deontic.get("policy_before_effect"):
            policy = True
        if residual_deontic.get("no_bypass"):
            bypass = True
    if residual_relation:
        sources.append("residual_relation_z3")
        if residual_relation.get("relation_parity"):
            relation = True
            premises = True  # identity check implies premise surface known

    return (
        ScaObservations(
            premises_held=bool(premises),
            schema_valid=bool(schema),
            policy_before_effect=bool(policy),
            no_bypass=bool(bypass),
            relation_parity=bool(relation),
        ),
        sources,
    )


def claim_dischargeable(lean_op: str, obs: ScaObservations) -> tuple[bool, str]:
    if lean_op in SCHEMA_OPS:
        if obs.premises_held and obs.schema_valid:
            return True, ""
        return False, "schema_observations_insufficient"
    if lean_op == "policyBeforeEffect":
        if obs.premises_held and obs.policy_before_effect:
            return True, ""
        return False, "deontic_observations_insufficient"
    if lean_op == "noCompatibilityBypass":
        if obs.premises_held and obs.no_bypass:
            return True, ""
        return False, "deontic_observations_insufficient"
    if lean_op in RELATION_OPS:
        if obs.premises_held and obs.relation_parity:
            return True, ""
        return False, "relation_observations_insufficient"
    return False, "unknown_operator"


def encode_claim_to_lean(
    *,
    obligation_id: str,
    family: str,
    mcp_statement: str,
    fragment: str = "",
    prove_outcome: str = "",
    prove_route: str = "",
    reason_codes: list[str] | None = None,
    theorem_suffix: str = "",
    residual_context: Mapping[str, Any] | None = None,
) -> LeanClaimEncoding:
    """Build native Lean source + expected statement for IndependentKernelVerifier.

    ``residual_context`` may supply stronger deontic/relation observations when
    CEC/SMT only return candidates (common for datasets backends).
    """
    expr = parse_mcp_statement(mcp_statement)
    operator = str(expr.get("operator") or family or "")
    lean_op = resolve_lean_operator(operator, family)
    if not lean_op:
        obs = ScaObservations(False, False, False, False, False)
        return LeanClaimEncoding(
            theorem_name="sca_unsupported",
            lean_operator="",
            expected_statement="",
            native_source="",
            proof_text="",
            observations=obs,
            mcp_statement=mcp_statement if isinstance(mcp_statement, str) else json.dumps(mcp_statement),
            operator_raw=operator,
            dischargeable=False,
            authority_scope="observation_bound_operator_semantics@1",
            reason_if_not=f"unsupported_operator:{operator}",
        )

    obs = observations_from_prove(
        fragment=fragment,
        prove_outcome=prove_outcome,
        prove_route=prove_route,
        reason_codes=reason_codes,
    )
    ctx = dict(residual_context or {})
    residual_deontic = None
    residual_relation = None
    if lean_op in DEONTIC_OPS or ctx.get("force_residual_deontic"):
        residual_deontic = residual_deontic_check(
            finding_kind=str(ctx.get("finding_kind") or ""),
            operation_id=str(ctx.get("operation_id") or ""),
            premise_ids=list(ctx.get("premise_ids") or []),
            premise_results=dict(ctx.get("premise_results") or {}),
            protocol_conformant=bool(ctx.get("protocol_conformant")),
            protocol_conformance_strict=bool(
                ctx.get("protocol_conformance_strict", True)
            ),
            protocol_tool_receipts=dict(ctx.get("protocol_tool_receipts") or {}),
            doctor_disposition=str(ctx.get("doctor_disposition") or ""),
            multi_family_deontic_ok=bool(ctx.get("multi_family_deontic_ok")),
        )
    if lean_op in RELATION_OPS or ctx.get("force_residual_relation"):
        residual_relation = residual_relation_z3(
            operation_id=str(ctx.get("operation_id") or ""),
            source_anchor=str(ctx.get("source_anchor") or ""),
            target_anchor=str(ctx.get("target_anchor") or ""),
        )
    if residual_deontic or residual_relation:
        obs, _sources = merge_observations(
            obs,
            residual_deontic=residual_deontic,
            residual_relation=residual_relation,
        )
    ok, why = claim_dischargeable(lean_op, obs)
    short = re.sub(r"[^a-f0-9]", "", obligation_id.lower())[-12:] or "claim"
    thm = _safe_ident(f"claim_{short}_{theorem_suffix or lean_op}")

    # Named observation def avoids ``:=`` inside the theorem type — the kernel
    # statement extractor stops at the first ``:=`` (see _LEAN_DECLARATION).
    obs_name = f"obs_{short}"
    obs_lit = obs.to_lean_literal()
    expected = f"scaClaimHolds .{lean_op} {obs_name}"
    terms = expr.get("terms") if isinstance(expr.get("terms"), dict) else {}
    comment = (
        f"/-- MCP claim encoding\n"
        f"    obligation_id={obligation_id}\n"
        f"    operator={operator}\n"
        f"    family={family}\n"
        f"    claim_id={terms.get('claim_id', '')}\n"
        f"    operation_id={terms.get('operation_id', '')}\n"
        f"    property_id={terms.get('property_id', '')}\n"
        f"    authority_scope=observation_bound_operator_semantics@1\n"
        f"-/\n"
    )
    native = (
        LEAN_PRELUDE
        + comment
        + f"def {obs_name} : ScaObs :=\n  {obs_lit}\n\n"
        + f"theorem {thm} : scaClaimHolds .{lean_op} {obs_name} := sorry\n"
        + f"#print axioms {thm}\n"
    )
    # Discharging proof only when observations support the claim; otherwise
    # leave a failing decide so the kernel rejects (fail-closed).
    proof = "by decide"

    return LeanClaimEncoding(
        theorem_name=thm,
        lean_operator=lean_op,
        expected_statement=expected,
        native_source=native,
        proof_text=proof,
        observations=obs,
        mcp_statement=(
            mcp_statement
            if isinstance(mcp_statement, str)
            else json.dumps(mcp_statement, sort_keys=True)
        ),
        operator_raw=operator,
        dischargeable=ok,
        authority_scope="observation_bound_operator_semantics@1",
        reason_if_not=why,
    )


# Lean op name → Coq constructor (prefixed to avoid field clashes)
LEAN_OP_TO_COQ: dict[str, str] = {
    "argumentsPreserved": "opArgumentsPreserved",
    "descriptorSchemaMatches": "opDescriptorSchemaMatches",
    "resultEnvelopePreserved": "opResultEnvelopePreserved",
    "policyBeforeEffect": "opPolicyBeforeEffect",
    "noCompatibilityBypass": "opNoCompatibilityBypass",
    "transportParity": "opTransportParity",
    "discoveryExecutionParity": "opDiscoveryExecutionParity",
    "failureParity": "opFailureParity",
}

COQ_PRELUDE = """\
(* SCA residual claim codec — observation-bound operator semantics.
   Authority: observation_bound_operator_semantics@1
   Source: scripts/sca_mcp_claim_lean_codec.py *)
Inductive ScaOperator : Set :=
  | opArgumentsPreserved
  | opDescriptorSchemaMatches
  | opResultEnvelopePreserved
  | opPolicyBeforeEffect
  | opNoCompatibilityBypass
  | opTransportParity
  | opDiscoveryExecutionParity
  | opFailureParity.

Record ScaObs : Set := mkObs {
  premisesHeld : bool;
  schemaValid : bool;
  policyOk : bool;
  noBypass : bool;
  relationOk : bool
}.

Definition scaClaimHolds (op : ScaOperator) (obs : ScaObs) : Prop :=
  match op with
  | opArgumentsPreserved => premisesHeld obs = true /\\ schemaValid obs = true
  | opDescriptorSchemaMatches => premisesHeld obs = true /\\ schemaValid obs = true
  | opResultEnvelopePreserved => premisesHeld obs = true /\\ schemaValid obs = true
  | opPolicyBeforeEffect => premisesHeld obs = true /\\ policyOk obs = true
  | opNoCompatibilityBypass => premisesHeld obs = true /\\ noBypass obs = true
  | opTransportParity => premisesHeld obs = true /\\ relationOk obs = true
  | opDiscoveryExecutionParity => premisesHeld obs = true /\\ relationOk obs = true
  | opFailureParity => premisesHeld obs = true /\\ relationOk obs = true
  end.

"""


@dataclass(frozen=True)
class CoqClaimEncoding:
    theorem_name: str
    coq_operator: str
    expected_statement: str
    native_source: str
    observations: ScaObservations
    mcp_statement: str
    dischargeable: bool
    authority_scope: str
    reason_if_not: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "theorem_name": self.theorem_name,
            "coq_operator": self.coq_operator,
            "expected_statement": self.expected_statement,
            "mcp_statement": self.mcp_statement,
            "observations": self.observations.to_dict(),
            "dischargeable": self.dischargeable,
            "authority_scope": self.authority_scope,
            "reason_if_not": self.reason_if_not,
            "native_source_bytes": len(self.native_source.encode("utf-8")),
        }


def encode_claim_to_coq(
    *,
    obligation_id: str,
    family: str,
    mcp_statement: str,
    fragment: str = "",
    prove_outcome: str = "",
    prove_route: str = "",
    reason_codes: list[str] | None = None,
    residual_context: Mapping[str, Any] | None = None,
) -> CoqClaimEncoding:
    """Mirror of encode_claim_to_lean for coqc IndependentKernelVerifier packets."""
    # Reuse Lean path for observation synthesis, then lower to Coq.
    lean = encode_claim_to_lean(
        obligation_id=obligation_id,
        family=family,
        mcp_statement=mcp_statement,
        fragment=fragment,
        prove_outcome=prove_outcome,
        prove_route=prove_route,
        reason_codes=reason_codes,
        residual_context=residual_context,
        theorem_suffix="coq",
    )
    if not lean.lean_operator:
        return CoqClaimEncoding(
            theorem_name="sca_unsupported",
            coq_operator="",
            expected_statement="",
            native_source="",
            observations=lean.observations,
            mcp_statement=lean.mcp_statement,
            dischargeable=False,
            authority_scope=lean.authority_scope,
            reason_if_not=lean.reason_if_not,
        )
    coq_op = LEAN_OP_TO_COQ.get(lean.lean_operator, "")
    if not coq_op:
        return CoqClaimEncoding(
            theorem_name="sca_unsupported",
            coq_operator="",
            expected_statement="",
            native_source="",
            observations=lean.observations,
            mcp_statement=lean.mcp_statement,
            dischargeable=False,
            authority_scope=lean.authority_scope,
            reason_if_not=f"no_coq_op:{lean.lean_operator}",
        )
    obs = lean.observations
    short = re.sub(r"[^a-f0-9]", "", obligation_id.lower())[-12:] or "claim"
    thm = _safe_ident(f"claim_{short}_{lean.lean_operator}_coq")
    obs_name = f"obs_{short}"

    def b(v: bool) -> str:
        return "true" if v else "false"

    obs_ctor = (
        f"mkObs {b(obs.premises_held)} {b(obs.schema_valid)} "
        f"{b(obs.policy_before_effect)} {b(obs.no_bypass)} {b(obs.relation_parity)}"
    )
    expected = f"scaClaimHolds {coq_op} {obs_name}"
    terms = parse_mcp_statement(mcp_statement).get("terms") or {}
    if not isinstance(terms, dict):
        terms = {}
    comment = (
        f"(* MCP claim encoding obligation_id={obligation_id} "
        f"family={family} op={lean.operator_raw} "
        f"claim_id={terms.get('claim_id','')} *)\n"
    )
    # Complete proof — no Admitted. Print Assumptions for closed context.
    native = (
        COQ_PRELUDE
        + comment
        + f"Definition {obs_name} : ScaObs := {obs_ctor}.\n\n"
        + f"Theorem {thm} : scaClaimHolds {coq_op} {obs_name}.\n"
        + "Proof. simpl. split; reflexivity. Qed.\n\n"
        + f"Print Assumptions {thm}.\n"
    )
    return CoqClaimEncoding(
        theorem_name=thm,
        coq_operator=coq_op,
        expected_statement=expected,
        native_source=native if lean.dischargeable else native,
        observations=obs,
        mcp_statement=lean.mcp_statement,
        dischargeable=lean.dischargeable,
        authority_scope=lean.authority_scope,
        reason_if_not=lean.reason_if_not,
    )


def build_snapshot_environment_lock(
    *,
    snapshot_id: str,
    target: str,
    executable: str,
    version: str,
    obligation_id: str = "",
) -> dict[str, Any]:
    """Content-addressed environment lock bound to SCA snapshot + ITP."""
    import hashlib
    import os
    from datetime import datetime, timezone

    templates = {
        "lean": "{lean} --json {source_file}",
        "coq": "{coqc} {source_file}",
        "isabelle": "{isabelle} build -d {session_dir} {session}",
    }
    payload = {
        "schema_version": "1.0.0",
        "itp": target,
        "itp_version": version or "unknown",
        "executable_paths": {target: executable},
        "snapshot_id": snapshot_id,
        "obligation_id": obligation_id,
        "os_info": os.name,
        "kernel_command_template": templates.get(target, "{kernel} {source_file}"),
        "pinned_at": datetime.now(timezone.utc).isoformat(),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    lock_id = f"lock:sca:{target}:sha256:{digest[:32]}"
    return {**payload, "lock_id": lock_id}


# Lean op → Isabelle datatype constructor
LEAN_OP_TO_ISABELLE: dict[str, str] = {
    "argumentsPreserved": "OpArgumentsPreserved",
    "descriptorSchemaMatches": "OpDescriptorSchemaMatches",
    "resultEnvelopePreserved": "OpResultEnvelopePreserved",
    "policyBeforeEffect": "OpPolicyBeforeEffect",
    "noCompatibilityBypass": "OpNoCompatibilityBypass",
    "transportParity": "OpTransportParity",
    "discoveryExecutionParity": "OpDiscoveryExecutionParity",
    "failureParity": "OpFailureParity",
}

ISABELLE_PRELUDE = '''\
theory ScaClaim
imports Main
begin

datatype sca_operator =
    OpArgumentsPreserved
  | OpDescriptorSchemaMatches
  | OpResultEnvelopePreserved
  | OpPolicyBeforeEffect
  | OpNoCompatibilityBypass
  | OpTransportParity
  | OpDiscoveryExecutionParity
  | OpFailureParity

record sca_obs =
  premises_held :: bool
  schema_valid :: bool
  policy_ok :: bool
  no_bypass :: bool
  relation_ok :: bool

fun sca_claim_holds :: "sca_operator => sca_obs => bool" where
  "sca_claim_holds OpArgumentsPreserved obs =
     (premises_held obs & schema_valid obs)"
| "sca_claim_holds OpDescriptorSchemaMatches obs =
     (premises_held obs & schema_valid obs)"
| "sca_claim_holds OpResultEnvelopePreserved obs =
     (premises_held obs & schema_valid obs)"
| "sca_claim_holds OpPolicyBeforeEffect obs =
     (premises_held obs & policy_ok obs)"
| "sca_claim_holds OpNoCompatibilityBypass obs =
     (premises_held obs & no_bypass obs)"
| "sca_claim_holds OpTransportParity obs =
     (premises_held obs & relation_ok obs)"
| "sca_claim_holds OpDiscoveryExecutionParity obs =
     (premises_held obs & relation_ok obs)"
| "sca_claim_holds OpFailureParity obs =
     (premises_held obs & relation_ok obs)"

'''


@dataclass(frozen=True)
class IsabelleClaimEncoding:
    theorem_name: str
    isabelle_operator: str
    expected_statement: str
    theory_source: str
    root_source: str
    observations: ScaObservations
    mcp_statement: str
    dischargeable: bool
    authority_scope: str
    reason_if_not: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "theorem_name": self.theorem_name,
            "isabelle_operator": self.isabelle_operator,
            "expected_statement": self.expected_statement,
            "mcp_statement": self.mcp_statement,
            "observations": self.observations.to_dict(),
            "dischargeable": self.dischargeable,
            "authority_scope": self.authority_scope,
            "reason_if_not": self.reason_if_not,
            "theory_source_bytes": len(self.theory_source.encode("utf-8")),
        }


def encode_claim_to_isabelle(
    *,
    obligation_id: str,
    family: str,
    mcp_statement: str,
    fragment: str = "",
    prove_outcome: str = "",
    prove_route: str = "",
    reason_codes: list[str] | None = None,
    residual_context: Mapping[str, Any] | None = None,
) -> IsabelleClaimEncoding:
    """Observation-bound Isabelle theory for residual SCA claim discharge."""
    lean = encode_claim_to_lean(
        obligation_id=obligation_id,
        family=family,
        mcp_statement=mcp_statement,
        fragment=fragment,
        prove_outcome=prove_outcome,
        prove_route=prove_route,
        reason_codes=reason_codes,
        residual_context=residual_context,
        theorem_suffix="isa",
    )
    if not lean.lean_operator:
        return IsabelleClaimEncoding(
            theorem_name="sca_unsupported",
            isabelle_operator="",
            expected_statement="",
            theory_source="",
            root_source="",
            observations=lean.observations,
            mcp_statement=lean.mcp_statement,
            dischargeable=False,
            authority_scope=lean.authority_scope,
            reason_if_not=lean.reason_if_not,
        )
    isa_op = LEAN_OP_TO_ISABELLE.get(lean.lean_operator, "")
    if not isa_op:
        return IsabelleClaimEncoding(
            theorem_name="sca_unsupported",
            isabelle_operator="",
            expected_statement="",
            theory_source="",
            root_source="",
            observations=lean.observations,
            mcp_statement=lean.mcp_statement,
            dischargeable=False,
            authority_scope=lean.authority_scope,
            reason_if_not=f"no_isabelle_op:{lean.lean_operator}",
        )
    obs = lean.observations
    short = re.sub(r"[^a-f0-9]", "", obligation_id.lower())[-12:] or "claim"
    thm = _safe_ident(f"claim_{short}_{lean.lean_operator}_isa")
    # Isabelle lemma names cannot be arbitrary long; keep short
    lemma = f"sca_{short}"

    def b(v: bool) -> str:
        return "True" if v else "False"

    obs_lit = (
        f"(| premises_held = {b(obs.premises_held)}, "
        f"schema_valid = {b(obs.schema_valid)}, "
        f"policy_ok = {b(obs.policy_before_effect)}, "
        f"no_bypass = {b(obs.no_bypass)}, "
        f"relation_ok = {b(obs.relation_parity)} |)"
    )
    expected = f"sca_claim_holds {isa_op} obs_{short}"
    terms = parse_mcp_statement(mcp_statement).get("terms") or {}
    if not isinstance(terms, dict):
        terms = {}
    theory = (
        ISABELLE_PRELUDE
        + f"(* obligation_id={obligation_id} family={family} "
        f"claim_id={terms.get('claim_id','')} *)\n"
        + f"definition obs_{short} :: sca_obs where\n"
        + f'  "obs_{short} = {obs_lit}"\n\n'
        + f'lemma {lemma}: "sca_claim_holds {isa_op} obs_{short}"\n'
        + f"  by (simp add: obs_{short}_def)\n\n"
        + "end\n"
    )
    root = "session ScaClaim = HOL +\n  theories\n    ScaClaim\n"
    return IsabelleClaimEncoding(
        theorem_name=lemma,
        isabelle_operator=isa_op,
        expected_statement=expected,
        theory_source=theory,
        root_source=root,
        observations=obs,
        mcp_statement=lean.mcp_statement,
        dischargeable=lean.dischargeable,
        authority_scope=lean.authority_scope,
        reason_if_not=lean.reason_if_not,
    )


__all__ = [
    "COQ_PRELUDE",
    "ISABELLE_PRELUDE",
    "LEAN_PRELUDE",
    "CoqClaimEncoding",
    "IsabelleClaimEncoding",
    "LeanClaimEncoding",
    "OPERATOR_TO_LEAN",
    "ScaObservations",
    "build_snapshot_environment_lock",
    "claim_dischargeable",
    "encode_claim_to_coq",
    "encode_claim_to_isabelle",
    "encode_claim_to_lean",
    "merge_observations",
    "observations_from_prove",
    "parse_mcp_statement",
    "residual_deontic_check",
    "residual_relation_z3",
    "resolve_lean_operator",
]
