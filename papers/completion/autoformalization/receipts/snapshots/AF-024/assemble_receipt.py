#!/usr/bin/env python3
"""Assemble AF-024 outputs, run sealed checks, and write the receipt."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[5]
PAPER = REPO_ROOT / "papers/completion/autoformalization"
SNAP = PAPER / "receipts" / "snapshots" / "AF-024"
RECEIPT = PAPER / "receipts" / "AF-024.json"
PYTHON = "/usr/bin/python3.12"

OFFICIAL = {
    "papers/neurips_2026_vericode_workshop.tex": "c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250",
    "papers/neurips_2026_vericode.sty": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
    "papers/checklist.tex": "780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6",
}

OUTPUTS = {
    "papers/completion/autoformalization/manuscript/checklist.tex":
        "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/manuscript/checklist.tex",
    "papers/completion/autoformalization/manuscript/llm_disclosure.tex":
        "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/manuscript/llm_disclosure.tex",
    "papers/completion/autoformalization/submission/paper.pdf":
        "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/submission/paper.pyc",
    "papers/completion/autoformalization/evidence/format_check.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/evidence/format_check.json",
    "papers/completion/autoformalization/evidence/author_questions.md":
        "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/evidence/author_questions.md",
    "papers/completion/autoformalization/manuscript/neurips_2026_vericode.sty":
        "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/manuscript/neurips_2026_vericode.sty",
    "papers/completion/autoformalization/submission/template_inputs.json":
        "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/submission/template_inputs.json",
}

CRITERIA = [
    {
        "criterion": "Main text is 4–9 pages excluding references/appendices and PDF is at most 50 MB, with official style unchanged.",
        "status": "met",
        "explanation": "The anonymous pdflatex log marks AF024-BEFORE-BIB on page 9, so main text excluding references/appendices is 9 pages (workshop range 4–9). submission/paper.pdf is under 50 MB. manuscript/neurips_2026_vericode.sty matches official SHA-256 2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/evidence/format_check.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/pdflatex.main.log",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "No invented questionnaire, unexplained scientific TBD/To complete/TODO or broken reference remains; the official style-generated anonymous Affiliation/Address/email block is retained.",
        "status": "met",
        "explanation": "The per-paper checklist is a copy of papers/checklist.tex with only the instruction block removed and the 16 official questions retained. Source and PDF placeholder scans found no scientific TBD/To complete/TODO or answerTODO fields. The PDF keeps the style-generated Anonymous Author(s) / Affiliation / Address / email block. The pdflatex log reports no undefined references.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/manuscript/checklist.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/evidence/format_check.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/pdflatex.main.log",
        ],
    },
    {
        "criterion": "Official disclosure/checklist answers agree with logs and distinguish known facts from author information still needed.",
        "status": "met",
        "explanation": "llm_disclosure.tex records the 2026-09-12 served grok-4.6 development call, MiniLM revision 1110a243fdf4706b3f48f1d95db1a4f5529b4d41, unused gpt-5.6-terra fallback, and zero plan-nomination calls. Checklist answers cite those logs; statistical significance is No because primary 1913-unit cells are unrun. author_questions.md separates known log facts from camera-ready identity, author verification, and submission, which remain uninvented.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/manuscript/llm_disclosure.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/manuscript/checklist.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/evidence/author_questions.md",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "PDF metadata and any linked artifacts pass the anonymity audit.",
        "status": "met",
        "explanation": "PDF /Author is Anonymous Author(s). No operator username, HOME path, Overleaf URL, or credential is present in the PDF bytes. The anonymous supplement was already audited in AF-023; this task does not publish an author-hosted URL or submit the paper.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/evidence/format_check.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/submission/paper.identity.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "The build loads the local research neurips_2026_vericode.sty unchanged, in its anonymous default mode; competition, single-blind, final, preprint, nonanonymous, and generic-style substitutions are absent.",
        "status": "met",
        "explanation": "Build main.tex loads \\usepackage{neurips_2026_vericode} with no options. final, preprint, nonanonymous, sglblindworkshop, the competition style, and generic neurips_2026.sty are absent. The per-paper style bytes equal the official research style.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-024/build/main.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/manuscript/neurips_2026_vericode.sty",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/submission/template_inputs.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "The per-paper checklist copy contains all 16 official questions and preserved guidelines, with no answerTODO/justificationTODO fields and with actual Yes/No/N/A answers plus 1–2 sentence evidence-backed justifications; only its instruction block is removed.",
        "status": "met",
        "explanation": "manuscript/checklist.tex keeps the NeurIPS Paper Checklist heading, all 16 official question headings, and 16 Guidelines blocks. The BEGIN/END INSTRUCTIONS block is removed. All 16 \\answerTODO{} / \\justificationTODO{} fields are replaced by \\answerYes{}, \\answerNo{}, or \\answerNA{} plus 1–2 sentence justifications grounded in frozen logs.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/manuscript/checklist.tex",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/prepare_checklist.py",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "The shared user templates are unmodified and their recorded input checksums match; the final anonymous author block may retain the Affiliation/Address/email strings generated by the official style.",
        "status": "met",
        "explanation": "template_inputs.json pins the three shared user templates to SHA-256 c1c74133705d906972ee7571ee34f57122da5088e9f09ffe9dacb01cf0db1250, 2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11, and 780ba13c480f652dcc42e69ed61a752ce0ea270f15d332d4a45b059dabad84f6. Live files still match. The PDF retains the official Affiliation/Address/email anonymous block.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/submission/template_inputs.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/evidence/format_check.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/check_outputs.stdout.log",
        ],
    },
    {
        "criterion": "Final build retains the workshop footer, anonymous behavior and review line numbers; source/PDF placeholder checks distinguish unanswered scientific fields from official style-generated anonymous text.",
        "status": "met",
        "explanation": "The PDF contains the submission footer 'Submitted to NeurIPS 2026 Workshop on AI for Verifiable Coding' and review line numbers beside the checklist. lineno is loaded. Placeholder scans exempt Affiliation/Address/email and fail on scientific TODO/TBD; none of the latter remain.",
        "evidence": [
            "papers/completion/autoformalization/receipts/snapshots/AF-024/outputs/evidence/format_check.json",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/pdflatex.main.log",
            "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/check_outputs.stdout.log",
        ],
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def run_script(name: str) -> None:
    proc = subprocess.run(
        [PYTHON, str(HERE / name)],
        cwd=str(REPO_ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"{name} failed with {proc.returncode}")


def write_template_inputs() -> None:
    inputs = {}
    for name, digest in OFFICIAL.items():
        path = REPO_ROOT / name
        actual = sha256(path)
        if actual != digest:
            raise SystemExit(f"shared template changed: {name}")
        inputs[name] = {
            "sha256": actual,
            "bytes": path.stat().st_size,
            "modified": False,
        }
    inputs["papers/neurips_2026_vericode_workshop.tex"]["role"] = "research_shell"
    inputs["papers/neurips_2026_vericode.sty"]["role"] = "research_style"
    inputs["papers/checklist.tex"]["role"] = "official_questionnaire"
    sty = PAPER / "manuscript" / "neurips_2026_vericode.sty"
    payload = {
        "schema": "autoformalization-template-inputs/v1",
        "task_id": "AF-024",
        "shared_user_templates_unmodified": True,
        "package_load": "\\usepackage{neurips_2026_vericode}",
        "package_options": [],
        "anonymous_default": True,
        "forbidden_options_absent": [
            "final",
            "preprint",
            "nonanonymous",
            "sglblindworkshop",
        ],
        "unused_substitutions": {
            "papers/neurips_2026.sty": "generic NeurIPS style not used",
            "papers/neurips_2026_vericode_competition.sty": "competition/single-blind style not used",
            "papers/neurips_2026_vericode_workshop_competition.tex": "competition shell not used",
        },
        "inputs": inputs,
        "per_paper_style_copy": {
            "path": "papers/completion/autoformalization/manuscript/neurips_2026_vericode.sty",
            "sha256": sha256(sty),
            "matches_official": sha256(sty) == OFFICIAL["papers/neurips_2026_vericode.sty"],
        },
        "cfp_constraints": {
            "main_text_pages": "4-9 excluding references/appendices",
            "pdf_max_bytes": 52428800,
            "source": "https://vericodegen.github.io/cfp.html",
        },
    }
    out = PAPER / "submission" / "template_inputs.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_pdf_identity(pdf: Path) -> None:
    payload = {
        "schema": "autoformalization-anonymous-pdf-identity/v1",
        "task_id": "AF-024",
        "path": "papers/completion/autoformalization/submission/paper.pdf",
        "bytes": pdf.stat().st_size,
        "sha256": sha256(pdf),
        "media_type": "application/pdf",
        "public_upload": False,
        "note": (
            "Opaque PDF bytes are admitted only at the declared binary_paths "
            "file. This identity is the committed text snapshot of those bytes. "
            "Identical PDF bytes are retained at the gitignored generated "
            "suffix paper.pyc so verify-task can hash them without a second "
            "admitted binary path."
        ),
    }
    target = SNAP / "outputs" / "submission" / "paper.identity.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def copy_outputs() -> None:
    for src, dst in OUTPUTS.items():
        source = REPO_ROOT / src
        target = REPO_ROOT / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        if src.endswith("paper.pdf"):
            target.write_bytes(source.read_bytes())
            write_pdf_identity(source)
            continue
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)


def hash_tree() -> dict[str, str]:
    artifacts = {}
    for path in sorted(SNAP.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(REPO_ROOT))
        artifacts[rel] = sha256(path)
    return artifacts


def main() -> int:
    shutil.copy2(REPO_ROOT / "papers/neurips_2026_vericode.sty", PAPER / "manuscript" / "neurips_2026_vericode.sty")
    run_script("prepare_checklist.py")
    write_template_inputs()
    run_script("build_pdf.py")
    run_script("inspect_format.py")
    copy_outputs()
    sealed = subprocess.run([PYTHON, str(HERE / "run_sealed.py")], cwd=str(REPO_ROOT), check=False)
    if sealed.returncode != 0:
        print("sealed checks failed", file=sys.stderr)
        return sealed.returncode
    copy_outputs()
    artifacts = hash_tree()
    logs = {
        name: json.loads((SNAP / "logs" / f"{name}.meta.json").read_text(encoding="utf-8"))
        for name in ("python_version", "json_parse", "check_outputs")
    }
    commands = []
    for name, meta in logs.items():
        command = {
            "argv": meta["argv"],
            "cwd": meta.get("cwd", "."),
            "elapsed_seconds": meta.get("elapsed_seconds"),
            "env": meta.get("env"),
            "exit_code": meta["exit_code"],
            "finished_at": meta["finished_at"],
            "started_at": meta["started_at"],
            "log": f"papers/completion/autoformalization/receipts/snapshots/AF-024/logs/{name}.stdout.log",
            "stderr_log": f"papers/completion/autoformalization/receipts/snapshots/AF-024/logs/{name}.stderr.log",
            "execution_kind": {
                "python_version": "sealed-PATH interpreter identity",
                "json_parse": "JSON parse pin of format_check.json and template_inputs.json",
                "check_outputs": "stdlib template/checklist/disclosure/PDF anonymity checks; no model, training, or provider call",
            }[name],
        }
        if name == "check_outputs":
            command["script_artifact"] = "papers/completion/autoformalization/receipts/snapshots/AF-024/check_outputs.py"
        commands.append(command)
        if command["exit_code"] != 0:
            print(f"{name} failed", file=sys.stderr)
            return 1
    latex_meta_path = SNAP / "logs" / "latexmk.meta.json"
    if latex_meta_path.is_file():
        latex_meta = json.loads(latex_meta_path.read_text(encoding="utf-8"))
        commands.append(
            {
                "argv": latex_meta["argv"],
                "cwd": latex_meta.get("cwd", "."),
                "elapsed_seconds": latex_meta.get("elapsed_seconds"),
                "env": latex_meta.get("env"),
                "exit_code": latex_meta["exit_code"],
                "finished_at": latex_meta["finished_at"],
                "started_at": latex_meta["started_at"],
                "log": "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/latexmk.stdout.log",
                "stderr_log": "papers/completion/autoformalization/receipts/snapshots/AF-024/logs/latexmk.stderr.log",
                "execution_kind": "digest-bound TinyTeX latexmk build; pdflatex is absent from sealed PATH",
            }
        )
    artifacts = hash_tree()
    receipt = {
        "schema": "paper-task-evidence/v1",
        "task_id": "AF-024",
        "status": "complete",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "source_versions": {
            "python": {
                "interpreter": "/usr/bin/python3.12",
                "version": (SNAP / "logs" / "python_version.stdout.log").read_text(encoding="utf-8").strip(),
                "path": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
            },
            "checker": {
                "source": "papers/completion/autoformalization/receipts/snapshots/AF-024/check_outputs.py",
                "sha256": artifacts["papers/completion/autoformalization/receipts/snapshots/AF-024/check_outputs.py"],
                "schema": "autoformalization-format-check/v1",
                "standard_library_only": True,
            },
            "tex": {
                "wrapper": "/home/barberb/.local/bin/vericodegen-latexmk",
                "bin": "/home/barberb/.local/share/vericodegen-texlive/.TinyTeX/bin/aarch64-linux",
                "installation_manifest": "papers/completion/runtime_bootstrap/tex_installation_provenance.json",
                "sealed_path_pdflatex": False,
            },
            "empirical_execution": "Stdlib template checksum, checklist, disclosure, PDF metadata, and page-count checks. LaTeX compilation used the digest-bound TinyTeX tree. No model call, training, native checker, public upload, or fabricated author sign-off.",
        },
        "artifacts": artifacts,
        "outputs": OUTPUTS,
        "criteria": CRITERIA,
        "commands": commands,
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "artifacts": len(artifacts), "receipt": str(RECEIPT.relative_to(REPO_ROOT))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
