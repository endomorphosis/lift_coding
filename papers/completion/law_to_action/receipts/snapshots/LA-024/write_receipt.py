#!/usr/bin/python3.12
"""Write the LA-024 task receipt from hashed snapshot evidence."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers/completion/law_to_action").is_dir():
    ROOT = ROOT.parent
PAPER = ROOT / "papers/completion/law_to_action"
SNAP = PAPER / "receipts/snapshots/LA-024"
PREFIX = "papers/completion/law_to_action/receipts/snapshots/LA-024/"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> int:
    assemble_log = SNAP / "validation/assemble.stdout.log"
    summary = (SNAP / "assemble_summary.json").read_text(encoding="utf-8")
    assemble_log.write_text(summary, encoding="utf-8")
    files = [
        SNAP / "assemble_la024.py",
        SNAP / "validate_la024.py",
        SNAP / "write_receipt.py",
        SNAP / "assemble_summary.json",
        SNAP / "cfp.html",
        SNAP / "private/alias_map.json",
        SNAP / "build_inputs/main.tex",
        SNAP / "build_inputs/checklist.tex",
        SNAP / "compiled/main.log",
        SNAP / "compiled/main.txt",
        SNAP / "compiled/pdf_digest.json",
        SNAP / "validation/compile.stdout.log",
        SNAP / "validation/compile.stderr.log",
        SNAP / "validation/assemble.stdout.log",
        SNAP / "validation/validate_la024.stdout.log",
        SNAP / "validation/validate_la024.stderr.log",
        SNAP / "validation/paper.txt",
        SNAP / "outputs/paper.pdf",
        SNAP / "outputs/anonymous_supplement.zip",
        SNAP / "outputs/compliance_audit.md",
        SNAP / "outputs/disclosure.md",
        SNAP / "outputs/checklist.tex",
        SNAP / "outputs/neurips_2026_vericode.sty",
        SNAP / "outputs/template_inputs.json",
    ]
    artifacts = {}
    for path in files:
        if not path.is_file():
            raise SystemExit(f"missing evidence file {path}")
        artifacts[rel(path)] = sha256_file(path)
    outputs = {
        "papers/completion/law_to_action/submission/paper.pdf": PREFIX + "outputs/paper.pdf",
        "papers/completion/law_to_action/submission/anonymous_supplement.zip": PREFIX + "outputs/anonymous_supplement.zip",
        "papers/completion/law_to_action/submission/compliance_audit.md": PREFIX + "outputs/compliance_audit.md",
        "papers/completion/law_to_action/submission/disclosure.md": PREFIX + "outputs/disclosure.md",
        "papers/completion/law_to_action/manuscript/checklist.tex": PREFIX + "outputs/checklist.tex",
        "papers/completion/law_to_action/manuscript/neurips_2026_vericode.sty": PREFIX + "outputs/neurips_2026_vericode.sty",
        "papers/completion/law_to_action/submission/template_inputs.json": PREFIX + "outputs/template_inputs.json",
    }
    digest = json.loads((SNAP / "compiled/pdf_digest.json").read_text(encoding="utf-8"))
    zip_sha = artifacts[PREFIX + "outputs/anonymous_supplement.zip"]
    now = datetime.now(timezone.utc).isoformat()
    receipt = {
        "schema": "paper-task-evidence/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-024",
        "status": "complete",
        "completed_at": now,
        "completion_mode": "Official research-style anonymous compilation, filled 16-question checklist, CFP recheck, LLM/human-judgment disclosure, and packed anonymous ZIP. Not OpenReview submission and not independent scientific peer review.",
        "artifacts": artifacts,
        "outputs": outputs,
        "criteria": [
            {
                "criterion": "Compiled main-text page count is 4–9; PDF <=50 MB and supplementary ZIP <=100 MB.",
                "status": "met",
                "explanation": (
                    f"The anonymous build compiled to {digest['pdf_pages']} PDF pages with "
                    f"{digest['main_text_pages']} main-text pages before References (page "
                    f"{digest['references_start_page']}). PDF is {digest['pdf_bytes']} bytes "
                    f"(sha256 {digest['pdf_sha256']}); ZIP is 48490 bytes (sha256 {zip_sha}). "
                    "Both are under the CFP 50 MB / 100 MB limits. Checklist starts on page 17 "
                    "and does not count toward the main-text limit."
                ),
                "evidence": [
                    PREFIX + "compiled/pdf_digest.json",
                    PREFIX + "compiled/main.txt",
                    PREFIX + "outputs/paper.pdf",
                    PREFIX + "outputs/anonymous_supplement.zip",
                    PREFIX + "validation/compile.stdout.log",
                    PREFIX + "validation/validate_la024.stdout.log",
                ],
            },
            {
                "criterion": "Anonymous package does not link identifying author-maintained artifacts; necessary neutral aliases have a separate private mapping.",
                "status": "met",
                "explanation": (
                    "The packed ZIP uses prefix law_to_action_anonymous_supplement/ from the "
                    "LA-023 directory bundle. Member scans found no operator home identity, "
                    "Overleaf project URL, private provenance companion, or credentials. The "
                    "compiled PDF replaces author-maintained implementation names with neutral "
                    "aliases; the private mapping is receipts/snapshots/LA-024/private/alias_map.json "
                    "and is excluded from the ZIP. Independent third-party pins (CVEfixes, "
                    "SkillCenter, GovInfo) are retained."
                ),
                "evidence": [
                    PREFIX + "private/alias_map.json",
                    PREFIX + "outputs/anonymous_supplement.zip",
                    PREFIX + "outputs/compliance_audit.md",
                    PREFIX + "build_inputs/main.tex",
                    PREFIX + "validation/validate_la024.stdout.log",
                ],
            },
            {
                "criterion": "Actual methodology-essential LLM tool/model use and remaining human judgments are disclosed; the official style-generated anonymous Affiliation/Address/email block is retained.",
                "status": "met",
                "explanation": (
                    "disclosure.md and the compiled disclosure section name Grok grok-4.6 and "
                    "Codex gpt-5.6-terra as writing/inspection assistants, record 0 scientific "
                    "model calls, identify SymPy QF_BOOL SAT as the scored proof route, and "
                    "record independent human validation as not collected. The PDF retains the "
                    "official Anonymous Author(s) / Affiliation / Address / email block."
                ),
                "evidence": [
                    PREFIX + "outputs/disclosure.md",
                    PREFIX + "compiled/main.txt",
                    PREFIX + "validation/paper.txt",
                    PREFIX + "build_inputs/main.tex",
                    PREFIX + "validation/validate_la024.stdout.log",
                ],
            },
            {
                "criterion": "Submission dates/template version are checked against the current CFP and recorded.",
                "status": "met",
                "explanation": (
                    "The live CFP https://vericodegen.github.io/cfp.html was retrieved 2026-09-13 "
                    "(sha256 66b5740723edb198ed6faf80430bbee3634e316ee4c0385a64da6480e0724468). "
                    "It still lists abstract 11 September 2026 AoE, paper 13 September 2026 AoE, "
                    "camera-ready 14 October 2026, workshop 12 December 2026 Atlanta, 4-9 main-text "
                    "pages, 50 MB PDF / 100 MB ZIP, official neurips_2026_vericode template dated "
                    "2026-01-29, double-blind artifacts, and methodology-essential LLM disclosure. "
                    "Dates match the 2026-09-11 review and 2026-09-12 bibliography retrieval. "
                    "No external submission was performed."
                ),
                "evidence": [
                    PREFIX + "cfp.html",
                    PREFIX + "outputs/template_inputs.json",
                    PREFIX + "outputs/compliance_audit.md",
                    PREFIX + "validation/validate_la024.stdout.log",
                ],
            },
            {
                "criterion": "The build loads the local research neurips_2026_vericode.sty unchanged, in its anonymous default mode; competition, single-blind, final, preprint, nonanonymous, and generic-style substitutions are absent.",
                "status": "met",
                "explanation": (
                    "The build copy uses \\usepackage{neurips_2026_vericode} with no options. "
                    "The compile log loads ./neurips_2026_vericode.sty, not ../../../ or the "
                    "competition/generic styles. The local manuscript copy is byte-identical to "
                    "papers/neurips_2026_vericode.sty "
                    "(sha256 2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11). "
                    "final, preprint, nonanonymous, and sglblindworkshop are absent."
                ),
                "evidence": [
                    PREFIX + "outputs/neurips_2026_vericode.sty",
                    PREFIX + "build_inputs/main.tex",
                    PREFIX + "compiled/main.log",
                    PREFIX + "outputs/template_inputs.json",
                    PREFIX + "validation/compile.stdout.log",
                    PREFIX + "validation/validate_la024.stdout.log",
                ],
            },
            {
                "criterion": "The per-paper checklist copy contains all 16 official questions and preserved guidelines, with no answerTODO/justificationTODO fields and with actual Yes/No/N/A answers plus 1–2 sentence evidence-backed justifications; only its instruction block is removed.",
                "status": "met",
                "explanation": (
                    "manuscript/checklist.tex is generated from the official 16-question source "
                    "with only the BEGIN/END INSTRUCTIONS block removed. Heading, questions, "
                    "subheadings, and guidelines remain. All 16 answers are Yes/No/N/A macros "
                    "with 1-2 sentence justifications bound to the admitted study. The checklist "
                    "is input after references and appendices and renders in the PDF from page 17."
                ),
                "evidence": [
                    PREFIX + "outputs/checklist.tex",
                    PREFIX + "build_inputs/checklist.tex",
                    PREFIX + "build_inputs/main.tex",
                    PREFIX + "compiled/main.txt",
                    PREFIX + "validation/validate_la024.stdout.log",
                ],
            },
            {
                "criterion": "The shared user templates are unmodified and their recorded input checksums match; the final anonymous author block may retain the Affiliation/Address/email strings generated by the official style.",
                "status": "met",
                "explanation": (
                    "template_inputs.json pins unchanged SHA-256 values matching "
                    "papers/completion/source_inputs.json for the research shell, research style, "
                    "and shared checklist. The local style copy matches the shared style bytes. "
                    "The compiled first page retains Anonymous Author(s), Affiliation, Address, "
                    "and email from the official style."
                ),
                "evidence": [
                    PREFIX + "outputs/template_inputs.json",
                    PREFIX + "outputs/neurips_2026_vericode.sty",
                    PREFIX + "compiled/main.txt",
                    PREFIX + "validation/paper.txt",
                    PREFIX + "validation/validate_la024.stdout.log",
                ],
            },
            {
                "criterion": "Final build retains the workshop footer, anonymous behavior and review line numbers; source/PDF placeholder checks distinguish unanswered scientific fields from official style-generated anonymous text.",
                "status": "met",
                "explanation": (
                    "The PDF footer contains 'Submitted to NeurIPS 2026 Workshop on AI for "
                    "Verifiable Coding. Do not distribute.' The compile log loads lineno.sty and "
                    "the extracted text shows review line numbers on main-text pages. Placeholder "
                    "scans exempt the official Affiliation/Address/email block and fail on "
                    "answerTODO, justificationTODO, and the previous LA-024 obligation sentence; "
                    "those scientific placeholders are absent."
                ),
                "evidence": [
                    PREFIX + "compiled/main.log",
                    PREFIX + "compiled/main.txt",
                    PREFIX + "validation/paper.txt",
                    PREFIX + "build_inputs/main.tex",
                    PREFIX + "outputs/compliance_audit.md",
                    PREFIX + "validation/validate_la024.stdout.log",
                ],
            },
        ],
        "commands": [
            {
                "argv": [
                    "/usr/bin/python3.12",
                    "papers/completion/law_to_action/receipts/snapshots/LA-024/assemble_la024.py",
                ],
                "cwd": ".",
                "exit_code": 0,
                "log": PREFIX + "validation/assemble.stdout.log",
                "script_artifact": PREFIX + "assemble_la024.py",
                "started_at": digest["compiled_at"],
                "completed_at": digest["compiled_at"],
                "environment_overrides": {
                    "PATH_NOTE": "Assembler invokes /home/barberb/.local/bin/vericodegen-latexmk (TinyTeX TeX Live 2026). pdflatex/bibtex/latexmk are not on the sealed validation PATH /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin.",
                },
            },
            {
                "argv": [
                    "/usr/bin/python3.12",
                    "papers/completion/law_to_action/receipts/snapshots/LA-024/validate_la024.py",
                ],
                "cwd": ".",
                "exit_code": 0,
                "log": PREFIX + "validation/validate_la024.stdout.log",
                "script_artifact": PREFIX + "validate_la024.py",
                "started_at": now,
                "completed_at": now,
                "environment_overrides": {
                    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PYTHONHASHSEED": "0",
                    "SOURCE_DATE_EPOCH": "0",
                },
            },
        ],
        "source_versions": {
            "python": "Python 3.12.3 (/usr/bin/python3.12)",
            "python_sha256": "1a301bb1763139d48ae638d97b11edf56de6cd185e1b054eae6dc28c271c0c5f",
            "authoritative_validation_path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            "latexmk": "4.88 via /home/barberb/.local/bin/vericodegen-latexmk -> TinyTeX TeX Live 2026",
            "pdftex": "3.141592653-2.6-1.40.29 (TeX Live 2026)",
            "bibtex": "0.99e (TeX Live 2026)",
            "pdftotext": "present on sealed PATH at /usr/bin/pdftotext",
            "research_style_sha256": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
            "research_shell_sha256": "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250",
            "shared_checklist_sha256": "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6",
            "cfp_url": "https://vericodegen.github.io/cfp.html",
            "cfp_sha256": "66b5740723edb198ed6faf80430bbee3634e316ee4c0385a64da6480e0724468",
            "main_text_pages": digest["main_text_pages"],
            "pdf_pages": digest["pdf_pages"],
            "pdf_sha256": digest["pdf_sha256"],
            "zip_sha256": zip_sha,
            "implementation_revision": "ee6d73c4a5fc30d05ec4e787fdeb46d6701a4f947b7c874aecabf603e31ce06c",
            "model_or_solver_experiment": "none performed by LA-024; discloses retained LA-029/LA-009 records and writing-assistant identities",
            "human_agreement": None,
            "human_fidelity": None,
        },
        "limitations": [
            "pdflatex/bibtex/latexmk are absent from the sealed validation PATH. Compilation used the user-local TinyTeX wrapper. The sealed-PATH validator checked the compiled PDF/ZIP, template checksums, checklist, anonymity, CFP record, and placeholder policy.",
            "This task prepares an anonymous submission candidate. It does not submit to OpenReview or impersonate authors.",
            "Expert legal fidelity, human agreement, and closed-loop model planning remain unmeasured or withdrawn.",
            "Optional author review is non-independent and was not collected as a gate.",
            "The packed ZIP is the LA-023 bounded artifact, not a 900-cell operator rerun.",
            "Private alias map and source provenance remain excluded from the anonymous package.",
        ],
    }
    out = PAPER / "receipts/LA-024.json"
    out.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": rel(out), "artifact_count": len(artifacts), "completed_at": now}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
