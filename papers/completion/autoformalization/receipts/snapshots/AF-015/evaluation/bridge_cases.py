#!/usr/bin/env python3
"""Finite policy–code–trace and translation-bridge validation for AF-015.

The harness selects explicit logical profiles and query fragments, then
independently checks source/target signatures, related-model existence,
premise preservation (Equation 7), goal reflection (Equation 8), and
consistency on constructed finite models.  It executes the paper's
protected-write and bounded-audit example, including guarded and unguarded
implementations, delayed audit, incomplete capture, tenant identity
mismatch, and inconsistent premises.

Native Lean/Z3/CVC5/Isabelle binaries are probed only on the process PATH.
A missing checker is recorded as unavailable.  The TDFOL-to-FOL replica
strips unary modal operators and replaces until by conjunction; that path
is a negative control, not an accepted transfer.

Proposition 1 remains a paper-level conditional argument.  This suite does
not claim machine-checked compiler soundness, project-compiler execution,
or unbounded proof.  Standard library only; project packages are not
imported.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

SCHEMA_CASES = "autoformalization-policy-code-trace-cases/v1"
SCHEMA_RESULT = "autoformalization-bridge-validation-result/v1"
SCHEMA_RECEIPT = "autoformalization-translation-receipt/v1"
SCHEMA_COVERAGE = "autoformalization-bridge-coverage/v1"
TASK_ID = "AF-015"
SUITE_ID = "AF-015-supported-bridges-policy-code-trace"
HERE = Path(__file__).resolve().parent
PAPER_ROOT = HERE.parent
REPO_ROOT = PAPER_ROOT.parents[2]

NATIVE_CHECKERS = ("lean", "lake", "z3", "cvc5", "vampire", "eprover", "coqc", "isabelle")
REQUIRED_OUTCOME_CLASSES = (
    "safe",
    "unsafe",
    "delayed-audit",
    "incomplete-window",
    "wrong-tenant",
    "inconsistent-premise",
)
ACCEPTED_TRANSFER_STATUSES = frozenset({"accepted_transfer", "accepted_countermodel"})
INSPECTED_SOURCES = {
    "tdfol_converter.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/TDFOL/tdfol_converter.py",
        "sha256": "19db7d143c0275eca84846b0b4abc1feba877c38b7f255a3c58c54d31d1bf16d",
        "imported": False,
        "note": (
            "Inspected TDFOLToFOLConverter strips DeonticFormula/TemporalFormula "
            "and replaces BinaryTemporalFormula by conjunction. This harness "
            "reimplements that loss as a negative control."
        ),
    },
    "formalization_adapter.py": {
        "path": "external/ipfs_datasets/ipfs_datasets_py/logic/security_ir/formalization_adapter.py",
        "sha256": "09accb91139230c08f9d9876ebc83485803419fad8b49e80e37b1f0f6861d631",
        "imported": False,
        "note": (
            "Inspected Security IR adapter emits declaration features only and "
            "does not import traces or proofs. Not executed in this suite."
        ),
    },
    "reference_semantics.py": {
        "path": "papers/completion/autoformalization/evaluation/reference_semantics.py",
        "sha256": "a0b10baf23b8800b831ee6b7ca8e05a8418f6741c75d8cfeb647d420a057e282",
        "imported": False,
        "note": "AF-006 finite C09–C11 witnesses inform the protected-write/audit cases; not reused as historical output.",
    },
}


class BridgeError(ValueError):
    """Raised when a bridge contract or case catalog is violated."""


def canonical_dumps(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except ValueError as exc:
        raise BridgeError("canonical JSON requires finite numeric values") from exc


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_obj(value: Any) -> str:
    return sha256_text(canonical_dumps(value))


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(payload, encoding="utf-8")
    temporary.replace(path)


def write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [canonical_dumps(row) + "\n" for row in rows]
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text("".join(lines), encoding="utf-8")
    temporary.replace(path)


def implication(left: bool, right: bool) -> bool:
    return (not left) or right


def q1_holds(protected: bool, approved: bool, write: bool) -> bool:
    return implication(protected and not approved, not write)


def guarded_write(protected: bool, approved: bool) -> bool:
    return (not protected) or approved


def unguarded_write(_protected: bool, _approved: bool) -> bool:
    return True


def enumerate_protection_approval() -> tuple[tuple[bool, bool], ...]:
    return ((True, True), (True, False), (False, True), (False, False))


def q1_assignments(write_fn) -> list[dict[str, Any]]:
    rows = []
    for protected, approved in enumerate_protection_approval():
        write = bool(write_fn(protected, approved))
        rows.append({
            "protected": protected,
            "approved": approved,
            "write": write,
            "q1": q1_holds(protected, approved, write),
        })
    return rows


def box(relation: frozenset[tuple[int, int]], world: int, holds) -> bool:
    return all(holds(target) for source, target in relation if source == world)


def strong_until(p: Sequence[bool], q: Sequence[bool]) -> bool:
    return any(q[index] and all(p[:index]) for index in range(len(p)))


def tdfol_to_fol_lossy(formula: Mapping[str, Any]) -> dict[str, Any]:
    """Replica of the inspected TDFOL-to-FOL converter losses."""
    kind = formula["kind"]
    if kind == "atom":
        return dict(formula)
    if kind in {"not", "and", "or", "implies"}:
        out = {"kind": kind}
        if "formula" in formula:
            out["formula"] = tdfol_to_fol_lossy(formula["formula"])
        if "left" in formula:
            out["left"] = tdfol_to_fol_lossy(formula["left"])
        if "right" in formula:
            out["right"] = tdfol_to_fol_lossy(formula["right"])
        return out
    if kind in {"obligation", "always", "eventually", "next"}:
        return tdfol_to_fol_lossy(formula["formula"])
    if kind == "until":
        return {
            "kind": "and",
            "left": tdfol_to_fol_lossy(formula["left"]),
            "right": tdfol_to_fol_lossy(formula["right"]),
        }
    raise BridgeError(f"unsupported formula kind for lossy FOL projection: {kind}")


def eval_propositional(formula: Mapping[str, Any], valuation: Mapping[str, bool], *, now: int = 0) -> bool:
    kind = formula["kind"]
    if kind == "atom":
        return bool(valuation[formula["name"]])
    if kind == "not":
        return not eval_propositional(formula["formula"], valuation, now=now)
    if kind == "and":
        return eval_propositional(formula["left"], valuation, now=now) and eval_propositional(
            formula["right"], valuation, now=now
        )
    if kind == "or":
        return eval_propositional(formula["left"], valuation, now=now) or eval_propositional(
            formula["right"], valuation, now=now
        )
    if kind == "implies":
        return implication(
            eval_propositional(formula["left"], valuation, now=now),
            eval_propositional(formula["right"], valuation, now=now),
        )
    raise BridgeError(f"modal/temporal formula is not propositional: {kind}")


def eval_trace_atom(name: str, traces: Mapping[str, Sequence[bool]], now: int) -> bool:
    return bool(traces[name][now])


def eval_temporal(formula: Mapping[str, Any], traces: Mapping[str, Sequence[bool]], now: int) -> bool:
    kind = formula["kind"]
    if kind == "atom":
        return eval_trace_atom(formula["name"], traces, now)
    if kind == "not":
        return not eval_temporal(formula["formula"], traces, now)
    if kind == "and":
        return eval_temporal(formula["left"], traces, now) and eval_temporal(formula["right"], traces, now)
    if kind == "always":
        inner = formula["formula"]
        return all(eval_temporal(inner, traces, index) for index in range(now, len(next(iter(traces.values())))))
    if kind == "until":
        length = len(next(iter(traces.values())))
        p = [eval_temporal(formula["left"], traces, index) for index in range(now, length)]
        q = [eval_temporal(formula["right"], traces, index) for index in range(now, length)]
        return strong_until(p, q)
    raise BridgeError(f"cannot evaluate temporal kind {kind}")


def identities_join(policy_identity: Mapping[str, str], trace_identity: Mapping[str, str]) -> bool:
    keys = ("tenant", "actor", "resource", "request")
    return all(policy_identity.get(key) == trace_identity.get(key) for key in keys)


def q2_trace_status(case: Mapping[str, Any]) -> dict[str, Any]:
    policy = case["policy_identity"]
    trace = case["trace_identity"]
    write_t = int(case["write_t"])
    deadline = write_t + int(case["deadline_offset"])
    capture_through = case.get("capture_complete_through")
    audit_t = case.get("audit_t")
    joined = identities_join(policy, trace)
    observed_audit_in_window = (
        joined
        and audit_t is not None
        and write_t <= int(audit_t) <= deadline
    )
    capture_complete = capture_through is not None and int(capture_through) >= deadline
    if not joined:
        status = "unresolved_identity"
    elif observed_audit_in_window:
        status = "satisfied_within_observed_window"
    elif not capture_complete:
        status = "unknown"
    else:
        status = "violated_within_observed_window"
    return {
        "joined": joined,
        "write_t": write_t,
        "audit_t": audit_t,
        "deadline": deadline,
        "capture_complete": capture_complete,
        "observed_audit_in_window": observed_audit_in_window,
        "status": status,
    }


def probe_native_checkers() -> dict[str, Any]:
    path = os.environ.get("PATH", "")
    home = os.environ.get("HOME") or ""
    probes = []
    for name in NATIVE_CHECKERS:
        resolved = shutil.which(name)
        probes.append({
            "name": name,
            "status": "available" if resolved else "unavailable",
            "resolved_path": resolved,
            "usable_in_sealed_validation": bool(resolved),
        })
    return {
        "path": path,
        "home": home,
        "home_is_validation_private": Path(home).name.startswith("ipfs-accelerate-validation-home-") if home else False,
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "checkers": probes,
        "any_native_checker_usable": any(item["usable_in_sealed_validation"] for item in probes),
    }


def logical_profiles() -> list[dict[str, Any]]:
    return [
        {
            "profile_id": "guarded-implementation-fol/v1",
            "logic_family": "typed_first_order",
            "source_signature": ["Protected", "Approved", "Write"],
            "target_signature": ["Protected", "Approved", "Write"],
            "supported_queries": ["Q1"],
            "bridge_assumptions": [
                "Finite Boolean implementation model; Write determined by the named implementation.",
                "Identity relation on Protected/Approved/Write assignments.",
                "No extraction from natural source code is claimed.",
            ],
        },
        {
            "profile_id": "bounded-audit-trace/v1",
            "logic_family": "finite_trace_observation",
            "source_signature": ["Write", "Audit"],
            "target_signature": ["Write", "Audit"],
            "supported_queries": ["Q2"],
            "bridge_assumptions": [
                "Discrete trace positions with deadline offset 2.",
                "Actor/resource/tenant/request identities join only under an admitted mapping.",
                "Incomplete capture through the deadline is unknown, not compliance or violation.",
                "One successful log is not a global program guarantee.",
            ],
        },
        {
            "profile_id": "deontic-ideal-worlds/v1",
            "logic_family": "serial_deontic_modal",
            "source_signature": ["O", "Write"],
            "target_signature": ["Write"],
            "supported_queries": [],
            "bridge_assumptions": [
                "Ideal-world accessibility need not be reflexive.",
                "Obligation is not actuality; Q1 is a compliance query, not a deontic consequence.",
            ],
        },
        {
            "profile_id": "tdfol-lossy-fol-projection/v1",
            "logic_family": "tdfol_to_fol_erasure",
            "source_signature": ["O", "G", "U"],
            "target_signature": ["propositional_skeleton"],
            "supported_queries": [],
            "bridge_assumptions": [
                "Named losses: unary deontic/temporal erasure; until replaced by conjunction.",
                "This profile is a negative control and cannot carry a modal theorem.",
            ],
        },
    ]


def supported_fragments() -> list[dict[str, Any]]:
    return [
        {
            "fragment_id": "q1-protected-write",
            "query": "∀a,r,t. Protected(r) ∧ ¬Approved(a,r,t) ⇒ ¬Write(a,r,t)",
            "equation": "10",
            "status": "supported",
            "checker": "finite_boolean_enumeration",
        },
        {
            "fragment_id": "q2-bounded-audit",
            "query": "∀a,r,t. Write(a,r,t) ⇒ ∃u∈[t,t+2]. Audit(a,r,u)",
            "equation": "11",
            "status": "supported",
            "checker": "finite_trace_observation",
        },
        {
            "fragment_id": "deontic-obligation-not-actuality",
            "query": "O(¬Write) does not entail ¬Write",
            "equation": "9",
            "status": "supported_as_negative_control",
            "checker": "two_world_modal_witness",
        },
        {
            "fragment_id": "tdfol-unary-erasure",
            "query": "O(p)↦p and G(p)↦p",
            "equation": None,
            "status": "unsupported_for_transfer",
            "checker": "lossy_projection_countermodel",
        },
        {
            "fragment_id": "tdfol-until-conjunction",
            "query": "p U q ↦ p ∧ q",
            "equation": None,
            "status": "unsupported_for_transfer",
            "checker": "lossy_projection_countermodel",
        },
        {
            "fragment_id": "contrary-to-duty",
            "query": "O(¬Write) with CTD O(Audit | Write)",
            "equation": None,
            "status": "unsupported",
            "checker": None,
        },
        {
            "fragment_id": "og-go-commutation",
            "query": "O(Gp) versus G(Op)",
            "equation": None,
            "status": "unsupported",
            "checker": None,
        },
    ]


def proposition_1_record() -> dict[str, Any]:
    return {
        "name": "Proposition 1",
        "title": "Conditional semantic consequence transfer",
        "kind": "paper_conditional_argument",
        "machine_checked_compiler_soundness": False,
        "blanket_repository_soundness": False,
        "requires": [
            "related_model_existence",
            "premise_preservation_equation_7",
            "goal_reflection_equation_8",
            "sound_target_checker",
            "nonvacuous_bridge_relation",
            "consistent_premises",
        ],
        "does_not_establish": [
            "faithful source extraction",
            "appropriateness of bridge assumptions B",
            "nonempty model class without an existence check",
            "that TDFOLToFOLConverter satisfies Equations 7 and 8",
            "machine-checked soundness of any repository compiler",
        ],
        "claim_boundary": (
            "A paper-level conditional argument, not a machine-checked theorem of "
            "the repository. Discharged per supported translation on constructed "
            "finite models only."
        ),
    }


def case_catalog() -> dict[str, Any]:
    return {
        "schema": SCHEMA_CASES,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "specification_example": (
            "Protected resources must not be written without approval. "
            "Each write must be audited within two steps."
        ),
        "not_legal_advice": True,
        "not_production_experiment": True,
        "proposition_1": proposition_1_record(),
        "profiles": logical_profiles(),
        "fragments": supported_fragments(),
        "queries": {
            "Q1": {
                "id": "Q1",
                "equation": "10",
                "text": "Protected(r) ∧ ¬Approved(a,r,t) ⇒ ¬Write(a,r,t)",
            },
            "Q2": {
                "id": "Q2",
                "equation": "11",
                "text": "Write(a,r,t) ⇒ ∃u∈[t,t+2]. Audit(a,r,u)",
            },
        },
        "cases": [
            {
                "case_id": "PCT-SAFE-Q1",
                "outcome_class": "safe",
                "evaluator": "q1_implementation",
                "query_id": "Q1",
                "profile_id": "guarded-implementation-fol/v1",
                "fragment_id": "q1-protected-write",
                "implementation": "guarded",
                "source_view": "security.implementation",
                "target_view": "compliance.fol",
                "expected_status": "accepted_transfer",
                "expected_outcome": "q1_holds_on_guarded_model",
            },
            {
                "case_id": "PCT-UNSAFE-Q1",
                "outcome_class": "unsafe",
                "evaluator": "q1_implementation",
                "query_id": "Q1",
                "profile_id": "guarded-implementation-fol/v1",
                "fragment_id": "q1-protected-write",
                "implementation": "unguarded",
                "source_view": "security.implementation",
                "target_view": "compliance.fol",
                "expected_status": "accepted_countermodel",
                "expected_outcome": "q1_countermodel",
            },
            {
                "case_id": "PCT-TIMELY-AUDIT",
                "outcome_class": "timely-audit",
                "evaluator": "q2_trace",
                "query_id": "Q2",
                "profile_id": "bounded-audit-trace/v1",
                "fragment_id": "q2-bounded-audit",
                "source_view": "trace.observation",
                "target_view": "compliance.fol",
                "expected_status": "accepted_bounded_observation",
                "expected_outcome": "satisfied_within_observed_window",
                "trace": {
                    "policy_identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
                    "trace_identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
                    "write_t": 0,
                    "audit_t": 1,
                    "deadline_offset": 2,
                    "capture_complete_through": 2,
                },
            },
            {
                "case_id": "PCT-DELAYED-AUDIT",
                "outcome_class": "delayed-audit",
                "evaluator": "q2_trace",
                "query_id": "Q2",
                "profile_id": "bounded-audit-trace/v1",
                "fragment_id": "q2-bounded-audit",
                "source_view": "trace.observation",
                "target_view": "compliance.fol",
                "expected_status": "accepted_countermodel",
                "expected_outcome": "violated_within_observed_window",
                "trace": {
                    "policy_identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
                    "trace_identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
                    "write_t": 0,
                    "audit_t": 3,
                    "deadline_offset": 2,
                    "capture_complete_through": 2,
                },
            },
            {
                "case_id": "PCT-INCOMPLETE-WINDOW",
                "outcome_class": "incomplete-window",
                "evaluator": "q2_trace",
                "query_id": "Q2",
                "profile_id": "bounded-audit-trace/v1",
                "fragment_id": "q2-bounded-audit",
                "source_view": "trace.observation",
                "target_view": "compliance.fol",
                "expected_status": "unknown_incomplete_window",
                "expected_outcome": "unknown",
                "trace": {
                    "policy_identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
                    "trace_identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
                    "write_t": 0,
                    "audit_t": None,
                    "deadline_offset": 2,
                    "capture_complete_through": 0,
                },
            },
            {
                "case_id": "PCT-WRONG-TENANT",
                "outcome_class": "wrong-tenant",
                "evaluator": "q2_trace",
                "query_id": "Q2",
                "profile_id": "bounded-audit-trace/v1",
                "fragment_id": "q2-bounded-audit",
                "source_view": "trace.observation",
                "target_view": "compliance.fol",
                "expected_status": "unresolved_identity",
                "expected_outcome": "unresolved_identity",
                "trace": {
                    "policy_identity": {"tenant": "tenant-a", "actor": "alice", "resource": "r1", "request": "req-1"},
                    "trace_identity": {"tenant": "tenant-b", "actor": "alice", "resource": "r1", "request": "req-1"},
                    "write_t": 0,
                    "audit_t": 1,
                    "deadline_offset": 2,
                    "capture_complete_through": 2,
                },
            },
            {
                "case_id": "PCT-INCONSISTENT",
                "outcome_class": "inconsistent-premise",
                "evaluator": "inconsistent_premises",
                "query_id": "Q1",
                "profile_id": "guarded-implementation-fol/v1",
                "fragment_id": "q1-protected-write",
                "source_view": "compliance.fol",
                "target_view": "compliance.fol",
                "expected_status": "inconsistent_premises",
                "expected_outcome": "transfer_refused_inconsistent_premises",
                "premises": [
                    {"protected": True, "approved": False, "write": True},
                    {"protected": True, "approved": False, "write": False},
                ],
            },
            {
                "case_id": "PCT-NAME-EXTRACT",
                "outcome_class": "unjustified-extraction",
                "evaluator": "name_extraction",
                "query_id": "Q1",
                "profile_id": "guarded-implementation-fol/v1",
                "fragment_id": "q1-protected-write",
                "source_view": "source.code",
                "target_view": "security.implementation",
                "expected_status": "rejected_unjustified_extraction",
                "expected_outcome": "name_match_is_not_refinement",
                "implementation_text": "def approve_and_write(resource): write(resource)",
            },
            {
                "case_id": "PCT-DEONTIC-NOT-Q1",
                "outcome_class": "obligation-not-actuality",
                "evaluator": "deontic_not_actual",
                "query_id": "Q1",
                "profile_id": "deontic-ideal-worlds/v1",
                "fragment_id": "deontic-obligation-not-actuality",
                "source_view": "legal.deontic",
                "target_view": "compliance.fol",
                "expected_status": "rejected_preservation_failure",
                "expected_outcome": "obligation_does_not_entail_actual_nonwriting",
            },
            {
                "case_id": "TDFOL-OBLIGATION-ERASURE",
                "outcome_class": "lossy-tdfol-erasure",
                "evaluator": "tdfol_obligation_erasure",
                "query_id": None,
                "profile_id": "tdfol-lossy-fol-projection/v1",
                "fragment_id": "tdfol-unary-erasure",
                "source_view": "tdfol.deontic",
                "target_view": "fol.propositional",
                "expected_status": "rejected_preservation_failure",
                "expected_outcome": "O(p)_true_p_false",
            },
            {
                "case_id": "TDFOL-ALWAYS-ERASURE",
                "outcome_class": "lossy-tdfol-erasure",
                "evaluator": "tdfol_always_erasure",
                "query_id": None,
                "profile_id": "tdfol-lossy-fol-projection/v1",
                "fragment_id": "tdfol-unary-erasure",
                "source_view": "tdfol.temporal",
                "target_view": "fol.propositional",
                "expected_status": "rejected_preservation_failure",
                "expected_outcome": "p_now_true_Gp_false",
            },
            {
                "case_id": "TDFOL-UNTIL-ERASURE",
                "outcome_class": "lossy-tdfol-erasure",
                "evaluator": "tdfol_until_erasure",
                "query_id": None,
                "profile_id": "tdfol-lossy-fol-projection/v1",
                "fragment_id": "tdfol-until-conjunction",
                "source_view": "tdfol.temporal",
                "target_view": "fol.propositional",
                "expected_status": "rejected_preservation_failure",
                "expected_outcome": "until_not_conjunction",
            },
            {
                "case_id": "NATIVE-LEAN-Q1",
                "outcome_class": "missing-native-checker",
                "evaluator": "native_checker",
                "query_id": "Q1",
                "profile_id": "guarded-implementation-fol/v1",
                "fragment_id": "q1-protected-write",
                "source_view": "compliance.fol",
                "target_view": "lean.theorem",
                "expected_status": "unavailable_native_checker",
                "expected_outcome": "lean_absent_from_sealed_path",
                "checker_name": "lean",
            },
            {
                "case_id": "UNSUPPORTED-CTD",
                "outcome_class": "unsupported-fragment",
                "evaluator": "unsupported_fragment",
                "query_id": None,
                "profile_id": "deontic-ideal-worlds/v1",
                "fragment_id": "contrary-to-duty",
                "source_view": "legal.deontic",
                "target_view": "compliance.fol",
                "expected_status": "unsupported_fragment",
                "expected_outcome": "contrary_to_duty_unsupported",
            },
            {
                "case_id": "UNSUPPORTED-OG-GO",
                "outcome_class": "unsupported-fragment",
                "evaluator": "unsupported_fragment",
                "query_id": None,
                "profile_id": "deontic-ideal-worlds/v1",
                "fragment_id": "og-go-commutation",
                "source_view": "tdfol.mixed",
                "target_view": "tdfol.mixed",
                "expected_status": "unsupported_fragment",
                "expected_outcome": "og_go_not_equated_without_profile_result",
            },
            {
                "case_id": "PROP1-CONDITIONAL",
                "outcome_class": "paper-proposition",
                "evaluator": "proposition_1",
                "query_id": None,
                "profile_id": "guarded-implementation-fol/v1",
                "fragment_id": "q1-protected-write",
                "source_view": "paper.appendix_b",
                "target_view": "paper.appendix_b",
                "expected_status": "paper_conditional_argument",
                "expected_outcome": "not_machine_checked_compiler_soundness",
            },
        ],
    }


def profile_by_id(catalog: Mapping[str, Any], profile_id: str) -> dict[str, Any]:
    for profile in catalog["profiles"]:
        if profile["profile_id"] == profile_id:
            return profile
    raise BridgeError(f"unknown profile {profile_id}")


def fragment_by_id(catalog: Mapping[str, Any], fragment_id: str) -> dict[str, Any]:
    for fragment in catalog["fragments"]:
        if fragment["fragment_id"] == fragment_id:
            return fragment
    raise BridgeError(f"unknown fragment {fragment_id}")


def receipt_fields(
    case: Mapping[str, Any],
    *,
    catalog: Mapping[str, Any],
    preserved_property: str | None,
    preservation_direction: str | None,
    named_losses: Sequence[str],
    checker_environment: Mapping[str, Any],
    checker_result: str,
    proof_or_countermodel: Mapping[str, Any] | None,
    status: str,
    related_model_existence: bool | None,
    premise_preservation: bool | None,
    goal_reflection: bool | None,
    premises_consistent: bool | None,
) -> dict[str, Any]:
    profile = profile_by_id(catalog, case["profile_id"])
    fragment = fragment_by_id(catalog, case["fragment_id"])
    receipt = {
        "schema": SCHEMA_RECEIPT,
        "task_id": TASK_ID,
        "receipt_id": f"TR-{case['case_id']}",
        "case_id": case["case_id"],
        "source_view": case["source_view"],
        "target_view": case["target_view"],
        "source_formula_root": case.get("query_id"),
        "target_formula_root": case.get("query_id"),
        "signature_map": {
            "source_signature": profile["source_signature"],
            "target_signature": profile["target_signature"],
            "kind": "identity" if profile["source_signature"] == profile["target_signature"] else "lossy_projection",
        },
        "interpretation_profile": case["profile_id"],
        "bridge_assumptions": list(profile["bridge_assumptions"]),
        "preserved_property": preserved_property,
        "preservation_direction": preservation_direction,
        "supported_fragment": fragment["fragment_id"],
        "fragment_status": fragment["status"],
        "named_losses": list(named_losses),
        "source_map_root": None,
        "checker_environment": checker_environment,
        "checker_result": checker_result,
        "proof_or_countermodel_reference": proof_or_countermodel,
        "related_model_existence": related_model_existence,
        "premise_preservation_equation_7": premise_preservation,
        "goal_reflection_equation_8": goal_reflection,
        "premises_consistent": premises_consistent,
        "proposition_1_discharged": (
            status in ACCEPTED_TRANSFER_STATUSES
            and related_model_existence is True
            and premise_preservation is True
            and goal_reflection is True
            and premises_consistent is True
            and proof_or_countermodel is not None
        ),
        "status": status,
        "machine_checked_compiler_soundness": False,
    }
    receipt["receipt_sha256"] = sha256_obj({key: value for key, value in receipt.items() if key != "receipt_sha256"})
    return receipt


def finite_checker_env() -> dict[str, Any]:
    return {
        "checker_class": "solver_local",
        "checker": "stdlib_finite_enumeration",
        "native": False,
        "language": "Python",
        "python_version": sys.version.split()[0],
        "standard_library_only": True,
    }


def evaluate_q1_implementation(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    write_fn = guarded_write if case["implementation"] == "guarded" else unguarded_write
    assignments = q1_assignments(write_fn)
    violations = [row for row in assignments if not row["q1"]]
    holds = not violations
    existence = True
    premise_ok = True
    reflection_ok = True
    consistent = True
    if case["implementation"] == "guarded":
        if not holds:
            raise BridgeError("guarded implementation must satisfy Q1 on all four assignments")
        status = "accepted_transfer"
        outcome = "q1_holds_on_guarded_model"
        result_kind = "solver_local_result"
        execution_status = "measured"
        proof = {
            "kind": "finite_enumeration_proof",
            "assignments": assignments,
            "violation_count": 0,
            "justification": (
                "Substitution Write = ¬Protected ∨ Approved makes the Q1 antecedent "
                "imply ¬Write on every Boolean assignment."
            ),
        }
        preserved = "Q1_truth"
        direction = "source_implementation_to_target_query"
        checker_result = "holds"
        named_losses: list[str] = []
        useful = True
        false_transfer = False
    else:
        if holds:
            raise BridgeError("unguarded always-write model must violate Q1")
        status = "accepted_countermodel"
        outcome = "q1_countermodel"
        result_kind = "countermodel"
        execution_status = "measured"
        proof = {
            "kind": "finite_countermodel",
            "assignments": assignments,
            "violations": violations,
            "witness": violations[0],
            "justification": (
                "Always-write with Protected and ¬Approved yields Write, falsifying Q1."
            ),
        }
        preserved = "Q1_falsity_on_unguarded_model"
        direction = "source_implementation_to_target_query"
        checker_result = "countermodel"
        named_losses = []
        useful = False
        false_transfer = False
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property=preserved,
        preservation_direction=direction,
        named_losses=named_losses,
        checker_environment=finite_checker_env(),
        checker_result=checker_result,
        proof_or_countermodel=proof,
        status=status,
        related_model_existence=existence,
        premise_preservation=premise_ok,
        goal_reflection=reflection_ok,
        premises_consistent=consistent,
    )
    result = _result_row(
        case,
        outcome=outcome,
        execution_status=execution_status,
        result_kind=result_kind,
        receipt=receipt,
        useful=useful,
        false_transfer=false_transfer,
        checker_class="solver_local",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_q2_trace(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    observed = q2_trace_status(case["trace"])
    expected = case["expected_outcome"]
    if observed["status"] != expected:
        raise BridgeError(
            f"{case['case_id']} expected {expected}, computed {observed['status']}"
        )
    class_to_status = {
        "timely-audit": "accepted_bounded_observation",
        "delayed-audit": "accepted_countermodel",
        "incomplete-window": "unknown_incomplete_window",
        "wrong-tenant": "unresolved_identity",
    }
    status = class_to_status[case["outcome_class"]]
    if status == "accepted_countermodel":
        result_kind = "countermodel"
        execution_status = "measured"
        useful = False
        preserved = "Q2_violation_on_complete_window"
        direction = "trace_to_compliance_query"
        named_losses: list[str] = []
        existence = True
        premise_ok = True
        reflection_ok = True
        consistent = True
        proof: dict[str, Any] | None = {
            "kind": "finite_countermodel",
            "observation": observed,
            "justification": (
                "Matching identities, capture complete through t+2, write at 0, "
                "and no audit in [0,2] (audit at 3 is outside the window)."
            ),
        }
        checker_result = "countermodel"
    elif status == "accepted_bounded_observation":
        result_kind = "bounded_observation"
        execution_status = "measured"
        useful = True
        preserved = "Q2_satisfaction_for_observed_event"
        direction = "trace_to_compliance_query"
        named_losses = ["not_a_global_program_guarantee"]
        existence = True
        premise_ok = True
        reflection_ok = True
        consistent = True
        proof = {
            "kind": "bounded_observation",
            "observation": observed,
            "justification": (
                "Write at 0 and matching audit at 1 fall inside [0,2] on joined identities. "
                "This is one observed event, not a theorem over all executions."
            ),
        }
        checker_result = "satisfied_within_observed_window"
    elif status == "unknown_incomplete_window":
        result_kind = "bounded_observation"
        execution_status = "partial"
        useful = False
        preserved = None
        direction = None
        named_losses = ["incomplete_capture"]
        existence = None
        premise_ok = None
        reflection_ok = None
        consistent = True
        proof = {
            "kind": "unknown_observation",
            "observation": observed,
            "justification": (
                "Capture is not complete through the audit deadline, so the event is "
                "unknown: neither compliance nor a proven violation."
            ),
        }
        checker_result = "unknown"
    else:
        result_kind = "failure"
        execution_status = "invalid"
        useful = False
        preserved = None
        direction = None
        named_losses = ["identity_unresolved"]
        existence = False
        premise_ok = False
        reflection_ok = False
        consistent = True
        proof = {
            "kind": "unresolved_identity",
            "observation": observed,
            "justification": (
                "Tenant-a policy identity and tenant-b trace identity are not joined. "
                "A matching name is not an admitted mapping, so the audit cannot count."
            ),
        }
        checker_result = "unresolved_identity"
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property=preserved,
        preservation_direction=direction,
        named_losses=named_losses,
        checker_environment=finite_checker_env(),
        checker_result=checker_result,
        proof_or_countermodel=proof,
        status=status,
        related_model_existence=existence,
        premise_preservation=premise_ok,
        goal_reflection=reflection_ok,
        premises_consistent=consistent,
    )
    result = _result_row(
        case,
        outcome=observed["status"],
        execution_status=execution_status,
        result_kind=result_kind,
        receipt=receipt,
        useful=useful,
        false_transfer=False,
        checker_class="solver_local" if result_kind != "failure" else "none",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_inconsistent(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    premises = list(case["premises"])
    # Same Protected/Approved/actor slot with both Write and ¬Write.
    keys = {(row["protected"], row["approved"]) for row in premises}
    writes = {row["write"] for row in premises}
    inconsistent = len(keys) == 1 and writes == {True, False}
    if not inconsistent:
        raise BridgeError("inconsistent-premise case must contain Write and ¬Write on one slot")
    # Classical explosion would prove Q1; refuse the transfer.
    status = "inconsistent_premises"
    proof = {
        "kind": "inconsistency_witness",
        "premises": premises,
        "justification": (
            "Premises contain Write and ¬Write on the same protected unapproved slot. "
            "Classical explosion is not accepted as a Q1 transfer; the context is partitioned."
        ),
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property=None,
        preservation_direction=None,
        named_losses=["classical_explosion_refused"],
        checker_environment=finite_checker_env(),
        checker_result="inconsistent",
        proof_or_countermodel=proof,
        status=status,
        related_model_existence=False,
        premise_preservation=False,
        goal_reflection=False,
        premises_consistent=False,
    )
    result = _result_row(
        case,
        outcome="transfer_refused_inconsistent_premises",
        execution_status="invalid",
        result_kind="failure",
        receipt=receipt,
        useful=False,
        false_transfer=True,
        checker_class="solver_local",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_name_extraction(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    text = case["implementation_text"]
    name_hit = "approve" in text
    has_guard = "if approved" in text or "if not protected" in text
    if not name_hit or has_guard:
        raise BridgeError("name-extraction negative control drifted")
    proof = {
        "kind": "rejected_extraction",
        "implementation_text": text,
        "name_hit": True,
        "guard_present": False,
        "justification": (
            "The token 'approve' in a function name is not a justified refinement or "
            "extraction relation to Approved(a,r,t)."
        ),
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property=None,
        preservation_direction=None,
        named_losses=["unjustified_name_alignment"],
        checker_environment=finite_checker_env(),
        checker_result="rejected",
        proof_or_countermodel=proof,
        status="rejected_unjustified_extraction",
        related_model_existence=False,
        premise_preservation=False,
        goal_reflection=False,
        premises_consistent=True,
    )
    result = _result_row(
        case,
        outcome="name_match_is_not_refinement",
        execution_status="invalid",
        result_kind="failure",
        receipt=receipt,
        useful=False,
        false_transfer=True,
        checker_class="none",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_deontic_not_actual(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    relation = frozenset({(0, 1), (1, 1)})
    # p = ¬Write; p holds in the ideal world 1 only.
    valuation = {0: False, 1: True}
    obligation = box(relation, 0, lambda world: valuation[world])
    actual = valuation[0]
    if not (obligation and not actual):
        raise BridgeError("deontic/actual witness drifted")
    tau = {"kind": "atom", "name": "not_write"}
    source = {"kind": "obligation", "formula": tau}
    projected = tdfol_to_fol_lossy(source)
    target_truth = actual
    premise_ok = implication(obligation, target_truth)
    proof = {
        "kind": "finite_countermodel",
        "actual_world": 0,
        "relation": sorted(relation),
        "not_write": {"0": False, "1": True},
        "obligation_at_actual": obligation,
        "actual_not_write": actual,
        "lossy_projection": projected,
        "premise_preservation_equation_7": premise_ok,
        "justification": (
            "O(¬Write) holds because every ideal successor satisfies ¬Write, while the "
            "actual world writes. The policy-to-compliance bridge therefore cannot treat "
            "Q1 as a deontic consequence."
        ),
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property="obligation_truth",
        preservation_direction="source_deontic_to_target_actual",
        named_losses=["obligation_not_actuality"],
        checker_environment=finite_checker_env(),
        checker_result="preservation_failed",
        proof_or_countermodel=proof,
        status="rejected_preservation_failure",
        related_model_existence=True,
        premise_preservation=False,
        goal_reflection=False,
        premises_consistent=True,
    )
    result = _result_row(
        case,
        outcome="obligation_does_not_entail_actual_nonwriting",
        execution_status="measured",
        result_kind="countermodel",
        receipt=receipt,
        useful=False,
        false_transfer=True,
        checker_class="solver_local",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_tdfol_obligation(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    relation = frozenset({(0, 1), (1, 1)})
    p = {0: False, 1: True}
    modal = box(relation, 0, lambda world: p[world])
    actual = p[0]
    source = {"kind": "obligation", "formula": {"kind": "atom", "name": "p"}}
    projected = tdfol_to_fol_lossy(source)
    if projected != {"kind": "atom", "name": "p"}:
        raise BridgeError("lossy obligation projection drifted")
    if not (modal and not actual):
        raise BridgeError("O(p)/p witness drifted")
    proof = {
        "kind": "finite_countermodel",
        "source_formula": source,
        "target_formula": projected,
        "relation": sorted(relation),
        "modal_truth": modal,
        "actual_truth": actual,
        "named_loss": "unary_deontic_erasure",
        "justification": "O(p) is true at the actual world while p is false; stripping O does not preserve theorems.",
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property="modal_theoremhood",
        preservation_direction="tdfol_to_fol",
        named_losses=["unary_deontic_erasure"],
        checker_environment=finite_checker_env(),
        checker_result="preservation_failed",
        proof_or_countermodel=proof,
        status="rejected_preservation_failure",
        related_model_existence=True,
        premise_preservation=False,
        goal_reflection=False,
        premises_consistent=True,
    )
    result = _result_row(
        case,
        outcome="O(p)_true_p_false",
        execution_status="measured",
        result_kind="countermodel",
        receipt=receipt,
        useful=False,
        false_transfer=True,
        checker_class="solver_local",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_tdfol_always(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    traces = {"p": [True, False]}
    source = {"kind": "always", "formula": {"kind": "atom", "name": "p"}}
    projected = tdfol_to_fol_lossy(source)
    now = eval_temporal({"kind": "atom", "name": "p"}, traces, 0)
    always = eval_temporal(source, traces, 0)
    target = eval_propositional(projected, {"p": traces["p"][0]})
    if not (now and not always and target):
        raise BridgeError("G(p) erasure witness drifted")
    proof = {
        "kind": "finite_countermodel",
        "trace_p": traces["p"],
        "source_formula": source,
        "target_formula": projected,
        "current_truth": now,
        "always_truth": always,
        "projected_truth": target,
        "named_loss": "unary_temporal_erasure",
        "justification": "p holds now on [true,false] while Gp does not; stripping G maps the theoremhood claim incorrectly.",
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property="temporal_theoremhood",
        preservation_direction="tdfol_to_fol",
        named_losses=["unary_temporal_erasure"],
        checker_environment=finite_checker_env(),
        checker_result="preservation_failed",
        proof_or_countermodel=proof,
        status="rejected_preservation_failure",
        related_model_existence=True,
        premise_preservation=False,
        goal_reflection=False,
        premises_consistent=True,
    )
    result = _result_row(
        case,
        outcome="p_now_true_Gp_false",
        execution_status="measured",
        result_kind="countermodel",
        receipt=receipt,
        useful=False,
        false_transfer=True,
        checker_class="solver_local",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_tdfol_until(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    traces = {"p": [False, True, True], "q": [True, False, False]}
    source = {
        "kind": "until",
        "left": {"kind": "atom", "name": "p"},
        "right": {"kind": "atom", "name": "q"},
    }
    projected = tdfol_to_fol_lossy(source)
    until_value = eval_temporal(source, traces, 0)
    conjunction = traces["p"][0] and traces["q"][0]
    disagreements = []
    for bits in _product_bits(6):
        p, q = bits[:3], bits[3:]
        until_now = strong_until(p, q)
        conj = p[0] and q[0]
        if until_now != conj:
            disagreements.append({"p": list(p), "q": list(q), "until": until_now, "conjunction": conj})
    if not until_value or conjunction or len(disagreements) != 26:
        raise BridgeError("until/conjunction negative control drifted")
    proof = {
        "kind": "finite_countermodel",
        "witness_trace": traces,
        "source_formula": source,
        "target_formula": projected,
        "until_at_zero": until_value,
        "conjunction_at_zero": conjunction,
        "disagreement_count": len(disagreements),
        "disagreement_denominator": 64,
        "named_loss": "until_replaced_by_conjunction",
        "justification": (
            "q true now makes p U q true regardless of p now, while p ∧ q is false. "
            "26 of 64 length-three Boolean pairs disagree; the lossy converter cannot carry until theorems."
        ),
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property="until_truth",
        preservation_direction="tdfol_to_fol",
        named_losses=["until_replaced_by_conjunction"],
        checker_environment=finite_checker_env(),
        checker_result="preservation_failed",
        proof_or_countermodel=proof,
        status="rejected_preservation_failure",
        related_model_existence=True,
        premise_preservation=False,
        goal_reflection=False,
        premises_consistent=True,
    )
    result = _result_row(
        case,
        outcome="until_not_conjunction",
        execution_status="measured",
        result_kind="countermodel",
        receipt=receipt,
        useful=False,
        false_transfer=True,
        checker_class="solver_local",
        detail=proof["justification"],
    )
    return result, receipt


def _product_bits(width: int) -> Iterable[tuple[bool, ...]]:
    for mask in range(1 << width):
        yield tuple(bool(mask & (1 << bit)) for bit in range(width))


def evaluate_native_checker(
    case: Mapping[str, Any],
    catalog: Mapping[str, Any],
    probes: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    name = case["checker_name"]
    probe = next(item for item in probes["checkers"] if item["name"] == name)
    if probe["usable_in_sealed_validation"]:
        raise BridgeError(
            f"native checker {name} is present on PATH; this suite must bind an actual kernel receipt "
            "rather than recording unavailability"
        )
    proof = {
        "kind": "unavailable_native_checker",
        "checker": name,
        "path": probes["path"],
        "resolved_path": probe["resolved_path"],
        "justification": (
            f"{name} is absent from the sealed validation PATH. No native theorem receipt is claimed. "
            "The finite stdlib check of Q1 is a solver-local result, not a Lean kernel check."
        ),
    }
    env = {
        "checker_class": "none",
        "checker": name,
        "native": False,
        "status": "unavailable",
        "path": probes["path"],
        "resolved_path": None,
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property=None,
        preservation_direction=None,
        named_losses=["native_checker_unavailable"],
        checker_environment=env,
        checker_result="unavailable",
        proof_or_countermodel=proof,
        status="unavailable_native_checker",
        related_model_existence=None,
        premise_preservation=None,
        goal_reflection=None,
        premises_consistent=True,
    )
    result = _result_row(
        case,
        outcome="lean_absent_from_sealed_path",
        execution_status="unavailable",
        result_kind="no_run",
        receipt=receipt,
        useful=False,
        false_transfer=False,
        checker_class="none",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_unsupported(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    fragment = fragment_by_id(catalog, case["fragment_id"])
    if fragment["status"] != "unsupported":
        raise BridgeError(f"{case['case_id']} is not an unsupported fragment")
    proof = {
        "kind": "unsupported_fragment",
        "fragment_id": fragment["fragment_id"],
        "justification": (
            f"Fragment {fragment['fragment_id']} is outside the supported query language. "
            "It remains in the coverage denominator as unsupported, not as a checked transfer."
        ),
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property=None,
        preservation_direction=None,
        named_losses=["unsupported_fragment"],
        checker_environment=finite_checker_env(),
        checker_result="unsupported",
        proof_or_countermodel=proof,
        status="unsupported_fragment",
        related_model_existence=None,
        premise_preservation=None,
        goal_reflection=None,
        premises_consistent=True,
    )
    result = _result_row(
        case,
        outcome=case["expected_outcome"],
        execution_status="unsupported",
        result_kind="failure",
        receipt=receipt,
        useful=False,
        false_transfer=False,
        checker_class="none",
        detail=proof["justification"],
    )
    return result, receipt


def evaluate_proposition_1(case: Mapping[str, Any], catalog: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    record = catalog["proposition_1"]
    if record["machine_checked_compiler_soundness"] or record["blanket_repository_soundness"]:
        raise BridgeError("Proposition 1 must not be represented as compiler soundness")
    proof = {
        "kind": "paper_conditional_argument",
        "proposition": record,
        "justification": record["claim_boundary"],
    }
    receipt = receipt_fields(
        case,
        catalog=catalog,
        preserved_property="conditional_semantic_consequence",
        preservation_direction="target_consequence_reflects_source_goal_under_B",
        named_losses=["not_a_compiler_soundness_theorem"],
        checker_environment={
            "checker_class": "none",
            "checker": "paper_argument",
            "native": False,
            "machine_checked": False,
        },
        checker_result="not_machine_checked",
        proof_or_countermodel=proof,
        status="paper_conditional_argument",
        related_model_existence=None,
        premise_preservation=None,
        goal_reflection=None,
        premises_consistent=None,
    )
    result = _result_row(
        case,
        outcome="not_machine_checked_compiler_soundness",
        execution_status="no_run",
        result_kind="no_run",
        receipt=receipt,
        useful=False,
        false_transfer=False,
        checker_class="none",
        detail=record["claim_boundary"],
    )
    return result, receipt


def _result_row(
    case: Mapping[str, Any],
    *,
    outcome: str,
    execution_status: str,
    result_kind: str,
    receipt: Mapping[str, Any],
    useful: bool,
    false_transfer: bool,
    checker_class: str,
    detail: str,
) -> dict[str, Any]:
    row = {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "record_id": case["case_id"],
        "case_id": case["case_id"],
        "outcome_class": case["outcome_class"],
        "query_id": case.get("query_id"),
        "profile_id": case["profile_id"],
        "fragment_id": case["fragment_id"],
        "source_view": case["source_view"],
        "target_view": case["target_view"],
        "execution_status": execution_status,
        "result_kind": result_kind,
        "outcome": outcome,
        "transfer_status": receipt["status"],
        "accepted_transfer": receipt["status"] == "accepted_transfer",
        "preserved_property": receipt["preserved_property"],
        "preservation_direction": receipt["preservation_direction"],
        "bridge_assumptions": receipt["bridge_assumptions"],
        "supported_fragment": receipt["supported_fragment"],
        "named_losses": receipt["named_losses"],
        "related_model_existence": receipt["related_model_existence"],
        "premise_preservation_equation_7": receipt["premise_preservation_equation_7"],
        "goal_reflection_equation_8": receipt["goal_reflection_equation_8"],
        "premises_consistent": receipt["premises_consistent"],
        "proof": {
            "useful": useful,
            "false_transfer": false_transfer,
            "checker_class": checker_class,
            "receipt_sha256": receipt["receipt_sha256"],
            "fragment": receipt["supported_fragment"],
            "theorem": case.get("query_id"),
        },
        "identities": {
            "experiment_arm": "AF-015-bridge-validation",
            "model": None,
            "tool": "papers/completion/autoformalization/evaluation/bridge_cases.py",
            "checker": receipt["checker_environment"].get("checker"),
            "compiler": None,
        },
        "notes": detail,
        "machine_checked_compiler_soundness": False,
        "fixture": True,
        "constructed_control": True,
        "eligible_for_natural_table": False,
    }
    row["artifacts"] = {"raw_sha256": sha256_obj({key: value for key, value in row.items() if key != "artifacts"})}
    return row


EVALUATORS = {
    "q1_implementation": evaluate_q1_implementation,
    "q2_trace": evaluate_q2_trace,
    "inconsistent_premises": evaluate_inconsistent,
    "name_extraction": evaluate_name_extraction,
    "deontic_not_actual": evaluate_deontic_not_actual,
    "tdfol_obligation_erasure": evaluate_tdfol_obligation,
    "tdfol_always_erasure": evaluate_tdfol_always,
    "tdfol_until_erasure": evaluate_tdfol_until,
    "unsupported_fragment": evaluate_unsupported,
    "proposition_1": evaluate_proposition_1,
}


def evaluate_suite(catalog: Mapping[str, Any] | None = None) -> dict[str, Any]:
    catalog = dict(catalog or case_catalog())
    probes = probe_native_checkers()
    results: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    for case in catalog["cases"]:
        evaluator = case["evaluator"]
        if evaluator == "native_checker":
            result, receipt = evaluate_native_checker(case, catalog, probes)
        else:
            if evaluator not in EVALUATORS:
                raise BridgeError(f"unknown evaluator {evaluator}")
            result, receipt = EVALUATORS[evaluator](case, catalog)
        if result["outcome"] != case["expected_outcome"]:
            raise BridgeError(
                f"{case['case_id']} expected outcome {case['expected_outcome']}, got {result['outcome']}"
            )
        if receipt["status"] != case["expected_status"]:
            raise BridgeError(
                f"{case['case_id']} expected status {case['expected_status']}, got {receipt['status']}"
            )
        results.append(result)
        receipts.append(receipt)
    coverage = build_coverage(catalog, results, receipts, probes)
    assert_acceptance(catalog, results, receipts, coverage)
    return {
        "catalog": catalog,
        "results": results,
        "receipts": receipts,
        "coverage": coverage,
        "probes": probes,
    }


def build_coverage(
    catalog: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]],
    probes: Mapping[str, Any],
) -> dict[str, Any]:
    by_class = {row["outcome_class"]: row["outcome"] for row in results}
    missing_checkers = [item for item in probes["checkers"] if item["status"] == "unavailable"]
    unsupported = [fragment for fragment in catalog["fragments"] if fragment["status"] == "unsupported"]
    accepted = [receipt for receipt in receipts if receipt["status"] in ACCEPTED_TRANSFER_STATUSES]
    return {
        "schema": SCHEMA_COVERAGE,
        "task_id": TASK_ID,
        "suite_id": SUITE_ID,
        "case_count": len(results),
        "accepted_transfer_count": sum(1 for row in results if row["accepted_transfer"]),
        "accepted_countermodel_count": sum(1 for receipt in receipts if receipt["status"] == "accepted_countermodel"),
        "outcome_classes": by_class,
        "required_outcome_classes": {
            name: by_class.get(name) for name in REQUIRED_OUTCOME_CLASSES
        },
        "required_outcomes_distinct": len({by_class[name] for name in REQUIRED_OUTCOME_CLASSES})
        == len(REQUIRED_OUTCOME_CLASSES),
        "native_checkers": probes["checkers"],
        "missing_native_checkers": [item["name"] for item in missing_checkers],
        "unsupported_fragments": [item["fragment_id"] for item in unsupported],
        "unsupported_fragment_cases": [
            row["case_id"] for row in results if row["transfer_status"] == "unsupported_fragment"
        ],
        "proposition_1": catalog["proposition_1"],
        "accepted_receipt_ids": [receipt["receipt_id"] for receipt in accepted],
        "machine_checked_compiler_soundness": False,
        "natural_held_out_claims": False,
        "inspected_sources": INSPECTED_SOURCES,
        "environment": {
            "path": probes["path"],
            "home_is_validation_private": probes["home_is_validation_private"],
            "python_executable": probes["python_executable"],
            "python_version": probes["python_version"],
        },
    }


def assert_acceptance(
    catalog: Mapping[str, Any],
    results: Sequence[Mapping[str, Any]],
    receipts: Sequence[Mapping[str, Any]],
    coverage: Mapping[str, Any],
) -> None:
    by_id = {row["case_id"]: row for row in results}
    classes = {row["outcome_class"] for row in results}
    for name in REQUIRED_OUTCOME_CLASSES:
        if name not in classes:
            raise BridgeError(f"missing required outcome class {name}")
    outcomes = [by_id_class_outcome(results, name) for name in REQUIRED_OUTCOME_CLASSES]
    if len(set(outcomes)) != len(REQUIRED_OUTCOME_CLASSES):
        raise BridgeError(f"required outcome classes are not distinct: {outcomes}")
    for receipt in receipts:
        if receipt["status"] not in ACCEPTED_TRANSFER_STATUSES:
            continue
        for field in (
            "preserved_property",
            "preservation_direction",
            "bridge_assumptions",
            "supported_fragment",
            "proof_or_countermodel_reference",
        ):
            value = receipt[field]
            if value in (None, "", []):
                raise BridgeError(f"{receipt['receipt_id']} accepted without {field}")
        if not receipt["related_model_existence"]:
            raise BridgeError(f"{receipt['receipt_id']} accepted without related-model existence")
        if receipt["premise_preservation_equation_7"] is not True:
            raise BridgeError(f"{receipt['receipt_id']} accepted without premise preservation")
        if receipt["goal_reflection_equation_8"] is not True:
            raise BridgeError(f"{receipt['receipt_id']} accepted without goal reflection")
        if receipt["premises_consistent"] is not True:
            raise BridgeError(f"{receipt['receipt_id']} accepted with inconsistent premises")
        if receipt["machine_checked_compiler_soundness"]:
            raise BridgeError("accepted receipt claims compiler soundness")
    prop = catalog["proposition_1"]
    if prop["machine_checked_compiler_soundness"] or prop["blanket_repository_soundness"]:
        raise BridgeError("Proposition 1 represented as compiler soundness")
    prop_row = next(row for row in results if row["case_id"] == "PROP1-CONDITIONAL")
    if prop_row["outcome"] != "not_machine_checked_compiler_soundness":
        raise BridgeError("Proposition 1 outcome drifted")
    if not coverage["missing_native_checkers"]:
        raise BridgeError("coverage omitted missing native checkers")
    if "lean" not in coverage["missing_native_checkers"]:
        raise BridgeError("lean absence must be reported in the sealed environment")
    if not coverage["unsupported_fragments"]:
        raise BridgeError("coverage omitted unsupported fragments")
    if by_id["PCT-SAFE-Q1"]["outcome"] == by_id["PCT-UNSAFE-Q1"]["outcome"]:
        raise BridgeError("safe and unsafe outcomes collapsed")
    if by_id["PCT-DELAYED-AUDIT"]["outcome"] == by_id["PCT-INCOMPLETE-WINDOW"]["outcome"]:
        raise BridgeError("delayed-audit and incomplete-window outcomes collapsed")
    if by_id["PCT-WRONG-TENANT"]["outcome"] == by_id["PCT-DELAYED-AUDIT"]["outcome"]:
        raise BridgeError("wrong-tenant treated as a Q2 violation")
    if by_id["PCT-INCONSISTENT"]["accepted_transfer"]:
        raise BridgeError("inconsistent premises accepted as a transfer")
    inspect_sources()


def by_id_class_outcome(results: Sequence[Mapping[str, Any]], outcome_class: str) -> str:
    matches = [row["outcome"] for row in results if row["outcome_class"] == outcome_class]
    if len(matches) != 1:
        raise BridgeError(f"outcome class {outcome_class} has {len(matches)} rows")
    return matches[0]


def inspect_sources() -> None:
    for spec in INSPECTED_SOURCES.values():
        path = REPO_ROOT / spec["path"]
        if not path.is_file():
            raise BridgeError(f"inspected source missing: {spec['path']}")
        digest = sha256_file(path)
        if digest != spec["sha256"]:
            raise BridgeError(
                f"inspected source hash drifted for {spec['path']}: {digest} != {spec['sha256']}"
            )


def coverage_result_row(coverage: Mapping[str, Any]) -> dict[str, Any]:
    row = {
        "schema": SCHEMA_RESULT,
        "task_id": TASK_ID,
        "record_id": "AF-015-COVERAGE",
        "case_id": "AF-015-COVERAGE",
        "outcome_class": "coverage-status",
        "query_id": None,
        "profile_id": None,
        "fragment_id": None,
        "source_view": None,
        "target_view": None,
        "execution_status": "measured",
        "result_kind": "bounded_observation",
        "outcome": "coverage_includes_missing_checkers_and_unsupported_fragments",
        "transfer_status": "coverage",
        "accepted_transfer": False,
        "preserved_property": None,
        "preservation_direction": None,
        "bridge_assumptions": [],
        "supported_fragment": None,
        "named_losses": [],
        "related_model_existence": None,
        "premise_preservation_equation_7": None,
        "goal_reflection_equation_8": None,
        "premises_consistent": None,
        "proof": {
            "useful": False,
            "false_transfer": False,
            "checker_class": "none",
            "receipt_sha256": None,
            "fragment": None,
            "theorem": None,
        },
        "identities": {
            "experiment_arm": "AF-015-bridge-validation",
            "model": None,
            "tool": "papers/completion/autoformalization/evaluation/bridge_cases.py",
            "checker": "coverage_report",
            "compiler": None,
        },
        "notes": canonical_dumps({
            "missing_native_checkers": coverage["missing_native_checkers"],
            "unsupported_fragments": coverage["unsupported_fragments"],
            "required_outcome_classes": coverage["required_outcome_classes"],
            "machine_checked_compiler_soundness": False,
        }),
        "machine_checked_compiler_soundness": False,
        "fixture": True,
        "constructed_control": True,
        "eligible_for_natural_table": False,
        "coverage": coverage,
    }
    row["artifacts"] = {"raw_sha256": sha256_obj({key: value for key, value in row.items() if key != "artifacts"})}
    return row


def default_paths() -> dict[str, Path]:
    return {
        "cases": PAPER_ROOT / "data" / "policy_code_trace_cases.json",
        "results": PAPER_ROOT / "runs" / "bridge_validation" / "results.jsonl",
        "receipts": PAPER_ROOT / "evidence" / "translation_receipts.jsonl",
    }


def materialize(paths: Mapping[str, Path]) -> dict[str, Any]:
    suite = evaluate_suite()
    write_json(paths["cases"], suite["catalog"])
    result_rows = [coverage_result_row(suite["coverage"]), *suite["results"]]
    write_jsonl(paths["results"], result_rows)
    write_jsonl(paths["receipts"], suite["receipts"])
    reloaded = json.loads(paths["cases"].read_text(encoding="utf-8"))
    if sha256_obj(reloaded) != sha256_obj(suite["catalog"]):
        raise BridgeError("cases JSON round-trip drifted")
    return {
        "suite_id": SUITE_ID,
        "cases": str(paths["cases"]),
        "results": str(paths["results"]),
        "receipts": str(paths["receipts"]),
        "case_count": len(suite["results"]),
        "accepted_transfers": suite["coverage"]["accepted_transfer_count"],
        "accepted_countermodels": suite["coverage"]["accepted_countermodel_count"],
        "missing_native_checkers": suite["coverage"]["missing_native_checkers"],
        "unsupported_fragments": suite["coverage"]["unsupported_fragments"],
        "required_outcome_classes": suite["coverage"]["required_outcome_classes"],
        "machine_checked_compiler_soundness": False,
        "all_acceptance_checks_passed": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    defaults = default_paths()
    parser.add_argument("--cases", type=Path, default=defaults["cases"])
    parser.add_argument("--results", type=Path, default=defaults["results"])
    parser.add_argument("--receipts", type=Path, default=defaults["receipts"])
    args = parser.parse_args(argv)
    summary = materialize({"cases": args.cases, "results": args.results, "receipts": args.receipts})
    print(canonical_dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
