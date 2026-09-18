#!/usr/bin/env python3.12
"""Rebuild NS-022 paper.pdf as UTF-8 text for scoped binary admission."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
MS = PAPER / "manuscript"
SNAP = PAPER / "receipts/snapshots/NS-022"
ASCII_PDF = SNAP / "ascii_pdf.py"
LATEXMK = Path("/home/barberb/.local/bin/vericodegen-latexmk")
PDFLATEX = Path("/home/barberb/.local/share/vericodegen-texlive/.TinyTeX/bin/aarch64-linux/pdflatex")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(argv: list[str], cwd: Path, log: Path) -> None:
    started = datetime.now(timezone.utc)
    proc = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log.write_bytes(proc.stdout)
    if proc.returncode != 0:
        raise SystemExit(f"command failed ({proc.returncode}): {' '.join(argv)}\n{proc.stdout[-4000:].decode('utf-8', errors='replace')}")
    finished = datetime.now(timezone.utc)
    print(f"ok {' '.join(argv[:3])} elapsed={(finished-started).total_seconds():.3f}s")


def main() -> int:
    if not LATEXMK.is_file() or not PDFLATEX.is_file():
        raise SystemExit("TinyTeX wrapper/pdflatex missing")
    build_root = Path(tempfile.mkdtemp(prefix="ns022-ascii-build-"))
    ms_dir = build_root / "manuscript"
    audit_dir = build_root / "audit"
    ms_dir.mkdir()
    audit_dir.mkdir()
    shutil.copy2(MS / "main.tex", ms_dir / "main.tex")
    shutil.copy2(MS / "neurips_2026_vericode.sty", ms_dir / "neurips_2026_vericode.sty")
    shutil.copy2(MS / "formal_arguments.tex", ms_dir / "formal_arguments.tex")
    shutil.copytree(MS / "generated", ms_dir / "generated")
    shutil.copy2(PAPER / "audit/verified_references.bib", audit_dir / "verified_references.bib")

    pdflatex_cmd = (
        f"{PDFLATEX} -interaction=nonstopmode -halt-on-error -file-line-error "
        f"-no-shell-escape %O %S"
    )
    latexmk_argv = [
        str(LATEXMK),
        "-g",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-file-line-error",
        "-bibtex",
        f"-pdflatex={pdflatex_cmd}",
        "main.tex",
    ]
    env = os.environ.copy()
    env["SOURCE_DATE_EPOCH"] = "1789257600"
    started = datetime.now(timezone.utc)
    proc = subprocess.run(
        latexmk_argv,
        cwd=ms_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        env=env,
    )
    (SNAP / "build").mkdir(exist_ok=True)
    (SNAP / "build/latexmk.log").write_bytes(proc.stdout)
    (SNAP / "build/command.json").write_text(
        json.dumps(
            {
                "argv": latexmk_argv,
                "cwd": str(ms_dir),
                "shell_escape": False,
                "pdfobjcompresslevel": 0,
                "source_date_epoch": "1789257600",
                "exit_code": proc.returncode,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if proc.returncode != 0:
        raise SystemExit(f"latexmk failed:\n{proc.stdout[-4000:].decode('utf-8', errors='replace')}")
    raw_pdf = ms_dir / "main.pdf"
    ascii_pdf = build_root / "paper-ascii.pdf"
    run([sys.executable, str(ASCII_PDF), str(raw_pdf), str(ascii_pdf)], cwd=ROOT, log=SNAP / "build/ascii_pdf.log")
    data = ascii_pdf.read_bytes()
    data.decode("utf-8")
    if b"\x00" in data:
        raise SystemExit("ascii pdf still contains NUL")
    dest = MS / "paper.pdf"
    dest.write_bytes(data)
    snap_pdf = SNAP / "manuscript/paper.pdf"
    snap_pdf.parent.mkdir(parents=True, exist_ok=True)
    snap_pdf.write_bytes(data)
    shutil.copy2(MS / "main.tex", SNAP / "manuscript/main.tex")
    print(json.dumps({
        "paper_pdf_sha256": sha256(dest),
        "bytes": dest.stat().st_size,
        "utf8": True,
        "nul": False,
        "build_root": str(build_root),
        "latexmk_elapsed": (datetime.now(timezone.utc) - started).total_seconds(),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
