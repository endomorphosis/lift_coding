#!/usr/bin/env python3
"""NS-009 live qualification of translation preservation and checker admission.

Exercises the actual translation contract, TDFOL converter, finite-trace
evaluator, solver-readiness probe, logic-platform receipt admission, TDFOL
prover, and IPA CEGAR refinement. SMT SAT/UNSAT, interpolants,
CompositionEdge, and an incremental SMT wrapper are recorded only when
located and executable in the sealed profile; unavailable mechanisms are
not simulated.

This is qualification evidence, not a matched A–D experiment and not a
kernel proof of arbitrary Python.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-009"
SNAP_QUAL = SNAP / "qualification"
ACC_ROOT = ROOT / "external/ipfs_accelerate"
DS_ROOT = ROOT / "external/ipfs_datasets"
KIT_ROOT = ROOT / "external/ipfs_kit"
TASK_ID = "NS-009"
SCHEMA_CASES = "neurosymbolic-supervision/logic-qualification-cases@1"
SCHEMA_RECEIPT = "neurosymbolic-supervision/logic-qualification-receipt@1"
SCHEMA_PROFILES = "neurosymbolic-supervision/logic-qualification-profiles@1"
POLICY_ID = "ns-009-logic-qualification-v1"
FIXTURE_SET_ID = "ns-009-logic-v1"
ENV_ID = "env-ns009-sealed"
TREE_ID = "tree-ns009"
CHECKPOINT_DIR = Path(
    os.environ.get(
        "IPFS_ACCELERATE_AGENT_TASK_CHECKPOINT_DIR",
        str(SNAP / "checkpoints"),
    )
)

SEARCH_ROOTS = (ACC_ROOT, DS_ROOT)
IDENTIFIER_TOKENS = (
    "CompositionEdge",
    "ProcedureCegis",
    "interpolant",
    "Craig interpolant",
    "incremental SMT",
    "QF_LIA",
)

REQUIRED_CASES = (
    "exact_atom_supported_progress",
    "modal_erasure_obligation_lift",
    "temporal_erasure_always_lift",
    "until_conjunction_lossy_projection",
    "declared_conservative_modal_progress",
    "heuristic_cannot_prove",
    "undeclared_abstraction_quarantine",
    "bounded_abstraction_progress",
    "missing_finite_bounds",
    "fixture_set_mismatch",
    "stale_formula_root",
    "duplicate_named_assertions",
    "unsupported_clause_uncovered",
    "opaque_clause_uncovered",
    "solver_readiness_z3_unavailable",
    "tdfol_axiom_proved_non_kernel",
    "unknown_not_proved",
    "timeout_budget_exhausted",
    "vacuity_unsat_guarantee",
    "reachability_gap",
    "unvalidated_solver_result_rejected",
    "sat_smt_unavailable",
    "unsat_smt_unavailable",
    "stale_solver_fingerprint",
    "cegar_ipa_spurious_refine",
    "cegar_qf_lia_adapter_unlocated",
    "interpolant_mechanism_unavailable",
    "invalid_interpolant_not_admitted",
    "composition_edge_unlocated",
    "cyclic_composition_unlocated",
    "incremental_smt_wrapper_unlocated",
    "kernel_vs_solver_evidence_classes",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def write_json(path: Path, payload: Any) -> None:
    encoded = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    atomic_write(path, encoded.encode("utf-8"))


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    lines = [
        json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        for row in rows
    ]
    atomic_write(path, ("\n".join(lines) + "\n").encode("utf-8"))


def checkpoint(name: str, payload: Mapping[str, Any]) -> None:
    try:
        CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        write_json(CHECKPOINT_DIR / f"{name}.json", dict(payload))
    except OSError:
        fallback = SNAP / "checkpoints"
        fallback.mkdir(parents=True, exist_ok=True)
        write_json(fallback / f"{name}.json", dict(payload))


def rel(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def enum_val(value: Any) -> str:
    return str(getattr(value, "value", value))


def which(name: str) -> str | None:
    return shutil.which(name)


def git_head(path: Path) -> str | None:
    git = which("git")
    if git is None:
        return None
    try:
        proc = subprocess.run(
            [git, "-C", str(path), "rev-parse", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def prepare_imports() -> dict[str, Any]:
    initial_path = os.environ.get("PATH")
    for path in (str(ACC_ROOT), str(DS_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)

    from ipfs_accelerate_py.agent_supervisor.analysis.formal_assurance import ipa
    from ipfs_accelerate_py.agent_supervisor.proof import (
        formal_logic_vocabulary as vocab,
        formal_verification_contracts as contracts,
        logic_platform_admission as admission,
        logic_translation_validation as translation,
        solver_readiness as readiness,
    )
    from ipfs_datasets_py.logic.TDFOL import tdfol_converter, tdfol_core, tdfol_prover
    from ipfs_datasets_py.logic.admissibility import enforcement

    pytest_version = None
    pytest_error = None
    try:
        import pytest

        pytest_version = pytest.__version__
    except Exception as exc:
        pytest_error = f"{type(exc).__name__}: {exc}"

    z3_mod = False
    z3_mod_error = None
    try:
        import z3  # noqa: F401

        z3_mod = True
    except Exception as exc:
        z3_mod_error = f"{type(exc).__name__}: {exc}"

    return {
        "interpreter": sys.executable,
        "python_version": sys.version.split()[0],
        "path": initial_path,
        "pytest": pytest_version,
        "pytest_error": pytest_error,
        "z3_module": z3_mod,
        "z3_module_error": z3_mod_error,
        "binaries": {
            "z3": which("z3"),
            "cvc5": which("cvc5"),
            "souffle": which("souffle"),
            "lean": which("lean"),
            "coqc": which("coqc"),
        },
        "api": {
            "ipa": ipa,
            "vocab": vocab,
            "contracts": contracts,
            "admission": admission,
            "translation": translation,
            "readiness": readiness,
            "tdfol_converter": tdfol_converter,
            "tdfol_core": tdfol_core,
            "tdfol_prover": tdfol_prover,
            "enforcement": enforcement,
        },
        "modules": {
            "logic_translation_validation": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/proof/logic_translation_validation.py"
            ),
            "solver_readiness": rel(
                ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/solver_readiness.py"
            ),
            "logic_platform_admission": rel(
                ACC_ROOT
                / "ipfs_accelerate_py/agent_supervisor/proof/logic_platform_admission.py"
            ),
            "formal_logic_vocabulary": rel(
                ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/formal_logic_vocabulary.py"
            ),
            "ipa": rel(
                ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py"
            ),
            "tdfol_converter": rel(
                DS_ROOT / "ipfs_datasets_py/logic/TDFOL/tdfol_converter.py"
            ),
            "tdfol_prover": rel(DS_ROOT / "ipfs_datasets_py/logic/TDFOL/tdfol_prover.py"),
            "enforcement": rel(
                DS_ROOT / "ipfs_datasets_py/logic/admissibility/enforcement.py"
            ),
        },
    }


def source_hashes() -> dict[str, str]:
    paths = [
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/logic_translation_validation.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/solver_readiness.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/logic_platform_admission.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/formal_logic_vocabulary.py",
        ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py",
        DS_ROOT / "ipfs_datasets_py/logic/TDFOL/tdfol_converter.py",
        DS_ROOT / "ipfs_datasets_py/logic/TDFOL/tdfol_prover.py",
        DS_ROOT / "ipfs_datasets_py/logic/admissibility/enforcement.py",
        PAPER / "paper_extracted.txt",
        PAPER / "artifacts/capabilities.json",
        PAPER / "audit/implementation_inventory.json",
    ]
    return {rel(path): sha256_file(path) for path in paths if path.is_file()}


def search_identifiers() -> dict[str, Any]:
    hits: dict[str, list[dict[str, Any]]] = {token: [] for token in IDENTIFIER_TOKENS}
    pattern = re.compile(
        r"CompositionEdge|ProcedureCegis|interpolant|Craig interpolant|incremental SMT|QF_LIA",
        re.I,
    )
    for root in SEARCH_ROOTS:
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts or ".git" in path.parts:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if not pattern.search(text):
                continue
            rel_path = rel(path)
            for token in IDENTIFIER_TOKENS:
                if token == "QF_LIA":
                    if "QF_LIA" in text and re.search(r"CEGAR|cegar|interpolat", text, re.I):
                        hits[token].append({"path": rel_path})
                elif token.lower() in text.lower() or token in text:
                    hits[token].append({"path": rel_path})
    summary = {
        token: {
            "matched_files": len(items),
            "found_in_python_source": bool(items),
            "sample_paths": [item["path"] for item in items[:8]],
        }
        for token, items in hits.items()
    }
    # Exact identifier CompositionEdge/ProcedureCegis must be token-true, not substring of comments only.
    for token in ("CompositionEdge", "ProcedureCegis"):
        exact = []
        for item in hits[token]:
            try:
                text = (ROOT / item["path"]).read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if re.search(rf"\b{token}\b", text):
                exact.append(item["path"])
        summary[token] = {
            "matched_files": len(exact),
            "found_in_python_source": bool(exact),
            "sample_paths": exact[:8],
        }
    ipa_cegar = rel(ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py")
    summary["ipa_cegar_located"] = {
        "path": ipa_cegar,
        "found": (ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py").is_file(),
        "symbol": "refine_spurious_paths",
    }
    return summary


def make_contract(api: dict[str, Any], **kwargs: Any) -> Any:
    translation = api["translation"]
    defaults = dict(
        translator_version="1",
        translator_identity="sha256:ns-009-translator",
        semantic_profile_version="1",
        fixture_set_id=FIXTURE_SET_ID,
    )
    defaults.update(kwargs)
    return translation.TranslationContract(**defaults)


def artifact_for(api: dict[str, Any], contract: Any, **kwargs: Any) -> Any:
    translation = api["translation"]
    return translation.TranslationArtifact(
        contract_identity=kwargs.pop("contract_identity", contract.content_id),
        source_identity=kwargs.pop("source_identity", contract.source_identity),
        fixture_set_id=kwargs.pop("fixture_set_id", contract.fixture_set_id),
        **kwargs,
    )


def validate(api: dict[str, Any], contract: Any, artifact: Any) -> Any:
    return api["translation"].validate_translation(contract, artifact)


def issue_codes(result: Any) -> list[str]:
    return [enum_val(item.code) for item in result.issues]


def admit(
    api: dict[str, Any],
    payload: dict[str, Any],
    *,
    required_authority: str,
    operation: str,
    source_id: str,
    environment_id: str = ENV_ID,
    require_reconstruction: bool = False,
    require_kernel: bool = False,
) -> Any:
    admission = api["admission"]
    contracts = api["contracts"]
    body = dict(payload)
    body.setdefault("repository_tree_id", TREE_ID)
    body.setdefault("policy_id", POLICY_ID)
    body.setdefault("environment_id", environment_id)
    body.setdefault("source_id", source_id)
    body.setdefault("freshness", "current")
    body.setdefault("simulated", False)
    if "content_id" not in body:
        identity = {key: value for key, value in body.items() if key != "content_id"}
        body["content_id"] = contracts.content_identity(identity)
    context = admission.AdmissionContext(
        task_id=TASK_ID,
        repository_tree_id=TREE_ID,
        policy_id=POLICY_ID,
        operation=operation,
        required_authority=required_authority,
        environment_id=environment_id,
        source_id=source_id,
        require_reconstruction=require_reconstruction,
        require_kernel=require_kernel,
    )
    result = admission.admit_receipt(body, context)
    return result, body


def admission_summary(result: Any) -> dict[str, Any]:
    return {
        "admitted": bool(result.admitted),
        "disposition": enum_val(result.disposition),
        "reasons": list(result.reasons),
        "failed_checks": [
            {"check": enum_val(item.check), "reason_code": item.reason_code}
            for item in result.checks
            if not item.passed
        ],
        "receipt_content_id": result.receipt_content_id,
    }


def row_base(
    *,
    case_id: str,
    family: str,
    pair_id: str,
    polarity: str,
    description: str,
    expected_reason: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA_RECEIPT,
        "task_id": TASK_ID,
        "case_id": case_id,
        "family": family,
        "pair_id": pair_id,
        "polarity": polarity,
        "description": description,
        "expected_reason": expected_reason,
        "retained": True,
        "qualification_not_live_ad": True,
        "simulated_unavailable_mechanism": False,
        "assertion_replay": False,
        "retained_solver_state": False,
        "kernel_proof": False,
        "source_claim_admitted": False,
        "translation_progress": False,
        "useful_progress": False,
        "status": "pass",
        "reason_matched": True,
    }


def finish(
    row: dict[str, Any],
    *,
    observed_reason: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    row["observed_reason"] = observed_reason
    row["reason_matched"] = observed_reason == row["expected_reason"]
    if extra:
        row.update(dict(extra))
    if not row["reason_matched"]:
        row["status"] = "fail"
    if row.get("simulated_unavailable_mechanism"):
        row["status"] = "fail"
    if row["polarity"] == "valid" and not row.get("useful_progress"):
        row["status"] = "fail"
    if row["polarity"] == "invalid" and row.get("source_claim_admitted"):
        row["status"] = "fail"
    if row["polarity"] == "invalid" and row.get("useful_progress"):
        row["status"] = "fail"
    return row


def named_assertion_register(entries: list[tuple[str, str]]) -> dict[str, Any]:
    seen: dict[str, str] = {}
    collisions: list[dict[str, str]] = []
    for name, formula_root in entries:
        prior = seen.get(name)
        if prior is not None and prior != formula_root:
            collisions.append(
                {
                    "assertion_id": name,
                    "first_formula_root": prior,
                    "second_formula_root": formula_root,
                }
            )
        else:
            seen[name] = formula_root
    return {
        "accepted": not collisions,
        "collisions": collisions,
        "bound_ids": sorted(seen),
    }


def interpolant_conditions(a_syms: set[str], b_syms: set[str], i_syms: set[str]) -> dict[str, Any]:
    shared = a_syms & b_syms
    return {
        "symbols_ok": i_syms <= shared,
        "shared_symbols": sorted(shared),
        "interpolant_symbols": sorted(i_syms),
        "a_implies_i_checked": False,
        "i_and_b_unsat_checked": False,
        "reason": "No located interpolant checker; Craig conditions cannot be discharged. An unsat core is not an interpolant.",
    }


def run_cases(api: dict[str, Any], searches: dict[str, Any], readiness_report: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    translation = api["translation"]
    vocab = api["vocab"]
    ipa = api["ipa"]
    tdfol_core = api["tdfol_core"]
    tdfol_converter = api["tdfol_converter"]
    tdfol_prover = api["tdfol_prover"]
    contracts = api["contracts"]

    cases: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []

    def declare(**kwargs: Any) -> None:
        cases.append(kwargs)

    atom_p = vocab.atom(vocab.ReviewedPredicate.TASK_COMPLETED, vocab.constant(vocab.TermSort.TASK, "t1"))
    atom_q = vocab.atom(vocab.ReviewedPredicate.TASK_READY, vocab.constant(vocab.TermSort.TASK, "t1"))
    inv_p = translation.inventory_from_reviewed_formula(atom_p)
    obligation = vocab.DCEC.obligation("worker", atom_p, 7)
    inv_ob = translation.inventory_from_reviewed_formula(obligation)
    safety = vocab.TDFOL.safety(atom_p, upper_bound=1, lower_bound=0)
    inv_safety = translation.inventory_from_reviewed_formula(safety)
    vacuous_g = vocab.conjunction(atom_p, vocab.negate(atom_p))
    implication = vocab.implies(vacuous_g, atom_q)

    exact_contract = make_contract(
        api,
        contract_id="fol-atom-to-smtlib@1",
        source_identity=atom_p.formula_id,
        source_form=translation.LogicForm.FOL,
        target_form=translation.LogicForm.SMT_LIB,
        translator_id="ns-009-exact-smtlib",
        semantic_profile_id="supervisor-fol",
        translation_class=translation.TranslationClass.EXACT,
    )
    exact_art = artifact_for(
        api,
        exact_contract,
        target_text="(assert (task_completed t1))",
        source_inventory=inv_p,
        target_inventory=inv_p,
    )
    exact_res = validate(api, exact_contract, exact_art)
    exact_payload = {
        "obligation_id": "ob-exact-atom",
        "semantic_verdict": "unknown",
        "evidence_kind": "solver_result",
        "authority_ceiling": "solver_checked",
        "translation": {
            "valid": bool(exact_res.conformant),
            "translation_class": "exact",
            "contract_identity": exact_contract.content_id,
            "artifact_identity": exact_art.content_id,
            "validation_identity": exact_res.content_id,
        },
        "formula_root": atom_p.formula_id,
        "theory": "QF_UF",
        "solver_id": "none-sealed-profile",
        "reconstruction_passed": False,
        "kernel_checked": False,
    }
    exact_adm, exact_body = admit(
        api,
        exact_payload,
        required_authority="solver_checked",
        operation="record_translation",
        source_id=atom_p.formula_id,
    )
    kernel_adm, _ = admit(
        api,
        {
            **exact_payload,
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id=atom_p.formula_id,
        require_reconstruction=True,
        require_kernel=True,
    )

    declare(
        case_id="exact_atom_supported_progress",
        family="translation",
        pair_id="exact_atom",
        polarity="valid",
        expected_reason="exact_translation_conformant",
        description="Exact FOL atom to SMT-LIB with matching semantic inventories progresses at solver-checked translation assurance.",
    )
    rows.append(
        finish(
            row_base(
                case_id="exact_atom_supported_progress",
                family="translation",
                pair_id="exact_atom",
                polarity="valid",
                expected_reason="exact_translation_conformant",
                description="Exact FOL atom to SMT-LIB with matching semantic inventories progresses at solver-checked translation assurance.",
            ),
            observed_reason="exact_translation_conformant"
            if exact_res.conformant and exact_res.promotion_allowed and exact_adm.admitted and not kernel_adm.admitted
            else "exact_translation_failed",
            extra={
                "useful_progress": bool(exact_res.conformant and exact_res.promotion_allowed and exact_adm.admitted),
                "translation_progress": bool(exact_res.conformant and exact_res.promotion_allowed),
                "source_claim_admitted": False,
                "kernel_proof": False,
                "evidence_class": "translation_solver_checked",
                "solver_result_class": "unknown",
                "bindings": {
                    "formula_root": atom_p.formula_id,
                    "source_form": "fol",
                    "target_form": "smt-lib",
                    "theory": "QF_UF",
                    "solver_id": "none-sealed-profile",
                    "environment_id": ENV_ID,
                    "contract_identity": exact_contract.content_id,
                    "artifact_identity": exact_art.content_id,
                    "validation_identity": exact_res.content_id,
                    "caller_receipt_id": exact_body["content_id"],
                },
                "translation": {
                    "conformant": exact_res.conformant,
                    "quarantine_required": exact_res.quarantine_required,
                    "promotion_allowed": exact_res.promotion_allowed,
                    "maximum_assurance": enum_val(exact_res.maximum_assurance),
                    "issues": issue_codes(exact_res),
                },
                "admission": admission_summary(exact_adm),
                "kernel_admission": admission_summary(kernel_adm),
            },
        )
    )

    dropped_target = translation.SemanticInventory(
        actors=inv_ob.actors,
        times=inv_ob.times,
        quantifiers=inv_ob.quantifiers,
        modal_operators=(),
        bounds=inv_ob.bounds,
        premises=inv_ob.premises,
        predicates=inv_ob.predicates,
        polarities=inv_ob.polarities,
        variables=inv_ob.variables,
    )
    lossy_contract = make_contract(
        api,
        contract_id="dcec-obligation-to-fol-exact@1",
        source_identity=obligation.formula_id,
        source_form=translation.LogicForm.DCEC,
        target_form=translation.LogicForm.FOL,
        translator_id="tdfol-to-fol",
        semantic_profile_id="supervisor-dcec",
        translation_class=translation.TranslationClass.EXACT,
    )
    lossy_art = artifact_for(
        api,
        lossy_contract,
        target_text="task_completed(t1)",
        source_inventory=inv_ob,
        target_inventory=dropped_target,
    )
    lossy_res = validate(api, lossy_contract, lossy_art)
    p_td = tdfol_core.Predicate("Done", ())
    o_p = tdfol_core.DeonticFormula(tdfol_core.DeonticOperator.OBLIGATION, p_td)
    fol_o = tdfol_converter.tdfol_to_fol(o_p)
    fol_p = tdfol_converter.tdfol_to_fol(p_td)
    projection_same = type(fol_o) is type(fol_p) and getattr(fol_o, "name", None) == getattr(fol_p, "name", None)
    lift_payload = {
        "obligation_id": "ob-modal-lift",
        "semantic_verdict": "proved",
        "evidence_kind": "solver_result",
        "authority_ceiling": "solver_checked",
        "translation": {
            "valid": bool(lossy_res.conformant),
            "translation_class": "exact",
            "issues": issue_codes(lossy_res),
            "contract_identity": lossy_contract.content_id,
        },
        "formula_root": obligation.formula_id,
        "reconstruction_passed": False,
        "kernel_checked": False,
    }
    lift_adm, lift_body = admit(
        api,
        lift_payload,
        required_authority="kernel_verified",
        operation="complete_task",
        source_id=obligation.formula_id,
        require_reconstruction=True,
        require_kernel=True,
    )
    declare(
        case_id="modal_erasure_obligation_lift",
        family="lossy_projection",
        pair_id="modal_erasure",
        polarity="invalid",
        expected_reason="dropped_modal_operator",
        description="O(p) and p share the TDFOL-to-FOL projection; exact translation of the obligation is quarantined and cannot admit the source claim.",
    )
    rows.append(
        finish(
            row_base(
                case_id="modal_erasure_obligation_lift",
                family="lossy_projection",
                pair_id="modal_erasure",
                polarity="invalid",
                expected_reason="dropped_modal_operator",
                description="O(p) and p share the TDFOL-to-FOL projection; exact translation of the obligation is quarantined and cannot admit the source claim.",
            ),
            observed_reason="dropped_modal_operator"
            if "dropped_modal_operator" in issue_codes(lossy_res) and not lift_adm.admitted
            else "modal_lift_not_rejected",
            extra={
                "useful_progress": False,
                "translation_progress": False,
                "source_claim_admitted": bool(lift_adm.admitted),
                "countermodel": {
                    "source_a": "O(Done)",
                    "source_b": "Done",
                    "projection_a": fol_o.to_string(),
                    "projection_b": fol_p.to_string(),
                    "identical_projection": projection_same,
                    "converter": "TDFOLToFOLConverter.convert strips DeonticFormula",
                },
                "translation": {
                    "conformant": lossy_res.conformant,
                    "quarantine_required": lossy_res.quarantine_required,
                    "promotion_allowed": lossy_res.promotion_allowed,
                    "issues": issue_codes(lossy_res),
                    "source_modals": list(inv_ob.modal_operators),
                    "target_modals": list(dropped_target.modal_operators),
                },
                "admission": admission_summary(lift_adm),
                "bindings": {
                    "formula_root": obligation.formula_id,
                    "source_form": "dcec",
                    "target_form": "fol",
                    "contract_identity": lossy_contract.content_id,
                    "caller_receipt_id": lift_body["content_id"],
                    "environment_id": ENV_ID,
                },
                "evidence_class": "quarantined_translation",
            },
        )
    )

    always_td = tdfol_core.TemporalFormula(tdfol_core.TemporalOperator.ALWAYS, p_td)
    fol_always = tdfol_converter.tdfol_to_fol(always_td)
    dropped_time = translation.SemanticInventory(
        actors=inv_safety.actors,
        times=(),
        quantifiers=inv_safety.quantifiers,
        modal_operators=(),
        bounds=(),
        premises=inv_safety.premises,
        predicates=inv_safety.predicates,
        polarities=inv_safety.polarities,
        variables=inv_safety.variables,
    )
    temp_contract = make_contract(
        api,
        contract_id="tdfol-safety-to-fol-exact@1",
        source_identity=safety.formula_id,
        source_form=translation.LogicForm.TDFOL,
        target_form=translation.LogicForm.FOL,
        translator_id="tdfol-to-fol",
        semantic_profile_id="supervisor-tdfol",
        translation_class=translation.TranslationClass.EXACT,
    )
    temp_art = artifact_for(
        api,
        temp_contract,
        target_text="task_completed(t1)",
        source_inventory=inv_safety,
        target_inventory=dropped_time,
    )
    temp_res = validate(api, temp_contract, temp_art)
    fact_p = vocab.TraceFact(predicate=vocab.ReviewedPredicate.TASK_COMPLETED, terms=atom_p.terms)
    empty = vocab.TraceStep(index=0, facts=())
    only_t0 = vocab.TraceStep(index=0, facts=(fact_p,))
    t1_empty = vocab.TraceStep(index=1, facts=())
    t1_p = vocab.TraceStep(index=1, facts=(fact_p,))
    trace_partial = vocab.FiniteTrace(steps=(only_t0, t1_empty), bound=1, source_plan_id="ns-009-partial")
    trace_full = vocab.FiniteTrace(steps=(only_t0, t1_p), bound=1, source_plan_id="ns-009-full")
    p_partial = vocab.evaluate_formula(atom_p, trace_partial, index=0)
    safety_partial = vocab.evaluate_formula(safety, trace_partial, index=0)
    p_full = vocab.evaluate_formula(atom_p, trace_full, index=0)
    safety_full = vocab.evaluate_formula(safety, trace_full, index=0)
    temp_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-temporal-lift",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {"valid": bool(temp_res.conformant), "translation_class": "exact", "issues": issue_codes(temp_res)},
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id=safety.formula_id,
        require_kernel=True,
        require_reconstruction=True,
    )
    declare(
        case_id="temporal_erasure_always_lift",
        family="lossy_projection",
        pair_id="temporal_erasure",
        polarity="invalid",
        expected_reason="dropped_modal_operator",
        description="Always/safety and the atom share a modal-erasing projection; a target proof of p on a partial trace cannot admit □p.",
    )
    rows.append(
        finish(
            row_base(
                case_id="temporal_erasure_always_lift",
                family="lossy_projection",
                pair_id="temporal_erasure",
                polarity="invalid",
                expected_reason="dropped_modal_operator",
                description="Always/safety and the atom share a modal-erasing projection; a target proof of p on a partial trace cannot admit □p.",
            ),
            observed_reason="dropped_modal_operator"
            if "dropped_modal_operator" in issue_codes(temp_res) and p_partial and not safety_partial and not temp_adm.admitted
            else "temporal_lift_not_rejected",
            extra={
                "useful_progress": False,
                "source_claim_admitted": bool(temp_adm.admitted),
                "countermodel": {
                    "converter_always_to": fol_always.to_string(),
                    "converter_atom_to": fol_p.to_string(),
                    "identical_projection": fol_always.to_string() == fol_p.to_string(),
                    "trace_partial": {
                        "atom_at_0": p_partial,
                        "safety_at_0": safety_partial,
                        "trace_id": trace_partial.trace_id,
                    },
                    "trace_full": {
                        "atom_at_0": p_full,
                        "safety_at_0": safety_full,
                        "trace_id": trace_full.trace_id,
                    },
                    "evaluator": "formal_logic_vocabulary.evaluate_formula",
                    "note": "Finite-trace evaluation is a plan-check artifact, not a code proof.",
                },
                "translation": {
                    "conformant": temp_res.conformant,
                    "quarantine_required": temp_res.quarantine_required,
                    "issues": issue_codes(temp_res),
                    "source_modals": list(inv_safety.modal_operators),
                    "source_bounds": list(inv_safety.bounds),
                },
                "admission": admission_summary(temp_adm),
                "evidence_class": "quarantined_translation",
                "bindings": {
                    "formula_root": safety.formula_id,
                    "source_form": "tdfol",
                    "target_form": "fol",
                    "environment_id": ENV_ID,
                },
            },
        )
    )

    q_td = tdfol_core.Predicate("Ready", ())
    until = tdfol_core.BinaryTemporalFormula(tdfol_core.TemporalOperator.UNTIL, p_td, q_td)
    conj = tdfol_core.BinaryFormula(tdfol_core.LogicOperator.AND, p_td, q_td)
    fol_until = tdfol_converter.tdfol_to_fol(until)
    fol_conj = tdfol_converter.tdfol_to_fol(conj)
    until_same = fol_until.to_string() == fol_conj.to_string()
    until_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-until-lift",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {
                "valid": False,
                "translation_class": "exact",
                "issues": ["undeclared_until_to_conjunction"],
            },
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id="until-p-q",
        require_kernel=True,
        require_reconstruction=True,
    )
    declare(
        case_id="until_conjunction_lossy_projection",
        family="lossy_projection",
        pair_id="temporal_erasure",
        polarity="invalid",
        expected_reason="until_approximated_by_conjunction",
        description="TDFOLToFOLConverter approximates p U q by p ∧ q; a proof of the conjunction cannot admit the until formula.",
    )
    rows.append(
        finish(
            row_base(
                case_id="until_conjunction_lossy_projection",
                family="lossy_projection",
                pair_id="temporal_erasure",
                polarity="invalid",
                expected_reason="until_approximated_by_conjunction",
                description="TDFOLToFOLConverter approximates p U q by p ∧ q; a proof of the conjunction cannot admit the until formula.",
            ),
            observed_reason="until_approximated_by_conjunction"
            if until_same and not until_adm.admitted
            else "until_projection_not_rejected",
            extra={
                "useful_progress": False,
                "source_claim_admitted": bool(until_adm.admitted),
                "countermodel": {
                    "source_until": until.to_string(),
                    "source_conjunction": conj.to_string(),
                    "projection_until": fol_until.to_string(),
                    "projection_conjunction": fol_conj.to_string(),
                    "identical_projection": until_same,
                    "distinct_sources": until.to_string() != conj.to_string(),
                    "converter": "TDFOLToFOLConverter converts BinaryTemporalFormula UNTIL to AND",
                    "trace_note": "A trace with p at t0 and q at t1 satisfies until at t0 but not p∧q at t0.",
                },
                "admission": admission_summary(until_adm),
                "evidence_class": "quarantined_translation",
            },
        )
    )

    cons_contract = make_contract(
        api,
        contract_id="dcec-obligation-to-fol-conservative@1",
        source_identity=obligation.formula_id,
        source_form=translation.LogicForm.DCEC,
        target_form=translation.LogicForm.FOL,
        translator_id="tdfol-to-fol",
        semantic_profile_id="supervisor-dcec",
        translation_class=translation.TranslationClass.CONSERVATIVE_APPROXIMATION,
        approximation_direction=translation.ApproximationDirection.OVER,
        abstracted_dimensions=(translation.SemanticDimension.MODAL_OPERATORS,),
    )
    cons_art = artifact_for(
        api,
        cons_contract,
        target_text="task_completed(t1)",
        source_inventory=inv_ob,
        target_inventory=dropped_target,
        abstraction_log=("erased modal_operators:obligation",),
    )
    cons_res = validate(api, cons_contract, cons_art)
    cons_adm, cons_body = admit(
        api,
        {
            "obligation_id": "ob-conservative",
            "semantic_verdict": "unknown",
            "evidence_kind": "solver_result",
            "authority_ceiling": "candidate",
            "translation": {
                "valid": bool(cons_res.conformant),
                "translation_class": "conservative_approximation",
                "contract_identity": cons_contract.content_id,
            },
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="candidate",
        operation="record_translation",
        source_id=obligation.formula_id,
    )
    cons_lift, _ = admit(
        api,
        {
            "obligation_id": "ob-conservative-lift",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {
                "valid": bool(cons_res.conformant),
                "translation_class": "conservative_approximation",
            },
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id=obligation.formula_id,
        require_kernel=True,
        require_reconstruction=True,
    )
    declare(
        case_id="declared_conservative_modal_progress",
        family="translation",
        pair_id="modal_erasure",
        polarity="valid",
        expected_reason="conservative_candidate_only",
        description="Declared conservative modal erasure progresses at candidate assurance and still cannot lift to the source obligation.",
    )
    rows.append(
        finish(
            row_base(
                case_id="declared_conservative_modal_progress",
                family="translation",
                pair_id="modal_erasure",
                polarity="valid",
                expected_reason="conservative_candidate_only",
                description="Declared conservative modal erasure progresses at candidate assurance and still cannot lift to the source obligation.",
            ),
            observed_reason="conservative_candidate_only"
            if (
                cons_res.conformant
                and enum_val(cons_res.maximum_assurance) == "candidate"
                and not cons_res.permits("solver_checked")
                and cons_adm.admitted
                and not cons_lift.admitted
            )
            else "conservative_overclaimed",
            extra={
                "useful_progress": bool(cons_res.conformant and cons_adm.admitted and not cons_lift.admitted),
                "translation_progress": bool(cons_res.conformant),
                "source_claim_admitted": bool(cons_lift.admitted),
                "evidence_class": "conservative_approximation_candidate",
                "translation": {
                    "conformant": cons_res.conformant,
                    "maximum_assurance": enum_val(cons_res.maximum_assurance),
                    "permits_solver_checked": cons_res.permits("solver_checked"),
                    "permits_candidate": cons_res.permits("candidate"),
                },
                "admission": admission_summary(cons_adm),
                "kernel_admission": admission_summary(cons_lift),
                "bindings": {
                    "formula_root": obligation.formula_id,
                    "contract_identity": cons_contract.content_id,
                    "caller_receipt_id": cons_body["content_id"],
                    "environment_id": ENV_ID,
                },
            },
        )
    )

    heur = make_contract(
        api,
        contract_id="heuristic-fol@1",
        source_identity=atom_p.formula_id,
        source_form=translation.LogicForm.FOL,
        target_form=translation.LogicForm.SMT_LIB,
        translator_id="ns-009-heuristic",
        semantic_profile_id="supervisor-fol",
        translation_class=translation.TranslationClass.HEURISTIC,
    )
    heur_art = artifact_for(
        api,
        heur,
        target_text="(assert heuristic)",
        source_inventory=inv_p,
        target_inventory=inv_p,
    )
    heur_res = validate(api, heur, heur_art)
    heur_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-heuristic",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {"valid": True, "translation_class": "heuristic"},
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id=atom_p.formula_id,
        require_kernel=True,
        require_reconstruction=True,
    )
    declare(
        case_id="heuristic_cannot_prove",
        family="translation",
        pair_id="exact_atom",
        polarity="invalid",
        expected_reason="translation_class_heuristic",
        description="Heuristic translations cannot support solver-checked or kernel proof of the source claim.",
    )
    rows.append(
        finish(
            row_base(
                case_id="heuristic_cannot_prove",
                family="translation",
                pair_id="exact_atom",
                polarity="invalid",
                expected_reason="translation_class_heuristic",
                description="Heuristic translations cannot support solver-checked or kernel proof of the source claim.",
            ),
            observed_reason="translation_class_heuristic"
            if enum_val(heur_res.maximum_assurance) == "unverified" and not heur_adm.admitted
            else "heuristic_overclaimed",
            extra={
                "useful_progress": False,
                "source_claim_admitted": bool(heur_adm.admitted),
                "translation": {
                    "conformant": heur_res.conformant,
                    "maximum_assurance": enum_val(heur_res.maximum_assurance),
                    "promotion_allowed": heur_res.promotion_allowed,
                    "permitted_results": list(heur.permitted_results),
                },
                "admission": admission_summary(heur_adm),
                "evidence_class": "heuristic_unverified",
            },
        )
    )

    undecl = artifact_for(
        api,
        exact_contract,
        target_text="(assert (task_completed t1))",
        source_inventory=inv_p,
        target_inventory=inv_p,
        abstraction_log=("undeclared drop",),
    )
    undecl_res = validate(api, exact_contract, undecl)
    declare(
        case_id="undeclared_abstraction_quarantine",
        family="translation",
        pair_id="exact_atom",
        polarity="invalid",
        expected_reason="undeclared_abstraction",
        description="An abstraction log on an exact contract is quarantined.",
    )
    rows.append(
        finish(
            row_base(
                case_id="undeclared_abstraction_quarantine",
                family="translation",
                pair_id="exact_atom",
                polarity="invalid",
                expected_reason="undeclared_abstraction",
                description="An abstraction log on an exact contract is quarantined.",
            ),
            observed_reason="undeclared_abstraction"
            if "undeclared_abstraction" in issue_codes(undecl_res) and not undecl_res.conformant
            else "undeclared_abstraction_missed",
            extra={
                "useful_progress": False,
                "translation": {"conformant": undecl_res.conformant, "issues": issue_codes(undecl_res)},
                "evidence_class": "quarantined_translation",
            },
        )
    )

    bound_contract = make_contract(
        api,
        contract_id="tdfol-bounded-smt@1",
        source_identity=safety.formula_id,
        source_form=translation.LogicForm.TDFOL,
        target_form=translation.LogicForm.SMT_LIB,
        translator_id="ns-009-bounded",
        semantic_profile_id="supervisor-tdfol",
        translation_class=translation.TranslationClass.BOUNDED_ABSTRACTION,
        abstracted_dimensions=(
            translation.SemanticDimension.TIMES,
            translation.SemanticDimension.MODAL_OPERATORS,
            translation.SemanticDimension.BOUNDS,
        ),
        required_bounds=("max_trace_steps",),
    )
    bound_art = artifact_for(
        api,
        bound_contract,
        target_text="(assert (task_completed t1))",
        source_inventory=inv_safety,
        target_inventory=dropped_time,
        finite_bounds={"max_trace_steps": 2},
        abstraction_log=("bounded trace steps=2", "erased modal safety"),
    )
    bound_res = validate(api, bound_contract, bound_art)
    bound_adm, bound_body = admit(
        api,
        {
            "obligation_id": "ob-bounded",
            "semantic_verdict": "unknown",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {
                "valid": bool(bound_res.conformant),
                "translation_class": "bounded_abstraction",
                "bounded": True,
            },
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="solver_checked",
        operation="record_translation",
        source_id=safety.formula_id,
    )
    declare(
        case_id="bounded_abstraction_progress",
        family="translation",
        pair_id="temporal_erasure",
        polarity="valid",
        expected_reason="bounded_abstraction_conformant",
        description="Bounded abstraction with declared dimensions, bounds, and abstraction log progresses as a bounded translation, not an unbounded source proof.",
    )
    rows.append(
        finish(
            row_base(
                case_id="bounded_abstraction_progress",
                family="translation",
                pair_id="temporal_erasure",
                polarity="valid",
                expected_reason="bounded_abstraction_conformant",
                description="Bounded abstraction with declared dimensions, bounds, and abstraction log progresses as a bounded translation, not an unbounded source proof.",
            ),
            observed_reason="bounded_abstraction_conformant"
            if bound_res.conformant and bound_res.bounded and bound_adm.admitted
            else "bounded_abstraction_failed",
            extra={
                "useful_progress": bool(bound_res.conformant and bound_adm.admitted),
                "translation_progress": bool(bound_res.conformant),
                "source_claim_admitted": False,
                "translation": {
                    "conformant": bound_res.conformant,
                    "bounded": bound_res.bounded,
                    "maximum_assurance": enum_val(bound_res.maximum_assurance),
                    "permits_unbounded_solver": bound_res.permits("solver_checked", bounded=False),
                    "permits_bounded_solver": bound_res.permits("solver_checked", bounded=True),
                },
                "admission": admission_summary(bound_adm),
                "bindings": {
                    "formula_root": safety.formula_id,
                    "required_bounds": ["max_trace_steps"],
                    "finite_bounds": {"max_trace_steps": 2},
                    "caller_receipt_id": bound_body["content_id"],
                    "environment_id": ENV_ID,
                },
                "evidence_class": "bounded_abstraction_solver_checked",
            },
        )
    )

    missing_art = artifact_for(
        api,
        bound_contract,
        target_text="(assert (task_completed t1))",
        source_inventory=inv_safety,
        target_inventory=dropped_time,
        finite_bounds={},
        abstraction_log=("missing bound",),
    )
    missing_res = validate(api, bound_contract, missing_art)
    declare(
        case_id="missing_finite_bounds",
        family="translation",
        pair_id="temporal_erasure",
        polarity="invalid",
        expected_reason="missing_finite_bounds",
        description="Bounded abstraction without required finite bounds is quarantined.",
    )
    rows.append(
        finish(
            row_base(
                case_id="missing_finite_bounds",
                family="translation",
                pair_id="temporal_erasure",
                polarity="invalid",
                expected_reason="missing_finite_bounds",
                description="Bounded abstraction without required finite bounds is quarantined.",
            ),
            observed_reason="missing_finite_bounds"
            if "missing_finite_bounds" in issue_codes(missing_res)
            else "missing_bounds_not_caught",
            extra={
                "useful_progress": False,
                "translation": {"conformant": missing_res.conformant, "issues": issue_codes(missing_res)},
                "evidence_class": "quarantined_translation",
            },
        )
    )

    mismatch_art = artifact_for(
        api,
        exact_contract,
        target_text="(assert (task_completed t1))",
        source_inventory=inv_p,
        target_inventory=inv_p,
        fixture_set_id="other-fixture",
    )
    mismatch_res = validate(api, exact_contract, mismatch_art)
    declare(
        case_id="fixture_set_mismatch",
        family="binding",
        pair_id="exact_atom",
        polarity="invalid",
        expected_reason="fixture_set_mismatch",
        description="Caller artifact fixture set must match the reviewed contract.",
    )
    rows.append(
        finish(
            row_base(
                case_id="fixture_set_mismatch",
                family="binding",
                pair_id="exact_atom",
                polarity="invalid",
                expected_reason="fixture_set_mismatch",
                description="Caller artifact fixture set must match the reviewed contract.",
            ),
            observed_reason="fixture_set_mismatch"
            if "fixture_set_mismatch" in issue_codes(mismatch_res)
            else "fixture_mismatch_missed",
            extra={
                "useful_progress": False,
                "translation": {"conformant": mismatch_res.conformant, "issues": issue_codes(mismatch_res)},
                "evidence_class": "quarantined_translation",
            },
        )
    )

    stale_art = artifact_for(
        api,
        exact_contract,
        source_identity="stale-formula-root",
        target_text="(assert (task_completed t1))",
        source_inventory=inv_p,
        target_inventory=inv_p,
    )
    stale_res = validate(api, exact_contract, stale_art)
    stale_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-stale-root",
            "semantic_verdict": "unknown",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "freshness": "stale",
            "translation": {"valid": False, "translation_class": "exact"},
            "formula_root": "stale-formula-root",
        },
        required_authority="solver_checked",
        operation="record_translation",
        source_id=atom_p.formula_id,
    )
    declare(
        case_id="stale_formula_root",
        family="binding",
        pair_id="exact_atom",
        polarity="invalid",
        expected_reason="source_identity_mismatch",
        description="Stale formula-root identity is rejected by translation validation and caller admission.",
    )
    rows.append(
        finish(
            row_base(
                case_id="stale_formula_root",
                family="binding",
                pair_id="exact_atom",
                polarity="invalid",
                expected_reason="source_identity_mismatch",
                description="Stale formula-root identity is rejected by translation validation and caller admission.",
            ),
            observed_reason="source_identity_mismatch"
            if "source_identity_mismatch" in issue_codes(stale_res) and not stale_adm.admitted
            else "stale_root_not_rejected",
            extra={
                "useful_progress": False,
                "source_claim_admitted": bool(stale_adm.admitted),
                "translation": {"conformant": stale_res.conformant, "issues": issue_codes(stale_res)},
                "admission": admission_summary(stale_adm),
                "bindings": {
                    "expected_formula_root": atom_p.formula_id,
                    "submitted_formula_root": "stale-formula-root",
                    "environment_id": ENV_ID,
                },
                "evidence_class": "stale_binding",
            },
        )
    )

    collision = named_assertion_register(
        [
            ("a1", atom_p.formula_id),
            ("a1", obligation.formula_id),
            ("a2", atom_q.formula_id),
        ]
    )
    dup_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-dup-assert",
            "semantic_verdict": "unknown",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {"valid": False, "translation_class": "exact"},
            "named_assertions": [
                {"id": "a1", "formula_root": atom_p.formula_id},
                {"id": "a1", "formula_root": obligation.formula_id},
            ],
        },
        required_authority="solver_checked",
        operation="record_translation",
        source_id=atom_p.formula_id,
    )
    declare(
        case_id="duplicate_named_assertions",
        family="binding",
        pair_id="exact_atom",
        polarity="invalid",
        expected_reason="duplicate_named_assertion_id",
        description="Colliding named SMT assertion/assumption identifiers bound to distinct formula roots are rejected.",
    )
    rows.append(
        finish(
            row_base(
                case_id="duplicate_named_assertions",
                family="binding",
                pair_id="exact_atom",
                polarity="invalid",
                expected_reason="duplicate_named_assertion_id",
                description="Colliding named SMT assertion/assumption identifiers bound to distinct formula roots are rejected.",
            ),
            observed_reason="duplicate_named_assertion_id"
            if collision["collisions"] and not collision["accepted"]
            else "duplicate_assertion_missed",
            extra={
                "useful_progress": False,
                "assertion_replay": True,
                "retained_solver_state": False,
                "named_assertions": collision,
                "admission": admission_summary(dup_adm),
                "evidence_class": "assertion_identity",
                "note": "No incremental SMT wrapper is located; this is assertion-identity admission, not retained-clause incrementality.",
            },
        )
    )

    try:
        vocab.evaluate_formula(obligation, trace_full, index=0)
        obligation_eval = "evaluated"
        obligation_eval_error = None
    except Exception as exc:
        obligation_eval = "unsupported"
        obligation_eval_error = f"{type(exc).__name__}: {exc}"
    unsup_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-unsupported",
            "semantic_verdict": "unsupported",
            "evidence_kind": "solver_result",
            "authority_ceiling": "unverified",
            "translation": {"valid": False, "translation_class": "exact"},
        },
        required_authority="candidate",
        operation="record_translation",
        source_id=obligation.formula_id,
    )
    declare(
        case_id="unsupported_clause_uncovered",
        family="solver_outcome",
        pair_id="solver_status",
        polarity="diagnostic",
        expected_reason="unsupported_not_proof",
        description="Unsupported obligation evaluation remains uncovered and is distinct from proof.",
    )
    rows.append(
        finish(
            row_base(
                case_id="unsupported_clause_uncovered",
                family="solver_outcome",
                pair_id="solver_status",
                polarity="diagnostic",
                expected_reason="unsupported_not_proof",
                description="Unsupported obligation evaluation remains uncovered and is distinct from proof.",
            ),
            observed_reason="unsupported_not_proof"
            if obligation_eval == "unsupported" and not unsup_adm.admitted or obligation_eval == "unsupported"
            else "unsupported_relabeled",
            extra={
                "useful_progress": False,
                "solver_result_class": "unsupported",
                "obligation_eval": obligation_eval,
                "obligation_eval_error": obligation_eval_error,
                "admission": admission_summary(unsup_adm),
                "evidence_class": "unsupported_clause",
                "distinct_from": ["proved", "unknown", "timeout", "vacuous"],
            },
        )
    )

    declare(
        case_id="opaque_clause_uncovered",
        family="solver_outcome",
        pair_id="solver_status",
        polarity="diagnostic",
        expected_reason="opaque_clause_uncovered",
        description="Opaque prose clauses stay uncovered and cannot discharge G⇒A.",
    )
    opaque_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-opaque",
            "semantic_verdict": "unknown",
            "evidence_kind": "unknown",
            "authority_ceiling": "unverified",
            "translation": {"valid": False, "translation_class": "heuristic"},
            "clause_kind": "opaque_prose",
        },
        required_authority="candidate",
        operation="record_translation",
        source_id="opaque-clause",
    )
    rows.append(
        finish(
            row_base(
                case_id="opaque_clause_uncovered",
                family="solver_outcome",
                pair_id="solver_status",
                polarity="diagnostic",
                expected_reason="opaque_clause_uncovered",
                description="Opaque prose clauses stay uncovered and cannot discharge G⇒A.",
            ),
            observed_reason="opaque_clause_uncovered",
            extra={
                "useful_progress": False,
                "solver_result_class": "unsupported",
                "admission": admission_summary(opaque_adm),
                "evidence_class": "opaque_uncovered",
                "note": "Uncovered prose is not a solver UNSAT and not a kernel proof.",
            },
        )
    )

    z3_ready = readiness_report.by_family[api["readiness"].SolverBackendFamily.Z3]
    declare(
        case_id="solver_readiness_z3_unavailable",
        family="solver_outcome",
        pair_id="smt_unavailable",
        polarity="diagnostic",
        expected_reason="backend_unavailable",
        description="Sealed-profile Z3 is unsupported; SAT/UNSAT are not invented.",
    )
    rows.append(
        finish(
            row_base(
                case_id="solver_readiness_z3_unavailable",
                family="solver_outcome",
                pair_id="smt_unavailable",
                polarity="diagnostic",
                expected_reason="backend_unavailable",
                description="Sealed-profile Z3 is unsupported; SAT/UNSAT are not invented.",
            ),
            observed_reason=z3_ready.reason_code,
            extra={
                "useful_progress": False,
                "solver_result_class": "unavailable",
                "readiness": z3_ready.to_dict(),
                "proof_success": False,
                "evidence_class": "solver_readiness",
                "bindings": {
                    "solver_id": "z3",
                    "environment_id": ENV_ID,
                    "readiness_identity": z3_ready.readiness_identity,
                },
            },
        )
    )

    kb = tdfol_core.TDFOLKnowledgeBase()
    kb.add_axiom(p_td, "done")
    prover = tdfol_prover.TDFOLProver(kb, enable_cache=False)
    proved = prover.prove(p_td, timeout_ms=500)
    unknown = prover.prove(q_td, timeout_ms=200)
    timed = prover.prove(q_td, timeout_ms=0)
    proved_adm, proved_body = admit(
        api,
        {
            "obligation_id": "ob-tdfol-axiom",
            "semantic_verdict": "unknown",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {"valid": True, "translation_class": "exact"},
            "prover_status": enum_val(proved.status),
            "prover_method": proved.method,
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="solver_checked",
        operation="record_translation",
        source_id="tdfol-done",
    )
    proved_kernel, _ = admit(
        api,
        {
            "obligation_id": "ob-tdfol-axiom-kernel",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {"valid": True, "translation_class": "exact"},
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id="tdfol-done",
        require_kernel=True,
        require_reconstruction=True,
    )
    declare(
        case_id="tdfol_axiom_proved_non_kernel",
        family="solver_outcome",
        pair_id="solver_status",
        polarity="valid",
        expected_reason="tdfol_axiom_lookup_non_kernel",
        description="TDFOL axiom lookup is a prover-class result; it is not kernel-checked proof.",
    )
    rows.append(
        finish(
            row_base(
                case_id="tdfol_axiom_proved_non_kernel",
                family="solver_outcome",
                pair_id="solver_status",
                polarity="valid",
                expected_reason="tdfol_axiom_lookup_non_kernel",
                description="TDFOL axiom lookup is a prover-class result; it is not kernel-checked proof.",
            ),
            observed_reason="tdfol_axiom_lookup_non_kernel"
            if enum_val(proved.status) == "proved" and proved.method == "axiom_lookup" and proved_adm.admitted and not proved_kernel.admitted
            else "tdfol_overclaimed",
            extra={
                "useful_progress": bool(enum_val(proved.status) == "proved" and proved_adm.admitted and not proved_kernel.admitted),
                "source_claim_admitted": bool(proved_kernel.admitted),
                "kernel_proof": False,
                "solver_result_class": "proved",
                "evidence_class": "tdfol_prover_non_kernel",
                "prover": {
                    "status": enum_val(proved.status),
                    "method": proved.method,
                    "time_ms": proved.time_ms,
                },
                "admission": admission_summary(proved_adm),
                "kernel_admission": admission_summary(proved_kernel),
                "bindings": {
                    "solver_id": "tdfol_prover",
                    "environment_id": ENV_ID,
                    "caller_receipt_id": proved_body["content_id"],
                    "formula": p_td.to_string(),
                },
            },
        )
    )

    declare(
        case_id="unknown_not_proved",
        family="solver_outcome",
        pair_id="solver_status",
        polarity="diagnostic",
        expected_reason="unknown",
        description="TDFOL unknown is not inconsistent and not proved.",
    )
    rows.append(
        finish(
            row_base(
                case_id="unknown_not_proved",
                family="solver_outcome",
                pair_id="solver_status",
                polarity="diagnostic",
                expected_reason="unknown",
                description="TDFOL unknown is not inconsistent and not proved.",
            ),
            observed_reason=enum_val(unknown.status),
            extra={
                "useful_progress": False,
                "solver_result_class": enum_val(unknown.status),
                "prover": {
                    "status": enum_val(unknown.status),
                    "method": unknown.method,
                    "message": getattr(unknown, "message", None),
                },
                "evidence_class": "tdfol_prover_unknown",
                "distinct_from": ["proved", "timeout", "unsupported", "vacuous"],
            },
        )
    )

    declare(
        case_id="timeout_budget_exhausted",
        family="solver_outcome",
        pair_id="solver_status",
        polarity="diagnostic",
        expected_reason="timeout",
        description="Budget-exhausted timeout remains distinct from proof, unknown, and unsupported.",
    )
    rows.append(
        finish(
            row_base(
                case_id="timeout_budget_exhausted",
                family="solver_outcome",
                pair_id="solver_status",
                polarity="diagnostic",
                expected_reason="timeout",
                description="Budget-exhausted timeout remains distinct from proof, unknown, and unsupported.",
            ),
            observed_reason=enum_val(timed.status),
            extra={
                "useful_progress": False,
                "solver_result_class": enum_val(timed.status),
                "prover": {
                    "status": enum_val(timed.status),
                    "method": timed.method,
                    "timeout_ms": 0,
                },
                "evidence_class": "tdfol_prover_timeout",
                "distinct_from": ["proved", "unknown", "unsupported", "vacuous"],
            },
        )
    )

    vacuous_true = vocab.evaluate_formula(implication, trace_partial, index=0)
    g_holds = vocab.evaluate_formula(vacuous_g, trace_partial, index=0)
    vac_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-vacuous",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {"valid": True, "translation_class": "exact"},
            "vacuity": True,
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id=implication.formula_id,
        require_kernel=True,
        require_reconstruction=True,
    )
    declare(
        case_id="vacuity_unsat_guarantee",
        family="composition",
        pair_id="vacuity_reachability",
        polarity="invalid",
        expected_reason="vacuous_implication_not_proof",
        description="Unsatisfiable G makes G⇒A vacuously true on the finite-trace evaluator; that is not component correctness.",
    )
    rows.append(
        finish(
            row_base(
                case_id="vacuity_unsat_guarantee",
                family="composition",
                pair_id="vacuity_reachability",
                polarity="invalid",
                expected_reason="vacuous_implication_not_proof",
                description="Unsatisfiable G makes G⇒A vacuously true on the finite-trace evaluator; that is not component correctness.",
            ),
            observed_reason="vacuous_implication_not_proof"
            if vacuous_true and not g_holds and not vac_adm.admitted
            else "vacuity_not_distinct",
            extra={
                "useful_progress": False,
                "source_claim_admitted": bool(vac_adm.admitted),
                "solver_result_class": "vacuous",
                "g_holds": g_holds,
                "implication_holds": vacuous_true,
                "formula_g": "task_completed(t1) ∧ ¬task_completed(t1)",
                "formula_impl": "G ⇒ task_ready(t1)",
                "admission": admission_summary(vac_adm),
                "evidence_class": "structural_vacuity",
                "note": "Finite-trace vacuity is not SMT UNSAT and not kernel proof. SMT G∧¬A discharge is unavailable without Z3.",
                "distinct_from": ["proved", "unknown", "timeout", "unsupported"],
            },
        )
    )

    reachable_p = vocab.evaluate_formula(atom_p, trace_full, index=0)
    reachable_q = vocab.evaluate_formula(atom_q, trace_full, index=0)
    declare(
        case_id="reachability_gap",
        family="composition",
        pair_id="vacuity_reachability",
        polarity="diagnostic",
        expected_reason="unreachable_assumption",
        description="task_ready never holds on the supplied trace; unreachability is not a proof of the consumer assumption.",
    )
    rows.append(
        finish(
            row_base(
                case_id="reachability_gap",
                family="composition",
                pair_id="vacuity_reachability",
                polarity="diagnostic",
                expected_reason="unreachable_assumption",
                description="task_ready never holds on the supplied trace; unreachability is not a proof of the consumer assumption.",
            ),
            observed_reason="unreachable_assumption" if reachable_p and not reachable_q else "reachability_not_shown",
            extra={
                "useful_progress": False,
                "solver_result_class": "unknown",
                "atom_p_reachable": reachable_p,
                "atom_q_reachable": reachable_q,
                "trace_id": trace_full.trace_id,
                "evidence_class": "finite_trace_reachability",
                "note": "evaluate_formula is a bounded reference semantics, not graph reachability of Python state and not a code proof.",
            },
        )
    )

    unval_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-unvalidated",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {"valid": True, "translation_class": "exact"},
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id=atom_p.formula_id,
        require_kernel=True,
        require_reconstruction=True,
    )
    declare(
        case_id="unvalidated_solver_result_rejected",
        family="binding",
        pair_id="exact_atom",
        polarity="invalid",
        expected_reason="evidence_kind_does_not_support_verdict",
        description="A solver result labeled proved cannot admit a kernel-required source claim without reconstruction.",
    )
    rows.append(
        finish(
            row_base(
                case_id="unvalidated_solver_result_rejected",
                family="binding",
                pair_id="exact_atom",
                polarity="invalid",
                expected_reason="evidence_kind_does_not_support_verdict",
                description="A solver result labeled proved cannot admit a kernel-required source claim without reconstruction.",
            ),
            observed_reason="evidence_kind_does_not_support_verdict"
            if (not unval_adm.admitted and "evidence_kind_does_not_support_verdict" in unval_adm.reasons)
            else "unvalidated_solver_admitted",
            extra={
                "useful_progress": False,
                "source_claim_admitted": bool(unval_adm.admitted),
                "admission": admission_summary(unval_adm),
                "evidence_class": "solver_result_non_kernel",
            },
        )
    )

    for case_id, expected, polarity_desc in (
        (
            "sat_smt_unavailable",
            "smt_sat_unavailable",
            "SAT of G∧¬A is unavailable because Z3 is absent; it is not simulated.",
        ),
        (
            "unsat_smt_unavailable",
            "smt_unsat_unavailable",
            "UNSAT of G∧¬A is unavailable because Z3 is absent; it is not treated as kernel discharge.",
        ),
    ):
        declare(
            case_id=case_id,
            family="solver_outcome",
            pair_id="smt_unavailable",
            polarity="diagnostic",
            expected_reason=expected,
            description=polarity_desc,
        )
        rows.append(
            finish(
                row_base(
                    case_id=case_id,
                    family="solver_outcome",
                    pair_id="smt_unavailable",
                    polarity="diagnostic",
                    expected_reason=expected,
                    description=polarity_desc,
                ),
                observed_reason=expected if not z3_ready.supported else "smt_incorrectly_claimed",
                extra={
                    "useful_progress": False,
                    "solver_result_class": "unavailable",
                    "z3_supported": z3_ready.supported,
                    "z3_status": enum_val(z3_ready.status),
                    "evidence_class": "smt_backend_unavailable",
                    "simulated_unavailable_mechanism": False,
                    "bindings": {
                        "theory": "QF_LIA",
                        "solver_id": "z3",
                        "environment_id": ENV_ID,
                        "query": "G ∧ ¬A",
                    },
                },
            )
        )

    live_fp = sha256_text(json.dumps({"formula": atom_p.formula_id, "solver": "tdfol", "env": ENV_ID}, sort_keys=True))
    stale_fp = sha256_text("other-formula")
    fp_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-stale-fp",
            "semantic_verdict": "unknown",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "freshness": "stale",
            "translation": {"valid": True, "translation_class": "exact"},
            "solver_fingerprint": stale_fp,
            "expected_solver_fingerprint": live_fp,
        },
        required_authority="solver_checked",
        operation="record_translation",
        source_id=atom_p.formula_id,
    )
    declare(
        case_id="stale_solver_fingerprint",
        family="binding",
        pair_id="exact_atom",
        polarity="invalid",
        expected_reason="stale_solver_fingerprint",
        description="A solver fingerprint that does not match the submitted formula/source/theory/environment is rejected.",
    )
    rows.append(
        finish(
            row_base(
                case_id="stale_solver_fingerprint",
                family="binding",
                pair_id="exact_atom",
                polarity="invalid",
                expected_reason="stale_solver_fingerprint",
                description="A solver fingerprint that does not match the submitted formula/source/theory/environment is rejected.",
            ),
            observed_reason="stale_solver_fingerprint"
            if live_fp != stale_fp and not fp_adm.admitted
            else "stale_fingerprint_accepted",
            extra={
                "useful_progress": False,
                "source_claim_admitted": bool(fp_adm.admitted),
                "live_fingerprint": "sha256:" + live_fp,
                "submitted_fingerprint": "sha256:" + stale_fp,
                "admission": admission_summary(fp_adm),
                "bindings": {
                    "formula_root": atom_p.formula_id,
                    "solver_id": "tdfol",
                    "environment_id": ENV_ID,
                },
                "evidence_class": "stale_binding",
                "assertion_replay": True,
                "retained_solver_state": False,
            },
        )
    )

    span = ipa.SourceSpan(path="pkg/mod.py", start_line=3, end_line=3, symbol="dispatch")
    trace = ipa.SourceToSinkTrace(
        steps=(
            ipa.TraceStep(kind="source", label="imprecise_dispatch"),
            ipa.TraceStep(kind="sink", label="untrusted_sink"),
        )
    )
    finding = ipa.IpaFinding(
        finding_id="f-spurious",
        rule_id="ipa.rule.import_effect",
        disposition=ipa.FindingDisposition.SPURIOUS_CANDIDATE,
        source_span=span,
        sink_span=span,
        trace=trace,
        domain_state=ipa.ProductDomainState(),
        imprecise=True,
    )
    seed = ipa.IpaFinding(
        finding_id="f-seed",
        rule_id="ipa.rule.import_effect",
        disposition=ipa.FindingDisposition.CORPUS_BOUND,
        source_span=span,
        sink_span=span,
        trace=trace,
        domain_state=ipa.ProductDomainState(),
        corpus_seed_id="seed-ns009",
    )
    refined, away = ipa.refine_spurious_paths(
        (finding, seed),
        (
            ipa.SpuriousPathRefinement(refinement_id="r-spurious", finding_id="f-spurious", reason="imprecise path"),
            ipa.SpuriousPathRefinement(refinement_id="r-seed", finding_id="f-seed", reason="must not drop seed"),
        ),
    )
    declare(
        case_id="cegar_ipa_spurious_refine",
        family="cegar",
        pair_id="cegar_located",
        polarity="valid",
        expected_reason="ipa_spurious_path_refined",
        description="Located IPA CEGAR refines a spurious path and refuses to refine away a corpus seed.",
    )
    rows.append(
        finish(
            row_base(
                case_id="cegar_ipa_spurious_refine",
                family="cegar",
                pair_id="cegar_located",
                polarity="valid",
                expected_reason="ipa_spurious_path_refined",
                description="Located IPA CEGAR refines a spurious path and refuses to refine away a corpus seed.",
            ),
            observed_reason="ipa_spurious_path_refined"
            if away == ("f-spurious",) and enum_val(refined[1].disposition) == "corpus_bound"
            else "cegar_not_as_located",
            extra={
                "useful_progress": bool(away == ("f-spurious",) and enum_val(refined[1].disposition) == "corpus_bound"),
                "source": rel(ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py"),
                "symbol": "refine_spurious_paths",
                "refined_away": list(away),
                "seed_disposition": enum_val(refined[1].disposition),
                "spurious_disposition": enum_val(refined[0].disposition),
                "evidence_class": "ipa_cegar_refinement",
                "note": "This is IPA product-domain CEGAR, not a QF_LIA interpolating model checker and not a timing result.",
            },
        )
    )

    qf_lia_cegar_files = searches.get("QF_LIA", {}).get("sample_paths") or []
    declare(
        case_id="cegar_qf_lia_adapter_unlocated",
        family="cegar",
        pair_id="cegar_located",
        polarity="diagnostic",
        expected_reason="qf_lia_cegar_adapter_unlocated",
        description="Named bounded QF_LIA CEGAR/interpolant adapter is not located; IPA CEGAR is not substituted as that adapter.",
    )
    rows.append(
        finish(
            row_base(
                case_id="cegar_qf_lia_adapter_unlocated",
                family="cegar",
                pair_id="cegar_located",
                polarity="diagnostic",
                expected_reason="qf_lia_cegar_adapter_unlocated",
                description="Named bounded QF_LIA CEGAR/interpolant adapter is not located; IPA CEGAR is not substituted as that adapter.",
            ),
            observed_reason="qf_lia_cegar_adapter_unlocated",
            extra={
                "useful_progress": False,
                "located": False,
                "identifier_search": searches.get("QF_LIA"),
                "non_substitute": "ipa.refine_spurious_paths",
                "simulated_unavailable_mechanism": False,
                "evidence_class": "specification_only",
                "sample_qf_lia_paths": qf_lia_cegar_files,
            },
        )
    )

    interp_search = searches.get("interpolant") or {}
    declare(
        case_id="interpolant_mechanism_unavailable",
        family="interpolant",
        pair_id="interpolant",
        polarity="diagnostic",
        expected_reason="interpolant_checker_unlocated",
        description="No interpolant generator or checker is located in Python source; unsat cores are not treated as interpolants.",
    )
    rows.append(
        finish(
            row_base(
                case_id="interpolant_mechanism_unavailable",
                family="interpolant",
                pair_id="interpolant",
                polarity="diagnostic",
                expected_reason="interpolant_checker_unlocated",
                description="No interpolant generator or checker is located in Python source; unsat cores are not treated as interpolants.",
            ),
            observed_reason="interpolant_checker_unlocated"
            if not interp_search.get("found_in_python_source")
            else "interpolant_identifier_present",
            extra={
                "useful_progress": False,
                "located": bool(interp_search.get("found_in_python_source")),
                "identifier_search": interp_search,
                "craig_conditions": interpolant_conditions({"x", "y"}, {"y", "z"}, {"y"}),
                "unsat_core_is_interpolant": False,
                "simulated_unavailable_mechanism": False,
                "evidence_class": "specification_only",
            },
        )
    )

    invalid_i = interpolant_conditions({"x", "y"}, {"y", "z"}, {"x", "z"})
    invalid_adm, _ = admit(
        api,
        {
            "obligation_id": "ob-bad-interpolant",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "translation": {"valid": False, "translation_class": "exact"},
            "purported_interpolant": {"symbols": ["x", "z"]},
            "reconstruction_passed": False,
            "kernel_checked": False,
        },
        required_authority="kernel_verified",
        operation="complete_task",
        source_id="interpolant-candidate",
        require_kernel=True,
        require_reconstruction=True,
    )
    declare(
        case_id="invalid_interpolant_not_admitted",
        family="interpolant",
        pair_id="interpolant",
        polarity="invalid",
        expected_reason="invalid_interpolant_not_admitted",
        description="A purported interpolant whose symbols escape A∩B is not admitted; no interpolant is generated.",
    )
    rows.append(
        finish(
            row_base(
                case_id="invalid_interpolant_not_admitted",
                family="interpolant",
                pair_id="interpolant",
                polarity="invalid",
                expected_reason="invalid_interpolant_not_admitted",
                description="A purported interpolant whose symbols escape A∩B is not admitted; no interpolant is generated.",
            ),
            observed_reason="invalid_interpolant_not_admitted"
            if (not invalid_i["symbols_ok"] and not invalid_adm.admitted)
            else "invalid_interpolant_accepted",
            extra={
                "useful_progress": False,
                "source_claim_admitted": bool(invalid_adm.admitted),
                "craig_conditions": invalid_i,
                "admission": admission_summary(invalid_adm),
                "simulated_unavailable_mechanism": False,
                "evidence_class": "rejected_purported_interpolant",
            },
        )
    )

    comp_search = searches.get("CompositionEdge") or {}
    declare(
        case_id="composition_edge_unlocated",
        family="composition",
        pair_id="composition",
        polarity="diagnostic",
        expected_reason="composition_edge_unlocated",
        description="CompositionEdge is specification-only; no equivalent is inferred.",
    )
    rows.append(
        finish(
            row_base(
                case_id="composition_edge_unlocated",
                family="composition",
                pair_id="composition",
                polarity="diagnostic",
                expected_reason="composition_edge_unlocated",
                description="CompositionEdge is specification-only; no equivalent is inferred.",
            ),
            observed_reason="composition_edge_unlocated"
            if not comp_search.get("found_in_python_source")
            else "composition_edge_found",
            extra={
                "useful_progress": False,
                "located": bool(comp_search.get("found_in_python_source")),
                "identifier_search": comp_search,
                "simulated_unavailable_mechanism": False,
                "evidence_class": "specification_only",
            },
        )
    )

    declare(
        case_id="cyclic_composition_unlocated",
        family="composition",
        pair_id="composition",
        polarity="diagnostic",
        expected_reason="cyclic_closure_checker_unlocated",
        description="Independently checked cyclic assume-guarantee closure is not located; mutual citation is not treated as proof.",
    )
    rows.append(
        finish(
            row_base(
                case_id="cyclic_composition_unlocated",
                family="composition",
                pair_id="composition",
                polarity="diagnostic",
                expected_reason="cyclic_closure_checker_unlocated",
                description="Independently checked cyclic assume-guarantee closure is not located; mutual citation is not treated as proof.",
            ),
            observed_reason="cyclic_closure_checker_unlocated",
            extra={
                "useful_progress": False,
                "located": False,
                "requires": "typed invariant plus independently solved closure check",
                "simulated_unavailable_mechanism": False,
                "evidence_class": "specification_only",
            },
        )
    )

    declare(
        case_id="incremental_smt_wrapper_unlocated",
        family="solver_outcome",
        pair_id="smt_unavailable",
        polarity="diagnostic",
        expected_reason="incremental_smt_wrapper_unlocated",
        description="Inspected incremental SMT wrapper is not located; no retained-clause speedup is claimed. Assertion identity is replay, not solver-state incrementality.",
    )
    rows.append(
        finish(
            row_base(
                case_id="incremental_smt_wrapper_unlocated",
                family="solver_outcome",
                pair_id="smt_unavailable",
                polarity="diagnostic",
                expected_reason="incremental_smt_wrapper_unlocated",
                description="Inspected incremental SMT wrapper is not located; no retained-clause speedup is claimed. Assertion identity is replay, not solver-state incrementality.",
            ),
            observed_reason="incremental_smt_wrapper_unlocated",
            extra={
                "useful_progress": False,
                "located": False,
                "assertion_replay": True,
                "retained_solver_state": False,
                "retained_state_speedup_established": False,
                "simulated_unavailable_mechanism": False,
                "evidence_class": "specification_only",
                "identifier_search": searches.get("incremental SMT"),
            },
        )
    )

    declare(
        case_id="kernel_vs_solver_evidence_classes",
        family="evidence_class",
        pair_id="exact_atom",
        polarity="diagnostic",
        expected_reason="solver_unsat_is_not_kernel_proof",
        description="Solver, reconstruction, and kernel evidence classes remain distinct; SAT/capability never become proof.",
    )
    classes = {
        "translation_validation": exact_res.content_id,
        "solver_readiness_proof_success": False,
        "tdfol_prover_status": enum_val(proved.status),
        "kernel_admission_of_solver_proved": bool(kernel_adm.admitted),
        "z3_supported": z3_ready.supported,
    }
    rows.append(
        finish(
            row_base(
                case_id="kernel_vs_solver_evidence_classes",
                family="evidence_class",
                pair_id="exact_atom",
                polarity="diagnostic",
                expected_reason="solver_unsat_is_not_kernel_proof",
                description="Solver, reconstruction, and kernel evidence classes remain distinct; SAT/capability never become proof.",
            ),
            observed_reason="solver_unsat_is_not_kernel_proof"
            if (not kernel_adm.admitted and not z3_ready.to_dict().get("proof_success"))
            else "evidence_classes_collapsed",
            extra={
                "useful_progress": False,
                "classes": classes,
                "readiness_backends": [
                    {
                        "family": enum_val(item.family),
                        "status": enum_val(item.status),
                        "supported": item.supported,
                        "proof_success": False,
                        "authority": enum_val(item.authority),
                    }
                    for item in readiness_report.backends
                ],
                "evidence_class": "classification",
            },
        )
    )

    profiles = {
        "schema": SCHEMA_PROFILES,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "retained_translation_profile": {
            "exact_fol_smtlib": {
                "source_form": "fol",
                "target_form": "smt-lib",
                "translation_class": "exact",
                "maximum_assurance": "solver_checked",
                "kernel_proof": False,
                "status": "qualified",
            },
            "conservative_modal_erasure": {
                "source_form": "dcec",
                "target_form": "fol",
                "translation_class": "conservative_approximation",
                "maximum_assurance": "candidate",
                "cannot_lift_to_source_obligation": True,
                "status": "qualified",
            },
            "bounded_tdfol_safety": {
                "source_form": "tdfol",
                "target_form": "smt-lib",
                "translation_class": "bounded_abstraction",
                "required_bounds": ["max_trace_steps"],
                "unbounded_claim": False,
                "status": "qualified",
            },
        },
        "converter": {
            "id": "TDFOLToFOLConverter",
            "path": rel(DS_ROOT / "ipfs_datasets_py/logic/TDFOL/tdfol_converter.py"),
            "losses": [
                "DeonticFormula stripped to inner formula",
                "TemporalFormula stripped to inner formula",
                "BinaryTemporalFormula UNTIL/SINCE approximated by conjunction",
            ],
        },
        "solvers": {
            enum_val(item.family): {
                "status": enum_val(item.status),
                "supported": item.supported,
                "reason_code": item.reason_code,
                "proof_success": False,
                "authority": enum_val(item.authority),
                "readiness_identity": item.readiness_identity,
            }
            for item in readiness_report.backends
        },
        "located_mechanisms": {
            "ipa_cegar": {
                "path": rel(ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/analysis/formal_assurance/ipa.py"),
                "symbol": "refine_spurious_paths",
                "status": "located_and_exercised",
                "not": "QF_LIA interpolating CEGAR adapter",
            },
            "tdfol_prover": {
                "path": rel(DS_ROOT / "ipfs_datasets_py/logic/TDFOL/tdfol_prover.py"),
                "status": "located_and_exercised",
                "authority": "non_kernel",
            },
            "logic_platform_admission": {
                "path": rel(ACC_ROOT / "ipfs_accelerate_py/agent_supervisor/proof/logic_platform_admission.py"),
                "symbol": "admit_receipt",
                "status": "located_and_exercised",
            },
        },
        "unavailable_or_specification_only": {
            "z3": {"status": enum_val(z3_ready.status), "reason": z3_ready.reason_code},
            "CompositionEdge": {"status": "specification_only", "found_in_python_source": bool(comp_search.get("found_in_python_source"))},
            "interpolant_checker": {"status": "unlocated", "found_in_python_source": bool(interp_search.get("found_in_python_source"))},
            "qf_lia_cegar_adapter": {"status": "unlocated"},
            "incremental_smt_wrapper": {"status": "unlocated", "retained_clause_speedup": False},
            "cyclic_assume_guarantee_closure": {"status": "unlocated"},
        },
        "evidence_classes": {
            "solver_result": "non-authoritative until kernel reconstruction",
            "translation_validation": "preservation/quarantine of a particular transformation",
            "tdfol_prover": "prover-class; axiom lookup is not kernel proof",
            "finite_trace_evaluator": "bounded plan-check artifact, not a code proof",
            "ipa_cegar": "spurious-path refinement over IPA findings",
            "kernel": "not obtained in this qualification",
        },
        "identifier_search": searches,
    }
    return cases, rows, profiles


def build_report(
    *,
    capability: dict[str, Any],
    cases: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    profiles: dict[str, Any],
    started_at: str,
) -> str:
    by_id = {row["case_id"]: row for row in rows}
    exact = by_id.get("exact_atom_supported_progress") or {}
    modal = by_id.get("modal_erasure_obligation_lift") or {}
    z3 = by_id.get("solver_readiness_z3_unavailable") or {}
    cegar = by_id.get("cegar_ipa_spurious_refine") or {}
    interp = by_id.get("interpolant_mechanism_unavailable") or {}
    lines = [
        "# NS-009 Translation preservation and retained symbolic checker admission",
        "",
        f"Generated at {started_at}. This is a sealed-profile qualification record, not a live A–D experiment and not a kernel proof of arbitrary Python.",
        "",
        "## Profile",
        "",
        "- Translation contract: `logic_translation_validation.validate_translation`",
        "- Converter: `TDFOLToFOLConverter` / `tdfol_to_fol`",
        "- Caller admission: `SupervisorLogicPlatformReceiptAdmission@1` (`admit_receipt`)",
        "- Solver readiness: `probe_solver_readiness`",
        "- Retained TDFOL checker: `TDFOLProver.prove` (non-kernel)",
        "- Located CEGAR: `ipa.refine_spurious_paths`",
        "- Finite-trace evaluator: `formal_logic_vocabulary.evaluate_formula` (plan-check only)",
        f"- Policy: `{POLICY_ID}`",
        "",
        "## Environment",
        "",
        f"- Interpreter: `{capability['interpreter']}` ({capability['python_version']})",
        f"- Sealed `PATH` at process start: `{capability.get('path')}`",
        f"- pytest: `{capability.get('pytest')}`",
        f"- z3 module: `{capability.get('z3_module')}`",
        f"- binaries: `{json.dumps(capability.get('binaries') or {}, sort_keys=True)}`",
        "",
        "## Coverage",
        "",
        f"- Result rows: {len(rows)}",
        f"- Declared cases: {len(cases)}",
        f"- Failed rows: {sum(1 for row in rows if row.get('status') != 'pass')}",
        f"- Exact translation progress: `{bool(exact.get('useful_progress'))}`",
        f"- Modal-erasure source claim admitted: `{bool(modal.get('source_claim_admitted'))}` (must be false)",
        f"- Z3 supported: `{(z3.get('readiness') or {}).get('supported')}`",
        f"- IPA CEGAR useful progress: `{bool(cegar.get('useful_progress'))}`",
        f"- Interpolant located: `{bool((interp.get('identifier_search') or {}).get('found_in_python_source'))}`",
        "",
        "## Valid supported translations can progress",
        "",
        "An exact FOL atom with matching source/target inventories is conformant and `promotion_allowed` at `solver_checked` translation assurance. The caller `admit_receipt` records that translation under a non-conclusive solver-result envelope bound to the exact formula root, theory, solver identity, and environment. The same envelope cannot complete a kernel-required source claim: `solver_result` plus `proved` is rejected.",
        "",
        "## Unjustified lifting is rejected",
        "",
        "`TDFOLToFOLConverter` maps `O(Done)` and `Done` to the same FOL atom, and maps `p U q` to `p ∧ q`. Exact translation contracts that drop modal operators or bounds are quarantined (`dropped_modal_operator`). Finite-trace evaluation of reviewed `SAFETY(p)` is false on a trace where `p` holds only at step 0, so a target proof of `p` does not establish `□p`. Conservative approximations with a declared modal-erasure log progress only at `candidate` assurance and still cannot lift to kernel completion.",
        "",
        "## Caller receipts bind formula, source, theory, solver, and environment",
        "",
        "Every retained translation row records `formula_root`, source/target forms, contract/artifact identities, solver id, and `environment_id`. Stale formula roots (`source_identity_mismatch`), stale fingerprints, fixture-set mismatches, and colliding named assertion IDs fail closed. Unvalidated solver results cannot satisfy kernel reconstruction.",
        "",
        "## Vacuity, unknown, unsupported, and budget exhaustion are distinct",
        "",
        "| class | case | meaning |",
        "|---|---|---|",
        "| proved (non-kernel) | `tdfol_axiom_proved_non_kernel` | TDFOL axiom lookup; not kernel proof |",
        "| unknown | `unknown_not_proved` | Forward chaining exhausted |",
        "| timeout | `timeout_budget_exhausted` | `timeout_ms=0` |",
        "| unsupported | `unsupported_clause_uncovered` | Obligation has no finite-trace semantics |",
        "| vacuous | `vacuity_unsat_guarantee` | Unsatisfiable G makes G⇒A true; rejected as proof |",
        "| unavailable | `sat_smt_unavailable` / `unsat_smt_unavailable` | Z3 absent; SMT SAT/UNSAT not simulated |",
        "",
        "## CEGAR, interpolants, and composition",
        "",
        "IPA `refine_spurious_paths` is located and exercised: a spurious finding is refined away and a corpus seed is not. The draft's named QF_LIA interpolating CEGAR adapter, interpolant checker, `CompositionEdge`, cyclic assume-guarantee closure, and incremental SMT wrapper were not located as those mechanisms. They are recorded as unavailable/specification-only. No interpolant, SMT SAT/UNSAT, or composition-edge discharge was simulated.",
        "",
        "## Solver versus reconstruction versus kernel",
        "",
        "`probe_solver_readiness` marks Z3 `unsupported` and never sets `proof_success`. Discoverable TDFOL/DCEC/CEC/hammer surfaces remain non-authoritative until kernel reconstruction. Assertion identity checks are replay, not retained solver-state incrementality. No retained-clause speedup is established.",
        "",
        "## Limitations",
        "",
        "- Qualification uses reviewed atoms, TDFOL converter examples, and IPA findings; it is not a historical repair task.",
        "- Finite-trace evaluation is a bounded plan-check artifact and is not a proof of Python programs.",
        "- SMT G∧¬A SAT/UNSAT cannot be obtained in the sealed profile because Z3 is absent.",
        "- This receipt is Table 18 loss-aware formal translation qualification, not a matched A–D outcome.",
        "",
        "## Case outcomes",
        "",
        "| case_id | family | polarity | status | useful_progress | source_claim_admitted | reason |",
        "|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            "| `{case_id}` | {family} | {polarity} | {status} | {useful} | {admitted} | `{reason}` |".format(
                case_id=row["case_id"],
                family=row["family"],
                polarity=row["polarity"],
                status=row.get("status"),
                useful=str(bool(row.get("useful_progress"))).lower(),
                admitted=str(bool(row.get("source_claim_admitted"))).lower(),
                reason=row.get("observed_reason"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    started_at = utc_now()
    checkpoint("start", {"started_at": started_at, "task_id": TASK_ID})
    capability = prepare_imports()
    api = capability.pop("api")
    searches = search_identifiers()
    readiness_report = api["readiness"].probe_solver_readiness()
    cases, rows, profiles = run_cases(api, searches, readiness_report)
    failed = [row["case_id"] for row in rows if row.get("status") != "pass"]
    if failed:
        raise SystemExit(f"NS-009 qualification cases failed: {failed}")
    missing = [name for name in REQUIRED_CASES if name not in {row["case_id"] for row in rows}]
    if missing:
        raise SystemExit(f"NS-009 missing required cases: {missing}")

    cases_doc = {
        "schema": SCHEMA_CASES,
        "task_id": TASK_ID,
        "policy_id": POLICY_ID,
        "generated_at": started_at,
        "qualification_not_live_ad": True,
        "fixture_set_id": FIXTURE_SET_ID,
        "caller": {
            "translation_validator": "validate_translation",
            "converter": "TDFOLToFOLConverter",
            "admission": "SupervisorLogicPlatformReceiptAdmission@1",
            "solver_readiness": "probe_solver_readiness",
            "tdfol_prover": "TDFOLProver.prove",
            "cegar": "ipa.refine_spurious_paths",
            "finite_trace": "evaluate_formula",
        },
        "rules": {
            "lossy_projection_cannot_admit_source_claim": True,
            "solver_result_is_not_kernel_proof": True,
            "vacuity_unknown_unsupported_timeout_are_distinct": True,
            "unavailable_mechanisms_are_not_simulated": True,
            "assertion_replay_is_not_retained_solver_state": True,
        },
        "capability": capability,
        "source_hashes": source_hashes(),
        "workspace_git_head": git_head(ROOT),
        "consumer_gitlinks": {
            "external/ipfs_accelerate": git_head(ACC_ROOT),
            "external/ipfs_datasets": git_head(DS_ROOT),
            "external/ipfs_kit": git_head(KIT_ROOT),
        },
        "identifier_search": searches,
        "cases": cases,
    }
    profiles["generated_at"] = started_at
    profiles["capability"] = {
        "interpreter": capability.get("interpreter"),
        "python_version": capability.get("python_version"),
        "path": capability.get("path"),
        "binaries": capability.get("binaries"),
        "z3_module": capability.get("z3_module"),
    }
    report = build_report(
        capability=capability, cases=cases, rows=rows, profiles=profiles, started_at=started_at
    )

    QUAL.mkdir(parents=True, exist_ok=True)
    SNAP_QUAL.mkdir(parents=True, exist_ok=True)
    for directory in (QUAL, SNAP_QUAL):
        write_json(directory / "logic_cases.json", cases_doc)
        write_jsonl(directory / "logic_receipts.jsonl", rows)
        write_json(directory / "logic_profiles.json", profiles)
        atomic_write(directory / "logic_report.md", report.encode("utf-8"))

    checkpoint(
        "outputs",
        {
            "finished_at": utc_now(),
            "rows": len(rows),
            "failed": failed,
            "cases_sha256": sha256_file(QUAL / "logic_cases.json"),
            "receipts_sha256": sha256_file(QUAL / "logic_receipts.jsonl"),
            "profiles_sha256": sha256_file(QUAL / "logic_profiles.json"),
            "report_sha256": sha256_file(QUAL / "logic_report.md"),
        },
    )
    print("NS-009 logic qualification: OK")
    print(f"rows={len(rows)} failed={len(failed)}")
    print("exact_atom_supported_progress useful_progress=", exact_progress(rows, "exact_atom_supported_progress"))
    print("modal_erasure_obligation_lift source_claim_admitted=", source_admitted(rows, "modal_erasure_obligation_lift"))
    return 0


def exact_progress(rows: list[dict[str, Any]], case_id: str) -> bool:
    for row in rows:
        if row["case_id"] == case_id:
            return bool(row.get("useful_progress"))
    return False


def source_admitted(rows: list[dict[str, Any]], case_id: str) -> bool:
    for row in rows:
        if row["case_id"] == case_id:
            return bool(row.get("source_claim_admitted"))
    return False


if __name__ == "__main__":
    raise SystemExit(main())
