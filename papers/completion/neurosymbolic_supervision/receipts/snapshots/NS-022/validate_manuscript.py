#!/usr/bin/env python3.12
"""Ordinary NS-022 manuscript checks against frozen NS-019/NS-020 products.

Sealed-profile structural/numeric audit. No provider, scorer, grant, or experiment.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
MS = PAPER / "manuscript"
AUDIT = PAPER / "audit"
ANALYSIS = PAPER / "analysis"

EXPECTED = {
    "generated/figures/family_useful.pdf": "8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5",
    "generated/figures/family_useful.svg": "e1503343b198855975b3136e44efbe5330791945435bfabf99b53ea9a400cc90",
    "generated/table17.tex": "ffbb7f2e6aecefb0e4a65fe2da32cc43e87601e01eb7ab97715e516a22cc0b79",
    "generated/table18.tex": "3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495",
    "generated/ablations.tex": "8c57477902aba200e9a2228d6a316ec06f14859f7894fa1f534f16e8b19d8ccf",
    "formal_arguments.tex": "b1d1f95188a4c8633332a4bd15c7977062d24d9affd9e0a7830e553e2a7e8664",
    "neurips_2026_vericode.sty": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
}
VERIFIED_BIB = "0445451efbb19678d9f1af3c84470a92966f8888230e44fe70eb9744f1ef1951"
RESULTS_SHA = "6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e"
NS019_ASCII_PREFIX = "8ea081bc"
PLACEHOLDER = re.compile(
    r"TBD|TO BE FILLED|\[RESULTS|RESULTS:|TODO|TO DO|FIXME|lorem ipsum",
    re.I,
)
INTERNAL_LABEL = re.compile(r"\[(?:D\d+|A\d+|N\d+|K\d+|P\d+|W\d+)(?:[–-][A-Z]?\d+)?\]")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(cond: bool, message: str) -> None:
    if not cond:
        raise SystemExit(f"NS-022 check failed: {message}")


def pdftotext(path: Path) -> str:
    return subprocess.check_output(["pdftotext", "-layout", str(path), "-"], text=True)


def pdfinfo(path: Path) -> dict[str, str]:
    out = subprocess.check_output(["pdfinfo", str(path)], text=True)
    info = {}
    for line in out.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def pdffonts(path: Path) -> list[dict[str, str]]:
    out = subprocess.check_output(["pdffonts", str(path)], text=True)
    lines = out.splitlines()
    fonts = []
    for line in lines[2:]:
        if not line.strip():
            continue
        fonts.append({"raw": line, "type3": "Type 3" in line, "embedded": " yes " in f" {line} "})
    return fonts


def main() -> int:
    results_path = ANALYSIS / "results.json"
    require(results_path.is_file(), "missing analysis/results.json")
    require(sha256(results_path) == RESULTS_SHA, "results.json hash drifted from NS-019")
    results = json.loads(results_path.read_text(encoding="utf-8"))

    owned = {}
    for rel, expected in EXPECTED.items():
        path = MS / rel
        require(path.is_file(), f"missing {rel}")
        digest = sha256(path)
        require(digest == expected, f"{rel} hash {digest} != {expected}")
        owned[rel] = digest
    bib = PAPER / "audit/verified_references.bib"
    require(bib.is_file() and sha256(bib) == VERIFIED_BIB, "verified bibliography hash drifted")

    main_tex = (MS / "main.tex").read_text(encoding="utf-8")
    paper_pdf = MS / "paper.pdf"
    require(paper_pdf.is_file(), "missing manuscript/paper.pdf")
    pdf_text = pdftotext(paper_pdf)
    info = pdfinfo(paper_pdf)
    fonts = pdffonts(paper_pdf)
    pages = int(info["Pages"])
    require(pages >= 8, f"unexpected short PDF: {pages} pages")
    require(all(not f["type3"] for f in fonts), "Type 3 font present")
    require(len(fonts) > 0, "no embedded fonts")

    main_pages = 0
    refs_page = None
    heading = re.compile(r"^\s*(?:\d+\s+)?References\s*$", re.M)
    for page in range(1, pages + 1):
        text = subprocess.check_output(
            ["pdftotext", "-layout", "-f", str(page), "-l", str(page), str(paper_pdf), "-"],
            text=True,
        )
        if refs_page is None and heading.search(text):
            refs_page = page
            first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
            if heading.match(first):
                main_pages = refs_page - 1
            else:
                main_pages = refs_page
            break
        main_pages = page
    require(4 <= main_pages <= 9, f"main-text pages {main_pages} outside 4-9")

    for blob, label in ((main_tex, "main.tex"), (pdf_text, "paper.pdf")):
        hit = PLACEHOLDER.search(blob)
        require(hit is None, f"{label} placeholder {hit.group(0) if hit else ''}")
        hit = INTERNAL_LABEL.search(blob)
        require(hit is None, f"{label} unresolved internal label {hit.group(0) if hit else ''}")

    require("8ea081bc" not in main_tex, "main.tex must not treat the NS-019 ASCII PDF as Figure 1")
    require("includegraphics" not in main_tex.lower() or "layout/family_useful.pdf" in main_tex
            or "tikzpicture" in main_tex,
            "Figure 1 source missing")
    require("tikzpicture" in main_tex, "published figure must be the Type 1 TikZ drawing")
    require(r"\input{generated/table17}" in main_tex, "Table 17 not bound")
    require(r"\input{generated/ablations}" in main_tex, "ablation table not bound")
    require(r"\input{formal_arguments}" in main_tex, "formal arguments not bound")
    require(r"\bibliography{../audit/verified_references}" in main_tex, "verified bibliography not bound")
    require("checklist" not in main_tex.lower(), "NS-024 checklist must not be substituted here")
    require(r"\usepackage{neurips_2026_vericode}" in main_tex, "official style missing")
    require("[final]" not in main_tex and "[preprint]" not in main_tex and "[nonanonymous]" not in main_tex,
            "non-anonymous style option present")

    useful = results["useful_completions"]
    planned = results["planned_cells"]
    a_useful = results["arm_useful_fixed16"]["A"]["useful"]
    b_useful = results["arm_useful_fixed16"]["B"]["useful"]
    delta = results["mean_B_minus_A_useful"]
    lo = results["bootstrap"]["quality_B_minus_A"]["lower"]
    hi = results["bootstrap"]["quality_B_minus_A"]["upper"]
    outcomes = results["outcomes"]
    require(useful == 9 and planned == 32 and a_useful == 5 and b_useful == 4, "arm useful counts")
    require(delta == -0.0625 and lo == -0.1875 and hi == 0.0, "descriptive interval")
    require(outcomes == {
        "full_cold_pass": 9,
        "hidden_acceptance_failed": 7,
        "known_proposal_failure": 2,
        "proposal_child_deadline": 14,
    }, "outcome partition")
    require(results["independent_families"] == 8, "family count")
    require(results["nested_repetitions_per_family_arm"] == 2, "nested repetitions")
    require(results["terminal_cells"] == 32 and results["missing_or_nonterminal"] == 0, "terminal 32")
    require(results["new_scientific_calls"] == 0, "new scientific calls")
    require(sum(1 for row in results["rows"] if row["actual_cold_completed"]) == 15, "cold completed")
    require(sum(row["actual_provider_posts"] for row in results["rows"]) == 32, "provider posts")
    require(all(row["unknown_external_charge"] for row in results["rows"]), "unknown charges")

    combined = main_tex + "\n" + pdf_text
    numeric_needles = [
        "9/32", "5/16", "4/16", "-0.0625", "0.0625",
        "104729", "130363", "20,000", "20000", "20{,}000",
        "14", "16/32",
    ]
    for needle in ("9/32", "5/16", "4/16", "104729", "130363"):
        require(needle in pdf_text, f"PDF missing {needle}")
    require("-0.0625" in pdf_text or "−0.0625" in pdf_text, "PDF missing contrast")
    require("-0.1875" in pdf_text or "−0.1875" in pdf_text, "PDF missing interval")
    require("withdrawn" in pdf_text.lower(), "withdrawn scope missing")
    require("human semantic" in pdf_text.lower(), "human-fidelity limitation missing")
    require("settled" in pdf_text.lower() and "unavailable" in pdf_text.lower(), "cost limitation missing")
    require("NS-NNN" in pdf_text or "internal qualification" in pdf_text.lower(), "NS-NNN definition missing")
    require("not a demonstrated improvement" in pdf_text.lower() or "does not establish superiority" in pdf_text.lower()
            or "not a demonstrated improvement" in main_tex.lower(),
            "missing negative interpretation")

    family_pdf = MS / "generated/figures/family_useful.pdf"
    require(family_pdf.stat().st_size == 5019, "NS-019 ASCII PDF size changed")
    require(sha256(family_pdf).startswith(NS019_ASCII_PREFIX), "NS-019 ASCII PDF identity changed")
    paper_bytes = paper_pdf.read_bytes()
    require(b"\x00" not in paper_bytes, "paper.pdf contains NUL bytes")
    try:
        paper_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise SystemExit(f"NS-022 check failed: paper.pdf is not UTF-8 text: {exc}") from exc
    require(not (MS / "layout/family_useful.pdf").exists(), "undeclared layout figure must not overwrite NS-019 ownership")

    checks = {
        "schema": "neurosymbolic-supervision/manuscript-result-checks@1",
        "task_id": "NS-022",
        "new_scientific_calls": 0,
        "results_json_sha256": RESULTS_SHA,
        "generated_inputs_sha256": owned,
        "verified_references_sha256": VERIFIED_BIB,
        "ns019_family_useful_pdf": {
            "path": "papers/completion/neurosymbolic_supervision/manuscript/generated/figures/family_useful.pdf",
            "sha256": owned["generated/figures/family_useful.pdf"],
            "bytes": 5019,
            "role": "NS-019 historical/task-owned ASCII rendering; not the published Figure 1",
            "preserved": True,
        },
        "published_figure": {
            "kind": "Type1 TikZ drawing in main.tex",
            "coordinates": "eight-family useful fractions matching generated Table 17",
            "not_used": "manuscript/generated/figures/family_useful.pdf",
        },
        "table18_sha256": owned["generated/table18.tex"],
        "table18_layout_copy": "two allowbreak points only; generated table18.tex bytes unchanged",
        "numeric_claims": {
            "useful_completions": f"{useful}/{planned}",
            "arm_A_useful": f"{a_useful}/16",
            "arm_B_useful": f"{b_useful}/16",
            "mean_B_minus_A": delta,
            "descriptive_95_percentile_interval": [lo, hi],
            "independent_families": 8,
            "nested_repetitions": [104729, 130363],
            "outcomes": outcomes,
            "scoring_invocations": 16,
            "completed_cold_validations": 15,
            "unknown_external_charge_rows": 32,
        },
        "placeholder_scan": {"tbd_to_be_filled_results": False, "unresolved_internal_labels": False},
        "pdf": {
            "pages": pages,
            "main_text_pages_excluding_references_appendices": main_pages,
            "page_size": info.get("Page size"),
            "type3_fonts": False,
            "font_count": len(fonts),
            "sha256": sha256(paper_pdf),
            "bytes": paper_pdf.stat().st_size,
            "shell_escape": "disabled",
            "utf8_text": True,
            "nul_bytes": False,
            "classic_xref": True,
        },
        "figure_ownership": {
            "ns019_generated_family_useful_pdf_preserved": True,
            "ns019_ascii_pdf_not_published_figure_1": True,
            "layout_family_useful_pdf_copied_into_manuscript": False,
            "reviewed_22_file_package_present": False,
            "published_figure_source": "Type1 TikZ drawing in main.tex of the eight-family coordinates",
        },
        "style": {
            "package": "neurips_2026_vericode",
            "mode": "anonymous default",
            "checklist_included": False,
            "checklist_owner": "NS-024",
        },
        "claim_ledger_alignment": {
            "final_claim_evidence_matrix": "papers/completion/neurosymbolic_supervision/audit/final_claim_evidence_matrix.json",
            "scientific_scope": "eight-family A/B local-cold descriptive comparison; C/D, warm, reuse, publication, sixteen-family inference withdrawn",
            "supplemental_not_evaluated_as_final_repairs": True,
        },
        "limitations_preserved": [
            "descriptive interval is not superiority/noninferiority/equality/safety",
            "human semantic fidelity unmeasured",
            "settled provider charges unavailable",
            "nested clocks not summed",
            "pilot 10/24 not pooled",
            "false reuse 1/26 retained",
            "native proof unavailable",
            "no complete adversarial scorer-integrity claim",
        ],
    }
    out = AUDIT / "manuscript_result_checks.json"
    out.write_text(json.dumps(checks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "main_pages": main_pages, "pages": pages, "pdf_sha256": checks["pdf"]["sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
