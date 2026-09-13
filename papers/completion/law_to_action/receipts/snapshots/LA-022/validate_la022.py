#!/usr/bin/python3.12
"""Structural evidence checks for LA-022 manuscript completion.

Sealed-PATH validator: placeholder scan, admitted-number binding, claim-matrix
links, withdrawn human-fidelity language, and citation resolution. Compilation
uses a user-local TinyTeX wrapper that is not on the sealed PATH; this script
checks sources and the pdftotext extract when present. It is not independent
scientific peer review.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers" / "completion" / "law_to_action").is_dir():
    ROOT = ROOT.parent
PAPER = ROOT / "papers/completion/law_to_action"
MAIN = PAPER / "manuscript/main.tex"
RESULTS = PAPER / "manuscript/results.tex"
LIMITS = PAPER / "manuscript/limitations.tex"
MATRIX = PAPER / "claim_evidence_matrix.json"
BIB = PAPER / "manuscript/related_work.bib"
SUMMARY = PAPER / "results/fixed_actions_admitted/summary.json"
GUIDANCE = PAPER / "results/fixed_actions_admitted/claim_guidance.md"
COST = PAPER / "results/fixed_actions_admitted/cost_report.md"
SOURCE_IR = PAPER / "results/source_ir/metrics.json"
COMPILED_TXT = PAPER / "receipts/snapshots/LA-022/compiled/main.txt"
COMPILED_LOG = PAPER / "receipts/snapshots/LA-022/compiled/main.log"
PDF_DIGEST = PAPER / "receipts/snapshots/LA-022/compiled/pdf_digest.json"


def fail(message: str) -> None:
    raise SystemExit("LA-022 validation failed: " + message)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing file {path}")
    return path.read_text(encoding="utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bib_keys(text: str) -> list[str]:
    keys = re.findall(r"(?m)^@\w+\{([^,\s]+)\s*,", text)
    if not keys:
        fail("bibliography has no entries")
    return keys


def cite_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    for command in re.finditer(r"\\cite(?:p|t|alt|alp|year|yearpar)?(?:\[[^\]]*\])?\{([^}]*)\}", tex):
        for key in command.group(1).split(","):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def folded(text: str) -> str:
    return " ".join(text.lower().split())


def require_phrases(text: str, phrases: list[str], label: str) -> None:
    blob = folded(text)
    missing = [p for p in phrases if p.lower() not in blob]
    if missing:
        fail(f"{label} missing required phrases: {missing}")


def forbid_patterns(text: str, patterns: list[str], label: str, flags: int = 0) -> None:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            fail(f"{label} still contains placeholder or unsupported claim {pattern!r} near {match.group(0)!r}")


def main() -> None:
    main_tex = read(MAIN)
    results = read(RESULTS)
    limits = read(LIMITS)
    combined = main_tex + "\n" + results + "\n" + limits
    matrix = json.loads(read(MATRIX))
    summary = json.loads(read(SUMMARY))
    source_ir = json.loads(read(SOURCE_IR))
    guidance = read(GUIDANCE)
    cost = read(COST)
    bib = read(BIB)

    if r"\input{results}" not in main_tex or r"\input{limitations}" not in main_tex:
        fail("main.tex must \\input results.tex and limitations.tex")
    if r"\bibliography{related_work}" not in main_tex:
        fail("main.tex must load related_work.bib")
    if re.search(r"\\bibliography\{[^}]*references", main_tex):
        fail("main.tex must not load references.bib together with related_work.bib")
    if r"\nocite{" in combined:
        fail("manuscript must not \\nocite unexecuted systems")

    forbid_patterns(
        combined,
        [
            r"Not run",
            r"run pending",
            r"frozen run pending",
            r"evaluation completion template",
            r"evaluation-template",
            r"Existing assertions inspected",
            r"Existing suite inspected",
            r"Existing implementation and test design inspected",
        ],
        "manuscript",
    )

    require_phrases(
        combined,
        [
            "0/90",
            "90/90",
            "33/90",
            "0/54",
            "54/54",
            "18/54",
            "60/60",
            "50/60",
            "shared-producer conformance",
            "protocol-unadmitted diagnostic",
            "separate diagnostic",
            "non-independent",
            "withdrawn",
            "unmeasured",
            "no outside review",
            "LA-029",
            "ENFORCE",
            "none is a scored baseline here",
        ],
        "manuscript",
    )
    require_phrases(
        combined,
        [
            "Expert legal fidelity",
            "human agreement",
            "legal-validity rates were not collected",
            "Optional author review is labeled non-independent",
        ],
        "withdrawn-human-claims",
    )

    positive_fidelity = re.search(
        r"(expert[- ]legal[- ]fidelity|human agreement|legal validity)"
        r"(?!.{0,80}\b(?:not |never |unmeasured|withdrawn|absent)\b).{0,40}"
        r"\b(?:measured|scored|collected as gold)\b",
        combined,
        re.I,
    )
    if positive_fidelity:
        fail(f"unsupported human-fidelity claim remains: {positive_fidelity.group(0)}")

    if summary.get("rows") != 900 or summary.get("all900_resource_qualified") is not True:
        fail("admitted summary is not the 900-cell resource-qualified matrix")
    if summary.get("human_agreement") is not None or summary.get("human_fidelity") is not None:
        fail("admitted summary must leave human_agreement and human_fidelity null")
    if summary.get("model_calls") != 0:
        fail("admitted summary model_calls must be 0")
    final = summary["split_analysis"]["final"]["arms"]
    if final["A4"]["forbidden_effect_rate"] != {"denominator": 54, "numerator": 0, "value": 0.0}:
        fail("final A4 forbidden-effect rate drifted")
    if final["A4"]["allowed_task_success_rate"]["numerator"] != 54:
        fail("final A4 allowed useful work drifted")
    if final["A3"]["forbidden_effect_rate"]["numerator"] != 18:
        fail("final A3 forbidden-effect rate drifted")
    if "LA022 must use this summary" not in guidance and "LA-022 must use this summary" not in guidance:
        fail("claim_guidance.md does not instruct LA-022 to consume the admitted summary")
    if "1608.817478" not in cost and "1608.817478" not in results:
        fail("measured group CPU seconds missing from cost report/results")
    if "1608.817478" not in results:
        fail("results.tex must report the admitted group CPU seconds")

    span = source_ir["metrics"]["source_span_linkage_coverage"]
    schema = source_ir["metrics"]["parse_schema_validity"]
    if span["numerator"] != 60 or span["denominator"] != 60:
        fail("source-span linkage drifted")
    if schema["numerator"] != 50 or schema["denominator"] != 60:
        fail("schema validity drifted")
    skill = source_ir["metrics"]["compiler_checker_consistency"]["skill_normalizer_shared_schema_conformance"]
    if skill["numerator"] != 18 or skill.get("shared_producer_dependence") is not True:
        fail("18/18 skill comparison is not labeled shared-producer")

    if matrix.get("schema") != "law-to-action-claim-evidence-matrix/v2":
        fail("claim matrix schema must be v2")
    if matrix.get("independent_human_gold") is not False:
        fail("claim matrix must record independent_human_gold false")
    if matrix.get("optional_author_review", {}).get("independent") is not False:
        fail("optional author review must be labeled non-independent")
    claims = matrix.get("manuscript_claims")
    if not isinstance(claims, list) or len(claims) < 20:
        fail("claim matrix must link manuscript claims")
    required_ids = {f"M{i}" for i in range(1, 23)}
    have = {c.get("id") for c in claims}
    if not required_ids <= have:
        fail(f"claim matrix missing ids: {sorted(required_ids - have)}")
    empirical = [c for c in claims if c.get("status") == "empirical_admitted"]
    if len(empirical) < 6:
        fail("claim matrix has too few empirical admitted claims")
    for claim in claims:
        if not claim.get("manuscript_locations") or not isinstance(claim.get("evidence_paths"), list):
            fail(f"claim {claim.get('id')} missing locations or evidence paths")
        if claim.get("status") == "empirical_admitted" and not claim.get("experiments"):
            fail(f"empirical claim {claim.get('id')} has no experiment")
        if claim.get("status") == "withdrawn_unmeasured" and claim.get("numeric_score_assigned") is not False:
            fail(f"withdrawn claim {claim.get('id')} must not assign a numeric score")

    cited = cite_keys(combined)
    keys = set(bib_keys(bib))
    unresolved = sorted(cited - keys)
    if unresolved:
        fail(f"unresolved citation keys: {unresolved}")
    required_cites = {
        "saltzer1975protection",
        "schneider2000enforceable",
        "necula1997pcc",
        "appel1999pca",
        "catala",
        "cutler2024cedar",
        "wang2025agentspec",
        "shi2025progent",
        "debenedetti2025camel",
        "debenedetti2024agentdojo",
        "vericode2026cfp",
        "mcp",
        "mcp-auth",
        "ucan",
        "cvefixes",
    }
    missing_cites = sorted(required_cites - cited)
    if missing_cites:
        fail(f"required primary sources not cited: {missing_cites}")

    if COMPILED_TXT.is_file():
        extract = re.sub(r"-\n\s*(?:\d+\s+)?", "", read(COMPILED_TXT))
        require_phrases(
            extract,
            [
                "0/90",
                "90/90",
                "33/90",
                "shared-producer conformance",
                "protocol-unadmitted diagnostic",
                "non-independent",
                "Withdrawn",
            ],
            "compiled extract",
        )
        forbid_patterns(extract, [r"Not run", r"run pending"], "compiled extract")
        if "References" not in extract:
            fail("compiled extract missing References")
    if COMPILED_LOG.is_file():
        log = read(COMPILED_LOG)
        if "Output written on main.pdf" not in log:
            fail("compiled log missing Output written")
        if re.search(r"Citation `[^']+' on page .* undefined", log) and "There were undefined citations" in log:
            # Final latexmk pass should have resolved citations; tolerate only if
            # the last Output written is not followed by remaining undefineds.
            last = log.rfind("Output written on main.pdf")
            tail = log[last:]
            if "undefined citations" in tail.lower():
                fail("final compilation still has undefined citations")
    if PDF_DIGEST.is_file():
        digest = json.loads(read(PDF_DIGEST))
        pages = digest.get("main_text_pages")
        if not isinstance(pages, int) or pages < 4 or pages > 9:
            fail(f"main-text page count out of workshop 4-9 range: {pages}")

    print(
        json.dumps(
            {
                "status": "ok",
                "main_sha256": sha256(MAIN),
                "results_sha256": sha256(RESULTS),
                "limitations_sha256": sha256(LIMITS),
                "matrix_sha256": sha256(MATRIX),
                "cited_keys": len(cited),
                "manuscript_claims": len(claims),
                "sealed_path": os.environ.get("PATH"),
                "pdftotext": shutil.which("pdftotext"),
                "pdflatex_on_sealed_path": shutil.which("pdflatex"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
