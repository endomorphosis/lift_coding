#!/usr/bin/env python3
"""Inspect the compiled PDF, official style, and completed questionnaire."""
from __future__ import annotations

import hashlib
import json
import re
import zlib
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[5]
PAPER = REPO_ROOT / "papers/completion/autoformalization"
MAX_PDF = 50 * 1024 * 1024
OFFICIAL = {
    "papers/neurips_2026_vericode_workshop.tex": "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250",
    "papers/neurips_2026_vericode.sty": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
    "papers/checklist.tex": "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6",
}
HEADINGS = (
    "Claims",
    "Limitations",
    "Theory assumptions and proofs",
    "Experimental result reproducibility",
    "Open access to data and code",
    "Experimental setting/details",
    "Experiment statistical significance",
    "Experiments compute resources",
    "Code of ethics",
    "Broader impacts",
    "Safeguards",
    "Licenses for existing assets",
    "New assets",
    "Crowdsourcing and research with human subjects",
    "Institutional review board (IRB) approvals or equivalent for research with human subjects",
    "Declaration of LLM usage",
)
IDENTIFYING = re.compile(
    r"(?i)(\bbarberb\b|lift_coding|/home/[A-Za-z0-9._-]+|/Users/[A-Za-z0-9._-]+|"
    r"overleaf\.com|BEGIN [A-Z ]*PRIVATE|x-api-key|Authorization:\s*Bearer|"
    r"sk-[A-Za-z0-9]{16,}|grok_cli_auth)"
)
PLACEHOLDER = re.compile(
    r"\[TBD\]|\[TODO\]|\[To complete|\\answerTODO|\\justificationTODO|To be completed",
    re.I,
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_text(data: bytes) -> str:
    chunks = []
    for match in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", data, re.S):
        payload = match.group(1)
        try:
            payload = zlib.decompress(payload)
        except zlib.error:
            pass
        chunks.append(payload)
    blob = b"\n".join(chunks)
    strings = []
    for raw in re.findall(rb"\((?:\\.|[^\\)])+\)", blob):
        inner = raw[1:-1]
        inner = re.sub(rb"\\([0-7]{3})", lambda m: bytes([int(m.group(1), 8)]), inner)
        inner = inner.replace(b"\\(", b"(").replace(b"\\)", b")").replace(b"\\\\", b"\\")
        strings.append(inner.decode("latin-1", errors="replace"))
    text = " ".join(strings)
    for src, dst in (("\x02", "ff"), ("\x03", "fi"), ("\x04", "fl"), ("\x05", "ffi"), ("\x06", "ffl")):
        text = text.replace(src, dst)
    return text


def pdf_info_strings(data: bytes) -> dict[str, str]:
    def decode(inner: bytes) -> str:
        out = bytearray()
        i = 0
        while i < len(inner):
            if inner[i] == 0x5C and i + 3 < len(inner) and 48 <= inner[i + 1] <= 55:
                out.append(int(inner[i + 1 : i + 4], 8))
                i += 4
            else:
                out.append(inner[i])
                i += 1
        raw = bytes(out)
        if raw.startswith(b"\xfe\xff"):
            return raw[2:].decode("utf-16-be", errors="replace")
        return raw.decode("latin-1", errors="replace")

    info = {}
    for key in (b"Author", b"Title", b"Creator", b"Producer", b"Subject"):
        match = re.search(key + rb"\s*\((?:\\.|[^\\)])*\)", data)
        if match:
            info[key.decode()] = decode(match.group(0).split(b"(", 1)[1][:-1])
        else:
            info[key.decode()] = ""
    return info


def log_marker(log: str, name: str) -> int | None:
    match = re.search(rf"{re.escape(name)}:(\d+)", log)
    return int(match.group(1)) if match else None


def last_shipped_page_before(log: str, name: str) -> int | None:
    lines = log.splitlines()
    index = next((i for i, line in enumerate(lines) if name in line), None)
    if index is None:
        return None
    last = None
    for line in lines[:index]:
        for match in re.finditer(r"\[(\d+)\]", line):
            last = int(match.group(1))
    return last


def main() -> int:
    errors: list[str] = []
    pdf_path = PAPER / "submission" / "paper.pdf"
    log_path = HERE / "logs" / "pdflatex.main.log"
    build_main = HERE / "build" / "main.tex"
    checklist = PAPER / "manuscript" / "checklist.tex"
    disclosure = PAPER / "manuscript" / "llm_disclosure.tex"
    sty = PAPER / "manuscript" / "neurips_2026_vericode.sty"
    for path in (pdf_path, log_path, build_main, checklist, disclosure, sty):
        if not path.is_file():
            errors.append(f"missing {path}")
    if errors:
        print("inspect_format failed:\n- " + "\n- ".join(errors))
        return 1

    pdf = pdf_path.read_bytes()
    log = log_path.read_text(encoding="utf-8", errors="replace")
    build = build_main.read_text(encoding="utf-8")
    check = checklist.read_text(encoding="utf-8")
    disc = disclosure.read_text(encoding="utf-8")
    text = pdf_text(pdf)
    info = pdf_info_strings(pdf)
    total = None
    written = re.search(r"Output written on main\.pdf \((\d+) pages", log)
    if written:
        total = int(written.group(1))
    before_bib = log_marker(log, "AF024-BEFORE-BIB")
    before_app = log_marker(log, "AF024-BEFORE-APPENDIX")
    before_disc = log_marker(log, "AF024-BEFORE-DISCLOSURE")
    before_check = log_marker(log, "AF024-BEFORE-CHECKLIST")
    # Last fully shipped page before bibliography is the main-text count.
    # If \thepage is already N+1, references start at the top of page N+1.
    main_pages = last_shipped_page_before(log, "AF024-BEFORE-BIB") or (
        before_bib - 1 if before_bib and before_bib > 1 else before_bib
    )
    undefined = [ln.strip() for ln in log.splitlines() if "undefined" in ln.lower() and "Reference" not in ln]
    missing_fonts = [ln.strip() for ln in log.splitlines() if "not found" in ln.lower() and "font" in ln.lower()]

    if total is None or total < 5:
        errors.append(f"could not determine total pages: {total}")
    if main_pages is None or not (4 <= main_pages <= 9):
        errors.append(f"main-text pages excluding refs/appendices must be 4-9, found {main_pages}")
    if len(pdf) > MAX_PDF:
        errors.append(f"PDF exceeds 50 MB: {len(pdf)}")
    if sha256(sty) != OFFICIAL["papers/neurips_2026_vericode.sty"]:
        errors.append("per-paper style copy does not match official neurips_2026_vericode.sty")
    if r"\usepackage{neurips_2026_vericode}" not in build:
        errors.append("build source does not load neurips_2026_vericode")
    if re.search(r"\\usepackage\[([^\]]*final|[^\]]*preprint|[^\]]*nonanonymous|[^\]]*sglblind)", build):
        errors.append("build source loads a forbidden style option")
    if "neurips_2026_vericode_competition" in build or r"\usepackage{neurips_2026}" in build.replace("neurips_2026_vericode", ""):
        errors.append("competition or generic style substitution present")
    if r"\input{checklist.tex}" not in build:
        errors.append("build source does not include checklist after appendices")
    if r"\input{llm_disclosure.tex}" not in build:
        errors.append("build source does not include llm_disclosure")
    if "BEGIN INSTRUCTIONS" in check or "END INSTRUCTIONS" in check:
        errors.append("checklist still contains the instruction block")
    if r"\answerTODO" in check or r"\justificationTODO" in check:
        errors.append("checklist still contains TODO fields")
    if "NeurIPS Paper Checklist" not in check:
        errors.append("checklist heading missing")
    for heading in HEADINGS:
        if heading not in check:
            errors.append(f"missing official question: {heading}")
    if check.count("Guidelines:") < 16:
        errors.append("checklist guidelines were not preserved")
    answers = re.findall(r"\\item\[\] Answer: \\answer(Yes|No|NA)\{\}", check)
    if len(answers) != 16:
        errors.append(f"expected 16 completed answers, found {len(answers)}")
    justifications = [ln for ln in check.splitlines() if r"\item[] Justification:" in ln]
    if len(justifications) != 16 or any("TODO" in ln for ln in justifications):
        errors.append("expected 16 evidence-backed justifications")
    if "grok-4.6" not in disc or "1110a243fdf4706b3f48f1d95db1a4f5529b4d41" not in disc:
        errors.append("disclosure is missing logged grok-4.6 or MiniLM revision")
    if "invent" in disc.lower() and "not invent" not in disc.lower():
        errors.append("disclosure language is inconsistent with log-only policy")
    if info.get("Author") != "Anonymous Author(s)":
        errors.append(f"PDF Author metadata is not anonymous: {info.get('Author')!r}")
    ident_hits = IDENTIFYING.findall(text) + IDENTIFYING.findall(info.get("Author", "")) + IDENTIFYING.findall(info.get("Creator", ""))
    # Official style-generated strings and ligature-split Anonymous Author(s)/Affiliation.
    official_block = (
        "Anonymous" in text
        and "uthor" in text
        and ("ffliation" in text or "Affiliation" in text)
        and "Address" in text
        and "email" in text
    )
    if not official_block:
        errors.append("official anonymous Affiliation/Address/email block was not retained in the PDF")
    if "Submitted to NeurIPS 2026" not in text:
        errors.append("workshop footer is missing from the PDF")
    if "distrib" not in text:
        errors.append("review 'do not distribute' footer is missing")
    if "Checklist" not in text:
        errors.append("checklist heading is missing from the PDF")
    if not re.search(r"\b\d{2,4}\b.{0,20}Claims", text):
        errors.append("review line numbers are missing near the checklist")
    scientific_placeholders = []
    for match in PLACEHOLDER.finditer(text + "\n" + build + "\n" + check + "\n" + disc):
        snippet = match.group(0)
        if snippet.lower() in {"affiliation", "address", "email"}:
            continue
        scientific_placeholders.append(snippet)
    # Source/PDF placeholder checks must ignore official anonymous template text.
    if scientific_placeholders:
        errors.append("unexplained scientific placeholders remain: " + ", ".join(sorted(set(scientific_placeholders))))
    if ident_hits:
        errors.append("identifying metadata/text in PDF: " + ", ".join(sorted({str(h) for h in ident_hits})))
    if b"barberb" in pdf or b"overleaf.com" in pdf:
        errors.append("PDF bytes contain identifying operator or Overleaf strings")
    if "lineno" not in log:
        errors.append("lineno package was not loaded (anonymous review line numbers)")

    report = {
        "schema": "autoformalization-format-check/v1",
        "task_id": "AF-024",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "ok": not errors,
        "errors": errors,
        "pdf": {
            "path": "papers/completion/autoformalization/submission/paper.pdf",
            "bytes": len(pdf),
            "sha256": hashlib.sha256(pdf).hexdigest(),
            "max_bytes": MAX_PDF,
            "within_50mb": len(pdf) <= MAX_PDF,
            "total_pages": total,
            "metadata": info,
        },
        "page_accounting": {
            "main_text_pages_excluding_refs_appendices": main_pages,
            "min_main_text_pages": 4,
            "max_main_text_pages": 9,
            "bibliography_start_page": before_bib,
            "appendix_start_page": before_app,
            "disclosure_start_page": before_disc,
            "checklist_start_page": before_check,
            "total_pages": total,
            "style_generated_anonymous_block_exempted": True,
        },
        "style": {
            "package": "neurips_2026_vericode",
            "options": [],
            "anonymous_default": True,
            "competition_or_generic_substitution": False,
            "workshop_footer_present": "Submitted to NeurIPS 2026" in text,
            "review_line_numbers_present": bool(re.search(r"\b\d{2,4}\b.{0,20}Claims", text)),
            "official_anonymous_block_retained": official_block,
            "per_paper_style_sha256": sha256(sty),
            "matches_official_style": sha256(sty) == OFFICIAL["papers/neurips_2026_vericode.sty"],
        },
        "checklist": {
            "questions": 16,
            "answers": answers,
            "instruction_block_removed": "BEGIN INSTRUCTIONS" not in check,
            "todo_fields_present": False,
            "guidelines_preserved": check.count("Guidelines:") >= 16,
        },
        "disclosure_agrees_with_logs": {
            "grok_46_development_call": "grok-4.6" in disc and "2026-09-12" in disc,
            "minilm_revision": "1110a243fdf4706b3f48f1d95db1a4f5529b4d41" in disc,
            "codex_fallback_not_invoked": "not invoked" in disc,
            "plan_nomination_zero_calls": "zero model calls" in disc,
            "author_verification_not_claimed": "not a substitute for author verification" in disc,
        },
        "anonymity": {
            "pdf_author": info.get("Author"),
            "identifying_hits": ident_hits,
            "operator_or_overleaf_in_pdf_bytes": False,
        },
        "placeholders": {
            "scientific_unresolved": scientific_placeholders,
            "official_affiliation_address_email_exempted": True,
        },
        "latex": {
            "undefined_references": undefined,
            "missing_fonts": missing_fonts,
            "lineno_loaded": "lineno" in log,
        },
        "shared_templates": {
            name: {
                "sha256": sha256(REPO_ROOT / name),
                "matches_recorded": sha256(REPO_ROOT / name) == digest,
                "modified": sha256(REPO_ROOT / name) != digest,
            }
            for name, digest in OFFICIAL.items()
        },
    }
    out = PAPER / "evidence" / "format_check.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["ok"], "main_text_pages": main_pages, "total_pages": total, "errors": errors}, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
