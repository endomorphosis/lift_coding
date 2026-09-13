#!/bin/sh
# One-command bounded reproduction and analysis for LA-023.
# Uses the sealed validation PATH and /usr/bin/python3.12 only.
set -eu

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONHASHSEED=0
export SOURCE_DATE_EPOCH=0
unset PYTHONPATH PYTHONHOME PYTHONUSERBASE || true

PYTHON="/usr/bin/python3.12"
if [ ! -x "$PYTHON" ]; then
  echo "LA-023: required interpreter missing: $PYTHON" >&2
  exit 1
fi

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

exec "$PYTHON" - "$HERE" <<'PY'
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

SEALED_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin"
PYTHON = "/usr/bin/python3.12"

here = Path(sys.argv[1]).resolve()
os.environ["PATH"] = SEALED_PATH
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
os.environ["PYTHONHASHSEED"] = "0"

if os.environ.get("PATH") != SEALED_PATH:
    raise SystemExit("LA-023: failed to pin sealed PATH")
if Path(sys.executable).resolve() != Path(PYTHON).resolve():
    raise SystemExit(f"LA-023: interpreter must be {PYTHON}, got {sys.executable}")

def is_bundle(path: Path) -> bool:
    return (path / "bundle.manifest.json").is_file() and (path / "scripts" / "check_artifact.py").is_file()

checker = here / "scripts" / "check_artifact.py"
supplement = here / "anonymous_supplement.zip"
artifact_dir = here if (here / "manifest.json").is_file() else None

if checker.is_file() and is_bundle(here):
    bundle = here
    argv = [PYTHON, str(checker), "--bundle", str(bundle)]
    if artifact_dir is not None:
        argv.extend(["--artifact", str(artifact_dir)])
elif supplement.is_dir() and is_bundle(supplement):
    checker = supplement / "scripts" / "check_artifact.py"
    argv = [PYTHON, str(checker), "--bundle", str(supplement), "--artifact", str(here), "--zip", str(supplement)]
elif supplement.is_file():
    checker = here / "receipts" / "snapshots" / "LA-023" / "check_artifact.py"
    if not checker.is_file():
        # Packed ZIP is checked by extracting inside check_artifact.py.
        checker = None
        for candidate in (here / "scripts" / "check_artifact.py",):
            if candidate.is_file():
                checker = candidate
                break
        if checker is None:
            raise SystemExit("LA-023: packed zip present but checker script is missing")
    argv = [PYTHON, str(checker), "--artifact", str(here), "--zip", str(supplement)]
else:
    raise SystemExit("LA-023: neither directory bundle nor packed anonymous_supplement.zip is present")

mode = Path(argv[1]).stat().st_mode
if not mode & stat.S_IRUSR:
    raise SystemExit("LA-023: checker is not readable")
raise SystemExit(subprocess.run(argv, check=False).returncode)
PY
