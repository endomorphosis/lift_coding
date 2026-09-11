#!/usr/bin/env python3.12
"""LA-021 structural citation, novelty, and bibliography check.

Runs under the authoritative validation interpreter and PATH. It does not
execute TeX, fetch the network, or claim that listed systems were benchmarked.
pdflatex/latexmk/bibtex are treated as a sealed-PATH capability gap.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

def repository_root() -> Path:
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        paper = parent / "papers" / "completion" / "law_to_action"
        if (paper / "manuscript" / "main.tex").is_file():
            return parent
    raise SystemExit("FAIL: cannot locate repository root from citation_check.py")


ROOT = repository_root()
PAPER = ROOT / "papers" / "completion" / "law_to_action"
TEX = PAPER / "manuscript" / "main.tex"
BIB = PAPER / "manuscript" / "related_work.bib"
RELATED = PAPER / "related_work.md"
NOVELTY = PAPER / "novelty_statement.md"
INHERITED = (
    "mcp",
    "mcp-auth",
    "catala",
    "cvefixes",
    "quack",
    "ipfs",
    "libp2p",
    "ucan",
)
REQUIRED_CITES = (
    "saltzer1975protection",
    "necula1997pcc",
    "appel1999pca",
    "schneider2000enforceable",
    "catala",
    "cvefixes",
    "cutler2024cedar",
    "debenedetti2024agentdojo",
    "debenedetti2025camel",
    "wang2025agentspec",
    "shi2025progent",
    "vericode2026cfp",
    "mcp",
    "mcp-auth",
    "ucan",
)
BIB_KEY_RE = re.compile(r"^@\w+\{([^,]+),", re.MULTILINE)
CITE_RE = re.compile(r"\\(?:cite|citep|citet|nocite)\{([^}]+)\}")
DOI_RE = re.compile(r"doi\s*=\s*\{([^}]+)\}", re.IGNORECASE)
EPRINT_RE = re.compile(r"eprint\s*=\s*\{([^}]+)\}", re.IGNORECASE)


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(path: Path) -> str:
    if not path.is_file():
        fail(f"missing file {path}")
    return path.read_text(encoding="utf-8")


def bib_entries(text: str) -> dict[str, str]:
    keys = BIB_KEY_RE.findall(text)
    if len(keys) != len(set(keys)):
        dupes = sorted({k for k in keys if keys.count(k) > 1})
        fail(f"duplicate bibliography keys: {dupes}")
    entries: dict[str, str] = {}
    parts = re.split(r"(?=@\w+\{)", text)
    for part in parts:
        match = BIB_KEY_RE.match(part)
        if match:
            entries[match.group(1)] = part
    return entries


def cited_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    for group in CITE_RE.findall(tex):
        for key in group.split(","):
            key = key.strip()
            if key:
                keys.add(key)
    return keys


def require_contains(text: str, needles, label: str) -> None:
    lowered = re.sub(r"\s+", " ", text.lower())
    for needle in needles:
        if needle.lower() not in lowered:
            fail(f"{label} missing required text: {needle}")


def entry_field(entry: str, pattern: re.Pattern[str]) -> str | None:
    match = pattern.search(entry)
    return match.group(1) if match else None


def resolve_on_path(name: str) -> str | None:
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if not directory:
            continue
        candidate = Path(directory) / name
        try:
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
        except OSError:
            continue
    return None


def report_sealed_path() -> None:
    print(f"PATH={os.environ.get('PATH', '')}")
    print(f"python={sys.executable}")
    for tool in ("pdflatex", "latexmk", "bibtex"):
        located = resolve_on_path(tool)
        if located:
            print(f"note: {tool} present at {located}; not invoked")
        else:
            print(f"capability_gap: {tool} absent from PATH")


def main() -> int:
    report_sealed_path()
    tex = load(TEX)
    bib = load(BIB)
    related = load(RELATED)
    novelty = load(NOVELTY)
    entries = bib_entries(bib)
    cites = cited_keys(tex)

    if r"\bibliography{related_work}" not in tex:
        fail("main.tex must load bibliography{related_work}")
    if re.search(r"\\bibliography\{references\}", tex):
        fail("main.tex must not load references.bib (duplicate inherited keys)")
    if re.search(r"\\nocite\{", tex):
        fail("main.tex must not nocite unrun systems as a substitute for discussion")
    if r"\section{Related work}" not in tex and r"\section{Related Work}" not in tex:
        fail("main.tex missing Related work section")
    if r"\label{sec:related}" not in tex:
        fail("main.tex missing sec:related label")

    missing_inherited = [k for k in INHERITED if k not in entries]
    if missing_inherited:
        fail(f"related_work.bib missing inherited keys: {missing_inherited}")

    unresolved = sorted(cites - set(entries))
    if unresolved:
        fail(f"unresolved citation keys: {unresolved}")
    unused_required = [k for k in REQUIRED_CITES if k not in cites]
    if unused_required:
        fail(f"required primary sources not cited in main.tex: {unused_required}")

    cedar = entries["cutler2024cedar"]
    if "10.1145/3649835" not in cedar:
        fail("Cedar DOI must be Crossref 10.1145/3649835")
    if "10.1145/3649817" in cedar or "2403.04623" in cedar:
        fail("Cedar entry still names Cocoon DOI or unrelated arXiv 2403.04623")
    if "2403.04651" not in cedar:
        fail("Cedar eprint must be arXiv 2403.04651")

    hamlen = entries["hamlen2006enforcement"]
    if "10.1145/1111596.1111601" not in hamlen:
        fail("Hamlen DOI must be Crossref 10.1145/1111596.1111601")
    if "10.1145/1111596.1111603" in hamlen:
        fail("Hamlen entry still uses the non-Crossref DOI suffix 1111603")

    clover = entries["sun2024clover"]
    if "10.1007/978-3-031-65112-0_7" not in clover:
        fail("Clover DOI must be the Springer AI Verification chapter")
    if "10.34727/2024/isbn.978-3-85448-065-5_27" in clover:
        fail("Clover entry still uses the Dureja FMCAD DOI")

    if "2503.18666" not in entries["wang2025agentspec"]:
        fail("AgentSpec eprint 2503.18666 missing")
    if "2504.11703" not in entries["shi2025progent"]:
        fail("Progent eprint 2504.11703 missing")
    if "2503.18813" not in entries["debenedetti2025camel"]:
        fail("CaMeL eprint 2503.18813 missing")

    require_contains(
        tex,
        [
            "not-yet-scored",
            "no cited external system was executed as a scored arm",
            "neither system was benchmarked here",
            "they were not run here",
            "lossy compilation",
            "model-free equivalence controls",
            "authorize",
            "ENFORCE",
            "AgentSpec",
            "Progent",
            "CaMeL",
            "implementation report",
        ],
        "main.tex",
    )
    forbidden = [
        "first neuro-symbolic MCP enforcement",
        "we introduce agent runtime rules",
        "state-of-the-art agent safety",
    ]
    lowered_tex = tex.lower()
    for phrase in forbidden:
        if phrase.lower() in lowered_tex:
            fail(f"main.tex contains unsupported novelty phrasing: {phrase}")

    require_contains(
        related,
        [
            "No system named below was executed as an experimental arm",
            "Benchmarked here?",
            "Assurance boundary",
            "Source fidelity",
            "Generated-code effect observation",
            "Useful-work measurement",
            "wang2025agentspec",
            "shi2025progent",
            "debenedetti2025camel",
            "A0",
            "A3",
            "A4",
            "10.1145/3649835",
            "10.1145/1111596.1111601",
            "10.1007/978-3-031-65112-0_7",
        ],
        "related_work.md",
    )
    if "| No |" not in related and "**No**" not in related:
        fail("related_work.md must mark listed systems as not benchmarked")

    require_contains(
        novelty,
        [
            "modeling assumptions",
            "trust and deployment assumptions",
            "Legal IR is a model, not the law",
            "Security IR is a scoped candidate prohibition",
            "Intent IR is an untrusted procedure description",
            "explicit `ENFORCE`",
            "InMemoryCapabilityConsumptionStore",
            "complete mediation",
            "AgentSpec",
            "Progent",
            "CaMeL",
            "workshop-specific",
            "not a first-of-kind claim",
        ],
        "novelty_statement.md",
    )

    print("LA-021 citation/novelty/bibliography check: PASS")
    print(f"bib_entries={len(entries)} cited_keys={len(cites)} inherited={len(INHERITED)}")
    print("bibliography=related_work; nocite=absent; related-work section=present")
    print("Cedar/Hamlen/Clover DOIs match Crossref-checked identifiers")
    print("AgentSpec/Progent/CaMeL cited; listed systems marked unrun")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
