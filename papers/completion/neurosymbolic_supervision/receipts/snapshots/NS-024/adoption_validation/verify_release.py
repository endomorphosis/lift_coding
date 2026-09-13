#!/usr/bin/env python3.12
"""Ordinary current-output verification for NS-024.

Sealed validation PATH is /usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin.
This program uses python3.12, pdffonts, pdfinfo, and pdftotext from that
environment. It does not invoke pdflatex, providers, scorers, or experiments.
"""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

def repository_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "scripts/paper_supervisors.py").is_file() and (
            candidate / "papers/completion/neurosymbolic_supervision"
        ).is_dir():
            return candidate
    raise FileNotFoundError("cannot locate repository root from validator path")


ROOT = repository_root()
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
LIVE_MS = PAPER / "manuscript"
LIVE_REL = PAPER / "release"
LIVE_AUDIT = PAPER / "audit"
LIVE_SUB = PAPER / "submission"
SNAP = PAPER / "receipts/snapshots/NS-024"
SRC_IN = PAPER / "writing_inputs/ns024_complete_release_v1"
MS_SRC = SNAP / "manuscript_source_v1"

ACCEPTED_PDF = "0fb82abbec94c3858b6c9e63fcd456b16a5ad4aa2f294c4b52d08a8592c59862"
ACCEPTED_ZIP = "48cee756e4e1bcdcf4d541b6c8721f21cba0800e990e1159a64f3eeb888a0b07"
SOURCE_MANIFEST = "89bffcb1545d491945dba5604dc11ea3fa0a0a9745d2b3ef44b0fd85a1aa0973"
HELPER = "03fd2813eda5350be5c54b8db1f67aac096caf070da2f481bdb650f68e71dae7"
WRITING_MANIFEST = "386cead215fba321f9e5ee04dbd84f86250d958e7022529361b229a346f0b7f8"
STYLE = "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11"
SHARED_CHECKLIST = "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6"
ANSWERED_CHECKLIST = "48859ff3d74dd0fabfbd77a1579b5d51d2d226a5564fab9b81f27aa3c4b531b1"
WORKSHOP_TEX = "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250"
NS022_MAIN = "d10683b13e4fb0c5566e3b71fb7941fb2a95f1be5e1a50aa38957fe3092bf8ab"
NS022_PDF = "907f0a24b775d22cbff1a35e958c2f121cbb4784756b2943dcee4eb5ae3e14ab"
NS019_ASCII_PDF = "8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5"
TABLE17 = "ffbb7f2e6aecefb0e4a65fe2da32cc43e87601e01eb7ab97715e516a22cc0b79"
TABLE18 = "3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495"
ABLATIONS = "8c57477902aba200e9a2228d6a316ec06f14859f7894fa1f534f16e8b19d8ccf"
RESULTS_SHA = "6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e"
FREEZE_FILE = "7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a"
FREEZE_CANON = "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d"
GENERIC_STY = "c3fc2894e83d2517ca18b66741d6c595986d97957dc08ec08bb2125a7ec4555a"
COMP_STY = "a0178f152d13cf24f44936da0ee95bab975ceced8d54980efbbf8f7c1bb31f72"

OUTPUT_MAP = {
    "papers/completion/neurosymbolic_supervision/release/README.md": SNAP / "release/README.md",
    "papers/completion/neurosymbolic_supervision/release/manifest.json": SNAP / "release/manifest.json",
    "papers/completion/neurosymbolic_supervision/release/reproduce.sh": SNAP / "release/reproduce.sh",
    "papers/completion/neurosymbolic_supervision/release/supplement.zip": SNAP / "release/supplement.zip",
    "papers/completion/neurosymbolic_supervision/release/paper.pdf": SNAP / "release/paper.pdf",
    "papers/completion/neurosymbolic_supervision/audit/anonymity_report.md": SNAP / "audit/anonymity_report.md",
    "papers/completion/neurosymbolic_supervision/audit/llm_use_disclosure.md": SNAP / "audit/llm_use_disclosure.md",
    "papers/completion/neurosymbolic_supervision/audit/author_attestations.md": SNAP / "audit/author_attestations.md",
    "papers/completion/neurosymbolic_supervision/audit/workshop_compliance.json": SNAP / "audit/workshop_compliance.json",
    "papers/completion/neurosymbolic_supervision/manuscript/checklist.tex": SNAP / "manuscript/checklist.tex",
    "papers/completion/neurosymbolic_supervision/manuscript/neurips_2026_vericode.sty": SNAP / "manuscript/neurips_2026_vericode.sty",
    "papers/completion/neurosymbolic_supervision/submission/template_inputs.json": SNAP / "submission/template_inputs.json",
}

EXPECTED_ANSWERS = [
    "Yes", "Yes", "No", "No", "No", "Yes", "Yes", "No",
    "N/A", "Yes", "N/A", "No", "Yes", "N/A", "N/A", "Yes",
]
DISCLOSURE_PLACEHOLDERS = [
    "[actual implementation assistance]",
    "[candidate goals/plans/patches]",
    "[proof candidates]",
    "[data processing]",
    "[manuscript preparation]",
]
SCIENTIFIC_PLACEHOLDERS = [
    r"\[TODO\]",
    r"answerTODO",
    r"justificationTODO",
    r"TO BE FILLED",
    r"\bTBD\b",
    r"compilation placeholder",
    r"\[RESULTS(?:\s*:|\])",
]


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def fail(failures: list[str], message: str) -> None:
    failures.append(message)


def run_tool(name: str, args: list[str]) -> subprocess.CompletedProcess[str]:
    binary = shutil.which(name)
    if binary is None:
        raise FileNotFoundError(f"sealed-PATH tool missing: {name}")
    return subprocess.run([binary, *args], check=True, capture_output=True, text=True)


def pdf_text(path: Path) -> str:
    return run_tool("pdftotext", ["-layout", str(path), "-"]).stdout


def pdf_info(path: Path) -> dict[str, str]:
    info = {}
    for line in run_tool("pdfinfo", [str(path)]).stdout.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
    return info


def pdf_fonts(path: Path) -> str:
    return run_tool("pdffonts", [str(path)]).stdout


def sealed_tool(name: str) -> str | None:
    for directory in ("/usr/local/sbin", "/usr/local/bin", "/usr/sbin", "/usr/bin"):
        candidate = Path(directory) / name
        if candidate.is_file():
            return str(candidate)
    return None


def placeholder_hits(text: str) -> list[str]:
    hits = []
    for pattern in SCIENTIFIC_PLACEHOLDERS:
        for match in re.finditer(pattern, text):
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 40)
            hits.append(f"{pattern}: ...{text[start:end].replace(chr(10), ' ')}...")
    return hits


def folded(text: str) -> str:
    return re.sub(r"\s+", " ", text)


def contains(text: str, *needles: str) -> bool:
    haystack = folded(text)
    return all(folded(needle) in haystack for needle in needles)


def verify_sources(failures: list[str]) -> dict:
    helper = MS_SRC / "build_from_snapshot.py"
    manifest_path = MS_SRC / "source_manifest.json"
    if sha256(helper) != HELPER:
        fail(failures, "source helper digest mismatch")
    if sha256(manifest_path) != SOURCE_MANIFEST:
        fail(failures, "source manifest digest mismatch")
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            str(helper),
            "--manifest-sha256",
            SOURCE_MANIFEST,
            "--verify-only",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if proc.returncode != 0:
        fail(failures, f"source verify-only failed: {proc.stderr[-400:]}")
        return {"verified": False, "stdout": proc.stdout, "stderr": proc.stderr}
    result = json.loads(proc.stdout)
    if result.get("verified") is not True or result.get("source_files") != 24:
        fail(failures, f"source verify-only unexpected result: {result}")
    payload_files = [p for p in MS_SRC.rglob("*") if p.is_file()]
    if len(payload_files) != 26:
        fail(failures, f"manuscript_source_v1 file count {len(payload_files)} != 26")
    return result


def checklist_answers(source: str) -> list[str]:
    answers = []
    for match in re.finditer(
        r"\\item\[\] Answer:\s*\\answer(Yes|No|NA)\{\}",
        source,
    ):
        token = match.group(1)
        answers.append("N/A" if token == "NA" else token)
    return answers


def build_report() -> dict:
    failures: list[str] = []

    if sha256(SRC_IN / "manifest.json") != WRITING_MANIFEST:
        fail(failures, "writing_inputs manifest sha mismatch")
    if sha256(SRC_IN / "paper.pdf") != ACCEPTED_PDF:
        fail(failures, "writing_inputs paper.pdf sha mismatch")
    if sha256(SRC_IN / "supplement.zip") != ACCEPTED_ZIP:
        fail(failures, "writing_inputs supplement.zip sha mismatch")

    live_hashes = {}
    for live_rel, snap in OUTPUT_MAP.items():
        live = ROOT / live_rel
        if not live.is_file() or not snap.is_file():
            fail(failures, f"missing live or snapshot: {live_rel}")
            continue
        live_hash = sha256(live)
        snap_hash = sha256(snap)
        live_hashes[live_rel] = {"sha256": live_hash, "bytes": live.stat().st_size}
        if live_hash != snap_hash:
            fail(failures, f"live/snapshot mismatch: {live_rel}")

    pdf = LIVE_REL / "paper.pdf"
    zpath = LIVE_REL / "supplement.zip"
    if sha256(pdf) != ACCEPTED_PDF or pdf.stat().st_size != 252576:
        fail(failures, "release/paper.pdf is not the accepted 0fb82abb product")
    if sha256(zpath) != ACCEPTED_ZIP or zpath.stat().st_size != 2280657:
        fail(failures, "release/supplement.zip is not the accepted 48cee756 product")
    if sha256(SNAP / "release/paper.pdf") != ACCEPTED_PDF:
        fail(failures, "raw PDF receipt snapshot digest mismatch")
    if sha256(SNAP / "release/supplement.zip") != ACCEPTED_ZIP:
        fail(failures, "raw ZIP receipt snapshot digest mismatch")

    if sha256(LIVE_MS / "main.tex") != NS022_MAIN:
        fail(failures, "NS-022 manuscript/main.tex changed")
    if sha256(LIVE_MS / "paper.pdf") != NS022_PDF:
        fail(failures, "NS-022 manuscript/paper.pdf changed")
    if sha256(LIVE_MS / "generated/figures/family_useful.pdf") != NS019_ASCII_PDF:
        fail(failures, "NS-019 generated family_useful.pdf changed")
    if sha256(LIVE_MS / "generated/table17.tex") != TABLE17:
        fail(failures, "NS-019 table17.tex changed")
    if sha256(LIVE_MS / "generated/table18.tex") != TABLE18:
        fail(failures, "NS-020 table18.tex changed")
    if sha256(LIVE_MS / "generated/ablations.tex") != ABLATIONS:
        fail(failures, "NS-019 ablations.tex changed")
    if sha256(PAPER / "analysis/results.json") != RESULTS_SHA:
        fail(failures, "NS-019 results.json changed")
    freeze_path = PAPER / "artifacts/final_experiment_freeze.json"
    if sha256(freeze_path) != FREEZE_FILE:
        fail(failures, "freeze file digest mismatch")
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    if freeze.get("freeze_sha256") != FREEZE_CANON:
        fail(failures, "canonical freeze digest mismatch")

    if sha256(ROOT / "papers/neurips_2026_vericode.sty") != STYLE:
        fail(failures, "shared research style changed")
    if sha256(ROOT / "papers/neurips_2026_vericode_workshop.tex") != WORKSHOP_TEX:
        fail(failures, "shared workshop template changed")
    if sha256(ROOT / "papers/checklist.tex") != SHARED_CHECKLIST:
        fail(failures, "shared official checklist changed")
    if sha256(LIVE_MS / "neurips_2026_vericode.sty") != STYLE:
        fail(failures, "per-paper style is not the unchanged official research style")
    if sha256(LIVE_MS / "checklist.tex") != ANSWERED_CHECKLIST:
        fail(failures, "per-paper checklist is not the answered 48859ff3 copy")
    if sha256(ROOT / "papers/neurips_2026.sty") != GENERIC_STY:
        fail(failures, "generic neurips_2026.sty unexpected digest")
    if sha256(ROOT / "papers/neurips_2026_vericode_competition.sty") != COMP_STY:
        fail(failures, "competition style unexpected digest")
    if sha256(LIVE_MS / "neurips_2026_vericode.sty") == GENERIC_STY:
        fail(failures, "generic style substitution")
    if sha256(LIVE_MS / "neurips_2026_vericode.sty") == COMP_STY:
        fail(failures, "competition style substitution")

    header = (MS_SRC / "sources/header.tex").read_text(encoding="utf-8")
    if not re.search(r"^\\usepackage\{neurips_2026_vericode\}$", header, re.M):
        fail(failures, "header does not load neurips_2026_vericode with no options")
    if re.search(r"\\usepackage\[[^\]]*\]\{neurips_2026_vericode\}", header):
        fail(failures, "header passes options to neurips_2026_vericode")
    if "neurips_2026_vericode_competition" in header or re.search(r"\\usepackage\{neurips_2026\}", header):
        fail(failures, "header loads a substituted style")
    main_src = (MS_SRC / "sources/main.tex").read_text(encoding="utf-8")
    for banned in ("[final]", "[preprint]", "[nonanonymous]", "sglblindworkshop", "competition"):
        if banned in header or banned in main_src:
            fail(failures, f"non-anonymous or substituted option present: {banned}")

    source_verify = verify_sources(failures)

    checklist = (LIVE_MS / "checklist.tex").read_text(encoding="utf-8")
    official = (ROOT / "papers/checklist.tex").read_text(encoding="utf-8")
    if "BEGIN INSTRUCTIONS" in checklist or "Delete this instruction block" in checklist:
        fail(failures, "checklist instruction block was not removed")
    if "BEGIN INSTRUCTIONS" not in official:
        fail(failures, "shared official checklist unexpectedly lost its instruction block")
    questions = [q.strip() for q in re.findall(r"\\item\[\] Question:\s*(.+)", checklist)]
    official_questions = [q.strip() for q in re.findall(r"\\item\[\] Question:\s*(.+)", official)]
    if len(questions) != 16 or len(official_questions) != 16:
        fail(failures, f"checklist question count paper={len(questions)} official={len(official_questions)}")
    if questions != official_questions:
        fail(failures, "per-paper checklist questions differ from the official shared questionnaire")
    answers = checklist_answers(checklist)
    if answers != EXPECTED_ANSWERS:
        fail(failures, f"checklist answers {answers} != {EXPECTED_ANSWERS}")
    if "\\answerTODO" in checklist or "\\justificationTODO" in checklist:
        fail(failures, "answered checklist still contains TODO fields")
    if not contains(checklist, "Guidelines:"):
        fail(failures, "checklist guidelines missing")
    justifications = re.findall(r"\\item\[\] Justification:\s*(.+)", checklist)
    if len(justifications) != 16:
        fail(failures, f"justification count {len(justifications)} != 16")
    for index, text in enumerate(justifications, 1):
        if "TODO" in text:
            fail(failures, f"justification {index} still contains TODO")

    info = pdf_info(pdf)
    fonts = pdf_fonts(pdf)
    text = pdf_text(pdf)
    pages = int(info.get("Pages", "0"))
    if pages != 20:
        fail(failures, f"paper.pdf pages={pages}, expected 20")
    if pdf.stat().st_size >= 50 * 1024 * 1024:
        fail(failures, "PDF exceeds 50 MB")
    if zpath.stat().st_size >= 100 * 1024 * 1024:
        fail(failures, "supplement ZIP exceeds 100 MB")
    if "Type 3" in fonts or "Type3" in fonts:
        fail(failures, "Type3 font present")
    if "Type 1" not in fonts:
        fail(failures, "expected Type 1 fonts missing")
    if not info.get("Author", "").startswith("Anonymous"):
        fail(failures, "paper.pdf author is not anonymous")
    if "Submitted to NeurIPS 2026 Workshop on AI for Verifiable Coding. Do not distribute." not in text:
        fail(failures, "workshop footer missing")
    if not re.search(r"^ 1\s+", text, re.M):
        fail(failures, "review line numbers missing")
    if not contains(text, "Anonymous Author(s)", "Affiliation", "Address", "email"):
        fail(failures, "official anonymous author block missing")
    if "References" not in text or "NeurIPS Paper Checklist" not in text:
        fail(failures, "references or checklist heading missing from PDF")
    if not contains(text, "LLM use, public reproduction, and responsible use"):
        fail(failures, "LLM disclosure heading missing from PDF")
    if not contains(text, "Grok 4.6", "4,096", "gpt-5.6-terra"):
        fail(failures, "methods-essential LLM details missing from PDF")
    for needle in DISCLOSURE_PLACEHOLDERS:
        if needle.lower() in text.lower() or needle.lower() in checklist.lower():
            fail(failures, f"disclosure placeholder remains: {needle}")
    if "compilation placeholder" in text.lower():
        fail(failures, "compilation placeholder remains in PDF")

    # Exempt official anonymous strings from scientific placeholder scan.
    exempted = text
    for allowed in ("Anonymous Author(s)", "Anonymous Authors", "Affiliation", "Address", "email"):
        exempted = exempted.replace(allowed, "ANON")
    pdf_hits = placeholder_hits(exempted)
    if pdf_hits:
        fail(failures, "placeholder remains in paper.pdf: " + pdf_hits[0])
    source_blob = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted(MS_SRC.rglob("*.tex"))
        if p.is_file()
    )
    source_hits = placeholder_hits(source_blob)
    if source_hits:
        fail(failures, "placeholder remains in manuscript sources: " + source_hits[0])
    # Style may define unused TODO macros.
    sty = (LIVE_MS / "neurips_2026_vericode.sty").read_text(encoding="utf-8")
    if "\\newcommand{\\answerTODO" not in sty or "\\linenumbers" not in sty:
        fail(failures, "official style lost TODO macros or line-number support")

    with zipfile.ZipFile(zpath) as archive:
        names = archive.namelist()
    if len(names) != 468:
        fail(failures, f"supplement entries {len(names)} != 468")
    required = {
        "README.md",
        "reproduce.py",
        "manifest.json",
        "final32/release_manifest.json",
        "final32/reproduce.py",
        "prior/manifest.json",
        "prior/source/reproduce.py",
        "boundary/manifest.json",
        "boundary/reproduce.py",
    }
    missing = sorted(required - set(names))
    if missing:
        fail(failures, f"supplement missing {missing}")
    with zipfile.ZipFile(zpath) as archive:
        combined = json.loads(archive.read("manifest.json"))
        if combined.get("schema") != "ns-combined-anonymous-supplement/v1":
            fail(failures, "combined supplement schema mismatch")
        if set(combined.get("components", {})) != {"final32", "prior", "boundary"}:
            fail(failures, "combined supplement components drifted")
        if combined.get("no_outcome_pooling") is not True:
            fail(failures, "combined supplement pools outcomes")
        if combined.get("original_signature_replay") is not False:
            fail(failures, "combined supplement claims signature replay")
        for kind, expected in {
            "final32": "6612cfa4b957d7aa701d6cc3255f37bd47c95758dbe88f22ecbc1a6b32f1ec26",
            "prior": "1d00715d05bbea2c7cab0ef1892f039153cc12ea0820bd556a13452ffe6b70a7",
            "boundary": "8addd3465f79791a1126d6fb4bf08c77107fa5a4e5b1ddf844d8b78b48271369",
        }.items():
            if combined["components"][kind]["sha256"] != expected:
                fail(failures, f"{kind} component manifest sha mismatch")
        zip_text_hits = []
        for name in names:
            if name.endswith("/"):
                continue
            payload = archive.read(name)
            if b"/home/barberb" in payload or b"@gmail.com" in payload:
                zip_text_hits.append(name)
        if zip_text_hits:
            fail(failures, "supplement contains raw author-host or gmail identity: " + zip_text_hits[0])

    reproduce = (LIVE_REL / "reproduce.sh").read_text(encoding="utf-8")
    if "reproduce.py" not in reproduce or "supplement.zip" not in reproduce:
        fail(failures, "reproduce.sh does not wrap extraction and included reproduce.py")
    readme = (LIVE_REL / "README.md").read_text(encoding="utf-8")
    if ACCEPTED_PDF not in readme or ACCEPTED_ZIP not in readme:
        fail(failures, "release README missing accepted PDF/ZIP digests")
    if "unmeasured" not in readme.lower():
        fail(failures, "release README missing unmeasured/withdrawn limits")
    attest = (LIVE_AUDIT / "author_attestations.md").read_text(encoding="utf-8")
    for required_attestation in (
        "Author proofread",
        "NeurIPS Code of Ethics",
        "Exact served Grok 4.6",
        "Human semantic fidelity",
        "Submission, camera-ready, or publication",
    ):
        if required_attestation not in attest:
            fail(failures, f"author attestation missing {required_attestation}")
    disclosure = (LIVE_AUDIT / "llm_use_disclosure.md").read_text(encoding="utf-8")
    if not contains(disclosure, "Grok 4.6", "4,096", "gpt-5.6-terra"):
        fail(failures, "llm disclosure missing actual model/settings")
    anonymity = (LIVE_AUDIT / "anonymity_report.md").read_text(encoding="utf-8")
    if "Anonymous Author(s)" not in anonymity or "lift_coding" not in anonymity:
        fail(failures, "anonymity report missing official block or residual path-token finding")
    compliance = json.loads((LIVE_AUDIT / "workshop_compliance.json").read_text(encoding="utf-8"))
    if compliance.get("paper_pdf", {}).get("sha256") != ACCEPTED_PDF:
        fail(failures, "workshop_compliance.pdf sha mismatch")
    if compliance.get("checklist", {}).get("answers") != EXPECTED_ANSWERS:
        fail(failures, "workshop_compliance answers mismatch")
    templates = json.loads((LIVE_SUB / "template_inputs.json").read_text(encoding="utf-8"))
    shared = {row["path"]: row["sha256"] for row in templates["shared_user_templates"]}
    if shared.get("papers/neurips_2026_vericode.sty") != STYLE:
        fail(failures, "template_inputs style checksum mismatch")
    if shared.get("papers/checklist.tex") != SHARED_CHECKLIST:
        fail(failures, "template_inputs shared checklist checksum mismatch")
    if templates.get("shared_user_templates_unmodified") is not True:
        fail(failures, "template_inputs does not record unmodified shared templates")

    if sealed_tool("pdflatex") is not None:
        fail(failures, "sealed validation PATH unexpectedly provides pdflatex")
    for required_tool in ("python3.12", "pdffonts", "pdfinfo", "pdftotext"):
        if sealed_tool(required_tool) is None:
            fail(failures, f"sealed validation PATH missing {required_tool}")

    report = {
        "schema": "ns024-release-verification/v1",
        "task_id": "NS-024",
        "all_passed": not failures,
        "failures": failures,
        "accepted_outputs": live_hashes,
        "source_verify": source_verify,
        "pdf": {
            "sha256": sha256(pdf),
            "bytes": pdf.stat().st_size,
            "pages": pages,
            "author": info.get("Author"),
            "type3": "Type 3" in fonts or "Type3" in fonts,
        },
        "supplement": {
            "sha256": sha256(zpath),
            "bytes": zpath.stat().st_size,
            "zip_entries": len(names),
        },
        "checklist_answers": answers,
        "protected": {
            "ns022_main_tex": sha256(LIVE_MS / "main.tex"),
            "ns022_paper_pdf": sha256(LIVE_MS / "paper.pdf"),
            "ns019_family_useful_pdf": sha256(LIVE_MS / "generated/figures/family_useful.pdf"),
        },
        "new_scientific_calls": 0,
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    if failures:
        raise SystemExit(1)
    return report


if __name__ == "__main__":
    build_report()
