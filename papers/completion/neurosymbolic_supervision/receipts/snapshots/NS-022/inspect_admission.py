#!/usr/bin/env python3.12
"""Inspect NS-022 admission-relevant file identities. No scientific calls."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
PAPER = ROOT / "papers/completion/neurosymbolic_supervision"
OUT = Path(__file__).resolve().parent / "inspect_admission.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pdf_flags(path: Path) -> dict:
    raw = path.read_bytes()
    utf8 = True
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        utf8 = False
    sample = raw[:8192]
    controls = sum(b < 32 and b not in {9, 10, 12, 13} for b in sample)
    return {
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "nul": b"\x00" in raw,
        "nul_in_sample": b"\x00" in sample,
        "utf8": utf8,
        "starts_pdf": raw.startswith(b"%PDF-"),
        "looks_binary_sample": (b"\x00" in sample) or (controls * 20 > len(sample)),
        "header": raw[:80].decode("latin-1", errors="replace"),
    }


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        text=True,
    )
    return (result.stdout or "") + (("\nSTDERR:\n" + result.stderr) if result.stderr else "")


def main() -> int:
    ms = PAPER / "manuscript"
    files = {
        "main.tex": ms / "main.tex",
        "paper.pdf": ms / "paper.pdf",
        "main.pdf": ms / "main.pdf",
        "main.aux": ms / "main.aux",
        "main.log": ms / "main.log",
        "family_useful.pdf": ms / "generated/figures/family_useful.pdf",
        "snapshot_paper.pdf": PAPER / "receipts/snapshots/NS-022/manuscript/paper.pdf",
        "snapshot_main.tex": PAPER / "receipts/snapshots/NS-022/manuscript/main.tex",
    }
    info = {
        "cwd": str(ROOT),
        "git_status_short": git("status", "--short", "--", "papers/completion/neurosymbolic_supervision"),
        "git_status_untracked_manuscript": git(
            "ls-files", "--others", "--exclude-standard", "--",
            "papers/completion/neurosymbolic_supervision/manuscript",
        ),
        "git_diff_names": git(
            "diff", "--name-status", "HEAD", "--",
            "papers/completion/neurosymbolic_supervision",
        ),
        "tracked_manuscript": git(
            "ls-files", "--", "papers/completion/neurosymbolic_supervision/manuscript",
        ),
        "files": {},
        "which": {
            "latexmk": git("rev-parse", "--is-inside-work-tree"),
        },
    }
    for name, path in files.items():
        if not path.is_file():
            info["files"][name] = {"exists": False, "path": str(path)}
            continue
        rec = {"exists": True, "path": str(path.relative_to(ROOT)), "bytes": path.stat().st_size, "sha256": sha256(path)}
        if path.suffix.lower() == ".pdf":
            rec.update(pdf_flags(path))
        info["files"][name] = rec
    wrappers = [
        "/home/barberb/.local/bin/vericodegen-latexmk",
        "/usr/bin/pdflatex",
        "/usr/bin/latexmk",
        "/usr/bin/pdffonts",
        "/usr/bin/pdfinfo",
        "/usr/bin/pdftotext",
        "/usr/bin/python3.12",
    ]
    info["tools"] = {p: os.path.isfile(p) for p in wrappers}
    OUT.write_text(json.dumps(info, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(str(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
