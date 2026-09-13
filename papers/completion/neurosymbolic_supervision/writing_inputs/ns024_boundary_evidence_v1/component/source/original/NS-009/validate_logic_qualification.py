#!/usr/bin/env python3
"""Validate NS-009 published logic qualification artifacts.

Stdlib plus the sealed translation/converter/admission/CEGAR sources.
Re-checks structural invariants and performs a live smoke of modal-erasure
rejection, exact translation progress, solver readiness, and IPA CEGAR.
Does not claim a live A–D experiment or a kernel proof.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import runpy
import shutil
import sys


ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
QUAL = PAPER / "qualification"
SNAP = PAPER / "receipts/snapshots/NS-009"
SNAP_QUAL = SNAP / "qualification"
RUNNER = SNAP / "run_logic_qualification.py"

CRITERIA = (
    "Valid supported translations can progress; unjustified lifting from modal-erasing or otherwise lossy projections cannot admit the source claim.",
    "Actual caller receipts bind exact formulas/source/theory/solver/environment and reject stale or unvalidated results.",
    "Vacuity, unknown, unsupported, and budget-exhausted cases remain distinct from meaningful proof.",
    "Any claimed CEGAR/interpolant/composition behavior is supported by located code and actual evidence; no unavailable mechanism is silently simulated.",
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

VALID_PROGRESS = (
    "exact_atom_supported_progress",
    "declared_conservative_modal_progress",
    "bounded_abstraction_progress",
    "tdfol_axiom_proved_non_kernel",
    "cegar_ipa_spurious_refine",
)

NO_SOURCE_LIFT = (
    "modal_erasure_obligation_lift",
    "temporal_erasure_always_lift",
    "until_conjunction_lossy_projection",
    "heuristic_cannot_prove",
    "vacuity_unsat_guarantee",
    "unvalidated_solver_result_rejected",
    "invalid_interpolant_not_admitted",
    "stale_formula_root",
    "stale_solver_fingerprint",
)

DISTINCT_STATUSES = {
    "unknown_not_proved": "unknown",
    "timeout_budget_exhausted": "timeout",
    "unsupported_clause_uncovered": "unsupported",
    "vacuity_unsat_guarantee": "vacuous",
    "sat_smt_unavailable": "unavailable",
    "unsat_smt_unavailable": "unavailable",
}

UNAVAILABLE_NOT_SIMULATED = (
    "cegar_qf_lia_adapter_unlocated",
    "interpolant_mechanism_unavailable",
    "composition_edge_unlocated",
    "cyclic_composition_unlocated",
    "incremental_smt_wrapper_unlocated",
    "sat_smt_unavailable",
    "unsat_smt_unavailable",
)


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def fail(message: str) -> None:
    raise SystemExit(f"NS-009 validation failed: {message}")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def live_smoke() -> None:
    acc = ROOT / "external/ipfs_accelerate"
    ds = ROOT / "external/ipfs_datasets"
    for path in (str(acc), str(ds)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from ipfs_accelerate_py.agent_supervisor.proof.formal_logic_vocabulary import (
        DCEC,
        ReviewedPredicate,
        TermSort,
        atom,
        constant,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.logic_translation_validation import (
        LogicForm,
        SemanticInventory,
        TranslationArtifact,
        TranslationClass,
        TranslationContract,
        inventory_from_reviewed_formula,
        validate_translation,
    )
    from ipfs_accelerate_py.agent_supervisor.proof.solver_readiness import probe_solver_readiness
    from ipfs_accelerate_py.agent_supervisor.proof.logic_platform_admission import (
        AdmissionContext,
        admit_receipt,
    )
    from ipfs_accelerate_py.agent_supervisor.analysis.formal_assurance.ipa import (
        FindingDisposition,
        IpaFinding,
        ProductDomainState,
        SourceSpan,
        SourceToSinkTrace,
        SpuriousPathRefinement,
        TraceStep,
        refine_spurious_paths,
    )
    from ipfs_datasets_py.logic.TDFOL.tdfol_core import DeonticFormula, DeonticOperator, Predicate
    from ipfs_datasets_py.logic.TDFOL.tdfol_converter import tdfol_to_fol

    src = atom(ReviewedPredicate.TASK_COMPLETED, constant(TermSort.TASK, "t1"))
    inv = inventory_from_reviewed_formula(src)
    contract = TranslationContract(
        contract_id="smoke-exact@1",
        source_identity=src.formula_id,
        source_form=LogicForm.FOL,
        target_form=LogicForm.SMT_LIB,
        translator_id="ns-009-smoke",
        translator_version="1",
        translator_identity="sha256:ns-009-smoke",
        semantic_profile_id="supervisor-fol",
        semantic_profile_version="1",
        translation_class=TranslationClass.EXACT,
        fixture_set_id="ns-009-logic-v1",
    )
    exact = validate_translation(
        contract,
        TranslationArtifact(
            contract_identity=contract.content_id,
            source_identity=contract.source_identity,
            target_text="(assert (task_completed t1))",
            source_inventory=inv,
            target_inventory=inv,
            fixture_set_id=contract.fixture_set_id,
        ),
    )
    if not exact.conformant or not exact.promotion_allowed:
        fail("live smoke: exact translation did not progress")

    obligation = DCEC.obligation("worker", src, 7)
    inv_ob = inventory_from_reviewed_formula(obligation)
    dropped = SemanticInventory(
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
    lossy_contract = TranslationContract(
        contract_id="smoke-lossy@1",
        source_identity=obligation.formula_id,
        source_form=LogicForm.DCEC,
        target_form=LogicForm.FOL,
        translator_id="tdfol-to-fol",
        translator_version="1",
        translator_identity="sha256:tdfol-to-fol",
        semantic_profile_id="supervisor-dcec",
        semantic_profile_version="1",
        translation_class=TranslationClass.EXACT,
        fixture_set_id="ns-009-logic-v1",
    )
    lossy = validate_translation(
        lossy_contract,
        TranslationArtifact(
            contract_identity=lossy_contract.content_id,
            source_identity=lossy_contract.source_identity,
            target_text="task_completed(t1)",
            source_inventory=inv_ob,
            target_inventory=dropped,
            fixture_set_id=lossy_contract.fixture_set_id,
        ),
    )
    if lossy.conformant or not lossy.quarantine_required:
        fail("live smoke: modal erasure was not quarantined")
    if "dropped_modal_operator" not in [item.code.value for item in lossy.issues]:
        fail("live smoke: dropped_modal_operator missing")

    p = Predicate("Done", ())
    o_p = DeonticFormula(DeonticOperator.OBLIGATION, p)
    if tdfol_to_fol(o_p).to_string() != tdfol_to_fol(p).to_string():
        fail("live smoke: O(p) and p projections diverged")

    z3 = probe_solver_readiness().by_family
    from ipfs_accelerate_py.agent_supervisor.proof.solver_readiness import SolverBackendFamily

    if z3[SolverBackendFamily.Z3].supported:
        fail("live smoke: Z3 must remain unsupported in the sealed profile")

    ctx = AdmissionContext(
        task_id="NS-009",
        repository_tree_id="tree-ns009",
        policy_id="ns-009-logic-qualification-v1",
        operation="complete_task",
        required_authority="kernel_verified",
        environment_id="env-ns009-sealed",
        source_id=obligation.formula_id,
        require_reconstruction=True,
        require_kernel=True,
    )
    admitted = admit_receipt(
        {
            "obligation_id": "smoke-lift",
            "semantic_verdict": "proved",
            "evidence_kind": "solver_result",
            "authority_ceiling": "solver_checked",
            "freshness": "current",
            "repository_tree_id": "tree-ns009",
            "policy_id": "ns-009-logic-qualification-v1",
            "environment_id": "env-ns009-sealed",
            "source_id": obligation.formula_id,
            "translation": {"valid": False, "translation_class": "exact"},
            "simulated": False,
            "content_id": "sha256:" + "b" * 64,
        },
        ctx,
    )
    if admitted.admitted:
        fail("live smoke: unjustified lifting was admitted")

    span = SourceSpan(path="x.py", start_line=1, end_line=1, symbol="f")
    trace = SourceToSinkTrace(
        steps=(TraceStep(kind="src", label="a"), TraceStep(kind="sink", label="b"))
    )
    finding = IpaFinding(
        finding_id="f1",
        rule_id="ipa.rule.import_effect",
        disposition=FindingDisposition.SPURIOUS_CANDIDATE,
        source_span=span,
        sink_span=span,
        trace=trace,
        domain_state=ProductDomainState(),
        imprecise=True,
    )
    refined, away = refine_spurious_paths(
        (finding,),
        (SpuriousPathRefinement(refinement_id="r1", finding_id="f1", reason="spurious"),),
    )
    if away != ("f1",) or refined[0].disposition is not FindingDisposition.REFINED_AWAY:
        fail("live smoke: IPA CEGAR did not refine the spurious path")

    if shutil.which("z3") is not None:
        fail("live smoke: z3 binary unexpectedly present on sealed PATH")


def main() -> None:
    cases_path = QUAL / "logic_cases.json"
    receipts_path = QUAL / "logic_receipts.jsonl"
    profiles_path = QUAL / "logic_profiles.json"
    report_path = QUAL / "logic_report.md"
    for path in (cases_path, receipts_path, profiles_path, report_path, RUNNER):
        if not path.is_file():
            fail(f"missing {path}")

    cases = load_json(cases_path)
    rows = load_jsonl(receipts_path)
    profiles = load_json(profiles_path)
    report = report_path.read_text(encoding="utf-8")

    if cases.get("schema") != "neurosymbolic-supervision/logic-qualification-cases@1":
        fail("unexpected cases schema")
    if cases.get("task_id") != "NS-009":
        fail("cases task_id mismatch")
    if profiles.get("schema") != "neurosymbolic-supervision/logic-qualification-profiles@1":
        fail("unexpected profiles schema")
    if not rows:
        fail("empty receipts")
    if any(row.get("schema") != "neurosymbolic-supervision/logic-qualification-receipt@1" for row in rows):
        fail("receipt schema mismatch")

    rules = cases.get("rules") or {}
    for key in (
        "lossy_projection_cannot_admit_source_claim",
        "solver_result_is_not_kernel_proof",
        "vacuity_unknown_unsupported_timeout_are_distinct",
        "unavailable_mechanisms_are_not_simulated",
        "assertion_replay_is_not_retained_solver_state",
    ):
        if rules.get(key) is not True:
            fail(f"cases omitted rule {key}")

    by_id = {row["case_id"]: row for row in rows}
    missing = [name for name in REQUIRED_CASES if name not in by_id]
    if missing:
        fail(f"missing required cases: {missing}")
    for row in rows:
        if row.get("status") != "pass":
            fail(f"case failed: {row['case_id']}")
        if row.get("simulated_unavailable_mechanism") is True:
            fail(f"unavailable mechanism simulated: {row['case_id']}")
        if row.get("kernel_proof") is True:
            fail(f"kernel proof claimed: {row['case_id']}")

    for name in VALID_PROGRESS:
        row = by_id[name]
        if row.get("useful_progress") is not True:
            fail(f"valid case did not progress: {name}")
        if row.get("source_claim_admitted") is True:
            fail(f"valid translation overclaimed source admission: {name}")

    for name in NO_SOURCE_LIFT:
        row = by_id[name]
        if row.get("source_claim_admitted") is not False:
            fail(f"lossy/invalid case admitted source claim: {name}")
        if row.get("useful_progress") is True:
            fail(f"invalid case reported useful progress: {name}")

    modal = by_id["modal_erasure_obligation_lift"]
    if not (modal.get("countermodel") or {}).get("identical_projection"):
        fail("modal countermodel did not share a projection")
    if "dropped_modal_operator" not in ((modal.get("translation") or {}).get("issues") or []):
        fail("modal erasure lacked dropped_modal_operator")

    until = by_id["until_conjunction_lossy_projection"]
    if not (until.get("countermodel") or {}).get("identical_projection"):
        fail("until/conjunction projections were not identical")
    if not (until.get("countermodel") or {}).get("distinct_sources"):
        fail("until and conjunction sources were not distinct")

    exact = by_id["exact_atom_supported_progress"]
    bindings = exact.get("bindings") or {}
    for key in ("formula_root", "source_form", "target_form", "theory", "solver_id", "environment_id"):
        if not bindings.get(key):
            fail(f"exact progress missing binding {key}")
    if (exact.get("kernel_admission") or {}).get("admitted") is True:
        fail("exact translation was admitted as kernel proof")

    stale = by_id["stale_formula_root"]
    if (stale.get("translation") or {}).get("conformant") is True:
        fail("stale formula root was conformant")
    fp = by_id["stale_solver_fingerprint"]
    if fp.get("live_fingerprint") == fp.get("submitted_fingerprint"):
        fail("stale fingerprint was not distinct")
    dup = by_id["duplicate_named_assertions"]
    if (dup.get("named_assertions") or {}).get("accepted") is not False:
        fail("duplicate assertions were accepted")
    if dup.get("retained_solver_state") is True:
        fail("duplicate-assertion case claimed retained solver state")

    classes = {name: by_id[name].get("solver_result_class") for name in DISTINCT_STATUSES}
    for name, expected in DISTINCT_STATUSES.items():
        if classes[name] != expected:
            fail(f"{name} solver_result_class was {classes[name]!r}, expected {expected!r}")
    if len({classes["unknown_not_proved"], classes["timeout_budget_exhausted"], classes["unsupported_clause_uncovered"], classes["vacuity_unsat_guarantee"]}) != 4:
        fail("vacuity/unknown/unsupported/timeout were not distinct")

    z3 = by_id["solver_readiness_z3_unavailable"]
    if (z3.get("readiness") or {}).get("supported") is True:
        fail("Z3 was marked supported")
    if (z3.get("readiness") or {}).get("proof_success") is True:
        fail("solver readiness claimed proof_success")

    cegar = by_id["cegar_ipa_spurious_refine"]
    if cegar.get("symbol") != "refine_spurious_paths":
        fail("CEGAR case did not bind refine_spurious_paths")
    if cegar.get("refined_away") != ["f-spurious"]:
        fail("CEGAR did not refine the spurious finding")
    if cegar.get("seed_disposition") != "corpus_bound":
        fail("CEGAR refined away a corpus seed")

    for name in UNAVAILABLE_NOT_SIMULATED:
        row = by_id[name]
        if row.get("simulated_unavailable_mechanism") is not False:
            fail(f"{name} did not deny simulation")
        if row.get("useful_progress") is True:
            fail(f"unavailable case claimed progress: {name}")
        if row.get("located") is True:
            fail(f"unavailable mechanism marked located: {name}")

    if (profiles.get("unavailable_or_specification_only") or {}).get("interpolant_checker", {}).get("found_in_python_source") is True:
        fail("profiles claimed an interpolant checker")
    if (profiles.get("unavailable_or_specification_only") or {}).get("CompositionEdge", {}).get("found_in_python_source") is True:
        fail("profiles claimed CompositionEdge")
    if (profiles.get("unavailable_or_specification_only") or {}).get("incremental_smt_wrapper", {}).get("retained_clause_speedup") is not False:
        fail("profiles claimed retained-clause speedup")

    for needle in (
        "Valid supported translations can progress",
        "Unjustified lifting is rejected",
        "Vacuity, unknown, unsupported, and budget exhaustion are distinct",
        "CEGAR, interpolants, and composition",
        "No interpolant",
        "not simulated",
    ):
        if needle not in report:
            fail(f"report omitted {needle!r}")

    for name in ("logic_cases.json", "logic_receipts.jsonl", "logic_profiles.json", "logic_report.md"):
        current = QUAL / name
        snapshot = SNAP_QUAL / name
        if digest(current) != digest(snapshot):
            fail(f"current output differs from snapshot: {name}")

    if "validate_translation" not in RUNNER.read_text(encoding="utf-8"):
        fail("runner does not call validate_translation")
    compile(RUNNER.read_bytes(), str(RUNNER), "exec")

    live_smoke()
    # Re-importing the runner is intentionally avoided here; live_smoke covers
    # the same APIs. Structural identity of published files is checked above.
    print("NS-009 logic qualification validation: OK")
    print(f"rows={len(rows)} required={len(REQUIRED_CASES)}")
    print("exact_progress=", exact.get("useful_progress"), "modal_lift=", modal.get("source_claim_admitted"))


if __name__ == "__main__":
    main()
