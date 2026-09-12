#!/usr/bin/env python3
"""Independent AF-022 manuscript/claim/bibliography checks."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

FORBIDDEN_PLACEHOLDERS = ("[TBD]", "[TODO]", "[To complete", "\\answerTODO", "\\justificationTODO")
INVENTED_PATTERNS = (
    r"held-out (?:source-)?fidelity of\s+\d",
    r"kappa\s*=\s*\d",
    r"inter-annotator agreement of",
    r"T4 (?:was |is )?(?:successfully )?activated",
    r"(?<!not )(?<!not a )applied learned(?:-feature)? guidance",
    r"Arm E (?:improves|outperforms|was promoted)",
    r"CUDA speedup of",
    r"native useful-proof coverage on 1913.{0,40}(?:success|achieved)",
    r"(?<!not )universal (?:compiler )?soundness",
    r"ProofNet accuracy",
    r"miniF2F (?:score|accuracy|pass)",
    r"LeanDojo (?:score|accuracy|pass)",
    r"we trained a new checkpoint",
    r"parameters are optimized",
    r"stable learned guidance reaches enabled consumers",
)
REQUIRED_ABSTRACT = (
    "automated structural",
    "independent human",
    "not original-source semantic gold",
    "1913",
    "unrun",
    "unmeasured",
    "unavailable",
    "sample-memory diagnostic",
    "finite",
)
REQUIRED_CONCLUSION = (
    "does not establish",
    "independent source fidelity",
    "unseen material",
)
AE_MARKERS = (
    "Pipeline comparisons A--E",
    "A--E pipeline comparison is not a T0--T5 result",
    "source-to-proof",
)
T_MARKERS = (
    "Learning comparisons T0--T5",
    "T0--T5 learning comparison is not an A--E result",
    "sample memory",
)


def find_repo_root(start: Path) -> Path:
    marker = Path("papers/completion/autoformalization/config/environment_manifest.json")
    for path in (start, *start.parents):
        if (path / marker).is_file():
            return path
    raise SystemExit("cannot locate repository root from check_outputs.py")


HERE = Path(__file__).resolve().parent
REPO_ROOT = find_repo_root(HERE)
PAPER = REPO_ROOT / "papers/completion/autoformalization"
MS = PAPER / "manuscript"
EV = PAPER / "evidence"
RESULTS = PAPER / "results"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_abstract(tex: str) -> str:
    match = re.search(r"\\begin\{abstract\}(.*?)\\end\{abstract\}", tex, re.S)
    return match.group(1) if match else ""


def extract_conclusion(tex: str) -> str:
    match = re.search(
        r"\\section\{Limitations and conclusion\}(.*?)\\begin\{ack\}",
        tex,
        re.S,
    )
    return match.group(1) if match else ""


def main() -> int:
    errors: list[str] = []
    paths = {
        "main": MS / "main.tex",
        "bib": MS / "references.bib",
        "audit": EV / "final_claim_audit.json",
        "bib_audit": EV / "bibliography_audit.md",
        "scope": MS / "empirical_scope.tex",
        "summary": RESULTS / "summary.json",
        "hyp": RESULTS / "hypothesis_report.md",
        "pages": MS / "pages" / "page-01.tex",
    }
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"missing {name}: {path}")
    if errors:
        print("AF-022 check failed:\n- " + "\n- ".join(errors))
        return 1

    tex = paths["main"].read_text(encoding="utf-8")
    bib = paths["bib"].read_text(encoding="utf-8")
    bib_audit = paths["bib_audit"].read_text(encoding="utf-8")
    scope = paths["scope"].read_text(encoding="utf-8")
    audit = load_json(paths["audit"])
    summary = load_json(paths["summary"])
    hyp = paths["hyp"].read_text(encoding="utf-8")
    abstract = extract_abstract(tex)
    conclusion = extract_conclusion(tex)

    if "neurips_2026_vericode" not in tex:
        errors.append("manuscript does not load neurips_2026_vericode")
    if re.search(r"\\usepackage\[([^\]]*final|[^\]]*preprint|[^\]]*nonanonymous|[^\]]*sglblind)", tex):
        errors.append("manuscript loads a non-anonymous or non-research style option")
    if "Reconstruction review copy; not ready for submission" in tex:
        errors.append("claim-bearing manuscript still presents the recovery copy as the paper")
    if "\\input{pages/page-01.tex}" in tex:
        errors.append("claim-bearing manuscript still inputs the historical page recovery as the body")

    for token in FORBIDDEN_PLACEHOLDERS:
        if token in tex:
            errors.append(f"manuscript still contains placeholder {token}")

    for pattern in INVENTED_PATTERNS:
        if re.search(pattern, tex, re.I):
            errors.append(f"invented-result pattern matched: {pattern}")

    abs_l = abstract.lower()
    for needle in REQUIRED_ABSTRACT:
        if needle.lower() not in abs_l:
            errors.append(f"abstract missing required scope phrase: {needle}")
    conc_l = conclusion.lower()
    for needle in REQUIRED_CONCLUSION:
        if needle.lower() not in conc_l:
            errors.append(f"conclusion missing required limiter: {needle}")

    if "\\input{empirical_scope.tex}" not in tex:
        errors.append("manuscript does not input empirical_scope.tex")
    for phrase in (
        "Independent human source-facet fidelity and agreement were not collected",
        "Checker and teacher success are not original-source semantic gold",
    ):
        if phrase not in tex and phrase not in scope:
            errors.append(f"empirical-scope wording missing: {phrase}")

    ae_ok = any(m in tex for m in AE_MARKERS) and "tab:arms-ae" in tex and "tab:pipeline-results" in tex
    t_ok = any(m in tex for m in T_MARKERS) and "tab:arms-t" in tex and "tab:training-results" in tex
    if not ae_ok:
        errors.append("A--E pipeline comparison is not distinguished in the narrative")
    if not t_ok:
        errors.append("T0--T5 learning comparison is not distinguished in the narrative")
    if "not merged" not in tex and "not the T0--T5" not in tex:
        errors.append("manuscript does not say the two matrices are distinct")

    for eq in ("eq:cycle", "eq:packed", "eq:prem", "eq:goal", "eq:obl", "eq:q1", "eq:q2"):
        if eq not in tex:
            errors.append(f"missing equation label {eq}")
    if "conditional paper proposition" not in tex.lower() and "conditional paper-level" not in tex.lower():
        if "conditional paper proposition" not in tex:
            errors.append("conditional transfer proposition is not labeled")
    if "finite constructed" not in tex.lower() and "finite illustration" not in tex.lower():
        if "illustrate composition" not in tex:
            errors.append("finite illustrations are not labeled")
    if "not a trained free-text decoder" not in tex:
        errors.append("vector-versus-text distinction missing")
    if "not proof of a correct interpretation" not in tex:
        errors.append("source-grounding-versus-truth distinction missing")
    if "Planning performs no proof" not in tex:
        errors.append("planning-versus-proof distinction missing")
    if "implemented routes" not in tex or "unavailable" not in tex:
        errors.append("implemented-versus-executed tense distinction missing")
    if "nonvacuous" not in tex and "vacuous" not in tex:
        errors.append("proof-transfer nonvacuity is not labeled")

    if "\\input{../results/table6_pipeline.tex}" not in tex:
        errors.append("Table 6 is not included from AF-021 results")
    if "\\input{../results/table11_training.tex}" not in tex:
        errors.append("Table 11 is not included from AF-021 results")
    if "\\input{../results/table13_assistance.tex}" not in tex:
        errors.append("Table 13 is not included from AF-021 results")

    pages = (MS / "pages").is_dir() and (MS / "pages" / "page-01.tex").is_file()
    if not pages:
        errors.append("historical recovery pages/ copy is missing")
    if "historical" not in tex.lower() or "pages/" not in tex:
        errors.append("manuscript does not preserve the recovery copy as historical evidence")

    if audit.get("schema") != "autoformalization-final-claim-audit/v1":
        errors.append("claim audit schema mismatch")
    claims = audit.get("claims") or []
    if len(claims) < 15:
        errors.append("claim audit is too thin")
    for claim in claims:
        if not str(claim.get("text") or "").strip():
            errors.append(f"{claim.get('id')} missing text")
        if not claim.get("source"):
            errors.append(f"{claim.get('id')} missing source")
        if not claim.get("kind"):
            errors.append(f"{claim.get('id')} missing kind")
        if claim.get("id") in {"C1", "C2", "C3", "C4", "C5", "C6"} and claim.get("status") == "supported":
            errors.append(f"{claim.get('id')} marked supported without independent/final-test evidence")
        if claim.get("kind") == "finite_illustration" and "finite" not in str(claim.get("text") or "").lower() and claim.get("id") not in {"AF015-Q1", "AF006-TWELVE", "ABS-FINITE"}:
            errors.append(f"{claim.get('id')} finite illustration unlabeled")
        if claim.get("kind") == "conditional_proposition" and "conditional" not in str(claim.get("text") or "").lower():
            errors.append("conditional proposition claim unlabeled")
    kinds = {c.get("kind") for c in claims}
    if "finite_illustration" not in kinds:
        errors.append("claim audit has no finite illustration")
    if "conditional_proposition" not in kinds:
        errors.append("claim audit has no conditional proposition")
    sep = audit.get("narrative_separation") or {}
    if not (sep.get("pipeline_A_to_E") and sep.get("learning_T0_to_T5")):
        errors.append("claim audit does not separate A--E from T0--T5")
    if audit.get("scope_policy", {}).get("optional_author_feedback_supplied") is not False:
        errors.append("audit invents author feedback")
    if audit.get("historical_recovery_copy", {}).get("unmeasured_promises_presented_as_results") is not False:
        errors.append("audit allows recovery promises as results")
    hyps = audit.get("hypotheses") or {}
    for hid in ("C1", "C2", "C3", "C4", "C5", "C6"):
        if hyps.get(hid) == "supported":
            errors.append(f"audit marks {hid} supported")
    if hyps.get("C7") not in {"inconclusive", "unrun", "unsupported"}:
        errors.append("C7 must remain inconclusive/unrun/unsupported")
    if hyps.get("H-T2-shared-learner") == "supported":
        errors.append("T2 generalization marked supported")
    if hyps.get("H-T1-claim_admissible_for_paper_primary") is not False:
        errors.append("T1 diagnostic was admitted as a primary paper claim")

    if summary.get("missingness", {}).get("arm_E_activated") is not False:
        errors.append("summary Arm E activated")
    if summary.get("false_transfer", {}).get("generalized_to_universal_soundness") is not False:
        errors.append("summary generalized false-transfer to soundness")
    if "Zero observed false transfers is not generalized to universal soundness" not in hyp:
        errors.append("hypothesis report lost the false-transfer guardrail")

    original_keys = (
        "wu2022autoformalization",
        "azerbayev2023proofnet",
        "benzmuller2020logikey",
        "goguen1992institutions",
        "kifer1995flogic",
        "kowalski1986events",
        "pnueli1998translation",
        "yi2018nsvqa",
        "jiang2024multilanguage",
        "jiang2022thor",
    )
    for key in original_keys:
        if key not in bib or f"{{{key}" not in tex and key not in tex:
            if f"{key}" not in bib:
                errors.append(f"missing original bibliography key {key}")
            elif key not in tex:
                errors.append(f"original key {key} is not cited in the manuscript")
    added = (
        "yang2023leandojo",
        "jiang2023dsp",
        "leroy2009compcert",
        "klein2009sel4",
        "leino2010dafny",
        "blanchette2013sledgehammer",
        "first2023baldur",
    )
    for key in added:
        if key not in bib or key not in tex:
            errors.append(f"missing related-work comparison {key}")
        if "not executed as a paper benchmark" not in bib.split(key, 1)[-1][:800] and "not re-benchmarked" not in bib.split(key, 1)[-1][:800]:
            errors.append(f"{key} is not labeled as comparison-only in the bib")
    if "Verified" not in bib_audit or "Original PDF references" not in bib_audit:
        errors.append("bibliography audit does not verify original references")
    if "were not executed" not in bib_audit and "was not executed" not in bib_audit:
        errors.append("bibliography audit does not state added comparisons were not run")
    if "No unrelated" not in bib_audit and "not added as padding" not in bib_audit:
        errors.append("bibliography audit does not address padding/unrelated benchmarks")

    report = {
        "ok": not errors,
        "errors": errors,
        "abstract_chars": len(abstract),
        "conclusion_chars": len(conclusion),
        "claim_count": len(claims),
        "hypothesis_status": hyps,
        "ae_separated": ae_ok,
        "t_separated": t_ok,
        "historical_recovery_present": pages,
        "final_test_denominator": summary.get("denominators", {}).get("table6_final_test"),
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
