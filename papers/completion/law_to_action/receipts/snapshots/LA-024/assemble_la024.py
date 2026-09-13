#!/usr/bin/python3.12
"""Assemble the LA-024 anonymous workshop submission package.

Compiles from a snapshot working copy that loads the local unchanged
neurips_2026_vericode.sty in default anonymous mode and includes the
filled per-paper checklist. TinyTeX is an implementation-only toolchain
and is not claimed on the sealed validation PATH.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers/completion/law_to_action").is_dir():
    ROOT = ROOT.parent
PAPER = ROOT / "papers/completion/law_to_action"
MANUSCRIPT = PAPER / "manuscript"
SUBMISSION = PAPER / "submission"
SNAPSHOT = PAPER / "receipts/snapshots/LA-024"
BUILD = SNAPSHOT / "build"
SHARED_STY = ROOT / "papers/neurips_2026_vericode.sty"
SHARED_CHECKLIST = ROOT / "papers/checklist.tex"
SHARED_SHELL = ROOT / "papers/neurips_2026_vericode_workshop.tex"
SHARED_GENERIC = ROOT / "papers/neurips_2026.sty"
SHARED_COMP_STY = ROOT / "papers/neurips_2026_vericode_competition.sty"
SHARED_COMP_TEX = ROOT / "papers/neurips_2026_vericode_workshop_competition.tex"
ARTIFACT_BUNDLE = PAPER / "artifact/anonymous_supplement.zip"
LATEXMK = Path("/home/barberb/.local/bin/vericodegen-latexmk")
PDFTOTEXT = Path("/usr/bin/pdftotext")
PYTHON = Path("/usr/bin/python3.12")

EXPECTED = {
    "papers/neurips_2026_vericode_workshop.tex": "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250",
    "papers/neurips_2026_vericode.sty": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
    "papers/checklist.tex": "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6",
    "papers/neurips_2026.sty": "c3fc2894e83d2517ca18b66741d6c595986d97957dc08ec08bb2125a7ec4555a",
    "papers/neurips_2026_vericode_competition.sty": "a0178f152d13cf24f44936da0ee95bab975ceced8d54980efbbf8f7c1bb31f72",
    "papers/neurips_2026_vericode_workshop_competition.tex": "0e21c08ce8a32cb3d4c0fb7123d38249209c2ef488a0c210acbea026f6fefc23",
}

ALIASES = [
    ("author-maintained legal program", "inspected legal-source program"),
    ("SupervisorPreInvocationEnforcement", "PreInvocationEnforcer"),
    ("BoundedExportHandler", "SandboxExportHandler"),
    ("LegalIRCompilerAPI", "LegalIRCompiler"),
    ("SkillCenterSkillRecord", "SkillRecordAdapter"),
    ("IRConstraintCompiler", "ConstraintCompiler"),
    ("IntentAuthorizationService", "AuthorizationService"),
    ("QuackStateClient", "TypedStateClient"),
    ("adapt\\_\\allowbreak{}cvefixes\\_\\allowbreak{}candidate", "CVEFixesAdapter"),
]

CHECKLIST_ANSWERS = [
    (
        r"\answerYes{}",
        r"The abstract and introduction state the bounded \texttt{ENFORCE} contribution "
        r"(admitted A4 $0/90$ forbidden effects and $90/90$ allowed useful work) and "
        r"explicitly withdraw expert legal fidelity, human agreement, and closed-loop planning.",
    ),
    (
        r"\answerYes{}",
        r"Section~\ref{sec:limits} records Legal/Security/Intent IR as lossy models, complete "
        r"mediation only for one sandbox \texttt{ENFORCE} route, SAT-only authority, withdrawn "
        r"closed-loop planning, and unmeasured expert review.",
    ),
    (
        r"\answerNA{}",
        r"The paper reports an empirical runtime-checking measurement and a qualified "
        r"QF\_BOOL SAT route with satisfiability authority only; it does not state numbered "
        r"theorems with complete proofs.",
    ),
    (
        r"\answerYes{}",
        r"Section~\ref{sec:eval} and the anonymous supplement pin the $30$-family/$60$-case "
        r"protocol, five arms, seeds, implementation revision, Docker image digest, and a "
        r"one-command bounded reproduce path from hashed raw records.",
    ),
    (
        r"\answerYes{}",
        r"The anonymous ZIP includes \texttt{environment.lock}, \texttt{reproduce.sh}, compact "
        r"outcome recipes, and SHA-256 identities; frozen legal/CVE/SkillCenter bodies are "
        r"retrieval-only with URI and hash and are not redistributed.",
    ),
    (
        r"\answerYes{}",
        r"Section~\ref{sec:eval-protocol} specifies lineage splits, seeds, matched arms, the "
        r"selected \texttt{ENFORCE} handler, independent journal counters, and the frozen "
        r"modeled policy; resource and mechanism pins are in the supplement.",
    ),
    (
        r"\answerYes{}",
        r"Section~\ref{sec:eval-admitted} reports Wilson and Clopper--Pearson $95\%$ intervals "
        r"and family-cluster bootstrap intervals for the primary arm contrasts, and states that "
        r"a degenerate zero interval does not prove population-level absence.",
    ),
    (
        r"\answerYes{}",
        r"Section~\ref{sec:eval-admitted} reports $1608.817478$ descendant-inclusive CPU seconds, "
        r"peak cell memory $274812928$ bytes, maximum whole-cell wall $18.022665$\,s, $902$ host "
        r"attempts, and a $1$ CPU / $2$\,GiB Docker recipe; sealed-PATH reproduction does not rerun that matrix.",
    ),
    (
        r"\answerYes{}",
        r"The study uses public legal texts and retrieval-only vulnerability/skill sources, "
        r"involves no human subjects, preserves double-blind anonymity, and does not redistribute "
        r"source bodies or exploit payloads.",
    ),
    (
        r"\answerNo{}",
        r"The paper discusses technical claim limits of runtime enforcement and withdrawn "
        r"legal-fidelity studies, but it does not include a dedicated positive-and-negative "
        r"societal-impact analysis.",
    ),
    (
        r"\answerNA{}",
        r"The submission does not release pretrained generative models, image generators, or "
        r"scraped web-scale datasets; source bodies remain retrieval-only with hashes.",
    ),
    (
        r"\answerYes{}",
        r"Independent sources are cited with pinned revisions; the supplement records GovInfo "
        r"U.S.\ government works, CVEfixes packaging Apache-2.0 with upstream code licenses still "
        r"governing, and SkillCenter packaging MIT that does not grant nested-source rights.",
    ),
    (
        r"\answerYes{}",
        r"The anonymous ZIP documents the harness, environment lock, outcome recipe, "
        r"measurement-integrity tests, and retrieval instructions; no author-maintained "
        r"repository URL is linked.",
    ),
    (
        r"\answerNA{}",
        r"The amended study collected no crowdsourcing and no research with human subjects; "
        r"expert review was not obtained and those claims were withdrawn.",
    ),
    (
        r"\answerNA{}",
        r"No human-subjects protocol was conducted, so no IRB or equivalent review was "
        r"required or obtained.",
    ),
    (
        r"\answerNA{}",
        r"LLMs are not an important, original, or non-standard component of the scored "
        r"\texttt{ENFORCE} method; writing/inspection assistants and the withdrawn closed-loop "
        r"model study are disclosed separately, and the admitted matrix executed $0$ model calls.",
    ),
]

DISCLOSURE_OLD = (
    "This draft was prepared using language-model assistance for source inspection, "
    "organization, and writing. Manuscript generation and the evidence-scoped submission "
    "candidate require no outside review. Optional author review is labeled non-independent "
    "and is not a prerequisite. No independent human legal, security, or intent validation "
    "and no inter-annotator agreement study was collected. Exact tools, model versions, and "
    "executed experiments for camera-ready disclosure remain an LA-024 obligation; the "
    "scientific claims above are bound to the retained receipts cited in the claim--evidence matrix."
)

DISCLOSURE_NEW = (
    "This draft was prepared using language-model assistance for source inspection, "
    "organization, and writing. The writing assistants were Grok \\texttt{grok-4.6} (xAI) as "
    "the primary drafting model and, when used, Codex \\texttt{gpt-5.6-terra} as a documented "
    "fallback; neither is a scored experimental arm. The admitted study executed $0$ scientific "
    "model calls. Arms A1 and A2 are model-free prompt/retrieval labels, not LLM efficacy. "
    "Closed-loop generated-code planning was withdrawn unrun. No independent human legal, "
    "security, or intent validation and no inter-annotator agreement study was collected. "
    "Optional author review is labeled non-independent, was not a prerequisite, and is not "
    "recorded as completed for this package. Executed experiments are the retained LA-029 "
    "admitted matrix, LA-009 source-contract measurements, and the qualification and diagnostic "
    "records cited in the claim--evidence matrix."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fail(message: str) -> None:
    raise SystemExit("LA-024 assemble failed: " + message)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verify_shared_inputs() -> dict[str, dict[str, object]]:
    recorded: dict[str, dict[str, object]] = {}
    for rel, expected in EXPECTED.items():
        path = ROOT / rel
        if not path.is_file():
            fail(f"missing shared input {rel}")
        digest = sha256_file(path)
        if digest != expected:
            fail(f"shared input changed: {rel} {digest} != {expected}")
        recorded[rel] = {"sha256": digest, "bytes": path.stat().st_size, "unchanged": True}
    return recorded


def make_checklist(source: str) -> str:
    text, n = re.subn(
        r"%%% BEGIN INSTRUCTIONS %%%.*?%%% END INSTRUCTIONS %%%\s*",
        "",
        source,
        count=1,
        flags=re.S,
    )
    if n != 1:
        fail("failed to remove the official instruction block once")
    if "BEGIN INSTRUCTIONS" in text or "END INSTRUCTIONS" in text:
        fail("instruction block remnants remain")
    if text.count(r"\answerTODO{}") != 16 or text.count(r"\justificationTODO{}") != 16:
        fail("expected 16 answerTODO and 16 justificationTODO fields")
    for answer, justification in CHECKLIST_ANSWERS:
        text = text.replace(r"\answerTODO{}", answer, 1)
        text = text.replace(r"\justificationTODO{}", justification, 1)
    if r"\answerTODO" in text or r"\justificationTODO" in text:
        fail("unreplaced checklist TODO fields remain")
    if r"\answerYes{}" not in text:
        fail("checklist is missing Yes answers")
    questions = re.findall(r"Question:", text)
    if len(questions) != 16:
        fail(f"expected 16 official questions, found {len(questions)}")
    if "NeurIPS Paper Checklist" not in text:
        fail("checklist heading missing")
    if "Guidelines:" not in text:
        fail("checklist guidelines missing")
    return text


def patch_main(source: str) -> str:
    text = source
    old_load = (
        "\\makeatletter\n"
        "\\def\\input@path{{../../../}}\n"
        "\\makeatother\n"
        "\\usepackage{neurips_2026_vericode}\n"
    )
    new_load = "\\usepackage{neurips_2026_vericode}\n"
    if old_load not in text:
        fail("expected local-path sty load block was not found in main.tex")
    text = text.replace(old_load, new_load, 1)
    if re.search(r"\\usepackage\[[^\]]*\]\{neurips_2026", text):
        fail("style package was loaded with options")
    if r"\usepackage{neurips_2026_vericode}" not in text:
        fail("anonymous default usepackage missing")
    if "neurips_2026_vericode_competition" in text or r"{neurips_2026}" in text:
        fail("competition or generic style substitution present")
    if DISCLOSURE_OLD not in text:
        fail("expected LA-022 disclosure paragraph was not found")
    text = text.replace(DISCLOSURE_OLD, DISCLOSURE_NEW, 1)
    if "LA-024 obligation" in text:
        fail("unresolved LA-024 disclosure obligation remains")
    for old, new in ALIASES:
        text = text.replace(old, new)
    if "author-maintained" in text:
        fail("author-maintained identifying phrase remains")
    if r"\input{checklist" in text:
        fail("checklist was already included; refusing a duplicate include")
    if not text.rstrip().endswith(r"\end{document}"):
        fail("main.tex does not end with \\end{document}")
    text = text.rstrip()[: -len(r"\end{document}")].rstrip() + (
        "\n\n"
        "% Per-paper checklist copy. Official instruction block removed; 16 questions,\n"
        "% guidelines, and Yes/No/N/A answers with 1--2 sentence justifications retained.\n"
        "\\clearpage\n"
        "\\input{checklist.tex}\n"
        "\\end{document}\n"
    )
    header = (
        "% Anonymous workshop submission compiled for LA-024 from the LA-022\n"
        "% evidence-scoped manuscript. Loads the local unchanged\n"
        "% neurips_2026_vericode.sty in default anonymous mode.\n"
    )
    marker = "\\documentclass{article}"
    index = text.find(marker)
    if index < 0:
        fail("patched main.tex is missing \\documentclass{article}")
    text = header + text[index:]
    if text.count(marker) != 1:
        fail("patched main.tex must contain exactly one documentclass")
    return text


def copy_build_inputs(checklist: str, main_tex: str, sty_bytes: bytes) -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    BUILD.mkdir(parents=True, exist_ok=True)
    (BUILD / "neurips_2026_vericode.sty").write_bytes(sty_bytes)
    write_text(BUILD / "checklist.tex", checklist)
    write_text(BUILD / "main.tex", main_tex)
    for name in ("results.tex", "limitations.tex", "related_work.bib"):
        src = MANUSCRIPT / name
        if not src.is_file():
            fail(f"missing manuscript input {name}")
        shutil.copyfile(src, BUILD / name)


def compile_pdf() -> dict[str, object]:
    if not LATEXMK.is_file():
        fail(f"implementation latexmk wrapper missing: {LATEXMK}")
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = "0"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    started = utc_now()
    proc = subprocess.run(
        [
            str(LATEXMK),
            "-g",
            "-pdf",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "-file-line-error",
            "main.tex",
        ],
        cwd=str(BUILD),
        env=env,
        capture_output=True,
        text=True,
    )
    compile_log = SNAPSHOT / "validation/compile.stdout.log"
    compile_err = SNAPSHOT / "validation/compile.stderr.log"
    write_text(compile_log, proc.stdout)
    write_text(compile_err, proc.stderr)
    if proc.returncode != 0:
        fail(f"latexmk exited {proc.returncode}; see {compile_log}")
    pdf = BUILD / "main.pdf"
    log = BUILD / "main.log"
    if not pdf.is_file() or not log.is_file():
        fail("compiled PDF or log missing")
    log_text = log.read_text(encoding="utf-8", errors="replace")
    if "(./neurips_2026_vericode.sty" not in log_text:
        fail("build did not load the local neurips_2026_vericode.sty")
    if "../../../neurips_2026_vericode" in log_text:
        fail("build still resolved the shared-root style via input@path")
    if "neurips_2026_vericode_competition" in log_text or "neurips_2026.sty" in log_text:
        fail("competition or generic style appeared in the build log")
    if "Package: neurips_2026_vericode 2026-01-29" not in log_text:
        fail("official style identity missing from the log")
    if "lineno.sty" not in log_text:
        fail("review line numbers were not loaded")
    if not PDFTOTEXT.is_file():
        fail("pdftotext missing")
    txt = SNAPSHOT / "compiled/main.txt"
    txt.parent.mkdir(parents=True, exist_ok=True)
    extract = subprocess.run(
        [str(PDFTOTEXT), "-layout", str(pdf), str(txt)],
        capture_output=True,
        text=True,
    )
    if extract.returncode != 0:
        fail(f"pdftotext exited {extract.returncode}: {extract.stderr}")
    pages = count_pages(txt.read_text(encoding="utf-8", errors="replace"))
    shutil.copyfile(pdf, SNAPSHOT / "compiled/main.pdf")
    shutil.copyfile(log, SNAPSHOT / "compiled/main.log")
    return {
        "started_at": started,
        "completed_at": utc_now(),
        "exit_code": proc.returncode,
        "pdf_bytes": pdf.stat().st_size,
        "pdf_sha256": sha256_file(pdf),
        **pages,
        "log": str(compile_log.relative_to(ROOT)),
    }


def count_pages(text: str) -> dict[str, object]:
    raw_pages = text.split("\f")
    pages = [p for p in raw_pages if p.strip()]
    if not pages:
        fail("pdftotext produced no pages")
    references_page = None
    appendix_page = None
    checklist_page = None
    for index, page in enumerate(pages, start=1):
        if references_page is None and re.search(r"(?m)^\s*(?:\d{1,4}\s+)?References\s*$", page):
            references_page = index
        if appendix_page is None and re.search(r"(?im)^\s*(?:\d{1,4}\s+)?A\s+Corpus lineage", page):
            appendix_page = index
        if checklist_page is None and "NeurIPS Paper Checklist" in page:
            checklist_page = index
    if references_page is None:
        fail("compiled PDF has no References heading page")
    main_text_pages = references_page - 1
    if not (4 <= main_text_pages <= 9):
        fail(f"main-text page count {main_text_pages} is outside 4-9")
    if checklist_page is None:
        fail("compiled PDF is missing the NeurIPS Paper Checklist")
    blob = "\n".join(pages)
    if "Anonymous Author(s)" not in blob:
        fail("anonymous author line missing")
    if not re.search(r"(?m)^\s*Affiliation\s*$", blob):
        fail("official style Affiliation line missing")
    if not re.search(r"(?m)^\s*Address\s*$", blob):
        fail("official style Address line missing")
    if not re.search(r"(?m)^\s*email\s*$", blob):
        fail("official style email line missing")
    if "Submitted to NeurIPS 2026 Workshop on AI for Verifiable Coding" not in blob:
        fail("workshop submission footer missing")
    if "Do not distribute" not in blob:
        fail("review-time do-not-distribute notice missing")
    if "[TODO]" in blob or "answerTODO" in blob or "justificationTODO" in blob:
        fail("TODO checklist answers remain in the PDF")
    if "LA-024 obligation" in blob:
        fail("unresolved disclosure obligation remains in the PDF")
    return {
        "pdf_pages": len(pages),
        "main_text_pages": main_text_pages,
        "references_start_page": references_page,
        "appendices_start_page": appendix_page,
        "checklist_start_page": checklist_page,
    }


def pack_zip() -> dict[str, object]:
    if not ARTIFACT_BUNDLE.is_dir():
        fail("LA-023 anonymous supplement directory bundle is missing")
    zip_path = SUBMISSION / "anonymous_supplement.zip"
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    prefix = "law_to_action_anonymous_supplement/"
    members: list[str] = []
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ARTIFACT_BUNDLE.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ARTIFACT_BUNDLE).as_posix()
            name = prefix + rel
            data = path.read_bytes()
            lowered = data.lower()
            is_checker = path.name == "check_artifact.py"
            if not is_checker:
                if b"barberb" in lowered or b"overleaf.com/project" in lowered:
                    fail(f"supplement member identifies an author artifact: {rel}")
                if b"begin openssh" in lowered or b"akia" in lowered:
                    fail(f"supplement member looks like a credential: {rel}")
            zf.writestr(name, data)
            members.append(name)
    raw = zip_path.read_bytes()
    private = PAPER / "private/source_provenance.json"
    if private.is_file() and private.read_bytes() in raw:
        fail("private author companion was packed")
    snapshot_zip = SNAPSHOT / "outputs/anonymous_supplement.zip"
    snapshot_zip.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(zip_path, snapshot_zip)
    return {
        "path": str(zip_path.relative_to(ROOT)),
        "bytes": zip_path.stat().st_size,
        "sha256": sha256_file(zip_path),
        "members": members,
        "member_count": len(members),
    }


def write_markdown_outputs(pages: dict[str, object], zip_info: dict[str, object], shared: dict[str, dict[str, object]], cfp: dict[str, object]) -> None:
    disclosure = f"""# LLM, tool, and human-judgment disclosure (LA-024)

Paper: From Law to Action: Neuro-Symbolic Runtime Enforcement for MCP Agents.
Track: NeurIPS 2026 Workshop on AI for Verifiable Coding (research, double-blind).
Recorded: {utc_now()}.

## Methodology-essential tools in the scored study

The scored method is pre-invocation runtime checking of a sandbox handler effect.
It does **not** use a language model as an important, original, or non-standard
component of that method.

| Tool | Version / pin | Role in scored method |
| --- | --- | --- |
| QF_BOOL SAT provider | SymPy 1.12 DPLL child process | Satisfiability authority only |
| Independent checker | Exhaustive truth table | Agrees with SAT/UNSAT; not a kernel theorem |
| Capability check | Real Ed25519 UCAN verification | A3/A4 grant check |
| Durable consumption | File-backed DuckDB typed Quack owner | A4 only |
| Effect observation | Independent filesystem journal | Forbidden-effect and useful-work counters |
| Scientific model calls | 0 | Closed-loop generated-code planning withdrawn |

Implementation revision of the admitted matrix:
`ee6d73c4a5fc30d05ec4e787fdeb46d6701a4f947b7c874aecabf603e31ce06c`.
Docker image used only for the operator matrix (absent from the sealed PATH):
`sha256:74c4a6ff67f397f8a10b058851d218896b2f1ee0f2cddf47741219b734de93a6`.

Arms A1 and A2 are model-free prompt-text and retrieval-context labels. They are
instrumentation/equivalence controls, not LLM efficacy.

## Language-model use that is not a scored arm

Manuscript generation used language-model assistance for source inspection,
organization, and writing.

| Assistant | Identifier | Use |
| --- | --- | --- |
| Grok | `grok-4.6` (xAI) | Primary drafting / inspection assistant |
| Codex | `gpt-5.6-terra` | Documented fallback; not a scored experimental arm |

No other methodology-essential LLM is claimed. These assistants are not baselines,
not generators of expert legal labels, and not the A4 enforcement mechanism.

## Remaining human judgments

| Judgment | Status |
| --- | --- |
| Independent human legal / security / intent validation | Not collected; claims withdrawn |
| Inter-annotator agreement | Not collected; unmeasured |
| Expert legal fidelity / legal-validity rates | Unmeasured; not filled from compiler agreement |
| Frozen allowed/forbidden labels | Machine-checkable modeled policy, not expert legality |
| Optional author review | Non-independent; not a prerequisite; not recorded as completed |
| Outside reviewers | Not available and not required for this amended study |

Packet-preparer field extraction and shared-producer schema checks are not
independent human review.

## Official anonymous author block

The official style in default anonymous mode prints `Anonymous Author(s)`,
`Affiliation`, `Address`, and `email`. Those strings are retained. They are
style-generated anonymous text, not unanswered scientific fields.

This file is part of the anonymous package and contains no author names,
affiliations, or author-maintained repository URLs.
"""
    write_text(SUBMISSION / "disclosure.md", disclosure)

    compliance = f"""# LA-024 workshop compliance audit

Recorded: {utc_now()}.
Live CFP retrieved {cfp['retrieved_at']} from {cfp['url']} (SHA-256 `{cfp['sha256']}`).

## 1. Page count and size

- Compiled PDF pages: {pages['pdf_pages']}
- Main-text pages excluding references/appendices/checklist: {pages['main_text_pages']} (required 4--9)
- References start page: {pages['references_start_page']}
- Appendices start page: {pages['appendices_start_page']}
- Checklist start page: {pages['checklist_start_page']}
- PDF bytes: {pages['pdf_bytes']} (limit 50 MB)
- Supplementary ZIP bytes: {zip_info['bytes']} (limit 100 MB)

Main results supporting the ENFORCE claim remain in the main text
(Section Evaluation / Table 3), not only in the appendix.

## 2. Anonymity of the package

The anonymous ZIP is packed from the LA-023 directory bundle with prefix
`law_to_action_anonymous_supplement/`. It contains no Overleaf project URL, no
operator home path, no private `source_provenance.json`, and no credentials.
Legitimate independent-source URIs (GovInfo; Hugging Face pins for CVEfixes and
SkillCenter) are retained.

Neutral aliases used in the compiled PDF have a separate private mapping at
`papers/completion/law_to_action/receipts/snapshots/LA-024/private/alias_map.json`.
That mapping is excluded from the anonymous ZIP.

## 3. LLM and human-judgment disclosure

See `disclosure.md` and the final disclosure section of the PDF. Writing
assistants are named. The scored study executed 0 model calls. Remaining human
judgments are recorded as not collected. The official style-generated Anonymous Author(s) /
Affiliation/Address/email block is retained.

## 4. CFP dates and template version

| Item | Live CFP 2026-09-13 | Prior records |
| --- | --- | --- |
| Abstract deadline | 11 September 2026 AoE | review.md 2026-09-11 |
| Paper deadline | September 13, 2026 AoE | related_work.bib 2026-09-12 |
| Review deadline | 27 September 2026 | (live page; not previously required) |
| Notification | 29 September 2026 | (live page) |
| Camera-ready | 14 October 2026 | review.md 2026-09-11 |
| Workshop | 12 December 2026, Atlanta | related_work.bib 2026-09-12 |
| Template | `neurips_2026_vericode_workshop.tex` + `neurips_2026_vericode.sty` dated 2026-01-29 | local research inputs |
| Main text | 4--9 pages excluding references/appendices | same |
| PDF / ZIP limits | 50 MB / 100 MB | same |
| Reviewing | double-blind including linked artifacts | same |
| LLM policy | methodology-essential tools must be described | same |
| Archival | non-archival | same |

This task prepares an anonymous submission candidate. It does not submit,
upload, or impersonate authors.

## 5. Style load and forbidden substitutions

The build working copy uses `\\usepackage{{neurips_2026_vericode}}` with no
options and loads `./neurips_2026_vericode.sty` from the manuscript/build
directory. The local copy is byte-identical to
`papers/neurips_2026_vericode.sty` (`{EXPECTED['papers/neurips_2026_vericode.sty']}`).

Absent from the build: `final`, `preprint`, `nonanonymous`, `sglblindworkshop`,
`dblblindworkshop` as a substitute, `neurips_2026.sty`, and the competition
shell/style.

## 6. Checklist

`papers/completion/law_to_action/manuscript/checklist.tex` is a per-paper copy
of the official 16-question checklist. Only the official instruction block
(BEGIN/END INSTRUCTIONS) is removed. Heading, questions, subheadings, and
guidelines are preserved. All 16
`\\answerTODO{{}}` / `\\justificationTODO{{}}` fields are replaced with actual
Yes/No/N/A macros and 1--2 sentence evidence-backed justifications. The copy is
`\\input` after references and appendices.

## 7. Shared templates unmodified

| Input | SHA-256 | Status |
| --- | --- | --- |
| papers/neurips_2026_vericode_workshop.tex | `{EXPECTED['papers/neurips_2026_vericode_workshop.tex']}` | unchanged |
| papers/neurips_2026_vericode.sty | `{EXPECTED['papers/neurips_2026_vericode.sty']}` | unchanged; copied locally |
| papers/checklist.tex | `{EXPECTED['papers/checklist.tex']}` | unchanged; per-paper copy filled separately |

The official anonymous author block may retain Affiliation/Address/email.

## 8. Footer, line numbers, placeholder policy

Default anonymous mode prints the workshop footer (``Submitted to NeurIPS 2026
Workshop on AI for Verifiable Coding. Do not distribute.''), hides
acknowledgments, and loads `lineno`. Placeholder scans treat the official
Affiliation/Address/email strings as style-generated anonymous text. Unanswered
scientific fields (`answerTODO`, `justificationTODO`, `LA-024 obligation`,
result TBD) remain failures and are absent from this build.

This audit is packaging compliance evidence, not independent scientific peer
review and not a workshop acceptance.
"""
    write_text(SUBMISSION / "compliance_audit.md", compliance)

    template_inputs = {
        "schema": "vericodegen-template-inputs/v1",
        "paper_id": "law_to_action",
        "task_id": "LA-024",
        "recorded_at": utc_now(),
        "cfp": cfp,
        "shared_inputs": shared,
        "local_copies": {
            "papers/completion/law_to_action/manuscript/neurips_2026_vericode.sty": {
                "source": "papers/neurips_2026_vericode.sty",
                "sha256": EXPECTED["papers/neurips_2026_vericode.sty"],
                "bytes_identical_to_source": True,
            },
            "papers/completion/law_to_action/manuscript/checklist.tex": {
                "source": "papers/checklist.tex",
                "instruction_block_removed": True,
                "questions_preserved": 16,
                "answerTODO_remaining": 0,
                "justificationTODO_remaining": 0,
            },
        },
        "build": {
            "usepackage": "\\usepackage{neurips_2026_vericode}",
            "options": [],
            "anonymous_default": True,
            "line_numbers": True,
            "acknowledgments_hidden": True,
            "workshop_footer": "Submitted to NeurIPS 2026 Workshop on AI for Verifiable Coding. Do not distribute.",
            "style_provides": "neurips_2026_vericode 2026-01-29",
            "official_anonymous_block": [
                "Anonymous Author(s)",
                "Affiliation",
                "Address",
                "email",
            ],
            "absent_substitutions": [
                "final",
                "preprint",
                "nonanonymous",
                "sglblindworkshop",
                "competition style/shell",
                "papers/neurips_2026.sty",
            ],
            "placeholder_policy": "Official style-generated Affiliation/Address/email are exempt; unanswered scientific and checklist fields are failures.",
        },
        "compiled": {
            "main_text_pages": pages["main_text_pages"],
            "pdf_pages": pages["pdf_pages"],
            "pdf_bytes": pages["pdf_bytes"],
            "pdf_sha256": pages["pdf_sha256"],
            "zip_bytes": zip_info["bytes"],
            "zip_sha256": zip_info["sha256"],
        },
    }
    write_json(SUBMISSION / "template_inputs.json", template_inputs)


def write_private_alias_map() -> None:
    mapping = {
        "schema": "law-to-action-private-alias-map/v1",
        "classification": "private author companion; exclude from anonymous public bundles",
        "task_id": "LA-024",
        "recorded_at": utc_now(),
        "note": "Anonymous PDF uses the public alias. Camera-ready restoration uses the author-maintained symbol.",
        "aliases": [
            {
                "anonymous": new,
                "author_maintained": old.replace(r"\_", "_").replace(r"\allowbreak{}", ""),
            }
            for old, new in ALIASES
        ],
        "retained_independent_sources": [
            "hitoshura25/cvefixes@d4f5c4ea65329d9ccbb8a3b3149e5d06eda5edb2",
            "Tommysha/skillcenter-bundles@f9dd4fec3c86d85ebf116c7408ac5ce602c418a1",
            "GovInfo USCODE-2024 section PDFs",
        ],
        "excluded_from_anonymous_package": [
            "papers/completion/law_to_action/private/source_provenance.json",
            "https://www.overleaf.com/project/6a7b4742e20ac910c422a7e0",
            "operator home paths",
        ],
    }
    write_json(SNAPSHOT / "private/alias_map.json", mapping)


def load_cfp() -> dict[str, object]:
    path = SNAPSHOT / "cfp.html"
    if not path.is_file():
        fail("live CFP snapshot missing")
    html = path.read_text(encoding="utf-8", errors="replace")
    required = [
        "Abstract Submission Deadline: September 11, 2026",
        "Paper Submission Deadline: September 13, 2026",
        "Camera-Ready Submission: October 14, 2026",
        "Workshop Date: December 12 (Atlanta)",
        "at least 4 pages long and no more than 9 pages",
        "neurips_2026_vericode_workshop.tex",
        "neurips_2026_vericode.sty",
        "50MB",
        "100MB",
        "anonymized",
        "use of LLMs",
        "non-archival",
    ]
    missing = [item for item in required if item not in html]
    if missing:
        fail(f"live CFP is missing expected statements: {missing}")
    return {
        "url": "https://vericodegen.github.io/cfp.html",
        "retrieved_at": "2026-09-13",
        "http_status": 200,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "title": "Call for Papers — VeriCodeGen: AI for Verifiable Coding at NeurIPS 2026",
        "abstract_deadline": "2026-09-11 AoE",
        "paper_deadline": "2026-09-13 AoE",
        "review_deadline": "2026-09-27",
        "notification": "2026-09-29",
        "camera_ready": "2026-10-14",
        "workshop": "2026-12-12 Atlanta",
        "main_text_pages": "4-9 excluding references and appendices",
        "pdf_max_mb": 50,
        "supplement_max_mb": 100,
        "template": "neurips_2026_vericode_workshop.tex + neurips_2026_vericode.sty (2026-01-29)",
        "double_blind": True,
        "llm_disclosure_required": True,
        "non_archival": True,
        "prior_checks": [
            "papers/completion/README.md and review.md on 2026-09-11",
            "related_work.bib live-page retrieval on 2026-09-12",
            "this task re-fetched the live page on 2026-09-13",
        ],
        "dates_unchanged_versus_2026-09-11_review": True,
    }


def copy_outputs(checklist: str, sty_bytes: bytes, pages: dict[str, object]) -> None:
    MANUSCRIPT.mkdir(parents=True, exist_ok=True)
    SUBMISSION.mkdir(parents=True, exist_ok=True)
    (MANUSCRIPT / "neurips_2026_vericode.sty").write_bytes(sty_bytes)
    write_text(MANUSCRIPT / "checklist.tex", checklist)
    pdf_src = BUILD / "main.pdf"
    pdf_dst = SUBMISSION / "paper.pdf"
    shutil.copyfile(pdf_src, pdf_dst)
    out_pdf = SNAPSHOT / "outputs/paper.pdf"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(pdf_src, out_pdf)
    shutil.copyfile(MANUSCRIPT / "checklist.tex", SNAPSHOT / "outputs/checklist.tex")
    shutil.copyfile(MANUSCRIPT / "neurips_2026_vericode.sty", SNAPSHOT / "outputs/neurips_2026_vericode.sty")
    shutil.copyfile(SUBMISSION / "disclosure.md", SNAPSHOT / "outputs/disclosure.md")
    shutil.copyfile(SUBMISSION / "compliance_audit.md", SNAPSHOT / "outputs/compliance_audit.md")
    shutil.copyfile(SUBMISSION / "template_inputs.json", SNAPSHOT / "outputs/template_inputs.json")
    write_json(
        SNAPSHOT / "compiled/pdf_digest.json",
        {
            "schema": "paper-la024-compiled-pdf-digest/v1",
            "compiled_at": utc_now(),
            "pdf": "papers/completion/law_to_action/submission/paper.pdf",
            "pdf_sha256": pages["pdf_sha256"],
            "pdf_bytes": pages["pdf_bytes"],
            "pdf_pages": pages["pdf_pages"],
            "main_text_pages": pages["main_text_pages"],
            "references_start_page": pages["references_start_page"],
            "appendices_start_page": pages["appendices_start_page"],
            "checklist_start_page": pages["checklist_start_page"],
            "style_sha256": EXPECTED["papers/neurips_2026_vericode.sty"],
            "anonymous_block_retained": True,
        },
    )


def main() -> int:
    SNAPSHOT.mkdir(parents=True, exist_ok=True)
    shared = verify_shared_inputs()
    sty_bytes = SHARED_STY.read_bytes()
    checklist = make_checklist(SHARED_CHECKLIST.read_text(encoding="utf-8"))
    main_tex = patch_main((MANUSCRIPT / "main.tex").read_text(encoding="utf-8"))
    write_text(SNAPSHOT / "build_inputs/main.tex", main_tex)
    write_text(SNAPSHOT / "build_inputs/checklist.tex", checklist)
    copy_build_inputs(checklist, main_tex, sty_bytes)
    if os.environ.get("LA024_SKIP_LATEX") == "1" and (BUILD / "main.pdf").is_file() and (SNAPSHOT / "compiled/main.txt").is_file():
        txt = (SNAPSHOT / "compiled/main.txt").read_text(encoding="utf-8", errors="replace")
        pages = count_pages(txt)
        pages["pdf_bytes"] = (BUILD / "main.pdf").stat().st_size
        pages["pdf_sha256"] = sha256_file(BUILD / "main.pdf")
        pages["started_at"] = utc_now()
        pages["completed_at"] = utc_now()
        pages["exit_code"] = 0
        pages["log"] = "papers/completion/law_to_action/receipts/snapshots/LA-024/validation/compile.stdout.log"
    else:
        pages = compile_pdf()
    zip_info = pack_zip()
    if zip_info["bytes"] > 100 * 1024 * 1024 or pages["pdf_bytes"] > 50 * 1024 * 1024:
        fail("PDF or ZIP exceeds CFP size limits")
    cfp = load_cfp()
    write_private_alias_map()
    write_markdown_outputs(pages, zip_info, shared, cfp)
    copy_outputs(checklist, sty_bytes, pages)
    summary = {
        "status": "assembled",
        "main_text_pages": pages["main_text_pages"],
        "pdf_pages": pages["pdf_pages"],
        "pdf_bytes": pages["pdf_bytes"],
        "pdf_sha256": pages["pdf_sha256"],
        "zip_bytes": zip_info["bytes"],
        "zip_sha256": zip_info["sha256"],
        "style_sha256": EXPECTED["papers/neurips_2026_vericode.sty"],
    }
    write_json(SNAPSHOT / "assemble_summary.json", summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
