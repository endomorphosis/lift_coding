#!/usr/bin/env python3
"""Compile the anonymous workshop PDF from the official style and completed questionnaire."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
PAPER = REPO_ROOT / "papers/completion/autoformalization"
MS = PAPER / "manuscript"
RESULTS = PAPER / "results"
OFFICIAL_STY = REPO_ROOT / "papers/neurips_2026_vericode.sty"
TEXBIN = Path("/home/barberb/.local/share/vericodegen-texlive/.TinyTeX/bin/aarch64-linux")
WRAPPER = Path("/home/barberb/.local/bin/vericodegen-latexmk")
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"

PATCH_PACKAGES = (
    r"\usepackage{hyperref,url,booktabs,amsfonts,amsmath,amssymb,graphicx,xcolor}"
    "\n"
    r"\hypersetup{pdfauthor={Anonymous Author(s)},pdftitle={Compiler-Guided Autoformalization with Adaptive Multi-View Representations},pdfsubject={NeurIPS 2026 Workshop on AI for Verifiable Coding},pdfcreator={LaTeX with neurips_2026_vericode},pdfproducer={pdfTeX}}"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def patch_main(text: str) -> str:
    if r"\usepackage{neurips_2026_vericode}" not in text.splitlines()[4] and r"\usepackage{neurips_2026_vericode}" not in text:
        raise SystemExit("manuscript does not load neurips_2026_vericode")
    if r"\usepackage[" in text and "neurips_2026_vericode" in text:
        for line in text.splitlines():
            if "neurips_2026_vericode" in line and line.strip().startswith(r"\usepackage["):
                raise SystemExit(f"non-default style options: {line}")
    text = text.replace(
        r"\usepackage{hyperref,url,booktabs,amsfonts,amsmath,amssymb,graphicx}",
        PATCH_PACKAGES,
    )
    if "xcolor" not in text:
        raise SystemExit("failed to add xcolor for official checklist macros")
    if "AF024-BEFORE-BIB" not in text:
        text = text.replace(
            r"\bibliographystyle{plainnat}",
            "\\typeout{AF024-BEFORE-BIB:\\thepage}\n\\bibliographystyle{plainnat}",
            1,
        )
        text = text.replace(
            r"\appendix",
            "\\typeout{AF024-BEFORE-APPENDIX:\\thepage}\n\\appendix",
            1,
        )
    if r"\input{llm_disclosure.tex}" not in text:
        text = text.replace(
            r"\end{document}",
            "\\typeout{AF024-BEFORE-DISCLOSURE:\\thepage}\n"
            "\\input{llm_disclosure.tex}\n"
            "\\newpage\n"
            "\\typeout{AF024-BEFORE-CHECKLIST:\\thepage}\n"
            "\\input{checklist.tex}\n"
            "\\end{document}\n",
        )
    if r"\input{checklist.tex}" not in text or r"\input{llm_disclosure.tex}" not in text:
        raise SystemExit("failed to include disclosure and checklist")
    if "AF024-BEFORE-BIB" not in text:
        raise SystemExit("failed to mark bibliography page")
    return text


def copy_build_tree(work: Path) -> Path:
    ms = work / "manuscript"
    results = work / "results"
    ms.mkdir(parents=True)
    results.mkdir()
    for name in (
        "references.bib",
        "figure-01.tex",
        "empirical_scope.tex",
        "neurips_2026_vericode.sty",
        "checklist.tex",
        "llm_disclosure.tex",
    ):
        shutil.copy2(MS / name, ms / name)
    shutil.copy2(OFFICIAL_STY, ms / "neurips_2026_vericode.sty")
    for name in ("table6_pipeline.tex", "table11_training.tex", "table13_assistance.tex"):
        shutil.copy2(RESULTS / name, results / name)
    patched = patch_main((MS / "main.tex").read_text(encoding="utf-8"))
    (ms / "main.tex").write_text(patched, encoding="utf-8")
    return ms


def main() -> int:
    logs = PAPER / "evidence/final_correction/format_logs"
    logs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OFFICIAL_STY, MS / "neurips_2026_vericode.sty")
    home = Path(tempfile.mkdtemp(prefix="ipfs-accelerate-validation-home-af024-tex-"))
    for sub in (".cache", ".config", ".local/share", ".local/state"):
        (home / sub).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="af024-tex-build-"))
    ms = copy_build_tree(work)
    build_src = PAPER / "evidence/final_correction/build"
    if build_src.exists():
        shutil.rmtree(build_src)
    shutil.copytree(ms, build_src)
    env = {
        "PATH": f"{TEXBIN}:{SEALED_PATH}",
        "HOME": str(home),
        "XDG_CACHE_HOME": str(home / ".cache"),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "XDG_DATA_HOME": str(home / ".local/share"),
        "XDG_STATE_HOME": str(home / ".local/state"),
        "USER": "anonymous",
        "USERNAME": "anonymous",
        "LOGNAME": "anonymous",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "SOURCE_DATE_EPOCH": "1767225600",
        "TEXMFVAR": str(home / ".cache" / "texmf-var"),
        "TEXMFCONFIG": str(home / ".config" / "texmf-config"),
        "TEXMFHOME": str(home / ".local" / "share" / "texmf"),
        "openout_any": "a",
        "openin_any": "a",
    }
    argv = [
        str(WRAPPER),
        "-g",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "main.tex",
    ]
    started = utc_now()
    t0 = time.perf_counter()
    proc = subprocess.run(
        argv,
        cwd=str(ms),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    elapsed = time.perf_counter() - t0
    finished = utc_now()
    stdout_path = logs / "latexmk.stdout.log"
    stderr_path = logs / "latexmk.stderr.log"
    stdout_path.write_text(proc.stdout, encoding="utf-8", errors="replace")
    stderr_path.write_text(proc.stderr, encoding="utf-8", errors="replace")
    pdf = ms / "main.pdf"
    log = ms / "main.log"
    if log.is_file():
        shutil.copy2(log, logs / "pdflatex.main.log")
    out_pdf = PAPER / "submission" / "paper.pdf"
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    snap_pdf = PAPER / "evidence/final_correction/paper.pdf"
    snap_pdf.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "argv": argv,
        "cwd": str(ms),
        "elapsed_seconds": elapsed,
        "env": {
            "HOME": str(home),
            "LANG": "C.UTF-8",
            "PATH": env["PATH"],
            "USER": "anonymous",
            "SOURCE_DATE_EPOCH": env["SOURCE_DATE_EPOCH"],
        },
        "exit_code": proc.returncode,
        "finished_at": finished,
        "name": "latexmk",
        "pdf_exists": pdf.is_file(),
        "started_at": started,
        "texbin": str(TEXBIN),
        "wrapper": str(WRAPPER),
    }
    (logs / "latexmk.meta.json").write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if proc.returncode != 0 or not pdf.is_file():
        print(json.dumps({"ok": False, "meta": meta, "stderr_tail": proc.stderr[-4000:]}, indent=2))
        return 1
    shutil.copy2(pdf, out_pdf)
    shutil.copy2(pdf, snap_pdf)
    shutil.copy2(ms / "main.aux", PAPER / "evidence/final_correction/main.aux")
    import hashlib
    identity = {"sha256":hashlib.sha256(out_pdf.read_bytes()).hexdigest(), "bytes":out_pdf.stat().st_size}
    (PAPER / "evidence/final_correction/paper.identity.json").write_text(json.dumps(identity,sort_keys=True,indent=2)+"\n")
    print(json.dumps({"ok": True, "pdf_bytes": out_pdf.stat().st_size, "elapsed_seconds": elapsed}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
