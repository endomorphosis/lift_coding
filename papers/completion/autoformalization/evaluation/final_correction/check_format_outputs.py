#!/usr/bin/env python3
"""Sealed-PATH AF-024 checks for template, checklist, disclosure, and PDF."""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

OFFICIAL = {
    "papers/neurips_2026_vericode_workshop.tex": "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250",
    "papers/neurips_2026_vericode.sty": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
    "papers/checklist.tex": "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6",
}
HEADINGS = (
    "Claims", "Limitations", "Theory assumptions and proofs",
    "Experimental result reproducibility", "Open access to data and code",
    "Experimental setting/details", "Experiment statistical significance",
    "Experiments compute resources", "Code of ethics", "Broader impacts",
    "Safeguards", "Licenses for existing assets", "New assets",
    "Crowdsourcing and research with human subjects",
    "Institutional review board (IRB) approvals or equivalent for research with human subjects",
    "Declaration of LLM usage",
)
FORBIDDEN_OPTIONS = ("final", "preprint", "nonanonymous", "sglblindworkshop")


def find_repo_root(start: Path) -> Path:
    marker = Path("papers/completion/autoformalization/config/environment_manifest.json")
    for path in (start, *start.parents):
        if (path / marker).is_file():
            return path
    raise SystemExit("cannot locate repository root from check_outputs.py")


HERE = Path(__file__).resolve().parent
REPO_ROOT = find_repo_root(HERE)
PAPER = REPO_ROOT / "papers/completion/autoformalization"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    errors: list[str] = []
    paths = {
        "checklist": PAPER / "manuscript" / "checklist.tex",
        "disclosure": PAPER / "manuscript" / "llm_disclosure.tex",
        "sty": PAPER / "manuscript" / "neurips_2026_vericode.sty",
        "pdf": PAPER / "submission" / "paper.pdf",
        "format": PAPER / "evidence" / "format_check.json",
        "questions": PAPER / "evidence" / "author_questions.md",
        "inputs": PAPER / "submission" / "template_inputs.json",
        "build_main": PAPER / "evidence/final_correction/build" / "main.tex",
        "pdf_bin": PAPER / "evidence/final_correction/paper.pdf",
        "pdf_identity": PAPER / "evidence/final_correction/paper.identity.json",
    }
    for name, path in paths.items():
        if not path.is_file():
            errors.append(f"missing {name}: {path}")
    if errors:
        print("AF-024 check failed:\n- " + "\n- ".join(errors))
        return 1

    for name, digest in OFFICIAL.items():
        actual = sha256(REPO_ROOT / name)
        if actual != digest:
            errors.append(f"shared user template modified: {name}")

    sty_hash = sha256(paths["sty"])
    if sty_hash != OFFICIAL["papers/neurips_2026_vericode.sty"]:
        errors.append("per-paper neurips_2026_vericode.sty is not an unchanged official copy")

    check = paths["checklist"].read_text(encoding="utf-8")
    disc = paths["disclosure"].read_text(encoding="utf-8")
    questions = paths["questions"].read_text(encoding="utf-8")
    build = paths["build_main"].read_text(encoding="utf-8")
    report = load_json(paths["format"])
    inputs = load_json(paths["inputs"])
    pdf = paths["pdf"].read_bytes()

    if "BEGIN INSTRUCTIONS" in check or r"\answerTODO" in check or r"\justificationTODO" in check:
        errors.append("checklist still has instructions or TODO fields")
    if "NeurIPS Paper Checklist" not in check or check.count("Guidelines:") < 16:
        errors.append("checklist heading or guidelines missing")
    for heading in HEADINGS:
        if heading not in check:
            errors.append(f"missing official question heading: {heading}")
    answers = re.findall(r"\\item\[\] Answer: \\answer(Yes|No|NA)\{\}", check)
    if len(answers) != 16:
        errors.append(f"need 16 Yes/No/N/A answers, found {len(answers)}")
    if answers[6] != "No":
        errors.append("statistical-significance answer is not the log-backed No")
    if answers[15] != "Yes":
        errors.append("LLM-usage answer is not Yes")
    if "grok-4.6" not in disc or "2026-09-12" not in disc:
        errors.append("disclosure missing logged grok-4.6 date")
    if "1110a243fdf4706b3f48f1d95db1a4f5529b4d41" not in disc:
        errors.append("disclosure missing logged MiniLM revision")
    if "gpt-5.6-terra" not in disc or "not invoked" not in disc:
        errors.append("disclosure must record the configured-but-unused Codex fallback")
    if "zero model calls" not in disc:
        errors.append("disclosure missing zero plan-nomination calls")
    if "author verification" not in disc.lower():
        errors.append("disclosure must not claim author verification occurred")
    if "Known from logs" not in questions or "Optional author input and future publication details" not in questions:
        errors.append("author_questions.md does not distinguish known facts from optional author facts / future publication details")
    if "sign-off" in questions.lower() and "does not assert that verification occurred" not in questions:
        if "This packet does not assert that verification occurred" not in questions:
            errors.append("author packet must not invent sign-off")

    if r"\usepackage{neurips_2026_vericode}" not in build:
        errors.append("build main.tex does not load the research style")
    for option in FORBIDDEN_OPTIONS:
        if re.search(rf"\\usepackage\[[^\]]*{option}", build):
            errors.append(f"forbidden style option present: {option}")
    if "neurips_2026_vericode_competition" in build or "sglblindworkshop" in build:
        errors.append("competition or single-blind style substitution present")
    if r"\input{checklist.tex}" not in build or r"\input{llm_disclosure.tex}" not in build:
        errors.append("build main.tex does not include disclosure and checklist")

    if report.get("schema") != "autoformalization-format-check/v1" or report.get("ok") is not True:
        errors.append("format_check.json is missing or not ok")
    pages = (report.get("page_accounting") or {}).get("main_text_pages_excluding_refs_appendices")
    if not isinstance(pages, int) or pages < 4 or pages > 9:
        errors.append(f"format_check main-text pages not in 4-9: {pages}")
    if report.get("pdf", {}).get("bytes") != len(pdf) or report.get("pdf", {}).get("sha256") != hashlib.sha256(pdf).hexdigest():
        errors.append("format_check.json does not match submission/paper.pdf")
    if len(pdf) > 50 * 1024 * 1024:
        errors.append("PDF exceeds 50 MB")
    if sha256(paths["pdf_bin"]) != hashlib.sha256(pdf).hexdigest():
        errors.append("corrective snapshot paper.pdf does not match submission/paper.pdf")
    identity = load_json(paths["pdf_identity"])
    if identity.get("sha256") != hashlib.sha256(pdf).hexdigest() or identity.get("bytes") != len(pdf):
        errors.append("paper.identity.json does not match submission/paper.pdf")
    if report.get("style", {}).get("matches_official_style") is not True:
        errors.append("format_check did not confirm unchanged official style")
    if report.get("style", {}).get("official_anonymous_block_retained") is not True:
        errors.append("format_check did not retain the official anonymous block")
    if report.get("placeholders", {}).get("scientific_unresolved"):
        errors.append("format_check still reports scientific placeholders")
    if report.get("anonymity", {}).get("identifying_hits"):
        errors.append("format_check reports identifying PDF hits")
    if b"barberb" in pdf or b"overleaf.com" in pdf or b"/home/" in pdf:
        errors.append("PDF contains operator path or Overleaf identity")

    if inputs.get("schema") != "autoformalization-template-inputs/v1":
        errors.append("template_inputs.json schema mismatch")
    if inputs.get("shared_user_templates_unmodified") is not True:
        errors.append("template_inputs.json does not pin unmodified shared templates")
    recorded = inputs.get("inputs") or {}
    for name, digest in OFFICIAL.items():
        rec = recorded.get(name) or {}
        if rec.get("sha256") != digest or rec.get("modified") is not False:
            errors.append(f"template_inputs.json mismatch for {name}")
    if inputs.get("per_paper_style_copy", {}).get("sha256") != sty_hash:
        errors.append("template_inputs.json per-paper style hash mismatch")
    if inputs.get("package_load") != r"\usepackage{neurips_2026_vericode}":
        errors.append("template_inputs.json does not record the anonymous default package load")
    if inputs.get("package_options"):
        errors.append("template_inputs.json records non-default style options")

    if errors:
        print("AF-024 check failed:\n- " + "\n- ".join(errors))
        return 1
    print("AF-024 check passed")
    print(f"main_text_pages={pages}")
    print(f"pdf_bytes={len(pdf)}")
    print(f"style_sha256={sty_hash}")
    print(f"answers={','.join(answers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
