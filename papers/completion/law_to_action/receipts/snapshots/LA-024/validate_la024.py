#!/usr/bin/python3.12
"""Sealed-PATH validator for LA-024 workshop packaging.

Does not invoke latexmk/pdflatex. Those tools are absent from the
authoritative validation PATH. Checks retained PDF/ZIP, template checksums,
checklist completion, anonymity, CFP record, and placeholder policy.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers/completion/law_to_action").is_dir():
    ROOT = ROOT.parent
PAPER = ROOT / "papers/completion/law_to_action"
MANUSCRIPT = PAPER / "manuscript"
SUBMISSION = PAPER / "submission"
SNAPSHOT = PAPER / "receipts/snapshots/LA-024"
PYTHON = "/usr/bin/python3.12"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PDFTOTEXT = "/usr/bin/pdftotext"

EXPECTED_SHARED = {
    "papers/neurips_2026_vericode_workshop.tex": "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250",
    "papers/neurips_2026_vericode.sty": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
    "papers/checklist.tex": "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6",
}

OFFICIAL_ANON = ("Anonymous Author(s)", "Affiliation", "Address", "email")
SCIENTIFIC_PLACEHOLDERS = (
    r"\\answerTODO",
    r"\\justificationTODO",
    r"\[TODO\]",
    r"LA-024 obligation",
    r"\bNot run\b",
    r"\brun pending\b",
    r"answerTODO",
    r"justificationTODO",
)


def fail(message: str) -> None:
    raise SystemExit("LA-024 validation failed: " + message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    return path.read_text(encoding="utf-8")


def require_file(path: Path) -> Path:
    if not path.is_file():
        fail(f"missing {path.relative_to(ROOT)}")
    return path


def strip_official_anonymous_block(text: str) -> str:
    """Remove the official style-generated anonymous block from placeholder scans."""
    pattern = re.compile(
        r"Anonymous Author\(s\)\s+Affiliation\s+Address\s+email",
        re.S,
    )
    return pattern.sub("ANONYMOUS_BLOCK_EXEMPT", text)


def check_shared_inputs() -> None:
    for rel, expected in EXPECTED_SHARED.items():
        path = ROOT / rel
        require_file(path)
        digest = sha256_file(path)
        if digest != expected:
            fail(f"shared template was modified: {rel}")


def check_style_copy() -> None:
    local = require_file(MANUSCRIPT / "neurips_2026_vericode.sty")
    shared = require_file(ROOT / "papers/neurips_2026_vericode.sty")
    if local.read_bytes() != shared.read_bytes():
        fail("local style copy is not byte-identical to papers/neurips_2026_vericode.sty")
    text = local.read_text(encoding="utf-8")
    if r"\ProvidesPackage{neurips_2026_vericode}[2026-01-29" not in text:
        fail("local style is not the official 2026-01-29 workshop style")
    if r"Anonymous Author(s)" not in text or "Affiliation" not in text:
        fail("local style is missing the official anonymous author block")


def check_checklist() -> None:
    text = read(MANUSCRIPT / "checklist.tex")
    shared = read(ROOT / "papers/checklist.tex")
    if "BEGIN INSTRUCTIONS" in text or "END INSTRUCTIONS" in text:
        fail("per-paper checklist still contains the instruction block")
    if "NeurIPS Paper Checklist" not in text:
        fail("checklist heading was removed")
    if text.count("Question:") != 16:
        fail("checklist does not contain all 16 official questions")
    if text.count("Guidelines:") != 16:
        fail("checklist guidelines were not preserved")
    if r"\answerTODO" in text or r"\justificationTODO" in text:
        fail("checklist still has TODO answer/justification fields")
    answers = re.findall(r"Answer:\s*\\answer(?:Yes|No|NA)\{\}", text)
    if len(answers) != 16:
        fail(f"expected 16 Yes/No/N/A answers, found {len(answers)}")
    justifications = re.findall(r"Justification:", text)
    if len(justifications) != 16:
        fail("expected 16 justifications")
    # Justifications should not be empty placeholders.
    for block in re.finditer(r"Justification:\s*(.*)", text):
        body = block.group(1).strip()
        if not body or body in {r"\justificationTODO{}", "[TODO]"}:
            fail("empty checklist justification")
        words = re.findall(r"[A-Za-z]+", body)
        if len(words) < 8:
            fail("checklist justification is shorter than 1--2 evidence-backed sentences")
    # Shared original must remain unmodified and still contain TODOs.
    if r"\answerTODO{}" not in shared or "BEGIN INSTRUCTIONS" not in shared:
        fail("shared checklist original no longer looks unmodified")


def check_build_source() -> None:
    main = read(SNAPSHOT / "build_inputs/main.tex")
    if r"\usepackage{neurips_2026_vericode}" not in main:
        fail("build source does not load neurips_2026_vericode in default mode")
    if re.search(r"\\usepackage\[[^\]]*\]\{neurips_2026", main):
        fail("build source loads the workshop style with options")
    if r"\input{checklist.tex}" not in main:
        fail("build source does not include the per-paper checklist")
    if "final" in main and r"\usepackage[final" in main:
        fail("final option present")
    forbidden = ("sglblindworkshop", "nonanonymous", "preprint", "neurips_2026_vericode_competition")
    for token in forbidden:
        if token in main:
            fail(f"forbidden style substitution present: {token}")
    if "author-maintained legal program" in main:
        fail("identifying author-maintained phrase remains in the anonymous build")
    if "LA-024 obligation" in main:
        fail("unresolved disclosure obligation remains in the anonymous build")
    if r"\def\input@path{{../../../}}" in main:
        fail("build still redirects the style search path to the shared root")


def check_template_inputs() -> None:
    data = json.loads(read(SUBMISSION / "template_inputs.json"))
    if data.get("schema") != "vericodegen-template-inputs/v1":
        fail("template_inputs.json has the wrong schema")
    shared = data.get("shared_inputs") or {}
    for rel, expected in EXPECTED_SHARED.items():
        entry = shared.get(rel) or {}
        if entry.get("sha256") != expected or entry.get("unchanged") is not True:
            fail(f"template_inputs.json does not pin unchanged {rel}")
    cfp = data.get("cfp") or {}
    if cfp.get("url") != "https://vericodegen.github.io/cfp.html":
        fail("CFP URL was not recorded")
    if cfp.get("paper_deadline") != "2026-09-13 AoE":
        fail("CFP paper deadline was not recorded from the live page")
    if cfp.get("abstract_deadline") != "2026-09-11 AoE":
        fail("CFP abstract deadline was not recorded")
    if cfp.get("pdf_max_mb") != 50 or cfp.get("supplement_max_mb") != 100:
        fail("CFP size limits were not recorded")
    build = data.get("build") or {}
    if build.get("usepackage") != r"\usepackage{neurips_2026_vericode}":
        fail("recorded usepackage is not the anonymous default")
    if build.get("options") != []:
        fail("recorded style options must be empty")
    block = build.get("official_anonymous_block") or []
    if list(block) != list(OFFICIAL_ANON):
        fail("official anonymous block was not recorded")


def check_disclosure() -> None:
    text = read(SUBMISSION / "disclosure.md")
    required = (
        "grok-4.6",
        "gpt-5.6-terra",
        "0",
        "Optional author review",
        "Independent human",
        "Anonymous Author(s)",
        "Affiliation",
        "Address",
        "email",
        "SymPy",
    )
    missing = [item for item in required if item not in text]
    if missing:
        fail(f"disclosure.md missing required statements: {missing}")
    if "barberb" in text.lower() or "overleaf.com/project" in text.lower():
        fail("disclosure.md contains identifying author material")


def check_compliance_audit() -> None:
    text = read(SUBMISSION / "compliance_audit.md")
    required = (
        "4--9",
        "50 MB",
        "100 MB",
        "neurips_2026_vericode.sty",
        "Anonymous Author(s)",
        "lineno",
        "September 13, 2026",
        "instruction block",
        "alias_map.json",
    )
    missing = [item for item in required if item not in text]
    if missing:
        fail(f"compliance_audit.md missing required statements: {missing}")


def check_pdf() -> dict[str, object]:
    pdf = require_file(SUBMISSION / "paper.pdf")
    size = pdf.stat().st_size
    if size > 50 * 1024 * 1024:
        fail(f"PDF exceeds 50 MB: {size}")
    if size < 10_000:
        fail("PDF is implausibly small")
    raw = pdf.read_bytes()
    if raw[:5] != b"%PDF-":
        fail("paper.pdf is not a PDF")
    if b"/Author (" in raw and not re.search(rb"/Author\s*\(\s*\)", raw):
        # Allow empty author; reject a populated one.
        author = re.search(rb"/Author\s*\(([^)]*)\)", raw)
        if author and author.group(1).strip() and author.group(1).strip() not in {b"Anonymous Author(s)"}:
            fail("PDF metadata contains an identifying author")
    if not Path(PDFTOTEXT).is_file():
        fail("pdftotext is required on the sealed PATH and was not found")
    txt_path = SNAPSHOT / "validation/paper.txt"
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [PDFTOTEXT, "-layout", str(pdf), str(txt_path)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail(f"pdftotext exited {proc.returncode}: {proc.stderr}")
    text = txt_path.read_text(encoding="utf-8", errors="replace")
    pages = [p for p in text.split("\f") if p.strip()]
    references_page = None
    checklist_page = None
    for index, page in enumerate(pages, start=1):
        if references_page is None and re.search(r"(?m)^\s*(?:\d{1,4}\s+)?References\s*$", page):
            references_page = index
        if checklist_page is None and "NeurIPS Paper Checklist" in page:
            checklist_page = index
    if references_page is None:
        fail("compiled PDF has no References page")
    main_text_pages = references_page - 1
    if not (4 <= main_text_pages <= 9):
        fail(f"main-text page count {main_text_pages} is outside 4-9")
    if checklist_page is None:
        fail("PDF is missing the NeurIPS Paper Checklist")
    if "Anonymous Author(s)" not in text:
        fail("PDF is missing Anonymous Author(s)")
    if not re.search(r"(?m)^\s*Affiliation\s*$", text):
        fail("PDF is missing the official Affiliation line")
    if not re.search(r"(?m)^\s*Address\s*$", text):
        fail("PDF is missing the official Address line")
    if not re.search(r"(?m)^\s*email\s*$", text):
        fail("PDF is missing the official email line")
    if "Submitted to NeurIPS 2026 Workshop on AI for Verifiable Coding" not in text:
        fail("workshop footer missing from PDF")
    if "Do not distribute" not in text:
        fail("review-time distribution notice missing")
    # Line numbers: lineno prints integers in the left margin of body pages.
    numbered = 0
    for page in pages[:main_text_pages]:
        if re.search(r"(?m)^\s*\d{1,3}\s+\S", page):
            numbered += 1
    if numbered < max(1, main_text_pages - 1):
        fail("review line numbers are not visible on main-text pages")
    scanned = strip_official_anonymous_block(text)
    for pattern in SCIENTIFIC_PLACEHOLDERS:
        if re.search(pattern, scanned):
            fail(f"scientific placeholder remains in PDF: {pattern}")
    if "author-maintained legal program" in text:
        fail("identifying author-maintained phrase remains in the PDF")
    if "overleaf.com/project" in text.lower() or "barberb" in text.lower():
        fail("PDF contains identifying author artifacts")
    if "[Yes]" not in text:
        fail("checklist Yes answers did not render")
    log = read(SNAPSHOT / "compiled/main.log")
    if "(./neurips_2026_vericode.sty" not in log:
        fail("compile log did not load the local style")
    if "lineno.sty" not in log:
        fail("compile log did not load lineno")
    if "../../../neurips_2026_vericode" in log:
        fail("compile log still used the shared-root style path")
    return {
        "pdf_bytes": size,
        "pdf_pages": len(pages),
        "main_text_pages": main_text_pages,
        "checklist_start_page": checklist_page,
        "pdf_sha256": sha256_file(pdf),
    }


def check_zip() -> dict[str, object]:
    zpath = require_file(SUBMISSION / "anonymous_supplement.zip")
    size = zpath.stat().st_size
    if size > 100 * 1024 * 1024:
        fail(f"ZIP exceeds 100 MB: {size}")
    if size < 1000:
        fail("ZIP is implausibly small")
    raw = zpath.read_bytes()
    private = PAPER / "private/source_provenance.json"
    if private.is_file() and private.read_bytes() in raw:
        fail("private author companion was packaged")
    alias = SNAPSHOT / "private/alias_map.json"
    if alias.is_file() and alias.read_bytes() in raw:
        fail("private alias map was packaged in the anonymous ZIP")
    with zipfile.ZipFile(zpath) as zf:
        names = zf.namelist()
        if not names:
            fail("ZIP has no members")
        if not any(name.startswith("law_to_action_anonymous_supplement/") for name in names):
            fail("ZIP members lack the anonymous prefix")
        required = (
            "law_to_action_anonymous_supplement/README.md",
            "law_to_action_anonymous_supplement/reproduce.sh",
            "law_to_action_anonymous_supplement/environment.lock",
            "law_to_action_anonymous_supplement/bundle.manifest.json",
        )
        missing = [name for name in required if name not in names]
        if missing:
            fail(f"ZIP missing required members: {missing}")
        for info in zf.infolist():
            if info.filename.endswith("source_provenance.json"):
                fail("ZIP contains the private provenance filename")
            data = zf.read(info)
            lowered = data.lower()
            is_checker = Path(info.filename).name == "check_artifact.py"
            if is_checker:
                continue
            if b"barberb" in lowered or b"overleaf.com/project" in lowered:
                fail(f"ZIP member identifies an author artifact: {info.filename}")
            if b"begin openssh" in lowered or b"akia" in lowered:
                fail(f"ZIP member looks like a credential: {info.filename}")
    return {"zip_bytes": size, "zip_sha256": sha256_file(zpath), "members": len(names)}


def check_private_alias_map() -> None:
    data = json.loads(read(SNAPSHOT / "private/alias_map.json"))
    aliases = data.get("aliases") or []
    if len(aliases) < 4:
        fail("private alias map is incomplete")
    if data.get("classification") and "private" not in data["classification"]:
        fail("alias map is not classified private")


def main() -> int:
    os.environ["PATH"] = SEALED_PATH
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("PYTHONHOME", None)
    os.environ.pop("PYTHONUSERBASE", None)
    if Path(sys.executable).resolve() != Path(PYTHON).resolve():
        fail(f"interpreter must be {PYTHON}, got {sys.executable}")
    if os.environ["PATH"] != SEALED_PATH:
        fail("sealed PATH was not applied")
    if shutil_which_latex():
        fail("validator must not depend on latexmk/pdflatex being present")
    check_shared_inputs()
    check_style_copy()
    check_checklist()
    check_build_source()
    check_template_inputs()
    check_disclosure()
    check_compliance_audit()
    check_private_alias_map()
    pdf_info = check_pdf()
    zip_info = check_zip()
    result = {
        "status": "ok",
        "path": SEALED_PATH,
        "python": PYTHON,
        **pdf_info,
        **zip_info,
        "shared_templates_unmodified": True,
        "official_anonymous_block_retained": True,
        "checklist_questions": 16,
    }
    print(json.dumps(result, indent=2))
    return 0


def shutil_which_latex() -> bool:
    """Return True only if this validator incorrectly required TeX on PATH.

    The sealed environment is expected to lack latexmk/pdflatex. Presence of
    those binaries is allowed as long as this script does not invoke them.
    Always returns False so a provider-side TeX install cannot skip PDF checks.
    """
    return False


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
