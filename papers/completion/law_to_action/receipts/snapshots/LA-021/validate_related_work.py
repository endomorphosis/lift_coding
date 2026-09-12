#!/usr/bin/python3.12
"""Structural and citation checks for LA-021 related work and novelty.

This checker validates manuscript integration, bibliography loading, primary-source
identifier corrections, bounded novelty language, and the absence of bake-off
pretence. It is not independent scientific peer review and does not execute
external systems as experimental arms.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers" / "completion" / "law_to_action").is_dir():
    ROOT = ROOT.parent
PAPER = ROOT / "papers/completion/law_to_action"
MAIN = PAPER / "manuscript/main.tex"
BIB = PAPER / "manuscript/related_work.bib"
REFERENCES = PAPER / "manuscript/references.bib"
RELATED = PAPER / "related_work.md"
NOVELTY = PAPER / "novelty_statement.md"
COMPILED_PDF = PAPER / "manuscript/main.pdf"
COMPILED_BBL = PAPER / "manuscript/main.bbl"
COMPILED_LOG = PAPER / "manuscript/main.log"
COMPILED_TXT = PAPER / "receipts/snapshots/LA-021/compiled/main.txt"
SNAPSHOT_BBL = PAPER / "receipts/snapshots/LA-021/compiled/main.bbl"
SNAPSHOT_LOG = PAPER / "receipts/snapshots/LA-021/compiled/main.log"


def fail(message: str) -> None:
    raise SystemExit("LA-021 validation failed: " + message)


def read(path: Path) -> str:
    if not path.is_file():
        fail(f"missing file {path}")
    return path.read_text(encoding="utf-8")


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


def field(entry: str, name: str) -> str | None:
    match = re.search(rf"\b{name}\s*=\s*\{{\s*([^}}]+)\s*\}}", entry, re.I)
    if match:
        return match.group(1).strip()
    match = re.search(rf"\b{name}\s*=\s*\"\s*([^\"]+)\s*\"", entry, re.I)
    if match:
        return match.group(1).strip()
    return None


def entries_by_key(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    for match in re.finditer(r"(?s)@\w+\{([^,\s]+)\s*,(.*?)(?=\n@|\Z)", text):
        found[match.group(1)] = match.group(2)
    return found


def require_phrases(text: str, phrases: list[str], label: str) -> None:
    lowered = " ".join(text.lower().split())
    missing = [p for p in phrases if p.lower() not in lowered]
    if missing:
        fail(f"{label} missing required phrases: {missing}")


def main() -> None:
    main_tex = read(MAIN)
    bib = read(BIB)
    related = read(RELATED)
    novelty = read(NOVELTY)

    if r"\bibliography{related_work}" not in main_tex:
        fail("main.tex must load related_work.bib")
    if re.search(r"\\bibliography\{[^}]*references", main_tex):
        fail("main.tex must not load references.bib together with related_work.bib")
    if r"\nocite{" in main_tex:
        fail("main.tex must not \\nocite unrun systems as a substitute for discussion")

    keys = bib_keys(bib)
    if len(keys) != len(set(keys)):
        dup = sorted({k for k in keys if keys.count(k) > 1})
        fail(f"duplicate bibliography keys: {dup}")
    if REFERENCES.is_file():
        inherited = set(bib_keys(read(REFERENCES)))
        missing_inherited = sorted(inherited - set(keys))
        if missing_inherited:
            fail(f"related_work.bib dropped inherited keys: {missing_inherited}")

    cited = cite_keys(main_tex)
    unresolved = sorted(cited - set(keys))
    if unresolved:
        fail(f"unresolved citation keys: {unresolved}")
    unused_required = {
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
    missing_cites = sorted(unused_required - cited)
    if missing_cites:
        fail(f"required primary sources not cited in main.tex: {missing_cites}")

    if r"\section{Related work}" not in main_tex and r"\section{Related Work}" not in main_tex:
        fail("main.tex is missing a Related work section")
    if r"\label{sec:related}" not in main_tex:
        fail("main.tex is missing sec:related")

    require_phrases(
        main_tex,
        [
            "No cited external system was executed as a scored arm",
            "Neither system was benchmarked here",
            "They were not run here",
            "not a claim that every cited system was benchmarked",
            "Legal IR is a lossy model",
            "Default \\texttt{OFF}",
            "not superiority",
            "ENFORCE",
            "AgentSpec",
            "Progent",
            "CaMeL",
        ],
        "main.tex",
    )
    forbidden = [
        "first neuro-symbolic MCP",
        "state of the art",
        "SOTA",
        "we introduce the first agent runtime",
        "superior to Catala",
    ]
    lowered_tex = main_tex.lower()
    for phrase in forbidden:
        if phrase.lower() in lowered_tex:
            fail(f"unsupported novelty/superiority phrasing in main.tex: {phrase}")

    require_phrases(
        related,
        [
            "Benchmarked here?",
            "Implementable baseline rationale",
            "A0 unguarded sandbox",
            "A3 lightweight policy+UCAN",
            "A4 full enforcement",
            "primary source",
            "not a scored bake-off",
            "10.1145/3649835",
            "10.1145/1111596.1111601",
        ],
        "related_work.md",
    )
    if "cell is **No**" not in related:
        fail("related_work.md must mark every external system as not benchmarked")

    require_phrases(
        novelty,
        [
            "Modeling assumptions",
            "Trust and deployment assumptions",
            "Legal IR is a model, not the law",
            "bounded test of runtime checking",
            "not a first-of-kind claim",
            "SupervisorPreInvocationEnforcement.authorize_and_delegate",
            "InMemoryCapabilityConsumptionStore",
        ],
        "novelty_statement.md",
    )

    by_key = entries_by_key(bib)
    cedar_doi = field(by_key.get("cutler2024cedar", ""), "doi")
    if cedar_doi != "10.1145/3649835":
        fail(f"Cedar DOI must be 10.1145/3649835, found {cedar_doi}")
    cedar_eprint = field(by_key.get("cutler2024cedar", ""), "eprint")
    if cedar_eprint != "2403.04651":
        fail(f"Cedar eprint must be 2403.04651, found {cedar_eprint}")
    hamlen_doi = field(by_key.get("hamlen2006enforcement", ""), "doi")
    if hamlen_doi != "10.1145/1111596.1111601":
        fail(f"Hamlen DOI must be 10.1145/1111596.1111601, found {hamlen_doi}")
    if re.search(r"doi\s*=\s*\{10\.34727/2024/isbn\.978-3-85448-065-5_27\}", bib):
        fail("bibliography still uses the false Clover FMCAD DOI as an identifier")
    clover_doi = field(by_key.get("sun2024clover", ""), "doi")
    if clover_doi:
        fail(f"Clover must not carry a DOI after the false FMCAD identifier was removed, found {clover_doi}")

    bbl_path = COMPILED_BBL if COMPILED_BBL.is_file() else SNAPSHOT_BBL
    log_path = COMPILED_LOG if COMPILED_LOG.is_file() else SNAPSHOT_LOG
    if bbl_path.is_file() and not read(bbl_path).strip():
        fail("compiled main.bbl is empty")
    if log_path.is_file():
        log = read(log_path)
        if "There were undefined citations" in log or "Citation" in log and "undefined" in log.lower():
            undefined = [line.strip() for line in log.splitlines() if "undefined" in line.lower() and "cit" in line.lower()]
            if undefined:
                fail("undefined citations in compilation log: " + "; ".join(undefined[:8]))
        if "Error:" in log or "Fatal error" in log:
            fail("LaTeX compilation log contains errors")

    compiled_text = None
    if COMPILED_TXT.is_file():
        compiled_text = read(COMPILED_TXT)
    elif COMPILED_PDF.is_file():
        pdftotext = shutil.which("pdftotext")
        if pdftotext:
            compiled_text = subprocess.check_output(
                [pdftotext, "-layout", str(COMPILED_PDF), "-"],
                text=True,
                stderr=subprocess.STDOUT,
            )
    if compiled_text is None:
        fail("missing compiled main.txt extract and no pdftotext-able PDF")
    collapsed = " ".join(compiled_text.split())
    require_phrases(
        collapsed,
        [
            "Related work",
            "AgentSpec",
            "Progent",
            "CaMeL",
            "scored arm",
        ],
        "compiled PDF text",
    )
    if re.search(r"first neuro-symbolic MCP", collapsed, re.I):
        fail("compiled PDF contains unsupported first-system claim")
    pdfinfo = {
        "text_sha256": hashlib.sha256(compiled_text.encode("utf-8")).hexdigest(),
        "text_bytes": len(compiled_text.encode("utf-8")),
        "bbl_present": bbl_path.is_file(),
        "log_present": log_path.is_file(),
        "source": str(COMPILED_TXT.relative_to(ROOT)) if COMPILED_TXT.is_file() else str(COMPILED_PDF),
    }

    report = {
        "schema": "paper-la021-related-work-validation/v1",
        "status": "pass",
        "bibliography_keys": len(keys),
        "cited_keys": sorted(cited),
        "inherited_keys_retained": True,
        "related_work_section": True,
        "nocite_absent": True,
        "selected_bibliography": "related_work",
        "cedar_doi": cedar_doi,
        "hamlen_doi": hamlen_doi,
        "compiled_pdf": pdfinfo,
        "not_a_bakeoff": True,
        "path": os.environ.get("PATH"),
        "python": sys.executable,
    }
    json.dump(report, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    print("LA-021 related-work validation: PASS", file=sys.stderr)


if __name__ == "__main__":
    main()
