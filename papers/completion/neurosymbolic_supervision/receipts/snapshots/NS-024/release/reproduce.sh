#!/bin/sh
# Portable NS-024 numerical reproduction wrapper.
# Extracts the adjacent supplement.zip into a fresh directory and runs the
# included reproduce.py. This regenerates retained scalar summaries only.
# It does not call providers, scorers, hidden tests, native services, or
# networks, and it does not authenticate original private signatures.
set -eu

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ZIP="$HERE/supplement.zip"
PYTHON="${PYTHON:-python3}"

usage() {
  echo "usage: $0 ABSOLUTE_EXTRACT_DIR ABSOLUTE_OUTPUT_DIR" >&2
  echo "Extract supplement.zip into a new directory and run included reproduce.py." >&2
  echo "Both paths must be absolute and must not already exist." >&2
  exit 2
}

if [ "$#" -ne 2 ]; then
  usage
fi

EXTRACT=$1
OUTPUT=$2
case "$EXTRACT" in
  /*) ;;
  *) echo "extract directory must be an absolute path" >&2; exit 2 ;;
esac
case "$OUTPUT" in
  /*) ;;
  *) echo "output directory must be an absolute path" >&2; exit 2 ;;
esac
if [ -e "$EXTRACT" ] || [ -e "$OUTPUT" ]; then
  echo "extract and output directories must not already exist" >&2
  exit 2
fi
if [ ! -f "$ZIP" ]; then
  echo "missing $ZIP" >&2
  exit 2
fi

"$PYTHON" -B -c '
import sys
from pathlib import Path
import zipfile
zip_path = Path(sys.argv[1])
dest = Path(sys.argv[2])
if dest.exists():
    raise SystemExit("extract directory already exists")
dest.mkdir(mode=0o700)
with zipfile.ZipFile(zip_path) as archive:
    archive.extractall(dest)
' "$ZIP" "$EXTRACT"

"$PYTHON" -B "$EXTRACT/reproduce.py" --root "$EXTRACT" --output "$OUTPUT"
