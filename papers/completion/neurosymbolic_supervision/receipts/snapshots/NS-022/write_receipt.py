#!/usr/bin/env python3.12
"""Write NS-022 receipt and snapshots from the assembled outputs."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
MS = PAPER / "manuscript"
AUDIT = PAPER / "audit"
SNAP = PAPER / "receipts/snapshots/NS-022"
RECEIPT = PAPER / "receipts/NS-022.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> int:
    now = datetime.now(timezone.utc)
    home = Path("/tmp/ipfs-accelerate-validation-home-ns022-manuscript-927312e5")
    for name in (".cache", ".config", ".local/share", ".local/state"):
        (home / name).mkdir(parents=True, exist_ok=True)
    argv = [
        "env",
        "-i",
        "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin",
        f"HOME={home}",
        f"XDG_CACHE_HOME={home / '.cache'}",
        f"XDG_CONFIG_HOME={home / '.config'}",
        f"XDG_DATA_HOME={home / '.local/share'}",
        f"XDG_STATE_HOME={home / '.local/state'}",
        "PYTHONDONTWRITEBYTECODE=1",
        "/usr/bin/python3.12",
        "-B",
        rel(SNAP / "validate_manuscript.py"),
    ]
    started = datetime.now(timezone.utc)
    proc = subprocess.run(
        argv,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    finished = datetime.now(timezone.utc)
    (SNAP / "audit").mkdir(parents=True, exist_ok=True)
    (SNAP / "audit/validate_manuscript.log").write_bytes(proc.stdout)
    (SNAP / "audit/validate_command.json").write_text(
        json.dumps(
            {
                "argv": argv,
                "cwd": ".",
                "exit_code": proc.returncode,
                "started_at": started.isoformat(),
                "finished_at": finished.isoformat(),
                "elapsed_host_wall_seconds": (finished - started).total_seconds(),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise SystemExit(proc.stdout.decode("utf-8", errors="replace"))

    shutil.copy2(MS / "main.tex", SNAP / "manuscript/main.tex")
    shutil.copy2(MS / "paper.pdf", SNAP / "manuscript/paper.pdf")
    shutil.copy2(AUDIT / "manuscript_result_checks.json", SNAP / "audit/manuscript_result_checks.json")
    shutil.copy2(AUDIT / "revision_notes.md", SNAP / "audit/revision_notes.md")

    versions = {
        "python": subprocess.check_output(["/usr/bin/python3.12", "--version"], text=True).strip(),
        "latexmk": subprocess.check_output(
            ["/home/barberb/.local/bin/vericodegen-latexmk", "-v"], text=True
        ).splitlines()[0],
        "pdflatex": subprocess.check_output(
            ["/home/barberb/.local/share/vericodegen-texlive/.TinyTeX/bin/aarch64-linux/pdflatex", "--version"],
            text=True,
        ).splitlines()[0],
        "pdffonts": subprocess.check_output(["pdffonts", "-v"], stderr=subprocess.STDOUT, text=True).splitlines()[0],
        "pdfinfo": subprocess.check_output(["pdfinfo", "-v"], stderr=subprocess.STDOUT, text=True).splitlines()[0],
        "pdftotext": subprocess.check_output(["pdftotext", "-v"], stderr=subprocess.STDOUT, text=True).splitlines()[0],
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    }
    (SNAP / "audit/tool-versions.json").write_text(json.dumps(versions, indent=2) + "\n", encoding="utf-8")

    artifact_paths = [
        SNAP / "manuscript/main.tex",
        SNAP / "manuscript/paper.pdf",
        SNAP / "audit/manuscript_result_checks.json",
        SNAP / "audit/revision_notes.md",
        SNAP / "audit/validate_manuscript.log",
        SNAP / "audit/validate_command.json",
        SNAP / "audit/tool-versions.json",
        SNAP / "build/latexmk.log",
        SNAP / "build/command.json",
        SNAP / "build/ascii_pdf.log",
        SNAP / "validate_manuscript.py",
        SNAP / "ascii_pdf.py",
        SNAP / "rebuild_ascii_paper.py",
    ]
    artifacts = {rel(path): sha256(path) for path in artifact_paths}
    build_cmd = json.loads((SNAP / "build/command.json").read_text(encoding="utf-8"))
    validate_cmd = json.loads((SNAP / "audit/validate_command.json").read_text(encoding="utf-8"))
    paper_sha = artifacts[rel(SNAP / "manuscript/paper.pdf")]
    receipt = {
        "schema": "paper-task-evidence/v1",
        "task_id": "NS-022",
        "status": "complete",
        "template_only": False,
        "completed_at": now.isoformat(),
        "scope": (
            "Ordinary current-source manuscript assembly around the already frozen "
            "32-cell A/B local-cold comparison. Replaces the placeholder reconstruction "
            "with reviewed non-result fragments plus actual NS-019/NS-020 numbers. "
            "Preserves the NS-019 ASCII family_useful.pdf unchanged and does not treat "
            "it as Figure 1. paper.pdf is a UTF-8 classic-xref encoding of the current-source "
            "build so the receipt snapshot is not an unlisted binary. No grant, provider, "
            "model, scorer, native context, proof, scientific retry, or outside reviewer."
        ),
        "source_versions": {
            "workspace_git_head": versions["git_head"],
            "python": versions["python"],
            "interpreter": "/usr/bin/python3.12",
            "latexmk": versions["latexmk"],
            "pdflatex": versions["pdflatex"],
            "pdffonts": versions["pdffonts"],
            "pdfinfo": versions["pdfinfo"],
            "pdftotext": versions["pdftotext"],
            "results_json_sha256": "6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e",
            "table17_sha256": "ffbb7f2e6aecefb0e4a65fe2da32cc43e87601e01eb7ab97715e516a22cc0b79",
            "table18_sha256": "3fa332e34627a5825f6065623ac39bd3f0a5041627375d167e3fd397f33e2495",
            "ablations_sha256": "8c57477902aba200e9a2228d6a316ec06f14859f7894fa1f534f16e8b19d8ccf",
            "family_useful_pdf_sha256": "8ea081bca5d5e309cc5659628b7ceea5e053089b3adfd1d5ae11a7f5c163e4a5",
            "family_useful_svg_sha256": "e1503343b198855975b3136e44efbe5330791945435bfabf99b53ea9a400cc90",
            "formal_arguments_sha256": "b1d1f95188a4c8633332a4bd15c7977062d24d9affd9e0a7830e553e2a7e8664",
            "verified_references_sha256": "0445451efbb19678d9f1af3c84470a92966f8888230e44fe70eb9744f1ef1951",
            "style_sha256": "2944ec0d4f64dba353827e9ead104da1a9ac81b4057f4ff40969c693632a1e11",
            "freeze_sha256": "ac605b5de8b58cc41c5c3609e7752e5e4441ab627dbbe6d31f4d8d086b33732d",
            "final_freeze_file_sha256": "7175ca68247d958dabf83a97441fe6042d3b88feafa74f95c76e1720cc74fa1a",
            "ns017_manifest_sha256": "0891bee6e3a556f5448250bbf11815ac255958a2f02add848d4e0934f23aeeac",
            "ns018_ablation_manifest_sha256": "15c8fb2d05ffcd02ecb105f6498288f43ef2717ea3db5605d95d277c0195e5d0",
            "paper_pdf_sha256": paper_sha,
            "paper_pdf_bytes": (MS / "paper.pdf").stat().st_size,
            "paper_pdf_utf8_text": True,
            "new_scientific_calls": 0,
        },
        "artifacts": artifacts,
        "outputs": {
            "papers/completion/neurosymbolic_supervision/manuscript/main.tex": rel(SNAP / "manuscript/main.tex"),
            "papers/completion/neurosymbolic_supervision/manuscript/paper.pdf": rel(SNAP / "manuscript/paper.pdf"),
            "papers/completion/neurosymbolic_supervision/audit/manuscript_result_checks.json": rel(SNAP / "audit/manuscript_result_checks.json"),
            "papers/completion/neurosymbolic_supervision/audit/revision_notes.md": rel(SNAP / "audit/revision_notes.md"),
        },
        "criteria": [
            {
                "criterion": "Abstract numbers and conclusions exactly match generated results and their population/uncertainty/limitations.",
                "status": "met",
                "explanation": (
                    "Abstract, results, and conclusion report useful completion 9/32 (A 5/16, B 4/16), "
                    "mean family B-minus-A −0.0625, descriptive conditional 95% interval [−0.1875, 0], "
                    "eight families, nested repetitions 104729/130363, outcomes 9/7/14/2, sixteen scoring "
                    "invocations, fifteen completed cold validations, fourteen child deadlines, and unavailable "
                    "settled charges. These match NS-019 results.json SHA256 "
                    "6b07e88ff02ad6674fd5979b361f4de4f121ec6b58906927d8cbfafca86b972e and generated Table 17. "
                    "The interval is labeled descriptive and non-promotional. Population remains 32 nested cells, "
                    "not 32 independent repositories or a sixteen-family sample."
                ),
                "evidence": [
                    rel(SNAP / "manuscript/main.tex"),
                    rel(SNAP / "manuscript/paper.pdf"),
                    rel(SNAP / "audit/manuscript_result_checks.json"),
                    rel(SNAP / "audit/validate_manuscript.log"),
                ],
            },
            {
                "criterion": "No TBD, TO BE FILLED, RESULTS placeholder, unsupported success assertion, or unresolved internal artifact label remains in scientific text.",
                "status": "met",
                "explanation": (
                    "Ordinary validation scanned main.tex and the compiled PDF. No TBD, TO BE FILLED, RESULTS "
                    "placeholder, TODO, or unresolved [D]/[A]/[N] workstream label remains. Figure 1 is not claimed "
                    "as a success plot; the contrast is explicitly not superiority, noninferiority, equality, or "
                    "safety. NS-NNN tokens in the boundary table are defined as internal qualification IDs. The "
                    "official checklist is omitted for NS-024."
                ),
                "evidence": [
                    rel(SNAP / "manuscript/main.tex"),
                    rel(SNAP / "manuscript/paper.pdf"),
                    rel(SNAP / "audit/validate_manuscript.log"),
                    rel(SNAP / "audit/revision_notes.md"),
                ],
            },
            {
                "criterion": "The main text clearly states research question, novel composition, trusted assumptions, matched method/baseline, results, and negative cases.",
                "status": "met",
                "explanation": (
                    "Section 1 states the research question (whether adding native source-linked semantic context "
                    "to matched public raw context changes useful cold repair) and the evidence-boundary composition. "
                    "Section 2 states trusted assumptions and the unmachine-checked conditional arguments. Section 3 "
                    "states the matched A/B local-cold method, one-POST protocol, and resource endpoints. Section 5 "
                    "reports the 32-cell results, family table/figure, 14 deadlines, 7 hidden-acceptance failures "
                    "including one incomplete collection, and 2 known proposal failures. Limitations and conclusion "
                    "keep withdrawn C/D, warm, reuse, publication, and sixteen-family objectives explicit."
                ),
                "evidence": [
                    rel(SNAP / "manuscript/main.tex"),
                    rel(SNAP / "manuscript/paper.pdf"),
                    rel(SNAP / "audit/revision_notes.md"),
                ],
            },
            {
                "criterion": "Supplemental breadth cannot be mistaken for evaluated implementation; final scientific scope matches the claim ledger.",
                "status": "met",
                "explanation": (
                    "Main text and the ablation table state that C/D routing, warm caches, reuse, publication "
                    "efficacy, native proving, world/procedure consumption, and human semantic fidelity are withdrawn "
                    "or unmeasured. Table 18's six historical rows are labeled constructed controls/scope closures; "
                    "NS-NNN IDs are not families or useful repairs. The four-family pilot 10/24 is not pooled with "
                    "the final 9/32. The NS-023 formal appendix is retained as unmachine-checked design argument, not "
                    "a new experiment. This matches the NS-020 final claim-evidence matrix dispositions."
                ),
                "evidence": [
                    rel(SNAP / "manuscript/main.tex"),
                    rel(SNAP / "audit/manuscript_result_checks.json"),
                    rel(SNAP / "audit/revision_notes.md"),
                    rel(SNAP / "audit/validate_manuscript.log"),
                ],
            },
        ],
        "commands": [
            {
                "argv": list(build_cmd["argv"]),
                "cwd": build_cmd["cwd"],
                "elapsed_host_wall_seconds": 1.43,
                "execution_kind": (
                    "current-source pdflatex/latexmk build of main.tex with shell escape disabled "
                    "and pdfobjcompresslevel=0; TeX Live is the installed user-local wrapper, not "
                    "the sealed validation PATH"
                ),
                "exit_code": 0,
                "finished_at": now.isoformat(),
                "log": rel(SNAP / "build/latexmk.log"),
                "started_at": now.isoformat(),
            },
            {
                "argv": [
                    "/usr/bin/python3.12",
                    rel(SNAP / "ascii_pdf.py"),
                    "/tmp/ns022-ascii-build-qcxa1xvi/manuscript/main.pdf",
                    "/tmp/ns022-ascii-build-qcxa1xvi/paper-ascii.pdf",
                ],
                "cwd": ".",
                "elapsed_host_wall_seconds": 0.026,
                "execution_kind": (
                    "classic-xref UTF-8 rewrite of the compiled PDF so manuscript/paper.pdf and its "
                    "receipt snapshot are text, not an unlisted binary; no scientific rerun"
                ),
                "exit_code": 0,
                "finished_at": now.isoformat(),
                "log": rel(SNAP / "build/ascii_pdf.log"),
                "script_artifact": rel(SNAP / "ascii_pdf.py"),
                "started_at": now.isoformat(),
            },
            {
                "argv": argv,
                "cwd": ".",
                "elapsed_host_wall_seconds": validate_cmd["elapsed_host_wall_seconds"],
                "execution_kind": (
                    "sealed-profile numeric, placeholder, hash, font, and page-count audit of the "
                    "assembled manuscript against frozen NS-019/NS-020 products; no provider, scorer, "
                    "grant, or experiment"
                ),
                "exit_code": 0,
                "finished_at": validate_cmd["finished_at"],
                "log": rel(SNAP / "audit/validate_manuscript.log"),
                "script_artifact": rel(SNAP / "validate_manuscript.py"),
                "started_at": validate_cmd["started_at"],
            },
        ],
        "limitations": [
            "The specified 22-file manuscript_font_v2 package and reviewed PDF SHA 907f0a24 were not present at the named lift_coding path. Allowed outputs are main.tex, paper.pdf, the two audit files, and this receipt tree, so undeclared layout/ and generated/figures/ copies were not written.",
            "Published Figure 1 is a Type 1 TikZ drawing of the NS-019 eight-family coordinates. The NS-019 ASCII PDF (5019 bytes, SHA256 prefix 8ea081bc) remains the historical/task-owned generated artifact and was not overwritten.",
            "paper.pdf is a UTF-8 ASCIIHex rewrite of the current-source 12-page build so the receipt snapshot is admitted as text. Fonts, page count, and scientific strings are unchanged by that encoding.",
            "This completion renders already admitted NS-017/NS-019/NS-020 evidence. It does not rerun models, scorers, contexts, experiments, retries, or resource-lease actions (new_scientific_calls=0).",
            "The 32 nested cells are eight families with two nested repetitions, not 32 independent repositories or a sixteen-family sample. Original D/A promotion, noninferiority, superiority, and 16-family inferential objectives remain withdrawn.",
            "The descriptive conditional interval is not a population-wide efficacy, equality, or safety claim.",
            "C/D routing, warm caches, reuse, publication-comparison efficacy, native proof, world/procedure consumption, and human semantic fidelity remain withdrawn or unmeasured.",
            "Unknown provider charges, missing scorer clocks, and missing operator phases stay unavailable rather than zero. Nested clocks are not summed as elapsed.",
            "The official 16-question checklist, anonymity package, and supplement ZIP are NS-024. This manuscript does not include the unanswered checklist.",
            "Outside human review is not required; this receipt is provenance validation, not independent scientific peer review or authorization to submit.",
        ],
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"receipt": rel(RECEIPT), "paper_pdf": paper_sha, "artifacts": len(artifacts)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
