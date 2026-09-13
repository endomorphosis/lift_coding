#!/usr/bin/python3.12
"""Sealed-PATH validator for LA-023 artifact consistency."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve()
while ROOT != ROOT.parent and not (ROOT / "papers/completion/law_to_action").is_dir():
    ROOT = ROOT.parent
PAPER = ROOT / "papers/completion/law_to_action"
CHECKER = PAPER / "receipts/snapshots/LA-023/check_artifact.py"
ARTIFACT = PAPER / "artifact"
PYTHON = "/usr/bin/python3.12"
SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"


def main() -> int:
    os.environ["PATH"] = SEALED_PATH
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["PYTHONHASHSEED"] = "0"
    os.environ["SOURCE_DATE_EPOCH"] = "0"
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("PYTHONHOME", None)
    os.environ.pop("PYTHONUSERBASE", None)
    if Path(sys.executable).resolve() != Path(PYTHON).resolve():
        raise SystemExit(f"LA-023: interpreter must be {PYTHON}, got {sys.executable}")
    if os.environ["PATH"] != SEALED_PATH:
        raise SystemExit("LA-023: sealed PATH was not applied")
    reproduce = subprocess.run(
        ["bash", str(ARTIFACT / "reproduce.sh")],
        cwd=str(ROOT),
        env=os.environ.copy(),
    )
    if reproduce.returncode != 0:
        raise SystemExit(f"LA-023: reproduce.sh exited {reproduce.returncode}")
    zip_arg = ARTIFACT / "anonymous_supplement.zip"
    checker = subprocess.run(
        [
            PYTHON,
            str(CHECKER),
            "--artifact",
            str(ARTIFACT),
            "--checkout",
            str(ROOT),
            "--zip",
            str(zip_arg),
        ],
        cwd=str(ROOT),
        env=os.environ.copy(),
    )
    if checker.returncode != 0:
        raise SystemExit(f"LA-023: check_artifact.py exited {checker.returncode}")
    private = PAPER / "private/source_provenance.json"
    if zip_arg.is_dir():
        for path in zip_arg.rglob("*"):
            if not path.is_file():
                continue
            if path.name == "check_artifact.py":
                continue
            data = path.read_bytes()
            lowered = data.lower()
            if b"barberb" in lowered or b"overleaf.com/project" in lowered:
                raise SystemExit(f"LA-023: bundle member contains identifying material: {path}")
            if b"BEGIN OPENSSH" in data or b"AKIA" in data:
                raise SystemExit(f"LA-023: bundle member contains credential material: {path}")
            if private.is_file() and private.read_bytes() in data:
                raise SystemExit("LA-023: private author companion bytes were packaged")
    elif zip_arg.is_file():
        zip_bytes = zip_arg.read_bytes()
        forbidden = (b"barberb", b"overleaf.com/project", b"BEGIN OPENSSH", b"AKIA")
        hits = [token.decode() for token in forbidden if token.lower() in zip_bytes.lower()]
        if hits:
            raise SystemExit(f"LA-023: anonymous ZIP contains identifying material: {hits}")
        if private.is_file() and private.read_bytes() in zip_bytes:
            raise SystemExit("LA-023: private author companion bytes were packaged")
    else:
        raise SystemExit("LA-023: anonymous_supplement.zip is missing")
    print("LA-023 validation ok: bounded reproduce.sh and artifact consistency checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
